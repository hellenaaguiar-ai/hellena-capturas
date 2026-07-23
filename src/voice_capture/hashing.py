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
