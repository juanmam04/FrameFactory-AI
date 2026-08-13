"""FASE 9: Montaje automático de video con FFmpeg (imágenes + narración + música opcional)."""
import os
import subprocess
import shutil
import sys
import time
from pathlib import Path

from .config_loader import BASE, get_duracion_por_imagen

OUTPUT_VIDEO = BASE / "output" / "videos"


def ffmpeg_exe() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        if (os.getenv("VERCEL") or "").strip():
            home = Path("/tmp/ff-home")
            home.mkdir(parents=True, exist_ok=True)
            os.environ["HOME"] = str(home)
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def verificar_ffmpeg() -> bool:
    """Verifica si FFmpeg está instalado y disponible en el PATH."""
    return bool(ffmpeg_exe())


def mp4_is_complete(path: Path | None) -> bool:
    """True if the file looks like a finished MP4 (ftyp + moov), not a truncated render."""
    if path is None or not path.is_file():
        return False
    try:
        size = path.stat().st_size
    except OSError:
        return False
    if size < 64:
        return False
    chunk = min(size, 2_000_000)
    try:
        with path.open("rb") as fh:
            head = fh.read(chunk)
            tail = b""
            if size > chunk:
                fh.seek(max(0, size - chunk))
                tail = fh.read(chunk)
    except OSError:
        return False
    blob = head + tail
    return b"ftyp" in head and b"moov" in blob


def ffmpeg_error_text(stderr: str) -> str:
    lines = [ln.strip() for ln in (stderr or "").splitlines() if ln.strip()]
    useful = [
        ln
        for ln in lines
        if any(
            k in ln.lower()
            for k in ("error", "invalid", "moov", "no such", "failed", "unknown", "not found")
        )
        and "enable-" not in ln.lower()
        and "libav" not in ln.lower()
        and "configuration:" not in ln.lower()
    ]
    if useful:
        return " | ".join(useful[-4:])[:400]
    return (stderr or "ffmpeg failed")[-400:]


class EditorialPaused(Exception):
    """Ran out of time mid-edit; caller should resume with cached still clips."""

    def __init__(self, done: int, total: int):
        super().__init__(f"editorial paused {done}/{total}")
        self.done = int(done)
        self.total = int(total)


def montar_slideshow(
    lista_imagenes: list[Path],
    audio_narracion: Path,
    output_path: Path,
    *,
    segundos_por_imagen: float,
    width: int = 1280,
    height: int = 720,
    musica_fondo: Path | None = None,
    music_volume: float = 0.08,
    fade_sec: float = 0.4,
    duration_sec: float | None = None,
    motion: str = "mix",
    transition: str = "fade",
    fps: int = 24,
    crf: int = 17,
    preset: str = "veryfast",
    editorial: bool = True,
    look: str = "soft",
    clip_dir: Path | None = None,
    deadline_mono: float | None = None,
    on_progress: object | None = None,
    abort: object | None = None,
) -> Path:
    """Stills + narration + Ken Burns + fades. Falls back to concat if the editorial pass fails."""
    ff = ffmpeg_exe()
    if not ff:
        raise RuntimeError("No hay FFmpeg en este servidor.")
    imgs = [p for p in lista_imagenes if p.is_file() and p.stat().st_size > 0]
    if not imgs:
        raise RuntimeError("No hay imágenes para armar el video.")
    if not audio_narracion.is_file() or audio_narracion.stat().st_size <= 0:
        raise RuntimeError("Falta la narración.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seg = min(7.0, max(2.8, float(segundos_por_imagen)))
    fade = min(0.5, max(0.25, float(fade_sec)), seg / 3)
    vol = max(0.0, min(0.22, float(music_volume)))
    music = musica_fondo if musica_fondo and musica_fondo.is_file() else None
    if music is None:
        try:
            from src.documentary.music_bed import documentary_bed_path

            bed = documentary_bed_path()
            if bed.is_file():
                music = bed
        except Exception:
            music = None
    vol = max(0.12, min(0.40, float(vol) * 2.8))
    looks = [look, "none"] if str(look or "soft") != "none" else ["none"]
    last = None
    long_job = len(imgs) > 8
    if editorial and not long_job:
        for lk in looks:
            try:
                return _slideshow_editorial(
                    ff, imgs, audio_narracion, output_path, seg, width, height, music, vol,
                    duration_sec, motion, transition, fps=fps, crf=crf, preset=preset, look=lk,
                    clip_dir=clip_dir, deadline_mono=deadline_mono, on_progress=on_progress, abort=abort,
                )
            except EditorialPaused:
                raise
            except Exception as e:
                last = e
    for lk in looks:
        try:
            return _slideshow_concat(
                ff, imgs, audio_narracion, output_path, seg, width, height, music, vol, duration_sec,
                fps=fps, crf=crf, preset=preset, look=lk, motion=motion, transition=transition,
            )
        except Exception as e:
            last = e
    if last:
        raise last
    return _slideshow_concat(
        ff, imgs, audio_narracion, output_path, seg, width, height, music, vol, duration_sec,
        fps=fps, crf=crf, preset=preset, look="none", motion=motion, transition=transition,
    )


def _vignette_vf(look: str) -> str:
    k = str(look or "soft").strip().lower()
    if k in ("none", "off", "0"):
        return ""
    if k in ("film", "strong", "cine"):
        return ",vignette=angle=PI/3.2"
    return ",vignette=angle=PI/2.8"


def _motion_vf(kind: str, index: int, seg: float, width: int, height: int) -> str:
    """Slow Ken Burns via scale/crop (faster than zoompan, same documentary feel)."""
    styles = ("push", "pull", "pan")
    k = kind if kind in styles else styles[index % 3]
    z = 0.07
    dur = max(0.8, float(seg))
    fill = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}"
    )
    if k == "pull":
        return (
            f"{fill},scale=w='2*trunc(iw*(1+{z}*(1-min(t/{dur:.3f}\\,1)))/2)':h=-2:eval=frame,"
            f"crop={width}:{height}"
        )
    if k == "pan":
        pw = int(width * 1.08) // 2 * 2
        ph = int(height * 1.08) // 2 * 2
        return (
            f"scale={pw}:{ph}:force_original_aspect_ratio=increase,crop={pw}:{ph},"
            f"crop={width}:{height}:x='(in_w-out_w)*min(t/{dur:.3f}\\,1)':y='(in_h-out_h)/2'"
        )
    return (
        f"{fill},scale=w='2*trunc(iw*(1+{z}*min(t/{dur:.3f}\\,1))/2)':h=-2:eval=frame,"
        f"crop={width}:{height}"
    )


