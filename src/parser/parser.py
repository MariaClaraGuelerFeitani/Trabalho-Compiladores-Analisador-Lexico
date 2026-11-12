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
from .ast import (
    No,
    NoAtribuicao,
    NoBinario,
    NoBloco,
    NoCampo,
    NoChamada,
    NoDeclaracaoConstante,
    NoDeclaracaoSubprograma,
    NoDeclaracaoTipo,
    NoDeclaracaoVariavel,
    NoDesvio,
    NoEnquanto,
    NoIndice,
    NoLiteral,
    NoNumero,
    NoPara,
    NoPrograma,
    NoRepita,
    NoSe,
    NoUnario,
    NoVariavel,
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

# `write`/`writeln` aceitam a formatação `expr : largura : precisao` do
# Pascal; `read`/`readln` não.
ESCRITA = ("write", "writeln")

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
    arvore: No | None = None

    @property
    def ok(self) -> bool:
        return not self.erros


@dataclass(frozen=True)
class ResultadoExpr:
    """Tipo inferido e nó da AST de uma expressão."""

    tipo: str = DESCONHECIDO
    no: No | None = None


@dataclass(frozen=True)
class Sufixo:
    """`[expr]` ou `.campo` aplicado a uma variável."""

    tipo: str
    token: Token | None = None
    indice: No | None = None


@dataclass(frozen=True)
class ResultadoAcesso:
    """Resultado de `id`, `id[expr]` ou `id.campo`, com o nó correspondente."""

    info: InfoAcesso
    no: No


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
        self._arvore: No | None = None

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
            self._arvore,
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
        token_nome = self._token_atual()
        self._esperar(ID, "o nome do programa")
        self._esperar(PONTO_E_VIRGULA)
        declaracoes = self._declaracoes()
        self._esperar(BEGIN, "'begin'")
        comandos = self._instrucoes()
        self._esperar(END, "'end'")
        self._esperar(PONTO, "'.'")
        self._arvore = NoPrograma(
            nome=token_nome.lexema if token_nome else "",
            declaracoes=declaracoes,
            comandos=comandos,
            linha=token_nome.linha if token_nome else 0,
            coluna=token_nome.coluna if token_nome else 0,
        )

    def _declaracoes(self) -> tuple[No, ...]:
        self._derivacao("declaracoes")
        declaracoes: list[No] = []
        while self._verificar(*INICIO_DE_DECLARACAO):
            if self._verificar(CONST):
                declaracoes.extend(self._declaracao_constante())
            elif self._verificar(VAR):
                declaracoes.extend(self._declaracao_variavel())
            elif self._verificar(TYPE):
                declaracoes.extend(self._declaracao_tipo())
            else:
                declaracoes.extend(self._declaracao_procedimento())
        return tuple(declaracoes)

    def _declaracao_constante(self) -> tuple[No, ...]:
        self._derivacao("declaracaoConstante")
        self._avancar()
        nos: list[No] = []
        while self._verificar(ID):
            no = self._declaracao_constante_simples()
            if no is None:
                self._sincronizar()
                return tuple(nos)
            nos.append(no)
        self._aceitar(PONTO_E_VIRGULA)
        return tuple(nos)

    def _declaracao_constante_simples(self) -> NoDeclaracaoConstante | None:
        self._derivacao("declConsList")
        if not self._verificar(ID):
            return None
        token_nome = self._token_atual()
        if not self._esperar(ID, "o nome de uma constante"):
            return None
        tipo_declarado = ""
        if self._aceitar(DOIS_PONTOS):
            tipo_declarado = self._tipo()
        if not self._verificar(IGUALDADE_COMPARACAO, ATRIBUICAO):
            self._erro("esperado '=' para o valor da constante")
            return None
        self._avancar()
        valor = self._valor()
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final da declaração de constante")
            return None
        self._avancar()
        if self._semantico is not None and token_nome is not None:
            self._semantico.declarar_constante(
                token_nome, tipo_declarado, valor.tipo
            )
        return NoDeclaracaoConstante(
            nome=token_nome.lexema if token_nome else "",
            valor=valor.no.rotulo() if valor.no is not None else "",
            linha=token_nome.linha if token_nome else 0,
            coluna=token_nome.coluna if token_nome else 0,
        )

    def _declaracao_variavel(self) -> tuple[No, ...]:
        self._derivacao("declaracaoVariavel")
        self._avancar()
        nos: list[No] = []
        while self._verificar(ID):
            no = self._declaracao_variavel_simples()
            if no is None:
                self._sincronizar()
                return tuple(nos)
            nos.append(no)
        self._aceitar(PONTO_E_VIRGULA)
        return tuple(nos)

    def _declaracao_variavel_simples(self) -> NoDeclaracaoVariavel | None:
        self._derivacao("declVar")
        nomes: list[Token] = []
        while True:
            token_nome = self._token_atual()
            if not self._esperar(ID, "o nome de uma variável"):
                return None
            if token_nome is not None:
                nomes.append(token_nome)
            if not self._aceitar(VIRGULA):
                break
        if not self._esperar(DOIS_PONTOS, "':' antes do tipo"):
            return None
        tipo = self._tipo()
        if self._semantico is not None and nomes:
            self._semantico.declarar_variaveis(tuple(nomes), tipo)
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final da declaração de variável")
            return None
        self._avancar()
        return self._no_declaracao_variavel(nomes, tipo)

    def _no_declaracao_variavel(
        self, nomes: list[Token], tipo: str
    ) -> NoDeclaracaoVariavel:
        primeiro = nomes[0] if nomes else None
        return NoDeclaracaoVariavel(
            nomes=tuple(token.lexema for token in nomes),
            tipo_declarado=tipo,
            linha=primeiro.linha if primeiro else 0,
            coluna=primeiro.coluna if primeiro else 0,
        )

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

    def _declaracao_tipo(self) -> tuple[No, ...]:
        self._derivacao("declaracaoTipo")
        self._avancar()
        nos: list[No] = []
        while self._verificar(ID):
            no = self._declaracao_tipo_simples()
            if no is None:
                self._sincronizar()
                return tuple(nos)
            nos.append(no)
        self._aceitar(PONTO_E_VIRGULA)
        return tuple(nos)

    def _declaracao_tipo_simples(self) -> NoDeclaracaoTipo | None:
        self._derivacao("declTipo")
        token_nome = self._token_atual()
        if not self._esperar(ID, "o nome de um tipo"):
            return None
        if not self._esperar(IGUALDADE_COMPARACAO, "'=' na declaração de tipo"):
            return None
        tipo_base = ""
        campos: tuple[tuple[str, str], ...] | None = None
        constantes: tuple[str, ...] | None = None
        if self._verificar(*TIPOS_PRIMARIOS):
            tipo_base = self._anterior().tipo if self._avancar() else ""
        elif self._verificar(ID):
            tipo_base = self._anterior().lexema if self._avancar() else ""
        elif self._verificar(ABRE_PARENTESES):
            constantes = self._lista_enumeracao()
            tipo_base = "enum"
            if constantes is None:
                return None
        elif self._verificar(RECORD):
            campos = self._corpo_registro()
            tipo_base = "record"
            if campos is None:
                return None
        elif self._verificar(ENUM):
            self._avancar()
            constantes = self._lista_enumeracao()
            tipo_base = "enum"
            if constantes is None:
                return None
        else:
            self._erro(
                "esperado um tipo, uma lista de enumeração ou 'record' na declaração de tipo"
            )
            return None
        if not self._verificar(PONTO_E_VIRGULA):
            self._erro("esperado ';' ao final da declaração de tipo")
            return None
        self._avancar()
        if self._semantico is not None and token_nome is not None:
            self._semantico.declarar_tipo(token_nome, tipo_base, campos, constantes)
        return NoDeclaracaoTipo(
            nome=token_nome.lexema if token_nome else "",
            tipo_declarado=tipo_base,
            linha=token_nome.linha if token_nome else 0,
            coluna=token_nome.coluna if token_nome else 0,
        )

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

    def _declaracao_procedimento(self) -> tuple[No, ...]:
        self._derivacao("declProcedimento")
        nos: list[No] = []
        while self._verificar(PROCEDURE, FUNCTION):
            inicio = self._estado.posicao
            no = self._declaracao_procedimento_simples()
            if no is not None:
                nos.append(no)
            if self._estado.posicao == inicio and not self._fim():
                # Cabeçalho malformado: evita repetir o mesmo token para sempre.
                self._sincronizar()
                if self._estado.posicao == inicio and not self._fim():
                    self._avancar()
            if not self._verificar(PROCEDURE, FUNCTION):
                break
        return tuple(nos)

    def _declaracao_procedimento_simples(self) -> NoDeclaracaoSubprograma | None:
        self._derivacao("declProc")
        eh_funcao = self._atual() == FUNCTION
        categoria = "funcao" if eh_funcao else "procedimento"
        self._avancar()
        token_nome = self._token_atual()
        if not self._esperar(ID, "o nome do subprograma"):
            return None
        parametros: tuple[tuple[str, str], ...] = ()
        if self._aceitar(ABRE_PARENTESES):
            parametros = self._lista_parametros()
            self._esperar(FECHA_PARENTESES, "')'")
        elif not self._verificar(DOIS_PONTOS, PONTO_E_VIRGULA):
            # A lista de parâmetros é opcional: `procedure Q;` é válido.
            self._erro("esperado '(', ':' ou ';' após o nome do subprograma")
            return None
        tipo_retorno = ""
        if eh_funcao:
            if not self._esperar(DOIS_PONTOS, "':' antes do tipo de retorno"):
                return None
            tipo_retorno = self._tipo()
        iniciado = self._semantico is not None and token_nome is not None
        if iniciado:
            self._semantico.abrir_subprograma(
                token_nome, eh_funcao, parametros, tipo_retorno
            )
        corpo: NoBloco | None = None
        declaracoes_locais: tuple[No, ...] = ()
        try:
            if not self._verificar(PONTO_E_VIRGULA):
                self._erro("esperado ';' ao final do cabeçalho do subprograma")
                return None
            self._avancar()
            if self._verificar(VAR):
                declaracoes_locais = self._declaracao_variavel()
            if not self._verificar(BEGIN):
                self._erro("esperado 'begin' no corpo do subprograma")
                return None
            corpo = self._bloco()
        finally:
            if iniciado:
                self._semantico.fechar_subprograma()
        linha = token_nome.linha if token_nome else 0
        coluna = token_nome.coluna if token_nome else 0
        nos_parametros = tuple(
            NoDeclaracaoVariavel(
                nomes=(nome,),
                tipo_declarado=tipo,
                linha=linha,
                coluna=coluna,
            )
            for nome, tipo in parametros
        )
        return NoDeclaracaoSubprograma(
            nome=token_nome.lexema if token_nome else "",
            categoria=categoria,
            parametros=nos_parametros,
            declaracoes=declaracoes_locais,
            corpo=corpo,
            linha=linha,
            coluna=coluna,
        )

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

    def _bloco(self, exigir_ponto_e_virgula: bool = True) -> NoBloco:
        self._derivacao("bloco")
        self._esperar(BEGIN, "'begin'")
        comandos = self._instrucoes()
        self._esperar(END, "'end'")
        if exigir_ponto_e_virgula:
            self._esperar(PONTO_E_VIRGULA, "';'")
        elif self._aceitar(PONTO_E_VIRGULA):
            pass
        elif not (self._verificar(*self._FIM_DE_BLOCO) or self._fim()):
            # O `;` só é dispensável quando o bloco é a última instrução.
            self._erro("esperado ';' após 'end'")
        return NoBloco(comandos=comandos)

    def _instrucoes(self) -> tuple[No, ...]:
        self._derivacao("instrucoes")
        comandos: list[No] = []
        while not self._fim() and not self._verificar(*self._FIM_DE_BLOCO):
            inicio = self._estado.posicao
            if not self._verificar(*self._INICIO_DE_INST):
                self._erro(
                    f"esperado uma instrução, encontrado {self._descricao(self._atual())}"
                )
                self._sincronizar()
            else:
                no = self._instrucao()
                if no is not None:
                    comandos.append(no)
                elif self._estado.posicao == inicio:
                    self._sincronizar()
            if self._estado.posicao == inicio and not self._fim():
                # Um ponto de sincronização que não inicia instrução faria o laço
                # girar sem consumir nada; descarta-o para garantir progresso.
                self._avancar()
        return tuple(comandos)

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

    def _instrucao(self) -> No | None:
        self._derivacao("inst")
        tipo = self._atual()
        if tipo == ID:
            return self._instrucao_identificador()
        if tipo == BEGIN:
            return self._bloco(exigir_ponto_e_virgula=False)
        if tipo == IF:
            return self._instrucao_se()
        if tipo == WHILE:
            return self._instrucao_enquanto()
        if tipo == REPEAT:
            return self._instrucao_repita()
        if tipo == FOR:
            return self._instrucao_para()
        if tipo in (BREAK, CONTINUE):
            token = self._avancar()
            if self._semantico is not None and token is not None:
                self._semantico.verificar_desvio(token, tipo.lower())
            if self._verificar(PONTO_E_VIRGULA):
                self._avancar()
            elif not (self._verificar(*self._FIM_DE_BLOCO) or self._fim()):
                self._erro(f"esperado ';' após '{tipo.lower()}'")
                return None
            return NoDesvio(
                comando=tipo.lower(),
                linha=token.linha if token else 0,
                coluna=token.coluna if token else 0,
            )
        self._erro(f"instrução inválida: {self._descricao(tipo)}")
        return None

    def _consumir_sufixos(self) -> list[Sufixo]:
        """Consome `indice[...]` e `.campo` encadeados; devolve os marcadores."""
        sufixos: list[Sufixo] = []
        while True:
            if self._verificar(ABRE_COLCHETES):
                marca = self._avancar()
                indice = self._expr_op()
                self._esperar(FECHA_COLCHETES, "']'")
                sufixos.append(Sufixo("indice", marca, indice.no))
            elif self._verificar(PONTO):
                self._avancar()
                campo = self._token_atual()
                self._esperar(ID, "o nome do campo do registro")
                sufixos.append(Sufixo("campo", campo))
            else:
                return sufixos

    def _aplicar_sufixo(self, info: InfoAcesso, sufixo: Sufixo) -> InfoAcesso:
        if self._semantico is None:
            return info
        if sufixo.tipo == "campo":
            return self._semantico.acesso_campo(info, sufixo.token)
        return self._semantico.acesso_indice(info, sufixo.token)

    def _no_com_sufixos(
        self, token_id: Token | None, sufixos: list[Sufixo]
    ) -> No:
        no: No = NoVariavel(
            nome=token_id.lexema if token_id else "",
            linha=token_id.linha if token_id else 0,
            coluna=token_id.coluna if token_id else 0,
        )
        for sufixo in sufixos:
            if sufixo.tipo == "campo":
                no = NoCampo(
                    base=no,
                    campo=sufixo.token.lexema if sufixo.token else "",
                    linha=sufixo.token.linha if sufixo.token else 0,
                    coluna=sufixo.token.coluna if sufixo.token else 0,
                )
            else:
                no = NoIndice(
                    base=no,
                    indice=sufixo.indice,
                    linha=sufixo.token.linha if sufixo.token else 0,
                    coluna=sufixo.token.coluna if sufixo.token else 0,
                )
        return no

    def _instrucao_identificador(self) -> No | None:
        token_id = self._token_atual()
        self._avancar()
        sufixos = self._consumir_sufixos()
        no_alvo = self._no_com_sufixos(token_id, sufixos)

        if self._verificar(ABRE_PARENTESES):
            self._avancar()
            formatar = token_id is not None and token_id.lexema.lower() in ESCRITA
            argumentos = self._argumentos(formatar=formatar)
            self._esperar(FECHA_PARENTESES, "')'")
            tipo_retorno = DESCONHECIDO
            if self._semantico is not None and token_id is not None:
                tipo_retorno = self._semantico.verificar_chamada(
                    token_id,
                    tuple(argumento.tipo for argumento in argumentos),
                    como_instrucao=True,
                )
            if not self._encerra_instrucao():
                return None
            return NoChamada(
                tipo=tipo_retorno,
                nome=token_id.lexema if token_id else "",
                argumentos=tuple(
                    argumento.no
                    for argumento in argumentos
                    if argumento.no is not None
                ),
                linha=token_id.linha if token_id else 0,
                coluna=token_id.coluna if token_id else 0,
            )

        if self._verificar(ATRIBUICAO):
            self._avancar()
            expressao = self._expr()
            if self._semantico is not None and token_id is not None:
                info = self._semantico.acesso(token_id, como_alvo=True)
                for sufixo in sufixos:
                    info = self._aplicar_sufixo(info, sufixo)
                self._semantico.verificar_atribuicao(info, expressao.tipo)
            if not self._encerra_instrucao():
                return None
            return NoAtribuicao(
                alvo=no_alvo,
                expressao=expressao.no,
                linha=token_id.linha if token_id else 0,
                coluna=token_id.coluna if token_id else 0,
            )

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
                return NoChamada(
                    nome=token_id.lexema if token_id else "",
                    linha=token_id.linha if token_id else 0,
                    coluna=token_id.coluna if token_id else 0,
                )
            self._avisar(
                f"instrução sem efeito: '{token_id.lexema if token_id else ''}' não altera nenhum valor",
                token_id,
            )
            self._aceitar(PONTO_E_VIRGULA)
            return no_alvo

        self._erro(
            f"esperado ':=', '[', '(' ou ';' após '{token_id.lexema if token_id else ''}'"
        )
        return None

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

    def _instrucao_se(self) -> No | None:
        token_se = self._avancar()
        token_condicao = self._token_atual()
        condicao = self._expr()
        self._verificar_condicao(condicao.tipo, token_condicao, "if")
        self._esperar(THEN, "'then'")
        entao = self._instrucao()
        senao = self._instrucao() if self._aceitar(ELSE) else None
        return NoSe(
            condicao=condicao.no,
            entao=entao,
            senao=senao,
            linha=token_se.linha if token_se else 0,
            coluna=token_se.coluna if token_se else 0,
        )

    def _instrucao_enquanto(self) -> No | None:
        token = self._avancar()
        token_condicao = self._token_atual()
        condicao = self._expr()
        self._verificar_condicao(condicao.tipo, token_condicao, "while")
        self._esperar(DO, "'do'")
        if self._semantico is not None:
            self._semantico.entrar_laco()
        try:
            corpo = self._instrucao()
        finally:
            if self._semantico is not None:
                self._semantico.sair_laco()
        return NoEnquanto(
            condicao=condicao.no,
            corpo=corpo,
            linha=token.linha if token else 0,
            coluna=token.coluna if token else 0,
        )

    def _instrucao_repita(self) -> No | None:
        token = self._avancar()
        # Lista de instruções como no Pascal padrão: o laço para em `until`
        # (`UNTIL` já está em `_FIM_DE_BLOCO`) e o `;` antes dele é facultativo.
        if self._semantico is not None:
            self._semantico.entrar_laco()
        try:
            corpo = self._instrucoes()
            self._esperar(UNTIL, "'until'")
            token_condicao = self._token_atual()
            condicao = self._expr()
            self._verificar_condicao(condicao.tipo, token_condicao, "until")
        finally:
            if self._semantico is not None:
                self._semantico.sair_laco()
        if not self._encerra_instrucao():
            return None
        return NoRepita(
            corpo=NoBloco(comandos=corpo),
            condicao=condicao.no,
            linha=token.linha if token else 0,
            coluna=token.coluna if token else 0,
        )

    def _instrucao_para(self) -> No | None:
        token = self._avancar()
        token_variavel = self._token_atual()
        if not self._esperar(ID, "o nome da variável de controle"):
            return None
        tipo_controle = DESCONHECIDO
        if self._semantico is not None and token_variavel is not None:
            tipo_controle = self._semantico.verificar_controle_de_for(token_variavel)
        if not self._esperar(ATRIBUICAO, "':='"):
            return None
        token_limite = self._token_atual()
        inicio = self._expr()
        self._verificar_limite_de_for(tipo_controle, inicio.tipo, token_limite)
        passo = "to"
        if self._aceitar(DOWNTO):
            passo = "downto"
        elif not self._aceitar(TO):
            self._erro("esperado 'to' ou 'downto' no laço 'for'")
            return None
        token_limite = self._token_atual()
        fim = self._expr()
        self._verificar_limite_de_for(tipo_controle, fim.tipo, token_limite)
        self._esperar(DO, "'do'")
        if self._semantico is not None:
            self._semantico.entrar_laco()
        try:
            corpo = self._instrucao()
        finally:
            if self._semantico is not None:
                self._semantico.sair_laco()
        return NoPara(
            variavel=token_variavel.lexema if token_variavel else "",
            inicio=inicio.no,
            fim=fim.no,
            passo=passo,
            corpo=corpo,
            linha=token.linha if token else 0,
            coluna=token.coluna if token else 0,
        )

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

    def _argumentos(self, formatar: bool = False) -> tuple[ResultadoExpr, ...]:
        """A lista de argumentos de uma chamada, com tipo e nó de cada um.

        Com `formatar=True` (chamadas de `write`/`writeln`) consome a
        formatação `expr : largura : precisao` após cada expressão.
        """
        self._derivacao("parametros2")
        if self._verificar(FECHA_PARENTESES):
            return ()
        argumentos: list[ResultadoExpr] = []
        while True:
            argumentos.append(self._expr())
            if formatar:
                self._consumir_formato_escrita()
            if not self._aceitar(VIRGULA):
                break
        return tuple(argumentos)

    def _consumir_formato_escrita(self) -> None:
        """`expr : NUM` ou `expr : NUM : NUM` do `write`; só valida os números."""
        if not self._verificar(DOIS_PONTOS):
            return
        self._avancar()
        if not self._verificar(NUM):
            self._erro("esperado a largura (um número) após ':'")
            return
        self._avancar()
        if not self._aceitar(DOIS_PONTOS):
            return
        if not self._verificar(NUM):
            self._erro("esperado a precisão (um número) após ':'")
            return
        self._avancar()

    # --- Expressões -------------------------------------------------------
    # Cada método devolve `ResultadoExpr` (tipo inferido + nó da AST), que os
    # ganchos semânticos usam nas checagens seguintes e a IDE usa na árvore.

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

    @staticmethod
    def _binario(
        esquerda: ResultadoExpr,
        direita: ResultadoExpr,
        operador: Token | None,
        tipo: str,
    ) -> ResultadoExpr:
        return ResultadoExpr(
            tipo,
            NoBinario(
                tipo=tipo,
                operador=operador.lexema if operador else "",
                esquerda=esquerda.no,
                direita=direita.no,
                linha=operador.linha if operador else 0,
                coluna=operador.coluna if operador else 0,
            ),
        )

    def _expr(self) -> ResultadoExpr:
        self._derivacao("expr")
        resultado = self._expr_e()
        while self._verificar(OU):
            operador = self._avancar()
            direita = self._expr_e()
            if self._semantico is not None and operador is not None:
                tipo = self._semantico.combinar_logico(
                    resultado.tipo, direita.tipo, operador
                )
            else:
                tipo = LOGICO
            resultado = self._binario(resultado, direita, operador, tipo)
        return resultado

    def _expr_e(self) -> ResultadoExpr:
        self._derivacao("exprE")
        resultado = self._expr_comparacao()
        while self._verificar(E):
            operador = self._avancar()
            direita = self._expr_comparacao()
            if self._semantico is not None and operador is not None:
                tipo = self._semantico.combinar_logico(
                    resultado.tipo, direita.tipo, operador
                )
            else:
                tipo = LOGICO
            resultado = self._binario(resultado, direita, operador, tipo)
        return resultado

    def _expr_comparacao(self) -> ResultadoExpr:
        self._derivacao("exprComparacao")
        resultado = self._expr_op()
        while self._verificar(*COMPARADORES):
            operador = self._avancar()
            direita = self._expr_op()
            if self._semantico is not None and operador is not None:
                tipo = self._semantico.comparar(
                    resultado.tipo, direita.tipo, operador
                )
            else:
                tipo = LOGICO
            resultado = self._binario(resultado, direita, operador, tipo)
        return resultado

    def _expr_op(self) -> ResultadoExpr:
        self._derivacao("exprOp")
        resultado = self._termo()
        while self._verificar(*OPERADORES):
            operador = self._avancar()
            direita = self._termo()
            tipo = self._combinar_aritmetico(
                resultado.tipo, direita.tipo, operador
            )
            resultado = self._binario(resultado, direita, operador, tipo)
        return resultado

    def _termo(self) -> ResultadoExpr:
        self._derivacao("termo")
        resultado = self._unario()
        while self._verificar(MULTIPLICACAO, DIVISAO, MOD, DIV):
            operador = self._avancar()
            direita = self._unario()
            tipo = self._combinar_aritmetico(
                resultado.tipo, direita.tipo, operador
            )
            resultado = self._binario(resultado, direita, operador, tipo)
        return resultado

    def _unario(self) -> ResultadoExpr:
        self._derivacao("unario")
        operador = self._token_atual()
        if self._aceitar(*OPERADORES):
            operando = self._unario()
            if self._semantico is not None and operador is not None:
                tipo = self._semantico.combinar_unario(operando.tipo, operador)
            else:
                tipo = resultado_aritmetico(INTEIRO, operando.tipo)
            return ResultadoExpr(
                tipo,
                NoUnario(
                    tipo=tipo,
                    operador=operador.lexema if operador else "",
                    operando=operando.no,
                    linha=operador.linha if operador else 0,
                    coluna=operador.coluna if operador else 0,
                ),
            )
        return self._fator()

    def _fator(self) -> ResultadoExpr:
        self._derivacao("fator")
        if self._verificar(ABRE_PARENTESES):
            self._avancar()
            resultado = self._expr()
            self._esperar(FECHA_PARENTESES, "')'")
            return resultado
        if self._verificar(NUM):
            token = self._avancar()
            tipo = (
                INTEIRO
                if token is not None and token.atributos == "inteiro"
                else REAL
            )
            return ResultadoExpr(
                tipo,
                NoNumero(
                    tipo=tipo,
                    valor=token.lexema if token else "",
                    linha=token.linha if token else 0,
                    coluna=token.coluna if token else 0,
                ),
            )
        if self._verificar(LITERAL):
            token = self._avancar()
            return ResultadoExpr(
                TIPO_STRING,
                NoLiteral(
                    tipo=TIPO_STRING,
                    valor=token.lexema if token else "",
                    linha=token.linha if token else 0,
                    coluna=token.coluna if token else 0,
                ),
            )
        if self._verificar(ID):
            self._derivacao("variavel")
            token_id = self._token_atual()
            acesso = self._acesso(token_id, como_alvo=False)
            tipo = acesso.info.tipo
            no = acesso.no
            chamou = False
            while self._verificar(ABRE_PARENTESES):
                # Chamada de função usada como operando: `x := dobro(n)`.
                self._derivacao("parametros2")
                self._avancar()
                argumentos = self._argumentos()
                self._esperar(FECHA_PARENTESES, "')'")
                chamou = True
                tipo = self._verificar_chamada(
                    token_id, tuple(arg.tipo for arg in argumentos)
                )
                no = NoChamada(
                    tipo=tipo,
                    nome=token_id.lexema if token_id else "",
                    argumentos=tuple(
                        arg.no for arg in argumentos if arg.no is not None
                    ),
                    linha=token_id.linha if token_id else 0,
                    coluna=token_id.coluna if token_id else 0,
                )
            if not chamou and self._semantico is not None and token_id is not None:
                tipo = self._semantico.uso_sem_argumentos(token_id, acesso.info)
            return ResultadoExpr(tipo, no)
        self._erro(f"esperado uma expressão, encontrado {self._descricao(self._atual())}")
        self._sincronizar()
        return ResultadoExpr(DESCONHECIDO, None)

    def _acesso(self, token_id: Token | None, como_alvo: bool) -> ResultadoAcesso:
        """Um `ID` com seus sufixos; infere o tipo e monta o nó do acesso."""
        if self._semantico is None or token_id is None:
            self._avancar()
            sufixos = self._consumir_sufixos()
            return ResultadoAcesso(
                InfoAcesso(Token(ID, "", 1, 1)),
                self._no_com_sufixos(token_id, sufixos),
            )
        info = self._semantico.acesso(token_id, como_alvo)
        self._avancar()
        sufixos = self._consumir_sufixos()
        for sufixo in sufixos:
            info = self._aplicar_sufixo(info, sufixo)
        return ResultadoAcesso(info, self._no_com_sufixos(token_id, sufixos))

    def _valor(self) -> ResultadoExpr:
        self._derivacao("valor")
        if self._verificar(LITERAL):
            token = self._avancar()
            return ResultadoExpr(
                TIPO_STRING,
                NoLiteral(
                    tipo=TIPO_STRING,
                    valor=token.lexema if token else "",
                    linha=token.linha if token else 0,
                    coluna=token.coluna if token else 0,
                ),
            )
        return self._unario()


def analisar(tokens: tuple[Token, ...], simbolos: tuple | None = None) -> ResultadoSintatico:
    """Analisa `tokens` e devolve erros, avisos, derivações e a AST."""
    return Parser(tokens, simbolos).analisar()


__all__ = [
    "DESCRICAO_DE_TOKEN",
    "FIM",
    "PONTOS_DE_SINCRONIZACAO",
    "Parser",
    "ResultadoAcesso",
    "ResultadoExpr",
    "ResultadoSintatico",
    "Sufixo",
    "analisar",
]