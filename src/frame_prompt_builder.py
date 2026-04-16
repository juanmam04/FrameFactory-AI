"""Compilador V2: FrameSpec -> prompt quirúrgico de imagen."""
from __future__ import annotations

from .config_loader import get_prohibido_en_imagen
from .frame_spec import FrameSpec


def _blob_spec(spec: FrameSpec) -> str:
    return _normalizar(
        f"{spec.event_core} {' '.join(spec.must_visible_evidence)} {' '.join(spec.must_visible_entities)}"
    )


def _normalizar(s: str) -> str:
    return (s or "").lower()


def _es_escena_violencia_herida(spec: FrameSpec) -> bool:
    b = _blob_spec(spec)
    return any(
        k in b
        for k in (
            "sangre",
            "herid",
            "desangr",
            "dispar",
            "pistola",
            "cuchillo",
            "puñal",
            "golpe",
            "pelea",
            "víctima",
            "victima",
            "cuerpo",
            "tirado",
            "yace",
            "ambulancia",
        )
    )


def build_structural_core_prompt(spec: FrameSpec) -> str:
    """
    Capa 1: obligatoria, física, en inglés corto.
    Usa structural_core_lines del director (multi-tema); ya no forzamos solo «herido en callejón».
    """
    lines = ["STRUCTURAL CORE (MANDATORY, FIRST):"]
    core = list(spec.structural_core_lines) if spec.structural_core_lines else []
    if not core:
        # Fallback si un spec viejo no trae líneas
        for ev in (spec.must_visible_evidence or [])[:5]:
            core.append(f"Must show on screen: {ev}")
    for item in core:
        lines.append(item.strip())

    if "pov" in (spec.camera_mode or "").lower():
        if _es_escena_violencia_herida(spec):
            lines.extend(
                [
                    "viewer is NOT the injured person on the ground",
                    "injured/victim is a different character from the viewer",
                    "POV: viewer body not shown (optional hands/arms only)",
                    "victim or focal injured figure remains readable in frame",
                ]
            )
        else:
            lines.extend(
                [
                    "POV first person: camera = viewer eyes",
                    "viewer protagonist body NOT visible (optional hands/forearms only)",
                    "show the environment and other characters/objects the story needs",
                ]
            )

    lines.extend(
        [
            "no empty white background",
            "no generic poster pose — show a real story moment",
        ]
    )
    return "\n".join(lines).strip()


def build_context_layer_prompt(spec: FrameSpec) -> str:
    """Capa 2: contexto narrativo y cámara."""
    location = (spec.location or "clear story location").strip()
    camera = (spec.camera_mode or "POV first person").strip()
    composition = (spec.composition or "").strip()
    motion = (spec.physical_motion or spec.action or "").strip()
    emotion = (spec.emotion or "").strip()

    lines = [
        "CONTEXT LAYER (SECOND):",
        f"location: {location}",
        f"camera: {camera}",
    ]
    if composition:
        lines.append(f"composition: {composition}")
    if motion:
        lines.append(f"movement: {motion}")
    if emotion:
        lines.append(f"emotion: {emotion}")
    lines.append("timing: mid-action instant, not before or after the event")

    forbidden_items = list(spec.forbidden_misread) if spec.forbidden_misread else []
    forbidden_items.extend(
        [
            "empty white background",
            "neutral poster composition with no story",
        ]
    )
    if _es_escena_violencia_herida(spec):
        forbidden_items.extend(
            [
                "viewer is the injured person on ground",
                "main character lying alone with no second presence when story needs witness",
                "calm domestic interior replacing danger scene",
            ]
        )
    forbidden = "; ".join(dict.fromkeys([f for f in forbidden_items if f]))
    if forbidden:
        lines.append(f"forbidden: {forbidden}")

    return "\n".join(lines).strip()


def _correccion_fisica_corta(spec: FrameSpec) -> str:
    """Refuerzo genérico según evidencias del spec (no solo herida)."""
    parts: list[str] = []
    for ev in (spec.must_visible_evidence or [])[:3]:
        parts.append(ev)
    if not parts:
        return "enforce central story event and readable environment"
    return "enforce: " + "; ".join(parts)


def build_event_prompt_short(
    spec: FrameSpec,
    corrective_prompt: str | None = None,
    attempt_index: int = 1,
    event_failures: int = 0,
) -> str:
    structural = build_structural_core_prompt(spec)
    context = build_context_layer_prompt(spec)
    base = f"{structural}\n\n{context}"
    if attempt_index >= 2 or event_failures >= 1:
        base += f"\n\nCORRECTION: {_correccion_fisica_corta(spec)}"
    if attempt_index >= 3 or event_failures >= 2:
        base += "\n\nCORRECTION: reject generic calm scenes; show the exact beat action and setting."
    if corrective_prompt:
        base = f"{base}\n\n{corrective_prompt.strip()}"
    return base.strip()


def build_style_prompt_short(spec: FrameSpec) -> str:
    _ = get_prohibido_en_imagen()
    return (
        "2D stick-figure / minimalist storyboard, same protagonist as character reference (Kontext): "
        "white round head, simple black eyes, thin limbs, clean outlines, flat colors, "
        "full frame edge to edge (no letterboxing), readable background, 16:9, no UI overlays."
    ).strip()


def combine_event_and_style_prompt(event_prompt: str, style_prompt: str) -> str:
    return f"{event_prompt}\n\nSTYLE (secondary): {style_prompt}".strip()


def prompt_desde_frame_spec(
    spec: FrameSpec,
    corrective_prompt: str | None = None,
    attempt_index: int = 1,
    event_failures: int = 0,
) -> str:
    event_prompt = build_event_prompt_short(
        spec,
        corrective_prompt=corrective_prompt,
        attempt_index=attempt_index,
        event_failures=event_failures,
    )
    style_prompt = build_style_prompt_short(spec)
    return combine_event_and_style_prompt(event_prompt, style_prompt)
