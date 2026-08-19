"""One-shot QC of Check visual prompts. No script rewrite. No image generation."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.documentary.formats.check_als.visuals import (  # noqa: E402
    CHECK_STYLE,
    OFFICE_BIBLE,
    SHARED_APT_BIBLE,
    characters_for,
    compose_image_prompt,
    location_from_key,
)
from src.documentary.flow_pack import _readme, _shot_txt  # noqa: E402
from src.documentary.project import append_log, load_project, project_dir, save_project, set_checkpoint  # noqa: E402


def _low(text: str) -> str:
    return (text or "").lower()


def _lock_key(visual: dict) -> str:
    m = re.search(r"Location lock: (\w+)", str(visual.get("continuity_notes") or ""))
    return (m.group(1) if m else "") or "city"


def _action_from_script(script: str, key: str) -> str:
    t = (script or "").strip()
    if not t or t == "---":
        return "a specific insert matching this story beat, protagonist recognizable if present"
    prefix = {
        "office": "in the cubicle farm",
        "shared_apt": "in the shared apartment",
        "new_apt": "in the modest own apartment near the arena",
        "locker": "in the Halcones locker room / tunnel threshold",
        "arena": "in the same municipal Halcones arena",
        "meeting": "in a cheap meeting/cafe",
    }.get(key, "in this story world")
    return f"{prefix}: {t[:120]}"


def _loc_from_script(text: str, current: str) -> str:
    t = _low(text)
    if "casa nueva" in t or "caja sin abrir" in t or "cuatro cuadras" in t or "colchón contra" in t:
        return "new_apt"
    if "departamento compart" in t or "poster de básquet" in t:
        return "shared_apt"
    if any(k in t for k in ("inversores", "vendedor retiene", "servilleta", "café que cierra", "contrato de sponsor", "reunión importante")):
        return "meeting"
    if "vestuario" in t or "lockers" in t or ("llaves" in t and ("utilero" in t or "jefe" in t or "palma" in t)):
        return "locker"
    if "excel del club en el almuerzo" in t or "compañero de cubículo" in t:
        return "office"
    if "vuelves a la oficina" in t or "sigues yendo a la oficina" in t:
        return "office"
    if "trabajas en una oficina" in t or ("oficina" in t and "casa nueva" not in t and "badge de oficina que no tiraste" not in t):
        if "sentado en una oficina" in t:
            return "office"
        if t.strip().startswith("trabajas") or "cubículo" in t:
            return "office"
    if any(k in t for k in ("sold out", "gradas", "asistencia", "estadio", "cancha", "playoff", "túnel", "tunel")):
        return "arena"
    return current


OPENING = {
    "protagonist_age": 22,
    "story_time": "AGE 22",
    "protagonist_state": "office employee, shared apartment, not yet owner",
}

ARENA = [
    dict(shot_type="establishing_wide", camera="high angle from the rafters", action="tiny figure at tunnel mouth; municipal bowl dominates", foreground="steel rafter and yellowed lamp", background="sparse or packed lower bowl, same Halcones roof", extra="Same municipal architecture; era from story_time."),
    dict(shot_type="over_the_shoulder", camera="behind him in the tunnel mouth looking out", action="hands on the dark tunnel rail, looking toward the court, body off-center", foreground="tunnel concrete and a drip stain", background="court lights, same floor orientation", extra="Tunnel locked; court in depth."),
    dict(shot_type="close_up", camera="close-up of a hand on a peeling seat", action="one hand on a cracked seat; hawk mark nearby", foreground="cracked green seat", background="soft stands", extra="Seat-level detail."),
    dict(shot_type="low_angle", camera="low angle from the baseline", action="walking the baseline, not frozen staring at the hoop", foreground="old wood court grain", background="stands rising", extra="From court toward stands."),
    dict(shot_type="two_shot", camera="side angle from aisle stairs", action="climbing a few aisle steps in profile", foreground="stair rail", background="bowl curve", extra="Aisle of the same arena."),
    dict(shot_type="environmental_detail", camera="insert of faded Halcones brick exterior", action="street-level brick facade; protagonist small or absent", foreground="faded Halcones lettering", background="municipal brick", extra="Same exterior all years."),
]
LOCKER = [
    dict(shot_type="doorway_threshold", camera="from inside looking at the doorway", action="equipment manager in the doorway with keys; protagonist just inside", foreground="green locker edge", background="tunnel light", extra=""),
    dict(shot_type="hands_on_object", camera="close-up", action="keys dropping into a younger palm; older staffer hand", foreground="ring of old arena keys", background="blurred lockers", extra=""),
    dict(shot_type="medium_action", camera="side angle along locker row", action="walking the locker aisle, not facing camera", foreground="open locker door", background="chalkboard 0-0", extra=""),
    dict(shot_type="object_detail", camera="static insert", action="faded Halcones jersey on a hook; empty locker room", foreground="worn jersey", background="green lockers", extra=""),
]
MEETING = [
    dict(shot_type="over_the_shoulder", camera="OTS toward three men in a cheap cafe booth", action="sitting across a stained table with a napkin of numbers", foreground="coffee cup and napkin", background="late-night cafe", extra=""),
    dict(shot_type="close_up", camera="top-down insert", action="thin contract and thick debt folder, hands only", foreground="folder and cheap pen", background="table laminate", extra=""),
    dict(shot_type="two_shot", camera="side booth", action="one investor signing while he watches", foreground="booth vinyl", background="cafe window night", extra=""),
    dict(shot_type="doorway_threshold", camera="from cafe door", action="entering or leaving; meeting in depth", foreground="door frame", background="booth", extra=""),
]
CAMS = ("high angle wide", "low angle close", "over the shoulder", "profile medium", "insert detail", "doorway frame", "top-down", "side tracking")
SHOTS = ("establishing_wide", "close_up", "over_the_shoulder", "hands_on_object", "object_detail", "doorway_threshold", "medium_action", "environmental_detail")


def opening_spec(n: int) -> dict:
    common = dict(OPENING)
    specs = {
        1: dict(location_key="city", action="22-year-old in cheap office shirt and worn backpack at a dull bus stop at dusk; no team jacket", camera="medium close portrait, slightly below eye line", shot_type="establishing_wide", environment="Ordinary city bus stop at dusk. Municipal arena brick only as a distant shape.", foreground="backpack strap", background="bus shelter, not a stadium interior", lighting="dusk mixed with cheap street sodium", important_objects=["worn backpack", "office collared shirt"]),
        2: dict(location_key="office", action="sitting in a gray cubicle typing, plastic badge clipped to the cheap collared shirt, still employed, AGE 22", camera="over the shoulder toward the cheap LCD", shot_type="medium_action", environment=OFFICE_BIBLE, foreground="cubicle partition and sad plant", background="fluorescent office rows", lighting="harsh fluorescent cubicle light", important_objects=["plastic office badge on the shirt", "cheap LCD", "sad plant"]),
        3: dict(location_key="shared_apt", action="sitting on a mattress in a shared bedroom, basketball poster on the wall", camera="wide from the kitchen doorway", shot_type="establishing_wide", environment=SHARED_APT_BIBLE, foreground="mattress corner", background="city night through a small window", lighting="cheap lamp + city window night", important_objects=["basketball poster"]),
        4: dict(location_key="shared_apt", action="phone in both hands showing a bank app; face lit by the screen; unreadable tiny type", camera="close-up over the phone", shot_type="hands_on_object", environment=SHARED_APT_BIBLE, foreground="smartphone", background="messy shared room", lighting="phone screen key light", important_objects=["smartphone with bank app, unreadable type"]),
        5: dict(location_key="office", action="leaning into a cheap cubicle monitor showing a sale listing; coworkers out of focus", camera="side angle through cubicle gap", shot_type="medium_action", environment=OFFICE_BIBLE, foreground="monitor edge", background="fluorescent office", lighting="harsh fluorescent cubicle light", important_objects=["cheap LCD", "badge on shirt"]),
        6: dict(location_key="arena", action="just inside the tunnel looking at a nearly empty municipal bowl, backpack on, AGE 22", camera="over the shoulder from darker tunnel toward the court", shot_type="over_the_shoulder", environment=location_from_key("arena", 22, "empty 620"), foreground="tunnel darkness and a water stain", background="sparse stands, yellowed lights, same Halcones architecture", lighting="yellowed arena practicals", important_objects=["Halcones hawk mark", "worn backpack"]),
        7: dict(location_key="office", action="holding a printed sale notice with a one-dollar figure, unreadably small type", camera="insert of paper and hands, cubicle behind", shot_type="hands_on_object", environment=OFFICE_BIBLE, foreground="printed aviso", background="gray cubicle", lighting="fluorescent + paper white", important_objects=["cheap printed sale notice / one-dollar figure on paper"]),
        8: dict(location_key="meeting", action="thick debt folder and thin purchase contract on an unused conference table; empty chairs", camera="top-down table insert", shot_type="object_detail", environment="A tired unused conference room, not a glass boardroom.", foreground="thick folder and thin contract", background="empty meeting chairs", lighting="dead overhead office light", important_objects=["debt folder", "thin $1 contract"]),
    }
    out = dict(common)
    out.update(specs[n])
    return out


def apply_variant(v: dict, var: dict, script: str, key: str) -> None:
    v["camera"] = var["camera"]
    v["shot_type"] = var["shot_type"]
    v["action"] = f"{var['action']}. Beat: {_action_from_script(script, key)}"
    v["foreground"] = var.get("foreground")
    v["background"] = var.get("background")
    extra = var.get("extra") or ""
    if extra:
        v["environment"] = str(v.get("environment") or "") + " " + extra
        v["location"] = str(v["environment"])[:180]


def qc(plan: dict) -> dict:
    visuals = list(plan.get("visuals") or [])
    report = {
        "shots_age22_fixed": [],
        "location_overrides": [],
        "consecutive_varied": [],
        "junk_action_replaced": [],
        "arena_tunnel_locker_varied": [],
    }
    loc_i: dict[str, int] = {}
    prev_key = ""
    prev_cam = ""
    for i, v in enumerate(visuals, start=1):
        n = int(v.get("number") or i)
        script = str(v.get("script_text") or v.get("narration_segment") or v.get("narration") or "")
        v["script_text"] = script
        v["narration_segment"] = script
        v["narration"] = script

        if n <= 8:
            spec = opening_spec(n)
            key = spec.pop("location_key")
            v.update(spec)
            v["location"] = str(spec.get("environment") or "")[:180]
            report["shots_age22_fixed"].append(n)
        else:
            key = _loc_from_script(script, _lock_key(v))
            old = _lock_key(v)
            if key != old:
                report["location_overrides"].append({"shot": n, "from": old, "to": key})
            age = int(v.get("protagonist_age") or 22)
            v["environment"] = location_from_key(key, age, script)
            v["location"] = str(v["environment"])[:180]
            act = str(v.get("action") or "")
            if act.startswith("El Joven Propietario") or script.strip() in {"---", ""}:
                v["action"] = _action_from_script(script, key)
                report["junk_action_replaced"].append(n)

        court_look = bool(
            re.search(
                r"mira(?:s)? desde|t[uú]nel|sold out|gradas|cancha|estadio est[aá]|el estadio|"
                r"asistencia|vac[ií]o despu[eé]s|no ves huecos|lleno",
                script,
                re.I,
            )
        )
        family = key == prev_key
        variants = None
        bucket = None
        if n > 8:
            if key == "locker" and not court_look:
                variants, bucket = LOCKER, "locker"
            elif key == "meeting":
                variants, bucket = MEETING, "meeting"
            elif key == "arena" or court_look:
                variants, bucket = ARENA, "arena"

        if variants is not None and bucket:
            idx = loc_i.get(bucket, 0)
            loc_i[bucket] = idx + 1
            apply_variant(v, variants[idx % len(variants)], script, key)
            report["arena_tunnel_locker_varied"].append(n)
            if family:
                report["consecutive_varied"].append(n)
        elif n > 8 and family:
            idx = loc_i.get(key, 0) + 1
            loc_i[key] = idx
            v["camera"] = CAMS[idx % len(CAMS)]
            v["shot_type"] = SHOTS[idx % len(SHOTS)]
            v["action"] = _action_from_script(script, key)
            v["foreground"] = "a distinct near-plane object for this beat"
            v["background"] = "deep environment, different depth than the previous still"
            if v.get("camera") == prev_cam:
                v["camera"] = CAMS[(idx + 3) % len(CAMS)]
            report["consecutive_varied"].append(n)
        else:
            loc_i[key] = loc_i.get(key, 0)

        age = int(v.get("protagonist_age") or 22)
        v["continuity_notes"] = (
            f"Reuse protagonist CHAR_YOU. Location lock: {key}. "
            f"Arena architecture constant. Age {age}."
        )
        v["characters"] = characters_for(key, script)
        prompt = compose_image_prompt(
            v,
            {
                "protagonist_age": age,
                "protagonist_state": v.get("protagonist_state"),
                "story_time": v.get("story_time"),
            },
        )
        v["image_prompt"] = prompt
        v["flow_prompt"] = prompt
        v["prompt"] = prompt
        prev_key = key
        prev_cam = str(v.get("camera") or "")

    scenes = []
    for v in visuals:
        scenes.append(
            {
                "scene_id": v.get("scene_id") or v.get("visual_id"),
                "number": v.get("number"),
                "script_text": v.get("script_text"),
                "story_time": v.get("story_time"),
                "duration_target": v.get("duration_target"),
                "location": v.get("location"),
                "characters": v.get("characters"),
                "action": v.get("action"),
                "emotion": v.get("emotion"),
                "protagonist_age": v.get("protagonist_age"),
                "protagonist_state": v.get("protagonist_state"),
                "camera": v.get("camera"),
                "shot_type": v.get("shot_type"),
                "composition": v.get("composition"),
                "lighting": v.get("lighting"),
                "important_objects": v.get("important_objects"),
                "continuity_notes": v.get("continuity_notes"),
                "image_prompt": v.get("image_prompt"),
                "foreground": v.get("foreground"),
                "background": v.get("background"),
            }
        )
    plan["visuals"] = visuals
    plan["image_prompts"] = scenes
    plan["qc_final"] = report
    stats = dict(plan.get("stats") or {})
    stats["scene_count"] = len(visuals)
    plan["stats"] = stats
    return report


def write_flow_pack(project: dict, plan: dict) -> Path:
    from src.documentary.visual_plan import batch_references, group_flow_batches, select_master_references, summarize_visuals

    root = project_dir(str(project["id"]))
    fp = root / "flow-pack"
    fp.mkdir(parents=True, exist_ok=True)
    visuals = plan.get("visuals") or []
    bible = plan.get("visual_bible") or {}
    bible["format"] = "check_als"
    bible["global_style"] = CHECK_STYLE
    masters = select_master_references(bible, visuals)
    plan["master_references"] = masters
    batches = group_flow_batches(visuals, batch_size=int(plan.get("batch_size") or 10))
    for b in batches:
        nums = b.get("visual_numbers") or []
        parts = []
        for num in nums[:2]:
            hit = next((x for x in visuals if int(x.get("number") or 0) == int(num)), None)
            if hit and hit.get("image_prompt"):
                parts.append(str(hit["image_prompt"])[:500])
        b["prompt"] = CHECK_STYLE + "\n\n" + "\n---\n".join(parts)
        b["references_needed"] = batch_references(b, visuals, masters)
    plan["flow_batches"] = batches
    stats = summarize_visuals(visuals, batches, masters)
    stats["scene_count"] = len(visuals)
    plan["stats"] = {**(plan.get("stats") or {}), **stats}

    (fp / "visual-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    scenes = plan.get("image_prompts") or []
    (fp / "image-prompts.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    (fp / "check-visual-bibles.json").write_text(
        json.dumps(plan.get("check_bibles") or {}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = ["# Check image prompts (QC final)", "", f"Scenes: {len(scenes)}", ""]
    for s in scenes:
        lines += [f"## {s.get('number') or s.get('scene_id')} · {s.get('story_time')}", s.get("script_text") or "", "", s.get("image_prompt") or "", ""]
    (fp / "image-prompts.md").write_text("\n".join(lines), encoding="utf-8")

    (fp / "shots").mkdir(parents=True, exist_ok=True)
    for shot in visuals:
        n = int(shot["number"])
        (fp / "shots" / f"{n:03d}.txt").write_text(_shot_txt(shot), encoding="utf-8")
    (fp / "global-style.txt").write_text(str(bible.get("global_style") or CHECK_STYLE), encoding="utf-8")
    (fp / "visual-bible.json").write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
    (fp / "story-bible.json").write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")

    shot_list = {
        "project_id": project["id"],
        "topic": project.get("topic"),
        "shot_count": len(visuals),
        "batch_size": int(plan.get("batch_size") or 10),
        "flow_batches": batches,
        "master_references": masters,
        "stats": plan["stats"],
        "shots": visuals,
        "visual_bible": bible,
        "qc_final": plan.get("qc_final"),
    }
    (fp / "shot-list.json").write_text(json.dumps(shot_list, ensure_ascii=False, indent=2), encoding="utf-8")
    (fp / "README.md").write_text(_readme(project, plan["stats"], int(plan.get("batch_size") or 10)), encoding="utf-8")
    set_checkpoint(project, "flow_pack_ready", True)
    project["flow_pack"] = {"shot_count": len(visuals), "batch_size": int(plan.get("batch_size") or 10), "stats": plan["stats"]}
    project["visual_plan"] = {"stats": plan["stats"], "batch_count": len(batches), "path": "flow-pack/visual-plan.json"}
    project["ui_step"] = "flow"
    save_project(project)
    append_log(str(project["id"]), f"check visual QC final shots={len(visuals)} (no image gen)")
    return fp


def main() -> int:
    pid = "pilot-fase2-basket"
    p = load_project(pid)
    fp = project_dir(pid) / "flow-pack"
    plan = json.loads((fp / "visual-plan.json").read_text(encoding="utf-8"))
    report = qc(plan)
    out = write_flow_pack(p, plan)
    summary = {
        "final_still_prompts": len(plan.get("visuals") or []),
        "shots_age22_fixed": report["shots_age22_fixed"],
        "location_overrides": report["location_overrides"],
        "consecutive_varied": report["consecutive_varied"],
        "junk_action_replaced": report["junk_action_replaced"],
        "arena_tunnel_locker_varied": report["arena_tunnel_locker_varied"],
        "flow_pack": str(out),
        "script_unchanged": True,
        "images_generated": False,
    }
    (fp / "qc-final-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
