"""Documentary 100-days: project workspace + checkpoints (FF100-P0-001/002)."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import os

from dotenv import load_dotenv

from src.config_loader import BASE

# Ensure .env / .env.local are loaded before reading workspace paths.
load_dotenv(BASE / ".env")
for _env_local in (BASE / ".env.local", BASE / "env.local"):
    if _env_local.is_file():
        load_dotenv(_env_local, override=True)


def _resolve_dir(env_name: str, default: Path) -> Path:
    raw = (os.getenv(env_name) or "").strip().strip('"').strip("'")
    if not raw:
        return default
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (BASE / p).resolve()
    return p


# Multi-PC: set FRAMEFACTORY_WORKSPACE to a cloud-synced folder (OneDrive/Drive/Dropbox).
# Example: FRAMEFACTORY_WORKSPACE=C:\Users\You\OneDrive\FrameFactory-Data
_WORKSPACE = _resolve_dir("FRAMEFACTORY_WORKSPACE", BASE)
if (os.getenv("FRAMEFACTORY_PROJECTS_DIR") or "").strip():
    PROJECTS_ROOT = _resolve_dir("FRAMEFACTORY_PROJECTS_DIR", _WORKSPACE / "projects")
else:
    PROJECTS_ROOT = _WORKSPACE / "projects"

CHECKPOINT_KEYS = (
    "script_ready",
    "flow_pack_ready",
    "images_imported",
    "voice_ready",
    "assembly_ready",
    "render_ready",
)

# Human-facing progress steps (UI). Internal checkpoints still drive gates.
# Topic = idea/topic selection; Story = Story Plan (engine + beats).
PROGRESS_STEPS = (
    "topic",
    "research",
    "story",
    "script",
    "flow",
    "images",
    "voice",
    "render",
    "done",
)

DEFAULT_PROJECT: dict[str, Any] = {
    "id": "",
    "slug": "",
    "mode": "documentary",
    "title": "",
    "topic": "",
    "language": "en",
    "target_words": 2000,
    "target_duration_min": [11, 15],
    "research_notes": "",
    "sources": [],
    "research_skipped": False,
    "script": "",
    "fact_check_status": "pending",  # pending | approved | needs_fixes
    "script_approved": False,
    "story_plan": {},
    "story_plan_approved": False,
    "voice_speed": 1.0,
    "music_path": "",
    "music_volume": 0.12,
    "subtitles_enabled": True,
    "batch_size": 10,
    "flow_shot_index": 0,
    "flow_batch_index": 0,
    "session_id": "",
    "episode_number": 0,
    "idea": {},
    "creative_profile_snapshot": {},
    "ui_step": "research",
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
    from src.documentary.runtime import configure_workspace

    configure_workspace()
    raw = (os.getenv("FRAMEFACTORY_PROJECTS_DIR") or "").strip()
    root = Path(raw) if raw else (BASE / "projects")
    if not root.is_absolute():
        root = (BASE / root).resolve()
    globals()["PROJECTS_ROOT"] = root
    root.mkdir(parents=True, exist_ok=True)
    return root


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
        "flow-import",
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
    if not isinstance(merged.get("idea"), dict):
        merged["idea"] = {}
    if not isinstance(merged.get("creative_profile_snapshot"), dict):
        merged["creative_profile_snapshot"] = {}
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


def list_projects_for_session(session_id: str | None) -> list[dict[str, Any]]:
    sid = str(session_id or "").strip()
    if not sid:
        return list_projects()
    return [p for p in list_projects() if str(p.get("session_id") or "") == sid]


def next_numeric_prefix(session_id: str | None = None) -> str:
    n = 1
    pool = list_projects_for_session(session_id) if session_id else list_projects()
    for p in pool:
        m = re.match(r"^(\d+)-", str(p.get("id") or ""))
        if m:
            n = max(n, int(m.group(1)) + 1)
        ep = p.get("episode_number")
        try:
            n = max(n, int(ep) + 1)
        except (TypeError, ValueError):
            pass
    return f"{n:03d}"


def next_episode_number(session_id: str | None) -> int:
    return int(next_numeric_prefix(session_id))


def create_project(
    topic: str,
    *,
    title: str | None = None,
    project_id: str | None = None,
    target_words: int = 2000,
    research_notes: str = "",
    sources: list[str] | None = None,
    session_id: str | None = None,
    creative_profile: dict[str, Any] | None = None,
    idea: dict[str, Any] | None = None,
    language: str = "en",
    target_duration_min: list[int] | None = None,
    episode_number: int | None = None,
) -> dict[str, Any]:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic required")
    title = (title or topic).strip()
    slug = slugify(title)
    sid = str(session_id or "").strip()
    ep = int(episode_number) if episode_number else next_episode_number(sid or None)
    pid = (project_id or f"{ep:03d}-{slug}").strip()
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
            "language": (language or "en").strip() or "en",
            "target_words": int(max(800, min(2500, target_words))),
            "target_duration_min": list(target_duration_min or [11, 15]),
            "research_notes": research_notes or "",
            "sources": list(sources or []),
            "session_id": sid,
            "episode_number": ep,
            "idea": dict(idea or {}),
            "creative_profile_snapshot": deepcopy(creative_profile) if isinstance(creative_profile, dict) else {},
            "ui_step": "research",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
    )
    save_project(data)
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
    if idea:
        (root / "metadata" / "idea.json").write_text(
            json.dumps(idea, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return data


def append_log(project_id: str, message: str) -> None:
    root = project_dir(project_id)
    ensure_layout(root)
    line = f"{_utc_now()} {message}\n"
    with (root / "logs" / "pipeline.log").open("a", encoding="utf-8") as f:
        f.write(line)


def derive_progress(project: dict[str, Any]) -> dict[str, Any]:
    """Map checkpoints → human stepper without exposing internal names."""
    cps = project.get("checkpoints") or {}
    # migrate legacy ui_step "story" (old topic step) → topic
    ui = str(project.get("ui_step") or "").strip()
    if ui == "story" and not (project.get("story_plan") or {}).get("central_story"):
        # ambiguous legacy: if no plan, treat as topic
        pass

    has_topic = bool(str(project.get("topic") or "").strip())
    has_research = bool(
        str(project.get("research_notes") or "").strip()
        or (project.get("sources") or [])
        or project.get("research_skipped")
    )
    has_story_plan = bool(
        project.get("story_plan_approved")
        or ((project.get("story_plan") or {}).get("approved"))
    )
    has_script = bool(str(project.get("script") or "").strip())
    approved = bool(project.get("script_approved"))
    flow = bool(cps.get("flow_pack_ready"))
    report = project.get("import_report") or {}
    expected = int(report.get("expected") or 0)
    ready = int(report.get("ready") or 0)
    images_full = bool(cps.get("images_imported")) and (expected == 0 or ready >= expected)
    images_partial = bool(cps.get("images_imported"))
    voice = bool(cps.get("voice_ready"))
    rendered = bool(cps.get("render_ready")) and (project_dir(str(project["id"])) / "render" / "final.mp4").exists()

    flags = {
        "topic": has_topic,
        "research": has_research,
        "story": has_story_plan,
        "script": has_script and approved,
        "flow": flow,
        "images": images_full or (images_partial and voice),
        "voice": voice,
        "render": rendered,
        "done": rendered,
    }
    current = "done"
    for step in PROGRESS_STEPS:
        if step == "done":
            continue
        if not flags.get(step):
            if step == "story" and (project.get("story_plan") or {}).get("central_story") and not has_story_plan:
                current = "story"
                break
            if step == "script" and has_script and not approved:
                current = "script"
                break
            if step == "images" and flow and not images_full:
                current = "images"
                break
            current = step
            break
    else:
        current = "done" if rendered else "render"

    if rendered:
        current = "done"
        flags["done"] = True

    return {"steps": list(PROGRESS_STEPS), "flags": flags, "current": current}


def session_stats(session_id: str | None, goal: int = 100) -> dict[str, int]:
    items = list_projects_for_session(session_id)
    completed = 0
    in_progress = 0
    for p in items:
        cps = p.get("checkpoints") or {}
        if cps.get("render_ready"):
            completed += 1
        else:
            in_progress += 1
    remaining = max(0, int(goal) - completed)
    day = completed + 1 if completed < goal else goal
    return {
        "total_projects": len(items),
        "completed": completed,
        "in_progress": in_progress,
        "remaining": remaining,
        "goal": int(goal),
        "day": min(day, int(goal)),
    }
