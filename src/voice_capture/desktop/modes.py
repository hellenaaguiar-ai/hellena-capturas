"""Definicao dos modos de captura no desktop (ideia / reuniao / terapia)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import Config

NOTE_TYPE_IDEA = "voice-capture"
NOTE_TYPE_MEETING = "meeting-capture"
NOTE_TYPE_THERAPY = "therapy-capture"


@dataclass(frozen=True)
class CaptureMode:
    key: str
    label: str
    hotkey: str
    capture_system_audio: bool
    note_type: str
    vault_dir: Path


def build_modes(config: Config) -> list[CaptureMode]:
    """Modos disponiveis, com hotkey e pasta de destino vindos da config."""
    return [
        CaptureMode(
            key="idea",
            label="Ideia",
            hotkey=config.hotkeys["idea"],
            capture_system_audio=False,
            note_type=NOTE_TYPE_IDEA,
            vault_dir=config.vault_inbox_dir,
        ),
        CaptureMode(
            key="meeting",
            label="Reunião",
            hotkey=config.hotkeys["meeting"],
            capture_system_audio=True,
            note_type=NOTE_TYPE_MEETING,
            vault_dir=config.vault_meeting_dir,
        ),
        CaptureMode(
            key="therapy",
            label="Terapia",
            hotkey=config.hotkeys["therapy"],
            capture_system_audio=True,
            note_type=NOTE_TYPE_THERAPY,
            vault_dir=config.vault_therapy_dir,
        ),
    ]


def get_mode(config: Config, key: str) -> CaptureMode:
    for mode in build_modes(config):
        if mode.key == key:
            return mode
    raise KeyError(f"Modo desconhecido: {key}")
