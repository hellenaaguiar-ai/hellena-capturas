from pathlib import Path

from voice_capture.config import Config
from voice_capture.desktop.modes import build_modes, get_mode


def make_config(tmp_path) -> Config:
    return Config(
        inbox_dir=tmp_path / "inbox",
        vault_inbox_dir=tmp_path / "vault" / "Inbox" / "Voz",
        data_dir=tmp_path / "data",
        whisper_model="small",
        whisper_language="pt",
        extraction_model="gpt-4.1",
        openai_api_key="fake-key",
        audio_retention_days=30,
        vault_meeting_dir=tmp_path / "vault" / "Inbox" / "Reuniões",
        vault_therapy_dir=tmp_path / "vault" / "Inbox" / "Terapia",
        vault_class_dir=tmp_path / "vault" / "Inbox" / "Aulas",
        vault_reflection_dir=tmp_path / "vault" / "Inbox" / "Reflexões",
    )


def test_build_modes_uses_config_hotkeys_and_dirs(tmp_path):
    config = make_config(tmp_path)
    modes = build_modes(config)

    keys = {m.key for m in modes}
    assert keys == {"idea", "reflection", "meeting", "therapy", "class"}

    idea = get_mode(config, "idea")
    assert idea.capture_mic is True
    assert idea.capture_system_audio is False
    assert idea.vault_dir == config.vault_inbox_dir

    reflection = get_mode(config, "reflection")
    assert reflection.capture_mic is True
    assert reflection.capture_system_audio is False
    assert reflection.vault_dir == config.vault_reflection_dir

    meeting = get_mode(config, "meeting")
    assert meeting.capture_mic is True
    assert meeting.capture_system_audio is True
    assert meeting.vault_dir == config.vault_meeting_dir

    therapy = get_mode(config, "therapy")
    assert therapy.capture_mic is True
    assert therapy.capture_system_audio is True
    assert therapy.vault_dir == config.vault_therapy_dir

    class_mode = get_mode(config, "class")
    # Aula so grava o audio da aula (sistema) - sem microfone.
    assert class_mode.capture_mic is False
    assert class_mode.capture_system_audio is True
    assert class_mode.vault_dir == config.vault_class_dir


def test_default_hotkeys(tmp_path):
    config = make_config(tmp_path)
    idea = get_mode(config, "idea")
    assert idea.hotkey == "ctrl+space"

    reflection = get_mode(config, "reflection")
    assert reflection.hotkey == "ctrl+alt+d"

    class_mode = get_mode(config, "class")
    assert class_mode.hotkey == "ctrl+alt+a"
