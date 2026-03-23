#!/usr/bin/env python3
"""Regenera tests/fixtures/golden/*.json tras cambios deliberados en visual_bible / mappers."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.prompt_builder import compute_beat_prompt_bundle  # noqa: E402
from src.storyboard_continuity import CharacterStateStore, initial_storyboard_state  # noqa: E402
from src.visual_beats import VisualBeat  # noqa: E402


def _beat(bid, scene, text, action, loc="", cam="medium_shot") -> VisualBeat:
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


def _serial(beats: list[VisualBeat], pid: str) -> dict:
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


def main() -> None:
    out = ROOT / "tests" / "fixtures" / "golden"
    out.mkdir(parents=True, exist_ok=True)
    A = [
        _beat(1, 1, "Camina por la calle.", "caminar", "calle oscura con neones", "wide_shot"),
        _beat(2, 2, "Corre por la misma calle.", "correr", "", "medium_shot"),
        _beat(3, 3, "Entra a un edificio.", "entrar", "entrada del edificio", "medium_shot"),
        _beat(4, 4, "Pasillo.", "caminar", "pasillo del edificio", "close_up"),
        _beat(5, 5, "Living.", "sentarse", "living del apartamento con sofa", "wide_shot"),
    ]
    room = "dormitorio pequeño con cama y escritorio"
    B = [
        _beat(1, 1, "Mira ventana.", "mirar", room, "wide_shot"),
        _beat(2, 2, "Triste en cama.", "sentarse", "", "close_up"),
        _beat(3, 3, "Llora.", "llorar", "", "medium_shot"),
    ]
    C = [_beat(1, 1, "De noche en la calle vacía.", "caminar solo", "", "wide_shot")]
    for name, pid, beats in [
        ("prompt_pipeline_case_a.json", "golden_a", A),
        ("prompt_pipeline_case_b.json", "golden_b", B),
        ("prompt_pipeline_case_c.json", "golden_c", C),
    ]:
        p = out / name
        p.write_text(json.dumps(_serial(beats, pid), ensure_ascii=False, indent=2), encoding="utf-8")
        print("Wrote", p)


if __name__ == "__main__":
    main()
