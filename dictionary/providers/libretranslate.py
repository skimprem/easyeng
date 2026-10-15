import requests
from django.conf import settings

from .base import LookupResult, OnlineProvider


class LibreTranslateProvider(OnlineProvider):
    """LibreTranslate — открытый машинный перевод, можно поднять у себя:
    docker run -p 5000:5000 libretranslate/libretranslate

    Включается переменной окружения LIBRETRANSLATE_URL.
    """

    key = "libretranslate"
    name = "LibreTranslate"
    description = "Открытый self-hosted машинный перевод (нужен свой сервер)."

    def is_available(self):
        return bool(settings.EASYENG_LIBRETRANSLATE_URL)

    def lookup(self, word, src, tgt, user=None):
        payload = {"q": word, "source": src, "target": tgt, "format": "text"}
        if settings.EASYENG_LIBRETRANSLATE_KEY:
            payload["api_key"] = settings.EASYENG_LIBRETRANSLATE_KEY
        url = settings.EASYENG_LIBRETRANSLATE_URL.rstrip("/") + "/translate"
        resp = requests.post(url, json=payload, timeout=settings.EASYENG_HTTP_TIMEOUT)
        resp.raise_for_status()
        text = (resp.json().get("translatedText") or "").strip()
        if not text or text.lower() == word.lower():
            return []
        return [LookupResult(provider=self.key, source=self.name, headword=word, translations=[text])]
