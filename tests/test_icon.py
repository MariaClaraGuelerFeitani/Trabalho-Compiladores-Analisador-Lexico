from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QIcon, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src import config  # noqa: E402
from src.config import APP_ICON_FILE  # noqa: E402


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def tamanhos_do_ico(caminho: Path) -> list[tuple[int, int]]:
    dados = caminho.read_bytes()
    assert dados[:4] == b"\x00\x00\x01\x00"
    quantidade = struct.unpack_from("<H", dados, 4)[0]
    lados = []
    for i in range(quantidade):
        inicio = 6 + i * 16
        lados.append((dados[inicio] or 256, dados[inicio + 1] or 256))
    return lados


def quadro_do_ico(caminho: Path, lado: int) -> QImage:
    dados = caminho.read_bytes()
    for i in range(struct.unpack_from("<H", dados, 4)[0]):
        inicio = 6 + i * 16
        if (dados[inicio] or 256, dados[inicio + 1] or 256) != (lado, lado):
            continue
        tamanho, offset = struct.unpack_from("<II", dados, inicio + 8)
        imagem = QImage()
        assert imagem.loadFromData(dados[offset : offset + tamanho], "PNG")
        return imagem.convertToFormat(QImage.Format.Format_RGBA8888)
    raise AssertionError(f"{caminho.name} nao tem um quadro de {lado}x{lado}")


def silhueta(imagem: QImage) -> tuple[int, int, int, int]:
    bits = imagem.constBits()
    linha = imagem.bytesPerLine()
    largura, altura = imagem.width(), imagem.height()

    def opaca(x: int, y: int) -> bool:
        return bits[y * linha + x * 4 + 3] > 0

    xs = [x for x in range(largura) if any(opaca(x, y) for y in range(altura))]
    ys = [y for y in range(altura) if any(opaca(x, y) for x in range(largura))]
    assert xs and ys, "a imagem nao tem nada opaco"
    return xs[0], ys[0], xs[-1] + 1, ys[-1] + 1


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


def test_ico_nao_corta_a_arte() -> None:
    ico = APP_ICON_FILE.with_suffix(".ico")
    png = QImage(str(APP_ICON_FILE)).convertToFormat(QImage.Format.Format_RGBA8888)

    x0, y0, x1, y1 = silhueta(quadro_do_ico(ico, 256))
    ax0, ay0, ax1, ay1 = silhueta(png)

    largura, altura = x1 - x0, y1 - y0
    assert (largura, altura) != (256, 256), "a arte preenche o quadro: foi recortada"

    proporcao = largura / altura
    original = (ax1 - ax0) / (ay1 - ay0)
    assert abs(proporcao - original) < 0.02, f"arte distorcida: {proporcao:.3f}"
    assert x0 == 256 - x1, "a arte nao esta centralizada no quadro"


def test_qt_carrega_o_icone(app: QApplication) -> None:
    assert not QIcon(str(APP_ICON_FILE)).isNull()


def test_caminho_vazio_sem_o_arquivo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "APP_ICON_FILE", Path("img") / "nao_existe.png")
    assert config.app_icon_file() == ""


def test_caminho_aponta_para_o_arquivo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "APP_ICON_FILE", APP_ICON_FILE)
    assert config.app_icon_file() == str(APP_ICON_FILE)
