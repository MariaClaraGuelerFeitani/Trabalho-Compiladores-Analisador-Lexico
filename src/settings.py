
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import get_type_hints

from PySide6.QtCore import QStandardPaths

from .config import (
    COLOR_CONSOLE_BACKGROUND,
    COLOR_CONSOLE_FOREGROUND,
    EDITOR_FONT_FAMILY,
    EDITOR_FONT_SIZE,
    default_background_image,
)

THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_CHOICES = (THEME_SYSTEM, THEME_LIGHT, THEME_DARK)

THEME_LABELS = {
    THEME_SYSTEM: "Sistema",
    THEME_LIGHT: "Claro",
    THEME_DARK: "Escuro",
}

MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 48

MIN_BACKGROUND_OPACITY = 0
MAX_BACKGROUND_OPACITY = 100

INT_LIMITS = {
    "font_size": (MIN_FONT_SIZE, MAX_FONT_SIZE),
    "background_image_opacity": (MIN_BACKGROUND_OPACITY, MAX_BACKGROUND_OPACITY),
}


@dataclass
class Settings:

    theme: str = THEME_SYSTEM
    font_family: str = EDITOR_FONT_FAMILY
    font_size: int = EDITOR_FONT_SIZE
    current_line_color: str = ""
    error_color: str = ""
    keyword_color: str = ""
    primitive_type_color: str = ""
    number_color: str = ""
    literal_color: str = ""
    comment_color: str = ""
    background_image_path: str = field(default_factory=default_background_image)
    background_image_opacity: int = 10
    console_background: str = COLOR_CONSOLE_BACKGROUND
    console_foreground: str = COLOR_CONSOLE_FOREGROUND

    def copy(self) -> "Settings":
        return Settings(**asdict(self))

    def is_default_font(self) -> bool:
        return self.font_family == EDITOR_FONT_FAMILY and self.font_size == EDITOR_FONT_SIZE


def default_settings_path() -> Path:
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    return Path(base) / "settings.json"


def load_settings(path: Path | None = None) -> Settings:
    target = path or default_settings_path()
    if not target.is_file():
        return Settings()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()

    known = get_type_hints(Settings)
    values = {}
    for key, value in raw.items():
        expected = known.get(key)
        if expected is None:
            continue
        if expected is int:
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            low, high = INT_LIMITS.get(key, (MIN_FONT_SIZE, MAX_FONT_SIZE))
            value = max(low, min(high, value))
        elif expected is str:
            if not isinstance(value, str):
                continue
        else:
            continue
        values[key] = value

    settings = Settings(**values)
    if settings.theme not in THEME_CHOICES:
        settings.theme = THEME_SYSTEM
    return settings


def save_settings(settings: Settings, path: Path | None = None) -> bool:
    target = path or default_settings_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    except OSError:
        return False
    return True
