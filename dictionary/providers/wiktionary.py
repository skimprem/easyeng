from urllib.parse import quote

import requests

from ..sanitize import clean_html
from .base import LookupResult, OnlineProvider


class WiktionaryProvider(OnlineProvider):
    """Толкования из Wiktionary (на языке оригинала) — открытый словарь CC BY-SA.

    Не перевод, а объяснение значения: полезно, когда перевод неоднозначен.
    """

    key = "wiktionary"
    name = "Wiktionary"
    description = "Толковый словарь (определения на языке оригинала)."

    def lookup(self, word, src, tgt, user=None):
        url = f"https://en.wiktionary.org/api/rest_v1/page/definition/{quote(word)}"
        try:
            data = self.get_json(url)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return []
            raise
        sections = data.get(src) or []
        if not sections:
            return []
        parts = []
        for sec in sections[:4]:
            defs = [d.get("definition", "") for d in sec.get("definitions", []) if d.get("definition")]
            if defs:
                items = "".join(f"<li>{d}</li>" for d in defs[:4])
                parts.append(f"<p><em>{sec.get('partOfSpeech', '')}</em></p><ol>{items}</ol>")
        if not parts:
            return []
        return [LookupResult(provider=self.key, source=self.name, headword=word, html=clean_html("".join(parts)))]
