"""Aciona um modo de captura sem usar o atalho de teclado - simula o
pressionamento do hotkey configurado, pra quem preferir clicar num icone
no Desktop em vez de decorar Ctrl+Alt+X. So funciona com o listener ja
rodando (mesma logica de sempre: aperta uma vez pra comecar, de novo pra
parar).

Uso:
  python -m voice_capture.desktop.trigger idea
  python -m voice_capture.desktop.trigger meeting
  python -m voice_capture.desktop.trigger therapy
"""
from __future__ import annotations

import sys
from typing import Callable

from ..config import Config, load_config
from .modes import CaptureMode, build_modes

VALID_MODE_KEYS = ("idea", "meeting", "therapy")


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


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_MODE_KEYS:
        print(f"Uso: python -m voice_capture.desktop.trigger {'|'.join(VALID_MODE_KEYS)}")
        sys.exit(1)

    config = load_config()
    mode = trigger_mode(sys.argv[1], config)
    print(f"Atalho de '{mode.label}' acionado ({mode.hotkey}).")


if __name__ == "__main__":
    main()
