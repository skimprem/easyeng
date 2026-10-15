"""Каталог открытых словарей FreeDict (https://freedict.org)."""

import tempfile
from pathlib import Path

import requests
from django.core.cache import cache

from .importers import import_dictionary
from .languages import ISO3_TO_ISO1

CATALOG_URL = "https://freedict.org/freedict-database.json"


def catalog():
    """Список словарей FreeDict, доступных в формате StarDict, для наших языков."""
    data = cache.get("freedict:catalog")
    if data is None:
        resp = requests.get(CATALOG_URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        cache.set("freedict:catalog", data, 60 * 60 * 24)
    result = []
    for entry in data:
        name = entry.get("name", "")
        if "-" not in name:
            continue
        src3, tgt3 = name.split("-", 1)
        src, tgt = ISO3_TO_ISO1.get(src3), ISO3_TO_ISO1.get(tgt3)
        release = next((r for r in entry.get("releases", []) if r.get("platform") == "stardict"), None)
        if src and tgt and release:
            result.append(
                {
                    "name": name,
                    "src": src,
                    "tgt": tgt,
                    "headwords": int(entry.get("headwords") or 0),
                    "version": release.get("version", ""),
                    "url": release["URL"],
                    "size": int(release.get("size") or 0),
                }
            )
    return sorted(result, key=lambda e: e["name"])


def install(name, owner=None):
    item = next((e for e in catalog() if e["name"] == name), None)
    if item is None:
        raise ValueError(f"Словарь {name} не найден в каталоге FreeDict")
    with tempfile.TemporaryDirectory(prefix="easyeng-freedict-") as tmp:
        archive = Path(tmp) / Path(item["url"]).name
        with requests.get(item["url"], stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with archive.open("wb") as f:
                for chunk in resp.iter_content(1 << 20):
                    f.write(chunk)
        return import_dictionary(
            archive, item["src"], item["tgt"], owner=owner, name=f"FreeDict {name} {item['version']}"
        )
