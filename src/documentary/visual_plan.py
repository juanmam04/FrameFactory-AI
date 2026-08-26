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

# Paper / screen props live IN the Flow still. Never ask the user for a real filing.
_PAPER_PROPS: list[tuple[tuple[str, ...], str]] = [
    (
        ("s-1", "s1", "sec filing", "prospectus", "ipo filing", " filing"),
        "Hands on a thick bound prospectus; pages dense; no readable SEC text.",
    ),
    (
        ("contract", "lease agreement", "term sheet"),
        "A contract packet on the table, signature page half-turned.",
    ),
    (
        ("headline", "newspaper", "wall street journal", "bloomberg", "new york times", "press report"),
        "A newspaper slapped on the desk, giant headline, letters not readable.",
    ),
    (
        ("screenshot", "app screen", "website", "dashboard", "interface"),
        "A laptop screen glowing; UI invented; no real brand interface.",
    ),
    (
        ("chart", "graph", "valuation chart", "stock chart"),
        "A printout of a rising-then-falling chart, numbers illegible.",
    ),
    (
        ("map of", "global expansion map"),
        "A paper map with pins, not a stock infographic.",
    ),
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
    is_check = str(project.get("content_format") or project.get("mode") or "") == "check_als"
    _rewrite_stills(visuals, bible, str(project.get("topic") or ""), use_llm=use_llm and not is_check)
    visuals = _assign_camera_variety(visuals)
    visuals = _assign_durations(visuals)

    if is_check:
        from src.documentary.formats.check_als.editorial import VISUAL_DIRECTION as CHECK_DIR

        bible["global_style"] = CHECK_DIR
        bible["format"] = "check_als"

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
    if is_check:
        from src.documentary.formats.check_als.visuals import apply_check_visual_layer

        plan = apply_check_visual_layer(project, plan)
        visuals = plan.get("visuals") or visuals
        bible = plan.get("visual_bible") or bible
        # Retag climates from Spanish VO + rebuild Flow blocks (rise/peak/crack/…).
        flow_batches = group_flow_batches(visuals, batch_size=batch_size)
        masters = plan.get("master_references") or masters
        for b in flow_batches:
            b["prompt"] = format_batch_prompt(b, visuals, bible, masters)
            b["references_needed"] = batch_references(b, visuals, masters)
        plan["flow_batches"] = flow_batches
        plan["visuals"] = visuals
        stats = summarize_visuals(visuals, flow_batches, masters)
        plan["stats"] = stats
        for v in visuals:
            if str(v.get("visual_type") or "") == "FLOW_REENACTMENT":
                v["flow_prompt"] = format_single_prompt(v, bible, masters)
                if v.get("image_prompt"):
                    # Refresh stored prompt with face lock after moment retag.
                    from src.documentary.formats.check_als.visuals import compose_image_prompt

                    meta = {
                        "protagonist_age": v.get("protagonist_age"),
                        "protagonist_state": v.get("protagonist_state"),
                        "story_time": v.get("story_time"),
                    }
                    prompt = compose_image_prompt(v, meta)
                    v["image_prompt"] = prompt
                    v["flow_prompt"] = prompt
                    v["prompt"] = prompt
        plan["visuals"] = visuals
        stats = plan.get("stats") or stats

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
        f"visual_plan visuals={len(visuals)} flow={stats.get('flow')} batches={len(flow_batches)}",
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


def _promote_all_to_flow(visuals: list[dict[str, Any]]) -> None:
    """Every still is a Flow photograph. No scavenger-hunt 'upload the real S-1' slots."""
    for v in visuals:
        v["visual_type"] = "FLOW_REENACTMENT"
        v["person_strategy"] = "FLOW_REENACTMENT"
        v.pop("acquisition_note", None)


def refresh_flow_prompts(plan: dict[str, Any]) -> dict[str, Any]:
    """Rebuild Flow copy-paste prompts so old episodes pick up director rules."""
    visuals = plan.get("visuals") or []
    bible = plan.get("visual_bible") or {}
    _promote_all_to_flow(visuals)
    _purge_stock_locations(bible)
    _tag_moments(visuals)
    used: dict[str, set[int]] = {}
    for v in visuals:
        _concretize_visual(v, bible, used)
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
    _dedupe_stills(visuals, bible)
    _assign_camera_variety(visuals)
    masters = select_master_references(bible, visuals)
    plan["master_references"] = masters
    plan["visual_bible"] = bible
    for v in visuals:
        if str(v.get("visual_type") or "") == "FLOW_REENACTMENT":
            v["flow_prompt"] = format_single_prompt(v, bible, masters)
    plan["flow_batches"] = group_flow_batches(visuals, batch_size=int(plan.get("batch_size") or 10))
    for b in plan["flow_batches"]:
        b["prompt"] = format_batch_prompt(b, visuals, bible, masters)
        b["references_needed"] = batch_references(b, visuals, masters)
    plan["stats"] = summarize_visuals(visuals, plan["flow_batches"], masters)
    return plan


def group_flow_batches(visuals: list[dict[str, Any]], *, batch_size: int = 10) -> list[dict[str, Any]]:
    """One Flow pack per story MOMENT (rise/peak/crack/collapse/aftermath), not a timeline of 001→002."""
    size = max(1, int(batch_size))
    _promote_all_to_flow(visuals)
    flow = list(visuals)
    _tag_moments(flow)
    order: list[str] = []
    buckets: dict[str, list[dict[str, Any]]] = {}
    for v in flow:
        mid = str(v.get("moment_id") or "rise")
        if mid not in buckets:
            order.append(mid)
            buckets[mid] = []
        buckets[mid].append(v)
    batches: list[dict[str, Any]] = []
    for mid in order:
        chunk = buckets[mid]
        label = str(chunk[0].get("moment_label") or mid)
        for i in range(0, len(chunk), size):
            part = chunk[i : i + size]
            nums = [int(v["number"]) for v in part]
            batches.append(
                {
                    "id": f"BATCH_{len(batches) + 1:02d}",
                    "moment_id": mid,
                    "moment_label": label,
                    "visual_numbers": nums,
                    "label": label,
                    "count": len(part),
                    "interchangeable": True,
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


_CANNED_STILL = re.compile(
    r"ONE investor at a private table|cheap printed paper sign|"
    r"emptied office floor at night|For Sale sign onto the company|"
    r"raw unfinished floor|in a specific real place, body in motion|"
    r"a group of (investors|entrepreneurs|employees)|busy office|open.?plan",
    re.I,
)

_MOMENT_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("aftermath", "Qué quedó", (" spacs", "spac ", "spac,", "2021", "layoff", "laid off", "covid", "pandemic", "remote work", "listed via")),
    (
        "collapse",
        "Se cae",
        (
            "pulled",
            "postponed",
            "stepped down",
            "bailout",
            "plummet",
            "8 billion",
            "chaos",
            "evaporated",
            "existential",
            "overnight",
            "abruptly",
        ),
    ),
    (
        "crack",
        "Se resquebraja",
        ("s-1", "roadshow", "scrutiny", "skepticism", "governance", "erratic", "conflict of interest", "critics", "red flags"),
    ),
    ("peak", "En la cima", ("47 billion", "20 billion", "most valuable", "staggering milestone", "catapulted", "worldwide")),
    (
        "rise",
        "Le va bien",
        ("founded", "launch", "2010", "2014", "community", "vision", "series d", "gig economy", "opened", "started"),
    ),
)
# Check ALS / Spanish VO — checked after English documentary cues.
_MOMENT_RULES_ES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "aftermath",
        "Qué quedó",
        (
            "años después",
            "qué quedó",
            "vacío después",
            "mañana lo lees",
            "bloqueas",
            "papel millonario",
            "millonario de papel",
            "27 años",
            "veintisiete",
        ),
    ),
    (
        "collapse",
        "Se cae",
        (
            "quiebra",
            "bancarrota",
            "eliminado",
            "no hay anillo",
            "cero campeonatos",
            "se cae",
            "se derrumba",
            "todo se rompe",
            "desastre",
            "te echan",
            "perdiste todo",
        ),
    ),
    (
        "crack",
        "Se resquebraja",
        (
            "deuda",
            "acreedor",
            "préstamo",
            "prestamo",
            "inyectas",
            "cuenta personal queda en cero",
            "diluci",
            "crisis",
            "presión",
            "se pierde",
            "derrota",
            "14-18",
            "no cierra",
            "miedo",
            "ansiedad",
            "no dormís",
            "no dormis",
            "ansiedad",
        ),
    ),
    (
        "peak",
        "En la cima",
        (
            "sold out",
            "no entra más",
            "no entra mas",
            "estadio lleno",
            "gradas llenas",
            "4800",
            "cuatro mil",
            "palco",
            "campeon",
            "campeón",
            "gloria",
            "en la cima",
            "primera vez no ves huecos",
        ),
    ),
    (
        "rise",
        "Le va bien",
        (
            "firmás",
            "firmas",
            "llaves",
            "utilero",
            "51%",
            "cincuenta y uno",
            "dueño",
            "renuncia",
            "badge",
            "arranca",
            "oportunidad",
            "playoff",
            "primera victoria",
            "mudás",
            "mudas",
            "es tuyo",
            "equipo sólido",
            "visión clara",
            "vision clara",
            "tienes 22",
            "oficina",
        ),
    ),
)
_MOOD_TO_MOMENT: dict[str, str] = {
    "neutral": "rise",
    "curiosity": "rise",
    "opportunity": "rise",
    "hope": "rise",
    "progress": "rise",
    "determination": "rise",
    "relief": "rise",
    "comeback": "rise",
    "confidence": "peak",
    "success": "peak",
    "happiness": "peak",
    "celebration": "peak",
    "glory": "peak",
    "wealth": "peak",
    "power": "peak",
    "freedom": "peak",
    "tension": "crack",
    "pressure": "crack",
    "anxiety": "crack",
    "fear": "crack",
    "risk": "crack",
    "failure": "collapse",
    "sadness": "collapse",
    "loneliness": "collapse",
    "despair": "collapse",
    "crisis": "collapse",
    "bankruptcy": "collapse",
    "reflection": "aftermath",
    "nostalgia": "aftermath",
}
_CHECK_FN_TO_MOMENT: dict[str, str] = {
    "setup": "rise",
    "opportunity": "rise",
    "decision": "rise",
    "commitment": "rise",
    "progress": "rise",
    "proof": "peak",
    "reward": "peak",
    "payoff": "peak",
    "climax": "peak",
    "setback": "crack",
    "escalation": "crack",
    "risk": "crack",
    "crisis": "collapse",
    "loss": "collapse",
    "recovery": "rise",
    "comeback": "rise",
    "reflection": "aftermath",
    "ending": "aftermath",
}
_FN_MOMENT = {
    "hook": "collapse",
    "setup": "rise",
    "desire": "rise",
    "progress": "rise",
    "obstacle": "crack",
    "escalation": "crack",
    "turn": "collapse",
    "consequence": "collapse",
    "resolution": "aftermath",
}
_MOMENT_LABEL = {
    "rise": "Le va bien",
    "peak": "En la cima",
    "crack": "Se resquebraja",
    "collapse": "Se cae",
    "aftermath": "Qué quedó",
}
_MOMENT_DIRECTOR = {
    "rise": (
        "ALL stills = the climb. Energy, cheap beginnings, belief. Nobody is ruined yet. "
        "FACE: hopeful / determined — slight smile or calm focus. NEVER depressed or suicidal face."
    ),
    "peak": (
        "ALL stills = the high. Money, crowd, the number, the illusion it will last. "
        "FACE: proud smile or clear joy. NOT sad, NOT hollow-eyed."
    ),
    "crack": (
        "ALL stills = the hairline fracture. Papers, doubt, 2am, the room going quiet. "
        "FACE: worried / tense — stressed, not theatrical despair."
    ),
    "collapse": (
        "ALL stills = it breaking. Night, empty, the phone, the exit. No victory lap. "
        "FACE: shock or devastation OK here — still readable, not gore."
    ),
    "aftermath": (
        "ALL stills = what is left. Quiet, leftover rooms, the smaller number. "
        "FACE: tired acceptance / soft neutral — not suicidal every frame."
    ),
}
_FACE_BY_MOMENT = {
    "rise": (
        "FACE LOCK: slight hopeful smile OR calm determined mouth; open / bright dot eyes; "
        "eyebrows neutral-up. FORBIDDEN: downturned suicidal mouth, dead eyes, crying, hollow despair."
    ),
    "peak": (
        "FACE LOCK: clear smile or proud calm grin; energetic eyebrows. "
        "FORBIDDEN: sad face, depressed mouth, looking like giving up."
    ),
    "crack": (
        "FACE LOCK: worried frown, tight mouth, tense eyebrows — stress readable. "
        "Not smiling; also not suicidal blank stare."
    ),
    "collapse": (
        "FACE LOCK: shocked or devastated — downturned mouth allowed; eyes wide or heavy. "
        "One clear emotion of loss, not generic depression on every beat."
    ),
    "aftermath": (
        "FACE LOCK: quiet tired neutral / soft acceptance; small closed mouth. "
        "NOT theatrical suicide-face; quieter than collapse."
    ),
}

