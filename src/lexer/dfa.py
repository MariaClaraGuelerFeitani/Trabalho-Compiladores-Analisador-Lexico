from __future__ import annotations

from ..services.lexer_service import DfaState, DfaTransition
from .tokens import (
    APOSTROFO,
    ATRIBUICAO,
    DIFERENTE_DE,
    ID,
    INTERVALO,
    LITERAL,
    MAIOR_OU_IGUAL_QUE,
    MAIOR_QUE,
    MENOR_OU_IGUAL_QUE,
    MENOR_QUE,
    NUM,
    PALAVRAS_RESERVADAS,
    PONTO_DECIMAL,
    SIMBOLOS,
    UNDERSCORE,
    eh_digito,
    eh_identificador,
    eh_letra,
)

ESTADO_INICIAL = "q0"
ESTADO_IDENTIFICADOR = "q_id"

ESTADO_NUMERO_INTEIRO = "q_num_inteiro"
ESTADO_NUMERO_DECIMAL = "q_num_decimal"
ESTADO_NUMERO_FRACAO = "q_num_fracao"

ESTADO_LITERAL_DENTRO = "q_lit_dentro"
ESTADO_LITERAL_FIM = "q_lit_fim"
ESTADOS_LITERAL: frozenset[str] = frozenset({ESTADO_LITERAL_DENTRO, ESTADO_LITERAL_FIM})

ESTADO_DOIS_PONTOS = "q_dois_pontos"
ESTADO_ATRIBUICAO = "q_atribuicao"
ESTADO_MENOR = "q_menor"
ESTADO_MENOR_OU_IGUAL = "q_menor_ou_igual"
ESTADO_DIFERENTE = "q_diferente"
ESTADO_MAIOR = "q_maior"
ESTADO_MAIOR_OU_IGUAL = "q_maior_ou_igual"
ESTADO_PONTO = "q_ponto"
ESTADO_INTERVALO = "q_intervalo"

PREFIXO_PALAVRA = "q_kw_"

DIGITO = "digito"
LETRA = "letra"
OUTRO_ID = "outra letra, digito ou _"
ESPECIAL = "caractere especial"
QUEBRA_DE_LINHA = "quebra de linha"

NOMES_SIMBOLOS_SIMPLES: dict[str, str] = {
    ";": "q_ponto_e_virgula",
    ".": ESTADO_PONTO,
    ",": "q_virgula",
    "=": "q_igualdade",
    "+": "q_adicao",
    "-": "q_subtracao",
    "*": "q_multiplicacao",
    "/": "q_divisao",
    "(": "q_abre_parenteses",
    ")": "q_fecha_parenteses",
    "[": "q_abre_colchetes",
    "]": "q_fecha_colchetes",
}

ESTRUTURAS_SIMBOLOS: dict[str, tuple[str, dict[str, tuple[str, str]]]] = {
    ":": (ESTADO_DOIS_PONTOS, {"=": (ESTADO_ATRIBUICAO, ATRIBUICAO)}),
    "<": (
        ESTADO_MENOR,
        {
            "=": (ESTADO_MENOR_OU_IGUAL, MENOR_OU_IGUAL_QUE),
            ">": (ESTADO_DIFERENTE, DIFERENTE_DE),
        },
    ),
    ">": (ESTADO_MAIOR, {"=": (ESTADO_MAIOR_OU_IGUAL, MAIOR_OU_IGUAL_QUE)}),
    ".": (ESTADO_PONTO, {".": (ESTADO_INTERVALO, INTERVALO)}),
}

PRIMEIRAS_LETRAS: frozenset[str] = frozenset(palavra[0] for palavra in PALAVRAS_RESERVADAS)


def nome_do_estado_de_palavra(prefixo: str) -> str:
    return f"{PREFIXO_PALAVRA}{prefixo}"


