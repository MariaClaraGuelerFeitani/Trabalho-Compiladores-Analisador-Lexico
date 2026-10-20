"""Análise semântica da etapa 2 do compilador.

O pacote expõe `AnaliseSemantica`, invocada pelos ganchos do analisador
sintático, e a `TabelaDeSimbolos` com escopos encadeados que sustenta a
verificação de declarações e de tipos.
"""

from __future__ import annotations

from .semantico import AnaliseSemantica, InfoAcesso, ResultadoSemantico
from .tabela import Entrada, Escopo, TabelaDeSimbolos
from .tipos import (
    CHAR,
    DESCONHECIDO,
    INTEIRO,
    LOGICO,
    REAL,
    TIPO_STRING,
    comparaveis,
    compativel_atribuicao,
    descrever,
    resultado_aritmetico,
)

__all__ = [
    "CHAR",
    "DESCONHECIDO",
    "INTEIRO",
    "LOGICO",
    "REAL",
    "TIPO_STRING",
    "AnaliseSemantica",
    "Entrada",
    "Escopo",
    "InfoAcesso",
    "ResultadoSemantico",
    "TabelaDeSimbolos",
    "comparaveis",
    "compativel_atribuicao",
    "descrever",
    "resultado_aritmetico",
]
