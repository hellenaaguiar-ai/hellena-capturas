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
from .transcribe import TimedTranscriptResult, transcribe_audio_words

CloudFn = Callable[..., DiarizedTranscript]
ProcessFn = Callable[[str, str, str], ProcessedMeeting]
LocalTranscribeFn = Callable[..., TimedTranscriptResult]
_MOBILE_DATE_RE = re.compile(r"(\d{2})_(\d{2})_(\d{4}),\s*(\d{2})_(\d{2})")
_MOBILE_NAME_RE = re.compile(r"^REUNIÃO\s*-\s*(.*?)\s*-\s*\d{2}_\d{2}_\d{4}", re.IGNORECASE)
_TOKEN_LIMIT_ERROR = "Resposta da OpenAI interrompida pelo limite de tokens"
_OWNER_NAME_RE = re.compile(r"\bHelena\b", re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+")
_ENGLISH_MARKERS = frozenset(
    "the and to of for with is are was were from that this will should you your "
    "we our they their not but have has had can could would about what when where "
    "why how all any some more very just really think know want need make work "
    "people time good right yeah yes okay thanks thank".split()
)


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


def _needs_portuguese_retranscription(text: str) -> bool:
    words = [word.casefold() for word in _WORD_RE.findall(text)]
    if not words:
        return False
    english_hits = sum(word in _ENGLISH_MARKERS for word in words)
    return english_hits >= 30 and english_hits / len(words) >= 0.015


def _normalize_owner_name(text: str) -> str:
    return _OWNER_NAME_RE.sub("Hellena", text)


def _align_local_words(
    diarized: DiarizedTranscript,
    local: TimedTranscriptResult,
) -> DiarizedTranscript:
    """Mantem falantes/tempos da nuvem e troca apenas o texto pelo Whisper local."""
    if not diarized.segments or not local.words:
        return diarized

    segments = sorted(diarized.segments, key=lambda segment: segment.start)
    buckets: list[list[str]] = [[] for _ in segments]
    current = 0
    for word in local.words:
        midpoint = (word.start + word.end) / 2
        while current + 1 < len(segments) and midpoint > segments[current].end:
            current += 1

        candidates = range(max(0, current - 1), min(len(segments), current + 2))
        containing = [
            index
            for index in candidates
            if segments[index].start <= midpoint <= segments[index].end
        ]
        if containing:
            target = containing[0]
        else:
            target = min(
                candidates,
                key=lambda index: min(
                    abs(midpoint - segments[index].start),
                    abs(midpoint - segments[index].end),
                ),
            )
        buckets[target].append(word.text)

    aligned_segments = [
        SpeakerSegment(
            speaker=segment.speaker,
            start=segment.start,
            end=segment.end,
            text=_normalize_owner_name("".join(words).strip() or segment.text),
        )
        for segment, words in zip(segments, buckets)
    ]
    merged_text = " ".join(segment.text for segment in aligned_segments if segment.text.strip())
    raw = {
        "text": merged_text,
        "duration": local.duration_seconds,
        "language": local.language,
        "source": "local-portuguese-aligned-to-cloud-diarization",
        "segments": [
            {
                "speaker": segment.speaker,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
            }
            for segment in aligned_segments
        ],
    }
    return DiarizedTranscript(merged_text, aligned_segments, raw)


def _transcript_only_fallback(audio_path: Path) -> ProcessedMeeting:
    """Nao deixa uma transcricao integra presa por falha do resumo opcional."""
    match = _MOBILE_NAME_RE.search(audio_path.name)
    meeting_name = match.group(1).strip() if match else ""
    title = f"Reunião com {meeting_name}" if meeting_name else "Reunião transcrita"
    return ProcessedMeeting(
        title=title[:80],
        summary=(
            "A transcrição integral da reunião foi preservada abaixo. O resumo estruturado "
            "automático não foi incluído porque a resposta excedeu o limite seguro de geração."
        ),
        confidence="baixa",
        uncertainty_notes=(
            "Resumo, decisões e ações pendentes de revisão; nenhum conteúdo foi inferido."
        ),
    )


def process_mobile_meeting(
    audio_path: Path,
    config: Config,
    state: StateStore,
    cloud_fn: CloudFn = transcribe_meeting_cloud,
    process_fn: ProcessFn = process_meeting_transcript,
    force: bool = False,
    local_transcribe_fn: LocalTranscribeFn = transcribe_audio_words,
) -> str:
    content_hash = sha256_file(audio_path)
    if state.is_done(content_hash) and not force:
        return "skipped-duplicate"
    existing = state.get(content_hash)
    if existing and existing.status == STATUS_ERROR and existing.attempts >= MAX_AUTOMATIC_ATTEMPTS and not force:
        return "skipped-error-limit"

    item = existing or ItemState(source_filename=audio_path.name, first_seen_at=_now_iso())
    # No reprocessamento, run.py entrega o arquivo arquivado (nome = hash).
    # Preserve o nome original, pois ele contem pessoa e data da reuniao.
    if not (force and existing and _MOBILE_DATE_RE.search(existing.source_filename)):
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
        localized_json_path = config.transcripts_raw_dir / f"{content_hash}.localized.diarized.json"
        localized_text_path = config.transcripts_raw_dir / f"{content_hash}.localized.txt"
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
        active_text_path = text_path
        if localized_json_path.exists() and localized_text_path.exists():
            transcript = _load_cached(localized_json_path, localized_text_path)
            active_text_path = localized_text_path
        elif _needs_portuguese_retranscription(transcript.text):
            local = local_transcribe_fn(
                archive_path,
                model_size=config.whisper_model,
                language=config.whisper_language,
                initial_prompt=config.whisper_initial_prompt,
            )
            transcript = _align_local_words(transcript, local)
            save_diarized_transcript(transcript, localized_json_path, localized_text_path)
            active_text_path = localized_text_path
        labeled_text = transcript.labeled_text()
        item.transcript_raw_path = str(active_text_path)
        item.status = STATUS_PROCESSING
        state.upsert(content_hash, item)
        state.save()

        try:
            processed = process_fn(labeled_text, config.openai_api_key, config.extraction_model)
        except RuntimeError as exc:
            if _TOKEN_LIMIT_ERROR not in str(exc):
                raise
            processed = _transcript_only_fallback(audio_path)
        recorded_source = Path(item.source_filename)
        recorded_at = parse_mobile_meeting_date(
            recorded_source if _MOBILE_DATE_RE.search(recorded_source.stem) else audio_path
        )
        meta = DesktopNoteMeta(
            content_hash=content_hash,
            created_at=datetime.now().astimezone(),
            recorded_at=recorded_at,
            mic_audio_path=str(archive_path),
            system_audio_path=None,
            transcription_model=config.meeting_transcription_model,
            processing_model=config.extraction_model,
            source="mobile-meeting",
        )
        markdown = build_mobile_meeting_markdown(processed, labeled_text, meta)
        replace_existing = bool(force and existing and existing.note_path)
        filename = (
            Path(existing.note_path).name
            if replace_existing
            else build_filename(recorded_at, processed.title)
        )
        final_path = write_note_atomic(
            config.vault_meeting_dir,
            filename,
            markdown,
            replace_existing=replace_existing,
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
