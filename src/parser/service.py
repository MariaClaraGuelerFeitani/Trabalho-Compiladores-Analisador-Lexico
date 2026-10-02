"""Serviço de análise da linguagem: léxico seguido de sintático.

`AnaliseService` satisfaz o protocolo `LexerService` e entrega um único
`AnalysisResult` ao IDE. Os erros e avisos do analisador sintático são anexados
aos do analisador léxico, de modo que a interface continue exibindo-os nas
mesmas abas, com o mesmo sublinhado vermelho.
"""

from __future__ import annotations

from ..lexer import Lexer
from ..services.lexer_service import AnalysisResult, LexerService
from .parser import Parser


class AnaliseService:
    """Encadeia analisador léxico e analisador sintático."""

    def __init__(self, lexer: LexerService | None = None) -> None:
        self._lexer: LexerService = lexer if lexer is not None else Lexer()

    @property
    def lexer(self) -> LexerService:
        return self._lexer

    def analyze(self, source: str) -> AnalysisResult:
        resultado = self._lexer.analyze(source)
        if resultado.has_errors:
            return resultado
        sintatico = Parser(resultado.tokens, resultado.symbols).analisar()
        if not sintatico.erros and not sintatico.avisos:
            return resultado
        return AnalysisResult(
            tokens=resultado.tokens,
            errors=resultado.errors + sintatico.erros,
            warnings=resultado.warnings + sintatico.avisos,
            symbols=resultado.symbols,
            token_classes=resultado.token_classes,
            dfa_states=resultado.dfa_states,
            dfa_transitions=resultado.dfa_transitions,
        )


__all__ = ["AnaliseService"]