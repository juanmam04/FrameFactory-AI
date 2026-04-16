"""Catalogs cerrados para SaaS MVP (sin uploads de usuario)."""
from __future__ import annotations

from pathlib import Path

from .config_loader import BASE

CHARACTERS = {
    "cartoon_biz_1": {
        "id": "cartoon_biz_1",
        "name": "Business Cartoon",
        "base_image_uri": "assets/characters/biz1.png",
    }
}

BACKGROUNDS = {
    "dark_studio": {
        "id": "dark_studio",
        "asset_uri": "assets/backgrounds/dark.mp4",
    }
}

VOICES = {
    "male_sharp": {
        "id": "male_sharp",
        "provider": "elevenlabs",
    }
}


def get_character(id: str) -> dict:
    item = CHARACTERS.get(id)
    if not item:
        raise KeyError(f"Character no encontrado: {id}")
    return item


def get_background(id: str) -> dict:
    item = BACKGROUNDS.get(id)
    if not item:
        raise KeyError(f"Background no encontrado: {id}")
    return item


def get_voice(id: str) -> dict:
    item = VOICES.get(id)
    if not item:
        raise KeyError(f"Voice no encontrada: {id}")
    return item


def ensure_catalog_dirs() -> tuple[Path, Path]:
    """Asegura estructura mínima de assets para el MVP."""
    chars_dir = BASE / "assets" / "characters"
    bgs_dir = BASE / "assets" / "backgrounds"
    chars_dir.mkdir(parents=True, exist_ok=True)
    bgs_dir.mkdir(parents=True, exist_ok=True)
    return chars_dir, bgs_dir
