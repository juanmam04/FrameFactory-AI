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
    creative_rules: list[str] = Field(default_factory=list)

@router.get("/editorial/list")
def editorial_project_list():
    from src.documentary import cloud_sync
    if cloud_sync.configured():
        cloud_sync.pull_home_index(timeout_sec=5.0)
    projects = list_projects()
    return {"projects": [
        {"id":p.get("id"),"title":p.get("title"),"language":p.get("language"),
         "topic":p.get("topic"),"target_duration_min":p.get("target_duration_min"),
         "target_words":p.get("target_words"),"editorial":current(p),
         "active_stage":current(p)["active_stage"],
         "completed":sum(bool(v["approved"]) for v in current(p)["stages"].values())}
        for p in projects if p.get("editorial")]}

@router.post("/editorial/create")
def editorial_project_create(body: EditorialCreate):
    # Also recover reusable rules from previously saved/synced productions.
    # This avoids making permanent feedback depend solely on one browser.
    remembered_rules = []
    try:
        from src.documentary import cloud_sync
        if cloud_sync.configured():
            cloud_sync.pull_home_index(timeout_sec=5.0)
        for existing in list_projects():
            if existing.get("editorial"):
                remembered_rules.extend(existing.get("creative_rules") or [])
    except Exception:
        pass
    shared_rules = list(dict.fromkeys(
        str(rule).strip()[:700] for rule in [*remembered_rules, *body.creative_rules]
        if str(rule).strip()))[-35:]
    brief=body.model_dump(exclude={"title", "creative_rules"})
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
    p["creative_rules"]=shared_rules
    p["target_words"]=words
    save_project(p)
    # This route has no project ID in its URL; middleware cannot sync it by regex.
    from src.documentary import cloud_sync
    sync_warning = ""
    if cloud_sync.url_configured() and not cloud_sync.configured():
        sync_warning = "La sincronización no está disponible. Guardamos un respaldo en este navegador."
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
    project_snapshot: dict[str, Any] | None = None