def _slideshow_editorial(
    ff: str,
    imgs: list[Path],
    audio: Path,
    output_path: Path,
    seg: float,
    width: int,
    height: int,
    music: Path | None,
    vol: float,
    duration_sec: float | None,
    motion: str,
    transition: str,
    fps: int = 24,
    crf: int = 17,
    preset: str = "veryfast",
    look: str = "soft",
    clip_dir: Path | None = None,
    deadline_mono: float | None = None,
    on_progress: object | None = None,
    abort: object | None = None,
) -> Path:
    """Ken Burns + per-still fades, in batches so Vercel does not die on 70 inputs."""
    import tempfile

    fps = max(12, min(30, int(fps)))
    frames = max(8, int(round(seg * fps)))
    fade = 0.28 if transition == "fade" else 0.0
    owned = clip_dir is None
    tmp = Path(tempfile.mkdtemp(prefix="ff-edit-")) if owned else Path(clip_dir)
    tmp.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    try:
        for i, img in enumerate(imgs):
            if callable(abort):
                abort()
            clip = tmp / f"s{i:03d}.mp4"
            if not mp4_is_complete(clip):
                if deadline_mono is not None and time.monotonic() >= float(deadline_mono):
                    raise EditorialPaused(i, len(imgs))
                _encode_one_still(
                    ff, img, clip, seg, width, height, motion, fade, frames, i,
                    fps=fps, crf=crf, preset=preset, look=look,
                )
            clips.append(clip)
            if callable(on_progress):
                on_progress(i + 1, len(imgs))
        video_only = tmp / "video.mp4"
        if len(clips) == 1:
            video_only = clips[0]
        else:
            lst = tmp / "clips.txt"
            lst.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8")
            cmd = [
                ff, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", str(lst),
                "-c", "copy", "-an", "-movflags", "+faststart", str(video_only),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=80)
            if r.returncode != 0 or not mp4_is_complete(video_only):
                cmd = [
                    ff, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(video_only),
                ]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if r.returncode != 0 or not mp4_is_complete(video_only):
                raise RuntimeError(ffmpeg_error_text(r.stderr or "concat clips"))
        try:
            _mix_voice_music(ff, video_only, audio, music, vol, output_path, duration_sec)
        except Exception:
            _mix_voice_music(ff, video_only, audio, None, vol, output_path, duration_sec)
        if not mp4_is_complete(output_path):
            raise RuntimeError("editorial mix incomplete")
        return output_path
    finally:
        if owned:
            shutil.rmtree(tmp, ignore_errors=True)


