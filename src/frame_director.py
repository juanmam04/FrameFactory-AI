"""Director visual V2: convierte VisualBeat en FrameSpec estructurado."""
from __future__ import annotations

from .frame_spec import FrameSpec
from .prompt_builder import emotion_to_expression_key
from .visual_beats import VisualBeat


_CAMERA_ROTATION = ["POV first person", "over the shoulder", "side angle", "close-up", "wide shot"]

_COMPOSITION_ROTATION = ["foreground action + readable context", "dynamic diagonal action frame", "hands/object detail + context", "mid-action with depth"]

_ABSTRACT_ACTIONS = ("entra", "mira", "ve", "piensa", "trabaja", "se aproxima", "llega a la escena")


def _normalizar_action(texto: str) -> str:
    t = (texto or "").strip()
    if not t:
        return "corre, se detiene en seco y extiende la mano hacia el evento principal"
    low = t.lower()
    if any(a in low for a in _ABSTRACT_ACTIONS):
        return f"{t}. Acción física visible: movimiento corporal concreto, interacción con objeto/persona y gesto de urgencia en progreso."
    return t


def _normalizar_location(texto: str) -> str:
    t = (texto or "").strip()
    if not t:
        return "ubicación específica coherente con la acción"
    return t


def _resolver_camera_visibility(camera_mode: str) -> str:
    mode = (camera_mode or "").lower()
    if "pov" in mode:
        return "protagonist_not_visible_except_hands_optional"
    if "over the shoulder" in mode:
        return "protagonist_partial_visible_allowed"
    return "protagonist_visible_allowed"


def _inferir_evidencia_evento(event_core: str, action: str, location: str) -> tuple[list[str], list[str], list[str]]:
    t = f"{event_core} {action} {location}".lower()
    entities: list[str] = ["personaje principal", "entorno contextual legible"]
    evidence: list[str] = ["evento central inequívoco en pantalla", "acción en progreso (mid-action)"]
    misread: list[str] = ["pose estática", "composición tipo póster", "fondo neutro/genérico"]

    if any(k in t for k in ("desangra", "herid", "sangre", "cuerpo en el suelo", "yace")):
        entities += ["persona herida en el suelo", "charcos/manchas de sangre visibles"]
        evidence += ["cuerpo caído claramente visible", "sangre visible en ropa o piso", "llegada urgente al lugar"]
        misread += ["habitación tranquila", "nadie herido", "sin sangre", "personaje parado sin reaccionar"]
    if any(k in t for k in ("program", "hacker", "código", "teclado", "monitor")):
        entities += ["teclado", "monitor con código"]
        evidence += ["manos tecleando rápido", "código desplazándose visible en pantalla"]
        misread += ["cocina/comedor", "personaje quieto mirando cámara"]

    return list(dict.fromkeys(entities)), list(dict.fromkeys(evidence)), list(dict.fromkeys(misread))


def beats_a_frame_specs(beats: list[VisualBeat]) -> list[FrameSpec]:
    specs: list[FrameSpec] = []
    prev: FrameSpec | None = None
    for i, beat in enumerate(beats, start=1):
        camera_mode = _CAMERA_ROTATION[(i - 1) % len(_CAMERA_ROTATION)]
        composition = _COMPOSITION_ROTATION[(i - 1) % len(_COMPOSITION_ROTATION)]
        action = _normalizar_action(beat.action or beat.original_text)
        location = _normalizar_location(beat.location)
        event_core = (beat.original_text or beat.context or action).strip()
        physical_motion = f"Movimiento físico visible en progreso: {action}"
        camera_subject_visibility = _resolver_camera_visibility(camera_mode)

        must_entities, must_evidence, forbidden_misread = _inferir_evidencia_evento(event_core, action, location)

        must_show = [
            "acción física en progreso (no posado)",
            "contexto del lugar claramente visible",
            "objetos relevantes para la acción",
            "evento central comprensible en 1 segundo",
        ]
        avoid = [
            "personaje quieto mirando cámara",
            "fondo blanco o genérico sin contexto",
            "repetición del mismo ángulo del frame anterior",
            "escena neutra sin evento narrativo",
        ]

        delta: list[str] = []
        if prev is not None:
            if prev.camera_mode == camera_mode:
                camera_mode = _CAMERA_ROTATION[i % len(_CAMERA_ROTATION)]
                camera_subject_visibility = _resolver_camera_visibility(camera_mode)
            if prev.location == location:
                delta.append("cambiar composición dentro del mismo lugar")
            else:
                delta.append("cambiar ubicación respecto al frame anterior")
            delta.append("mostrar consecuencia visible del frame anterior")
            delta.append(f"usar cámara '{camera_mode}' en vez de '{prev.camera_mode}'")
        else:
            delta.append("establecer contexto inicial de la historia")

        specs.append(
            FrameSpec(
                frame_id=i,
                beat_id=beat.beat_id,
                scene_id=beat.scene,
                scene_priority="P1_EVENT_OVER_STYLE",
                event_core=event_core,
                subject="mismo personaje principal del video POV",
                action=action,
                physical_motion=physical_motion,
                location=location,
                camera_mode=camera_mode,
                camera_subject_visibility=camera_subject_visibility,
                composition=composition,
                emotion=(beat.emotion or "tensión").strip(),
                must_visible_entities=must_entities,
                must_visible_evidence=must_evidence,
                forbidden_misread=forbidden_misread,
                must_show=must_show,
                avoid=avoid,
                delta_from_previous=delta,
                story_step=(beat.context or beat.original_text or "").strip(),
                expression_key=emotion_to_expression_key(beat.emotion),
            )
        )
        prev = specs[-1]
    return specs
