"""Compilação do C gerado com o TCC embutido em `tools/tcc`.

`compilar` grava o `.c` ao lado do `.exe` pedido e chama o `tcc.exe`
vendored; `executar` abre o binário em um console novo do sistema
(`CREATE_NEW_CONSOLE` no Windows), para que `read`/`readln` rodem de forma
interativa como em qualquer programa Pascal nativo.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ..config import tcc_path

CREATE_NEW_CONSOLE = 0x00000010

TCC_AUSENCIA = (
    "TCC nao encontrado em tools/tcc; reinstale o IDE ou copie "
    "tcc.exe, include/ e lib/ para essa pasta."
)

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
    """Abre o `.exe` em um console do sistema; devolve se conseguiu."""
    destino = Path(destino)
    if not destino.is_file():
        return False
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                [str(destino)],
                cwd=str(destino.parent),
                creationflags=CREATE_NEW_CONSOLE,
            )
        else:
            subprocess.Popen([str(destino)], cwd=str(destino.parent))
        return True
    except OSError:
        return False


__all__ = ["TCC_AUSENCIA", "compilar", "executar", "tcc_disponivel"]
