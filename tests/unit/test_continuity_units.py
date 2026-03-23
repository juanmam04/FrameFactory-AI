"""Tests unitarios: resolve_location, resolve_camera, personaje, sanitize, update_storyboard_state."""
from __future__ import annotations

from src.storyboard_continuity import (
    CharacterStateStore,
    ResolvedCamera,
    ResolvedLocation,
    SceneContinuity,
    StoryboardState,
    initial_storyboard_state,
    resolve_camera,
    resolve_character_state,
    resolve_interior_subtype,
    resolve_location,
    sanitize_symbolic_elements_by_subtype,
    sanitize_symbolic_elements,
    symbolic_overlay_allowed,
    update_storyboard_state,
)
from src.visual_beats import VisualBeat


def _beat(
    bid: int = 1,
    text: str = "x",
    action: str = "y",
    location: str = "",
    camera_type: str = "medium_shot",
    context: str = "",
) -> VisualBeat:
    return VisualBeat(
        beat_id=bid,
        scene=1,
        original_text=text,
        action=action,
        emotion="neutral",
        context=context,
        location=location,
        time_of_day="",
        shot_role="action",
        camera_type=camera_type,
        camera_position="",
        camera_distance="",
        importance="normal",
        act=1,
    )


class TestResolveLocation:
    def test_uses_beat_location_when_present(self):
        state = initial_storyboard_state("p")
        b = _beat(location="café porteño con ventanal")
        base = {"scene_type": "city_street", "location": "generic city template"}
        r = resolve_location(b, state, base)
        assert isinstance(r, ResolvedLocation)
        assert r.source == "beat.location"
        assert r.location_prompt == "café porteño con ventanal"
        assert r.inherited_from_previous is False
        assert r.changed is True

    def test_inherits_when_empty_beat_location_and_no_strong_change(self):
        state = initial_storyboard_state("p")
        state.current_location_prompt = "calle oscura con neones"
        state.current_location_id = "calle_oscura_con_neones"
        b = _beat(text="Sigue corriendo.", action="correr", location="")
        base = {"scene_type": "city_street", "location": "city street template"}
        r = resolve_location(b, state, base)
        assert r.source == "state_inheritance"
        assert r.inherited_from_previous is True
        assert r.changed is False
        assert r.location_prompt == "calle oscura con neones"

    def test_fallback_inference_when_no_inheritance(self):
        state = initial_storyboard_state("p")
        b = _beat(text="Todo pasa en un aula.", action="escribir", location="")
        base = {"scene_type": "classroom", "location": "classroom with desks"}
        r = resolve_location(b, state, base)
        assert r.source == "text_inference"
        assert "classroom" in r.location_prompt.lower()

    def test_flags_changed_when_beat_location_differs_from_prev(self):
        state = initial_storyboard_state("p")
        state.current_location_id = "a"
        state.current_location_prompt = "lugar A"
        b = _beat(location="lugar B distinto")
        r = resolve_location(b, state, {"scene_type": "generic_interior", "location": "x"})
        assert r.changed is True


class TestResolveCamera:
    def test_uses_beat_camera_type(self):
        state = StoryboardState()
        b = _beat(camera_type="wide_shot")
        full = {"camera_priority": "close up"}
        r = resolve_camera(b, full, state, cameras=["wide shot", "medium shot", "close up"])
        assert r.inherited_from_beat is True
        assert r.chosen_camera == "wide shot"

    def test_avoids_consecutive_duplicate(self):
        state = StoryboardState(last_camera="wide shot")
        b = _beat(camera_type="wide_shot")
        full = {"camera_priority": "wide shot"}
        cams = ["wide shot", "medium shot", "close up"]
        r = resolve_camera(b, full, state, cameras=cams)
        assert r.chosen_camera != "wide shot"
        assert r.changed_due_to_repeat is True

    def test_chosen_camera_matches_resolved_context_in_pipeline(self):
        """Integración mínima: resolve_camera output == ctx.resolved_camera (vía resolve_scene_context)."""
        from src.scene_visual_mapper import map_beat_to_visual_meta
        from src.visual_story_mapper import enrich_beat_visual_meta
        from src.storyboard_continuity import resolve_scene_context

        state = initial_storyboard_state("t")
        store = CharacterStateStore()
        b = _beat(camera_type="close_up", location="sala", text="t", action="a")
        base = map_beat_to_visual_meta(b)
        full = enrich_beat_visual_meta(base)
        ctx = resolve_scene_context(0, b, base, full, state, store)
        rc = resolve_camera(b, full, initial_storyboard_state("t"), cameras=["wide shot", "medium shot", "close up"])
        assert ctx.resolved_camera == rc.chosen_camera


