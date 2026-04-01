"""Regenerador inteligente V2: modifica campos de FrameSpec según fallos/feedback."""
from __future__ import annotations

from .frame_spec import FrameSpec


def build_corrective_prompt_from_reasons(reasons: list[str]) -> str:
    motivos = "; ".join((reasons or [])[:8]) if reasons else "central event not visible"
    return (
        "The previous image failed because the central event was not visible.\n"
        f"Detected issues: {motivos}.\n"
        "Correct these errors strictly.\n"
        "Ensure the injured friend is clearly visible and clearly injured if required.\n"
        "Ensure required blood/evidence is visible if requested.\n"
        "Ensure environment matches the requested scene (no safe interior substitutions).\n"
        "Reject calm standing/posed compositions."
    )


def patch_framespec_para_regeneracion(
    spec: FrameSpec,
    errores: list[str],
    feedback_usuario: str = "",
) -> FrameSpec:
    patched = FrameSpec(**spec.__dict__)
    feedback = (feedback_usuario or "").lower()
    errores_l = " | ".join(errores).lower()

    # Repetición visual: cambiar cámara y composición primero.
    if "similar" in errores_l or "repet" in errores_l:
        patched.camera_mode = "side angle" if spec.camera_mode != "side angle" else "close-up"
        patched.camera_subject_visibility = "protagonist_visible_allowed"
        patched.composition = (
            "subject right-third, action center, foreground prop, deep background context"
            if "right-third" not in spec.composition
            else "dynamic diagonal composition with clear focal point and strong depth"
        )
        patched.delta_from_previous = list(dict.fromkeys(patched.delta_from_previous + ["cambiar cámara y composición drásticamente"]))

    # Imagen negra/vacía: reforzar contexto visual obligatorio.
    if "negra" in errores_l or "vacía" in errores_l or "vacia" in errores_l:
        patched.must_show = list(dict.fromkeys(patched.must_show + ["iluminación visible sobre sujeto y entorno", "fondo detallado y utilizable"]))
        patched.avoid = list(dict.fromkeys(patched.avoid + ["fondos oscuros sin detalle", "escena subexpuesta"]))
        patched.forbidden_misread = list(dict.fromkeys(patched.forbidden_misread + ["escena oscura donde no se entiende el evento"]))

    # Feedback semántico: mover campos concretos, no texto random.
    if "cocina" in feedback and "program" in feedback:
        patched.location = "habitación/oficina con escritorio, monitor con código y ambiente de programación"
        patched.must_visible_entities = list(dict.fromkeys(patched.must_visible_entities + ["monitor con código", "teclado"]))
        patched.must_visible_evidence = list(dict.fromkeys(patched.must_visible_evidence + ["código visible en pantalla", "manos tecleando"]))
        patched.forbidden_misread = list(dict.fromkeys(patched.forbidden_misread + ["cocina", "comedor"]))
    if "quieto" in feedback or "pos" in feedback:
        patched.action = f"{spec.action}. Acción física fuerte: cuerpo en movimiento e interacción directa con el evento."
        patched.physical_motion = "movimiento corporal urgente y visible en progreso; no pose estática"
        patched.must_show = list(dict.fromkeys(patched.must_show + ["postura dinámica con acción en progreso"]))
        patched.forbidden_misread = list(dict.fromkeys(patched.forbidden_misread + ["pose estática", "mirada fija a cámara"]))

    if "event_core vacío" in errores_l or "must_visible_evidence" in errores_l:
        patched.event_core = (patched.event_core or patched.story_step or patched.action or "").strip()
        patched.must_visible_evidence = list(
            dict.fromkeys(
                patched.must_visible_evidence
                + ["evidencia física inequívoca del evento central", "contexto narrativo legible en 1 segundo"]
            )
        )
    if "acción abstracta" in errores_l:
        patched.action = f"{patched.action}. VERBO+CUERPO+OBJETO+MOVIMIENTO+CONTEXTO explícito."
        patched.physical_motion = f"mid-action visible: {patched.action}"
    if "camera_mode contradictorio" in errores_l:
        patched.camera_mode = "POV first person"
        patched.camera_subject_visibility = "protagonist_not_visible_except_hands_optional"

    # Endurecer contra escenas seguras/genéricas
    if any(k in errores_l for k in ("mismatch de entorno", "no se observa sangre", "no se ve cuerpo en el suelo", "falta evidencia visual")):
        patched.forbidden_misread = list(
            dict.fromkeys(
                patched.forbidden_misread
                + [
                    "calm interior scene",
                    "standing characters without event evidence",
                    "no blood",
                    "no injured body on ground",
                    "neutral safe composition",
                ]
            )
        )
        patched.must_visible_evidence = list(
            dict.fromkeys(
                patched.must_visible_evidence
                + [
                    "central event evidence must be explicit at first glance",
                    "injury evidence visible (if requested)",
                ]
            )
        )

    return patched
