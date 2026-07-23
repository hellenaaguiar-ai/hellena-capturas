"""Escreve falhas como nota visivel no vault, para nunca falhar em silencio."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .state import ItemState

HEADER = "# ⚠️ Erros de captura de voz\n\nGerado automaticamente. Cada item abaixo falhou no pipeline e precisa de atenção.\n"


def write_errors_note(error_note_path: Path, errors: dict[str, ItemState]) -> None:
    if not errors:
        if error_note_path.exists():
            error_note_path.unlink()
        return

    lines = [HEADER]
    for content_hash, item in sorted(errors.items(), key=lambda kv: kv[1].updated_at or ""):
        lines.append(f"## {item.source_filename}")
        lines.append(f"- hash: `{content_hash[:16]}`")
        lines.append(f"- tentativas: {item.attempts}")
        lines.append(f"- última atualização: {item.updated_at}")
        lines.append(f"- erro: {item.error}")
        lines.append(
            f"- reprocessar: `python -m voice_capture.run --reprocess {content_hash[:16]}`"
        )
        lines.append("")

    content = "\n".join(lines)
    error_note_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(error_note_path.parent), prefix=".errnote_", suffix=".md.tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, error_note_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
