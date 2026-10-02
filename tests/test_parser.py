from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lexer import PROGRAMA_EXTENSOES, Lexer  # noqa: E402
from src.parser import Parser  # noqa: E402
from src.parser.service import AnaliseService  # noqa: E402

servico = AnaliseService()


def analisar(fonte: str):
    return servico.analyze(fonte)


def sem_erros(fonte: str) -> None:
    resultado = analisar(fonte)
    assert resultado.errors == (), [
        (e.line, e.column, e.lexeme, e.message) for e in resultado.errors
    ]


def mensagens_de_erro(fonte: str) -> list[str]:
    return [e.message for e in analisar(fonte).errors]


def mensagens_de_aviso(fonte: str) -> list[str]:
    return [w.message for w in analisar(fonte).warnings]


# --- Programas válidos -----------------------------------------------------


@pytest.mark.parametrize(
    "fonte",
    [
        "programa P; begin end.",
        "programa P;\nbegin\nend.",
        "PROGRAM P;\nBEGIN\nEND.",
        "programa P; begin x := 1; end.",
        "programa P; begin x := 1 + 2 * 3; end.",
        "programa P; begin x := (1 + 2) * (3 - 4); end.",
        "programa P; begin x := -1; end.",
        "programa P; begin x := 1 ou 2 e 3; end.",
        "programa P; begin if x > 1 then x := 2; end.",
        "programa P; begin if x > 1 then x := 2 else x := 3; end.",
        "programa P; begin if x > 1 then begin x := 2; end; end.",
        "programa P; begin while x < 10 do x := x + 1; end.",
        "programa P; begin repeat x := x - 1; until x = 0; end.",
        "programa P; begin break; end.",
        "programa P; begin continue; end.",
        "programa P; var x: integer; begin x := 1; end.",
        "programa P; var x, y: real; begin x := 1; end.",
        "programa P; const c: integer := 1; begin end.",
        "programa P; const c = 1; begin end.",
        "programa P; var a: integer; procedure Q; begin a := 1; end; begin Q; end.",
        "programa P; function Q: integer; begin end; begin end.",
        "programa P; procedure Q(a: integer; b: real); begin end; begin Q(1, 2.0); end.",
        "programa P; var x: integer; begin x[1] := 2; end.",
        "programa P; var x: integer; begin x[1 + 2] := x[3]; end.",
        "programa P; begin x := 'texto'; end.",
        "programa P; begin { comentario } x := 1; end.",
        "programa P; begin (* comentario *) x := 1; // fim\nend.",
    ],
)
def test_programas_validos(fonte: str) -> None:
    sem_erros(fonte)


# --- for -------------------------------------------------------------------


@pytest.mark.parametrize(
    "fonte",
    [
        "programa P; var i: integer; begin for i := 1 to 10 do i := i + 1; end.",
        "programa P; var i: integer; begin for i := 10 downto 1 do i := i - 1; end.",
        "programa P; var i: integer; begin FOR I := 1 TO 10 DO I := I + 1; end.",
        "programa P; var i: integer; begin for i := 1 to 2 * 3 do i := i + 1; end.",
        "programa P; var i: integer; begin for i := 1 to 10 do if i > 5 then break; end.",
        "programa P; var i: integer; begin for i := 1 to 10 do begin i := i + 1; end; end.",
        "programa P; var i: integer; begin for i := 1 to 10 do for i := 1 to 2 do i := 0; end.",
        "programa P; var i: integer; begin for i := 1 to 10 do while i < 3 do i := i + 1; end.",
        "programa P; var i: integer; begin for i := 1 to 10 do repeat i := i - 1; until i = 0; end.",
    ],
)
def test_for_valido(fonte: str) -> None:
    sem_erros(fonte)


def test_for_exige_to_ou_downto() -> None:
    assert any("'to'" in m for m in mensagens_de_erro("programa P; begin for i := 1 2 do i := 1; end."))


def test_for_exige_do() -> None:
    assert any("'do'" in m for m in mensagens_de_erro("programa P; begin for i := 1 to 10 i := 1; end."))


def test_for_exige_nome_de_variavel() -> None:
    assert mensagens_de_erro("programa P; begin for := 1 to 10 do i := 1; end.")


def test_for_exige_atribuicao_inicial() -> None:
    assert any("':='" in m for m in mensagens_de_erro("programa P; begin for i 1 to 10 do i := 1; end."))


def test_for_exige_corpo() -> None:
    assert mensagens_de_erro("programa P; begin for i := 1 to 10 do end.")


# --- Aviso de instrução sem efeito ----------------------------------------


def test_identificador_so_avisa_sem_efeito() -> None:
    avisos = mensagens_de_aviso("programa P; begin x; end.")
    assert len(avisos) == 1
    assert "sem efeito" in avisos[0]
    assert "'x'" in avisos[0]


def test_identificador_so_antes_do_end_avisa() -> None:
    avisos = mensagens_de_aviso("programa P; begin x end.")
    assert len(avisos) == 1
    assert "sem efeito" in avisos[0]


def test_instrucao_valida_nao_avisa() -> None:
    assert mensagens_de_aviso("programa P; begin x := 1; end.") == []


