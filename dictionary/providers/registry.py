"""Реестр словарей. Новый провайдер — добавить класс в PROVIDER_CLASSES."""

from .libretranslate import LibreTranslateProvider
from .local import LocalProvider
from .mymemory import MyMemoryProvider
from .wiktionary import WiktionaryProvider

PROVIDER_CLASSES = [LocalProvider, MyMemoryProvider, WiktionaryProvider, LibreTranslateProvider]

PROVIDERS = {cls.key: cls() for cls in PROVIDER_CLASSES}

DEFAULT_PROVIDER_ORDER = ["local", "mymemory", "wiktionary"]


def get_provider(key):
    return PROVIDERS.get(key)


def available_providers():
    return [p for p in PROVIDERS.values() if p.is_available()]
