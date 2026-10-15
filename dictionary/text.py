import re
import unicodedata

import simplemma

from .languages import LANGUAGE_CODES

APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})
WORD_RE = re.compile(r"^[\w'\-]+(?: [\w'\-]+){0,5}$")


def normalize_key(word):
    """Ключ для поиска в словаре: NFC, нижний регистр, единые апострофы."""
    word = unicodedata.normalize("NFC", word).translate(APOSTROPHES)
    return word.strip().lower()[:255]


def clean_word(raw):
    """Очищает выделенное в тексте слово/фразу от пунктуации по краям."""
    word = unicodedata.normalize("NFC", raw).translate(APOSTROPHES)
    word = re.sub(r"\s+", " ", word).strip(" \t\n.,;:!?\"«»“”()[]{}*_—–-'")
    return word if word and WORD_RE.match(word) else ""


def candidates(word, lang):
    """Варианты для поиска: как есть, затем словарная форма (лемма).

    'running' -> ['running', 'run'], "children's" -> ["children's", 'children', 'child'].
    """
    result = [word]
    base = word
    if lang == "en" and base.lower().endswith("'s"):
        base = base[:-2]
        result.append(base)
    if lang in LANGUAGE_CODES and " " not in base:
        try:
            lemma = simplemma.lemmatize(base.lower(), lang=lang)
        except ValueError:
            lemma = None
        if lemma:
            result.append(lemma)
    seen, unique = set(), []
    for c in result:
        k = normalize_key(c)
        if k not in seen:
            seen.add(k)
            unique.append(c)
    return unique