def _encode_one_still(
    ff: str,
    img: Path,
    out: Path,
    seg: float,
    width: int,
    height: int,
    motion: str,
    fade: float,
    frames: int,
    index: int,
    fps: int = 24,
    crf: int = 17,
    preset: str = "veryfast",
    look: str = "soft",
) -> None:
    motion_vf = _motion_vf(motion, index, seg, width, height)
    fo = max(0.12, seg - fade) if fade else 0
    fades = (
        f",fade=t=in:st=0:d={fade:.2f},fade=t=out:st={fo:.2f}:d={fade:.2f}"
        if fade
        else ""
    )
    vig = _vignette_vf(look)
    vf = f"{motion_vf}{fades}{vig},format=yuv420p,setsar=1"
    part = out.with_suffix(".part.mp4")
    cmd = [
        ff, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(fps), "-loop", "1", "-t", f"{seg:.3f}", "-i", str(img.resolve()),
        "-vf", vf, "-r", str(fps), "-t", f"{seg:.3f}",
        "-c:v", "libx264", "-preset", preset, "-tune", "stillimage", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(part),
    ]
    limit = 18 if width <= 1280 else 28
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=limit)
    if r.returncode != 0 or not mp4_is_complete(part):
        part.unlink(missing_ok=True)
        raise RuntimeError(ffmpeg_error_text(r.stderr or "still clip"))
    part.replace(out)


def _mix_voice_music(
    ff: str,
    video: Path,
    audio: Path,
    music: Path | None,
    vol: float,
    dest: Path,
    duration_sec: float | None,
) -> None:
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(audio)]
    if music is not None:
        cmd.extend(["-stream_loop", "-1", "-i", str(music)])
        cmd.extend(
            [
                "-filter_complex",
                "[1:a]aformat=sample_fmts=fltp:sample_rates=44100,volume=1[a1];"
                f"[2:a]aformat=sample_fmts=fltp:sample_rates=44100,volume={vol:.3f}[a2];"
                "[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                "-map", "0:v", "-map", "[aout]",
            ]
        )
    else:
        cmd.extend(["-map", "0:v", "-map", "1:a"])
    if duration_sec and float(duration_sec) > 0:
        cmd.extend(["-t", f"{float(duration_sec):.3f}"])
    cmd.extend(
        [
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", str(dest),
        ]
    )
    mix_limit = 130 if (duration_sec or 0) > 60 else 90
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=mix_limit)
    if r.returncode != 0 or not mp4_is_complete(dest):
        raise RuntimeError(ffmpeg_error_text(r.stderr or "mix audio"))


