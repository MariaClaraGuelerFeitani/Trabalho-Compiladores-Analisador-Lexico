"""Gramática da linguagem, em forma de dados.

O texto do Anexo I é transcrito literalmente em `ANEXO_I`, e as extensões da
parte 2 do trabalho (`for`, tipos `record` e enumeração) ficam em `EXTENSOES`.
`GRAMATICA` é a união das duas e é o que o IDE exibe na aba *Gramática*.

Cada produção é um `Producao` com um não terminal e suas alternativas, escritas
na notação do enunciado. `VAZIA` (`ε`) marca a alternativa vazia, e `LPAREN`
(`(`) marca o início do lado direito para não confundir parênteses de agrupamento
com o token `ABRE_PARENTESES`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VAZIA = "ε"
LPAREN = "("
RPAREN = ")"


@dataclass(frozen=True)
class Producao:
    """Uma regra `nome → alternativa | alternativa | ...`."""

    nome: str
    alternativas: tuple[str, ...]

    def texto(self) -> str:
        return f"{self.nome} → {' | '.join(self.alternativas)}"


ANEXO_I: tuple[Producao, ...] = (
    Producao("programa", ("PROGRAM ID ; declaracoes BEGIN instrucoes END .",)),
    Producao("bloco", ("BEGIN instrucoes END ;",)),
    Producao(
        "declaracoes",
        ("declaracaoVariavel declaracaoConstante declProcedimento",),
    ),
    Producao("declaracaoConstante", ("CONST declConsList", VAZIA)),
    Producao(
        "declConsList",
        (
            "ID : tipo = valor ; declConsList",
            "ID = valor ; declConsList",
            VAZIA,
        ),
    ),
    Producao("declaracaoVariavel", ("VAR declVarList", VAZIA)),
    Producao("declVarList", ("declVar declVarList", VAZIA)),
    Producao("declVar", ("variavel conjuntoIds : tipo ;",)),
    Producao("conjuntoIds", (", variavel conjuntoIds", VAZIA)),
    Producao("tipo", ("INTEGER", "REAL", "CHAR", "STRING")),
    Producao("valor", ("unario", "LITERAL")),
    Producao("declProcedimento", ("declProc declProcedimento", VAZIA)),
    Producao(
        "declProc",
        (
            "PROCEDURE ID ( parametros ) ; declaracaoVariavel bloco",
            "FUNCTION ID ( parametros ) : tipo ; declaracaoVariavel bloco",
            "PROCEDURE ID ; declaracaoVariavel bloco",
            "FUNCTION ID : tipo ; declaracaoVariavel bloco",
        ),
    ),
    Producao("parametros", ("declVarList", VAZIA)),
    Producao("instrucoes", ("inst instrucoes", VAZIA)),
    Producao(
        "inst",
        (
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
        ),
    ),
    Producao("parametros2", ("expr parametros2", ", expr parametros2", VAZIA)),
    Producao("expr", ("exprComparacao expr2",)),
    Producao(
        "expr2",
        ("OU exprComparacao expr2", "E exprComparacao expr2", VAZIA),
    ),
    Producao("exprComparacao", ("exprOp exprComparacao2",)),
    Producao(
        "exprComparacao2",
        (
            "= exprOp exprComparacao2",
            "<> exprOp exprComparacao2",
            "< exprOp exprComparacao2",
            "<= exprOp exprComparacao2",
            "> exprOp exprComparacao2",
            ">= exprOp exprComparacao2",
            VAZIA,
        ),
    ),
    Producao("exprOp", ("termo exprOp2",)),
    Producao("exprOp2", ("+ termo exprOp2", "- termo exprOp2", VAZIA)),
    Producao("termo", ("unario termo2",)),
    Producao("termo2", ("* unario termo2", "/ unario termo2", VAZIA)),
    Producao("unario", ("+ fator", "- fator", "fator")),
    Producao(
        "fator",
        (f"{LPAREN} expr {RPAREN}", "variavel ( parametros2 )", "variavel", "NUM", "LITERAL"),
    ),
    Producao("variavel", ("ID", "ID [ exprOp ]", "ID . ID")),
    Producao("NUM", ("digitos", "digitos . digitos")),
)

# Produções que definem o reconhecimento das classes de lexemas. Elas usam notação
# de expressões regulares, não terminais da linguagem, e por isso ficam fora da
# extração de terminais e da verificação contra os tokens do lexer.
DEFINICOES_DE_LEXEMA: tuple[Producao, ...] = (
    Producao("digitos", ("dig digitos*",)),
    Producao("dig", ("[0-9]",)),
    Producao("ID", ("[A-Za-z] [ letra | dig | _ ]*",)),
    Producao("LITERAL", ("' [ letra | dig | CARACTER_ESPECIAL ]* '",)),
)

# Símbolos auxiliares citados pelas definições de lexema.
SIMBOLOS_META: frozenset[str] = frozenset(
    {"digitos", "dig", "letra", "CARACTER_ESPECIAL", "A", "Z"}
)

EXTENSOES: tuple[Producao, ...] = (
    Producao(
        "declaracoes",
        (
            "declaracaoVariavel declaracaoConstante declaracaoTipo declProcedimento",
        ),
    ),
    Producao("declaracaoTipo", ("TYPE declTipoList", VAZIA)),
    Producao("declTipoList", ("declTipo declTipoList", VAZIA)),
    Producao(
        "declTipo",
        ("ID = tipoSimples ;", "ID = listaEnum ;", "ID = ENUM listaEnum ;", "ID = RECORD campos END ;"),
    ),
    Producao("tipoSimples", ("INTEGER", "REAL", "CHAR", "STRING", "ID")),
    Producao("listaEnum", ("ID", "ID .. NUM , listaEnum", "ID .. ID , listaEnum")),
    Producao("campos", ("campo campos", VAZIA)),
    Producao("campo", ("conjuntoIds : tipoSimples ;",)),
    Producao(
        "inst",
        (
            "FOR ID := expr TO expr DO inst",
            "FOR ID := expr DOWNTO expr DO inst",
        ),
    ),
)

# Produções sobrescritas por `EXTENSOES` recebem as alternativas extras em vez de
# perder as originais.
SOBRESCRITAS = {"declaracoes", "inst"}


def _mesclar(base: tuple[Producao, ...], extras: tuple[Producao, ...]) -> tuple[Producao, ...]:
    por_nome: dict[str, Producao] = {p.nome: p for p in base}
    for extra in extras:
        if extra.nome in por_nome and extra.nome in SOBRESCRITAS:
            anterior = por_nome[extra.nome]
            novas = tuple(a for a in anterior.alternativas if a not in extra.alternativas)
            por_nome[extra.nome] = Producao(extra.nome, novas + extra.alternativas)
        else:
            por_nome[extra.nome] = extra
    return tuple(por_nome.values())


LEXICO_GRAMATICA = DEFINICOES_DE_LEXEMA
GRAMATICA: tuple[Producao, ...] = _mesclar(ANEXO_I + DEFINICOES_DE_LEXEMA, EXTENSOES)

NOMES = frozenset(p.nome for p in GRAMATICA)
NOMES_DE_DEFINICAO = frozenset(p.nome for p in DEFINICOES_DE_LEXEMA)

_SIMBOLO = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


def _simbolos(producao: Producao) -> set[str]:
    return set(_SIMBOLO.findall(producao.nome + " " + " ".join(producao.alternativas)))


def terminais(gramatica: tuple[Producao, ...] = GRAMATICA) -> frozenset[str]:
    """Terminais nomeados: símbolos citados à direita que não são não terminais.

    Terminais de pontuação (`:=`, `;`, `.`) não entram no resultado porque não são
    identificadores; eles aparecem literais em `Producao.alternativas`.
    """
    nao_terminais = {p.nome for p in gramatica}
    achados: set[str] = set()
    for producao in gramatica:
        if producao.nome in NOMES_DE_DEFINICAO:
            continue
        achados |= _simbolos(producao) - nao_terminais
    return frozenset(achados - SIMBOLOS_META)


def indefinidos(conhecidos: frozenset[str], gramatica: tuple[Producao, ...] = GRAMATICA) -> frozenset[str]:
    """Terminais da gramática que não existem no conjunto `conhecidos` de tokens."""
    return terminais(gramatica) - conhecidos


def nao_terminal_de(gramatica: tuple[Producao, ...], simbolo: str) -> tuple[str, ...]:
    return tuple(p for p in gramatica if p.nome == simbolo)


def linhas_da_gramatica(gramatica: tuple[Producao, ...] = GRAMATICA) -> tuple[str, ...]:
    """Uma linha por produção, para exibição no IDE."""
    return tuple(p.texto() for p in gramatica)


__all__ = [
    "ANEXO_I",
    "EXTENSOES",
    "GRAMATICA",
    "LPAREN",
    "NOMES",
    "Producao",
    "RPAREN",
    "VAZIA",
    "linhas_da_gramatica",
    "nao_terminal_de",
    "terminais",
]