# Angles inside one moment — same climate, different camera. Not a sequence.
_MOMENT_PALETTES: dict[str, tuple[tuple[str, str], ...]] = {
    "rise": (
        ("hangs a cheap paper sign on a raw storefront, almost nobody watching", "early-2010s NYC storefront"),
        ("at a kitchen table, sketching a floor plan on scrap paper", "small apartment kitchen"),
        ("walking a raw unfinished floor — paint cans, one table, selling a room that is not built", "raw loft"),
        ("on a city sidewalk with a printed flyer, early street clothes, a few curious passersby", "sidewalk midday"),
        ("laughing with ONE cofounder over coffee in a scuffed diner booth", "diner booth"),
        ("carrying a cheap banner into an empty ground-floor space", "empty storefront interior"),
        ("on a fire escape in daylight, looking at the block like it already belongs to them", "fire escape, day"),
        ("in a tiny office with a second-hand desk, phone in hand, still hungry", "tiny first office"),
        ("taping a floor plan to a brick wall, sleeves rolled", "brick-wall studio"),
        ("on a bike or on foot through the neighborhood, the building behind them still ordinary", "neighborhood street"),
    ),
    "peak": (
        ("on a private jet, looking out the window, a closed folder on the tray", "private jet cabin"),
        ("walking out of a glass tower at golden hour, the city looking easy", "tower plaza, golden hour"),
        ("at a long table with ONE investor and a bottle, the term sheet already signed", "private dining room"),
        ("in a hotel suite overlooking the skyline, jacket off, the night still going", "hotel suite"),
        ("on a rooftop at dusk, city below, phone face-down, nothing urgent yet", "rooftop dusk"),
        ("in the back of a black car, skyline sliding by, calm", "car on the FDR"),
        ("standing in a huge empty floor they just leased, arms open, daylight", "new empty floor, day"),
        ("at a packed keynote edge of stage, lights, one person in focus", "conference stage wing"),
        ("pouring a drink in a penthouse kitchen, the view doing the talking", "penthouse kitchen"),
        ("crossing a plaza at noon like the building is already theirs", "corporate plaza, noon"),
    ),
    "crack": (
        ("leans on a hotel-room desk at 2am, thick filing pages scattered", "hotel room at 2am"),
        ("stands in a freight elevator with one banker, both silent, doors closing", "service elevator"),
        ("at a printer at 5am, pulling a thick prospectus, the floor otherwise dark", "copy room at 5am"),
        ("in a narrow hallway after a meeting, forehead against the wall", "empty conference hallway"),
        ("on a rainy sidewalk outside a bank, the other person already walking away", "bank entrance in rain"),
        ("reading a phone under a desk lamp, the rest of the room dark", "desk at night"),
        ("in a dim bar booth with ONE other person, a handshake that already looks wrong", "back-room bar booth"),
        ("waiting outside a closed boardroom door, chair against the wall", "corridor outside boardroom"),
        ("sits alone at a corner table, a contract face-down, wine untouched", "quiet restaurant after closing"),
        ("in the back seat, staring at a number that just got smaller", "car at night"),
    ),
    "collapse": (
        ("walks away from a glass tower at night, phone lighting the face, street empty", "Manhattan sidewalk at night"),
        ("alone on an emptied floor at night, one desk lamp, everyone else gone", "gutted office floor at night"),
        ("on a loading dock at dusk, watching a moving truck pull away", "loading dock at dusk"),
        ("waits on courthouse steps at dawn, coat collar up, no entourage", "courthouse steps at dawn"),
        ("in a taxi in traffic, the company tower shrinking in the rear window", "yellow cab in traffic"),
        ("in a boardroom AFTER everyone left, one chair kicked back, lights still on", "abandoned boardroom"),
        ("on a fire escape at dusk, looking at the building no longer under control", "fire escape at dusk"),
        ("crossing a plaza at noon, head down, no crowd in the frame", "city plaza at noon"),
        ("in a bedroom doorway at night, still in a suit, home but not present", "apartment doorway at night"),
        ("on a rooftop at night, holding a phone with the bad headline", "rooftop at night"),
    ),
    "aftermath": (
        ("at a warehouse window with a for-lease flyer in hand", "industrial window, late day"),
        ("walking an empty event space after the crowd left, chairs stacked", "ballroom after the event"),
        ("on an emptied floor in daylight, dust in the sun, nobody coming back", "empty floor, day"),
        ("in a taxi, older, watching a smaller sign on the same tower", "cab, grey day"),
        ("at a kitchen table with a thinner stack of papers, morning", "apartment kitchen, morning"),
        ("standing in a doorway of a space that used to be loud", "quiet doorway"),
        ("on a sidewalk in winter light, the old HQ behind, ordinary traffic", "sidewalk, winter"),
        ("in an office with half the desks gone, one plant still alive", "half-empty office"),
        ("looking at a phone with a much smaller valuation, no reaction left", "desk, late day"),
        ("closing a cardboard box of nameplates, the hallway empty", "storage hallway"),
    ),
}
_UNIQUE_BEATS = _MOMENT_PALETTES["collapse"] + _MOMENT_PALETTES["rise"]
_TIMES = ("dawn", "midday", "golden hour", "blue hour", "night", "3am", "rain", "winter light")
_BEAT_DETAILS = (
    "wool coat",
    "open collar, no tie",
    "2014-era thin laptop under one arm",
    "paper cup going cold",
    "scuffed dress shoes",
    "a single page folded in a pocket",
    "wedding ring catching the light",
    "backpack from the first year",
    "untucked shirt after a long night",
    "keys to a space that is no longer theirs",
    "a phone with the ringer off",
)


