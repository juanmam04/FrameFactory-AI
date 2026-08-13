"""Assemble + render documentary stills + voice via montar_video."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from src.config_loader import get_background_music_path

from src.documentary.import_images import ordered_images_for_render
from src.documentary.project import _utc_now, append_log, load_project, project_dir, save_project, set_checkpoint
from src.video_assembler import montar_slideshow, mp4_is_complete, verificar_ffmpeg


def set_render_state(
    project: dict[str, Any],
    state: str,
    *,
    message: str = "",
    error: str = "",
) -> dict[str, Any]:
    rec = dict(project.get("render") or {}) if isinstance(project.get("render"), dict) else {}
    now = _utc_now()
    rec["state"] = state
    rec["updated_at"] = now
    if state == "running":
        rec["started_at"] = now
        rec["finished_at"] = ""
        rec["error"] = ""
        rec["cancelled"] = False
        rec["message"] = message or "Armando el video…"
        set_checkpoint(project, "render_ready", False)
        try:
            flag = project_dir(str(project.get("id") or "")) / "render" / "cancel.flag"
            flag.unlink(missing_ok=True)
        except Exception:
            pass
    elif state == "done":
        rec["finished_at"] = now
        rec["error"] = ""
        rec["message"] = message or "Terminado. Ya lo podés descargar."
        set_checkpoint(project, "render_ready", True)
    elif state == "error":
        rec["finished_at"] = now
        rec["error"] = (error or message or "Falló el render.")[:400]
        rec["message"] = rec["error"]
        set_checkpoint(project, "render_ready", False)
    else:
        rec["state"] = "idle"
        rec["message"] = message or "Todavía no se armó el video."
        rec["error"] = ""
    project["render"] = rec
    save_project(project)
    return rec


class RenderCancelled(Exception):
    """User stopped the render."""


def cancel_flag_path(project_id: str) -> Path:
    return project_dir(project_id) / "render" / "cancel.flag"


def cancel_render(project: dict[str, Any]) -> dict[str, Any]:
    pid = str(project["id"])
    flag = cancel_flag_path(pid)
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("1", encoding="utf-8")
    rec = set_render_state(project, "idle", message="Frenaste el render.")
    rec["cancelled"] = True
    rec["state"] = "idle"
    rec["message"] = "Frenaste el render."
    project["render"] = rec
    save_project(project)
    append_log(pid, "render cancelled by user")
    return rec


def render_was_cancelled(project_id: str) -> bool:
    flag = cancel_flag_path(project_id)
    if flag.is_file():
        return True
    try:
        from src.documentary import cloud_sync

        if cloud_sync.configured():
            cloud_sync.pull_one(project_id, "render/cancel.flag", force=True)
            if flag.is_file():
                return True
            cloud_sync.pull_one(project_id, "project.json", force=True)
        p = load_project(project_id)
        rec = p.get("render") if isinstance(p.get("render"), dict) else {}
        if rec.get("cancelled"):
            return True
    except Exception:
        pass
    return False


def _abort_if_cancelled(project_id: str) -> None:
    if render_was_cancelled(project_id):
        raise RenderCancelled("Frenaste el render.")


MAX_STILL_SEC = 7.0
DEFAULT_EDIT = {
    "seconds_per_image": 6.0,
    "motion": "mix",
    "transition": "fade",
    "music_volume": 0.08,
    "look": "soft",
}


def edit_settings(project: dict[str, Any]) -> dict[str, Any]:
    rec = {}
    if isinstance(project.get("render"), dict):
        rec = dict((project["render"].get("edit") or {}))
    sec = float(rec.get("seconds_per_image") or DEFAULT_EDIT["seconds_per_image"])
    sec = min(MAX_STILL_SEC, max(4.0, sec))
    motion = str(rec.get("motion") or "mix")
    if motion not in ("push", "pull", "pan", "mix"):
        motion = "mix"
    trans = str(rec.get("transition") or "fade")
    if trans not in ("fade", "cut"):
        trans = "fade"
    vol = float(rec.get("music_volume") or 0.08)
    vol = min(0.18, max(0.04, vol))
    look = str(rec.get("look") or "soft")
    if look not in ("none", "soft", "film"):
        look = "soft"
    return {
        "seconds_per_image": sec,
        "motion": motion,
        "transition": trans,
        "music_volume": vol,
        "look": look,
    }


def expand_stills_for_voice(
    images: list[Path],
    duration_sec: float | None,
    max_sec: float = MAX_STILL_SEC,
) -> tuple[list[Path], float]:
    """No still longer than max_sec. Cycle the pool if the voice is longer."""
    n = len(images)
    if n == 0:
        return [], 6.0
    dur = float(duration_sec or 0)
    if dur <= 0:
        return images, min(max_sec, 6.0)
    n_needed = max(n, int(math.ceil(dur / max_sec)))
    seq = [images[i % n] for i in range(n_needed)]
    sec = dur / len(seq)
    return seq, min(max_sec, max(2.8, sec))


def save_edit_settings(project: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    rec = dict(project.get("render") or {}) if isinstance(project.get("render"), dict) else {}
    edit = dict(rec.get("edit") or {})
    edit.update({k: v for k, v in body.items() if v is not None})
    rec["edit"] = edit_settings({**project, "render": {**rec, "edit": edit}})
    project["render"] = rec
    save_project(project)
    return rec["edit"]


def build_preview(project: dict[str, Any]) -> dict[str, Any]:
    pid = str(project["id"])
    images, missing = ordered_images_for_render(pid)
    audio = project_dir(pid) / "audio" / "narration.mp3"
    voice_ok = audio.exists() and audio.stat().st_size > 0
    duration = (project.get("voice") or {}).get("duration_sec")
    n = len(images)
    edit = edit_settings(project)
    _, sec_each = expand_stills_for_voice(images, duration, max_sec=float(edit["seconds_per_image"]))
    long_shots = []
    if duration and n and float(duration) / n > MAX_STILL_SEC:
        long_shots.append(
            f"faltan fotos para cubrir la voz: la IA reutiliza las que encajan "
            f"(máx {edit['seconds_per_image']:.0f}s cada una)"
        )
    preview = {
        "image_count": n,
        "missing_images": missing,
        "voice_ok": voice_ok,
        "voice_duration_sec": duration,
        "seconds_per_image": sec_each,
        "warnings": long_shots
        + ([f"faltan bloques {', '.join(missing[:8])}: se reutilizan fotos del relato"] if missing else [])
        + ([] if voice_ok else ["voice missing"]),
        "ready_to_assemble": bool(n and voice_ok),
    }
    project["preview"] = preview
    save_project(project)
    return preview


def _pull_render_assets(project_id: str) -> None:
    from src.documentary import cloud_sync

    if not cloud_sync.configured():
        return
    cloud_sync.pull_one(project_id, "audio/narration.mp3")
    cloud_sync.pull_one(project_id, "flow-pack/shot-list.json")
    cloud_sync.pull_prefix(project_id, "images/")


def assemble_and_render(
    project: dict[str, Any],
    *,
    allow_missing: bool = False,
    transiciones_suaves: bool = True,
) -> Path:
    from src.documentary.runtime import on_vercel

    if on_vercel():
        _pull_render_assets(str(project["id"]))
    if not verificar_ffmpeg():
        raise RuntimeError("Rendering needs FFmpeg installed and available in your PATH.")
    pid = str(project["id"])
    preview = build_preview(project)
    if not preview["voice_ok"]:
        raise RuntimeError("Voice is not ready yet. Generate voice before rendering.")
    if not preview["image_count"] and not allow_missing:
        raise RuntimeError("No images found to assemble. Import Flow stills first.")

    audio = project_dir(pid) / "audio" / "narration.mp3"
    music = _resolve_music(project)
    edit = edit_settings(project)
    music_vol = float(edit["music_volume"])
    duration = (project.get("voice") or {}).get("duration_sec")
    from src.documentary.reuse_stills import plan_still_timeline

    images, sec, reuse = plan_still_timeline(
        project, duration, max_sec=float(edit["seconds_per_image"])
    )
    if not images:
        raise RuntimeError("No images found to assemble. Import Flow stills first.")

    out = project_dir(pid) / "render" / "final.mp4"
    # versioned backup if exists
    if out.exists():
        bak = project_dir(pid) / "render" / f"final_backup_{_ts()}.mp4"
        out.replace(bak)

    log_path = project_dir(pid) / "logs" / "render.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    vercel = on_vercel()
    if vercel:
        width, height, fps, crf, preset = 1920, 1080, 24, 17, "veryfast"
        editorial = float(duration or 0) <= 30
        quality_label = "Full HD 1080p"
    else:
        width, height, fps, crf, preset = 3840, 2160, 24, 16, "medium"
        editorial = True
        quality_label = "4K"
    try:
        _abort_if_cancelled(pid)
        try:
            from src.documentary.captions import captions_srt_path, generate_captions

            srt = captions_srt_path(pid)
            if not srt.is_file() or srt.stat().st_size <= 0:
                generate_captions(project)
        except Exception as e:
            append_log(pid, f"captions srt skip: {e}")
        result = montar_slideshow(
            images,
            audio,
            out,
            segundos_por_imagen=sec,
            width=width,
            height=height,
            musica_fondo=music,
            music_volume=music_vol,
            duration_sec=float(duration or 0) or None,
            motion=str(edit["motion"]),
            transition=str(edit["transition"]),
            fps=fps,
            crf=crf,
            preset=preset,
            editorial=editorial,
            look=str(edit.get("look") or "soft"),
        )
        _abort_if_cancelled(pid)
        if not mp4_is_complete(Path(result)):
            Path(result).unlink(missing_ok=True)
            raise RuntimeError("El render no terminó bien (video incompleto). Probá de nuevo.")
        try:
            import shutil as _sh

            from src.documentary.captions import master_video_path

            _sh.copy2(Path(result), master_video_path(pid))
        except Exception:
            pass
        burned = False
        try:
            from src.documentary.captions import burn_into_final

            burn_into_final(project, width=width)
            burned = True
        except Exception as cap_err:
            append_log(pid, f"captions burn skip: {cap_err}")
        _abort_if_cancelled(pid)
        set_checkpoint(project, "assembly_ready", True)
        set_checkpoint(project, "render_ready", True)
        if burned:
            set_checkpoint(project, "captions_ready", True)
        rec = dict(project.get("render") or {}) if isinstance(project.get("render"), dict) else {}
        msg = (
            f"Terminado · {quality_label} · subtítulos incluidos."
            if burned
            else f"Terminado · {quality_label}. Los subtítulos no se pudieron quemar."
        )
        filled = int((reuse or {}).get("filled") or 0)
        if filled:
            how = "IA" if (reuse or {}).get("method") == "ai" else "criterio"
            msg += f" Reutilizó {filled} tomas con {how}."
        rec.update(
            {
                "path": "render/final.mp4",
                "seconds_per_image": sec,
                "width": width,
                "height": height,
                "fps": fps,
                "reuse": reuse,
                "state": "done",
                "message": msg,
                "error": "",
                "finished_at": _utc_now(),
            }
        )
        project["render"] = rec
        if isinstance(project.get("captions"), dict):
            project["captions"]["burned"] = burned
        save_project(project)
        append_log(pid, f"render ok → {result} {quality_label} captions={burned}")
        log_path.write_text(f"OK {result}\n", encoding="utf-8")
        return Path(result)
    except RenderCancelled:
        append_log(pid, "render stopped by user")
        raise
    except Exception as e:
        append_log(pid, f"render FAIL: {e}")
        log_path.write_text(f"FAIL {e}\n", encoding="utf-8")
        try:
            set_render_state(project, "error", error=str(e)[:400])
        except Exception:
            pass
        raise


def _resolve_music(project: dict[str, Any]) -> Path | None:
    mp = str(project.get("music_path") or "").strip()
    if mp:
        cand = Path(mp).expanduser()
        if cand.is_file():
            return cand
    try:
        env_m = get_background_music_path()
        if env_m and Path(env_m).is_file():
            return Path(env_m)
    except Exception:
        pass
    try:
        from src.documentary.music_bed import documentary_bed_path

        bed = documentary_bed_path()
        if bed.is_file() and bed.stat().st_size > 0:
            return bed
    except Exception:
        return None
    return None


def _pull_preview_assets(project_id: str) -> None:
    """Don't pull the whole still library just to test 20 seconds."""
    from src.documentary import cloud_sync
    from src.documentary.import_images import list_project_images

    if not cloud_sync.configured():
        return
    cloud_sync.pull_one(project_id, "audio/narration.mp3")
    if len(list_project_images(project_id)) >= 3:
        return
    try:
        rels = cloud_sync.list_rel_paths(project_id, "images/")
    except Exception:
        rels = []
    n = 0
    for rel in sorted(rels):
        low = rel.lower()
        if ".thumb." in low:
            continue
        if not low.endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        cloud_sync.pull_one(project_id, rel)
        n += 1
        if n >= 6:
            break