def _slideshow_fades(
    ff: str,
    imgs: list[Path],
    audio: Path,
    output_path: Path,
    seg: float,
    width: int,
    height: int,
    fade: float,
    music: Path | None,
    vol: float,
) -> Path:
    parts: list[str] = []
    for i in range(len(imgs)):
        fo = max(0.05, seg - fade)
        parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps=24,setsar=1,format=yuv420p,"
            f"fade=t=in:st=0:d={fade:.2f},fade=t=out:st={fo:.2f}:d={fade:.2f}[v{i}]"
        )
    concat = "".join(f"[v{i}]" for i in range(len(imgs)))
    fc = ";".join(parts) + f";{concat}concat=n={len(imgs)}:v=1:a=0[vout]"
    cmd = [ff, "-y"]
    for p in imgs:
        cmd.extend(["-loop", "1", "-t", f"{seg:.3f}", "-i", str(p.resolve())])
    cmd.extend(["-i", str(audio)])
    maps_v = "[vout]"
    if music is not None:
        cmd.extend(["-stream_loop", "-1", "-i", str(music.resolve())])
        n_aud = len(imgs)
        n_mus = len(imgs) + 1
        fc += (
            f";[{n_aud}:a]aformat=sample_fmts=fltp:sample_rates=44100,volume=1[a1];"
            f"[{n_mus}:a]aformat=sample_fmts=fltp:sample_rates=44100,volume={vol:.3f}[a2];"
            f"[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd.extend(["-filter_complex", fc, "-map", maps_v, "-map", "[aout]"])
    else:
        cmd.extend(["-filter_complex", fc, "-map", maps_v, "-map", f"{len(imgs)}:a"])
    cmd.extend(
        [
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "28",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart",
            str(output_path),
        ]
    )
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    if result.returncode != 0 or not mp4_is_complete(output_path):
        if output_path.is_file() and not mp4_is_complete(output_path):
            output_path.unlink(missing_ok=True)
        err = ffmpeg_error_text(result.stderr or result.stdout or "ffmpeg failed")
        raise RuntimeError(err)
    return output_path


def _concat_edit_vf(
    *,
    n: int,
    seg: float,
    width: int,
    height: int,
    fps: int,
    look: str,
    motion: str,
    transition: str,
    total: float,
) -> str:
    """One-pass pan/drift + per-still fades. Cheap enough for a 10 min Vercel encode."""
    fps = max(12, min(30, int(fps)))
    pw = int(width * 1.08) // 2 * 2
    ph = int(height * 1.08) // 2 * 2
    p = f"min(mod(t\\,{seg:.3f})/{max(seg, 0.01):.3f}\\,1)"
    m = str(motion or "mix").strip().lower()
    if m == "pull":
        x = f"(in_w-out_w)*(1-{p})"
        y = f"(in_h-out_h)/2"
    elif m == "pan":
        x = f"(in_w-out_w)*{p}"
        y = f"(in_h-out_h)/2"
    elif m == "push":
        x = f"(in_w-out_w)*{p}"
        y = f"(in_h-out_h)*(0.25+0.5*{p})"
    else:
        x = f"(in_w-out_w)*if(eq(mod(floor(t/{seg:.3f})\\,2),0)\\,{p}\\,1-{p})"
        y = f"(in_h-out_h)*(0.35+0.30*sin(2*PI*{p}))"
    fade = 0.28 if str(transition or "fade") == "fade" else 0.0
    bits = [
        f"scale={pw}:{ph}:force_original_aspect_ratio=increase",
        f"crop={pw}:{ph}",
        f"crop={width}:{height}:x='{x}':y='{y}'",
        f"fps={fps}",
        "format=yuv420p",
    ]
    vig = _vignette_vf(look)
    if vig.startswith(","):
        bits.append(vig[1:])
    if fade:
        s = max(seg, 0.8)
        d = min(fade, s / 3)
        bits.append(
            "eq=brightness='if(lt(mod(t"
            f"\\,{s:.3f}),{d:.2f}),-0.7*(1-mod(t\\,{s:.3f})/{d:.2f}),"
            f"if(gt(mod(t\\,{s:.3f}),{s:.3f}-{d:.2f}),"
            f"-0.7*(1-({s:.3f}-mod(t\\,{s:.3f}))/{d:.2f}),0))'"
        )
    fade_out_at = max(0.4, float(total) - 0.35)
    bits.append("fade=t=in:st=0:d=0.28")
    bits.append(f"fade=t=out:st={fade_out_at:.2f}:d=0.35")
    return ",".join(bits)


def _slideshow_concat(
    ff: str,
    imgs: list[Path],
    audio: Path,
    output_path: Path,
    seg: float,
    width: int,
    height: int,
    music: Path | None,
    vol: float,
    duration_sec: float | None = None,
    fps: int = 24,
    crf: int = 17,
    preset: str = "veryfast",
    look: str = "soft",
    motion: str = "mix",
    transition: str = "fade",
) -> Path:
    list_file = output_path.with_suffix(".concat.txt")
    with list_file.open("w", encoding="utf-8") as fh:
        for p in imgs:
            fh.write(f"file '{p.resolve().as_posix()}'\n")
            fh.write(f"duration {seg:.3f}\n")
        fh.write(f"file '{imgs[-1].resolve().as_posix()}'\n")
    cmd = [
        ff, "-hide_banner", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-i", str(audio),
    ]
    total = float(duration_sec or 0) or (seg * max(1, len(imgs)))
    vf = _concat_edit_vf(
        n=len(imgs),
        seg=seg,
        width=width,
        height=height,
        fps=fps,
        look=look,
        motion=motion,
        transition=transition,
        total=total,
    )
    if music is not None:
        cmd.extend(["-stream_loop", "-1", "-i", str(music.resolve())])
        cmd.extend(
            [
                "-filter_complex",
                f"[0:v]{vf}[vout];"
                "[1:a]aformat=sample_fmts=fltp:sample_rates=44100,volume=1[a1];"
                f"[2:a]aformat=sample_fmts=fltp:sample_rates=44100,volume={vol:.3f}[a2];"
                "[a1][a2]amix=inputs=2:duration=first[aout]",
                "-map", "[vout]", "-map", "[aout]",
            ]
        )
    else:
        cmd.extend(["-vf", vf, "-map", "0:v", "-map", "1:a"])
    cmd.extend(
        [
            "-c:v", "libx264", "-preset", preset, "-tune", "stillimage", "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart",
            str(output_path),
        ]
    )
    limit = 45 if (duration_sec or 0) < 30 else 250
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=limit)
    list_file.unlink(missing_ok=True)
    if result.returncode != 0 or not mp4_is_complete(output_path):
        if output_path.is_file() and not mp4_is_complete(output_path):
            output_path.unlink(missing_ok=True)
        err = ffmpeg_error_text(result.stderr or result.stdout or "ffmpeg failed")
        raise RuntimeError(f"No se pudo armar el video: {err}")
    return output_path


