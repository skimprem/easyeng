from dataclasses import asdict, dataclass, field

import requests
from django.conf import settings


@dataclass
class LookupResult:
    provider: str          # ключ провайдера
    source: str            # человекочитаемое имя источника
    headword: str          # найденная словарная форма
    translations: list[str] = field(default_factory=list)  # короткие варианты перевода
    html: str = ""         # подробная статья (санитизированный HTML)

    def to_dict(self):
        return asdict(self)


class Provider:
    """Базовый класс словаря.

    Чтобы подключить новый словарь: унаследоваться, задать key/name,
    реализовать lookup() и зарегистрировать класс в registry.py.
    """

    key = ""
    name = ""
    online = False
    description = ""

    def is_available(self):
        return True

    def supports(self, src, tgt):
        return True

    def lookup(self, word, src, tgt, user=None) -> list[LookupResult]:
        raise NotImplementedError


class OnlineProvider(Provider):
    online = True

    def get_json(self, url, **kwargs):
        kwargs.setdefault("timeout", settings.EASYENG_HTTP_TIMEOUT)
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", "EasyEng/0.1 (personal reading app)")
        resp = requests.get(url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
