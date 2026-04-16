#!/usr/bin/env python3
"""
Una sola imagen por consola (Replicate / Comfy según .env), sin guion ni beats.

Ejemplos (desde la raíz del repo):
  ./venv/bin/python scripts/generar_escena_replicate.py \\
    -p "POV: mirás tu reflejo en el espejo del baño, stickman, noche, tensión"

  ./venv/bin/python scripts/generar_escena_replicate.py -n 5 -p @prompt.txt

  REPLICATE_MIN_INTERVAL_SEC=0 ./venv/bin/python scripts/generar_escena_replicate.py -p "wide shot calle mojada"

Sin REPLICATE_API_TOKEN usa ComfyUI si está configurado y disponible.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generar una escena (un PNG) con el mismo motor que la app.")
    ap.add_argument(
        "-p",
        "--prompt",
        type=str,
        default="",
        help="Texto del prompt. Si empieza con @, se lee el archivo (ej. @mi_prompt.txt)",
    )
    ap.add_argument(
        "-n",
        "--numero",
        type=int,
        default=2,
        metavar="N",
        help="Número de escena (archivo escena_NNNN.png). Default: 2",
    )
    ap.add_argument(
        "-o",
        "--dir",
        type=Path,
        default=ROOT / "test" / "manual_scene",
        help="Carpeta de salida (default: test/manual_scene)",
    )
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument(
        "--expression-key",
        type=str,
        default=None,
        help="Clave opcional en character_reference (ej. side); si no, se usa front.",
    )
    ap.add_argument(
        "--text-only",
        action="store_true",
        help="Replicate: forzar FLUX solo texto (sin PNG de Kontext).",
    )
    args = ap.parse_args()

    raw = (args.prompt or "").strip()
    if raw.startswith("@"):
        path = Path(raw[1:]).expanduser()
        if not path.is_file():
            print(f"ERROR: no existe el archivo de prompt: {path}", file=sys.stderr)
            return 1
        prompt = path.read_text(encoding="utf-8").strip()
    else:
        prompt = raw

    if not prompt:
        print("ERROR: falta --prompt / -p (o archivo @ruta)", file=sys.stderr)
        return 1

    from src.image_generator import generar_imagen

    args.dir.mkdir(parents=True, exist_ok=True)
    print(f"→ Escena {args.numero} → {args.dir.resolve()}")
    print(f"→ Prompt ({len(prompt)} chars): {prompt[:200]}{'…' if len(prompt) > 200 else ''}")

    path = generar_imagen(
        prompt,
        args.numero,
        args.dir,
        width=args.width,
        height=args.height,
        expression_key=args.expression_key,
        replicate_text_only=bool(args.text_only),
    )
    if path and path.exists():
        print(f"✅ {path.resolve()}")
        return 0
    print("ERROR: generar_imagen no devolvió archivo.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
