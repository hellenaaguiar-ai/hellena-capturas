"""Transcrição em nuvem exclusiva para reuniões móveis, com diarização."""
from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path

import httpx

OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"


@dataclass(frozen=True)
class SpeakerSegment:
    speaker: str
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class DiarizedTranscript:
    text: str
    segments: list[SpeakerSegment]
    raw: dict

    def labeled_text(self) -> str:
        lines = []
        for segment in self.segments:
            minutes, seconds = divmod(max(0, int(segment.start)), 60)
            lines.append(
                f"[{minutes:02d}:{seconds:02d}] {segment.speaker}: {segment.text.strip()}"
            )
        return "\n".join(lines) or self.text


def _reference_data_url(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Amostra de voz não encontrada: {path}")
    mime = mimetypes.guess_type(path.name)[0] or "audio/mp4"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def transcribe_meeting_cloud(
    audio_path: Path,
    api_key: str,
    model: str = "gpt-4o-transcribe-diarize",
    language: str = "pt",
    speaker_reference_path: Path | None = None,
    known_speaker_name: str = "Hellena",
    timeout_seconds: float = 1800,
) -> DiarizedTranscript:
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não definida para transcrever reuniões")

    data: list[tuple[str, str]] = [
        ("model", model),
        ("language", language),
        ("response_format", "diarized_json"),
        ("chunking_strategy", "auto"),
    ]
    if speaker_reference_path is not None:
        data.extend(
            [
                ("known_speaker_names[]", known_speaker_name),
                ("known_speaker_references[]", _reference_data_url(speaker_reference_path)),
            ]
        )

    mime = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
    with audio_path.open("rb") as audio_file:
        response = httpx.post(
            OPENAI_TRANSCRIPTIONS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files={"file": (audio_path.name, audio_file, mime)},
            timeout=timeout_seconds,
        )
    if response.is_error:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except (ValueError, AttributeError):
            detail = response.text
        raise RuntimeError(f"OpenAI transcription falhou ({response.status_code}): {detail}")

    payload = response.json()
    segments = [
        SpeakerSegment(
            speaker=str(segment.get("speaker", "Falante")),
            start=float(segment.get("start", 0)),
            end=float(segment.get("end", 0)),
            text=str(segment.get("text", "")),
        )
        for segment in payload.get("segments", [])
        if str(segment.get("text", "")).strip()
    ]
    return DiarizedTranscript(text=str(payload.get("text", "")), segments=segments, raw=payload)


def save_diarized_transcript(result: DiarizedTranscript, json_path: Path, text_path: Path) -> None:
    json_path.write_text(json.dumps(result.raw, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(result.labeled_text(), encoding="utf-8")
