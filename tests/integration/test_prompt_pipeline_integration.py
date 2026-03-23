"""Integración: beat → meta → enriched → resolved → prompt → estado (sin modelo de imagen)."""
from __future__ import annotations

from src.prompt_builder import compute_beat_prompt_bundle, prompts_para_beats
from src.storyboard_continuity import initial_storyboard_state, CharacterStateStore
from src.storyboard_debug import extract_camera_line_from_prompt
from src.visual_beats import VisualBeat


def _b(
    bid: int,
    scene: int,
    text: str,
    action: str,
    location: str = "",
    camera_type: str = "medium_shot",
) -> VisualBeat:
    return VisualBeat(
        beat_id=bid,
        scene=scene,
        original_text=text,
        action=action,
        emotion="neutral",
        context="",
        location=location,
        time_of_day="noche",
        shot_role="action",
        camera_type=camera_type,
        camera_position="",
        camera_distance="",
        importance="normal",
        act=1,
    )


class TestCaseAStreetToApartment:
    """CASO A: calle → misma calle → edificio → pasillo → living."""

    @classmethod
    def setup_method(cls):
        cls.beats = [
            _b(1, 1, "Camina por la calle.", "caminar", "calle oscura con neones", "wide_shot"),
            _b(2, 2, "Corre por la misma calle.", "correr", "", "medium_shot"),
            _b(3, 3, "Entra a un edificio.", "entrar al edificio", "entrada del edificio", "medium_shot"),
            _b(4, 4, "Pasillo interior.", "caminar", "pasillo del edificio", "close_up"),
            _b(5, 5, "Living.", "sentarse en el sofa", "living del apartamento con sofa", "wide_shot"),
        ]

    def test_scenes_1_and_2_share_resolved_location(self):
        state = initial_storyboard_state("case_a")
        store = CharacterStateStore()
        _, _, b1 = compute_beat_prompt_bundle(0, self.beats[0], state, store, None)
        _, _, b2 = compute_beat_prompt_bundle(1, self.beats[1], state, store, None)
        assert b1.resolved_context["resolved_location"] == b2.resolved_context["resolved_location"]
        assert "calle oscura con neones" in b1.resolved_context["resolved_location"]

    def test_scene_3_transition_and_scene_4_not_generic_bedroom(self):
        state = initial_storyboard_state("case_a")
        store = CharacterStateStore()
        for i in range(2):
            compute_beat_prompt_bundle(i, self.beats[i], state, store, None)
        _, _, b3 = compute_beat_prompt_bundle(2, self.beats[2], state, store, None)
        assert b3.resolved_context["location_changed"] is True
        assert "edificio" in b3.resolved_context["resolved_location"].lower() or "entrada" in b3.resolved_context[
            "resolved_location"
        ].lower()
        _, _, b4 = compute_beat_prompt_bundle(3, self.beats[3], state, store, None)
        prompt4 = b4.prompt_final.lower()
        assert "pasillo" in prompt4
        assert "simple private room" not in prompt4  # plantilla bedroom genérica no debe pisar beat.location

    def test_scene_5_living_coherent(self):
        state = initial_storyboard_state("case_a")
        store = CharacterStateStore()
        for i in range(5):
            _, _, bundle = compute_beat_prompt_bundle(i, self.beats[i], state, store, None)
        assert "living" in bundle.prompt_final.lower() or "sofa" in bundle.prompt_final.lower()

    def test_protagonist_lock_stable_all_five(self):
        state = initial_storyboard_state("case_a")
        store = CharacterStateStore()
        first_lock = None
        for i in range(5):
            _, _, bundle = compute_beat_prompt_bundle(i, self.beats[i], state, store, None)
            lock_line = [x for x in bundle.prompt_final.split("\n") if "Locked appearance:" in x][0]
            if first_lock is None:
                first_lock = lock_line
            assert lock_line == first_lock

    def test_cameras_not_all_identical(self):
        triples = prompts_para_beats(self.beats, shuffle_planos=False, project_id="case_a")
        cams = [extract_camera_line_from_prompt(p) for _, p, _ in triples]
        assert len(set(cams)) >= 2

    def test_continuity_block_present_from_scene_2(self):
        state = initial_storyboard_state("case_a")
        store = CharacterStateStore()
        compute_beat_prompt_bundle(0, self.beats[0], state, store, None)
        _, _, b2 = compute_beat_prompt_bundle(1, self.beats[1], state, store, None)
        assert "CONTINUITY FROM PREVIOUS SCENE" in b2.prompt_final
        assert "Previous location was:" in b2.prompt_final


class TestCaseBSameRoom:
    def test_three_scenes_same_location_string(self):
        room = "dormitorio pequeño con cama y escritorio, lámpara cálida"
        beats = [
            _b(1, 1, "Mira la ventana.", "mirar", room, "wide_shot"),
            _b(2, 2, "Se sienta triste.", "sentarse", "", "close_up"),
            _b(3, 3, "Llora.", "llorar", "", "medium_shot"),
        ]
        state = initial_storyboard_state("case_b")
        store = CharacterStateStore()
        locs = []
        actions = []
        for i, b in enumerate(beats):
            _, _, bundle = compute_beat_prompt_bundle(i, b, state, store, None)
            locs.append(bundle.resolved_context["resolved_location"])
            actions.append(bundle.resolved_context["action"])
        assert locs[0] == locs[1] == locs[2] == room
        assert len(set(actions)) == 3
        triples = prompts_para_beats(beats, project_id="case_b")
        for _, prompt, _ in triples:
            assert room in prompt


class TestCaseCExteriorSymbolic:
    def test_exterior_neutralizes_interior_overlay(self):
        beat = _b(1, 1, "Noche en la calle vacía.", "caminar solo", "", "wide_shot")
        triples = prompts_para_beats([beat], project_id="case_c")
        prompt = triples[0][1]
        # Calle + acción: no empty_room_tension ni mobiliario de ficha interior
        assert "empty_room_tension" not in prompt
        assert "empty chair facing the protagonist" not in prompt.lower()
        assert "dynamic_interaction" in prompt or "ACTION REQUIREMENT" in prompt


class TestDebugOutputWritesJson:
    def test_debug_dir_writes_one_file_per_beat(self, tmp_path):
        beats = [
            _b(1, 1, "a", "a", "lugar", "wide_shot"),
            _b(2, 2, "b", "b", "", "medium_shot"),
        ]
        prompts_para_beats(beats, project_id="dbg", debug_output_dir=tmp_path)
        files = sorted(tmp_path.glob("scene_*.json"))
        assert len(files) == 2
        import json

        data = json.loads(files[0].read_text(encoding="utf-8"))
        for key in (
            "beat",
            "base_meta",
            "enriched_meta",
            "resolved_context",
            "prompt_final",
            "state_before",
            "state_after",
        ):
            assert key in data
