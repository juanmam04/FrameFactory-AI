"""Documentary voice: single continuous narration (FF100-P0-006/007)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.voice_generator import OUTPUT_AUDIO, generar_voz


def generate_project_voice(project: dict[str, Any], *, velocidad: float | None = None) -> Path:
    from src.documentary.credentials import check_elevenlabs, check_openai

    script = str(project.get("script") or "").strip()
    if not script:
        raise ValueError("No script yet. Generate a script before voice.")
    if not project.get("script_approved"):
        raise ValueError("Approve the script before generating voice.")

    oa = check_openai(live=False)
    el = check_elevenlabs(live=False)
    if oa.status != "ok" and el.status != "ok":
        details = []
        if oa.status != "ok":
            details.append(f"OpenAI: {oa.detail}")
        if el.status not in ("ok", "missing"):
            details.append(f"ElevenLabs: {el.detail}")
        elif el.status == "missing":
            details.append("ElevenLabs: not configured")
        raise RuntimeError(
            "Voice blocked — no working TTS provider.\n" + "\n".join(details)
        )

    speed = float(velocidad if velocidad is not None else project.get("voice_speed") or 1.0)
    # Generate into global OUTPUT_AUDIO then copy into project workspace (stem unique)
    stem = f"doc_{project['id']}_narration".replace("/", "_")
    path = generar_voz(script, nombre_archivo=stem, formato="mp3", velocidad=speed)
    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError("Voice generation returned empty file")

    dest = project_dir(str(project["id"])) / "audio" / "narration.mp3"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)

    # cleanup global copy optional — keep for debugging
    duration = _probe_duration(dest)
    project["voice"] = {"path": "audio/narration.mp3", "duration_sec": duration, "speed": speed}
    set_checkpoint(project, "voice_ready", True)
    set_checkpoint(project, "assembly_ready", False)
    set_checkpoint(project, "render_ready", False)
    save_project(project)
    append_log(str(project["id"]), f"voice ready duration={duration}")
    return dest


def _probe_duration(path: Path) -> float | None:
    import shutil as sh
    import subprocess

    if not sh.which("ffprobe"):
        return None
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(r.stdout.strip())
    except Exception:
        return None
