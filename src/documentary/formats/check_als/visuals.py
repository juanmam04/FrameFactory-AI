"""Check ALS visual layer: 2D cinematic illustrated stills + locked bibles. Prompts only."""
from __future__ import annotations

import json
import re
from typing import Any

from src.documentary.formats.check_als.editorial import VISUAL_DIRECTION, VISUAL_STYLE_ID
from src.documentary.project import project_dir

CHECK_STYLE = (
    "2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, "
    "clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. "
    "Not anime, not clipart, not stock-photo look, not hyperrealistic random humans."
)

PROTAGONIST_BIBLE = (
    "Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, "
    "readable eyes, clean linework, not a model, not a cartoon mascot. "
    "Age 22: cheap office collared shirt, dark trousers, worn backpack. "
    "After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. "
    "Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. "
    "Never swap ethnicity, never redesign the face."
)

ARENA_BIBLE = (
    "Same municipal basketball arena throughout: brick exterior, faded 'Halcones' sign, 4800-seat bowl, "
    "same roof shape, same tunnel to the court, same floor orientation. "
    "Early: peeling paint, empty stands, yellowed lights, water stains, old wood floor. "
    "Later: same architecture, better lighting, fresh paint, packed then sold-out stands. "
    "The building evolves; it does not become a different NBA arena."
)

OFFICE_BIBLE = (
    "Dull corporate cubicle farm: gray partitions, fluorescent lights, cheap LCD, a sad plant, plastic badge. "
    "Not WeWork, not glass startup HQ."
)

SHARED_APT_BIBLE = (
    "Small shared apartment: two roommates' clutter, cheap furniture, a basketball poster, city night "
    "through a small window. Modest, lived-in, not luxury."
)

NEW_APT_BIBLE = (
    "Simple one-bedroom of his own, four blocks from the arena: moving boxes, a window that can see arena lights "
    "at night. Modest upgrade, not a penthouse."
)

TEAM_BIBLE = (
    "Los Halcones de la Ciudad: dark green and copper-gold, hawk mark on jerseys. Worn kits early, cleaner later. "
    "Same uniform identity across years."
)

COACH_BIBLE = (
    "Head coach, early 50s, short gray-brown hair, sideline jacket, clipboard. Same man once hired. "
    "Interim coach (if shown earlier) is a different, older, less sharp staffer."
)

UTILERO_BIBLE = (
    "Older stadium equipment man, about 60, keys on a ring, faded staff polo, practical shoes. Recurring extra."
)

CHECK_CHARACTERS = [
    {
        "id": "CHAR_YOU",
        "name": "YOU",
        "description": PROTAGONIST_BIBLE,
        "visual_description": PROTAGONIST_BIBLE,
        "reference_required": True,
    },
    {
        "id": "CHAR_UTILERO",
        "name": "equipment manager",
        "description": UTILERO_BIBLE,
        "visual_description": UTILERO_BIBLE,
        "reference_required": True,
    },
    {
        "id": "CHAR_COACH",
        "name": "head coach",
        "description": COACH_BIBLE,
        "visual_description": COACH_BIBLE,
        "reference_required": True,
    },
]

CHECK_LOCATIONS = [
    {
        "id": "LOC_OFFICE",
        "name": "corporate cubicle office",
        "description": OFFICE_BIBLE,
        "visual_description": OFFICE_BIBLE,
        "reference_required": True,
    },
    {
        "id": "LOC_SHARED_APT",
        "name": "shared apartment",
        "description": SHARED_APT_BIBLE,
        "visual_description": SHARED_APT_BIBLE,
        "reference_required": True,
    },
    {
        "id": "LOC_ARENA",
        "name": "Halcones municipal arena",
        "description": ARENA_BIBLE,
        "visual_description": ARENA_BIBLE,
        "reference_required": True,
    },
    {
        "id": "LOC_NEW_APT",
        "name": "own apartment near arena",
        "description": NEW_APT_BIBLE,
        "visual_description": NEW_APT_BIBLE,
        "reference_required": True,
    },
    {
        "id": "LOC_LOCKER",
        "name": "Halcones locker room",
        "description": (
            "Same locker room throughout: old green metal lockers early, later a cleaner coat of paint "
            "and better lighting but the same room geometry."
        ),
        "visual_description": "old municipal locker room that slowly improves, same room",
        "reference_required": True,
    },
]


