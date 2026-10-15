import re
from html import escape
from pathlib import Path


def find_tsv(directory: Path):
    return next(iter(sorted([*directory.rglob("*.tsv"), *directory.rglob("*.txt")])), None)


def parse(directory: Path):
    path = find_tsv(directory)
    if path is None:
        raise ValueError("Не найден .tsv файл")

    def entries():
        with path.open(encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#") or "\t" not in line:
                    continue
                word, rest = line.split("\t", 1)
                variants = [v.strip() for v in re.split(r"[;|\t]", rest) if v.strip()]
                if word.strip() and variants:
                    items = "".join(f"<li>{escape(v)}</li>" for v in variants)
                    yield word.strip(), f"<ol>{items}</ol>"

    return {"name": path.stem, "description": "", "format": "tsv"}, entries()
