"""Assemble + render documentary stills + voice via montar_video."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config_loader import get_background_music_path
from src.documentary.import_images import ordered_images_for_render
from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.video_assembler import montar_slideshow, montar_video, verificar_ffmpeg


def build_preview(project: dict[str, Any]) -> dict[str, Any]:
    pid = str(project["id"])
    images, missing = ordered_images_for_render(pid)
    audio = project_dir(pid) / "audio" / "narration.mp3"
    voice_ok = audio.exists() and audio.stat().st_size > 0
    duration = (project.get("voice") or {}).get("duration_sec")
    n = len(images)
    sec_each = None
    if duration and n:
        sec_each = float(duration) / n
    long_shots = []
    if sec_each and sec_each > 14:
        long_shots.append(f"avg still length {sec_each:.1f}s (>14s) — consider more images")
    preview = {
        "image_count": n,
        "missing_images": missing,
        "voice_ok": voice_ok,
        "voice_duration_sec": duration,
        "seconds_per_image": sec_each,
        "warnings": long_shots
        + ([f"missing {len(missing)} images"] if missing else [])
        + ([] if voice_ok else ["voice missing"]),
        "ready_to_assemble": bool(n and voice_ok and not missing),
    }
    project["preview"] = preview
    save_project(project)
    return preview


def _pull_render_assets(project_id: str) -> None:
    from src.documentary import cloud_sync
    from src.documentary.flow_pack import load_shot_list
    from src.documentary.import_images import still_file

    if not cloud_sync.configured():
        return
    cloud_sync.pull_one(project_id, "audio/narration.mp3")
    root = project_dir(project_id) / "images"
    try:
        shots = load_shot_list(project_id).get("shots") or []
        nums = [int(s["number"]) for s in shots if s.get("number")]
    except Exception:
        nums = list(range(1, 80))
    for n in nums:
        if still_file(root, n) is not None:
            continue
        for name in (f"{n:03d}.jpg", f"{n:03d}.png", f"{n:03d}.webp", f"{n:03d}.jpeg"):
            if cloud_sync.pull_one(project_id, f"images/{name}"):
                break


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
    if preview["missing_images"] and not allow_missing:
        miss = preview["missing_images"]
        raise RuntimeError(
            f"Falta el bloque de imágenes: " + ", ".join(miss[:40]) + ("…" if len(miss) > 40 else "")
        )
    if not preview["voice_ok"]:
        raise RuntimeError("Voice is not ready yet. Generate voice before rendering.")

    images, _missing = ordered_images_for_render(pid)
    if not images:
        raise RuntimeError("No images found to assemble. Import Flow stills first.")

    audio = project_dir(pid) / "audio" / "narration.mp3"
    music = None
    mp = str(project.get("music_path") or "").strip()
    if mp:
        cand = Path(mp).expanduser()
        if cand.is_file():
            music = cand
    if music is None:
        try:
            env_m = get_background_music_path()
            if env_m and Path(env_m).is_file():
                music = Path(env_m)
        except Exception:
            pass
    music_vol = float(project.get("music_volume") or 0.08)
    if music_vol >= 0.12:
        music_vol = 0.08

    duration = (project.get("voice") or {}).get("duration_sec")
    sec = float(duration) / len(images) if duration else None
    if sec is None:
        sec = 6.0
    sec = max(2.5, min(20.0, float(sec)))

    out = project_dir(pid) / "render" / "final.mp4"
    # versioned backup if exists
    if out.exists():
        bak = project_dir(pid) / "render" / f"final_backup_{_ts()}.mp4"
        out.replace(bak)

    log_path = project_dir(pid) / "logs" / "render.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if on_vercel():
            result = montar_slideshow(
                images,
                audio,
                out,
                segundos_por_imagen=sec,
                width=1280,
                height=720,
                musica_fondo=music,
                music_volume=music_vol,
            )
        else:
            result = montar_video(
                lista_imagenes=images,
                audio_narracion=audio,
                musica_fondo=music,
                segundos_por_imagen=sec,
                width=1920,
                height=1080,
                transiciones_suaves=transiciones_suaves,
                output_path=out,
                music_volume=music_vol,
            )
        set_checkpoint(project, "assembly_ready", True)
        set_checkpoint(project, "render_ready", True)
        set_checkpoint(project, "captions_ready", False)
        try:
            from src.documentary.captions import clear_burned_captions

            clear_burned_captions(pid)
        except Exception:
            pass
        project["render"] = {"path": "render/final.mp4", "seconds_per_image": sec}
        if isinstance(project.get("captions"), dict):
            project["captions"]["burned"] = False
        save_project(project)
        append_log(pid, f"render ok → {result}")
        log_path.write_text(f"OK {result}\n", encoding="utf-8")
        return Path(result)
    except Exception as e:
        append_log(pid, f"render FAIL: {e}")
        log_path.write_text(f"FAIL {e}\n", encoding="utf-8")
        raise


def _ts() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d_%H%M%S")