def _prop_from_narration(visual: dict[str, Any]) -> str:
    text = " ".join(
        str(visual.get(k) or "")
        for k in ("narration_segment", "narration", "description", "action", "acquisition_note")
    ).lower()
    for cues, prop in _PAPER_PROPS:
        if any(c in text for c in cues):
            return prop
    return ""


def _tag_moments(visuals: list[dict[str, Any]]) -> None:
    total = max(1, len(visuals))
    for i, v in enumerate(visuals):
        text = " ".join(
            str(v.get(k) or "")
            for k in ("narration_segment", "narration", "description", "action", "script_text")
        ).lower()
        mid = ""
        label = ""
        for kid, lab, keys in _MOMENT_RULES:
            if any(k in text for k in keys):
                mid, label = kid, lab
                break
        if not mid:
            for kid, lab, keys in _MOMENT_RULES_ES:
                if any(k in text for k in keys):
                    mid, label = kid, lab
                    break
        if not mid:
            fn = str(v.get("story_function") or v.get("function") or "").lower()
            if fn in _FN_MOMENT:
                mid = _FN_MOMENT[fn]
            elif fn in _CHECK_FN_TO_MOMENT:
                mid = _CHECK_FN_TO_MOMENT[fn]
            if mid:
                label = _MOMENT_LABEL.get(mid, label)
        if not mid:
            mood = str(v.get("mood") or (v.get("scene_semantics") or {}).get("mood") or "").lower()
            check_fn = str(
                v.get("story_function")
                or (v.get("scene_semantics") or {}).get("story_function")
                or ""
            ).lower()
            if not mood or not check_fn:
                try:
                    from src.documentary.formats.check_als.asset_reuse import infer_mood_function

                    m2, f2, _ = infer_mood_function(v)
                    mood = mood or str(m2 or "").lower()
                    check_fn = check_fn or str(f2 or "").lower()
                except Exception:
                    pass
            if mood in _MOOD_TO_MOMENT:
                mid = _MOOD_TO_MOMENT[mood]
            elif check_fn in _CHECK_FN_TO_MOMENT:
                mid = _CHECK_FN_TO_MOMENT[check_fn]
            if mid:
                label = _MOMENT_LABEL.get(mid, "Le va bien")
        if not mid:
            # Arc by position — never dump the whole episode into "Le va bien".
            frac = (i + 1) / total
            if frac <= 0.22:
                mid = "rise"
            elif frac <= 0.42:
                mid = "rise"
            elif frac <= 0.58:
                mid = "crack"
            elif frac <= 0.78:
                mid = "peak"
            elif frac <= 0.90:
                mid = "collapse"
            else:
                mid = "aftermath"
            label = _MOMENT_LABEL[mid]
        v["moment_id"] = mid
        v["moment_label"] = label or _MOMENT_LABEL.get(mid, "Le va bien")
        face = _FACE_BY_MOMENT.get(mid, "")
        if face:
            v["face_direction"] = face


