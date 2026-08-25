"""Check ALS visual layer: high-quality stickman 2D stills + locked character/location bibles."""
from __future__ import annotations

import json
import re
from typing import Any

from src.documentary.formats.check_als.editorial import VISUAL_DIRECTION, VISUAL_STYLE_ID
from src.documentary.project import project_dir

# Locked house style — matches Check / ALS POV stickman channels (round white head, dot eyes,
# bold outlines, flat color) with RICH environments that stay consistent shot-to-shot.
CHECK_STYLE = (
    "High-quality 2D stickman cartoon illustration for YouTube POV storytelling. "
    "Characters: classic stickman body (thin limbs, simplified torso) with a LARGE round WHITE head, "
    "tiny black-dot eyes, simple line eyebrows/mouth, solid flat hair shapes (no strand detail), "
    "bold black outlines, flat cel colors with light shading. Clothing is readable and specific. "
    "Environments: HIGH DETAIL — shops, offices, apartments, counters, props, depth layers — "
    "same polish as premium webcomic/animation stills, NOT crude MS Paint stick figures. "
    "Not anime, not 3D, not photoreal, not clipart, not stock photo, not chibi, not mascot redesign."
)

PROTAGONIST_BIBLE = (
    "LOCKED PROTAGONIST (YOU) — same stickman in EVERY frame: large round white head, black-dot eyes, "
    "simple line mouth, thick spiky black hair as a solid shape, thin stick limbs, lean proportions. "
    "Identity never changes: same face, same hair silhouette, same body proportions. "
    "AGE 22 wardrobe: cheap office collared shirt or hoodie, dark trousers, worn backpack. "
    "After ownership / business launch: same face + hair; wardrobe upgrades modestly "
    "(team jacket green-and-gold OR creator/startup casual — still the SAME stickman). "
    "AGE 27: same character five years older — slightly tired eyes, faint stubble lines optional, "
    "SAME hair spike pattern and head shape. Never swap ethnicity, never redesign into a realistic human, "
    "never change hair color/style mid-story."
)

SUPPORTING_STICKMAN = (
    "All supporting people are the SAME stickman system: round white heads, dot eyes, bold outlines, "
    "flat hair blocks, simple clothes. Each named role keeps ONE locked design for the whole episode."
)

# Captions/VO belong in the edit — Flow loves to burn Spanish lines into the plate.
NO_ON_IMAGE_TEXT = (
    "TEXT HARD BAN (critical): CLEAN plate only. ZERO on-image lettering of any kind — "
    "no subtitles, captions, lower-thirds, titles, speech bubbles, watermarks, logos, "
    "UI chrome, posters with readable words, Spanish or English sentences, burned dialogue. "
    "Never write narration on the image. Voiceover and subtitles are added later in editing."
)

ARENA_BIBLE = (
    "LOCKED LOCATION — same municipal basketball arena throughout: brick exterior, faded 'Halcones' sign, "
    "4800-seat bowl, same roof, same tunnel, same floor orientation. "
    "Early: peeling paint, empty stands, yellowed lights. Later: same architecture, better lights, packed stands. "
    "Building evolves; it NEVER becomes a different arena."
)

OFFICE_BIBLE = (
    "LOCKED LOCATION — same dull corporate cubicle farm every time: gray partitions, fluorescent lights, "
    "cheap LCD, sad plant, plastic badge. Not WeWork, not glass HQ. Geometry and desk placement stay fixed."
)

SHARED_APT_BIBLE = (
    "LOCKED LOCATION — same small shared apartment: roommate clutter, cheap furniture, city night window. "
    "Same room layout every return. Modest, lived-in, not luxury."
)

NEW_APT_BIBLE = (
    "LOCKED LOCATION — same simple one-bedroom of his own: moving boxes early, same window view later. "
    "Modest upgrade, not a penthouse. Layout fixed once introduced."
)

TEAM_BIBLE = (
    "Los Halcones: dark green and copper-gold, hawk mark. Same uniform identity across years."
)

