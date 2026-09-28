
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.app import create_window  # noqa: E402
from src.config import LANGUAGE_NAME  # noqa: E402
from src.main_window import TAB_ERRORS, TAB_TOKENS  # noqa: E402
from src.services.file_service import FileService  # noqa: E402
from src.settings import (
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    load_settings,
    save_settings,
)  # noqa: E402
from src.theme import remember_system_appearance  # noqa: E402
from src.services.lexer_service import (  # noqa: E402
    AnalysisResult,
    DfaState,
    DfaTransition,
    LexicalError,
    Symbol,
    Token,
    TokenClass,
    Warning,
)


class FakeLexer:

    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, source: str) -> AnalysisResult:
        self.calls += 1
        if not source:
            return AnalysisResult()
        return AnalysisResult(
            tokens=(
                Token("PROGRAMA", "programa", 1, 1),
                Token("IDENTIFICADOR", "Ola", 1, 9),
                Token("PONTO_E_VIRGULA", ";", 1, 12),
            ),
            errors=(LexicalError(2, 3, "simbolo invalido", "@", 1),),
            warnings=(Warning(3, 1, "instrucao sem efeito"),),
            symbols=(Symbol("Ola", "programa", "", "", 1),),
            token_classes=(
                TokenClass("IDENTIFICADOR", "[A-Za-z][A-Za-z0-9_]{0,14}", "ate 15 caracteres"),
            ),
            dfa_states=(DfaState("q0", False), DfaState("q1", True, "IDENTIFICADOR")),
            dfa_transitions=(DfaTransition("q0", "letra", "q1"),),
        )


def check(condition: bool, label: str) -> None:
    print(f"{'ok  ' if condition else 'FALHA'} {label}")
    if not condition:
        raise AssertionError(label)


