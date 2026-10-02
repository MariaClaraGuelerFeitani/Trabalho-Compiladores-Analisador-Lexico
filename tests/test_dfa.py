from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lexer import dfa  # noqa: E402
from src.lexer.tokens import (  # noqa: E402
    ID,
    LITERAL,
    NUM,
    PALAVRAS_RESERVADAS,
    SIMBOLOS,
    TOKEN_CLASSES,
)

NOMES = {estado.name for estado in dfa.ESTADOS}


def test_tem_estado_inicial() -> None:
    assert dfa.ESTADO_INICIAL in NOMES


def test_todos_os_destinos_existem() -> None:
    inexistentes = {t.target for t in dfa.TRANSICOES} - NOMES
    assert inexistentes == set()


def test_todas_as_origens_existem() -> None:
    inexistentes = {t.state for t in dfa.TRANSICOES} - NOMES
    assert inexistentes == set()


def test_automato_e_deterministico() -> None:
    contagem = Counter((t.state, t.symbol) for t in dfa.TRANSICOES)
    repetidos = [par for par, total in contagem.items() if total > 1]
    assert repetidos == []


def test_nenhum_par_estado_simbolo_repete_destino() -> None:
    destinos: dict[tuple[str, str], set[str]] = {}
    for transicao in dfa.TRANSICOES:
        destinos.setdefault((transicao.state, transicao.symbol), set()).add(transicao.target)
    assert all(len(valores) == 1 for valores in destinos.values())


def test_todos_os_estados_sao_alcancaveis() -> None:
    assert dfa.alcancaveis() == NOMES


def test_estado_inicial_e_alcancavel() -> None:
    assert dfa.ESTADO_INICIAL in dfa.alcancaveis()


def test_todo_estado_de_aceitacao_tem_token_conhecido() -> None:
    conhecidos = {classe.tipo for classe in TOKEN_CLASSES}
    for nome, token in dfa.ACEITACAO.items():
        assert token in conhecidos, f"{nome} aceita token desconhecido {token}"


def test_estado_de_aceitacao_marca_a_bandeira() -> None:
    por_nome = {estado.name: estado for estado in dfa.ESTADOS}
    for nome, token in dfa.ACEITACAO.items():
        assert por_nome[nome].is_accepting
        assert por_nome[nome].token == token


def test_apenas_o_estado_inicial_nao_aceita() -> None:
    nao_aceitaveis = {estado.name for estado in dfa.ESTADOS if not estado.is_accepting}
    assert nao_aceitaveis <= (
        {dfa.ESTADO_INICIAL, dfa.ESTADO_NUMERO_DECIMAL, dfa.ESTADO_LITERAL_DENTRO}
        | {nome for nome in NOMES if nome.startswith(dfa.PREFIXO_PALAVRA)}
    )
    assert dfa.ESTADO_INICIAL in nao_aceitaveis


def test_prefixos_de_palavra_nao_sao_aceitaveis() -> None:
    nao_aceitaveis = {estado.name for estado in dfa.ESTADOS if not estado.is_accepting}
    for nome in nao_aceitaveis:
        if not nome.startswith(dfa.PREFIXO_PALAVRA):
            continue
        prefixo = nome[len(dfa.PREFIXO_PALAVRA) :]
        assert prefixo not in PALAVRAS_RESERVADAS


def test_identificador_e_aceito_em_q_id() -> None:
    assert dfa.ACEITACAO[dfa.ESTADO_IDENTIFICADOR] == ID


def test_q_id_continua_em_letra_digito_e_sublinhado() -> None:
    assert dfa.delta(dfa.ESTADO_IDENTIFICADOR, dfa.LETRA) == dfa.ESTADO_IDENTIFICADOR
    assert dfa.delta(dfa.ESTADO_IDENTIFICADOR, dfa.DIGITO) == dfa.ESTADO_IDENTIFICADOR
    assert dfa.delta(dfa.ESTADO_IDENTIFICADOR, "_") == dfa.ESTADO_IDENTIFICADOR


@pytest.mark.parametrize("palavra", sorted(PALAVRAS_RESERVADAS))
def test_cada_palavra_reservada_atinge_estado_de_aceitacao(palavra: str) -> None:
    estado, token, lexema = dfa.simular(palavra)
    assert token == PALAVRAS_RESERVADAS[palavra]
    assert lexema == palavra
    assert dfa.ACEITACAO[estado] == PALAVRAS_RESERVADAS[palavra]


@pytest.mark.parametrize("palavra", sorted(PALAVRAS_RESERVADAS))
def test_palavra_reservada_nao_diferencia_caixa(palavra: str) -> None:
    for variante in (palavra.upper(), palavra.capitalize()):
        assert dfa.simular(variante)[1] == PALAVRAS_RESERVADAS[palavra]


@pytest.mark.parametrize(
    "identificador",
    ["programador", "integerx", "variavel", "continuo", "realce", "formula", "esquerda", "efetivo"],
)
def test_identificador_que_so_comeca_como_palavra_reservada(identificador: str) -> None:
    estado, token, lexema = dfa.simular(identificador)
    assert token == ID
    assert lexema == identificador
    assert estado == dfa.ESTADO_IDENTIFICADOR


