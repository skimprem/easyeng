"""Импорт локальных словарей.

Поддерживаемые форматы:
  * StarDict (.ifo + .idx[.gz] + .dict[.dz]) — формат FreeDict, большинство открытых словарей;
  * TSV (слово<TAB>перевод1; перевод2) — простой формат для своих словарей.

Можно загружать архивы (.zip, .tar.gz, .tar.xz, .tar.bz2) с этими файлами.
Новый формат = модуль с функцией parse(path) -> (meta, iter[(headword, html)])
и строка в detect_format().
"""

from .loader import import_dictionary, ImportError_  # noqa: F401
