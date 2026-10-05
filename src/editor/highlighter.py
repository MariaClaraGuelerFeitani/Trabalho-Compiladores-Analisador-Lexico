from __future__ import annotations

from collections.abc import Iterable, Mapping

from PySide6.QtGui import (
    QColor,
    QFont,
    QPalette,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)

from ..lexer.tokens import (
    ABRE_COMENTARIO_BLOCO,
    ABRE_COMENTARIO_PARENTESE,
    FECHA_COMENTARIO_BLOCO,
    FECHA_COMENTARIO_PARENTESE,
    LITERAL,
    MARCA_COMENTARIO_LINHA,
    NUM,
    PALAVRAS_RESERVADAS,
    TIPOS_PRIMARIOS,
)

CATEGORY_KEYWORD = "palavra_reservada"
CATEGORY_TYPE = "tipo_primario"
CATEGORY_NUMBER = "numero"
CATEGORY_LITERAL = "literal"
CATEGORY_COMMENT = "comentario"

CATEGORIES: tuple[str, ...] = (
    CATEGORY_KEYWORD,
    CATEGORY_TYPE,
    CATEGORY_NUMBER,
    CATEGORY_LITERAL,
    CATEGORY_COMMENT,
)

CATEGORY_LABELS: dict[str, str] = {
    CATEGORY_KEYWORD: "Palavra reservada",
    CATEGORY_TYPE: "Tipo primário",
    CATEGORY_NUMBER: "Número",
    CATEGORY_LITERAL: "Literal",
    CATEGORY_COMMENT: "Comentário",
}

PREFERENCE_FIELDS: dict[str, str] = {
    CATEGORY_KEYWORD: "keyword_color",
    CATEGORY_TYPE: "primitive_type_color",
    CATEGORY_NUMBER: "number_color",
    CATEGORY_LITERAL: "literal_color",
    CATEGORY_COMMENT: "comment_color",
}

CATEGORY_BY_TOKEN: dict[str, str] = {
    **{tipo: CATEGORY_KEYWORD for tipo in PALAVRAS_RESERVADAS.values()},
    **{tipo: CATEGORY_TYPE for tipo in TIPOS_PRIMARIOS},
    NUM: CATEGORY_NUMBER,
    LITERAL: CATEGORY_LITERAL,
}

DARK_COLORS: dict[str, str] = {
    CATEGORY_KEYWORD: "#569cd6",
    CATEGORY_TYPE: "#4ec9b0",
    CATEGORY_NUMBER: "#d7ba7d",
    CATEGORY_LITERAL: "#ce9178",
    CATEGORY_COMMENT: "#7ca668",
}

LIGHT_COLORS: dict[str, str] = {
    CATEGORY_KEYWORD: "#0b5cad",
    CATEGORY_TYPE: "#0f7b7b",
    CATEGORY_NUMBER: "#a05000",
    CATEGORY_LITERAL: "#a31515",
    CATEGORY_COMMENT: "#5a8a4a",
}

FREE_STATE = 0


def category_of(token_type: str) -> str:
    return CATEGORY_BY_TOKEN.get(token_type, "")


def default_colors(palette: QPalette) -> dict[str, QColor]:
    claro = palette.color(QPalette.ColorRole.Base).lightness() >= 128
    tabela = LIGHT_COLORS if claro else DARK_COLORS
    return {categoria: QColor(tabela[categoria]) for categoria in CATEGORIES}


def resolve_colors(
    overrides: Mapping[str, QColor], palette: QPalette
) -> dict[str, QColor]:
    cores = default_colors(palette)
    for categoria, cor in overrides.items():
        if categoria in cores and cor.isValid():
            cores[categoria] = QColor(cor)
    return cores


def _encode_state(depth: int, parenteses: bool) -> int:
    if depth <= 0:
        return FREE_STATE
    return depth * 2 + (1 if parenteses else 0)


def _decode_state(state: int) -> tuple[int, bool]:
    if state <= FREE_STATE:
        return 0, False
    return state // 2, bool(state % 2)