def _load(project_id: str, recovery_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return load_project(project_id)
    except FileNotFoundError as exc:
        if not recovery_snapshot:
            raise HTTPException(404, "Project not found") from exc
        # A serverless invocation may be on an entirely different ephemeral filesystem.
        # Rehydrate during THIS request so a second request isn't needed.
        snapshot = deepcopy(recovery_snapshot)
        if (snapshot.get("id") != project_id
                or not isinstance(snapshot.get("editorial"), dict)
                or not isinstance(snapshot["editorial"].get("stages"), dict)
                or not isinstance(snapshot.get("title"), str)):
            raise HTTPException(422, "El respaldo local no coincide con el proyecto") from exc
        if not snapshot.get("topic"):
            snapshot["topic"] = (snapshot["editorial"]["stages"].get("brief") or {}).get("data", {}).get("premise") or snapshot["title"]
        snapshot.setdefault("content_format", "documentary")
        save_project(snapshot)
        return load_project(project_id)

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

class EditorialLoadRequest(BaseModel):
    project_snapshot: dict[str, Any] | None = None

@router.post("/{project_id}/editorial/load")
def restore_and_get_editorial(project_id: str, body: EditorialLoadRequest):
    p = _load(project_id, body.project_snapshot)
    return {"project_id": project_id, "editorial": current(p), "stage_labels": dict(STAGES),
            "default_visual": DEFAULT_VISUAL}

@router.get("/{project_id}/editorial")
def get_editorial(project_id: str):
    p = _load(project_id)
    return {"project_id": project_id, "editorial": current(p), "stage_labels": dict(STAGES),
            "default_visual": DEFAULT_VISUAL}

@router.put("/{project_id}/editorial/{stage}")
def update_editorial(project_id: str, stage: str, body: StageUpdate):
    if stage not in STAGE_IDS:
        raise HTTPException(404, "Unknown editorial stage")
    p = _load(project_id, body.project_snapshot)
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
    if stage == "packaging" and body.approve:
        selected_option = next((x for x in body.data.get("options", [])
            if str(x.get("id")) == str(body.data.get("selected"))), {})
        title = str(selected_option.get("title") or "").strip()
        if title:
            if not title.lower().startswith("pov:"):
                title = "POV: " + title
            p["title"] = title
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
    project_snapshot: dict[str, Any] | None = None

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
            "Create exactly THREE hugely entertaining original cinematic POV fictional simulations. "
            "Entertainment, curiosity, audacious situations, escalating setbacks and satisfying dramatic "
            "payoffs matter MORE than real-world financial, legal or operational plausibility. "
            "For the RESCUE A BANKRUPT BUSINESS category specifically, make each initial acquisition "
            "a SYMBOLIC ONE DOLLAR (US$1) takeover of a major troubled business, never an ordinary "
            "multimillion-dollar purchase. Example of the energy, NOT a script to copy: "
            "'POV: Te dan las llaves de 20 restaurantes por US$1… y solo tenés 30 días para salvarlos'. "
            "The protagonist should face vivid escalating operational chaos, astonishing discoveries, "
            "bold smart decisions, mistakes, losses, reversals and eventual consequences. "
            "Examples: banks arrive, staff walkouts, suppliers cut off deliveries, equipment fails, "
            "major customers cancel. Do not repeat the same industry or problems in all three. "
            "Never make the story a dry MBA case, dry financial simulation, standard asset valuation, "
            "or realistic compliance exercise. No inheritance, grandparents, secret family recipe, "
            "motivational speeches or boring ordinary risks. "
            "Allow exaggerated numbers and heightened fiction. Preserve INTERNAL narrative continuity; "
            "do not enforce real-world deal feasibility or real-world financial logic. "
            "Titles MUST start 'POV:' and foreground the US$1 handover and a startling challenge. "
            "Provide id,title,premise,hook,thumbnail,why_it_works,retention,risks."
        ),
        "packaging": (
            "TITLE AND THUMBNAIL TEST FOR EXACTLY ONE ALREADY APPROVED STORY. "
            "NEVER suggest other video ideas, new plots, new acquisitions, or change its protagonist, "
            "industry, purchase price, problems, deadline or ending. Make three DIFFERENT alternative "
            "YouTube TITLES for the SAME locked story, not three rewordings of its original concept title. "
            "DO NOT REPEAT the exact prior concept title in any option. Each title MUST start POV:. "
            "Title A sells the shocking US$1 handover or impossible bargain; "
            "title B sells the immediate 30-day countdown and danger of losing everything; "
            "title C sells the scale and unexpected nightmare of running the acquired business. "
            "Titles MUST emphasize noticeably different hooks and word choices while all remaining "
            "factually consistent with this same fictional story. "
            "Pair each title with a distinct illustrated thumbnail DESCRIPTION, no URL, "
            "and an original gripping 30-second POV narration hook plus retention argument. "
            "The user is choosing the TITLE, not choosing a different STORY. "
            "Return id,title,thumbnail,hook,retention,risks for each option."
        ),
        "structure": "Return one JSON object containing acts: ARRAY of 7-9 objects, each with title,start_min,end_min,events,viewer_reward. For every major business rescue act specify a concrete obstacle, protagonist decision, alternatives considered, implementation steps, costs/cash flow, measurable outcome and consequences. Prioritize surprising entertainment and smart choices; do not demand real-world feasibility. Avoid vague summaries. Preserve LOCKED_STORY and LOCKED_PACKAGING. Honour requested duration and chosen hook. Never return chapters, outline or structure as top-level key.",
        "bible": "Make a coherent original story bible: setting,characters array (name,role,arc,visual),timeline,economics (numbers and cash sources logically reconciled),ending,continuity_risks, plus decision_ledger ARRAY with problem, alternatives, chosen_strategy, implementation, time_cost, cash_effect, result and side_effects for each turning-point decision. Fiction can be exaggerated and surprising; keep character and event continuity without forcing real-world financing feasibility. Distinguish narrative fiction from sourced facts.",
        "visual": "WORLD LOCK: stickman universe. Produce style modern_2d_animation. "
        "characters array MUST include YOU as the locked protagonist stickman "
        "(round white head, black-dot eyes, thin stick limbs, bold outlines, consistent hair) "
        "plus supporting stickman cast with invariant designs. locations array with architecture, "
        "props, time periods and continuity_rules array. STRICTLY no photorealistic human characters. "
        "Every person is a stickman. Visual environments are detailed 2D illustrated. "
        "Keep each character head, hair, outfit, proportions, silhouette and palette identical "
        "between scenes. Give every recurring location a locked layout, colors and props. "
        "Use cinematic lighting, atmosphere, foreground/midground/background depth, purposeful "
        "angles and adult expressive acting; avoid generic childish stick figures. "
        "All images must look like frames of the same premium modern 2D animated film.",
        "production": "Produce script_plan with intended pacing, scenes and narration strategy; continuity_checks array and quality_gate describing meaningful editorial tests and visual asset requirements.",
    }[stage]
    # Approved feedback from the user's agent is part of every new editorial stage.
    creative_rules = p.get("creative_rules") or []
    if stage in ("concepts", "packaging", "structure", "bible", "visual", "production"):
        requirement += (" Apply these USER-APPROVED EDITORIAL RULES to this stage where relevant: "
                        +json.dumps(creative_rules,ensure_ascii=False))
    prompt = ("You are FrameFactory senior story editor, audience strategist, continuity supervisor and critical reviewer. "
              "Write astonishing, highly entertaining adult fictional POV narratives, NOT a documentary or a business textbook. Never promise viral outcome. "
              "Use powerful consequential reversals, risky clever tactics and escalating entertaining setbacks. Avoid boring ordinary stakes, repeated clichés and claiming fiction is true. "
              "All data must be concrete, coherent and distinctive. Output one JSON object only. "
              "Respond in "+("native Spanish" if locale=="es" else "native English")+". "
              +requirement)
    # Explicit JSON contract, plus a single repair attempt when the model uses
    # "ideas"/"proposals" instead of "options" or returns too few entries.
    if stage == "bible":
        prompt += (' REQUIRED top-level JSON: {"setting":{"location":"", "time_period":"", "atmosphere":""},'
                   '"characters":[{"name":"","role":"","arc":"","visual":""}],'
                   '"timeline":[{"day":"","event":""}],"economics":{"resources":"","obstacles":""},'
                   '"ending":{"resolution":""},"continuity_risks":[],'
                   '"decision_ledger":[{"problem":"","alternatives":[],"chosen_strategy":"",'
                   '"implementation":"","time_cost":"","cash_effect":"","result":"","side_effects":""}]}. '
                   'Do not return only a story or nested bible wrapper.')
    elif stage == "visual":
        prompt += (' REQUIRED top-level JSON: {"style":"modern_2d_animation",'
                   '"characters":[{"name":"","design":"","outfit":"","continuity":""}],'
                   '"locations":[{"name":"","visual_description":"","continuity":""}],'
                   '"continuity_rules":[]}. Do not nest in visual_bible.')
    elif stage == "production":
        prompt += (' REQUIRED top-level JSON: {"script_plan":{"opening":"","acts":[],"pacing":"",'
                   '"narration":"","target_duration":""},"continuity_checks":[{"check":"","how":""}],'
                   '"quality_gate":{"must_pass":[]}}. Do not nest in plan.')
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
    if stage == "packaging":
        prompt += (" PREVIOUS STORY CONCEPT TITLE (FORBIDDEN TO REUSE): " +
                   json.dumps(selected_concept.get("title") or "", ensure_ascii=False) +
                   ". Output three original alternatives with mutually distinct angles.")
    client = OpenAI(api_key=require_openai_api_key("Generación editorial"))
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps({
            "previous_approved_stages": context,
            "guidance": guidance,
            "project_topic": p.get("topic"),
            "PERMANENT_EDITORIAL_RULES": p.get("creative_rules") or [],
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
        for option in options:
            title = str(option.get("title") or "").strip()
            if not title.lower().startswith("pov:"):
                option["title"] = "POV: " + title
        data["selected"] = ""
        if stage == "packaging":
            import re
            def title_key(title):
                return re.sub(r"[^a-z0-9]+", "", str(title).casefold()
                              .replace("á", "a").replace("é", "e").replace("í", "i")
                              .replace("ó", "o").replace("ú", "u"))
            concept_key = title_key(selected_concept.get("title", ""))
            keys = [title_key(option.get("title", "")) for option in options]
            if len(set(keys)) != 3 or concept_key in keys:
                retry_messages = messages + [
                    {"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                    {"role": "user", "content": (
                        "Your three titles are duplicates of each other or of the already "
                        "approved idea title. Rewrite all three titles (and matching hooks) "
                        "for this SAME story with clearly different angles: A purchase price, "
                        "B countdown, C operational nightmare. Do not alter story facts. "
                        "None may equal the original concept title. Return complete JSON "
                        "with options array and all original fields."
                    )}]
                revision = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    temperature=0.8,
                    response_format={"type": "json_object"},
                    messages=retry_messages)
                revised = json.loads(revision.choices[0].message.content or "{}")
                candidates = revised.get("options") if isinstance(revised, dict) else None
                if isinstance(candidates, list) and len(candidates) == 3 and all(
                    isinstance(item, dict) for item in candidates
                ):
                    options = candidates
                    for i, option in enumerate(options):
                        option["id"] = chr(65 + i)
                        title = str(option.get("title") or "").strip()
                        if not title.lower().startswith("pov:"):
                            option["title"] = "POV: " + title
                    data["options"] = options
                    keys = [title_key(option.get("title", "")) for option in options]
                if len(set(keys)) != 3 or concept_key in keys:
                    raise ValueError("La IA repitió el título original; volvé a generar los títulos.")

            for option in options:
                thumbnail = str(option.get("thumbnail") or "")
                if thumbnail.startswith(("https://", "http://")) or "example.com" in thumbnail:
                    raise ValueError("Miniatura incorrecta: se requiere una descripción, no un enlace.")
                if len(str(option.get("hook") or "")) < 60:
                    raise ValueError("El hook necesita una apertura narrada, no una frase genérica.")
                option["concept_id"] = str(selected_concept.get("id") or "")
    elif stage == "structure":
        raw = next((data.get(key) for key in ("acts", "chapters", "segments", "outline", "structure", "timeline")
                    if isinstance(data.get(key), list)), [])
        if not raw and isinstance(data.get("structure"), dict):
            raw = data["structure"].get("acts") or data["structure"].get("chapters") or []
        if not isinstance(raw, list) or len(raw) < 3:
            # Ask the model to repair invalid chapter structure rather than strand the user.
            repair = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.2,
                response_format={"type": "json_object"},
                messages=messages + [
                    {"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                    {"role": "user", "content": "Restructure this exact approved story as a JSON object with an acts array of 7 to 9 concrete act objects, each with title,start_min,end_min,events,viewer_reward. JSON only."}
                ])
            fixed = json.loads(repair.choices[0].message.content or "{}")
            raw = next((fixed.get(key) for key in ("acts", "chapters", "segments")
                        if isinstance(fixed.get(key), list)), [])
        data = {"acts": [dict(act) if isinstance(act, dict) else {"title": str(act), "events": str(act)} for act in raw]}
        _validate(stage,data)
    elif stage in ("bible", "visual", "production"):
        from fastapi import HTTPException as ValidationError
        aliases = {
            "bible": {"narrative_bible": "setting", "world": "setting", "cast": "characters",
                      "chronology": "timeline", "finances": "economics", "resolution": "ending"},
            "visual": {"character_designs": "characters", "settings": "locations",
                       "visual_style": "style"},
            "production": {"plan": "script_plan", "checks": "continuity_checks"},
        }[stage]
        wrappers = ("bible", "narrative_bible", "visual_bible", "visual_plan",
                    "production_plan", "plan")
        def normalize(raw):
            normalized = dict(raw)
            for wrapper in wrappers:
                if isinstance(normalized.get(wrapper), dict):
                    inner = normalized.pop(wrapper)
                    normalized = {**inner, **normalized}
            for alternate, canonical in aliases.items():
                if not normalized.get(canonical) and normalized.get(alternate):
                    normalized[canonical] = normalized[alternate]
            return normalized
        data = normalize(data)
        for attempt in range(2):
            try:
                _validate(stage, data)
                break
            except ValidationError:
                if attempt:
                    raise
                repair = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
                    temperature=0.2, response_format={"type":"json_object"},
                    messages=messages+[
                        {"role":"assistant","content":json.dumps(data,ensure_ascii=False)},
                        {"role":"user","content":"Repair your output to exactly match the required top-level JSON shape for "
                         +stage+". Preserve the approved story and all original useful details. JSON only."}])
                fixed = json.loads(repair.choices[0].message.content or "{}")
                data = normalize(fixed if isinstance(fixed, dict) else {})
    else:
        _validate(stage,data)
    return data

