
from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPalette,
    QPixmap,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from ..config import monospace_font
from ..services.lexer_service import LexicalError, Token
from .highlighter import TokenHighlighter, resolve_colors

LINE_NUMBER_MARGIN = 4
MIN_LINE_NUMBER_DIGITS = 2

CURRENT_LINE_TINT = 0.07
LINE_NUMBER_MUTED = 0.45
LINE_NUMBER_CURRENT = 0.20

ERROR_ON_DARK = "#ff5252"
ERROR_ON_LIGHT = "#c62828"

DEFAULT_BACKGROUND_OPACITY = 10
MIN_BACKGROUND_OPACITY = 0
MAX_BACKGROUND_OPACITY = 100


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


def error_color(palette: QPalette) -> QColor:
    return QColor(ERROR_ON_LIGHT if _base(palette).lightness() >= 128 else ERROR_ON_DARK)


class LineNumberArea(QWidget):

    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802 - nome imposto pelo Qt
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self._error_selections: list[QTextEdit.ExtraSelection] = []
        self._error_list: list[LexicalError] = []
        self._current_line_override: QColor | None = None
        self._error_override: QColor | None = None
        self._highlight_overrides: dict[str, QColor] = {}
        self._highlighter = TokenHighlighter(self.document())
        self._background: QPixmap | None = None
        self._background_opacity = DEFAULT_BACKGROUND_OPACITY / 100
        self._cover: QPixmap | None = None
        self._cover_key: tuple[QSize, int] | None = None

        self.setFont(monospace_font())
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setPlaceholderText("Escreva seu codigo aqui.")

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

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        contents = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(contents.left(), contents.top(), self.line_number_area_width(), contents.height())
        )

    def changeEvent(self, event) -> None:  # noqa: N802
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

    def paintEvent(self, event) -> None:  # noqa: N802
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
        self.setExtraSelections(selections)


    def current_line_color(self) -> QColor:
        return self._current_line_override or current_line_color(self.palette())

    def current_error_color(self) -> QColor:
        return self._error_override or error_color(self.palette())

    def set_current_line_color(self, color: QColor | None) -> None:
        self._current_line_override = None if color is None else QColor(color)
        self._refresh_selections()

    def set_error_color(self, color: QColor | None) -> None:
        self._error_override = None if color is None else QColor(color)
        self.set_error_marks(self._error_list)

    def set_highlight_colors(self, colors: dict[str, QColor | None]) -> None:
        self._highlight_overrides = {
            categoria: QColor(cor)
            for categoria, cor in colors.items()
            if cor is not None
        }
        self._apply_highlight_colors()

    def _apply_highlight_colors(self) -> None:
        self._highlighter.set_colors(
            resolve_colors(self._highlight_overrides, self.palette())
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
