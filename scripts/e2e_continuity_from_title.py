#!/usr/bin/env python3
"""
End-to-end de continuidad visual SOLO vía título:
title
  -> micro-guion automático (estrés de continuidad espacial)
  -> VisualBeat (con beat.location y beat.camera_type explícitos)
  -> prompts secuenciales (prompts_para_beats) con StoryboardState y debug JSON
  -> validaciones automáticas de continuidad (sin modelo de imagen)
  -> (opcional) 3 imágenes de prueba si hay backend disponible
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.image_generator import OUTPUT_IMAGES  # noqa: E402
from src.prompt_builder import prompts_para_beats  # noqa: E402
from src.scene_splitter import Escena  # noqa: E402
from src.storyboard_debug import extract_camera_line_from_prompt  # noqa: E402
from src.visual_beats import VisualBeat  # noqa: E402
from src.image_generator import generar_lote  # noqa: E402
from src.config_loader import BASE  # noqa: E402
from src.image_generator import _comfyui_disponible  # noqa: E402


def _slug(s: str) -> str:
    t = (s or "").strip().lower()
    t = re.sub(r"[^a-z0-9áéíóúüñ\s-]+", "", t, flags=re.I)
    t = re.sub(r"\s+", "_", t.strip())
    t = t[:60].strip("_")
    return t or "e2e_title"


def generate_micro_script_from_title(title: str) -> list[dict[str, Any]]:
    """
    Micro-guion determinista basado en el título (pero diseñado para forzar continuidad):
    A->A->B->B->C->C con exterior->interior y cambios de acción/emoción.
    """
    # El título puede ser vago; igual hacemos una secuencia visual testeable.
    # Si el título contiene palabras clave, ajustamos ligeramente acción/emoción.
    t = (title or "").lower()
    if "mister" in t or "misterio" in t or "spy" in t:
        fear_word = "tensión"
        urgency_action = "camina rápido, mira atrás, miedo"
    elif "persec" in t or "corre" in t or "run" in t:
        fear_word = "tenso"
        urgency_action = "corre, respira agitado, miedo"
    else:
        fear_word = "tenso"
        urgency_action = "corre, respira agitado, miedo"

    # Locaciones concretas (deben ser distinguibles y repetidas consecutivamente)
    A = "calle oscura con neones"
    B = "pasillo del edificio"
    C = "living del apartamento con sofa"

    # 6 escenas: A, A, B, B, C, C
    return [
        {
            "scene_idx": 1,
            "location": A,
            "camera_type": "wide_shot",
            "action": urgency_action,
            "original_text": "En la calle oscura con neones, el protagonista corre y respira agitado, con miedo.",
            "emotion": "tensión",
        },
        {
            "scene_idx": 2,
            "location": A,
            "camera_type": "medium_shot",
            "action": "se detiene un segundo, mira alrededor, la tensión aumenta, incertidumbre",
            "original_text": "Sigue en la misma calle con neones; se detiene, mira alrededor y traga saliva con preocupación.",
            "emotion": "preocupación",
        },
        {
            "scene_idx": 3,
            "location": B,
            "camera_type": "wide_shot",
            "action": "entra al edificio, camina rápido por el pasillo, pasos detrás",
            "original_text": "Entra al edificio y se mete al pasillo; escucha pasos detrás y acelera el paso.",
            "emotion": "alarma",
        },
        {
            "scene_idx": 4,
            "location": B,
            "camera_type": "wide_shot",  # repetida a propósito para forzar anti-repeat en resolved_camera
            "action": "avanza por el pasillo, mira una puerta entreabierta, la tensión se vuelve amenaza",
            "original_text": "Avanza por el pasillo del edificio; mira una puerta entreabierta y siente amenaza cerca.",
            "emotion": "amenaza",
        },
        {
            "scene_idx": 5,
            "location": C,
            "camera_type": "close_up",
            "action": "llega al living, respira aliviado, sostiene el teléfono, shock",
            "original_text": "Llega al living del apartamento; abre la puerta y queda quieto, en shock, con el teléfono en la mano.",
            "emotion": "shock",
        },
        {
            "scene_idx": 6,
            "location": C,
            "camera_type": "close_up",  # repetida a propósito
            "action": "se sienta en el sofa, mira el teléfono, la respiración baja, alivio mezclado con dudas",
            "original_text": "Se sienta en el sofa del living y mira el teléfono; la tensión baja lentamente, pero aún duda.",
            "emotion": "alivio",
        },
    ]


def beats_from_micro_script(script: list[dict[str, Any]]) -> list[VisualBeat]:
    beats: list[VisualBeat] = []
    for sc in script:
        bid = int(sc["scene_idx"])
        beat = VisualBeat(
            beat_id=bid,
            scene=bid,  # para compat; el continuity resuelve por orden en prompts_para_beats
            original_text=sc["original_text"],
            action=sc["action"],
            emotion=sc["emotion"],
            context="",
            location=sc["location"],
            time_of_day="noche",
            shot_role="action",
            camera_type=sc["camera_type"],
            camera_position="frontal",
            camera_distance="media",
            importance="normal",
            act=1,
        )
        beats.append(beat)
    return beats


def load_debug_json(debug_dir: Path, n: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for beat_id in range(1, n + 1):
        p = debug_dir / f"scene_{beat_id:04d}.json"
        if not p.exists():
            raise FileNotFoundError(f"Falta debug JSON: {p}")
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def locked_signature_from_prompt(prompt: str) -> str:
    # En prompts secuenciales aparece una línea "Locked appearance: ..."
    m = re.search(r"Locked appearance:\s*(.+)\n", prompt)
    return m.group(1).strip() if m else ""


def camera_from_prompt_final(prompt: str) -> str:
    return extract_camera_line_from_prompt(prompt).strip().lower()


def resolved_camera_from_debug(d: dict[str, Any]) -> str:
    return (d["resolved_context"]["resolved_camera"] or "").strip().lower()


def run_validations(script: list[dict[str, Any]], debug: list[dict[str, Any]]) -> dict[str, Any]:
    results: dict[str, Any] = {"ok": True, "checks": []}
    # 1) Continuidad de locación N->N+1 por beat.location explícita
    for i in range(len(script) - 1):
        expected_same = script[i]["location"] == script[i + 1]["location"]
        ctx_cur = debug[i]["resolved_context"]
        ctx_next = debug[i + 1]["resolved_context"]
        same_loc = (ctx_cur["resolved_location"] == ctx_next["resolved_location"]) or (
            ctx_cur["location_changed"] is False and ctx_next["location_changed"] is False
        )

        if expected_same:
            cond = same_loc
            msg = f"Scene {i+1}->{i+2}: misma location => resolved_location debería mantenerse."
        else:
            cond = ctx_next["location_changed"] is True
            msg = f"Scene {i+1}->{i+2}: cambio de location => location_changed debe ser true."

        results["checks"].append(
            {"type": "location_continuity", "i": i, "expected_same": expected_same, "ok": bool(cond), "msg": msg}
        )
        results["ok"] = results["ok"] and bool(cond)

    # 2) Prompt incluye bloque de continuidad explícito
    for i, d in enumerate(debug):
        ok = "CONTINUITY FROM PREVIOUS SCENE" in (d["prompt_final"] or "")
        results["checks"].append(
            {"type": "continuity_block_present", "i": i, "ok": ok, "msg": f"Continuity block en prompt scene {i+1}."}
        )
        results["ok"] = results["ok"] and bool(ok)

    # 3) Cámara: el prompt final debe coincidir con resolved_camera
    for i, d in enumerate(debug):
        cam_prompt = camera_from_prompt_final(d["prompt_final"])
        cam_resolved = resolved_camera_from_debug(d)
        ok = (cam_prompt == cam_resolved) or (cam_resolved and cam_resolved in cam_prompt)
        results["checks"].append(
            {
                "type": "camera_matches_resolved",
                "i": i,
                "ok": ok,
                "msg": f"CAMERA efectiva coincide con resolved_camera (scene {i+1}).",
                "cam_prompt": cam_prompt,
                "cam_resolved": cam_resolved,
            }
        )
        results["ok"] = results["ok"] and bool(ok)

    # 4) Protagonista: locked signature estable en todas las escenas
    sigs = [locked_signature_from_prompt(d["prompt_final"]) for d in debug]
    base = sigs[0]
    for i, s in enumerate(sigs):
        ok = (s == base) and bool(s)
        results["checks"].append(
            {"type": "protagonist_signature_stable", "i": i, "ok": ok, "msg": f"Protagonist lock estable en scene {i+1}."}
        )
        results["ok"] = results["ok"] and bool(ok)

    # 5) Overlay simbólico incompatible con exterior: validar que en calle no aparezcan props de interior
    street_indices = [0, 1]  # escenas 1 y 2 son exteriores (A)
    for i in street_indices:
        p = (debug[i]["prompt_final"] or "").lower()
        forbidden = ["empty chair", "single desk lamp", "desk lamp", "empty_chair"]
        ok = not any(x in p for x in forbidden)
        results["checks"].append(
            {"type": "symbolic_overlay_filtered_for_exterior", "i": i, "ok": ok, "msg": f"Overlay de interior filtrado en scene {i+1}."}
        )
        results["ok"] = results["ok"] and bool(ok)

    # 6) beat.location no reemplazada por plantilla: resolved_location contiene beat.location textual
    for i, sc in enumerate(script):
        loc = sc["location"].lower()
        resolved = (debug[i]["resolved_context"]["resolved_location"] or "").lower()
        ok = loc in resolved or resolved in loc
        results["checks"].append(
            {"type": "beat_location_priority", "i": i, "ok": ok, "msg": f"resolved_location conserva beat.location en scene {i+1}."}
        )
        results["ok"] = results["ok"] and bool(ok)

    return results


def try_generate_images(beats: list[VisualBeat], prompts: list[tuple[VisualBeat, str, dict]], debug_dir: Path, title_slug: str) -> dict[str, Any]:
    # Intento mínimo: 3 imágenes (escenas 1..3) para estrés de identidad/cámara.
    img_dir = OUTPUT_IMAGES / title_slug / "e2e_probe_imgs"
    img_dir.mkdir(parents=True, exist_ok=True)

    # Ver backend disponible
    comfy_ok = False
    replicate_ok = False
    try:
        comfy_ok = bool(_comfyui_disponible())
    except Exception:
        comfy_ok = False

    # Si ComfyUI está arriba, preferimos eso. Replicate lo intentamos solo si no hay ComfyUI.
    # (No hacemos chequeo caro de replicate aquí.)
    backend = "comfyui" if comfy_ok else "replicate"

    # Preparar tuplas que acepta generar_lote: (Escena, prompt, expression_key, outfit_key, seed_material)
    # expression_key / outfit_key se mantienen legacy-compatible aunque en esta prueba no usamos expresiones.
    from src.prompt_builder import get_outfit_key_for_beat, emotion_to_expression_key

    escenas_con_prompts = []
    for i in range(min(3, len(beats))):
        beat, prompt, gen_meta = prompts[i]
        escena = Escena(numero=beat.beat_id, texto=beat.original_text, duracion_segundos=5.0)
        escenas_con_prompts.append(
            (
                escena,
                prompt,
                emotion_to_expression_key(beat.emotion),
                get_outfit_key_for_beat(beat),
                (gen_meta or {}).get("seed_material", ""),
            )
        )

    try:
        lista = generar_lote(
            escenas_con_prompts,
            subcarpeta=str(title_slug),
            width=1920,
            height=1080,
        )
        return {"generated": True, "backend_used": backend, "images": [str(p) for p in lista]}
    except Exception as e:
        return {"generated": False, "backend_used": backend, "error": str(e), "images": []}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", type=str, default="[TITULO_AQUI]")
    ap.add_argument("--debug-dir", type=str, default="")
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args()

    title = args.title
    title_slug = _slug(title)

    micro = generate_micro_script_from_title(title)
    beats = beats_from_micro_script(micro)

    # Ejecutar ruta real de prompts secuenciales con debug
    run_dir = BASE / "output" / "debug" / f"e2e_{title_slug}"
    debug_dir = Path(args.debug_dir) if args.debug_dir else run_dir
    debug_dir.mkdir(parents=True, exist_ok=True)

    prompts = prompts_para_beats(
        beats,
        shuffle_planos=False,
        video_theme=title,
        project_id=title_slug,
        debug_output_dir=debug_dir,
    )
    debug_json = load_debug_json(debug_dir, n=len(beats))

    # Validaciones
    validations = run_validations(micro, debug_json)

    # Informe por consola + escribir un resumen JSON
    report = {
        "title_used": title,
        "micro_script": micro,
        "prompts": [
            {
                "scene_idx": p[0].scene,
                "beat_id": p[0].beat_id,
                "prompt_final": p[1],
                "gen_meta": p[2],
                "seed_material": (p[2] or {}).get("seed_material"),
            }
            for p in prompts
        ],
        "validations": validations,
        "debug_dir": str(debug_dir),
    }
    (run_dir / "e2e_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Intentar generar imágenes (opcional)
    img_result: dict[str, Any] = {"generated": False, "images": [], "reason": "skipped by --no-images"}
    if not args.no_images:
        img_result = try_generate_images(beats, prompts, debug_dir, title_slug)
        report["image_generation"] = img_result
        (run_dir / "e2e_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Salida de texto
    print("=== E2E CONTINUIDAD VISUAL ===")
    print("1) título usado:", title)
    print("\n2) micro-guion:")
    for sc in micro:
        print(f"   escena {sc['scene_idx']}: location={sc['location']} camera_type={sc['camera_type']} action={sc['action']} emotion={sc['emotion']}")

    print("\n3) resumen por escena (del debug):")
    for i, d in enumerate(debug_json):
        ctx = d["resolved_context"]
        print(
            f"   scene {i+1}: location_id={ctx['location_id']} resolved_location={ctx['resolved_location']} "
            f"inherited_from_previous={ctx['inherited_from_previous']} location_changed={ctx['location_changed']} "
            f"resolved_camera={ctx['resolved_camera']} previous_camera={ctx['previous_camera']} "
            f"overlay_allowed={ctx['symbolic_overlay_allowed']} seed_material={d['gen_meta'].get('seed_material')}"
        )

    print("\n4) prompts finales (cámara + continuidad):")
    for i, p in enumerate(prompts):
        prompt = p[1]
        cam_line = camera_from_prompt_final(prompt)
        print(f"   prompt scene {i+1} camera_effective='{cam_line}' | contains continuity={('CONTINUITY FROM PREVIOUS SCENE' in prompt)}")

    print("\n5) validaciones automáticas:")
    print("   OK overall:", validations["ok"])
    for chk in validations["checks"]:
        print(f"   - {chk['type']} scene_index={chk.get('i','?')} ok={chk['ok']} | {chk['msg']}")
    if img_result and not img_result.get("generated", False):
        print("\n6) imágenes de prueba:")
        print("   backend_used:", img_result.get("backend_used"))
        print("   generated:", img_result.get("generated"))
        print("   error:", img_result.get("error"))
    else:
        print("\n6) imágenes de prueba generadas:")
        print("   images:", img_result.get("images", []))

    print("\n7) debug JSON por escena:")
    print("   ", debug_dir)
    print("8) reporte final JSON:")
    print("   ", str(run_dir / "e2e_report.json"))


if __name__ == "__main__":
    main()

