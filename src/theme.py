
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from .settings import (
    THEME_CONTRAST,
    THEME_DARK,
    THEME_FOREST,
    THEME_LIGHT,
    THEME_OCEAN,
    THEME_SEPIA,
    THEME_SOLARIZED_DARK,
    THEME_SOLARIZED_LIGHT,
    THEME_SYSTEM,
)

APP_STYLE = "Fusion"


@dataclass(frozen=True)
class ThemeSpec:

    name: str
    window: str
    window_text: str
    base: str
    alternate_base: str
    text: str
    placeholder: str
    button: str
    button_text: str
    highlight: str
    highlighted_text: str
    tooltip_base: str
    tooltip_text: str
    disabled_text: str
    mid: str
    syntax: Mapping[str, str] = field(default_factory=dict)
    error: str = ""


def _cores(**cores: str) -> Mapping[str, str]:
    return MappingProxyType(dict(cores))


DARK = ThemeSpec(
    name="dark",
    window="#1e1e1e",
    window_text="#d4d4d4",
    base="#2d2d2d",
    alternate_base="#333333",
    text="#ffffff",
    placeholder="#8a8a8a",
    button="#3a3a3a",
    button_text="#e4e4e4",
    highlight="#0078d4",
    highlighted_text="#ffffff",
    tooltip_base="#2b2b2b",
    tooltip_text="#f0f0f0",
    disabled_text="#6b6b6b",
    mid="#4a4a4a",
    syntax=_cores(
        palavra_reservada="#569cd6",
        tipo_primario="#4ec9b0",
        numero="#d7ba7d",
        literal="#ce9178",
        comentario="#7ca668",
    ),
    error="#ff5252",
)

LIGHT = ThemeSpec(
    name="light",
    window="#f0f0f0",
    window_text="#1c1c1c",
    base="#ffffff",
    alternate_base="#f5f7fa",
    text="#1c1c1c",
    placeholder="#9aa4b2",
    button="#e6e6e6",
    button_text="#1c1c1c",
    highlight="#0078d4",
    highlighted_text="#ffffff",
    tooltip_base="#ffffdc",
    tooltip_text="#1c1c1c",
    disabled_text="#a0a0a0",
    mid="#c0c0c0",
    syntax=_cores(
        palavra_reservada="#0b5cad",
        tipo_primario="#0f7b7b",
        numero="#a05000",
        literal="#a31515",
        comentario="#5a8a4a",
    ),
    error="#c62828",
)

OCEAN = ThemeSpec(
    name="ocean",
    window="#1b2430",
    window_text="#cdd9e5",
    base="#16202b",
    alternate_base="#1e2a37",
    text="#e6edf3",
    placeholder="#7d8f9e",
    button="#26313d",
    button_text="#dbe6ef",
    highlight="#2f81f7",
    highlighted_text="#ffffff",
    tooltip_base="#22303c",
    tooltip_text="#e6edf3",
    disabled_text="#5f7180",
    mid="#3a4854",
    syntax=_cores(
        palavra_reservada="#7aa2f7",
        tipo_primario="#56d4dd",
        numero="#e0af68",
        literal="#f7768e",
        comentario="#5f7e97",
    ),
    error="#ff6b6b",
)

SEPIA = ThemeSpec(
    name="sepia",
    window="#f0e6d2",
    window_text="#3b2f22",
    base="#fbf4e4",
    alternate_base="#f4ead6",
    text="#3b2f22",
    placeholder="#a8977f",
    button="#e6d9bf",
    button_text="#3b2f22",
    highlight="#b5651d",
    highlighted_text="#ffffff",
    tooltip_base="#f7eeda",
    tooltip_text="#3b2f22",
    disabled_text="#b0a08a",
    mid="#d3c3a5",
    syntax=_cores(
        palavra_reservada="#a0522d",
        tipo_primario="#6b7b3a",
        numero="#8a6d1f",
        literal="#a13d2d",
        comentario="#7f8c72",
    ),
    error="#b3261e",
)

CONTRAST = ThemeSpec(
    name="contrast",
    window="#000000",
    window_text="#ffffff",
    base="#000000",
    alternate_base="#1a1a1a",
    text="#ffffff",
    placeholder="#b0b0b0",
    button="#1f1f1f",
    button_text="#ffffff",
    highlight="#ffd400",
    highlighted_text="#000000",
    tooltip_base="#1f1f1f",
    tooltip_text="#ffffff",
    disabled_text="#8a8a8a",
    mid="#6a6a6a",
    syntax=_cores(
        palavra_reservada="#ffd400",
        tipo_primario="#00e5ff",
        numero="#7cff7c",
        literal="#ff9d5c",
        comentario="#bdbdbd",
    ),
    error="#ff4d4d",
)

