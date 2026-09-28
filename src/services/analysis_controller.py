
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from ..config import ANALYSIS_DEBOUNCE_MS
from .lexer_service import AnalysisResult, LexerService


class AnalysisController(QObject):

    result_ready = Signal(object)

    def __init__(self, lexer: LexerService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lexer = lexer
        self._pending_source = ""
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(ANALYSIS_DEBOUNCE_MS)
        self._timer.timeout.connect(self._run)

    @property
    def lexer(self) -> LexerService:
        return self._lexer

    def set_lexer(self, lexer: LexerService) -> None:
        self._lexer = lexer

    def request(self, source: str) -> None:
        self._pending_source = source
        self._timer.start()

    def analyze_now(self, source: str) -> AnalysisResult:
        self._timer.stop()
        result = self._lexer.analyze(source)
        self.result_ready.emit(result)
        return result

    def _run(self) -> None:
        result = self._lexer.analyze(self._pending_source)
        self.result_ready.emit(result)
