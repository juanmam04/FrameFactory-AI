"""Persistent, approval-gated editorial preproduction for every Studio project."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.documentary.project import load_project, save_project

router = APIRouter(prefix="/api/projects", tags=["editorial"])

STAGES = (
    ("brief", "Brief creativo"),
    ("concepts", "Investigación e ideas"),
    ("packaging", "Títulos, miniaturas y hooks"),
    ("structure", "Sinopsis y mapa narrativo"),
    ("bible", "Biblia narrativa y financiera"),
    ("visual", "Identidad visual y continuidad"),
    ("production", "Plan de producción y auditoría"),
)
STAGE_IDS = tuple(stage for stage, _ in STAGES)

DEFAULT_VISUAL = {
    "style": "modern_2d_animation",
    "character_design": "expressive_2d_stylized",
    "photorealistic_people": False,
    "environment_design": "illustrated_cinematic_2d",
    "continuity_required": True,
}

def fresh() -> dict[str, Any]:
    return {
        "version": 1,
        "stages": {key: {"data": {}, "approved": False, "approved_at": None} for key in STAGE_IDS},
        "history": [],
        "active_stage": "brief",
    }

def current(project: dict[str, Any]) -> dict[str, Any]:
    editorial = deepcopy(project.get("editorial") or fresh())
    for key in STAGE_IDS:
        editorial.setdefault("stages", {}).setdefault(key, {"data": {}, "approved": False, "approved_at": None})
    editorial.setdefault("history", [])
    editorial.setdefault("active_stage", "brief")
    return editorial

class StageUpdate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    approve: bool = False

def _load(project_id: str) -> dict[str, Any]:
    try:
        return load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Project not found") from exc

def _validate(stage: str, data: dict[str, Any]):
    if stage == "brief":
        for key in ("language", "premise", "narration", "tone", "duration_min"):
            if not data.get(key):
                raise HTTPException(422, f"Brief requires: {key}")
        if data["language"] not in ("es", "en"):
            raise HTTPException(422, "Language must be es or en")
    elif stage in ("concepts", "packaging"):
        if len(data.get("options") or []) < 3 or not data.get("selected"):
            raise HTTPException(422, "Three options and a selected option are required")
        ids = [str(option.get("id", "")) for option in data["options"] if isinstance(option, dict)]
        if str(data["selected"]) not in ids:
            raise HTTPException(422, "Selected option must exist")
    elif stage == "structure":
        if len(data.get("acts") or []) < 3:
            raise HTTPException(422, "Structure needs at least three acts")
    elif stage == "bible":
        for key in ("setting", "characters", "timeline", "economics", "ending"):
            if not data.get(key):
                raise HTTPException(422, f"Narrative bible requires: {key}")
    elif stage == "visual":
        if not data.get("style") or not data.get("characters") or not data.get("locations"):
            raise HTTPException(422, "Visual bible needs style, characters and locations")
    elif stage == "production":
        if not data.get("continuity_checks") or not data.get("script_plan"):
            raise HTTPException(422, "Production requires continuity checks and script plan")

@router.get("/{project_id}/editorial")
def get_editorial(project_id: str):
    p = _load(project_id)
    return {"project_id": project_id, "editorial": current(p), "stage_labels": dict(STAGES),
            "default_visual": DEFAULT_VISUAL}

@router.put("/{project_id}/editorial/{stage}")
def update_editorial(project_id: str, stage: str, body: StageUpdate):
    if stage not in STAGE_IDS:
        raise HTTPException(404, "Unknown editorial stage")
    p = _load(project_id)
    ed = current(p)
    index = STAGE_IDS.index(stage)
    if index and not ed["stages"][STAGE_IDS[index-1]]["approved"]:
        raise HTTPException(409, "Approve the preceding stage first")
    _validate(stage, body.data)
    previous = ed["stages"][stage]
    changed = previous["data"] != body.data
    previous["data"] = body.data
    previous["approved"] = bool(body.approve)
    previous["approved_at"] = datetime.now(timezone.utc).isoformat() if body.approve else None
    if changed or not body.approve:
        # Never silently keep dependent approvals after an upstream change.
        for later in STAGE_IDS[index+1:]:
            ed["stages"][later]["approved"] = False
            ed["stages"][later]["approved_at"] = None
        p["story_plan_approved"] = False
        p["script_approved"] = False
    if stage == "brief":
        p["language"] = body.data["language"]
        p["target_duration_min"] = [int(body.data["duration_min"][0]), int(body.data["duration_min"][-1])]
    if body.approve and index < len(STAGE_IDS)-1:
        ed["active_stage"] = STAGE_IDS[index+1]
    else:
        ed["active_stage"] = stage
    ed["history"].append({"stage": stage, "action": "approved" if body.approve else "saved",
                          "at": datetime.now(timezone.utc).isoformat()})
    p["editorial"] = ed
    save_project(p)
    return {"editorial": ed, "ready_for_script": all(ed["stages"][key]["approved"] for key in STAGE_IDS)}

@router.post("/{project_id}/editorial/reopen/{stage}")
def reopen_editorial(project_id: str, stage: str):
    if stage not in STAGE_IDS:
        raise HTTPException(404, "Unknown editorial stage")
    p = _load(project_id)
    ed = current(p)
    for key in STAGE_IDS[STAGE_IDS.index(stage):]:
        ed["stages"][key]["approved"] = False
        ed["stages"][key]["approved_at"] = None
    ed["active_stage"] = stage
    p["story_plan_approved"] = False
    p["script_approved"] = False
    p["editorial"] = ed
    save_project(p)
    return {"editorial": ed}