def check_visual_bibles() -> dict[str, str]:
    return {
        "protagonist_visual_bible": PROTAGONIST_BIBLE,
        "arena_visual_bible": ARENA_BIBLE,
        "office_visual_bible": OFFICE_BIBLE,
        "shared_apartment_visual_bible": SHARED_APT_BIBLE,
        "new_apartment_visual_bible": NEW_APT_BIBLE,
        "team_visual_bible": TEAM_BIBLE,
        "coach_visual_bible": COACH_BIBLE,
        "utilero_visual_bible": UTILERO_BIBLE,
        "style": CHECK_STYLE,
        "style_id": VISUAL_STYLE_ID,
        "visual_direction": VISUAL_DIRECTION,
    }


def _low(text: str) -> str:
    return (text or "").lower()


def infer_story_time(text: str, index: int, total: int) -> dict[str, Any]:
    t = _low(text)
    frac = index / max(1, total)
    age = 22
    season = 1
    state = "office employee, shared apartment"
    if "27 años" in t or "veintisiete" in t or frac > 0.88:
        age = 27
        season = 6
        state = "owner, paper millionaire, empty arena"
    elif "26 años" in t or frac > 0.72:
        age = 26
        season = 5
        state = "full-time owner, sold-out arena"
    elif "25 años" in t or "mud" in t or frac > 0.58:
        age = 25
        season = 4
        state = "owner moving into own apartment"
    elif "renuncia" in t or "badge" in t or frac > 0.42:
        age = 23
        season = 3
        state = "quitting the office job"
    elif "playoff" in t or "final" in t or frac > 0.28:
        age = 22
        season = 1
        state = "first-year owner in playoffs"
    elif "51" in t or "firm" in t or "dueño" in t or "utilero" in t or "llaves" in t:
        age = 22
        season = 1
        state = "new 51% owner entering the arena"
    elif "oficina" in t or "departamento compart" in t or frac < 0.12:
        age = 22
        season = 0
        state = "office, shared apartment, not yet owner"
    loc_key = infer_location_key(t)
    if loc_key == "office":
        age = min(age, 23)
    return {
        "story_time": f"AGE {age}" + (f" · season {season}" if season else ""),
        "protagonist_age": age,
        "protagonist_state": state,
        "season": season,
        "location_key": loc_key,
    }


def infer_location_key(text: str) -> str:
    t = _low(text)
    if any(k in t for k in ("cubicle", "oficina", "badge", "escritorio", "renuncia")) and "estadio" not in t:
        return "office"
    if any(k in t for k in ("compart", "roommates", "roommate", "departamento compart")):
        return "shared_apt"
    if any(k in t for k in ("cajas", "mud", "departamento propio", "cuatro cuadras")):
        return "new_apt"
    if any(k in t for k in ("vestuario", "locker", "utilero", "llaves")):
        return "locker"
    if any(k in t for k in ("túnel", "tunel", "grada", "estadio", "arena", "sold out", "playoff", "cancha")):
        return "arena"
    if any(k in t for k in ("reunión", "reunion", "inversores", "vendedor", "contrato")):
        return "meeting"
    return "arena" if "halcon" in t else "city"


def location_from_key(key: str, age: int, attendance_hint: str) -> str:
    arena_state = ARENA_BIBLE
    if age <= 22 and key == "arena":
        arena_state = (
            "Run-down municipal Halcones arena: empty or sparse stands (~620 early, later filling), "
            "yellowed lights, peeling paint. SAME building as later sold-out years. " + ARENA_BIBLE
        )
    elif key == "arena" and ("sold" in attendance_hint or age >= 23):
        arena_state = (
            "Same Halcones municipal arena now packed toward 4800 capacity, stronger lights, "
            "same architecture. " + ARENA_BIBLE
        )
    mapping = {
        "office": OFFICE_BIBLE,
        "shared_apt": SHARED_APT_BIBLE,
        "new_apt": NEW_APT_BIBLE,
        "locker": "Halcones locker room. " + TEAM_BIBLE,
        "arena": arena_state,
        "meeting": "A tired conference room or a cheap cafe booth in Ciudad Central, not a glass boardroom.",
        "city": "Night streets of a mid-size fictional city near the municipal arena.",
    }
    return mapping.get(key, arena_state)