FOREST = ThemeSpec(
    name="forest",
    window="#17221b",
    window_text="#d7e6da",
    base="#101a14",
    alternate_base="#1a2620",
    text="#e3f0e6",
    placeholder="#7f968a",
    button="#22302a",
    button_text="#dceadf",
    highlight="#2e9e6b",
    highlighted_text="#06120c",
    tooltip_base="#1d2a23",
    tooltip_text="#e3f0e6",
    disabled_text="#61756a",
    mid="#33473c",
    syntax=_cores(
        palavra_reservada="#7fd6a5",
        tipo_primario="#6fd3b8",
        numero="#e3c46a",
        literal="#f0a882",
        comentario="#6f8f78",
    ),
    error="#ff7b72",
)

SOLARIZED_LIGHT = ThemeSpec(
    name="solarized_light",
    window="#eee8d5",
    window_text="#4a5c62",
    base="#fdf6e3",
    alternate_base="#f2ecd9",
    text="#586e75",
    placeholder="#93a1a1",
    button="#e4ddc8",
    button_text="#4a5c62",
    highlight="#268bd2",
    highlighted_text="#fdf6e3",
    tooltip_base="#fdf6e3",
    tooltip_text="#586e75",
    disabled_text="#a9b2ab",
    mid="#d3cbb4",
    syntax=_cores(
        palavra_reservada="#6e8000",
        tipo_primario="#207fa4",
        numero="#9a7400",
        literal="#1f8b84",
        comentario="#657b83",
    ),
    error="#c02c29",
)

SOLARIZED_DARK = ThemeSpec(
    name="solarized_dark",
    window="#073642",
    window_text="#93a1a1",
    base="#002b36",
    alternate_base="#0a4b58",
    text="#93a1a1",
    placeholder="#657b83",
    button="#0d4f5c",
    button_text="#b8c4c7",
    highlight="#268bd2",
    highlighted_text="#002b36",
    tooltip_base="#073642",
    tooltip_text="#eee8d5",
    disabled_text="#4d6a75",
    mid="#1b5563",
    syntax=_cores(
        palavra_reservada="#859900",
        tipo_primario="#268bd2",
        numero="#b58900",
        literal="#2aa198",
        comentario="#6c8f99",
    ),
    error="#dc322f",
)

THEMES: dict[str, ThemeSpec] = {
    THEME_LIGHT: LIGHT,
    THEME_DARK: DARK,
    THEME_OCEAN: OCEAN,
    THEME_SEPIA: SEPIA,
    THEME_CONTRAST: CONTRAST,
    THEME_FOREST: FOREST,
    THEME_SOLARIZED_LIGHT: SOLARIZED_LIGHT,
    THEME_SOLARIZED_DARK: SOLARIZED_DARK,
}

PALETTE_FIELDS: tuple[str, ...] = (
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


def build_palette(spec: ThemeSpec) -> QPalette:
    palette = QPalette()
    role = QPalette.ColorRole

    palette.setColor(role.Window, QColor(spec.window))
    palette.setColor(role.WindowText, QColor(spec.window_text))
    palette.setColor(role.Base, QColor(spec.base))
    palette.setColor(role.AlternateBase, QColor(spec.alternate_base))
    palette.setColor(role.Text, QColor(spec.text))
    palette.setColor(role.PlaceholderText, QColor(spec.placeholder))
    palette.setColor(role.Button, QColor(spec.button))
    palette.setColor(role.ButtonText, QColor(spec.button_text))
    palette.setColor(role.Highlight, QColor(spec.highlight))
    palette.setColor(role.HighlightedText, QColor(spec.highlighted_text))
    palette.setColor(role.ToolTipBase, QColor(spec.tooltip_base))
    palette.setColor(role.ToolTipText, QColor(spec.tooltip_text))
    palette.setColor(role.Mid, QColor(spec.mid))
    palette.setColor(role.Link, QColor(spec.highlight))

    disabled = QPalette.ColorGroup.Disabled
    for name in ("WindowText", "Text", "ButtonText", "HighlightedText"):
        palette.setColor(disabled, getattr(role, name), QColor(spec.disabled_text))
    palette.setColor(disabled, role.Highlight, QColor(spec.button))
    return palette


def spec_for(theme: str) -> ThemeSpec | None:
    return THEMES.get(theme)


def is_dark(spec: ThemeSpec) -> bool:
    return QColor(spec.base).lightness() < 128


_system_appearance: dict[str, object] = {}


def remember_system_appearance(app: QApplication) -> None:
    if app is None:
        return
    _system_appearance["style"] = app.style().objectName()
    _system_appearance["palette"] = QPalette(app.palette())


def apply_theme(app: QApplication | None, theme: str) -> None:
    if app is None:
        return

    if theme == THEME_SYSTEM:
        if "style" in _system_appearance:
            app.setStyle(str(_system_appearance["style"]))
            app.setPalette(_system_appearance["palette"])
        app.setStyleSheet("")
        return

    spec = spec_for(theme)
    if spec is None:
        return
    app.setStyle(APP_STYLE)
    app.setPalette(build_palette(spec))
    app.setStyleSheet("")