def face_direction_for_moment(moment_id: str) -> str:
    return _FACE_BY_MOMENT.get(str(moment_id or "rise"), _FACE_BY_MOMENT["rise"])


def _still_from_vo(
    visual: dict[str, Any],
    bible: dict[str, Any] | None,
    used: dict[str, set[int]] | set[int] | None = None,
) -> str:
    still, _loc = _unique_beat(visual, bible, used)
    return still


def _unique_beat(
    visual: dict[str, Any],
    bible: dict[str, Any] | None,
    used: dict[str, set[int]] | set[int] | None = None,
) -> tuple[str, str]:
    narr = str(visual.get("narration_segment") or visual.get("narration") or "").strip()
    who = _names_in_text(narr, bible)
    who_s = ", ".join(who) if who else _lead(bible)
    n = max(1, int(visual.get("number") or 1))
    mid = str(visual.get("moment_id") or "rise")
    palette = _MOMENT_PALETTES.get(mid) or _UNIQUE_BEATS
    if isinstance(used, dict):
        taken = used.setdefault(mid, set())
    else:
        taken = used if used is not None else set()
    start = (n - 1) % len(palette)
    idx = start
    for off in range(len(palette)):
        cand = (start + off) % len(palette)
        if cand not in taken:
            idx = cand
            break
    taken.add(idx)
    action, loc = palette[idx]
    when = _TIMES[(n * 5 + idx) % len(_TIMES)]
    detail = _BEAT_DETAILS[(n * 3 + idx) % len(_BEAT_DETAILS)]
    still = f"{who_s} {action}, {when}, {detail}. No crowd, no open-plan office."
    return still, loc


