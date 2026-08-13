"""Segmentos de video de gameplay (p. ej. parkour) para clips del MVP sin Replicate."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


def probe_media_duration_seconds(media_path: Path) -> float:
    if not shutil.which("ffprobe") or not media_path.exists():
        return 0.0
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
                str(media_path.resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return max(0.0, float((r.stdout or "").strip()))
    except Exception:
        return 0.0


def output_size_for_aspect(aspect: str) -> tuple[int, int]:
    a = (aspect or "16:9").strip().lower().replace(" ", "")
    if a in ("9:16", "vertical", "portrait", "tiktok"):
        return 1080, 1920
    return 1920, 1080


def _escape_drawtext(s: str) -> str:
    return (
        (s or "")
        .replace("\\", r"\\")
        .replace("'", r"\'")
        .replace(":", r"\:")
        .replace("%", r"\%")
        .replace(",", r"\,")
    )


def render_gameplay_block_clip(
    gameplay_source: Path,
    audio_path: Path,
    output_path: Path,
    *,
    segment_start_sec: float,
    duration_sec: float,
    aspect: str = "16:9",
    motion: str = "static",
    transition_in: str = "none",
    transition_out: str = "none",
    drawtext_overlay: dict | None = None,
) -> Path:
    """
    Corta un tramo del video de gameplay (con -stream_loop para cubrir duraciones largas),
    escala a 16:9 o 9:16, aplica motion/fades y muxea el audio del bloque.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg no está instalado o no está en PATH.")
    if not gameplay_source.exists():
        raise FileNotFoundError(f"No existe gameplay source: {gameplay_source}")
    if not audio_path.exists():
        raise FileNotFoundError(str(audio_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    w, h = output_size_for_aspect(aspect)
    vlen = probe_media_duration_seconds(gameplay_source)
    if vlen <= 0.1:
        raise RuntimeError(f"No se pudo leer duración del gameplay: {gameplay_source}")

    start = float(segment_start_sec) % vlen
    dur = max(0.5, float(duration_sec))

    motion = str(motion or "static").strip().lower()
    if motion not in ("static", "slow_push"):
        motion = "static"
    tin = str(transition_in or "none").strip().lower()
    tout = str(transition_out or "none").strip().lower()
    if tin not in ("none", "fade"):
        tin = "none"
    if tout not in ("none", "fade"):
        tout = "none"

    fade_out_start = max(0.0, dur - 0.26)
    fps = 30

    trim_scale = (
        f"[0:v]trim=start={start:.3f}:duration={dur:.3f},setpts=PTS-START/TB,"
        f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},format=yuv420p,setsar=1[v0]"
    )

    if motion == "slow_push":
        motion_chain = (
            f"[v0]scale=iw*2:ih*2,"
            f"zoompan=z='min(zoom+0.0012,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps={fps}[vmid]"
        )
    else:
        motion_chain = "[v0]format=yuv420p[vmid]"

    fade_parts: list[str] = []
    if tin == "fade":
        fade_parts.append("fade=t=in:st=0:d=0.22")
    if tout == "fade":
        fade_parts.append(f"fade=t=out:st={fade_out_start:.2f}:d=0.24")
    if fade_parts:
        fade_seg = f"[vmid]{','.join(fade_parts)}[vpost]"
    else:
        fade_seg = "[vmid]format=yuv420p[vpost]"

    dt = drawtext_overlay if isinstance(drawtext_overlay, dict) else None
    if dt and str(dt.get("text") or "").strip():
        tx = _escape_drawtext(str(dt["text"])[:200])
        fs = int(dt.get("size") or 42)
        fs = max(18, min(96, fs))
        xc = float(dt.get("x", 0.5))
        yc = float(dt.get("y", 0.72))
        col = re.sub(r"[^#0-9a-zA-Z]", "", str(dt.get("color") or "white")) or "white"
        draw = (
            f"drawtext=text='{tx}':fontsize={fs}:fontcolor={col}:"
            f"x=(w-text_w)*{max(0.0, min(1.0, xc))}:y=(h-text_h)*{max(0.05, min(0.95, yc))}:"
            "borderw=3:bordercolor=black@0.85"
        )
        out_chain = f"[vpost]{draw}[vout]"
    else:
        out_chain = "[vpost]format=yuv420p[vout]"

    fc = f"{trim_scale};{motion_chain};{fade_seg};{out_chain}"

    cmd = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(gameplay_source.resolve()),
        "-i",
        str(audio_path.resolve()),
        "-filter_complex",
        fc,
        "-map",
        "[vout]",
        "-map",
        "1:a:0",
        "-t",
        f"{dur:.3f}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_path.resolve()),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or "")[-800:]
        fade_simple = fade_parts[0] if fade_parts else "format=yuv420p"
        if len(fade_parts) > 1:
            fade_simple = ",".join(fade_parts)
        simple_fc = (
            f"[0:v]trim=start={start:.3f}:duration={dur:.3f},setpts=PTS-START/TB,"
            f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},format=yuv420p,setsar=1[vmid];"
            f"[vmid]{fade_simple}[vout]"
        )
        cmd2 = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(gameplay_source.resolve()),
            "-i",
            str(audio_path.resolve()),
            "-filter_complex",
            simple_fc,
            "-map",
            "[vout]",
            "-map",
            "1:a:0",
            "-t",
            f"{dur:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path.resolve()),
        ]
        try:
            subprocess.run(cmd2, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e2:
            raise RuntimeError(f"[gameplay] FFmpeg falló: {msg} // fallback: {(e2.stderr or '')[-500:]}") from e2
    return output_path
