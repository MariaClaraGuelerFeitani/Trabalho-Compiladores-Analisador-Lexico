
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from .settings import THEME_DARK, THEME_LIGHT, THEME_SYSTEM

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
)

THEMES: dict[str, ThemeSpec] = {THEME_LIGHT: LIGHT, THEME_DARK: DARK}


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
