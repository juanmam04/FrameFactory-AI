"""Semillas: determinismo sin random silencioso en el material del pipeline."""
from __future__ import annotations

from src.storyboard_continuity import comfyui_seed_from_material
from src.prompt_builder import prompts_para_beats
from src.visual_beats import VisualBeat


def _one_beat():
    return [
        VisualBeat(
            1,
            1,
            "txt",
            "act",
            "n",
            "",
            "loc fija",
            "",
            "action",
            "wide_shot",
            "",
            "",
            "n",
            1,
        )
    ]


def test_comfyui_seed_same_material_same_int():
    s = "proyecto|1|lid|sig"
    assert comfyui_seed_from_material(s) == comfyui_seed_from_material(s)


def test_comfyui_seed_different_material_different_int():
    a = comfyui_seed_from_material("a|1|x|y")
    b = comfyui_seed_from_material("a|2|x|y")
    assert a != b


def test_prompts_para_beats_seed_material_identical_across_runs():
    beats = _one_beat()
    r1 = prompts_para_beats(beats, project_id="seed_test", shuffle_planos=False)
    r2 = prompts_para_beats(beats, project_id="seed_test", shuffle_planos=False)
    assert r1[0][2]["seed_material"] == r2[0][2]["seed_material"]


def test_seed_material_changes_with_location_or_beat_id():
    b1 = _one_beat()
    b2 = [
        VisualBeat(
            2,
            1,
            "txt",
            "act",
            "n",
            "",
            "otro lugar distinto",
            "",
            "action",
            "wide_shot",
            "",
            "",
            "n",
            1,
        )
    ]
    m1 = prompts_para_beats(b1, project_id="p", shuffle_planos=False)[0][2]["seed_material"]
    m2 = prompts_para_beats(b2, project_id="p", shuffle_planos=False)[0][2]["seed_material"]
    assert m1 != m2
