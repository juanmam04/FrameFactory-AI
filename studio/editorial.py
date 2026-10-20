"""Persistent, approval-gated editorial preproduction for every Studio project."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
import json
import os
from pydantic import BaseModel, Field

from src.documentary.project import load_project, save_project, create_project, list_projects

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
    "character_design": "expressive_2d_stickman",
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


class EditorialCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    language: str = "es"
    premise: str = Field(min_length=8)
    narration: str = "segunda persona"
    tone: str = "realista y cinematográfico"
    duration_min: list[int] = Field(default_factory=lambda: [20, 25])

@router.get("/editorial/list")
def editorial_project_list():
    from src.documentary import cloud_sync
    if cloud_sync.configured():
        cloud_sync.pull_home_index(timeout_sec=5.0)
    projects = list_projects()
    return {"projects": [
        {"id":p.get("id"),"title":p.get("title"),"language":p.get("language"),
         "active_stage":current(p)["active_stage"],
         "completed":sum(bool(v["approved"]) for v in current(p)["stages"].values())}
        for p in projects if p.get("editorial")]}

@router.post("/editorial/create")
def editorial_project_create(body: EditorialCreate):
    brief=body.model_dump(exclude={"title"})
    _validate("brief",brief)
    if len(body.duration_min)!=2 or not 5<=body.duration_min[0]<=body.duration_min[1]<=90:
        raise HTTPException(422,"Duración inválida")
    words=round(sum(body.duration_min)/2*135)
    try:
        p=create_project(body.premise,title=body.title,language=body.language,
           target_duration_min=body.duration_min,target_words=words,content_format="documentary")
    except FileExistsError as exc:
        raise HTTPException(409,"Ya existe un proyecto con ese nombre. Usá otro título.") from exc
    ed=fresh()
    ed["stages"]["brief"]={"data":brief,"approved":True,"approved_at":datetime.now(timezone.utc).isoformat()}
    ed["active_stage"]="concepts"
    p["editorial"]=ed
    p["target_words"]=words
    save_project(p)
    # This route has no project ID in its URL; middleware cannot sync it by regex.
    from src.documentary import cloud_sync
    sync_warning = ""
    if cloud_sync.configured():
        try:
            cloud_sync.push_paths(str(p["id"]), ["project.json"])
        except Exception:
            sync_warning = "No se pudo sincronizar. Conservá este dispositivo hasta reintentar."
    return {"project_id":p["id"],"editorial":ed,"sync_warning":sync_warning}

def invalidate_production(project):
    from src.documentary.project import CHECKPOINT_KEYS, set_checkpoint
    project["story_plan_approved"] = False
    project["script_approved"] = False
    project["editorial_audit"] = {}
    for key in CHECKPOINT_KEYS:
        set_checkpoint(project, key, False)
    if project.get("voice"):
        project["voice"] = {**project["voice"], "stale": True, "stale_reason": "Editorial decisions changed"}
    project["ui_step"] = "script"


class StageUpdate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    approve: bool = False

def _load(project_id: str) -> dict[str, Any]:
    try:
        return load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Project not found") from exc

def _validate(stage: str, data: dict[str, Any], *, approve: bool = True):
    if stage == "brief":
        for key in ("language", "premise", "narration", "tone", "duration_min"):
            if not data.get(key):
                raise HTTPException(422, f"Brief requires: {key}")
        duration = data["duration_min"]
        if (not isinstance(duration, list) or len(duration) != 2
                or any(type(v) is not int for v in duration)
                or not 5 <= duration[0] <= duration[1] <= 90):
            raise HTTPException(422, "Duración inválida")
        if data["language"] not in ("es", "en"):
            raise HTTPException(422, "Language must be es or en")
    elif stage in ("concepts", "packaging"):
        if len(data.get("options") or []) != 3 or (approve and not data.get("selected")):
            raise HTTPException(422, "Three options and a selected option are required")
        ids = [str(option.get("id", "")) for option in data["options"] if isinstance(option, dict)]
        if len(ids) != 3 or len(set(ids)) != 3 or not all(ids):
            raise HTTPException(422, "Las tres opciones requieren identificadores distintos")
        if data.get("selected") and str(data["selected"]) not in ids:
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
    _validate(stage, body.data, approve=body.approve)
    if stage == "packaging":
        chosen_story = ed["stages"]["concepts"]["data"]
        concept_id = str(chosen_story.get("selected") or "")
        if not concept_id:
            raise HTTPException(409, "Primero aprobá una historia.")
        for option in body.data.get("options") or []:
            if str(option.get("concept_id") or concept_id) != concept_id:
                raise HTTPException(422, "El packaging debe pertenecer a la historia aprobada.")
            thumbnail = str(option.get("thumbnail") or "")
            if thumbnail.startswith(("http://", "https://")) or "example.com" in thumbnail:
                raise HTTPException(422, "Describí la miniatura visualmente; no uses enlaces.")
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
        invalidate_production(p)
    if stage == "brief":
        p["language"] = body.data["language"]
        p["target_duration_min"] = list(body.data["duration_min"])
        p["target_words"] = round(sum(p["target_duration_min"]) / 2 * 135)
        p["topic"] = body.data["premise"]
    if body.approve and stage in ("concepts", "packaging"):
        chosen = next(o for o in body.data["options"] if str(o["id"]) == str(body.data["selected"]))
        p["title"] = chosen.get("title") or p["title"]
        if stage == "concepts":
            p["topic"] = chosen.get("premise") or p["topic"]
    if body.approve and index < len(STAGE_IDS)-1:
        ed["active_stage"] = STAGE_IDS[index+1]
    else:
        ed["active_stage"] = stage
    ed["history"].append({"stage": stage, "action": "approved" if body.approve else "saved",
                          "at": datetime.now(timezone.utc).isoformat()})
    p["editorial"] = ed
    if all(ed["stages"][key]["approved"] for key in STAGE_IDS):
        p["ui_step"] = "script"
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
    invalidate_production(p)
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
    selected_concept = {}
    if stage != "concepts":
        prior = context.get("concepts") or {}
        selected_concept = next((x for x in prior.get("options", [])
            if isinstance(x, dict) and str(x.get("id")) == str(prior.get("selected"))), {})
        if not selected_concept:
            raise ValueError("No hay historia elegida. Volvé a la etapa de conceptos.")
    selected_packaging = {}
    if STAGE_IDS.index(stage) > STAGE_IDS.index("packaging"):
        pack = context.get("packaging") or {}
        selected_packaging = next((x for x in pack.get("options", [])
            if isinstance(x, dict) and str(x.get("id")) == str(pack.get("selected"))), {})
    requirement = {
        "concepts": (
            "Create THREE different high-concept POV simulation stories rooted in the selected genre. "
            "The viewer is making a startling choice: buying a costly asset or distressed large "
            "company for almost nothing, accepting a dangerous liability, taking over a business "
            "with a deadline, or turning around an expensive failure. Give concrete credible "
            "prices, debt, pressure, choices, consequences and earned outcomes. "
            "Generate striking YouTube-ready titles with specific stakes. No bland abstract "
            "names, inherited cafes, dead grandparents, family legacy, secret recipes, "
            "sentimental community rescue or repeated narrative templates. "
            "Each story must be structurally and commercially distinct, immersive and "
            "sufficient for 20-35 minutes. Include title,premise,hook,thumbnail,"
            "why_it_works,retention,risks."
        ),
        "packaging": (
            "PACKAGING ONLY. The previously selected story is LOCKED. DO NOT create a new "
            "business, protagonist, origin, crisis, purchase price, setting or premise. "
            "Produce THREE strong YouTube TITLES for the very same selected story, plus "
            "THREE visually describable thumbnail concepts (descriptions, NEVER URLs), "
            "THREE first-30-second narration hooks in the approved POV, specific retention "
            "arguments and editorial risks. Angle A emphasizes the impossible price, "
            "B emphasizes the deadline/financial risk, C emphasizes the discovery. "
            "Be cinematic, specific, audience-driven and true to the exact selected pitch. "
            "Return id,title,thumbnail,hook,retention,risks per option."
        ),
        "structure": "Create 7-9 acts, each with title,start_min,end_min,events,viewer_reward. Honour requested duration and chosen hook, avoid filler.",
        "bible": "Make a coherent original story bible: setting,characters array (name,role,arc,visual),timeline,economics (numbers and cash sources logically reconciled),ending,continuity_risks. Distinguish narrative fiction from sourced facts.",
        "visual": "Produce style modern_2d_animation, characters array with invariant expressive 2D stickman features, locations array with architecture, props, time periods and continuity_rules array. STRICTLY no photorealistic human characters. Visual environments are 2D illustrated.",
        "production": "Produce script_plan with intended pacing, scenes and narration strategy; continuity_checks array and quality_gate describing meaningful editorial tests and visual asset requirements.",
    }[stage]
    prompt = ("You are FrameFactory senior story editor, audience strategist, continuity supervisor and critical reviewer. "
              "Write commercially compelling adult longform narrative, not fake documentary. Never promise viral outcome. "
              "Avoid formulaic manufactured cliffhangers, repetitive motivation, copied plots, magic money, invented verified facts. "
              "All data must be concrete, coherent and distinctive. Output one JSON object only. "
              "Respond in "+("native Spanish" if locale=="es" else "native English")+". "
              +requirement)
    # Explicit JSON contract, plus a single repair attempt when the model uses
    # "ideas"/"proposals" instead of "options" or returns too few entries.
    if stage in ("concepts", "packaging"):
        schema = {"options": [
            {"id": "A", "title": "", "premise": "", "hook": "", "thumbnail": "",
             "why_it_works": "", "retention": "", "risks": ""},
            {"id": "B", "title": "", "premise": "", "hook": "", "thumbnail": "",
             "why_it_works": "", "retention": "", "risks": ""},
            {"id": "C", "title": "", "premise": "", "hook": "", "thumbnail": "",
             "why_it_works": "", "retention": "", "risks": ""}
        ], "selected": ""}
        prompt += (" REQUIRED TOP-LEVEL JSON SHAPE: " + json.dumps(schema) +
                   ". Exactly three fully developed options. Do not return ideas, stories, "
                   "proposals, concepts, or variants as the root property.")
    client = OpenAI(api_key=require_openai_api_key("Generación editorial"))
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps({
            "previous_approved_stages": context,
            "guidance": guidance,
            "project_topic": p.get("topic"),
            "LOCKED_STORY": selected_concept,
            "LOCKED_PACKAGING": selected_packaging
        }, ensure_ascii=False)}
    ]
    data = {}
    for attempt in range(2):
        result = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7 if attempt == 0 else 0.3,
            response_format={"type": "json_object"},
            messages=messages)
        data = json.loads(result.choices[0].message.content or "{}")
        if not isinstance(data, dict):
            data = {}
        if stage not in ("concepts", "packaging"):
            break
        raw = next((data.get(key) for key in
                   ("options", "ideas", "proposals", "stories", "concepts", "variants")
                   if isinstance(data.get(key), list)), [])
        if len(raw) >= 3 and all(isinstance(x, dict) for x in raw[:3]):
            data["options"] = raw[:3]
            break
        messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
        messages.append({"role": "user", "content":
                         "Repair your output: provide exactly three distinct entries under "
                         "the top-level options array, each with id, title, premise, hook, "
                         "thumbnail, why_it_works, retention and risks. Return JSON only."})
    if stage in ("concepts", "packaging"):
        options = data.get("options")
        if not isinstance(options, list) or len(options) < 3:
            raise ValueError("La IA no devolvió tres historias después de dos intentos. "
                             "No se perdió tu proyecto; podés reintentar.")
        for i, option in enumerate(options):
            option["id"] = chr(65 + i)
            option.setdefault("title", str(option.get("title_concept") or
                          option.get("name") or option.get("premise") or
                          f"Propuesta {chr(65 + i)}"))
            for field in ("premise", "hook", "thumbnail", "why_it_works", "retention", "risks"):
                option.setdefault(field, "")
        data["selected"] = ""
        if stage == "packaging":
            for option in options:
                thumbnail = str(option.get("thumbnail") or "")
                if thumbnail.startswith(("https://", "http://")) or "example.com" in thumbnail:
                    raise ValueError("Miniatura incorrecta: se requiere una descripción, no un enlace.")
                if len(str(option.get("hook") or "")) < 60:
                    raise ValueError("El hook necesita una apertura narrada, no una frase genérica.")
                option["concept_id"] = str(selected_concept.get("id") or "")
    else:
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
    invalidate_production(p)
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
        audit["verdict"] = str(audit.get("verdict") or "revise").strip().lower()
        p["editorial_audit"]=audit
        save_project(p)
        return {"audit":audit}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502,"Audit failed: "+str(exc)[:180]) from exc
