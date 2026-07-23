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
        anthropic_model="claude-sonnet-5",
        anthropic_api_key="fake-key",
        audio_retention_days=30,
        vault_meeting_dir=tmp_path / "vault" / "Inbox" / "Reuniões",
        vault_therapy_dir=tmp_path / "vault" / "Inbox" / "Terapia",
    )


def test_build_modes_uses_config_hotkeys_and_dirs(tmp_path):
    config = make_config(tmp_path)
    modes = build_modes(config)

    keys = {m.key for m in modes}
    assert keys == {"idea", "meeting", "therapy"}

    idea = get_mode(config, "idea")
    assert idea.capture_system_audio is False
    assert idea.vault_dir == config.vault_inbox_dir

    meeting = get_mode(config, "meeting")
    assert meeting.capture_system_audio is True
    assert meeting.vault_dir == config.vault_meeting_dir

    therapy = get_mode(config, "therapy")
    assert therapy.capture_system_audio is True
    assert therapy.vault_dir == config.vault_therapy_dir


def test_default_hotkeys(tmp_path):
    config = make_config(tmp_path)
    idea = get_mode(config, "idea")
    assert idea.hotkey == "ctrl+alt+i"
