"""Script de prueba en consola para validar el pipeline V2 de imágenes.

Incluye:
- flujo completo de generación/regeneración (manual)
- pruebas CONTROLADAS del validador (3 casos) con caption forzado
"""
from __future__ import annotations

import argparse
from pathlib import Path
import os

from PIL import Image, ImageDraw

from src.config_loader import BASE
from src.frame_prompt_builder import prompt_desde_frame_spec
from src.frame_regenerator import patch_framespec_para_regeneracion
from src.frame_spec import FrameSpec
from src.frame_validator import validar_frame
from src.image_generator import generar_imagen


def _print_scores(tag: str, result) -> None:
    print(f"\n=== {tag} ===")
    print(f"is_valid: {result.is_valid}")
    print(f"score_total: {result.score:.3f}")
    print(f"event_match_score: {result.event_match_score:.3f}")
    print(f"action_score: {result.action_score:.3f}")
    print(f"camera_consistency_score: {result.camera_consistency_score:.3f}")
    print(f"narrative_clarity_score: {result.narrative_clarity_score:.3f}")
    print(f"repetition_score: {result.repetition_score:.3f}")
    print(f"caption: {result.caption or '(sin caption VLM)'}")
    if result.reasons:
        print("reasons:")
        for r in result.reasons:
            print(f"  - {r}")
    else:
        print("reasons: []")


def _crear_spec_evento_herido() -> FrameSpec:
    return FrameSpec(
        frame_id=1,
        beat_id=1,
        scene_id=1,
        scene_priority="P1_EVENT_OVER_STYLE",
        event_core="Llegas y ves a tu amigo de la infancia tirado en el suelo, gravemente herido y desangrándose.",
        subject="mismo protagonista del video POV",
        action="corres por el callejón, frenas en seco y extiendes la mano hacia tu amigo herido en el suelo",
        physical_motion="movimiento urgente de llegada; cuerpo en inercia de frenado; mano extendida hacia el herido",
        location="callejón oscuro urbano con suelo visible y entorno deteriorado",
        camera_mode="POV first person",
        camera_subject_visibility="protagonist_not_visible_except_hands_optional",
        composition="camera rushing toward the body, friend on ground in foreground, readable alley context in background",
        emotion="shock, anguish, urgency",
        must_visible_entities=[
            "amigo herido",
            "suelo del callejón",
            "sangre visible",
        ],
        must_visible_evidence=[
            "cuerpo caído en el suelo",
            "manchas de sangre visibles en ropa o piso",
            "sensación de llegada urgente al lugar",
        ],
        forbidden_misread=[
            "personaje parado calmado en una habitación",
            "interior doméstico",
            "pose neutra tipo póster",
            "amigo no visible",
            "sin sangre",
        ],
        must_show=[
            "evento central inequívoco",
            "acción física en progreso",
            "contexto narrativo legible",
        ],
        avoid=[
            "pose estática",
            "escena limpia sin conflicto",
            "fondo genérico",
        ],
        delta_from_previous=["establecer contexto inicial de alto impacto narrativo"],
        story_step="Primer encuentro con el evento traumático principal.",
        expression_key="shocked",
    )


def _crear_imagen_dummy(path: Path, seed: int) -> None:
    """Imagen simple no-negra/no-plana para tests controlados del validador."""
    img = Image.new("RGB", (640, 360), (40 + seed * 20, 60, 90))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 620, 340], outline=(220, 220, 220), width=3)
    d.line([0, 0, 640, 360], fill=(180, 120, 120), width=4)
    d.ellipse([120 + seed * 10, 110, 280 + seed * 10, 260], outline=(255, 200, 80), width=4)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def _decidir_final(result, strict_event: bool) -> bool:
    if strict_event and result.event_match_score < 0.8:
        return False
    return result.is_valid


