"""Tabela de símbolos com escopos encadeados para a análise semântica.

Cada `Escopo` tem seus próprios símbolos e um ponteiro para o escopo-pai; a
busca sobe a cadeia até o escopo global, onde ficam os símbolos predefinidos
(`writeln` etc.) e as declarações do programa. Em contraste com a tabela
plana do analisador léxico (`src/lexer/models.py`), esta tabela distingue o
mesmo nome declarado em procedimentos diferentes e conhece parâmetros,
campos de registro e a categoria de cada entrada — o que é o que a
verificação de tipos precisa.

Identificadores são tratados sem distinção de maiúsculas, como no restante
da linguagem: a chave interna é o lexema em minúsculas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Categorias de entrada.
CONSTANTE = "constante"
CONSTANTE_ENUM = "constante de enumacao"
FUNCAO = "funcao"
PARAMETRO = "parametro"
PREDEFINIDO = "predefinido"
PROCEDIMENTO = "procedimento"
TIPO = "tipo"
TIPO_ENUMERACAO = "tipo_enumeracao"
TIPO_REGISTRO = "tipo_registro"
VARIAVEL = "variavel"


@dataclass
class Entrada:
    """Um símbolo declarado, com tudo o que a verificação de tipos usa."""

    nome: str
    categoria: str
    tipo: str = ""
    linha: int = 0
    coluna: int = 0
    parametros: list[tuple[str, str]] = field(default_factory=list)
    tipo_retorno: str = ""
    campos: dict[str, str] = field(default_factory=dict)
    variadico: bool = False
    eh_propria: bool = False
    usado: bool = False

    @property
    def eh_subprograma(self) -> bool:
        return self.categoria in (FUNCAO, PROCEDIMENTO, PREDEFINIDO)


@dataclass
class Escopo:
    """Um nível de visibilidade; `pai` é o escopo onde a busca continua."""

    nome: str
    pai: Escopo | None = None
    entradas: dict[str, Entrada] = field(default_factory=dict)

    def proprio(self, chave: str) -> Entrada | None:
        return self.entradas.get(chave)


class TabelaDeSimbolos:
    """Pilha de escopos com busca encadeada até o global."""

    def __init__(self) -> None:
        self.global_ = Escopo("global")
        self.atual = self.global_

    def abrir_escopo(self, nome: str) -> None:
        self.atual = Escopo(nome, pai=self.atual)

    def fechar_escopo(self) -> Escopo:
        encerrado = self.atual
        if self.atual.pai is not None:
            self.atual = self.atual.pai
        return encerrado

    def declarar(self, entrada: Entrada) -> Entrada | None:
        """Registra `entrada` no escopo atual.

        Devolve a entrada anterior quando o nome já existia *no mesmo escopo*
        (redeclaração); sombreamento de um escopo externo é permitido.
        """
        chave = entrada.nome.lower()
        anterior = self.atual.proprio(chave)
        if anterior is not None:
            return anterior
        self.atual.entradas[chave] = entrada
        return None

    def buscar(self, nome: str) -> Entrada | None:
        """Localiza `nome` no escopo atual ou em algum pai, marcando o uso."""
        chave = nome.lower()
        escopo: Escopo | None = self.atual
        while escopo is not None:
            entrada = escopo.proprio(chave)
            if entrada is not None:
                entrada.usado = True
                return entrada
            escopo = escopo.pai
        return None


__all__ = [
    "CONSTANTE",
    "CONSTANTE_ENUM",
    "FUNCAO",
    "PARAMETRO",
    "PREDEFINIDO",
    "PROCEDIMENTO",
    "TIPO",
    "TIPO_ENUMERACAO",
    "TIPO_REGISTRO",
    "VARIAVEL",
    "Entrada",
    "Escopo",
    "TabelaDeSimbolos",
]