class TestResolveCharacterState:
    def test_protagonist_stable_across_two_beats(self):
        store = CharacterStateStore()
        b1 = _beat(bid=1, text="uno", action="a", location="calle")
        b2 = _beat(bid=2, text="dos", action="b", location="calle")
        s1 = resolve_character_state(store, b1, 0, ["protagonist"], {})
        s2 = resolve_character_state(store, b2, 1, ["protagonist"], {})
        assert "Locked appearance:" in s1 and "Locked appearance:" in s2
        # Misma línea de apariencia (mismo slot)
        line1 = [x for x in s1.split("\n") if "Locked appearance:" in x][0]
        line2 = [x for x in s2.split("\n") if "Locked appearance:" in x][0]
        assert line1 == line2

    def test_no_outfit_change_without_explicit_event(self):
        store = CharacterStateStore()
        b = _beat(text="Está en la oficina.", action="trabajar", location="oficina")
        resolve_character_state(
            store,
            b,
            0,
            ["protagonist"],
            {"protagonist": {"outfit_base": "formal_dark"}},
        )
        slot = store.ensure_protagonist(0)
        assert "casual_dark" in slot.stable_description or "formal" not in slot.stable_description.split("outfit")[0]


class TestSanitizeSymbolic:
    def test_strips_interior_overlay_on_exterior_scene(self):
        tags = ["empty_room_tension", "empty_chair", "single_lamp"]
        descs = ["empty chair", "desk lamp"]
        nt, nd, reason = sanitize_symbolic_elements("city_street", "empty_room_tension", tags, descs)
        assert nt == []
        assert not any("chair" in d.lower() and "empty" in d.lower() for d in nd)
        assert "filtered" in reason.lower() or "incompatible" in reason.lower()

    def test_preserves_when_compatible(self):
        tags = ["phone_call"]
        descs = ["glowing phone"]
        nt, nd, reason = sanitize_symbolic_elements("generic_interior", "phone_call", tags, descs)
        assert nt == tags
        assert nd == descs
        assert "compatible" in reason.lower()

    def test_symbolic_overlay_allowed_false_for_street_empty_room(self):
        assert symbolic_overlay_allowed("city_street", "empty_room_tension") is False

    def test_generic_exterior_also_filters_empty_room_device(self):
        tags = ["empty_room_tension", "desk"]
        descs = ["desk lamp indoors"]
        nt, nd, reason = sanitize_symbolic_elements("generic_exterior", "empty_room_tension", tags, descs)
        assert nt == []
        assert "exterior" in " ".join(nd).lower() or "outdoor" in " ".join(nd).lower()
        assert "filtered" in reason.lower() or "incompatible" in reason.lower()

    def test_hallway_subtype_filters_room_props(self):
        subtype = resolve_interior_subtype(
            resolved_location="pasillo del edificio",
            scene_type="generic_interior",
            action="avanza por el pasillo",
            text="puertas a ambos lados",
        )
        assert subtype == "hallway"
        tags = ["empty_room_tension", "empty_chair", "single_lamp", "door"]
        descs = [
            "empty chair facing the protagonist",
            "single desk lamp as main light source",
            "door",
        ]
        nt, nd, reason = sanitize_symbolic_elements_by_subtype(
            interior_subtype=subtype,
            scene_type="generic_interior",
            visual_device="empty_room_tension",
            symbolic_tags=tags,
            symbolic_descriptions=descs,
        )
        out = " ".join(nd).lower()
        assert nt == []
        assert "desk" not in out and "lamp" not in out and "bed" not in out and "sofa" not in out
        assert "corridor" in out or "hallway" in out
        assert "neutralized" in reason

    def test_living_subtype_keeps_living_and_blocks_bedroom_props(self):
        subtype = resolve_interior_subtype(
            resolved_location="living del apartamento con sofa",
            scene_type="home_living_room",
            action="mira el telefono",
            text="en la sala",
        )
        assert subtype == "living_room"
        tags = ["phone_call", "phone_screen", "desk", "lamp"]
        descs = [
            "glowing phone screen with important caller ID visible",
            "sofa near coffee table",
            "bed near window",
        ]
        nt, nd, reason = sanitize_symbolic_elements_by_subtype(
            interior_subtype=subtype,
            scene_type="home_living_room",
            visual_device="phone_call",
            symbolic_tags=tags,
            symbolic_descriptions=descs,
        )
        out = " ".join(nd).lower()
        assert nt == []
        assert "bed" not in out
        assert ("sofa" in out) or ("living room" in out)
        assert "neutralized" in reason


