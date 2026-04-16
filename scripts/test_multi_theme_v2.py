#!/usr/bin/env python3
"""
Prueba consola: varios beats con temas distintos → FrameSpec → imagen + validación VLM.

Sin guion largo de OpenAI (ideal para no esperar 15–20 min por prueba):
  TEST_THEMES_MAX=1 python scripts/test_multi_theme_v2.py
  # Con cuenta Replicate “tier bajo” (~6 req/min), dejá espaciado por defecto del repo (≈11s) o:
  REPLICATE_MIN_INTERVAL_SEC=11 TEST_THEMES_MAX=1 python scripts/test_multi_theme_v2.py

Solo ver prompts (sin Replicate ni VLM):
  python scripts/test_multi_theme_v2.py --dry-run

Varios temas:
  TEST_THEMES_MAX=2 python scripts/test_multi_theme_v2.py

Requiere .env: REPLICATE_API_TOKEN (imagen) y OPENAI_API_KEY (caption VLM en validar_frame).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
# Pruebas por consola: permitir FLUX sin PNG de referencia si no está en disco
os.environ.setdefault("REPLICATE_FORCE_KONTEXT", "0")

from src.config_loader import BASE
from src.frame_director import beats_a_frame_specs
from src.frame_prompt_builder import prompt_desde_frame_spec
from src.frame_validator import validar_frame
from src.image_generator import generar_imagen
from src.visual_beats import VisualBeat


def _beat(
    bid: int,
    scene: int,
    original: str,
    action: str,
    location: str,
    emotion: str = "tensión",
) -> VisualBeat:
    return VisualBeat(
        beat_id=bid,
        scene=scene,
        original_text=original,
        action=action,
        emotion=emotion,
        context=original[:400],
        location=location,
        time_of_day="noche",
        shot_role="action",
        camera_type="POV",
        camera_position="",
        camera_distance="medium",
        importance="alta",
    )


# Cuatro “mini guiones” con vocación de escena visual clara y distinta
THEMES: list[tuple[str, list[VisualBeat]]] = [
    (
        "callejon_herida",
        [
            _beat(
                1,
                1,
                "Llegás al callejón y ves a tu amigo desangrándose en el suelo.",
                "corres y te agachás junto al cuerpo; mano extendida hacia el herido",
                "callejón estrecho entre edificios, asfalto mojado",
                "shock",
            ),
        ],
    ),
    (
        "hacker_mision",
        [
            _beat(
                1,
                1,
                "Sos un hacker infiltrado: última ventana de código antes del fallo del firewall.",
                "teclea frenético; reflejo de la cara en el monitor",
                "habitación oscura con triple monitor y servidor",
                "tensión",
            ),
        ],
    ),
    (
        "futbol_estadio",
        [
            _beat(
                1,
                1,
                "Definición del campeonato: encarás el arco con el balón en el último minuto.",
                "dispara al arco; cuerpo en tensión máxima",
                "cancha de fútbol de estadio lleno, luces",
                "determinación",
            ),
        ],
    ),
    (
        "streamer_youtube",
        [
            _beat(
                1,
                1,
                "Directo con un millón de personas: leés la alerta de donación en el monitor.",
                "señala el monitor y abre la boca sorprendido",
                "habitación con micrófono, cámara y luces LED",
                "sorpresa",
            ),
        ],
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Solo imprimir prompts, sin Replicate")
    args = parser.parse_args()
    out_dir = BASE / "test" / "themes"
    out_dir.mkdir(parents=True, exist_ok=True)

    max_t = int(os.getenv("TEST_THEMES_MAX", "4"))
    subset = THEMES[:max_t]

    for idx, (theme_name, beats) in enumerate(subset):
        if idx > 0 and not args.dry_run:
            time.sleep(12)  # evitar 429 de Replicate (límite bajo con poco crédito)
        print("\n" + "=" * 72)
        print(f"TEMA: {theme_name}")
        print("=" * 72)
        specs = beats_a_frame_specs(beats)
        for spec in specs:
            prompt = prompt_desde_frame_spec(spec)
            print("\n--- PROMPT (primeros 1200 chars) ---\n")
            print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
            if args.dry_run:
                print("(dry-run: no se generó imagen)")
                continue
            escena_num = hash(theme_name) % 9000 + 1000
            img = generar_imagen(
                prompt=prompt,
                escena_num=escena_num,
                carpeta=out_dir,
                width=1920,
                height=1080,
                expression_key=spec.expression_key,
            )
            if not img:
                print("ERROR: generar_imagen devolvió None")
                continue
            dest = out_dir / f"{theme_name}_frame{spec.frame_id:04d}.png"
            import shutil

            shutil.copy2(img, dest)
            print(f"\nImagen: {dest}")
            res = validar_frame(spec=spec, image_path=dest, prev_image_path=None)
            print(f"is_valid={res.is_valid} score={res.score:.3f} event={res.event_match_score:.3f}")
            print(f"caption: {res.caption[:400]}..." if len(res.caption) > 400 else f"caption: {res.caption}")
            if res.reasons:
                for r in res.reasons[:6]:
                    print(f"  - {r}")

    print(f"\nListo. Salida en {out_dir}")


if __name__ == "__main__":
    main()
