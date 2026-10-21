
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QColor, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect
except ImportError:  # pragma: no cover - pacote opcional
    QMediaPlayer = None  # type: ignore
    QSoundEffect = None  # type: ignore
    QAudioOutput = None  # type: ignore

from .codegen import ErroDeTraducao, compilar, executar, traduzir
from .config import (
    LANGUAGE_NAME,
    NEW_FILE_TEMPLATE,
    RECENT_LIMIT,
    sfx_background_path,
    sfx_button_path,
    sfx_compile_path,
)
from .editor.code_editor import CodeEditor
from .editor.highlighter import CATEGORIES, PREFERENCE_FIELDS
from .lexer.tokens import PALAVRAS_RESERVADAS
from .panels.console_view import ConsoleView
from .panels.data_table import DataTable
from .panels.file_explorer import FileExplorer
from .panels.find_bar import FindBar
from .panels.settings_dialog import SettingsDialog
from .parser.grammar import linhas_da_gramatica
from .services.analysis_controller import AnalysisController
from .services.file_service import UNSAVED_TITLE, FileService
from .services.lexer_service import AnalysisResult, LexerService
from .settings import (
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    THEME_CHOICES,
    THEME_RESIDENT_EVIL,
    Settings,
    load_settings,
    save_settings,
)
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

PALAVRAS_DE_COMPLETAR = ("write", "writeln", "read", "readln")


def _optional_color(value: str) -> QColor | None:
    return QColor(value) if value else None


