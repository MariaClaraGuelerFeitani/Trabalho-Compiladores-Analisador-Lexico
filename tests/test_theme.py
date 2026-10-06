from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QColor, QPalette  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.editor.code_editor import ERROR_ON_DARK, ERROR_ON_LIGHT, error_color  # noqa: E402
from src.editor.highlighter import (  # noqa: E402
    CATEGORIES,
    CATEGORY_COMMENT,
    CATEGORY_KEYWORD,
    DARK_COLORS,
    LIGHT_COLORS,
    default_colors,
    resolve_colors,
)
from src.settings import (  # noqa: E402
    THEME_CHOICES,
    THEME_CONTRAST,
    THEME_DARK,
    THEME_FOREST,
    THEME_LABELS,
    THEME_LIGHT,
    THEME_OCEAN,
    THEME_SEPIA,
    THEME_SOLARIZED_DARK,
    THEME_SOLARIZED_LIGHT,
    THEME_SYSTEM,
    Settings,
    load_settings,
    save_settings,
)
from src.theme import (  # noqa: E402
    DARK,
    FOREST,
    LIGHT,
    PALETTE_FIELDS,
    THEMES,
    apply_theme,
    build_palette,
    is_dark,
    remember_system_appearance,
    spec_for,
)

HEX = re.compile(r"#[0-9a-f]{6}")

TEMAS_ESCUROS = (THEME_DARK, THEME_OCEAN, THEME_CONTRAST, THEME_FOREST, THEME_SOLARIZED_DARK)
TEMAS_CLAROS = (THEME_LIGHT, THEME_SEPIA, THEME_SOLARIZED_LIGHT)

TEMAS_NOVOS = (
    THEME_OCEAN,
    THEME_SEPIA,
    THEME_CONTRAST,
    THEME_FOREST,
    THEME_SOLARIZED_LIGHT,
    THEME_SOLARIZED_DARK,
)

CLARO = QPalette.ColorRole.Base
TEXTO = QPalette.ColorRole.Text

MINIMO_SEPARACAO = 12

MINIMO_CONTRASTE_TEXTO = 4.5
MINIMO_CONTRASTE_REALCE = 3.0


def _canal(valor: int) -> float:
    fracao = valor / 255
    return fracao / 12.92 if fracao <= 0.04045 else ((fracao + 0.055) / 1.055) ** 2.4


def contraste(primeira: str, segunda: str) -> float:
    """Razao de contraste WCAG entre duas cores hex."""
    a, b = QColor(primeira), QColor(segunda)
    la = (
        0.2126 * _canal(a.red())
        + 0.7152 * _canal(a.green())
        + 0.0722 * _canal(a.blue())
    )
    lb = (
        0.2126 * _canal(b.red())
        + 0.7152 * _canal(b.green())
        + 0.0722 * _canal(b.blue())
    )
    alto, baixo = max(la, lb), min(la, lb)
    return (alto + 0.05) / (baixo + 0.05)


@pytest.fixture(scope="module")
def app() -> QApplication:
    instancia = QApplication.instance() or QApplication([])
    remember_system_appearance(instancia)
    original = (instancia.style().objectName(), QPalette(instancia.palette()))
    yield instancia
    instancia.setStyle(original[0])
    instancia.setPalette(original[1])


def paleta_de(tema: str) -> QPalette:
    return build_palette(spec_for(tema))


def base_de(tema: str) -> QColor:
    return paleta_de(tema).color(CLARO)


def brilho(cor: str) -> int:
    return QColor(cor).lightness()


def test_padrao_do_usuario_continua_sendo_o_tema_do_sistema() -> None:
    assert Settings().theme == THEME_SYSTEM

def test_escolhas_de_tema_sao_unicas() -> None:
    assert len(set(THEME_CHOICES)) == len(THEME_CHOICES)

def test_escolhas_sao_o_sistema_mais_todos_os_temas_embutidos() -> None:
    assert THEME_CHOICES[0] == THEME_SYSTEM
    assert set(THEME_CHOICES) - {THEME_SYSTEM} == set(THEMES)
    assert len(THEMES) == 8

def test_todos_os_temas_novos_estao_disponiveis() -> None:
    assert set(TEMAS_NOVOS) <= set(THEME_CHOICES)
    assert set(TEMAS_NOVOS) <= set(THEMES)

