from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.config import (  # noqa: E402
    BUNDLED_BACKGROUND_IMAGE,
    default_background_image,
)
from src.editor.code_editor import CodeEditor  # noqa: E402
from src.settings import (  # noqa: E402
    MAX_BACKGROUND_OPACITY,
    MAX_FONT_SIZE,
    MIN_BACKGROUND_OPACITY,
    Settings,
    load_settings,
    save_settings,
)

FUNDO_TESTE = "#3060c0"

@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])

@pytest.fixture
def imagem(tmp_path) -> Path:
    from PySide6.QtGui import QColor, QPixmap

    pixmap = QPixmap(40, 30)
    pixmap.fill(QColor(FUNDO_TESTE))
    pixmap.save(str(tmp_path / "fundo.png"), "PNG")
    return tmp_path / "fundo.png"

def pixel_do_editor(editor: CodeEditor, x: int, y: int):
    editor.resize(240, 120)
    alvo = QImage(editor.size(), QImage.Format.Format_ARGB32)
    alvo.fill(0)
    editor.render(alvo)
    return alvo.pixelColor(x, y)

def test_imagem_do_projeto_existe() -> None:
    assert BUNDLED_BACKGROUND_IMAGE.is_file()

def test_padrao_aponta_para_a_imagem_do_projeto() -> None:
    assert Settings().background_image_path == str(BUNDLED_BACKGROUND_IMAGE)

def test_caminho_padrao_desaparece_sem_a_pasta_img() -> None:
    assert default_background_image() == "" or Path(default_background_image()).is_file()

def test_imagem_valida_e_aplicada(app: QApplication, imagem: Path) -> None:
    editor = CodeEditor()
    assert editor.set_background_image(str(imagem), 10)
    assert editor.has_background_image()

def test_caminho_vazio_deixa_o_editor_sem_fundo(app: QApplication, imagem: Path) -> None:
    editor = CodeEditor()
    editor.set_background_image(str(imagem), 10)
    assert not editor.set_background_image("", 10)
    assert not editor.has_background_image()

def test_arquivo_inexistente_deixa_o_editor_sem_fundo(app: QApplication, tmp_path) -> None:
    editor = CodeEditor()
    assert not editor.set_background_image(str(tmp_path / "nao-existe.png"), 10)
    assert not editor.has_background_image()

def test_opacidade_e_aparada(app: QApplication, imagem: Path) -> None:
    editor = CodeEditor()
    editor.set_background_image(str(imagem), 999)
    assert editor._background_opacity == MAX_BACKGROUND_OPACITY / 100
    editor.set_background_image(str(imagem), -50)
    assert editor._background_opacity == MIN_BACKGROUND_OPACITY / 100

def test_opacidade_zero_nao_apaga_a_preferencia(app: QApplication, imagem: Path) -> None:
    editor = CodeEditor()
    editor.set_background_image(str(imagem), 0)
    assert editor.has_background_image()

def test_fundo_desenha_uma_cor_que_nao_e_a_do_tema(app: QApplication, imagem: Path) -> None:
    editor = CodeEditor()
    editor.setPlainText("programa Ola;\nbegin\nend.")
    antes = pixel_do_editor(editor, 200, 100)

    editor.set_background_image(str(imagem), 100)
    depois = pixel_do_editor(editor, 200, 100)

    assert antes != depois

@pytest.mark.parametrize(
    ("largura", "altura", "editor_l", "editor_a"),
    [
        (200, 50, 300, 120),   # imagem panorâmica em área também panorâmica
        (200, 50, 100, 400),   # imagem panorâmica em área vertical
        (50, 200, 300, 120),   # imagem vertical em área panorâmica
        (100, 100, 300, 120),  # imagem quadrada
    ],
)
def test_imagem_cobre_a_area_inteira(
    app: QApplication,
    tmp_path,
    largura: int,
    altura: int,
    editor_l: int,
    editor_a: int,
) -> None:
    from PySide6.QtGui import QColor, QPixmap

    pixmap = QPixmap(largura, altura)
    pixmap.fill(QColor(FUNDO_TESTE))
    caminho = tmp_path / "forma.png"
    pixmap.save(str(caminho), "PNG")

    editor = CodeEditor()
    editor.resize(editor_l, editor_a)
    editor.set_background_image(str(caminho), 100)
    editor.show()
    app.processEvents()

    alvo = QImage(editor.size(), QImage.Format.Format_ARGB32)
    alvo.fill(0)
    editor.render(alvo)

    esperado = QColor(FUNDO_TESTE)
    viewport = editor.viewport()
    margem = 3
    pontos = [
        (viewport.x() + margem, viewport.y() + margem),
        (viewport.x() + viewport.width() - margem - 1, viewport.y() + margem),
        (viewport.x() + margem, viewport.y() + viewport.height() - margem - 1),
        (
            viewport.x() + viewport.width() - margem - 1,
            viewport.y() + viewport.height() - margem - 1,
        ),
    ]
    for x, y in pontos:
        assert alvo.pixelColor(x, y) == esperado, f"canto ({x}, {y}) sem imagem"

