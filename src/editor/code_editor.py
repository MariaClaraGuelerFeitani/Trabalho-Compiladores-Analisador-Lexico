
from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, QStringListModel, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QPainter,
    QPalette,
    QPixmap,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)
from PySide6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget

from ..config import monospace_font
from ..services.lexer_service import LexicalError, Token
from ..theme import spec_for
from .highlighter import TokenHighlighter, resolve_colors

LINE_NUMBER_MARGIN = 4
MIN_LINE_NUMBER_DIGITS = 2

CURRENT_LINE_TINT = 0.07
LINE_NUMBER_MUTED = 0.45
LINE_NUMBER_CURRENT = 0.20

ERROR_ON_DARK = "#ff5252"
ERROR_ON_LIGHT = "#c62828"

DEFAULT_BACKGROUND_OPACITY = 15
MIN_BACKGROUND_OPACITY = 0
MAX_BACKGROUND_OPACITY = 100


FIND_HIGHLIGHT_ALPHA = 90

IDENTIFIER_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)


def _base(palette: QPalette) -> QColor:
    return palette.color(QPalette.ColorRole.Base)


def _text(palette: QPalette) -> QColor:
    return palette.color(QPalette.ColorRole.Text)


def _blend(origin: QColor, target: QColor, ratio: float) -> QColor:
    return QColor(
        round(origin.red() + (target.red() - origin.red()) * ratio),
        round(origin.green() + (target.green() - origin.green()) * ratio),
        round(origin.blue() + (target.blue() - origin.blue()) * ratio),
    )


def current_line_color(palette: QPalette) -> QColor:
    return _blend(_base(palette), _text(palette), CURRENT_LINE_TINT)


def line_number_color(palette: QPalette, current: bool) -> QColor:
    return _blend(
        _text(palette),
        _base(palette),
        LINE_NUMBER_CURRENT if current else LINE_NUMBER_MUTED,
    )


def error_color(palette: QPalette, theme: str = "") -> QColor:
    spec = spec_for(theme) if theme else None
    if spec is not None and spec.error:
        return QColor(spec.error)
    return QColor(ERROR_ON_LIGHT if _base(palette).lightness() >= 128 else ERROR_ON_DARK)


