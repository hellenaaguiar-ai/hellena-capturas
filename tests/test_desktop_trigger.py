import pytest

from voice_capture.config import Config
from voice_capture.desktop.trigger import trigger_mode, trigger_reflection, trigger_stop


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
        vault_class_dir=tmp_path / "vault" / "Inbox" / "Aulas",
    )


def test_trigger_mode_sends_configured_hotkey(tmp_path):
    config = make_config(tmp_path)
    sent = []

    mode = trigger_mode("therapy", config, send_keys=sent.append)

    assert mode.key == "therapy"
    assert sent == [config.hotkeys["therapy"]]


def test_trigger_mode_idea_and_meeting(tmp_path):
    config = make_config(tmp_path)
    sent = []

    trigger_mode("idea", config, send_keys=sent.append)
    trigger_mode("meeting", config, send_keys=sent.append)

    assert sent == [config.hotkeys["idea"], config.hotkeys["meeting"]]


def test_trigger_mode_unknown_key_raises(tmp_path):
    config = make_config(tmp_path)
    with pytest.raises(ValueError):
        trigger_mode("nao-existe", config, send_keys=lambda k: None)


def test_trigger_mode_class(tmp_path):
    config = make_config(tmp_path)
    sent = []

    mode = trigger_mode("class", config, send_keys=sent.append)

    assert mode.key == "class"
    assert sent == [config.hotkeys["class"]]


def test_trigger_stop_sends_configured_hotkey(tmp_path):
    config = make_config(tmp_path)
    sent = []

    hotkey = trigger_stop(config, send_keys=sent.append)

    assert hotkey == config.hotkeys["stop"]
    assert sent == [config.hotkeys["stop"]]


def test_trigger_reflection_sends_configured_hotkey(tmp_path):
    config = make_config(tmp_path)
    sent = []

    hotkey = trigger_reflection(config, send_keys=sent.append)

    assert hotkey == config.hotkeys["reflection"]
    assert sent == [config.hotkeys["reflection"]]
