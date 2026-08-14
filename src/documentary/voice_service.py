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

    if velocidad is not None:
        speed = float(velocidad)
    else:
        raw = project.get("voice_speed")
        speed = 1.2 if raw in (None, "", 1, 1.0) else float(raw)
    speed = max(0.8, min(1.5, speed))
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
    project["voice_speed"] = speed
    project["voice"] = {"path": "audio/narration.mp3", "duration_sec": duration, "speed": speed}
    # Old captions were timed guesses / stale Whisper — wipe so the next burn re-aligns to this take.
    try:
        from src.documentary.captions import captions_srt_path, clear_burned_captions

        srt = captions_srt_path(str(project["id"]))
        if srt.is_file():
            srt.unlink(missing_ok=True)
        preview_srt = project_dir(str(project["id"])) / "render" / "captions_preview.srt"
        if preview_srt.is_file():
            preview_srt.unlink(missing_ok=True)
        clear_burned_captions(str(project["id"]))
    except Exception:
        pass
    project["captions"] = {"burned": False, "source": "", "voice_fp": ""}
    set_checkpoint(project, "captions_ready", False)
    set_checkpoint(project, "voice_ready", True)
    set_checkpoint(project, "assembly_ready", False)
    set_checkpoint(project, "render_ready", False)
    save_project(project)
    append_log(str(project["id"]), f"voice ready duration={duration}")
    return dest


def _probe_duration(path: Path) -> float | None:
    import re
    import subprocess

    from src.video_assembler import ffmpeg_exe

    ff = ffmpeg_exe()
    if not ff:
        return None
    try:
        r = subprocess.run([ff, "-i", str(path)], capture_output=True, text=True, timeout=30)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr or "")
        if not m:
            return None
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        return None
