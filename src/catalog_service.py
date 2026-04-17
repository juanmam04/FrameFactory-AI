"""Catalogs cerrados para SaaS MVP (sin uploads de usuario)."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from .config_loader import BASE, get_character_references

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
        "name": "Estudio oscuro",
        "asset_uri": "assets/backgrounds/dark_studio.png",
    },
    "soft_gradient": {
        "id": "soft_gradient",
        "name": "Degradado suave",
        "asset_uri": "assets/backgrounds/soft_gradient.png",
    },
}

VOICES = {
    "male_sharp": {
        "id": "male_sharp",
        "name": "ElevenLabs (usa ELEVENLABS_VOICE_ID del .env)",
        "provider": "elevenlabs",
        "elevenlabs_voice_id": None,
    },
    "openai_alloy": {
        "id": "openai_alloy",
        "name": "OpenAI · Alloy",
        "provider": "openai",
        "openai_voice": "alloy",
    },
    "openai_nova": {
        "id": "openai_nova",
        "name": "OpenAI · Nova",
        "provider": "openai",
        "openai_voice": "nova",
    },
    "openai_echo": {
        "id": "openai_echo",
        "name": "OpenAI · Echo",
        "provider": "openai",
        "openai_voice": "echo",
    },
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


def resolve_character_id(character_id: str | None) -> dict:
    cid = (character_id or "").strip()
    return CHARACTERS.get(cid) or CHARACTERS["cartoon_biz_1"]


def resolve_background_id(background_id: str | None) -> dict:
    bid = (background_id or "").strip()
    return BACKGROUNDS.get(bid) or BACKGROUNDS["dark_studio"]


def resolve_voice_id(voice_id: str | None) -> dict:
    vid = (voice_id or "").strip()
    return VOICES.get(vid) or VOICES["male_sharp"]


def resolve_saas_character_image_path(catalog_image: Path) -> Path:
    """
    PNG del personaje para el MVP (overlay en clips):
    1) SAAS_CHARACTER_PNG o MVP_CHARACTER_PNG en .env (absoluta o relativa al proyecto)
    2) character_reference.* de visual_bible.yaml si el archivo existe
    3) catalog_image (p. ej. assets/characters/biz1.png)
    """
    for env_key in ("SAAS_CHARACTER_PNG", "MVP_CHARACTER_PNG"):
        raw = (os.getenv(env_key) or "").strip().strip('"').strip("'")
        if not raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = (BASE / raw).resolve()
        else:
            p = p.resolve()
        if p.is_file() and p.stat().st_size > 0:
            return p
    try:
        refs = get_character_references() or {}
        for key in ("front", "side", "closeup"):
            rel = refs.get(key)
            if isinstance(rel, str) and rel.strip():
                p = (BASE / rel.strip()).resolve()
                if p.is_file() and p.stat().st_size > 0:
                    return p
        for rel in refs.values():
            if isinstance(rel, str) and rel.strip():
                p = (BASE / rel.strip()).resolve()
                if p.is_file() and p.stat().st_size > 0:
                    return p
    except Exception:
        pass
    return catalog_image


def materialize_background_image(background: dict, scratch_dir: Path) -> Path:
    """
    Ruta a PNG (o JPG) usable como capa de fondo: archivo estático, primer frame de .mp4,
    o fallback a dark_studio.png tras ensure_default_catalog_assets().
    """
    ensure_default_catalog_assets()
    scratch_dir.mkdir(parents=True, exist_ok=True)
    rel = str(background.get("asset_uri") or "").strip()
    uri = BASE / rel if rel else Path()
    if uri.exists() and uri.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        return uri
    if uri.exists() and uri.suffix.lower() == ".mp4" and shutil.which("ffmpeg"):
        out = scratch_dir / f"_bg_frame_{background.get('id', 'bg')}.png"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(uri.resolve()),
                    "-vf",
                    "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720",
                    "-frames:v",
                    "1",
                    str(out.resolve()),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception:
            out = Path()
        if out.exists() and out.stat().st_size > 0:
            return out
    return BASE / "assets" / "backgrounds" / "dark_studio.png"


def ensure_catalog_dirs() -> tuple[Path, Path]:
    """Asegura estructura mínima de assets para el MVP."""
    chars_dir = BASE / "assets" / "characters"
    bgs_dir = BASE / "assets" / "backgrounds"
    chars_dir.mkdir(parents=True, exist_ok=True)
    bgs_dir.mkdir(parents=True, exist_ok=True)
    return chars_dir, bgs_dir


def ensure_default_catalog_assets() -> None:
    """PNG mínimos para personaje y fondos si faltan (evita clips vacíos o negros)."""
    ensure_catalog_dirs()
    biz = BASE / "assets" / "characters" / "biz1.png"
    if not biz.exists():
        img = Image.new("RGB", (1280, 720), (32, 36, 48))
        d = ImageDraw.Draw(img)
        d.ellipse((480, 100, 800, 420), fill=(245, 245, 250), outline=(18, 18, 24), width=5)
        d.rectangle((520, 420, 760, 640), fill=(245, 245, 250), outline=(18, 18, 24), width=4)
        d.line([(640, 420), (560, 520), (640, 480), (720, 520), (640, 420)], fill=(18, 18, 24), width=5)
        d.text((420, 660), "Personaje catálogo (placeholder)", fill=(200, 200, 210))
        biz.parent.mkdir(parents=True, exist_ok=True)
        img.save(biz, format="PNG")

    dark = BASE / "assets" / "backgrounds" / "dark_studio.png"
    if not dark.exists():
        img = Image.new("RGB", (1280, 720), (14, 14, 22))
        d = ImageDraw.Draw(img)
        for y in range(0, 720, 40):
            d.line([(0, y), (1280, y)], fill=(26, 26, 38), width=1)
        d.rectangle((80, 80, 1200, 640), outline=(55, 55, 72), width=3)
        d.text((100, 100), "Estudio (placeholder)", fill=(120, 120, 140))
        dark.parent.mkdir(parents=True, exist_ok=True)
        img.save(dark, format="PNG")

    grad = BASE / "assets" / "backgrounds" / "soft_gradient.png"
    if not grad.exists():
        img = Image.new("RGB", (1280, 720))
        px = img.load()
        for y in range(720):
            t = y / 719.0
            r = int(40 + t * 80)
            g = int(50 + t * 60)
            b = int(90 + t * 40)
            for x in range(1280):
                px[x, y] = (r, g, b)
        grad.parent.mkdir(parents=True, exist_ok=True)
        img.save(grad, format="PNG")
