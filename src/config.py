
from __future__ import annotations

from PySide6.QtGui import QFont

LANGUAGE_NAME = "Trabalho de Compiladores"

SOURCE_EXTENSION = "pas"

SOURCE_FILE_FILTER = f"Fonte {LANGUAGE_NAME} (*.{SOURCE_EXTENSION});;Todos os arquivos (*)"

ANALYSIS_DEBOUNCE_MS = 250

MAX_IDENTIFIER_LENGTH = 15

EDITOR_FONT_FAMILY = "Consolas"
EDITOR_FONT_FALLBACK = "Courier New"
EDITOR_FONT_SIZE = 11

COLOR_CONSOLE_BACKGROUND = "#1e1e1e"
COLOR_CONSOLE_FOREGROUND = "#d4d4d4"

NEW_FILE_TEMPLATE = (
    "programa {nome};\n"
    "\n"
    "begin\n"
    "end.\n"
)


def monospace_font(family: str = "", size: int = 0) -> QFont:
    font = QFont(family or EDITOR_FONT_FAMILY, size or EDITOR_FONT_SIZE)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font
