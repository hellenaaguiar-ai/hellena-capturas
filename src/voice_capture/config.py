"""Carrega configuracao de config.yaml + .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = Path("config.yaml")


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

    @property
    def audio_archive_dir(self) -> Path:
        return self.data_dir / "audio_archive"

    @property
    def transcripts_raw_dir(self) -> Path:
        return self.data_dir / "transcripts_raw"

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
            self.data_dir,
            self.audio_archive_dir,
            self.transcripts_raw_dir,
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

    return Config(
        inbox_dir=Path(raw["inbox_dir"]),
        vault_inbox_dir=Path(raw["vault_inbox_dir"]),
        data_dir=Path(raw.get("data_dir", "data")),
        whisper_model=raw.get("whisper_model", "small"),
        whisper_language=raw.get("whisper_language", "pt"),
        anthropic_model=raw.get("anthropic_model", "claude-sonnet-5"),
        anthropic_api_key=api_key,
        audio_retention_days=int(raw.get("audio_retention_days", 30)),
    )
