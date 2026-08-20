"""Export Check production packs. Each slot gets its own prompt; reuse is fallback only."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.documentary.formats.check_als.asset_reuse import load_raw_visual_plan
from src.documentary.project import project_dir

_POLICY_NOTE = (
    "Each visual slot targets its own still (NNN.png). "
    "P0–P3 = generation order only, not permission to skip slots. "
    "Smart reuse activates only when the exact asset is missing."
)

_BIBLE_BY_FAMILY = {
    "office": ["protagonist_visual_bible", "office_visual_bible"],
    "arena": ["protagonist_visual_bible", "arena_visual_bible", "team_visual_bible"],
    "home": ["protagonist_visual_bible"],
    "city": ["protagonist_visual_bible"],
}


def _shot_num(asset_id: str) -> int:
    return int(str(asset_id).split("_")[-1])


def _bible_refs(sem: dict[str, Any], visual: dict[str, Any]) -> list[str]:
    refs = [str(x) for x in (visual.get("reference_ids") or visual.get("references") or []) if x]
    fam = str(sem.get("location_family") or "city")
    loc = str(sem.get("location") or "")
    out = list(dict.fromkeys(refs + _BIBLE_BY_FAMILY.get(fam, ["protagonist_visual_bible"])))
    if loc in ("shared_apartment", "shared_apt"):
        out.append("shared_apartment_visual_bible")
    if loc in ("new_apartment", "new_apt"):
        out.append("new_apartment_visual_bible")
    if sem.get("hero_id") == "utilero_keys" or "utilero" in str(visual.get("script_text") or "").lower():
        out.append("utilero_visual_bible")
    if sem.get("visual_subject") == "coach":
        out.append("coach_visual_bible")
    return list(dict.fromkeys(out))


def _fallback_slots(shot: int, groups: list[dict[str, Any]]) -> list[int]:
    """Semantic neighbours that could reuse this still if their exact asset is missing."""
    asset = f"still_{shot:03d}"
    found = {shot}
    for g in groups:
        if g.get("recommended_asset") == asset:
            found.update(int(n) for n in (g.get("slots") or []))
        elif shot in [int(n) for n in (g.get("slots") or [])]:
            found.update(int(n) for n in (g.get("slots") or []))
    return sorted(x for x in found if x != shot)


def _priority_map(queue: dict[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for pri in ("P0", "P1", "P2", "P3"):
        for aid in queue.get(pri) or []:
            if isinstance(aid, str) and aid.startswith("still_"):
                out[_shot_num(aid)] = pri
            elif str(aid).isdigit():
                out[int(aid)] = pri
    return out


def _build_item(
    n: int,
    *,
    semantics: dict[int, dict[str, Any]],
    visuals: dict[int, dict[str, Any]],
    groups: list[dict[str, Any]],
    priority: str,
) -> dict[str, Any]:
    sem = semantics.get(n) or {}
    v = visuals.get(n) or {}
    prompt = str(v.get("image_prompt") or v.get("flow_prompt") or v.get("prompt") or "")
    return {
        "shot_id": f"{n:03d}",
        "priority": priority,
        "image_prompt": prompt,
        "visual_bible_refs": _bible_refs(sem, v),
        "protagonist_era": sem.get("protagonist_era"),
        "location": sem.get("location"),
        "mood": sem.get("mood"),
        "story_function": sem.get("story_function"),
        "reuse_slots": [f"{x:03d}" for x in _fallback_slots(n, groups)],
        "hero_id": sem.get("hero_id"),
        "expected_file": f"{n:03d}.png",
        "requires_own_still": True,
    }


def _write_pack(
    dest: Path,
    *,
    batch_id: str,
    project_id: str,
    items: list[dict[str, Any]],
    note: str,
) -> None:
    prompts_dir = dest / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "batch": batch_id,
        "project_id": project_id,
        "policy": _POLICY_NOTE,
        "total_prompts": len(items),
        "note": note,
        "items": [
            {k: v for k, v in it.items() if k != "image_prompt"}
            | {"prompt_file": f"prompts/{it['shot_id']}.txt"}
            for it in items
        ],
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    title = batch_id.replace("-", " ").upper()
    md = [
        f"# Check production — {title}",
        "",
        f"**{len(items)} prompts** · {_POLICY_NOTE}",
        "",
        "Import each still as `NNN.png` matching `shot_id`.",
        "",
        "## Index",
        "",
    ]
    for it in items:
        fb = ", ".join(it["reuse_slots"]) or "—"
        md.append(
            f"- `{it['shot_id']}` · {it['priority']} · {it['mood']}/{it['story_function']} · "
            f"{it['location']} · era `{it['protagonist_era']}` · fallback neighbours: {fb}"
        )
    md.append("")
    for it in items:
        md.extend(
            [
                f"## {it['shot_id']} — {it['priority']}",
                "",
                f"- shot_id: `{it['shot_id']}`",
                f"- priority: `{it['priority']}` (generation order)",
                f"- requires_own_still: `true`",
                f"- protagonist_era: `{it['protagonist_era']}`",
                f"- location: `{it['location']}`",
                f"- mood: `{it['mood']}`",
                f"- story_function: `{it['story_function']}`",
                f"- visual_bible_refs: {', '.join(it['visual_bible_refs'])}",
                f"- reuse_slots (fallback only): {', '.join(it['reuse_slots']) or '—'}",
                "",
                "```",
                it["image_prompt"],
                "```",
                "",
            ]
        )
    (dest / "prompts.md").write_text("\n".join(md), encoding="utf-8")

    for it in items:
        header = "\n".join(
            [
                f"shot_id: {it['shot_id']}",
                f"priority: {it['priority']}",
                f"requires_own_still: true",
                f"protagonist_era: {it['protagonist_era']}",
                f"location: {it['location']}",
                f"mood: {it['mood']}",
                f"story_function: {it['story_function']}",
                f"visual_bible_refs: {', '.join(it['visual_bible_refs'])}",
                f"reuse_slots: {', '.join(it['reuse_slots']) or '—'}",
                "---",
                it["image_prompt"],
                "",
            ]
        )
        (prompts_dir / f"{it['shot_id']}.txt").write_text(header, encoding="utf-8")


def _load_context(project_id: str) -> tuple[Path, dict[str, Any], dict[int, dict], dict[int, dict], list, dict]:
    fp = project_dir(project_id) / "flow-pack"
    cov = json.loads((fp / "asset-coverage.json").read_text(encoding="utf-8"))
    semantics = {int(s["slot"]): s for s in json.loads((fp / "scene-semantics.json").read_text(encoding="utf-8"))}
    plan = load_raw_visual_plan(project_id)
    visuals = {int(v.get("number") or 0): v for v in (plan.get("visuals") or [])}
    groups = cov.get("reuse_groups") or []
    queue = cov.get("generation_queue") or {}
    return fp, cov, semantics, visuals, groups, queue


def export_p0_p1_pack(project_id: str) -> dict[str, Any]:
    fp, cov, semantics, visuals, groups, queue = _load_context(project_id)
    pri_map = _priority_map(queue)
    nums = sorted(n for n, p in pri_map.items() if p in ("P0", "P1"))
    items = [
        _build_item(n, semantics=semantics, visuals=visuals, groups=groups, priority=pri_map[n])
        for n in nums
    ]
    dest = fp / "batches" / "p0-p1"
    _write_pack(
        dest,
        batch_id="p0-p1",
        project_id=project_id,
        items=items,
        note="Optional first batch: P0 heroes + P1 high-value moments. Generate all 100 via all-stills pack.",
    )
    cov.setdefault("production_batches", {})["p0-p1"] = {
        "path": "flow-pack/batches/p0-p1",
        "prompts": len(items),
        "shots": [it["shot_id"] for it in items],
        "role": "optional_priority_batch",
    }
    (fp / "asset-coverage.json").write_text(json.dumps(cov, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(dest), "count": len(items), "shots": [it["shot_id"] for it in items]}


def export_all_stills_pack(project_id: str) -> dict[str, Any]:
    fp, cov, semantics, visuals, groups, queue = _load_context(project_id)
    total = int(cov.get("total_slots") or max(semantics.keys(), default=100))
    pri_map = _priority_map(queue)
    pri_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    nums = sorted(range(1, total + 1), key=lambda n: (pri_rank.get(pri_map.get(n, "P2"), 2), n))
    items = [
        _build_item(
            n,
            semantics=semantics,
            visuals=visuals,
            groups=groups,
            priority=pri_map.get(n, "P2"),
        )
        for n in nums
    ]
    dest = fp / "batches" / "all-stills"
    _write_pack(
        dest,
        batch_id="all-stills",
        project_id=project_id,
        items=items,
        note="Full production pack: one prompt per visual slot (001–100). Import each as NNN.png.",
    )
    imported = int((cov.get("production_progress") or {}).get("imported_exact") or 0)
    cov.setdefault("production_batches", {})["all-stills"] = {
        "path": "flow-pack/batches/all-stills",
        "prompts": len(items),
        "total_slots": len(items),
        "role": "full_still_generation_pack",
    }
    cov["full_still_pack"] = {
        "path": "flow-pack/batches/all-stills",
        "total_slots": len(items),
        "prompts_ready": len(items),
        "imported_exact": imported,
        "policy": _POLICY_NOTE,
    }
    (fp / "asset-coverage.json").write_text(json.dumps(cov, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(dest), "count": len(items), "prompts_ready": len(items)}


def export_production_packs(project_id: str) -> dict[str, Any]:
    p01 = export_p0_p1_pack(project_id)
    allp = export_all_stills_pack(project_id)
    return {"p0_p1": p01, "all_stills": allp}
