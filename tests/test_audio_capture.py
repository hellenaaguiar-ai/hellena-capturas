import numpy as np
import pytest

from voice_capture.desktop.audio_capture import (
    _default_input_device,
    _default_loopback_device,
    _wasapi_hostapi_index,
    _wasapi_loopback_settings,
    _write_wav,
)


class FakeSoundDevice:
    """Dublê de `sounddevice`: so implementa o que audio_capture.py usa,
    permitindo testar a logica de selecao de dispositivo sem hardware real
    nem rodar em Windows."""

    def __init__(self, hostapis, devices=None, wasapi_settings_supports_loopback=True):
        self._hostapis = hostapis
        self._devices = devices or {}
        self._wasapi_settings_supports_loopback = wasapi_settings_supports_loopback

    def query_hostapis(self, index=None):
        if index is None:
            return self._hostapis
        return self._hostapis[index]

    def query_devices(self, index):
        return self._devices[index]

    def WasapiSettings(self, loopback=False):
        if loopback and not self._wasapi_settings_supports_loopback:
            raise TypeError("WasapiSettings.__init__() got an unexpected keyword argument 'loopback'")
        return {"loopback": loopback}


def test_wasapi_hostapi_index_found():
    sd = FakeSoundDevice([{"name": "MME"}, {"name": "Windows WASAPI"}])
    assert _wasapi_hostapi_index(sd) == 1


def test_wasapi_hostapi_index_missing_raises_clear_error():
    sd = FakeSoundDevice([{"name": "MME"}])
    with pytest.raises(RuntimeError, match="WASAPI"):
        _wasapi_hostapi_index(sd)


def test_default_input_device_returns_index():
    sd = FakeSoundDevice([{"name": "Windows WASAPI", "default_input_device": 3}])
    assert _default_input_device(sd) == 3


def test_default_input_device_none_configured_raises_clear_error():
    sd = FakeSoundDevice([{"name": "Windows WASAPI", "default_input_device": -1}])
    with pytest.raises(RuntimeError, match="microfone"):
        _default_input_device(sd)


def test_default_loopback_device_returns_index_and_channels():
    sd = FakeSoundDevice(
        [{"name": "Windows WASAPI", "default_output_device": 5}],
        devices={5: {"max_output_channels": 2}},
    )
    assert _default_loopback_device(sd) == (5, 2)


def test_default_loopback_device_none_configured_raises_clear_error():
    sd = FakeSoundDevice([{"name": "Windows WASAPI", "default_output_device": -1}])
    with pytest.raises(RuntimeError, match="saida"):
        _default_loopback_device(sd)


def test_wasapi_loopback_settings_ok_on_supported_version():
    sd = FakeSoundDevice([], wasapi_settings_supports_loopback=True)
    assert _wasapi_loopback_settings(sd) == {"loopback": True}


def test_wasapi_loopback_settings_raises_clear_error_on_old_sounddevice():
    sd = FakeSoundDevice([], wasapi_settings_supports_loopback=False)
    with pytest.raises(RuntimeError, match="atualize|Atualize"):
        _wasapi_loopback_settings(sd)


def test_write_wav_mixes_multi_channel_down_to_mono(tmp_path):
    frames = [np.array([[0.5, -0.5], [0.25, -0.25]], dtype="float32")]
    path = _write_wav(tmp_path / "audio.wav", frames)

    import wave

    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getnframes() == 2


def test_write_wav_empty_frames_writes_silence(tmp_path):
    path = _write_wav(tmp_path / "vazio.wav", [])

    import wave

    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getnframes() == 0