def characters_for(key: str, text: str) -> list[str]:
    names = ["YOU (protagonist)"]
    t = _low(text)
    if "utilero" in t or "llaves" in t or "jefe" in t:
        names.append("equipment manager")
    if "entrenador" in t or "coach" in t:
        names.append("head coach")
    if "sponsor" in t or "empresario" in t or "logo" in t:
        names.append("local businessman")
    if "padres" in t or "mamá" in t or "papá" in t:
        names.append("parents")
    if key == "office" and "renuncia" not in t:
        names.append("office coworkers as background silhouettes")
    return names


def compose_image_prompt(visual: dict[str, Any], meta: dict[str, Any]) -> str:
    action = str(visual.get("action") or visual.get("description") or "the protagonist in a specific story beat").strip()
    camera = str(visual.get("camera") or visual.get("shot_type") or "medium shot").strip()
    lighting = str(visual.get("lighting") or "cinematic motivated light").strip()
    composition = str(visual.get("composition") or "16:9, subject off-center, strong depth, readable silhouette").strip()
    loc = str(visual.get("environment") or visual.get("location") or "").strip()
    age = meta.get("protagonist_age") or 22
    state = meta.get("protagonist_state") or ""
    story_time = meta.get("story_time") or f"AGE {age}"
    objects = visual.get("important_objects") or []
    obj_line = ", ".join(str(x) for x in objects) if objects else "story-specific props only"
    fg = str(visual.get("foreground") or "").strip()
    bg = str(visual.get("background") or "").strip()
    if fg or bg:
        composition = (
            f"{composition} Foreground: {fg or 'readable silhouette'}. "
            f"Background: {bg or 'deep environment'}."
        )
    wardrobe = "Wardrobe matches age/state from the protagonist bible."
    if int(age or 22) == 22 and "not yet owner" in str(state or ""):
        wardrobe = (
            "AGE 22 wardrobe only: cheap office collared shirt, dark trousers, worn backpack. No team jacket."
        )
    return (
        f"{CHECK_STYLE}\n"
        f"STYLE LOCK (Check): {VISUAL_DIRECTION}\n"
        f"EXACT CHARACTER: {PROTAGONIST_BIBLE} Age now: {age}. State: {state}. {wardrobe}\n"
        f"EXACT ACTION: {action}\n"
        f"EXACT ENVIRONMENT: {loc}\n"
        f"STORY TIME: {story_time}\n"
        f"CAMERA: {camera}\n"
        f"COMPOSITION: {composition}\n"
        f"LIGHTING: {lighting}\n"
        f"IMPORTANT OBJECTS: {obj_line}\n"
        f"CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. "
        f"{wardrobe} Do not invent a new man or a new building.\n"
        f"AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks."
    )


def format_check_prompt(visual: dict[str, Any], bible: dict[str, Any] | None = None) -> str:
    meta = {
        "protagonist_age": visual.get("protagonist_age"),
        "protagonist_state": visual.get("protagonist_state"),
        "story_time": visual.get("story_time"),
    }
    return compose_image_prompt(visual, meta)


