from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MAX_IDENTIFIER_LENGTH  # noqa: E402
from src.lexer import Lexer  # noqa: E402
from src.lexer import PROGRAMA_EXEMPLO  # noqa: E402
from src.lexer.tokens import *  # noqa: E402,F403
from src.services.lexer_service import AnalysisResult, LexerService  # noqa: E402


@pytest.fixture
def lexer() -> Lexer:
    return Lexer()


def tipos(lexer: Lexer, fonte: str) -> list[str]:
    return [token.tipo for token in lexer.analisar(fonte).tokens]


def pares(lexer: Lexer, fonte: str) -> list[tuple[str, str]]:
    return [(token.tipo, token.lexema) for token in lexer.analisar(fonte).tokens]


def test_lexer_satisfaz_o_protocolo() -> None:
    assert isinstance(Lexer(), LexerService)


def test_programa_de_exemplo_nao_gera_erro(lexer: Lexer) -> None:
    resultado = lexer.analisar(PROGRAMA_EXEMPLO)
    assert resultado.errors == ()
    assert resultado.warnings == ()
    assert resultado.token_count > 40


def test_todas_as_colecoes_do_resultado_sao_preenchidas(lexer: Lexer) -> None:
    resultado: AnalysisResult = lexer.analisar(PROGRAMA_EXEMPLO)
    assert resultado.tokens
    assert resultado.symbols
    assert resultado.token_classes
    assert resultado.dfa_states
    assert resultado.dfa_transitions


@pytest.mark.parametrize(
    ("palavra", "token"),
    [
        ("program", PROGRAM),
        ("begin", BEGIN),
        ("end", END),
        ("const", CONST),
        ("var", VAR),
        ("integer", INTEGER),
        ("real", REAL),
        ("char", CHAR),
        ("string", STRING),
        ("procedure", PROCEDURE),
        ("function", FUNCTION),
        ("if", IF),
        ("else", ELSE),
        ("then", THEN),
        ("while", WHILE),
        ("do", DO),
        ("repeat", REPEAT),
        ("until", UNTIL),
        ("break", BREAK),
        ("continue", CONTINUE),
        ("ou", OU),
        ("e", E),
    ],
)
def test_palavras_reservadas(lexer: Lexer, palavra: str, token: str) -> None:
    assert pares(lexer, palavra) == [(token, palavra)]


@pytest.mark.parametrize("forma", [str.lower, str.upper, str.title])
def test_palavras_reservadas_nao_diferenciam_caixa(lexer: Lexer, forma) -> None:
    assert pares(lexer, forma("begin")) == [(BEGIN, forma("begin"))]


def test_lexema_preserva_a_caixa_original(lexer: Lexer) -> None:
    assert pares(lexer, "BEGIN") == [(BEGIN, "BEGIN")]
    assert pares(lexer, "Begin") == [(BEGIN, "Begin")]


@pytest.mark.parametrize(
    ("lexema", "token"),
    [
        (";", PONTO_E_VIRGULA),
        (".", PONTO),
        (",", VIRGULA),
        (":", DOIS_PONTOS),
        ("=", IGUALDADE_COMPARACAO),
        (":=", ATRIBUICAO),
        ("<>", DIFERENTE_DE),
        ("<", MENOR_QUE),
        (">", MAIOR_QUE),
        ("<=", MENOR_OU_IGUAL_QUE),
        (">=", MAIOR_OU_IGUAL_QUE),
        ("+", ADICAO),
        ("-", SUBTRACAO),
        ("*", MULTIPLICACAO),
        ("/", DIVISAO),
        ("(", ABRE_PARENTESES),
        (")", FECHA_PARENTESES),
        ("[", ABRE_COLCHETES),
        ("]", FECHA_COLCHETES),
    ],
)
def test_simbolos(lexer: Lexer, lexema: str, token: str) -> None:
    assert pares(lexer, lexema) == [(token, lexema)]