def test_temas_antigos_continuam_disponiveis() -> None:
    assert THEME_LIGHT in THEMES and THEME_DARK in THEMES
    assert THEMES[THEME_LIGHT] is LIGHT
    assert THEMES[THEME_DARK] is DARK

def test_rotulo_existe_para_cada_escolha() -> None:
    assert set(THEME_LABELS) == set(THEME_CHOICES)

def test_rotulos_sao_unicos_e_nao_vazios() -> None:
    rotulos = list(THEME_LABELS.values())
    assert len(set(rotulos)) == len(rotulos)
    for rotulo in rotulos:
        assert rotulo.strip(), rotulo
        assert rotulo[0].isupper(), rotulo

def test_spec_registrado_tem_nome_igual_a_chave() -> None:
    for chave, spec in THEMES.items():
        assert spec.name == chave, chave

def test_tema_do_sistema_nao_vira_spec() -> None:
    assert spec_for(THEME_SYSTEM) is None
    assert THEME_SYSTEM not in THEMES

def test_tema_desconhecido_nao_vira_spec() -> None:
    assert spec_for("inexistente") is None
    assert spec_for("") is None
    assert spec_for("LIGHT") is None

def test_campos_de_paleta_sao_os_esperados() -> None:
    assert PALETTE_FIELDS == (
        "window",
        "window_text",
        "base",
        "alternate_base",
        "text",
        "placeholder",
        "button",
        "button_text",
        "highlight",
        "highlighted_text",
        "tooltip_base",
        "tooltip_text",
        "disabled_text",
        "mid",
    )

def test_toda_cor_de_paleta_e_hexadecimal() -> None:
    for chave, spec in THEMES.items():
        for campo in PALETTE_FIELDS:
            valor = getattr(spec, campo)
            assert HEX.fullmatch(valor), (chave, campo, valor)

def test_paleta_aplica_as_cores_do_spec() -> None:
    for chave, spec in THEMES.items():
        paleta = build_palette(spec)
        role = QPalette.ColorRole
        assert paleta.color(role.Window) == QColor(spec.window), chave
        assert paleta.color(role.Base) == QColor(spec.base), chave
        assert paleta.color(role.Text) == QColor(spec.text), chave
        assert paleta.color(role.Highlight) == QColor(spec.highlight), chave
        assert paleta.color(role.Mid) == QColor(spec.mid), chave

def test_cor_desabilitada_fica_cinza() -> None:
    for chave, spec in THEMES.items():
        paleta = build_palette(spec)
        cinza = QColor(spec.disabled_text)
        desabilitado = QPalette.ColorGroup.Disabled
        assert paleta.color(desabilitado, QPalette.ColorRole.Text) == cinza, chave
        assert paleta.color(desabilitado, QPalette.ColorRole.WindowText) == cinza, chave

def test_link_usa_a_cor_de_destaque() -> None:
    for chave, spec in THEMES.items():
        paleta = build_palette(spec)
        link = paleta.color(QPalette.ColorRole.Link)
        destaque = paleta.color(QPalette.ColorRole.Highlight)
        assert link == destaque, chave

def test_is_dark_confere_com_a_cor_de_base() -> None:
    for chave, spec in THEMES.items():
        assert is_dark(spec) == (brilho(spec.base) < 128), chave

def test_temas_escuros_tem_base_escura_e_texto_claro() -> None:
    for tema in TEMAS_ESCUROS:
        spec = spec_for(tema)
        assert brilho(spec.base) < 128, tema
        assert brilho(spec.text) > 128, tema
        assert brilho(spec.error) > 128, tema

def test_temas_claros_tem_base_clara_e_texto_escuro() -> None:
    for tema in TEMAS_CLAROS:
        spec = spec_for(tema)
        assert brilho(spec.base) >= 128, tema
        assert brilho(spec.text) < 128, tema

def test_temas_escuros_tem_destaque_visivel() -> None:
    for tema in TEMAS_ESCUROS:
        spec = spec_for(tema)
        assert brilho(spec.highlight) > brilho(spec.base), tema
        assert brilho(spec.highlighted_text) != brilho(spec.highlight), tema

def test_o_texto_selecionado_nao_some_na_base() -> None:
    for chave, spec in THEMES.items():
        razao = contraste(spec.highlighted_text, spec.highlight)
        assert razao >= MINIMO_CONTRASTE_REALCE, (chave, round(razao, 2))


