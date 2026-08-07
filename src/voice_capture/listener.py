"""Processo de fundo: registra os atalhos globais dos 3 modos, alterna
gravacao on/off, e dispara o pipeline correspondente ao soltar.

Uso:
  python -m voice_capture.listener

Pensado para rodar continuamente, iniciado com o Windows (ver
docs/desktop-capture.md e docs/windows-setup.md para o atalho de
autostart). Cada gravacao processada roda numa thread separada, protegida
por um lock, para nao competir por CPU com o Whisper local nem corromper o
estado se duas gravacoes terminarem quase juntas.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import pipeline
from .config import Config, load_config
from .desktop import modes as modes_module
from .desktop.audio_capture import RecordingSession, start_capture
from .desktop.indicator import RecordingIndicator, close_badge
from .desktop.singleton import acquire_single_instance_lock
from .desktop.modes import CaptureMode, NOTE_TYPE_IDEA
from .desktop.tray import TrayIcon
from .desktop_pipeline import process_desktop_recording
from .errors_note import write_errors_note
from .run import setup_logging
from .state import StateStore

_pipeline_lock = threading.Lock()
_active_sessions: dict[str, tuple[RecordingSession, datetime, RecordingIndicator]] = {}
_tray_icon: Optional[TrayIcon] = None


def _update_tray_state() -> None:
    if _tray_icon is not None:
        _tray_icon.set_recording(bool(_active_sessions))


def _notify(title: str, message: str) -> None:
    try:
        from plyer import notification

        notification.notify(title=title, message=message, timeout=5)
    except Exception:  # noqa: BLE001 - notificacao e best-effort, nunca deve derrubar o listener
        logging.info("%s: %s", title, message)


def _paths_for(config: Config, mode: CaptureMode, timestamp: str) -> tuple[Optional[Path], Optional[Path]]:
    mic_path = (
        config.desktop_audio_dir / f"{mode.key}-mic-{timestamp}.wav" if mode.capture_mic else None
    )
    system_path = (
        config.desktop_audio_dir / f"{mode.key}-system-{timestamp}.wav"
        if mode.capture_system_audio
        else None
    )
    return mic_path, system_path


def _process_in_background(
    config: Config,
    mode: CaptureMode,
    mic_path: Optional[Path],
    system_path: Optional[Path],
    recorded_at: datetime,
    indicator: RecordingIndicator,
) -> None:
    try:
        with _pipeline_lock:
            state = StateStore(config.state_file)
            try:
                if mode.note_type == NOTE_TYPE_IDEA:
                    result = pipeline.process_item(mic_path, config, state)
                else:
                    result = process_desktop_recording(mode, mic_path, system_path, recorded_at, config, state)
            except Exception as exc:  # noqa: BLE001
                logging.exception("Falha inesperada processando modo %s", mode.key)
                _notify("Erro na captura", f"{mode.label}: {exc}")
                return

            write_errors_note(config.error_note_path, state.errors())

            if result == "done":
                _notify("Captura concluída", f"{mode.label} processado e salvo no Obsidian.")
            elif result == "skipped-duplicate":
                logging.info("Gravacao de %s ja processada (duplicada)", mode.key)
            else:
                _notify("Falha na captura", f"{mode.label} falhou — veja _Erros de captura.md no vault.")
    finally:
        # So esconde o indicador quando TUDO (transcricao + IA + nota) de
        # fato terminou - sucesso, duplicata ou erro. Enquanto isso, fica
        # visivel em "Processando", pra nao parecer que sumiu no vazio.
        indicator.hide()


def _safe_toggle(config: Config, mode: CaptureMode) -> None:
    """Wrapper de seguranca: garante que qualquer excecao dentro do callback
    do atalho apareca no log, em vez de ser engolida silenciosamente pela
    thread interna da biblioteca `keyboard`."""
    logging.info("Atalho do modo '%s' acionado.", mode.label)
    try:
        _toggle(config, mode)
    except Exception:
        logging.exception("Erro inesperado ao processar o atalho do modo '%s'.", mode.key)


def _stop_mode(config: Config, mode: CaptureMode) -> None:
    """Encerra a gravacao ativa do modo indicado e dispara o processamento
    em segundo plano. Assume que mode.key esta em _active_sessions."""
    session, recorded_at, indicator = _active_sessions.pop(mode.key)
    indicator.set_processing()
    _update_tray_state()
    try:
        mic_path, system_path = session.stop()
    except Exception as exc:  # noqa: BLE001
        logging.exception("Falha ao parar gravacao do modo %s", mode.key)
        _notify("Erro na gravação", f"{mode.label}: {exc}")
        indicator.hide()
        return

    _notify("Processando...", f"{mode.label} — transcrevendo e estruturando.")
    thread = threading.Thread(
        target=_process_in_background,
        args=(config, mode, mic_path, system_path, recorded_at, indicator),
        daemon=True,
    )
    thread.start()


def _safe_stop_any(config: Config) -> None:
    """Wrapper de seguranca do atalho global de 'parar' (equivalente ao
    _safe_toggle dos outros modos)."""
    logging.info("Atalho de 'Parar' acionado.")
    try:
        _stop_any(config)
    except Exception:
        logging.exception("Erro inesperado ao processar o atalho de 'Parar'.")


def _stop_any(config: Config) -> None:
    """Encerra qualquer gravacao em andamento, seja ela qual modo for - pra
    quem nao lembra em qual dos tres icones/atalhos comecou a gravar.
    Sem efeito se nada estiver gravando."""
    if not _active_sessions:
        _notify("Nada gravando", "Nenhuma gravação em andamento no momento.")
        return

    active_modes = modes_module.build_modes(config)
    modes_by_key = {m.key: m for m in active_modes}
    for mode_key in list(_active_sessions.keys()):
        mode = modes_by_key.get(mode_key)
        if mode is None:
            continue
        _stop_mode(config, mode)


def _toggle(config: Config, mode: CaptureMode) -> None:
    if mode.key in _active_sessions:
        _stop_mode(config, mode)
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    mic_path, system_path = _paths_for(config, mode, timestamp)
    try:
        session = start_capture(mic_path, system_path)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Falha ao iniciar gravacao do modo %s", mode.key)
        _notify("Erro ao gravar", f"{mode.label}: {exc}")
        return

    indicator = RecordingIndicator(mode.label)
    indicator.start()
    _active_sessions[mode.key] = (session, datetime.now().astimezone(), indicator)
    _update_tray_state()
    _notify(
        "Gravando...",
        f"{mode.label} — aperte {mode.hotkey} de novo (ou {config.hotkeys['stop']}) para parar.",
    )


def main() -> None:
    global _tray_icon

    config = load_config()
    config.ensure_dirs()
    setup_logging(config)

    # So uma instancia por vez - clicar no icone "Iniciar Listener" sem
    # saber se ja tem um rodando nao pode resultar em dois processos
    # competindo pelos mesmos atalhos globais.
    import os

    lock_path = config.data_dir / "listener.pid"
    if not acquire_single_instance_lock(lock_path, os.getpid()):
        logging.info("Ja existe um listener rodando - encerrando esta segunda instancia.")
        return

    import keyboard

    # Importa o pyaudiowpatch uma unica vez aqui, nesta thread, ANTES de
    # qualquer gravacao - evita que duas threads de gravacao (mic + sistema)
    # inicializem o PortAudio pela primeira vez ao mesmo tempo.
    import pyaudiowpatch  # noqa: F401

    # suppress=True bloqueia a tecla na origem (nao deixa vazar pro
    # aplicativo que estiver em foco nem pro resto do Windows) - alem de
    # evitar side-effects tipo o Caps Lock ligando/desligando sozinho nos
    # atalhos que usam ele, tambem impede que o Ctrl+Espaco "vaze" pra
    # dentro de outro programa (ex: autocompletar do VS Code) enquanto o
    # listener esta rodando.
    active_modes = modes_module.build_modes(config)
    for mode in active_modes:
        keyboard.add_hotkey(mode.hotkey, lambda m=mode: _safe_toggle(config, m), suppress=True)
        logging.info("Modo '%s' registrado em %s -> %s", mode.label, mode.hotkey, mode.vault_dir)

    stop_hotkey = config.hotkeys["stop"]
    keyboard.add_hotkey(stop_hotkey, lambda: _safe_stop_any(config), suppress=True)
    logging.info("Atalho 'Parar' (qualquer modo) registrado em %s", stop_hotkey)

    # Atalho extra pro MESMO modo "idea" (mesmo mode.key, mesma pasta,
    # mesmo processamento) - so uma segunda tecla pra quem quiser separar
    # mentalmente "tive uma ideia" de "preciso desabafar/refletir", ja que
    # a IA classifica automaticamente o tipo de conteudo de qualquer jeito.
    idea_mode = next((m for m in active_modes if m.key == "idea"), None)
    reflection_hotkey = config.hotkeys.get("reflection")
    if idea_mode is not None and reflection_hotkey:
        keyboard.add_hotkey(reflection_hotkey, lambda: _safe_toggle(config, idea_mode), suppress=True)
        logging.info("Atalho alternativo para '%s' (reflexão/desabafo) registrado em %s", idea_mode.label, reflection_hotkey)

    logging.info("Listener ativo. Use o icone na bandeja do sistema para encerrar.")

    # keyboard.wait() bloqueia para sempre - roda em segundo plano para o
    # icone da bandeja poder ocupar a thread principal (necessario para
    # funcionar de forma confiavel).
    threading.Thread(target=keyboard.wait, daemon=True).start()

    _tray_icon = TrayIcon()
    _tray_icon.run()  # bloqueia ate clicar em "Sair" no menu do icone
    close_badge()
    logging.info("Encerrado pelo icone da bandeja.")


if __name__ == "__main__":
    main()