def test_e_e_else_compartilham_prefixo() -> None:
    assert dfa.simular("e")[1] == "E"
    assert dfa.simular("else")[1] == "ELSE"
    assert dfa.simular("eba")[1] == ID


def test_ramo_de_palavra_reservada_cai_para_identificador() -> None:
    estados = [nome for nome in NOMES if nome.startswith(dfa.PREFIXO_PALAVRA)]
    assert estados
    for nome in estados:
        assert dfa.delta(nome, dfa.OUTRO_ID) == dfa.ESTADO_IDENTIFICADOR


def test_ramos_de_palavra_reservada_nao_saem_do_lexema() -> None:
    for nome in NOMES:
        if not nome.startswith(dfa.PREFIXO_PALAVRA):
            continue
        for simbolo in dfa.simbolos_de(nome):
            assert simbolo == dfa.OUTRO_ID or len(simbolo) == 1


@pytest.mark.parametrize(
    ("entrada", "token"),
    [
        ("0", NUM),
        ("42", NUM),
        ("007", NUM),
        ("3.14", NUM),
        ("0.5", NUM),
    ],
)
def test_numeros_sao_aceitos(entrada: str, token: str) -> None:
    assert dfa.simular(entrada)[1] == token


def test_ponto_so_aceita_numero_com_digito_depois() -> None:
    assert dfa.ESTADO_NUMERO_DECIMAL not in dfa.ACEITACAO
    assert dfa.ACEITACAO[dfa.ESTADO_NUMERO_FRACAO] == NUM
    assert dfa.delta(dfa.ESTADO_NUMERO_INTEIRO, ".") == dfa.ESTADO_NUMERO_DECIMAL
    assert dfa.delta(dfa.ESTADO_NUMERO_DECIMAL, dfa.DIGITO) == dfa.ESTADO_NUMERO_FRACAO


def test_ponto_no_inicio_nao_e_numero() -> None:
    assert dfa.simular(".5")[1] == "PONTO"


def test_literal_precisa_de_apostrofo_de_abertura_e_fecho() -> None:
    assert dfa.ACEITACAO[dfa.ESTADO_LITERAL_FIM] == LITERAL
    assert dfa.ESTADO_LITERAL_DENTRO not in dfa.ACEITACAO
    assert dfa.simular("'abc'")[1] == LITERAL
    assert dfa.simular("''")[1] == LITERAL


def test_literal_aspas_duplas_voltam_para_dentro() -> None:
    assert dfa.delta(dfa.ESTADO_LITERAL_FIM, "'") == dfa.ESTADO_LITERAL_DENTRO
    assert dfa.simular("'d''art'")[2] == "'d''art'"


def test_simbolo_de_entrada_unico_para_cada_lexema() -> None:
    entradas = {
        t.symbol for t in dfa.TRANSICOES_POR_ESTADO[dfa.ESTADO_INICIAL]
    }
    for lexema, _ in SIMBOLOS:
        assert lexema[0] in entradas


@pytest.mark.parametrize(("lexema", "token"), SIMBOLOS)
def test_simbolo_e_reconhecido_pelo_automato(lexema: str, token: str) -> None:
    assert dfa.simular(lexema)[1] == token


def test_maximo_casamento_no_automato() -> None:
    assert dfa.simular(":=")[2] == ":="
    assert dfa.simular("<=")[2] == "<="
    assert dfa.simular("<>")[2] == "<>"
    assert dfa.simular(">=")[2] == ">="
    assert dfa.simular("<")[2] == "<"
    assert dfa.simular("12.")[2] == "12"


def test_simbolo_desconhecido_nao_tem_transicao() -> None:
    assert dfa.delta(dfa.ESTADO_INICIAL, "@") is None
    assert dfa.delta(dfa.ESTADO_INICIAL, "#") is None
    assert dfa.delta(dfa.ESTADO_INICIAL, "\n") is None
    assert dfa.delta(dfa.ESTADO_INICIAL, " ") is None


def test_simbolo_desconhecido_para_o_lexema(entrada: str = "@") -> None:
    assert dfa.simular(entrada)[1] == ""


def test_tabela_de_transicao_e_igual_a_lista() -> None:
    esperado = {(t.state, t.symbol): t.target for t in dfa.TRANSICOES}
    assert dfa.TABELA == esperado
    assert len(dfa.TABELA) == len(dfa.TRANSICOES)


def test_indices_sao_consistentes() -> None:
    for indice, estado in enumerate(dfa.ESTADOS):
        assert dfa.INDICES[estado.name] == indice


def test_classes_de_token_cobrem_todos_os_aceitos() -> None:
    tipos = {classe.tipo for classe in TOKEN_CLASSES}
    assert tipos == set(dfa.ACEITACAO.values())


def test_classes_de_token_incluem_a_regex_do_identificador() -> None:
    identificador = next(c for c in TOKEN_CLASSES if c.tipo == ID)
    assert identificador.regex == "[A-Za-z][A-Za-z0-9_]{0,14}"
    assert identificador.description


def test_numero_de_estados_e_estavel() -> None:
    assert len(dfa.ESTADOS) == 119
    assert len(dfa.TRANSICOES) == 218
    assert len(dfa.ACEITACAO) == 46