def _concretize_visual(
    visual: dict[str, Any],
    bible: dict[str, Any] | None,
    used: dict[str, set[int]] | set[int] | None = None,
) -> None:
    if str(visual.get("visual_type") or "FLOW_REENACTMENT") != "FLOW_REENACTMENT":
        return
    desc = _FILLER_ACTION.sub("", str(visual.get("description") or visual.get("action") or "")).strip(" .")
    stale = (not desc) or _is_vo(desc) or _STOCKY_DESC.search(desc) or _CANNED_STILL.search(desc)
    if stale:
        still, loc = _unique_beat(visual, bible, used)
        prop = _prop_from_narration(visual)
        if prop:
            still = f"{still.rstrip('. ')}. {prop}"
        visual["description"] = still
        visual["action"] = still
        visual["location"] = loc
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


def _dedupe_stills(visuals: list[dict[str, Any]], bible: dict[str, Any] | None) -> None:
    seen: set[str] = set()
    used: dict[str, set[int]] = {}
    for v in visuals:
        if str(v.get("visual_type") or "") != "FLOW_REENACTMENT":
            continue
        key = re.sub(r"[^a-z0-9]+", " ", str(v.get("description") or v.get("action") or "").lower()).strip()
        if key and key not in seen:
            seen.add(key)
            continue
        still, loc = _unique_beat(v, bible, used)
        v["description"] = still
        v["action"] = still
        v["location"] = loc
        seen.add(re.sub(r"[^a-z0-9]+", " ", still.lower()).strip())


