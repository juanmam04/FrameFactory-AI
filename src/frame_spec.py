"""Estructuras de datos V2: beat -> frame spec -> prompt -> imagen."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from .config_loader import BASE


@dataclass
class FrameSpec:
    frame_id: int
    beat_id: int
    scene_id: int
    scene_priority: str
    event_core: str
    subject: str
    action: str
    physical_motion: str
    location: str
    camera_mode: str
    camera_subject_visibility: str
    composition: str
    emotion: str
    must_visible_entities: list[str] = field(default_factory=list)
    must_visible_evidence: list[str] = field(default_factory=list)
    forbidden_misread: list[str] = field(default_factory=list)
    must_show: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    delta_from_previous: list[str] = field(default_factory=list)
    story_step: str = ""
    expression_key: str | None = None


def framespec_to_dict(spec: FrameSpec) -> dict[str, Any]:
    return asdict(spec)


def framespec_from_dict(data: dict[str, Any]) -> FrameSpec:
    camera_mode = str(data.get("camera_mode") or data.get("camera") or "").strip()
    return FrameSpec(
        frame_id=int(data.get("frame_id", 0)),
        beat_id=int(data.get("beat_id", 0)),
        scene_id=int(data.get("scene_id", 0)),
        scene_priority=str(data.get("scene_priority") or "P1_EVENT_OVER_STYLE").strip(),
        event_core=str(data.get("event_core") or data.get("story_step") or "").strip(),
        subject=str(data.get("subject", "")).strip(),
        action=str(data.get("action", "")).strip(),
        physical_motion=str(data.get("physical_motion") or "").strip(),
        location=str(data.get("location", "")).strip(),
        camera_mode=camera_mode,
        camera_subject_visibility=str(data.get("camera_subject_visibility") or "auto").strip(),
        composition=str(data.get("composition", "")).strip(),
        emotion=str(data.get("emotion", "")).strip(),
        must_visible_entities=list(data.get("must_visible_entities") or []),
        must_visible_evidence=list(data.get("must_visible_evidence") or []),
        forbidden_misread=list(data.get("forbidden_misread") or []),
        must_show=list(data.get("must_show") or []),
        avoid=list(data.get("avoid") or []),
        delta_from_previous=list(data.get("delta_from_previous") or []),
        story_step=str(data.get("story_step", "")).strip(),
        expression_key=(str(data.get("expression_key")).strip() if data.get("expression_key") else None),
    )


def guardar_frame_specs(frame_specs: list[FrameSpec], proyecto: str) -> Path:
    out_dir = BASE / "output" / "meta"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"framespecs_{proyecto}.json"
    payload = [framespec_to_dict(s) for s in frame_specs]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def cargar_frame_specs(proyecto: str) -> list[FrameSpec]:
    path = BASE / "output" / "meta" / f"framespecs_{proyecto}.json"
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    specs: list[FrameSpec] = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            try:
                specs.append(framespec_from_dict(item))
            except Exception:
                continue
    return specs
