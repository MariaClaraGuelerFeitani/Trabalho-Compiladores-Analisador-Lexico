"""Prelúdio C emitido antes de todo código traduzido.

O tradutor concatena estas linhas logo após os `#include` e antes das
typedefs. As funções auxiliares resolvem as diferenças entre Pascal e C:

- `gx_concat` devolve um de uma rodagem de buffers estáticos, permitindo
  `a + b` sobre `string` sem alocação dinâmica;
- `gx_char_para_str` e `gx_str_para_char` cobrem a convolução char/string que
  a análise semântica aceita nos dois sentidos;
- `gx_consumir_linha` descarta o restante da linha depois de um `readln`,
  copiando o comportamento do Pascal.

As strings da linguagem são arrays de `GX_TAM_STRING` caracteres; leituras
usam `%255s` para nunca estourar o buffer.
"""

from __future__ import annotations

PRELUDIO_LINHAS: tuple[str, ...] = (
    "#define GX_TAM_STRING 256",
    "",
    "static char gx_bufs[8][GX_TAM_STRING];",
    "static int gx_buf_atual = 0;",
    "",
    "static char* gx_proximo_buffer(void) {",
    "\tchar* b = gx_bufs[gx_buf_atual];",
    "\tgx_buf_atual = (gx_buf_atual + 1) % 8;",
    "\treturn b;",
    "}",
    "",
    "static char* gx_concat(const char* a, const char* b) {",
    "\tchar* saida = gx_proximo_buffer();",
    '\tsnprintf(saida, GX_TAM_STRING, "%s%s", a, b);',
    "\treturn saida;",
    "}",
    "",
    "static char* gx_char_para_str(char c) {",
    "\tchar* saida = gx_proximo_buffer();",
    "\tsaida[0] = c;",
    "\tsaida[1] = '\\0';",
    "\treturn saida;",
    "}",
    "",
    "static char gx_str_para_char(const char* s) {",
    "\treturn s ? s[0] : '\\0';",
    "}",
    "",
    "static void gx_consumir_linha(void) {",
    "\tint ch;",
    "\twhile ((ch = getchar()) != '\\n' && ch != EOF) { }",
    "}",
)

__all__ = ["PRELUDIO_LINHAS"]
