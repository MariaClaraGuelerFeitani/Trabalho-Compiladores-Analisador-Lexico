
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from ..config import COLOR_CONSOLE_BACKGROUND, COLOR_CONSOLE_FOREGROUND, monospace_font


class ConsoleView(QPlainTextEdit):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)
        self._background = COLOR_CONSOLE_BACKGROUND
        self._foreground = COLOR_CONSOLE_FOREGROUND
        self.apply_font("", 0)
        self._restyle()

    def apply_font(self, family: str, size: int) -> None:
        self.setFont(monospace_font(family, size))

    def apply_colors(self, background: str, foreground: str) -> None:
        self._background = background or COLOR_CONSOLE_BACKGROUND
        self._foreground = foreground or COLOR_CONSOLE_FOREGROUND
        self._restyle()

    def _restyle(self) -> None:
        background = QColor(self._background)
        if background.name().lower() == self._foreground.lower():
            self._foreground = "#ffffff" if background.lightness() < 140 else "#000000"
        self.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {background.name()};"
            f" color: {self._foreground}; }}"
        )

    def append_line(self, text: str) -> None:
        self.appendPlainText(text)

    def clear_output(self) -> None:
        self.clear()
