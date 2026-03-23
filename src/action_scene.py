"""
Detección de escenas con acción explícita y ajustes automáticos de meta/prompt
(pose dinámica, sin empty_room_tension estático).
"""
from __future__ import annotations

from typing import Any

from .visual_beats import VisualBeat

# Keywords ES/EN en texto de escena (match simple, case-insensitive)
_ACTION_KEYWORDS: tuple[str, ...] = (
    # levantar / raise
    "levanta", "levantar", "levantó", "levanto", "alza", "alzar", "raise", "raises", "lifting", "lifts", "lift ",
    # correr / run
    "corre", "correr", "corriendo", "corría", "run", "runs", "running", "sprint",
    # caminar / walk
    "camina", "caminar", "caminando", "walk", "walks", "walking",
    # entrar / salir
    "entra", "entrar", "entrando", "enter", "enters", "entering", "ingresa", "ingresar",
    "sale", "salir", "saliendo", "salió", "exit", "exits", "leaves", "leaving",
    # unirse / join
    "se une", "unirse", "únase", "join", "joins", "joining", "reúne", "reune",
    # lucha / fight
    "ataca", "atacar", "atacando", "pelea", "pelear", "lucha", "luchar", "fight", "fights", "fighting",
    "attack", "attacks", "golpea", "golpear",
    # hablar / speak
    "habla", "hablar", "hablando", "habló", "speak", "speaks", "speaking", "talk", "talks", "talking", "dice", "decir",
    "grita", "gritar", "shout", "shouts",
    # interactuar
    "interactúa", "interactua", "interactuar", "interact", "interacts", "interaction",
    # entregar / give
    "entrega", "entregar", "give", "gives", "giving", "hand over", "hands over",
    # mirar a otros / look
    "mira a", "mirando a", "look at", "looks at", "looking at", "observa a", "stares at",
    # movimiento genérico útil
    "agarra", "agarrar", "toma", "tomar", "coge", "coger", "sostiene", "sostener",
    "abraz", "besa", "besar", "empuja", "empujar", "tira", "tirar", "salta", "saltar",
    "sienta", "sentarse", "sentado", "se sienta", "sit", "sits", "sitting", "seated",
)

ACTION_REQUIREMENT_BLOCK = """ACTION REQUIREMENT:
The protagonist MUST be actively performing the described action.
No static standing pose allowed.
The body must clearly show movement and intention.
If other characters are present, they must interact with the protagonist."""

COMPOSITION_RULES_ACTION_BLOCK = """COMPOSITION RULES:
Do not center the character in a neutral standing pose.
Avoid symmetrical composition.
Use dynamic staging and interaction with the environment."""


def _text_blob(action: str, original_text: str, context: str) -> str:
    return f"{action} {original_text} {context}".lower()


def detect_action_scene_from_fields(action: str, original_text: str, context: str) -> bool:
    """Keyword match sobre los tres campos de texto."""
    blob = _text_blob(action or "", original_text or "", context or "")
    if not blob.strip():
        return False
    return any(k in blob for k in _ACTION_KEYWORDS)


def detect_action_scene(beat: VisualBeat) -> bool:
    """True si el beat describe acción física o interacción (usa action, original_text, context)."""
    return detect_action_scene_from_fields(
        getattr(beat, "action", None) or "",
        getattr(beat, "original_text", None) or "",
        getattr(beat, "context", None) or "",
    )


def action_prompt_appendix() -> str:
    """Bloques a añadir al prompt cuando ``action_scene_dynamic`` está activo."""
    return f"{ACTION_REQUIREMENT_BLOCK}\n\n{COMPOSITION_RULES_ACTION_BLOCK}"


def apply_action_scene_meta_overrides(
    meta: dict[str, Any],
    *,
    beat: VisualBeat | None = None,
    escena_text: str | None = None,
) -> dict[str, Any]:
    """
    Si hay acción detectada:
    - ``scene_focus`` → ``full_body_action``
    - si ``visual_device`` es ``empty_room_tension`` → ``group_interaction`` o ``dynamic_interaction``
    - refresca tags simbólicos según el nuevo device
    - marca ``action_scene_dynamic`` para el ensamblado del prompt
    """
    from .visual_story_mapper import refresh_symbolic_metadata

    m = dict(meta)
    if beat is not None:
        is_action = detect_action_scene(beat)
    else:
        is_action = detect_action_scene_from_fields(
            m.get("action") or "",
            escena_text or "",
            "",
        )
    if not is_action:
        m.pop("action_scene_dynamic", None)
        return m

    m["action_scene_dynamic"] = True
    m["scene_focus"] = "full_body_action"

    chars = [c for c in (m.get("scene_characters") or []) if c and c != "extras"]
    multi = len(chars) > 1

    if (m.get("visual_device") or "") == "empty_room_tension":
        m["visual_device"] = "group_interaction" if multi else "dynamic_interaction"

    # Prioridad de encuadre más amplia para leer el cuerpo en acción
    m["camera_priority"] = "medium shot"

    return refresh_symbolic_metadata(m)
