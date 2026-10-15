import re
from html import unescape

from django.db.models import Q

from ..models import Dictionary, DictionaryEntry
from ..text import normalize_key
from .base import LookupResult, Provider

MAX_TRANSLATIONS = 6
LEAF_DIV_RE = re.compile(r"<div>([^<>]{1,80})</div>")
LEAF_LI_RE = re.compile(r"<li>([^<>]{1,80})</li>")
STRESS_RE = re.compile("[̀́]")
# Пометки части речи, которые WikDict кладёт в такие же <div>, как и переводы
POS_WORDS = {
    "noun", "verb", "adjective", "adverb", "pronoun", "preposition", "conjunction", "interjection",
    "determiner", "article", "numeral", "particle", "prefix", "suffix", "phrase", "proper noun",
    "abbreviation", "contraction", "symbol", "letter", "idiom", "proverb",
}


class LocalProvider(Provider):
    key = "local"
    name = "Локальные словари"
    description = "Словари, загруженные из файлов (StarDict, FreeDict, TSV). Работают без интернета."

    def lookup(self, word, src, tgt, user=None):
        owner_q = Q(owner__isnull=True)
        if user is not None and user.is_authenticated:
            owner_q |= Q(owner=user)
        dictionaries = Dictionary.objects.filter(owner_q, source_lang=src, target_lang=tgt, enabled=True)
        entries = (
            DictionaryEntry.objects.filter(dictionary__in=dictionaries, key=normalize_key(word))
            .select_related("dictionary")
            .order_by("-dictionary__owner_id", "id")[:20]  # личные словари — первыми
        )
        # Точное совпадение регистра — выше: "set" раньше, чем "Set" (имя собственное)
        entries = sorted(entries, key=lambda e: e.headword != word)
        # Несколько статей одного словаря (разные части речи) сливаем в один результат
        by_dict = {}
        for e in entries:
            r = by_dict.get(e.dictionary_id)
            if r is None:
                r = by_dict[e.dictionary_id] = LookupResult(
                    provider=self.key, source=e.dictionary.name, headword=e.headword
                )
            r.translations = merge_unique(r.translations, short_translations(e.definition))
            r.html += e.definition
        return list(by_dict.values())


def merge_unique(a, b, limit=MAX_TRANSLATIONS):
    seen = {x.lower() for x in a}
    result = list(a)
    for x in b:
        if x.lower() not in seen and len(result) < limit:
            seen.add(x.lower())
            result.append(x)
    return result


def short_translations(definition_html):
    """Короткие варианты перевода для всплывающей подсказки.

    В статьях FreeDict/WikDict переводы — это «листовые» <div>перевод</div>,
    в TSV-словарях — <li>перевод</li>. Если структуры нет — первая строка текста.
    """
    items = [i for i in LEAF_DIV_RE.findall(definition_html) if i.strip().lower() not in POS_WORDS]
    if not items:
        items = LEAF_LI_RE.findall(definition_html)
    if not items:
        text = unescape(re.sub(r"<[^>]+>", "\n", definition_html))
        items = [ln for ln in text.splitlines() if ln.strip()][:1]
    cleaned = (STRESS_RE.sub("", unescape(i)).strip() for i in items)
    return merge_unique([], [c for c in cleaned if c])
