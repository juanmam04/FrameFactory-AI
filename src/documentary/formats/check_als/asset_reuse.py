"""Check visual asset semantics + smart still reuse. No LLM at match time. Does not rewrite script."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.documentary.import_images import still_file
from src.documentary.project import project_dir

MOODS = (
    "neutral", "curiosity", "opportunity", "hope",
    "tension", "pressure", "anxiety", "fear",
    "sadness", "loneliness", "failure", "despair",
    "crisis", "bankruptcy", "risk",
    "progress", "relief", "confidence",
    "success", "happiness", "celebration", "glory",
    "wealth", "power", "freedom",
    "reflection", "nostalgia",
    "comeback", "determination",
)
STORY_FUNCTIONS = (
    "setup", "opportunity", "decision", "commitment",
    "progress", "proof", "reward",
    "setback", "crisis", "loss",
    "escalation", "risk",
    "recovery", "comeback",
    "payoff", "climax",
    "reflection", "ending",
)
INTENSITIES = ("low", "medium", "high")
ERAS = (
    "ordinary_life", "pre_owner", "early_owner",
    "struggling_owner", "growing_owner", "established_owner", "late_story",
)
SUBJECTS = (
    "protagonist", "team", "crowd", "arena", "money", "documents",
    "phone", "family", "coach", "player", "city", "object", "environment",
)
ACTIONS = (
    "working", "reading", "watching", "walking", "meeting", "negotiating",
    "signing", "waiting", "celebrating", "thinking", "packing", "moving",
    "calling", "training", "playing", "losing", "winning",
)
LOCATION_FAMILIES = {
    "office": "office",
    "cubicle": "office",
    "owner_office": "office",
    "meeting": "office",
    "shared_apt": "home",
    "new_apt": "home",
    "home": "home",
    "arena": "arena",
    "locker": "arena",
    "tunnel": "arena",
    "court": "arena",
    "stands": "arena",
    "city": "city",
}

MOOD_NEIGHBORS: dict[str, set[str]] = {
    "anxiety": {"pressure", "fear", "tension"},
    "pressure": {"anxiety", "tension", "risk"},
    "tension": {"pressure", "anxiety", "curiosity"},
    "fear": {"anxiety", "crisis"},
    "glory": {"success", "celebration", "confidence"},
    "success": {"glory", "celebration", "confidence", "progress"},
    "celebration": {"glory", "success", "happiness"},
    "failure": {"sadness", "despair", "loneliness", "setback"},
    "sadness": {"failure", "loneliness", "despair"},
    "despair": {"failure", "sadness", "crisis"},
    "progress": {"hope", "confidence", "relief"},
    "hope": {"progress", "opportunity", "curiosity"},
    "crisis": {"fear", "bankruptcy", "risk", "pressure"},
    "bankruptcy": {"crisis", "despair", "risk"},
    "reflection": {"nostalgia", "neutral"},
    "curiosity": {"opportunity", "hope"},
    "opportunity": {"curiosity", "hope"},
}
MOOD_FORBIDDEN: dict[str, set[str]] = {
    "glory": {"bankruptcy", "despair", "crisis"},
    "celebration": {"bankruptcy", "despair", "failure", "crisis"},
    "success": {"bankruptcy", "despair"},
    "bankruptcy": {"glory", "celebration", "success", "happiness"},
    "crisis": {"glory", "celebration"},
    "failure": {"glory", "celebration"},
}

FN_NEIGHBORS: dict[str, set[str]] = {
    "setback": {"crisis", "loss", "risk"},
    "crisis": {"setback", "loss", "escalation"},
    "loss": {"setback", "crisis"},
    "progress": {"proof", "reward"},
    "proof": {"progress", "reward"},
    "reward": {"progress", "proof", "payoff"},
    "recovery": {"comeback", "progress"},
    "comeback": {"recovery", "progress"},
    "payoff": {"climax", "reward"},
    "climax": {"payoff"},
    "setup": {"opportunity"},
    "opportunity": {"setup", "decision"},
    "ending": {"reflection", "payoff"},
    "reflection": {"ending"},
}

WEIGHTS = {
    "mood": 0.25,
    "story_function": 0.20,
    "location": 0.15,
    "era": 0.15,
    "subject": 0.10,
    "intensity": 0.05,
    "action": 0.05,
    "age": 0.05,
}

AUTO_REUSE = 0.75
REVIEW_REUSE = 0.60
MIN_DISTANCE = 8
DEFAULT_MAX_REUSE = 3
AMBIENT_MAX_REUSE = 4

_HERO_PATTERNS = (
    (r"aviso impreso", "dollar_listing"),
    (r"precio de compra es un d[oó]lar", "dollar_listing"),
    (r"otro firma igual|contrato fino", "signing_acquisition"),
    (r"manojo de llaves", "utilero_keys"),
    (r"al fondo, la cancha vac[ií]a", "first_entrance"),
    (r"llavero del estadio|badge sobre el escritorio|pas[aá]s el molinete", "quit_job"),
    (r"mudan las cajas|cuatro cuadras de la arena", "moving_home"),
    (r"familia del jefe|padres suben", "parents_box"),
    (r"^sold out\.?$", "sold_out_reveal"),
    (r"oferta de adquisici[oó]n", "acquisition_email"),
    (r"bloqueas el tel[eé]fono", "acquisition_email"),
)


def load_raw_visual_plan(project_id: str) -> dict[str, Any]:
    path = project_dir(project_id) / "flow-pack" / "visual-plan.json"
    if not path.is_file():
        raise FileNotFoundError("visual-plan.json missing")
    return json.loads(path.read_text(encoding="utf-8"))


def _lock_key(visual: dict[str, Any]) -> str:
    m = re.search(r"Location lock: (\w+)", str(visual.get("continuity_notes") or ""))
    return (m.group(1) if m else "") or "city"


def _family(location: str) -> str:
    loc = (location or "city").strip().lower()
    return LOCATION_FAMILIES.get(loc, loc if loc in ("office", "home", "arena", "city") else "city")


def _exact_location(visual: dict[str, Any]) -> str:
    key = _lock_key(visual)
    mapping = {
        "office": "cubicle",
        "shared_apt": "shared_apartment",
        "new_apt": "new_apartment",
        "locker": "locker_room",
        "arena": "arena",
        "meeting": "owner_office",
        "city": "city",
    }
    text = _low(visual)
    if "t[uú]nel" in text or "tunel" in text:
        return "arena_tunnel"
    if "cancha" in text or "baseline" in text:
        return "court"
    if "grada" in text or "sold out" in text:
        return "stands"
    if key == "office" and "dueño" in text:
        return "owner_office"
    return mapping.get(key, key)


def _low(visual: dict[str, Any] | str) -> str:
    if isinstance(visual, str):
        return visual.lower()
    return " ".join(
        str(visual.get(k) or "")
        for k in ("script_text", "narration_segment", "narration", "action", "protagonist_state")
    ).lower()


def _hero_id(visual: dict[str, Any] | str) -> str | None:
    text = visual if isinstance(visual, str) else str(visual.get("script_text") or visual.get("narration") or "")
    text = text.strip()
    for pat, hid in _HERO_PATTERNS:
        if re.search(pat, text, re.I | re.M):
            return hid
    return None


def infer_era(visual: dict[str, Any]) -> str:
    age = int(visual.get("protagonist_age") or 22)
    state = str(visual.get("protagonist_state") or "").lower()
    text = _low(visual)
    loc = _lock_key(visual)
    if "not yet owner" in state or (age == 22 and loc in ("office", "shared_apt", "city") and not re.search(r"51|dueño|llaves|utilero", text)):
        if re.search(r"51%|cincuenta y uno|precio de compra|inversores|un d[oó]lar", text):
            return "pre_owner"
        return "ordinary_life"
    if age == 22:
        if re.search(r"llaves|utilero|entras a tu estadio", text):
            return "early_owner"
        if "oficina" in text or loc == "office":
            return "struggling_owner"
        return "early_owner"
    if age == 23:
        if re.search(r"badge|renuncia|molinete", text):
            return "growing_owner"
        return "struggling_owner"
    if age == 25:
        return "growing_owner"
    if age == 26:
        return "established_owner"
    return "late_story"


def infer_mood_function(visual: dict[str, Any]) -> tuple[str, str, str]:
    text = _low(visual)
    n = int(visual.get("number") or 0)
    if re.search(r"oferta|bloqueas|mañana lo lees|vac[ií]o despu[eé]s", text):
        return "reflection", "ending", "medium"
    if re.search(r"sold out|no entra m[aá]s", text):
        return "glory", "payoff", "high"
    if re.search(r"padres|palco|familia del jefe", text):
        return "happiness", "reward", "medium"
    if re.search(r"mudan las cajas|es tuyo", text) and "penthouse" not in text:
        return "progress", "reward", "medium"
    if re.search(r"badge|renuncia|molinete", text):
        return "determination", "commitment", "high"
    if re.search(r"utilero|llaves|jefe", text):
        return "hope", "payoff", "high"
    if re.search(r"51%|cincuenta y uno|precio de compra|firm", text):
        return "opportunity", "commitment", "high"
    if re.search(r"un d[oó]lar|aviso|seiscientos cincuenta", text):
        return "curiosity", "opportunity", "medium"
    if re.search(r"inyectas|cuenta personal queda en cero|deuda|acreedor|pr[eé]stamo", text):
        return "pressure", "crisis", "medium" if "quiebra" not in text else "high"
    if re.search(r"se pierde|eliminado|no hay anillo|cero campeonatos|14-18", text):
        return "failure", "setback", "medium"
    if re.search(r"playoff|final|primera victoria|19-13", text):
        return "progress", "proof", "medium"
    if re.search(r"millones|excel|papel", text) and re.search(r"cero|nada|cena", text):
        return "wealth", "reflection", "medium"
    if re.search(r"oficina|cub[ií]culo|colectivo", text):
        return "neutral", "setup" if n <= 8 else "progress", "low"
    if re.search(r"tienes 22|compartes departamento", text):
        return "neutral", "setup", "low"
    return "tension", "progress", "low"


def infer_subject_action(visual: dict[str, Any]) -> tuple[str, str]:
    text = _low(visual)
    if re.search(r"tel[eé]fono|correo|app del banco", text):
        return "phone", "reading"
    if re.search(r"contrato|carpeta|excel|aviso|document", text):
        return "documents", "reading"
    if re.search(r"padres|familia", text):
        return "family", "watching"
    if re.search(r"utilero", text):
        return "protagonist", "waiting"
    if re.search(r"sold out|gradas|asistencia|p[uú]blico", text):
        return "crowd", "watching"
    if re.search(r"cajas|mud", text):
        return "protagonist", "moving"
    if re.search(r"firm|51|inversores|reuni", text):
        return "documents", "signing"
    if re.search(r"entrenador|coach|interino", text):
        return "coach", "training"
    if re.search(r"estadio|t[uú]nel|cancha|arena", text):
        return "arena", "watching"
    if re.search(r"colectivo|avenida|ciudad", text):
        return "city", "walking"
    return "protagonist", "thinking"


def infer_states(visual: dict[str, Any], era: str) -> dict[str, str]:
    text = _low(visual)
    crowd = "empty"
    if re.search(r"sold out|no entra", text):
        crowd = "sold_out"
    elif re.search(r"lleno|cuatro mil|4800|primera vez no ves huecos", text):
        crowd = "full"
    elif re.search(r"asistencia|tres mil|menos huecos|vivo", text):
        crowd = "filling"
    elif re.search(r"620|seiscientas veinte|vac[ií]o|huecos", text):
        crowd = "sparse"
    wealth = "employee"
    if re.search(r"millonario|45|noventa millones|papel", text):
        wealth = "paper_rich"
    if re.search(r"cero en el bolsillo|cuenta personal|cinco mil", text):
        wealth = "cash_poor"
    biz = "pre_acquisition"
    if era in ("ordinary_life", "pre_owner"):
        biz = "pre_acquisition"
    elif era in ("early_owner", "struggling_owner"):
        biz = "debt_risk"
    else:
        biz = "healthy"
    return {"crowd_state": crowd, "wealth_state": wealth, "business_state": biz}


def slot_semantics(visual: dict[str, Any]) -> dict[str, Any]:
    n = int(visual.get("number") or 0)
    age = int(visual.get("protagonist_age") or 22)
    loc_key = _lock_key(visual)
    exact = _exact_location(visual)
    family = _family(loc_key if loc_key != "locker" else "locker")
    if loc_key == "locker":
        family = "arena"
        exact = exact if exact != "arena" else "locker_room"
    era = infer_era(visual)
    mood, fn, intensity = infer_mood_function(visual)
    subject, action = infer_subject_action(visual)
    states = infer_states(visual, era)
    text = _low(visual)
    hero = _hero_id(visual)
    is_hero = bool(hero)
    ambient = family in ("city",) or subject in ("city", "environment") or action == "walking" and subject == "city"
    reusable = (not is_hero) and mood not in ("glory",) and fn not in ("ending",)
    max_reuse = 1 if is_hero else (AMBIENT_MAX_REUSE if ambient else DEFAULT_MAX_REUSE)
    return {
        "slot": n,
        "mood": mood,
        "story_function": fn,
        "intensity": intensity,
        "location": exact,
        "location_family": family,
        "protagonist_era": era,
        "protagonist_age": age,
        "visual_subject": subject,
        "action_family": action,
        "crowd_state": states["crowd_state"],
        "wealth_state": states["wealth_state"],
        "business_state": states["business_state"],
        "reusable": reusable,
        "reuse_priority": "low" if is_hero else ("high" if ambient or intensity == "low" else "medium"),
        "hero_shot": is_hero,
        "hero_id": hero,
        "support_shot": not is_hero,
        "must_have_unique_asset": is_hero,
        "max_reuse_count": max_reuse,
        "minimum_reuse_distance": 1 if is_hero else MIN_DISTANCE,
        "primary_asset": f"still_{n:03d}",
    }


def annotate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    visuals = plan.get("visuals") or []
    semantics = []
    for v in visuals:
        sem = slot_semantics(v)
        v["scene_semantics"] = sem
        v["primary_asset"] = sem["primary_asset"]
        v["hero_shot"] = sem["hero_shot"]
        v["support_shot"] = sem["support_shot"]
        v["must_have_unique_asset"] = sem["must_have_unique_asset"]
        semantics.append(sem)
    plan["scene_semantics"] = semantics
    return plan


def _mood_score(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if b in MOOD_FORBIDDEN.get(a, set()) or a in MOOD_FORBIDDEN.get(b, set()):
        return -1.0
    if b in MOOD_NEIGHBORS.get(a, set()) or a in MOOD_NEIGHBORS.get(b, set()):
        return 0.7
    return 0.2


def _fn_score(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if b in FN_NEIGHBORS.get(a, set()) or a in FN_NEIGHBORS.get(b, set()):
        return 0.7
    return 0.15


def _int_score(a: str, b: str) -> float:
    order = {"low": 0, "medium": 1, "high": 2}
    d = abs(order.get(a, 1) - order.get(b, 1))
    return 1.0 if d == 0 else (0.55 if d == 1 else 0.15)


def _as_sem(item: dict[str, Any]) -> dict[str, Any]:
    mood = item.get("mood")
    if isinstance(mood, list):
        mood = mood[0] if mood else "neutral"
    fn = item.get("story_function") or item.get("story_functions")
    if isinstance(fn, list):
        fn = fn[0] if fn else "progress"
    out = dict(item)
    out["mood"] = mood
    out["story_function"] = fn
    out["slot"] = item.get("slot") or item.get("source_shot")
    return out


def reusable_still_brief(sem: dict[str, Any]) -> str:
    return (
        f"{sem.get('visual_subject')} {sem.get('action_family')} in {sem.get('location')}, "
        f"{sem.get('mood')} atmosphere, {sem.get('intensity')} intensity, "
        "medium cinematic shot, no specific plot numbers in frame"
    )


def hard_reject(need: dict[str, Any], have: dict[str, Any]) -> str | None:
    need, have = _as_sem(need), _as_sem(have)
    if need.get("protagonist_era") != have.get("protagonist_era"):
        # adjacent eras ok only ordinary↔pre_owner and established↔late
        pair = {need.get("protagonist_era"), have.get("protagonist_era")}
        ok = pair <= {"ordinary_life", "pre_owner"} or pair <= {"established_owner", "late_story"} or pair <= {
            "growing_owner",
            "established_owner",
        }
        if not ok:
            return "wrong protagonist era"
    if need.get("hero_shot") and have.get("slot") != need.get("slot"):
        return "hero requires unique asset"
    crowd_n, crowd_h = need.get("crowd_state"), have.get("crowd_state")
    if crowd_n == "sold_out" and crowd_h in ("empty", "sparse"):
        return "empty arena during sold-out payoff"
    if crowd_n in ("empty", "sparse") and crowd_h == "sold_out":
        return "sold-out arena during early failure"
    if need.get("location") == "new_apartment" and have.get("location") == "shared_apartment":
        return "new apartment before move"
    if have.get("location") == "new_apartment" and need.get("protagonist_era") in ("ordinary_life", "pre_owner", "early_owner"):
        return "new apartment before protagonist moves"
    if need.get("protagonist_era") in ("ordinary_life", "pre_owner") and have.get("location") in ("owner_office",):
        return "owner office while still office employee"
    if need.get("visual_subject") == "family" and have.get("visual_subject") != "family":
        if have.get("hero_id") == "parents_box" or need.get("hero_id") == "parents_box":
            return "parents present mismatch"
    if need.get("business_state") == "pre_acquisition" and have.get("business_state") == "healthy":
        return "wrong ownership stage"
    loc_ok = (
        need.get("location") == have.get("location")
        or need.get("location_family") == have.get("location_family")
    )
    if not loc_ok:
        return "impossible location"
    return None


def compatibility_score(need: dict[str, Any], have: dict[str, Any]) -> tuple[float, str]:
    need, have = _as_sem(need), _as_sem(have)
    reason = hard_reject(need, have)
    if reason:
        return 0.0, reason
    ms = _mood_score(str(need.get("mood")), str(have.get("mood")))
    if ms < 0:
        return 0.0, "incompatible mood"
    loc = 1.0 if need.get("location") == have.get("location") else 0.65
    era = 1.0 if need.get("protagonist_era") == have.get("protagonist_era") else 0.55
    subj = 1.0 if need.get("visual_subject") == have.get("visual_subject") else 0.4
    act = 1.0 if need.get("action_family") == have.get("action_family") else 0.45
    age_n, age_h = int(need.get("protagonist_age") or 0), int(have.get("protagonist_age") or 0)
    age = 1.0 if age_n == age_h else (0.6 if abs(age_n - age_h) <= 2 else 0.2)
    score = (
        WEIGHTS["mood"] * ms
        + WEIGHTS["story_function"] * _fn_score(str(need.get("story_function")), str(have.get("story_function")))
        + WEIGHTS["location"] * loc
        + WEIGHTS["era"] * era
        + WEIGHTS["subject"] * subj
        + WEIGHTS["intensity"] * _int_score(str(need.get("intensity")), str(have.get("intensity")))
        + WEIGHTS["action"] * act
        + WEIGHTS["age"] * age
    )
    why = f"mood {need.get('mood')}~{have.get('mood')} loc {need.get('location_family')} era {have.get('protagonist_era')}"
    return round(score, 3), why


def ken_burns_for_appearance(index: int) -> str:
    return ("slow_push", "slight_pan", "slow_pull")[index % 3]


def virtual_assets_from_semantics(semantics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assets = []
    for sem in semantics:
        n = int(sem["slot"])
        assets.append(
            {
                "asset_id": f"still_{n:03d}",
                "source_shot": n,
                "exists": False,
                "mood": [sem["mood"]],
                "story_functions": [sem["story_function"]],
                "intensity": sem["intensity"],
                "location": sem["location"],
                "location_family": sem["location_family"],
                "protagonist_era": sem["protagonist_era"],
                "age_range": f"{sem['protagonist_age']}-{sem['protagonist_age']}",
                "visual_subject": sem["visual_subject"],
                "action_family": sem["action_family"],
                "crowd_state": sem["crowd_state"],
                "wealth_state": sem["wealth_state"],
                "business_state": sem["business_state"],
                "reusable": sem["reusable"],
                "reuse_priority": sem["reuse_priority"],
                "hero_shot": sem["hero_shot"],
                "hero_id": sem.get("hero_id"),
                "max_reuse_count": sem["max_reuse_count"],
                "slot": n,
            }
        )
    return assets


def mark_existing_assets(project_id: str, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    images = project_dir(project_id) / "images"
    for a in assets:
        n = int(a["source_shot"])
        a["exists"] = still_file(images, n) is not None
    return assets


def plan_coverage(
    semantics: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    *,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cluster slots; heroes unique; support can share a representative still."""
    overrides = overrides or {}
    by_id = {a["asset_id"]: a for a in assets}
    heroes = [s for s in semantics if s.get("hero_shot")]
    support = [s for s in semantics if not s.get("hero_shot")]

    used_at: dict[str, list[int]] = defaultdict(list)
    assignments: list[dict[str, Any]] = []

    def can_place(asset_id: str, slot: int, sem: dict[str, Any], asset: dict[str, Any]) -> tuple[bool, str, float]:
        ov = overrides.get(str(slot)) or overrides.get(slot) or {}
        if ov.get("disable_reuse") and asset.get("source_shot") != slot:
            return False, "disable_reuse", 0.0
        if ov.get("force_asset"):
            ok = ov["force_asset"] == asset_id
            return ok, "forced" if ok else "force_mismatch", 1.0 if ok else 0.0
        if sem.get("must_have_unique_asset") and asset.get("source_shot") != slot:
            return False, "hero unique", 0.0
        score, why = compatibility_score(sem, {**asset, "slot": asset.get("source_shot")})
        appearances = used_at.get(asset_id) or []
        if appearances:
            if len(appearances) >= int(asset.get("max_reuse_count") or DEFAULT_MAX_REUSE):
                return False, "reuse budget", score
            if min(abs(slot - x) for x in appearances) < int(sem.get("minimum_reuse_distance") or MIN_DISTANCE):
                return False, "minimum spacing", score
        if not asset.get("reusable", True) and asset.get("source_shot") != slot:
            return False, "asset not reusable", score
        return True, why, score

    # Exact primary first (planned unique for every slot conceptually)
    for sem in semantics:
        slot = int(sem["slot"])
        primary = sem["primary_asset"]
        ov = overrides.get(str(slot)) or {}
        assignments.append(
            {
                "slot": slot,
                "status": "PENDING",
                "primary_asset": primary,
                "assigned_asset": None,
                "score": None,
                "reason": "",
            }
        )

    # Cluster support: greedy seeds
    ungrouped = [s for s in support]
    clusters: list[dict[str, Any]] = []
    while ungrouped:
        seed = ungrouped.pop(0)
        members = [seed]
        rest = []
        for other in ungrouped:
            sc, why = compatibility_score(other, seed)
            if sc >= AUTO_REUSE and hard_reject(other, seed) is None:
                dist_ok = all(abs(int(other["slot"]) - int(m["slot"])) >= MIN_DISTANCE for m in members)
                cap = int(seed.get("max_reuse_count") or DEFAULT_MAX_REUSE)
                if dist_ok and len(members) < cap:
                    members.append(other)
                    continue
            rest.append(other)
        ungrouped = rest
        # representative = highest reuse_priority then middle intensity
        members_sorted = sorted(members, key=lambda m: (0 if m.get("reuse_priority") == "high" else 1, int(m["slot"])))
        rep = members_sorted[0]
        clusters.append(
            {
                "id": f"g_{rep['slot']:03d}",
                "group": f"{rep['mood']}_{rep['story_function']}_{rep['location_family']}",
                "slots": [int(m["slot"]) for m in members],
                "recommended_asset": f"still_{int(rep['slot']):03d}",
                "size": len(members),
                "mood": rep["mood"],
                "story_function": rep["story_function"],
                "era": rep["protagonist_era"],
                "reusable_prompt": reusable_still_brief(rep) if len(members) >= 2 else None,
            }
        )

    must = [f"still_{int(h['slot']):03d}" for h in heroes]
    p1 = [c["recommended_asset"] for c in clusters if c["size"] >= 2]
    p2 = [c["recommended_asset"] for c in clusters if c["size"] == 1]
    unique_recommended = sorted(set(must + p1 + p2), key=lambda x: int(x.split("_")[1]))
    # P3 = none of unique if covered by p1/must only in simulation

    generate_ids = set(must + p1)  # P0+P1
    generate_p012 = set(must + p1 + p2)

    def simulate(available: set[str]) -> dict[str, Any]:
        used: dict[str, list[int]] = defaultdict(list)
        rows = []
        missing = 0
        reused = 0
        exact = 0
        review = 0
        for sem in semantics:
            slot = int(sem["slot"])
            primary = sem["primary_asset"]
            ov = overrides.get(str(slot)) or {}
            chosen = None
            status = "MISSING_VISUAL"
            score = 0.0
            reason = "no compatible generated asset"
            # exact
            if primary in available:
                asset = by_id[primary]
                chosen, status, score, reason = primary, "EXACT", 1.0, "primary asset"
                used[primary].append(slot)
                exact += 1
            else:
                best = None
                best_sc = 0.0
                best_why = "none"
                for aid in available:
                    asset = by_id[aid]
                    ok, why, sc = can_place(aid, slot, sem, asset)
                    if not ok:
                        continue
                    if sc > best_sc:
                        best, best_sc, best_why = aid, sc, why
                if best and best_sc >= AUTO_REUSE:
                    chosen, status, score, reason = best, "REUSED", best_sc, best_why
                    used[best].append(slot)
                    reused += 1
                elif best and best_sc >= REVIEW_REUSE:
                    chosen, status, score, reason = best, "REVIEW_REUSE", best_sc, best_why
                    review += 1
                else:
                    missing += 1
                    reason = f"best={best} score={best_sc:.2f} ({best_why})"
                    score = best_sc
            kb_i = len(used.get(chosen or "", [])) - 1
            rows.append(
                {
                    "slot": slot,
                    "status": status,
                    "assigned_asset": chosen,
                    "primary_asset": primary,
                    "score": score,
                    "reason": reason,
                    "ken_burns": ken_burns_for_appearance(max(0, kb_i)) if chosen else None,
                    "hero": bool(sem.get("hero_shot")),
                }
            )
        return {
            "rows": rows,
            "exact": exact,
            "reused": reused,
            "review": review,
            "missing": missing,
            "covered": exact + reused,
        }

    sim_all = simulate(generate_p012)
    sim_p01 = simulate(generate_ids)

    queue = {
        "P0": sorted(must, key=lambda x: int(x.split("_")[1])),
        "P1": sorted(set(p1), key=lambda x: int(x.split("_")[1])),
        "P2": sorted(set(p2), key=lambda x: int(x.split("_")[1])),
        "P3": [],
    }
    # P3: support cluster members not chosen as representative
    reps = set(must + p1 + p2)
    p3 = [s["primary_asset"] for s in support if s["primary_asset"] not in reps]
    queue["P3"] = p3

    return {
        "total_slots": len(semantics),
        "must_have_unique": len(must),
        "recommended_unique": len(set(must + p1 + p2)),
        "coverable_by_reuse": sim_all["reused"],
        "missing_if_all_recommended_generated": sim_all["missing"],
        "heroes": [
            {"slot": int(h["slot"]), "hero_id": h.get("hero_id"), "asset": h["primary_asset"], "script": None}
            for h in heroes
        ],
        "reuse_groups": clusters,
        "generation_queue": queue,
        "simulation_p0_p1": {
            "generated": sorted(generate_ids, key=lambda x: int(x.split("_")[1])),
            "unique_generated": len(generate_ids),
            "covered": sim_p01["covered"],
            "reused": sim_p01["reused"],
            "review": sim_p01["review"],
            "missing": sim_p01["missing"],
        },
        "simulation_recommended": {
            "unique_generated": len(set(must + p1 + p2)),
            "covered": sim_all["covered"],
            "reused": sim_all["reused"],
            "review": sim_all["review"],
            "missing": sim_all["missing"],
        },
        "slot_plan": sim_all["rows"],
        "thresholds": {"auto_reuse": AUTO_REUSE, "review_reuse": REVIEW_REUSE, "min_distance": MIN_DISTANCE},
    }


