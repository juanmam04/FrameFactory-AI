"""Proveedor MVP: clip de video desde imagen fija + audio usando FFmpeg."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def render_block(block: dict, audio_path: Path, character_image: Path, output_path: Path) -> Path:
    """
    Genera un clip mp4 reproducible:
    - loop de imagen de personaje
    - mezcla con audio
    - corta al más corto (-shortest)
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg no está instalado o no está en PATH.")
    if not character_image.exists():
        raise FileNotFoundError(f"No existe imagen de personaje: {character_image}")
    if not audio_path.exists():
        raise FileNotFoundError(f"No existe audio para bloque {block.get('id')}: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = (block.get("text") or "").strip()
    words = len(text.split()) if text else 8
    # Duración acotada por bloque para MVP (render rápido y estable).
    clip_seconds = max(2, min(6, int(round(words / 2.5))))

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(character_image.resolve()),
        "-i",
        str(audio_path.resolve()),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "24",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-t",
        str(clip_seconds),
        "-shortest",
        str(output_path.resolve()),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or str(e))[-500:]
        raise RuntimeError(f"FFmpeg falló en bloque {block.get('id')}: {msg}") from e
    return output_path
