from __future__ import annotations

from ..config import MAX_IDENTIFIER_LENGTH
from ..services.lexer_service import AnalysisResult, LexicalError, Token, Warning
from . import dfa, error_recovery as recuperacao
from .models import SymbolTable
from .tokens import (
    ABRE_COLCHETES,
    ABRE_COMENTARIO_BLOCO,
    ABRE_COMENTARIO_PARENTESE,
    ABRE_PARENTESES,
    ATRIBUICAO,
    BEGIN,
    CONST,
    DOIS_PONTOS,
    END,
    FECHA_COLCHETES,
    FECHA_COMENTARIO_BLOCO,
    FECHA_COMENTARIO_PARENTESE,
    FECHA_PARENTESES,
    FUNCTION,
    ID,
    IGUALDADE_COMPARACAO,
    IGNORADOS,
    INTERVALO,
    LITERAL,
    MARCA_COMENTARIO_LINHA,
    NUM,
    PONTO_E_VIRGULA,
    PROCEDURE,
    PROGRAM,
    RECORD,
    SIMBOLOS,
    SUBTRACAO,
    TIPOS_PRIMARIOS,
    TOKEN_CLASSES,
    TYPE,
    VAR,
    VIRGULA,
)

CLASSES_DECLARACAO: dict[str, str] = {
    PROGRAM: "programa",
    PROCEDURE: "procedimento",
    FUNCTION: "funcao",
    CONST: "constante",
    VAR: "variavel",
    TYPE: "tipo",
}

INICIO_DE_VALOR: frozenset[str] = frozenset({ATRIBUICAO, IGUALDADE_COMPARACAO})

PROGRAMA_EXEMPLO = (
    "programa Ola;\n"
    "\n"
    "const\n"
    "  limite: integer := 10;\n"
    "\n"
    "var\n"
    "  contador: integer;\n"
    "  nome: string;\n"
    "  media: real;\n"
    "\n"
    "procedure mostrar;\n"
    "begin\n"
    "  contador := contador + 1;\n"
    "end;\n"
    "\n"
    "begin\n"
    "  nome := 'mundo';\n"
    "  // isto e um comentario\n"
    "  { tambem isto }\n"
    "  if contador <= limite e nome <> '' then\n"
    "    mostrar;\n"
    "end.\n"
)

# Exercita as extensões da parte 2: `for`, registro e enumeração.
PROGRAMA_EXTENSOES = (
    "programa Completo;\n"
    "\n"
    "type\n"
    "  cor = (vermelho, verde, azul);\n"
    "  dias = (segunda..sexta);\n"
    "  ponto = record\n"
    "            x, y: real;\n"
    "            rotulo: string;\n"
    "          end;\n"
    "\n"
    "const\n"
    "  passos: integer := 3;\n"
    "\n"
    "var\n"
    "  i: integer;\n"
    "  p: ponto;\n"
    "  c: cor;\n"
    "\n"
    "begin\n"
    "  c := verde;\n"
    "  for i := 1 to passos do\n"
    "  begin\n"
    "    p.x := p.x + 1.0;\n"
    "  end;\n"
    "  for i := passos downto 1 do\n"
    "    i := i - 1;\n"
    "end.\n"
)