def apply_check_visual_layer(project: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    visuals = list(plan.get("visuals") or [])
    total = max(1, len(visuals))
    bibles = check_visual_bibles()
    bible = dict(plan.get("visual_bible") or {})
    bible["global_style"] = CHECK_STYLE
    bible["format"] = "check_als"
    bible["style_id"] = VISUAL_STYLE_ID
    bible["check_bibles"] = bibles
    bible["characters"] = _merge_ents(CHECK_CHARACTERS, bible.get("characters") or [])
    bible["locations"] = _merge_ents(CHECK_LOCATIONS, bible.get("locations") or [])

    seen_prompts: dict[str, int] = {}
    scenes: list[dict[str, Any]] = []
    for i, v in enumerate(visuals, start=1):
        narr = str(v.get("narration_segment") or v.get("narration") or v.get("script_text") or "").strip()
        meta = infer_story_time(narr + " " + str(v.get("action") or ""), i, total)
        loc_key = meta["location_key"]
        env = location_from_key(loc_key, int(meta["protagonist_age"]), narr)
        chars = characters_for(loc_key, narr)
        objects = _objects_for(loc_key, narr)
        lighting = _lighting_for(loc_key, narr)
        composition = "16:9 widescreen, strong foreground/midground/background, one clear subject"
        v["scene_id"] = v.get("scene_id") or v.get("visual_id") or f"V{i:03d}"
        v["script_text"] = narr
        v["story_time"] = meta["story_time"]
        v["duration_target"] = int(v.get("duration_target") or 7)
        v["location"] = env[:180]
        v["environment"] = env
        v["characters"] = chars
        v["action"] = str(v.get("action") or v.get("description") or "protagonist in this beat").strip()
        v["emotion"] = v.get("emotion") or _emotion_for(narr)
        v["protagonist_age"] = meta["protagonist_age"]
        v["protagonist_state"] = meta["protagonist_state"]
        v["camera"] = v.get("camera") or v.get("shot_type") or "medium shot"
        v["shot_type"] = v.get("shot_type") or v.get("camera") or "medium_shot"
        v["composition"] = composition
        v["lighting"] = lighting
        v["important_objects"] = objects
        v["continuity_notes"] = (
            f"Reuse protagonist CHAR_YOU. Location lock: {loc_key}. "
            f"Arena architecture constant. Age {meta['protagonist_age']}."
        )
        prompt = compose_image_prompt(v, meta)
        sig = re.sub(r"\s+", " ", (v.get("action") or "")[:80] + loc_key)
        reuse = seen_prompts.get(sig)
        if reuse and abs(reuse - i) <= 2:
            v["reuse_of"] = reuse
        else:
            seen_prompts[sig] = i
        v["image_prompt"] = prompt
        v["flow_prompt"] = prompt
        v["prompt"] = prompt
        scenes.append(
            {
                "scene_id": v["scene_id"],
                "script_text": v["script_text"],
                "story_time": v["story_time"],
                "duration_target": v["duration_target"],
                "location": v["location"],
                "characters": v["characters"],
                "action": v["action"],
                "emotion": v["emotion"],
                "protagonist_age": v["protagonist_age"],
                "protagonist_state": v["protagonist_state"],
                "camera": v["camera"],
                "shot_type": v["shot_type"],
                "composition": v["composition"],
                "lighting": v["lighting"],
                "important_objects": v["important_objects"],
                "continuity_notes": v["continuity_notes"],
                "image_prompt": v["image_prompt"],
                "reuse_of": v.get("reuse_of"),
            }
        )

    plan["visuals"] = visuals
    plan["visual_bible"] = bible
    plan["check_bibles"] = bibles
    plan["image_prompts"] = scenes
    stats = dict(plan.get("stats") or {})
    stats["scene_count"] = len(scenes)
    stats["unique_locations"] = sorted({s.get("continuity_notes", "").split("Location lock: ")[-1].split(".")[0] for s in scenes})
    stats["characters"] = sorted({c for s in scenes for c in (s.get("characters") or [])})
    stats["timeline"] = sorted({s.get("story_time") for s in scenes if s.get("story_time")})
    plan["stats"] = stats
    plan["qc"] = _visual_qc(scenes)
    for b in plan.get("flow_batches") or []:
        nums = b.get("visual_numbers") or []
        parts = []
        for n in nums[:2]:
            hit = next((x for x in visuals if int(x.get("number") or 0) == int(n)), None)
            if hit and hit.get("image_prompt"):
                parts.append(str(hit["image_prompt"])[:500])
        if parts:
            b["prompt"] = CHECK_STYLE + "\n\n" + "\n---\n".join(parts)
    _persist_prompts(project, plan, scenes)
    return plan


def _merge_ents(locked: list[dict[str, Any]], existing: list[Any]) -> list[dict[str, Any]]:
    out = list(locked)
    seen = {str(e.get("id") or e.get("name") or "").lower() for e in out}
    for e in existing:
        if not isinstance(e, dict):
            continue
        key = str(e.get("id") or e.get("name") or "").lower()
        if key and key not in seen:
            out.append(e)
            seen.add(key)
    return out


def _objects_for(key: str, text: str) -> list[str]:
    t = _low(text)
    objs: list[str] = []
    if "llaves" in t:
        objs.append("ring of old arena keys")
    if "badge" in t or "renuncia" in t:
        objs.append("plastic office badge on a desk")
    if "teléfono" in t or "telefono" in t or "correo" in t or "oferta" in t:
        objs.append("smartphone with an email on screen, unreadable tiny type")
    if "un dólar" in t or "un dolar" in t or "$1" in text:
        objs.append("cheap printed sale notice / one-dollar figure on paper")
    if key == "office":
        objs.extend(["cubicle monitor", "sad plant"])
    if key == "arena":
        objs.append("Halcones hawk mark")
    if key == "new_apt":
        objs.append("moving boxes")
    return objs[:6]


def _lighting_for(key: str, text: str) -> str:
    t = _low(text)
    if "noche" in t or "vacío" in t or "vacio" in t:
        return "empty-arena practicals, long shadows, quiet night"
    if key == "office":
        return "harsh fluorescent cubicle light"
    if key == "shared_apt":
        return "cheap lamp + city window night"
    if "playoff" in t or "sold" in t:
        return "harder game lights, crowd glow"
    return "cinematic motivated light, strong depth"


def _emotion_for(text: str) -> str:
    t = _low(text)
    if "oferta" in t or "vacío" in t or "vacio" in t:
        return "quiet, unresolved"
    if "renuncia" in t:
        return "decisive, small"
    if "sold" in t or "lleno" in t:
        return "crowded heat"
    if "deuda" in t or "derrota" in t:
        return "pressure"
    if "llaves" in t or "jefe" in t:
        return "disbelief made physical"
    return "lived-in"


def _visual_qc(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    loc_keys = []
    for s in scenes:
        notes = str(s.get("continuity_notes") or "")
        m = re.search(r"Location lock: (\w+)", notes)
        loc_keys.append(m.group(1) if m else "")
    needed = ["office", "shared_apt", "arena", "locker", "new_apt"]
    missing = [k for k in needed if k not in loc_keys]
    repeats = 0
    for i in range(1, len(scenes)):
        if scenes[i].get("action") == scenes[i - 1].get("action") and scenes[i].get("location") == scenes[i - 1].get("location"):
            repeats += 1
    generic = [s["scene_id"] for s in scenes if "young entrepreneur" in _low(s.get("image_prompt") or "")]
    return {
        "scene_count": len(scenes),
        "missing_visual_coverage": missing,
        "consecutive_repeat_pairs": repeats,
        "generic_prompts": generic,
        "has_office": "office" in loc_keys,
        "has_arena": "arena" in loc_keys,
        "has_new_apt": "new_apt" in loc_keys,
    }


def _persist_prompts(project: dict[str, Any], plan: dict[str, Any], scenes: list[dict[str, Any]]) -> None:
    root = project_dir(str(project["id"]))
    fp = root / "flow-pack"
    fp.mkdir(parents=True, exist_ok=True)
    (fp / "image-prompts.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    (fp / "check-visual-bibles.json").write_text(
        json.dumps(plan.get("check_bibles") or {}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (fp / "visual-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Check image prompts", "", f"Scenes: {len(scenes)}", ""]
    for s in scenes:
        lines.append(f"## {s.get('scene_id')} · {s.get('story_time')}")
        lines.append(s.get("script_text") or "")
        lines.append("")
        lines.append(s.get("image_prompt") or "")
        lines.append("")
    (fp / "image-prompts.md").write_text("\n".join(lines), encoding="utf-8")
