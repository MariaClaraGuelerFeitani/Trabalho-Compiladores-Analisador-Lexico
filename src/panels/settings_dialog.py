
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import default_background_image
from ..editor.highlighter import (
    CATEGORIES,
    CATEGORY_COMMENT,
    CATEGORY_KEYWORD,
    CATEGORY_LABELS,
    CATEGORY_LITERAL,
    CATEGORY_NUMBER,
    CATEGORY_TYPE,
    PREFERENCE_FIELDS,
    default_colors,
)
from ..settings import (
    MAX_BACKGROUND_OPACITY,
    MAX_FONT_SIZE,
    MIN_BACKGROUND_OPACITY,
    MIN_FONT_SIZE,
    THEME_CHOICES,
    THEME_LABELS,
    Settings,
)

IMAGE_FILTER = "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;Todos os arquivos (*)"

PREVIEW_SEGMENTS: tuple[tuple[str | None, str], ...] = (
    (CATEGORY_KEYWORD, "programa"),
    (None, " Ola;\n"),
    (CATEGORY_KEYWORD, "var"),
    (None, " x: "),
    (CATEGORY_TYPE, "integer"),
    (None, ";\n"),
    (CATEGORY_KEYWORD, "begin"),
    (None, "\n  x := "),
    (CATEGORY_NUMBER, "10"),
    (None, ";  "),
    (CATEGORY_COMMENT, "// um comentario"),
    (None, "\n  "),
    (CATEGORY_KEYWORD, "writeln"),
    (None, "("),
    (CATEGORY_LITERAL, "'ola'"),
    (None, ", x);\n"),
    (CATEGORY_KEYWORD, "end"),
    (None, "."),
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

        self._build_highlight_tab(settings)
        self._build_background_tab(settings)

        self._connect()
        self._sync_enabled_state()

    def _build_highlight_tab(self, settings: Settings) -> None:
        self.highlight_buttons: dict[str, ColorButton] = {}
        self.highlight_auto: dict[str, QCheckBox] = {}

        padrao = default_colors(self.palette())
        layout = QFormLayout()
        for categoria in CATEGORIES:
            valor = getattr(settings, PREFERENCE_FIELDS[categoria])
            botao = ColorButton(
                QColor(valor) if valor else padrao[categoria],
                CATEGORY_LABELS[categoria],
            )
            auto = QCheckBox("Usar a cor do tema")
            auto.setChecked(not valor)
            self.highlight_buttons[categoria] = botao
            self.highlight_auto[categoria] = auto
            layout.addRow(
                CATEGORY_LABELS[categoria], self._color_row(botao, auto)
            )

        self.highlight_preview = QLabel()
        self.highlight_preview.setTextFormat(Qt.TextFormat.RichText)
        self.highlight_preview.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addRow("Previa:", self.highlight_preview)
        self._tabs.addTab(self._wrap(layout), "Realce")
        self._update_preview()

    def _build_background_tab(self, settings: Settings) -> None:
        self.background_edit = QLineEdit(settings.background_image_path)
        self.background_edit.setReadOnly(True)
        self.background_edit.setPlaceholderText("Sem imagem de fundo")

        self.background_spin = QSpinBox()
        self.background_spin.setRange(MIN_BACKGROUND_OPACITY, MAX_BACKGROUND_OPACITY)
        self.background_spin.setValue(settings.background_image_opacity)
        self.background_spin.setSuffix(" %")

        choose = QPushButton("Escolher...")
        choose.clicked.connect(self._choose_background)

        bundled = QPushButton("Imagem do projeto")
        bundled.setToolTip(default_background_image() or "A pasta img/ nao foi encontrada")
        bundled.clicked.connect(self._use_bundled_background)

        remove = QPushButton("Remover")
        remove.clicked.connect(self._remove_background)

        self.background_hint = QLabel()
        self.background_hint.setWordWrap(True)

        layout = QFormLayout()
        layout.addRow("Arquivo:", self._wrap_row(self.background_edit, choose, bundled, remove))
        layout.addRow("Opacidade:", self.background_spin)
        layout.addRow("", self.background_hint)
        self._tabs.addTab(self._wrap(layout), "Fundo")
        self._update_background_hint()

    @staticmethod
    def _wrap_row(*widgets: QWidget) -> QWidget:
        row = QHBoxLayout()
        for widget in widgets:
            row.addWidget(widget)
        row.addStretch()
        holder = QWidget()
        holder.setLayout(row)
        return holder

    def _choose_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Imagem de fundo", "", IMAGE_FILTER)
        if path:
            self.background_edit.setText(path)
            self._emit()

    def _use_bundled_background(self) -> None:
        path = default_background_image()
        if path:
            self.background_edit.setText(path)
            self._emit()

    def _remove_background(self) -> None:
        self.background_edit.setText("")
        self._emit()

    def _exists(self, path: str) -> bool:
        return bool(path) and Path(path).is_file()

    def _update_background_hint(self) -> None:
        caminho = self.background_edit.text().strip()
        if not caminho:
            self.background_hint.setText("Sem imagem: o editor usa só a cor do tema.")
        elif self._exists(caminho):
            self.background_hint.setText(
                "A imagem cobre o editor mantendo a proporcao; o que sobra e cortado."
            )
        else:
            self.background_hint.setText("Arquivo nao encontrado: o editor fica sem fundo.")

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

    def _highlight_colors(self) -> dict[str, QColor]:
        cores = default_colors(self.palette())
        for categoria in CATEGORIES:
            if not self.highlight_auto[categoria].isChecked():
                cores[categoria] = self.highlight_buttons[categoria].color()
        return cores

    def _update_preview(self) -> None:
        self.highlight_preview.setFont(
            QFont(self.font_combo.currentFont().family(), self.size_spin.value())
        )
        base = self.palette().color(QPalette.ColorRole.Base).name()
        self.highlight_preview.setStyleSheet(
            f"background-color: {base}; color: {self.palette().color(QPalette.ColorRole.Text).name()};"
            " padding: 6px;"
        )
        cores = self._highlight_colors()
        partes = [
            texto if categoria is None
            else f'<span style="color:{cores[categoria].name()}">{texto}</span>'
            for categoria, texto in PREVIEW_SEGMENTS
        ]
        html = "".join(partes).replace("\n", "<br>")
        self.highlight_preview.setText(html)

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
        for categoria in CATEGORIES:
            self.highlight_buttons[categoria].clicked.connect(
                lambda c=categoria: self._after_color_pick(
                    self.highlight_buttons[c], self.highlight_auto[c]
                )
            )
            self.highlight_auto[categoria].toggled.connect(self._sync_enabled_state)
            self.highlight_auto[categoria].toggled.connect(self._emit)
        self.background_spin.valueChanged.connect(self._emit)

    def _after_color_pick(self, button: ColorButton, checkbox: QCheckBox) -> None:
        checkbox.setChecked(False)
        self._emit()

    def _sync_enabled_state(self) -> None:
        self.current_line_button.setEnabled(not self.current_line_auto.isChecked())
        self.error_button.setEnabled(not self.error_auto.isChecked())
        for categoria in CATEGORIES:
            self.highlight_buttons[categoria].setEnabled(
                not self.highlight_auto[categoria].isChecked()
            )


    def settings(self) -> Settings:
        valores = {
            "theme": self.theme_combo.currentData(),
            "font_family": self.font_combo.currentFont().family(),
            "font_size": self.size_spin.value(),
            "current_line_color": (
                "" if self.current_line_auto.isChecked() else self.current_line_button.color().name()
            ),
            "error_color": "" if self.error_auto.isChecked() else self.error_button.color().name(),
            "console_background": self.console_bg_button.color().name(),
            "console_foreground": self.console_fg_button.color().name(),
            "background_image_path": self.background_edit.text().strip(),
            "background_image_opacity": self.background_spin.value(),
        }
        for categoria, campo in PREFERENCE_FIELDS.items():
            valores[campo] = (
                ""
                if self.highlight_auto[categoria].isChecked()
                else self.highlight_buttons[categoria].color().name()
            )
        return Settings(**valores)

    def _emit(self) -> None:
        self._update_preview()
        self._update_background_hint()
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
        self.background_edit.setText(defaults.background_image_path)
        self.background_spin.setValue(defaults.background_image_opacity)
        padrao = default_colors(self.palette())
        for categoria in CATEGORIES:
            self.highlight_buttons[categoria].set_color(padrao[categoria])
            self.highlight_auto[categoria].setChecked(True)
        self._emit()

    def _accept(self) -> None:
        self._on_change(self.settings())
        self.accept()

    def _reject(self) -> None:
        self._on_change(self._original)
        self.reject()
