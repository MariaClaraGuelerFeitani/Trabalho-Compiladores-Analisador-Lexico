
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFontComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..settings import (
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    THEME_CHOICES,
    THEME_LABELS,
    Settings,
)


class ColorButton(QPushButton):

    def __init__(self, color: QColor, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self._title = title
        self.setMinimumWidth(120)
        self.clicked.connect(self._pick)
        self._render()

    def color(self) -> QColor:
        return QColor(self._color)

    def set_color(self, color: QColor) -> None:
        self._color = QColor(color)
        self._render()

    def _pick(self) -> None:
        chosen = QColorDialog.getColor(self._color, self, self._title)
        if chosen.isValid():
            self.set_color(chosen)

    def _render(self) -> None:
        text = self._color.name()
        readable = "#000000" if self._color.lightness() > 140 else "#ffffff"
        self.setText(text)
        self.setStyleSheet(
            f"QPushButton {{ background-color: {text}; color: {readable};"
            f" border: 1px solid #888888; padding: 3px 8px; }}"
        )


class SettingsDialog(QDialog):

    def __init__(
        self,
        settings: Settings,
        on_change: Callable[[Settings], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferencias")
        self.setModal(True)
        self._original = settings.copy()
        self._on_change = on_change

        self._build_ui(settings)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self._reject)

        root = QVBoxLayout(self)
        root.addWidget(self._tabs)
        root.addWidget(buttons)


    def _build_ui(self, settings: Settings) -> None:
        self._tabs = QTabWidget()

        self.theme_combo = QComboBox()
        for value in THEME_CHOICES:
            self.theme_combo.addItem(THEME_LABELS[value], value)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(settings.theme))

        self.font_combo = QFontComboBox()
        self.font_combo.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
        self.font_combo.setCurrentFont(QFont(settings.font_family))
        if self.font_combo.currentFont().family() != settings.font_family:
            self.font_combo.setCurrentIndex(0)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self.size_spin.setValue(settings.font_size)
        self.size_spin.setSuffix(" pt")

        font_preview = QLabel("programa Ola;\nbegin\nend.")
        font_preview.setFont(QFont(settings.font_family, settings.font_size))
        font_preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        appearance = QFormLayout()
        appearance.addRow("Tema:", self.theme_combo)
        appearance.addRow("Fonte do editor:", self.font_combo)
        appearance.addRow("Tamanho:", self.size_spin)
        appearance.addRow("Previa:", font_preview)
        self._tabs.addTab(self._wrap(appearance), "Aparencia")

        self.current_line_button = ColorButton(
            QColor(settings.current_line_color)
            if settings.current_line_color
            else self._fallback_current_line(),
            "Cor da linha atual",
        )
        self.current_line_auto = QCheckBox("Usar a cor do tema")
        self.current_line_auto.setChecked(not settings.current_line_color)

        self.error_button = ColorButton(
            QColor(settings.error_color) if settings.error_color else self._fallback_error(),
            "Cor do erro lexico",
        )
        self.error_auto = QCheckBox("Usar a cor do tema")
        self.error_auto.setChecked(not settings.error_color)

        self.console_bg_button = ColorButton(QColor(settings.console_background), "Fundo da saida")
        self.console_fg_button = ColorButton(QColor(settings.console_foreground), "Texto da saida")

        colors = QFormLayout()
        colors.addRow("Linha atual:", self._color_row(self.current_line_button, self.current_line_auto))
        colors.addRow("Erro lexico:", self._color_row(self.error_button, self.error_auto))
        colors.addRow("Fundo da saida:", self.console_bg_button)
        colors.addRow("Texto da saida:", self.console_fg_button)

        restore = QPushButton("Restaurar padroes")
        restore.clicked.connect(self._restore_defaults)
        colors.addRow("", restore)
        self._tabs.addTab(self._wrap(colors), "Cores")

        self._connect()
        self._sync_enabled_state()

    @staticmethod
    def _wrap(layout) -> QWidget:
        widget = QWidget()
        layout.setContentsMargins(12, 12, 12, 12)
        widget.setLayout(layout)
        return widget

    @staticmethod
    def _color_row(button: ColorButton, checkbox: QCheckBox) -> QWidget:
        row = QHBoxLayout()
        row.addWidget(button)
        row.addWidget(checkbox)
        row.addStretch()
        holder = QWidget()
        holder.setLayout(row)
        return holder

    def _fallback_current_line(self) -> QColor:
        from ..editor.code_editor import current_line_color  # noqa: PLC0415

        return current_line_color(self.palette())

    def _fallback_error(self) -> QColor:
        from ..editor.code_editor import error_color  # noqa: PLC0415

        return error_color(self.palette())

    def _connect(self) -> None:
        self.theme_combo.currentIndexChanged.connect(self._emit)
        self.font_combo.currentFontChanged.connect(self._emit)
        self.size_spin.valueChanged.connect(self._emit)
        self.current_line_button.clicked.connect(
            lambda: self._after_color_pick(self.current_line_button, self.current_line_auto)
        )
        self.error_button.clicked.connect(
            lambda: self._after_color_pick(self.error_button, self.error_auto)
        )
        self.console_bg_button.clicked.connect(self._emit)
        self.console_fg_button.clicked.connect(self._emit)
        self.current_line_auto.toggled.connect(self._sync_enabled_state)
        self.current_line_auto.toggled.connect(self._emit)
        self.error_auto.toggled.connect(self._sync_enabled_state)
        self.error_auto.toggled.connect(self._emit)

    def _after_color_pick(self, button: ColorButton, checkbox: QCheckBox) -> None:
        checkbox.setChecked(False)
        self._emit()

    def _sync_enabled_state(self) -> None:
        self.current_line_button.setEnabled(not self.current_line_auto.isChecked())
        self.error_button.setEnabled(not self.error_auto.isChecked())


    def settings(self) -> Settings:
        return Settings(
            theme=self.theme_combo.currentData(),
            font_family=self.font_combo.currentFont().family(),
            font_size=self.size_spin.value(),
            current_line_color=(
                "" if self.current_line_auto.isChecked() else self.current_line_button.color().name()
            ),
            error_color="" if self.error_auto.isChecked() else self.error_button.color().name(),
            console_background=self.console_bg_button.color().name(),
            console_foreground=self.console_fg_button.color().name(),
        )

    def _emit(self) -> None:
        self._on_change(self.settings())

    def _restore_defaults(self) -> None:
        defaults = Settings()
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(defaults.theme))
        self.size_spin.setValue(defaults.font_size)
        self.current_line_button.set_color(self._fallback_current_line())
        self.current_line_auto.setChecked(True)
        self.error_button.set_color(self._fallback_error())
        self.error_auto.setChecked(True)
        self.console_bg_button.set_color(QColor(defaults.console_background))
        self.console_fg_button.set_color(QColor(defaults.console_foreground))
        self._emit()

    def _accept(self) -> None:
        self._on_change(self.settings())
        self.accept()

    def _reject(self) -> None:
        self._on_change(self._original)
        self.reject()
