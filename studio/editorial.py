"""Persistent, approval-gated editorial preproduction for every Studio project."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
import json
import os
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

class GenerateRequest(BaseModel):
    guidance: str = ""

def _generate_stage_content(stage: str, p: dict[str, Any], guidance: str) -> dict[str, Any]:
    from openai import OpenAI
    from src.documentary.openai_key import require_openai_api_key
    ed = current(p)
    idx = STAGE_IDS.index(stage)
    context = {name: ed["stages"][name]["data"] for name in STAGE_IDS[:idx]}
    locale = str((context.get("brief") or {}).get("language") or p.get("language") or "es")
    requirement = {
        "concepts": "Create three distinct original story pitches with credible causal stakes. Each option has id,title,premise,hook,thumbnail,why_it_works,risks. Include selected default A.",
        "packaging": "Create three DISTINCT title+thumbnail+first-30-second-hook combinations for the selected premise. Each option has id,title,thumbnail,hook,retention,risks. Include selected default A.",
        "structure": "Create 7-9 acts, each with title,start_min,end_min,events,viewer_reward. Honour requested duration and chosen hook, avoid filler.",
        "bible": "Make a coherent original story bible: setting,characters array (name,role,arc,visual),timeline,economics (numbers and cash sources logically reconciled),ending,continuity_risks. Distinguish narrative fiction from sourced facts.",
        "visual": "Produce style modern_2d_animation, characters array with invariant 2D features, locations array with architecture, props, time periods and continuity_rules array. STRICTLY no photorealistic human characters. Visual environments are 2D illustrated.",
        "production": "Produce script_plan with intended pacing, scenes and narration strategy; continuity_checks array and quality_gate describing meaningful editorial tests and visual asset requirements.",
    }[stage]
    prompt = ("You are FrameFactory senior story editor, audience strategist, continuity supervisor and critical reviewer. "
              "Write commercially compelling adult longform narrative, not fake documentary. Never promise viral outcome. "
              "Avoid formulaic manufactured cliffhangers, repetitive motivation, copied plots, magic money, invented verified facts. "
              "All data must be concrete, coherent and distinctive. Output one JSON object only. "
              "Respond in "+("native Spanish" if locale=="es" else "native English")+". "
              +requirement)
    result = OpenAI(api_key=require_openai_api_key("Generación editorial")).chat.completions.create(
        model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),temperature=0.75,
        response_format={"type":"json_object"},messages=[
            {"role":"system","content":prompt},
            {"role":"user","content":json.dumps({"previous_approved_stages":context,"guidance":guidance,"project_topic":p.get("topic")},ensure_ascii=False)},
        ])
    data=json.loads(result.choices[0].message.content or "{}")
    if not isinstance(data,dict):
        raise ValueError("Invalid editorial AI response")
    _validate(stage,data)
    return data

@router.post("/{project_id}/editorial/{stage}/generate")
def generate_editorial(project_id: str,stage: str,body: GenerateRequest):
    if stage not in STAGE_IDS or stage=="brief":
        raise HTTPException(404,"Cannot generate this stage")
    p=_load(project_id)
    ed=current(p)
    idx=STAGE_IDS.index(stage)
    if not ed["stages"][STAGE_IDS[idx-1]]["approved"]:
        raise HTTPException(409,"Approve preceding stage first")
    try:
        data=_generate_stage_content(stage,p,body.guidance[:2000])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502,"Editorial generation failed: "+str(exc)[:300]) from exc
    ed["stages"][stage]={"data":data,"approved":False,"approved_at":None}
    for later in STAGE_IDS[idx+1:]:
        ed["stages"][later]["approved"]=False
        ed["stages"][later]["approved_at"]=None
    ed["active_stage"]=stage
    p["editorial"]=ed
    save_project(p)
    return {"editorial":ed,"generated":data}

@router.get("/{project_id}/editorial/export")
def export_editorial(project_id: str):
    p=_load(project_id)
    ed=current(p)
    return {"project_id":project_id,"title":p.get("title"),"language":p.get("language"),
            "approved":all(ed["stages"][k]["approved"] for k in STAGE_IDS),
            "brief":ed["stages"]["brief"]["data"],"concepts":ed["stages"]["concepts"]["data"],
            "packaging":ed["stages"]["packaging"]["data"],"structure":ed["stages"]["structure"]["data"],
            "narrative_bible":ed["stages"]["bible"]["data"],"visual_bible":ed["stages"]["visual"]["data"],
            "production_plan":ed["stages"]["production"]["data"]}

@router.post("/{project_id}/editorial/audit")
def audit_script(project_id: str):
    p=_load(project_id)
    if not p.get("script"): raise HTTPException(409,"Generate the script first")
    ed=current(p)
    if not all(ed["stages"][k]["approved"] for k in STAGE_IDS):
        raise HTTPException(409,"Approve preproduction first")
    try:
        from openai import OpenAI
        from src.documentary.openai_key import require_openai_api_key
        response=OpenAI(api_key=require_openai_api_key("Editorial audit")).chat.completions.create(
          model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),temperature=0.2,
          response_format={"type":"json_object"},
          messages=[{"role":"system","content":"You are a demanding story editor. Analyze factual consistency within fiction, financial logic, opening promise, attention risks and redundancy. Return JSON with verdict (pass or revise), issues list, strengths list, recommended_fixes list. Do not estimate virality probabilities."},
                    {"role":"user","content":json.dumps({"brief":ed["stages"]["brief"]["data"],"bible":ed["stages"]["bible"]["data"],"packaging":ed["stages"]["packaging"]["data"],"script":str(p["script"])[:45000]},ensure_ascii=False)}])
        audit=json.loads(response.choices[0].message.content or "{}")
        p["editorial_audit"]=audit
        save_project(p)
        return {"audit":audit}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502,"Audit failed: "+str(exc)[:180]) from exc