class TestUpdateStoryboardState:
    def test_updates_location_camera_action_mood(self):
        state = initial_storyboard_state("proj")
        ctx = SceneContinuity(
            scene_index=1,
            raw_location="",
            resolved_location="nueva loc",
            location_changed=True,
            previous_location="vieja",
            raw_camera="medium_shot",
            resolved_camera="medium shot",
            previous_camera="wide shot",
            action="correr",
            previous_action="caminar",
            characters_present=["protagonist"],
            protagonist_locked_description="lock",
            continuity_block="cont",
            symbolic_overlay_allowed=True,
            symbolic_overlay_reason="ok",
            sanitized_symbolic_descriptions=[],
            seed_material="x",
            protagonist_signature="sig",
        )
        full = {"scene_type": "city_street", "mood": "tense"}
        update_storyboard_state(state, ctx, full, beat=_beat())
        assert state.current_location_prompt == "nueva loc"
        assert state.last_camera == "medium shot"
        assert state.last_action == "correr"
        assert state.current_mood == "tense"
        assert "location_updated" in state.continuity_notes

    def test_mood_not_wiped_when_full_meta_omits_mood(self):
        state = initial_storyboard_state("p")
        state.current_mood = "happy"
        ctx = SceneContinuity(
            scene_index=0,
            raw_location="",
            resolved_location="loc",
            location_changed=False,
            previous_location=None,
            raw_camera="",
            resolved_camera="close up",
            previous_camera=None,
            action="x",
            previous_action=None,
            characters_present=["protagonist"],
            protagonist_locked_description="l",
            continuity_block="c",
            symbolic_overlay_allowed=True,
            symbolic_overlay_reason="r",
            sanitized_symbolic_descriptions=[],
            seed_material="s",
            protagonist_signature="p",
        )
        update_storyboard_state(state, ctx, {"scene_type": "generic_interior"}, beat=None)
        assert state.current_mood == "happy"

    def test_preserves_notes_append_only(self):
        state = initial_storyboard_state("p")
        state.continuity_notes = ["existing"]
        ctx = SceneContinuity(
            scene_index=0,
            raw_location="",
            resolved_location="loc",
            location_changed=True,
            previous_location=None,
            raw_camera="",
            resolved_camera="wide shot",
            previous_camera=None,
            action="a",
            previous_action=None,
            characters_present=["protagonist"],
            protagonist_locked_description="l",
            continuity_block="c",
            symbolic_overlay_allowed=True,
            symbolic_overlay_reason="r",
            sanitized_symbolic_descriptions=[],
            seed_material="s",
            protagonist_signature="p",
        )
        update_storyboard_state(state, ctx, {"scene_type": "x", "mood": "calm"}, beat=None)
        assert "existing" in state.continuity_notes
