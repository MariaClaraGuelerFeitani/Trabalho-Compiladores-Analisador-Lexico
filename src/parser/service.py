"""Serviço de análise da linguagem: léxico, sintático e semântico.

`AnaliseService` satisfaz o protocolo `LexerService` e entrega um único
`AnalysisResult` ao IDE. A ordem das fases é a clássica de um compilador:

1. léxico — se falhar, a análise para (não há tokens confiáveis);
2. sintático — roda com os ganchos do `AnaliseSemantica` ligados;
3. semântico — seus erros e avisos só entram no resultado quando não houve
   erro sintático, evitando erros em cascata sobre árvores incompletas.

Erros e avisos das três fases reaproveitam `LexicalError` e `Warning`, de
modo que o IDE os exibe nas mesmas abas, com o mesmo sublinhado vermelho.
Os campos `semantic_errors` / `semantic_warnings` do resultado separam as
fases; `AnalysisResult.all_errors` e `.all_warnings` trazem a união para
exibição.
"""

from __future__ import annotations

from ..lexer import Lexer
from ..semantic import AnaliseSemantica
from ..services.lexer_service import AnalysisResult, LexerService
from .parser import Parser


class AnaliseService:
    """Encadeia analisador léxico, sintático e semântico."""

    def __init__(self, lexer: LexerService | None = None) -> None:
        self._lexer: LexerService = lexer if lexer is not None else Lexer()

    @property
    def lexer(self) -> LexerService:
        return self._lexer

    def analyze(self, source: str) -> AnalysisResult:
        resultado = self._lexer.analyze(source)
        if resultado.has_errors:
            return resultado
        semantico = AnaliseSemantica()
        sintatico = Parser(resultado.tokens, resultado.symbols, semantico).analisar()
        erros_semanticos = ()
        avisos_semanticos = ()
        if not sintatico.erros:
            consolidado = semantico.resultado()
            erros_semanticos = consolidado.erros
            avisos_semanticos = consolidado.avisos
        if (
            not sintatico.erros
            and not sintatico.avisos
            and not erros_semanticos
            and not avisos_semanticos
        ):
            return resultado
        return AnalysisResult(
            tokens=resultado.tokens,
            errors=resultado.errors + sintatico.erros,
            warnings=resultado.warnings + sintatico.avisos,
            symbols=resultado.symbols,
            token_classes=resultado.token_classes,
            dfa_states=resultado.dfa_states,
            dfa_transitions=resultado.dfa_transitions,
            semantic_errors=erros_semanticos,
            semantic_warnings=avisos_semanticos,
        )


__all__ = ["AnaliseService"]
