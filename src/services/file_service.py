
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

from ..config import SOURCE_EXTENSION, SOURCE_FILE_FILTER

UNSAVED_TITLE = "sem titulo"


class FileService:

    @staticmethod
    def open_dialog(parent: QWidget) -> str | None:
        path, _ = QFileDialog.getOpenFileName(parent, "Abrir programa", "", SOURCE_FILE_FILTER)
        return path or None

    @staticmethod
    def save_dialog(parent: QWidget, suggested_path: str = "") -> str | None:
        if not suggested_path:
            suggested_path = f"programa.{SOURCE_EXTENSION}"
        path, _ = QFileDialog.getSaveFileName(parent, "Salvar programa", suggested_path, SOURCE_FILE_FILTER)
        return path or None

    @staticmethod
    def read(path: str) -> str:
        return Path(path).read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def write(path: str, content: str) -> None:
        Path(path).write_text(content, encoding="utf-8")