def verificar_ffprobe() -> bool:
    """Verifica si ffprobe está instalado y disponible en el PATH."""
    return shutil.which("ffprobe") is not None


def _montar_video_con_zoom_y_transiciones(
    lista_imagenes: list[Path],
    seg: float,
    width: int,
    height: int,
    video_solo: Path,
    fade_segundos: float = 0.25,
    zoom_final: float = 1.06,
) -> None:
    """
    Genera el video de imágenes con zoom suave (Ken Burns) y fundidos cortos entre escenas.
    Una sola llamada a FFmpeg: N entradas (una por imagen) + filter_complex con zoompan + fade + concat.
    """
    imagenes = [p for p in lista_imagenes if p.exists()]
    if not imagenes:
        return
    fps = 24
    frames_clip = max(1, int(seg * fps))
    # Zoom muy sutil: de 1.0 a zoom_final en frames_clip frames. Incremento por frame:
    zoom_inc = (zoom_final - 1.0) / frames_clip if frames_clip else 0
    # Fade in en frames (fade_segundos). OJO: evitamos fade out completo para no dejar el último clip totalmente negro,
    # porque luego el pipeline puede extender el video repitiendo el último tramo para igualar la duración del audio.
    # Si el último frame termina 100% negro, la extensión produce varios segundos/minutos de pantalla negra.
    fade_frames = max(1, int(fade_segundos * fps))

    # Rutas con barras normales para filter_complex (evitar problemas en Windows)
    def path_ff(v: Path) -> str:
        return str(v.resolve()).replace("\\", "/")

    # Construir filter_complex: [0:v] scale,crop,zoompan,fade in,fade out [v0]; [1:v] ... [v1]; ... [v0][v1]... concat
    partes = []
    for i in range(len(imagenes)):
        # zoompan: z='min(zoom+inc,zoom_final)':d=frames_clip:s=WxH
        # fade=t=in:st=0:d=fade_segundos
        scale_crop = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
        zp = f"zoompan=z='min(zoom+{zoom_inc:.6f},{zoom_final})':d={frames_clip}:s={width}x{height}:fps={fps}"
        fi = f"fade=t=in:st=0:d={fade_segundos}"
        # IMPORTANTÍSIMO: NO aplicamos fade out a negro aquí. Si el último clip termina en negro
        # y luego extendemos el video (stream_loop) para igualar la duración del audio,
        # el usuario ve muchos segundos de pantalla negra. Mejor dejar la última imagen visible.
        partes.append(f"[{i}:v]{scale_crop},{zp},{fi}[v{i}]")
    concat_inputs = "".join(f"[v{i}]" for i in range(len(imagenes)))
    concat_n = len(imagenes)
    filter_complex = ";".join(partes) + f";{concat_inputs}concat=n={concat_n}:v=1:a=0[out]"

    cmd = ["ffmpeg", "-y"]
    for p in imagenes:
        cmd.extend(["-loop", "1", "-t", "1", "-i", path_ff(p)])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        str(video_solo),
    ])
    try:
        # Timeout de seguridad: si FFmpeg se cuelga (por filtros o archivos raros),
        # no bloquear todo el pipeline; lanzamos error y el caller hará fallback a montaje estático.
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"FFmpeg (zoom+transiciones) excedió el tiempo límite: {e}")

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg (zoom+transiciones) falló: {result.stderr[:500]}")


