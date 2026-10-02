from __future__ import annotations

import re

from ..config import MAX_IDENTIFIER_LENGTH
from ..services.lexer_service import TokenClass

ID = "ID"
NUM = "NUM"
LITERAL = "LITERAL"

PROGRAM = "PROGRAM"
BEGIN = "BEGIN"
END = "END"
CONST = "CONST"
VAR = "VAR"
INTEGER = "INTEGER"
REAL = "REAL"
CHAR = "CHAR"
STRING = "STRING"
PROCEDURE = "PROCEDURE"
FUNCTION = "FUNCTION"
IF = "IF"
ELSE = "ELSE"
THEN = "THEN"
WHILE = "WHILE"
DO = "DO"
REPEAT = "REPEAT"
UNTIL = "UNTIL"
BREAK = "BREAK"
CONTINUE = "CONTINUE"
OU = "OU"
E = "E"
FOR = "FOR"
TO = "TO"
DOWNTO = "DOWNTO"
TYPE = "TYPE"
RECORD = "RECORD"
ENUM = "ENUM"

PONTO_E_VIRGULA = "PONTO_E_VIRGULA"
PONTO = "PONTO"
VIRGULA = "VIRGULA"
DOIS_PONTOS = "DOIS_PONTOS"
INTERVALO = "INTERVALO"
IGUALDADE_COMPARACAO = "IGUALDADE_COMPARACAO"
ATRIBUICAO = "ATRIBUICAO"
DIFERENTE_DE = "DIFERENTE_DE"
MENOR_QUE = "MENOR_QUE"
MAIOR_QUE = "MAIOR_QUE"
MENOR_OU_IGUAL_QUE = "MENOR_OU_IGUAL_QUE"
MAIOR_OU_IGUAL_QUE = "MAIOR_OU_IGUAL_QUE"
ADICAO = "ADICAO"
SUBTRACAO = "SUBTRACAO"
MULTIPLICACAO = "MULTIPLICACAO"
DIVISAO = "DIVISAO"
ABRE_PARENTESES = "ABRE_PARENTESES"
FECHA_PARENTESES = "FECHA_PARENTESES"
ABRE_COLCHETES = "ABRE_COLCHETES"
FECHA_COLCHETES = "FECHA_COLCHETES"

PALAVRAS_RESERVADAS: dict[str, str] = {
    "program": PROGRAM,
    "programa": PROGRAM,
    "begin": BEGIN,
    "end": END,
    "const": CONST,
    "var": VAR,
    "integer": INTEGER,
    "real": REAL,
    "char": CHAR,
    "string": STRING,
    "procedure": PROCEDURE,
    "function": FUNCTION,
    "if": IF,
    "else": ELSE,
    "then": THEN,
    "while": WHILE,
    "do": DO,
    "repeat": REPEAT,
    "until": UNTIL,
    "break": BREAK,
    "continue": CONTINUE,
    "ou": OU,
    "e": E,
    "for": FOR,
    "to": TO,
    "downto": DOWNTO,
    "type": TYPE,
    "record": RECORD,
    "enum": ENUM,
}

SIMBOLOS: tuple[tuple[str, str], ...] = (
    (":=", ATRIBUICAO),
    ("<=", MENOR_OU_IGUAL_QUE),
    (">=", MAIOR_OU_IGUAL_QUE),
    ("<>", DIFERENTE_DE),
    ("..", INTERVALO),
    (";", PONTO_E_VIRGULA),
    (".", PONTO),
    (",", VIRGULA),
    (":", DOIS_PONTOS),
    ("=", IGUALDADE_COMPARACAO),
    ("<", MENOR_QUE),
    (">", MAIOR_QUE),
    ("+", ADICAO),
    ("-", SUBTRACAO),
    ("*", MULTIPLICACAO),
    ("/", DIVISAO),
    ("(", ABRE_PARENTESES),
    (")", FECHA_PARENTESES),
    ("[", ABRE_COLCHETES),
    ("]", FECHA_COLCHETES),
)

SIMBOLOS_POR_ROTULO: dict[str, str] = dict(SIMBOLOS)

TIPOS_PRIMARIOS: frozenset[str] = frozenset({INTEGER, REAL, CHAR, STRING})

DIGITOS = "0123456789"
IGNORADOS = " \t\r\n\v\f"
UNDERSCORE = "_"
APOSTROFO = "'"
PONTO_DECIMAL = "."
MARCA_COMENTARIO_LINHA = "//"
ABRE_COMENTARIO_BLOCO = "{"
FECHA_COMENTARIO_BLOCO = "}"
ABRE_COMENTARIO_PARENTESE = "(*"
FECHA_COMENTARIO_PARENTESE = "*)"

REGEX_IDENTIFICADOR = f"[A-Za-z][A-Za-z0-9_]{{0,{MAX_IDENTIFIER_LENGTH - 1}}}"
REGEX_NUMERO = "[0-9]+(\\.[0-9]+)?"
REGEX_LITERAL = "'(letra|digito|especial)*'"
REGEX_DIGITOS = "[0-9]+"
REGEX_DIGITO = "[0-9]"

DESCRICAO_PALAVRA_RESERVADA = "palavra reservada, não diferencia maiúsculas de minúsculas"
DESCRICAO_SIMBOLO = "símbolo da linguagem"
DESCRICAO_POR_TOKEN: dict[str, str] = {
    INTEGER: "tipo primário inteiro",
    REAL: "tipo primário real",
    CHAR: "tipo primário caractere",
    STRING: "tipo primário cadeia de caracteres",
}


def eh_digito(caractere: str) -> bool:
    return caractere in DIGITOS


def eh_letra(caractere: str) -> bool:
    return "a" <= caractere <= "z" or "A" <= caractere <= "Z"


def eh_identificador(caractere: str) -> bool:
    return eh_letra(caractere) or eh_digito(caractere) or caractere == UNDERSCORE


def normalizar(lexema: str) -> str:
    return lexema.lower()


def tamanho_maximo_identificador() -> int:
    return MAX_IDENTIFIER_LENGTH


def token_classes() -> tuple[TokenClass, ...]:
    classes = [
        TokenClass(
            ID,
            REGEX_IDENTIFICADOR,
            f"identificador, inicia por letra e aceita no máximo {MAX_IDENTIFIER_LENGTH} caracteres",
        ),
        TokenClass(NUM, REGEX_NUMERO, "constante numérica inteira ou real"),
        TokenClass(LITERAL, REGEX_LITERAL, "constante textual delimitada por apóstrofos"),
    ]
    classes.extend(
        TokenClass(tipo, f"(?i){palavra}", DESCRICAO_POR_TOKEN.get(tipo, DESCRICAO_PALAVRA_RESERVADA))
        for palavra, tipo in PALAVRAS_RESERVADAS.items()
    )
    classes.extend(
        TokenClass(tipo, re.escape(lexema), DESCRICAO_SIMBOLO) for lexema, tipo in SIMBOLOS
    )
    return tuple(classes)


TOKEN_CLASSES: tuple[TokenClass, ...] = token_classes()