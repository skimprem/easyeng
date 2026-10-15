import re
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

from django.db import transaction

from ..models import Dictionary, DictionaryEntry
from ..sanitize import clean_html
from ..text import normalize_key
from . import stardict, tsv

BATCH = 2000
WIKILINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")  # [[зуб|зу́бьев]] -> зу́бьев
MAX_UNPACKED = 1024 * 1024 * 1024  # 1 GB
ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2")
KEEP_SUFFIXES = (".ifo", ".idx", ".idx.gz", ".dict", ".dict.dz", ".syn", ".tsv", ".txt")


class ImportError_(Exception):
    pass


def _safe_name(name):
    # Берём только имя файла: никаких путей из архива (защита от ../ и абсолютных путей)
    return Path(name.replace("\\", "/")).name


def _unpack(src: Path, dest: Path):
    """Распаковывает только нужные файлы, плоско, с проверкой размера."""
    total = 0
    lower = src.name.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(src) as zf:
            for info in zf.infolist():
                name = _safe_name(info.filename)
                if info.is_dir() or not name.lower().endswith(KEEP_SUFFIXES):
                    continue
                total += info.file_size
                if total > MAX_UNPACKED:
                    raise ImportError_("Архив слишком большой")
                with zf.open(info) as fin, open(dest / name, "wb") as fout:
                    shutil.copyfileobj(fin, fout)
    else:
        with tarfile.open(src) as tf:
            for member in tf.getmembers():
                name = _safe_name(member.name)
                if not member.isfile() or not name.lower().endswith(KEEP_SUFFIXES):
                    continue
                total += member.size
                if total > MAX_UNPACKED:
                    raise ImportError_("Архив слишком большой")
                with tf.extractfile(member) as fin, open(dest / name, "wb") as fout:
                    shutil.copyfileobj(fin, fout)


def detect_format(directory: Path):
    if stardict.find_ifo(directory):
        return stardict
    if tsv.find_tsv(directory):
        return tsv
    raise ImportError_("Не удалось определить формат словаря (нужен StarDict или TSV)")


def import_dictionary(path, source_lang, target_lang, owner=None, name=None, files=None):
    """Импортирует словарь из файла/архива `path` или набора файлов `files`.

    Возвращает созданный Dictionary.
    """
    with tempfile.TemporaryDirectory(prefix="easyeng-dict-") as tmp:
        tmp = Path(tmp)
        for p in [path] if path else files:
            p = Path(p)
            if p.name.lower().endswith(ARCHIVE_SUFFIXES):
                try:
                    _unpack(p, tmp)
                except (tarfile.TarError, zipfile.BadZipFile, EOFError) as e:
                    raise ImportError_(f"Не удалось распаковать архив: {e}") from e
            else:
                shutil.copy(p, tmp / _safe_name(p.name))
        parser = detect_format(tmp)
        try:
            info, entries = parser.parse(tmp)
            with transaction.atomic():
                dictionary = Dictionary.objects.create(
                    name=(name or info["name"])[:200],
                    source_lang=source_lang,
                    target_lang=target_lang,
                    owner=owner,
                    format=info["format"],
                    description=clean_html(info["description"]),
                )
                count, batch = 0, []
                for headword, html in entries:
                    batch.append(
                        DictionaryEntry(
                            dictionary=dictionary,
                            headword=headword[:255],
                            key=normalize_key(headword),
                            definition=clean_html(WIKILINK_RE.sub(r"\1", html)),
                        )
                    )
                    if len(batch) >= BATCH:
                        DictionaryEntry.objects.bulk_create(batch)
                        count += len(batch)
                        batch = []
                DictionaryEntry.objects.bulk_create(batch)
                count += len(batch)
                if count == 0:
                    raise ImportError_("В словаре не найдено ни одной статьи")
                dictionary.entry_count = count
                dictionary.save(update_fields=["entry_count"])
        except (ValueError, UnicodeError, IndexError) as e:
            raise ImportError_(f"Ошибка разбора словаря: {e}") from e
    return dictionary