def _load_overrides(project_id: str) -> dict[str, Any]:
    path = project_dir(project_id) / "flow-pack" / "reuse-plan.json"
    if not path.is_file():
        return {}
    try:
        return dict((json.loads(path.read_text(encoding="utf-8")) or {}).get("overrides") or {})
    except Exception:
        return {}


def persist_asset_system(
    project_id: str,
    plan: dict[str, Any],
    coverage: dict[str, Any],
    assets: list[dict[str, Any]],
    *,
    overrides: dict[str, Any] | None = None,
    write_visual_plan: bool = False,
    write_semantics: bool = False,
) -> Path:
    fp = project_dir(project_id) / "flow-pack"
    fp.mkdir(parents=True, exist_ok=True)
    semantics = plan.get("scene_semantics") or []
    (fp / "asset-library.json").write_text(json.dumps({"assets": assets}, ensure_ascii=False, indent=2), encoding="utf-8")
    (fp / "asset-coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
    reuse_plan = {
        "slots": coverage.get("slot_plan") or [],
        "groups": coverage.get("reuse_groups") or [],
        "queue": coverage.get("generation_queue") or {},
        "next_queue": coverage.get("next_queue") or {},
        "reuse_reviews": coverage.get("reuse_reviews") or [],
        "overrides": overrides if overrides is not None else _load_overrides(project_id),
    }
    (fp / "reuse-plan.json").write_text(json.dumps(reuse_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if write_visual_plan:
        (fp / "visual-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if write_semantics:
        (fp / "scene-semantics.json").write_text(json.dumps(semantics, ensure_ascii=False, indent=2), encoding="utf-8")
    return fp


def production_progress(
    semantics: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    slot_plan: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Production metrics: exact stills are the goal; reuse is contingency."""
    total = len(semantics)
    imported_exact = sum(1 for a in assets if a.get("exists"))
    missing_exact = max(0, total - imported_exact)
    fb_auto = fb_review = 0
    for row in slot_plan or []:
        st = str(row.get("status") or "")
        if st == "REUSED":
            fb_auto += 1
        elif st == "REVIEW_REUSE":
            fb_review += 1
    return {
        "total_slots": total,
        "prompts_ready": total,
        "imported_exact": imported_exact,
        "generated_imported": imported_exact,
        "exact_coverage": imported_exact,
        "missing_exact_assets": missing_exact,
        "temporarily_covered_by_reuse": fb_auto + fb_review,
        "fallback_auto_reuse": fb_auto,
        "fallback_review": fb_review,
        "fallback_coverage_available": fb_auto + fb_review,
        "policy": "Each slot targets its own still. Smart reuse is fallback only.",
    }


def build_for_project(project_id: str) -> dict[str, Any]:
    plan = load_raw_visual_plan(project_id)
    plan = annotate_plan(plan)
    semantics = plan["scene_semantics"]
    # attach script snippet to heroes from visuals
    by_n = {int(v.get("number") or 0): v for v in (plan.get("visuals") or [])}
    assets = virtual_assets_from_semantics(semantics)
    assets = mark_existing_assets(project_id, assets)
    overrides = _load_overrides(project_id)
    coverage = plan_coverage(semantics, assets)
    real = match_real_coverage(semantics, assets, overrides=overrides)
    coverage["slot_plan"] = real["slot_plan"]
    coverage["real_coverage"] = real["real_coverage"]
    coverage["reuse_reviews"] = real["reuse_reviews"]
    coverage["next_queue"] = real["next_queue"]
    coverage["production_progress"] = production_progress(semantics, assets, real["slot_plan"])
    coverage["generation_order_note"] = "P0–P3 = order of generation, not permission to skip slots."
    for h in coverage["heroes"]:
        v = by_n.get(h["slot"]) or {}
        h["script"] = str(v.get("script_text") or v.get("narration") or "")[:160]
    persist_asset_system(
        project_id,
        plan,
        coverage,
        assets,
        overrides=overrides,
        write_semantics=True,
    )
    return coverage


def refresh_assets_after_import(project_id: str) -> dict[str, Any]:
    """Keep frozen semantics; match only stills that exist on disk."""
    fp = project_dir(project_id) / "flow-pack"
    sem_path = fp / "scene-semantics.json"
    plan = load_raw_visual_plan(project_id)
    if sem_path.is_file():
        semantics = json.loads(sem_path.read_text(encoding="utf-8"))
        plan["scene_semantics"] = semantics
    elif plan.get("scene_semantics"):
        semantics = plan["scene_semantics"]
    else:
        return build_for_project(project_id)
    assets = virtual_assets_from_semantics(semantics)
    assets = mark_existing_assets(project_id, assets)
    lib_path = fp / "asset-library.json"
    if lib_path.is_file():
        prev = (json.loads(lib_path.read_text(encoding="utf-8")) or {}).get("assets") or []
        flags = {a.get("asset_id"): a for a in prev}
        for a in assets:
            old = flags.get(a["asset_id"]) or {}
            if "reusable" in old:
                a["reusable"] = old["reusable"]
            if "max_reuse_count" in old:
                a["max_reuse_count"] = old["max_reuse_count"]
    overrides = _load_overrides(project_id)
    planned = {}
    cov_path = fp / "asset-coverage.json"
    if cov_path.is_file():
        try:
            planned = json.loads(cov_path.read_text(encoding="utf-8"))
        except Exception:
            planned = {}
    real = match_real_coverage(semantics, assets, overrides=overrides)
    coverage = dict(planned)
    coverage.update(real)
    coverage["production_progress"] = production_progress(semantics, assets, real["slot_plan"])
    persist_asset_system(project_id, plan, coverage, assets, overrides=overrides)
    return coverage


def apply_override(project_id: str, slot: int, *, force_asset: str | None = None, disable_reuse: bool | None = None) -> dict[str, Any]:
    fp = project_dir(project_id) / "flow-pack"
    rp_path = fp / "reuse-plan.json"
    data = json.loads(rp_path.read_text(encoding="utf-8")) if rp_path.is_file() else {"overrides": {}}
    ov = dict((data.get("overrides") or {}).get(str(slot)) or {})
    if force_asset is not None:
        ov["force_asset"] = force_asset
    if disable_reuse is not None:
        ov["disable_reuse"] = bool(disable_reuse)
    data.setdefault("overrides", {})[str(slot)] = ov
    rp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return refresh_assets_after_import(project_id)


def mark_asset_flags(
    project_id: str,
    asset_id: str,
    *,
    reusable: bool | None = None,
    max_reuse_count: int | None = None,
) -> dict[str, Any]:
    fp = project_dir(project_id) / "flow-pack"
    lib_path = fp / "asset-library.json"
    sem_path = fp / "scene-semantics.json"
    plan = load_raw_visual_plan(project_id)
    if sem_path.is_file():
        semantics = json.loads(sem_path.read_text(encoding="utf-8"))
    else:
        semantics = plan.get("scene_semantics") or []
    assets = virtual_assets_from_semantics(semantics)
    assets = mark_existing_assets(project_id, assets)
    if lib_path.is_file():
        prev = (json.loads(lib_path.read_text(encoding="utf-8")) or {}).get("assets") or []
        flags = {a.get("asset_id"): a for a in prev}
        for a in assets:
            old = flags.get(a["asset_id"]) or {}
            if "reusable" in old:
                a["reusable"] = old["reusable"]
            if "max_reuse_count" in old:
                a["max_reuse_count"] = old["max_reuse_count"]
    for a in assets:
        if a["asset_id"] != asset_id:
            continue
        if reusable is not None:
            a["reusable"] = bool(reusable)
        if max_reuse_count is not None:
            a["max_reuse_count"] = max(1, int(max_reuse_count))
    lib_path.write_text(json.dumps({"assets": assets}, ensure_ascii=False, indent=2), encoding="utf-8")
    return refresh_assets_after_import(project_id)


_RETENTION_FN = {
    "climax": 5,
    "payoff": 5,
    "crisis": 4,
    "commitment": 4,
    "ending": 4,
    "opportunity": 3,
    "loss": 3,
    "setback": 3,
    "escalation": 3,
    "progress": 2,
    "proof": 2,
    "reward": 2,
    "setup": 1,
}


def match_real_coverage(
    semantics: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    *,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assign slots using only assets that exist. Same scores/thresholds as the matcher."""
    overrides = overrides or {}
    by_id = {a["asset_id"]: a for a in assets}
    available = {a["asset_id"] for a in assets if a.get("exists")}
    used: dict[str, list[int]] = defaultdict(list)
    rows: list[dict[str, Any]] = []
    exact = reused = review = missing = 0

    def eligible(asset_id: str, slot: int, sem: dict[str, Any], asset: dict[str, Any]) -> tuple[bool, str, float]:
        ov = overrides.get(str(slot)) or overrides.get(slot) or {}
        if ov.get("disable_reuse") and asset.get("source_shot") != slot:
            return False, "disable_reuse", 0.0
        if ov.get("force_asset"):
            ok = ov["force_asset"] == asset_id
            return ok, "forced" if ok else "force_mismatch", 1.0 if ok else 0.0
        if sem.get("must_have_unique_asset") and int(asset.get("source_shot") or 0) != slot:
            return False, "hero unique", 0.0
        score, why = compatibility_score(sem, {**asset, "slot": asset.get("source_shot")})
        appearances = used.get(asset_id) or []
        if appearances:
            if len(appearances) >= int(asset.get("max_reuse_count") or DEFAULT_MAX_REUSE):
                return False, "reuse budget", score
            if min(abs(slot - x) for x in appearances) < int(sem.get("minimum_reuse_distance") or MIN_DISTANCE):
                return False, "minimum spacing", score
        if not asset.get("reusable", True) and int(asset.get("source_shot") or 0) != slot:
            return False, "asset not reusable", score
        return True, why, score

    for sem in semantics:
        slot = int(sem["slot"])
        primary = sem["primary_asset"]
        chosen = None
        status = "MISSING_VISUAL"
        score = 0.0
        reason = "no existing compatible asset"
        if primary in available:
            chosen, status, score, reason = primary, "EXACT", 1.0, "primary asset"
            used[primary].append(slot)
            exact += 1
        else:
            best = None
            best_sc = 0.0
            best_why = "none"
            for aid in available:
                asset = by_id[aid]
                ok, why, sc = eligible(aid, slot, sem, asset)
                if not ok:
                    continue
                if sc > best_sc:
                    best, best_sc, best_why = aid, sc, why
            if best and best_sc >= AUTO_REUSE:
                chosen, status, score, reason = best, "REUSED", best_sc, best_why
                used[best].append(slot)
                reused += 1
            elif best and best_sc >= REVIEW_REUSE:
                chosen, status, score, reason = best, "REVIEW_REUSE", best_sc, best_why
                used[best].append(slot)
                review += 1
            else:
                missing += 1
                reason = f"best={best} score={best_sc:.2f} ({best_why})"
                score = best_sc
        kb_i = len(used.get(chosen or "", [])) - 1
        prev = [x for x in (used.get(chosen) or []) if x != slot]
        dist = min((abs(slot - x) for x in prev), default=None)
        rows.append(
            {
                "slot": slot,
                "status": status,
                "assigned_asset": chosen,
                "primary_asset": primary,
                "score": score,
                "reason": reason,
                "ken_burns": ken_burns_for_appearance(max(0, kb_i)) if chosen else None,
                "hero": bool(sem.get("hero_shot")),
                "reuse_count": len(used.get(chosen or "", [])),
                "distance": dist,
            }
        )

    reviews = []
    for row in rows:
        if row["status"] not in ("REUSED", "REVIEW_REUSE"):
            continue
        reviews.append(
            {
                "source_asset": row["assigned_asset"],
                "target_slot": row["slot"],
                "reuse_score": row["score"],
                "semantic_reason": row["reason"],
                "reuse_count": row.get("reuse_count"),
                "distance": row.get("distance"),
                "visual_quality": "UNREVIEWED",
                "status": row["status"],
            }
        )

    next_queue = (
        build_next_generation_queue(semantics, rows, assets)
        if available
        else {
            "NEXT_REQUIRED": [],
            "NEXT_RECOMMENDED": [],
            "OPTIONAL": [],
            "note": "Import exact stills (NNN.png). Fallback reuse applies only while an exact asset is missing.",
        }
    )

    total_slots = len(semantics)
    missing_exact_assets = max(0, total_slots - len(available))

    return {
        "real_coverage": {
            "imported_unique": len(available),
            "imported_exact": len(available),
            "EXACT": exact,
            "AUTO_REUSE": reused,
            "REVIEW_REUSE": review,
            "MISSING": missing,
            "missing_exact_assets": missing_exact_assets,
        },
        "slot_plan": rows,
        "reuse_reviews": reviews,
        "next_queue": next_queue,
        "production_progress": production_progress(semantics, assets, rows),
    }


def build_next_generation_queue(
    semantics: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    assets: list[dict[str, Any]],
) -> dict[str, Any]:
    by_slot = {int(s["slot"]): s for s in semantics}
    missing_sems = [by_slot[int(r["slot"])] for r in rows if r.get("status") == "MISSING_VISUAL" and int(r["slot"]) in by_slot]
    existing_keys = {
        (a.get("location_family"), (a.get("mood") or [None])[0] if isinstance(a.get("mood"), list) else a.get("mood"))
        for a in assets
        if a.get("exists")
    }

    ungrouped = list(missing_sems)
    clusters: list[list[dict[str, Any]]] = []
    while ungrouped:
        seed = ungrouped.pop(0)
        members = [seed]
        rest = []
        for other in ungrouped:
            sc, _why = compatibility_score(other, seed)
            if sc >= AUTO_REUSE and hard_reject(other, seed) is None:
                dist_ok = all(abs(int(other["slot"]) - int(m["slot"])) >= MIN_DISTANCE for m in members)
                cap = int(seed.get("max_reuse_count") or DEFAULT_MAX_REUSE)
                if dist_ok and len(members) < cap:
                    members.append(other)
                    continue
            rest.append(other)
        ungrouped = rest
        clusters.append(members)

    scored = []
    for members in clusters:
        rep = sorted(members, key=lambda m: int(m["slot"]))[0]
        variety = 0 if (rep.get("location_family"), rep.get("mood")) in existing_keys else 1
        retention = _RETENTION_FN.get(str(rep.get("story_function") or ""), 1)
        hero = 1 if rep.get("hero_shot") or rep.get("must_have_unique_asset") else 0
        size = len(members)
        rank = hero * 1000 + 100 + size * 10 + variety * 5 + retention
        scored.append(
            {
                "asset": rep["primary_asset"],
                "slot": int(rep["slot"]),
                "covers": [int(m["slot"]) for m in members],
                "hero": bool(hero),
                "potentially_covered": size,
                "variety_new": bool(variety),
                "retention": retention,
                "rank": rank,
            }
        )
    scored.sort(key=lambda x: (-x["rank"], x["slot"]))

    required = [x for x in scored if x["hero"] or x["potentially_covered"] >= 2]
    recommended = [x for x in scored if not (x["hero"] or x["potentially_covered"] >= 2)]
    optional = [
        {
            "slot": int(r["slot"]),
            "source_asset": r.get("assigned_asset"),
            "score": r.get("score"),
            "note": "REVIEW_REUSE — generate only if the human rejects the still",
        }
        for r in rows
        if r.get("status") == "REVIEW_REUSE"
    ]
    return {
        "NEXT_REQUIRED": required,
        "NEXT_RECOMMENDED": recommended,
        "OPTIONAL": optional,
    }