def montar_video(
    lista_imagenes: list[Path],
    audio_narracion: Path | None,
    musica_fondo: Path | None = None,
    segundos_por_imagen: float | None = None,
    nombre_salida: str = "video_final",
    width: int = 1920,
    height: int = 1080,
    duracion_maxima_segundos: float | None = None,
    subtitles_path: Path | None = None,
    subtitle_style: str | None = None,
    transiciones_suaves: bool = False,
    *,
    output_path: Path | None = None,
    music_volume: float = 0.2,
) -> Path:
    """
    Une imágenes en secuencia (duración por imagen configurable),
    agrega narración como pista principal y música de fondo opcional.
    Si transiciones_suaves=True, aplica zoom suave (Ken Burns) y fundidos cortos entre imágenes.
    Si no hay imágenes, genera un video negro con la duración del audio.
    output_path: si se indica, escribe ahí (workspace documental); si no, output/videos/<nombre>.mp4.
    music_volume: volumen relativo de la música (narración siempre volume=1).
    """
    seg = segundos_por_imagen or get_duracion_por_imagen()
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        OUTPUT_VIDEO.mkdir(parents=True, exist_ok=True)
        out = OUTPUT_VIDEO / f"{nombre_salida}.mp4"
    music_vol = max(0.0, min(1.0, float(music_volume)))

    # Verificar FFmpeg antes de continuar
    if not verificar_ffmpeg():
        cmd = "brew install ffmpeg" if sys.platform == "darwin" else "winget install ffmpeg o choco install ffmpeg"
        raise RuntimeError(
            "FFmpeg no está instalado o no está en el PATH del sistema.\n\n"
            f"Para instalar: {cmd}\n"
            "O descargá desde: https://ffmpeg.org/download.html\n\n"
            "Después de instalar, reiniciá la aplicación."
        )
    
    # Calcular duración del audio para video negro
    duracion_audio = None
    if audio_narracion and audio_narracion.exists() and audio_narracion.stat().st_size > 0:
        if verificar_ffprobe():
            try:
                # Obtener duración del audio con ffprobe
                cmd_probe = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(audio_narracion)
                ]
                result = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
                duracion_audio = float(result.stdout.strip())
            except Exception:
                # Si falla, usar duración estimada basada en imágenes o default
                duracion_audio = len(lista_imagenes) * seg if lista_imagenes else 60.0
        else:
            # Si no hay ffprobe, usar duración estimada
            duracion_audio = len(lista_imagenes) * seg if lista_imagenes else 60.0

    # Si no hay imágenes, generar video negro
    if not lista_imagenes or all(not p.exists() for p in lista_imagenes):
        video_solo = out.with_stem(out.stem + "_solo_video")
        # Generar video negro con la duración del audio o 60 segundos por defecto
        duracion = duracion_audio or 60.0
        cmd_video_negro = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={width}x{height}:d={duracion}",
            "-r", "24",
            "-pix_fmt", "yuv420p",
            str(video_solo),
        ]
        subprocess.run(cmd_video_negro, check=True, capture_output=True)
    else:
        video_solo = out.with_stem(out.stem + "_solo_video")
        if transiciones_suaves and len([p for p in lista_imagenes if p.exists()]) > 0:
            try:
                print("🎬 Aplicando zoom suave y transiciones entre imágenes...")
                _montar_video_con_zoom_y_transiciones(
                    lista_imagenes=lista_imagenes,
                    seg=seg,
                    width=width,
                    height=height,
                    video_solo=video_solo,
                    fade_segundos=0.25,
                    zoom_final=1.06,
                )
            except Exception as e:
                print(f"⚠️ Falló video con zoom/transiciones ({e}), usando montaje estático.")
                transiciones_suaves = False
        if not transiciones_suaves:
            # Montaje estático: concat de imágenes con leve fade inicial
            list_file = out.with_suffix(".list.txt")
            with open(list_file, "w") as f:
                for p in lista_imagenes:
                    if p.exists():
                        f.write(f"file '{p.absolute()}'\nduration {seg}\n")
                if lista_imagenes:
                    f.write(f"file '{lista_imagenes[-1].absolute()}'\n")
            cmd_video = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-vf",
                (
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},"
                    f"fade=t=in:st=0:d=0.5"
                ),
                "-r", "24",
                "-pix_fmt", "yuv420p",
                str(video_solo),
            ]
            subprocess.run(cmd_video, check=True, capture_output=True)
            if list_file.exists():
                list_file.unlink()

    # Mezclar con audio
    if audio_narracion and audio_narracion.exists() and audio_narracion.stat().st_size > 0:
        if musica_fondo and musica_fondo.exists():
            # Dos pistas: narración + música baja
            mix = out.with_stem(out.stem + "_mix")
            cmd_mix = [
                "ffmpeg", "-y",
                "-i", str(audio_narracion),
                "-i", str(musica_fondo),
                "-filter_complex",
                f"[0:a]volume=1[a1];[1:a]volume={music_vol:.3f}[a2];[a1][a2]amix=inputs=2:duration=first",
                "-shortest", str(mix),
            ]
            subprocess.run(cmd_mix, check=True, capture_output=True)
            audio_final = mix
        else:
            audio_final = audio_narracion

        # Obtener duración del audio para asegurar que el video tenga esa duración
        duracion_audio_final = None
        print(f"🔍 Obteniendo duración del audio final...")
        if verificar_ffprobe():
            try:
                cmd_probe_audio = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(audio_final)
                ]
                result_audio = subprocess.run(cmd_probe_audio, capture_output=True, text=True, check=True)
                duracion_audio_final = float(result_audio.stdout.strip())
                print(f"📊 Duración del audio final: {duracion_audio_final:.1f} segundos ({duracion_audio_final/60:.1f} minutos)")
            except Exception as e:
                print(f"⚠️ No se pudo obtener duración del audio final: {e}")
                print(f"   Intentando método alternativo...")
                # Método alternativo: calcular desde el tamaño del archivo (aproximado)
                if audio_final.exists():
                    size_mb = audio_final.stat().st_size / (1024 * 1024)
                    # Estimación aproximada: 1 MB ≈ 1 minuto de audio MP3
                    duracion_audio_final = size_mb * 60
                    print(f"   Estimación aproximada: {duracion_audio_final:.1f} segundos")
        else:
            print(f"⚠️ ffprobe no disponible, no se puede obtener duración exacta del audio")
        
        # Obtener duración del video de imágenes
        duracion_video_imagenes = None
        print(f"🔍 Obteniendo duración del video de imágenes...")
        if verificar_ffprobe():
            try:
                cmd_probe_video = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(video_solo)
                ]
                result_video = subprocess.run(cmd_probe_video, capture_output=True, text=True, check=True)
                duracion_video_imagenes = float(result_video.stdout.strip())
                print(f"📊 Duración del video de imágenes: {duracion_video_imagenes:.1f} segundos ({duracion_video_imagenes/60:.1f} minutos)")
            except Exception as e:
                print(f"⚠️ No se pudo obtener duración del video: {e}")
                # Calcular duración estimada desde imágenes
                num_imagenes = len([p for p in lista_imagenes if p.exists()]) if lista_imagenes else 0
                duracion_video_imagenes = num_imagenes * seg
                print(f"   Estimación desde imágenes: {num_imagenes} imágenes × {seg}s = {duracion_video_imagenes:.1f} segundos")
        else:
            # Calcular duración estimada desde imágenes
            num_imagenes = len([p for p in lista_imagenes if p.exists()]) if lista_imagenes else 0
            duracion_video_imagenes = num_imagenes * seg
            print(f"📊 Duración estimada del video (sin ffprobe): {num_imagenes} imágenes × {seg}s = {duracion_video_imagenes:.1f} segundos")
        
        # Asegurar que siempre tengamos ambas duraciones antes de comparar
        if not duracion_video_imagenes and lista_imagenes:
            num_imagenes = len([p for p in lista_imagenes if p.exists()])
            duracion_video_imagenes = num_imagenes * seg
            print(f"📊 Duración estimada del video (fallback): {num_imagenes} imágenes × {seg}s = {duracion_video_imagenes:.1f}s")
        
        # Si el video es más corto que el audio, extenderlo
        print(f"🔍 Comparando duraciones:")
        print(f"   Video de imágenes: {duracion_video_imagenes}")
        print(f"   Audio final: {duracion_audio_final}")
        
        if duracion_audio_final and duracion_video_imagenes:
            diferencia = duracion_audio_final - duracion_video_imagenes
            print(f"   Diferencia: {diferencia:.1f} segundos")
            if duracion_video_imagenes < duracion_audio_final:
                print(f"⚠️ El video de imágenes ({duracion_video_imagenes:.1f}s) es más corto que el audio ({duracion_audio_final:.1f}s)")
                print(f"   Extendiendo el video para que coincida con el audio...")
                
                # Extender el video repitiendo el último frame
                video_extendido = out.with_stem(out.stem + "_extendido")
                
                # Usar loop del video existente y limitar a la duración del audio
                cmd_extend = [
                    "ffmpeg", "-y",
                    "-stream_loop", "-1",  # Loop infinito
                    "-i", str(video_solo),
                    "-t", str(duracion_audio_final),  # Limitar a la duración del audio
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-pix_fmt", "yuv420p",
                    "-avoid_negative_ts", "make_zero",
                    str(video_extendido)
                ]
                result_extend = subprocess.run(cmd_extend, capture_output=True, text=True)
                if result_extend.returncode != 0:
                    print(f"⚠️ Error al extender video: {result_extend.stderr}")
                    print(f"   Intentando método alternativo...")
                    # Método alternativo: concatenar el video consigo mismo
                    list_loop = out.with_suffix(".loop.txt")
                    num_loops = int(duracion_audio_final / duracion_video_imagenes) + 1
                    with open(list_loop, "w") as f:
                        for _ in range(num_loops):
                            f.write(f"file '{video_solo.absolute()}'\n")
                    cmd_concat = [
                        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", str(list_loop),
                        "-t", str(duracion_audio_final),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-pix_fmt", "yuv420p",
                        str(video_extendido)
                    ]
                    subprocess.run(cmd_concat, check=True, capture_output=True)
                    if list_loop.exists():
                        list_loop.unlink()
                else:
                    print(f"   ✅ Video extendido a {duracion_audio_final:.1f} segundos")
                
                # Verificar que el video extendido existe y tiene la duración correcta
                if video_extendido.exists():
                    video_solo = video_extendido
                    # Verificar duración del video extendido
                    if verificar_ffprobe():
                        try:
                            cmd_check = [
                                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1", str(video_extendido)
                            ]
                            result_check = subprocess.run(cmd_check, capture_output=True, text=True, check=True)
                            duracion_extendido = float(result_check.stdout.strip())
                            print(f"   ✅ Video extendido verificado: {duracion_extendido:.1f}s (objetivo: {duracion_audio_final:.1f}s)")
                        except:
                            pass
        
        # Limitar duración si se especifica
        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(video_solo),
            "-i", str(audio_final),
        ]

        # Subtítulos opcionales (SRT/ASS) con estilo configurable (ASS force_style)
        if subtitles_path and subtitles_path.exists():
            sub_filter = f"subtitles='{subtitles_path.as_posix()}'"
            if subtitle_style:
                sub_filter += f":force_style='{subtitle_style}'"
            cmd_final.extend(["-vf", sub_filter])

        cmd_final.extend([
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",  # Re-encodear video para mejor control
            "-c:a", "aac", "-b:a", "192k",
        ])
        
        # NUNCA usar -shortest porque puede cortar el audio
        # Siempre usar la duración del audio como referencia
        print(f"🔧 Configurando duración final del video...")
        print(f"   duracion_audio_final: {duracion_audio_final}")
        print(f"   duracion_maxima_segundos: {duracion_maxima_segundos}")
        
        # Asegurar que siempre tengamos la duración del audio
        if not duracion_audio_final:
            print(f"⚠️ No se obtuvo duración del audio antes, obteniéndola ahora...")
            if verificar_ffprobe():
                try:
                    cmd_probe_ahora = [
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_final)
                    ]
                    result_ahora = subprocess.run(cmd_probe_ahora, capture_output=True, text=True, check=True)
                    duracion_audio_final = float(result_ahora.stdout.strip())
                    print(f"   ✅ Duración del audio obtenida: {duracion_audio_final:.1f} segundos")
                except Exception as e:
                    print(f"   ⚠️ Error al obtener duración: {e}")
                    # Estimar desde tamaño del archivo
                    if audio_final.exists():
                        size_mb = audio_final.stat().st_size / (1024 * 1024)
                        duracion_audio_final = size_mb * 60  # 1 MB ≈ 1 minuto
                        print(f"   📊 Estimación desde tamaño: {duracion_audio_final:.1f} segundos")
        
        if duracion_maxima_segundos is not None:
            # Si hay límite máximo, usar el menor entre audio y límite
            duracion_final = min(duracion_audio_final or float('inf'), duracion_maxima_segundos)
            cmd_final.extend(["-t", str(duracion_final)])
            print(f"📹 Limitando video a {duracion_final:.1f} segundos (máximo especificado)")
        elif duracion_audio_final:
            # Usar la duración del audio como referencia
            cmd_final.extend(["-t", str(duracion_audio_final)])
            print(f"📹 Combinando video y audio con duración: {duracion_audio_final:.1f} segundos ({duracion_audio_final/60:.1f} minutos)")
            print(f"   ⚠️ IMPORTANTE: El video se limitará a esta duración. Si el video es más corto, debería haberse extendido antes.")
        else:
            # Último recurso: usar duración muy larga para no cortar
            print(f"⚠️ ADVERTENCIA CRÍTICA: No se puede determinar duración del audio")
            print(f"   Usando 10 minutos (600s) como seguridad para NO cortar el audio")
            cmd_final.extend(["-t", "600"])  # 10 minutos como seguridad
        
        cmd_final.append(str(out))
        print(f"🔧 Comando FFmpeg: {' '.join(cmd_final)}")
        result = subprocess.run(cmd_final, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️ Error al combinar video y audio:")
            print(f"   {result.stderr}")
            raise RuntimeError(f"Error al montar video: {result.stderr}")
        
        # Verificar duración final del video
        if verificar_ffprobe() and out.exists():
            try:
                cmd_verify = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(out)
                ]
                result_verify = subprocess.run(cmd_verify, capture_output=True, text=True, check=True)
                duracion_final_video = float(result_verify.stdout.strip())
                print(f"✅ Video final generado: {duracion_final_video:.1f} segundos")
                if duracion_audio_final and abs(duracion_final_video - duracion_audio_final) > 2.0:
                    print(f"⚠️ ADVERTENCIA: Duración del video ({duracion_final_video:.1f}s) no coincide con audio ({duracion_audio_final:.1f}s)")
            except:
                pass
    else:
        # Si no hay audio, copiar el video solo (negro o con imágenes)
        out.write_bytes(video_solo.read_bytes())

    return out