class LineNumberArea(QWidget):

    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):

    zoom_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self._error_selections: list[QTextEdit.ExtraSelection] = []
        self._error_list: list[LexicalError] = []
        self._current_line_override: QColor | None = None
        self._error_override: QColor | None = None
        self._theme: str = ""
        self._highlight_overrides: dict[str, QColor] = {}
        self._highlighter = TokenHighlighter(self.document())
        self._background: QPixmap | None = None
        self._background_opacity = DEFAULT_BACKGROUND_OPACITY / 100
        self._cover: QPixmap | None = None
        self._cover_key: tuple[QSize, int] | None = None
        self._find_text = ""
        self._find_sensitive = False
        self._find_selections: list[QTextEdit.ExtraSelection] = []
        self._completer: QCompleter | None = None

        self.setFont(monospace_font())
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setPlaceholderText("Escreva seu codigo aqui.")

        self._configurar_completer()
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._refresh_selections)
        self._update_line_number_width()
        self._apply_highlight_colors()


    def line_number_area_width(self) -> int:
        digits = max(len(str(max(1, self.blockCount()))), MIN_LINE_NUMBER_DIGITS)
        return 2 * LINE_NUMBER_MARGIN + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_width(self) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        contents = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(contents.left(), contents.top(), self.line_number_area_width(), contents.height())
        )

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._line_number_area.update()
            self._error_selections = [
                selection
                for selection in (self._build_error_selection(e) for e in self._error_list)
                if selection is not None
            ]
            self._apply_highlight_colors()
            self._refresh_selections()
            self._repaint_background()

    def paintEvent(self, event) -> None:
        if self._background is not None:
            covering = self._cover_pixmap()
            painter = QPainter(self.viewport())
            try:
                painter.fillRect(
                    self.viewport().rect(), self.palette().brush(QPalette.ColorRole.Base)
                )
                painter.setOpacity(self._background_opacity)
                if covering is not None:
                    painter.drawPixmap(
                        QPoint(
                            -(covering.width() - self.viewport().width()) // 2,
                            -(covering.height() - self.viewport().height()) // 2,
                        ),
                        covering,
                    )
            finally:
                painter.end()
        super().paintEvent(event)

    def _cover_pixmap(self) -> QPixmap | None:
        if self._background is None:
            return None
        area = self.viewport().size()
        chave = (area, self._background.cacheKey())
        if chave != self._cover_key:
            self._cover = self._background.scaled(
                area,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cover_key = chave
        return self._cover

    def _repaint_background(self) -> None:
        self.viewport().update()

    def set_background_image(self, path: str, opacity: int) -> bool:
        self._background_opacity = max(
            MIN_BACKGROUND_OPACITY, min(MAX_BACKGROUND_OPACITY, opacity)
        ) / 100
        pixmap = QPixmap(path) if path else QPixmap()
        self._background = None if pixmap.isNull() else pixmap
        self._cover = None
        self._cover_key = None
        self._repaint_background()
        return self._background is not None

    def has_background_image(self) -> bool:
        return self._background is not None

    # --- Busca e substituicao ----------------------------------------------

    def _flags_de_busca(self, backwards: bool, sensivel: bool) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if backwards:
            flags |= QTextDocument.FindFlag.FindBackward
        if sensivel:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    def find_next(
        self, text: str, backwards: bool = False, sensivel: bool = False
    ) -> bool:
        """Move o cursor para a proxima ocorrencia de `text`, com volta ao inicio."""
        if not text:
            return False
        flags = self._flags_de_busca(backwards, sensivel)
        inicio = self.textCursor()
        if not backwards and inicio.hasSelection():
            inicio.setPosition(inicio.selectionEnd())
        achado = self.document().find(text, inicio, flags)
        if achado.isNull():
            limite = QTextCursor(self.document())
            if backwards:
                limite.movePosition(QTextCursor.MoveOperation.End)
            else:
                limite.movePosition(QTextCursor.MoveOperation.Start)
            achado = self.document().find(text, limite, flags)
        if achado.isNull():
            return False
        self.setTextCursor(achado)
        self.ensureCursorVisible()
        return True

    def highlight_find(self, text: str, sensivel: bool = False) -> None:
        """Realca em amarelo todas as ocorrencias de `text` no documento."""
        self._find_text = text
        self._find_sensitive = sensivel
        self._find_selections = []
        if text:
            flags = self._flags_de_busca(False, sensivel)
            achado = QTextCursor(self.document())
            while True:
                achado = self.document().find(text, achado, flags)
                if achado.isNull():
                    break
                selection = QTextEdit.ExtraSelection()
                cor = QColor(255, 220, 80)
                cor.setAlpha(FIND_HIGHLIGHT_ALPHA)
                selection.format.setBackground(cor)
                selection.cursor = achado
                self._find_selections.append(selection)
        self._refresh_selections()

    def clear_find_highlight(self) -> None:
        self._find_text = ""
        self._find_selections = []
        self._refresh_selections()

    def replace_current(self, busca: str, substituir: str, sensivel: bool = False) -> bool:
        """Substitui a selecao atual (se casar com `busca`); devolve se trocou."""
        cursor = self.textCursor()
        if not busca or not cursor.hasSelection():
            return False
        selecionado = cursor.selectedText()
        if sensivel:
            if selecionado != busca:
                return False
        elif selecionado.lower() != busca.lower():
            return False
        cursor.insertText(substituir)
        return True

    def replace_all(self, busca: str, substituir: str, sensivel: bool = False) -> int:
        """Substitui todas as ocorrencias; devolve quantas trocas foram feitas."""
        if not busca:
            return 0
        flags = self._flags_de_busca(False, sensivel)
        total = 0
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        while True:
            achado = self.document().find(busca, cursor, flags)
            if achado.isNull():
                break
            achado.insertText(substituir)
            total += 1
            cursor = achado
        self._refresh_selections()
        return total

    # --- Autocompletar -------------------------------------------------------

    def _configurar_completer(self) -> None:
        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setWrapAround(True)
        # Nao mexer no focusPolicy do popup: o QCompleter define o proprio editor
        # como focus proxy do popup, e nesse build do Qt repassar um setFocusPolicy
        # ao popup zera o foco do editor (o teclado deixa de chegar a ele).
        # O popup ja nasce com NoFocus e nao rouba o foco.
        self._completer.activated.connect(self._inserir_completacao)

    def set_completer_words(self, words: list[str]) -> None:
        """Atualiza o vocabulario sugerido pelo autocompletar."""
        if self._completer is None:
            return
        unicos = sorted({palavra for palavra in words if palavra})
        # Guardamos o modelo: sem referencia em Python o QCompleter ficaria com um
        # ponteiro morto apos a coleta de lixo.
        self._completer_model = QStringListModel(unicos)
        self._completer.setModel(self._completer_model)
        if self._completer.popup().isVisible():
            self._completer.popup().hide()

    def _prefixo_atual(self) -> str:
        cursor = self.textCursor()
        posicao = cursor.position()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfWord)
        cursor.setPosition(posicao, QTextCursor.MoveMode.KeepAnchor)
        return cursor.selectedText()

    def _mostrar_popup(self) -> None:
        if self._completer is None:
            return
        prefixo = self._prefixo_atual()
        if not prefixo or not prefixo[0] in IDENTIFIER_CHARS:
            self._completer.popup().hide()
            return
        if len(prefixo) < 2:
            self._completer.popup().hide()
            return
        self._completer.setCompletionPrefix(prefixo)
        if self._completer.completionCount() == 0:
            self._completer.popup().hide()
            return
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        rect = self.cursorRect()
        rect.setWidth(
            max(
                160,
                popup.sizeHintForColumn(0)
                + popup.verticalScrollBar().sizeHint().width()
                + 24,
            )
        )
        popup.setGeometry(rect)
        popup.show()

    def _invocar_completer(self) -> None:
        if self._completer is None:
            return
        prefixo = self._prefixo_atual()
        if not prefixo:
            return
        self._completer.setCompletionPrefix(prefixo)
        if self._completer.completionCount() == 0:
            return
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        rect = self.cursorRect()
        rect.setWidth(
            max(
                160,
                popup.sizeHintForColumn(0)
                + popup.verticalScrollBar().sizeHint().width()
                + 24,
            )
        )
        popup.setGeometry(rect)
        popup.show()

    def _inserir_completacao(self, completacao: str) -> None:
        prefixo = self._prefixo_atual()
        extra = len(completacao) - len(prefixo)
        cursor = self.textCursor()
        if extra > 0:
            cursor.insertText(completacao[len(completacao) - extra:])
        else:
            cursor.insertText(completacao)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        popup = self._completer.popup() if self._completer is not None else None
        if popup is not None and popup.isVisible():
            chave = event.key()
            if chave in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                atual = self._completer.currentCompletion()
                if atual:
                    self._inserir_completacao(atual)
                    popup.hide()
                    event.accept()
                    return
            elif chave == Qt.Key.Key_Escape:
                popup.hide()
                event.accept()
                return
            elif chave in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                modelo = self._completer.model()
                linhas = modelo.rowCount() if modelo is not None else 0
                if linhas > 0:
                    delta = -1 if chave == Qt.Key.Key_Up else 1
                    indice = self._completer.currentIndex().row()
                    novo = (indice + delta) % linhas
                    self._completer.setCurrentIndex(modelo.index(novo, 0))
                    popup.setCurrentIndex(self._completer.currentIndex())
                    event.accept()
                    return
        super().keyPressEvent(event)
        if self._completer is None:
            return
        if (
            event.modifiers() == Qt.KeyboardModifier.NoModifier
            and event.text()
            and event.text()[0] in IDENTIFIER_CHARS
        ):
            self._mostrar_popup()
        elif (
            event.key() == Qt.Key.Key_Space
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self._invocar_completer()
        else:
            self._completer.popup().hide()

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoom_requested.emit(1 if delta > 0 else -1)
                event.accept()
                return
        super().wheelEvent(event)

    def focusOutEvent(self, event) -> None:
        if self._completer is not None and self._completer.popup().isVisible():
            self._completer.popup().hide()
        super().focusOutEvent(event)


    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), self.palette().window())
        painter.setFont(self.font())

        current_block_number = self.textCursor().blockNumber()
        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(
                    line_number_color(self.palette(), block.blockNumber() == current_block_number)
                )
                painter.drawText(
                    0,
                    int(top),
                    self._line_number_area.width() - LINE_NUMBER_MARGIN,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block.blockNumber() + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()


    def _refresh_selections(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []
        cursor = self.textCursor()

        if not cursor.hasSelection():
            current_line = QTextEdit.ExtraSelection()
            current_line.format.setBackground(self.current_line_color())
            current_line.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            current_line.cursor = cursor
            current_line.cursor.clearSelection()
            selections.append(current_line)

        selections.extend(self._error_selections)
        selections.extend(self._find_selections)
        self.setExtraSelections(selections)


    def current_line_color(self) -> QColor:
        return self._current_line_override or current_line_color(self.palette())

    def current_error_color(self) -> QColor:
        return self._error_override or error_color(self.palette(), self._theme)

    def set_current_line_color(self, color: QColor | None) -> None:
        self._current_line_override = None if color is None else QColor(color)
        self._refresh_selections()

    def set_error_color(self, color: QColor | None) -> None:
        self._error_override = None if color is None else QColor(color)
        self.set_error_marks(self._error_list)

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self._apply_highlight_colors()
        self.set_error_marks(self._error_list)
        self._refresh_selections()

    def set_highlight_colors(self, colors: dict[str, QColor | None]) -> None:
        self._highlight_overrides = {
            categoria: QColor(cor)
            for categoria, cor in colors.items()
            if cor is not None
        }
        self._apply_highlight_colors()

    def _apply_highlight_colors(self) -> None:
        self._highlighter.set_colors(
            resolve_colors(self._highlight_overrides, self.palette(), self._theme)
        )

    def set_tokens(self, tokens: tuple[Token, ...]) -> None:
        self._highlighter.set_tokens(tokens)

    def highlight_color(self, category: str) -> QColor:
        return self._highlighter.colors().get(category, QColor())

    def apply_font(self, family: str, size: int) -> None:
        self.setFont(monospace_font(family, size))
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self._update_line_number_width()
        self._line_number_area.update()


    def set_error_marks(self, errors: list[LexicalError]) -> None:
        self._error_list = list(errors)
        self._error_selections = [
            selection
            for selection in (self._build_error_selection(error) for error in self._error_list)
            if selection is not None
        ]
        self._refresh_selections()

    def clear_error_marks(self) -> None:
        self.set_error_marks([])

    def _build_error_selection(self, error: LexicalError) -> QTextEdit.ExtraSelection | None:
        start, end = self._positions_for(error)
        if start is None:
            return None
        red = self.current_error_color()
        selection = QTextEdit.ExtraSelection()
        selection.format.setForeground(red)
        selection.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        selection.format.setUnderlineColor(red)
        cursor = QTextCursor(self.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor
        return selection

    def _positions_for(self, error: LexicalError) -> tuple[int | None, int | None]:
        block = self.document().findBlockByNumber(error.line - 1)
        if not block.isValid():
            return None, None

        column = max(0, error.column - 1)
        first = block.position()
        last = first + max(1, block.length() - 1)

        start = min(first + column, last)
        end = min(max(start + max(1, error.length), start + 1), max(last, start + 1))
        return start, end
