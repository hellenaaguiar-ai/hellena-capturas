import wave

import pytest

from voice_capture.desktop.audio_capture import (
    _default_loopback_device,
    _default_mic_device,
    _wasapi_host_api_info,
    _write_wav,
)


class FakePyAudioModule:
    paWASAPI = 42


class FakePyAudioInstance:
    """Dublê de uma instancia de `pyaudiowpatch.PyAudio()`: so implementa o
    que audio_capture.py usa, permitindo testar a logica de selecao de
    dispositivo sem hardware real nem rodar em Windows."""

    def __init__(self, wasapi_info=None, devices=None, loopback_devices=None, raise_no_wasapi=False):
        self._wasapi_info = wasapi_info or {}
        self._devices = devices or {}
        self._loopback_devices = loopback_devices or []
        self._raise_no_wasapi = raise_no_wasapi

    def get_host_api_info_by_type(self, api_type):
        if self._raise_no_wasapi:
            raise OSError("WASAPI nao encontrado")
        return self._wasapi_info

    def get_device_info_by_index(self, index):
        return self._devices[index]

    def get_loopback_device_info_generator(self):
        return iter(self._loopback_devices)


def test_wasapi_host_api_info_missing_raises_clear_error():
    p = FakePyAudioInstance(raise_no_wasapi=True)
    with pytest.raises(RuntimeError, match="WASAPI"):
        _wasapi_host_api_info(FakePyAudioModule, p)


def test_default_mic_device_returns_device_info():
    p = FakePyAudioInstance(
        wasapi_info={"defaultInputDevice": 3},
        devices={3: {"index": 3, "name": "Microfone X", "maxInputChannels": 1, "defaultSampleRate": 48000.0}},
    )
    device = _default_mic_device(FakePyAudioModule, p)
    assert device["index"] == 3


def test_default_mic_device_none_configured_raises_clear_error():
    p = FakePyAudioInstance(wasapi_info={"defaultInputDevice": -1})
    with pytest.raises(RuntimeError, match="microfone"):
        _default_mic_device(FakePyAudioModule, p)


def test_default_loopback_device_when_default_output_is_already_loopback():
    p = FakePyAudioInstance(
        wasapi_info={"defaultOutputDevice": 5},
        devices={5: {"index": 5, "name": "Speakers [Loopback]", "isLoopbackDevice": True, "maxInputChannels": 2, "defaultSampleRate": 48000.0}},
    )
    device = _default_loopback_device(FakePyAudioModule, p)
    assert device["index"] == 5


def test_default_loopback_device_finds_matching_loopback_by_name():
    p = FakePyAudioInstance(
        wasapi_info={"defaultOutputDevice": 5},
        devices={5: {"index": 5, "name": "Speakers (Realtek)", "isLoopbackDevice": False}},
        loopback_devices=[
            {"index": 9, "name": "Speakers (Realtek) [Loopback]", "maxInputChannels": 2, "defaultSampleRate": 48000.0},
        ],
    )
    device = _default_loopback_device(FakePyAudioModule, p)
    assert device["index"] == 9


def test_default_loopback_device_none_configured_raises_clear_error():
    p = FakePyAudioInstance(wasapi_info={"defaultOutputDevice": -1})
    with pytest.raises(RuntimeError, match="saida"):
        _default_loopback_device(FakePyAudioModule, p)


def test_default_loopback_device_no_match_raises_clear_error():
    p = FakePyAudioInstance(
        wasapi_info={"defaultOutputDevice": 5},
        devices={5: {"index": 5, "name": "Speakers (Realtek)", "isLoopbackDevice": False}},
        loopback_devices=[{"index": 9, "name": "Outro dispositivo qualquer", "maxInputChannels": 2, "defaultSampleRate": 48000.0}],
    )
    with pytest.raises(RuntimeError, match="loopback"):
        _default_loopback_device(FakePyAudioModule, p)


def test_write_wav_joins_raw_pcm_frames(tmp_path):
    frames = [b"\x01\x00\x02\x00", b"\x03\x00\x04\x00"]
    path = _write_wav(tmp_path / "audio.wav", frames, channels=1, sample_rate=48000)

    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 48000
        assert wf.getnframes() == 4
        assert wf.readframes(4) == b"\x01\x00\x02\x00\x03\x00\x04\x00"


def test_write_wav_empty_frames_writes_silence(tmp_path):
    path = _write_wav(tmp_path / "vazio.wav", [], channels=2, sample_rate=48000)

    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 2
        assert wf.getnframes() == 0