class Lexer:
    """Analisador léxico do dialeto de Pascal descrito em `src/lexer/tokens.py`.

O reconhecimento usa máximo casamento sobre o autômato finito determinístico
    de `src/lexer/dfa.py`. Comentários e espaços em branco são descartados antes do
    autômato, por serem classes que não produzem token.
    """

    def __init__(self) -> None:
        self._fonte = ""
        self._posicao = 0
        self._linha = 1
        self._coluna = 1
        self._tokens: list[Token] = []
        self._erros: list[LexicalError] = []
        self._avisos: list[Warning] = []
        self._simbolos = SymbolTable()
        self._abertos: list[tuple[str, int, int]] = []

    def analyze(self, source: str) -> AnalysisResult:
        return self.analisar(source)

    def analisar(self, fonte: str) -> AnalysisResult:
        self._reiniciar(fonte)
        while not self._fim:
            if self._consumir_comentario() or self._consumir_espaco():
                continue
            self._consumir_lexema()
        self._encerrar_aberacoes()
        self._montar_tabela_de_simbolos()
        return AnalysisResult(
            tokens=tuple(self._tokens),
            errors=tuple(self._erros),
            warnings=tuple(self._avisos),
            symbols=self._simbolos.como_tupla(),
            token_classes=TOKEN_CLASSES,
            dfa_states=dfa.ESTADOS,
            dfa_transitions=dfa.TRANSICOES,
        )

    def tokens_de(self, fonte: str) -> tuple[tuple[str, str], ...]:
        return tuple((token.tipo, token.lexema) for token in self.analisar(fonte).tokens)

    def _reiniciar(self, fonte: str) -> None:
        self._fonte = fonte
        self._posicao = 0
        self._linha = 1
        self._coluna = 1
        self._tokens.clear()
        self._erros.clear()
        self._avisos.clear()
        self._simbolos = SymbolTable()
        self._abertos.clear()

    @property
    def _fim(self) -> bool:
        return self._posicao >= len(self._fonte)

    @property
    def _atual(self) -> str:
        return self._fonte[self._posicao]

    def _avancar(self) -> None:
        caractere = self._fonte[self._posicao]
        self._posicao += 1
        if caractere == "\n":
            self._linha += 1
            self._coluna = 1
        else:
            self._coluna += 1

    def _voltar_para(self, posicao: int, linha: int, coluna: int) -> None:
        self._posicao = posicao
        self._linha = linha
        self._coluna = coluna

    def _lexema_mais_longo(self) -> str:
        for lexema, _ in SIMBOLOS:
            if self._fonte.startswith(lexema, self._posicao):
                return lexema
        return ""

    def _consumir_espaco(self) -> bool:
        if self._atual not in IGNORADOS:
            return False
        while not self._fim and self._atual in IGNORADOS:
            self._avancar()
        return True

    def _consumir_comentario(self) -> bool:
        if self._fonte.startswith(MARCA_COMENTARIO_LINHA, self._posicao):
            while not self._fim and self._atual != "\n":
                self._avancar()
            return True
        if self._fonte.startswith(ABRE_COMENTARIO_BLOCO, self._posicao):
            self._consumir_bloco(ABRE_COMENTARIO_BLOCO, FECHA_COMENTARIO_BLOCO)
            return True
        if self._fonte.startswith(ABRE_COMENTARIO_PARENTESE, self._posicao):
            self._consumir_bloco(ABRE_COMENTARIO_PARENTESE, FECHA_COMENTARIO_PARENTESE)
            return True
        return False

    def _consumir_bloco(self, abertura: str, fechamento: str) -> None:
        linha, coluna = self._linha, self._coluna
        profundidade = 0
        while not self._fim:
            if self._fonte.startswith(abertura, self._posicao):
                profundidade += 1
                self._consumir_delimitador(abertura)
                continue
            if self._fonte.startswith(fechamento, self._posicao):
                profundidade -= 1
                self._consumir_delimitador(fechamento)
                if profundidade == 0:
                    return
                continue
            self._avancar()
        self._erros.append(
            recuperacao.criar_erro(
                linha,
                coluna,
                f"comentário iniciado em {abertura!r} não foi fechado",
                abertura,
                len(abertura),
            )
        )

    def _consumir_delimitador(self, delimitador: str) -> None:
        for _ in delimitador:
            if self._fim:
                return
            self._avancar()

    def _consumir_lexema(self) -> None:
        linha, coluna = self._linha, self._coluna
        inicio = self._posicao
        estado = dfa.ESTADO_INICIAL
        aceito: tuple[str, str, int, int, int] | None = None
        desclassificado = False

        while True:
            if self._fim:
                if self._desclassificar(estado, aceito, desclassificado, inicio, linha, coluna):
                    desclassificado = True
                    estado = dfa.ESTADO_IDENTIFICADOR
                    continue
                break
            lexema = self._lexema_mais_longo() if estado == dfa.ESTADO_INICIAL else ""
            simbolo = dfa.simbolo_lido(estado, self._atual, lexema)
            destino = dfa.delta(estado, simbolo)
            if destino is None:
                if self._desclassificar(estado, aceito, desclassificado, inicio, linha, coluna):
                    desclassificado = True
                    estado = dfa.ESTADO_IDENTIFICADOR
                    continue
                break
            estado = destino
            self._avancar()
            if estado in dfa.ACEITACAO:
                aceito = (
                    dfa.ACEITACAO[estado],
                    self._fonte[inicio : self._posicao],
                    self._posicao,
                    self._linha,
                    self._coluna,
                )

        if aceito is None:
            self._recuperar(inicio, linha, coluna)
            return

        tipo, lexema, fim, linha_final, coluna_final = aceito
        self._voltar_para(fim, linha_final, coluna_final)
        self._validar(tipo, lexema, linha, coluna)
        self._emitir(tipo, lexema, linha, coluna)

    def _desclassificar(
        self,
        estado: str,
        aceito: tuple[str, str, int, int, int] | None,
        ja_desclassificado: bool,
        inicio: int,
        linha: int,
        coluna: int,
    ) -> bool:
        """Abandona o ramo de palavra reservada e relê o lexema como identificador."""
        if ja_desclassificado or aceito is not None:
            return False
        if estado not in dfa.ESTADOS_PALAVRA:
            return False
        self._voltar_para(inicio, linha, coluna)
        return True

    def _recuperar(self, inicio: int, linha: int, coluna: int) -> None:
        if self._posicao == inicio:
            self._erros.append(recuperacao.criar_erro_de_caractere(linha, coluna, self._atual))
            self._avancar()
            return
        self._erros.append(
            recuperacao.criar_erro(
                linha,
                coluna,
                "lexema incompleto ou não reconhecido",
                self._fonte[inicio : self._posicao],
                self._posicao - inicio,
            )
        )
        self._voltar_para(*self._sincronizar(self._posicao, self._linha, self._coluna))

    def _sincronizar(self, posicao: int, linha: int, coluna: int) -> tuple[int, int, int]:
        return recuperacao.sincronizar_fonte(self._fonte, posicao, linha, coluna)

    def _validar(self, tipo: str, lexema: str, linha: int, coluna: int) -> None:
        if tipo == ID and len(lexema) > MAX_IDENTIFIER_LENGTH:
            self._erros.append(
                recuperacao.criar_erro(
                    linha,
                    coluna,
                    f"identificador com {len(lexema)} caracteres, o limite é {MAX_IDENTIFIER_LENGTH}",
                    lexema,
                    len(lexema),
                )
            )
        elif tipo == ABRE_PARENTESES:
            self._abertos.append((ABRE_PARENTESES, lexema, linha, coluna))
        elif tipo == ABRE_COLCHETES:
            self._abertos.append((ABRE_COLCHETES, lexema, linha, coluna))
        elif tipo in (FECHA_PARENTESES, FECHA_COLCHETES):
            self._fechar(tipo, lexema, linha, coluna)

    def _fechar(self, tipo: str, lexema: str, linha: int, coluna: int) -> None:
        if not self._abertos:
            self._erros.append(
                recuperacao.criar_erro(linha, coluna, recuperacao.mensagem_de_fechamento(lexema), lexema)
            )
            return
        abertura, _, _, _ = self._abertos.pop()
        if (abertura, tipo) in (
            (ABRE_PARENTESES, FECHA_PARENTESES),
            (ABRE_COLCHETES, FECHA_COLCHETES),
        ):
            return
        self._erros.append(
            recuperacao.criar_erro(linha, coluna, recuperacao.mensagem_de_fechamento(lexema), lexema)
        )

    def _encerrar_aberacoes(self) -> None:
        while self._abertos:
            _, lexema, linha, coluna = self._abertos.pop()
            self._erros.append(
                recuperacao.criar_erro(
                    linha,
                    coluna,
                    f"'{lexema}' não foi fechado antes do fim do arquivo",
                    lexema,
                )
            )

    def _emitir(self, tipo: str, lexema: str, linha: int, coluna: int) -> None:
        self._tokens.append(Token(tipo, lexema, linha, coluna, self._atributos(tipo, lexema)))

    def _atributos(self, tipo: str, lexema: str) -> str:
        if tipo == NUM:
            return "real" if "." in lexema else "inteiro"
        if tipo == LITERAL:
            return f"{len(lexema) - 2} caracteres"
        return ""

    def _montar_tabela_de_simbolos(self) -> None:
        tokens = self._tokens
        secao = ""
        profundidade = 0
        indice = 0
        while indice < len(tokens):
            tipo = tokens[indice].tipo
            if tipo in CLASSES_DECLARACAO:
                indice, secao = self._declarar_cabecalho(tokens, indice, secao)
                continue
            if tipo == ABRE_PARENTESES:
                profundidade += 1
            elif tipo == FECHA_PARENTESES:
                profundidade = max(0, profundidade - 1)
            elif tipo == BEGIN:
                secao = ""
            elif tipo == ID and secao == "tipo":
                indice = self._declarar_tipo(tokens, indice)
                continue
            elif tipo == ID and secao and self._e_declaracao(tokens, indice):
                classe = "parametro" if profundidade and secao == "parametros" else secao
                indice = self._declarar_lista(tokens, indice, classe)
                continue
            indice += 1

    def _nome_do_tipo(self, tokens: tuple[Token, ...], indice: int) -> str:
        """Nome do tipo em `indice`: primário (`INTEGER`) ou definido pelo usuário (`Ponto`)."""
        if indice >= len(tokens):
            return ""
        token = tokens[indice]
        if token.tipo in TIPOS_PRIMARIOS:
            return token.tipo
        return token.lexema if token.tipo == ID else ""

    def _declarar_tipo(self, tokens: tuple[Token, ...], indice: int) -> int:
        nome = tokens[indice]
        cursor = indice + 1
        if cursor >= len(tokens) or tokens[cursor].tipo != IGUALDADE_COMPARACAO:
            return indice + 1
        cursor += 1
        if cursor >= len(tokens):
            return cursor
        if tokens[cursor].tipo in TIPOS_PRIMARIOS:
            self._registrar(nome, "tipo", tokens[cursor].tipo)
            return self._consumir_ate(tokens, cursor + 1, PONTO_E_VIRGULA)
        if tokens[cursor].tipo == ABRE_PARENTESES:
            self._registrar(nome, "tipo_enumeracao")
            return self._declarar_enumeracao(tokens, cursor)
        if tokens[cursor].tipo == RECORD:
            self._registrar(nome, "tipo_registro")
            return self._declarar_registro(tokens, cursor)
        alvo = self._nome_do_tipo(tokens, cursor)
        if alvo:
            self._registrar(nome, "tipo", alvo)
            return self._consumir_ate(tokens, cursor + 1, PONTO_E_VIRGULA)
        return cursor

    def _declarar_enumeracao(self, tokens: tuple[Token, ...], indice: int) -> int:
        cursor = indice + 1
        while cursor < len(tokens) and tokens[cursor].tipo != FECHA_PARENTESES:
            if tokens[cursor].tipo != ID:
                break
            self._registrar(tokens[cursor], "constante_enumeracao")
            cursor += 1
            if cursor < len(tokens) and tokens[cursor].tipo == INTERVALO:
                cursor = self._pular_ate_numero(tokens, cursor + 1)
            if cursor < len(tokens) and tokens[cursor].tipo == VIRGULA:
                cursor += 1
                continue
            break
        return self._consumir_ate(tokens, cursor, PONTO_E_VIRGULA)

    def _pular_ate_numero(self, tokens: tuple[Token, ...], indice: int) -> int:
        cursor = indice
        while cursor < len(tokens) and tokens[cursor].tipo in (SUBTRACAO, NUM):
            cursor += 1
        return cursor

    def _declarar_registro(self, tokens: tuple[Token, ...], indice: int) -> int:
        cursor = indice + 1
        while cursor < len(tokens) and tokens[cursor].tipo != END:
            if tokens[cursor].tipo != ID:
                cursor += 1
                continue
            primeiro = tokens[cursor]
            nomes = [primeiro.lexema]
            cursor += 1
            while (
                cursor + 1 < len(tokens)
                and tokens[cursor].tipo == VIRGULA
                and tokens[cursor + 1].tipo == ID
            ):
                nomes.append(tokens[cursor + 1].lexema)
                cursor += 2
            tipo = ""
            if cursor < len(tokens) and tokens[cursor].tipo == DOIS_PONTOS:
                cursor += 1
                tipo = self._nome_do_tipo(tokens, cursor)
                if tipo:
                    cursor += 1
            if cursor < len(tokens) and tokens[cursor].tipo == PONTO_E_VIRGULA:
                cursor += 1
            for nome in nomes:
                self._registrar(Token(ID, nome, primeiro.linha, primeiro.coluna), "campo", tipo)
        return cursor + 1 if cursor < len(tokens) else cursor

    def _consumir_ate(self, tokens: tuple[Token, ...], indice: int, alvo: str) -> int:
        cursor = indice
        while cursor < len(tokens) and tokens[cursor].tipo != alvo:
            cursor += 1
        return cursor + 1 if cursor < len(tokens) else cursor

    def _declarar_cabecalho(
        self, tokens: tuple[Token, ...], indice: int, secao: str
    ) -> tuple[int, str]:
        tipo = tokens[indice].tipo
        if tipo not in (PROGRAM, PROCEDURE, FUNCTION):
            return indice + 1, CLASSES_DECLARACAO[tipo]
        if indice + 1 >= len(tokens) or tokens[indice + 1].tipo != ID:
            return indice + 1, secao
        nome = tokens[indice + 1]
        retorno = self._tipo_de_retorno(tokens, indice + 2) if tipo == FUNCTION else ""
        self._registrar(nome, CLASSES_DECLARACAO[tipo], retorno)
        return indice + 2, "" if tipo == PROGRAM else "parametros"

    def _tipo_de_retorno(self, tokens: tuple[Token, ...], inicio: int) -> str:
        cursor = inicio
        while cursor < len(tokens):
            tipo = tokens[cursor].tipo
            if tipo == DOIS_PONTOS:
                return self._nome_do_tipo(tokens, cursor + 1)
            if tipo in (PONTO_E_VIRGULA, BEGIN):
                return ""
            cursor += 1
        return ""

    def _e_declaracao(self, tokens: tuple[Token, ...], indice: int) -> bool:
        cursor = indice + 1
        while cursor < len(tokens) and tokens[cursor].tipo == VIRGULA:
            cursor += 2
        if cursor >= len(tokens):
            return False
        return tokens[cursor].tipo in (
            DOIS_PONTOS,
            ATRIBUICAO,
            IGUALDADE_COMPARACAO,
            PONTO_E_VIRGULA,
        )

    def _declarar_lista(self, tokens: tuple[Token, ...], indice: int, classe: str) -> int:
        linha = tokens[indice].linha
        coluna = tokens[indice].coluna
        nomes = [tokens[indice].lexema]
        cursor = indice + 1
        while cursor < len(tokens) and tokens[cursor].tipo == VIRGULA:
            if cursor + 1 >= len(tokens) or tokens[cursor + 1].tipo != ID:
                break
            nomes.append(tokens[cursor + 1].lexema)
            cursor += 2
        tipo = ""
        valor = ""
        if cursor < len(tokens) and tokens[cursor].tipo == DOIS_PONTOS:
            cursor += 1
            tipo = self._nome_do_tipo(tokens, cursor)
            if tipo:
                cursor += 1
        if cursor < len(tokens) and tokens[cursor].tipo in INICIO_DE_VALOR:
            cursor += 1
            if cursor < len(tokens):
                valor = tokens[cursor].lexema
                cursor += 1
        if cursor < len(tokens) and tokens[cursor].tipo == PONTO_E_VIRGULA:
            cursor += 1
        for nome in nomes:
            self._registrar(Token(ID, nome, linha, coluna), classe, tipo, valor)
        return cursor

    def _registrar(self, token: Token, classe: str, tipo: str = "", valor: str = "") -> None:
        anterior = self._simbolos.declarar(token.lexema, classe, tipo, valor, token.linha)
        if anterior is not None:
            self._avisos.append(
                Warning(
                    token.linha,
                    token.coluna,
                    f"'{token.lexema}' já declarado na linha {anterior.line} como {anterior.kind}",
                )
            )


__all__ = ["Lexer", "PROGRAMA_EXEMPLO", "PROGRAMA_EXTENSOES"]