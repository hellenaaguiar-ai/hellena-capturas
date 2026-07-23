"""Captura de audio no desktop: microfone e, opcionalmente, uma segunda
trilha com o audio que esta tocando no computador (loopback WASAPI), para
separar "voce" de "outra pessoa" sem precisar de diarizacao.

Dependencia pesada (soundcard) e importada so na hora de gravar, nao no
import do modulo - o resto do pacote (modos, pipeline, markdown) continua
testavel sem hardware de audio.
"""
from __future__ import annotations

import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SAMPLE_RATE = 48000
CHANNELS = 1
CHUNK_FRAMES = SAMPLE_RATE // 10  # 100ms por leitura, mantem o stop responsivo


class RecordingSession:
    """Grava microfone e, se configurado, a trilha de loopback do sistema,
    em threads separadas, ate stop() ser chamado."""

    def __init__(self, mic_path: Path, system_path: Optional[Path]):
        self.mic_path = mic_path
        self.system_path = system_path
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._mic_frames: list = []
        self._system_frames: list = []
        self._error: Optional[Exception] = None

    def start(self) -> None:
        self._threads.append(threading.Thread(target=self._run_mic, daemon=True))
        if self.system_path is not None:
            self._threads.append(threading.Thread(target=self._run_system, daemon=True))
        for t in self._threads:
            t.start()

    def _run_mic(self) -> None:
        try:
            import soundcard as sc

            mic = sc.default_microphone()
            with mic.recorder(samplerate=SAMPLE_RATE, channels=CHANNELS) as recorder:
                while not self._stop_event.is_set():
                    self._mic_frames.append(recorder.record(numframes=CHUNK_FRAMES))
        except Exception as exc:  # noqa: BLE001
            self._error = exc

    def _run_system(self) -> None:
        try:
            import soundcard as sc

            speaker = sc.default_speaker()
            loopback = sc.get_microphone(id=str(speaker.name), include_loopback=True)
            with loopback.recorder(samplerate=SAMPLE_RATE, channels=CHANNELS) as recorder:
                while not self._stop_event.is_set():
                    self._system_frames.append(recorder.record(numframes=CHUNK_FRAMES))
        except Exception as exc:  # noqa: BLE001
            self._error = exc

    def stop(self) -> tuple[Path, Optional[Path]]:
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=5)
        if self._error is not None:
            raise self._error

        mic_path = _write_wav(self.mic_path, self._mic_frames)
        system_path = None
        if self.system_path is not None:
            system_path = _write_wav(self.system_path, self._system_frames)
        return mic_path, system_path


def _write_wav(path: Path, frames: list) -> Path:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    if frames:
        data = np.concatenate(frames, axis=0)
    else:
        data = np.zeros((0, CHANNELS), dtype="float32")
    pcm16 = np.clip(data * 32767, -32768, 32767).astype("int16")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm16.tobytes())
    return path


def start_capture(mic_path: Path, system_path: Optional[Path]) -> RecordingSession:
    session = RecordingSession(mic_path, system_path)
    session.start()
    return session