def _rewrite_stills(
    visuals: list[dict[str, Any]],
    bible: dict[str, Any],
    topic: str,
    *,
    use_llm: bool,
) -> None:
    used: dict[str, set[int]] = {}
    _tag_moments(visuals)
    for v in visuals:
        _concretize_visual(v, bible, used)
    _dedupe_stills(visuals, bible)
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
        "sidewalk, bedroom at 3am, loading dock, courthouse steps — not 'office' twice in a row.\n"
        "Keep the SAME emotional register as the moment (rise vs collapse). Different camera, same climate."
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
    _dedupe_stills(flow, bible)


def _story_description(visual: dict[str, Any], bible: dict[str, Any] | None = None) -> str:
    raw = str(visual.get("description") or visual.get("action") or "").strip()
    raw = _FILLER_ACTION.sub("", raw).strip(" .")
    if raw.lower().startswith("photograph this exact"):
        raw = ""
    if raw and not _is_vo(raw) and not _STOCKY_DESC.search(raw) and not _CANNED_STILL.search(raw):
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
    mid = str(batch.get("moment_id") or "")
    if not mid and nums:
        mid = str((by_num.get(nums[0]) or {}).get("moment_id") or "rise")
    label = str(batch.get("moment_label") or _MOMENT_LABEL.get(mid, "this moment"))
    climate = _MOMENT_DIRECTOR.get(mid, "ALL stills share the same emotional register.")
    lines = [
        f"Create {n} separate 16:9 cinematic documentary stills of ONE STORY MOMENT: {label.upper()}.",
        climate,
        "They are INTERCHANGEABLE — not a sequence, not 1 then 2 then 3. Different camera and place, SAME climate.",
        "Do not create a collage. Do not tell a 10-step timeline. Do not repeat the same office/crowd.",
        "",
        "HARD RULES:",
        "- The same person must look like the same person across images (use character refs).",
        "- Change location, time of day, and camera every shot.",
        "- Forbidden: crowded coworking, rows of laptops, generic glass conference rooms,",
        "  handshake, CEO portrait, anonymous extras filling the frame.",
        "",
        f"DIRECTOR: {FLOW_DIRECTOR_RULES}",
        f"STYLE: {_style_text(bible)[:320]}",
        "",
        f"ANGLES on {label} (same moment, different photograph):",
        "",
    ]
    for i, num in enumerate(nums, start=1):
        v = by_num.get(num) or {}
        lines.append(f"{i}. {format_scene_line(v, masters, bible)}")
        lines.append("")
    lines.extend(
        [
            "GENERAL RULES:",
            "- 16:9 photoreal documentary;",
            "- protagonist visible and doing the action;",
            "- period-accurate wardrobe, phones, cars, interiors;",
            "- every frame is the SAME emotional beat from a new angle;",
            "- CLEAN plate: NO subtitles, captions, titles, lower-thirds, speech bubbles,",
            "  logos, watermarks, or any readable on-image text (Spanish or English);",
            "  voiceover/subs are added later in editing — never burn words into the frame;",
            "- no collage; no stock office crowd.",
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
        f"{when}{place} {desc}{who} "
        f"{cam} candid documentary still, photoreal, period-accurate. Same story climate, new angle, not stock."
        f"{master_hint}"
    ).strip()


def format_single_prompt(
    visual: dict[str, Any],
    bible: dict[str, Any],
    masters: list[dict[str, Any]] | None = None,
) -> str:
    if str((bible or {}).get("format") or "") == "check_als":
        from src.documentary.formats.check_als.visuals import format_check_prompt

        # Always go through format_check_prompt so TEXT HARD BAN is appended to cached prompts.
        return format_check_prompt(visual, bible)
    body = (
        "Create ONE 16:9 cinematic documentary still. One story beat. One protagonist.\n"
        "Photoreal. No collage. No crowded office stock.\n"
        "CLEAN plate: no subtitles, captions, titles, or any burned-in text (added later in edit).\n"
        f"STYLE: {_style_text(bible)[:280]}\n"
        f"DIRECTOR: {FLOW_DIRECTOR_RULES}\n\n"
        f"{format_scene_line(visual, bible=bible, masters=masters)}\n"
    )
    return body


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
    vtype = "FLOW_REENACTMENT"
    beat_id = map_story_beat(narr, beats, index=i)
    period = _guess_period(narr) or _guess_period(action)
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
    return visual


def classify_visual_type(text: str) -> str:
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