def test_maximo_casamento_ganha_dos_simbolos_simples(lexer: Lexer) -> None:
    assert tipos(lexer, ":=") == [ATRIBUICAO]
    assert tipos(lexer, "<=") == [MENOR_OU_IGUAL_QUE]
    assert tipos(lexer, ">=") == [MAIOR_OU_IGUAL_QUE]
    assert tipos(lexer, "<>") == [DIFERENTE_DE]
    assert tipos(lexer, ":") == [DOIS_PONTOS]
    assert tipos(lexer, "<") == [MENOR_QUE]
    assert tipos(lexer, ">") == [MAIOR_QUE]


@pytest.mark.parametrize(
    "identificador",
    ["a", "A", "contador", "x1", "valor_1", "a" * MAX_IDENTIFIER_LENGTH],
)
def test_identificadores_validos(lexer: Lexer, identificador: str) -> None:
    resultado = lexer.analisar(identificador)
    assert pares(lexer, identificador) == [(ID, identificador)]
    assert resultado.errors == ()


@pytest.mark.parametrize("invalido", ["_x", "_"])
def test_identificador_precisa_comecar_por_letra(lexer: Lexer, invalido: str) -> None:
    resultado = lexer.analisar(invalido)
    assert (ID, invalido) not in pares(lexer, invalido)
    assert resultado.errors != ()


def test_digito_no_inicio_quebra_o_lexema_sem_erro(lexer: Lexer) -> None:
    assert pares(lexer, "1x") == [(NUM, "1"), (ID, "x")]


@pytest.mark.parametrize("identificador", ["a" * (MAX_IDENTIFIER_LENGTH + 1), "a" * 40])
def test_identificador_acima_do_limite_erra_mantem_o_token(lexer: Lexer, identificador: str) -> None:
    resultado = lexer.analisar(identificador)
    assert pares(lexer, identificador) == [(ID, identificador)]
    assert len(resultado.errors) == 1
    erro = resultado.errors[0]
    assert erro.line == 1
    assert erro.column == 1
    assert erro.lexeme == identificador
    assert erro.length == len(identificador)
    assert str(MAX_IDENTIFIER_LENGTH) in erro.message


def test_identificador_nao_pode_comecar_com_digito(lexer: Lexer) -> None:
    assert pares(lexer, "1abc") == [(NUM, "1"), (ID, "abc")]


def test_identificador_aceita_digito_e_sublinhado(lexer: Lexer) -> None:
    assert pares(lexer, "a_1b2") == [(ID, "a_1b2")]


@pytest.mark.parametrize(
    ("lexema", "atributo"),
    [("0", "inteiro"), ("42", "inteiro"), ("3.14", "real"), ("10.0", "real"), ("007", "inteiro")],
)
def test_numeros(lexer: Lexer, lexema: str, atributo: str) -> None:
    resultado = lexer.analisar(lexema)
    assert resultado.errors == ()
    token = resultado.tokens[0]
    assert (token.tipo, token.lexema, token.atributos) == (NUM, lexema, atributo)


def test_numero_com_ponto_sem_digitos(lexer: Lexer) -> None:
    assert pares(lexer, "12.") == [(NUM, "12"), (PONTO, ".")]


def test_ponto_no_inicio_e_numero_separado(lexer: Lexer) -> None:
    assert pares(lexer, ".5") == [(PONTO, "."), (NUM, "5")]


def test_numeros_com_ponto_duplo(lexer: Lexer) -> None:
    assert pares(lexer, "1.2.3") == [(NUM, "1.2"), (PONTO, "."), (NUM, "3")]


def test_numero_em_frase(lexer: Lexer) -> None:
    assert pares(lexer, "x := 12.5 + 3;") == [
        (ID, "x"),
        (ATRIBUICAO, ":="),
        (NUM, "12.5"),
        (ADICAO, "+"),
        (NUM, "3"),
        (PONTO_E_VIRGULA, ";"),
    ]


@pytest.mark.parametrize(
    ("lexema", "conteudo"),
    [
        ("''", ""),
        ("'a'", "a"),
        ("'abc'", "abc"),
        ("'oi mundo'", "oi mundo"),
        ("'123'", "123"),
        ("'a,b;c'", "a,b;c"),
        ("'a+b'", "a+b"),
    ],
)
def test_literals(lexer: Lexer, lexema: str, conteudo: str) -> None:
    resultado = lexer.analisar(lexema)
    assert resultado.errors == ()
    token = resultado.tokens[0]
    assert (token.tipo, token.lexema) == (LITERAL, lexema)
    assert token.atributos == f"{len(conteudo)} caracteres"


