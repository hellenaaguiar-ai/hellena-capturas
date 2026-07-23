import wave
from datetime import datetime
from pathlib import Path

from voice_capture.config import Config
from voice_capture.desktop.modes import get_mode
from voice_capture.desktop_ai import ProcessedMeeting, ProcessedTherapy
from voice_capture.desktop_pipeline import process_desktop_recording
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
        vault_meeting_dir=tmp_path / "vault" / "Inbox" / "Reuniões",
        vault_therapy_dir=tmp_path / "vault" / "Inbox" / "Terapia",
    )
    config.ensure_dirs()
    return config


def make_silent_wav(path: Path) -> Path:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        wf.writeframes(b"\x00\x00" * 100)
    return path


def fake_transcribe(path: Path, model_size: str, language: str) -> TranscriptResult:
    label = "mic" if "mic" in path.name else "system"
    return TranscriptResult(text=f"texto transcrito ({label})", language="pt", duration_seconds=5.0)


def fake_meeting_process(labeled_text: str, api_key: str, model: str) -> ProcessedMeeting:
    assert "[Você - microfone]" in labeled_text
    assert "áudio do sistema" in labeled_text
    return ProcessedMeeting(
        title="Reunião de alinhamento",
        summary="Discussão sobre o roadmap.",
        decisions=["Adiar o lançamento"],
        action_items=["Enviar resumo por e-mail"],
        participants_mentioned=["Ana"],
        open_questions=[],
        confidence="alta",
        uncertainty_notes="",
    )


def failing_meeting_process(labeled_text: str, api_key: str, model: str) -> ProcessedMeeting:
    raise RuntimeError("Claude API indisponível")


def fake_therapy_process(labeled_text: str, api_key: str, model: str) -> ProcessedTherapy:
    return ProcessedTherapy(
        title="Sessão sobre rotina",
        session_summary="Conversa sobre organização do dia a dia.",
        themes=["rotina"],
        insights=["percebi que adio tarefas quando estou ansiosa"],
        follow_ups=["Anotar horários de sono"],
        confidence="media",
        uncertainty_notes="",
    )


def test_meeting_mode_creates_note_and_marks_done(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config.state_file)
    mode = get_mode(config, "meeting")

    mic_path = make_silent_wav(config.desktop_audio_dir / "meeting-mic-1.wav")
    system_path = make_silent_wav(config.desktop_audio_dir / "meeting-system-1.wav")

    result = process_desktop_recording(
        mode,
        mic_path,
        system_path,
        datetime(2026, 7, 23, 10, 0),
        config,
        state,
        transcribe_fn=fake_transcribe,
        process_meeting_fn=fake_meeting_process,
    )

    assert result == "done"
    notes = list(mode.vault_dir.glob("*.md"))
    assert len(notes) == 1
    content = notes[0].read_text(encoding="utf-8")
    assert "type: meeting-capture" in content
    assert "Adiar o lançamento" in content
    assert "texto transcrito (mic)" in content
    assert "texto transcrito (system)" in content


def test_therapy_mode_creates_note_with_expected_sections(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config.state_file)
    mode = get_mode(config, "therapy")

    mic_path = make_silent_wav(config.desktop_audio_dir / "therapy-mic-1.wav")
    system_path = make_silent_wav(config.desktop_audio_dir / "therapy-system-1.wav")

    result = process_desktop_recording(
        mode,
        mic_path,
        system_path,
        datetime(2026, 7, 23, 18, 0),
        config,
        state,
        transcribe_fn=fake_transcribe,
        process_therapy_fn=fake_therapy_process,
    )

    assert result == "done"
    notes = list(mode.vault_dir.glob("*.md"))
    content = notes[0].read_text(encoding="utf-8")
    assert "type: therapy-capture" in content
    assert "## Percepções expressas na sessão" in content
    assert "adio tarefas quando estou ansiosa" in content


def test_desktop_recording_is_idempotent(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config.state_file)
    mode = get_mode(config, "meeting")

    mic_path = make_silent_wav(config.desktop_audio_dir / "meeting-mic-2.wav")
    system_path = make_silent_wav(config.desktop_audio_dir / "meeting-system-2.wav")
    recorded_at = datetime(2026, 7, 23, 11, 0)

    first = process_desktop_recording(
        mode, mic_path, system_path, recorded_at, config, state,
        transcribe_fn=fake_transcribe, process_meeting_fn=fake_meeting_process,
    )
    second = process_desktop_recording(
        mode, mic_path, system_path, recorded_at, config, state,
        transcribe_fn=fake_transcribe, process_meeting_fn=fake_meeting_process,
    )

    assert first == "done"
    assert second == "skipped-duplicate"
    assert len(list(mode.vault_dir.glob("*.md"))) == 1


def test_desktop_recording_failure_marks_error_and_preserves_transcript(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config.state_file)
    mode = get_mode(config, "meeting")

    mic_path = make_silent_wav(config.desktop_audio_dir / "meeting-mic-3.wav")
    system_path = make_silent_wav(config.desktop_audio_dir / "meeting-system-3.wav")

    result = process_desktop_recording(
        mode,
        mic_path,
        system_path,
        datetime(2026, 7, 23, 12, 0),
        config,
        state,
        transcribe_fn=fake_transcribe,
        process_meeting_fn=failing_meeting_process,
    )

    assert result == "error"
    items = list(state.all_items().values())
    assert len(items) == 1
    assert items[0].status == STATUS_ERROR
    assert "Claude API indisponível" in items[0].error
    assert Path(items[0].transcript_raw_path).exists()
    assert list(mode.vault_dir.glob("*.md")) == []


def test_idea_mode_has_no_system_audio(tmp_path):
    config = make_config(tmp_path)
    mode = get_mode(config, "idea")
    assert mode.capture_system_audio is False