@dataclass
class _AbaEditor:

    editor: CodeEditor
    caminho: str | None = None
    modificado: bool = False

    @property
    def nome(self) -> str:
        if not self.caminho:
            return UNSAVED_TITLE
        return Path(self.caminho).name


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
        self._background_error = ""
        self.settings = load_settings(settings_path)
        self._abas: list[_AbaEditor] = []

        self.setWindowTitle(f"{LANGUAGE_NAME} - IDE")
        self.resize(*WINDOW_SIZE)

        self.find_bar = FindBar(self)
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setMovable(True)
        self.editor_tabs.setDocumentMode(True)
        self.editor_tabs.tabCloseRequested.connect(self._fechar_aba_solicitada)

        botao_novo = QToolButton()
        botao_novo.setText("+")
        botao_novo.setToolTip("Novo arquivo (Ctrl+N)")
        botao_novo.clicked.connect(self.new_file)
        self.editor_tabs.setCornerWidget(botao_novo, Qt.Corner.TopRightCorner)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.find_bar)
        layout.addWidget(self.editor_tabs)
        self.find_bar.hide()
        self.setCentralWidget(central)

        self._build_docks()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_status_bar()
        self._connect()

        self._init_sfx()
        self._geometria_padrao = bytes(self.saveGeometry())
        self._estado_padrao = bytes(self.saveState())
        self._restaurar_geometria_salva()
        self.apply_settings(self.settings)
        self.explorer.definir_raiz(self._raiz_inicial())
        self.new_file()
        self._log(f"{LANGUAGE_NAME} pronto.")

    # --- Estrutura de abas -----------------------------------------------------

    @property
    def editor(self) -> CodeEditor:
        """O editor da aba atual (compatibilidade com a versao de aba unica)."""
        aba = self._aba_atual()
        if aba is None:
            aba = self._criar_aba(NEW_FILE_TEMPLATE.format(nome="Ola"), None)
        return aba.editor

    @property
    def _current_path(self) -> str | None:
        aba = self._aba_atual()
        return aba.caminho if aba else None

    @property
    def _modified(self) -> bool:
        aba = self._aba_atual()
        return bool(aba and aba.modificado)

    def _aba_atual(self) -> _AbaEditor | None:
        indice = self.editor_tabs.currentIndex()
        if 0 <= indice < len(self._abas):
            return self._abas[indice]
        return None

    def _aplicar_ao_editor(self, editor: CodeEditor) -> None:
        configuracoes = self.settings
        editor.set_theme(configuracoes.theme)
        editor.set_current_line_color(_optional_color(configuracoes.current_line_color))
        editor.set_error_color(_optional_color(configuracoes.error_color))
        editor.set_highlight_colors(
            {
                categoria: _optional_color(
                    getattr(configuracoes, PREFERENCE_FIELDS[categoria])
                )
                for categoria in CATEGORIES
            }
        )
        editor.set_background_image(
            configuracoes.background_image_path, configuracoes.background_image_opacity
        )
        editor.apply_font(configuracoes.font_family, configuracoes.font_size)
        editor.set_completer_words(self._palavras_do_completar(()))

    def _criar_aba(
        self, texto: str, caminho: str | None, marcar_limpa: bool = True
    ) -> _AbaEditor:
        editor = CodeEditor()
        editor.blockSignals(True)
        try:
            editor.setPlainText(texto)
        finally:
            editor.blockSignals(False)
        aba = _AbaEditor(editor=editor, caminho=caminho)
        self._aplicar_ao_editor(editor)
        editor.textChanged.connect(self._on_text_changed)
        editor.cursorPositionChanged.connect(self._update_position)
        editor.zoom_requested.connect(self._zoom_editor)

        self._abas.append(aba)
        indice = self.editor_tabs.addTab(editor, aba.nome)
        self.editor_tabs.setTabToolTip(
            indice, caminho if caminho else "arquivo novo"
        )
        self.editor_tabs.setCurrentIndex(indice)
        if marcar_limpa:
            self._marcar_aba_limpa(aba)
        self._atualizar_rotulo_da_aba(indice)
        self._update_title()
        self._clear_result_panels()
        self.analysis.request(texto)
        return aba

    def _fechar_aba_solicitada(self, indice: int) -> None:
        self._fechar_aba(indice)

    def _fechar_aba(self, indice: int) -> bool:
        if not (0 <= indice < len(self._abas)):
            return False
        aba = self._abas[indice]
        if aba.modificado:
            resposta = QMessageBox.question(
                self,
                f"{LANGUAGE_NAME} - IDE",
                f"Salvar as alterações em {aba.nome} antes de continuar?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if resposta == QMessageBox.StandardButton.Cancel:
                return False
            if resposta == QMessageBox.StandardButton.Save:
                self.editor_tabs.setCurrentIndex(indice)
                if not self.save_file():
                    return False
        editor = aba.editor
        self.editor_tabs.removeTab(indice)
        del self._abas[indice]
        editor.deleteLater()
        if not self._abas:
            self._criar_aba(NEW_FILE_TEMPLATE.format(nome="Ola"), None)
        else:
            self._update_position()
            self.analysis.request(self.editor.toPlainText())
        return True

    def _marcar_aba_limpa(self, aba: _AbaEditor) -> None:
        aba.modificado = False
        aba.editor.document().setModified(False)

    def _mark_clean(self) -> None:
        """Marca a aba atual como não modificada (API da versão de aba única)."""
        aba = self._aba_atual()
        if aba is not None:
            self._marcar_aba_limpa(aba)
            self._atualizar_rotulo_da_aba(self.editor_tabs.indexOf(aba.editor))
        self._update_title()

    def _atualizar_rotulo_da_aba(self, indice: int) -> None:
        if not (0 <= indice < len(self._abas)):
            return
        aba = self._abas[indice]
        marcador = " *" if aba.modificado else ""
        self.editor_tabs.setTabText(indice, f"{aba.nome}{marcador}")

    def _trocar_aba(self, indice: int) -> None:
        aba = self._aba_atual()
        if aba is None:
            return
        self._update_position()
        self._update_title()
        self.analysis.request(aba.editor.toPlainText())
        if self.find_bar.isVisible() and self.find_bar.texto_busca():
            aba.editor.highlight_find(
                self.find_bar.texto_busca(), self.find_bar.diferenciar_maiusculas()
            )

    # --- Construcao da interface -------------------------------------------------

    def _build_docks(self) -> None:
        self.explorer = FileExplorer()
        self.dock_explorer = self._add_dock(
            "Explorador de arquivos",
            self.explorer,
            Qt.DockWidgetArea.LeftDockWidgetArea,
        )

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
        self.dock_output = self._add_dock(
            "Paineis de saida",
            self.output_tabs,
            Qt.DockWidgetArea.BottomDockWidgetArea,
        )

        self.dfa_tabs = QTabWidget()
        self.dfa_tabs.setObjectName("dfaTabs")
        self.dfa_tabs.addTab(self.token_classes_table, "Classes de tokens")
        self.dfa_tabs.addTab(self.dfa_states_table, "DFA - estados")
        self.dfa_tabs.addTab(self.dfa_transitions_table, "DFA - transicoes")
        self.dfa_tabs.addTab(self.grammar_table, "Gramatica")
        self.dock_dfa = self._add_dock(
            "Tokens e automato",
            self.dfa_tabs,
            Qt.DockWidgetArea.RightDockWidgetArea,
        )

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
        sfx: str = "button",
    ) -> QAction:
        action = QAction(text, self)
        # O som vem antes do slot: clicar num item que abre um dialogo
        # precisa soar no momento da abertura, nao quando ele fecha.
        if sfx == "button":
            action.triggered.connect(self._maybe_play_button_sfx)
        elif sfx == "compile":
            action.triggered.connect(self._maybe_play_compile_sfx)
        action.triggered.connect(slot)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        if tip:
            action.setStatusTip(tip)
        return action

    def _build_actions(self) -> None:
        self.action_new = self._action(
            "&Novo", self.new_file, QKeySequence.StandardKey.New, "Cria um programa de exemplo"
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
            "&Compilar", self.compile, "Ctrl+B", "Roda a analise lexica agora", sfx="compile"
        )
        self.action_generate = self._action(
            "Gerar &executavel",
            self.generate_executable,
            "F9",
            "Traduz o programa para C e gera um .exe com o TCC embutido",
            sfx="compile",
        )
        self.action_run = self._action(
            "&Executar executavel",
            self.run_executable,
            "F5",
            "Abre o .exe gerado em uma janela de console",
            sfx="compile",
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
        self.action_pin_project_theme = self._action(
            "Fixar tema para e&sta pasta",
            self.fixar_tema_projeto,
            "",
            "Aplica o tema atual a todos os arquivos desta pasta",
        )
        self.action_unpin_project_theme = self._action(
            "&Remover tema da pasta",
            self.remover_tema_projeto,
            "",
            "Deixa a pasta de novo no tema global",
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
        self.action_find = self._action(
            "&Localizar", self.mostrar_busca, "Ctrl+F", "Localizar no editor"
        )
        self.action_find_replace = self._action(
            "Localizar e &substituir",
            lambda: self.mostrar_busca(True),
            "Ctrl+H",
            "Localizar e substituir no editor",
        )

    def _build_menus(self) -> None:
        menu_file = self.menuBar().addMenu("&Arquivo")
        menu_file.addActions([self.action_new, self.action_open])
        self.menu_recentes = menu_file.addMenu("Recen&tes")
        self.menu_recentes.aboutToShow.connect(self._reconstruir_recentes)
        menu_file.addSeparator()
        menu_file.addActions([self.action_save, self.action_save_as])
        menu_file.addSeparator()
        menu_file.addAction(self.action_exit)

        menu_run = self.menuBar().addMenu("&Executar")
        menu_run.addAction(self.action_compile)
        menu_run.addAction(self.action_generate)
        menu_run.addAction(self.action_run)
        menu_run.addAction(self.action_clear_output)

        menu_tools = self.menuBar().addMenu("&Ferramentas")
        menu_tools.addAction(self.action_preferences)
        menu_tools.addAction(self.action_restore_defaults)
        menu_tools.addSeparator()
        menu_tools.addAction(self.action_pin_project_theme)
        menu_tools.addAction(self.action_unpin_project_theme)
        menu_tools.addSeparator()
        menu_tools.addActions(
            [self.action_zoom_in, self.action_zoom_out, self.action_zoom_reset]
        )
        menu_tools.addSeparator()
        menu_tools.addActions([self.action_find, self.action_find_replace])

        self.menu_view = self.menuBar().addMenu("&Exibir")
        self.menu_view.addAction(self.dock_explorer.toggleViewAction())
        self.menu_view.addAction(self.dock_output.toggleViewAction())
        self.menu_view.addAction(self.dock_dfa.toggleViewAction())
        self.menu_view.addSeparator()
        self.action_restore_layout = self._action(
            "&Restaurar layout padrao",
            self.restaurar_layout_padrao,
            "",
            "Devolve os paineis a disposicao original",
        )
        self.menu_view.addAction(self.action_restore_layout)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Principal")
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.addActions([self.action_new, self.action_open, self.action_save])
        toolbar.addSeparator()
        toolbar.addActions(
            [self.action_compile, self.action_generate, self.action_run]
        )

    def _build_status_bar(self) -> None:
        self.position_label = QLabel("Ln 1, Col 1")
        self.state_label = QLabel("Pronto")
        self.statusBar().addPermanentWidget(self.position_label)
        self.statusBar().addPermanentWidget(self.state_label)

    def _init_sfx(self) -> None:
        self._sfx_players: dict[str, QMediaPlayer] = {}
        self._sfx_outputs: dict[str, QAudioOutput] = {}
        if QMediaPlayer is not None:
            for name, path_func in (
                ("compile", sfx_compile_path),
                ("button", sfx_button_path),
                ("background", sfx_background_path),
            ):
                path = path_func()
                if path:
                    player = QMediaPlayer(self)
                    output = QAudioOutput(self)
                    player.setAudioOutput(output)
                    player.setSource(QUrl.fromLocalFile(path))
                    if name == "background":
                        player.setLoops(-1)
                    self._sfx_players[name] = player
                    self._sfx_outputs[name] = output

    def _sfx_ativos(self) -> bool:
        """So o tema Resident Evil tem sons de interface."""
        return self.settings.theme == THEME_RESIDENT_EVIL

    def _play_sfx(self, name: str) -> None:
        if not self._sfx_ativos():
            return
        player = self._sfx_players.get(name)
        if player is not None:
            try:
                player.setPosition(0)
                player.play()
            except RuntimeError:
                # sem backend de audio o Qt levanta RuntimeError: ignora
                pass

    def _maybe_play_button_sfx(self) -> None:
        self._play_sfx("button")

    def _maybe_play_compile_sfx(self) -> None:
        self._play_sfx("compile")

    def _maybe_start_bg_sfx(self) -> None:
        player = self._sfx_players.get("background")
        if player is not None:
            try:
                player.play()
            except RuntimeError:
                pass

    def _maybe_stop_bg_sfx(self) -> None:
        player = self._sfx_players.get("background")
        if player is not None:
            try:
                player.stop()
            except RuntimeError:
                pass

    def _connect(self) -> None:
        self.analysis.result_ready.connect(self._show_result)
        self.editor_tabs.currentChanged.connect(self._trocar_aba)
        self.explorer.pasta_escolhida.connect(self._definir_raiz_do_explorador)
        self.explorer.arquivo_escolhido.connect(self.abrir_caminho)
        self.find_bar.fechar.connect(self._fechar_busca)
        self.find_bar.procura_mudou.connect(self._realcar_busca)
        self.find_bar.aviso.connect(self._tratar_aviso_da_busca)

    # --- Arquivos e abas -----------------------------------------------------------

    def new_file(self) -> None:
        self._criar_aba(NEW_FILE_TEMPLATE.format(nome="Ola"), None)

    def open_file(self) -> None:
        path = FileService.open_dialog(self)
        if path is None:
            return
        self.abrir_caminho(path)

    def abrir_caminho(self, path: str) -> None:
        caminho = str(Path(path))
        for indice, aba in enumerate(self._abas):
            if aba.caminho and str(Path(aba.caminho)) == caminho:
                self.editor_tabs.setCurrentIndex(indice)
                return
        try:
            content = FileService.read(caminho)
        except OSError as error:
            QMessageBox.critical(
                self, "Erro ao abrir", f"Não foi possível ler o arquivo:\n{error}"
            )
            return
        self._criar_aba(content, caminho)
        self._log(f"Abrido: {caminho}")
        self._registrar_recente(caminho)
        self._aplicar_tema_do_projeto(caminho)
        self.explorer.marcar_arquivo_aberto(caminho)

    def save_file(self) -> bool:
        aba = self._aba_atual()
        if aba is None:
            return False
        if aba.caminho is None:
            return self.save_file_as()
        return self._write_to(aba.caminho)

    def save_file_as(self) -> bool:
        aba = self._aba_atual()
        if aba is None:
            return False
        path = FileService.save_dialog(self, aba.caminho or "")
        if path is None:
            return False
        return self._write_to(path)

    def _write_to(self, path: str) -> bool:
        aba = self._aba_atual()
        if aba is None:
            return False
        try:
            FileService.write(path, aba.editor.toPlainText())
        except OSError as error:
            QMessageBox.critical(
                self, "Erro ao salvar", f"Não foi possível salvar o arquivo:\n{error}"
            )
            return False
        aba.caminho = str(Path(path))
        self._marcar_aba_limpa(aba)
        indice = self.editor_tabs.indexOf(aba.editor)
        self._atualizar_rotulo_da_aba(indice)
        self.editor_tabs.setTabToolTip(indice, aba.caminho)
        self._update_title()
        self._log(f"Salvo: {aba.caminho}")
        self._registrar_recente(aba.caminho)
        self.explorer.marcar_arquivo_aberto(aba.caminho)
        return True

    def _confirm_discard(self) -> bool:
        aba = self._aba_atual()
        if aba is None or not aba.modificado:
            return True
        answer = QMessageBox.question(
            self,
            f"{LANGUAGE_NAME} - IDE",
            f"Salvar as alterações em {aba.nome} antes de continuar?",
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
        aba = self._aba_atual()
        return aba.nome if aba else UNSAVED_TITLE

    def _update_title(self) -> None:
        marker = " *" if self._modified else ""
        self.setWindowTitle(f"{self._display_name()}{marker} - {LANGUAGE_NAME} - IDE")

    # --- Recentes --------------------------------------------------------------------

    def _registrar_recente(self, caminho: str) -> None:
        alvo = str(Path(caminho))
        lista = [item for item in self.settings.recent_files if str(Path(item)) != alvo]
        lista.insert(0, alvo)
        self.settings.recent_files = lista[:RECENT_LIMIT]
        if not save_settings(self.settings, self._settings_path):
            self._log("Nao foi possivel gravar as preferencias.")

    def _reconstruir_recentes(self) -> None:
        self.menu_recentes.clear()
        if not self.settings.recent_files:
            acao = self.menu_recentes.addAction("(vazio)")
            acao.setEnabled(False)
            return
        for caminho in self.settings.recent_files:
            acao = self.menu_recentes.addAction(caminho)
            acao.triggered.connect(
                lambda checked=False, alvo=caminho: self.abrir_caminho(alvo)
            )

    # --- Explorador de arquivos --------------------------------------------------------

    def _raiz_inicial(self) -> str:
        if self.settings.explorer_root and Path(self.settings.explorer_root).is_dir():
            return self.settings.explorer_root
        aba = self._aba_atual()
        if aba is not None and aba.caminho:
            return str(Path(aba.caminho).parent)
        return str(Path.cwd())

    def _definir_raiz_do_explorador(self, caminho: str) -> None:
        self.explorer.definir_raiz(caminho)
        self.settings.explorer_root = self.explorer.raiz()
        if not save_settings(self.settings, self._settings_path):
            self._log("Nao foi possivel gravar as preferencias.")

    # --- Temas por pasta ---------------------------------------------------------------

    def _pasta_atual(self) -> str | None:
        aba = self._aba_atual()
        if aba is None or not aba.caminho:
            return None
        return str(Path(aba.caminho).parent)

    def fixar_tema_projeto(self) -> None:
        pasta = self._pasta_atual()
        if pasta is None:
            self._log("Salve o arquivo antes de fixar um tema para a pasta.")
            return
        self.settings.project_themes[pasta] = self.settings.theme
        if not save_settings(self.settings, self._settings_path):
            self._log("Nao foi possivel gravar as preferencias.")
            return
        self._log(f"Tema '{self.settings.theme}' fixado para a pasta {pasta}.")

    def remover_tema_projeto(self) -> None:
        pasta = self._pasta_atual()
        if pasta is None or pasta not in self.settings.project_themes:
            self._log("Esta pasta nao tem tema proprio.")
            return
        del self.settings.project_themes[pasta]
        if not save_settings(self.settings, self._settings_path):
            self._log("Nao foi possivel gravar as preferencias.")
            return
        self._log(f"Tema proprio removido da pasta {pasta}.")

    def _aplicar_tema_do_projeto(self, caminho: str) -> None:
        pasta = str(Path(caminho).parent)
        tema = self.settings.project_themes.get(pasta)
        if tema and tema in THEME_CHOICES and tema != self.settings.theme:
            configuracoes = self.settings.copy()
            configuracoes.theme = tema
            self.commit_settings(configuracoes)
            self._log(f"Tema do projeto aplicado: {tema}.")

    # --- Busca e substituicao -----------------------------------------------------------

    def mostrar_busca(self, com_substituicao: bool = False) -> None:
        texto = ""
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selecionado = cursor.selectedText()
            if "\u2029" not in selecionado:
                texto = selecionado
        self.find_bar.mostrar(com_substituicao, texto)

    def _fechar_busca(self) -> None:
        self.find_bar.esconder()
        self.editor.clearFocus()
        self.editor.setFocus()

    def _realcar_busca(self, texto: str, sensivel: bool) -> None:
        editor = self.editor
        if not texto:
            editor.clear_find_highlight()
            self.find_bar.mostrar_aviso("")
            return
        editor.highlight_find(texto, sensivel)
        self.find_bar.mostrar_aviso("")

    def _tratar_aviso_da_busca(self, comando: str) -> None:
        if not comando:
            self.find_bar.mostrar_aviso("")
            return
        editor = self.editor
        busca = self.find_bar.texto_busca()
        sensivel = self.find_bar.diferenciar_maiusculas()
        if not busca:
            return
        if comando == "proxima":
            if not editor.find_next(busca, False, sensivel):
                self.find_bar.mostrar_aviso("nao encontrado")
        elif comando == "anterior":
            if not editor.find_next(busca, True, sensivel):
                self.find_bar.mostrar_aviso("nao encontrado")
        elif comando == "substituir":
            if editor.replace_current(busca, self.find_bar.texto_substituir(), sensivel):
                editor.find_next(busca, False, sensivel)
                self.find_bar.mostrar_aviso("")
            else:
                self.find_bar.mostrar_aviso("nao encontrado")
        elif comando == "substituir_tudo":
            total = editor.replace_all(
                busca, self.find_bar.texto_substituir(), sensivel
            )
            self.find_bar.mostrar_aviso(f"{total} substituicao(oes)")

    # --- Analise ------------------------------------------------------------------------

    def compile(self) -> None:
        result = self.analysis.analyze_now(self.editor.toPlainText())
        self._log(self._summarize(result))
        self.output_tabs.setCurrentWidget(
            self.errors_table if result.has_any_errors else self.output_console
        )

    def _on_text_changed(self) -> None:
        aba = self._aba_atual()
        if aba is None:
            return
        aba.modificado = True
        indice = self.editor_tabs.indexOf(aba.editor)
        self._atualizar_rotulo_da_aba(indice)
        self._update_title()
        self.analysis.request(aba.editor.toPlainText())

    def _update_position(self) -> None:
        cursor = self.editor.textCursor()
        self.position_label.setText(
            f"Ln {cursor.blockNumber() + 1}, Col {cursor.positionInBlock() + 1}"
        )

    def _summarize(self, result: AnalysisResult) -> str:
        if result.has_any_errors:
            return f"Analise concluida com {len(result.all_errors)} erro(s) e {result.token_count} token(s)."
        return f"Analise concluida sem erros: {result.token_count} token(s)."

    def _palavras_do_completar(self, simbolos) -> list[str]:
        palavras = list(PALAVRAS_RESERVADAS)
        palavras.extend(PALAVRAS_DE_COMPLETAR)
        palavras.extend(s.identifier for s in simbolos)
        return palavras

    def _show_result(self, result: AnalysisResult) -> None:
        editor = self.editor
        editor.set_error_marks(list(result.all_errors))
        editor.set_tokens(result.tokens)
        editor.set_completer_words(self._palavras_do_completar(result.symbols))

        self.errors_table.set_rows(
            [(e.line, e.column, e.lexeme, e.message) for e in result.all_errors]
        )
        self.warnings_table.set_rows(
            [(w.line, w.column, w.message) for w in result.all_warnings]
        )
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
            f"{len(result.all_errors)} erro(s)"
            if result.has_any_errors
            else f"{result.token_count} token(s)"
        )

    def _update_count_labels(self, result: AnalysisResult) -> None:
        self.output_tabs.setTabText(TAB_ERRORS, f"Erros ({len(result.all_errors)})")
        self.output_tabs.setTabText(
            TAB_WARNINGS, f"Avisos ({len(result.all_warnings)})"
        )
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

    # --- Geracao e execucao do executavel -------------------------------------------------

    def _garantir_arquivo_salvo(self) -> bool:
        aba = self._aba_atual()
        if aba is None:
            return False
        if aba.caminho is None:
            return self.save_file_as()
        if aba.modificado:
            return self.save_file()
        return True

    def generate_executable(self) -> None:
        if not self._garantir_arquivo_salvo():
            return
        resultado = self.analysis.analyze_now(self.editor.toPlainText())
        self._log(self._summarize(resultado))
        if resultado.has_any_errors:
            self.output_tabs.setCurrentWidget(self.errors_table)
            return
        destino = Path(self._current_path or "").with_suffix(".exe")
        try:
            codigo = traduzir(resultado.tokens)
        except ErroDeTraducao as erro:
            self._log(f"Geracao de C interrompida: {erro}")
            return
        ok, mensagem = compilar(codigo, destino)
        self._log(mensagem)
        if ok:
            self.output_tabs.setCurrentWidget(self.output_console)

    def run_executable(self) -> None:
        aba = self._aba_atual()
        if aba is None or not aba.caminho:
            self._log("Salve o programa antes de executar.")
            return
        destino = Path(aba.caminho).with_suffix(".exe")
        if not destino.is_file():
            self.generate_executable()
        if not destino.is_file():
            return
        if executar(destino):
            self._log(f"Executando: {destino}")
        else:
            self._log(f"Nao foi possivel executar {destino}.")

    # --- Preferencias -----------------------------------------------------------------------

    def apply_settings(self, settings: Settings) -> None:
        self.settings = settings

        apply_theme(QApplication.instance(), settings.theme)

        for aba in self._abas:
            self._aplicar_ao_editor(aba.editor)

        self.output_console.apply_font(settings.font_family, settings.font_size)
        self.output_console.apply_colors(
            settings.console_background, settings.console_foreground
        )
        if settings.theme == THEME_RESIDENT_EVIL:
            self._maybe_start_bg_sfx()
        else:
            self._maybe_stop_bg_sfx()

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

    def _zoom_editor(self, delta: int) -> None:
        self._set_font_size(self.settings.font_size + delta)

    def zoom_in(self) -> None:
        self._set_font_size(self.settings.font_size + 1)

    def zoom_out(self) -> None:
        self._set_font_size(self.settings.font_size - 1)

    def zoom_reset(self) -> None:
        self._set_font_size(Settings().font_size)

    # --- Exibir e geometria ------------------------------------------------------------------

    def restaurar_layout_padrao(self) -> None:
        self.restoreGeometry(self._geometria_padrao)
        self.restoreState(self._estado_padrao)
        self.settings.window_geometry = ""
        self.settings.window_state = ""
        if not save_settings(self.settings, self._settings_path):
            self._log("Nao foi possivel gravar as preferencias.")
        self._log("Layout padrao restaurado.")

    def _restaurar_geometria_salva(self) -> None:
        if self.settings.window_geometry:
            self.restoreGeometry(
                QByteArray.fromBase64(self.settings.window_geometry.encode())
            )
        if self.settings.window_state:
            self.restoreState(
                QByteArray.fromBase64(self.settings.window_state.encode())
            )

    def _salvar_geometria(self) -> None:
        self.settings.window_geometry = bytes(self.saveGeometry().toBase64()).decode()
        self.settings.window_state = bytes(self.saveState().toBase64()).decode()
        if not save_settings(self.settings, self._settings_path):
            self._log("Nao foi possivel gravar as preferencias.")

    # --- Saida -------------------------------------------------------------------------------

    def _log(self, message: str) -> None:
        self.output_console.append_line(message)

    def clear_output(self) -> None:
        self.output_console.clear_output()

    def closeEvent(self, event: QCloseEvent) -> None:
        for indice, aba in enumerate(list(self._abas)):
            if not aba.modificado:
                continue
            resposta = QMessageBox.question(
                self,
                f"{LANGUAGE_NAME} - IDE",
                f"Salvar as alterações em {aba.nome} antes de continuar?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if resposta == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if resposta == QMessageBox.StandardButton.Save:
                self.editor_tabs.setCurrentIndex(indice)
                if not self.save_file():
                    event.ignore()
                    return
        self._salvar_geometria()
        event.accept()
