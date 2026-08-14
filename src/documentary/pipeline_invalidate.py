"""Cascade invalidation: when voice/script changes, wipe everything derived from it."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from src.documentary.project import append_log, project_dir, save_project, set_checkpoint

# Anything that embeds or depends on narration.mp3 / script timing.
VOICE_DERIVED_RELS = [
    "render/preview.mp4",
    "render/preview_master.mp4",
    "render/preview_burn.mp4",
    "render/narration_head.mp3",
    "render/captions_preview.srt",
    "render/captions.srt",
    "render/captions.ass",
    "render/final.mp4",
    "render/final_master.mp4",
    "render/final_captions.mp4",
    "render/final_burn.mp4",
]


def file_sha256(path: Path, *, limit: int | None = None) -> str:
    if not path.is_file() or path.stat().st_size <= 0:
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        if limit is None:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        else:
            h.update(f.read(max(0, int(limit))))
    return h.hexdigest()[:24]


def narration_fingerprint(project_id: str) -> dict[str, Any]:
    audio = project_dir(project_id) / "audio" / "narration.mp3"
    size = int(audio.stat().st_size) if audio.is_file() else 0
    return {
        "audio_sha": file_sha256(audio) if size else "",
        "audio_bytes": size,
    }


def preview_matches_voice(project: dict[str, Any]) -> bool:
    """True only if the on-disk preview was built from the current voice take."""
    pid = str(project.get("id") or "")
    prev = project_dir(pid) / "render" / "preview.mp4"
    if not prev.is_file() or prev.stat().st_size <= 0:
        return False
    voice = project.get("voice") if isinstance(project.get("voice"), dict) else {}
    meta = ((project.get("render") or {}).get("preview_meta") or {}) if isinstance(project.get("render"), dict) else {}
    v_hash = str(voice.get("script_hash") or "").strip()
    v_sha = str(voice.get("audio_sha") or "").strip()
    m_hash = str(meta.get("voice_script_hash") or "").strip()
    m_sha = str(meta.get("audio_sha") or "").strip()
    if not v_hash or not m_hash or v_hash != m_hash:
        return False
    if v_sha and m_sha and v_sha != m_sha:
        return False
    return True


def wipe_voice_derived(project: dict[str, Any], *, reason: str = "voice changed") -> dict[str, Any]:
    """Delete local + cloud artifacts that must be rebuilt after a new narration."""
    pid = str(project.get("id") or "")
    root = project_dir(pid)
    removed: list[str] = []
    for rel in VOICE_DERIVED_RELS:
        path = root / rel
        try:
            if path.is_file():
                path.unlink(missing_ok=True)
                removed.append(rel)
        except OSError:
            pass

    try:
        from src.documentary import cloud_sync

        if cloud_sync.configured():
            cloud_sync.delete_paths(pid, VOICE_DERIVED_RELS)
    except Exception as e:
        append_log(pid, f"wipe derived cloud skip: {e}")

    rec = dict(project.get("render") or {}) if isinstance(project.get("render"), dict) else {}
    rec.pop("preview", None)
    rec.pop("preview_meta", None)
    if str(rec.get("stage") or "").startswith("preview"):
        rec["stage"] = "idle"
        rec["message"] = "Voz nueva — hay que volver a armar la prueba / el episodio."
        rec["percent"] = 0
    project["render"] = rec
    project["captions"] = {"burned": False, "source": "", "voice_fp": ""}
    set_checkpoint(project, "captions_ready", False)
    set_checkpoint(project, "assembly_ready", False)
    set_checkpoint(project, "render_ready", False)
    append_log(pid, f"invalidated voice-derived ({reason}) removed={len(removed)}")
    return project


def stamp_voice_fingerprint(project: dict[str, Any]) -> dict[str, Any]:
    pid = str(project.get("id") or "")
    fp = narration_fingerprint(pid)
    voice = dict(project.get("voice") or {})
    voice.update(fp)
    project["voice"] = voice
    return project
