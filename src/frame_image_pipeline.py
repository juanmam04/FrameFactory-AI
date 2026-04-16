"""Generación de imágenes V2: multi-intento + validación + regeneración semántica (única implementación)."""
from __future__ import annotations

import os
import time
from pathlib import Path

from .frame_prompt_builder import prompt_desde_frame_spec
from .frame_regenerator import build_corrective_prompt_from_reasons, patch_framespec_para_regeneracion
from .frame_spec import FrameSpec, guardar_frame_specs
from .frame_validator import validar_frame
from .image_generator import OUTPUT_IMAGES, generar_imagen


def _candidate_rank(result) -> tuple[float, float, float, float]:
    return (
        1.0 if result.is_valid else 0.0,
        float(result.event_match_score),
        float(result.action_score),
        float(result.score),
    )


def generar_imagenes_desde_frame_specs(
    frame_specs: list[FrameSpec],
    proyecto: str,
    *,
    width: int = 1920,
    height: int = 1080,
    attempts_per_frame: int | None = None,
    carpeta_raiz: Path | None = None,
    on_progress_imagenes=None,
    delay_between_frames_sec: float | None = None,
) -> tuple[list[Path], list[dict], list[FrameSpec]]:
    """
    Para cada FrameSpec: N intentos → validar → opcional regeneración con patch.
    Actualiza ``frame_specs`` in-place cuando hay patch.
    """
    if attempts_per_frame is None:
        attempts_per_frame = int(os.getenv("ATTEMPTS_PER_FRAME", "4"))
    attempts_per_frame = max(1, attempts_per_frame)
    hard_streak = int(os.getenv("HARD_FAIL_EVENT_STREAK", "3"))
    hard_streak = max(2, min(8, hard_streak))

    if delay_between_frames_sec is None:
        delay_between_frames_sec = float(os.getenv("REPLICATE_INTER_FRAME_DELAY_SEC", "0") or 0)

    base = carpeta_raiz if carpeta_raiz is not None else (OUTPUT_IMAGES / proyecto)
    carpeta_frames = base
    carpeta_attempts = carpeta_frames / "_attempts"
    carpeta_frames.mkdir(parents=True, exist_ok=True)
    carpeta_attempts.mkdir(parents=True, exist_ok=True)

    lista_imagenes: list[Path] = []
    frame_metrics: list[dict] = []
    validas = 0
    n = len(frame_specs)

    print(f"🖼️ Generando {n} imágenes (intentos/frame: {attempts_per_frame}, hard_fail tras {hard_streak} fallos de evento)…")

    for idx, spec in enumerate(frame_specs):
        if idx > 0 and delay_between_frames_sec > 0:
            time.sleep(delay_between_frames_sec)

        current = carpeta_frames / f"escena_{spec.frame_id:04d}.png"
        prev = carpeta_frames / f"escena_{spec.frame_id - 1:04d}.png" if spec.frame_id > 1 else None
        best_result = None
        best_path: Path | None = None
        total_attempts_done = 0
        valid_attempts = 0
        regenerated = False
        hard_fail_event = False
        event_fail_count = 0

        for intento in range(1, attempts_per_frame + 1):
            attempt_scene_num = spec.frame_id * 100 + intento
            attempt_path = generar_imagen(
                prompt_desde_frame_spec(spec, attempt_index=intento, event_failures=event_fail_count),
                attempt_scene_num,
                carpeta_attempts,
                width=width,
                height=height,
                expression_key=spec.expression_key,
            )
            if not attempt_path:
                continue
            total_attempts_done += 1
            debug_name = carpeta_attempts / f"escena_{spec.frame_id:04d}_try{intento}.png"
            try:
                debug_name.write_bytes(attempt_path.read_bytes())
                attempt_path = debug_name
            except OSError:
                pass
            result = validar_frame(spec=spec, image_path=attempt_path, prev_image_path=prev)
            if float(result.event_match_score) < 0.80:
                event_fail_count += 1
            if result.is_valid:
                valid_attempts += 1
            if best_result is None or _candidate_rank(result) > _candidate_rank(best_result):
                best_result = result
                best_path = attempt_path
            if event_fail_count >= hard_streak:
                hard_fail_event = True
                break

        if not hard_fail_event and (best_result is None or not best_result.is_valid):
            reasons = best_result.reasons if best_result else ["no valid candidate generated"]
            for _ in range(2):
                regenerated = True
                patched = patch_framespec_para_regeneracion(spec, reasons)
                corrective_prompt = build_corrective_prompt_from_reasons(reasons)
                frame_specs[idx] = patched

                local_best_res = None
                local_best_path = None
                for intento in range(1, attempts_per_frame + 1):
                    attempt_scene_num = spec.frame_id * 1000 + 100 + intento
                    attempt_path = generar_imagen(
                        prompt_desde_frame_spec(
                            patched,
                            corrective_prompt=corrective_prompt,
                            attempt_index=intento + 1,
                            event_failures=event_fail_count,
                        ),
                        attempt_scene_num,
                        carpeta_attempts,
                        width=width,
                        height=height,
                        expression_key=patched.expression_key,
                    )
                    if not attempt_path:
                        continue
                    total_attempts_done += 1
                    debug_name = carpeta_attempts / f"escena_{spec.frame_id:04d}_regen_try{intento}.png"
                    try:
                        debug_name.write_bytes(attempt_path.read_bytes())
                        attempt_path = debug_name
                    except OSError:
                        pass
                    result = validar_frame(spec=patched, image_path=attempt_path, prev_image_path=prev)
                    if float(result.event_match_score) < 0.80:
                        event_fail_count += 1
                    if result.is_valid:
                        valid_attempts += 1
                    if local_best_res is None or _candidate_rank(result) > _candidate_rank(local_best_res):
                        local_best_res = result
                        local_best_path = attempt_path
                    if event_fail_count >= hard_streak:
                        hard_fail_event = True
                        break
                if hard_fail_event:
                    break

                if local_best_res is not None and (best_result is None or _candidate_rank(local_best_res) > _candidate_rank(best_result)):
                    best_result = local_best_res
                    best_path = local_best_path
                if best_result is not None and best_result.is_valid:
                    break
                reasons = best_result.reasons if best_result else reasons

        if not hard_fail_event and best_path and best_path.exists():
            current.write_bytes(best_path.read_bytes())
            lista_imagenes.append(current)
            if best_result and best_result.is_valid:
                validas += 1
        elif hard_fail_event:
            print(
                f"❌ Frame {spec.frame_id}: hard fail (event_match < 0.8 en {hard_streak} acumulados). "
                "Se detiene este frame."
            )

        frame_metrics.append(
            {
                "frame": spec.frame_id,
                "attempts": total_attempts_done,
                "valid": valid_attempts,
                "best_score": float(best_result.score) if best_result else 0.0,
                "regenerated": regenerated,
                "hard_fail_event": hard_fail_event,
            }
        )
        if best_result is not None:
            print(
                f"Frame {spec.frame_id}: attempts={total_attempts_done} | "
                f"valid={valid_attempts} | best_score={best_result.score:.2f} | regenerated={regenerated} | hard_fail={hard_fail_event}"
            )
        else:
            print(
                f"Frame {spec.frame_id}: attempts={total_attempts_done} | "
                f"valid={valid_attempts} | best_score=0.00 | regenerated={regenerated} | hard_fail={hard_fail_event}"
            )

        if on_progress_imagenes:
            try:
                on_progress_imagenes(idx + 1, n)
            except Exception:
                pass

    guardar_frame_specs(frame_specs, proyecto)
    print(f"✅ Frames válidos: {validas}/{n} | Imágenes escritas: {len(lista_imagenes)}")
    return lista_imagenes, frame_metrics, frame_specs