def test_literal_com_aspas_duplas_adentro(lexer: Lexer) -> None:
    assert pares(lexer, "'d''art'") == [(LITERAL, "'d''art'")]


@pytest.mark.parametrize("lexema", ["'aberta", "'a'b'"])
def test_literal_nao_encerrado(lexer: Lexer, lexema: str) -> None:
    resultado = lexer.analisar(lexema)
    assert len(resultado.errors) == 1
    assert "não reconhecido" in resultado.errors[0].message
    assert (LITERAL, lexema) not in pares(lexer, lexema)


def test_literal_nao_atravessa_a_quebra_de_linha(lexer: Lexer) -> None:
    resultado = lexer.analisar("a := 'aberta\nb := 2;")
    assert len(resultado.errors) == 1
    assert tipos(lexer, "a := 'aberta\nb := 2;") == [
        ID,
        ATRIBUICAO,
        ID,
        ATRIBUICAO,
        NUM,
        PONTO_E_VIRGULA,
    ]


def test_tres_aspas_deixam_o_literal_vazio_e_um_erro(lexer: Lexer) -> None:
    resultado = lexer.analisar("'''")
    assert [(t.tipo, t.lexema) for t in resultado.tokens] == [(LITERAL, "''")]
    assert len(resultado.errors) == 1


def test_comentario_de_linha(lexer: Lexer) -> None:
    assert pares(lexer, "a := 1; // isto e um comentario\nb := 2;") == [
        (ID, "a"),
        (ATRIBUICAO, ":="),
        (NUM, "1"),
        (PONTO_E_VIRGULA, ";"),
        (ID, "b"),
        (ATRIBUICAO, ":="),
        (NUM, "2"),
        (PONTO_E_VIRGULA, ";"),
    ]


def test_comentario_de_bloco(lexer: Lexer) -> None:
    assert pares(lexer, "a { isto e um comentario } b") == [(ID, "a"), (ID, "b")]


def test_comentario_de_bloco_com_ninho(lexer: Lexer) -> None:
    assert pares(lexer, "a { um { dois } tres } b") == [(ID, "a"), (ID, "b")]


def test_comentario_de_parenteses(lexer: Lexer) -> None:
    assert pares(lexer, "a (* isto e um comentario *) b") == [(ID, "a"), (ID, "b")]


def test_comentario_de_parenteses_com_ninho(lexer: Lexer) -> None:
    assert pares(lexer, "a (* um (* dois *) tres *) b") == [(ID, "a"), (ID, "b")]


def test_comentario_ganha_da_ambiguidade_com_parenteses(lexer: Lexer) -> None:
    assert pares(lexer, "(*a*)") == []


@pytest.mark.parametrize("abertura", ["{", "(*"])
def test_comentario_nao_encerrado(lexer: Lexer, abertura: str) -> None:
    resultado = lexer.analisar(f"a := 1; {abertura} comentario sem fim\nb := 2;")
    assert len(resultado.errors) == 1
    assert abertura in resultado.errors[0].lexeme


@pytest.mark.parametrize("espaco", [" ", "\t", "\r", "\n", "\v", "\f"])
def test_espacos_sao_descartados(lexer: Lexer, espaco: str) -> None:
    assert pares(lexer, espaco) == []


def test_espacos_entre_tokens(lexer: Lexer) -> None:
    assert pares(lexer, "  a\t+\tb  ") == [(ID, "a"), (ADICAO, "+"), (ID, "b")]


def test_linha_e_coluna_sao_base_um(lexer: Lexer) -> None:
    resultado = lexer.analisar("a;\nb;")
    assert [(t.linha, t.coluna) for t in resultado.tokens] == [
        (1, 1),
        (1, 2),
        (2, 1),
        (2, 2),
    ]


