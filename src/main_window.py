
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QWidget,
)

from .config import LANGUAGE_NAME, NEW_FILE_TEMPLATE
from .editor.code_editor import CodeEditor
from .panels.console_view import ConsoleView
from .panels.data_table import DataTable
from .panels.settings_dialog import SettingsDialog
from .parser.grammar import linhas_da_gramatica
from .services.analysis_controller import AnalysisController
from .services.file_service import UNSAVED_TITLE, FileService
from .services.lexer_service import AnalysisResult, LexerService
from .settings import MAX_FONT_SIZE, MIN_FONT_SIZE, Settings, load_settings, save_settings
from .theme import apply_theme

WINDOW_SIZE = (1100, 720)

TAB_OUTPUT = 0
TAB_ERRORS = 1
TAB_WARNINGS = 2
TAB_TOKENS = 3
TAB_SYMBOLS = 4

COLUMNS_ERRORS = ["Linha", "Coluna", "Lexema", "Mensagem"]
COLUMNS_WARNINGS = ["Linha", "Coluna", "Mensagem"]
COLUMNS_TOKENS = ["#", "Token", "Lexema", "Linha", "Coluna"]
COLUMNS_SYMBOLS = ["Identificador", "Classe", "Tipo", "Valor", "Linha"]
COLUMNS_TOKEN_CLASSES = ["Token", "Expressao Regular", "Descricao"]
COLUMNS_DFA_STATES = ["Estado", "Aceita", "Token associado"]
COLUMNS_DFA_TRANSITIONS = ["Estado de origem", "Simbolo", "Estado de destino"]
COLUMNS_GRAMATICA = ["Producao"]


def _optional_color(value: str) -> QColor | None:
    return QColor(value) if value else None


