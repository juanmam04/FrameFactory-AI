"""Detección de acción y overrides automáticos en meta/prompt."""
from src.action_scene import (
    ACTION_REQUIREMENT_BLOCK,
    apply_action_scene_meta_overrides,
    detect_action_scene,
    detect_action_scene_from_fields,
)
from src.prompt_builder import compute_beat_prompt_bundle
from src.storyboard_continuity import CharacterStateStore, initial_storyboard_state
from src.visual_beats import VisualBeat


def _beat_action_phone_group() -> VisualBeat:
    txt = "el protagonista levanta el teléfono y se une a un grupo"
    return VisualBeat(
        beat_id=1,
        scene=1,
        original_text=txt,
        action=txt,
        emotion="neutral",
        context="",
        location="calle",
        time_of_day="day",
        shot_role="action",
        camera_type="medium_shot",
        camera_position="",
        camera_distance="",
        importance="normal",
        act=1,
    )


def test_detect_action_from_user_example():
    b = _beat_action_phone_group()
    assert detect_action_scene(b) is True
    assert detect_action_scene_from_fields("", "levanta y corre", "") is True


def test_detect_action_false_when_static():
    assert (
        detect_action_scene_from_fields(
            "El protagonista permanece inmóvil mirando la pared.",
            "Silencio en la habitación.",
            "",
        )
        is False
    )


def test_apply_override_swaps_empty_room_tension():
    meta = {
        "visual_device": "empty_room_tension",
        "scene_focus": "protagonist_face",
        "scene_characters": ["protagonist"],
        "thematic_context": None,
        "action": "corre hacia la puerta",
    }
    # Sin beat: usa action + escena_text
    out = apply_action_scene_meta_overrides(meta, escena_text="corre hacia la puerta")
    assert out["scene_focus"] == "full_body_action"
    assert out["visual_device"] == "dynamic_interaction"
    assert out.get("action_scene_dynamic") is True


def test_apply_group_interaction_when_multiple_characters():
    meta = {
        "visual_device": "empty_room_tension",
        "scene_focus": "protagonist_face",
        "scene_characters": ["protagonist", "friend_main"],
        "thematic_context": None,
        "action": "entrega el sobre",
    }
    out = apply_action_scene_meta_overrides(meta, escena_text="entrega el sobre a su amigo")
    assert out["visual_device"] == "group_interaction"


def test_pipeline_user_example_prompt_and_meta():
    b = _beat_action_phone_group()
    state = initial_storyboard_state("test_proj")
    store = CharacterStateStore()
    prompt, _gen_meta, bundle = compute_beat_prompt_bundle(0, b, state, store, None)

    assert bundle.enriched_meta.get("scene_focus") == "full_body_action"
    assert "empty_room_tension" not in prompt
    assert "ACTION REQUIREMENT:" in prompt
    assert ACTION_REQUIREMENT_BLOCK.splitlines()[0] in prompt
    assert "COMPOSITION RULES:" in prompt
    assert "No static standing pose allowed." in prompt
