"""Modelo de tipos e regras de compatibilidade da análise semântica.

Os tipos da linguagem são representados por *strings*: os primitivos usam o
próprio nome do token (`INTEGER`, `REAL`, `CHAR`, `STRING`) e os tipos
definidos pelo usuário usam o nome do identificador (`cor`, `ponto`). Duas
representações internas completam o conjunto:

- `LOGICO` — resultado dos comparadores e dos operadores `E`/`OU`. Não é
  declarável, como em Pascal, onde o booleano é uma classe de tipos.
- `DESCONHECIDO` (`""`) — propagado quando a inferência já falhou; os
  verificadores suprimem checagens envolvendo o desconhecido para não gerar
  erros em cascata depois do primeiro problema real.
"""

from __future__ import annotations

INTEIRO = "INTEGER"
REAL = "REAL"
CHAR = "CHAR"
TIPO_STRING = "STRING"

LOGICO = "LOGICO"
DESCONHECIDO = ""

TIPOS_NUMERICOS = frozenset({INTEIRO, REAL})

DESCRICAO: dict[str, str] = {
    INTEIRO: "integer",
    REAL: "real",
    CHAR: "char",
    TIPO_STRING: "string",
    LOGICO: "lógico",
}


def descrever(tipo: str) -> str:
    """Nome legível de um tipo, para as mensagens de erro."""
    if not tipo:
        return "desconhecido"
    return DESCRICAO.get(tipo, tipo)


def resolver_alias(tipo: str, base_de: dict[str, str]) -> str:
    """Segue a cadeia de apelidos (`type idade = integer`) até o tipo real.

    `base_de` mapeia o nome de um tipo definido pelo usuário para o nome do
    tipo-base declarado após o `=`. Cadeias cíclicas param na primeira
    repetição, devolvendo o próprio nome.
    """
    visto: set[str] = set()
    atual = tipo
    while atual in base_de and atual not in visto:
        visto.add(atual)
        atual = base_de[atual]
    return atual


def compativel_atribuicao(destino: str, origem: str) -> bool:
    """Pode o valor de tipo `origem` ser atribuído a algo de tipo `destino`?

    A única promoção permitida é `integer` para `real` (regra de Pascal).
    O desconhecido é aceito para suprimir erros em cascata.
    """
    if not destino or not origem:
        return True
    if destino == origem:
        return True
    if destino == REAL and origem == INTEIRO:
        return True
    # O lexer tipa todo literal como `string`, então um `char` só pode
    # receber valor por essa via; a troca nos dois sentidos é a
    # leniência documentada do dialeto.
    return {destino, origem} == {CHAR, TIPO_STRING}


def resultado_aritmetico(esquerda: str, direita: str) -> str:
    """Tipo do resultado de `esquerda operador direita` aritmético.

    Devolve `""` quando um dos lados é desconhecido ou os operandos não são
    numéricos; o chamador decide se isso vira erro.
    """
    if not esquerda or not direita:
        return DESCONHECIDO
    if esquerda in TIPOS_NUMERICOS and direita in TIPOS_NUMERICOS:
        if REAL in (esquerda, direita):
            return REAL
        return INTEIRO
    return DESCONHECIDO


def comparaveis(esquerda: str, direita: str) -> bool:
    """Os dois tipos podem ser comparados por `=`, `<`, `>`, `E`, `OU`?"""
    if not esquerda or not direita:
        return True
    if esquerda in TIPOS_NUMERICOS and direita in TIPOS_NUMERICOS:
        return True
    if esquerda == direita:
        return True
    return {esquerda, direita} == {CHAR, TIPO_STRING}


__all__ = [
    "CHAR",
    "DESCONHECIDO",
    "DESCRICAO",
    "INTEIRO",
    "LOGICO",
    "REAL",
    "TIPOS_NUMERICOS",
    "TIPO_STRING",
    "comparaveis",
    "compativel_atribuicao",
    "descrever",
    "resolver_alias",
    "resultado_aritmetico",
]
