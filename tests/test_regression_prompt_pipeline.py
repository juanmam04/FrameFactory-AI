"""Regresión explícita: bug de cámara (camera_priority) y beat.location vs plantilla."""
from __future__ import annotations

from src.prompt_builder import construir_prompt
from src.scene_splitter import Escena
from src.scene_visual_mapper import map_beat_to_visual_meta
from src.storyboard_debug import extract_camera_line_from_prompt
from src.storyboard_continuity import (
    CharacterStateStore,
    construir_prompt_secuencial,
    initial_storyboard_state,
    resolve_scene_context,
)
from src.visual_beats import VisualBeat
from src.visual_story_mapper import enrich_beat_visual_meta


def _beat(location: str = "", camera_type: str = "medium_shot", text: str = "t", action: str = "a") -> VisualBeat:
    return VisualBeat(
        beat_id=1,
        scene=1,
        original_text=text,
        action=action,
        emotion="n",
        context="",
        location=location,
        time_of_day="",
        shot_role="action",
        camera_type=camera_type,
        camera_position="",
        camera_distance="",
        importance="n",
        act=1,
    )


def test_regression_construir_prompt_does_not_prefer_camera_priority_over_resolved_camera():
    """
    Bug histórico: camera_block usaba meta.get('camera_priority') or cam, pisando anti-repeat.
    Debe usarse solo `cam` (meta['camera'] resuelto).
    """
    escena = Escena(numero=1, texto="test", duracion_segundos=5.0)
    meta = {
        "location": "calle",
        "action": "caminar",
        "mood": "neutral",
        "scene_characters": ["protagonist"],
        "thematic_context": "generic",
        "visual_device": "literal",
        "narrative_representation_mode": "literal",
        "scene_focus": "protagonist_face",
        "symbolic_descriptions": [],
        "camera_priority": "close up",
        "camera": "wide shot",
    }
    prompt = construir_prompt(escena, scene_meta=meta)
    line = extract_camera_line_from_prompt(prompt)
    assert "wide shot" in line.lower()
    assert "close up" not in line.lower()


def test_regression_sequential_prompt_uses_resolved_camera_not_stale_priority():
    """Si enriched_meta tuviera camera_priority distinto, el bloque CAMERA debe seguir ctx.resolved_camera."""
    state = initial_storyboard_state("r")
    store = CharacterStateStore()
    b = _beat(location="plaza", camera_type="rear_view", text="mira atrás", action="mirar")
    base = map_beat_to_visual_meta(b)
    full = enrich_beat_visual_meta(base)
    full["camera_priority"] = "close up"  # forzar valor “viejo” incompatible con beat
    ctx = resolve_scene_context(0, b, base, full, state, store)
    assert ctx.resolved_camera == "rear view"
    prompt = construir_prompt_secuencial(ctx, full, "")
    cam_line = extract_camera_line_from_prompt(prompt)
    assert "rear view" in cam_line.lower()
    # El prompt secuencial no debe terminar mostrando solo close up como plano final
    assert "close up" not in cam_line.lower()
    # No debe mezclar nota contradictoria del beat original
    assert "director note" not in cam_line.lower()
    assert "rear_view" not in cam_line.lower()


def test_regression_camera_block_clean_when_beat_and_resolved_differ():
    state = initial_storyboard_state("r2")
    store = CharacterStateStore()
    b = _beat(location="pasillo del edificio", camera_type="wide_shot", text="avanza", action="caminar")
    base = map_beat_to_visual_meta(b)
    full = enrich_beat_visual_meta(base)
    # Forzar prev cámara para anti-repeat => resolución final distinta a wide_shot
    state.last_camera = "wide shot"
    ctx = resolve_scene_context(1, b, base, full, state, store)
    prompt = construir_prompt_secuencial(ctx, full, "")
    cam_line = extract_camera_line_from_prompt(prompt).lower()
    assert ctx.resolved_camera in cam_line
    assert "wide_shot" not in cam_line
    assert "director note" not in cam_line


def test_regression_beat_location_not_replaced_by_scene_type_template():
    unique = "LOCAL_UNICO_CAFE_PORTEÑO_XYZ"
    b = _beat(location=unique, text="Toma café.", action="beber")
    meta = map_beat_to_visual_meta(b)
    assert meta.get("location") == unique
    assert "simple private room" not in meta.get("location", "").lower()
