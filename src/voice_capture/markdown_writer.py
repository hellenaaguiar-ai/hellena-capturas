"""Monta o Markdown da captura e escreve no vault de forma atomica."""
from __future__ import annotations

import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .process_ai import POSSIBLE_USES, ProcessedCapture

CONFIDENCE_DISPLAY = {"baixa": "baixa", "media": "média", "alta": "alta"}


def slugify(text: str, max_len: int = 40) -> str:
    """Gera um slug curto para nome de arquivo, sempre cortando em palavra
    inteira (nunca no meio de uma palavra)."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    words = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower().split("-")

    slug = ""
    for word in words:
        if not word:
            continue
        candidate = f"{slug}-{word}" if slug else word
        if len(candidate) > max_len:
            break
        slug = candidate
    return slug or "captura"


def _yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    escaped = ", ".join(f'"{i}"' for i in items)
    return f"[{escaped}]"


def _yaml_str(value: str) -> str:
    escaped = value.replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


@dataclass
class NoteMeta:
    content_hash: str
    created_at: datetime
    recorded_at: datetime
    audio_archive_path: str
    transcription_model: str
    processing_model: str


def build_filename(recorded_at: datetime, title: str) -> str:
    stamp = recorded_at.strftime("%Y-%m-%d %H%M")
    return f"{stamp} - {slugify(title)}.md"


def build_markdown(processed: ProcessedCapture, raw_text: str, meta: NoteMeta) -> str:
    confidence_key = processed.confidence if processed.confidence in CONFIDENCE_DISPLAY else "baixa"
    needs_review = confidence_key == "baixa"

    entities = "\n".join(f"- {e}" for e in processed.entities) or "_Nenhuma identificada._"
    evidence = "\n".join(f"- {e}" for e in processed.evidence_and_connections) or "_Nenhuma._"
    questions = "\n".join(f"- {q}" for q in processed.open_questions) or "_Nenhuma._"
    checklist = "\n".join(
        f"- [{'x' if use in processed.possible_uses else ' '}] {use}" for use in POSSIBLE_USES
    )

    frontmatter = "\n".join(
        [
            "---",
            "type: voice-capture",
            f"id: {meta.content_hash[:16]}",
            f"created_at: {meta.created_at.isoformat()}",
            f"recorded_at: {meta.recorded_at.isoformat()}",
            "source: mobile-voice",
            "processing_status: done",
            f"classification: {processed.classification}",
            f"confidence: {CONFIDENCE_DISPLAY[confidence_key]}",
            f"needs_review: {'true' if needs_review else 'false'}",
            f"related_topics: {_yaml_list(processed.related_topics)}",
            "possible_connections: []",
            f"audio_file: {meta.audio_archive_path}",
            f"transcription_model: {meta.transcription_model}",
            f"processing_model: {meta.processing_model}",
            "---",
        ]
    )

    uncertainty_block = ""
    if processed.uncertainty_notes:
        uncertainty_block = f"\n> ⚠️ {processed.uncertainty_notes}\n"

    body = f"""
# {processed.title}
{uncertainty_block}
## Síntese
{processed.synthesis}

## Transcrição limpa
{processed.cleaned_transcript}

## Possíveis entidades identificadas
{entities}

## Evidências e conexões
{evidence}

## Perguntas abertas
{questions}

## Possíveis usos
{checklist}

## Transcrição bruta
{raw_text}
"""
    return frontmatter + "\n" + body.strip() + "\n"


def write_note_atomic(vault_dir: Path, filename: str, content: str) -> Path:
    vault_dir.mkdir(parents=True, exist_ok=True)
    final_path = vault_dir / filename
    if final_path.exists():
        # Nome colidiu (mesmo minuto + mesmo titulo). Acrescenta sufixo curto
        # em vez de sobrescrever uma nota existente.
        stem, suffix = final_path.stem, final_path.suffix
        i = 2
        while (vault_dir / f"{stem}-{i}{suffix}").exists():
            i += 1
        final_path = vault_dir / f"{stem}-{i}{suffix}"

    fd, tmp_path = tempfile.mkstemp(dir=str(vault_dir), prefix=".note_", suffix=".md.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, final_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return final_path
