"""Testes das melhorias de qualidade de vida da interface.

Cobrem: menu Exibir, explorador de arquivos, sons so no tema Resident Evil
(inclusive a ordem som-antes-do-dialogo), recentes, busca/substituicao,
zoom pela roda do mouse, geometria persistida, temas por pasta, abas e a
geracao de executavel pela janela principal.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from src.app import build_lexer
from src.codegen import tcc_disponivel
from src.editor.code_editor import DEFAULT_BACKGROUND_OPACITY, CodeEditor
from src.main_window import MainWindow
from src.panels.file_explorer import FileExplorer
from src.services.lexer_service import Symbol
from src.settings import (
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    THEME_DARK,
    THEME_RESIDENT_EVIL,
    Settings,
    load_settings,
)

requer_tcc = pytest.mark.skipif(
    not tcc_disponivel(), reason="TCC embutido ausente em tools/tcc"
)

PROGRAMA = "programa Demo;\nvar total: integer;\nbegin\ntotal := 1;\nend.\n"


@pytest.fixture(scope="module")
def app() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    return instance


@pytest.fixture
def janela(app: QApplication, tmp_path) -> MainWindow:
    window = MainWindow(build_lexer(), tmp_path / "preferencias.json")
    yield window
    for aba in window._abas:
        window._marcar_aba_limpa(aba)  # evita dialogo de salvamento no teardown
    window.close()
    window.deleteLater()
    QApplication.processEvents()


class _PlayerFalso:
    """Substitui o QMediaPlayer e registra quando toca."""

    def __init__(self, registro: list[str]) -> None:
        self.registro = registro

    def setPosition(self, _pos: int) -> None:
        pass

    def play(self) -> None:
        self.registro.append("sfx")

    def stop(self) -> None:
        self.registro.append("stop")


# --- Padroes -----------------------------------------------------------------


def test_opacidade_padrao_e_15() -> None:
    assert Settings().background_image_opacity == 15
    assert DEFAULT_BACKGROUND_OPACITY == 15


def test_campos_novos_existem_no_settings() -> None:
    config = Settings()
    assert config.window_geometry == ""
    assert config.window_state == ""
    assert config.explorer_root == ""
    assert config.recent_files == []
    assert config.project_themes == {}


# --- Menu Exibir ---------------------------------------------------------------


def test_menu_exibir_lista_todos_os_docks(janela: MainWindow) -> None:
    menu = janela.menu_view
    textos = [acao.text().replace("&", "") for acao in menu.actions()]
    for dock in (janela.dock_explorer, janela.dock_output, janela.dock_dfa):
        acao = dock.toggleViewAction()
        assert acao.text() in textos
        assert acao.isCheckable()
    assert "Restaurar layout padrao" in textos


def test_menu_exibir_esconde_e_mostra_dock(janela: MainWindow) -> None:
    janela.show()
    assert janela.dock_explorer.isVisible()
    janela.dock_explorer.toggleViewAction().trigger()
    assert not janela.dock_explorer.isVisible()
    janela.dock_explorer.toggleViewAction().trigger()
    assert janela.dock_explorer.isVisible()


def test_restaurar_layout_limpa_geometria_salva(janela: MainWindow) -> None:
    janela._salvar_geometria()
    assert janela.settings.window_geometry
    janela.restaurar_layout_padrao()
    assert janela.settings.window_geometry == ""
    assert janela.settings.window_state == ""


def test_geometria_e_persistida_entre_sessoes(app: QApplication, tmp_path) -> None:
    caminho = tmp_path / "pref_geo.json"
    primeira = MainWindow(build_lexer(), caminho)
    primeira.resize(987, 654)
    primeira._salvar_geometria()
    primeira.close()

    salvo = load_settings(caminho)
    assert salvo.window_geometry
    assert salvo.window_state

    segunda = MainWindow(build_lexer(), caminho)
    assert segunda.settings.window_geometry == salvo.window_geometry
    segunda.close()
    segunda.deleteLater()
    QApplication.processEvents()


# --- Explorador de arquivos -----------------------------------------------------


def _montar_pasta(base: Path) -> Path:
    raiz = base / "projeto"
    (raiz / "sub").mkdir(parents=True)
    (raiz / "a.pas").write_text("programa A;\nbegin\nend.\n", encoding="utf-8")
    (raiz / "sub" / "b.pas").write_text("programa B;\nbegin\nend.\n", encoding="utf-8")
    (raiz / ".oculto").write_text("nao aparece", encoding="utf-8")
    return raiz


def test_explorador_lista_ignora_ocultos_e_carrega_subpastas(
    app: QApplication, tmp_path
) -> None:
    raiz = _montar_pasta(tmp_path)
    (raiz / "outra").mkdir()
    explorador = FileExplorer()
    explorador.definir_raiz(str(raiz))

    nomes = [
        explorador.arvore.topLevelItem(i).text(0)
        for i in range(explorador.arvore.topLevelItemCount())
    ]
    assert nomes == ["outra", "sub", "a.pas"]  # pastas primeiro, sem .oculto

    # a primeira pasta da lista abre sozinha (mesmo vazia, nao tem filhos)
    assert explorador.arvore.topLevelItem(0).childCount() == 0
    # ...e as demais cargam os filhos so quando expandidas (carga preguicosa)
    item_sub = explorador.arvore.topLevelItem(1)
    assert item_sub.childCount() == 0
    explorador._expandir(item_sub)
    assert item_sub.childCount() == 1
    assert item_sub.child(0).text(0) == "b.pas"


def test_explorador_emite_arquivo_ao_duplo_clique(
    app: QApplication, tmp_path
) -> None:
    raiz = _montar_pasta(tmp_path)
    explorador = FileExplorer()
    explorador.definir_raiz(str(raiz))
    recebidos: list[str] = []
    explorador.arquivo_escolhido.connect(recebidos.append)

    item_arquivo = explorador.arvore.topLevelItem(1)
    explorador._abrir_item(item_arquivo)
    assert recebidos == [str(raiz / "a.pas")]


def test_explorador_marca_arquivo_aberto_em_negrito(
    app: QApplication, tmp_path
) -> None:
    raiz = _montar_pasta(tmp_path)
    explorador = FileExplorer()
    explorador.definir_raiz(str(raiz))
    explorador.marcar_arquivo_aberto(str(raiz / "a.pas"))

    item_arquivo = explorador.arvore.topLevelItem(1)
    assert item_arquivo.font(0).bold()
    item_sub = explorador.arvore.topLevelItem(0)
    assert not item_sub.font(0).bold()


def test_janela_persiste_raiz_do_explorador(janela: MainWindow, tmp_path) -> None:
    raiz = _montar_pasta(tmp_path)
    janela._definir_raiz_do_explorador(str(raiz))
    assert janela.explorer.raiz() == str(raiz)
    salvo = load_settings(janela._settings_path)
    assert salvo.explorer_root == str(raiz)


def test_duplo_clique_no_explorador_abre_na_janela(
    janela: MainWindow, tmp_path
) -> None:
    raiz = _montar_pasta(tmp_path)
    janela._definir_raiz_do_explorador(str(raiz))
    item_arquivo = janela.explorer.arvore.topLevelItem(1)
    janela.explorer._abrir_item(item_arquivo)
    assert janela._current_path == str(raiz / "a.pas")
    assert janela._display_name() == "a.pas"
    assert item_arquivo.font(0).bold()  # explorador marca o arquivo aberto


# --- Sons so no tema Resident Evil ---------------------------------------------


def test_sons_desligados_fora_do_tema_resident_evil(janela: MainWindow) -> None:
    registro: list[str] = []
    janela._sfx_players["button"] = _PlayerFalso(registro)  # type: ignore[assignment]
    janela.settings.theme = THEME_DARK
    janela._maybe_play_button_sfx()
    assert registro == []


def test_sons_ligados_no_tema_resident_evil(janela: MainWindow) -> None:
    registro: list[str] = []
    configuracoes = janela.settings.copy()
    configuracoes.theme = THEME_RESIDENT_EVIL
    janela.apply_settings(configuracoes)
    janela._sfx_players["button"] = _PlayerFalso(registro)  # type: ignore[assignment]
    janela._maybe_play_button_sfx()
    assert registro == ["sfx"]


def test_som_toca_antes_de_abrir_dialogo(janela: MainWindow, monkeypatch) -> None:
    registro: list[str] = []
    configuracoes = janela.settings.copy()
    configuracoes.theme = THEME_RESIDENT_EVIL
    janela.apply_settings(configuracoes)
    janela._sfx_players["button"] = _PlayerFalso(registro)  # type: ignore[assignment]

    class DialogoFalso:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def exec(self) -> int:
            registro.append("dialogo")
            return QDialog.DialogCode.Rejected

        def settings(self) -> Settings:  # pragma: no cover - nunca chamado
            return Settings()

    monkeypatch.setattr("src.main_window.SettingsDialog", DialogoFalso)
    janela.action_preferences.trigger()
    assert registro == ["sfx", "dialogo"]


# --- Arquivos recentes -----------------------------------------------------------


def test_recentes_mantem_os_ultimos_cinco(janela: MainWindow, tmp_path) -> None:
    for indice in range(7):
        janela._registrar_recente(str(tmp_path / f"arq{indice}.pas"))
    assert len(janela.settings.recent_files) == 5
    assert janela.settings.recent_files[0] == str(tmp_path / "arq6.pas")
    salvo = load_settings(janela._settings_path)
    assert salvo.recent_files == janela.settings.recent_files


def test_recentes_repetido_vai_para_o_topo(janela: MainWindow, tmp_path) -> None:
    janela._registrar_recente(str(tmp_path / "a.pas"))
    janela._registrar_recente(str(tmp_path / "b.pas"))
    janela._registrar_recente(str(tmp_path / "a.pas"))
    assert janela.settings.recent_files[:2] == [
        str(tmp_path / "a.pas"),
        str(tmp_path / "b.pas"),
    ]


def test_menu_de_recentes_mostra_e_abre(janela: MainWindow, tmp_path) -> None:
    arquivo = tmp_path / "recente.pas"
    arquivo.write_text(PROGRAMA, encoding="utf-8")
    janela._registrar_recente(str(arquivo))
    janela._reconstruir_recentes()
    acoes = janela.menu_recentes.actions()
    assert [acao.text() for acao in acoes] == [str(arquivo)]
    acoes[0].trigger()
    assert janela._current_path == str(arquivo)


def test_menu_de_recentes_vazio_mostra_aviso(janela: MainWindow) -> None:
    janela.settings.recent_files = []
    janela._reconstruir_recentes()
    acoes = janela.menu_recentes.actions()
    assert len(acoes) == 1
    assert acoes[0].text() == "(vazio)"
    assert not acoes[0].isEnabled()


# --- Busca e substituicao ----------------------------------------------------------


def test_barra_de_busca_fica_oculta_por_padrao(janela: MainWindow) -> None:
    assert not janela.find_bar.isVisible()


def test_mostrar_busca_preenche_com_selecao(janela: MainWindow) -> None:
    janela.show()
    janela.editor.setPlainText("abc xyz abc")
    cursor = janela.editor.textCursor()
    cursor.setPosition(4)
    cursor.setPosition(7, QTextCursor.MoveMode.KeepAnchor)
    janela.editor.setTextCursor(cursor)

    janela.mostrar_busca()
    assert janela.find_bar.isVisible()
    assert janela.find_bar.texto_busca() == "xyz"
    assert not janela.find_bar.campo_substituir.isVisibleTo(janela.find_bar)

    janela.mostrar_busca(True)
    assert janela.find_bar.campo_substituir.isVisibleTo(janela.find_bar)


def test_busca_avisa_quando_nao_encontra(janela: MainWindow) -> None:
    janela.editor.setPlainText("programa X;\nbegin\nend.\n")
    janela.find_bar.campo_busca.setText("zzz")
    janela._tratar_aviso_da_busca("proxima")
    assert janela.find_bar.rotulo.text() == "nao encontrado"


def test_substituir_tudo_conta_ocorrencias(janela: MainWindow) -> None:
    janela.editor.setPlainText("a a a")
    janela.find_bar.campo_busca.setText("a")
    janela.find_bar.campo_substituir.setText("b")
    janela._tratar_aviso_da_busca("substituir_tudo")
    assert janela.editor.toPlainText() == "b b b"
    assert "3 substituicao" in janela.find_bar.rotulo.text()


def test_substituir_um_por_um(janela: MainWindow) -> None:
    janela.editor.setPlainText("x x x")
    janela.editor.moveCursor(QTextCursor.MoveOperation.Start)
    janela.find_bar.campo_busca.setText("x")
    janela.find_bar.campo_substituir.setText("y")
    janela._tratar_aviso_da_busca("proxima")  # seleciona a primeira ocorrencia
    janela._tratar_aviso_da_busca("substituir")
    assert janela.editor.toPlainText().startswith("y")


def test_fechar_busca_esconde_a_barra(janela: MainWindow) -> None:
    janela.show()
    janela.mostrar_busca()
    assert janela.find_bar.isVisible()
    janela._fechar_busca()
    assert not janela.find_bar.isVisible()


# --- Zoom --------------------------------------------------------------------------


def test_roda_do_mouse_muda_o_zoom(janela: MainWindow) -> None:
    inicial = janela.settings.font_size
    janela.editor.zoom_requested.emit(1)
    assert janela.settings.font_size == inicial + 1
    janela.editor.zoom_requested.emit(-1)
    assert janela.settings.font_size == inicial


def test_zoom_respeita_limites(janela: MainWindow) -> None:
    for _ in range(80):
        janela.zoom_in()
    assert janela.settings.font_size <= MAX_FONT_SIZE
    for _ in range(160):
        janela.zoom_out()
    assert janela.settings.font_size >= MIN_FONT_SIZE


# --- Temas por pasta -----------------------------------------------------------------


def test_fixar_e_remover_tema_da_pasta(janela: MainWindow, tmp_path) -> None:
    arquivo = tmp_path / "projeto" / "x.pas"
    arquivo.parent.mkdir()
    arquivo.write_text(PROGRAMA, encoding="utf-8")
    janela.abrir_caminho(str(arquivo))

    configuracoes = janela.settings.copy()
    configuracoes.theme = THEME_DARK
    janela.commit_settings(configuracoes)

    janela.fixar_tema_projeto()
    salvo = load_settings(janela._settings_path)
    assert salvo.project_themes[str(arquivo.parent)] == THEME_DARK

    janela.remover_tema_projeto()
    salvo = load_settings(janela._settings_path)
    assert str(arquivo.parent) not in salvo.project_themes


def test_tema_da_pasta_e_aplicado_ao_abrir(janela: MainWindow, tmp_path) -> None:
    pasta = tmp_path / "estilo"
    pasta.mkdir()
    arquivo = pasta / "y.pas"
    arquivo.write_text(PROGRAMA, encoding="utf-8")

    configuracoes = janela.settings.copy()
    configuracoes.theme = THEME_DARK
    janela.commit_settings(configuracoes)
    janela.settings.project_themes[str(pasta)] = THEME_DARK
    configuracoes_claras = janela.settings.copy()
    configuracoes_claras.theme = "light"
    janela.commit_settings(configuracoes_claras)
    assert janela.settings.theme == "light"

    janela.abrir_caminho(str(arquivo))
    assert janela.settings.theme == THEME_DARK


# --- Abas ------------------------------------------------------------------------------


def test_novo_arquivo_abre_uma_aba(janela: MainWindow) -> None:
    inicial = janela.editor_tabs.count()
    janela.new_file()
    assert janela.editor_tabs.count() == inicial + 1


def test_editor_reflete_a_aba_atual(janela: MainWindow) -> None:
    janela.new_file()
    aba_nova = janela.editor
    janela.editor_tabs.setCurrentIndex(0)
    assert janela.editor is not aba_nova


def test_aba_modificada_mostra_marcador(janela: MainWindow) -> None:
    janela.editor.insertPlainText("x")
    assert janela._modified
    assert "*" in janela.windowTitle()
    assert "*" in janela.editor_tabs.tabText(janela.editor_tabs.currentIndex())


def test_fechar_aba_modificada_pergunta(janela: MainWindow, monkeypatch) -> None:
    janela.editor.insertPlainText("x")
    chamadas: list[str] = []

    def responder(*_args, **_kwargs):
        chamadas.append("perguntou")
        return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(QMessageBox, "question", responder)
    indice = janela.editor_tabs.currentIndex()
    assert not janela._fechar_aba(indice)
    assert chamadas == ["perguntou"]


def test_sempre_restama_pelo_menos_uma_aba(janela: MainWindow) -> None:
    while janela.editor_tabs.count() > 1:
        janela._fechar_aba(janela.editor_tabs.count() - 1)
    assert janela.editor_tabs.count() == 1
    janela._fechar_aba(0)  # fechar a ultima aba cria outra no lugar
    assert janela.editor_tabs.count() == 1


# --- Completar automatico ---------------------------------------------------------------


def test_editor_aceita_foco(janela: MainWindow) -> None:
    # Regressao: o focusPolicy do popup do autocompletar repassa ao editor
    # (o popup tem o editor como focus proxy); setar NoFocus no popup deixava
    # o editor incapaz de receber foco e o teclado nao chegava a ele.
    editor_novo = CodeEditor()
    assert editor_novo.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert janela.editor.focusPolicy() == Qt.FocusPolicy.StrongFocus


def test_palavras_de_completar_incluem_reservadas_e_simbolos(
    janela: MainWindow,
) -> None:
    palavras = janela._palavras_do_completar(
        [Symbol(identifier="contador", kind="variavel", type="integer")]
    )
    assert "programa" in palavras
    assert "writeln" in palavras
    assert "contador" in palavras


def test_analise_alimenta_o_completar(janela: MainWindow) -> None:
    janela.editor.setPlainText(PROGRAMA)
    resultado = janela.analysis.analyze_now(PROGRAMA)
    janela._show_result(resultado)
    modelo = janela.editor._completer.model()
    textos = [modelo.data(modelo.index(i)) for i in range(modelo.rowCount())]
    assert "total" in textos


# --- Geracao de executavel pela janela ----------------------------------------------------


def test_menu_executar_tem_acao_unica(janela: MainWindow) -> None:
    # "Gerar executavel" virou parte do proprio Executar (F5); sem F9
    assert not hasattr(janela, "action_generate")
    assert janela.action_run.shortcut().toString() == "F5"
    assert "Executar" in janela.action_run.text()


@requer_tcc
def test_generate_executable_produz_exe(janela: MainWindow, tmp_path) -> None:
    arquivo = tmp_path / "ola.pas"
    arquivo.write_text(
        "programa Ola;\nbegin\nwriteln('oi');\nend.\n", encoding="utf-8"
    )
    janela.abrir_caminho(str(arquivo))
    janela.generate_executable()
    assert arquivo.with_suffix(".exe").is_file()
    assert arquivo.with_suffix(".c").is_file()


@requer_tcc
def test_generate_executable_para_com_erro_semantico(
    janela: MainWindow, tmp_path
) -> None:
    arquivo = tmp_path / "quebrado.pas"
    arquivo.write_text("programa Q;\nbegin\nx := 1;\nend.\n", encoding="utf-8")
    janela.abrir_caminho(str(arquivo))
    janela.generate_executable()
    assert not arquivo.with_suffix(".exe").is_file()


def test_executar_sem_exe_gera_antes(janela: MainWindow, tmp_path, monkeypatch) -> None:
    arquivo = tmp_path / "rodar.pas"
    arquivo.write_text(PROGRAMA, encoding="utf-8")
    janela.abrir_caminho(str(arquivo))
    assert not arquivo.with_suffix(".exe").is_file()

    chamados: list[str] = []
    monkeypatch.setattr(janela, "generate_executable", lambda: chamados.append("gerou"))
    monkeypatch.setattr("src.main_window.executar", lambda _destino: True)
    janela.run_executable()
    assert chamados == ["gerou"]  # gera antes de tentar rodar


def test_executar_sem_arquivo_salvo_avisa(janela: MainWindow) -> None:
    # a aba atual e um arquivo novo sem caminho: nada para executar
    registros: list[str] = []
    janela._log = registros.append  # type: ignore[method-assign]
    janela.run_executable()
    assert registros == ["Salve o programa antes de executar."]