def run_controlled_validator_tests(strict_event: bool) -> None:
    print("\n================ PRUEBAS CONTROLADAS DEL VALIDADOR (3 CASOS) ================\n")
    test_dir = BASE / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    spec = _crear_spec_evento_herido()

    casos = [
        {
            "nombre": "CASO 1 - INCORRECTO OBVIO",
            "img": test_dir / "validator_case_1.png",
            "caption": (
                "Interior tranquilo de una habitación limpia. Dos personajes de pie hablando. "
                "No hay sangre, no hay cuerpo en el suelo, no hay urgencia."
            ),
        },
        {
            "nombre": "CASO 2 - CORRECTO OBVIO",
            "img": test_dir / "validator_case_2.png",
            "caption": (
                "Callejón exterior oscuro. Un amigo herido yace tirado en el suelo con sangre visible en el piso y la ropa. "
                "La cámara llega con urgencia hacia el cuerpo, momento de shock y angustia."
            ),
        },
        {
            "nombre": "CASO 3 - AMBIGUO",
            "img": test_dir / "validator_case_3.png",
            "caption": (
                "Exterior urbano con dos personajes visibles. Se ve al amigo, pero está de pie y no hay sangre clara. "
                "No se aprecia cuerpo caído ni evidencia inequívoca de herida grave."
            ),
        },
    ]

    for i, caso in enumerate(casos, start=1):
        _crear_imagen_dummy(caso["img"], seed=i)
        res = validar_frame(
            spec=spec,
            image_path=caso["img"],
            prev_image_path=None,
            caption_override=caso["caption"],
        )
        _print_scores(caso["nombre"], res)
        decision = _decidir_final(res, strict_event=strict_event)
        print(f"decision_final: {'APROBADA' if decision else 'RECHAZADA'}")
        if strict_event:
            print(f"strict_event: ON (event_match_score >= 0.8 requerido). Valor: {res.event_match_score:.3f}")
        print("-" * 78)


def run_generation_flow(strict_event: bool) -> None:
    test_dir = BASE / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    spec = _crear_spec_evento_herido()

    attempts_per_round = max(1, int(os.getenv("TEST_ATTEMPTS_PER_ROUND", "4")))
    max_rounds = max(1, int(os.getenv("TEST_MAX_ROUNDS", "2")))
    scene_seed_base = 1
    prev_image: Path | None = None
    current_spec = spec

    for round_idx in range(1, max_rounds + 1):
        prompt = prompt_desde_frame_spec(current_spec)
        print(f"\n================ PROMPT GENERADO (RONDA {round_idx}) ================\n")
        print(prompt)
        print("\n=====================================================================\n")

        best: tuple[Path, object] | None = None
        for local_attempt in range(1, attempts_per_round + 1):
            scene_num = scene_seed_base + local_attempt - 1
            img = generar_imagen(
                prompt=prompt,
                escena_num=scene_num,
                carpeta=test_dir,
                width=1920,
                height=1080,
                expression_key=current_spec.expression_key,
            )
            if not img:
                continue
            res = validar_frame(spec=current_spec, image_path=img, prev_image_path=prev_image)
            tag = f"RONDA {round_idx} - INTENTO {local_attempt} (escena_num={scene_num})"
            _print_scores(tag, res)
            print(f"decision_final: {'APROBADA' if _decidir_final(res, strict_event) else 'RECHAZADA'}")
            if best is None:
                best = (img, res)
            else:
                prev_best = best[1]
                cur_key = (_decidir_final(res, strict_event), res.event_match_score, res.action_score, res.score)
                best_key = (_decidir_final(prev_best, strict_event), prev_best.event_match_score, prev_best.action_score, prev_best.score)
                if cur_key > best_key:
                    best = (img, res)

            if _decidir_final(res, strict_event):
                print(f"\n✅ Aprobada en ronda {round_idx}, intento {local_attempt}.")
                print(f"Imagen elegida: {img}")
                print(f"\nListo. Imágenes guardadas en: {test_dir}")
                return

        if best is None:
            raise RuntimeError(f"No se pudo generar ninguna imagen en la ronda {round_idx}.")

        best_img, best_res = best
        print(f"\nMejor de ronda {round_idx}: {best_img}")
        _print_scores(f"MEJOR RONDA {round_idx}", best_res)

        if round_idx < max_rounds:
            current_spec = patch_framespec_para_regeneracion(current_spec, best_res.reasons)
            prev_image = best_img
            scene_seed_base += attempts_per_round
            print("\nNo aprobó todavía; aplicando parche semántico al FrameSpec y continuando...")
        else:
            print("\nNo se alcanzó aprobación dentro de las rondas configuradas.")

    print(f"\nListo. Imágenes guardadas en: {test_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test del pipeline V2 y validador semántico")
    parser.add_argument("--strict-event", action="store_true", help="Falla automáticamente si event_match_score < 0.8")
    parser.add_argument(
        "--mode",
        choices=["controlled", "generate", "all"],
        default="controlled",
        help="controlled: solo 3 casos controlados; generate: genera imagen real; all: ambos",
    )
    args = parser.parse_args()

    if args.mode in ("controlled", "all"):
        run_controlled_validator_tests(strict_event=args.strict_event)
    if args.mode in ("generate", "all"):
        run_generation_flow(strict_event=args.strict_event)


if __name__ == "__main__":
    main()