def test_escala_preserva_a_proporcao(app: QApplication, tmp_path) -> None:
    from PySide6.QtGui import QColor, QPixmap

    pixmap = QPixmap(200, 50)
    pixmap.fill(QColor(FUNDO_TESTE))
    caminho = tmp_path / "panoramica.png"
    pixmap.save(str(caminho), "PNG")

    editor = CodeEditor()
    editor.resize(100, 400)
    editor.set_background_image(str(caminho), 10)

    covering = editor._cover_pixmap()
    assert covering is not None

    area = editor.viewport().size()
    assert covering.width() >= area.width()
    assert covering.height() >= area.height()
    assert covering.width() / covering.height() == pytest.approx(200 / 50, rel=0.01)

def test_imagem_menor_que_a_area_e_ampliada(app: QApplication, imagem: Path) -> None:
    editor = CodeEditor()
    editor.resize(900, 700)
    editor.set_background_image(str(imagem), 10)

    covering = editor._cover_pixmap()
    area = editor.viewport().size()
    assert covering.width() >= area.width()
    assert covering.height() >= area.height()

def test_escala_reaproveitada_para_o_mesmo_tamanho(app: QApplication, imagem: Path) -> None:
    editor = CodeEditor()
    editor.resize(300, 200)
    editor.set_background_image(str(imagem), 10)

    primeiro = editor._cover_pixmap()
    segundo = editor._cover_pixmap()
    assert primeiro is segundo
    assert primeiro.cacheKey() == segundo.cacheKey()

def test_escala_recalculada_quando_a_area_muda(app: QApplication, imagem: Path) -> None:
    editor = CodeEditor()
    editor.resize(300, 200)
    editor.set_background_image(str(imagem), 10)
    editor.show()
    app.processEvents()
    pequeno = editor._cover_pixmap()

    editor.resize(600, 400)
    app.processEvents()
    grande = editor._cover_pixmap()

    assert grande.width() > pequeno.width()
    assert grande.height() > pequeno.height()

def test_trocar_de_imagem_invalida_a_escala(app: QApplication, imagem: Path, tmp_path) -> None:
    from PySide6.QtGui import QColor, QPixmap

    editor = CodeEditor()
    editor.resize(300, 200)
    editor.set_background_image(str(imagem), 10)
    primeiro = editor._cover_pixmap()

    outra = QPixmap(300, 100)
    outra.fill(QColor("#c05030"))
    caminho = tmp_path / "outra.png"
    outra.save(str(caminho), "PNG")
    editor.set_background_image(str(caminho), 10)
    segundo = editor._cover_pixmap()

    assert segundo.cacheKey() != primeiro.cacheKey()
    assert segundo.width() / segundo.height() == pytest.approx(3.0, rel=0.01)

def test_opacidade_alta_deixa_a_cor_mais_proxima_da_imagem(
    app: QApplication, imagem: Path
) -> None:
    editor = CodeEditor()
    editor.setPlainText("programa Ola;\nbegin\nend.")
    editor.set_background_image(str(imagem), 100)
    opaco = pixel_do_editor(editor, 200, 100)
    editor.set_background_image(str(imagem), 0)
    claro = pixel_do_editor(editor, 200, 100)

    assert opaco != claro

def test_opacidade_sobrevive_ao_round_trip(tmp_path: Path) -> None:
    caminho = tmp_path / "preferencias.json"
    config = Settings(background_image_path="C:/fundo.png", background_image_opacity=35)
    assert save_settings(config, caminho)

    recarregado = load_settings(caminho)
    assert recarregado.background_image_path == "C:/fundo.png"
    assert recarregado.background_image_opacity == 35

def test_opacidade_fora_da_faixa_e_aparada(tmp_path: Path) -> None:
    caminho = tmp_path / "preferencias.json"
    caminho.write_text(
        '{"background_image_opacity": 900}', encoding="utf-8"
    )
    assert load_settings(caminho).background_image_opacity == MAX_BACKGROUND_OPACITY

    caminho.write_text('{"background_image_opacity": -3}', encoding="utf-8")
    assert load_settings(caminho).background_image_opacity == MIN_BACKGROUND_OPACITY

def test_fonte_da_opacidade_nao_altera_a_faixa_da_fonte(tmp_path: Path) -> None:
    caminho = tmp_path / "preferencias.json"
    caminho.write_text('{"font_size": 5000}', encoding="utf-8")
    assert load_settings(caminho).font_size == MAX_FONT_SIZE

def test_preferencias_sem_o_campo_usa_o_padrao(tmp_path: Path) -> None:
    caminho = tmp_path / "preferencias.json"
    caminho.write_text('{"theme": "dark"}', encoding="utf-8")
    recarregado = load_settings(caminho)
    assert recarregado.background_image_path == Settings().background_image_path
    assert recarregado.background_image_opacity == Settings().background_image_opacity
