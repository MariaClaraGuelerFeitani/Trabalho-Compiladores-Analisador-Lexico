"""Testes da geração de executável: tradutor Pascal->C e TCC embutido.

Os testes sem `app` cobrem a tradução linha a linha; os de integração
(skipados quando o TCC está ausente) compilam com o `tools/tcc/tcc.exe`
real e rodam o binário, comparando a saída.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.app import build_lexer
from src.codegen import (
    ErroDeTraducao,
    compilador,
    compilar,
    literal_para_c,
    mangle,
    tcc_disponivel,
    traduzir,
)
from src.lexer import Lexer

RAIZ = Path(__file__).resolve().parent.parent
VALIDO = RAIZ / "relatorio" / "casos_de_teste" / "valido.pas"

requer_tcc = pytest.mark.skipif(
    not tcc_disponivel(), reason="TCC embutido ausente em tools/tcc"
)

requer_windows = pytest.mark.skipif(
    sys.platform != "win32", reason="a cadeia com pause roda no cmd do Windows"
)


def traduzir_fonte(fonte: str) -> str:
    resultado = Lexer().analyze(fonte)
    assert not resultado.errors, resultado.errors
    return traduzir(resultado.tokens)


# --- Tradução -----------------------------------------------------------------


def test_programa_minimo_vira_main_com_declarações() -> None:
    codigo = traduzir_fonte(
        "programa Ola;\nvar x: integer;\nbegin\nx := 1;\nend.\n"
    )
    assert "#include <stdio.h>" in codigo
    assert "int gx_x;" in codigo
    assert "gx_x = 1;" in codigo
    assert codigo.count("int main(void)") == 1
    assert "return 0;" in codigo


def test_constante_vira_define_e_e_usada() -> None:
    codigo = traduzir_fonte(
        "programa C;\nconst maximo = 10;\nvar x: integer;\n"
        "begin\nx := maximo;\nend.\n"
    )
    assert "#define gx_maximo (10)" in codigo
    assert "gx_x = gx_maximo;" in codigo


def test_constante_com_aspas_duplas_escapadas() -> None:
    assert literal_para_c("'ola''mundo'") == '"ola\'mundo"'


def test_mangle_e_insensivel_a_maiusculas() -> None:
    assert mangle("Contador") == "gx_contador"
    assert mangle("CONTADOR") == "gx_contador"


def test_tipos_primarios_mapeiam_para_c() -> None:
    codigo = traduzir_fonte(
        "programa T;\nvar i: integer; r: real; c: char; s: string;\n"
        "begin\ni := 1; r := 2.5; c := 'a'; s := 'b';\nend.\n"
    )
    assert "int gx_i;" in codigo
    assert "double gx_r;" in codigo
    assert "char gx_c;" in codigo
    assert "char gx_s[GX_TAM_STRING];" in codigo
    assert 'strcpy(gx_s, ("b"));' in codigo
    assert 'gx_c = gx_str_para_char("a");' in codigo


def test_atribuicao_string_para_char_usa_conversao() -> None:
    codigo = traduzir_fonte(
        "programa T;\nvar c: char; s: string;\n"
        "begin\ns := 'ab'; c := s;\nend.\n"
    )
    assert "gx_c = gx_str_para_char(gx_s);" in codigo


def test_divisao_sempre_em_double() -> None:
    codigo = traduzir_fonte(
        "programa D;\nvar a, b: integer; r: real;\nbegin\nr := a / b;\nend.\n"
    )
    assert "((double)(gx_a) / (double)(gx_b))" in codigo


def test_operadores_logicos_viram_sintaxe_c() -> None:
    codigo = traduzir_fonte(
        "programa L;\nvar a, b: integer;\n"
        "begin\nif a = 1 ou b = 2 e a <> b then\na := 0;\nend.\n"
    )
    assert "==" in codigo
    assert "!=" in codigo
    assert "||" in codigo
    assert "&&" in codigo
    assert ":=" not in codigo


def test_concatenacao_e_comparacao_de_string() -> None:
    codigo = traduzir_fonte(
        "programa S;\nvar a, b, c: string;\n"
        "begin\na := b + 'x';\nif a = b then\nc := 'igual';\nend.\n"
    )
    assert "gx_concat(gx_b, \"x\")" in codigo
    assert "strcmp(" in codigo
    assert "strcpy(gx_a" in codigo


def test_record_vira_struct_com_prefixo() -> None:
    codigo = traduzir_fonte(
        "programa R;\ntype ponto = record\nx, y: integer;\nend;\n"
        "var p: ponto;\nbegin\np.x := 1;\nend.\n"
    )
    assert "typedef struct {" in codigo
    assert "int gx_x;" in codigo
    assert "} gx_ponto;" in codigo
    assert "gx_ponto gx_p;" in codigo
    assert "gx_p.gx_x = 1;" in codigo


def test_enumeração_vira_enum_com_constantes() -> None:
    codigo = traduzir_fonte(
        "programa Demo;\ntype cor = (vermelho, verde);\nvar c: cor;\n"
        "begin\nc := verde;\nend.\n"
    )
    assert "typedef enum { gx_vermelho, gx_verde } gx_cor;" in codigo
    assert "gx_c = gx_verde;" in codigo


def test_alias_de_tipo_comporta_como_a_base() -> None:
    codigo = traduzir_fonte(
        "programa A;\ntype nome = string;\nvar s: nome;\n"
        "begin\ns := 'oi';\nend.\n"
    )
    assert "char gx_s[GX_TAM_STRING];" in codigo
    assert "strcpy(gx_s" in codigo


def test_laço_for_to_avalia_limites_uma_vez() -> None:
    codigo = traduzir_fonte(
        "programa F;\nvar i: integer;\nbegin\nfor i := 1 to 5 do\ni := i;\nend.\n"
    )
    assert "int gx_ini1 = (1);" in codigo
    assert "int gx_fim1 = (5);" in codigo
    assert "gx_i = gx_ini1; gx_i <= gx_fim1; gx_i = gx_i + 1" in codigo


def test_laço_for_downto_decrementa() -> None:
    codigo = traduzir_fonte(
        "programa F;\nvar i: integer;\nbegin\nfor i := 5 downto 1 do\ni := i;\nend.\n"
    )
    assert ">=" in codigo
    assert "gx_i = gx_i - 1" in codigo


def test_repeat_vira_do_while_negado() -> None:
    codigo = traduzir_fonte(
        "programa P;\nvar i: integer;\nbegin\nrepeat\ni := i + 1;\nuntil i > 3;\nend.\n"
    )
    assert "do {" in codigo
    assert "} while (!((gx_i) > (3)));" in codigo


def test_while_e_if_geram_blocos_chaveados() -> None:
    codigo = traduzir_fonte(
        "programa W;\nvar i: integer;\n"
        "begin\nwhile i < 3 do\ni := i + 1;\nif i = 3 then\ni := 0;\nend.\n"
    )
    assert "while ((gx_i) < (3)) {" in codigo
    assert "if ((gx_i) == (3)) {" in codigo
    assert "} else {" not in codigo


def test_funcao_usa_variavel_de_resultado() -> None:
    codigo = traduzir_fonte(
        "programa F;\nfunction dobro(n: integer): integer;\nbegin\ndobro := n * 2;\nend;\n"
        "var x: integer;\nbegin\nx := dobro(4);\nend.\n"
    )
    assert "int gx_dobro(int gx_n)" in codigo
    assert "int gx_ret_dobro = 0;" in codigo
    assert "return gx_ret_dobro;" in codigo
    assert "gx_x = gx_dobro(4);" in codigo


def test_funcao_que_retorna_string_devolve_char_ponteiro() -> None:
    codigo = traduzir_fonte(
        "programa F;\nfunction nome(x: integer): string;\nbegin\nnome := 'a';\nend;\n"
        "var s: string;\nbegin\ns := nome(1);\nend.\n"
    )
    assert "char* gx_nome(int gx_x)" in codigo
    assert 'static char gx_ret_nome[GX_TAM_STRING] = "";' in codigo
    assert "return gx_ret_nome;" in codigo


def test_procedimento_sem_parametros_usa_void() -> None:
    codigo = traduzir_fonte(
        "programa P;\nprocedure fechar;\nbegin\nend;\nbegin\nfechar;\nend.\n"
    )
    assert "void gx_fechar(void);" in codigo
    assert "gx_fechar();" in codigo


def test_procedimento_com_variavel_local() -> None:
    codigo = traduzir_fonte(
        "programa P;\nprocedure t;\nvar k: integer;\nbegin\nk := 1;\nend;\n"
        "begin\nend.\n"
    )
    assert "int gx_k;" in codigo
    assert "gx_k = 1;" in codigo


def test_write_com_formatos_por_tipo() -> None:
    codigo = traduzir_fonte(
        "programa W;\nvar i: integer; r: real; s: string;\n"
        "begin\nwriteln(i, r, s);\nend.\n"
    )
    assert 'printf("%d%g%s\\n", gx_i, gx_r, gx_s);' in codigo


def test_writeln_sem_argumentos_imprime_quebra_de_linha() -> None:
    codigo = traduzir_fonte("programa W;\nbegin\nwriteln;\nend.\n")
    assert 'printf("\\n");' in codigo


def test_read_usa_scanf_com_ponteiros() -> None:
    codigo = traduzir_fonte(
        "programa R;\nvar i: integer; r: real; s: string;\n"
        "begin\nreadln(i, r, s);\nend.\n"
    )
    assert 'scanf("%d %lf %255s", &gx_i, &gx_r, gx_s);' in codigo
    assert "gx_consumir_linha();" in codigo


def test_indexacao_em_string_e_base_um() -> None:
    codigo = traduzir_fonte(
        "programa I;\nvar s: string; c: char;\nbegin\nc := s[2];\nend.\n"
    )
    assert "gx_s[(gx_s[(2) - 1]" not in codigo
    assert "gx_c = gx_s[(2) - 1];" in codigo


def test_indexacao_em_integer_gera_erro_claro() -> None:
    with pytest.raises(ErroDeTraducao) as captura:
        traduzir_fonte(
            "programa I;\nvar i: integer;\nbegin\ni := i[1];\nend.\n"
        )
    assert "vetores" in str(captura.value)


def test_break_fora_de_laco_nao_quebra_o_c() -> None:
    codigo = traduzir_fonte("programa B;\nbegin\nbreak;\nend.\n")
    assert "break ignorado: fora de laco" in codigo
    assert "break;" not in codigo.replace("break ignorado", "")


def test_break_dentro_de_laco_e_gerado() -> None:
    codigo = traduzir_fonte(
        "programa B;\nvar i: integer;\nbegin\nwhile i < 3 do\nbegin\nbreak;\nend;\nend.\n"
    )
    assert "break;" in codigo


def test_nome_de_identificador_nao_colide_com_c() -> None:
    codigo = traduzir_fonte(
        "programa C;\nvar printf: integer;\nbegin\nprintf := 1;\nend.\n"
    )
    assert "int gx_printf;" in codigo
    assert "gx_printf = 1;" in codigo


# --- Integração com o TCC embutido -------------------------------------------


def _compilar_e_rodar(tmp_path: Path, fonte: str, entrada: str = "") -> str:
    codigo = traduzir_fonte(fonte)
    destino = tmp_path / "programa.exe"
    ok, mensagem = compilar(codigo, destino)
    assert ok, mensagem
    assert destino.with_suffix(".c").is_file()
    processo = subprocess.run(
        [str(destino)],
        input=entrada,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert processo.returncode == 0, processo.stderr
    return processo.stdout


@requer_tcc
def test_programa_simples_compila_e_imprime(tmp_path: Path) -> None:
    saida = _compilar_e_rodar(
        tmp_path,
        "programa Ola;\nbegin\nwriteln('ola, mundo');\nend.\n",
    )
    assert saida == "ola, mundo\n"


@requer_tcc
def test_soma_e_funcao_compilam(tmp_path: Path) -> None:
    saida = _compilar_e_rodar(
        tmp_path,
        "programa S;\nfunction dobro(n: integer): integer;\n"
        "begin\ndobro := n * 2;\nend;\nvar x: integer;\n"
        "begin\nx := dobro(3);\nwriteln('dobro: ', x);\nend.\n",
    )
    assert saida == "dobro: 6\n"


@requer_tcc
def test_readln_le_do_entrada_padrao(tmp_path: Path) -> None:
    saida = _compilar_e_rodar(
        tmp_path,
        "programa L;\nvar n: integer;\nbegin\nreadln(n);\nn := n + 1;\n"
        "writeln('mais um: ', n);\nend.\n",
        entrada="41\n",
    )
    assert saida == "mais um: 42\n"


@requer_tcc
def test_caso_canonico_valido_compila_e_roda(tmp_path: Path) -> None:
    resultado = build_lexer().analyze(VALIDO.read_text(encoding="utf-8"))
    assert not resultado.all_errors
    codigo = traduzir(resultado.tokens)
    destino = tmp_path / "valido.exe"
    ok, mensagem = compilar(codigo, destino)
    assert ok, mensagem
    processo = subprocess.run(
        [str(destino)], capture_output=True, text=True, timeout=60, check=False
    )
    assert processo.returncode == 0, processo.stderr
    assert processo.stdout == "totais0ponto7ponto\nfim\n"


@requer_tcc
def test_erro_do_tcc_vira_mensagem_completa(tmp_path: Path) -> None:
    destino = tmp_path / "quebrado.exe"
    ok, mensagem = compilar("isto nao e C;", destino)
    assert not ok
    assert "Erros do compilador C" in mensagem


def test_compilar_sem_tcc_avisa(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(compilador, "tcc_path", lambda: "")
    ok, mensagem = compilador.compilar("int main(void){return 0;}", tmp_path / "x.exe")
    assert not ok
    assert "TCC nao encontrado" in mensagem


# --- Execução em console com pausa --------------------------------------------


def _rodar_cadeia_no_cmd(exe: Path) -> subprocess.CompletedProcess:
    """Roda a cadeia real do `executar` por pipe; o `pause` devolve no fim do stdin."""
    comspec = os.environ.get("ComSpec", "cmd.exe")
    linha = f'{comspec} /c "{compilador._comando_com_pausa(exe)}"'
    processo = subprocess.run(
        linha,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    return processo


def test_comando_da_execucao_segura_o_console() -> None:
    linha = compilador._comando_com_pausa(Path(r"C:\meus programas\ola.exe"))
    # o cmd /c remove uma aspa de cada ponta e sobra o caminho entre aspas
    assert linha.startswith('"C:\\meus programas\\ola.exe" & ')
    assert linha.count('"') == 2
    assert linha.endswith("pause >nul")
    # a linha de separacao vem antes do aviso de fim, nos dois ramos
    assert compilador.MENSAGEM_SEPARADOR == "-" * 48
    assert f"echo {compilador.MENSAGEM_SEPARADOR} & if errorlevel 1 " in linha
    assert compilador.MENSAGEM_FIM_SEM_ERROS in linha
    assert compilador.MENSAGEM_FIM_COM_ERRO in linha
    assert compilador.MENSAGEM_FECHAR in linha


@requer_windows
def test_cadeia_de_execucao_roda_no_cmd() -> None:
    hostname = (
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "hostname.exe"
    )
    if not hostname.is_file():
        pytest.skip("hostname.exe ausente")
    processo = _rodar_cadeia_no_cmd(hostname)
    texto = processo.stdout.decode("utf-8", errors="replace")
    assert processo.returncode == 0, processo.stderr
    assert compilador.MENSAGEM_SEPARADOR in texto
    assert compilador.MENSAGEM_FIM_SEM_ERROS in texto
    assert compilador.MENSAGEM_FECHAR in texto


@requer_windows
@requer_tcc
def test_cadeia_de_execucao_avisa_erro_de_execucao(tmp_path: Path) -> None:
    destino = tmp_path / "sai_com_3.exe"
    ok, mensagem = compilador.compilar("int main(void){return 3;}", destino)
    assert ok, mensagem
    processo = _rodar_cadeia_no_cmd(destino)
    texto = processo.stdout.decode("utf-8", errors="replace")
    assert compilador.MENSAGEM_SEPARADOR in texto
    assert compilador.MENSAGEM_FIM_COM_ERRO in texto


def test_executar_com_arquivo_inexistente(tmp_path: Path) -> None:
    assert compilador.executar(tmp_path / "nao_existe.exe") is False
