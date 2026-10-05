from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QPalette,
    QTextCharFormat,
    QTextDocument,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.editor.highlighter import (  # noqa: E402
    CATEGORIES,
    CATEGORY_BY_TOKEN,
    CATEGORY_COMMENT,
    CATEGORY_KEYWORD,
    CATEGORY_LABELS,
    CATEGORY_LITERAL,
    CATEGORY_NUMBER,
    CATEGORY_TYPE,
    DARK_COLORS,
    LIGHT_COLORS,
    PREFERENCE_FIELDS,
    TokenHighlighter,
    category_of,
    default_colors,
    resolve_colors,
)
from src.app import build_lexer  # noqa: E402
from src.editor.code_editor import CodeEditor  # noqa: E402
from src.lexer import Lexer  # noqa: E402
from src.lexer.tokens import (  # noqa: E402
    LITERAL,
    NUM,
    PALAVRAS_RESERVADAS,
    SIMBOLOS,
    TIPOS_PRIMARIOS,
    TOKEN_CLASSES,
)
from src.main_window import MainWindow  # noqa: E402
from src.settings import Settings  # noqa: E402

CORES: dict[str, QColor] = {
    CATEGORY_KEYWORD: QColor("#010101"),
    CATEGORY_TYPE: QColor("#020202"),
    CATEGORY_NUMBER: QColor("#030303"),
    CATEGORY_LITERAL: QColor("#040404"),
    CATEGORY_COMMENT: QColor("#050505"),
}

PROGRAMA = (
    "programa Ola;\n"
    "var x: integer;\n"
    "begin\n"
    "x := 10; // um comentario\n"
    "writeln('ola', x);\n"
    "end.\n"
)

@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])

def realcar(fonte: str, tokens=()):
    documento = QTextDocument()
    documento.setPlainText(fonte)
    realcador = TokenHighlighter(documento)
    realcador.set_colors(dict(CORES))
    realcador.set_tokens(tokens)
    return documento, realcador

def analisar(fonte: str):
    return Lexer().analisar(fonte)

def posicao_de(fonte: str, tipo: str, ocorrencia: int = 1) -> tuple[int, int]:
    tokens = [t for t in analisar(fonte).tokens if t.tipo == tipo]
    return tokens[ocorrencia - 1].linha, tokens[ocorrencia - 1].coluna

def cor_em(documento: QTextDocument, linha: int, coluna: int) -> QColor:
    bloco = documento.findBlockByNumber(linha - 1)
    assert bloco.isValid(), f"linha {linha} não existe no documento"
    for intervalo in bloco.layout().formats():
        if intervalo.start <= coluna - 1 < intervalo.start + intervalo.length:
            return intervalo.format.foreground().color()
    return QColor()

def faixa_em(documento: QTextDocument, linha: int) -> list[tuple[int, int, QColor]]:
    bloco = documento.findBlockByNumber(linha - 1)
    return [
        (i.start, i.length, i.format.foreground().color())
        for i in bloco.layout().formats()
    ]

def test_palavra_reservada_usa_a_categoria_de_palavra() -> None:
    for tipo in set(PALAVRAS_RESERVADAS.values()) - set(TIPOS_PRIMARIOS):
        assert category_of(tipo) == CATEGORY_KEYWORD, tipo

def test_tipo_primario_tem_categoria_propria() -> None:
    for tipo in TIPOS_PRIMARIOS:
        assert category_of(tipo) == CATEGORY_TYPE, tipo

def test_numero_e_literal() -> None:
    assert category_of(NUM) == CATEGORY_NUMBER
    assert category_of(LITERAL) == CATEGORY_LITERAL

def test_identificador_e_simbolo_ficam_com_a_cor_normal() -> None:
    assert category_of("ID") == ""
    for _, tipo in SIMBOLOS:
        assert category_of(tipo) == "", tipo

def test_toda_classe_de_token_ou_tem_cor_ou_e_id() -> None:
    for classe in TOKEN_CLASSES:
        sem_cor = [t for t in PALAVRAS_RESERVADAS.values() if t == classe.tipo]
        assert category_of(classe.tipo) or not sem_cor, classe.tipo

def test_categorias_publicadas_tem_rotulo() -> None:
    assert set(CATEGORY_LABELS) == set(CATEGORIES)
    for rotulo in CATEGORY_LABELS.values():
        assert rotulo and rotulo[0].isupper()