def test_cada_tema_cobre_todas_as_categorias_de_realce() -> None:
    for chave, spec in THEMES.items():
        assert set(spec.syntax) == set(CATEGORIES), chave

def test_toda_cor_de_realce_e_hexadecimal() -> None:
    for chave, spec in THEMES.items():
        for categoria, cor in spec.syntax.items():
            assert HEX.fullmatch(cor), (chave, categoria, cor)

def test_cor_de_realce_nunca_iguala_a_base_nem_ao_texto() -> None:
    for chave, spec in THEMES.items():
        for categoria, cor in spec.syntax.items():
            assert cor != spec.base, (chave, categoria)
            assert cor != spec.text, (chave, categoria)
            razao = contraste(cor, spec.base)
            assert razao >= MINIMO_CONTRASTE_REALCE, (chave, categoria, round(razao, 2))

def test_texto_do_editor_tem_contraste_suficiente() -> None:
    for chave, spec in THEMES.items():
        razao = contraste(spec.text, spec.base)
        assert razao >= MINIMO_CONTRASTE_TEXTO, (chave, round(razao, 2))

def test_cor_de_erro_tem_contraste_suficiente() -> None:
    for chave, spec in THEMES.items():
        razao = contraste(spec.error, spec.base)
        assert razao >= MINIMO_CONTRASTE_REALCE, (chave, round(razao, 2))

def test_texto_da_janela_tem_contraste_suficiente() -> None:
    for chave, spec in THEMES.items():
        razao = contraste(spec.window_text, spec.window)
        assert razao >= MINIMO_CONTRASTE_TEXTO, (chave, round(razao, 2))

def test_texto_do_botao_tem_contraste_sobre_o_botao() -> None:
    for chave, spec in THEMES.items():
        razao = contraste(spec.button_text, spec.button)
        assert razao >= MINIMO_CONTRASTE_TEXTO, (chave, round(razao, 2))

def test_dica_de_ferramenta_tem_contraste_sobre_o_fundo_dela() -> None:
    for chave, spec in THEMES.items():
        razao = contraste(spec.tooltip_text, spec.tooltip_base)
        assert razao >= MINIMO_CONTRASTE_TEXTO, (chave, round(razao, 2))

def test_cor_de_erro_e_hexadecimal() -> None:
    for chave, spec in THEMES.items():
        assert HEX.fullmatch(spec.error), (chave, spec.error)

def test_temas_claro_e_escuro_preservam_as_cores_antigas() -> None:
    assert dict(LIGHT.syntax) == {
        CATEGORY_KEYWORD: "#0b5cad",
        "tipo_primario": "#0f7b7b",
        "numero": "#a05000",
        "literal": "#a31515",
        CATEGORY_COMMENT: "#5a8a4a",
    }
    assert dict(DARK.syntax) == {
        CATEGORY_KEYWORD: "#569cd6",
        "tipo_primario": "#4ec9b0",
        "numero": "#d7ba7d",
        "literal": "#ce9178",
        CATEGORY_COMMENT: "#7ca668",
    }
    assert LIGHT.error == ERROR_ON_LIGHT
    assert DARK.error == ERROR_ON_DARK

def test_temas_novos_tem_realce_proprio() -> None:
    genericas = [dict(LIGHT.syntax), dict(DARK.syntax)]
    for tema in TEMAS_NOVOS:
        spec = spec_for(tema)
        for generica in genericas:
            diferente = any(
                spec.syntax[categoria] != generica[categoria]
                for categoria in CATEGORIES
            )
            assert diferente, (tema, "repetiu as cores do tema claro/escuro")

def test_temas_novos_tem_paleta_ou_acentos_proprios() -> None:
    genericos = {LIGHT.base, DARK.base, LIGHT.highlight, DARK.highlight}
    for tema in TEMAS_NOVOS:
        spec = spec_for(tema)
        assert spec.base not in genericos or spec.highlight not in genericos, tema

@pytest.mark.parametrize("tema", sorted(THEMES))
def test_realce_do_tema_e_o_esperado(tema: str) -> None:
    spec = spec_for(tema)
    paleta = paleta_de(tema)
    cores = default_colors(paleta, tema)
    assert set(cores) == set(CATEGORIES)
    for categoria in CATEGORIES:
        assert cores[categoria] == QColor(spec.syntax[categoria]), (tema, categoria)

