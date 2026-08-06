"""Captura de audio no desktop via PyAudioWPatch: microfone e, opcionalmente,
uma segunda trilha com o audio que esta tocando no computador (loopback
WASAPI), para separar "voce" de "outra pessoa" sem precisar de diarizacao.

Historico de bibliotecas (2 trocas ate chegar aqui, cada uma por um motivo
real encontrado em producao):
1. `soundcard` - assume que todo driver de audio do Windows relata o
   formato WAVEFORMATEXTENSIBLE; em drivers que nao relatam isso a
   gravacao falhava com AssertionError sem mensagem, sem nenhuma
   configuracao do Windows resolvendo.
2. `sounddevice` - resolveu o problema acima, mas seu `WasapiSettings`
   nunca teve (em nenhuma versao) um parametro de loopback de verdade;
   isso era uma suposicao errada, nao uma limitacao de versao.
3. `pyaudiowpatch` (atual) - fork do PyAudio com um PortAudio compilado
   com patch especifico pra expor dispositivos de loopback WASAPI de
   verdade (usado pelo Audacity e outros). Documentado e testado
   especificamente para este caso de uso.

Dependencia pesada (pyaudiowpatch) e importada so na hora de gravar, nao
no import do modulo - o resto do pacote (modos, pipeline, markdown)
continua testavel sem hardware de audio.
"""
from __future__ import annotations

import threading
import wave
from pathlib import Path
from typing import Optional

SAMPLE_RATE = 48000  # usado so como fallback, se o dispositivo nao informar o proprio
CHUNK_FRAMES = 4800  # 100ms a 48kHz, mantem o stop responsivo


def _wasapi_host_api_info(pyaudio_module, pyaudio_instance) -> dict:
    try:
        return pyaudio_instance.get_host_api_info_by_type(pyaudio_module.paWASAPI)
    except OSError as exc:
        raise RuntimeError(
            "WASAPI nao disponivel neste computador - a captura de audio no "
            "desktop so foi testada no Windows."
        ) from exc


def _default_mic_device(pyaudio_module, pyaudio_instance) -> dict:
    wasapi_info = _wasapi_host_api_info(pyaudio_module, pyaudio_instance)
    index = wasapi_info.get("defaultInputDevice", -1)
    if index is None or index < 0:
        raise RuntimeError(
            "Nenhum microfone padrao encontrado (WASAPI). Confira em Painel "
            "de Controle > Som > Gravação se existe um dispositivo marcado "
            "como padrão."
        )
    return pyaudio_instance.get_device_info_by_index(index)


def _default_loopback_device(pyaudio_module, pyaudio_instance) -> dict:
    """Retorna as infos do dispositivo de loopback equivalente a saida de
    audio padrao - grava-lo como INPUT captura o que esta tocando no
    computador, sem precisar de driver extra (tipo "Stereo Mix"). Mesma
    logica do exemplo oficial do pyaudiowpatch."""
    wasapi_info = _wasapi_host_api_info(pyaudio_module, pyaudio_instance)
    output_index = wasapi_info.get("defaultOutputDevice", -1)
    if output_index is None or output_index < 0:
        raise RuntimeError(
            "Nenhuma saida de audio padrao encontrada (WASAPI). Confira em "
            "Painel de Controle > Som > Reprodução se existe um dispositivo "
            "marcado como padrão."
        )
    default_speakers = pyaudio_instance.get_device_info_by_index(output_index)
    if default_speakers.get("isLoopbackDevice"):
        return default_speakers

    for loopback in pyaudio_instance.get_loopback_device_info_generator():
        if default_speakers["name"] in loopback["name"]:
            return loopback

    raise RuntimeError(
        "Nao encontrei um dispositivo de loopback correspondente a saida de "
        f"audio padrao ('{default_speakers.get('name', '?')}'). Rode "
        "'.venv\\Scripts\\python.exe -m pyaudiowpatch' no terminal pra listar "
        "os dispositivos disponiveis."
    )


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
        self._mic_frames: list[bytes] = []
        self._system_frames: list[bytes] = []
        self._mic_format: tuple[int, int] = (1, SAMPLE_RATE)  # (canais, taxa)
        self._system_format: tuple[int, int] = (2, SAMPLE_RATE)
        self._error: Optional[Exception] = None

    def start(self) -> None:
        if self.mic_path is not None:
            self._threads.append(threading.Thread(target=self._run_mic, daemon=True))
        if self.system_path is not None:
            self._threads.append(threading.Thread(target=self._run_system, daemon=True))
        for t in self._threads:
            t.start()

    def _record(self, device_info: dict, frames: list[bytes], pyaudio, p) -> tuple[int, int]:
        channels = int(device_info["maxInputChannels"]) or 1
        rate = int(device_info["defaultSampleRate"]) or SAMPLE_RATE
        stream = p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_info["index"],
            frames_per_buffer=CHUNK_FRAMES,
        )
        try:
            while not self._stop_event.is_set():
                frames.append(stream.read(CHUNK_FRAMES, exception_on_overflow=False))
        finally:
            stream.stop_stream()
            stream.close()
        return channels, rate

    def _run_mic(self) -> None:
        try:
            import pyaudiowpatch as pyaudio

            with pyaudio.PyAudio() as p:
                device_info = _default_mic_device(pyaudio, p)
                self._mic_format = self._record(device_info, self._mic_frames, pyaudio, p)
        except Exception as exc:  # noqa: BLE001
            self._error = exc

    def _run_system(self) -> None:
        try:
            import pyaudiowpatch as pyaudio

            with pyaudio.PyAudio() as p:
                device_info = _default_loopback_device(pyaudio, p)
                self._system_format = self._record(device_info, self._system_frames, pyaudio, p)
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
            channels, rate = self._mic_format
            mic_path = _write_wav(self.mic_path, self._mic_frames, channels, rate)
        system_path = None
        if self.system_path is not None:
            channels, rate = self._system_format
            system_path = _write_wav(self.system_path, self._system_frames, channels, rate)
        return mic_path, system_path


def _write_wav(path: Path, frames: list[bytes], channels: int, sample_rate: int) -> Path:
    """PyAudioWPatch ja entrega os frames como bytes PCM16 (format=paInt16),
    entao so precisamos concatenar e escrever - sem numpy, sem conversao."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # paInt16 = 2 bytes por amostra
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
    return path


def start_capture(mic_path: Optional[Path], system_path: Optional[Path]) -> RecordingSession:
    session = RecordingSession(mic_path, system_path)
    session.start()
    return session
