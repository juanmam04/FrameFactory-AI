#!/usr/bin/env python3
"""
Prueba por consola del flujo REAL del producto:

  Guion (OpenAI) → escenas → beats visuales → FrameSpecs → [opcional] imágenes (Replicate)

Los otros scripts (test_pipeline_v2.py, test_multi_theme_v2.py) NO generan guion:
solo prueban imágenes con escenas inventadas en código.

Uso (desde la raíz del repo):
  venv/bin/python scripts/test_consola_pipeline_completo.py --tema "POV: sos piloto comercial"
  venv/bin/python scripts/test_consola_pipeline_completo.py --tema "POV hacker" --imagen --max-beats 4
  venv/bin/python scripts/test_consola_pipeline_completo.py --tema "POV" --imagenes-todas --max-beats 4

Salida:
  - Carpeta: test/console_run/<nombre_proyecto>/
    - guion.txt
    - resumen.txt
    - beats_prompt.json (export rápido)
  - Si --imagen: imagen_primer_beat.png (solo el primer beat; costo API bajo)
  - Si --imagenes-todas: carpeta imagenes/ con escena_0001.png… (mismo motor que el pipeline; costo API alto)

Requiere: OPENAI_API_KEY en .env. Para --imagen / --imagenes-todas: REPLICATE_API_TOKEN (y opcional REPLICATE_FORCE_KONTEXT=0 si no tenés PNG de referencia).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def _slug(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)[:60]
    return re.sub(r"[-\s]+", "_", s).strip("_") or "proyecto"


def main() -> None:
    parser = argparse.ArgumentParser(description="Guion → escenas → beats → [imagen] por consola")
    parser.add_argument("--tema", type=str, required=True, help="Tema / idea del video POV")
    parser.add_argument("--target-words", type=int, default=320, help="Palabras objetivo del guion (default 320)")
    parser.add_argument("--max-beats", type=int, default=6, help="Tope de beats visuales a generar")
    img = parser.add_mutually_exclusive_group()
    img.add_argument("--imagen", action="store_true", help="Generar solo la imagen del primer beat (Replicate)")
    img.add_argument(
        "--imagenes-todas",
        action="store_true",
        help="Generar todas las escenas con validación/regeneración (mismo código que pipeline)",
    )
    parser.add_argument("--attempts-per-frame", type=int, default=None, help="Intentos por frame (default: env ATTEMPTS_PER_FRAME o 4)")
    parser.add_argument("--segundos-por-imagen", type=float, default=5.0)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("ERROR: Falta OPENAI_API_KEY en .env para generar el guion.")
        sys.exit(1)

    os.environ.setdefault("REPLICATE_FORCE_KONTEXT", "0")

    from src.config_loader import BASE
    from src.frame_director import beats_a_frame_specs
    from src.frame_image_pipeline import generar_imagenes_desde_frame_specs
    from src.frame_prompt_builder import prompt_desde_frame_spec
    from src.frame_spec import guardar_frame_specs
    from src.image_generator import generar_imagen
    from src.pipeline import sanitizar_nombre_proyecto
    from src.scene_splitter import dividir_en_escenas
    from src.script_generator import generar_guion, guardar_guion
    from src.visual_beats import generar_beats_para_escenas, guardar_beats

    tema = args.tema.strip()
    proy = sanitizar_nombre_proyecto(_slug(tema))
    out = BASE / "test" / "console_run" / proy
    out.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 72)
    print("FRAMEFACTORY — prueba consola: guion + escenas + beats (+ imagen opcional)")
    print("=" * 72)
    print(f"Tema: {tema}")
    print(f"Carpeta de salida: {out}\n")

    print("→ Generando guion con OpenAI…")
    guion_texto, word_count, estimated_minutes = generar_guion(
        tema,
        target_words=args.target_words,
        plantilla="explicativo",
        segundos_por_imagen=args.segundos_por_imagen,
    )
    guardar_guion(guion_texto, proy)
    (out / "guion.txt").write_text(guion_texto, encoding="utf-8")
    print(f"   Palabras: {word_count} (~{estimated_minutes:.1f} min estimados)")

    escenas = dividir_en_escenas(guion_texto, segundos_por_imagen=args.segundos_por_imagen)
    print(f"→ Escenas divididas: {len(escenas)}")

    lines_escenas = []
    for e in escenas:
        lines_escenas.append(f"--- Escena {e.numero} ({e.duracion_segundos}s) ---\n{e.texto}\n")
    (out / "escenas.txt").write_text("\n".join(lines_escenas), encoding="utf-8")

    print(f"→ Generando beats visuales (máx {args.max_beats})…")
    beats = generar_beats_para_escenas(
        escenas,
        tema=tema,
        max_beats_total=args.max_beats,
    )
    print(f"   Beats generados: {len(beats)}")
    guardar_beats(beats, proy)

    beats_dump = [
        {
            "beat_id": b.beat_id,
            "scene": b.scene,
            "original_text": b.original_text[:300],
            "action": b.action[:200],
            "location": b.location,
            "emotion": b.emotion,
        }
        for b in beats
    ]
    (out / "beats_resumen.json").write_text(
        json.dumps(beats_dump, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    frame_specs = beats_a_frame_specs(beats)
    guardar_frame_specs(frame_specs, proy)
    (out / "framespecs_count.txt").write_text(f"{len(frame_specs)} FrameSpecs\n", encoding="utf-8")

    resumen = [
        f"tema: {tema}",
        f"proyecto: {proy}",
        f"palabras_guion: {word_count}",
        f"escenas: {len(escenas)}",
        f"beats: {len(beats)}",
        f"framespecs: {len(frame_specs)}",
        "",
        "Primeros beats (texto):",
    ]
    for b in beats[:5]:
        resumen.append(f"  - [{b.beat_id}] {b.original_text[:120]}…")
    (out / "resumen.txt").write_text("\n".join(resumen), encoding="utf-8")

    print("\n--- Resumen (primer beat) ---")
    if beats:
        b0 = beats[0]
        print(f"  Beat 1: {b0.original_text[:200]}…")
    if frame_specs:
        s0 = frame_specs[0]
        print(f"  FrameSpec 1 event_core: {s0.event_core[:200]}…")

    if args.imagen:
        if not os.getenv("REPLICATE_API_TOKEN", "").strip():
            print("\nERROR: --imagen requiere REPLICATE_API_TOKEN en .env")
            sys.exit(1)
        spec = frame_specs[0]
        prompt = prompt_desde_frame_spec(spec)
        img_path = out / "imagen_primer_beat.png"
        print("\n→ Generando imagen del primer beat (Replicate)…")
        time.sleep(2)
        img = generar_imagen(
            prompt=prompt,
            escena_num=1,
            carpeta=out,
            width=1920,
            height=1080,
            expression_key=spec.expression_key,
        )
        if img and img.exists():
            import shutil

            shutil.copy2(img, img_path)
            print(f"   Guardada: {img_path}")
        else:
            print("   Falló generar_imagen (revisá token / crédito Replicate).")
    elif args.imagenes_todas:
        if not os.getenv("REPLICATE_API_TOKEN", "").strip():
            print("\nERROR: --imagenes-todas requiere REPLICATE_API_TOKEN en .env")
            sys.exit(1)
        carpeta_imgs = out / "imagenes"
        print("\n→ Generando todas las imágenes (pipeline V2: validación + regeneración)…")
        time.sleep(2)
        paths, metrics, _ = generar_imagenes_desde_frame_specs(
            frame_specs,
            proy,
            width=1920,
            height=1080,
            attempts_per_frame=args.attempts_per_frame,
            carpeta_raiz=carpeta_imgs,
        )
        (out / "frame_metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"   Imágenes escritas: {len(paths)} en {carpeta_imgs}")
        print(f"   Métricas: {out / 'frame_metrics.json'}")
    else:
        print("\n(Sin --imagen ni --imagenes-todas: no se llamó a Replicate.)")

    print(f"\n✅ Listo. Archivos en:\n   {out}\n")
    print("Archivos: guion.txt, escenas.txt, beats_resumen.json, resumen.txt")
    if args.imagen:
        print("            imagen_primer_beat.png (si la API respondió)")
    if args.imagenes_todas:
        print("            imagenes/escena_*.png, frame_metrics.json")


if __name__ == "__main__":
    main()
