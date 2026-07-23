"""Hash de conteudo usado como chave de deduplicacao."""
from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def short_hash(full_hash: str, length: int = 10) -> str:
    return full_hash[:length]


def combined_hash(paths: list[Path]) -> str:
    """Hash estavel para um conjunto de arquivos (ex: trilhas mic+sistema
    da mesma gravacao), usado como chave de dedupe."""
    digest = hashlib.sha256()
    for path in paths:
        if path is None:
            continue
        digest.update(sha256_file(path).encode("ascii"))
    return digest.hexdigest()