@pytest.mark.parametrize("tema", sorted(THEMES))
def test_cor_de_erro_do_tema_e_a_esperada(tema: str) -> None:
    assert error_color(paleta_de(tema), tema) == QColor(spec_for(tema).error)

@pytest.mark.parametrize("tema", sorted(THEMES))
def test_preferencia_do_usuario_vence_a_cor_do_tema(tema: str) -> None:
    paleta = paleta_de(tema)
    antes = default_colors(paleta, tema)
    depois = resolve_colors({CATEGORY_KEYWORD: QColor("#ff00ff")}, paleta, tema)
    assert depois[CATEGORY_KEYWORD] == QColor("#ff00ff"), tema
    assert depois[CATEGORY_COMMENT] == antes[CATEGORY_COMMENT], tema

def test_tema_sem_spec_usa_a_heuristica_claro_escuro() -> None:
    assert default_colors(paleta_de(THEME_LIGHT)) == {
        c: QColor(v) for c, v in LIGHT_COLORS.items()
    }
    assert default_colors(paleta_de(THEME_DARK)) == {
        c: QColor(v) for c, v in DARK_COLORS.items()
    }

def test_tema_do_sistema_ou_desconhecido_cai_na_heuristica() -> None:
    for tema in (THEME_SYSTEM, "inexistente", ""):
        cores = default_colors(paleta_de(THEME_DARK), tema)
        assert cores == {c: QColor(v) for c, v in DARK_COLORS.items()}, tema

def test_preferencia_tambem_vence_na_heuristica() -> None:
    paleta = paleta_de(THEME_LIGHT)
    cores = resolve_colors({CATEGORY_KEYWORD: QColor("#ff00ff")}, paleta)
    assert cores[CATEGORY_KEYWORD] == QColor("#ff00ff")
    assert cores[CATEGORY_COMMENT] == QColor(LIGHT_COLORS[CATEGORY_COMMENT])

def test_tema_com_realce_incompleto_cai_na_heuristica() -> None:
    incompleto = replace(LIGHT, syntax={CATEGORY_KEYWORD: "#123456"})
    paleta = build_palette(incompleto)
    default_colors(paleta, "tema-que-nao-existe")
    assert default_colors(paleta) == {c: QColor(v) for c, v in LIGHT_COLORS.items()}

def test_tema_sem_realce_cai_na_heuristica() -> None:
    vazio = replace(DARK, syntax={})
    assert default_colors(build_palette(vazio)) == {
        c: QColor(v) for c, v in DARK_COLORS.items()
    }

def test_cor_de_erro_sem_tema_usa_a_heuristica() -> None:
    assert error_color(paleta_de(THEME_DARK)) == QColor(ERROR_ON_DARK)
    assert error_color(paleta_de(THEME_LIGHT)) == QColor(ERROR_ON_LIGHT)

def test_cor_de_erro_de_tema_desconhecido_usa_a_heuristica() -> None:
    assert error_color(paleta_de(THEME_DARK), "inexistente") == QColor(ERROR_ON_DARK)
    assert error_color(paleta_de(THEME_LIGHT), THEME_SYSTEM) == QColor(ERROR_ON_LIGHT)


@pytest.mark.parametrize("tema", sorted(THEMES))
def test_apply_theme_muda_a_paleta_do_app(app: QApplication, tema: str) -> None:
    apply_theme(app, tema)
    assert app.palette().color(CLARO) == QColor(spec_for(tema).base), tema
    assert app.palette().color(TEXTO) == QColor(spec_for(tema).text), tema

@pytest.mark.parametrize("tema", sorted(TEMAS_NOVOS))
def test_linha_atual_acompanha_o_tema(app: QApplication, tema: str) -> None:
    from src.editor.code_editor import current_line_color  # noqa: PLC0415

    apply_theme(app, tema)
    paleta = QPalette(app.palette())
    cor = current_line_color(paleta)
    assert cor != paleta.color(CLARO), tema
    assert abs(cor.lightness() - paleta.color(CLARO).lightness()) >= 1, tema
    esperado = ">" if is_dark(spec_for(tema)) else "<"
    assert (cor.lightness() > paleta.color(CLARO).lightness()) == (esperado == ">"), tema