def test_coluna_conta_caracteres_dentro_da_linha(lexer: Lexer) -> None:
    resultado = lexer.analisar("x := 123;")
    numeros = [t for t in resultado.tokens if t.tipo == NUM]
    assert (numeros[0].linha, numeros[0].coluna) == (1, 6)


def test_quebra_crlf_conta_uma_vez(lexer: Lexer) -> None:
    resultado = lexer.analisar("a;\r\nb;")
    assert [(t.linha, t.coluna) for t in resultado.tokens] == [
        (1, 1),
        (1, 2),
        (2, 1),
        (2, 2),
    ]


def test_quebra_lf_linha_e_coluna(lexer: Lexer) -> None:
    resultado = lexer.analisar("a;\nb;\nc;")
    assert [t.linha for t in resultado.tokens] == [1, 1, 2, 2, 3, 3]


@pytest.mark.parametrize("caractere", ["@", "#", "$", "!", "?", "`", "~", "^", "&", "|", "\\"])
def test_caracteres_invalidos(lexer: Lexer, caractere: str) -> None:
    resultado = lexer.analisar(f"a := 1{caractere};")
    assert len(resultado.errors) == 1
    erro = resultado.errors[0]
    assert erro.lexeme == caractere
    assert (erro.line, erro.column) == (1, 7)
    assert "inválido" in erro.message


def test_letra_acentuada_e_invalida(lexer: Lexer) -> None:
    resultado = lexer.analisar("número")
    assert [t.tipo for t in resultado.tokens] == [ID, ID]
    assert len(resultado.errors) == 1
    assert resultado.errors[0].lexeme == "ú"


def test_fechador_sem_abertura(lexer: Lexer) -> None:
    resultado = lexer.analisar("a := 1);")
    assert len(resultado.errors) == 1
    assert resultado.errors[0].lexeme == ")"


def test_colchete_sem_abertura(lexer: Lexer) -> None:
    resultado = lexer.analisar("a := ] ;")
    assert len(resultado.errors) == 1
    assert resultado.errors[0].lexeme == "]"


def test_chave_fora_de_comentario(lexer: Lexer) -> None:
    resultado = lexer.analisar("a := } ;")
    assert len(resultado.errors) == 1
    assert resultado.errors[0].lexeme == "}"


def test_parenteses_balanceados_nao_geram_erro(lexer: Lexer) -> None:
    assert lexer.analisar("f(x, (y));").errors == ()


def test_abertura_nao_fechada_no_fim_do_arquivo(lexer: Lexer) -> None:
    resultado = lexer.analisar("begin f(1")
    assert len(resultado.errors) == 1
    assert resultado.errors[0].lexeme == "("


def test_recuperacao_apos_caractere_invalido(lexer: Lexer) -> None:
    resultado = lexer.analisar("a := 1; @ b := 2;")
    assert len(resultado.errors) == 1
    assert tipos(lexer, "a := 1; @ b := 2;") == [
        ID,
        ATRIBUICAO,
        NUM,
        PONTO_E_VIRGULA,
        ID,
        ATRIBUICAO,
        NUM,
        PONTO_E_VIRGULA,
    ]


def test_recupereria_apos_literal_aberto(lexer: Lexer) -> None:
    resultado = lexer.analisar("a := 'aberta;\nb := 2;")
    assert len(resultado.errors) == 1
    assert tipos(lexer, "a := 'aberta;\nb := 2;") == [
        ID,
        ATRIBUICAO,
        ID,
        ATRIBUICAO,
        NUM,
        PONTO_E_VIRGULA,
    ]


def test_fonte_vazia(lexer: Lexer) -> None:
    resultado = lexer.analisar("")
    assert resultado.tokens == ()
    assert resultado.errors == ()
    assert resultado.symbols == ()


def test_fonte_so_com_espacos(lexer: Lexer) -> None:
    assert lexer.analisar("   \n\t  ").tokens == ()


