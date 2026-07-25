"""Icone na bandeja do sistema: mostra que o listener esta ativo, muda de
cor enquanto uma gravacao esta em andamento, e permite encerrar pelo menu -
sem isso, a unica forma de saber que o programa esta rodando era a janela
do terminal aberta."""
from __future__ import annotations

_IDLE_COLOR = "#2c7be5"
_RECORDING_COLOR = "#c0392b"


def _make_image(color: str):
    from PIL import Image, ImageDraw

    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((6, 6, size - 6, size - 6), fill=color)
    return image


class TrayIcon:
    def __init__(self, title: str = "Hellena Capturas"):
        import pystray

        self._pystray = pystray
        self._icon = pystray.Icon(
            "hellena-capturas",
            _make_image(_IDLE_COLOR),
            title,
            menu=pystray.Menu(
                pystray.MenuItem(title, None, enabled=False),
                pystray.MenuItem("Sair", self._handle_exit),
            ),
        )

    def _handle_exit(self, icon, item) -> None:
        icon.stop()

    def set_recording(self, recording: bool) -> None:
        self._icon.icon = _make_image(_RECORDING_COLOR if recording else _IDLE_COLOR)

    def run(self) -> None:
        """Bloqueia ate o usuario clicar em 'Sair' no menu do icone."""
        self._icon.run()

    def stop(self) -> None:
        self._icon.stop()