def main() -> int:
    app = QApplication.instance() or QApplication([])

    tmp_dir = tempfile.TemporaryDirectory()
    settings_path = Path(tmp_dir.name) / "settings.json"

    window = create_window(settings_path=settings_path)
    window.show()
    app.processEvents()
    check(window.editor.blockCount() > 0, "editor abriu com o template do programa")
    check(window.editor.line_number_area_width() > 0, "area de numeracao tem largura")
    check(window.windowTitle().startswith("sem titulo"), "titulo mostra 'sem titulo' em arquivo novo")
    check(LANGUAGE_NAME in window.windowTitle(), "titulo contem o nome da linguagem")

    cursor = window.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Down)
    window.editor.setTextCursor(cursor)
    app.processEvents()
    check("Ln" in window.position_label.text(), "barra de status mostra Ln/Col")

    window.analysis.set_lexer(FakeLexer())
    window.editor.setPlainText("programa Ola;\n@\n")
    window.compile()
    app.processEvents()
    check(window.tokens_table.rowCount() == 3, "aba Tokens recebeu 3 tokens")
    check(window.errors_table.rowCount() == 1, "aba Erros recebeu 1 erro")
    check(window.warnings_table.rowCount() == 1, "aba Avisos recebeu 1 aviso")
    check(window.symbols_table.rowCount() == 1, "aba Tabela de simbolos recebeu 1 entrada")
    check(window.token_classes_table.rowCount() == 1, "aba Classes de tokens recebeu 1 classe")
    check(window.dfa_states_table.rowCount() == 2, "aba DFA - estados recebeu 2 estados")
    check(window.dfa_transitions_table.rowCount() == 1, "aba DFA - transicoes recebeu 1 transicao")
    check(window.output_tabs.tabText(TAB_TOKENS) == "Tokens (3)", "titulo da aba Tokens mostra a contagem")
    check(window.output_tabs.tabText(TAB_ERRORS) == "Erros (1)", "titulo da aba Erros mostra a contagem")

    selections = window.editor.extraSelections()
    check(len(selections) == 2, f"editor tem 2 selecoes extra (linha atual + erro), veio {len(selections)}")
    error_selection = selections[1]
    check(error_selection.format.underlineStyle() is not None, "selecao do erro tem sublinhado")
    check(
        error_selection.cursor.selectionStart() == error_selection.cursor.selectionEnd() - 1,
        "sublinhado cobre exatamente 1 caractere",
    )

    from PySide6.QtGui import QPalette  # noqa: PLC0415

    from src.editor.code_editor import current_line_color, error_color  # noqa: PLC0415
    palette = window.editor.palette()
    base = palette.color(QPalette.ColorRole.Base)
    text_color = palette.color(QPalette.ColorRole.Text)
    tint = current_line_color(palette)
    check(tint != base, "cor da linha atual difere do fundo do editor")
    check(
        not (tint.lightness() > 200 and text_color.lightness() > 200),
        "linha atual nao fica clara em cima de texto claro",
    )
    check(
        not (tint.lightness() < 40 and text_color.lightness() < 40),
        "linha atual nao fica escura em cima de texto escuro",
    )
    check(error_color(palette) not in (base, text_color), "vermelho de erro se distingue do texto")

    window.editor.setPlainText("")
    window.analysis.analyze_now("")
    app.processEvents()
    check(len(window.editor.extraSelections()) == 1, "sem erros sobra so o realce da linha atual")

    fake = window.analysis.lexer
    before = fake.calls
    window.editor.setPlainText("programa Teste;\nbegin\nend.\n")
    check(fake.calls == before, "digitacao ainda nao chamou o analisador (debounce ativo)")
    window.analysis._timer.setInterval(0)
    window.analysis.request(window.editor.toPlainText())
    app.processEvents()
    app.processEvents()
    check(fake.calls > before, "analise ao vivo rodou depois do debounce")

    window.editor.setPlainText("programa Salvo;\nbegin\nend.\n")
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "teste.pas")
        check(window._write_to(path), "janela gravou o arquivo")
        check(window._display_name() == "teste.pas", "janela passou a exibir o nome do arquivo")
        check(FileService.read(path).startswith("programa Salvo"), "conteudo gravado e relido")
        check(not window._modified, "flag de alteracao limpa apos salvar")

    from src.settings import THEME_DARK, THEME_LIGHT, THEME_SYSTEM, Settings  # noqa: PLC0415

    remember_system_appearance(app)
    dark = Settings(theme=THEME_DARK)
    window.apply_settings(dark)
    app.processEvents()
    dark_base = app.palette().color(QPalette.ColorRole.Base)
    check(dark_base.lightness() < 128, f"tema escuro aplicou palette escura ({dark_base.name()})")
    check(
        window.editor.current_line_color().lightness() < 128,
        "linha atual escura no tema escuro",
    )

    light = Settings(theme=THEME_LIGHT)
    window.apply_settings(light)
    app.processEvents()
    light_base = app.palette().color(QPalette.ColorRole.Base)
    check(light_base.lightness() > 128, f"tema claro aplicou palette clara ({light_base.name()})")
    check(
        window.editor.current_line_color().lightness() > 128,
        "linha atual clara no tema claro",
    )

    window.apply_settings(Settings(theme=THEME_SYSTEM))
    app.processEvents()
    system_base = app.palette().color(QPalette.ColorRole.Base)
    check(
        system_base != dark_base or system_base == app.palette().color(QPalette.ColorRole.Base),
        "tema Sistema devolveu a paleta do sistema",
    )

    window.apply_settings(Settings(font_family="Courier New", font_size=18))
    app.processEvents()
    check(window.editor.font().pointSize() == 18, "fonte do editor mudou para 18 pt")
    check(window.editor.font().family() == "Courier New", "fonte do editor trocou de familia")
    check(
        window.editor.line_number_area_width() > 0,
        "numeracao de linha recalculada para a nova fonte",
    )

    window.apply_settings(Settings(current_line_color="#ff00ff"))
    app.processEvents()
    check(
        window.editor.current_line_color().name() == "#ff00ff",
        "cor manual da linha atual foi aplicada",
    )
    window.apply_settings(Settings())
    app.processEvents()
    check(
        window.editor.current_line_color() != QColor("#ff00ff"),
        "linha atual voltou a derivar do tema",
    )

    window.apply_settings(Settings(font_size=15))
    window.zoom_in()
    check(window.settings.font_size == 16, "Ctrl+ aumentou a fonte")
    window.zoom_out()
    window.zoom_out()
    check(window.settings.font_size == 14, "Ctrl- diminuiu a fonte")
    window.zoom_reset()
    check(window.settings.font_size == Settings().font_size, "Ctrl+0 voltou ao tamanho padrao")

    for _ in range(MAX_FONT_SIZE + 5):
        window.zoom_in()
    check(window.settings.font_size == MAX_FONT_SIZE, "Ctrl+ parou no tamanho maximo")
    for _ in range(MAX_FONT_SIZE + 5):
        window.zoom_out()
    check(window.settings.font_size == MIN_FONT_SIZE, "Ctrl- parou no tamanho minimo")
    window.zoom_reset()

    window.zoom_in()
    saved = load_settings(settings_path)
    check(saved.font_size == window.settings.font_size, "preferencia foi gravada em disco")
    check(settings_path.is_file(), "arquivo de preferencias criado")

    settings2 = Settings(theme=THEME_DARK, font_size=14, error_color="#00ff00")
    save_settings(settings2, settings_path)
    reloaded = load_settings(settings_path)
    check(reloaded.theme == THEME_DARK, "tema sobreviveu ao round-trip")
    check(reloaded.font_size == 14, "tamanho da fonte sobreviveu ao round-trip")
    check(reloaded.error_color == "#00ff00", "cor de erro sobreviveu ao round-trip")

    settings_path.write_text("{isto nao e json", encoding="utf-8")
    check(load_settings(settings_path) == Settings(), "JSON invalido cai no padrao")
    settings_path.write_text('{"theme":"inexistente","font_size":9999}', encoding="utf-8")
    salvaged = load_settings(settings_path)
    check(salvaged.theme == THEME_SYSTEM, "tema desconhecido cai no padrao")
    check(salvaged.font_size <= MAX_FONT_SIZE, "tamanho fora da faixa foi aparado")
    settings_path.unlink()
    check(load_settings(settings_path) == Settings(), "arquivo ausente cai no padrao")

    window.apply_settings(Settings())
    window.close()
    print("\nTodos os testes de fumaça passaram.")
    tmp_dir.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
