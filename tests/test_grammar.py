from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lexer.tokens import TOKEN_CLASSES  # noqa: E402
from src.parser.grammar import (  # noqa: E402
    ANEXO_I,
    DEFINICOES_DE_LEXEMA,
    EXTENSOES,
    GRAMATICA,
    LPAREN,
    RPAREN,
    VAZIA,
    linhas_da_gramatica,
    nao_terminal_de,
    terminais,
)

CONHECIDOS = frozenset(classe.tipo for classe in TOKEN_CLASSES)


def test_gramatica_nao_e_vazia() -> None:
    assert len(GRAMATICA) > 30


def test_toda_producao_tem_nome_e_alternativas() -> None:
    for producao in GRAMATICA:
        assert producao.nome, "produção sem nome"
        assert producao.alternativas, f"{producao.nome} sem alternativas"


def test_nomes_de_producao_sao_unicos() -> None:
    nomes = [p.nome for p in GRAMATICA]
    assert len(nomes) == len(set(nomes))


def test_texto_da_producao() -> None:
    producao = next(p for p in GRAMATICA if p.nome == "bloco")
    assert producao.texto() == "bloco → BEGIN instrucoes END ;"


def test_todo_nao_terminal_citado_existe() -> None:
    nomes = {p.nome for p in GRAMATICA}
    definicoes = {p.nome for p in DEFINICOES_DE_LEXEMA}
    citados: set[str] = set()
    for producao in GRAMATICA:
        if producao.nome in definicoes:
            continue  # notação de expressão regular, não símbolo da gramática
        for palavra in _palavras(producao.texto()):
            if palavra[0].islower():
                citados.add(palavra)
    assert citados <= nomes, citados - nomes


def _palavras(texto: str) -> list[str]:
    import re

    return re.findall(r"[A-Za-z_][A-Za-z_0-9]*", texto)


def test_todo_terminal_nomeado_existe_no_lexer() -> None:
    assert terminais() <= CONHECIDOS


def test_nenhum_terminal_desconhecido() -> None:
    assert sorted(terminais() - CONHECIDOS) == []


def test_terminais_principais_estao_presentes() -> None:
    esperados = {
        "PROGRAM", "BEGIN", "END", "CONST", "VAR", "TYPE", "RECORD",
        "ENUM", "PROCEDURE", "FUNCTION", "IF", "ELSE", "THEN", "WHILE", "DO",
        "REPEAT", "UNTIL", "BREAK", "CONTINUE", "FOR", "TO", "DOWNTO", "OU",
        "E", "INTEGER", "REAL", "CHAR", "STRING",
    }
    assert esperados <= terminais()


def test_id_num_e_literal_sao_producoes_definicionais() -> None:
    # No enunciado `ID`, `NUM` e `LITERAL` têm produção própria; por isso não
    # aparecem como terminais de `terminais()`, e sim em `DEFINICOES_DE_LEXEMA`.
    nomes = {p.nome for p in GRAMATICA}
    assert {"ID", "NUM", "LITERAL"} <= nomes
    assert not {"ID", "NUM", "LITERAL"} & terminais()


def test_anexo_i_esta_transcrito() -> None:
    nomes = {p.nome for p in ANEXO_I}
    for exigido in (
        "programa", "bloco", "declaracoes", "declaracaoConstante", "declConsList",
        "declaracaoVariavel", "declVarList", "declVar", "conjuntoIds", "tipo",
        "valor", "declProcedimento", "declProc", "parametros", "instrucoes",
        "inst", "parametros2", "expr", "expr2", "exprComparacao",
        "exprComparacao2", "exprOp", "exprOp2", "termo", "termo2", "unario",
        "fator", "variavel",
    ):
        assert exigido in nomes, exigido


def test_anexo_i_inclui_as_comparacoes_do_enunciado() -> None:
    comparacao = nao_terminal_de(GRAMATICA, "exprComparacao2")[0]
    for operador in ("=", "<>", "<", "<=", ">", ">="):
        assert any(operador in alternativa for alternativa in comparacao.alternativas)
    assert VAZIA in comparacao.alternativas


