"""Serialización y dumps JSON para auditar el pipeline de prompts (sin modelo de imagen)."""
from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from .storyboard_continuity import SceneContinuity, StoryboardState
from .visual_beats import VisualBeat


def clone_storyboard_state(state: StoryboardState) -> StoryboardState:
    """Copia profunda mínima para snapshot antes/después."""
    return StoryboardState(
        current_location_id=state.current_location_id,
        current_location_prompt=state.current_location_prompt,
        current_scene_type=state.current_scene_type,
        current_time_of_day=state.current_time_of_day,
        current_mood=state.current_mood,
        current_characters=list(state.current_characters),
        protagonist_profile=copy.deepcopy(state.protagonist_profile),
        wardrobe_state=copy.deepcopy(state.wardrobe_state),
        last_camera=state.last_camera,
        last_action=state.last_action,
        last_prompt_summary=state.last_prompt_summary,
        continuity_notes=list(state.continuity_notes),
        project_id=state.project_id,
        video_theme=state.video_theme,
    )


def storyboard_state_to_dict(state: StoryboardState) -> dict[str, Any]:
    return {
        "current_location_id": state.current_location_id,
        "current_location_prompt": state.current_location_prompt,
        "current_scene_type": state.current_scene_type,
        "current_time_of_day": state.current_time_of_day,
        "current_mood": state.current_mood,
        "current_characters": list(state.current_characters),
        "protagonist_profile": copy.deepcopy(state.protagonist_profile),
        "wardrobe_state": copy.deepcopy(state.wardrobe_state),
        "last_camera": state.last_camera,
        "last_action": state.last_action,
        "last_prompt_summary": state.last_prompt_summary,
        "continuity_notes": list(state.continuity_notes),
        "project_id": state.project_id,
        "video_theme": state.video_theme,
    }


def scene_continuity_to_dict(ctx: SceneContinuity) -> dict[str, Any]:
    if is_dataclass(ctx):
        return asdict(ctx)
    raise TypeError(type(ctx))


def visual_beat_to_dict(beat: VisualBeat) -> dict[str, Any]:
    return asdict(beat)


def extract_camera_line_from_prompt(prompt: str) -> str:
    """Línea efectiva de cámara (después de 'CAMERA:' o 'Camera:')."""
    lower = prompt.lower()
    key = "camera:\n"
    i = lower.find(key)
    if i == -1:
        return ""
    rest = prompt[i + len(key) :]
    line = rest.split("\n", 1)[0].strip()
    return line


@dataclass
class BeatPromptDebugBundle:
    scene_index: int
    beat_id: int
    state_before: dict[str, Any]
    state_after: dict[str, Any]
    beat: dict[str, Any]
    base_meta: dict[str, Any]
    enriched_meta: dict[str, Any]
    resolved_context: dict[str, Any]
    prompt_final: str
    gen_meta: dict[str, Any]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "scene_index": self.scene_index,
            "beat_id": self.beat_id,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "beat": self.beat,
            "base_meta": self.base_meta,
            "enriched_meta": self.enriched_meta,
            "resolved_context": self.resolved_context,
            "prompt_final": self.prompt_final,
            "gen_meta": self.gen_meta,
        }


def write_beat_debug_json(bundle: BeatPromptDebugBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(bundle.to_json_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_meta_for_golden(meta: dict[str, Any]) -> dict[str, Any]:
    """Quita claves internas volátiles si hiciera falta (placeholder)."""
    m = dict(meta)
    m.pop("_beat_camera_position", None)
    return m
