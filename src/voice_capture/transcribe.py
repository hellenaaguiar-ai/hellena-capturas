"""Transcricao local via faster-whisper. Nenhum audio sai da maquina aqui."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptResult:
    text: str
    language: str
    duration_seconds: float


_model_cache: dict[str, object] = {}


def _get_model(model_size: str):
    if model_size not in _model_cache:
        # Import tardio: so exige a dependencia pesada quando de fato for transcrever.
        from faster_whisper import WhisperModel

        _model_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model_cache[model_size]


def transcribe_audio(path: Path, model_size: str, language: str) -> TranscriptResult:
    model = _get_model(model_size)
    segments, info = model.transcribe(str(path), language=language, vad_filter=True)
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return TranscriptResult(
        text=text,
        language=info.language or language,
        duration_seconds=float(info.duration or 0.0),
    )
