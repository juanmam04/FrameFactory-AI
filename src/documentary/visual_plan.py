"""Documentary Visual Plan — Story/Script → visuals → Flow batches of 10.

FrameFactory prepares everything. User copies batch → Google Flow → import.
NO Flow API / browser automation / image generation.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.documentary.editorial import FLOW_DIRECTOR_RULES, VISUAL_DIRECTION
from src.documentary.project import append_log, project_dir, save_project
from src.documentary.story_plan import get_story_plan, selected_beats

VISUAL_PLAN_VERSION = 1

VISUAL_TYPES = (
    "FLOW_REENACTMENT",
    "ARCHIVAL_PHOTO",
    "ARCHIVAL_VIDEO",
    "DOCUMENT",
    "HEADLINE",
    "LOGO",
    "PRODUCT",
    "SCREENSHOT",
    "MAP",
    "CHART",
    "OTHER",
)

CAMERA_VARIETY = (
    "establishing_wide",
    "medium_action",
    "close_up",
    "environmental_detail",
    "over_the_shoulder",
    "two_shot",
    "hands_on_object",
    "object_detail",
    "intimate_moment",
    "doorway_threshold",
)

KEN_BURNS = ("slow_push", "slow_pull", "pan_left", "pan_right", "static")

_NON_FLOW_CUES: list[tuple[str, tuple[str, ...]]] = [
    ("DOCUMENT", ("s-1", "s1", "filing", "prospectus", "sec filing", "contract", "lease agreement")),
    ("HEADLINE", ("headline", "newspaper", "wall street journal", "bloomberg", "new york times", "press report")),
    ("SCREENSHOT", ("screenshot", "app screen", "website", "dashboard", "interface")),
    ("LOGO", (" company logo", "logo of", "brand mark")),
    ("CHART", ("chart", "graph", "valuation chart", "stock chart")),
    ("MAP", ("map of", "across cities", "global expansion map")),
    ("ARCHIVAL_PHOTO", ("photograph of", "archive photo", "historical photo")),
    ("PRODUCT", ("product shot", "the product itself")),
]


def build_visual_plan(
    project: dict[str, Any],
    *,
    use_llm: bool = True,
    target_visuals: int = 80,
    batch_size: int | None = None,
) -> dict[str, Any]:
    """Build Visual Plan + Visual Bible + Flow batches from approved script + Story Plan."""
    script = str(project.get("script") or "").strip()
    if not script:
        raise ValueError("Generate a script before creating a Visual Plan.")
    if not project.get("script_approved"):
        raise ValueError("Approve the script first — then build the Visual Plan.")

    from src.documentary.visual_director import analyze_visuals

    batch_size = int(batch_size or project.get("batch_size") or 10)
    batch_size = 10 if batch_size not in (5, 10) else batch_size
    project["batch_size"] = batch_size

    analyze_visuals(project, use_llm=use_llm, max_shots=int(max(70, min(100, target_visuals))))
    from src.documentary.project import load_project
    from src.documentary.visual_director import load_analysis

    project = load_project(str(project["id"]))
    analysis = load_analysis(str(project["id"]))
    raw_shots = analysis.get("shots") or []
    bible_raw = analysis.get("story_bible") or {}

    story = get_story_plan(project)
    beats = selected_beats(story) or (story.get("beats") or [])
    visuals = [_enrich_visual(i, shot, beats) for i, shot in enumerate(raw_shots, start=1)]
    bible = _upgrade_bible(bible_raw, visuals, story)
    _purge_stock_locations(bible)
    _rewrite_stills(visuals, bible, str(project.get("topic") or ""), use_llm=use_llm)
    visuals = _assign_camera_variety(visuals)
    visuals = _assign_durations(visuals)

    masters = select_master_references(bible, visuals)
    # Attach flow prompts with master hints
    for v in visuals:
        if v.get("visual_type") == "FLOW_REENACTMENT":
            v["flow_prompt"] = format_single_prompt(v, bible, masters)

    flow_batches = group_flow_batches(visuals, batch_size=batch_size)
    for b in flow_batches:
        b["prompt"] = format_batch_prompt(b, visuals, bible, masters)
        b["references_needed"] = batch_references(b, visuals, masters)

    coverage = coverage_check(visuals, beats)
    stats = summarize_visuals(visuals, flow_batches, masters)

    plan = {
        "version": VISUAL_PLAN_VERSION,
        "target_visuals": target_visuals,
        "batch_size": batch_size,
        "visuals": visuals,
        "visual_bible": bible,
        "master_references": masters,
        "flow_batches": flow_batches,
        "coverage": coverage,
        "stats": stats,
    }

    root = project_dir(str(project["id"]))
    fp = root / "flow-pack"
    fp.mkdir(parents=True, exist_ok=True)
    (fp / "visual-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (fp / "visual-plan.md").write_text(plan_to_markdown(plan), encoding="utf-8")
    analysis["shots"] = visuals
    analysis["story_bible"] = bible
    analysis["visual_plan"] = {"stats": stats, "batch_count": len(flow_batches)}
    (fp / "visual_analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    project["visual_plan"] = {
        "stats": stats,
        "batch_count": len(flow_batches),
        "path": "flow-pack/visual-plan.json",
    }
    save_project(project)
    append_log(
        str(project["id"]),
        f"visual_plan visuals={len(visuals)} flow={stats['flow']} batches={len(flow_batches)}",
    )
    return plan


def load_visual_plan(project_id: str) -> dict[str, Any]:
    path = project_dir(project_id) / "flow-pack" / "visual-plan.json"
    if not path.exists():
        from src.documentary.project import _pull_if_missing

        _pull_if_missing(project_id)
        path = project_dir(project_id) / "flow-pack" / "visual-plan.json"
    if not path.exists():
        raise FileNotFoundError("visual-plan.json missing — generate Visual Plan first")
    plan = refresh_flow_prompts(json.loads(path.read_text(encoding="utf-8")))
    from src.documentary.import_images import attach_master_status

    attach_master_status(project_id, plan.get("master_references") or [])
    return plan


def refresh_flow_prompts(plan: dict[str, Any]) -> dict[str, Any]:
    """Rebuild Flow copy-paste prompts so old episodes pick up director rules."""
    visuals = plan.get("visuals") or []
    bible = plan.get("visual_bible") or {}
    _purge_stock_locations(bible)
    for v in visuals:
        _concretize_visual(v, bible)
        names = _cast_names(v, bible)
        if names:
            v["characters"] = names
            refs = [str(x) for x in (v.get("reference_ids") or v.get("references") or [])]
            refs = [r for r in refs if not str(r).upper().startswith("LOC_")]
            for ent in bible.get("characters") or []:
                if str(ent.get("name") or "") in names:
                    eid = str(ent.get("id") or "")
                    if eid and eid not in refs:
                        refs.append(eid)
            v["reference_ids"] = refs
            v["references"] = refs
    masters = select_master_references(bible, visuals)
    plan["master_references"] = masters
    plan["visual_bible"] = bible
    for v in visuals:
        if str(v.get("visual_type") or "") == "FLOW_REENACTMENT":
            v["flow_prompt"] = format_single_prompt(v, bible, masters)
    for b in plan.get("flow_batches") or []:
        b["prompt"] = format_batch_prompt(b, visuals, bible, masters)
        b["references_needed"] = batch_references(b, visuals, masters)
    return plan


def group_flow_batches(visuals: list[dict[str, Any]], *, batch_size: int = 10) -> list[dict[str, Any]]:
    size = max(1, int(batch_size))
    flow = [v for v in visuals if str(v.get("visual_type") or "") == "FLOW_REENACTMENT"]
    batches: list[dict[str, Any]] = []
    for i in range(0, len(flow), size):
        chunk = flow[i : i + size]
        nums = [int(v["number"]) for v in chunk]
        batches.append(
            {
                "id": f"BATCH_{len(batches) + 1:02d}",
                "visual_numbers": nums,
                "label": _batch_label(nums),
                "count": len(chunk),
                "status": "ready_to_generate",
                "imported": 0,
            }
        )
    return batches


def _style_text(bible: dict[str, Any]) -> str:
    raw = (bible or {}).get("global_style") or (bible or {}).get("visual_style") or ""
    if isinstance(raw, dict):
        bits = [str(raw.get("look") or raw.get("visual_style") or ""), str(raw.get("tone") or "")]
        raw = " ".join(b for b in bits if b and not str(b).startswith("{"))
    text = str(raw or "").strip()
    if not text or text.startswith("{") or text.startswith("{'"):
        return VISUAL_DIRECTION
    return text


_STOCKY_DESC = re.compile(
    r"grupo de|a group of|busy office|open.?plan|cowork|people working|"
    r"oficina llena|llena de gente|conference room|filled with desks|"
    r"acción física visible|lugar principal de la historia|inversores aplaudi|"
    r"empleados observa",
    re.I,
)
_GENERIC_LOC = re.compile(
    r"^(wework\s*)?(office|oficina|cowork(ing)?(\s+space)?|open.?plan|headquarters|hq|"
    r"conference room|sala de (conferencias|reuniones)( moderna| de wework)?|"
    r"ubicación específica.*)s?\.?$",
    re.I,
)
_FILLER_ACTION = re.compile(r"\.?\s*Acci[oó]n f[ií]sica visible:.*$", re.I)
_VO_LEAD = re.compile(
    r"^(photograph this exact story beat:\s*)?(this |the |their |how |why |by \d{4}|to understand)",
    re.I,
)
_PHYSICAL = re.compile(
    r"\b(holds|holding|stands|standing|sits|sitting|walks|walking|stares|staring|"
    r"rips|signs|dances|enters|hangs|places|reads|tears|runs|collapses|pours|"
    r"watches|watching|drills|alone|sidewalk|term sheet|for sale|cartel|sosteniendo|"
    r"frente a|phone in hand|empty floor)\b",
    re.I,
)
_CAM_FIX = {
    "crowd": "two_shot",
    "building_exterior": "establishing_wide",
    "building exterior": "establishing_wide",
    "large_scale": "medium_action",
    "large scale": "medium_action",
}


def _cast_names(visual: dict[str, Any], bible: dict[str, Any] | None) -> list[str]:
    existing = [str(x).strip() for x in (visual.get("characters") or []) if str(x).strip()]
    if existing:
        return existing[:3]
    text = " ".join(
        str(visual.get(k) or "")
        for k in ("narration_segment", "narration", "description", "action", "location")
    ).lower()
    names: list[str] = []
    for ent in (bible or {}).get("characters") or []:
        name = str(ent.get("name") or "").strip()
        if name and name.lower() in text and name not in names:
            names.append(name)
    return names[:3]


def _is_vo(text: str) -> bool:
    t = " ".join((text or "").split())
    if not t:
        return True
    if t.endswith("?") or t.lower().startswith("photograph this"):
        return True
    if _STOCKY_DESC.search(t):
        return True
    if _VO_LEAD.match(t) and not _PHYSICAL.search(t):
        return True
    if len(t.split()) > 22 and not _PHYSICAL.search(t):
        return True
    return False


def _names_in_text(text: str, bible: dict[str, Any] | None) -> list[str]:
    low = (text or "").lower()
    out: list[str] = []
    for ent in (bible or {}).get("characters") or []:
        name = str(ent.get("name") or "").strip()
        if name and name.lower() in low and name not in out:
            out.append(name)
    return out[:3]


def _lead(bible: dict[str, Any] | None) -> str:
    for c in (bible or {}).get("characters") or []:
        name = str(c.get("name") or "").strip()
        if name:
            return name
    return "the founder"


def _still_from_vo(visual: dict[str, Any], bible: dict[str, Any] | None) -> str:
    narr = str(visual.get("narration_segment") or visual.get("narration") or "").strip()
    who = _names_in_text(narr, bible)
    who_s = ", ".join(who) if who else _lead(bible)
    low = narr.lower()
    if any(k in low for k in ("for sale", "ipo", "pulled", "offering")):
        return (
            f"{who_s} alone on a dark sidewalk as a worker drills a For Sale sign onto the company building. "
            "Empty street, night, no employees in frame."
        )
    if any(k in low for k in ("raised", "funding", "series", "million", "billion", "softbank", "investors")):
        return (
            f"{who_s} and ONE investor at a private table, a term sheet between them, wine, no applause, no boardroom crowd."
        )
    if any(k in low for k in ("launch", "founded", "started", "opened", "2010")):
        return (
            f"{who_s} on a city sidewalk with a cheap printed paper sign, early-2010s street clothes, almost nobody watching."
        )
    if any(k in low for k in ("fallout", "crisis", "collapsed", "unstoppable", "questions", "overnight", "downfall")):
        return (
            f"{who_s} alone in an emptied office floor at night, one desk lamp, phone showing the bad headline. Everyone else is gone."
        )
    if any(k in low for k in ("community", "coworking", "freelance", "gig", "flexible office", "vision")):
        return (
            f"{who_s} walking a raw unfinished floor — exposed brick, one table, paint cans — selling a vision that does not exist yet."
        )
    clause = re.split(r"[.;?]", narr)[0].strip()[:120] if narr else "this turning point"
    return (
        f"{who_s} in a specific real place, body in motion, the visible consequence of: {clause}. "
        "No crowd, no open-plan office."
    )


def _concretize_visual(visual: dict[str, Any], bible: dict[str, Any] | None) -> None:
    if str(visual.get("visual_type") or "FLOW_REENACTMENT") != "FLOW_REENACTMENT":
        return
    desc = _FILLER_ACTION.sub("", str(visual.get("description") or visual.get("action") or "")).strip(" .")
    if not desc or _is_vo(desc) or _STOCKY_DESC.search(desc):
        still = _still_from_vo(visual, bible)
        visual["description"] = still
        visual["action"] = still
        people = _names_in_text(still, bible) or _names_in_text(
            str(visual.get("narration_segment") or ""), bible
        )
        if not people:
            people = [_lead(bible)]
        visual["characters"] = people[:2]
    loc = str(visual.get("location") or "").strip()
    if loc and (_GENERIC_LOC.match(loc) or _STOCKY_DESC.search(loc)):
        visual["location"] = ""
    st = str(visual.get("shot_type") or "")
    visual["shot_type"] = _CAM_FIX.get(st, _CAM_FIX.get(st.replace("_", " "), st))


def _rewrite_stills(
    visuals: list[dict[str, Any]],
    bible: dict[str, Any],
    topic: str,
    *,
    use_llm: bool,
) -> None:
    for v in visuals:
        _concretize_visual(v, bible)
    if not use_llm:
        return
    flow = [v for v in visuals if str(v.get("visual_type") or "") == "FLOW_REENACTMENT"]
    if not flow:
        return
    import os

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return
    try:
        from openai import OpenAI
    except Exception:
        return
    client = OpenAI(api_key=key)
    cast = [str(c.get("name") or "").strip() for c in (bible.get("characters") or []) if c.get("name")]
    system = (
        "You are a documentary stills photographer. Convert each narration line into ONE photograph.\n"
        "Return ONLY a JSON list. Each item: number, action, location, characters (names from the cast only), time_of_day.\n"
        "action = one sentence, a body doing something, a specific place. NEVER copy the narration. "
        "NEVER a rhetorical question. NEVER a crowded office or coworking floor.\n"
        "If the VO is abstract, invent the honest visual consequence "
        "(empty floor after the crash, a For Sale sign at night, two cofounders on a sidewalk with a cheap sign).\n"
        "Locations MUST change across the list: street, apartment, car, jet, empty hallway, restaurant, "
        "sidewalk, bedroom at 3am, loading dock, courthouse steps — not 'office' twice in a row."
    )
    for i in range(0, len(flow), 8):
        chunk = flow[i : i + 8]
        payload = {
            "topic": topic,
            "cast": cast[:8],
            "shots": [
                {
                    "number": int(v.get("number") or 0),
                    "narration": str(v.get("narration_segment") or v.get("narration") or "")[:400],
                }
                for v in chunk
            ],
        }
        try:
            r = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                temperature=0.7,
                max_tokens=1400,
            )
            raw = (r.choices[0].message.content or "").strip()
            blob = raw[raw.find("[") : raw.rfind("]") + 1]
            rows = json.loads(blob) if blob else []
        except Exception:
            continue
        if not isinstance(rows, list):
            continue
        by_n = {int(v["number"]): v for v in chunk}
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                n = int(row.get("number") or 0)
            except (TypeError, ValueError):
                continue
            v = by_n.get(n)
            if v is None:
                continue
            action = str(row.get("action") or "").strip()
            loc = str(row.get("location") or "").strip()
            chars = [str(x).strip() for x in (row.get("characters") or []) if str(x).strip()]
            if action and not _is_vo(action):
                v["description"] = action
                v["action"] = action
            if loc and not _GENERIC_LOC.match(loc) and not _STOCKY_DESC.search(loc):
                v["location"] = loc
            if chars:
                allowed = {c.lower() for c in cast}
                v["characters"] = [c for c in chars if c.lower() in allowed][:3] or v.get("characters") or []


def _story_description(visual: dict[str, Any], bible: dict[str, Any] | None = None) -> str:
    raw = str(visual.get("description") or visual.get("action") or "").strip()
    raw = _FILLER_ACTION.sub("", raw).strip(" .")
    if raw.lower().startswith("photograph this exact"):
        raw = ""
    if raw and not _is_vo(raw) and not _STOCKY_DESC.search(raw):
        return raw
    return _still_from_vo(visual, bible)


def format_batch_prompt(
    batch: dict[str, Any],
    visuals: list[dict[str, Any]],
    bible: dict[str, Any],
    masters: list[dict[str, Any]] | None = None,
) -> str:
    by_num = {int(v["number"]): v for v in visuals}
    nums = [int(n) for n in (batch.get("visual_numbers") or [])]
    n = len(nums)
    lines = [
        f"Create {n} separate 16:9 cinematic documentary stills — a STORY SEQUENCE, not stock.",
        "Each numbered item = ONE unique story beat with a named protagonist.",
        "Do not create a collage. Do not repeat the same office/crowd.",
        "",
        "HARD RULES:",
        "- The same person must look like the same person across images (use character refs).",
        "- Change location, time of day, and camera every shot unless the story stays put.",
        "- Forbidden: crowded coworking, rows of laptops, generic glass conference rooms,",
        "  handshake, CEO portrait, anonymous extras filling the frame.",
        "",
        f"DIRECTOR: {FLOW_DIRECTOR_RULES}",
        f"STYLE: {_style_text(bible)[:320]}",
        "",
    ]
    for idx, num in enumerate(nums, start=1):
        v = by_num.get(num) or {}
        lines.append(f"{idx}. {format_scene_line(v, masters, bible)}")
        lines.append("")
    lines.extend(
        [
            "GENERAL RULES:",
            "- 16:9 photoreal documentary;",
            "- protagonist visible and doing the action;",
            "- period-accurate wardrobe, phones, cars, interiors;",
            "- each image must be recognizable as a DIFFERENT moment;",
            "- no readable text unless requested; no logos; no collage;",
            "- no stock office crowd.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def format_scene_line(
    visual: dict[str, Any],
    masters: list[dict[str, Any]] | None = None,
    bible: dict[str, Any] | None = None,
) -> str:
    num = int(visual.get("number") or 0)
    period = str(visual.get("period") or "").strip()
    loc = str(visual.get("location") or "").strip()
    if loc and (_GENERIC_LOC.match(loc) or _STOCKY_DESC.search(loc)):
        loc = ""
    desc = _story_description(visual, bible)
    cam_key = str(visual.get("shot_type") or visual.get("camera") or "medium_action")
    cam = _CAM_FIX.get(cam_key, _CAM_FIX.get(cam_key.replace("_", " "), cam_key)).replace("_", " ")
    refs = [str(rid) for rid in (visual.get("reference_ids") or visual.get("references") or [])]
    # LOC masters in this project are generic coworking interiors — they make every still look the same.
    refs = [r for r in refs if not r.upper().startswith("LOC_")]
    master_hint = ""
    if refs and masters:
        names = []
        for m in masters:
            if m.get("id") in refs:
                names.append(str(m.get("master_filename") or m.get("name") or m.get("id")))
        if names:
            master_hint = " Use " + ", ".join(names) + " as identity reference."
    elif refs:
        master_hint = " Use " + ", ".join(refs) + " as identity reference."
    when = f" {period}." if period else ""
    place = f" {loc}." if loc else ""
    people = _cast_names(visual, bible)
    who = (
        f" Protagonist in frame: {', '.join(people[:3])} — same face as their master reference."
        if people
        else " One named person from this story in frame — not a crowd of extras."
    )
    return (
        f"{num:03d}.{when}{place} {desc}{who} "
        f"{cam} candid documentary still, photoreal, period-accurate. Unique story moment, not stock."
        f"{master_hint}"
    ).strip()


def format_single_prompt(
    visual: dict[str, Any],
    bible: dict[str, Any],
    masters: list[dict[str, Any]] | None = None,
) -> str:
    return (
        "Create ONE 16:9 cinematic documentary still. One story beat. One protagonist.\n"
        "Photoreal. No collage. No crowded office stock.\n"
        f"STYLE: {_style_text(bible)[:280]}\n"
        f"DIRECTOR: {FLOW_DIRECTOR_RULES}\n\n"
        f"{format_scene_line(visual, bible=bible, masters=masters)}\n"
    )


def batch_references(
    batch: dict[str, Any],
    visuals: list[dict[str, Any]],
    masters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_num = {int(v["number"]): v for v in visuals}
    needed_ids: set[str] = set()
    for num in batch.get("visual_numbers") or []:
        v = by_num.get(int(num)) or {}
        for rid in v.get("reference_ids") or v.get("references") or []:
            needed_ids.add(str(rid))
    out = []
    for m in masters:
        if m.get("id") in needed_ids:
            out.append(
                {
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "master_filename": m.get("master_filename"),
                    "kind": m.get("kind"),
                }
            )
    return out


_STOCK_LOC = re.compile(
    r"headquarters|cowork|open.?plan|open.?concept|glass walls|bustling|"
    r"diverse professionals|filled with people|networking|locations worldwide|"
    r"communal tables|lounge areas|corporate office|open-plan|professionals working",
    re.I,
)


def _is_stock_location(ent: dict[str, Any]) -> bool:
    blob = " ".join(
        str(ent.get(k) or "")
        for k in ("name", "description", "visual_description")
    )
    return bool(_STOCK_LOC.search(blob))


def _purge_stock_locations(bible: dict[str, Any]) -> None:
    locs = [e for e in (bible.get("locations") or []) if isinstance(e, dict) and not _is_stock_location(e)]
    bible["locations"] = locs


def select_master_references(bible: dict[str, Any], visuals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flow_nums = {int(v["number"]) for v in visuals if v.get("visual_type") == "FLOW_REENACTMENT"}
    masters: list[dict[str, Any]] = []

    def _count(ent: dict) -> int:
        apps = ent.get("appears_in_shots") or []
        return len([n for n in apps if int(n) in flow_nums])

    chars = [e for e in (bible.get("characters") or []) if e.get("name")]
    for i, ent in enumerate(chars):
        c = _count(ent)
        # Always lock the first two faces — that's what Flow needs for continuity.
        if i >= 2 and c < 3 and not ent.get("reference_required"):
            continue
        masters.append(_master_entry(ent, "character", max(c, 1)))

    for ent in bible.get("locations") or []:
        if _is_stock_location(ent):
            continue
        c = _count(ent)
        if c < 4 and not ent.get("reference_required"):
            continue
        if sum(1 for m in masters if m.get("kind") == "location") >= 1:
            continue
        masters.append(_master_entry(ent, "location", c))

    for ent in bible.get("important_objects") or []:
        c = _count(ent)
        if c < 3 and not ent.get("reference_required"):
            continue
        if sum(1 for m in masters if m.get("kind") == "object") >= 1:
            continue
        masters.append(_master_entry(ent, "object", c))

    return masters[:5]


def coverage_check(visuals: list[dict[str, Any]], beats: list[dict[str, Any]]) -> dict[str, Any]:
    by_beat: dict[str, list[int]] = {}
    for v in visuals:
        bid = str(v.get("story_beat_id") or "unassigned")
        by_beat.setdefault(bid, []).append(int(v.get("number") or 0))

    missing_beats = []
    for b in beats:
        if str(b.get("priority") or "").lower() not in ("essential", "strong"):
            continue
        bid = str(b.get("id"))
        if bid and bid not in by_beat:
            missing_beats.append(bid)

    near_dup = 0
    prev = ""
    for v in visuals:
        d = str(v.get("description") or "")[:80].lower()
        if d and d == prev:
            near_dup += 1
        prev = d

    return {
        "by_beat": by_beat,
        "essential_beats_without_visual": missing_beats,
        "near_duplicate_pairs": near_dup,
        "ok": len(missing_beats) == 0 and near_dup < 5,
    }


def summarize_visuals(
    visuals: list[dict[str, Any]],
    batches: list[dict[str, Any]],
    masters: list[dict[str, Any]],
) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    for v in visuals:
        t = str(v.get("visual_type") or "OTHER")
        by_type[t] = by_type.get(t, 0) + 1
    flow = by_type.get("FLOW_REENACTMENT", 0)
    realish = sum(c for t, c in by_type.items() if t != "FLOW_REENACTMENT")
    return {
        "total": len(visuals),
        "flow": flow,
        "real_or_other": realish,
        "by_type": by_type,
        "flow_batches": len(batches),
        "master_references": len(masters),
    }


def sync_ready_from_disk(project_id: str, *, check_remote: bool = True) -> dict[str, Any]:
    root = project_dir(project_id)
    images = root / "images"
    plan_path = root / "flow-pack" / "visual-plan.json"
    shot_path = root / "flow-pack" / "shot-list.json"
    ready: list[str] = []
    missing: list[str] = []

    visuals: list[dict] = []
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        visuals = plan.get("visuals") or []
    elif shot_path.exists():
        visuals = json.loads(shot_path.read_text(encoding="utf-8")).get("shots") or []

    remote_nums: set[int] = set()
    if check_remote:
        try:
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                for rel in cloud_sync.list_rel_paths(project_id, "images/"):
                    stem = Path(rel).stem
                    if stem.isdigit():
                        remote_nums.add(int(stem))
        except Exception:
            pass

    from src.documentary.import_images import still_file

    def _has(num: int) -> bool:
        return still_file(images, num) is not None or num in remote_nums

    for v in visuals:
        num = int(v.get("number") or 0)
        if not num:
            continue
        if _has(num):
            v["status"] = "READY"
            ready.append(f"{num:03d}")
        else:
            v["status"] = "MISSING"
            missing.append(f"{num:03d}")

    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["visuals"] = visuals
        for b in plan.get("flow_batches") or []:
            nums = [int(n) for n in b.get("visual_numbers") or []]
            imported = sum(1 for n in nums if _has(n))
            b["imported"] = imported
            b["status"] = (
                "complete"
                if imported >= len(nums) and nums
                else ("partial" if imported else "ready_to_generate")
            )
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    if shot_path.exists():
        data = json.loads(shot_path.read_text(encoding="utf-8"))
        for s in data.get("shots") or []:
            num = int(s.get("number") or 0)
            s["status"] = "READY" if _has(num) else "MISSING"
        data["ready_count"] = len(ready)
        data["missing"] = missing
        shot_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "expected": len(visuals),
        "ready": len(ready),
        "missing": missing,
        "ready_ids": ready,
    }


def update_visual_description(project_id: str, number: int, description: str) -> dict[str, Any]:
    plan = load_visual_plan(project_id)
    visuals = plan.get("visuals") or []
    bible = plan.get("visual_bible") or {}
    masters = plan.get("master_references") or []
    found = None
    for v in visuals:
        if int(v.get("number") or 0) == int(number):
            v["description"] = description.strip()
            v["action"] = description.strip()
            if v.get("visual_type") == "FLOW_REENACTMENT":
                v["flow_prompt"] = format_single_prompt(v, bible, masters)
            found = v
            break
    if not found:
        raise ValueError(f"Visual {number:03d} not found")

    for b in plan.get("flow_batches") or []:
        if int(number) in [int(x) for x in (b.get("visual_numbers") or [])]:
            b["prompt"] = format_batch_prompt(b, visuals, bible, masters)
            b["references_needed"] = batch_references(b, visuals, masters)

    path = project_dir(project_id) / "flow-pack" / "visual-plan.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    sp = project_dir(project_id) / "flow-pack" / "shot-list.json"
    if sp.exists():
        data = json.loads(sp.read_text(encoding="utf-8"))
        for s in data.get("shots") or []:
            if int(s.get("number") or 0) == int(number):
                s["description"] = found["description"]
                s["action"] = found["description"]
                s["prompt"] = found.get("flow_prompt") or s.get("prompt")
                s["flow_prompt"] = found.get("flow_prompt")
        data["flow_batches"] = plan.get("flow_batches")
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def plan_to_markdown(plan: dict[str, Any]) -> str:
    stats = plan.get("stats") or {}
    lines = [
        "# Visual Plan",
        "",
        f"- Total visuals: **{stats.get('total', 0)}**",
        f"- Flow reenactments: **{stats.get('flow', 0)}**",
        f"- Archival / document / other: **{stats.get('real_or_other', 0)}**",
        f"- Master references: **{stats.get('master_references', 0)}**",
        f"- Flow batches: **{stats.get('flow_batches', 0)}**",
        "",
        "## Master references",
    ]
    for m in plan.get("master_references") or []:
        lines.append(
            f"- **{m.get('name')}** (`{m.get('id')}`) — used in {m.get('used_in_flow', 0)} Flow visuals — "
            f"`{m.get('master_filename')}`"
        )
    lines.extend(["", "## Flow batches"])
    for b in plan.get("flow_batches") or []:
        refs = ", ".join(r.get("name") or r.get("id") for r in (b.get("references_needed") or [])) or "(none)"
        lines.append(f"- {b.get('id')}: {b.get('label')} — refs: {refs}")
    lines.extend(["", "## By type"])
    for t, c in sorted((stats.get("by_type") or {}).items()):
        lines.append(f"- {t}: {c}")
    cov = plan.get("coverage") or {}
    if cov.get("by_beat"):
        lines.extend(["", "## Coverage by story beat"])
        for bid, nums in list(cov["by_beat"].items())[:20]:
            lines.append(f"- Beat {bid}: {len(nums)} visuals ({nums[0]:03d}…)" if nums else f"- Beat {bid}: 0")
    return "\n".join(lines) + "\n"


def _enrich_visual(i: int, shot: dict[str, Any], beats: list[dict]) -> dict[str, Any]:
    narr = str(shot.get("narration") or "").strip()
    action = str(shot.get("action") or "").strip()
    vtype = classify_visual_type(narr + " " + action)
    beat_id = map_story_beat(narr, beats, index=i)
    period = _guess_period(narr) or _guess_period(action)
    if vtype in ("DOCUMENT", "HEADLINE", "SCREENSHOT", "LOGO", "CHART", "MAP"):
        person_strategy = "NO_FACE"
    elif vtype == "ARCHIVAL_PHOTO":
        person_strategy = "ARCHIVAL_REAL"
    else:
        person_strategy = "FLOW_REENACTMENT"

    desc = action or _description_from_narration(narr)
    visual = {
        **shot,
        "number": int(shot.get("number") or i),
        "visual_id": f"V{int(shot.get('number') or i):03d}",
        "id": shot.get("id") or f"SHOT_{int(shot.get('number') or i):03d}",
        "expected_file": f"{int(shot.get('number') or i):03d}.png",
        "story_beat_id": beat_id,
        "narration_segment": narr,
        "visual_type": vtype,
        "description": desc,
        "characters": list(shot.get("characters") or []),
        "location": shot.get("location") or "",
        "period": period,
        "duration_target": int(shot.get("duration_target") or 7),
        "reference_ids": list(shot.get("references") or []),
        "references": list(shot.get("references") or []),
        "person_strategy": person_strategy,
        "ken_burns": shot.get("ken_burns") or "slow_push",
        "status": "MISSING",
        "flow_prompt": "",
    }
    if vtype != "FLOW_REENACTMENT":
        visual["acquisition_note"] = (
            f"Import a real {vtype.replace('_', ' ').lower()} asset. "
            f"Do NOT ask Flow to fake authentic filings/headlines/logos. "
            f"Hint: {(desc or narr)[:160]}"
        )
    return visual


def classify_visual_type(text: str) -> str:
    low = (text or "").lower()
    for vtype, cues in _NON_FLOW_CUES:
        if any(c in low for c in cues):
            return vtype
    return "FLOW_REENACTMENT"


def map_story_beat(narration: str, beats: list[dict], *, index: int) -> str:
    if not beats:
        return ""
    low = (narration or "").lower()
    best = ""
    best_score = 0
    for b in beats:
        event = str(b.get("event") or "").lower()
        tokens = [t for t in re.findall(r"[a-z0-9$]+", event) if len(t) > 3]
        score = sum(1 for t in tokens if t in low)
        if score > best_score:
            best_score = score
            best = str(b.get("id") or "")
    if best_score >= 2:
        return best
    bi = min(len(beats) - 1, max(0, (index - 1) % len(beats)))
    return str(beats[bi].get("id") or "")


def _guess_period(text: str) -> str:
    m = re.search(r"\b((?:19|20)\d{2})\b", text or "")
    return m.group(1) if m else ""


def _description_from_narration(narr: str) -> str:
    return _still_from_vo({"narration": narr, "narration_segment": narr}, None)


def _assign_camera_variety(visuals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    vi = 0
    for v in visuals:
        if v.get("visual_type") != "FLOW_REENACTMENT":
            continue
        v["shot_type"] = CAMERA_VARIETY[vi % len(CAMERA_VARIETY)]
        v["ken_burns"] = KEN_BURNS[vi % len(KEN_BURNS)]
        vi += 1
    return visuals


def _assign_durations(visuals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for v in visuals:
        st = str(v.get("shot_type") or "")
        vt = str(v.get("visual_type") or "")
        if st in ("establishing_wide", "large_scale"):
            v["duration_target"] = 10
        elif vt in ("DOCUMENT", "HEADLINE", "SCREENSHOT"):
            v["duration_target"] = 8
        elif st in ("close_up", "object_detail", "environmental_detail"):
            v["duration_target"] = 5
        else:
            v["duration_target"] = 7
    return visuals


def _upgrade_bible(bible: dict[str, Any], visuals: list[dict], story: dict) -> dict[str, Any]:
    out = deepcopy(bible) if isinstance(bible, dict) else {}
    out.setdefault("global_style", VISUAL_DIRECTION)
    out.setdefault("visual_style", out.get("global_style"))
    out.setdefault("period_rules", [])
    if not out.get("characters") and story.get("characters"):
        chars = []
        for i, c in enumerate(story.get("characters") or [], start=1):
            if not isinstance(c, dict):
                continue
            name = str(c.get("name") or "").strip()
            if not name:
                continue
            chars.append(
                {
                    "id": f"CHAR_{i:03d}",
                    "name": name,
                    "role": c.get("role_in_story") or "",
                    "description": c.get("important_actions") or "",
                    "visual_description": (
                        f"Documentary reconstruction of {name}, period-accurate wardrobe, "
                        "photorealistic — illustration/reconstruction, not claimed archival photo"
                    ),
                    "appearance_strategy": "FLOW_REENACTMENT",
                    "reference_required": i <= 2,
                    "appears_in_shots": [],
                    "periods": [c.get("relevant_period") or ""],
                    "master_reference_filename": f"CHAR_{i:03d}.png",
                }
            )
        out["characters"] = chars

    _attach_from_visuals(out, visuals)
    years = sorted({str(v.get("period")) for v in visuals if v.get("period")})
    if years and not out.get("period_rules"):
        out["period_rules"] = [
            f"{y}: period-accurate clothing, phones, computers, interiors — avoid anachronisms"
            for y in years[:8]
        ]
    return out


def _attach_from_visuals(bible: dict, visuals: list[dict]) -> None:
    for v in visuals:
        num = int(v.get("number") or 0)
        text = f"{v.get('narration_segment')} {v.get('description')} {v.get('location')}".lower()
        for group in ("characters", "important_objects"):
            for ent in bible.get(group) or []:
                name = str(ent.get("name") or "").lower()
                if name and name in text:
                    apps = list(ent.get("appears_in_shots") or [])
                    if num and num not in apps:
                        apps.append(num)
                    ent["appears_in_shots"] = apps
                    refs = list(v.get("reference_ids") or [])
                    eid = str(ent.get("id") or "")
                    if eid and eid not in refs and v.get("visual_type") == "FLOW_REENACTMENT":
                        refs.append(eid)
                    refs = [r for r in refs if not str(r).upper().startswith("LOC_")]
                    v["reference_ids"] = refs
                    v["references"] = refs
                    if group == "characters":
                        disp = str(ent.get("name") or "").strip()
                        people = [str(x).strip() for x in (v.get("characters") or []) if str(x).strip()]
                        if disp and disp not in people:
                            people.append(disp)
                        v["characters"] = people
    for group in ("characters", "locations", "important_objects"):
        for ent in bible.get(group) or []:
            apps = ent.get("appears_in_shots") or []
            if len(apps) >= 3:
                ent["reference_required"] = True
            ent.setdefault("appearance_strategy", "FLOW_REENACTMENT")
            ent.setdefault("master_reference_filename", f"{ent.get('id')}.png")
            ent.setdefault("periods", [])


def _master_entry(ent: dict, kind: str, used: int) -> dict[str, Any]:
    eid = str(ent.get("id") or "REF")
    name = str(ent.get("name") or eid)
    look = str(ent.get("visual_description") or ent.get("description") or "").strip()
    if kind == "character":
        prompt = (
            f"Generate ONE master reference of {name} for FACE continuity in a true-story documentary.\n"
            f"{look}\n"
            "Close-up to chest. Face fully visible, distinctive hair, period-accurate wardrobe. "
            "Plain or empty background. Photoreal 16:9.\n"
            "ZERO other people. NO open-plan office, NO laptops, NO coworking, NO crowd.\n"
            "Reconstruction reference — not an archival photo."
        )
    elif kind == "location":
        prompt = (
            f"Generate ONE empty location plate of {name}. Architecture and light only.\n"
            f"{look}\n"
            "Photoreal 16:9 documentary. ZERO people. Not a stock coworking photo."
        )
    else:
        prompt = (
            f"Generate ONE object still of {name}.\n"
            f"{look}\n"
            "Hands allowed, no crowd, no logos, photoreal 16:9."
        )
    return {
        "id": eid,
        "name": ent.get("name"),
        "kind": kind,
        "role": ent.get("role") or ent.get("description") or "",
        "appearance_strategy": ent.get("appearance_strategy") or "FLOW_REENACTMENT",
        "reference_required": True,
        "master_filename": ent.get("master_reference_filename") or f"{eid}.png",
        "master_prompt": prompt,
        "used_in_flow": used,
        "notes": ent.get("notes") or "",
    }


def _batch_label(nums: list[int]) -> str:
    if not nums:
        return "(empty)"
    if len(nums) == 1:
        return f"visual {nums[0]:03d}"
    consecutive = all(nums[i] == nums[0] + i for i in range(len(nums)))
    if consecutive:
        return f"visuals {nums[0]:03d}–{nums[-1]:03d}"
    return "visuals " + ", ".join(f"{n:03d}" for n in nums)