class MainWindow(QMainWindow):
    def __init__(
        self,
        lexer: LexerService,
        settings_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.lexer = lexer
        self.analysis = AnalysisController(lexer, self)
        self._settings_path = settings_path
        self._current_path: str | None = None
        self._modified = False
        self.settings = load_settings(settings_path)

        self.setWindowTitle(f"{LANGUAGE_NAME} - IDE")
        self.resize(*WINDOW_SIZE)

        self.editor = CodeEditor()
        self.setCentralWidget(self.editor)

        self._build_docks()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_status_bar()
        self._connect()

        self.apply_settings(self.settings)
        self.new_file()
        self._log(f"{LANGUAGE_NAME} pronto.")


    def _build_docks(self) -> None:
        self.output_console = ConsoleView()

        self.errors_table = DataTable(COLUMNS_ERRORS)
        self.warnings_table = DataTable(COLUMNS_WARNINGS)
        self.tokens_table = DataTable(COLUMNS_TOKENS)
        self.symbols_table = DataTable(COLUMNS_SYMBOLS)
        self.token_classes_table = DataTable(COLUMNS_TOKEN_CLASSES)
        self.dfa_states_table = DataTable(COLUMNS_DFA_STATES)
        self.dfa_transitions_table = DataTable(COLUMNS_DFA_TRANSITIONS)
        self.grammar_table = DataTable(COLUMNS_GRAMATICA)

        self.output_tabs = QTabWidget()
        self.output_tabs.setObjectName("outputTabs")
        self.output_tabs.addTab(self.output_console, "Saida")
        self.output_tabs.addTab(self.errors_table, "Erros")
        self.output_tabs.addTab(self.warnings_table, "Avisos")
        self.output_tabs.addTab(self.tokens_table, "Tokens")
        self.output_tabs.addTab(self.symbols_table, "Tabela de simbolos")
        self._add_dock("Paineis de saida", self.output_tabs, Qt.DockWidgetArea.BottomDockWidgetArea)

        self.dfa_tabs = QTabWidget()
        self.dfa_tabs.setObjectName("dfaTabs")
        self.dfa_tabs.addTab(self.token_classes_table, "Classes de tokens")
        self.dfa_tabs.addTab(self.dfa_states_table, "DFA - estados")
        self.dfa_tabs.addTab(self.dfa_transitions_table, "DFA - transicoes")
        self.dfa_tabs.addTab(self.grammar_table, "Gramatica")
        self._add_dock("Tokens e automato", self.dfa_tabs, Qt.DockWidgetArea.RightDockWidgetArea)

    def _add_dock(self, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(f"dock{title.replace(' ', '')}")
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(area, dock)
        return dock

    def _action(
        self,
        text: str,
        slot,
        shortcut: QKeySequence | str | None = None,
        tip: str = "",
    ) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        if tip:
            action.setStatusTip(tip)
        return action

    def _build_actions(self) -> None:
        self.action_new = self._action(
            "&Novo", self.new_file, QKeySequence.StandardKey.New, "Cria um programa vazio"
        )
        self.action_open = self._action(
            "&Abrir...", self.open_file, QKeySequence.StandardKey.Open, "Abre um programa existente"
        )
        self.action_save = self._action(
            "&Salvar", self.save_file, QKeySequence.StandardKey.Save, "Salva o programa"
        )
        self.action_save_as = self._action(
            "Salvar &como...", self.save_file_as, QKeySequence.StandardKey.SaveAs, "Salva com outro nome"
        )
        self.action_exit = self._action("&Sair", self.close, QKeySequence.StandardKey.Quit)
        self.action_compile = self._action(
            "&Compilar", self.compile, "Ctrl+B", "Roda a analise lexica agora"
        )
        self.action_clear_output = self._action(
            "&Limpar saida", self.clear_output, "Ctrl+L", "Limpa o log da aba Saida"
        )
        self.action_preferences = self._action(
            "&Preferencias...", self.open_preferences, "Ctrl+,", "Tema, fonte e cores do IDE"
        )
        self.action_restore_defaults = self._action(
            "Restaurar &aparencia padrao",
            self.restore_default_appearance,
            "",
            "Volta tema, fonte e cores ao padrao",
        )
        self.action_zoom_in = self._action(
            "Aumentar &fonte", self.zoom_in, "Ctrl++", "Aumenta a fonte do editor"
        )
        self.action_zoom_out = self._action(
            "Diminuir &fonte", self.zoom_out, "Ctrl+-", "Diminui a fonte do editor"
        )
        self.action_zoom_reset = self._action(
            "Fonte &normal", self.zoom_reset, "Ctrl+0", "Volta a fonte ao tamanho padrao"
        )

    def _build_menus(self) -> None:
        menu_file = self.menuBar().addMenu("&Arquivo")
        menu_file.addActions([self.action_new, self.action_open])
        menu_file.addSeparator()
        menu_file.addActions([self.action_save, self.action_save_as])
        menu_file.addSeparator()
        menu_file.addAction(self.action_exit)

        menu_run = self.menuBar().addMenu("&Executar")
        menu_run.addAction(self.action_compile)
        menu_run.addAction(self.action_clear_output)

        menu_tools = self.menuBar().addMenu("&Ferramentas")
        menu_tools.addAction(self.action_preferences)
        menu_tools.addAction(self.action_restore_defaults)
        menu_tools.addSeparator()
        menu_tools.addActions(
            [self.action_zoom_in, self.action_zoom_out, self.action_zoom_reset]
        )

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Principal")
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.addActions([self.action_new, self.action_open, self.action_save])
        toolbar.addSeparator()
        toolbar.addAction(self.action_compile)

    def _build_status_bar(self) -> None:
        self.position_label = QLabel("Ln 1, Col 1")
        self.state_label = QLabel("Pronto")
        self.statusBar().addPermanentWidget(self.position_label)
        self.statusBar().addPermanentWidget(self.state_label)

    def _connect(self) -> None:
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._update_position)
        self.analysis.result_ready.connect(self._show_result)


    def new_file(self) -> None:
        if not self._confirm_discard():
            return
        self._replace_editor_text(NEW_FILE_TEMPLATE.format(nome="Ola"))
        self._current_path = None
        self._mark_clean()
        self._clear_result_panels()
        self.analysis.request(self.editor.toPlainText())

    def open_file(self) -> None:
        if not self._confirm_discard():
            return
        path = FileService.open_dialog(self)
        if path is None:
            return
        try:
            content = FileService.read(path)
        except OSError as error:
            QMessageBox.critical(self, "Erro ao abrir", f"Não foi possível ler o arquivo:\n{error}")
            return
        self._replace_editor_text(content)
        self._current_path = path
        self._mark_clean()
        self._log(f"Abrido: {path}")
        self.analysis.request(content)

    def _replace_editor_text(self, text: str) -> None:
        self.editor.blockSignals(True)
        try:
            self.editor.setPlainText(text)
        finally:
            self.editor.blockSignals(False)
        self._update_position()

    def _mark_clean(self) -> None:
        self.editor.document().setModified(False)
        self._modified = False
        self._update_title()

    def save_file(self) -> bool:
        if self._current_path is None:
            return self.save_file_as()
        return self._write_to(self._current_path)

    def save_file_as(self) -> bool:
        path = FileService.save_dialog(self, self._current_path or "")
        if path is None:
            return False
        return self._write_to(path)

    def _write_to(self, path: str) -> bool:
        try:
            FileService.write(path, self.editor.toPlainText())
        except OSError as error:
            QMessageBox.critical(self, "Erro ao salvar", f"Não foi possível salvar o arquivo:\n{error}")
            return False
        self._current_path = path
        self._mark_clean()
        self._log(f"Salvo: {path}")
        return True

    def _confirm_discard(self) -> bool:
        if not self._modified:
            return True
        answer = QMessageBox.question(
            self,
            f"{LANGUAGE_NAME} - IDE",
            f"Salvar as alterações em {self._display_name()} antes de continuar?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save_file()
        return True

    def _display_name(self) -> str:
        if self._current_path is None:
            return UNSAVED_TITLE
        return Path(self._current_path).name

    def _update_title(self) -> None:
        marker = " *" if self._modified else ""
        self.setWindowTitle(f"{self._display_name()}{marker} - {LANGUAGE_NAME} - IDE")


    def compile(self) -> None:
        result = self.analysis.analyze_now(self.editor.toPlainText())
        self._log(self._summarize(result))
        self.output_tabs.setCurrentWidget(self.errors_table if result.has_errors else self.output_console)

    def _on_text_changed(self) -> None:
        self._modified = True
        self._update_title()
        self.analysis.request(self.editor.toPlainText())

    def _update_position(self) -> None:
        cursor = self.editor.textCursor()
        self.position_label.setText(f"Ln {cursor.blockNumber() + 1}, Col {cursor.positionInBlock() + 1}")

    def _summarize(self, result: AnalysisResult) -> str:
        if result.has_errors:
            return f"Analise concluida com {len(result.errors)} erro(s) e {result.token_count} token(s)."
        return f"Analise concluida sem erros: {result.token_count} token(s)."

    def _show_result(self, result: AnalysisResult) -> None:
        self.editor.set_error_marks(list(result.errors))

        self.errors_table.set_rows(
            [(e.line, e.column, e.lexeme, e.message) for e in result.errors]
        )
        self.warnings_table.set_rows([(w.line, w.column, w.message) for w in result.warnings])
        self.tokens_table.set_rows(
            [(i, t.tipo, t.lexema, t.linha, t.coluna) for i, t in enumerate(result.tokens, start=1)]
        )
        self.symbols_table.set_rows(
            [(s.identifier, s.kind, s.type, s.value, s.line) for s in result.symbols]
        )
        self.token_classes_table.set_rows(
            [(c.tipo, c.regex, c.description) for c in result.token_classes]
        )
        self.dfa_states_table.set_rows(
            [(s.name, "sim" if s.is_accepting else "nao", s.token) for s in result.dfa_states]
        )
        self.dfa_transitions_table.set_rows(
            [(t.state, t.symbol, t.target) for t in result.dfa_transitions]
        )
        self.grammar_table.set_rows([(linha,) for linha in linhas_da_gramatica()])

        self._update_count_labels(result)
        self.state_label.setText(
            f"{len(result.errors)} erro(s)" if result.has_errors else f"{result.token_count} token(s)"
        )

    def _update_count_labels(self, result: AnalysisResult) -> None:
        self.output_tabs.setTabText(TAB_ERRORS, f"Erros ({len(result.errors)})")
        self.output_tabs.setTabText(TAB_WARNINGS, f"Avisos ({len(result.warnings)})")
        self.output_tabs.setTabText(TAB_TOKENS, f"Tokens ({result.token_count})")
        self.output_tabs.setTabText(TAB_SYMBOLS, f"Tabela de simbolos ({len(result.symbols)})")

    def _clear_result_panels(self) -> None:
        for table in (
            self.errors_table,
            self.warnings_table,
            self.tokens_table,
            self.symbols_table,
            self.token_classes_table,
            self.dfa_states_table,
            self.dfa_transitions_table,
        ):
            table.set_rows([])


    def apply_settings(self, settings: Settings) -> None:
        self.settings = settings

        apply_theme(QApplication.instance(), settings.theme)

        self.editor.set_current_line_color(_optional_color(settings.current_line_color))
        self.editor.set_error_color(_optional_color(settings.error_color))
        self.editor.apply_font(settings.font_family, settings.font_size)
        self.output_console.apply_font(settings.font_family, settings.font_size)
        self.output_console.apply_colors(
            settings.console_background, settings.console_foreground
        )

    def open_preferences(self) -> None:
        dialog = SettingsDialog(self.settings, self._preview_settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.commit_settings(dialog.settings())

    def _preview_settings(self, settings: Settings) -> None:
        self.apply_settings(settings)

    def commit_settings(self, settings: Settings) -> None:
        self.apply_settings(settings)
        if not save_settings(settings, self._settings_path):
            self._log("Nao foi possivel gravar as preferencias.")

    def restore_default_appearance(self) -> None:
        self.commit_settings(Settings())

    def _set_font_size(self, size: int) -> None:
        settings = self.settings.copy()
        settings.font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))
        self.commit_settings(settings)

    def zoom_in(self) -> None:
        self._set_font_size(self.settings.font_size + 1)

    def zoom_out(self) -> None:
        self._set_font_size(self.settings.font_size - 1)

    def zoom_reset(self) -> None:
        self._set_font_size(Settings().font_size)


    def _log(self, message: str) -> None:
        self.output_console.append_line(message)

    def clear_output(self) -> None:
        self.output_console.clear_output()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
