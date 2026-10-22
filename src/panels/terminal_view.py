"""Console interativo embutido na IDE.

Diferente do console novo do Windows — onde os bytes passam pela codepage do
OEM e palavras acentuadas saem trocadas — aqui stdin e stdout são pipes e o
texto circula em UTF-8, então `readln('José')` e `writeln('até')` chegam
inteiros nos dois sentidos.

O widget dirige toda a edição pelo `keyPressEvent`: o que já foi impresso não
pode ser apagado, só a linha que está sendo digitada, exatamente como um
terminal de verdade.
"""

from __future__ import annotations

import codecs
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QColor, QKeyEvent, QTextCursor
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QWidget

from ..config import COLOR_CONSOLE_BACKGROUND, COLOR_CONSOLE_FOREGROUND, monospace_font


class TerminalView(QPlainTextEdit):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setUndoRedoEnabled(False)
        self.setAcceptDrops(False)
        self.setReadOnly(False)
        self.setMaximumBlockCount(5000)
        self._processo: QProcess | None = None
        self._linha = ""
        self._decodificador = codecs.getincrementaldecoder("utf-8")("replace")
        self._background = COLOR_CONSOLE_BACKGROUND
        self._foreground = COLOR_CONSOLE_FOREGROUND
        self.apply_font("", 0)
        self._restyle()

    # --- Aparência (a mesma do ConsoleView) ----------------------------------

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

    # --- Processo -------------------------------------------------------------

    @property
    def em_execucao(self) -> bool:
        return self._processo is not None

    def iniciar(self, exe: Path) -> None:
        """Limpa o terminal e roda `exe` com pipes; texto entra e sai em UTF-8."""
        self.parar()
        self.clear()
        self._linha = ""
        self._decodificador = codecs.getincrementaldecoder("utf-8")("replace")
        processo = QProcess(self)
        processo.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        processo.readyReadStandardOutput.connect(self._receber)
        processo.finished.connect(self._terminou)
        processo.errorOccurred.connect(self._falhou)
        self._processo = processo
        processo.start(str(exe), [])

    def parar(self) -> None:
        """Mata o programa em execução, se houver."""
        if self._processo is not None:
            processo = self._processo
            self._processo = None
            processo.kill()
            processo.waitForFinished(2000)

    def _receber(self) -> None:
        if self._processo is None:
            return
        dados = bytes(self._processo.readAllStandardOutput())
        if dados:
            self._escrever(self._decodificador.decode(dados))

    def _terminou(self, codigo: int, _status: QProcess.ExitStatus) -> None:
        self._processo = None
        self._escrever(f"\n[programa terminado com codigo {codigo}]\n")

    def _falhou(self, erro: QProcess.ProcessError) -> None:
        if erro != QProcess.ProcessError.FailedToStart:
            return
        motivo = self._processo.errorString() if self._processo is not None else ""
        self._processo = None
        self._escrever(f"\n[nao foi possivel iniciar o programa: {motivo}]\n")

    # --- Digitação -------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if ctrl and event.key() == Qt.Key.Key_C:
            super().keyPressEvent(event)  # copiar a seleção
            return
        if ctrl and event.key() == Qt.Key.Key_V:
            self._colar()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._processo is not None:
                self._enviar_linha()
            return
        if event.key() == Qt.Key.Key_Backspace:
            if self._linha:
                self._linha = self._linha[:-1]
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.deletePreviousChar()
            return
        texto = event.text()
        if texto and texto.isprintable() and self._processo is not None:
            self._linha += texto
            self._escrever(texto)
            return
        # Qualquer outra tecla é ignorada: a saída impressa não se edita.
        event.ignore()

    def contextMenuEvent(self, event) -> None:
        # O menu de contexto cortaria/colaria no meio do que já foi impresso.
        event.ignore()

    def _colar(self) -> None:
        texto = QApplication.clipboard().text()
        if not texto or self._processo is None:
            return
        partes = texto.replace("\r\n", "\n").split("\n")
        for parte in partes[:-1]:
            self._linha += parte
            self._enviar_linha()
        if partes[-1]:
            self._linha += partes[-1]
            self._escrever(partes[-1])

    def _enviar_linha(self) -> None:
        linha, self._linha = self._linha, ""
        self._escrever("\n")
        if self._processo is not None:
            self._processo.write((linha + "\n").encode("utf-8"))

    def _escrever(self, texto: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.insertPlainText(texto)
        self.ensureCursorVisible()


__all__ = ["TerminalView"]
