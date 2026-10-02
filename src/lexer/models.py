from __future__ import annotations

from ..services.lexer_service import (
    AnalysisResult,
    DfaState,
    DfaTransition,
    LexicalError,
    Symbol,
    Token,
    TokenClass,
    Warning,
)

__all__ = [
    "AnalysisResult",
    "DfaState",
    "DfaTransition",
    "LexicalError",
    "Symbol",
    "SymbolTable",
    "Token",
    "TokenClass",
    "Warning",
]


class SymbolTable:
    """Tabela de símbolos do programa, na ordem da primeira declaração."""

    def __init__(self) -> None:
        self._entradas: dict[str, Symbol] = {}

    def __len__(self) -> int:
        return len(self._entradas)

    def __contains__(self, identificador: object) -> bool:
        return identificador in self._entradas

    def buscar(self, identificador: str) -> Symbol | None:
        return self._entradas.get(identificador)

    def declarar(
        self,
        identificador: str,
        classe: str,
        tipo: str = "",
        valor: str = "",
        linha: int = 0,
    ) -> Symbol | None:
        """Registra uma declaração e devolve a anterior, se já existia."""
        anterior = self._entradas.get(identificador)
        if anterior is not None:
            return anterior
        self._entradas[identificador] = Symbol(identificador, classe, tipo, valor, linha)
        return None

    def como_tupla(self) -> tuple[Symbol, ...]:
        return tuple(self._entradas.values())