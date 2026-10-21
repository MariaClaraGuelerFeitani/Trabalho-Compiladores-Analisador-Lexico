"""Geração de executável: traduz Guaxinim Pascal para C e liga com o TCC.

Fluxo completo, acionado pelo menu "Executar -> Gerar executável (F9)":

1. a análise léxica, sintática e semântica roda normalmente e precisa
   terminar sem erros;
2. `traduzir` consome os tokens e devolve uma fonte C autossuficiente;
3. `compilar` chama o `tcc.exe` embutido em `tools/tcc` e grava o `.exe`
   ao lado do `.pas`;
4. `executar` abre o binário em um console novo do Windows.
"""

from __future__ import annotations

from .compilador import TCC_AUSENCIA, compilar, executar, tcc_disponivel
from .tradutor import ErroDeTraducao, Tradutor, literal_para_c, mangle, traduzir

__all__ = [
    "TCC_AUSENCIA",
    "ErroDeTraducao",
    "Tradutor",
    "compilar",
    "executar",
    "literal_para_c",
    "mangle",
    "tcc_disponivel",
    "traduzir",
]
