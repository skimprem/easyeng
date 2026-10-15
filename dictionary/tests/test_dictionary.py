import io
import struct
import tarfile
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dictionary.importers import ImportError_, import_dictionary
from dictionary.models import Dictionary
from dictionary.providers.local import short_translations
from dictionary.service import lookup
from dictionary.text import candidates, clean_word

User = get_user_model()


def make_stardict(directory: Path, entries, sametypesequence="h"):
    idx, data = b"", b""
    for word, definition in sorted(entries):
        raw = definition.encode()
        idx += word.encode() + b"\0" + struct.pack(">II", len(data), len(raw))
        data += raw
    (directory / "test.idx").write_bytes(idx)
    (directory / "test.dict").write_bytes(data)
    (directory / "test.ifo").write_text(
        "StarDict's dict ifo file\nversion=2.4.2\nbookname=Test Dict\n"
        f"wordcount={len(entries)}\nidxfilesize={len(idx)}\nsametypesequence={sametypesequence}\n"
    )


class TextHelpersTests(TestCase):
    def test_clean_word(self):
        self.assertEqual(clean_word("  «Hello!» "), "Hello")
        self.assertEqual(clean_word("don’t"), "don't")
        self.assertEqual(clean_word("<script>"), "")

    def test_candidates_include_lemma(self):
        self.assertIn("go", candidates("went", "en"))
        self.assertEqual(candidates("children's", "en")[:2], ["children's", "children"])


class ImportTests(TestCase):
    def test_stardict_archive_import_and_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            src.mkdir()
            make_stardict(src, [
                ("go", "<div>verb</div><ol><li><div>идти́</div></li><li><div>ходить</div></li></ol>"),
                ("cat", "<div>noun</div><div>кот</div><script>alert(1)</script>"),
            ])
            archive = tmp / "dict.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                for f in src.iterdir():
                    tf.add(f, arcname=f"test/{f.name}")
            d = import_dictionary(archive, "en", "ru")
        self.assertEqual(d.entry_count, 2)
        self.assertEqual(d.name, "Test Dict")
        self.assertNotIn("<script>", d.entries.get(key="cat").definition)

        result = lookup("went", "en", "ru", providers=["local"])
        self.assertEqual(result["results"][0]["headword"], "go")
        self.assertEqual(result["results"][0]["translations"], ["идти", "ходить"])

    def test_tsv_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "my.tsv"
            path.write_text("# comment\napple\tяблоко; яблоня\nbook\tкнига\n", encoding="utf-8")
            d = import_dictionary(path, "en", "ru")
        self.assertEqual(d.entry_count, 2)
        self.assertEqual(lookup("apples", "en", "ru", providers=["local"])["results"][0]["translations"], ["яблоко", "яблоня"])

    def test_archive_path_traversal_is_flattened(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            archive = tmp / "evil.tar"
            with tarfile.open(archive, "w") as tf:
                payload = "word\tслово\n".encode()
                info = tarfile.TarInfo("../../evil.tsv")
                info.size = len(payload)
                tf.addfile(info, io.BytesIO(payload))
            d = import_dictionary(archive, "en", "ru")
            self.assertEqual(d.entry_count, 1)
            self.assertFalse((tmp.parent / "evil.tsv").exists())

    def test_unknown_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.bin"
            path.write_bytes(b"\0\1\2")
            with self.assertRaises(ImportError_):
                import_dictionary(path, "en", "ru")

    def test_short_translations_skip_part_of_speech(self):
        html = "<div>/ɡoʊ/<br><div>noun</div><ol><li>A turn.<div>о́чередь</div></li></ol></div>"
        self.assertEqual(short_translations(html), ["очередь"])


class LookupViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("reader", password="pw-12345-long")
        self.other = User.objects.create_user("other", password="pw-12345-long")
        d = Dictionary.objects.create(name="Mine", source_lang="en", target_lang="ru", owner=self.other, format="tsv")
        d.entries.create(headword="secret", key="secret", definition="<ol><li>тайна</li></ol>")

    def test_requires_login(self):
        resp = self.client.get(reverse("dictionary:lookup"), {"w": "cat"})
        self.assertEqual(resp.status_code, 302)

    def test_private_dictionary_not_visible_to_others(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dictionary:lookup"), {"w": "secret", "src": "en", "tgt": "ru"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([r for r in resp.json()["results"] if r["provider"] == "local"], [])

    def test_online_errors_are_reported_not_raised(self):
        self.client.force_login(self.user)
        with mock.patch("dictionary.providers.mymemory.MyMemoryProvider.lookup", side_effect=OSError("offline")), \
             mock.patch("dictionary.providers.wiktionary.WiktionaryProvider.lookup", return_value=[]):
            resp = self.client.get(reverse("dictionary:lookup"), {"w": "unknownword", "src": "en", "tgt": "ru"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["errors"][0]["provider"], "mymemory")

    def test_bad_input(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("dictionary:lookup"), {"w": "!!!"}).status_code, 400)
        self.assertEqual(self.client.get(reverse("dictionary:lookup"), {"w": "cat", "src": "xx"}).status_code, 400)
