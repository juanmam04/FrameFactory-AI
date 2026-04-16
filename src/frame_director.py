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


def _inferir_evidencia_evento(
    event_core: str, action: str, location: str
) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    Entidades/evidencias en español (validador) + structural_core_lines en inglés (prompt dominante).
    Orden de prioridad: violencia/herida → stream (antes que «monitor» técnico) → deporte → aeropuerto → oficina → hacker/PC → default.
    """
    t = f"{event_core} {action} {location}".lower()
    # Evitar frases demasiado meta para el validador por caption; el director añade evidencias concretas por tema.
    entities: list[str] = ["personaje principal"]
    evidence: list[str] = []
    misread: list[str] = ["pose estática", "composición tipo póster", "fondo neutro/genérico"]
    structural_en: list[str] = [
        "Main character or focal subject clearly visible",
        "Physical action in progress (mid-action, not a static poster shot)",
        "Environment readable and tied to the location (not a blank studio)",
        "Story-relevant props and characters on screen",
    ]

    # 1) Violencia / herida / urgencia física extrema
    if any(
        k in t
        for k in (
            "desangra",
            "herid",
            "sangre",
            "cuerpo en el suelo",
            "yace",
            "tirado",
            "disparo",
            "pistola",
            "puñal",
            "apuñal",
            "golpe",
            "pelea",
            "ambulancia",
        )
    ):
        entities += ["persona herida o en peligro visible", "evidencia de violencia o herida en pantalla"]
        evidence += ["cuerpo o víctima claramente visible", "sangre o herida visible si aplica", "reacción física creíble"]
        misread += ["habitación tranquila", "nadie herido", "sin sangre cuando el guión pide herida", "personaje parado sin reaccionar"]
        structural_en = [
            "Injured or endangered person clearly visible if the story requires it",
            "If collapse: body horizontal on ground, readable pose",
            "Blood or wound visible when the beat implies injury (clear red, not hidden)",
            "Second figure allowed: witness, responder, or threat — OR clear POV toward the victim",
            "No single calm portrait; show the crisis moment",
        ]

    # 2) Streamer / YouTube (antes que «monitor» de PC para no confundir alertas en pantalla)
    elif any(
        k in t
        for k in (
            "stream",
            "streamer",
            "youtube",
            "twitch",
            "directo",
            "micrófono",
            "microfono",
            "cámara web",
            "camara web",
            "setup",
            "donación",
            "donacion",
            "suscriptores",
        )
    ):
        entities += ["micrófono", "monitor"]
        evidence += ["micrófono o cámara", "pantalla o alerta en monitor"]
        misread += ["exterior callejón", "cancha de fútbol", "cocina como único foco"]
        structural_en = [
            "Streaming desk setup: mic, camera or ring light, monitor",
            "Character seated or gesturing at camera",
            "Room reads as bedroom or studio, not sports field",
        ]

    # 3) Deporte / estadio
    elif any(k in t for k in ("fútbol", "futbol", "estadio", "gol", "cancha", "partido", "balón", "balon", "arquero")):
        entities += ["cancha o estadio", "balón"]
        evidence += ["balón o jugador en movimiento", "césped o estadio visible"]
        misread += ["oficina", "habitación sin campo"]
        structural_en = [
            "Outdoor field or stadium interior clearly visible",
            "Ball or athletic action in frame",
            "Player body in motion (kick, sprint, tackle)",
            "No office or random indoor room",
        ]

    # 5) Aeropuerto / equipaje
    elif any(k in t for k in ("aeropuerto", "maleta", "equipaje", "control", "pasaport", "avión", "avion", "vuelo")):
        entities += ["terminal o cinta", "maletas o mostrador"]
        evidence += ["entorno de aeropuerto reconocible", "interacción con equipaje o control"]
        misread += ["cocina doméstica", "calle vacía sin contexto"]
        structural_en = [
            "Airport interior: scanners, belts, signs, or gates visible",
            "Luggage or security context visible",
            "Crowd or airport architecture for scale",
        ]

    # 6) Hacker / código / PC (monitor solo si va con contexto técnico)
    elif any(
        k in t
        for k in (
            "program",
            "hacker",
            "código",
            "codigo",
            "teclado",
            "computadora",
            "ordenador",
            "terminal",
            "servidor",
            "firewall",
        )
    ) or (
        "monitor" in t
        and any(k in t for k in ("código", "codigo", "terminal", "hacker", "servidor", "firewall", "program", "infiltr"))
    ):
        entities += ["teclado", "monitor con código o terminal"]
        evidence += ["código o terminal en pantalla", "manos en teclado"]
        misread += ["cocina", "comedor", "personaje solo mirando cámara sin PC"]
        structural_en = [
            "Desk or server room clearly visible",
            "At least one screen showing code, terminal, or hacking UI",
            "Hands on keyboard OR clear typing gesture",
            "Multiple monitors OK if story implies a mission setup",
            "NOT a kitchen or cooking scene",
        ]

    # 7) Oficina / negocios
    elif any(k in t for k in ("oficina", "reunión", "reunion", "empresa", "junta", "director", "traje")):
        entities += ["mesa de reunión o escritorio", "pantallas o documentos"]
        evidence += ["entorno corporativo claro", "interacción con otros o con objetos de trabajo"]
        misread += ["cancha", "cocina"]
        structural_en = [
            "Office or meeting room clearly visible",
            "Business props: desk, chairs, screens, papers",
            "Characters in work-related action or conversation",
        ]

    if not evidence:
        evidence.append("acción visible en el lugar del beat")

    return (
        list(dict.fromkeys(entities)),
        list(dict.fromkeys(evidence)),
        list(dict.fromkeys(misread)),
        structural_en,
    )


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

        must_entities, must_evidence, forbidden_misread, structural_core_lines = _inferir_evidencia_evento(
            event_core, action, location
        )

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
                structural_core_lines=structural_core_lines,
            )
        )
        prev = specs[-1]
    return specs
