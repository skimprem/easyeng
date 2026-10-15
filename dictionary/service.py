"""Поиск перевода: опрашивает словари в порядке из профиля пользователя."""

import hashlib
import logging

from django.core.cache import cache

from .providers.registry import DEFAULT_PROVIDER_ORDER, get_provider
from .text import candidates, normalize_key

log = logging.getLogger(__name__)


def provider_order_for(user):
    if user is not None and user.is_authenticated and hasattr(user, "profile"):
        return user.profile.providers or DEFAULT_PROVIDER_ORDER
    return DEFAULT_PROVIDER_ORDER


def lookup(word, src, tgt, user=None, providers=None):
    """Возвращает {'word', 'results': [LookupResult.to_dict()], 'errors': [...]}.

    Локальный словарь проверяется для всех словоформ (слово, лемма) — это дёшево.
    Онлайн-словари вызываются один раз: для первой формы, давшей результат,
    либо для исходного слова. Ответы онлайн-словарей кэшируются.
    """
    order = providers or provider_order_for(user)
    forms = candidates(word, src)
    results, errors = [], []
    for key in order:
        provider = get_provider(key)
        if provider is None or not provider.is_available() or not provider.supports(src, tgt):
            continue
        try:
            if provider.online:
                found = []
                for form in forms:
                    found = _cached_online(provider, form, src, tgt)
                    if found:
                        break
            else:
                found = []
                for form in forms:
                    found = provider.lookup(form, src, tgt, user=user)
                    if found:
                        break
        except Exception as e:  # сеть, квоты, неожиданный формат ответа
            log.warning("Provider %s failed for %r: %s", key, word, e)
            errors.append({"provider": key, "error": str(e)[:200]})
            continue
        results.extend(r.to_dict() for r in found)
    return {"word": word, "forms": forms, "src": src, "tgt": tgt, "results": results, "errors": errors}


def _cached_online(provider, word, src, tgt):
    raw = f"{provider.key}:{src}:{tgt}:{normalize_key(word)}"
    cache_key = "lookup:" + hashlib.sha1(raw.encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        from .providers.base import LookupResult

        return [LookupResult(**r) for r in cached]
    found = provider.lookup(word, src, tgt)
    cache.set(cache_key, [r.to_dict() for r in found])
    return found