def test_chamada_de_procedimento_nao_avisa() -> None:
    assert mensagens_de_aviso("programa P; procedure Q; begin end; begin Q; end.") == []


def test_chamada_com_argumentos_nao_avisa() -> None:
    assert mensagens_de_aviso("programa P; procedure Q(a: integer); begin end; begin Q(1); end.") == []


def test_atribuicao_com_indice_nao_avisa() -> None:
    assert mensagens_de_aviso("programa P; var x: integer; begin x[1] := 2; end.") == []


def test_varios_identificadores_geram_varios_avisos() -> None:
    resultado = analisar("programa P; begin x; y; z end.")
    assert len(resultado.warnings) == 3


def test_aviso_aponta_a_posicao_do_identificador() -> None:
    resultado = analisar("programa P;\nbegin\n  x;\nend.")
    assert resultado.warnings[0].line == 3
    assert resultado.warnings[0].column == 3


# --- record e enum ---------------------------------------------------------


@pytest.mark.parametrize(
    "fonte",
    [
        "programa P; type c = (a, b); begin end.",
        "programa P; type c = enum (a, b); begin end.",
        "programa P; type c = (a, b, c, d); begin end.",
        "programa P; type d = (seg..sex); begin end.",
        "programa P; type t = integer; var x: t; begin end.",
        "programa P; type p = record x: integer; end; var v: p; begin end.",
        "programa P; type p = record x, y: real; z: string; end; begin end.",
        "programa P; type p = record inner: integer; end; begin end.",
        "programa P; type c = (a); t = integer; p = record x: integer; end; begin end.",
        "programa P; type\n c = (a, b);\nbegin\nend.",
    ],
)
def test_tipos_definidos_pelo_usuario(fonte: str) -> None:
    sem_erros(fonte)


def test_registro_exige_end() -> None:
    assert any("'end'" in m for m in mensagens_de_erro("programa P; type p = record x: integer; begin end."))


def test_campo_exige_tipo() -> None:
    assert any("':'" in m for m in mensagens_de_erro("programa P; type p = record x ; end; begin end."))


def test_campo_exige_ponto_e_virgula() -> None:
    assert any("';'" in m for m in mensagens_de_erro("programa P; type p = record x: integer end; begin end."))


def test_enumeracao_com_parenthese_desbalanceada_e_erro_lexico() -> None:
    # O lexer detecta o `(` sem fechamento antes de o parser ser chamado.
    resultado = analisar("programa P; type c = (a, b; begin end.")
    assert resultado.has_errors
    assert all("sintaxe" not in e.message for e in resultado.errors)


def test_enumeracao_exige_identificadores() -> None:
    assert mensagens_de_erro("programa P; type c = (); begin end.")


def test_declaracao_de_tipo_exige_igual() -> None:
    assert any("'='" in m for m in mensagens_de_erro("programa P; type c integer; begin end."))


def test_declaracao_de_tipo_exige_ponto_e_virgula() -> None:
    assert any("';'" in m for m in mensagens_de_erro("programa P; type c = integer begin end."))


@pytest.mark.parametrize(
    "fonte",
    [
        "programa P; type r = record x: integer; end; var v: r; begin v.x := 1; end.",
        "programa P; type r = record x: integer; end; var v: r; begin v.x := v.x + 1; end.",
        "programa P; type r = record x, y: real; end; var v: r; begin v.y := 1.0; end.",
        "programa P; type r = record x: integer; end; var v: r; begin if v.x > 0 then v.x := 0; end.",
        "programa P; type r = record x: integer; end; var v: r; begin v.x := 1; v.x := 2; end.",
    ],
)
def test_acesso_a_campo_de_registro(fonte: str) -> None:
    sem_erros(fonte)


def test_campo_requer_nome() -> None:
    assert any("campo" in m for m in mensagens_de_erro("programa P; begin v. := 1; end."))


# --- Exemplo oficial com as extensões --------------------------------------


def test_programa_de_extensoes_da_parte_2_e_valido() -> None:
    resultado = analisar(PROGRAMA_EXTENSOES)
    assert resultado.errors == (), [e.message for e in resultado.errors]
    assert resultado.warnings == ()
    assert len(resultado.tokens) > 80


def test_exemplo_de_extensoes_tem_todos_os_simbolos() -> None:
    tipos = {s.kind for s in analisar(PROGRAMA_EXTENSOES).symbols}
    assert {"tipo_enumeracao", "tipo_registro", "campo", "constante_enumeracao", "constante"} <= tipos


def test_exemplo_de_extensoes_usa_for() -> None:
    lexemas = [t.lexema.lower() for t in analisar(PROGRAMA_EXTENSOES).tokens]
    assert "for" in lexemas and "to" in lexemas and "downto" in lexemas


# --- Erros sintáticos ------------------------------------------------------


