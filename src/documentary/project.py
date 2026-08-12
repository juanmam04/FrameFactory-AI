"""Documentary 100-days: project workspace + checkpoints (FF100-P0-001/002)."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config_loader import BASE

PROJECTS_ROOT = BASE / "projects"

CHECKPOINT_KEYS = (
    "script_ready",
    "flow_pack_ready",
    "images_imported",
    "voice_ready",
    "assembly_ready",
    "render_ready",
)

DEFAULT_PROJECT: dict[str, Any] = {
    "id": "",
    "slug": "",
    "mode": "documentary",
    "title": "",
    "topic": "",
    "language": "en",
    "target_words": 1500,
    "target_duration_min": [8, 12],
    "research_notes": "",
    "sources": [],
    "script": "",
    "fact_check_status": "pending",  # pending | approved | needs_fixes
    "script_approved": False,
    "voice_speed": 1.0,
    "music_path": "",
    "music_volume": 0.12,
    "subtitles_enabled": True,
    "batch_size": 10,
    "flow_shot_index": 0,
    "flow_batch_index": 0,
    "checkpoints": {k: False for k in CHECKPOINT_KEYS},
    "import_report": {},
    "preview": {},
    "errors": [],
    "created_at": "",
    "updated_at": "",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str, fallback: str = "project") -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:48] or fallback)


def projects_root() -> Path:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    return PROJECTS_ROOT


def project_dir(project_id: str) -> Path:
    return projects_root() / project_id


def ensure_layout(root: Path) -> None:
    for name in (
        "script",
        "flow-pack",
        "flow-pack/shots",
        "flow-pack/references/characters",
        "flow-pack/references/locations",
        "flow-pack/references/objects",
        "images",
        "audio",
        "render",
        "metadata",
        "logs",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)


def project_json_path(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def load_project(project_id: str) -> dict[str, Any]:
    path = project_json_path(project_id)
    if not path.exists():
        raise FileNotFoundError(f"Documentary project not found: {project_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid project.json: {path}")
    merged = deepcopy(DEFAULT_PROJECT)
    merged.update(data)
    cps = dict(DEFAULT_PROJECT["checkpoints"])
    cps.update(data.get("checkpoints") or {})
    merged["checkpoints"] = cps
    return merged


def save_project(data: dict[str, Any]) -> Path:
    pid = str(data.get("id") or "").strip()
    if not pid:
        raise ValueError("project.id required")
    root = project_dir(pid)
    ensure_layout(root)
    data = deepcopy(data)
    data["updated_at"] = _utc_now()
    path = root / "project.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def set_checkpoint(data: dict[str, Any], key: str, value: bool = True) -> dict[str, Any]:
    if key not in CHECKPOINT_KEYS:
        raise ValueError(f"Unknown checkpoint: {key}")
    cps = dict(data.get("checkpoints") or {})
    cps[key] = bool(value)
    data["checkpoints"] = cps
    return data


def list_projects() -> list[dict[str, Any]]:
    root = projects_root()
    items: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        pj = child / "project.json"
        if not pj.exists():
            continue
        try:
            items.append(load_project(child.name))
        except Exception:
            continue
    return items


def next_numeric_prefix() -> str:
    n = 1
    for p in list_projects():
        m = re.match(r"^(\d+)-", str(p.get("id") or ""))
        if m:
            n = max(n, int(m.group(1)) + 1)
    return f"{n:03d}"


def create_project(
    topic: str,
    *,
    title: str | None = None,
    project_id: str | None = None,
    target_words: int = 1500,
    research_notes: str = "",
    sources: list[str] | None = None,
) -> dict[str, Any]:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic required")
    title = (title or topic).strip()
    slug = slugify(title)
    pid = (project_id or f"{next_numeric_prefix()}-{slug}").strip()
    root = project_dir(pid)
    if root.exists() and (root / "project.json").exists():
        raise FileExistsError(f"Project already exists: {pid}")
    ensure_layout(root)
    data = deepcopy(DEFAULT_PROJECT)
    data.update(
        {
            "id": pid,
            "slug": slug,
            "title": title,
            "topic": topic,
            "target_words": int(max(800, min(2500, target_words))),
            "research_notes": research_notes or "",
            "sources": list(sources or []),
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
    )
    save_project(data)
    # starter research file
    (root / "script" / "research_notes.md").write_text(
        f"# Research — {title}\n\n## Topic\n{topic}\n\n## Notes\n{research_notes or '_Add notes before approving the script._'}\n\n## Sources\n"
        + ("\n".join(f"- {s}" for s in (sources or [])) or "- _Add sources._\n"),
        encoding="utf-8",
    )
    (root / "script" / "fact_checklist.md").write_text(
        "# Fact checklist\n\n"
        "- [ ] Names / companies spelled correctly\n"
        "- [ ] Dates / years verified\n"
        "- [ ] Dollar figures verified or marked UNKNOWN\n"
        "- [ ] No invented quotes\n"
        "- [ ] Ending takeaway is fair (not sensationalized falsehood)\n",
        encoding="utf-8",
    )
    return data


def append_log(project_id: str, message: str) -> None:
    root = project_dir(project_id)
    ensure_layout(root)
    line = f"{_utc_now()} {message}\n"
    with (root / "logs" / "pipeline.log").open("a", encoding="utf-8") as f:
        f.write(line)