@router.post("/{project_id}/editorial/{stage}/generate")
def generate_editorial(project_id: str,stage: str,body: GenerateRequest):
    if stage not in STAGE_IDS or stage=="brief":
        raise HTTPException(404,"Cannot generate this stage")
    p=_load(project_id,body.project_snapshot)
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
          messages=[{"role":"system","content":"You are a demanding story editor. Analyze factual consistency within fiction, financial logic, opening promise, attention risks and redundancy. For EVERY key turnaround strategy check whether the script demonstrates concrete problem/evidence, alternatives and tradeoffs, chosen action, execution mechanics, real cost, quantifiable result and consequences. If major outcomes are explained only as worked hard/improved management/secured funding/negotiated debt, set verdict to revise and identify specific missing causal scenes. Check internal continuity, established debts and deadlines in the fiction; do not downgrade exciting stories merely for being unrealistic. Reject a purchased-business script that starts inside the property without showing how the protagonist received the offer, negotiated or accepted the deal, took the keys and discovered the catch. Detect repeated versions of the same event, recycled scenes, sudden influencer rescues, characters reversing their development and unresolved purchase or closure stakes. Apply user-approved creative_rules as mandatory audit criteria. Return JSON with verdict (pass or revise), issues list, strengths list, recommended_fixes list, decision_audit list. Do not estimate virality probabilities."},
                    {"role":"user","content":json.dumps({"brief":ed["stages"]["brief"]["data"],"bible":ed["stages"]["bible"]["data"],"packaging":ed["stages"]["packaging"]["data"],"script":str(p["script"])[:45000],"creative_rules":p.get("creative_rules") or []},ensure_ascii=False)}])
        audit=json.loads(response.choices[0].message.content or "{}")
        audit["verdict"] = str(audit.get("verdict") or "revise").strip().lower()
        p["editorial_audit"]=audit
        save_project(p)
        return {"audit":audit}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502,"Audit failed: "+str(exc)[:180]) from exc
