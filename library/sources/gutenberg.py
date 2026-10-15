"""Project Gutenberg — 70 000+ книг в общественном достоянии.

Поиск — через открытый API Gutendex (https://gutendex.com), он бывает медленным,
поэтому результаты кэшируются. Скачивание книги от Gutendex не зависит:
текст берётся напрямую с gutenberg.org, метаданные — из шапки файла.
"""

import hashlib
import re

import requests
from django.core.cache import cache

from ..markdown import plain_text_to_markdown

API = "https://gutendex.com/books/"
TXT_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
BOOK_URL = "https://www.gutenberg.org/ebooks/{id}"
HEADERS = {"User-Agent": "EasyEng/0.1 (personal reading app)"}

START_RE = re.compile(r"^\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*$", re.M | re.I)
END_RE = re.compile(r"^\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*$", re.M | re.I)
ID_RE = re.compile(r"^(?:https?://(?:www\.)?gutenberg\.org/(?:ebooks|cache/epub|files)/)?(\d{1,6})(?:[/.].*)?$")
LANGS = {"english": "en", "russian": "ru", "german": "de", "french": "fr", "spanish": "es", "italian": "it",
         "portuguese": "pt", "dutch": "nl", "polish": "pl", "ukrainian": "uk", "czech": "cs", "swedish": "sv",
         "finnish": "fi", "turkish": "tr", "greek": "el"}


def parse_book_id(value):
    """'1661', 'https://www.gutenberg.org/ebooks/1661' -> 1661, иначе None."""
    m = ID_RE.match((value or "").strip())
    return int(m.group(1)) if m else None


def search(query, language=None, page=1):
    params = {"search": query, "page": page}
    if language:
        params["languages"] = language
    key = "gutendex:" + hashlib.sha1(repr(sorted(params.items())).encode()).hexdigest()
    result = cache.get(key)
    if result is None:
        resp = requests.get(API, params=params, headers=HEADERS, timeout=(5, 25))
        resp.raise_for_status()
        data = resp.json()
        books = [
            {
                "id": item["id"],
                "title": item.get("title", ""),
                "authors": ", ".join(a.get("name", "") for a in item.get("authors", [])),
                "languages": item.get("languages", []),
                "downloads": item.get("download_count", 0),
            }
            for item in data.get("results", [])
            if any(m.startswith("text/plain") for m in item.get("formats", {}))
        ]
        result = {"count": data.get("count", 0), "has_next": bool(data.get("next")), "books": books}
        cache.set(key, result, 60 * 60 * 24)
    return result


def fetch(book_id):
    """Скачивает книгу. Возвращает поля для модели Text."""
    book_id = int(book_id)
    resp = requests.get(TXT_URL.format(id=book_id), headers=HEADERS, timeout=(5, 60))
    if resp.status_code == 404:
        raise ValueError(f"Книга №{book_id} не найдена или у неё нет текстовой версии")
    resp.raise_for_status()
    resp.encoding = "utf-8"
    raw = resp.text
    meta = parse_header(raw)
    return {
        "title": (meta.get("title") or f"Gutenberg #{book_id}")[:300],
        "author": meta.get("author", "")[:300],
        "language": LANGS.get(meta.get("language", "").lower(), "en"),
        "content": plain_text_to_markdown(strip_boilerplate(raw)),
        "source_url": BOOK_URL.format(id=book_id),
    }


def parse_header(text):
    head = text[: (START_RE.search(text) or re.search(r"$", text)).start()][:20000]
    meta = {}
    for field in ("Title", "Author", "Language"):
        # Значение может продолжаться на следующих строках с отступом
        m = re.search(rf"^{field}:[ \t]*(.+(?:\n[ \t]+.+)*)", head, re.M)
        if m:
            meta[field.lower()] = re.sub(r"\s+", " ", m.group(1)).strip()
    return meta


def strip_boilerplate(text):
    """Убирает лицензионные шапку и подвал Project Gutenberg."""
    start = START_RE.search(text)
    if start:
        text = text[start.end():]
    end = END_RE.search(text)
    if end:
        text = text[:end.start()]
    return text.strip()