def test_anexo_i_mantem_as_dez_instrucoes() -> None:
    inst = nao_terminal_de(GRAMATICA, "inst")[0]
    for pedaco in (
        "ID := expr ;",
        "ID [ expr ] := expr ;",
        "ID ( parametros2 ) ;",
        "IF expr THEN inst",
        "IF expr THEN inst ELSE inst",
        "WHILE expr DO inst",
        "REPEAT inst UNTIL expr ;",
        "BREAK ;",
        "CONTINUE ;",
        "bloco",
    ):
        assert pedaco in inst.alternativas, pedaco


def test_extensoes_adicionam_for() -> None:
    inst = nao_terminal_de(GRAMATICA, "inst")[0]
    assert "FOR ID := expr TO expr DO inst" in inst.alternativas
    assert "FOR ID := expr DOWNTO expr DO inst" in inst.alternativas


def test_extensoes_adicionam_registro_e_enumeracao() -> None:
    decl_tipo = nao_terminal_de(GRAMATICA, "declTipo")[0]
    assert "ID = RECORD campos END ;" in decl_tipo.alternativas
    assert "ID = listaEnum ;" in decl_tipo.alternativas
    assert "ID = tipoSimples ;" in decl_tipo.alternativas


def test_declaracoes_aceita_secao_de_tipos() -> None:
    declaracoes = nao_terminal_de(GRAMATICA, "declaracoes")[0]
    assert any("declaracaoTipo" in a for a in declaracoes.alternativas)


def test_tipo_simples_aceita_tipo_definido_pelo_usuario() -> None:
    tipo = nao_terminal_de(GRAMATICA, "tipoSimples")[0]
    assert "ID" in tipo.alternativas


def test_lista_enum_aceita_intervalo() -> None:
    lista = nao_terminal_de(GRAMATICA, "listaEnum")[0]
    assert any(".." in alternativa for alternativa in lista.alternativas)


def test_mergem_nao_perde_alternativas_do_anexo_i() -> None:
    inst = nao_terminal_de(GRAMATICA, "inst")[0]
    original = nao_terminal_de(ANEXO_I, "inst")[0]
    for alternativa in original.alternativas:
        assert alternativa in inst.alternativas


def test_definicoes_de_lexema_foram_separadas() -> None:
    nomes = {p.nome for p in DEFINICOES_DE_LEXEMA}
    assert nomes == {"digitos", "dig", "ID", "LITERAL"}


def test_definicoes_de_lexema_estao_na_gramatica() -> None:
    nomes = {p.nome for p in GRAMATICA}
    assert {p.nome for p in DEFINICOES_DE_LEXEMA} <= nomes


def test_definicoes_de_lexema_nao_viram_terminal() -> None:
    # `digitos`, `dig`, `letra` e `CARACTER_ESPECIAL` são meta-símbolos.
    for meta in ("digitos", "dig", "letra", "CARACTER_ESPECIAL"):
        assert meta not in terminais()


def test_parentesis_de_agrupamento_nao_confundem_com_token() -> None:
    fator = nao_terminal_de(GRAMATICA, "fator")[0]
    assert f"{LPAREN} expr {RPAREN}" in fator.alternativas


def test_linhas_para_exibicao() -> None:
    linhas = linhas_da_gramatica()
    assert len(linhas) == len(GRAMATICA)
    assert all("→" in linha for linha in linhas)


def test_gramatica_nao_depende_de_estado_global_mutavel() -> None:
    antes = linhas_da_gramatica()
    GRAMATICA[0].alternativas  # leitura não altera nada
    assert linhas_da_gramatica() == antes


@pytest.mark.parametrize("secao", [ANEXO_I, EXTENSOES])
def test_secoes_tem_producoes_validas(secao: tuple) -> None:
    assert secao
    for producao in secao:
        assert isinstance(producao.nome, str)
        assert all(isinstance(a, str) and a for a in producao.alternativas)