"""Export Flow Pack folder + batch helpers (manual Google Flow)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.documentary.visual_plan import (
    build_visual_plan,
    load_visual_plan,
    sync_ready_from_disk,
)


def export_flow_pack(
    project: dict[str, Any],
    *,
    use_llm: bool = True,
    rebuild_visuals: bool = True,
) -> dict[str, Any]:
    """Approve-script gate → Visual Plan → shot-list + batch prompts on disk."""
    if not project.get("script_approved"):
        raise ValueError("Approve the script first — then we can build Flow references and shots.")

    root = project_dir(str(project["id"]))
    fp = root / "flow-pack"
    plan_path = fp / "visual-plan.json"

    if rebuild_visuals or not plan_path.exists():
        plan = build_visual_plan(project, use_llm=use_llm, target_visuals=80)
        from src.documentary.project import load_project

        project = load_project(str(project["id"]))
    else:
        plan = load_visual_plan(str(project["id"]))

    visuals = plan.get("visuals") or []
    bible = plan.get("visual_bible") or {}
    batches = plan.get("flow_batches") or []
    masters = plan.get("master_references") or []
    stats = plan.get("stats") or {}

    (fp / "shots").mkdir(parents=True, exist_ok=True)
    for sub in ("characters", "locations", "objects"):
        (fp / "references" / sub).mkdir(parents=True, exist_ok=True)

    (fp / "global-style.txt").write_text(str(bible.get("global_style") or ""), encoding="utf-8")
    (fp / "story-bible.json").write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
    (fp / "visual-bible.json").write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")

    _write_refs(fp / "references" / "characters", bible.get("characters") or [])
    _write_refs(fp / "references" / "locations", bible.get("locations") or [])
    _write_refs(fp / "references" / "objects", bible.get("important_objects") or [])
    _write_master_prompts(fp / "references", masters)

    batch_size = int(plan.get("batch_size") or project.get("batch_size") or 10)

    for shot in visuals:
        n = int(shot["number"])
        path = fp / "shots" / f"{n:03d}.txt"
        path.write_text(_shot_txt(shot), encoding="utf-8")

    # Legacy-compatible batches field + new flow_batches
    legacy_batches = []
    for b in batches:
        nums = [int(x) for x in (b.get("visual_numbers") or [])]
        legacy_batches.append(
            {
                "id": b.get("id"),
                "start": nums[0] if nums else 0,
                "end": nums[-1] if nums else 0,
                "label": b.get("label"),
                "visual_numbers": nums,
            }
        )

    shot_list = {
        "project_id": project["id"],
        "topic": project.get("topic"),
        "shot_count": len(visuals),
        "batch_size": batch_size,
        "batches": legacy_batches,
        "flow_batches": batches,
        "master_references": masters,
        "stats": stats,
        "shots": visuals,
        "story_bible": bible,
        "visual_bible": bible,
    }
    (fp / "shot-list.json").write_text(json.dumps(shot_list, ensure_ascii=False, indent=2), encoding="utf-8")
    (fp / "README.md").write_text(_readme(project, stats, batch_size), encoding="utf-8")

    sync_ready_from_disk(str(project["id"]))

    set_checkpoint(project, "flow_pack_ready", True)
    project["flow_pack"] = {
        "shot_count": len(visuals),
        "batch_size": batch_size,
        "stats": stats,
    }
    project["ui_step"] = "flow"
    save_project(project)
    append_log(
        str(project["id"]),
        f"flow pack exported visuals={len(visuals)} flow={stats.get('flow')} batches={len(batches)}",
    )
    return project


def update_shot_status(project_id: str, shot_number: int, status: str) -> dict[str, Any]:
    """Prefer filesystem READY/MISSING; allow needs_regen override."""
    allowed = {"pending", "generated", "approved", "needs_regen", "READY", "MISSING"}
    if status not in allowed:
        raise ValueError(f"status must be one of {allowed}")
    path = project_dir(project_id) / "flow-pack" / "shot-list.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for s in data.get("shots") or []:
        if int(s.get("number") or 0) == int(shot_number):
            s["status"] = status
            break
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ap = project_dir(project_id) / "flow-pack" / "visual_analysis.json"
    if ap.exists():
        analysis = json.loads(ap.read_text(encoding="utf-8"))
        for s in analysis.get("shots") or []:
            if int(s.get("number") or 0) == int(shot_number):
                s["status"] = status
                break
        ap.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    vp = project_dir(project_id) / "flow-pack" / "visual-plan.json"
    if vp.exists():
        plan = json.loads(vp.read_text(encoding="utf-8"))
        for s in plan.get("visuals") or []:
            if int(s.get("number") or 0) == int(shot_number):
                s["status"] = status
                break
        vp.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def load_shot_list(project_id: str) -> dict[str, Any]:
    path = project_dir(project_id) / "flow-pack" / "shot-list.json"
    if not path.exists():
        raise FileNotFoundError("shot-list.json missing — export Flow Pack first")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_refs(folder: Path, entities: list) -> None:
    for ent in entities:
        eid = str(ent.get("id") or "UNK")
        text = (
            f"{eid}\n"
            f"Name: {ent.get('name')}\n\n"
            f"Description:\n{ent.get('description')}\n\n"
            f"Generate reference image:\n{ent.get('visual_description')}\n\n"
            f"Strategy: {ent.get('appearance_strategy') or 'FLOW_REENACTMENT'}\n"
            f"Instructions: Generate ONE clear master reference. Reuse this look in later shots.\n"
            f"Treat as reconstruction reference — not a claim of an archival photograph.\n"
        )
        (folder / f"{eid}.txt").write_text(text, encoding="utf-8")


def _write_master_prompts(ref_root: Path, masters: list[dict[str, Any]]) -> None:
    master_dir = ref_root / "masters"
    master_dir.mkdir(parents=True, exist_ok=True)
    for m in masters:
        eid = str(m.get("id") or "REF")
        (master_dir / f"{eid}.txt").write_text(str(m.get("master_prompt") or ""), encoding="utf-8")


def _shot_txt(shot: dict) -> str:
    refs = ", ".join(shot.get("reference_ids") or shot.get("references") or []) or "(none)"
    vtype = shot.get("visual_type") or "FLOW_REENACTMENT"
    prompt = shot.get("flow_prompt") or shot.get("prompt") or ""
    extra = ""
    if vtype != "FLOW_REENACTMENT":
        extra = f"\nACQUISITION:\n{shot.get('acquisition_note') or 'Import real asset — do not fake in Flow.'}\n"
    return (
        f"VISUAL {int(shot['number']):03d}\n\n"
        f"TYPE: {vtype}\n"
        f"EXPECTED FILE: {shot.get('expected_file')}\n"
        f"STORY BEAT: {shot.get('story_beat_id')}\n"
        f"DURATION TARGET: {shot.get('duration_target')}s\n"
        f"KEN BURNS: {shot.get('ken_burns')}\n\n"
        f"NARRATION:\n{shot.get('narration_segment') or shot.get('narration')}\n\n"
        f"DESCRIPTION:\n{shot.get('description')}\n\n"
        f"REFERENCES:\n{refs}\n"
        f"{extra}\n"
        f"PROMPT:\n{prompt}\n"
    )


def _readme(project: dict, stats: dict, batch_size: int) -> str:
    return f"""# Flow Pack — {project.get('id')}

Topic: {project.get('topic')}

## Totals

- Total visuals: {stats.get('total', '?')}
- Flow reenactments: {stats.get('flow', '?')}
- Archival / document / other: {stats.get('real_or_other', '?')}
- Master references: {stats.get('master_references', '?')}
- Flow batches: {stats.get('flow_batches', '?')} (size {batch_size})

## Steps

1. Generate **MASTER REFERENCES** first (`references/masters` + character/location prompts).
2. For each Flow batch: attach needed references in Google Flow → paste **batch prompt** → generate **separate** images (not collage).
3. Download and rename using visual numbers (`001.png`, `014.png`, …). Non-consecutive IDs are normal when archival slots exist.
4. Import into FrameFactory Images (bulk). Truth = file on disk (READY), not a checkbox.
5. For DOCUMENT / HEADLINE / LOGO slots: import real assets — do not invent them in Flow.
6. Replace one bad image with its single prompt — do not redo the whole batch.

Illustrate the EVENT, not the sentence.
"""
