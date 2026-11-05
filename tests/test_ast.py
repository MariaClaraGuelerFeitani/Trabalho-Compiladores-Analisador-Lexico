"""Testes da AST e da validação de break/continue (etapa 3)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parser.ast import (
    NoAtribuicao,
    NoBinario,
    NoDesvio,
    NoEnquanto,
    NoNumero,
    NoPara,
    NoPrograma,
    NoRepita,
    NoVariavel,
    para_ascii,
    para_dict,
    para_json,
)
from src.parser.service import AnaliseService

servico = AnaliseService()


def arvore(fonte: str):
    resultado = servico.analyze(fonte)
    assert resultado.all_errors == (), [e.message for e in resultado.all_errors]
    return resultado.arvore


# --- Estrutura da AST -----------------------------------------------------


def test_ast_respeita_precedencia_de_multiplicacao() -> None:
    programa = arvore(
        "programa P; var X: integer; begin X := 7 + 3 * 5; end."
    )
    assert isinstance(programa, NoPrograma)
    atribuicao = programa.comandos[0]
    assert isinstance(atribuicao, NoAtribuicao)
    assert isinstance(atribuicao.alvo, NoVariavel)
    assert atribuicao.alvo.nome == "X"

    soma = atribuicao.expressao
    assert isinstance(soma, NoBinario)
    assert soma.operador == "+"
    assert isinstance(soma.esquerda, NoNumero)
    assert soma.esquerda.valor == "7"

    produto = soma.direita
    assert isinstance(produto, NoBinario)
    assert produto.operador == "*"
    assert produto.esquerda.valor == "3"
    assert produto.direita.valor == "5"


def test_ast_parenteses_mudam_a_raiz() -> None:
    programa = arvore(
        "programa P; var X: integer; begin X := (7 + 3) * 5; end."
    )
    produto = programa.comandos[0].expressao
    assert isinstance(produto, NoBinario)
    assert produto.operador == "*"
    assert produto.esquerda.operador == "+"


def test_ast_associatividade_a_esquerda() -> None:
    programa = arvore(
        "programa P; var X: integer; begin X := 10 - 3 - 2; end."
    )
    raiz = programa.comandos[0].expressao
    assert raiz.operador == "-"
    assert raiz.esquerda.operador == "-"
    assert raiz.esquerda.esquerda.valor == "10"


def test_ascii_desenha_operador_no_topo() -> None:
    programa = arvore(
        "programa P; var X: integer; begin X := 7 + 3 * 5; end."
    )
    desenho = para_ascii(programa.comandos[0].expressao)
    linhas = [linha.strip() for linha in desenho.splitlines()]
    assert linhas[0] == "+"
    assert "/" in desenho and "\\" in desenho
    assert "7" in desenho
    assert "*" in desenho
    assert desenho.index("+") < desenho.index("*")


def test_ascii_do_programa_completo_contem_comandos() -> None:
    programa = arvore(
        "programa P; var i: integer; begin "
        "while i < 3 do begin i := i + 1; break; end; "
        "end."
    )
    desenho = para_ascii(programa)
    assert "Programa P" in desenho
    assert "Enquanto" in desenho
    assert "break" in desenho


def test_json_serializa_tipos_e_filhos() -> None:
    programa = arvore(
        "programa P; var X: integer; begin X := 7 + 3 * 5; end."
    )
    dados = para_dict(programa)
    assert dados["no"] == "Programa"
    assert dados["nome"] == "P"
    assert dados["comandos"][0]["no"] == "Atribuicao"
    expressao = dados["comandos"][0]["expressao"]
    assert expressao["no"] == "Binario"
    assert expressao["operador"] == "+"
    assert expressao["direita"]["operador"] == "*"
    # A saída textual é JSON válido.
    assert json.loads(para_json(programa))["no"] == "Programa"


# --- AST do programa inteiro ---------------------------------------------


def test_ast_inclui_while_for_e_repeat() -> None:
    programa = arvore(
        "programa P; var i: integer; begin "
        "while i < 3 do break; "
        "for i := 1 to 3 do continue; "
        "repeat break until i = 0; "
        "end."
    )
    tipos = [type(no) for no in programa.comandos]
    assert tipos == [NoEnquanto, NoPara, NoRepita]
    assert isinstance(programa.comandos[0].corpo, NoDesvio)
    assert programa.comandos[0].corpo.comando == "break"
    assert isinstance(programa.comandos[1].corpo, NoDesvio)
    assert programa.comandos[1].corpo.comando == "continue"


# --- break/continue fora de laço -----------------------------------------


def erros(fonte: str) -> list[str]:
    return [e.message for e in servico.analyze(fonte).all_errors]


def test_break_fora_de_laco_e_erro() -> None:
    assert any("fora de um laço" in m for m in erros("programa P; begin break; end."))


def test_continue_fora_de_laco_e_erro() -> None:
    assert any(
        "fora de um laço" in m for m in erros("programa P; begin continue; end.")
    )


def test_break_e_continue_dentro_de_laco_sao_aceitos() -> None:
    fonte = (
        "programa P; var i: integer; begin "
        "while i < 3 do begin break; end; "
        "for i := 1 to 3 do continue; "
        "repeat continue until i = 0; "
        "end."
    )
    assert servico.analyze(fonte).all_errors == ()


def test_laco_aninhado_valida_desvio_no_interno() -> None:
    fonte = (
        "programa P; var i: integer; begin "
        "while i < 3 do while i < 2 do break; "
        "end."
    )
    assert servico.analyze(fonte).all_errors == ()
