from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QIcon, QImage  # noqa: E402

from src import config  # noqa: E402
from src.config import APP_ICON_FILE  # noqa: E402


def tamanhos_do_ico(caminho: Path) -> list[tuple[int, int]]:
    dados = caminho.read_bytes()
    assert dados[:4] == b"\x00\x00\x01\x00"
    quantidade = struct.unpack_from("<H", dados, 4)[0]
    lados = []
    for i in range(quantidade):
        inicio = 6 + i * 16
        lados.append((dados[inicio] or 256, dados[inicio + 1] or 256))
    return lados


def test_icone_do_projeto_existe() -> None:
    assert APP_ICON_FILE.is_file()


def test_ico_tem_os_tamanhos_que_o_windows_usa() -> None:
    ico = APP_ICON_FILE.with_suffix(".ico")
    assert ico.is_file(), "rode tools/make_icon.py"
    assert (16, 16) in tamanhos_do_ico(ico)
    assert (32, 32) in tamanhos_do_ico(ico)
    assert (256, 256) in tamanhos_do_ico(ico)


def test_icone_tem_fundo_transparente() -> None:
    assert APP_ICON_FILE.suffix == ".png"
    assert QImage(str(APP_ICON_FILE)).hasAlphaChannel()


def test_qt_carrega_o_icone() -> None:
    assert not QIcon(str(APP_ICON_FILE)).isNull()


def test_caminho_vazio_sem_o_arquivo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "APP_ICON_FILE", Path("img") / "nao_existe.png")
    assert config.app_icon_file() == ""


def test_caminho_aponta_para_o_arquivo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "APP_ICON_FILE", APP_ICON_FILE)
    assert config.app_icon_file() == str(APP_ICON_FILE)