def assemble_preview_clip(project: dict[str, Any]) -> Path:
    """~20s editorial test: few stills, Ken Burns, vignette, music, first seconds of VO."""
    from src.documentary.runtime import on_vercel

    pid = str(project["id"])
    if on_vercel():
        _pull_preview_assets(pid)
    if not verificar_ffmpeg():
        raise RuntimeError("No hay FFmpeg en este servidor.")
    images, _missing = ordered_images_for_render(pid)
    if not images:
        raise RuntimeError("Subí imágenes antes de probar el render.")
    audio = project_dir(pid) / "audio" / "narration.mp3"
    if not audio.is_file() or audio.stat().st_size <= 0:
        raise RuntimeError("Generá la voz antes de probar el video.")
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in images:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
        if len(uniq) >= 4:
            break
    while len(uniq) < 3:
        uniq.append(images[len(uniq) % len(images)])
    edit = edit_settings(project)
    sec = min(5.0, float(edit["seconds_per_image"]))
    dur = min(20.0, sec * len(uniq))
    out = project_dir(pid) / "render" / "preview.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    montar_slideshow(
        uniq,
        audio,
        out,
        segundos_por_imagen=sec,
        width=1280,
        height=720,
        musica_fondo=_resolve_music(project),
        music_volume=max(0.08, float(edit["music_volume"])),
        duration_sec=dur,
        motion=str(edit["motion"]),
        transition=str(edit["transition"]),
        fps=24,
        crf=20,
        preset="veryfast",
        editorial=True,
        look=str(edit.get("look") or "soft"),
    )
    if not mp4_is_complete(out):
        raise RuntimeError("La prueba no se pudo armar. Probá de nuevo.")
    rec = dict(project.get("render") or {}) if isinstance(project.get("render"), dict) else {}
    rec["preview"] = "render/preview.mp4"
    rec["edit"] = edit
    project["render"] = rec
    save_project(project)
    append_log(pid, f"render preview ok {dur:.0f}s")
    return out


def _ts() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d_%H%M%S")
