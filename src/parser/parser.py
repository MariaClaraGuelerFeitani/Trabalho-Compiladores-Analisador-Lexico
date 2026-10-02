"""Analisador sintático por descida recursiva.

O parser consome a sequência de tokens produzida por `src/lexer/lexer.py` e
confronta-a com a gramática de `src/parser/grammar.py`, que transcreve o Anexo I
e acrescenta as extensões da parte 2 (`for`, tipos `record` e enumeração).

Dois artefatos são produzidos:

- **Erros sintáticos**, com linha, coluna e lexema, no mesmo formato de
  `LexicalError`, para que o editor os sublinhe em vermelho sem novo código.
- **Avisos**, entre eles o aviso de *instrução sem efeito* exigido no
  enunciado: uma instrução formada apenas por um identificador.

A recuperação de erros é o método de panic: ao encontrar um token inesperado,
o parser registra o erro e descarta tokens até um ponto de sincronização
(`PONTOS_DE_SINCRONIZACAO`), de onde tenta continuar. Isso permite corrigir
vários erros do mesmo arquivo em uma única passagem.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..services.lexer_service import LexicalError, Token, Warning
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
    DIVISAO,
    DO,
    DOIS_PONTOS,
    DOWNTO,
    E,
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
)

# Marca usada internamente para "fim da entrada". Não colide com nenhum token.
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

# Onde o parser pode reiniciar a análise depois de um erro.
PONTOS_DE_SINCRONIZACAO = (
    PONTO_E_VIRGULA,
    PONTO,
    END,
    BEGIN,
    ELSE,
    THEN,
    DO,
    UNTIL,
)

DESCRICAO_DE_TOKEN = {
    PONTO_E_VIRGULA: "';'",
    PONTO: "'.'",
    DOIS_PONTOS: "':'",
    VIRGULA: "','",
    ABRE_PARENTESES: "'('",
    FECHA_PARENTESES: "')'",
    ABRE_COLCHETES: "'['",
    FECHA_COLCHETES: "']'",
    ATRIBUICAO: "':='",
    IGUALDADE_COMPARACAO: "'='",
    ADICAO: "'+'",
    SUBTRACAO: "'-'",
    MULTIPLICACAO: "'*'",
    DIVISAO: "'/'",
    BEGIN: "'begin'",
    END: "'end'",
    IF: "'if'",
    THEN: "'then'",
    ELSE: "'else'",
    WHILE: "'while'",
    DO: "'do'",
    REPEAT: "'repeat'",
    UNTIL: "'until'",
    FOR: "'for'",
    TO: "'to'",
    DOWNTO: "'downto'",
    CONST: "'const'",
    VAR: "'var'",
    TYPE: "'type'",
    PROCEDURE: "'procedure'",
    FUNCTION: "'function'",
    ID: "um identificador",
    NUM: "um número",
    LITERAL: "um literal",
    RECORD: "'record'",
}


@dataclass(frozen=True)
class ResultadoSintatico:
    """Saída do analisador sintático."""

    erros: tuple[LexicalError, ...] = ()
    avisos: tuple[Warning, ...] = ()
    derivacoes: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.erros


@dataclass
class _Estado:
    posicao: int = 0
    erros: list[LexicalError] = field(default_factory=list)
    avisos: list[Warning] = field(default_factory=list)
    derivacoes: list[str] = field(default_factory=list)


class Parser:
    """Analisador sintático por descida recursiva sobre a gramática do Anexo I."""

    def __init__(
        self,
        tokens: tuple[Token, ...],
        simbolos: tuple | None = None,
    ) -> None:
        self._tokens = tokens
        self._estado = _Estado()
        self._subprogramas = {
            simbolo.identifier
            for simbolo in (simbolos or ())
            if simbolo.kind in ("procedimento", "funcao")
        }

    def analisar(self) -> ResultadoSintatico:
        self._estado = _Estado()
        self._programa()
        if not self._fim() and not self._estado.erros:
            self._erro(f"token inesperado após o fim do programa: {self._descricao(self._atual())}")
        return ResultadoSintatico(
            tuple(self._estado.erros),
            tuple(self._estado.avisos),
            tuple(self._estado.derivacoes),
        )

    # --- Cursor -----------------------------------------------------------

    def _atual(self) -> str:
        if self._estado.posicao >= len(self._tokens):
            return FIM
        return self._tokens[self._estado.posicao].tipo

    def _olhar(self, quantos: int) -> str:
        indice = self._estado.posicao + quantos
        if indice >= len(self._tokens):
            return FIM
        return self._tokens[indice].tipo

    def _fim(self) -> bool:
        return self._estado.posicao >= len(self._tokens)

    def _token_atual(self) -> Token | None:
        if self._fim():
            return None
        return self._tokens[self._estado.posicao]

    def _anterior(self) -> Token | None:
        indice = self._estado.posicao - 1
        if indice < 0 or indice >= len(self._tokens):
            return None
        return self._tokens[indice]

    def _avancar(self) -> Token | None:
        token = self._token_atual()
        if token is not None:
            self._estado.posicao += 1
        return token

    def _verificar(self, *tipos: str) -> bool:
        return self._atual() in tipos

    def _aceitar(self, *tipos: str) -> bool:
        if self._verificar(*tipos):
            self._avancar()
            return True
        return False

    def _derivacao(self, nome: str) -> None:
        self._estado.derivacoes.append(nome)

    # --- Erros ------------------------------------------------------------

    def _descricao(self, tipo: str) -> str:
        if tipo == FIM:
            return "fim do arquivo"
        return DESCRICAO_DE_TOKEN.get(tipo, f"'{tipo}'")

    def _erro(self, mensagem: str, token: Token | None = None) -> None:
        alvo = token if token is not None else self._token_atual()
        if alvo is None:
            anterior = self._anterior()
            linha = anterior.linha if anterior else 1
            coluna = (anterior.coluna + len(anterior.lexema)) if anterior else 1
            self._estado.erros.append(
                LexicalError(linha, coluna, f"sintaxe: {mensagem}", "", 1)
            )
            return
        self._estado.erros.append(
            LexicalError(
                alvo.linha,
                alvo.coluna,
                f"sintaxe: {mensagem}",
                alvo.lexema,
                max(1, len(alvo.lexema)),
            )
        )

    def _esperar(self, tipo: str, descricao: str = "") -> bool:
        if self._aceitar(tipo):
            return True
        self._erro(f"esperado {descricao or self._descricao(tipo)}")
        return False

    def _sincronizar(self) -> None:
        while not self._fim():
            if self._atual() in PONTOS_DE_SINCRONIZACAO:
                if self._atual() == PONTO_E_VIRGULA:
                    self._avancar()
                return
            self._avancar()

    def _avisar(self, mensagem: str, token: Token | None = None) -> None:
        alvo = token if token is not None else self._anterior()
        if alvo is None:
            self._estado.avisos.append(Warning(1, 1, mensagem))
            return
        self._estado.avisos.append(Warning(alvo.linha, alvo.coluna, mensagem))

    # --- Produções --------------------------------------------------------

    def _programa(self) -> None:
        self._derivacao("programa")
        if self._fim():
            self._erro("esperado 'program' ou 'programa': o arquivo está vazio")
            return
        self._esperar(PROGRAM, "'program' ou 'programa'")
        self._esperar(ID, "o nome do programa")
        self._esperar(PONTO_E_VIRGULA)
        self._declaracoes()
        self._esperar(BEGIN, "'begin'")
        self._instrucoes()
        self._esperar(END, "'end'")
        self._esperar(PONTO, "'.'")

    def _declaracoes(self) -> None:
        self._derivacao("declaracoes")
        while self._verificar(*INICIO_DE_DECLARACAO):
            if self._verificar(CONST):
                self._declaracao_constante()
            elif self._verificar(VAR):
                self._declaracao_variavel()
            elif self._verificar(TYPE):
                self._declaracao_tipo()
            else:
                self._declaracao_procedimento()

    def _declaracao_constante(self) -> None:
        self._derivacao("declaracaoConstante")
        self._avancar()
        while self._verificar(ID):
            if not self._declaracao_constante_simples():
                self._sincronizar()
                return
        self._aceitar(PONTO_E_VIRGULA)

    def _declaracao_constante_simples(self) -> bool:
        self._derivacao("declConsList")
        if not self._verificar(ID):
            return False
        if not self._esperar(ID, "o nome de uma constante"):
            return False
        if self._aceitar(DOIS_PONTOS):
            self._tipo()
        if not self._verificar(IGUALDADE_COMPARACAO, ATRIBUICAO):
            self._erro("esperado '=' para o valor da constante")
            return False
        self._avancar()
        self._valor()
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final da declaração de constante")
            return False
        self._avancar()
        return True

    def _declaracao_variavel(self) -> None:
        self._derivacao("declaracaoVariavel")
        self._avancar()
        while self._verificar(ID):
            if not self._declaracao_variavel_simples():
                self._sincronizar()
                return
        self._aceitar(PONTO_E_VIRGULA)

    def _declaracao_variavel_simples(self) -> bool:
        self._derivacao("declVar")
        while True:
            if not self._esperar(ID, "o nome de uma variável"):
                return False
            if not self._aceitar(VIRGULA):
                break
        if not self._esperar(DOIS_PONTOS, "':' antes do tipo"):
            return False
        self._tipo()
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final da declaração de variável")
            return False
        self._avancar()
        return True

    def _tipo(self) -> str:
        self._derivacao("tipo")
        if self._verificar(*TIPOS_PRIMARIOS):
            self._avancar()
            return self._anterior().tipo
        self._derivacao("tipoSimples")
        if self._aceitar(ID):
            return self._anterior().lexema
        self._erro("esperado um tipo (integer, real, char, string ou um tipo definido)")
        return ""

    def _declaracao_tipo(self) -> None:
        self._derivacao("declaracaoTipo")
        self._avancar()
        while self._verificar(ID):
            if not self._declaracao_tipo_simples():
                self._sincronizar()
                return
        self._aceitar(PONTO_E_VIRGULA)

    def _declaracao_tipo_simples(self) -> bool:
        self._derivacao("declTipo")
        if not self._esperar(ID, "o nome de um tipo"):
            return False
        if not self._esperar(IGUALDADE_COMPARACAO, "'=' na declaração de tipo"):
            return False
        if self._verificar(*TIPOS_PRIMARIOS):
            self._avancar()
        elif self._verificar(ID):
            self._avancar()
        elif self._verificar(ABRE_PARENTESES):
            if not self._lista_enumeracao():
                return False
        elif self._verificar(RECORD):
            if not self._corpo_registro():
                return False
        elif self._verificar(ENUM):
            self._avancar()
            if not self._lista_enumeracao():
                return False
        else:
            self._erro(
                "esperado um tipo, uma lista de enumeração ou 'record' na declaração de tipo"
            )
            return False
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final da declaração de tipo")
            return False
        self._avancar()
        return True

    def _lista_enumeracao(self) -> bool:
        self._derivacao("listaEnum")
        self._avancar()
        if not self._verificar(ID):
            self._erro("esperado o nome de uma constante de enumeração")
            self._sincronizar()
            return False
        while self._verificar(ID):
            self._avancar()
            if self._aceitar(INTERVALO):
                if not self._verificar(NUM, ID):
                    self._erro("esperado um número ou identificador para o fim do intervalo")
                    self._sincronizar()
                    return False
                self._avancar()
            if not self._aceitar(VIRGULA):
                break
        if not self._verificar(FECHA_PARENTESES):
            self._erro("esperado ')' para fechar a enumeração")
            self._sincronizar()
            return False
        self._avancar()
        return True

    def _corpo_registro(self) -> bool:
        self._derivacao("campos")
        self._avancar()
        while not self._verificar(END):
            if self._fim():
                self._erro("esperado 'end' para fechar o registro")
                return False
            inicio = self._estado.posicao
            if not self._verificar(ID):
                # Só um `ID` pode iniciar um campo; qualquer outro token significa
                # que o `record` foi esquecido.
                self._erro("esperado 'end' para fechar o registro")
                return False
            if not self._campo():
                self._sincronizar()
                if self._estado.posicao == inicio and not self._fim():
                    self._avancar()
                return False
        self._avancar()
        return True

    def _campo(self) -> bool:
        self._derivacao("campo")
        if not self._verificar(ID):
            self._erro("esperado o nome de um campo do registro")
            return False
        self._avancar()
        while self._aceitar(VIRGULA):
            if not self._esperar(ID, "o nome de um campo do registro"):
                return False
        if not self._esperar(DOIS_PONTOS, "':' antes do tipo do campo"):
            return False
        self._tipo()
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final da declaração do campo")
            return False
        self._avancar()
        return True

    def _declaracao_procedimento(self) -> None:
        self._derivacao("declProcedimento")
        self._declaracao_procedimento_simples()
        if self._verificar(PROCEDURE, FUNCTION):
            self._declaracao_procedimento()

    def _declaracao_procedimento_simples(self) -> bool:
        self._derivacao("declProc")
        eh_funcao = self._atual() == FUNCTION
        self._avancar()
        if not self._esperar(ID, "o nome do subprograma"):
            return False
        if self._aceitar(ABRE_PARENTESES):
            self._lista_parametros()
            self._esperar(FECHA_PARENTESES, "')'")
        elif not self._verificar(DOIS_PONTOS, PONTO_E_VIRGULA):
            # A lista de parâmetros é opcional: `procedure Q;` é válido.
            self._erro("esperado '(', ':' ou ';' após o nome do subprograma")
            return False
        if eh_funcao:
            if not self._esperar(DOIS_PONTOS, "':' antes do tipo de retorno"):
                return False
            self._tipo()
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final do cabeçalho do subprograma")
            return False
        self._avancar()
        if self._verificar(VAR):
            self._declaracao_variavel()
        if not self._verificar(BEGIN):
            self._erro("esperado 'begin' no corpo do subprograma")
            return False
        self._bloco()
        return True

    def _lista_parametros(self) -> None:
        self._derivacao("parametros")
        while self._verificar(ID):
            if not self._parametro():
                return

    def _parametro(self) -> bool:
        """Um parâmetro; em Pascal o separador `;` é facultativo antes do `)`."""
        self._derivacao("campo")
        if not self._esperar(ID, "o nome de um parâmetro"):
            return False
        while self._aceitar(VIRGULA):
            if not self._esperar(ID, "o nome de um parâmetro"):
                return False
        if not self._esperar(DOIS_PONTOS, "':' antes do tipo do parâmetro"):
            return False
        self._tipo()
        if self._aceitar(PONTO_E_VIRGULA) or self._verificar(FECHA_PARENTESES):
            return True
        self._erro("esperado ';' ou ')' ao final da declaração de parâmetro")
        return False

    def _bloco(self) -> None:
        self._derivacao("bloco")
        self._esperar(BEGIN, "'begin'")
        self._instrucoes()
        self._esperar(END, "'end'")
        self._esperar(PONTO_E_VIRGULA, "';'")

    def _instrucoes(self) -> None:
        self._derivacao("instrucoes")
        while not self._fim() and not self._verificar(END):
            inicio = self._estado.posicao
            if not self._verificar(*self._INICIO_DE_INST):
                self._erro(
                    f"esperado uma instrução, encontrado {self._descricao(self._atual())}"
                )
                self._sincronizar()
            elif not self._instrucao():
                self._sincronizar()
            if self._estado.posicao == inicio and not self._fim():
                # Um ponto de sincronização que não inicia instrução faria o laço
                # girar sem consumir nada; descarta-o para garantir progresso.
                self._avancar()

    _INICIO_DE_INST = (
        ID,
        BEGIN,
        IF,
        WHILE,
        REPEAT,
        FOR,
        BREAK,
        CONTINUE,
    )

    def _instrucao(self) -> bool:
        self._derivacao("inst")
        tipo = self._atual()
        if tipo == ID:
            return self._instrucao_identificador()
        if tipo == BEGIN:
            self._bloco()
            return True
        if tipo == IF:
            return self._instrucao_se()
        if tipo == WHILE:
            return self._instrucao_enquanto()
        if tipo == REPEAT:
            return self._instrucao_repita()
        if tipo == FOR:
            return self._instrucao_para()
        if tipo in (BREAK, CONTINUE):
            self._avancar()
            if not self._verificar(PONTO_E_VIRGULA):
                self._erro(f"esperado ';' após '{tipo.lower()}'")
                return False
            self._avancar()
            return True
        self._erro(f"instrução inválida: {self._descricao(tipo)}")
        return False

    def _sufixos_de_acesso(self) -> None:
        """Consome `indice[...]` e `.campo` encadeados após um identificador."""
        while True:
            if self._verificar(ABRE_COLCHETES):
                self._avancar()
                self._expr_op()
                self._esperar(FECHA_COLCHETES, "']'")
            elif self._verificar(PONTO):
                self._avancar()
                self._esperar(ID, "o nome do campo do registro")
            else:
                return

    def _instrucao_identificador(self) -> bool:
        nome = self._token_atual()
        self._avancar()
        self._sufixos_de_acesso()

        if self._verificar(ABRE_PARENTESES):
            self._avancar()
            self._argumentos()
            self._esperar(FECHA_PARENTESES, "')'")
            return self._encerra_instrucao()

        if self._verificar(ATRIBUICAO):
            self._avancar()
            self._expr()
            return self._encerra_instrucao()

        if self._verificar(PONTO_E_VIRGULA, END) or self._fim():
            if nome is not None and nome.lexema in self._subprogramas:
                # `Q;` onde Q é um procedimento declarado é uma chamada sem
                # argumentos, não uma instrução sem efeito.
                self._aceitar(PONTO_E_VIRGULA)
                return True
            self._avisar(
                f"instrução sem efeito: '{nome.lexema if nome else ''}' não altera nenhum valor",
                nome,
            )
            self._aceitar(PONTO_E_VIRGULA)
            return True

        self._erro(
            f"esperado ':=', '[', '(' ou ';' após '{nome.lexema if nome else ''}'"
        )
        return False

    def _encerra_instrucao(self) -> bool:
        if self._verificar(PONTO_E_VIRGULA):
            self._avancar()
            return True
        if self._verificar(ELSE):
            # Em `if C then S1 else S2`, o `;` pertence ao ramo `else`.
            return True
        self._erro("esperado ';' ao final da instrução")
        return False

    def _instrucao_se(self) -> bool:
        self._avancar()
        self._expr()
        self._esperar(THEN, "'then'")
        if not self._instrucao():
            return False
        if self._aceitar(ELSE):
            return self._instrucao()
        return True

    def _instrucao_enquanto(self) -> bool:
        self._avancar()
        self._expr()
        self._esperar(DO, "'do'")
        return self._instrucao()

    def _instrucao_repita(self) -> bool:
        self._avancar()
        if not self._instrucao():
            return False
        self._esperar(UNTIL, "'until'")
        self._expr()
        return self._encerra_instrucao()

    def _instrucao_para(self) -> bool:
        self._avancar()
        self._esperar(ID, "o nome da variável de controle")
        if not self._esperar(ATRIBUICAO, "':='"):
            return False
        self._expr()
        if not self._aceitar(TO, DOWNTO):
            self._erro("esperado 'to' ou 'downto' no laço 'for'")
            return False
        self._expr()
        self._esperar(DO, "'do'")
        return self._instrucao()

    def _argumentos(self) -> None:
        self._derivacao("parametros2")
        if not self._verificar(FECHA_PARENTESES):
            while True:
                self._expr()
                if not self._aceitar(VIRGULA):
                    break

    # --- Expressões -------------------------------------------------------

    def _expr(self) -> None:
        self._derivacao("expr")
        self._expr_comparacao()
        while self._verificar(OU, E):
            self._avancar()
            self._expr_comparacao()

    def _expr_comparacao(self) -> None:
        self._derivacao("exprComparacao")
        self._expr_op()
        while self._verificar(*COMPARADORES):
            self._avancar()
            self._expr_op()

    def _expr_op(self) -> None:
        self._derivacao("exprOp")
        self._termo()
        while self._verificar(*OPERADORES):
            self._avancar()
            self._termo()

    def _termo(self) -> None:
        self._derivacao("termo")
        self._unario()
        while self._verificar(MULTIPLICACAO, DIVISAO):
            self._avancar()
            self._unario()

    def _unario(self) -> None:
        self._derivacao("unario")
        if self._aceitar(*OPERADORES):
            return self._unario()
        self._fator()

    def _fator(self) -> None:
        self._derivacao("fator")
        if self._verificar(ABRE_PARENTESES):
            self._avancar()
            self._expr()
            self._esperar(FECHA_PARENTESES, "')'")
            return
        if self._verificar(NUM, LITERAL):
            self._avancar()
            return
        if self._verificar(ID):
            self._variavel()
            return
        self._erro(f"esperado uma expressão, encontrado {self._descricao(self._atual())}")
        self._sincronizar()

    def _variavel(self) -> None:
        self._derivacao("variavel")
        self._avancar()
        if self._verificar(ABRE_COLCHETES):
            self._avancar()
            self._expr_op()
            self._esperar(FECHA_COLCHETES, "']'")
        elif self._verificar(PONTO):
            # Acesso a campo de registro: `p.x`
            self._avancar()
            self._esperar(ID, "o nome do campo do registro")

    def _valor(self) -> None:
        self._derivacao("valor")
        if self._verificar(LITERAL):
            self._avancar()
            return
        self._unario()


def analisar(tokens: tuple[Token, ...], simbolos: tuple | None = None) -> ResultadoSintatico:
    """Analisa `tokens` e devolve erros, avisos e as derivações aplicadas."""
    return Parser(tokens, simbolos).analisar()


__all__ = [
    "DESCRICAO_DE_TOKEN",
    "FIM",
    "PONTOS_DE_SINCRONIZACAO",
    "Parser",
    "ResultadoSintatico",
    "analisar",
]