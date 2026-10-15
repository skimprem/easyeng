"""Поддерживаемые языки (ISO 639-1).

Список намеренно ограничен языками, для которых simplemma умеет
лемматизацию — так поиск по словарю работает и для словоформ.
Добавить язык = добавить строку сюда.
"""

LANGUAGES = [
    ("en", "English"),
    ("ru", "Русский"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("es", "Español"),
    ("it", "Italiano"),
    ("pt", "Português"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("uk", "Українська"),
    ("cs", "Čeština"),
    ("sv", "Svenska"),
    ("fi", "Suomi"),
    ("tr", "Türkçe"),
    ("el", "Ελληνικά"),
]

LANGUAGE_CODES = {code for code, _ in LANGUAGES}

# Коды FreeDict (ISO 639-3) -> ISO 639-1
ISO3_TO_ISO1 = {
    "eng": "en", "rus": "ru", "deu": "de", "fra": "fr", "spa": "es",
    "ita": "it", "por": "pt", "nld": "nl", "pol": "pl", "ukr": "uk",
    "ces": "cs", "swe": "sv", "fin": "fi", "tur": "tr", "ell": "el",
}
ISO1_TO_ISO3 = {v: k for k, v in ISO3_TO_ISO1.items()}


def language_name(code):
    return dict(LANGUAGES).get(code, code)