def _montar_arvore() -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    filhos: dict[str, dict[str, str]] = {}
    aceitos: dict[str, str] = {}
    for palavra, tipo in PALAVRAS_RESERVADAS.items():
        prefixo = ""
        for letra in palavra:
            ramos = filhos.setdefault(prefixo, {})
            prefixo = prefixo + letra
            ramos[letra] = prefixo
        filhos.setdefault(prefixo, {})
        aceitos[prefixo] = tipo
    return filhos, aceitos


class _Construtor:
    def __init__(self) -> None:
        self.estados: list[DfaState] = []
        self.transicoes: list[DfaTransition] = []
        self.criados: set[str] = set()
        self.aceitacao: dict[str, str] = {}

    def estado(self, nome: str, token: str = "") -> None:
        if nome in self.criados:
            return
        self.criados.add(nome)
        self.estados.append(DfaState(nome, bool(token), token))
        if token:
            self.aceitacao[nome] = token

    def ligar(self, origem: str, simbolo: str, destino: str) -> None:
        self.transicoes.append(DfaTransition(origem, simbolo, destino))

    def simbolo(self, estado: str, simbolo: str) -> None:
        self.ligar(ESTADO_INICIAL, simbolo, estado)


def _construir() -> _Construtor:
    construtor = _Construtor()
    construtor.estado(ESTADO_INICIAL)
    filhos, aceitos = _montar_arvore()

    construtor.estado(ESTADO_IDENTIFICADOR, ID)
    construtor.simbolo(ESTADO_IDENTIFICADOR, LETRA)
    construtor.ligar(ESTADO_IDENTIFICADOR, LETRA, ESTADO_IDENTIFICADOR)
    construtor.ligar(ESTADO_IDENTIFICADOR, DIGITO, ESTADO_IDENTIFICADOR)
    construtor.ligar(ESTADO_IDENTIFICADOR, UNDERSCORE, ESTADO_IDENTIFICADOR)

    construtor.estado(ESTADO_NUMERO_INTEIRO, NUM)
    construtor.simbolo(ESTADO_NUMERO_INTEIRO, DIGITO)
    construtor.ligar(ESTADO_NUMERO_INTEIRO, DIGITO, ESTADO_NUMERO_INTEIRO)
    construtor.estado(ESTADO_NUMERO_DECIMAL)
    construtor.ligar(ESTADO_NUMERO_INTEIRO, PONTO_DECIMAL, ESTADO_NUMERO_DECIMAL)
    construtor.estado(ESTADO_NUMERO_FRACAO, NUM)
    construtor.ligar(ESTADO_NUMERO_DECIMAL, DIGITO, ESTADO_NUMERO_FRACAO)
    construtor.ligar(ESTADO_NUMERO_FRACAO, DIGITO, ESTADO_NUMERO_FRACAO)

    construtor.estado(ESTADO_LITERAL_DENTRO)
    construtor.simbolo(ESTADO_LITERAL_DENTRO, APOSTROFO)
    construtor.ligar(ESTADO_LITERAL_DENTRO, ESPECIAL, ESTADO_LITERAL_DENTRO)
    construtor.estado(ESTADO_LITERAL_FIM, LITERAL)
    construtor.ligar(ESTADO_LITERAL_DENTRO, APOSTROFO, ESTADO_LITERAL_FIM)
    construtor.ligar(ESTADO_LITERAL_FIM, APOSTROFO, ESTADO_LITERAL_DENTRO)

    for lexema, token in SIMBOLOS:
        if len(lexema) > 1:
            continue
        estrutura = ESTRUTURAS_SIMBOLOS.get(lexema)
        if estrutura is not None:
            estado_inicial, derivadas = estrutura
            construtor.estado(estado_inicial, token)
            construtor.simbolo(estado_inicial, lexema)
            for sufixo, (destino, token_derivado) in derivadas.items():
                construtor.estado(destino, token_derivado)
                construtor.ligar(estado_inicial, sufixo, destino)
            continue
        construtor.estado(NOMES_SIMBOLOS_SIMPLES[lexema], token)
        construtor.simbolo(NOMES_SIMBOLOS_SIMPLES[lexema], lexema)

    for prefixo in filhos:
        if not prefixo:
            continue
        estado = nome_do_estado_de_palavra(prefixo)
        construtor.estado(estado, aceitos.get(prefixo, ""))
        if len(prefixo) == 1:
            construtor.simbolo(estado, prefixo)
        else:
            construtor.ligar(nome_do_estado_de_palavra(prefixo[:-1]), prefixo[-1], estado)
        construtor.ligar(estado, OUTRO_ID, ESTADO_IDENTIFICADOR)

    return construtor