def test_campos_de_preferencia_existem_em_settings() -> None:
    assert set(PREFERENCE_FIELDS) == set(CATEGORIES)
    for campo in PREFERENCE_FIELDS.values():
        assert hasattr(Settings(), campo), campo

def test_padroes_de_settings_deixam_a_cor_para_o_tema() -> None:
    padrao = Settings()
    for campo in PREFERENCE_FIELDS.values():
        assert getattr(padrao, campo) == "", campo

def test_cores_padrao_cobrem_todas_as_categorias() -> None:
    for paleta in (QPalette(), QPalette()):
        cores = default_colors(paleta)
        assert set(cores) == set(CATEGORIES)
        for cor in cores.values():
            assert cor.isValid()

def test_tema_claro_e_escuro_tem_cores_distintas() -> None:
    for categoria in CATEGORIES:
        assert LIGHT_COLORS[categoria] != DARK_COLORS[categoria], categoria
        assert QColor(LIGHT_COLORS[categoria]).isValid()
        assert QColor(DARK_COLORS[categoria]).isValid()

def test_tema_escuro_nao_tem_cores_claras(app: QApplication) -> None:
    from src.theme import DARK, LIGHT, build_palette  # noqa: PLC0415

    for spec, tabela in ((LIGHT, LIGHT_COLORS), (DARK, DARK_COLORS)):
        paleta = build_palette(spec)
        for categoria in CATEGORIES:
            esperada = QColor(tabela[categoria])
            assert default_colors(paleta)[categoria] == esperada, (spec.name, categoria)

def test_preferencia_sobrepoe_a_cor_do_tema() -> None:
    paleta = QPalette()
    antes = default_colors(paleta)[CATEGORY_KEYWORD]
    depois = resolve_colors({CATEGORY_KEYWORD: QColor("#ff00ff")}, paleta)
    assert depois[CATEGORY_KEYWORD] == QColor("#ff00ff")
    assert antes != QColor("#ff00ff")
    assert depois[CATEGORY_COMMENT] == default_colors(paleta)[CATEGORY_COMMENT]

def test_preferencia_invalida_ou_desconhecida_e_ignorada() -> None:
    paleta = QPalette()
    cores = resolve_colors(
        {
            CATEGORY_KEYWORD: QColor("nao e uma cor"),
            "categoria_inexistente": QColor("#ff00ff"),
        },
        paleta,
    )
    assert cores == default_colors(paleta)

def test_palavra_reservada_receb_cor_e_negrito(app: QApplication) -> None:
    fonte = "programa Ola;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    linha, coluna = posicao_de(fonte, "PROGRAM")
    assert cor_em(documento, linha, coluna) == CORES[CATEGORY_KEYWORD]

    bloco = documento.findBlockByNumber(linha - 1)
    formatos = {i.start: QTextCharFormat(i.format) for i in bloco.layout().formats()}
    assert formatos[coluna - 1].fontWeight() == QFont.Weight.Bold

def test_numero_e_literal_recebem_cores_diferentes(app: QApplication) -> None:
    fonte = "x := 10; y := 'ola';"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, *posicao_de(fonte, NUM)) == CORES[CATEGORY_NUMBER]
    assert cor_em(documento, *posicao_de(fonte, LITERAL)) == CORES[CATEGORY_LITERAL]

def test_identificadores_e_simbolos_nao_recebem_cor(app: QApplication) -> None:
    fonte = "contador := alvo;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, *posicao_de(fonte, "ID", 1)) == QColor()
    assert cor_em(documento, *posicao_de(fonte, "ID", 2)) == QColor()
    assert cor_em(documento, *posicao_de(fonte, "ATRIBUICAO")) == QColor()
    assert cor_em(documento, *posicao_de(fonte, "PONTO_E_VIRGULA")) == QColor()

def test_token_que_passa_do_fim_da_linha_e_preso(app: QApplication) -> None:
    from src.services.lexer_service import Token  # noqa: PLC0415

    documento, _ = realcar("ab", [Token("BEGIN", "begin", 1, 1)])
    assert faixa_em(documento, 1) == []

