"""Testes da análise semântica da etapa 2.

A suíte exercita o módulo `src/semantic/` de ponta a ponta pelo
`AnaliseService`, mais os três arquivos de caso de teste em
`relatorio/casos_de_teste/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lexer import PROGRAMA_EXTENSOES
from src.parser import Parser
from src.parser.service import AnaliseService
from src.semantic import AnaliseSemantica

servico = AnaliseService()

CASOS = Path(__file__).resolve().parent.parent / "relatorio" / "casos_de_teste"


def analisar(fonte: str):
    return servico.analyze(fonte)


def erros_semanticos(fonte: str) -> list[str]:
    return [e.message for e in analisar(fonte).semantic_errors]


def avisos_semanticos(fonte: str) -> list[str]:
    return [w.message for w in analisar(fonte).semantic_warnings]


def sem_diagnosticos(fonte: str) -> None:
    resultado = analisar(fonte)
    assert resultado.semantic_errors == (), [
        (e.line, e.column, e.message) for e in resultado.semantic_errors
    ]
    assert resultado.semantic_warnings == (), [
        (w.line, w.column, w.message) for w in resultado.semantic_warnings
    ]


# --- Programas semanticamente válidos --------------------------------------


@pytest.mark.parametrize(
    "fonte",
    [
        "programa P; begin end.",
        "programa P; var x: integer; begin x := 1; end.",
        "programa P; var x: real; begin x := 1; end.",
        "programa P; var x: real; begin x := 1.5; end.",
        "programa P; var x: string; begin x := 'oi'; end.",
        "programa P; var x: integer; begin x := 1 + 2 * 3 - 4; end.",
        "programa P; var x: real; begin x := 1 / 2; end.",
        "programa P; var x: integer; begin x := -1; end.",
        "programa P; var a, b: integer; begin if a < b then a := 1; end.",
        "programa P; var a, b: integer; begin if a < b ou a > b e a = b then a := 1; end.",
        "programa P; var a: integer; begin while a > 0 do a := a - 1; end.",
        "programa P; var a: integer; begin repeat a := a - 1; until a = 0; end.",
        "programa P; var i: integer; begin for i := 1 to 10 do i := i; end.",
        "programa P; var i: integer; const c: integer = 3; begin for i := c downto 1 do i := i; end.",
        "programa P; const c = 1; var x: integer; begin x := c; end.",
        "programa P; const c: real = 1; var x: real; begin x := c; end.",
        "programa P; type idade = integer; var a: idade; begin a := 1; end.",
        "programa P; type cor = (azul); var c: cor; begin c := azul; end.",
        "programa P; type p = record x: integer; end; var v: p; begin v.x := 1; end.",
        "programa P; type p = record x: real; end; var v: p; begin v.x := 1; end.",
        "programa P; procedure Q; begin end; begin Q; end.",
        "programa P; procedure Q(a: integer); begin end; begin Q(1); end.",
        "programa P; procedure Q(a, b: real); begin end; begin Q(1, 2.0); end.",
        "programa P; function f(n: integer): integer; begin f := n; end; begin end.",
        "programa P; function f(n: integer): integer; begin f := n; end; begin f(1); end.",
        "programa P; var x: integer; function f(n: integer): integer; begin f := n; end; begin x := f(1); end.",
        "programa P; function f: integer; begin f := 1; end; begin end.",
        "programa P; var x: integer; procedure Q; var x: real; begin x := 1.0; end; begin x := 1; end.",
        "programa P; begin writeln('texto', 1, 2.5); end.",
        "programa P; var x: integer; begin readln(x); end.",
        "programa P; var a, b: char; begin if a = b then a := 'x'; end.",
    ],
)
def test_programas_semanticamente_validos(fonte: str) -> None:
    sem_diagnosticos(fonte)


# --- Verificação de declaração ---------------------------------------------


def test_variavel_nao_declarada() -> None:
    erros = erros_semanticos("programa P; begin x := 1; end.")
    assert len(erros) == 1
    assert "'x' não declarado" in erros[0]


def test_erro_de_nao_declarado_tem_posicao() -> None:
    resultado = analisar("programa P;\nbegin\n  x := 1;\nend.")
    erro = resultado.semantic_errors[0]
    assert erro.line == 3
    assert erro.column == 3
    assert erro.lexeme == "x"
    assert erro.message.startswith("semantica: ")


def test_uso_em_expressao_nao_declarado() -> None:
    assert any("'y' não declarado" in m for m in erros_semanticos("programa P; var x: integer; begin x := y; end."))


def test_chamada_nao_declarada() -> None:
    erros = erros_semanticos("programa P; begin Q(1); end.")
    assert any("'Q' não declarado" in m for m in erros)


def test_variavel_local_nao_vaza_para_o_global() -> None:
    fonte = (
        "programa P; var x: integer; "
        "procedure Q; var y: integer; begin y := 1; end; "
        "begin x := y; end."
    )
    assert any("'y' não declarado" in m for m in erros_semanticos(fonte))


def test_sombreamento_em_escopo_local_e_permitido() -> None:
    fonte = (
        "programa P; var x: integer; "
        "procedure Q; var x: real; begin x := 1.0; end; "
        "begin x := 1; end."
    )
    sem_diagnosticos(fonte)


def test_parametro_visivel_apenas_no_corpo() -> None:
    fonte = (
        "programa P; procedure Q(a: integer); begin end; "
        "begin Q(a); end."
    )
    assert any("'a' não declarado" in m for m in erros_semanticos(fonte))


# --- Redeclaração -----------------------------------------------------------


def test_redeclaracao_no_mesmo_escopo() -> None:
    fonte = "programa P; var x: integer; x: real; begin end."
    assert any("'x' já declarado" in m for m in erros_semanticos(fonte))


def test_redeclaracao_de_constante() -> None:
    fonte = "programa P; const c = 1; c = 2; begin end."
    assert any("'c' já declarado" in m for m in erros_semanticos(fonte))


def test_redeclaracao_de_procedimento() -> None:
    fonte = (
        "programa P; procedure Q; begin end; "
        "procedure Q; begin end; begin end."
    )
    assert any("'Q' já declarado" in m for m in erros_semanticos(fonte))


def test_redeclaracao_de_parametro() -> None:
    fonte = (
        "programa P; procedure Q(a: integer; a: real); begin end; "
        "begin end."
    )
    assert any("'a' já declarado" in m for m in erros_semanticos(fonte))


def test_constante_de_enumeracao_redeclarada() -> None:
    fonte = "programa P; type cor = (azul); var azul: integer; begin end."
    assert any("'azul' já declarado" in m for m in erros_semanticos(fonte))


# --- Compatibilidade de tipos em atribuição ---------------------------------


@pytest.mark.parametrize(
    "fonte,trecho",
    [
        ("programa P; var x: integer; begin x := 'abc'; end.", "string a integer"),
        ("programa P; var x: integer; r: real; begin x := r; end.", "real a integer"),
        ("programa P; var x: integer; begin x := 1.5; end.", "real a integer"),
        ("programa P; var x: real; begin x := 'abc'; end.", "string a real"),
        ("programa P; var x: string; begin x := 1; end.", "integer a string"),
        ("programa P; type cor = (azul); var c: cor; begin c := 1; end.", "integer a cor"),
        ("programa P; type cor = (azul); var c: cor; var o: cor; begin c := o; end.", None),
    ],
)
def test_atribuicao_por_tipo(fonte: str, trecho: str | None) -> None:
    erros = erros_semanticos(fonte)
    if trecho is None:
        assert erros == []
    else:
        assert any(trecho in m for m in erros), erros


def test_atribuicao_de_enum_de_outro_tipo() -> None:
    fonte = (
        "programa P; type cor = (azul); type dia = (seg); "
        "var c: cor; begin c := seg; end."
    )
    assert any("dia a cor" in m for m in erros_semanticos(fonte))


def test_atribuicao_a_funcao_de_fora_do_corpo() -> None:
    fonte = (
        "programa P; function f: integer; begin f := 1; end; "
        "begin f := 2; end."
    )
    assert any("somente o próprio corpo" in m for m in erros_semanticos(fonte))


def test_atribuicao_a_constante() -> None:
    fonte = "programa P; const c = 1; begin c := 2; end."
    assert any("constante" in m for m in erros_semanticos(fonte))


def test_atribuicao_a_procedimento() -> None:
    fonte = (
        "programa P; procedure Q; begin end; "
        "begin Q := 1; end."
    )
    assert any("não é uma variável" in m for m in erros_semanticos(fonte))


# --- Expressões aritméticas e lógicas ---------------------------------------


@pytest.mark.parametrize(
    "fonte,trecho",
    [
        ("programa P; var x: integer; s: string; begin x := 1 + s; end.", "operandos incompatíveis em '+'"),
        ("programa P; var x: integer; s: string; begin x := 1 * s; end.", "operandos incompatíveis em '*'"),
        ("programa P; var s: string; begin s := -'a'; end.", "espera um valor numérico"),
        ("programa P; var a, b: integer; begin if a ou b then a := 1; end.", "espera valores lógicos"),
        ("programa P; var a: integer; begin a := 1 e 2; end.", "espera valores lógicos"),
        ("programa P; var a: integer; s: string; begin if a < s then a := 1; end.", "tipos incompatíveis em '<'"),
        ("programa P; var a: string; s: string; begin if a < s then a := 'x'; end.", None),
    ],
)
def test_operadores_por_tipo(fonte: str, trecho: str | None) -> None:
    erros = erros_semanticos(fonte)
    if trecho is None:
        assert erros == []
    else:
        assert any(trecho in m for m in erros), erros


def test_divisao_sempre_produz_real() -> None:
    # `4 / 2` é real em Pascal; atribuir a integer é incompatível.
    erros = erros_semanticos("programa P; var x: integer; begin x := 4 / 2; end.")
    assert any("real a integer" in m for m in erros)


def test_mod_e_div_entre_inteiros() -> None:
    sem_diagnosticos(
        "programa P; var a, b: integer; begin a := 7 mod 3; b := 7 div 2; end."
    )


def test_mod_exige_operandos_inteiros() -> None:
    fonte = "programa P; var x: real; y: integer; begin y := x mod 2; end."
    assert any("espera operandos inteiros" in m for m in erros_semanticos(fonte))


def test_div_exige_operandos_inteiros() -> None:
    fonte = "programa P; var x: real; y: integer; begin y := 2 div x; end."
    assert any("espera operandos inteiros" in m for m in erros_semanticos(fonte))


def test_sqrt_e_sqr_sao_reconhecidas_sem_declaracao() -> None:
    sem_diagnosticos(
        "programa P; var x, y: real; "
        "begin x := sqrt(sqr(3.0) + sqr(4.0)); y := sqr(x); end."
    )


def test_sqrt_devolve_real_e_sqr_devolve_o_tipo_do_argumento() -> None:
    # `sqrt` sempre é real (mesmo sobre integer); `sqr` segue o argumento
    fonte = "programa P; var i: integer; r: real; begin i := sqr(3); r := sqrt(2); end."
    sem_diagnosticos(fonte)


def test_sqrt_de_argumento_nao_numerico() -> None:
    fonte = "programa P; var s: string; r: real; begin r := sqrt(s); end."
    assert any("esperado número" in m for m in erros_semanticos(fonte))


def test_sqrt_com_argumento_roubado_e_como_instrucao() -> None:
    assert any(
        "espera 1 argumento(s)" in m
        for m in erros_semanticos("programa P; var r: real; begin r := sqrt(1, 2); end.")
    )
    assert any(
        "não pode ser usada como instrução" in m
        for m in erros_semanticos("programa P; begin sqr(3); end.")
    )


def test_condicao_de_if_deve_ser_logica() -> None:
    fonte = "programa P; var x: integer; begin if x then x := 1; end."
    assert any("condição lógica" in m for m in erros_semanticos(fonte))


def test_condicao_de_while_deve_ser_logica() -> None:
    fonte = "programa P; var x: integer; begin while x do x := 1; end."
    assert any("condição lógica" in m for m in erros_semanticos(fonte))


def test_condicao_de_until_deve_ser_logica() -> None:
    fonte = "programa P; var x: integer; begin repeat x := 1; until x; end."
    assert any("condição lógica" in m for m in erros_semanticos(fonte))


# --- Tipos definidos pelo usuário -------------------------------------------


def test_tipo_nao_declarado_na_variavel() -> None:
    fonte = "programa P; var x: inexistente; begin end."
    assert any("tipo 'inexistente' não declarado" in m for m in erros_semanticos(fonte))


def test_campo_inexistente_no_registro() -> None:
    fonte = (
        "programa P; type p = record x: integer; end; "
        "var v: p; begin v.z := 1; end."
    )
    assert any("campo 'z' não existe" in m for m in erros_semanticos(fonte))


def test_acesso_a_campo_de_nao_registro() -> None:
    fonte = "programa P; var x: integer; begin x.campo := 1; end."
    assert any("não é um registro" in m for m in erros_semanticos(fonte))


def test_registro_com_campo_de_tipo_inexistente() -> None:
    fonte = "programa P; type p = record a: nada; end; begin end."
    assert any("tipo 'nada' não declarado" in m for m in erros_semanticos(fonte))


def test_alias_de_tipo_valida_o_uso() -> None:
    fonte = (
        "programa P; type idade = integer; var a: idade; "
        "begin a := 'x'; end."
    )
    assert any("string a integer" in m for m in erros_semanticos(fonte))


def test_tipo_usado_como_valor() -> None:
    fonte = "programa P; type cor = (azul); var x: integer; begin x := cor; end."
    assert any("é um tipo" in m for m in erros_semanticos(fonte))


# --- Procedimentos e funções ------------------------------------------------


def test_numero_de_argumentos() -> None:
    fonte = (
        "programa P; procedure Q(a: integer); begin end; "
        "begin Q(1, 2); end."
    )
    assert any("espera 1 argumento(s), encontrado 2" in m for m in erros_semanticos(fonte))


def test_argumento_faltando() -> None:
    fonte = (
        "programa P; procedure Q(a: integer); begin end; "
        "begin Q(); end."
    )
    assert any("encontrado 0" in m for m in erros_semanticos(fonte))


def test_tipo_de_argumento() -> None:
    fonte = (
        "programa P; procedure Q(a: integer); begin end; "
        "begin Q('x'); end."
    )
    assert any("esperado integer, encontrado string" in m for m in erros_semanticos(fonte))


def test_funcao_como_procedimento_e_permitido() -> None:
    # Chamar função descartando o resultado é válido em Pascal.
    sem_diagnosticos(
        "programa P; function f(n: integer): integer; begin f := n; end; "
        "begin f(1); end."
    )


def test_procedimento_em_expressao_e_erro() -> None:
    fonte = (
        "programa P; var x: integer; procedure Q; begin end; "
        "begin x := Q; end."
    )
    assert any("é um procedimento" in m for m in erros_semanticos(fonte))


def test_variavel_chamada_como_funcao() -> None:
    fonte = "programa P; var x: integer; begin x := x(1); end."
    assert any("não é um procedimento ou função" in m for m in erros_semanticos(fonte))


def test_funcao_sem_parenteses_com_argumentos() -> None:
    fonte = (
        "programa P; function f(n: integer): integer; begin f := n; end; "
        "begin f := f; end."
    )
    assert any("exige 1 argumento(s)" in m for m in erros_semanticos(fonte))


def test_funcao_de_retorno_incompativel() -> None:
    fonte = (
        "programa P; function f(n: integer): integer; begin f := 'x'; end; "
        "begin end."
    )
    assert any("string a integer" in m for m in erros_semanticos(fonte))


def test_tipo_de_retorno_nao_declarado() -> None:
    fonte = (
        "programa P; function f: nada; begin f := 1; end; begin end."
    )
    assert any("tipo 'nada' não declarado" in m for m in erros_semanticos(fonte))


# --- Laço for ---------------------------------------------------------------


def test_for_com_variavel_nao_declarada() -> None:
    fonte = "programa P; begin for i := 1 to 3 do i := 1; end."
    assert any("'i' não declarado" in m for m in erros_semanticos(fonte))


def test_for_sobre_constante() -> None:
    fonte = "programa P; const c = 1; begin for c := 1 to 3 do c := 1; end."
    assert any("laço 'for' exige uma variável" in m for m in erros_semanticos(fonte))


def test_for_sobre_variavel_real() -> None:
    fonte = "programa P; var r: real; begin for r := 1 to 3 do r := 1.0; end."
    assert any("espera uma variável integer" in m for m in erros_semanticos(fonte))


def test_for_com_limite_real() -> None:
    fonte = (
        "programa P; var i: integer; r: real; "
        "begin for i := 1 to r do i := i; end."
    )
    assert any("limites inteiros" in m for m in erros_semanticos(fonte))


def test_for_com_limites_inteiros_e_valido() -> None:
    sem_diagnosticos(
        "programa P; var i: integer; const n = 3; "
        "begin for i := n downto 1 do i := i; end."
    )


# --- Constantes -------------------------------------------------------------


def test_constante_com_tipo_incompativel() -> None:
    fonte = "programa P; const c: integer = 'x'; begin end."
    assert any("incompatível" in m for m in erros_semanticos(fonte))


def test_constante_com_tipo_inteiro_e_valor_real() -> None:
    fonte = "programa P; const c: integer = 1.5; begin end."
    assert any("incompatível" in m for m in erros_semanticos(fonte))


def test_constante_com_tipo_nao_declarado() -> None:
    fonte = "programa P; const c: nada = 1; begin end."
    assert any("tipo 'nada' não declarado" in m for m in erros_semanticos(fonte))


# --- Avisos -----------------------------------------------------------------


def test_variavel_nao_usada_gera_aviso() -> None:
    avisos = avisos_semanticos("programa P; var x: integer; begin end.")
    assert len(avisos) == 1
    assert "'x' declarada e não usada" in avisos[0]


def test_parametro_nao_usado_nao_gera_aviso() -> None:
    fonte = "programa P; procedure Q(a: integer); begin end; begin end."
    assert avisos_semanticos(fonte) == []


def test_id_isolado_continua_sendo_aviso_sintatico() -> None:
    # O enunciado exige aceitar `x;` com aviso de instrução sem efeito;
    # o aviso sai do parser e não vira erro semântico de declaração.
    resultado = analisar("programa P; var x: integer; begin x; end.")
    assert resultado.semantic_errors == ()
    assert any("sem efeito" in w.message for w in resultado.warnings)


def test_id_isolado_nao_declarado_nao_vira_erro() -> None:
    resultado = analisar("programa P; begin xyz; end.")
    assert resultado.semantic_errors == ()
    assert any("sem efeito" in w.message for w in resultado.warnings)


# --- Integração com as fases ------------------------------------------------


def test_erros_semanticos_so_entram_sem_erro_sintatico() -> None:
    resultado = analisar("programa P; begin x := ; end.")
    assert resultado.errors
    assert resultado.semantic_errors == ()


def test_fases_separadas_no_resultado() -> None:
    resultado = analisar("programa P; var x: integer; begin x := 'a'; end.")
    assert resultado.errors == ()
    assert len(resultado.semantic_errors) == 1
    assert len(resultado.all_errors) == 1
    assert resultado.has_any_errors


def test_programa_limpo_nao_tem_campos_semanticos() -> None:
    resultado = analisar("programa P; var x: integer; begin x := 1; end.")
    assert resultado.semantic_errors == ()
    assert resultado.semantic_warnings == ()
    assert resultado.all_errors == ()
    assert not resultado.has_any_errors


def test_parser_sem_semantico_continua_funcionando() -> None:
    # O parser direto, sem o módulo semântico, segue aceitando o mesmo código.
    tokens = analisar("programa P; begin x := 1 + 2; end.").tokens
    resultado = Parser(tokens).analisar()
    assert resultado.ok


def test_tabela_final_expoe_as_declaracoes() -> None:
    semantico = AnaliseSemantica()
    tokens = analisar(
        "programa P; var contador: integer; procedure Q; begin end; begin end."
    ).tokens
    Parser(tokens, None, semantico).analisar()
    nomes = {entrada.nome for entrada in semantico.resultado().tabela}
    assert {"writeln", "readln", "contador", "Q"} <= nomes


# --- Arquivos de caso de teste ----------------------------------------------


def _ler(nome: str) -> str:
    return (CASOS / nome).read_text(encoding="utf-8")


def test_caso_valido_nao_tem_nenhum_diagnostico() -> None:
    resultado = analisar(_ler("valido.pas"))
    assert resultado.all_errors == (), [e.message for e in resultado.all_errors]
    assert resultado.all_warnings == (), [w.message for w in resultado.all_warnings]


def test_programa_de_extensoes_e_semanticamente_valido() -> None:
    # O programa oficial da parte 2 (for, record, enum) não pode ter nenhum
    # diagnóstico nem das fases antigas nem da semântica.
    sem_diagnosticos(PROGRAMA_EXTENSOES)


def test_caso_de_erro_sintatico_e_recuperado() -> None:
    resultado = analisar(_ler("erro_sintatico.pas"))
    mensagens = [e.message for e in resultado.errors]
    assert len(mensagens) == 2, mensagens
    assert any("'then'" in m for m in mensagens)
    assert any("'do'" in m for m in mensagens)
    # sem erros semânticos: a fase semântica só roda sem erro sintático
    assert resultado.semantic_errors == ()


def test_caso_de_erros_semanticos() -> None:
    resultado = analisar(_ler("erros_semanticos.pas"))
    mensagens = [e.message for e in resultado.semantic_errors]
    assert len(mensagens) == 9, mensagens
    assert any("string a integer" in m for m in mensagens)
    assert any("real a integer" in m for m in mensagens)
    assert any("espera 2 argumento(s), encontrado 1" in m for m in mensagens)
    assert any("argumento 1 ('a')" in m for m in mensagens)
    assert any("'naoexiste' não declarado" in m for m in mensagens)
    assert any("constante" in m for m in mensagens)
    assert any("laço 'for' exige uma variável" in m for m in mensagens)
    avisos = [w.message for w in resultado.semantic_warnings + resultado.warnings]
    assert len([a for a in avisos if "sem efeito" in a]) == 2
