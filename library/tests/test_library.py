import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from library.markdown import plain_text_to_markdown, render_markdown
from library.models import Share, Text
from library.sources.gutenberg import parse_book_id, parse_header, strip_boilerplate

User = get_user_model()


class MarkdownTests(TestCase):
    def test_render_is_sanitized(self):
        html = render_markdown("Hi <script>alert(1)</script> [x](javascript:alert(1)) **bold**")
        self.assertNotIn("<script", html)
        self.assertNotIn("javascript:", html)
        self.assertIn("<strong>bold</strong>", html)

    def test_plain_text_conversion(self):
        md = plain_text_to_markdown("CHAPTER I\n\n# not a heading\n    indented line\n\nI took the paper.\n")
        self.assertIn("## CHAPTER I", md)
        self.assertIn("\\# not a heading", md)
        self.assertNotIn("## I took", md)
        self.assertNotIn("<pre>", render_markdown(md))


class GutenbergParsingTests(TestCase):
    def test_parse_book_id(self):
        self.assertEqual(parse_book_id("1661"), 1661)
        self.assertEqual(parse_book_id("https://www.gutenberg.org/ebooks/1661"), 1661)
        self.assertIsNone(parse_book_id("https://evil.example/1661"))

    def test_header_and_boilerplate(self):
        raw = ("Title: Some Book\nAuthor: Jane Doe\nLanguage: English\n"
               "*** START OF THE PROJECT GUTENBERG EBOOK X ***\nBody.\n*** END OF THE PROJECT GUTENBERG EBOOK X ***\nLicense")
        self.assertEqual(parse_header(raw), {"title": "Some Book", "author": "Jane Doe", "language": "English"})
        self.assertEqual(strip_boilerplate(raw), "Body.")


class LibraryViewTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw-12345-long")
        self.bob = User.objects.create_user("bob", password="pw-12345-long")
        self.text = Text.objects.create(owner=self.alice, title="Story", content="Once upon a *time*.")

    def test_content_html_rendered_on_save(self):
        self.assertIn("<em>time</em>", self.text.content_html)

    def test_other_user_cannot_read_or_edit(self):
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(reverse("library:read", args=[self.text.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("library:delete", args=[self.text.pk])).status_code, 404)

    def test_read_and_progress(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("library:read", args=[self.text.pk]))
        self.assertContains(resp, "<em>time</em>", html=False)
        resp = self.client.post(reverse("library:progress", args=[self.text.pk]), json.dumps({"progress": 0.5}),
                                content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.text.refresh_from_db()
        self.assertEqual(self.text.progress, 0.5)

    def test_upload_txt(self):
        self.client.force_login(self.alice)
        f = SimpleUploadedFile("tale.txt", "CHAPTER I\n\nHello world.\n".encode())
        resp = self.client.post(reverse("library:upload"), {"file": f, "language": "en"})
        text = Text.objects.get(title="tale")
        self.assertRedirects(resp, reverse("library:read", args=[text.pk]))
        self.assertIn("<h2>CHAPTER I</h2>", text.content_html)

    def test_upload_rejects_other_extensions(self):
        self.client.force_login(self.alice)
        f = SimpleUploadedFile("x.exe", b"MZ")
        resp = self.client.post(reverse("library:upload"), {"file": f, "language": "en"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Text.objects.filter(title="x").exists())

    def test_share_flow(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("library:share", args=[self.text.pk]), {"recipient": "Bob", "message": "Read it"})
        share = Share.objects.get()
        self.assertEqual(share.recipient, self.bob)

        self.client.force_login(self.bob)
        self.assertContains(self.client.get(reverse("library:inbox")), "Story")
        self.client.post(reverse("library:share_respond", args=[share.pk]), {"action": "accept"})
        copy = Text.objects.get(owner=self.bob)
        self.assertEqual(copy.content, self.text.content)
        self.assertEqual(copy.source, "shared")
        # Повторно принять нельзя
        resp = self.client.post(reverse("library:share_respond", args=[share.pk]), {"action": "accept"})
        self.assertEqual(resp.status_code, 404)

    def test_cannot_share_to_self_or_unknown(self):
        self.client.force_login(self.alice)
        for name in ("alice", "nobody"):
            self.client.post(reverse("library:share", args=[self.text.pk]), {"recipient": name})
        self.assertFalse(Share.objects.exists())

    def test_preview(self):
        self.client.force_login(self.alice)
        resp = self.client.post(reverse("library:preview"), {"content": "# Title"})
        self.assertContains(resp, "<h1>Title</h1>", html=True)


class GlossesTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw-12345-long")
        self.bob = User.objects.create_user("bob", password="pw-12345-long")
        self.text = Text.objects.create(owner=self.alice, title="Story", content="Once upon a time.")
        self.url = reverse("library:glosses", args=[self.text.pk])

    def post(self, glosses):
        return self.client.post(self.url, json.dumps({"glosses": glosses}), content_type="application/json")

    def test_save_and_render(self):
        self.client.force_login(self.alice)
        resp = self.post([{"o": 12, "w": "time", "t": "время"}, {"o": 0, "w": "Once", "t": "однажды"}])
        self.assertEqual(resp.json()["count"], 2)
        self.text.refresh_from_db()
        self.assertEqual([g["w"] for g in self.text.glosses], ["Once", "time"])  # отсортированы по смещению
        page = self.client.get(reverse("library:read", args=[self.text.pk]))
        self.assertContains(page, 'id="glosses-data"')
        self.assertContains(page, "\\u0432\\u0440\\u0435\\u043c\\u044f")  # «время» в json_script

    def test_reset_with_empty_list(self):
        self.text.glosses = [{"o": 0, "w": "Once", "t": "однажды"}]
        self.text.save()
        self.client.force_login(self.alice)
        self.post([])
        self.text.refresh_from_db()
        self.assertEqual(self.text.glosses, [])

    def test_invalid_payload_rejected(self):
        self.client.force_login(self.alice)
        for bad in ("nope", [{"o": -1, "w": "a", "t": "b"}], [{"o": 1, "w": 5, "t": "b"}], ["x"]):
            self.assertEqual(self.post(bad).status_code, 400, bad)

    def test_other_user_cannot_save(self):
        self.client.force_login(self.bob)
        self.assertEqual(self.post([]).status_code, 404)

    def test_glosses_not_copied_when_shared(self):
        self.text.glosses = [{"o": 0, "w": "Once", "t": "однажды"}]
        self.text.save()
        self.assertEqual(self.text.copy_for(self.bob).glosses, [])