class TokenHighlighter(QSyntaxHighlighter):

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._cores: dict[str, QColor] = {}
        self._formatos: dict[str, QTextCharFormat] = {}
        self._tokens_por_linha: dict[int, list[tuple[int, int, str]]] = {}

    def set_colors(self, cores: dict[str, QColor]) -> None:
        self._cores = dict(cores)
        self._formatos = {
            categoria: self._build_format(categoria) for categoria in self._cores
        }
        self._repintar()

    def set_tokens(self, tokens: Iterable) -> None:
        por_linha: dict[int, list[tuple[int, int, str]]] = {}
        for token in tokens:
            categoria = category_of(token.tipo)
            if categoria:
                por_linha.setdefault(token.linha, []).append(
                    (token.coluna - 1, len(token.lexema), categoria)
                )
        self._tokens_por_linha = por_linha
        self._repintar()

    def _repintar(self) -> None:
        documento = self.document()
        bloqueado = documento.blockSignals(True)
        try:
            self.rehighlight()
        finally:
            documento.blockSignals(bloqueado)

    def colors(self) -> dict[str, QColor]:
        return {categoria: QColor(cor) for categoria, cor in self._cores.items()}

    def _build_format(self, categoria: str) -> QTextCharFormat:
        formato = QTextCharFormat()
        cor = self._cores.get(categoria)
        if cor is not None and cor.isValid():
            formato.setForeground(cor)
        if categoria == CATEGORY_KEYWORD:
            formato.setFontWeight(QFont.Weight.Bold)
        elif categoria == CATEGORY_COMMENT:
            formato.setFontItalic(True)
        return formato

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - nome imposto pelo Qt
        comentarios: list[tuple[int, int]] = []
        profundidade, parenteses = _decode_state(self.previousBlockState())
        profundidade, parenteses = self._scan(
            text, comentarios, profundidade, parenteses
        )
        self.setCurrentBlockState(_encode_state(profundidade, parenteses))

        for inicio, tamanho, categoria in self._tokens_por_linha.get(
            self.currentBlock().blockNumber() + 1, ()
        ):
            formato = self._formatos.get(categoria)
            if formato is None or tamanho < 1 or inicio < 0:
                continue
            if inicio + tamanho > len(text):
                continue
            self.setFormat(inicio, tamanho, formato)

        formato_comentario = self._formatos.get(CATEGORY_COMMENT)
        if formato_comentario is not None:
            for inicio, tamanho in comentarios:
                self.setFormat(inicio, tamanho, formato_comentario)

    def _scan(
        self,
        text: str,
        comentarios: list[tuple[int, int]],
        profundidade: int,
        parenteses: bool,
    ) -> tuple[int, bool]:
        cursor = 0
        tamanho = len(text)
        while cursor < tamanho:
            if profundidade == 0:
                abertura = self._abertura_em(text, cursor)
                if abertura == "":
                    cursor += 1
                    continue
                if abertura == MARCA_COMENTARIO_LINHA:
                    comentarios.append((cursor, tamanho - cursor))
                    break
                comentarios.append((cursor, len(abertura)))
                cursor += len(abertura)
                profundidade = 1
                parenteses = abertura == ABRE_COMENTARIO_PARENTESE
                continue
            cursor, profundidade = self._consumir_corpo(
                text, cursor, profundidade, parenteses, comentarios
            )
        return profundidade, parenteses

    @staticmethod
    def _abertura_em(text: str, cursor: int) -> str:
        for marca in (
            MARCA_COMENTARIO_LINHA,
            ABRE_COMENTARIO_PARENTESE,
            ABRE_COMENTARIO_BLOCO,
        ):
            if text.startswith(marca, cursor):
                return marca
        return ""

    @staticmethod
    def _consumir_corpo(
        text: str,
        inicio: int,
        profundidade: int,
        parenteses: bool,
        comentarios: list[tuple[int, int]],
    ) -> tuple[int, int]:
        abertura, fechamento = (
            (ABRE_COMENTARIO_PARENTESE, FECHA_COMENTARIO_PARENTESE)
            if parenteses
            else (ABRE_COMENTARIO_BLOCO, FECHA_COMENTARIO_BLOCO)
        )
        cursor = inicio
        tamanho = len(text)
        while cursor < tamanho:
            if text.startswith(fechamento, cursor):
                cursor += len(fechamento)
                profundidade -= 1
                comentarios.append((inicio, cursor - inicio))
                if profundidade == 0:
                    return cursor, 0
                continue
            if text.startswith(abertura, cursor):
                profundidade += 1
                cursor += len(abertura)
                continue
            cursor += 1
        comentarios.append((inicio, tamanho - inicio))
        return tamanho, profundidade


__all__ = [
    "CATEGORIES",
    "CATEGORY_BY_TOKEN",
    "CATEGORY_COMMENT",
    "CATEGORY_KEYWORD",
    "CATEGORY_LABELS",
    "CATEGORY_LITERAL",
    "CATEGORY_NUMBER",
    "CATEGORY_TYPE",
    "DARK_COLORS",
    "LIGHT_COLORS",
    "PREFERENCE_FIELDS",
    "TokenHighlighter",
    "category_of",
    "default_colors",
    "resolve_colors",
]
