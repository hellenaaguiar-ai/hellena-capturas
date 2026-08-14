"""Orquestra uma gravacao do inicio ao fim: hash -> arquivo -> transcricao ->
processamento por IA -> markdown no vault -> estado local.

Cada etapa grava seu resultado intermediario em disco antes de seguir para a
proxima, para que uma falha no meio nao perca o trabalho ja feito.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .book_notes import AmbiguousBookNoteError, append_spoken_capture
from .capture_types import CAPTURE_REFLECTION, detect_capture_type
from .config import Config
from .desktop_ai import ProcessedReflection, process_reflection_transcript
from .desktop_markdown import DesktopNoteMeta, build_reflection_markdown
from .hashing import sha256_file
from .markdown_writer import NoteMeta, build_filename, build_markdown, write_note_atomic
from .process_ai import ProcessedCapture, process_transcript
from .state import ItemState, STATUS_DONE, STATUS_ERROR, STATUS_PROCESSING, STATUS_TRANSCRIBING, StateStore
from .transcribe import TranscriptResult, transcribe_audio

TranscribeFn = Callable[[Path, str, str, str], TranscriptResult]
ProcessFn = Callable[[str, str, str], ProcessedCapture]
ReflectionProcessFn = Callable[[str, str, str], ProcessedReflection]

_RECORDED_AT_RE = re.compile(r"(\d{4}-\d{2}-\d{2}) (\d{2})-(\d{2})-(\d{2})")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def parse_recorded_at(path: Path) -> datetime:
    """Tenta extrair a data/hora do nome do arquivo (padrao do Atalho iOS);
    cai para o horario de modificacao do arquivo se nao encontrar."""
    match = _RECORDED_AT_RE.search(path.stem)
    if match:
        date_part, hh, mm, ss = match.groups()
        try:
            return datetime.fromisoformat(f"{date_part}T{hh}:{mm}:{ss}").astimezone()
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone()


def process_item(
    audio_path: Path,
    config: Config,
    state: StateStore,
    transcribe_fn: TranscribeFn = transcribe_audio,
    process_fn: ProcessFn = process_transcript,
    reflection_process_fn: ReflectionProcessFn = process_reflection_transcript,
) -> str:
    content_hash = sha256_file(audio_path)

    if state.is_done(content_hash):
        return "skipped-duplicate"

    existing = state.get(content_hash)
    item = existing or ItemState(
        source_filename=audio_path.name,
        first_seen_at=_now_iso(),
    )
    item.source_filename = audio_path.name
    item.attempts += 1
    item.updated_at = _now_iso()
    state.upsert(content_hash, item)
    state.save()

    recorded_at = parse_recorded_at(audio_path)

    try:
        archive_path = config.audio_archive_dir / f"{content_hash}{audio_path.suffix}"
        if not archive_path.exists():
            shutil.copy2(audio_path, archive_path)
        item.audio_archive_path = str(archive_path)

        item.status = STATUS_TRANSCRIBING
        item.updated_at = _now_iso()
        state.upsert(content_hash, item)
        state.save()

        transcript_path = config.transcripts_raw_dir / f"{content_hash}.txt"
        if transcript_path.exists() and transcript_path.stat().st_size > 0:
            transcript_text = transcript_path.read_text(encoding="utf-8")
        else:
            transcript = transcribe_fn(
                archive_path, config.whisper_model, config.whisper_language, config.whisper_initial_prompt
            )
            transcript_text = transcript.text
            transcript_path.write_text(transcript_text, encoding="utf-8")
        item.transcript_raw_path = str(transcript_path)

        item.status = STATUS_PROCESSING
        item.updated_at = _now_iso()
        state.upsert(content_hash, item)
        state.save()

        capture_type = detect_capture_type(audio_path)
        if capture_type == CAPTURE_REFLECTION:
            processed_reflection = reflection_process_fn(
                transcript_text, config.anthropic_api_key, config.anthropic_model
            )
            reflection_meta = DesktopNoteMeta(
                content_hash=content_hash,
                created_at=datetime.now().astimezone(),
                recorded_at=recorded_at,
                mic_audio_path=str(archive_path),
                system_audio_path=None,
                transcription_model=f"faster-whisper-{config.whisper_model}",
                processing_model=config.anthropic_model,
                source="mobile-voice",
            )
            markdown = build_reflection_markdown(
                processed_reflection, transcript_text, reflection_meta
            )
            filename = build_filename(recorded_at, processed_reflection.title)
            final_path = write_note_atomic(config.vault_reflection_dir, filename, markdown)
        else:
            processed = process_fn(
                transcript_text, config.anthropic_api_key, config.anthropic_model
            )

            meta = NoteMeta(
                content_hash=content_hash,
                created_at=datetime.now().astimezone(),
                recorded_at=recorded_at,
                audio_archive_path=str(archive_path),
                transcription_model=f"faster-whisper-{config.whisper_model}",
                processing_model=config.anthropic_model,
            )
            route_to_book = bool(
                processed.book_title and processed.book_title_confidence == "alta"
            )
            if route_to_book:
                try:
                    final_path = append_spoken_capture(
                        config.resolved_vault_books_dir,
                        processed.book_title,
                        transcript_text,
                        recorded_at,
                    )
                except AmbiguousBookNoteError:
                    route_to_book = False

            if not route_to_book:
                markdown = build_markdown(processed, transcript_text, meta)
                filename = build_filename(recorded_at, processed.title)
                final_path = write_note_atomic(config.vault_inbox_dir, filename, markdown)

        item.status = STATUS_DONE
        item.note_path = str(final_path)
        item.error = None
        item.updated_at = _now_iso()
        state.upsert(content_hash, item)
        state.save()
        return "done"

    except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha e registrar
        item.status = STATUS_ERROR
        item.error = f"{type(exc).__name__}: {exc}"
        item.updated_at = _now_iso()
        state.upsert(content_hash, item)
        state.save()
        return "error"