COACH_BIBLE = (
    "LOCKED SUPPORT — head coach stickman: early 50s, short gray-brown flat hair block, sideline jacket, clipboard. "
    "Same design every appearance. " + SUPPORTING_STICKMAN
)

UTILERO_BIBLE = (
    "LOCKED SUPPORT — older equipment-man stickman ~60, keys on a ring, faded staff polo. "
    "Same design every appearance. " + SUPPORTING_STICKMAN
)

CREATOR_HUB_BIBLE = (
    "LOCKED LOCATION — Creative Hub / creator workspace when story is business: same small Madrid apartment-studio "
    "or same office set once established — desk, monitors, posters, window to the street. Layout never redesigns."
)

INVESTOR_CAFE_BIBLE = (
    "LOCKED LOCATION — same local cafe booth for investor meetings: wood table, same wall color, same window. "
    "Reuse every meeting scene."
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
            "and better lighting but the same room geometry. Stickman style, high-detail props."
        ),
        "visual_description": "old municipal locker room that slowly improves, same room",
        "reference_required": True,
    },
    {
        "id": "LOC_CREATOR_HUB",
        "name": "creator hub studio",
        "description": CREATOR_HUB_BIBLE,
        "visual_description": CREATOR_HUB_BIBLE,
        "reference_required": True,
    },
    {
        "id": "LOC_INVESTOR_CAFE",
        "name": "investor cafe",
        "description": INVESTOR_CAFE_BIBLE,
        "visual_description": INVESTOR_CAFE_BIBLE,
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
        "creator_hub_visual_bible": CREATOR_HUB_BIBLE,
        "investor_cafe_visual_bible": INVESTOR_CAFE_BIBLE,
        "style": CHECK_STYLE,
        "style_id": VISUAL_STYLE_ID,
        "visual_direction": VISUAL_DIRECTION,
        "character_system": SUPPORTING_STICKMAN,
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
    if any(k in t for k in ("inversor", "investor", "café", "cafe", "reunión", "reunion")) and any(
        k in t for k in ("café", "cafe", "mesa", "booth", "inversores", "contrato")
    ):
        return "investor_cafe"
    if any(k in t for k in ("creative hub", "estudio", "canal", "contenido", "grab", "set de")):
        return "creator_hub"
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
    if any(k in t for k in ("departamento", "madrid", "habitación", "laptop", "cliente")):
        return "creator_hub"
    return "arena" if "halcon" in t else "city"


def location_from_key(key: str, age: int, attendance_hint: str) -> str:
    arena_state = ARENA_BIBLE
    if age <= 22 and key == "arena":
        arena_state = (
            "Run-down municipal Halcones arena: empty or sparse stands, yellowed lights, peeling paint. "
            "SAME building as later sold-out years. Stickman scene, high-detail environment. " + ARENA_BIBLE
        )
    elif key == "arena" and ("sold" in attendance_hint or age >= 23):
        arena_state = (
            "Same Halcones municipal arena now packed, stronger lights, same architecture. "
            "Stickman scene, high-detail environment. " + ARENA_BIBLE
        )
    mapping = {
        "office": OFFICE_BIBLE,
        "shared_apt": SHARED_APT_BIBLE,
        "new_apt": NEW_APT_BIBLE,
        "locker": "Halcones locker room. " + TEAM_BIBLE,
        "arena": arena_state,
        "meeting": "A tired conference room in Ciudad Central — same room if reused. Stickman cast. " + SUPPORTING_STICKMAN,
        "investor_cafe": INVESTOR_CAFE_BIBLE,
        "creator_hub": CREATOR_HUB_BIBLE,
        "city": "Night streets of a mid-size fictional city; same street palette when reused. Stickman protagonist.",
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
    # If action is actually VO/narration, treat it as beat mood only — never as words to paint.
    if _looks_like_vo_line(action):
        action = (
            f"Show the protagonist living this beat visually (do NOT write these words on the image): "
            f"mood/context only — {action[:220]}"
        )
    camera = str(visual.get("camera") or visual.get("shot_type") or "medium shot").strip()
    lighting = str(visual.get("lighting") or "clean cartoon lighting with soft depth").strip()
    composition = str(
        visual.get("composition")
        or "16:9, stickman subject readable, detailed environment layers, strong depth"
    ).strip()
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
            f"{composition} Foreground: {fg or 'stickman silhouette'}. "
            f"Background: {bg or 'high-detail locked location'}."
        )
    wardrobe = "Wardrobe matches age/state from the locked protagonist bible — same stickman."
    if int(age or 22) == 22 and "not yet owner" in str(state or ""):
        wardrobe = (
            "AGE 22 wardrobe only: cheap office shirt or hoodie, dark trousers, worn backpack. "
            "Still the SAME white-head stickman with spiky black hair."
        )
    return (
        f"{CHECK_STYLE}\n"
        f"STYLE LOCK (Check stickman): {VISUAL_DIRECTION}\n"
        f"EXACT CHARACTER LOCK: {PROTAGONIST_BIBLE} Age now: {age}. State: {state}. {wardrobe}\n"
        f"SUPPORT CAST RULE: {SUPPORTING_STICKMAN}\n"
        f"EXACT ACTION: {action}\n"
        f"EXACT ENVIRONMENT LOCK: {loc}\n"
        f"STORY TIME: {story_time}\n"
        f"CAMERA: {camera}\n"
        f"COMPOSITION: {composition}\n"
        f"LIGHTING: {lighting}\n"
        f"IMPORTANT OBJECTS: {obj_line}\n"
        f"CONTINUITY HARD RULES: Same protagonist head/hair/proportions in every shot. "
        f"Same location geometry when returning to a place. Locations are rich and consistent — "
        f"do not invent a new shop, office, or arena mid-story. {wardrobe}\n"
        f"AVOID: photoreal faces, anime eyes, 3D render, clipart, redesigning the stickman, "
        f"changing hair, random new locations, watermarks, readable UI text, "
        f"subtitles, captions, burned-in dialogue, any on-image words.\n"
        f"{NO_ON_IMAGE_TEXT}"
    )


def _looks_like_vo_line(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 28:
        return False
    low = t.lower()
    vo_markers = (
        "tú ", " tu ", "tienes ", "sientes ", "pero no", "los primeros",
        "con un equipo", "en un mundo", "la empresa", "tu decisión",
        "you ", "you're ", "you feel", "you have",
    )
    if any(m in f" {low}" for m in vo_markers):
        return True
    # Long Spanish sentence without camera/visual verbs → likely narration.
    if re.search(r"[áéíóúñ¿¡]", low) and not re.search(
        r"\b(shot|camera|close-up|medium|wide|stickman|foreground|sitting|standing|holding)\b",
        low,
    ):
        return True
    return False


def format_check_prompt(visual: dict[str, Any], bible: dict[str, Any] | None = None) -> str:
    meta = {
        "protagonist_age": visual.get("protagonist_age"),
        "protagonist_state": visual.get("protagonist_state"),
        "story_time": visual.get("story_time"),
    }
    base = str(visual.get("image_prompt") or "").strip()
    if base and "TEXT HARD BAN" in base:
        return base
    if base:
        return f"{base.rstrip()}\n\n{NO_ON_IMAGE_TEXT}"
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
            f"Reuse stickman CHAR_YOU (white round head, spiky black hair). "
            f"Location lock: {loc_key}. Age {meta['protagonist_age']}. "
            f"Do not redesign character or location."
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
    lines = [
        "# Check image prompts",
        "",
        f"Scenes: {len(scenes)}",
        "",
        "IMPORTANT: Copy ONLY the Flow prompt block into Google Flow.",
        "Never paste the VO line — Flow will burn it as a subtitle.",
        "",
    ]
    for s in scenes:
        lines.append(f"## {s.get('scene_id')} · {s.get('story_time')}")
        vo = str(s.get("script_text") or "").strip()
        if vo:
            lines.append(f"VO (audio only — DO NOT paste into Flow): {vo}")
            lines.append("")
        lines.append("### Flow prompt")
        lines.append(s.get("image_prompt") or "")
        lines.append("")
    (fp / "image-prompts.md").write_text("\n".join(lines), encoding="utf-8")
