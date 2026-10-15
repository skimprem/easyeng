import gzip
import struct
from html import escape
from pathlib import Path

TEXT_TYPES = {"m", "l", "t", "y", "k", "w", "r"}
MARKUP_TYPES = {"h", "g", "x"}


def find_ifo(directory: Path):
    return next(iter(sorted(directory.rglob("*.ifo"))), None)


def _read_ifo(path: Path):
    meta = {}
    for line in path.read_text("utf-8", errors="replace").splitlines()[1:]:
        if "=" in line:
            k, v = line.split("=", 1)
            meta[k.strip()] = v.strip()
    return meta


def _companion(ifo: Path, *suffixes):
    stem = ifo.with_suffix("")
    for s in suffixes:
        p = Path(str(stem) + s)
        if p.exists():
            return p
    return None


def _read_maybe_gz(path: Path):
    if path.suffix in (".gz", ".dz"):
        with gzip.open(path, "rb") as f:
            return f.read()
    return path.read_bytes()


def _render(type_char, data: bytes):
    text = data.decode("utf-8", errors="replace")
    if type_char in MARKUP_TYPES:
        return text
    if type_char in TEXT_TYPES:
        return escape(text).replace("\n", "<br>")
    return ""  # бинарные типы (картинки, звук) пропускаем


def _parse_fields(data: bytes, sametypesequence: str):
    parts = []
    if sametypesequence:
        pos = 0
        for i, t in enumerate(sametypesequence):
            last = i == len(sametypesequence) - 1
            if t.isupper():
                if last:
                    chunk, pos = data[pos:], len(data)
                else:
                    (size,) = struct.unpack(">I", data[pos:pos + 4])
                    chunk, pos = data[pos + 4:pos + 4 + size], pos + 4 + size
            elif last:
                chunk, pos = data[pos:], len(data)
            else:
                end = data.index(b"\0", pos)
                chunk, pos = data[pos:end], end + 1
            parts.append(_render(t, chunk))
    else:
        pos = 0
        while pos < len(data):
            t = chr(data[pos])
            pos += 1
            if t.isupper():
                (size,) = struct.unpack(">I", data[pos:pos + 4])
                chunk, pos = data[pos + 4:pos + 4 + size], pos + 4 + size
            else:
                end = data.find(b"\0", pos)
                end = len(data) if end == -1 else end
                chunk, pos = data[pos:end], end + 1
            parts.append(_render(t, chunk))
    return "<br>".join(p for p in parts if p)


def parse(directory: Path):
    ifo = find_ifo(directory)
    if ifo is None:
        raise ValueError("Не найден .ifo файл StarDict")
    meta = _read_ifo(ifo)
    idx_path = _companion(ifo, ".idx", ".idx.gz")
    dict_path = _companion(ifo, ".dict", ".dict.dz")
    if not idx_path or not dict_path:
        raise ValueError("Не найдены .idx или .dict файлы StarDict")
    offset_fmt = ">QI" if meta.get("idxoffsetbits") == "64" else ">II"
    rec = struct.calcsize(offset_fmt)
    idx = _read_maybe_gz(idx_path)
    dic = _read_maybe_gz(dict_path)
    sts = meta.get("sametypesequence", "")

    def entries():
        pos = 0
        while pos < len(idx):
            end = idx.index(b"\0", pos)
            word = idx[pos:end].decode("utf-8", errors="replace")
            offset, size = struct.unpack(offset_fmt, idx[end + 1:end + 1 + rec])
            pos = end + 1 + rec
            html = _parse_fields(dic[offset:offset + size], sts)
            if word and html:
                yield word, html

    info = {
        "name": meta.get("bookname", ifo.stem),
        "description": meta.get("description", ""),
        "format": "stardict",
    }
    return info, entries()
