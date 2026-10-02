
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .config import LANGUAGE_NAME
from .main_window import MainWindow
from .parser.service import AnaliseService
from .services.lexer_service import LexerService
from .theme import remember_system_appearance


def build_lexer() -> LexerService:
    """Serviço de análise mostrado no IDE: léxico e sintático encadeados."""
    return AnaliseService()


def create_window(
    lexer: LexerService | None = None,
    settings_path: Path | None = None,
) -> MainWindow:
    return MainWindow(lexer if lexer is not None else build_lexer(), settings_path)


def run(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(LANGUAGE_NAME)
    app.setApplicationDisplayName(f"{LANGUAGE_NAME} - IDE")
    app.setOrganizationName("Trabalho de Compiladores")

    remember_system_appearance(app)

    window = create_window()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
