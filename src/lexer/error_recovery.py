from __future__ import annotations

from ..services.lexer_service import LexicalError, Token
from .tokens import BEGIN, CONST, END, PONTO_E_VIRGULA, PROCEDURE, VAR

PONTOS_DE_SINCRONIZACAO: frozenset[str] = frozenset(
    {BEGIN, END, VAR, CONST, PROCEDURE, PONTO_E_VIRGULA}
)

CARACTERES_DE_SINCRONIZACAO: frozenset[str] = frozenset({";", "\n"})

SIMBOLOS_INVALIDOS: frozenset[str] = frozenset("@#$!?`~^&|\\\"'")

FECHADORES: dict[str, tuple[str, str]] = {
    ")": ("(", "parêntese"),
    "]": ("[", "colchete"),
    "}": ("{", "chave"),
}


def criar_erro(
    linha: int,
    coluna: int,
    mensagem: str,
    lexema: str = "",
    comprimento: int = 1,
) -> LexicalError:
    return LexicalError(
        line=linha,
        column=coluna,
        message=mensagem,
        lexeme=lexema,
        length=max(1, comprimento),
    )


def criar_erro_de_caractere(
    linha: int, coluna: int, caractere: str, comentario: str = ""
) -> LexicalError:
    return criar_erro(
        linha,
        coluna,
        f"caractere inválido {caractere!r}{comentario}",
        caractere,
        1,
    )


def sincronizar_fonte(fonte: str, posicao: int, linha: int, coluna: int) -> tuple[int, int, int]:
    """Avança até o próximo ponto de sincronização ou o fim da fonte."""
    while posicao < len(fonte) and fonte[posicao] not in CARACTERES_DE_SINCRONIZACAO:
        posicao += 1
        coluna += 1
    return posicao, linha, coluna


def indice_de_sincronizacao(tokens: tuple[Token, ...], indice: int) -> int:
    """Devolve o índice do próximo token de sincronização, ou o fim da lista."""
    while indice < len(tokens) and tokens[indice].tipo not in PONTOS_DE_SINCRONIZACAO:
        indice += 1
    return indice


def mensagem_de_fechamento(fechador: str) -> str:
    _, nome = FECHADORES[fechador]
    return f"'{fechador}' sem '{FECHADORES[fechador][0]}' correspondente"


def nomes_dos_fechadores() -> tuple[str, ...]:
    return tuple(FECHADORES)