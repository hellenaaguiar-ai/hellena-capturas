"""Acrescenta falas espontaneas a notas de livro sem inventar conteudo."""
from __future__ import annotations

import os
import re
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path


class AmbiguousBookNoteError(RuntimeError):
    """Mais de uma nota existente pode representar o mesmo livro."""


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^\w\s]", " ", value.lower()).split())


def _declared_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', text, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def find_book_note(books_dir: Path, title: str) -> Path | None:
    wanted = _normalized(title)
    matches = []
    for path in books_dir.rglob("*.md") if books_dir.exists() else []:
        filename_title = re.split(r"\s+-\s+", path.stem, maxsplit=1)[0]
        if wanted in {_normalized(_declared_title(path)), _normalized(filename_title)}:
            matches.append(path)
    if len(matches) > 1:
        raise AmbiguousBookNoteError(f"Mais de uma nota corresponde ao livro {title!r}")
    return matches[0] if matches else None


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".book_", suffix=".md.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def append_spoken_capture(books_dir: Path, title: str, raw_text: str, recorded_at: datetime) -> Path:
    """Anexa a fala literal a uma nota existente ou cria uma nota minima."""
    note = find_book_note(books_dir, title)
    heading = recorded_at.strftime("%d/%m/%Y %H:%M")
    entry = f"### Fala gravada em {heading}\n\n{raw_text.strip()}\n"

    if note is None:
        safe_title = re.sub(r'[<>:"/\\|?*]', " ", title).strip().rstrip(".") or "Livro"
        note = books_dir / f"{safe_title}.md"
        created = recorded_at.strftime("%Y-%m-%d %H:%M")
        escaped_title = title.replace('"', '\\"')
        content = (
            "---\n"
            "type: book\n"
            f'title: "{escaped_title}"\n'
            f"Data de criação: {created}\n"
            "tags:\n  - livro\n"
            "---\n\n"
            f"# {title}\n\n## Insights\n\n{entry}"
        )
    else:
        content = note.read_text(encoding="utf-8").rstrip() + "\n"
        placeholder = "_Ainda não há reflexões gravadas._"
        if placeholder in content:
            content = content.replace(placeholder, entry.rstrip(), 1) + "\n"
        elif re.search(r"^## Insights\s*$", content, re.MULTILINE):
            content += "\n" + entry
        else:
            content += "\n## Insights\n\n" + entry

    _write_atomic(note, content)
    return note
