"""Compilação do C gerado com o TCC embutido em `tools/tcc`.

`compilar` grava o `.c` ao lado do `.exe` pedido e chama o `tcc.exe`
vendored; `executar` abre o binário em um console novo do sistema
(`CREATE_NEW_CONSOLE` no Windows), para que `read`/`readln` rodem de forma
interativa como em qualquer programa Pascal nativo. O console espera uma
tecla antes de fechar, avisando se o programa terminou sem erros.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..config import tcc_path

CREATE_NEW_CONSOLE = 0x00000010

TCC_AUSENCIA = (
    "TCC nao encontrado em tools/tcc; reinstale o IDE ou copie "
    "tcc.exe, include/ e lib/ para essa pasta."
)

# Mensagens do console de execucao, sem acento: o console novo usa a
# codepage OEM do sistema e acentos podem sair errados.
MENSAGEM_SEPARADOR = "-" * 44
MENSAGEM_FIM_SEM_ERROS = "O programa terminou sem erros."
MENSAGEM_FIM_COM_ERRO = "O programa terminou com erro em tempo de execucao."
MENSAGEM_FECHAR = "Pressione qualquer tecla para fechar o terminal."

_TIMEOUT_COMPILACAO = 120


def tcc_disponivel() -> bool:
    return bool(tcc_path())


def compilar(codigo_c: str, destino: Path) -> tuple[bool, str]:
    """Grava `destino`'s `.c`, liga com o TCC e devolve (ok, mensagem)."""
    destino = Path(destino)
    fonte = destino.with_suffix(".c")
    executavel = tcc_path()
    if not executavel:
        return False, TCC_AUSENCIA
    try:
        fonte.write_text(codigo_c, encoding="utf-8")
    except OSError as error:
        return False, f"Nao foi possivel gravar {fonte}: {error}"
    try:
        processo = subprocess.run(
            [executavel, "-o", str(destino), str(fonte)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(destino.parent),
            timeout=_TIMEOUT_COMPILACAO,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return False, f"Falha ao executar o TCC: {error}"
    detalhes = ((processo.stdout or "") + (processo.stderr or "")).strip()
    if processo.returncode != 0:
        if detalhes:
            return False, f"Erros do compilador C:\n{detalhes}"
        return False, f"O TCC falhou com o codigo {processo.returncode}."
    mensagem = f"C gerado: {fonte}\nExecutavel gerado: {destino}"
    if detalhes:
        mensagem += f"\n{detalhes}"
    return True, mensagem


def executar(destino: Path) -> bool:
    """Abre o `.exe` em um console do sistema; devolve se conseguiu.

    No Windows o console é aberto por um `cmd` que espera uma tecla no
    fim (com aviso de sucesso ou erro), em vez de fechar sozinho junto
    com o programa.
    """
    destino = Path(destino)
    if not destino.is_file():
        return False
    try:
        if sys.platform == "win32":
            comspec = os.environ.get("ComSpec", "cmd.exe")
            subprocess.Popen(
                f'{comspec} /c "{_comando_com_pausa(destino)}"',
                cwd=str(destino.parent),
                creationflags=CREATE_NEW_CONSOLE,
            )
        else:
            subprocess.Popen([str(destino)], cwd=str(destino.parent))
        return True
    except OSError:
        return False


def _comando_com_pausa(destino: Path) -> str:
    """Cadeia do `cmd` que roda o binário, informa o fim e espera uma tecla.

    O console do Windows fecha junto com o processo que o criou; sem a
    volta com `pause`, a saída do programa sumiria antes de dar para
    ler. `if errorlevel 1` separa o término normal do erro em tempo de
    execução. A cadeia vai embrulhada em aspas no `/c "..."` (as aspas
    de fora são adicionadas em `executar`); o `cmd` as remove pela
    regra de aspas dele, deixando o caminho do exe entre aspas como
    primeiro comando da cadeia.
    """
    return (
        f'"{destino}" & '
        f"echo {MENSAGEM_SEPARADOR} & "
        "if errorlevel 1 "
        f"(echo {MENSAGEM_FIM_COM_ERRO}) else (echo {MENSAGEM_FIM_SEM_ERROS}) & "
        f"echo {MENSAGEM_FECHAR} & pause >nul"
    )


__all__ = [
    "MENSAGEM_FECHAR",
    "MENSAGEM_FIM_COM_ERRO",
    "MENSAGEM_FIM_SEM_ERROS",
    "MENSAGEM_SEPARADOR",
    "TCC_AUSENCIA",
    "compilar",
    "executar",
    "tcc_disponivel",
]
