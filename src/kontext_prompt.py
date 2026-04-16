"""
Ensamblado del prompt para FLUX Kontext: identidad desde input_image sin copiar composición de ficha/model sheet.
"""
from __future__ import annotations

MODE_IDENTITY_SHEET = "identity_sheet"
MODE_SCENE_REFERENCE = "scene_reference"

# Subcadenas que deben aparecer en el guard (tests de ensamblado)
KONTEXT_GUARD_TEST_SUBSTRINGS = (
    "Use the input image ONLY",
    "CURRENT SCENE",
    "not the backdrop in the reference",
)


def normalize_character_reference_mode(raw: str | None) -> str:
    """Default ``identity_sheet``. Acepta alias corto ``scene`` → ``scene_reference``."""
    v = (raw or "").strip().lower()
    if not v or v == MODE_IDENTITY_SHEET:
        return MODE_IDENTITY_SHEET
    if v in (MODE_SCENE_REFERENCE, "scene"):
        return MODE_SCENE_REFERENCE
    return MODE_IDENTITY_SHEET


def kontext_identity_sheet_composition_guard() -> str:
    """
    Bloque anti-copia de composición cuando la referencia es tipo model sheet (fondo plano, pose neutra).
    Solo identidad y vestuario deben anclarse al input_image.
    """
    return (
        "COMPOSITION AND REFERENCE USE: Use the input image ONLY to preserve character identity "
        "(face design, head shape, body proportions, line weight) and consistent outfit colors. "
        "Mirrors, reflections, and glass: the reflected figure must wear the SAME outfit colors as the real character—no palette swap. "
        "Do NOT copy the plain white, gray, or flat studio background from the reference—the environment "
        "must follow the CURRENT SCENE text, not the backdrop in the reference image. "
        "Do NOT keep the same neutral standing pose or centered model-sheet framing unless the scene explicitly requires it; "
        "match a dynamic pose and camera to the action described. "
        "Generate a full narrative setting with cinematic depth, readable space, and no blank void backdrop. "
        "Full bleed to frame edges: no letterboxing, no black bars, no cinematic mattes unless the scene explicitly demands it. "
        "Overall composition and layout must follow this scene’s description, not the reference image layout."
    )


def build_kontext_prompt_for_replicate(
    scene_prompt: str,
    context_instruction: str,
    reference_mode: str,
    *,
    max_chars: int = 3500,
) -> str:
    """
    Concatena instrucción base de Kontext + (opcional) guard anti–model-sheet + prompt de escena.
    ``reference_mode``: ``identity_sheet`` | ``scene_reference`` (usar ``normalize_character_reference_mode``).
    """
    base = (context_instruction or "").strip()
    mode = normalize_character_reference_mode(reference_mode)
    parts: list[str] = []
    if base:
        parts.append(base)
    if mode == MODE_IDENTITY_SHEET:
        parts.append(kontext_identity_sheet_composition_guard())
    parts.append((scene_prompt or "").strip())
    out = " ".join(p for p in parts if p).strip()
    if len(out) > max_chars:
        out = out[:max_chars]
    return out


def identity_sheet_guard_active(reference_mode: str | None) -> bool:
    return normalize_character_reference_mode(reference_mode) == MODE_IDENTITY_SHEET
