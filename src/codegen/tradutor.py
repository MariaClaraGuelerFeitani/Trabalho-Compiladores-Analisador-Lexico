"""Tradutor de Guaxinim Pascal para C.

Reconhece a mesma gramática do `src/parser/parser.py`, porém emits código C
em vez de derivações. O tradutor só roda quando léxico, sintático e
semântico não têm erros, portanto pode confiar nas declarações e nos tipos
inferidos — mas mantém sua própria pilha de escopos e sua própria tabela de
tipos, porque não existe AST para reaproveitar.

Convenções de geração:

- identificadores viram `gx_<minúsculas>`, evitando colisão com palavras
  reservadas de C e com a biblioteca padrão;
- record -> struct, enumeração -> enum, alias -> o tipo C correspondente;
- `string` é `char[256]` (atribuição usa `strcpy`, comparação usa `strcmp`,
  `+` concatena via `gx_concat`);
- o resultado de uma função é uma variável local `gx_ret_<nome>` devolvida
  por `return`;
- `/` sempre gera divisão em `double`, como no Pascal;
- o laço `for` avalia os limites uma única vez em temporários, para o
  comportamento não depender do efeito colateral do corpo.

Qualquer construção que o C não possa reproduzir fielmente (por exemplo
indexar algo que não é `string`) lança `ErroDeTraducao` com mensagem em
português, em vez de emitir código quebrado.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..lexer.tokens import (
    ABRE_COLCHETES,
    ABRE_PARENTESES,
    ADICAO,
    ATRIBUICAO,
    BEGIN,
    BREAK,
    CHAR,
    CONST,
    CONTINUE,
    DIFERENTE_DE,
    DIV,
    DIVISAO,
    DO,
    DOIS_PONTOS,
    DOWNTO,
    ELSE,
    END,
    ENUM,
    FECHA_COLCHETES,
    FECHA_PARENTESES,
    FOR,
    FUNCTION,
    ID,
    IF,
    IGUALDADE_COMPARACAO,
    INTEGER,
    INTERVALO,
    LITERAL,
    MAIOR_OU_IGUAL_QUE,
    MAIOR_QUE,
    MENOR_OU_IGUAL_QUE,
    MENOR_QUE,
    MOD,
    MULTIPLICACAO,
    NUM,
    OU,
    PONTO,
    PONTO_E_VIRGULA,
    PROCEDURE,
    PROGRAM,
    REAL,
    RECORD,
    REPEAT,
    STRING,
    SUBTRACAO,
    THEN,
    TO,
    TYPE,
    UNTIL,
    VAR,
    VIRGULA,
    WHILE,
    E,
)
from ..semantic.tipos import CHAR as TIPO_CHAR
from ..semantic.tipos import INTEIRO, LOGICO, TIPO_STRING
from ..semantic.tipos import REAL as TIPO_REAL
from ..services.lexer_service import Token
from .preludio import PRELUDIO_LINHAS

FIM = ""

COMPARADORES = (
    IGUALDADE_COMPARACAO,
    DIFERENTE_DE,
    MENOR_QUE,
    MENOR_OU_IGUAL_QUE,
    MAIOR_QUE,
    MAIOR_OU_IGUAL_QUE,
)

OPERADORES = (ADICAO, SUBTRACAO)

TIPOS_PRIMARIOS = (INTEGER, REAL, CHAR, STRING)

INICIO_DE_DECLARACAO = (CONST, VAR, TYPE, PROCEDURE, FUNCTION)

FIM_DE_BLOCO = (END, UNTIL, ELSE, PONTO)

ROTULAS_DE_ENTRADA_SAIDA = ("write", "writeln", "read", "readln")

PREFIXO = "gx_"

COMPARADOR_C = {
    IGUALDADE_COMPARACAO: "==",
    DIFERENTE_DE: "!=",
    MENOR_QUE: "<",
    MENOR_OU_IGUAL_QUE: "<=",
    MAIOR_QUE: ">",
    MAIOR_OU_IGUAL_QUE: ">=",
}


class ErroDeTraducao(Exception):
    """Construção que o tradutor não sabe reproduzir em C."""

    def __init__(self, mensagem: str, token: Token | None = None) -> None:
        self.mensagem = mensagem
        self.linha = token.linha if token is not None else 0
        self.coluna = token.coluna if token is not None else 0
        local = f" (linha {self.linha})" if self.linha else ""
        super().__init__(f"{mensagem}{local}")


@dataclass
class _Simbolo:
    nome_c: str
    tipo: str


@dataclass
class _Rotina:
    nome_c: str
    parametros: list[tuple[str, str]]
    retorno: str
    eh_funcao: bool


@dataclass
class _TipoDef:
    kind: str  # "record", "enum" ou "alias"
    tipo_c: str = ""
    base: str = ""
    # "alias" guarda em `base` o tipo Pascal apontado, para o `_resolver_tipo`
    # devolver sempre um nome que o restante do tradutor entende.
    campos: list[tuple[str, str, str]] = field(default_factory=list)
    # campos: (chave minúscula, nome em C, tipo Pascal)


def mangle(nome: str) -> str:
    """Nome em C de um identificador da linguagem."""
    return f"{PREFIXO}{nome.lower()}"


def literal_para_c(lexema: str) -> str:
    """Converte o lexema de um LITERAL Pascal (com aspas) para C."""
    conteudo = lexema[1:-1].replace("''", "'")
    escapado = conteudo.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escapado}"'


class Tradutor:
    """Descida recursiva sobre os tokens, emitindo C em buffers separados."""

    def __init__(self, tokens: tuple[Token, ...]) -> None:
        self._tokens = tokens
        self._posicao = 0
        self._temporario = 0

        self._globais: dict[str, _Simbolo] = {}
        self._locais: dict[str, _Simbolo] | None = None
        self._constantes: dict[str, tuple[str, str]] = {}
        self._tipos: dict[str, _TipoDef] = {}
        self._rotinas: dict[str, _Rotina] = {}
        self._funcao_atual = ""
        self._retorno_c = ""
        self._profundidade_laco = 0

        self._linhas_macros: list[str] = []
        self._linhas_typedefs: list[str] = []
        self._linhas_globais: list[str] = []
        self._linhas_prototipos: list[str] = []
        self._corpos: list[list[str]] = []
        self._saida: list[str] = []

    # --- API ----------------------------------------------------------------

    def traduzir(self) -> str:
        self._programa()
        linhas: list[str] = [
            "/* Gerado pelo Guaxinim Pascal IDE; nao editar a mao. */",
            "#include <stdio.h>",
            "#include <string.h>",
            "",
        ]
        linhas.extend(PRELUDIO_LINHAS)
        linhas.append("")
        linhas.extend(self._linhas_typedefs)
        linhas.extend(self._linhas_macros)
        linhas.extend(self._linhas_globais)
        linhas.extend(self._linhas_prototipos)
        for corpo in self._corpos:
            linhas.append("")
            linhas.extend(corpo)
        linhas.append("")
        linhas.append("int main(void) {")
        linhas.extend(self._saida)
        linhas.append("\treturn 0;")
        linhas.append("}")
        return "\n".join(linhas) + "\n"

    # --- Cursor -------------------------------------------------------------

    def _atual(self) -> str:
        if self._posicao >= len(self._tokens):
            return FIM
        return self._tokens[self._posicao].tipo

    def _token(self) -> Token | None:
        if self._posicao >= len(self._tokens):
            return None
        return self._tokens[self._posicao]

    def _avancar(self) -> Token:
        token = self._token()
        if token is None:
            raise ErroDeTraducao("fim inesperado do programa")
        self._posicao += 1
        return token

    def _verificar(self, *tipos: str) -> bool:
        return self._atual() in tipos

    def _aceitar(self, *tipos: str) -> bool:
        if self._verificar(*tipos):
            self._posicao += 1
            return True
        return False

    def _esperar(self, tipo: str) -> Token:
        if not self._verificar(tipo):
            token = self._token()
            raise ErroDeTraducao(f"esperado o token '{tipo}'", token)
        return self._avancar()

    def _emitir(self, linha: str, nivel: int | None = None) -> None:
        indentacao = self._nivel if nivel is None else nivel
        self._saida.append("\t" * indentacao + linha if linha else "")

    @property
    def _nivel(self) -> int:
        return getattr(self, "_nivel_atual", 0)

    def _entrar_bloco(self) -> None:
        self._nivel_atual = self._nivel + 1

    def _sair_bloco(self) -> None:
        self._nivel_atual = max(0, self._nivel - 1)

    # --- Programa -----------------------------------------------------------

    def _programa(self) -> None:
        self._esperar(PROGRAM)
        self._esperar(ID)
        self._esperar(PONTO_E_VIRGULA)
        self._declaracoes_de_topo()
        self._esperar(BEGIN)
        self._nivel_atual = 1
        self._instrucoes()
        self._esperar(END)
        self._esperar(PONTO)

    def _declaracoes_de_topo(self) -> None:
        while self._verificar(*INICIO_DE_DECLARACAO):
            if self._verificar(CONST):
                self._secao_const()
            elif self._verificar(VAR):
                self._secao_var(self._globais, self._linhas_globais)
            elif self._verificar(TYPE):
                self._secao_tipo()
            else:
                self._subrotina()

    # --- const ---------------------------------------------------------------

    def _secao_const(self) -> None:
        self._avancar()
        while self._verificar(ID):
            if not self._constante_simples():
                break
        self._aceitar(PONTO_E_VIRGULA)

    def _constante_simples(self) -> bool:
        token_nome = self._avancar()
        tipo_declarado = ""
        if self._aceitar(DOIS_PONTOS):
            tipo_declarado = self._tipo()
        if not self._aceitar(IGUALDADE_COMPARACAO, ATRIBUICAO):
            raise ErroDeTraducao("esperado '=' na constante", self._token())
        valor_c, tipo_valor = self._valor_constante()
        self._esperar(PONTO_E_VIRGULA)
        tipo = tipo_declarado or tipo_valor
        chave = token_nome.lexema.lower()
        nome_c = mangle(token_nome.lexema)
        self._constantes[chave] = (nome_c, tipo)
        self._linhas_macros.append(f"#define {nome_c} ({valor_c})")
        return True

    def _valor_constante(self) -> tuple[str, str]:
        """O valor de uma constante: literal, número ou outra constante."""
        if self._verificar(LITERAL):
            return literal_para_c(self._avancar().lexema), TIPO_STRING
        sinal = ""
        while self._verificar(ADICAO, SUBTRACAO):
            if self._avancar().tipo == SUBTRACAO:
                sinal = "-" if not sinal else ""
            else:
                sinal = ""
        if self._verificar(NUM):
            token = self._avancar()
            return sinal + token.lexema, (
                INTEIRO if token.atributos == "inteiro" else TIPO_REAL
            )
        if self._verificar(ID):
            token = self._avancar()
            constante = self._constantes.get(token.lexema.lower())
            if constante is None:
                raise ErroDeTraducao(
                    f"a constante '{token.lexema}' ainda nao foi declarada", token
                )
            return sinal + constante[0], constante[1]
        raise ErroDeTraducao("esperado um valor na constante", self._token())

    # --- var -----------------------------------------------------------------

    def _secao_var(
        self, escopo: dict[str, _Simbolo], destino: list[str]
    ) -> None:
        self._avancar()
        while self._verificar(ID):
            if not self._variavel_simples(escopo, destino):
                break
        self._aceitar(PONTO_E_VIRGULA)

    def _variavel_simples(
        self, escopo: dict[str, _Simbolo], destino: list[str]
    ) -> bool:
        nomes: list[Token] = []
        while True:
            nomes.append(self._esperar(ID))
            if not self._aceitar(VIRGULA):
                break
        self._esperar(DOIS_PONTOS)
        tipo = self._tipo()
        for token_nome in nomes:
            chave = token_nome.lexema.lower()
            if chave in escopo:
                raise ErroDeTraducao(
                    f"'{token_nome.lexema}' ja declarada neste escopo", token_nome
                )
            nome_c = mangle(token_nome.lexema)
            escopo[chave] = _Simbolo(nome_c, tipo)
            destino.append(f"{self._declaracao_c(tipo, nome_c)};")
        self._esperar(PONTO_E_VIRGULA)
        return True

    # --- type ----------------------------------------------------------------

    def _secao_tipo(self) -> None:
        self._avancar()
        while self._verificar(ID):
            if not self._tipo_simples():
                break
        self._aceitar(PONTO_E_VIRGULA)

    def _tipo_simples(self) -> bool:
        token_nome = self._avancar()
        self._esperar(IGUALDADE_COMPARACAO)
        chave = token_nome.lexema.lower()
        if self._verificar(*TIPOS_PRIMARIOS):
            tipo_base = self._avancar().tipo
            self._tipos[chave] = _TipoDef("alias", base=tipo_base)
            self._esperar(PONTO_E_VIRGULA)
            return True
        if self._verificar(ID):
            base = self._avancar().lexema
            self._tipos[chave] = _TipoDef("alias", base=base)
            self._esperar(PONTO_E_VIRGULA)
            return True
        if self._verificar(ABRE_PARENTESES, ENUM):
            nomes = self._lista_enumeracao()
            tipo_c = mangle(token_nome.lexema)
            self._linhas_typedefs.append(
                f"typedef enum {{ {', '.join(mangle(n) for n in nomes)} }} {tipo_c};"
            )
            self._tipos[chave] = _TipoDef("enum", tipo_c=tipo_c)
            for nome in nomes:
                self._constantes[nome.lower()] = (mangle(nome), token_nome.lexema)
            self._esperar(PONTO_E_VIRGULA)
            return True
        if self._verificar(RECORD):
            campos = self._corpo_registro()
            tipo_c = mangle(token_nome.lexema)
            linhas = ["typedef struct {"]
            registrados: list[tuple[str, str, str]] = []
            for nome, tipo in campos:
                nome_c = mangle(nome)
                linhas.append(f"\t{self._declaracao_c(tipo, nome_c)};")
                registrados.append((nome.lower(), nome_c, tipo))
            linhas.append(f"}} {tipo_c};")
            self._linhas_typedefs.append("\n".join(linhas))
            self._tipos[chave] = _TipoDef("record", tipo_c=tipo_c, campos=registrados)
            self._esperar(PONTO_E_VIRGULA)
            return True
        raise ErroDeTraducao(
            "esperado um tipo, uma enumeracao ou 'record'", self._token()
        )

    def _lista_enumeracao(self) -> list[str]:
        if self._verificar(ENUM):
            self._avancar()
        self._esperar(ABRE_PARENTESES)
        nomes: list[str] = []
        while self._verificar(ID):
            nomes.append(self._avancar().lexema)
            if self._aceitar(INTERVALO):
                if not self._verificar(NUM, ID):
                    raise ErroDeTraducao(
                        "esperado o fim do intervalo na enumeracao", self._token()
                    )
                fim = self._avancar()
                if fim.tipo == ID:
                    nomes.append(fim.lexema)
            if not self._aceitar(VIRGULA):
                break
        self._esperar(FECHA_PARENTESES)
        return nomes

    def _corpo_registro(self) -> list[tuple[str, str]]:
        self._esperar(RECORD)
        campos: list[tuple[str, str]] = []
        while not self._verificar(END):
            if self._fim():
                raise ErroDeTraducao("esperado 'end' para fechar o record")
            nomes: list[str] = []
            while True:
                nomes.append(self._esperar(ID).lexema)
                if not self._aceitar(VIRGULA):
                    break
            self._esperar(DOIS_PONTOS)
            tipo = self._tipo()
            self._esperar(PONTO_E_VIRGULA)
            campos.extend((nome, tipo) for nome in nomes)
        self._avancar()
        return campos

    def _fim(self) -> bool:
        return self._posicao >= len(self._tokens)

    # --- Subrotinas -----------------------------------------------------------

    def _subrotina(self) -> None:
        eh_funcao = self._verificar(FUNCTION)
        self._avancar()
        token_nome = self._esperar(ID)

        parametros: list[tuple[str, str]] = []
        if self._aceitar(ABRE_PARENTESES):
            parametros = self._lista_parametros()
            self._esperar(FECHA_PARENTESES)
        tipo_retorno = ""
        if eh_funcao:
            self._esperar(DOIS_PONTOS)
            tipo_retorno = self._tipo()
        self._esperar(PONTO_E_VIRGULA)

        chave = token_nome.lexema.lower()
        nome_c = mangle(token_nome.lexema)
        rotina = _Rotina(
            nome_c=nome_c,
            parametros=[(mangle(n), t) for n, t in parametros],
            retorno=self._resolver_tipo(tipo_retorno) if tipo_retorno else "",
            eh_funcao=eh_funcao,
        )
        self._rotinas[chave] = rotina
        self._linhas_prototipos.append(self._prototipo_c(rotina) + ";")

        corpo: list[str] = []
        self._corpos.append(corpo)
        self._saida = corpo
        self._nivel_atual = 1
        self._locais = {}
        for nome_c, tipo in rotina.parametros:
            self._locais[nome_c[len(PREFIXO):]] = _Simbolo(
                nome_c, self._resolver_tipo(tipo)
            )
        self._funcao_atual = chave if eh_funcao else ""
        self._retorno_c = f"{PREFIXO}ret_{chave}" if eh_funcao else ""

        if eh_funcao:
            self._emitir(self._declaracao_resultado(rotina))

        if self._verificar(VAR):
            self._secao_var(self._locais, corpo)

        self._esperar(BEGIN)
        self._instrucoes()
        self._esperar(END)
        self._esperar(PONTO_E_VIRGULA)

        if eh_funcao:
            self._emitir(f"return {self._retorno_c};")

        corpo.insert(0, self._prototipo_c(rotina) + " {")
        corpo.append("}")

        self._locais = None
        self._funcao_atual = ""
        self._saida = []

    def _lista_parametros(self) -> list[tuple[str, str]]:
        parametros: list[tuple[str, str]] = []
        while self._verificar(ID):
            nomes: list[str] = []
            while True:
                nomes.append(self._esperar(ID).lexema)
                if not self._aceitar(VIRGULA):
                    break
            self._esperar(DOIS_PONTOS)
            tipo = self._tipo()
            parametros.extend((nome, tipo) for nome in nomes)
            if not self._aceitar(PONTO_E_VIRGULA) and not self._verificar(
                FECHA_PARENTESES
            ):
                raise ErroDeTraducao(
                    "esperado ';' ou ')' na lista de parametros", self._token()
                )
        return parametros

    def _prototipo_c(self, rotina: _Rotina) -> str:
        if not rotina.parametros:
            argumentos = "void"
        else:
            argumentos = ", ".join(
                f"{self._parametro_c(tipo)} {nome_c}"
                for nome_c, tipo in rotina.parametros
            )
        retorno = self._parametro_c(rotina.retorno) if rotina.eh_funcao else "void"
        return f"{retorno} {rotina.nome_c}({argumentos})"

    def _parametro_c(self, tipo: str) -> str:
        if tipo == TIPO_STRING:
            return f"{self._tipo_c_base(TIPO_STRING)}*"
        return self._tipo_c(tipo)

    def _declaracao_resultado(self, rotina: _Rotina) -> str:
        if rotina.retorno == TIPO_STRING:
            # `static` porque a função devolve o próprio buffer: um array
            # local morreria no return (recursão compartilha o buffer, como
            # já fazem os demais helpers de string do prelúdio).
            return f'static char {self._retorno_c}[GX_TAM_STRING] = "";'
        return f"{self._tipo_c(rotina.retorno)} {self._retorno_c} = 0;"

    # --- Tipos -----------------------------------------------------------------

    def _tipo(self) -> str:
        if self._verificar(*TIPOS_PRIMARIOS):
            return self._avancar().tipo
        if self._verificar(ID):
            return self._avancar().lexema
        raise ErroDeTraducao("esperado um tipo", self._token())

    def _resolver_tipo(self, tipo: str, visto: frozenset[str] = frozenset()) -> str:
        """Segue aliases até chegar a um tipo primitivo, record ou enum."""
        if not tipo:
            return ""
        chave = tipo.lower()
        definido = self._tipos.get(chave)
        if definido is None or definido.kind != "alias":
            return tipo
        if chave in visto:
            return tipo
        return self._resolver_tipo(definido.base, visto | {chave})

    def _tipo_c_base(self, tipo: str) -> str:
        return {
            INTEIRO: "int",
            TIPO_REAL: "double",
            TIPO_CHAR: "char",
            TIPO_STRING: "char",
            LOGICO: "int",
        }.get(tipo, "int")

    def _tipo_c(self, tipo: str) -> str:
        """Nome do tipo em C, seguindo aliases quando preciso."""
        resolvido = self._resolver_tipo(tipo)
        if not resolvido:
            return "int"
        definido = self._tipos.get(resolvido.lower())
        if definido is not None and definido.kind in ("record", "enum"):
            return definido.tipo_c
        return self._tipo_c_base(resolvido)

    def _declaracao_c(self, tipo: str, nome_c: str) -> str:
        if self._resolver_tipo(tipo) == TIPO_STRING:
            return f"char {nome_c}[GX_TAM_STRING]"
        return f"{self._tipo_c(tipo)} {nome_c}"

    # --- Escopos --------------------------------------------------------------

    def _buscar_variavel(self, chave: str) -> _Simbolo | None:
        if self._locais is not None and chave in self._locais:
            return self._locais[chave]
        return self._globais.get(chave)

    def _declarar_local(self, chave: str, simbolo: _Simbolo) -> None:
        assert self._locais is not None
        self._locais[chave] = simbolo

    # --- Instruções -----------------------------------------------------------

    def _instrucoes(self) -> None:
        while not self._fim() and not self._verificar(*FIM_DE_BLOCO):
            self._instrucao()

    def _instrucao(self) -> None:
        tipo = self._atual()
        if tipo == ID:
            self._instrucao_identificador()
            return
        if tipo == BEGIN:
            self._bloco()
            return
        if tipo == IF:
            self._instrucao_se()
            return
        if tipo == WHILE:
            self._instrucao_enquanto()
            return
        if tipo == REPEAT:
            self._instrucao_repita()
            return
        if tipo == FOR:
            self._instrucao_para()
            return
        if tipo in (BREAK, CONTINUE):
            self._avancar()
            rotulo = "break" if tipo == BREAK else "continue"
            if self._profundidade_laco == 0:
                # A analise semantica aceita break/continue fora de laco; em C
                # isso nao compila, e fora de laco a instrucao nao teria
                # efeito de qualquer forma.
                self._emitir(f"/* {rotulo} ignorado: fora de laco */")
            else:
                self._emitir(f"{rotulo};")
            self._aceitar(PONTO_E_VIRGULA)
            return
        raise ErroDeTraducao(f"instrucao invalida: '{tipo}'", self._token())

    def _bloco(self) -> None:
        self._esperar(BEGIN)
        self._emitir("{")
        self._entrar_bloco()
        self._instrucoes()
        self._sair_bloco()
        self._emitir("}")
        self._esperar(END)
        self._esperar(PONTO_E_VIRGULA)

    def _encerra_instrucao(self) -> None:
        if self._aceitar(PONTO_E_VIRGULA):
            return
        if self._verificar(*FIM_DE_BLOCO) or self._fim():
            return
        raise ErroDeTraducao("esperado ';' ao final da instrucao", self._token())

    def _instrucao_identificador(self) -> None:
        token_id = self._avancar()
        sufixos = self._consumir_sufixos()

        if self._verificar(ABRE_PARENTESES):
            if sufixos:
                raise ErroDeTraducao(
                    f"nao e possivel usar '.' ou '[]' na chamada de "
                    f"'{token_id.lexema}'",
                    token_id,
                )
            self._avancar()
            argumentos = self._argumentos()
            self._esperar(FECHA_PARENTESES)
            self._emitir_chamada_como_instrucao(token_id, argumentos)
            self._encerra_instrucao()
            return

        if self._verificar(ATRIBUICAO):
            self._avancar()
            alvo_c, tipo_alvo = self._acesso(token_id, sufixos, como_alvo=True)
            expr_c, tipo_expr = self._expr()
            self._emitir_atribuicao(alvo_c, tipo_alvo, expr_c, tipo_expr)
            self._encerra_instrucao()
            return

        if self._verificar(PONTO_E_VIRGULA, END) or self._fim():
            if token_id.lexema.lower() in ROTULAS_DE_ENTRADA_SAIDA:
                # `writeln;` sem argumentos continua sendo escrita de linha.
                self._emitir_entrada_saida(token_id.lexema.lower(), [])
                self._aceitar(PONTO_E_VIRGULA)
                return
            rotina = self._rotinas.get(token_id.lexema.lower())
            if rotina is not None and not rotina.eh_funcao:
                self._emitir(f"{rotina.nome_c}();")
            else:
                self._emitir(
                    f"/* instrucao sem efeito: {token_id.lexema} */"
                )
            self._aceitar(PONTO_E_VIRGULA)
            return

        raise ErroDeTraducao(
            f"esperado ':=' ou '(' apos '{token_id.lexema}'", self._token()
        )

    def _instrucao_se(self) -> None:
        self._avancar()
        condicao_c, _ = self._expr()
        self._esperar(THEN)
        self._emitir(f"if ({condicao_c}) {{")
        self._entrar_bloco()
        self._instrucao()
        self._sair_bloco()
        if self._aceitar(ELSE):
            self._emitir("} else {")
            self._entrar_bloco()
            self._instrucao()
            self._sair_bloco()
        self._emitir("}")

    def _instrucao_enquanto(self) -> None:
        self._avancar()
        condicao_c, _ = self._expr()
        self._esperar(DO)
        self._emitir(f"while ({condicao_c}) {{")
        self._entrar_bloco()
        self._profundidade_laco += 1
        self._instrucao()
        self._profundidade_laco -= 1
        self._sair_bloco()
        self._emitir("}")

    def _instrucao_repita(self) -> None:
        self._avancar()
        self._emitir("do {")
        self._entrar_bloco()
        self._profundidade_laco += 1
        self._instrucoes()
        self._profundidade_laco -= 1
        self._sair_bloco()
        self._esperar(UNTIL)
        condicao_c, _ = self._expr()
        self._emitir(f"}} while (!({condicao_c}));")
        self._encerra_instrucao()

    def _instrucao_para(self) -> None:
        self._avancar()
        token_var = self._esperar(ID)
        simbolo = self._buscar_variavel(token_var.lexema.lower())
        if simbolo is None:
            raise ErroDeTraducao(
                f"a variavel '{token_var.lexema}' nao foi declarada", token_var
            )
        self._esperar(ATRIBUICAO)
        inicial_c, _ = self._expr()
        eh_downto = self._aceitar(DOWNTO)
        if not eh_downto:
            self._esperar(TO)
        final_c, _ = self._expr()
        self._esperar(DO)

        self._temporario += 1
        ini = f"{PREFIXO}ini{self._temporario}"
        fim = f"{PREFIXO}fim{self._temporario}"
        comparacao = ">=" if eh_downto else "<="
        passo = "- 1" if eh_downto else "+ 1"
        self._emitir("{")
        self._emitir(f"int {ini} = ({inicial_c});", self._nivel + 1)
        self._emitir(f"int {fim} = ({final_c});", self._nivel + 1)
        self._emitir(
            f"for ({simbolo.nome_c} = {ini}; "
            f"{simbolo.nome_c} {comparacao} {fim}; "
            f"{simbolo.nome_c} = {simbolo.nome_c} {passo}) {{",
            self._nivel + 1,
        )
        self._entrar_bloco()
        self._entrar_bloco()
        self._profundidade_laco += 1
        self._instrucao()
        self._profundidade_laco -= 1
        self._sair_bloco()
        self._sair_bloco()
        self._emitir("}", self._nivel + 1)
        self._emitir("}")

    # --- Acessos e chamadas ------------------------------------------------------

    def _consumir_sufixos(self) -> list[tuple[str, object]]:
        """Consome `.campo` e `[expr]` encadeados; devolve os marcadores."""
        sufixos: list[tuple[str, object]] = []
        while True:
            if self._verificar(ABRE_COLCHETES):
                self._avancar()
                indice_c, indice_tipo = self._expr_op()
                self._esperar(FECHA_COLCHETES)
                sufixos.append(("indice", (indice_c, indice_tipo)))
            elif self._verificar(PONTO):
                self._avancar()
                sufixos.append(("campo", self._esperar(ID)))
            else:
                return sufixos

    def _acesso(
        self,
        token_id: Token,
        sufixos: list[tuple[str, object]],
        como_alvo: bool = False,
    ) -> tuple[str, str]:
        """Um ID com sufixos, como operando ou alvo de atribuição."""
        chave = token_id.lexema.lower()
        if self._funcao_atual and chave == self._funcao_atual:
            rotina = self._rotinas[self._funcao_atual]
            return self._aplicar_sufixos(
                self._retorno_c, rotina.retorno, sufixos, token_id
            )
        simbolo = self._buscar_variavel(chave)
        if simbolo is not None:
            return self._aplicar_sufixos(
                simbolo.nome_c, self._resolver_tipo(simbolo.tipo), sufixos, token_id
            )
        constante = self._constantes.get(chave)
        if constante is not None:
            if como_alvo or sufixos:
                raise ErroDeTraducao(
                    f"'{token_id.lexema}' e uma constante e nao pode receber "
                    f"atribuicao",
                    token_id,
                )
            return constante[0], constante[1]
        raise ErroDeTraducao(
            f"'{token_id.lexema}' nao foi declarada neste programa", token_id
        )

    def _aplicar_sufixos(
        self,
        expr_c: str,
        tipo: str,
        sufixos: list[tuple[str, object]],
        token_id: Token,
    ) -> tuple[str, str]:
        for kind, dado in sufixos:
            if kind == "campo":
                token_campo = dado  # type: ignore[assignment]
                definido = self._tipos.get(self._resolver_tipo(tipo).lower())
                if definido is None or definido.kind != "record":
                    raise ErroDeTraducao(
                        f"'{token_id.lexema}' nao e um record; nao ha campo "
                        f"'{token_campo.lexema}'",
                        token_campo,
                    )
                chave_campo = token_campo.lexema.lower()  # type: ignore[union-attr]
                for chave, nome_c, tipo_campo in definido.campos:
                    if chave == chave_campo:
                        expr_c = f"{expr_c}.{nome_c}"
                        tipo = self._resolver_tipo(tipo_campo)
                        break
                else:
                    raise ErroDeTraducao(
                        f"o record '{token_id.lexema}' nao tem o campo "
                        f"'{token_campo.lexema}'",
                        token_campo,
                    )
                continue
            indice_c, indice_tipo = dado  # type: ignore[misc]
            if tipo != TIPO_STRING:
                raise ErroDeTraducao(
                    f"nao e possivel indexar '{token_id.lexema}': so e "
                    f"possivel indexar string (a linguagem nao declara vetores)",
                    token_id,
                )
            if indice_tipo == TIPO_REAL:
                indice_c = f"(int)({indice_c})"
            expr_c = f"{expr_c}[({indice_c}) - 1]"
            tipo = TIPO_CHAR
        return expr_c, tipo

    def _argumentos(self) -> list[tuple[str, str]]:
        if self._verificar(FECHA_PARENTESES):
            return []
        argumentos: list[tuple[str, str]] = []
        while True:
            argumentos.append(self._expr())
            if not self._aceitar(VIRGULA):
                break
        return argumentos

    def _emitir_chamada_como_instrucao(
        self, token_id: Token, argumentos: list[tuple[str, str]]
    ) -> None:
        nome = token_id.lexema.lower()
        if nome in ROTULAS_DE_ENTRADA_SAIDA:
            self._emitir_entrada_saida(nome, argumentos)
            return
        rotina = self._rotinas.get(nome)
        if rotina is None:
            raise ErroDeTraducao(
                f"'{token_id.lexema}' nao e um procedimento declarado", token_id
            )
        if rotina.eh_funcao:
            raise ErroDeTraducao(
                f"'{token_id.lexema}' e uma funcao; use o resultado dela",
                token_id,
            )
        chamada = f"{rotina.nome_c}({self._argumentos_c(rotina, argumentos)});"
        self._emitir(chamada)

    def _chamar_como_operando(
        self, token_id: Token, argumentos: list[tuple[str, str]]
    ) -> tuple[str, str]:
        nome = token_id.lexema.lower()
        rotina = self._rotinas.get(nome)
        if rotina is None or not rotina.eh_funcao:
            raise ErroDeTraducao(
                f"'{token_id.lexema}' nao e uma funcao declarada", token_id
            )
        chamada = f"{rotina.nome_c}({self._argumentos_c(rotina, argumentos)})"
        return chamada, rotina.retorno

    def _argumentos_c(
        self, rotina: _Rotina, argumentos: list[tuple[str, str]]
    ) -> str:
        convertidos: list[str] = []
        for indice, (expr_c, tipo_expr) in enumerate(argumentos):
            tipo_param = (
                rotina.parametros[indice][1]
                if indice < len(rotina.parametros)
                else ""
            )
            convertidos.append(
                self._converter(expr_c, tipo_expr, tipo_param)
            )
        return ", ".join(convertidos)

    def _converter(self, expr_c: str, tipo_origem: str, tipo_destino: str) -> str:
        if not tipo_destino or not tipo_origem:
            return expr_c
        if tipo_destino == TIPO_REAL and tipo_origem == INTEIRO:
            return f"(double)({expr_c})"
        if tipo_destino == TIPO_STRING and tipo_origem == TIPO_CHAR:
            return f"gx_char_para_str({expr_c})"
        if tipo_destino == TIPO_CHAR and tipo_origem == TIPO_STRING:
            return f"gx_str_para_char({expr_c})"
        return expr_c

    # --- entrada e saida -----------------------------------------------------------

    def _emitir_entrada_saida(
        self, nome: str, argumentos: list[tuple[str, str]]
    ) -> None:
        if nome in ("read", "readln"):
            self._emitir_leitura(nome, argumentos)
            return
        eh_writeln = nome == "writeln"
        formato = ""
        valores: list[str] = []
        for expr_c, tipo in argumentos:
            if tipo == LOGICO:
                formato += "%s"
                valores.append(f"(({expr_c}) ? \"True\" : \"False\")")
            elif tipo == INTEIRO:
                formato += "%d"
                valores.append(expr_c)
            elif tipo == TIPO_REAL:
                formato += "%g"
                valores.append(expr_c)
            elif tipo == TIPO_CHAR:
                formato += "%c"
                valores.append(expr_c)
            else:
                formato += "%s"
                valores.append(expr_c)
        if eh_writeln:
            formato += "\\n"
        if not valores:
            self._emitir(f'printf("{formato}");')
            return
        argumentos_c = ", ".join(valores)
        self._emitir(f'printf("{formato}", {argumentos_c});')

    def _emitir_leitura(
        self, nome: str, argumentos: list[tuple[str, str]]
    ) -> None:
        destino: list[str] = []
        formato = ""
        for indice, (expr_c, tipo) in enumerate(argumentos):
            # Separador entre diretrizes; o espaco no FINAL do formato faria o
            # scanf bloquear esperando algo que nao seja branco depois do valor.
            separador = "" if indice == 0 else " "
            if tipo == INTEIRO:
                formato += f"{separador}%d"
                destino.append(f"&{expr_c}")
            elif tipo == TIPO_REAL:
                formato += f"{separador}%lf"
                destino.append(f"&{expr_c}")
            elif tipo == TIPO_CHAR:
                formato += " %c"
                destino.append(f"&{expr_c}")
            else:
                formato += f"{separador}%255s"
                destino.append(expr_c)
        if formato:
            self._emitir(
                f'scanf("{formato}", {", ".join(destino)});'
            )
        if nome == "readln" or not formato:
            self._emitir("gx_consumir_linha();")

    # --- Atribuição -------------------------------------------------------------------

    def _emitir_atribuicao(
        self,
        alvo_c: str,
        tipo_alvo: str,
        expr_c: str,
        tipo_expr: str,
    ) -> None:
        if tipo_alvo == TIPO_STRING:
            origem = self._converter(expr_c, tipo_expr, TIPO_STRING)
            self._emitir(f"strcpy({alvo_c}, ({origem}));")
            return
        if tipo_alvo == TIPO_CHAR and tipo_expr == TIPO_STRING:
            self._emitir(f"{alvo_c} = gx_str_para_char({expr_c});")
            return
        if tipo_alvo == TIPO_REAL and tipo_expr == INTEIRO:
            self._emitir(f"{alvo_c} = (double)({expr_c});")
            return
        self._emitir(f"{alvo_c} = {expr_c};")

    # --- Expressões ----------------------------------------------------------------------

    def _expr(self) -> tuple[str, str]:
        expr_c, tipo = self._expr_comparacao()
        while self._verificar(OU, E):
            operador = self._avancar().tipo
            direita_c, _ = self._expr_comparacao()
            operador_c = "||" if operador == OU else "&&"
            expr_c = f"({expr_c}) {operador_c} ({direita_c})"
            tipo = LOGICO
        return expr_c, tipo

    def _expr_comparacao(self) -> tuple[str, str]:
        expr_c, tipo = self._expr_op()
        while self._verificar(*COMPARADORES):
            operador = self._avancar().tipo
            direita_c, tipo_direita = self._expr_op()
            if tipo in (TIPO_STRING, TIPO_CHAR) or tipo_direita in (
                TIPO_STRING,
                TIPO_CHAR,
            ):
                esquerda = self._converter(expr_c, tipo, TIPO_STRING)
                direita = self._converter(
                    direita_c, tipo_direita, TIPO_STRING
                )
                expr_c = f"(strcmp({esquerda}, {direita}) {COMPARADOR_C[operador]} 0)"
            else:
                expr_c = f"({expr_c}) {COMPARADOR_C[operador]} ({direita_c})"
            tipo = LOGICO
        return expr_c, tipo

    def _expr_op(self) -> tuple[str, str]:
        expr_c, tipo = self._termo()
        while self._verificar(*OPERADORES):
            operador = self._avancar().tipo
            direita_c, tipo_direita = self._termo()
            if operador == ADICAO and (
                tipo in (TIPO_STRING, TIPO_CHAR)
                or tipo_direita in (TIPO_STRING, TIPO_CHAR)
            ):
                esquerda = self._converter(expr_c, tipo, TIPO_STRING)
                direita = self._converter(direita_c, tipo_direita, TIPO_STRING)
                expr_c = f"gx_concat({esquerda}, {direita})"
                tipo = TIPO_STRING
            else:
                operador_c = "+" if operador == ADICAO else "-"
                expr_c = f"{expr_c} {operador_c} {direita_c}"
                tipo = self._tipo_aritmetico(tipo, tipo_direita)
        return expr_c, tipo

    def _termo(self) -> tuple[str, str]:
        expr_c, tipo = self._unario()
        while self._verificar(MULTIPLICACAO, DIVISAO, MOD, DIV):
            operador = self._avancar().tipo
            direita_c, tipo_direita = self._unario()
            if operador == DIVISAO:
                expr_c = (
                    f"((double)({expr_c}) / (double)({direita_c}))"
                )
                tipo = TIPO_REAL
            elif operador == MOD:
                expr_c = f"(({expr_c}) % ({direita_c}))"
                tipo = INTEIRO
            elif operador == DIV:
                # `div` de Pascal: divisão inteira; em C, inteiros já dividem assim.
                expr_c = f"(({expr_c}) / ({direita_c}))"
                tipo = INTEIRO
            else:
                expr_c = f"{expr_c} * {direita_c}"
                tipo = self._tipo_aritmetico(tipo, tipo_direita)
        return expr_c, tipo

    def _unario(self) -> tuple[str, str]:
        if self._verificar(*OPERADORES):
            operador = self._avancar().tipo
            expr_c, tipo = self._unario()
            if operador == SUBTRACAO:
                return f"-({expr_c})", tipo
            return expr_c, tipo
        return self._fator()

    def _fator(self) -> tuple[str, str]:
        if self._verificar(ABRE_PARENTESES):
            self._avancar()
            expr_c, tipo = self._expr()
            self._esperar(FECHA_PARENTESES)
            return f"({expr_c})", tipo
        if self._verificar(NUM):
            token = self._avancar()
            return token.lexema, (
                INTEIRO if token.atributos == "inteiro" else TIPO_REAL
            )
        if self._verificar(LITERAL):
            return literal_para_c(self._avancar().lexema), TIPO_STRING
        if self._verificar(ID):
            token_id = self._avancar()
            sufixos = self._consumir_sufixos()
            if self._verificar(ABRE_PARENTESES) and not sufixos:
                self._avancar()
                argumentos = self._argumentos()
                self._esperar(FECHA_PARENTESES)
                return self._chamar_como_operando(token_id, argumentos)
            return self._acesso(token_id, sufixos)
        raise ErroDeTraducao("esperado uma expressao", self._token())

    @staticmethod
    def _tipo_aritmetico(esquerda: str, direita: str) -> str:
        if esquerda == TIPO_REAL or direita == TIPO_REAL:
            return TIPO_REAL
        return INTEIRO


def traduzir(tokens: tuple[Token, ...]) -> str:
    """Converte os tokens de um programa em C; levanta `ErroDeTraducao`."""
    return Tradutor(tokens).traduzir()


__all__ = ["ErroDeTraducao", "Tradutor", "literal_para_c", "mangle", "traduzir"]
