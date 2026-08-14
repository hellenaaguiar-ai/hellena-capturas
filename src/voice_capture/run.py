"""Ponto de entrada: varre a pasta de inbox e processa o que estiver pendente.

Uso:
  python -m voice_capture.run                    # processa tudo que estiver pendente
  python -m voice_capture.run --status            # so mostra o estado atual, nao processa
  python -m voice_capture.run --reprocess <hash>  # reprocessa um item especifico
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from .config import Config, load_config
from .errors_note import write_errors_note
from .hashing import sha256_file
from .pipeline import process_item
from .state import StateStore

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".caf", ".aac", ".mp4"}
STABILITY_CHECK_SECONDS = 2


def setup_logging(config: Config) -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(config.log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _is_stable(path: Path) -> bool:
    """Evita processar um arquivo que o Google Drive ainda esta sincronizando."""
    try:
        size_before = path.stat().st_size
        time.sleep(STABILITY_CHECK_SECONDS)
        size_after = path.stat().st_size
        return size_before == size_after and size_after > 0
    except FileNotFoundError:
        return False


def scan_inbox(inbox_dir: Path) -> list[Path]:
    if not inbox_dir.exists():
        return []
    return sorted(
        p for p in inbox_dir.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )


def run_all(config: Config) -> int:
    state = StateStore(config.state_file)
    files = scan_inbox(config.inbox_dir)

    processed = skipped = held_errors = errors = 0
    for path in files:
        if not _is_stable(path):
            logging.info("Ignorando %s (ainda sincronizando)", path.name)
            continue

        result = process_item(path, config, state)
        if result == "done":
            processed += 1
            logging.info("OK: %s", path.name)
        elif result == "skipped-duplicate":
            skipped += 1
        elif result == "skipped-error-limit":
            held_errors += 1
            logging.warning("Aguardando reprocessamento manual após 3 falhas: %s", path.name)
        else:
            errors += 1
            logging.error("Falhou: %s", path.name)

    write_errors_note(config.error_note_path, state.errors())

    logging.info(
        "Resumo: %d processado(s), %d duplicado(s) ignorado(s), "
        "%d erro(s) aguardando reprocessamento manual, %d erro(s) novo(s)",
        processed,
        skipped,
        held_errors,
        errors,
    )
    return 1 if errors else 0


def run_reprocess(config: Config, hash_prefix: str) -> int:
    state = StateStore(config.state_file)
    matches = [h for h in state.all_items() if h.startswith(hash_prefix)]
    if not matches:
        logging.error("Nenhum item encontrado com hash comecando em %s", hash_prefix)
        return 1
    if len(matches) > 1:
        logging.error("Prefixo de hash ambiguo, corresponde a %d itens", len(matches))
        return 1

    content_hash = matches[0]
    item = state.get(content_hash)
    audio_path = Path(item.audio_archive_path) if item.audio_archive_path else None
    if not audio_path or not audio_path.exists():
        logging.error("Audio arquivado nao encontrado para reprocessar: %s", audio_path)
        return 1

    result = process_item(audio_path, config, state, force=True)
    write_errors_note(config.error_note_path, state.errors())
    logging.info("Reprocessamento de %s: %s", content_hash[:16], result)
    return 0 if result == "done" else 1


def print_status(config: Config) -> None:
    state = StateStore(config.state_file)
    for content_hash, item in state.all_items().items():
        print(f"{content_hash[:16]}  {item.status:12}  {item.source_filename}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de captura de voz -> Obsidian")
    parser.add_argument("--reprocess", metavar="HASH", help="reprocessa um item pelo hash (ou prefixo)")
    parser.add_argument("--status", action="store_true", help="mostra o estado atual sem processar")
    args = parser.parse_args()

    config = load_config()
    config.ensure_dirs()
    setup_logging(config)

    if args.status:
        print_status(config)
        return

    if args.reprocess:
        sys.exit(run_reprocess(config, args.reprocess))

    sys.exit(run_all(config))


if __name__ == "__main__":
    main()
