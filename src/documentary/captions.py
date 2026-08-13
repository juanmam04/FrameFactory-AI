"""English documentary captions: SRT from the script, burned onto the render."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.video_assembler import ffmpeg_error_text, ffmpeg_exe, mp4_is_complete

_DOC_STYLE = (
    "Fontname=Arial,Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
    "BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=42,MarginL=48,MarginR=48"
)


def captions_srt_path(project_id: str) -> Path:
    return project_dir(project_id) / "render" / "captions.srt"


def captioned_video_path(project_id: str) -> Path:
    return project_dir(project_id) / "render" / "final_captions.mp4"


def srt_to_cues(srt: str) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", (srt or "").strip())
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        m = re.search(
            r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})",
            lines[1] if not lines[0][0].isdigit() or "-->" in lines[1] else lines[0],
        )
        if not m:
            continue
        text_lines = lines[2:] if "-->" in lines[1] else lines[1:]
        cues.append({"start": m.group(1), "end": m.group(2), "text": "\n".join(text_lines)})
    return cues


def build_srt(script: str, duration_sec: float) -> str:
    pieces = _cue_texts(script)
    if not pieces:
        return ""
    dur = max(8.0, float(duration_sec or 0) or 60.0)
    weights = [max(1, len(p.split())) for p in pieces]
    total = sum(weights) or 1
    t = 0.0
    lines: list[str] = []
    for i, (text, w) in enumerate(zip(pieces, weights)):
        dt = dur * (w / total)
        end = dur if i == len(pieces) - 1 else min(dur, t + dt)
        if end <= t:
            end = min(dur, t + 1.2)
        lines.append(str(i + 1))
        lines.append(f"{_fmt(t)} --> {_fmt(end)}")
        lines.append(text)
        lines.append("")
        t = end
    return "\n".join(lines).strip() + "\n"


def generate_captions(project: dict[str, Any]) -> dict[str, Any]:
    pid = str(project["id"])
    script = str(project.get("script") or "").strip()
    if not script:
        raise ValueError("No hay guion para subtitular.")
    duration = float((project.get("voice") or {}).get("duration_sec") or 0)
    if duration <= 0:
        duration = max(60.0, len(script.split()) / 2.4)
    srt = build_srt(script, duration)
    dest = captions_srt_path(pid)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(srt, encoding="utf-8")
    project["captions"] = {
        "path": "render/captions.srt",
        "cues": len(srt_to_cues(srt)),
        "burned": False,
    }
    set_checkpoint(project, "captions_ready", False)
    save_project(project)
    append_log(pid, f"captions srt cues={project['captions']['cues']}")
    return {"srt": srt, "cues": srt_to_cues(srt), "burned": False}


def save_captions(project: dict[str, Any], srt: str) -> dict[str, Any]:
    pid = str(project["id"])
    text = (srt or "").strip()
    if not text:
        raise ValueError("Subtítulos vacíos.")
    dest = captions_srt_path(pid)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text + "\n", encoding="utf-8")
    burned = captioned_video_path(pid)
    if burned.is_file():
        burned.unlink(missing_ok=True)
    project["captions"] = {
        "path": "render/captions.srt",
        "cues": len(srt_to_cues(text)),
        "burned": False,
    }
    set_checkpoint(project, "captions_ready", False)
    save_project(project)
    return {"srt": text, "cues": srt_to_cues(text), "burned": False}


def ensure_final_mp4(project_id: str) -> Path:
    """Get a finished render/final.mp4. Re-pull from the cloud if the local copy is truncated."""
    src = project_dir(project_id) / "render" / "final.mp4"
    if mp4_is_complete(src):
        return src
    try:
        from src.documentary import cloud_sync

        if cloud_sync.configured():
            if src.is_file():
                src.unlink(missing_ok=True)
            cloud_sync.pull_one(project_id, "render/final.mp4", force=True)
    except Exception:
        pass
    if mp4_is_complete(src):
        return src
    raise RuntimeError("El video quedó a medias o no está. Volvé al paso Video y renderizá de nuevo.")


def burn_captions(project: dict[str, Any]) -> Path:
    pid = str(project["id"])
    src = ensure_final_mp4(pid)
    srt = captions_srt_path(pid)
    if not srt.is_file() or srt.stat().st_size <= 0:
        generate_captions(project)
        srt = captions_srt_path(pid)
    ff = ffmpeg_exe()
    if not ff:
        raise RuntimeError("No hay FFmpeg en este servidor.")
    dest = captioned_video_path(pid)
    dest.parent.mkdir(parents=True, exist_ok=True)
    import subprocess

    cmd = [
        ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
        "-vf", _subtitles_filter(srt),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    if result.returncode != 0 or not mp4_is_complete(dest):
        if dest.is_file():
            dest.unlink(missing_ok=True)
        err = (result.stderr or result.stdout or "").lower()
        if "subtitles" in err or "ass" in err or "no such filter" in err or result.returncode != 0:
            _burn_with_overlays(ff, src, dest, srt_to_cues(srt.read_text(encoding="utf-8")))
        if not mp4_is_complete(dest):
            raise RuntimeError(
                "No se pudieron quemar los subtítulos: "
                + ffmpeg_error_text(result.stderr or result.stdout or "ffmpeg failed")
            )
    project["captions"] = {
        **(project.get("captions") or {}),
        "path": "render/captions.srt",
        "video": "render/final_captions.mp4",
        "burned": True,
    }
    set_checkpoint(project, "captions_ready", True)
    save_project(project)
    append_log(pid, "captions burned")
    return dest


def clear_burned_captions(project_id: str) -> None:
    p = captioned_video_path(project_id)
    if p.is_file():
        p.unlink(missing_ok=True)


def _cue_texts(script: str) -> list[str]:
    raw = re.sub(r"\s+", " ", (script or "").strip())
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw) if s.strip()]
    out: list[str] = []
    for sent in sentences:
        out.extend(_wrap_cue(sent))
    return out


def _wrap_cue(text: str, width: int = 42, max_lines: int = 2) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    cues: list[str] = []
    for i in range(0, len(lines), max_lines):
        cues.append("\n".join(lines[i : i + max_lines]))
    return cues or [text]


def _fmt(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _subtitles_filter(srt: Path) -> str:
    raw = srt.resolve().as_posix()
    escaped = raw.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return f"subtitles='{escaped}':force_style='{_DOC_STYLE}'"


def _srt_sec(ts: str) -> float:
    ts = (ts or "0").replace(",", ".")
    parts = ts.split(":")
    if len(parts) != 3:
        return 0.0
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _caption_font(size: int):
    from PIL import ImageFont

    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _cue_png(text: str, dest: Path, width: int = 1280, height: int = 140) -> None:
    from PIL import Image, ImageDraw

    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    font = _caption_font(28)
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()] or [""]
    line_h = 34
    total_h = line_h * len(lines)
    y0 = max(8, (height - total_h) // 2)
    for i, line in enumerate(lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = len(line) * 14
        x = max(16, (width - tw) // 2)
        y = y0 + i * line_h
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)):
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 220))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "PNG")


def _burn_with_overlays(ff: str, src: Path, dest: Path, cues: list[dict[str, Any]]) -> Path:
    """Burn captions without libass: overlay PIL PNGs (works with imageio-ffmpeg on Vercel)."""
    import shutil
    import subprocess
    import tempfile

    if not cues:
        raise RuntimeError("No hay carteles para quemar.")
    tmp = Path(tempfile.mkdtemp(prefix="ff-subs-"))
    try:
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
        parts: list[str] = []
        last = "0:v"
        for i, cue in enumerate(cues[:120]):
            png = tmp / f"c{i:03d}.png"
            _cue_png(cue.get("text") or "", png)
            cmd.extend(["-i", str(png)])
            start = _srt_sec(str(cue.get("start") or "0"))
            end = _srt_sec(str(cue.get("end") or "0"))
            out = f"v{i}"
            parts.append(
                f"[{last}][{i + 1}:v]overlay=0:H-h-36:enable='between(t,{start:.3f},{end:.3f})'[{out}]"
            )
            last = out
        cmd.extend(
            [
                "-filter_complex",
                ";".join(parts),
                "-map",
                f"[{last}]",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "28",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-shortest",
                "-movflags",
                "+faststart",
                str(dest),
            ]
        )
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=260)
        if result.returncode != 0 or not mp4_is_complete(dest):
            if dest.is_file():
                dest.unlink(missing_ok=True)
            raise RuntimeError(
                "No se pudieron quemar los subtítulos: "
                + ffmpeg_error_text(result.stderr or result.stdout or "ffmpeg failed")
            )
        return dest
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
