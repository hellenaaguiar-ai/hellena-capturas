"""Captura de audio no desktop: microfone e, opcionalmente, uma segunda
trilha com o audio que esta tocando no computador (loopback WASAPI), para
separar "voce" de "outra pessoa" sem precisar de diarizacao.

Usa `sounddevice` (biblioteca baseada no PortAudio) em vez de `soundcard`:
a primeira versao usava `soundcard`, que assume que todo driver de audio
do Windows relata o formato WAVEFORMATEXTENSIBLE - em alguns drivers isso
e falso e a gravacao falhava com um AssertionError sem mensagem, sem
nenhuma configuracao do Windows resolvendo (caracteristica do driver, nao
do formato configurado). PortAudio negocia o formato de audio de forma
mais tolerante e e o que esse projeto usa hoje.

Dependencia pesada (sounddevice) e importada so na hora de gravar, nao no
import do modulo - o resto do pacote (modos, pipeline, markdown) continua
testavel sem hardware de audio.
"""
from __future__ import annotations

import threading
import wave
from pathlib import Path
from typing import Optional

SAMPLE_RATE = 48000
CHANNELS = 1
CHUNK_FRAMES = SAMPLE_RATE // 10  # 100ms por leitura, mantem o stop responsivo

WASAPI_HOSTAPI_NAME = "Windows WASAPI"


def _wasapi_hostapi_index(sd) -> int:
    for idx, api in enumerate(sd.query_hostapis()):
        if api["name"] == WASAPI_HOSTAPI_NAME:
            return idx
    raise RuntimeError(
        "Nao encontrei o host de audio 'Windows WASAPI' neste computador - "
        "a captura de audio no desktop so foi testada no Windows."
    )


def _default_input_device(sd) -> int:
    hostapi = sd.query_hostapis(_wasapi_hostapi_index(sd))
    device_index = hostapi["default_input_device"]
    if device_index < 0:
        raise RuntimeError(
            "Nenhum microfone padrao encontrado (WASAPI). Confira em Painel de "
            "Controle > Som > Gravação se existe um dispositivo marcado como padrão."
        )
    return device_index


def _default_loopback_device(sd) -> tuple[int, int]:
    """Retorna (indice do dispositivo de saida padrao, numero de canais dele) -
    grava-lo como INPUT com WasapiSettings(loopback=True) captura o que esta
    tocando no computador, sem precisar de driver extra (tipo "Stereo Mix")."""
    hostapi = sd.query_hostapis(_wasapi_hostapi_index(sd))
    device_index = hostapi["default_output_device"]
    if device_index < 0:
        raise RuntimeError(
            "Nenhuma saida de audio padrao encontrada (WASAPI). Confira em "
            "Painel de Controle > Som > Reprodução se existe um dispositivo "
            "marcado como padrão."
        )
    channels = sd.query_devices(device_index)["max_output_channels"] or 2
    return device_index, channels


class RecordingSession:
    """Grava, cada uma se configurada, a trilha do microfone e/ou a trilha
    de loopback do sistema, em threads separadas, ate stop() ser chamado.
    O modo Aula, por exemplo, so grava a trilha de sistema (mic_path=None) -
    voce esta assistindo, nao falando."""

    def __init__(self, mic_path: Optional[Path], system_path: Optional[Path]):
        self.mic_path = mic_path
        self.system_path = system_path
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._mic_frames: list = []
        self._system_frames: list = []
        self._error: Optional[Exception] = None

    def start(self) -> None:
        if self.mic_path is not None:
            self._threads.append(threading.Thread(target=self._run_mic, daemon=True))
        if self.system_path is not None:
            self._threads.append(threading.Thread(target=self._run_system, daemon=True))
        for t in self._threads:
            t.start()

    def _run_mic(self) -> None:
        try:
            import sounddevice as sd

            device_index = _default_input_device(sd)
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                device=device_index,
            ) as stream:
                while not self._stop_event.is_set():
                    data, _overflowed = stream.read(CHUNK_FRAMES)
                    self._mic_frames.append(data)
        except Exception as exc:  # noqa: BLE001
            self._error = exc

    def _run_system(self) -> None:
        try:
            import sounddevice as sd

            device_index, device_channels = _default_loopback_device(sd)
            extra_settings = sd.WasapiSettings(loopback=True)
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=device_channels,
                dtype="float32",
                device=device_index,
                extra_settings=extra_settings,
            ) as stream:
                while not self._stop_event.is_set():
                    data, _overflowed = stream.read(CHUNK_FRAMES)
                    self._system_frames.append(data)
        except Exception as exc:  # noqa: BLE001
            self._error = exc

    def stop(self) -> tuple[Optional[Path], Optional[Path]]:
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=5)
        if self._error is not None:
            raise self._error

        mic_path = None
        if self.mic_path is not None:
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
        data = np.zeros((0, 1), dtype="float32")
    # A trilha de sistema pode vir com mais de 1 canal (o loopback reflete o
    # numero de canais da saida, normalmente estereo) - mixa pra mono aqui,
    # ja que a transcricao nao precisa de estereo e isso mantem os dois
    # arquivos (mic/sistema) no mesmo formato simples.
    if data.ndim == 2 and data.shape[1] > 1:
        data = data.mean(axis=1, keepdims=True)
    pcm16 = np.clip(data * 32767, -32768, 32767).astype("int16")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm16.tobytes())
    return path


def start_capture(mic_path: Optional[Path], system_path: Optional[Path]) -> RecordingSession:
    session = RecordingSession(mic_path, system_path)
    session.start()
    return session
