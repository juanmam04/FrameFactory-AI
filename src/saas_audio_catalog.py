"""Catálogo local de música y SFX pensados para uso seguro en YouTube (p. ej. descargados de la Biblioteca de audio)."""
from __future__ import annotations

from pathlib import Path

from .config_loader import BASE

ROOT = BASE / "assets" / "saas_youtube_audio"
MUSIC_DIR = ROOT / "music"
SFX_DIR = ROOT / "sfx"
_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}


def _scan(dir_path: Path) -> list[Path]:
    if not dir_path.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(dir_path.iterdir()):
        if p.is_file() and p.suffix.lower() in _EXTENSIONS:
            out.append(p)
    return out


def list_safe_music() -> list[tuple[str, Path]]:
    """Etiqueta legible + ruta absoluta."""
    return [(p.stem.replace("_", " "), p) for p in _scan(MUSIC_DIR)]


def list_safe_sfx() -> list[tuple[str, Path]]:
    return [(p.stem.replace("_", " "), p) for p in _scan(SFX_DIR)]


def ensure_audio_dirs() -> None:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    SFX_DIR.mkdir(parents=True, exist_ok=True)
