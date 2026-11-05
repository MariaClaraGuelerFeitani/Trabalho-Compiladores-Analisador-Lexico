"""Árvore sintática abstrata (AST) do dialeto Pascal do projeto.

O parser de descida recursiva constrói estes nós à medida que reconhece o
programa. A AST é independente do tradutor para C (`src/codegen/tradutor.py`):
ela serve à inspeção da estrutura do programa, à validação visual da
precedência dos operadores e à exportação em texto/JSON para a IDE.

Todos os nós são imutáveis e guardam a linha/coluna do token que os originou.
`para_ascii` desenha expressões binárias na forma clássica (operador no topo,
filhos abaixo) e o restante como árvore indentada; `para_json` devolve uma
estrutura pronta para ser consumida pela interface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class No:
    """Base de todos os nós. `tipo` é o tipo inferido quando aplicável."""

    tipo: str = ""
    linha: int = 0
    coluna: int = 0

    def rotulo(self) -> str:
        """Texto curto exibido na árvore."""
        return type(self).__name__.removeprefix("No")

    def filhos(self) -> tuple[tuple[str, No], ...]:
        """Pares (rótulo da aresta, nó filho), na ordem de exibição."""
        return ()


@dataclass(frozen=True)
class NoPrograma(No):
    nome: str = ""
    declaracoes: tuple[No, ...] = ()
    comandos: tuple[No, ...] = ()

    def rotulo(self) -> str:
        return f"Programa {self.nome}".rstrip()

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(
            [("decl", no) for no in self.declaracoes]
            + [("cmd", no) for no in self.comandos]
        )


@dataclass(frozen=True)
class NoBloco(No):
    comandos: tuple[No, ...] = ()

    def rotulo(self) -> str:
        return "Bloco"

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(("cmd", no) for no in self.comandos)


@dataclass(frozen=True)
class NoDeclaracaoVariavel(No):
    nomes: tuple[str, ...] = ()
    tipo_declarado: str = ""

    def rotulo(self) -> str:
        nomes = ", ".join(self.nomes)
        return f"var {nomes}: {self.tipo_declarado}".rstrip(": ")


@dataclass(frozen=True)
class NoDeclaracaoConstante(No):
    nome: str = ""
    valor: str = ""

    def rotulo(self) -> str:
        return f"const {self.nome} = {self.valor}".rstrip("= ")


@dataclass(frozen=True)
class NoDeclaracaoTipo(No):
    nome: str = ""
    tipo_declarado: str = ""

    def rotulo(self) -> str:
        return f"type {self.nome} = {self.tipo_declarado}".rstrip("= ")


@dataclass(frozen=True)
class NoDeclaracaoSubprograma(No):
    nome: str = ""
    categoria: str = ""
    parametros: tuple[NoDeclaracaoVariavel, ...] = ()
    declaracoes: tuple[No, ...] = ()
    corpo: No | None = None

    def rotulo(self) -> str:
        return f"{self.categoria} {self.nome}".strip()

    def filhos(self) -> tuple[tuple[str, No], ...]:
        filhos: list[tuple[str, No]] = [
            ("param", no) for no in self.parametros
        ]
        filhos.extend(("decl", no) for no in self.declaracoes)
        if self.corpo is not None:
            filhos.append(("corpo", self.corpo))
        return tuple(filhos)


@dataclass(frozen=True)
class NoAtribuicao(No):
    alvo: No | None = None
    expressao: No | None = None

    def rotulo(self) -> str:
        return "Atribuicao"

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(
            (rotulo, no)
            for rotulo, no in (("alvo", self.alvo), ("expr", self.expressao))
            if no is not None
        )


@dataclass(frozen=True)
class NoChamada(No):
    nome: str = ""
    argumentos: tuple[No, ...] = ()

    def rotulo(self) -> str:
        return f"Chamada {self.nome}".strip()

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(("arg", no) for no in self.argumentos)


@dataclass(frozen=True)
class NoSe(No):
    condicao: No | None = None
    entao: No | None = None
    senao: No | None = None

    def rotulo(self) -> str:
        return "Se"

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(
            (rotulo, no)
            for rotulo, no in (
                ("cond", self.condicao),
                ("entao", self.entao),
                ("senao", self.senao),
            )
            if no is not None
        )


@dataclass(frozen=True)
class NoEnquanto(No):
    condicao: No | None = None
    corpo: No | None = None

    def rotulo(self) -> str:
        return "Enquanto"

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(
            (rotulo, no)
            for rotulo, no in (("cond", self.condicao), ("corpo", self.corpo))
            if no is not None
        )


@dataclass(frozen=True)
class NoRepita(No):
    corpo: No | None = None
    condicao: No | None = None

    def rotulo(self) -> str:
        return "Repita"

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(
            (rotulo, no)
            for rotulo, no in (("corpo", self.corpo), ("ate", self.condicao))
            if no is not None
        )


@dataclass(frozen=True)
class NoPara(No):
    variavel: str = ""
    inicio: No | None = None
    fim: No | None = None
    passo: str = "to"
    corpo: No | None = None

    def rotulo(self) -> str:
        return f"Para {self.variavel} ({self.passo})".strip()

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(
            (rotulo, no)
            for rotulo, no in (
                ("inicio", self.inicio),
                ("fim", self.fim),
                ("corpo", self.corpo),
            )
            if no is not None
        )


@dataclass(frozen=True)
class NoDesvio(No):
    comando: str = ""

    def rotulo(self) -> str:
        return self.comando


@dataclass(frozen=True)
class NoNumero(No):
    valor: str = ""

    def rotulo(self) -> str:
        return self.valor


@dataclass(frozen=True)
class NoLiteral(No):
    valor: str = ""

    def rotulo(self) -> str:
        return self.valor


@dataclass(frozen=True)
class NoVariavel(No):
    nome: str = ""

    def rotulo(self) -> str:
        return self.nome


@dataclass(frozen=True)
class NoIndice(No):
    base: No | None = None
    indice: No | None = None

    def rotulo(self) -> str:
        return "[]"

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(
            (rotulo, no)
            for rotulo, no in (("base", self.base), ("indice", self.indice))
            if no is not None
        )


@dataclass(frozen=True)
class NoCampo(No):
    base: No | None = None
    campo: str = ""

    def rotulo(self) -> str:
        return f".{self.campo}"

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return (("base", self.base),) if self.base is not None else ()


@dataclass(frozen=True)
class NoBinario(No):
    operador: str = ""
    esquerda: No | None = None
    direita: No | None = None

    def rotulo(self) -> str:
        return self.operador

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return tuple(
            (rotulo, no)
            for rotulo, no in (
                ("esq", self.esquerda),
                ("dir", self.direita),
            )
            if no is not None
        )


@dataclass(frozen=True)
class NoUnario(No):
    operador: str = ""
    operando: No | None = None

    def rotulo(self) -> str:
        return self.operador

    def filhos(self) -> tuple[tuple[str, No], ...]:
        return (("operando", self.operando),) if self.operando is not None else ()


# --- Exportação -----------------------------------------------------------


def para_dict(no: No | None) -> dict | None:
    """Converte a AST em dicionários/listas prontos para JSON."""
    if no is None:
        return None
    resultado: dict = {"no": type(no).__name__.removeprefix("No")}
    for campo in fields(no):
        valor = getattr(no, campo.name)
        if isinstance(valor, No):
            resultado[campo.name] = para_dict(valor)
        elif isinstance(valor, tuple):
            resultado[campo.name] = [
                para_dict(item) if isinstance(item, No) else item for item in valor
            ]
        else:
            resultado[campo.name] = valor
    return resultado


def para_json(no: No | None, indent: int | None = 2) -> str:
    """Serializa a AST em JSON (com `indent=None`, em uma linha)."""
    return json.dumps(para_dict(no), ensure_ascii=False, indent=indent)


def _prefixo(no: No) -> list[str]:
    """Árvore indentada com `├──`/`└──`, usada para comandos e declarações."""
    linhas = [no.rotulo()]
    filhos = no.filhos()
    for indice, (_, filho) in enumerate(filhos):
        ultimo = indice == len(filhos) - 1
        ramo = "└── " if ultimo else "├── "
        sub = _prefixo(filho)
        linhas.append(ramo + sub[0])
        recuo = "    " if ultimo else "│   "
        linhas.extend(recuo + linha for linha in sub[1:])
    return linhas


def _expr(no: No | None) -> tuple[list[str], int, int]:
    """Desenha uma expressão; devolve (linhas, largura, coluna da raiz).

    Expressões binárias ficam centralizadas, como no enunciado:

             +
            / \\
           7   *
              / \\
             3   5
    """
    if no is None:
        return ["?"], 1, 0
    if isinstance(no, NoBinario):
        esquerda, largura_esq, _ = _expr(no.esquerda)
        direita, largura_dir, _ = _expr(no.direita)
        intervalo = 2
        raiz = largura_esq + intervalo // 2
        largura = max(
            largura_esq + intervalo + largura_dir,
            raiz + 2,
            len(no.rotulo()),
        )
        linhas = [" " * raiz + no.rotulo()]
        conector = [" "] * largura
        conector[max(0, raiz - 1)] = "/"
        if raiz + 1 < largura:
            conector[raiz + 1] = "\\"
        linhas.append("".join(conector).rstrip())
        for indice in range(max(len(esquerda), len(direita))):
            linha_esq = esquerda[indice] if indice < len(esquerda) else ""
            linha_dir = direita[indice] if indice < len(direita) else ""
            linhas.append(
                linha_esq.ljust(largura_esq + intervalo) + linha_dir
            )
        return linhas, largura, raiz
    linhas = _prefixo(no)
    largura = max(len(linha) for linha in linhas)
    return linhas, largura, largura // 2


def para_ascii(no: No | None) -> str:
    """Desenha a AST para exibição no terminal/IDE.

    A raiz de uma expressão binária sai na forma centralizada do enunciado;
    comandos e declarações saem como árvore indentada.
    """
    if no is None:
        return ""
    if isinstance(no, (NoBinario, NoNumero, NoLiteral, NoVariavel)):
        linhas, _, _ = _expr(no)
    else:
        linhas = _prefixo(no)
    return "\n".join(linha.rstrip() for linha in linhas)


def para_texto_estruturado(no: No | None) -> str:
    """Árvore indentada uniforme, útil para percorrer programas completos."""
    if no is None:
        return ""
    return "\n".join(linha.rstrip() for linha in _prefixo(no))


__all__ = [
    "No",
    "NoAtribuicao",
    "NoBinario",
    "NoBloco",
    "NoCampo",
    "NoChamada",
    "NoDeclaracaoConstante",
    "NoDeclaracaoSubprograma",
    "NoDeclaracaoTipo",
    "NoDeclaracaoVariavel",
    "NoDesvio",
    "NoEnquanto",
    "NoIndice",
    "NoLiteral",
    "NoNumero",
    "NoPara",
    "NoPrograma",
    "NoRepita",
    "NoSe",
    "NoUnario",
    "NoVariavel",
    "para_ascii",
    "para_dict",
    "para_json",
    "para_texto_estruturado",
]
