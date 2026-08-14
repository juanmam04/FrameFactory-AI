"""English documentary captions: SRT from the script, burned onto the render."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.video_assembler import ffmpeg_error_text, ffmpeg_exe, mp4_is_complete

_DOC_STYLE = (
    "Fontname=Liberation Sans,Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
    "BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=42,MarginL=48,MarginR=48"
)

_REPO_FONT = (
    Path(__file__).resolve().parents[2] / "studio" / "static" / "fonts" / "LiberationSans-Regular.ttf"
)


def captions_srt_path(project_id: str) -> Path:
    return project_dir(project_id) / "render" / "captions.srt"


def captioned_video_path(project_id: str) -> Path:
    return project_dir(project_id) / "render" / "final_captions.mp4"


def master_video_path(project_id: str) -> Path:
    return project_dir(project_id) / "render" / "final_master.mp4"


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


def whisper_srt_from_audio(audio: Path, *, language: str = "en") -> str:
    """Build SRT from what was actually spoken (Whisper segments)."""
    from openai import OpenAI

    from src.documentary.openai_key import require_openai_api_key

    if not audio.is_file() or audio.stat().st_size <= 0:
        raise RuntimeError("No hay audio de narración para alinear subtítulos.")
    client = OpenAI(api_key=require_openai_api_key("Caption alignment"))
    with audio.open("rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language=language,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
    segments = list(getattr(result, "segments", None) or [])
    if not segments and getattr(result, "text", None):
        # Fallback single block — better than silence, timing still weak.
        text = str(result.text or "").strip()
        if not text:
            raise RuntimeError("Whisper no devolvió texto.")
        return build_srt(text, _probe_audio_duration(audio) or 60.0)
    if not segments:
        raise RuntimeError("Whisper no devolvió segmentos con tiempos.")
    lines: list[str] = []
    n = 0
    for seg in segments:
        if isinstance(seg, dict):
            start = float(seg.get("start") or 0)
            end = float(seg.get("end") or start + 1.2)
            text = str(seg.get("text") or "").strip()
        else:
            start = float(getattr(seg, "start", 0) or 0)
            end = float(getattr(seg, "end", start + 1.2) or start + 1.2)
            text = str(getattr(seg, "text", "") or "").strip()
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        if end <= start:
            end = start + 1.2
        # Split long Whisper segments into short documentary cues, keep wall-clock span.
        parts = _wrap_cue(text, width=48, max_lines=2)
        if not parts:
            continue
        span = max(0.4, end - start)
        weights = [max(1, len(p.split())) for p in parts]
        wtot = sum(weights) or 1
        t = start
        for i, (piece, w) in enumerate(zip(parts, weights)):
            te = end if i == len(parts) - 1 else min(end, t + span * (w / wtot))
            if te <= t:
                te = min(end, t + 0.35)
            n += 1
            lines.append(str(n))
            lines.append(f"{_fmt(t)} --> {_fmt(te)}")
            lines.append(piece)
            lines.append("")
            t = te
    if not lines:
        raise RuntimeError("Whisper no produjo carteles útiles.")
    return "\n".join(lines).strip() + "\n"


def _probe_audio_duration(path: Path) -> float | None:
    try:
        from src.documentary.voice_service import _probe_duration

        return float(_probe_duration(path) or 0) or None
    except Exception:
        return None


def narration_audio_path(project_id: str) -> Path:
    return project_dir(project_id) / "audio" / "narration.mp3"


def captions_for_window(project: dict[str, Any], window_sec: float) -> Path:
    """SRT that matches the opening of the narration (for the 20s preview burn)."""
    import subprocess

    pid = str(project["id"])
    dest = project_dir(pid) / "render" / "captions_preview.srt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    audio = narration_audio_path(pid)
    prev = project.get("captions") if isinstance(project.get("captions"), dict) else {}
    full = captions_srt_path(pid)
    voice_fp = f"{float((project.get('voice') or {}).get('duration_sec') or 0):.2f}:{audio.stat().st_size if audio.is_file() else 0}"
    if (
        str(prev.get("source") or "") == "whisper"
        and str(prev.get("voice_fp") or "") == voice_fp
        and full.is_file()
        and full.stat().st_size > 0
    ):
        return full

    limit = max(8.0, float(window_sec or 20) + 1.5)
    if audio.is_file() and audio.stat().st_size > 0:
        try:
            from src.video_assembler import ffmpeg_exe

            ff = ffmpeg_exe()
            head = project_dir(pid) / "render" / "narration_head.mp3"
            if ff:
                subprocess.run(
                    [
                        ff,
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-i",
                        str(audio),
                        "-t",
                        f"{limit:.2f}",
                        "-c:a",
                        "libmp3lame",
                        "-q:a",
                        "4",
                        str(head),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                src = head if head.is_file() and head.stat().st_size > 0 else audio
            else:
                src = audio
            srt = whisper_srt_from_audio(src, language="en")
            dest.write_text(srt, encoding="utf-8")
            append_log(pid, f"preview captions whisper window={limit:.0f}s cues={len(srt_to_cues(srt))}")
            return dest
        except Exception as e:
            append_log(pid, f"preview captions whisper window failed: {e}")

    # Fallback: regenerate estimate and use the full SRT (still better than stale junk).
    generate_captions(project, force=True)
    return captions_srt_path(pid)


def generate_captions(project: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    pid = str(project["id"])
    script = str(project.get("script") or "").strip()
    if not script:
        raise ValueError("No hay guion para subtitular.")
    duration = float((project.get("voice") or {}).get("duration_sec") or 0)
    audio = narration_audio_path(pid)
    if duration <= 0 and audio.is_file():
        duration = float(_probe_audio_duration(audio) or 0)
    if duration <= 0:
        duration = max(60.0, len(script.split()) / 2.4)

    dest = captions_srt_path(pid)
    prev = project.get("captions") if isinstance(project.get("captions"), dict) else {}
    voice_fp = f"{duration:.2f}:{audio.stat().st_size if audio.is_file() else 0}"
    if (
        not force
        and dest.is_file()
        and dest.stat().st_size > 0
        and str(prev.get("source") or "") == "whisper"
        and str(prev.get("voice_fp") or "") == voice_fp
    ):
        text = dest.read_text(encoding="utf-8")
        return {
            "srt": text,
            "cues": srt_to_cues(text),
            "burned": bool(prev.get("burned")),
            "source": "whisper",
        }

    source = "estimate"
    srt = ""
    err = ""
    if audio.is_file() and audio.stat().st_size > 0:
        try:
            srt = whisper_srt_from_audio(audio, language="en")
            source = "whisper"
            append_log(pid, f"captions aligned via whisper cues={len(srt_to_cues(srt))}")
        except Exception as e:
            err = str(e)[:240]
            append_log(pid, f"captions whisper failed → estimate: {err}")
    if not srt.strip():
        srt = build_srt(script, duration)
        source = "estimate"
        if err:
            append_log(pid, f"captions estimate fallback after: {err}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(srt, encoding="utf-8")
    project["captions"] = {
        "path": "render/captions.srt",
        "cues": len(srt_to_cues(srt)),
        "burned": False,
        "source": source,
        "voice_fp": voice_fp,
        "voice_duration_sec": duration,
    }
    set_checkpoint(project, "captions_ready", False)
    save_project(project)
    append_log(pid, f"captions srt cues={project['captions']['cues']} source={source}")
    return {"srt": srt, "cues": srt_to_cues(srt), "burned": False, "source": source}


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
        "source": "manual",
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


def caption_font_path() -> Path | None:
    for path in (
        _REPO_FONT,
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ):
        if path.is_file():
            return path
    return None


def srt_to_vtt(srt: str) -> str:
    lines = ["WEBVTT", ""]
    for cue in srt_to_cues(srt):
        start = str(cue.get("start") or "0").replace(",", ".")
        end = str(cue.get("end") or "0").replace(",", ".")
        text = str(cue.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def apply_captions_file(
    src: Path,
    srt: Path,
    dest: Path,
    *,
    width: int = 1920,
    crf: int = 17,
    preset: str = "veryfast",
    prefer_overlays: bool = False,
    max_seconds: float | None = None,
) -> Path:
    """Burn English captions onto an mp4. libass first (one filter), then PNG, then drawtext."""
    import subprocess

    ff = ffmpeg_exe()
    if not ff:
        raise RuntimeError("No hay FFmpeg en este servidor.")
    if not mp4_is_complete(src):
        raise RuntimeError("El video fuente está incompleto.")
    if not srt.is_file() or srt.stat().st_size <= 0:
        raise RuntimeError("No hay archivo de subtítulos.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink(missing_ok=True)
    cues = srt_to_cues(srt.read_text(encoding="utf-8"))
    if max_seconds is not None and max_seconds > 0:
        limit = float(max_seconds) + 0.35
        clipped: list[dict[str, Any]] = []
        for c in cues:
            start = _srt_sec(str(c.get("start") or "0"))
            if start >= limit:
                continue
            end = _srt_sec(str(c.get("end") or "0"))
            if end > limit:
                c = {**c, "end": _fmt(limit)}
            clipped.append(c)
        cues = clipped
    if not cues:
        raise RuntimeError("El SRT no tiene carteles.")
    last_err = ""

    def _try_overlays() -> Path | None:
        nonlocal last_err
        try:
            _burn_with_overlays(
                ff,
                src,
                dest,
                cues,
                width=width,
                crf=crf,
                preset=preset,
                big=True,
                # Never mash cues together — that makes captions disagree with the voice.
                merge_max=999,
            )
            if mp4_is_complete(dest):
                return dest
        except Exception as e:
            last_err = str(e)[:400] or last_err
            dest.unlink(missing_ok=True)
        return None

    def _try_ass() -> Path | None:
        nonlocal last_err
        ass = srt.with_suffix(".ass")
        fontsdir = _prepare_font_dir()
        try:
            ass.write_text(_ass_from_cues(cues, width=width), encoding="utf-8")
            vf = _subtitles_filter(ass, fontsdir=fontsdir)
            cmd = [
                ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                "-vf", vf,
                "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                "-movflags", "+faststart",
                str(dest),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if result.returncode == 0 and mp4_is_complete(dest):
                return dest
            last_err = ffmpeg_error_text(result.stderr or result.stdout or "subtitles")
            dest.unlink(missing_ok=True)
        except Exception as e:
            last_err = str(e)[:400]
            dest.unlink(missing_ok=True)
        return None

    def _try_drawtext() -> Path | None:
        nonlocal last_err
        font = caption_font_path()
        if font is None:
            return None
        try:
            vf = _drawtext_filter(
                _merge_cues(cues, max_n=36),
                font,
                56 if width >= 1600 else 36,
            )
            cmd = [
                ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                "-vf", vf,
                "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                "-movflags", "+faststart",
                str(dest),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=160)
            if result.returncode == 0 and mp4_is_complete(dest):
                return dest
            last_err = ffmpeg_error_text(result.stderr or result.stdout or last_err or "drawtext")
            dest.unlink(missing_ok=True)
        except Exception as e:
            last_err = str(e)[:400] or last_err
            dest.unlink(missing_ok=True)
        return None

    order = (_try_overlays, _try_ass, _try_drawtext) if prefer_overlays else (_try_ass, _try_overlays, _try_drawtext)
    for fn in order:
        got = fn()
        if got is not None:
            return got
    raise RuntimeError("No se pudieron quemar los subtítulos: " + (last_err or "ffmpeg failed"))


def burn_into_final(project: dict[str, Any], *, width: int = 1920) -> Path:
    """Write English captions onto render/final.mp4 from the caption-free master."""
    import shutil

    pid = str(project["id"])
    master = master_video_path(pid)
    if not mp4_is_complete(master):
        try:
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                cloud_sync.pull_one(pid, "render/final_master.mp4", force=True)
        except Exception:
            pass
    if not mp4_is_complete(master):
        src = ensure_final_mp4(pid)
        master.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, master)
    srt = captions_srt_path(pid)
    generate_captions(project, force=True)
    srt = captions_srt_path(pid)
    tmp = project_dir(pid) / "render" / "final_burn.mp4"
    apply_captions_file(master, srt, tmp, width=width, crf=17, preset="veryfast")
    cap = captioned_video_path(pid)
    shutil.copy2(tmp, cap)
    final = project_dir(pid) / "render" / "final.mp4"
    tmp.replace(final)
    project["captions"] = {
        **(project.get("captions") or {}),
        "path": "render/captions.srt",
        "video": "render/final.mp4",
        "burned": True,
    }
    set_checkpoint(project, "captions_ready", True)
    save_project(project)
    append_log(pid, "captions burned into final.mp4")
    return final


def burn_captions(project: dict[str, Any]) -> Path:
    return burn_into_final(project)


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


def _prepare_font_dir() -> Path | None:
    import shutil

    src = caption_font_path()
    if src is None:
        return None
    dest_dir = Path("/tmp/ff-fonts") if Path("/tmp").is_dir() else src.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    try:
        if not dest.is_file() or dest.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dest)
    except Exception:
        return src.parent
    return dest_dir


def _ass_clock(ts: str) -> str:
    sec = _srt_sec(ts)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_from_cues(cues: list[dict[str, Any]], *, width: int = 1920) -> str:
    fs = 64 if width >= 3000 else 48 if width >= 1600 else 32
    play_w = 3840 if width >= 3000 else 1920
    play_h = 2160 if width >= 3000 else 1080
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {play_w}",
        f"PlayResY: {play_h}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Liberation Sans,{fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2.4,0,2,80,80,64,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for cue in cues:
        text = str(cue.get("text") or "").strip().replace("\n", r"\N")
        text = text.replace("{", "(").replace("}", ")")
        if not text:
            continue
        lines.append(
            "Dialogue: 0,"
            f"{_ass_clock(str(cue.get('start') or '0'))},"
            f"{_ass_clock(str(cue.get('end') or '0'))},"
            f"Default,,0,0,0,,{text}"
        )
    return "\n".join(lines) + "\n"


def _subtitles_filter(srt: Path, fontsdir: Path | None = None) -> str:
    raw = srt.resolve().as_posix()
    escaped = raw.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    extra = ""
    if fontsdir is not None and fontsdir.is_dir():
        fd = fontsdir.resolve().as_posix().replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
        extra = f":fontsdir='{fd}'"
    return f"subtitles='{escaped}'{extra}"


def _fontfile_esc(path: Path) -> str:
    return path.resolve().as_posix().replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _drawtext_escape(text: str) -> str:
    t = " ".join(str(text or "").split())
    t = t.replace("\\", "\\\\").replace("'", "’").replace(":", r"\:").replace("%", r"\%")
    return t[:160]


def _drawtext_filter(cues: list[dict[str, Any]], font: Path, fontsize: int) -> str:
    parts: list[str] = []
    font_esc = _fontfile_esc(font)
    for cue in cues[:160]:
        text = _drawtext_escape(str(cue.get("text") or ""))
        if not text:
            continue
        start = _srt_sec(str(cue.get("start") or "0"))
        end = _srt_sec(str(cue.get("end") or "0"))
        if end <= start:
            end = start + 1.2
        parts.append(
            "drawtext="
            f"fontfile='{font_esc}':fontsize={fontsize}:fontcolor=white:"
            "borderw=3:bordercolor=black:x=(w-text_w)/2:y=h-th-72:"
            f"enable='between(t,{start:.3f},{end:.3f})':text='{text}':expansion=none"
        )
    if not parts:
        raise RuntimeError("No hay carteles para dibujar.")
    return ",".join(parts)


def _srt_sec(ts: str) -> float:
    ts = (ts or "0").replace(",", ".")
    parts = ts.split(":")
    if len(parts) != 3:
        return 0.0
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _caption_font(size: int):
    from PIL import ImageFont

    path = caption_font_path()
    if path is not None:
        return ImageFont.truetype(str(path), size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _cue_png(text: str, dest: Path, width: int = 1920, height: int = 160, *, big: bool = False) -> None:
    from PIL import Image, ImageDraw

    # Transparent plate — white letters + thin black outline only (no YouTube-style box).
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    font_size = (46 if width >= 1600 else 30) if big else (40 if width >= 1600 else 26)
    font = _caption_font(font_size)
    raw = " ".join(str(text or "").split())
    # Prefer short documentary lines, max ~2.
    max_chars = 52 if width >= 1600 else 38
    words = raw.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and len(trial) > max_chars:
            lines.append(cur)
            cur = w
            if len(lines) >= 2:
                break
        else:
            cur = trial
    if cur and len(lines) < 2:
        lines.append(cur)
    elif cur and len(lines) >= 2:
        lines[-1] = (lines[-1] + " " + cur).strip()[: max_chars + 8]
    if not lines:
        lines = [""]
    line_h = int(font_size * 1.22)
    total_h = line_h * len(lines)
    y0 = max(4, height - total_h - 10)
    for i, line in enumerate(lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = len(line) * 14
        x = max(16, (width - tw) // 2)
        y = y0 + i * line_h
        for dx, dy in (
            (-2, 0),
            (2, 0),
            (0, -2),
            (0, 2),
            (-1, -1),
            (1, -1),
            (-1, 1),
            (1, 1),
        ):
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 220))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "PNG")


def _merge_cues(cues: list[dict[str, Any]], max_n: int = 48) -> list[dict[str, Any]]:
    if len(cues) <= max_n:
        return cues
    out: list[dict[str, Any]] = []
    step = max(2, int(round(len(cues) / max_n)))
    for i in range(0, len(cues), step):
        chunk = cues[i : i + step]
        text = " ".join(" ".join(str(c.get("text") or "").split()) for c in chunk).strip()
        out.append(
            {
                "start": chunk[0].get("start"),
                "end": chunk[-1].get("end"),
                "text": text[:160],
            }
        )
    return out


def _burn_with_overlays(
    ff: str,
    src: Path,
    dest: Path,
    cues: list[dict[str, Any]],
    *,
    width: int = 1920,
    crf: int = 17,
    preset: str = "veryfast",
    big: bool = False,
    merge_max: int = 48,
) -> Path:
    """Burn captions without libass: overlay PIL PNGs (works with imageio-ffmpeg on Vercel)."""
    import shutil
    import subprocess
    import tempfile

    cues = _merge_cues(cues, max_n=merge_max)
    if not cues:
        raise RuntimeError("No hay carteles para quemar.")
    # Cap overlays so ffmpeg filter graphs stay manageable on short clips.
    if len(cues) > 36:
        cues = cues[:36]
    bar_h = (140 if width >= 1600 else 110) if big else (120 if width >= 1600 else 96)
    tmp = Path(tempfile.mkdtemp(prefix="ff-subs-"))
    try:
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
        parts: list[str] = []
        last = "0:v"
        for i, cue in enumerate(cues):
            png = tmp / f"c{i:03d}.png"
            _cue_png(cue.get("text") or "", png, width=width, height=bar_h, big=big)
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
                preset,
                "-crf",
                str(crf),
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
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
