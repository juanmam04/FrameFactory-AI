"""Subtítulos para el MVP SaaS: SRT por bloque según duración real del TTS + burn con FFmpeg."""
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path


def ffprobe_duration_seconds(media_path: Path) -> float:
    """Duración en segundos vía ffprobe; fallback conservador si falla."""
    if not media_path.exists():
        return 0.0
    if not shutil.which("ffprobe"):
        return 0.0
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path.resolve()),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        return max(0.0, float(r.stdout.strip()))
    except Exception:
        return 0.0


def _fmt_srt_time(t: float) -> str:
    td = timedelta(seconds=max(0.0, t))
    total_ms = int(td.total_seconds() * 1000)
    h, rem = divmod(total_ms, 3600 * 1000)
    m, rem = divmod(rem, 60 * 1000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _clean_cue_text(raw: str) -> str:
    t = re.sub(r"\s+", " ", (raw or "").strip())
    if len(t) > 420:
        t = t[:417] + "…"
    return t


def _ass_ts(t: float) -> str:
    """Tiempo ASS h:mm:ss.cc"""
    t = max(0.0, float(t))
    cs = int(round((t - int(t)) * 100.0)) % 100
    ti = int(t)
    h, rem = divmod(ti, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    t = _clean_cue_text(text)
    return (
        t.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", "\\N")
    )


def _ass_style_row(style_key: str) -> str:
    """
    Una fila Style ASS (alineación explícita: 2=abajo centro, 5=medio, 8=arriba).
    Colores &HAABBGGRR (alfa en AA).
    """
    k = (style_key or "default").strip().lower()
    # prim, sec, outl, back, fs, ol, bs, al, mv  (BorderStyle bs, Outline ol, Alignment al, MarginV mv)
    rows = {
        "default": ("&H00FFFFFF", "&H000000FF", "&H00000000", "&H00000000", 38, 3, 1, 2, 72),
        "studio_lower": ("&H00FFFFFF", "&H000000FF", "&H00000000", "&HA0101010", 34, 2, 3, 2, 88),
        "tiktok_karaoke": ("&H0000FFFF", "&H000000FF", "&H00000000", "&H00000000", 48, 4, 1, 2, 58),
        "clean_center": ("&H00FFFFFF", "&H000000FF", "&H00000000", "&H00000000", 42, 0, 1, 5, 30),
        "soft_bar": ("&H00FFFFFF", "&H000000FF", "&H00000000", "&H80000000", 36, 0, 3, 2, 70),
        "news_banner": ("&H00000000", "&H000000FF", "&H00000000", "&H00D7FF", 34, 0, 3, 8, 40),
    }
    prim, sec, outl, back, fs, ol, bs, al, mv = rows.get(k, rows["default"])
    return (
        f"Style: Default,Arial,{fs},{prim},{sec},{outl},{back},"
        f"0,0,0,0,100,100,0,0,{bs},{ol},0,{al},48,48,{mv},1"
    )


def _ass_dialogue_prefix(style_key: str) -> str:
    """Override de alineación para que no quede en el medio salvo clean_center."""
    k = (style_key or "default").strip().lower()
    if k == "clean_center":
        return "{\\an5}"  # centro pantalla
    if k == "news_banner":
        return "{\\an8}"  # arriba centro
    return "{\\an2}"  # abajo centro (forzado además del Style)


def write_ass_from_block_audios(
    blocks: list[dict],
    audio_paths: list[Path],
    out_ass: Path,
    *,
    subtitle_style_key: str = "default",
) -> Path:
    """
    ASS con PlayRes 1280x720 y estilos explícitos (libass respeta Alignment; evita fallos de SRT+force_style).
    """
    if len(blocks) != len(audio_paths):
        raise ValueError("blocks y audio_paths deben tener la misma longitud.")
    out_ass.parent.mkdir(parents=True, exist_ok=True)
    style_row = _ass_style_row(subtitle_style_key)
    prefix = _ass_dialogue_prefix(subtitle_style_key)

    head = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "PlayResX: 1280\n"
        "PlayResY: 720\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"{style_row}\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines: list[str] = [head]
    t_cursor = 0.0
    for block, apath in zip(blocks, audio_paths, strict=True):
        dur = ffprobe_duration_seconds(apath)
        start = t_cursor
        end = t_cursor + dur
        t_cursor = end
        raw = str(block.get("text") or "")
        if not raw.strip():
            continue
        body = _ass_escape(raw)
        if not body:
            continue
        lines.append(
            f"Dialogue: 0,{_ass_ts(start)},{_ass_ts(end)},Default,,0,0,0,,{prefix}{body}\n"
        )
    out_ass.write_text("".join(lines), encoding="utf-8-sig")
    return out_ass


def write_srt_from_block_audios(
    blocks: list[dict],
    audio_paths: list[Path],
    out_path: Path,
) -> Path:
    """
    Un cue por bloque con texto del guion y tiempos según duración real de cada audio TTS.
    """
    if len(blocks) != len(audio_paths):
        raise ValueError("blocks y audio_paths deben tener la misma longitud.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    t_cursor = 0.0
    cue_n = 0
    for block, apath in zip(blocks, audio_paths, strict=True):
        dur = ffprobe_duration_seconds(apath)
        start = t_cursor
        end = t_cursor + dur
        t_cursor = end
        text = _clean_cue_text(str(block.get("text") or ""))
        if not text:
            continue
        cue_n += 1
        lines.append(str(cue_n))
        lines.append(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}")
        lines.append(text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _ffmpeg_subtitles_path_escaped(srt_path: Path) -> str:
    """Ruta para filtro subtitles= en Windows (escapa la unidad C:...)."""
    s = srt_path.resolve().as_posix()
    if len(s) >= 2 and s[1] == ":":
        s = s[0] + "\\:" + s[2:]
    return s.replace("'", r"\'")


def burn_subtitles_on_video(
    video_in: Path,
    srt_path: Path,
    force_style: str | None,
    video_out: Path,
) -> Path:
    """
    Re-encode video con subtítulos incrustados (libass). Audio se copia sin recodificar.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg no está en PATH; no se pueden quemar subtítulos.")
    if not video_in.exists():
        raise FileNotFoundError(video_in)
    if not srt_path.exists():
        raise FileNotFoundError(srt_path)
    video_out.parent.mkdir(parents=True, exist_ok=True)

    sub_filter = f"subtitles='{_ffmpeg_subtitles_path_escaped(srt_path)}'"
    # Los .ass generados por la app ya traen [V4+ Styles]; force_style en SRT a veces ignora Alignment.
    if (
        force_style
        and str(force_style).strip()
        and not str(srt_path.resolve()).lower().endswith(".ass")
    ):
        fs = str(force_style).strip().replace("'", "")
        sub_filter += f":force_style='{fs}'"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_in.resolve()),
        "-vf",
        sub_filter,
        "-c:a",
        "copy",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        str(video_out.resolve()),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=7200)
    except subprocess.CalledProcessError as e:
        tail = (e.stderr or e.stdout or "")[-800:]
        raise RuntimeError(f"FFmpeg (subtítulos) falló: {tail}") from e
    if not video_out.exists() or video_out.stat().st_size == 0:
        raise RuntimeError(f"No se generó el video con subtítulos: {video_out}")
    return video_out


def list_subtitle_style_keys(styles: dict) -> list[str]:
    """Claves de estilo con force_style (YAML de config)."""
    keys: list[str] = []
    for k, v in (styles or {}).items():
        if isinstance(v, dict) and v.get("force_style"):
            keys.append(str(k))
    return sorted(keys, key=lambda x: (0 if x == "default" else 1, x))


# Miniaturas HTML solo para la UI (no se usan en el video).
_SUBTITLE_STYLE_PREVIEW_HTML: dict[str, str] = {
    "default": """
<div style="background:linear-gradient(180deg,#1a1a2e 0%,#0f0f1a 100%);border-radius:10px;padding:28px 12px 36px;text-align:center;font-family:Arial,sans-serif;">
  <span style="color:#fff;font-size:18px;font-weight:600;text-shadow:0 0 4px #000,2px 2px 0 #000, -1px -1px 0 #000;">Así se ve la narración abajo</span>
</div>""",
    "tiktok_karaoke": """
<div style="background:linear-gradient(180deg,#2d1b4e 0%,#0d0221 100%);border-radius:10px;padding:32px 12px 32px;text-align:center;font-family:Impact,Arial,sans-serif;">
  <span style="color:#ffe600;font-size:22px;font-weight:800;-webkit-text-stroke:1.2px #000;text-shadow:2px 2px 0 #000;">ASÍ SE VE MÁS LLAMATIVO</span>
</div>""",
    "clean_center": """
<div style="background:radial-gradient(ellipse at center,#2a2a3a 0%,#121218 70%);border-radius:10px;padding:48px 16px;text-align:center;font-family:Arial,sans-serif;">
  <span style="color:#f8f8f8;font-size:20px;font-weight:500;">Texto limpio al centro</span>
</div>""",
    "soft_bar": """
<div style="background:linear-gradient(180deg,#1e1e28 60%,rgba(0,0,0,.55) 60%,rgba(0,0,0,.75) 100%);border-radius:10px;padding:36px 12px 28px;text-align:center;font-family:Georgia,serif;">
  <span style="color:#fff;font-size:17px;">Lectura cómoda con franja suave</span>
</div>""",
    "news_banner": """
<div style="background:#1a1a1a;border-radius:10px;padding:0;overflow:hidden;text-align:center;font-family:Arial,sans-serif;">
  <div style="background:linear-gradient(90deg,#ffd400,#ffea70);padding:10px 8px;">
    <span style="color:#111;font-size:17px;font-weight:700;">Cinta tipo noticiero arriba</span>
  </div>
  <div style="padding:24px 8px;color:#888;font-size:12px;">video</div>
</div>""",
    "studio_lower": """
<div style="background:linear-gradient(180deg,#3a3d45 0%,#2a2d32 45%,#1a1c20 45%,#121418 100%);border-radius:10px;min-height:200px;position:relative;overflow:hidden;font-family:Arial,Helvetica,sans-serif;">
  <div style="position:absolute;left:0;right:0;bottom:0;top:38%;background:linear-gradient(180deg,rgba(18,20,24,.92),#0d0e12);border-radius:12px 12px 0 0;padding:20px 16px 28px;text-align:center;">
    <div style="width:56px;height:56px;margin:0 auto 12px;background:#f2f2f2;border-radius:50%;border:2px solid #444;"></div>
    <div style="color:#fff;font-size:15px;font-weight:600;line-height:1.35;max-width:92%;margin:0 auto;text-shadow:0 0 1px #000,1px 1px 0 #000,-1px -1px 0 #000,1px -1px 0 #000,-1px 1px 0 #000;">
      Hoy es el día decisivo:<br/>una reunión a las 10:00 a.m.
    </div>
  </div>
</div>""",
}


def subtitle_style_preview_html(style_key: str) -> str:
    """HTML para mostrar en Streamlit (sin exponer el nombre técnico al usuario)."""
    return _SUBTITLE_STYLE_PREVIEW_HTML.get(style_key) or _SUBTITLE_STYLE_PREVIEW_HTML["default"]
