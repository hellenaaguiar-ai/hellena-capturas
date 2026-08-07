"""Indicador visual de atividade: uma janela pequena, sem borda, sempre no
topo, no canto da tela. So aparece quando tem algo de fato acontecendo -
gravando (vermelho) ou processando/transcrevendo (laranja) - e some
sozinha assim que termina. Fica escondida o resto do tempo, pra nao virar
poluicao visual permanente.

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

RECORDING_STYLE = {"bg": "#c0392b", "font": ("Segoe UI", 11, "bold"), "padx": 16, "pady": 8}
PROCESSING_STYLE = {"bg": "#d68910", "font": ("Segoe UI", 11, "bold"), "padx": 16, "pady": 8}

_command_queue: "queue.Queue[tuple[str, dict, str]]" = queue.Queue()
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
        root.attributes("-alpha", 0.92)
    except Exception:  # noqa: BLE001 - alpha nem sempre suportado, nao e critico
        pass

    label = tk.Label(root, fg="white")
    label.pack()

    def reposition() -> None:
        root.update_idletasks()
        width, height = root.winfo_width(), root.winfo_height()
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        x = screen_w - width - 24
        y = screen_h - height - 60
        root.geometry(f"{width}x{height}+{x}+{y}")

    def hide() -> None:
        # Move pra bem fora da tela em vez de root.withdraw(). Uma janela
        # "withdrawn" no Tkinter as vezes reporta o tamanho errado
        # (menor/cortado) na proxima vez que e mostrada de novo, porque o
        # gerenciador de geometria nao recalculou o tamanho de verdade
        # enquanto ela estava escondida - foi exatamente o que causou a
        # janelinha aparecer cortada/estreita. Mantendo ela sempre
        # "mapeada" (so que fora da area visivel), o tamanho calculado em
        # reposition() sempre reflete o conteudo atual de verdade.
        root.geometry("1x1+-2000+-2000")

    # comeca fora da tela, ja mapeada (nunca usamos withdraw/deiconify)
    hide()
    root.deiconify()

    def poll_queue() -> None:
        try:
            while True:
                action, style, text = _command_queue.get_nowait()
                if action == "show":
                    label.config(text=text, **style)
                    reposition()
                elif action == "hide":
                    hide()
                elif action == "close":
                    root.destroy()
                    return
        except queue.Empty:
            pass
        root.after(100, poll_queue)

    root.after(100, poll_queue)
    root.mainloop()


def close_badge() -> None:
    """Chame ao encerrar o listener - fecha a janela de vez."""
    _command_queue.put(("close", {}, ""))


class RecordingIndicator:
    """Uma gravacao chama start() -> set_processing() -> hide(), na ordem -
    por baixo, so manda comandos pra fila da janela unica (thread-safe),
    nunca mexe no Tk diretamente."""

    def __init__(self, label: str):
        self._label = label

    def start(self) -> None:
        _ensure_gui_thread()
        _command_queue.put(("show", RECORDING_STYLE, f"🔴 Gravando — {self._label}"))

    def set_processing(self) -> None:
        _ensure_gui_thread()
        _command_queue.put(("show", PROCESSING_STYLE, f"⏳ Processando — {self._label}"))

    def hide(self) -> None:
        _command_queue.put(("hide", {}, ""))
