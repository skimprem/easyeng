import re

import markdown as md

from dictionary.sanitize import clean_html

EXTENSIONS = ["extra", "sane_lists", "smarty"]


def render_markdown(text):
    html = md.markdown(text or "", extensions=EXTENSIONS, output_format="html")
    return clean_html(html)


CHAPTER_RE = re.compile(
    r"^(?:(?:CHAPTER|BOOK|PART|VOLUME|ACT|SCENE|Chapter|Book|Part)\b.{0,60}"  # CHAPTER IV, Part 2. Title
    r"|[IVXLC]{1,8}\.?"                                                        # II.
    r"|[IVXLC]{1,8}\.\s+[^a-z]{1,60})$"                                         # IV. THE TITLE (без строчных)
)


def plain_text_to_markdown(text):
    """Мягко превращает простой текст в Markdown.

    - нормализует переводы строк;
    - экранирует случайную markdown-разметку в начале строк (#, >, 1. и т.п.);
    - строки-заголовки глав ("CHAPTER IV", "II.") превращает в ## заголовки;
    - строки с отступом (стихи, оглавления) сохраняют переносы, а не склеиваются
      и не превращаются в блоки кода.
    Абзацы (разделённые пустой строкой) Markdown склеит сам.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        prev_blank = i == 0 or not lines[i - 1].strip()
        next_blank = i + 1 >= len(lines) or not lines[i + 1].strip()
        if stripped and prev_blank and next_blank and CHAPTER_RE.match(stripped):
            out.append(f"## {stripped}")
            continue
        indented = stripped and line[:1] in " \t"
        line = re.sub(r"^([#>+=|]|\d+\.\s|[-*]\s)", r"\\\1", stripped)
        out.append(line + "  " if indented else line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"
