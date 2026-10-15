from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccountTests(TestCase):
    def test_signup_creates_profile_and_logs_in(self):
        resp = self.client.post(reverse("accounts:signup"), {
            "username": "newbie", "email": "", "password1": "Very-Secret-42", "password2": "Very-Secret-42",
        })
        self.assertRedirects(resp, reverse("library:list"))
        user = User.objects.get(username="newbie")
        self.assertEqual((user.profile.source_lang, user.profile.target_lang), ("en", "ru"))

    def test_settings_update(self):
        user = User.objects.create_user("u", password="pw-12345-long")
        self.client.force_login(user)
        self.client.post(reverse("accounts:settings"), {"source_lang": "de", "target_lang": "ru", "providers": ["local"], "session_size": 20})
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.source_lang, "de")
        self.assertEqual(user.profile.providers, ["local"])

    def test_provider_order_is_kept(self):
        user = User.objects.create_user("u", password="pw-12345-long")
        self.client.force_login(user)
        self.client.post(reverse("accounts:settings"), {
            "source_lang": "en", "target_lang": "ru", "session_size": 20,
            "providers": ["wiktionary", "local", "mymemory"],
        })
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.providers, ["wiktionary", "local", "mymemory"])
        # На странице настроек словари выводятся в сохранённом порядке
        html = self.client.get(reverse("accounts:settings")).content.decode()
        self.assertLess(html.index('value="wiktionary"'), html.index('value="local"'))

    def test_same_languages_rejected(self):
        user = User.objects.create_user("u", password="pw-12345-long")
        self.client.force_login(user)
        resp = self.client.post(reverse("accounts:settings"), {"source_lang": "en", "target_lang": "en"})
        self.assertEqual(resp.status_code, 200)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.target_lang, "ru")

    def test_pages_render(self):
        user = User.objects.create_user("u", password="pw-12345-long")
        self.client.force_login(user)
        for name in ("library:list", "library:create", "library:upload", "library:gutenberg",
                     "library:inbox", "dictionary:list", "accounts:settings"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
