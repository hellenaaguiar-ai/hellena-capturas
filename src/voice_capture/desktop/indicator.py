"""Indicador visual de gravacao em andamento: uma janela pequena, sem
borda, sempre no topo, num canto da tela - fica visivel do inicio ao fim
da gravacao, para nao depender so de uma notificacao que passa rapido.

Cria UM UNICO Tk() e roda o mainloop dele numa UNICA thread dedicada, viva
por todo o tempo de vida do listener - cada gravacao so manda "mostra" ou
"esconde" pra essa mesma janela, em vez de criar/destruir um Tk() novo por
gravacao. Isso importa: criar varios interpretadores Tcl em threads
diferentes ao longo da vida do processo derrubava o listener inteiro no
Windows com "Tcl_AsyncDelete: async handler deleted by the wrong thread"
- que nao e um aviso, e um erro fatal do Tcl (mata o processo, incluindo
qualquer gravacao/transcricao em andamento). A primeira versao criava um
Tk() por gravacao, numa thread nova a cada vez, e batia nisso direto.
"""
from __future__ import annotations

import queue
import threading
from typing import Optional

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
    root.withdraw()  # comeca escondida - so aparece quando uma gravacao pedir
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.92)
    except Exception:  # noqa: BLE001 - alpha nem sempre suportado, nao e critico
        pass

    label = tk.Label(
        root,
        bg="#c0392b",
        fg="white",
        font=("Segoe UI", 11, "bold"),
        padx=16,
        pady=8,
    )
    label.pack()

    def poll_queue() -> None:
        try:
            while True:
                action, text = _command_queue.get_nowait()
                if action == "show":
                    label.config(text=text)
                    root.update_idletasks()
                    width, height = root.winfo_width(), root.winfo_height()
                    screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
                    x = screen_w - width - 24
                    y = screen_h - height - 60
                    root.geometry(f"{width}x{height}+{x}+{y}")
                    root.deiconify()
                elif action == "hide":
                    root.withdraw()
        except queue.Empty:
            pass
        root.after(100, poll_queue)

    root.after(100, poll_queue)
    root.mainloop()


class RecordingIndicator:
    """Uma gravacao chama start()/stop() - por baixo, so manda um comando
    pra fila da janela unica (thread-safe), nunca mexe no Tk diretamente."""

    def __init__(self, text: str):
        self._text = text

    def start(self) -> None:
        _ensure_gui_thread()
        _command_queue.put(("show", self._text))

    def stop(self) -> None:
        _command_queue.put(("hide", ""))
