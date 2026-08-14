"""Keep narration audio locked to the approved script text."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from src.documentary.project import project_dir, save_project, set_checkpoint


def normalize_script(script: str) -> str:
    return re.sub(r"\s+", " ", (script or "").strip())


def script_hash(script: str) -> str:
    return hashlib.sha256(normalize_script(script).encode("utf-8")).hexdigest()[:20]


def voice_script_hash(project: dict[str, Any]) -> str:
    voice = project.get("voice") if isinstance(project.get("voice"), dict) else {}
    return str(voice.get("script_hash") or "").strip()


def voice_matches_script(project: dict[str, Any]) -> bool:
    script = str(project.get("script") or "").strip()
    if not script:
        return False
    stored = voice_script_hash(project)
    if not stored:
        return False
    return stored == script_hash(script)


def invalidate_voice_for_script_change(project: dict[str, Any], *, reason: str = "script changed") -> dict[str, Any]:
    """Mark voice stale when the script no longer matches the take on disk."""
    if not (project.get("voice") or project.get("checkpoints", {}).get("voice_ready")):
        return project
    if voice_matches_script(project):
        return project
    voice = dict(project.get("voice") or {})
    voice["stale"] = True
    voice["stale_reason"] = reason
    project["voice"] = voice
    set_checkpoint(project, "voice_ready", False)
    set_checkpoint(project, "assembly_ready", False)
    set_checkpoint(project, "render_ready", False)
    set_checkpoint(project, "captions_ready", False)
    return project


def require_voice_matches_script(project: dict[str, Any]) -> None:
    if not voice_matches_script(project):
        raise RuntimeError(
            "La voz no es de este guion (quedó de una toma vieja o el texto cambió). "
            "Andá a Voz → Volver a generar voz, y recién después probá el video."
        )


def word_overlap(a: str, b: str, *, limit: int = 100) -> float:
    wa = re.findall(r"[a-z0-9']+", (a or "").lower())[:limit]
    wb = set(re.findall(r"[a-z0-9']+", (b or "").lower())[:limit])
    if not wa or not wb:
        return 0.0
    hit = sum(1 for w in wa if w in wb)
    return hit / max(1, len(wa))


def save_narration_script(project_id: str, script: str) -> None:
    root = project_dir(project_id)
    (root / "audio").mkdir(parents=True, exist_ok=True)
    (root / "audio" / "narration_script.txt").write_text(normalize_script(script) + "\n", encoding="utf-8")
