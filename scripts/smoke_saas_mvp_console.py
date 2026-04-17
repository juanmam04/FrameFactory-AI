#!/usr/bin/env python3
"""
Smoke del MVP SaaS sin APIs: mocks de guion/plan/voz y FFmpeg real.

  .venv/bin/python scripts/smoke_saas_mvp_console.py

Requiere: ffmpeg en PATH. No llama OpenAI ni TTS.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    # Forzar fallback local (evita HeyGen/API si el .env define otro proveedor).
    os.environ["CHARACTER_ANIMATOR_PROVIDER"] = "ffmpeg_static"

    import shutil

    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg no está en PATH", file=sys.stderr)
        sys.exit(1)

    from src.voice_generator import OUTPUT_AUDIO

    def fake_guion(*a, **k):
        return "Este eres tú. Primera escena. Segunda escena distinta.", 8, 0.1

    def fake_plan(_script: str):
        return [
            {"id": "scene_0001", "text": "Bloque uno: narración corta."},
            {"id": "scene_0002", "text": "Bloque dos: texto completamente diferente para el audio."},
        ]

    def fake_annotate(blocks, *a, **k):
        return blocks

    def fake_generar_voz(texto: str, nombre_archivo: str = "n", formato: str = "mp3", velocidad: float = 1.0):
        OUTPUT_AUDIO.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_AUDIO / f"{nombre_archivo}.{formato}"
        dur = 0.25 + (len(texto) % 50) * 0.02
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=mono",
                "-t",
                str(dur),
                "-c:a",
                "libmp3lame",
                "-q:a",
                "9",
                str(path),
            ],
            check=True,
            capture_output=True,
        )
        return path

    with (
        patch("src.pipeline.generar_guion", fake_guion),
        patch("src.pipeline.plan_scenes", fake_plan),
        patch("src.pipeline.annotate_blocks_with_editing", fake_annotate),
        patch("src.pipeline.generar_voz", fake_generar_voz),
    ):
        from src.pipeline import run_saas_mvp

        out = run_saas_mvp("smoke consola MVP", use_env_music_if_no_upload=False)
        print("Video:", out.resolve())

    def _dur(p: Path) -> float:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(p),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(r.stdout.strip())

    c1, c2 = ROOT / "output" / "clip_0001.mp4", ROOT / "output" / "clip_0002.mp4"
    d1, d2 = _dur(c1), _dur(c2)
    if abs(d1 - d2) <= 0.05:
        print("ERROR: clips de duración casi idéntica (esperado audio distinto por bloque)", file=sys.stderr)
        sys.exit(1)
    print("Duraciones clip_0001 / clip_0002:", d1, d2)
    print("OK smoke_saas_mvp")


if __name__ == "__main__":
    main()
