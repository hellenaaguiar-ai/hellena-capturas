"""Fila local em JSON: estado de cada gravacao, indexado por hash do audio."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

STATUS_PENDING = "pending"
STATUS_TRANSCRIBING = "transcribing"
STATUS_PROCESSING = "processing"
STATUS_DONE = "done"
STATUS_ERROR = "error"


@dataclass
class ItemState:
    source_filename: str
    first_seen_at: str
    recorded_at: Optional[str] = None
    status: str = STATUS_PENDING
    attempts: int = 0
    error: Optional[str] = None
    note_path: Optional[str] = None
    audio_archive_path: Optional[str] = None
    transcript_raw_path: Optional[str] = None
    updated_at: Optional[str] = None


class StateStore:
    """Wrapper simples sobre um dict[hash -> ItemState] persistido em JSON."""

    def __init__(self, path: Path):
        self.path = path
        self._items: dict[str, ItemState] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._items = {}
            return
        raw = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        self._items = {k: ItemState(**v) for k, v in raw.items()}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: asdict(v) for k, v in self._items.items()}
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=".state_", suffix=".json.tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def get(self, content_hash: str) -> Optional[ItemState]:
        return self._items.get(content_hash)

    def upsert(self, content_hash: str, item: ItemState) -> None:
        self._items[content_hash] = item

    def is_done(self, content_hash: str) -> bool:
        item = self._items.get(content_hash)
        return item is not None and item.status == STATUS_DONE

    def all_items(self) -> dict[str, ItemState]:
        return dict(self._items)

    def errors(self) -> dict[str, ItemState]:
        return {h: i for h, i in self._items.items() if i.status == STATUS_ERROR}