@pytest.mark.parametrize(
    "fonte",
    [
        "programa P; begin x := 1; end",
        "P begin end.",
        "programa P; var x: ; begin end.",
        "programa P; begin x := ; end.",
        "programa P; begin if x then end.",
        "programa P; begin while x do end.",
        "programa P; begin if x then y := 1 else end.",
        "programa P; begin x := 1 +; end.",
        "programa P; begin x := (1 + 2; end.",
        "programa P; var x integer; begin end.",
        "programa P; procedure Q begin end; begin end.",
        "programa P; begin x[1 := 1; end.",
        "programa P; begin x := 1 y := 2; end.",
        "programa P; begin ; end.",
        "",
    ],
)
def test_programas_invalidos(fonte: str) -> None:
    assert analisar(fonte).errors, fonte


def test_erro_sintatico_esta_marcado_como_sintaxe() -> None:
    assert all(
        e.message.startswith("sintaxe: ") for e in analisar("programa P; begin end").errors
    )


def test_erro_tem_linha_coluna_e_lexema() -> None:
    resultado = analisar("programa P;\nbegin\n  x := ;\nend.")
    erro = resultado.errors[0]
    assert erro.line == 3
    assert erro.column == 8
    assert erro.lexeme == ";"
    assert erro.length >= 1


def test_erro_aponta_para_o_fim_do_arquivo() -> None:
    resultado = analisar("programa P; begin end")
    erro = resultado.errors[-1]
    assert "fim do arquivo" in erro.message or "'.'" in erro.message


def test_arquivo_vazio_gera_um_unico_erro() -> None:
    assert len(analisar("").errors) == 1


# --- Recuperação -----------------------------------------------------------


def test_varios_erros_em_uma_passagem() -> None:
    resultado = analisar(
        "programa P;\n"
        "begin\n"
        "  x := ;\n"
        "  if then ;\n"
        "  y := 1\n"
        "end"
    )
    assert len(resultado.errors) >= 3


def test_recuperacao_continua_depois_do_erro() -> None:
    resultado = analisar("programa P; begin @@@ x := 1; end.")
    # o erro é léxico; o serviço não analisa sintaxe quando o léxico falha
    assert resultado.has_errors
    assert all("sintaxe" not in e.message for e in resultado.errors)


def test_sincronizacao_no_ponto_e_virgula() -> None:
    # o erro dentro da primeira instrução não impede as seguintes
    resultado = analisar("programa P; begin x := ; y := 2; z := 3; end.")
    assert len(resultado.errors) <= 3
    assert len(resultado.tokens) > 8


@pytest.mark.parametrize(
    "fonte",
    [
        "programa P; begin",
        "programa P; begin begin",
        "programa P; begin if",
        "programa P; begin if x then",
        "programa P; begin while",
        "programa P; begin repeat",
        "programa P; begin for",
        "programa P; begin for i :=",
        "programa P; begin for i := 1",
        "programa P; var",
        "programa P; type",
        "programa P; type p = record",
        "programa P; type p = record x",
        "programa P; type p = record x:",
        "programa P; type c = (",
        "programa P; procedure",
        "programa P; procedure Q",
        "programa P; procedure Q(",
        "programa P; function Q",
        "))))))))",
        "@@@@@@@@",
        ";;;;;;",
        "programa P; begin end. ((((((",
    ],
)
def test_entradas_incompletas_nao_travam(fonte: str) -> None:
    analisar(fonte)


# --- Derivações ------------------------------------------------------------


def test_derivacoes_sao_registradas() -> None:
    resultado = Parser(analisar("programa P; begin end.").tokens).analisar()
    assert "programa" in resultado.derivacoes
    assert "declaracoes" in resultado.derivacoes
    assert "instrucoes" in resultado.derivacoes


def test_derivacoes_incluem_instrucao_for() -> None:
    resultado = Parser(
        analisar("programa P; begin for i := 1 to 2 do i := 1; end.").tokens
    ).analisar()
    assert resultado.derivacoes.count("inst") >= 2


# --- Serviço ---------------------------------------------------------------


def test_servico_satisfaz_o_protocolo() -> None:
    from src.services.lexer_service import LexerService

    assert isinstance(servico, LexerService)


def test_servico_preserva_dados_do_lexer() -> None:
    resultado = analisar("programa P; begin x := 1; end.")
    assert resultado.tokens
    assert resultado.symbols
    assert resultado.token_classes
    assert resultado.dfa_states
    assert resultado.dfa_transitions


def test_servico_nao_analisa_sintaxe_quando_ha_erro_lexico() -> None:
    resultado = analisar("programa P; begin x := 1 @; end.")
    assert resultado.errors
    assert not any(e.message.startswith("sintaxe") for e in resultado.errors)


def test_servico_e_reutilizavel() -> None:
    primeiro = analisar("programa P; begin x; end.")
    segundo = analisar("programa P; begin x; end.")
    assert [w.message for w in primeiro.warnings] == [w.message for w in segundo.warnings]


def test_servico_aceita_lexer_injetado() -> None:
    outro = AnaliseService(Lexer())
    assert isinstance(outro.analyze("programa P; begin end."), type(primeiro_resultado()))


def primeiro_resultado():
    return analisar("programa P; begin end.")


def test_lexer_continua_disponivel_no_servico() -> None:
    assert servico.lexer is not None
    assert servico.lexer.analyze("programa P; begin end.").has_errors is False