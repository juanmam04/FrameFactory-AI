"""Export Flow Pack folder + batch helpers (manual Google Flow)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.documentary.visual_director import analyze_visuals, load_analysis


def export_flow_pack(project: dict[str, Any], *, use_llm: bool = True, rebuild_visuals: bool = True) -> dict[str, Any]:
    if not project.get("script_approved"):
        raise ValueError("Script must be APPROVED before Flow Pack")
    if rebuild_visuals or not (project_dir(str(project["id"])) / "flow-pack" / "visual_analysis.json").exists():
        analyze_visuals(project, use_llm=use_llm)
        from src.documentary.project import load_project

        project = load_project(str(project["id"]))

    analysis = load_analysis(str(project["id"]))
    shots = analysis.get("shots") or []
    bible = analysis.get("story_bible") or {}
    root = project_dir(str(project["id"]))
    fp = root / "flow-pack"
    (fp / "shots").mkdir(parents=True, exist_ok=True)
    for sub in ("characters", "locations", "objects"):
        (fp / "references" / sub).mkdir(parents=True, exist_ok=True)

    (fp / "global-style.txt").write_text(str(bible.get("global_style") or ""), encoding="utf-8")
    (fp / "story-bible.json").write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")

    # Master references
    _write_refs(fp / "references" / "characters", bible.get("characters") or [], "CHAR")
    _write_refs(fp / "references" / "locations", bible.get("locations") or [], "LOC")
    _write_refs(fp / "references" / "objects", bible.get("important_objects") or [], "OBJ")

    batch_size = int(project.get("batch_size") or 10)
    batches = _batches(len(shots), batch_size)

    for shot in shots:
        n = int(shot["number"])
        path = fp / "shots" / f"{n:03d}.txt"
        path.write_text(_shot_txt(shot), encoding="utf-8")

    shot_list = {
        "project_id": project["id"],
        "topic": project.get("topic"),
        "shot_count": len(shots),
        "batch_size": batch_size,
        "batches": batches,
        "shots": shots,
        "story_bible": bible,
    }
    (fp / "shot-list.json").write_text(json.dumps(shot_list, ensure_ascii=False, indent=2), encoding="utf-8")
    (fp / "README.md").write_text(_readme(project, len(shots), batch_size), encoding="utf-8")

    set_checkpoint(project, "flow_pack_ready", True)
    project["flow_pack"] = {"shot_count": len(shots), "batch_size": batch_size}
    save_project(project)
    append_log(str(project["id"]), f"flow pack exported shots={len(shots)}")
    return project


def update_shot_status(project_id: str, shot_number: int, status: str) -> dict[str, Any]:
    allowed = {"pending", "generated", "approved", "needs_regen"}
    if status not in allowed:
        raise ValueError(f"status must be one of {allowed}")
    path = project_dir(project_id) / "flow-pack" / "shot-list.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for s in data.get("shots") or []:
        if int(s.get("number") or 0) == int(shot_number):
            s["status"] = status
            break
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # mirror analysis
    ap = project_dir(project_id) / "flow-pack" / "visual_analysis.json"
    if ap.exists():
        analysis = json.loads(ap.read_text(encoding="utf-8"))
        for s in analysis.get("shots") or []:
            if int(s.get("number") or 0) == int(shot_number):
                s["status"] = status
                break
        ap.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def load_shot_list(project_id: str) -> dict[str, Any]:
    path = project_dir(project_id) / "flow-pack" / "shot-list.json"
    if not path.exists():
        raise FileNotFoundError("shot-list.json missing — export Flow Pack first")
    return json.loads(path.read_text(encoding="utf-8"))


def _batches(n: int, size: int) -> list[dict[str, Any]]:
    size = max(1, int(size))
    out = []
    for i, start in enumerate(range(1, n + 1, size), start=1):
        end = min(n, start + size - 1)
        out.append({"id": f"BATCH_{i:02d}", "start": start, "end": end, "label": f"shots {start:03d}–{end:03d}"})
    return out


def _write_refs(folder: Path, entities: list, _prefix: str) -> None:
    for ent in entities:
        eid = str(ent.get("id") or "UNK")
        text = (
            f"{eid}\n"
            f"Name: {ent.get('name')}\n\n"
            f"Description:\n{ent.get('description')}\n\n"
            f"Generate reference image:\n{ent.get('visual_description')}\n\n"
            f"Instructions: Generate ONE clear master reference. Reuse this look in later shots.\n"
        )
        (folder / f"{eid}.txt").write_text(text, encoding="utf-8")


def _shot_txt(shot: dict) -> str:
    refs = ", ".join(shot.get("references") or []) or "(none)"
    return (
        f"SHOT {int(shot['number']):03d}\n\n"
        f"EXPECTED FILE: {shot.get('expected_file')}\n\n"
        f"NARRATION:\n{shot.get('narration')}\n\n"
        f"REFERENCES:\n{refs}\n\n"
        f"CONTINUITY:\n{shot.get('continuity')}\n\n"
        f"SHOT TYPE:\n{shot.get('shot_type')}\n\n"
        f"CAMERA:\n{shot.get('camera')}\n\n"
        f"ACTION:\n{shot.get('action')}\n\n"
        f"PROMPT:\n{shot.get('prompt')}\n"
    )


def _readme(project: dict, n: int, batch_size: int) -> str:
    return f"""# Flow Pack — {project.get('id')}

Topic: {project.get('topic')}

## Steps

1. Read `global-style.txt` and keep it consistent in Google Flow.
2. Generate **MASTER REFERENCES** first (`references/characters|locations|objects`).
3. Work in batches of {batch_size} (`BATCH_01` = shots 001–{min(n, batch_size):03d}, …). Total shots: {n}.
4. For each shot, copy the PROMPT from FrameFactory Flow Workspace (or `shots/NNN.txt`).
5. Download images as zero-padded files: `001.png`, `002.png`, …
6. Import the folder into FrameFactory → Images (bulk import).

Do **not** invent new wardrobe/architecture when a CHAR/LOC reference exists.
"""