def test_tabela_de_simbolos_do_programa(lexer: Lexer) -> None:
    resultado = lexer.analisar(PROGRAMA_EXEMPLO)
    declaracoes = {
        simbolo.identifier: (simbolo.kind, simbolo.type, simbolo.value, simbolo.line)
        for simbolo in resultado.symbols
    }
    assert declaracoes == {
        "Ola": ("programa", "", "", 1),
        "limite": ("constante", INTEGER, "10", 4),
        "contador": ("variavel", INTEGER, "", 7),
        "nome": ("variavel", STRING, "", 8),
        "media": ("variavel", REAL, "", 9),
        "mostrar": ("procedimento", "", "", 11),
    }


def test_tabela_de_simbolos_ignora_uso_como_identificador(lexer: Lexer) -> None:
    resultado = lexer.analisar("programa P;\nbegin\n  P := 1;\nend.\n")
    assert [s.identifier for s in resultado.symbols] == ["P"]
    assert resultado.symbols[0].kind == "programa"


def test_tabela_de_simbolos_de_funcao(lexer: Lexer) -> None:
    fonte = "function somar(a: integer; b: integer): integer;\nbegin\nend;\n"
    resultado = lexer.analisar(fonte)
    declaracoes = {s.identifier: (s.kind, s.type) for s in resultado.symbols}
    assert declaracoes == {
        "somar": ("funcao", INTEGER),
        "a": ("parametro", INTEGER),
        "b": ("parametro", INTEGER),
    }


def test_tabela_de_simbolos_com_lista_de_nomes(lexer: Lexer) -> None:
    fonte = "var x, y, z: real;\n"
    resultado = lexer.analisar(fonte)
    assert [s.identifier for s in resultado.symbols] == ["x", "y", "z"]
    assert all(s.type == REAL for s in resultado.symbols)
    assert all(s.kind == "variavel" for s in resultado.symbols)


def test_tabela_de_simbolos_registra_constante_com_igual(lexer: Lexer) -> None:
    resultado = lexer.analisar("const pi = 3.14;")
    simbolo = resultado.symbols[0]
    assert (simbolo.kind, simbolo.type, simbolo.value) == ("constante", "", "3.14")


def test_redeclaracao_gera_aviso_e_mantem_a_primeira(lexer: Lexer) -> None:
    resultado = lexer.analisar("var x: integer;\nvar x: real;\n")
    assert len(resultado.warnings) == 1
    assert "já declarado" in resultado.warnings[0].message
    assert len(resultado.symbols) == 1
    assert resultado.symbols[0].type == INTEGER


def test_simbolo_repetido_na_mesma_lista_nao_avisa(lexer: Lexer) -> None:
    resultado = lexer.analisar("var x: integer;")
    assert resultado.warnings == ()


def test_aviso_aponta_linha_e_coluna(lexer: Lexer) -> None:
    resultado = lexer.analisar("var x: integer;\n  x: real;\n")
    assert (resultado.warnings[0].line, resultado.warnings[0].column) == (2, 3)


def test_tabela_de_simbolos_nao_declara_parametro_fora_de_subprograma(lexer: Lexer) -> None:
    resultado = lexer.analisar("begin x := 1; end.")
    assert resultado.symbols == ()


def test_analise_e_deterministica(lexer: Lexer) -> None:
    primeiro = lexer.analisar(PROGRAMA_EXEMPLO)
    segundo = lexer.analisar(PROGRAMA_EXEMPLO)
    assert primeiro.tokens == segundo.tokens
    assert primeiro.errors == segundo.errors
    assert primeiro.symbols == segundo.symbols


def test_lexador_e_reutilizavel(lexer: Lexer) -> None:
    primeiro = lexer.analisar("a := 1;").tokens
    segundo = lexer.analisar("begin end.").tokens
    terceiro = lexer.analisar("a := 1;").tokens
    assert primeiro == terceiro
    assert len(primeiro) == 4
    assert [t.tipo for t in segundo] == [BEGIN, END, PONTO]


def test_estado_nao_vaza_entre_analises(lexer: Lexer) -> None:
    lexer.analisar("begin")
    lexer.analisar("x := 1;")
    assert len(lexer.analisar("y := 2;").tokens) == 4
    assert lexer.analisar("").tokens == ()