import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from library.models import Text
from vocab.models import INTERVALS, MAX_BOX, Card
from vocab.services import build_session, stats

User = get_user_model()


class SchedulingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="pw-12345-long")
        self.card = Card.objects.create(user=self.user, word="reluctant", translation="неохотный")

    def test_right_moves_to_next_box_with_growing_interval(self):
        now = timezone.now()
        for box in range(1, MAX_BOX + 1):
            self.card.answer(True, now=now)
            self.assertEqual(self.card.box, box)
            self.assertEqual(self.card.due, now + timedelta(days=INTERVALS[box]))
        # Выученное слово всё равно возвращается — через самый длинный интервал
        self.card.answer(True, now=now)
        self.assertEqual(self.card.box, MAX_BOX)
        self.assertEqual(self.card.due, now + timedelta(days=INTERVALS[-1]))

    def test_wrong_sends_back_to_learning(self):
        now = timezone.now()
        self.card.box = 3
        self.card.answer(False, now=now)
        self.assertEqual((self.card.box, self.card.due, self.card.lapses), (0, now, 1))

    def test_early_check_right_keeps_schedule_wrong_resets(self):
        due = timezone.now() + timedelta(days=10)
        self.card.box, self.card.due = 4, due
        self.card.answer(True, early=True)
        self.assertEqual((self.card.box, self.card.due), (4, due))
        self.card.answer(False, early=True)
        self.assertEqual(self.card.box, 0)

    def test_session_contains_due_learning_first_and_random_checks(self):
        now = timezone.now()
        self.card.box, self.card.due = 2, now - timedelta(hours=1)
        self.card.save()
        Card.objects.create(user=self.user, word="new", translation="новый")  # box 0, due now
        later = Card.objects.create(user=self.user, word="known", translation="известный", box=3,
                                    due=now + timedelta(days=5))
        session = build_session(self.user, limit=10)
        due = [c.word for c, early in session if not early]
        checks = [c for c, early in session if early]
        self.assertEqual(due, ["new", "reluctant"])
        self.assertEqual(checks, [later])  # один внеплановый «экзамен» на знакомое слово

    def test_stats(self):
        Card.objects.create(user=self.user, word="a", translation="а", box=MAX_BOX, due=timezone.now() + timedelta(days=9))
        s = stats(self.user)
        self.assertEqual((s["total"], s["learning"], s["mastered"], s["due"]), (2, 1, 1, 1))


class VocabApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="pw-12345-long")
        self.other = User.objects.create_user("o", password="pw-12345-long")
        self.client.force_login(self.user)
        self.text = Text.objects.create(owner=self.user, title="T", content="He went home.")

    def add(self, **kw):
        data = {"word": "go", "form": "went", "translation": "идти", "src": "en", "tgt": "ru",
                "context": "He went home.", "text_id": self.text.pk}
        data.update(kw)
        return self.client.post(reverse("vocab:add"), json.dumps(data), content_type="application/json")

    def test_add_from_reader_and_dedupe(self):
        self.assertTrue(self.add().json()["created"])
        resp = self.add(word="Go", translation="ходить").json()
        self.assertFalse(resp["created"])
        card = Card.objects.get()
        self.assertEqual(card.translation, "идти; ходить")
        self.assertEqual((card.form, card.text, card.context), ("went", self.text, "He went home."))

    def test_add_validation(self):
        self.assertEqual(self.add(word="").status_code, 400)
        self.assertEqual(self.add(src="xx").status_code, 400)

    def test_foreign_text_not_linked(self):
        foreign = Text.objects.create(owner=self.other, title="X")
        self.add(text_id=foreign.pk)
        self.assertIsNone(Card.objects.get().text)

    def test_lookup_reports_vocab_card(self):
        self.add()
        resp = self.client.get(reverse("dictionary:lookup"), {"w": "went", "src": "en", "tgt": "ru"})
        self.assertEqual(resp.json()["vocab"]["word"], "go")

    def test_answer_and_ownership(self):
        self.add()
        card = Card.objects.get()
        url = reverse("vocab:answer", args=[card.pk])
        resp = self.client.post(url, json.dumps({"correct": True}), content_type="application/json")
        self.assertEqual(resp.json()["box"], 1)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url, "{}", content_type="application/json").status_code, 404)

    def test_pages(self):
        self.add()
        card = Card.objects.get()
        for url in (reverse("vocab:list"), reverse("vocab:list") + "?status=learning&q=go",
                    reverse("vocab:review"), reverse("vocab:review") + "?mode=practice",
                    reverse("vocab:edit", args=[card.pk])):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertContains(self.client.get(reverse("vocab:review")), '"word": "go"')

    def test_manual_create_and_duplicate(self):
        data = {"word": "apple", "translation": "яблоко", "context": "", "src_lang": "en", "tgt_lang": "ru"}
        self.client.post(reverse("vocab:create"), data)
        self.client.post(reverse("vocab:create"), data)
        self.assertEqual(Card.objects.filter(word="apple").count(), 1)

    def test_delete_and_relearn(self):
        self.add()
        card = Card.objects.get()
        card.box = 3
        card.save()
        self.client.post(reverse("vocab:relearn", args=[card.pk]))
        card.refresh_from_db()
        self.assertEqual(card.box, 0)
        self.client.post(reverse("vocab:delete", args=[card.pk]))
        self.assertFalse(Card.objects.exists())
