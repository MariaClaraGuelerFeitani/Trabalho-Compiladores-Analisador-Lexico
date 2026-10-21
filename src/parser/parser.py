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

A **análise semântica** da etapa 2 é feita por um `AnaliseSemantica`
injetado: o parser chama seus ganchos (declarações, atribuições, chamadas,
controle do `for` e inferência de tipos das expressões) à medida que cada
construção é reconhecida. Os erros semânticos são coletados pelo próprio
módulo `src/semantic/` e só entram no resultado final quando não há erro
sintático.
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
from ..semantic.semantico import AnaliseSemantica, InfoAcesso
from ..semantic.tipos import (
    DESCONHECIDO,
    INTEIRO,
    LOGICO,
    TIPO_STRING,
    resultado_aritmetico,
)
from ..services.lexer_service import LexicalError, Token, Warning

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
    MOD: "'mod'",
    DIV: "'div'",
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
    """Analisador sintático por descida recursiva sobre a gramática do Anexo I.

Quando um `AnaliseSemantica` é injetado, o parser chama seus ganchos durante a
    análise (declarações, atribuições, chamadas, expressões); sem esse objeto,
    a descida continua funcionando apenas com a checagem sintática, devolvendo
    tipos desconhecidos nas expressões.
    """

    def __init__(
        self,
        tokens: tuple[Token, ...],
        simbolos: tuple | None = None,
        semantico: AnaliseSemantica | None = None,
    ) -> None:
        self._tokens = tokens
        self._estado = _Estado()
        self._semantico = semantico
        self._subprogramas = {
            simbolo.identifier
            for simbolo in (simbolos or ())
            if simbolo.kind in ("procedimento", "funcao")
        }

    def analisar(self) -> ResultadoSintatico:
        self._estado = _Estado()
        if self._semantico is not None:
            self._semantico.programa_iniciar()
        try:
            self._programa()
            if not self._fim() and not self._estado.erros:
                self._erro(
                    f"token inesperado após o fim do programa: "
                    f"{self._descricao(self._atual())}"
                )
        finally:
            if self._semantico is not None:
                self._semantico.programa_encerrar()
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
        token_nome = self._token_atual()
        if not self._esperar(ID, "o nome de uma constante"):
            return False
        tipo_declarado = ""
        if self._aceitar(DOIS_PONTOS):
            tipo_declarado = self._tipo()
        if not self._verificar(IGUALDADE_COMPARACAO, ATRIBUICAO):
            self._erro("esperado '=' para o valor da constante")
            return False
        self._avancar()
        tipo_valor = self._valor()
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final da declaração de constante")
            return False
        self._avancar()
        if self._semantico is not None and token_nome is not None:
            self._semantico.declarar_constante(token_nome, tipo_declarado, tipo_valor)
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
        nomes: list[Token] = []
        while True:
            token_nome = self._token_atual()
            if not self._esperar(ID, "o nome de uma variável"):
                return False
            if token_nome is not None:
                nomes.append(token_nome)
            if not self._aceitar(VIRGULA):
                break
        if not self._esperar(DOIS_PONTOS, "':' antes do tipo"):
            return False
        tipo = self._tipo()
        if self._semantico is not None and nomes:
            self._semantico.declarar_variaveis(tuple(nomes), tipo)
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
        token_nome = self._token_atual()
        if not self._esperar(ID, "o nome de um tipo"):
            return False
        if not self._esperar(IGUALDADE_COMPARACAO, "'=' na declaração de tipo"):
            return False
        tipo_base = ""
        campos: tuple[tuple[str, str], ...] | None = None
        constantes: tuple[str, ...] | None = None
        if self._verificar(*TIPOS_PRIMARIOS):
            tipo_base = self._anterior().tipo if self._avancar() else ""
        elif self._verificar(ID):
            tipo_base = self._anterior().lexema if self._avancar() else ""
        elif self._verificar(ABRE_PARENTESES):
            constantes = self._lista_enumeracao()
            if constantes is None:
                return False
        elif self._verificar(RECORD):
            campos = self._corpo_registro()
            if campos is None:
                return False
        elif self._verificar(ENUM):
            self._avancar()
            constantes = self._lista_enumeracao()
            if constantes is None:
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
        if self._semantico is not None and token_nome is not None:
            self._semantico.declarar_tipo(token_nome, tipo_base, campos, constantes)
        return True

    def _lista_enumeracao(self) -> tuple[str, ...] | None:
        """Uma enumeração entre parênteses; devolve os nomes declarados."""
        self._derivacao("listaEnum")
        self._avancar()
        if not self._verificar(ID):
            self._erro("esperado o nome de uma constante de enumeração")
            self._sincronizar()
            return None
        nomes: list[str] = []
        while self._verificar(ID):
            token = self._avancar()
            if token is not None:
                nomes.append(token.lexema)
            if self._aceitar(INTERVALO):
                if not self._verificar(NUM, ID):
                    self._erro("esperado um número ou identificador para o fim do intervalo")
                    self._sincronizar()
                    return None
                fim = self._avancar()
                if fim is not None and fim.tipo == ID:
                    # As duas pontas do intervalo viram constantes do tipo.
                    nomes.append(fim.lexema)
            if not self._aceitar(VIRGULA):
                break
        if not self._verificar(FECHA_PARENTESES):
            self._erro("esperado ')' para fechar a enumeração")
            self._sincronizar()
            return None
        self._avancar()
        return tuple(nomes)

    def _corpo_registro(self) -> tuple[tuple[str, str], ...] | None:
        """O corpo `record ... end`; devolve pares (campo, tipo)."""
        self._derivacao("campos")
        self._avancar()
        campos: list[tuple[str, str]] = []
        while not self._verificar(END):
            if self._fim():
                self._erro("esperado 'end' para fechar o registro")
                return None
            inicio = self._estado.posicao
            if not self._verificar(ID):
                # Só um `ID` pode iniciar um campo; qualquer outro token significa
                # que o `record` foi esquecido.
                self._erro("esperado 'end' para fechar o registro")
                return None
            declaracao = self._campo()
            if declaracao is None:
                self._sincronizar()
                if self._estado.posicao == inicio and not self._fim():
                    self._avancar()
                return None
            campos.extend(declaracao)
        self._avancar()
        return tuple(campos)

    def _campo(self) -> tuple[tuple[str, str], ...] | None:
        self._derivacao("campo")
        if not self._verificar(ID):
            self._erro("esperado o nome de um campo do registro")
            return None
        token = self._avancar()
        nomes = [token.lexema] if token is not None else []
        while self._aceitar(VIRGULA):
            if not self._esperar(ID, "o nome de um campo do registro"):
                return None
            nomes.append(self._anterior().lexema)
        if not self._esperar(DOIS_PONTOS, "':' antes do tipo do campo"):
            return None
        tipo = self._tipo()
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final da declaração do campo")
            return None
        self._avancar()
        return tuple((nome, tipo) for nome in nomes)

    def _declaracao_procedimento(self) -> None:
        self._derivacao("declProcedimento")
        self._declaracao_procedimento_simples()
        if self._verificar(PROCEDURE, FUNCTION):
            self._declaracao_procedimento()

    def _declaracao_procedimento_simples(self) -> bool:
        self._derivacao("declProc")
        eh_funcao = self._atual() == FUNCTION
        self._avancar()
        token_nome = self._token_atual()
        if not self._esperar(ID, "o nome do subprograma"):
            return False
        parametros: tuple[tuple[str, str], ...] = ()
        if self._aceitar(ABRE_PARENTESES):
            parametros = self._lista_parametros()
            self._esperar(FECHA_PARENTESES, "')'")
        elif not self._verificar(DOIS_PONTOS, PONTO_E_VIRGULA):
            # A lista de parâmetros é opcional: `procedure Q;` é válido.
            self._erro("esperado '(', ':' ou ';' após o nome do subprograma")
            return False
        tipo_retorno = ""
        if eh_funcao:
            if not self._esperar(DOIS_PONTOS, "':' antes do tipo de retorno"):
                return False
            tipo_retorno = self._tipo()
        iniciado = self._semantico is not None and token_nome is not None
        if iniciado:
            self._semantico.abrir_subprograma(
                token_nome, eh_funcao, parametros, tipo_retorno
            )
        try:
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
        finally:
            if iniciado:
                self._semantico.fechar_subprograma()

    def _lista_parametros(self) -> tuple[tuple[str, str], ...]:
        """A lista completa entre parênteses; `;` separa grupos de parâmetros."""
        self._derivacao("parametros")
        parametros: list[tuple[str, str]] = []
        while self._verificar(ID):
            grupo = self._parametro()
            if grupo is None:
                break
            parametros.extend(grupo)
        return tuple(parametros)

    def _parametro(self) -> tuple[tuple[str, str], ...] | None:
        """Um parâmetro; em Pascal o separador `;` é facultativo antes do `)`."""
        self._derivacao("campo")
        if not self._esperar(ID, "o nome de um parâmetro"):
            return None
        nomes = [self._anterior().lexema]
        while self._aceitar(VIRGULA):
            if not self._esperar(ID, "o nome de um parâmetro"):
                return None
            nomes.append(self._anterior().lexema)
        if not self._esperar(DOIS_PONTOS, "':' antes do tipo do parâmetro"):
            return None
        tipo = self._tipo()
        if self._aceitar(PONTO_E_VIRGULA) or self._verificar(FECHA_PARENTESES):
            return tuple((nome, tipo) for nome in nomes)
        self._erro("esperado ';' ou ')' ao final da declaração de parâmetro")
        return None

    def _bloco(self) -> None:
        self._derivacao("bloco")
        self._esperar(BEGIN, "'begin'")
        self._instrucoes()
        self._esperar(END, "'end'")
        self._esperar(PONTO_E_VIRGULA, "';'")

    def _instrucoes(self) -> None:
        self._derivacao("instrucoes")
        while not self._fim() and not self._verificar(*self._FIM_DE_BLOCO):
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

    # Tokens que encerram uma sequência de instruções sem exigir `;` final.
    _FIM_DE_BLOCO = (END, UNTIL, ELSE, PONTO)

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
            if self._verificar(PONTO_E_VIRGULA):
                self._avancar()
                return True
            if self._verificar(*self._FIM_DE_BLOCO) or self._fim():
                return True
            self._erro(f"esperado ';' após '{tipo.lower()}'")
            return False
        self._erro(f"instrução inválida: {self._descricao(tipo)}")
        return False

    def _consumir_sufixos(self) -> list[tuple[str, Token | None]]:
        """Consome `indice[...]` e `.campo` encadeados; devolve os marcadores."""
        sufixos: list[tuple[str, Token | None]] = []
        while True:
            if self._verificar(ABRE_COLCHETES):
                marca = self._avancar()
                self._expr_op()
                self._esperar(FECHA_COLCHETES, "']'")
                sufixos.append(("indice", marca))
            elif self._verificar(PONTO):
                self._avancar()
                campo = self._token_atual()
                self._esperar(ID, "o nome do campo do registro")
                sufixos.append(("campo", campo))
            else:
                return sufixos

    def _aplicar_sufixo(
        self, info: InfoAcesso, tipo_sufixo: str, token: Token | None
    ) -> InfoAcesso:
        if self._semantico is None:
            return info
        if tipo_sufixo == "campo":
            return self._semantico.acesso_campo(info, token)
        return self._semantico.acesso_indice(info, token)

    def _instrucao_identificador(self) -> bool:
        token_id = self._token_atual()
        self._avancar()
        sufixos = self._consumir_sufixos()

        if self._verificar(ABRE_PARENTESES):
            self._avancar()
            tipos_argumentos = self._argumentos()
            self._esperar(FECHA_PARENTESES, "')'")
            if self._semantico is not None and token_id is not None:
                self._semantico.verificar_chamada(
                    token_id, tipos_argumentos, como_instrucao=True
                )
            return self._encerra_instrucao()

        if self._verificar(ATRIBUICAO):
            self._avancar()
            tipo_expr = self._expr()
            if self._semantico is not None and token_id is not None:
                info = self._semantico.acesso(token_id, como_alvo=True)
                for tipo_sufixo, token_sufixo in sufixos:
                    info = self._aplicar_sufixo(info, tipo_sufixo, token_sufixo)
                self._semantico.verificar_atribuicao(info, tipo_expr)
            return self._encerra_instrucao()

        if self._verificar(PONTO_E_VIRGULA, END) or self._fim():
            chamada = None
            if self._semantico is not None and token_id is not None:
                # `Q;` onde Q é um procedimento declarado é uma chamada sem
                # argumentos, não uma instrução sem efeito.
                chamada = self._semantico.instrucao_isolada(token_id)
            elif token_id is not None and token_id.lexema in self._subprogramas:
                chamada = True
            if chamada:
                self._aceitar(PONTO_E_VIRGULA)
                return True
            self._avisar(
                f"instrução sem efeito: '{token_id.lexema if token_id else ''}' não altera nenhum valor",
                token_id,
            )
            self._aceitar(PONTO_E_VIRGULA)
            return True

        self._erro(
            f"esperado ':=', '[', '(' ou ';' após '{token_id.lexema if token_id else ''}'"
        )
        return False

    def _encerra_instrucao(self) -> bool:
        if self._verificar(PONTO_E_VIRGULA):
            self._avancar()
            return True
        if self._verificar(*self._FIM_DE_BLOCO) or self._fim():
            # O `;` é facultativo na última instrução de um bloco (`S1; S2 end.`)
            # e antes do `until`; no ramo `if C then S1 else S2` o `;` pertence
            # ao `else`.
            return True
        self._erro("esperado ';' ao final da instrução")
        return False

    def _instrucao_se(self) -> bool:
        self._avancar()
        token_condicao = self._token_atual()
        tipo_condicao = self._expr()
        self._verificar_condicao(tipo_condicao, token_condicao, "if")
        self._esperar(THEN, "'then'")
        if not self._instrucao():
            return False
        if self._aceitar(ELSE):
            return self._instrucao()
        return True

    def _instrucao_enquanto(self) -> bool:
        self._avancar()
        token_condicao = self._token_atual()
        tipo_condicao = self._expr()
        self._verificar_condicao(tipo_condicao, token_condicao, "while")
        self._esperar(DO, "'do'")
        return self._instrucao()

    def _instrucao_repita(self) -> bool:
        self._avancar()
        # Lista de instruções como no Pascal padrão: o laço para em `until`
        # (`UNTIL` já está em `_FIM_DE_BLOCO`) e o `;` antes dele é facultativo.
        self._instrucoes()
        self._esperar(UNTIL, "'until'")
        token_condicao = self._token_atual()
        tipo_condicao = self._expr()
        self._verificar_condicao(tipo_condicao, token_condicao, "until")
        return self._encerra_instrucao()

    def _instrucao_para(self) -> bool:
        self._avancar()
        token_variavel = self._token_atual()
        if not self._esperar(ID, "o nome da variável de controle"):
            return False
        tipo_controle = DESCONHECIDO
        if self._semantico is not None and token_variavel is not None:
            tipo_controle = self._semantico.verificar_controle_de_for(token_variavel)
        if not self._esperar(ATRIBUICAO, "':='"):
            return False
        token_limite = self._token_atual()
        tipo_inicial = self._expr()
        self._verificar_limite_de_for(tipo_controle, tipo_inicial, token_limite)
        if not self._aceitar(TO, DOWNTO):
            self._erro("esperado 'to' ou 'downto' no laço 'for'")
            return False
        token_limite = self._token_atual()
        tipo_final = self._expr()
        self._verificar_limite_de_for(tipo_controle, tipo_final, token_limite)
        self._esperar(DO, "'do'")
        return self._instrucao()

    def _verificar_condicao(
        self, tipo: str, token: Token | None, comando: str
    ) -> None:
        if self._semantico is not None:
            self._semantico.verificar_condicao(tipo, token, comando)

    def _verificar_limite_de_for(
        self, tipo_controle: str, tipo_limite: str, token: Token | None
    ) -> None:
        if self._semantico is not None:
            self._semantico.verificar_limite_de_for(tipo_controle, tipo_limite, token)

    def _verificar_chamada(self, token: Token | None, tipos_argumentos: tuple[str, ...]) -> str:
        if self._semantico is None or token is None:
            return DESCONHECIDO
        return self._semantico.verificar_chamada(token, tipos_argumentos)

    def _argumentos(self) -> tuple[str, ...]:
        """A lista de argumentos de uma chamada; devolve o tipo de cada um."""
        self._derivacao("parametros2")
        if self._verificar(FECHA_PARENTESES):
            return ()
        tipos: list[str] = []
        while True:
            tipos.append(self._expr())
            if not self._aceitar(VIRGULA):
                break
        return tuple(tipos)

    # --- Expressões -------------------------------------------------------
    # Cada método devolve o tipo inferido da expressão (`""` quando
    # desconhecido), que os ganchos semânticos usam nas checagens seguintes.

    def _combinar_aritmetico(self, esquerda: str, direita: str, operador: Token | None) -> str:
        if self._semantico is not None and operador is not None:
            return self._semantico.combinar_aritmetico(esquerda, direita, operador)
        resultado = resultado_aritmetico(esquerda, direita)
        if resultado and operador is not None and operador.tipo == DIVISAO:
            return REAL
        if operador is not None and operador.tipo in (MOD, DIV):
            # `mod` e `div` só operam entre inteiros (Pascal padrão).
            return resultado if resultado == INTEIRO else DESCONHECIDO
        return resultado

    def _expr(self) -> str:
        self._derivacao("expr")
        tipo = self._expr_comparacao()
        while self._verificar(OU, E):
            operador = self._avancar()
            direita = self._expr_comparacao()
            if self._semantico is not None and operador is not None:
                tipo = self._semantico.combinar_logico(tipo, direita, operador)
            else:
                tipo = LOGICO
        return tipo

    def _expr_comparacao(self) -> str:
        self._derivacao("exprComparacao")
        tipo = self._expr_op()
        while self._verificar(*COMPARADORES):
            operador = self._avancar()
            direita = self._expr_op()
            if self._semantico is not None and operador is not None:
                tipo = self._semantico.comparar(tipo, direita, operador)
            else:
                tipo = LOGICO
        return tipo

    def _expr_op(self) -> str:
        self._derivacao("exprOp")
        tipo = self._termo()
        while self._verificar(*OPERADORES):
            operador = self._avancar()
            direita = self._termo()
            tipo = self._combinar_aritmetico(tipo, direita, operador)
        return tipo

    def _termo(self) -> str:
        self._derivacao("termo")
        tipo = self._unario()
        while self._verificar(MULTIPLICACAO, DIVISAO, MOD, DIV):
            operador = self._avancar()
            direita = self._unario()
            tipo = self._combinar_aritmetico(tipo, direita, operador)
        return tipo

    def _unario(self) -> str:
        self._derivacao("unario")
        operador = self._token_atual()
        if self._aceitar(*OPERADORES):
            tipo = self._unario()
            if self._semantico is not None and operador is not None:
                return self._semantico.combinar_unario(tipo, operador)
            return resultado_aritmetico(INTEIRO, tipo)
        return self._fator()

    def _fator(self) -> str:
        self._derivacao("fator")
        if self._verificar(ABRE_PARENTESES):
            self._avancar()
            tipo = self._expr()
            self._esperar(FECHA_PARENTESES, "')'")
            return tipo
        if self._verificar(NUM):
            token = self._avancar()
            if token is not None and token.atributos == "inteiro":
                return INTEIRO
            return REAL
        if self._verificar(LITERAL):
            self._avancar()
            return TIPO_STRING
        if self._verificar(ID):
            self._derivacao("variavel")
            token_id = self._token_atual()
            info = self._acesso(token_id, como_alvo=False)
            tipo = info.tipo
            chamou = False
            while self._verificar(ABRE_PARENTESES):
                # Chamada de função usada como operando: `x := dobro(n)`.
                self._derivacao("parametros2")
                self._avancar()
                tipos_argumentos = self._argumentos()
                self._esperar(FECHA_PARENTESES, "')'")
                chamou = True
                tipo = self._verificar_chamada(token_id, tipos_argumentos)
            if not chamou and self._semantico is not None and token_id is not None:
                tipo = self._semantico.uso_sem_argumentos(token_id, info)
            return tipo
        self._erro(f"esperado uma expressão, encontrado {self._descricao(self._atual())}")
        self._sincronizar()
        return DESCONHECIDO

    def _acesso(self, token_id: Token | None, como_alvo: bool) -> InfoAcesso:
        """Um `ID` com seus sufixos; infere o tipo final do acesso."""
        if self._semantico is None or token_id is None:
            self._avancar()
            self._consumir_sufixos()
            return InfoAcesso(Token(ID, "", 1, 1))
        info = self._semantico.acesso(token_id, como_alvo)
        self._avancar()
        for tipo_sufixo, token_sufixo in self._consumir_sufixos():
            info = self._aplicar_sufixo(info, tipo_sufixo, token_sufixo)
        return info

    def _valor(self) -> str:
        self._derivacao("valor")
        if self._verificar(LITERAL):
            self._avancar()
            return TIPO_STRING
        return self._unario()


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