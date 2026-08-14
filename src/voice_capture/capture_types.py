"""Identifica a intencao da captura mobile pelo prefixo do arquivo."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

CAPTURE_IDEA = "idea"
CAPTURE_REFLECTION = "reflection"
CAPTURE_BOOK = "book"


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", ascii_text.upper()).strip()


def detect_capture_type(path: Path) -> str:
    """Aceita variacoes de acento/separador; arquivos legados continuam ideias."""
    prefix = _normalized(path.stem).split(" 202", 1)[0]
    if prefix.startswith(("LIVRO", "INSIGHT DE LIVRO", "INSIGHT LIVRO", "INSIGHTS DE LIVRO", "CAPTURA DE LIVRO")):
        return CAPTURE_BOOK
    if prefix.startswith(("REFLEXAO", "CAPTURA DE REFLEXAO", "PENSAMENTO", "CAPTURA DE PENSAMENTO", "PENSAMENTOS E REFLEXOES")):
        return CAPTURE_REFLECTION
    return CAPTURE_IDEA
