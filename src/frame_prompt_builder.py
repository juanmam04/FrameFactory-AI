"""Compilador V2: FrameSpec -> prompt quirúrgico de imagen."""
from __future__ import annotations

from .config_loader import get_prohibido_en_imagen
from .frame_spec import FrameSpec


def build_structural_core_prompt(spec: FrameSpec) -> str:
    """
    Capa 1 (obligatoria): estructura física explícita, sin narrativa abstracta.
    Orden fijo para máxima obediencia del modelo.
    """
    # Mantenerlo corto y físico.
    lines = [
        "STRUCTURAL CORE (MANDATORY, FIRST):",
        "injured person visible",
        "full body lying on ground (horizontal, clearly readable)",
        "clear red blood visible on body and/or floor (not tiny, not hidden)",
        "second character approaching",
    ]
    # Reglas de rol solo físicas (sin relato)
    if "pov" in (spec.camera_mode or "").lower():
        lines.extend(
            [
                "viewer is NOT the injured person",
                "viewer is NOT on ground",
                "injured person is a different character",
                "POV framing: viewer body not shown, optional hands/arms only",
                "injured friend must still occupy clear foreground area",
            ]
        )
    lines.extend(
        [
            "no single-character scene",
            "no standing-only composition",
            "no clean neutral pose",
            "no bloodless interpretation of injury",
        ]
    )
    return "\n".join(lines).strip()


def build_context_layer_prompt(spec: FrameSpec) -> str:
    """
    Capa 2: contexto después de la estructura.
    Solo info útil (lugar, cámara, movimiento, emoción) sin frases abstractas.
    """
    location = (spec.location or "exterior alley").strip()
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

    # Bloque de errores críticos, compacto.
    forbidden_items = list(spec.forbidden_misread) if spec.forbidden_misread else []
    forbidden_items.extend(
        [
            "viewer is the injured person",
            "main character lying on ground alone",
            "no second character present",
            "interior calm room",
            "neutral poster composition",
        ]
    )
    forbidden = "; ".join(dict.fromkeys([f for f in forbidden_items if f]))
    if forbidden:
        lines.append(f"forbidden: {forbidden}")

    return "\n".join(lines).strip()


def build_event_prompt_short(
    spec: FrameSpec,
    corrective_prompt: str | None = None,
    attempt_index: int = 1,
    event_failures: int = 0,
) -> str:
    structural = build_structural_core_prompt(spec)
    context = build_context_layer_prompt(spec)
    base = f"{structural}\n\n{context}"
    # Corrección progresiva, corta y física.
    if attempt_index >= 2 or event_failures >= 1:
        base += "\n\nCORRECTION: enforce body on ground + visible blood + second character approaching."
    if attempt_index >= 3 or event_failures >= 2:
        base += "\nCORRECTION: reject interior calm scenes and standing-only outputs."
    if corrective_prompt:
        base = f"{base}\n\n{corrective_prompt.strip()}"
    return base.strip()


def build_style_prompt_short(spec: FrameSpec) -> str:
    _ = get_prohibido_en_imagen()  # mantener dependencia de config sin inyectar bloque largo
    # Estilo mínimo para no diluir evento
    return (
        "2D cinematic minimalist illustration, same main character identity, "
        "white round head, black oval eyes, clean outlines, consistent visual style, "
        "readable background, 16:9, no UI overlays."
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
