from pathlib import Path

import pytest

from voice_capture.config import Config
from voice_capture.pipeline import process_item
from voice_capture.process_ai import ProcessedCapture
from voice_capture.state import STATUS_DONE, STATUS_ERROR, StateStore
from voice_capture.transcribe import TranscriptResult


def make_config(tmp_path) -> Config:
    config = Config(
        inbox_dir=tmp_path / "inbox",
        vault_inbox_dir=tmp_path / "vault" / "Inbox" / "Voz",
        data_dir=tmp_path / "data",
        whisper_model="small",
        whisper_language="pt",
        anthropic_model="claude-sonnet-5",
        anthropic_api_key="fake-key",
        audio_retention_days=30,
    )
    config.ensure_dirs()
    return config


def fake_transcribe(path: Path, model_size: str, language: str) -> TranscriptResult:
    return TranscriptResult(text="Esse personagem interpreta o controle como cuidado.", language="pt", duration_seconds=12.0)


def fake_process(raw_text: str, api_key: str, model: str) -> ProcessedCapture:
    return ProcessedCapture(
        title="Vigilância como cuidado",
        synthesis="Reflexão sobre controle interpretado como cuidado.",
        cleaned_transcript=raw_text,
        entities=[],
        evidence_and_connections=[],
        open_questions=[],
        possible_uses=["Second Brain"],
        classification="reflexao-livro",
        confidence="media",
        related_topics=["vigilância"],
        uncertainty_notes="",
    )


def failing_process(raw_text: str, api_key: str, model: str) -> ProcessedCapture:
    raise RuntimeError("Claude API indisponível")


def make_audio_file(config: Config, name: str = "Gravação 2026-07-23 22-14-00.m4a", content: bytes = b"audio-fake-bytes") -> Path:
    path = config.inbox_dir / name
    path.write_bytes(content)
    return path


def test_process_item_success_creates_note_and_marks_done(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config.state_file)
    audio_path = make_audio_file(config)

    result = process_item(audio_path, config, state, transcribe_fn=fake_transcribe, process_fn=fake_process)

    assert result == "done"
    notes = list(config.vault_inbox_dir.glob("*.md"))
    assert len(notes) == 1
    assert notes[0].name.startswith("2026-07-23 2214")

    content_hash = next(iter(state.all_items()))
    item = state.get(content_hash)
    assert item.status == STATUS_DONE
    assert item.note_path == str(notes[0])
    assert Path(item.audio_archive_path).exists()


def test_process_item_is_idempotent_no_duplicate_note(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config.state_file)
    audio_path = make_audio_file(config)

    process_item(audio_path, config, state, transcribe_fn=fake_transcribe, process_fn=fake_process)
    result_second = process_item(audio_path, config, state, transcribe_fn=fake_transcribe, process_fn=fake_process)

    assert result_second == "skipped-duplicate"
    notes = list(config.vault_inbox_dir.glob("*.md"))
    assert len(notes) == 1


def test_process_item_failure_preserves_audio_and_marks_error(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config.state_file)
    audio_path = make_audio_file(config)

    result = process_item(audio_path, config, state, transcribe_fn=fake_transcribe, process_fn=failing_process)

    assert result == "error"
    content_hash = next(iter(state.all_items()))
    item = state.get(content_hash)
    assert item.status == STATUS_ERROR
    assert "Claude API indisponível" in item.error
    # audio ja tinha sido arquivado antes da falha do processamento por IA
    assert Path(item.audio_archive_path).exists()
    # transcricao bruta tambem foi preservada
    assert Path(item.transcript_raw_path).exists()
    assert list(config.vault_inbox_dir.glob("*.md")) == []


def test_process_item_different_content_same_name_is_not_deduped(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config.state_file)

    audio1 = make_audio_file(config, name="a.m4a", content=b"conteudo-1")
    result1 = process_item(audio1, config, state, transcribe_fn=fake_transcribe, process_fn=fake_process)
    audio1.write_bytes(b"conteudo-2")
    result2 = process_item(audio1, config, state, transcribe_fn=fake_transcribe, process_fn=fake_process)

    assert result1 == "done"
    assert result2 == "done"
    assert len(state.all_items()) == 2
