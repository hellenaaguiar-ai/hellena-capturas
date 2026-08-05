"""Aciona um modo de captura (ou o comando de parar) sem usar o atalho de
teclado - simula o pressionamento do hotkey configurado, pra quem preferir
clicar num icone no Desktop em vez de decorar Ctrl+Alt+X. So funciona com
o listener ja rodando.

Cada modo (idea/meeting/therapy/class) alterna: aperta uma vez pra
comecar, aperta o MESMO de novo pra parar. 'stop' e um atalho a parte que
encerra qualquer gravacao em andamento, seja ela qual modo for - pensado
pra quem nao lembra em qual dos quatro cliques comecou a gravar.

Uso:
  python -m voice_capture.desktop.trigger idea
  python -m voice_capture.desktop.trigger meeting
  python -m voice_capture.desktop.trigger therapy
  python -m voice_capture.desktop.trigger class
  python -m voice_capture.desktop.trigger stop
"""
from __future__ import annotations

import sys
from typing import Callable

from ..config import Config, load_config
from .modes import CaptureMode, build_modes

VALID_MODE_KEYS = ("idea", "meeting", "therapy", "class")
STOP_KEY = "stop"
ALL_TRIGGER_KEYS = VALID_MODE_KEYS + (STOP_KEY,)


def trigger_mode(mode_key: str, config: Config, send_keys: Callable[[str], None] | None = None) -> CaptureMode:
    """Simula o pressionamento do hotkey do modo indicado. Retorna o
    CaptureMode acionado, para quem chamar poder confirmar/logar."""
    if mode_key not in VALID_MODE_KEYS:
        raise ValueError(f"Modo desconhecido: {mode_key} (esperado um de {VALID_MODE_KEYS})")

    modes = {m.key: m for m in build_modes(config)}
    mode = modes[mode_key]

    if send_keys is None:
        import keyboard

        send_keys = keyboard.send

    send_keys(mode.hotkey)
    return mode


def trigger_stop(config: Config, send_keys: Callable[[str], None] | None = None) -> str:
    """Simula o pressionamento do hotkey global de 'parar'. Retorna o
    hotkey acionado, para quem chamar poder confirmar/logar."""
    if send_keys is None:
        import keyboard

        send_keys = keyboard.send

    hotkey = config.hotkeys[STOP_KEY]
    send_keys(hotkey)
    return hotkey


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ALL_TRIGGER_KEYS:
        print(f"Uso: python -m voice_capture.desktop.trigger {'|'.join(ALL_TRIGGER_KEYS)}")
        sys.exit(1)

    config = load_config()
    key = sys.argv[1]
    if key == STOP_KEY:
        hotkey = trigger_stop(config)
        print(f"Atalho de 'Parar' acionado ({hotkey}).")
    else:
        mode = trigger_mode(key, config)
        print(f"Atalho de '{mode.label}' acionado ({mode.hotkey}).")


if __name__ == "__main__":
    main()
