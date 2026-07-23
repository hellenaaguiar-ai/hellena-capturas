"""Apaga audio arquivado de itens ja concluidos ha mais de N dias.
Nao apaga transcricoes (sao arquivos de texto pequenos, mantidos indefinidamente).
Nao roda automaticamente - e um comando manual (ver docs/windows-setup.md).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from .config import Config, load_config
from .state import STATUS_DONE, StateStore


def cleanup_old_audio(config: Config, state: StateStore) -> list[str]:
    cutoff = datetime.now().astimezone() - timedelta(days=config.audio_retention_days)
    removed: list[str] = []

    for content_hash, item in state.all_items().items():
        if item.status != STATUS_DONE or not item.audio_archive_path:
            continue
        if not item.updated_at:
            continue
        updated_at = datetime.fromisoformat(item.updated_at)
        if updated_at >= cutoff:
            continue
        audio_path = Path(item.audio_archive_path)
        if audio_path.exists():
            audio_path.unlink()
            removed.append(str(audio_path))
        item.audio_archive_path = None
        state.upsert(content_hash, item)

    if removed:
        state.save()
    return removed


def main() -> None:
    config = load_config()
    state = StateStore(config.state_file)
    removed = cleanup_old_audio(config, state)
    if removed:
        print(f"Removidos {len(removed)} arquivo(s) de audio com mais de {config.audio_retention_days} dias:")
        for path in removed:
            print(f"  - {path}")
    else:
        print("Nada para remover.")


if __name__ == "__main__":
    main()
