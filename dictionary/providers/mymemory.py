import re

from django.conf import settings

from .base import LookupResult, OnlineProvider

JUNK_RE = re.compile(r"[\\%{}<>@#=]|\d")


class MyMemoryProvider(OnlineProvider):
    """MyMemory — бесплатная переводческая память, без ключа.

    Лимит ~5000 слов/день на IP (50000 с указанием email).
    https://mymemory.translated.net/doc/spec.php
    """

    key = "mymemory"
    name = "MyMemory"
    description = "Бесплатный онлайн-перевод, без регистрации. Любые пары языков."

    def lookup(self, word, src, tgt, user=None):
        params = {"q": word, "langpair": f"{src}|{tgt}"}
        if settings.EASYENG_MYMEMORY_EMAIL:
            params["de"] = settings.EASYENG_MYMEMORY_EMAIL
        data = self.get_json("https://api.mymemory.translated.net/get", params=params)
        if data.get("responseStatus") != 200:
            return []
        variants = []
        main = (data.get("responseData") or {}).get("translatedText") or ""
        # Альтернативы — только точные совпадения по исходному слову с приличным качеством
        candidates = [main] + [
            m.get("translation", "")
            for m in data.get("matches") or []
            if (m.get("segment") or "").strip().lower() == word.lower()
            and float(m.get("match") or 0) >= 1
            and int(m.get("quality") or 0) >= 70
        ]
        seen = set()
        for c in candidates:
            c = c.strip()
            if c and c.lower() not in seen and c.lower() != word.lower() and len(c) < 80 and not JUNK_RE.search(c):
                seen.add(c.lower())
                variants.append(c)
        if not variants:
            return []
        return [LookupResult(provider=self.key, source=self.name, headword=word, translations=variants[:5])]