def test_token_de_outra_linha_e_ignorado(app: QApplication) -> None:
    from src.services.lexer_service import Token  # noqa: PLC0415

    documento, _ = realcar("ab", [Token("BEGIN", "begin", 9, 1)])
    assert faixa_em(documento, 1) == []

def test_mudanca_de_cor_repinta_o_documento(app: QApplication) -> None:
    fonte = "programa Ola;"
    documento, realcador = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, 1, 1) == CORES[CATEGORY_KEYWORD]
    realcador.set_colors({**CORES, CATEGORY_KEYWORD: QColor("#abcdef")})
    assert cor_em(documento, 1, 1) == QColor("#abcdef")

def test_comentario_de_linha(app: QApplication) -> None:
    fonte = "x := 1; // ate o fim"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    inicio = fonte.index("//")
    assert faixa_em(documento, 1) == [
        (5, 1, CORES[CATEGORY_NUMBER]),
        (inicio, len(fonte) - inicio, CORES[CATEGORY_COMMENT]),
    ]

def test_comentario_de_linha_nao_atinge_a_linha_seguinte(app: QApplication) -> None:
    fonte = "// nota\nx := 1;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, 1, 1) == CORES[CATEGORY_COMMENT]
    assert cor_em(documento, 2, 1) == QColor()

def test_comentario_de_bloco_na_mesma_linha(app: QApplication) -> None:
    fonte = "x := 1; { nota } y := 2;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    inicio = fonte.index("{")
    assert (inicio, 8, CORES[CATEGORY_COMMENT]) in faixa_em(documento, 1)
    assert cor_em(documento, *posicao_de(fonte, "ID", 2)) == QColor()

def test_comentario_de_bloco_com_varias_linhas(app: QApplication) -> None:
    fonte = "{ um\ndois\ntres }"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    for linha in (1, 2, 3):
        assert cor_em(documento, linha, 1) == CORES[CATEGORY_COMMENT], linha
    assert faixa_em(documento, 1) == [(0, 4, CORES[CATEGORY_COMMENT])]
    assert faixa_em(documento, 2) == [(0, 4, CORES[CATEGORY_COMMENT])]
    assert faixa_em(documento, 3) == [(0, 6, CORES[CATEGORY_COMMENT])]

def test_estado_de_comentario_desaparece_ao_fechar(app: QApplication) -> None:
    fonte = "{ nota }\nx := 1;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, 1, 1) == CORES[CATEGORY_COMMENT]
    assert cor_em(documento, 2, 1) == QColor()

def test_comentario_de_parenteses_com_varias_linhas(app: QApplication) -> None:
    fonte = "(* um\ndois *)\nx := 1;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, 1, 1) == CORES[CATEGORY_COMMENT]
    assert cor_em(documento, 1, 3) == CORES[CATEGORY_COMMENT]
    assert cor_em(documento, 2, 1) == CORES[CATEGORY_COMMENT]
    assert cor_em(documento, 3, 1) == QColor()

def test_comentario_de_bloco_aninhado(app: QApplication) -> None:
    fonte = "{ a { b } c } x := 1;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, 1, 13) == CORES[CATEGORY_COMMENT]
    assert cor_em(documento, 1, 15) == QColor()

def test_comentario_de_parenteses_aninhado(app: QApplication) -> None:
    fonte = "(* a (* b *) c *) x := 1;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, 1, 17) == CORES[CATEGORY_COMMENT]
    assert cor_em(documento, 1, 19) == QColor()

def test_comentario_nao_fechado_atinge_o_fim_do_arquivo(app: QApplication) -> None:
    fonte = "{ aberto\ny := 1;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, 1, 2) == CORES[CATEGORY_COMMENT]
    assert cor_em(documento, 2, 1) == CORES[CATEGORY_COMMENT]

def test_parenteses_estrela_e_operador_e_nao_comentario(app: QApplication) -> None:
    fonte = "x := (a * b) * c;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert faixa_em(documento, 1) == []

def test_comentario_comeca_com_asterisco_estrela(app: QApplication) -> None:
    fonte = "x := 1; (*nada*)\ny := 2;"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, 1, 9) == CORES[CATEGORY_COMMENT]
    assert cor_em(documento, 2, 1) == QColor()