_CONSTRUIDOR = _construir()

ESTADOS: tuple[DfaState, ...] = tuple(_CONSTRUIDOR.estados)
TRANSICOES: tuple[DfaTransition, ...] = tuple(_CONSTRUIDOR.transicoes)
ACEITACAO: dict[str, str] = dict(_CONSTRUIDOR.aceitacao)

INDICES: dict[str, int] = {estado.name: indice for indice, estado in enumerate(ESTADOS)}

ESTADOS_PALAVRA: frozenset[str] = frozenset(
    nome for nome in INDICES if nome.startswith(PREFIXO_PALAVRA)
)

TABELA: dict[tuple[str, str], str] = {
    (transicao.state, transicao.symbol): transicao.target for transicao in TRANSICOES
}

TRANSICOES_POR_ESTADO: dict[str, tuple[DfaTransition, ...]] = {
    nome: tuple(transicao for transicao in TRANSICOES if transicao.state == nome)
    for nome in INDICES
}


def delta(estado: str, simbolo: str) -> str | None:
    return TABELA.get((estado, simbolo))


def simbolos_de(estado: str) -> tuple[str, ...]:
    return tuple(sorted({transicao.symbol for transicao in TRANSICOES_POR_ESTADO[estado]}))


def alcancaveis() -> frozenset[str]:
    visitados = {ESTADO_INICIAL}
    pendentes = [ESTADO_INICIAL]
    while pendentes:
        for transicao in TRANSICOES_POR_ESTADO[pendentes.pop()]:
            if transicao.target not in visitados:
                visitados.add(transicao.target)
                pendentes.append(transicao.target)
    return frozenset(visitados)


def simbolo_lido(estado: str, caractere: str, lexema: str = "") -> str:
    if estado in ESTADOS_LITERAL:
        if caractere == APOSTROFO:
            return APOSTROFO
        if caractere in "\r\n":
            return QUEBRA_DE_LINHA
        return ESPECIAL
    if estado in ESTADOS_PALAVRA:
        if not eh_identificador(caractere):
            return caractere
        minuscula = caractere.lower()
        if delta(estado, minuscula) is not None:
            return minuscula
        return OUTRO_ID
    if estado == ESTADO_INICIAL:
        if lexema:
            return lexema[0]
        if caractere.lower() in PRIMEIRAS_LETRAS:
            return caractere.lower()
    if eh_digito(caractere):
        return DIGITO
    if caractere == UNDERSCORE:
        return UNDERSCORE
    if eh_letra(caractere):
        return LETRA
    if caractere == PONTO_DECIMAL:
        return PONTO_DECIMAL
    if caractere == APOSTROFO:
        return APOSTROFO
    return caractere


def simular(entrada: str, estado: str = ESTADO_INICIAL) -> tuple[str, str, str]:
    """Executa o autômato sobre `entrada` aplicando o máximo casamento.

    Devolve (estado final, token do último estado de aceitação, lexema aceito).
    """
    token = ACEITACAO.get(estado, "")
    aceito = ""
    for posicao, caractere in enumerate(entrada):
        proximo = delta(estado, simbolo_lido(estado, caractere))
        if proximo is None:
            break
        estado = proximo
        if estado in ACEITACAO:
            token = ACEITACAO[estado]
            aceito = entrada[: posicao + 1]
    return estado, token, aceito