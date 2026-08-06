"""Indicador visual persistente: um badge pequeno, sem borda, sempre no
topo, no canto da tela - fica visivel o tempo todo enquanto o listener
esta rodando (nao so durante gravacao), pra voce saber de relance que ele
esta ativo sem precisar abrir a bandeja do sistema. Durante uma gravacao,
o mesmo badge cresce e fica vermelho; ao parar, volta ao estado discreto
(nunca some de vez enquanto o listener estiver de pe).

Cria UM UNICO Tk() e roda o mainloop dele numa UNICA thread dedicada, viva
por todo o tempo de vida do listener - cada gravacao so manda um comando
pra essa mesma janela, em vez de criar/destruir um Tk() novo por gravacao.
Isso importa: criar varios interpretadores Tcl em threads diferentes ao
longo da vida do processo derrubava o listener inteiro no Windows com
"Tcl_AsyncDelete: async handler deleted by the wrong thread" - que nao e
um aviso, e um erro fatal do Tcl (mata o processo, incluindo qualquer
gravacao/transcricao em andamento). A primeira versao criava um Tk() por
gravacao, numa thread nova a cada vez, e batia nisso direto.
"""
from __future__ import annotations

import queue
import threading
from typing import Optional

IDLE_TEXT = "🎙️ Hellena Capturas — ouvindo"
IDLE_STYLE = {"bg": "#34495e", "font": ("Segoe UI", 9), "padx": 10, "pady": 5}
ACTIVE_STYLE = {"bg": "#c0392b", "font": ("Segoe UI", 11, "bold"), "padx": 16, "pady": 8}

_command_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
_gui_thread: Optional[threading.Thread] = None
_gui_thread_lock = threading.Lock()


def _ensure_gui_thread() -> None:
    global _gui_thread
    with _gui_thread_lock:
        if _gui_thread is None or not _gui_thread.is_alive():
            _gui_thread = threading.Thread(target=_run_gui, daemon=True)
            _gui_thread.start()


def _run_gui() -> None:
    import tkinter as tk

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.90)
    except Exception:  # noqa: BLE001 - alpha nem sempre suportado, nao e critico
        pass

    label = tk.Label(root, text=IDLE_TEXT, fg="white", **IDLE_STYLE)
    label.pack()

    def reposition() -> None:
        root.update_idletasks()
        width, height = root.winfo_width(), root.winfo_height()
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        x = screen_w - width - 24
        y = screen_h - height - 60
        root.geometry(f"{width}x{height}+{x}+{y}")

    def set_idle() -> None:
        label.config(text=IDLE_TEXT, **IDLE_STYLE)
        reposition()

    def set_active(text: str) -> None:
        label.config(text=text, **ACTIVE_STYLE)
        reposition()

    set_idle()
    root.deiconify()  # ja comeca visivel - o listener esta rodando desde ja

    def poll_queue() -> None:
        try:
            while True:
                action, text = _command_queue.get_nowait()
                if action == "active":
                    set_active(text)
                elif action == "idle":
                    set_idle()
                elif action == "close":
                    root.destroy()
                    return
        except queue.Empty:
            pass
        root.after(100, poll_queue)

    root.after(100, poll_queue)
    root.mainloop()


def show_idle_badge() -> None:
    """Chame uma vez, quando o listener terminar de registrar os atalhos -
    deixa visivel um badge pequeno e discreto confirmando que ele esta
    rodando, sem precisar abrir a bandeja do sistema pra saber."""
    _ensure_gui_thread()
    _command_queue.put(("idle", ""))


def close_badge() -> None:
    """Chame ao encerrar o listener - fecha a janela de vez."""
    _command_queue.put(("close", ""))


class RecordingIndicator:
    """Uma gravacao chama start()/stop() - por baixo, so manda um comando
    pra fila da janela unica (thread-safe), nunca mexe no Tk diretamente.
    stop() nao esconde o badge, so devolve ele ao estado discreto (idle) -
    o listener continua "visivelmente" rodando."""

    def __init__(self, text: str):
        self._text = text

    def start(self) -> None:
        _ensure_gui_thread()
        _command_queue.put(("active", self._text))

    def stop(self) -> None:
        _command_queue.put(("idle", ""))