def test_programa_do_relatorio_fica_colorido(app: QApplication) -> None:
    resultado = analisar(PROGRAMA)
    assert resultado.errors == ()
    documento, _ = realcar(PROGRAMA, resultado.tokens)

    esperado = [
        ("PROGRAM", CATEGORY_KEYWORD),
        ("VAR", CATEGORY_KEYWORD),
        ("BEGIN", CATEGORY_KEYWORD),
        ("END", CATEGORY_KEYWORD),
        ("INTEGER", CATEGORY_TYPE),
        ("NUM", CATEGORY_NUMBER),
        ("LITERAL", CATEGORY_LITERAL),
    ]
    for tipo, categoria in esperado:
        posicao = posicao_de(PROGRAMA, tipo)
        assert cor_em(documento, *posicao) == CORES[categoria], tipo

    for ocorrencia in range(1, 6):
        assert cor_em(documento, *posicao_de(PROGRAMA, "ID", ocorrencia)) == QColor()
    linha = PROGRAMA.split("\n")[3]
    assert cor_em(documento, 4, linha.index("//") + 1) == CORES[CATEGORY_COMMENT]

def test_literal_no_programa_do_relatorio(app: QApplication) -> None:
    fonte = "programa Ola;\nbegin\n  writeln('ola');\nend.\n"
    documento, _ = realcar(fonte, analisar(fonte).tokens)
    assert cor_em(documento, *posicao_de(fonte, LITERAL)) == CORES[CATEGORY_LITERAL]

def test_todo_token_com_cor_esta_pintado(app: QApplication) -> None:
    resultado = analisar(PROGRAMA)
    documento, _ = realcar(PROGRAMA, resultado.tokens)
    linhas = PROGRAMA.split("\n")
    for token in resultado.tokens:
        categoria = category_of(token.tipo)
        if not categoria:
            continue
        assert cor_em(documento, token.linha, token.coluna) == CORES[categoria], (
            token.tipo,
            token.lexema,
        )
        linha = linhas[token.linha - 1]
        assert linha[token.coluna - 1 : token.coluna - 1 + len(token.lexema)] == (
            token.lexema
        )
        assert (token.coluna - 1, len(token.lexema), CORES[categoria]) in faixa_em(
            documento, token.linha
        )

def test_erro_lexico_nao_derruba_o_realce(app: QApplication) -> None:
    fonte = "programa Ola;\n@\nbegin\nend.\n"
    resultado = analisar(fonte)
    assert resultado.has_errors
    documento, _ = realcar(fonte, resultado.tokens)
    assert cor_em(documento, *posicao_de(fonte, "PROGRAM")) == CORES[CATEGORY_KEYWORD]
    assert cor_em(documento, *posicao_de(fonte, "BEGIN")) == CORES[CATEGORY_KEYWORD]

def test_cores_por_classe_sao_distintas(app: QApplication) -> None:
    valores = {categoria: cor.name() for categoria, cor in CORES.items()}
    assert len(set(valores.values())) == len(CATEGORIES)

def test_abrir_janela_nao_marca_o_documento_como_modificado(app: QApplication, tmp_path) -> None:
    janela = MainWindow(build_lexer(), tmp_path / "preferencias.json")
    assert not janela._modified
    assert "programa" in janela.editor.toPlainText()
    assert "*" not in janela.windowTitle()

def test_mudar_cor_de_realce_nao_marca_o_documento_como_modificado(
    app: QApplication, tmp_path
) -> None:
    janela = MainWindow(build_lexer(), tmp_path / "preferencias.json")
    janela.editor.setPlainText(PROGRAMA)
    janela.analysis.analyze_now(PROGRAMA)
    janela._on_text_changed()
    janela._mark_clean()

    config = janela.settings.copy()
    config.keyword_color = "#ff00ff"
    janela.apply_settings(config)

    assert not janela._modified
    documento = janela.editor.document()
    assert cor_em(documento, *posicao_de(PROGRAMA, PALAVRAS_RESERVADAS["program"])) == QColor(
        "#ff00ff"
    )

def test_repintura_nao_dispara_text_changed(app: QApplication) -> None:
    editor = CodeEditor()
    editor.setPlainText(PROGRAMA)

    disparos: list[int] = []
    editor.textChanged.connect(lambda: disparos.append(1))

    editor.set_tokens(analisar(PROGRAMA).tokens)
    editor.set_highlight_colors(dict(CORES))

    assert disparos == []
