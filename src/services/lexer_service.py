
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Token:

    tipo: str
    lexema: str
    linha: int
    coluna: int
    atributos: str = ""


@dataclass(frozen=True)
class LexicalError:

    line: int
    column: int
    message: str
    lexeme: str = ""
    length: int = 1


@dataclass(frozen=True)
class Warning:

    line: int
    column: int
    message: str


@dataclass(frozen=True)
class Symbol:

    identifier: str
    kind: str = ""
    type: str = ""
    value: str = ""
    line: int = 0


@dataclass(frozen=True)
class TokenClass:

    tipo: str
    regex: str
    description: str = ""


@dataclass(frozen=True)
class DfaTransition:

    state: str
    symbol: str
    target: str


@dataclass(frozen=True)
class DfaState:

    name: str
    is_accepting: bool = False
    token: str = ""


@dataclass(frozen=True)
class AnalysisResult:

    tokens: tuple[Token, ...] = ()
    errors: tuple[LexicalError, ...] = ()
    warnings: tuple[Warning, ...] = ()
    symbols: tuple[Symbol, ...] = ()
    token_classes: tuple[TokenClass, ...] = ()
    dfa_states: tuple[DfaState, ...] = ()
    dfa_transitions: tuple[DfaTransition, ...] = ()

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def token_count(self) -> int:
        return len(self.tokens)


EMPTY_RESULT = AnalysisResult()


@runtime_checkable
class LexerService(Protocol):

    def analyze(self, source: str) -> AnalysisResult:
        ...


class NullLexerService:

    def analyze(self, source: str) -> AnalysisResult:
        return AnalysisResult()
