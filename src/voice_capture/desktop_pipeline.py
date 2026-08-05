"""Orquestra uma gravacao de reuniao/aula ou terapia: duas trilhas de audio
ja gravadas -> transcricao de cada uma -> estruturacao por IA conforme o
modo -> Markdown no vault -> estado local.

O modo "ideia" no desktop reaproveita o pipeline mobile (pipeline.py)
diretamente, ja que produz o mesmo tipo de nota - nao passa por aqui.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .config import Config
from .desktop.modes import CaptureMode, NOTE_TYPE_MEETING, NOTE_TYPE_THERAPY
from .desktop_ai import (
    ProcessedMeeting,
    ProcessedTherapy,
    process_meeting_transcript,
    process_therapy_transcript,
)
from .desktop_markdown import DesktopNoteMeta, build_meeting_markdown, build_therapy_markdown
from .hashing import combined_hash
from .markdown_writer import build_filename, write_note_atomic
from .state import ItemState, STATUS_DONE, STATUS_ERROR, STATUS_PROCESSING, STATUS_TRANSCRIBING, StateStore
from .transcribe import TranscriptResult, transcribe_audio

TranscribeFn = Callable[[Path, str, str, str], TranscriptResult]
MeetingProcessFn = Callable[[str, str, str], ProcessedMeeting]
TherapyProcessFn = Callable[[str, str, str], ProcessedTherapy]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def process_desktop_recording(
    mode: CaptureMode,
    mic_path: Path,
    system_path: Optional[Path],
    recorded_at: datetime,
    config: Config,
    state: StateStore,
    transcribe_fn: TranscribeFn = transcribe_audio,
    process_meeting_fn: MeetingProcessFn = process_meeting_transcript,
    process_therapy_fn: TherapyProcessFn = process_therapy_transcript,
) -> str:
    if mode.note_type not in (NOTE_TYPE_MEETING, NOTE_TYPE_THERAPY):
        raise ValueError(f"Modo desktop nao suportado neste pipeline: {mode.key}")

    content_hash = combined_hash([p for p in (mic_path, system_path) if p is not None])
    state_key = f"desktop:{mode.key}:{content_hash}"

    if state.is_done(state_key):
        return "skipped-duplicate"

    existing = state.get(state_key)
    item = existing or ItemState(source_filename=mic_path.name, first_seen_at=_now_iso())
    item.attempts += 1
    item.updated_at = _now_iso()
    state.upsert(state_key, item)
    state.save()

    try:
        item.status = STATUS_TRANSCRIBING
        item.updated_at = _now_iso()
        state.upsert(state_key, item)
        state.save()

        mic_transcript: TranscriptResult = transcribe_fn(
            mic_path, config.whisper_model, config.whisper_language, config.whisper_initial_prompt
        )
        mic_text = mic_transcript.text
        system_text = ""
        if system_path is not None:
            system_transcript = transcribe_fn(
                system_path, config.whisper_model, config.whisper_language, config.whisper_initial_prompt
            )
            system_text = system_transcript.text

        transcript_path = config.transcripts_raw_dir / f"{content_hash}_{mode.key}.txt"
        transcript_path.write_text(
            f"[Você - microfone]\n{mic_text}\n\n[Outros - áudio do sistema]\n{system_text}",
            encoding="utf-8",
        )
        item.transcript_raw_path = str(transcript_path)

        item.status = STATUS_PROCESSING
        item.updated_at = _now_iso()
        state.upsert(state_key, item)
        state.save()

        labeled_text = (
            f"[Você - microfone]\n{mic_text}\n\n"
            f"[Outros participantes - áudio do sistema]\n{system_text}"
        )

        meta = DesktopNoteMeta(
            content_hash=content_hash,
            created_at=datetime.now().astimezone(),
            recorded_at=recorded_at,
            mic_audio_path=str(mic_path),
            system_audio_path=str(system_path) if system_path is not None else None,
            transcription_model=f"faster-whisper-{config.whisper_model}",
            processing_model=config.anthropic_model,
        )

        if mode.note_type == NOTE_TYPE_MEETING:
            processed_meeting = process_meeting_fn(labeled_text, config.anthropic_api_key, config.anthropic_model)
            markdown = build_meeting_markdown(processed_meeting, mic_text, system_text, meta)
            title = processed_meeting.title
        else:
            processed_therapy = process_therapy_fn(labeled_text, config.anthropic_api_key, config.anthropic_model)
            markdown = build_therapy_markdown(processed_therapy, mic_text, system_text, meta)
            title = processed_therapy.title

        filename = build_filename(recorded_at, title)
        final_path = write_note_atomic(mode.vault_dir, filename, markdown)

        item.status = STATUS_DONE
        item.note_path = str(final_path)
        item.error = None
        item.updated_at = _now_iso()
        state.upsert(state_key, item)
        state.save()
        return "done"

    except Exception as exc:  # noqa: BLE001
        item.status = STATUS_ERROR
        item.error = f"{type(exc).__name__}: {exc}"
        item.updated_at = _now_iso()
        state.upsert(state_key, item)
        state.save()
        return "error"
