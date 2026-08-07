"""Carrega configuracao de config.yaml + .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = Path("config.yaml")

DEFAULT_HOTKEYS = {
    "idea": "ctrl+space",
    # Caps Lock+letra por pedido explicito (mais facil de lembrar/alcancar
    # que Ctrl+Alt+letra). listener.py registra esses hotkeys com
    # suppress=True especificamente por causa deles - isso bloqueia o
    # evento na origem, o que deve evitar o efeito colateral de ligar/
    # desligar o Caps Lock de verdade (nao pode ser testado neste
    # ambiente, so num Windows real).
    "meeting": "caps lock+r",
    "therapy": "caps lock+t",
    "class": "caps lock+a",
    "stop": "caps lock+p",
    # Atalho extra pro MESMO modo "idea" (mesma pasta, mesmo processamento -
    # a IA ja classifica reflexao/desabafo/mudanca de pensamento
    # automaticamente). So um segundo jeito de acionar, pra separar na
    # cabeca "tive uma ideia" de "preciso desabafar/refletir".
    "reflection": "caps lock+d",
}


@dataclass(frozen=True)
class Config:
    inbox_dir: Path
    vault_inbox_dir: Path
    data_dir: Path
    whisper_model: str
    whisper_language: str
    anthropic_model: str
    anthropic_api_key: str
    audio_retention_days: int
    vault_meeting_dir: Path
    vault_therapy_dir: Path
    vault_class_dir: Path
    hotkeys: dict = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))
    whisper_initial_prompt: str = ""

    @property
    def audio_archive_dir(self) -> Path:
        return self.data_dir / "audio_archive"

    @property
    def transcripts_raw_dir(self) -> Path:
        return self.data_dir / "transcripts_raw"

    @property
    def desktop_audio_dir(self) -> Path:
        return self.data_dir / "desktop_recordings"

    @property
    def state_file(self) -> Path:
        return self.data_dir / "state.json"

    @property
    def log_file(self) -> Path:
        return self.data_dir / "pipeline.log"

    @property
    def error_note_path(self) -> Path:
        return self.vault_inbox_dir / "_Erros de captura.md"

    def ensure_dirs(self) -> None:
        for d in (
            self.inbox_dir,
            self.vault_inbox_dir,
            self.vault_meeting_dir,
            self.vault_therapy_dir,
            self.vault_class_dir,
            self.data_dir,
            self.audio_archive_dir,
            self.transcripts_raw_dir,
            self.desktop_audio_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config nao encontrada em {path}. Copie config.example.yaml para "
            "config.yaml e ajuste os caminhos."
        )
    load_dotenv()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY nao definida. Copie .env.example para .env e "
            "preencha a chave."
        )

    vault_inbox_dir = Path(raw["vault_inbox_dir"])
    desktop_raw = raw.get("desktop", {}) or {}
    hotkeys = dict(DEFAULT_HOTKEYS)
    hotkeys.update(desktop_raw.get("hotkeys", {}) or {})

    return Config(
        inbox_dir=Path(raw["inbox_dir"]),
        vault_inbox_dir=vault_inbox_dir,
        data_dir=Path(raw.get("data_dir", "data")),
        whisper_model=raw.get("whisper_model", "small"),
        whisper_language=raw.get("whisper_language", "pt"),
        whisper_initial_prompt=raw.get("whisper_initial_prompt", ""),
        anthropic_model=raw.get("anthropic_model", "claude-sonnet-5"),
        anthropic_api_key=api_key,
        audio_retention_days=int(raw.get("audio_retention_days", 30)),
        vault_meeting_dir=Path(desktop_raw.get("vault_meeting_dir", vault_inbox_dir.parent / "Reuniões")),
        vault_therapy_dir=Path(desktop_raw.get("vault_therapy_dir", vault_inbox_dir.parent / "Terapia")),
        vault_class_dir=Path(desktop_raw.get("vault_class_dir", vault_inbox_dir.parent / "Aulas")),
        hotkeys=hotkeys,
    )
