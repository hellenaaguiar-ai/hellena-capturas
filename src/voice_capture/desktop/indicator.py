"""Indicador visual de gravacao em andamento: uma janela pequena, sem
borda, sempre no topo, num canto da tela - fica visivel do inicio ao fim
da gravacao, para nao depender so de uma notificacao que passa rapido."""
from __future__ import annotations

import threading


class RecordingIndicator:
    def __init__(self, text: str):
        self._text = text
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.attributes("-alpha", 0.92)
        except Exception:  # noqa: BLE001 - alpha nem sempre suportado, nao e critico
            pass

        label = tk.Label(
            root,
            text=self._text,
            bg="#c0392b",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            padx=16,
            pady=8,
        )
        label.pack()

        root.update_idletasks()
        width, height = root.winfo_width(), root.winfo_height()
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        x = screen_w - width - 24
        y = screen_h - height - 60
        root.geometry(f"{width}x{height}+{x}+{y}")

        def check_stop() -> None:
            if self._stop_event.is_set():
                root.destroy()
            else:
                root.after(150, check_stop)

        root.after(150, check_stop)
        root.mainloop()