def test_tema_sistema_devolve_a_paleta_do_sistema(app: QApplication) -> None:
    apply_theme(app, THEME_DARK)
    remember_system_appearance(app)
    antes = QPalette(app.palette())
    apply_theme(app, THEME_LIGHT)
    assert app.palette().color(CLARO) != antes.color(CLARO)
    apply_theme(app, THEME_SYSTEM)
    assert app.palette().color(CLARO) == antes.color(CLARO)

def test_apply_theme_ignora_id_desconhecido(app: QApplication) -> None:
    apply_theme(app, THEME_FOREST)
    antes = QPalette(app.palette())
    apply_theme(app, "inexistente")
    assert app.palette().color(CLARO) == antes.color(CLARO)


@pytest.mark.parametrize("tema", sorted(THEME_CHOICES))
def test_tema_sobrevive_ao_round_trip(tema: str, tmp_path: Path) -> None:
    caminho = tmp_path / "settings.json"
    assert save_settings(Settings(theme=tema), caminho)
    assert load_settings(caminho).theme == tema

@pytest.mark.parametrize("tema", sorted(TEMAS_NOVOS))
def test_previa_do_dialogo_muda_com_o_tema(app: QApplication, tema: str) -> None:
    from src.panels.settings_dialog import SettingsDialog  # noqa: PLC0415

    dialog = SettingsDialog(Settings(theme=THEME_LIGHT), lambda _s: None)
    dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData(tema))
    folha = dialog.highlight_preview.styleSheet()
    assert spec_for(tema).base in folha, tema
    assert spec_for(tema).text in folha, tema
    dialog.close()

@pytest.mark.parametrize("tema", sorted(TEMAS_NOVOS))
def test_dialogo_comeca_com_a_cor_do_tema(app: QApplication, tema: str) -> None:
    from src.panels.settings_dialog import SettingsDialog  # noqa: PLC0415

    dialog = SettingsDialog(Settings(theme=tema), lambda _s: None)
    spec = spec_for(tema)
    assert dialog.error_button.color() == QColor(spec.error)
    for categoria in CATEGORIES:
        assert dialog.highlight_buttons[categoria].color() == QColor(spec.syntax[categoria])
    assert dialog.settings().theme == tema
    dialog.close()

def test_dialogo_troca_de_tema_respeita_a_cor_manual(app: QApplication) -> None:
    from src.panels.settings_dialog import SettingsDialog  # noqa: PLC0415

    dialog = SettingsDialog(Settings(theme=THEME_LIGHT), lambda _s: None)
    dialog.highlight_auto[CATEGORY_COMMENT].setChecked(False)
    dialog.highlight_buttons[CATEGORY_COMMENT].set_color(QColor("#123456"))
    dialog.error_auto.setChecked(False)
    dialog.error_button.set_color(QColor("#654321"))

    dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData(THEME_CONTRAST))

    assert dialog.highlight_buttons[CATEGORY_COMMENT].color() == QColor("#123456")
    assert dialog.error_button.color() == QColor("#654321")
    assert dialog.settings().comment_color == "#123456"
    assert dialog.settings().error_color == "#654321"
    dialog.close()

def test_dialogo_troca_de_tema_repoe_a_semente_livre(app: QApplication) -> None:
    from src.panels.settings_dialog import SettingsDialog  # noqa: PLC0415

    dialog = SettingsDialog(Settings(theme=THEME_LIGHT), lambda _s: None)
    dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData(THEME_FOREST))

    assert dialog.error_button.color() == QColor(FOREST.error)
    assert dialog.highlight_buttons[CATEGORY_COMMENT].color() == QColor(
        FOREST.syntax[CATEGORY_COMMENT]
    )
    assert dialog.current_line_button.color() != dialog.highlight_preview.palette().color(
        QPalette.ColorRole.Base
    )
    dialog.close()

def test_tema_desconhecido_gravado_cai_no_padrao(tmp_path: Path) -> None:
    caminho = tmp_path / "settings.json"
    caminho.write_text(json.dumps({"theme": "inexistente"}), encoding="utf-8")
    assert load_settings(caminho).theme == THEME_SYSTEM

def test_tema_com_caixa_preservada_e_aceito(tmp_path: Path) -> None:
    caminho = tmp_path / "settings.json"
    caminho.write_text(json.dumps({"theme": THEME_OCEAN}), encoding="utf-8")
    assert load_settings(caminho).theme == THEME_OCEAN
