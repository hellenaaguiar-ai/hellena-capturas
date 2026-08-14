"""Pipeline das reuniões gravadas no iPhone e recebidas pela pasta Reuniões."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from .cloud_transcribe import DiarizedTranscript, SpeakerSegment, save_diarized_transcript, transcribe_meeting_cloud
from .config import Config
from .desktop_ai import ProcessedMeeting, process_meeting_transcript
from .desktop_markdown import DesktopNoteMeta, build_mobile_meeting_markdown
from .hashing import sha256_file
from .markdown_writer import build_filename, write_note_atomic
from .pipeline import MAX_AUTOMATIC_ATTEMPTS, _now_iso
from .state import ItemState, STATUS_DONE, STATUS_ERROR, STATUS_PROCESSING, STATUS_TRANSCRIBING, StateStore

CloudFn = Callable[..., DiarizedTranscript]
ProcessFn = Callable[[str, str, str], ProcessedMeeting]
_MOBILE_DATE_RE = re.compile(r"(\d{2})_(\d{2})_(\d{4}),\s*(\d{2})_(\d{2})")


def parse_mobile_meeting_date(path: Path) -> datetime:
    match = _MOBILE_DATE_RE.search(path.stem)
    if match:
        day, month, year, hour, minute = map(int, match.groups())
        try:
            return datetime(year, month, day, hour, minute).astimezone()
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone()


def _load_cached(json_path: Path, text_path: Path) -> DiarizedTranscript:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    segments = [
        SpeakerSegment(str(s.get("speaker", "Falante")), float(s.get("start", 0)), float(s.get("end", 0)), str(s.get("text", "")))
        for s in payload.get("segments", [])
        if str(s.get("text", "")).strip()
    ]
    return DiarizedTranscript(str(payload.get("text", "")), segments, payload)


def process_mobile_meeting(
    audio_path: Path,
    config: Config,
    state: StateStore,
    cloud_fn: CloudFn = transcribe_meeting_cloud,
    process_fn: ProcessFn = process_meeting_transcript,
    force: bool = False,
) -> str:
    content_hash = sha256_file(audio_path)
    if state.is_done(content_hash):
        return "skipped-duplicate"
    existing = state.get(content_hash)
    if existing and existing.status == STATUS_ERROR and existing.attempts >= MAX_AUTOMATIC_ATTEMPTS and not force:
        return "skipped-error-limit"

    item = existing or ItemState(source_filename=audio_path.name, first_seen_at=_now_iso())
    item.source_filename = audio_path.name
    item.attempts += 1
    item.updated_at = _now_iso()
    state.upsert(content_hash, item)
    state.save()

    try:
        archive_path = config.audio_archive_dir / f"{content_hash}{audio_path.suffix}"
        if not archive_path.exists():
            shutil.copy2(audio_path, archive_path)
        item.audio_archive_path = str(archive_path)
        item.status = STATUS_TRANSCRIBING
        state.upsert(content_hash, item)
        state.save()

        json_path = config.transcripts_raw_dir / f"{content_hash}.diarized.json"
        text_path = config.transcripts_raw_dir / f"{content_hash}.txt"
        if json_path.exists() and text_path.exists():
            transcript = _load_cached(json_path, text_path)
        else:
            transcript = cloud_fn(
                archive_path,
                api_key=config.openai_api_key,
                model=config.meeting_transcription_model,
                language=config.whisper_language,
                speaker_reference_path=config.speaker_reference_path,
                known_speaker_name=config.known_speaker_name,
            )
            save_diarized_transcript(transcript, json_path, text_path)
        labeled_text = transcript.labeled_text()
        item.transcript_raw_path = str(text_path)
        item.status = STATUS_PROCESSING
        state.upsert(content_hash, item)
        state.save()

        processed = process_fn(labeled_text, config.anthropic_api_key, config.anthropic_model)
        recorded_at = parse_mobile_meeting_date(audio_path)
        meta = DesktopNoteMeta(
            content_hash=content_hash,
            created_at=datetime.now().astimezone(),
            recorded_at=recorded_at,
            mic_audio_path=str(archive_path),
            system_audio_path=None,
            transcription_model=config.meeting_transcription_model,
            processing_model=config.anthropic_model,
            source="mobile-meeting",
        )
        markdown = build_mobile_meeting_markdown(processed, labeled_text, meta)
        final_path = write_note_atomic(
            config.vault_meeting_dir, build_filename(recorded_at, processed.title), markdown
        )
        item.status = STATUS_DONE
        item.note_path = str(final_path)
        item.error = None
        item.updated_at = _now_iso()
        state.upsert(content_hash, item)
        state.save()
        return "done"
    except Exception as exc:  # noqa: BLE001
        item.status = STATUS_ERROR
        item.error = f"{type(exc).__name__}: {exc}"
        item.updated_at = _now_iso()
        state.upsert(content_hash, item)
        state.save()
        return "error"
