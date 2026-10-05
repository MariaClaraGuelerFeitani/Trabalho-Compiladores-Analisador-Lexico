"""Gera a tabela de tokens do relatorio a partir do codigo do analisador lexico.

As expressoes regulares, as palavras reservadas e os simbolos vem de
`src/lexer/tokens.py`; a coluna de atributos vem de `Lexer._atributos`, o mesmo
metodo que a interface usa para preencher a aba *Tokens*. Por isso a tabela do
relatorio nao consegue divergir do comportamento real do programa.

    python tools/gerar_tabela_tokens.py             # imprime a tabela
    python tools/gerar_tabela_tokens.py --write     # reescreve a secao do relatorio
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.lexer import tokens  # noqa: E402
from src.lexer.lexer import Lexer  # noqa: E402

RELATORIO = RAIZ / "relatorio" / "relatorio.md"
MARKER_INICIO = "<!-- tabela-tokens:inicio -->"
MARKER_FIM = "<!-- tabela-tokens:fim -->"

CABECALHO = (
    "| Token | Lexema | Expressao regular | Atributo | Valor |\n"
    "| --- | --- | --- | --- | --- |\n"
)

VAZIO = ""


def celula(texto: str) -> str:
    """Escapa o que quebraria a coluna de um markdown."""
    return texto.replace("|", "\\|")


def celula_codigo(texto: str) -> str:
    """Vazio vira `-`; o resto vai entre crases, para as col ficarem iguais."""
    return f"`{texto}`" if texto else "-"


def celula_regex(regexes: list[str]) -> str:
    return " ou ".join(f"`{celula(regex)}`" for regex in regexes)


def expressoes_por_tipo() -> dict[str, list[str]]:
    tabela: dict[str, list[str]] = {}
    for classe in tokens.TOKEN_CLASSES:
        tabela.setdefault(classe.tipo, []).append(classe.regex)
    return tabela


def valor_de(tipo: str, lexema: str) -> str:
    """Valor semantico que o token carrega para as fases seguintes."""
    if tipo == tokens.LITERAL:
        return lexema[1:-1].replace("''", "'")
    if tipo in (tokens.ID, tokens.NUM):
        return lexema
    return VAZIO


# `Lexer._atributos` e privado por estar interno ao scanner, mas e ele que preenche
# a coluna `atributos` de cada `Token`. Reusar o metodo, em vez de reimplementar a
# regra aqui, e o que garante que a tabela do relatorio bate com a aba *Tokens*.
atributos_de = Lexer()._atributos


def linha(tipo: str, lexema: str, regexes: list[str], atributo: str, valor: str) -> str:
    return (
        f"| `{tipo}` | `{lexema}` | {celula_regex(regexes)} "
        f"| {celula_codigo(atributo)} | {celula_codigo(valor)} |\n"
    )


def secao_variaveis(regexes: dict[str, list[str]]) -> str:
    """As tres classes de variaveis, com um exemplo por valor possivel do atributo."""
    texto = ""
    # `007` mostra para que serve o atributo: o valor e 7, nao o lexema.
    for tipo, lexema in ((tokens.ID, "contador"), (tokens.NUM, "007"), (tokens.NUM, "3.14")):
        atributo = atributos_de(tipo, lexema)
        valor = str(int(lexema)) if tipo == tokens.NUM and atributo == "inteiro" else valor_de(tipo, lexema)
        texto += linha(tipo, lexema, regexes[tipo], atributo, valor)
    lexema = "'d''art'"
    texto += linha(
        tokens.LITERAL,
        lexema,
        regexes[tokens.LITERAL],
        atributos_de(tokens.LITERAL, lexema),
        valor_de(tokens.LITERAL, lexema),
    )
    return texto


def secao_reservadas(regexes: dict[str, list[str]]) -> str:
    lexemas: dict[str, list[str]] = {}
    for palavra, tipo in tokens.PALAVRAS_RESERVADAS.items():
        lexemas.setdefault(tipo, []).append(palavra)
    texto = ""
    for tipo, palavras in lexemas.items():
        joined = ", ".join(f"`{p}`" for p in palavras)
        texto += f"| `{tipo}` | {joined} | {celula_regex(regexes[tipo])} | - | - |\n"
    return texto


def secao_simbolos(regexes: dict[str, list[str]]) -> str:
    texto = ""
    for lexema, tipo in tokens.SIMBOLOS:
        texto += linha(tipo, lexema, regexes[tipo], VAZIO, VAZIO)
    return texto


def secao_descartados() -> str:
    """O que o scanner reconhece e joga fora antes de chegar ao automato."""
    return (
        "| Constructo | Inicio | Fim | Observacao |\n"
        "| --- | --- | --- | --- |\n"
"| `espaco`, `\\t`, `\\r`, `\\n`, `\\v`, `\\f` | - | - | "
        "`Lexer._consumir_espaco` (`src/lexer/lexer.py`) |\n"
        f"| `{tokens.MARCA_COMENTARIO_LINHA}` | `{tokens.MARCA_COMENTARIO_LINHA}` | fim da linha | "
        "`Lexer._consumir_comentario` |\n"
        "| `{ ... }` | `{` | `}` | aninhamento permitido |\n"
        "| `(* ... *)` | `(*` | `*)` | aninhamento permitido |\n"
    )


def gerar() -> str:
    regexes = expressoes_por_tipo()
    total = len({c.tipo for c in tokens.TOKEN_CLASSES})

    texto = (
        f"Um token por tipo reconhecido: {total} tipos, {len(tokens.TOKEN_CLASSES)} entradas "
        "em `TokenClass`, porque `program` e `programa` sao o mesmo token `PROGRAM`.\n\n"
        "A coluna **Expressao regular** reproduz literalmente o que a aba *Classes de "
        "tokens* da IDE mostra. As palavras reservadas vem com o prefixo `(?i)`, que e o "
        "jeito de escrever *case-insensitive* em regex. Os simbolos aparecem escapados "
        "(`+` como `\\+`) porque e o que `re.escape` devolve.\n\n"
        "Somente `ID`, `NUM` e `LITERAL` carregam atributo; palavra reservada e simbolo "
        "nao tem valor semantico. O par **Atributo** / **Valor** e o que o analisador "
        "sintatico usa para saber se `007` vale zero ou sete, e se `'d''art'` contem um "
        "ou dois apostrofos.\n\n"
        "### 11.1 Classes de variaveis\n\n"
        f"{CABECALHO}{secao_variaveis(regexes)}\n"
        f"### 11.2 Palavras reservadas ({len(set(tokens.PALAVRAS_RESERVADAS.values()))} tokens, "
        f"{len(tokens.PALAVRAS_RESERVADAS)} grafias)\n\n"
        f"{CABECALHO}{secao_reservadas(regexes)}\n"
        f"### 11.3 Simbolos ({len(tokens.SIMBOLOS)})\n\n"
        f"{CABECALHO}{secao_simbolos(regexes)}\n"
        "### 11.4 Reconhecidos sem produzir token\n\n"
        "Estes construcoes sao consumidas e descartadas antes do automato, porque nao "
        "pertencem a nenhuma classe de lexema:\n\n"
        f"{secao_descartados()}"
    )
    return texto


def reescrever_relatorio(tabela: str) -> bool:
    if not RELATORIO.is_file():
        print(f"ERRO: relatorio nao encontrado em {RELATORIO}", file=sys.stderr)
        return False
    texto = RELATORIO.read_text(encoding="utf-8")
    if MARKER_INICIO not in texto or MARKER_FIM not in texto:
        print(f"ERRO: marcadores ausentes em {RELATORIO}", file=sys.stderr)
        return False
    inicio = texto.index(MARKER_INICIO) + len(MARKER_INICIO)
    fim = texto.index(MARKER_FIM)
    RELATORIO.write_text(f"{texto[:inicio]}\n{tabela}\n{texto[fim:]}", encoding="utf-8")
    return True


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analisador.add_argument("--write", action="store_true", help="atualiza relatorio/relatorio.md")
    opcoes = analisador.parse_args()

    tabela = gerar()
    if opcoes.write:
        if not reescrever_relatorio(tabela):
            return 1
        print(f"{RELATORIO.name}: secao 11 atualizada")
        return 0
    sys.stdout.write(tabela)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())