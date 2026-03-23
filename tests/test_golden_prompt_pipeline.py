"""
Snapshots JSON del pipeline (tests/fixtures/golden/).

Actualizar fixtures tras cambios intencionales en YAML/prompts:
  set UPDATE_PROMPT_GOLDENS=1
  pytest tests/test_golden_prompt_pipeline.py -v
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.prompt_builder import compute_beat_prompt_bundle
from src.storyboard_continuity import CharacterStateStore, initial_storyboard_state
from src.visual_beats import VisualBeat

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "tests" / "fixtures" / "golden"


def _serial_pipeline(beats: list[VisualBeat], pid: str) -> dict:
    state = initial_storyboard_state(project_id=pid, video_theme=None)
    store = CharacterStateStore()
    scenes = []
    for i, beat in enumerate(beats):
        _, _, bundle = compute_beat_prompt_bundle(i, beat, state, store, None)
        scenes.append(
            {
                "beat_id": beat.beat_id,
                "resolved_context": bundle.resolved_context,
                "prompt_final": bundle.prompt_final,
                "state_after": bundle.state_after,
                "gen_meta": bundle.gen_meta,
            }
        )
    return {"project_id": pid, "scenes": scenes}


def _beat_like(
    bid: int,
    scene: int,
    text: str,
    action: str,
    loc: str = "",
    cam: str = "medium_shot",
) -> VisualBeat:
    return VisualBeat(
        beat_id=bid,
        scene=scene,
        original_text=text,
        action=action,
        emotion="neutral",
        context="",
        location=loc,
        time_of_day="noche",
        shot_role="action",
        camera_type=cam,
        camera_position="",
        camera_distance="",
        importance="normal",
        act=1,
    )


def _beats_case_a():
    return [
        _beat_like(1, 1, "Camina por la calle.", "caminar", "calle oscura con neones", "wide_shot"),
        _beat_like(2, 2, "Corre por la misma calle.", "correr", "", "medium_shot"),
        _beat_like(3, 3, "Entra a un edificio.", "entrar", "entrada del edificio", "medium_shot"),
        _beat_like(4, 4, "Pasillo.", "caminar", "pasillo del edificio", "close_up"),
        _beat_like(5, 5, "Living.", "sentarse", "living del apartamento con sofa", "wide_shot"),
    ]


def _beats_case_b():
    room = "dormitorio pequeño con cama y escritorio"
    return [
        _beat_like(1, 1, "Mira ventana.", "mirar", room, "wide_shot"),
        _beat_like(2, 2, "Triste en cama.", "sentarse", "", "close_up"),
        _beat_like(3, 3, "Llora.", "llorar", "", "medium_shot"),
    ]


def _beats_case_c():
    return [
        _beat_like(1, 1, "De noche en la calle vacía.", "caminar solo", "", "wide_shot"),
    ]


CASES = [
    ("prompt_pipeline_case_a.json", "golden_a", _beats_case_a),
    ("prompt_pipeline_case_b.json", "golden_b", _beats_case_b),
    ("prompt_pipeline_case_c.json", "golden_c", _beats_case_c),
]


@pytest.mark.parametrize("filename,pid,beats_fn", CASES)
def test_golden_matches_fixture(filename, pid, beats_fn):
    path = GOLDEN_DIR / filename
    assert path.exists(), f"Falta fixture {path}"
    beats = beats_fn()
    actual = _serial_pipeline(beats, pid)
    if os.environ.get("UPDATE_PROMPT_GOLDENS", "").strip().lower() in ("1", "true", "yes"):
        path.write_text(json.dumps(actual, ensure_ascii=False, indent=2), encoding="utf-8")
        pytest.skip("Fixture actualizado (UPDATE_PROMPT_GOLDENS).")
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual == expected
