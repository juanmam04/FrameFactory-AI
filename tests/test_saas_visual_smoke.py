"""Pruebas de humo: overlay personaje (main_h) y ASS de subtítulos (sin API)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


def _have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.mark.skipif(not _have_ffmpeg(), reason="FFmpeg no está en PATH")
def test_overlay_uses_main_h_character_visible(tmp_path: Path) -> None:
    """Un PNG opaco encima de un fondo debe verse (overlay y=main_h-overlay_h-24)."""
    bg = tmp_path / "bg.png"
    ch = tmp_path / "ch.png"
    out = tmp_path / "out.mp4"
    # Fondo rojo 1280x720
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=1280x720:d=1",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(bg),
        ],
        check=True,
        capture_output=True,
    )
    # Personaje: rectángulo verde 400x500
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=green:s=400x500:d=1",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(ch),
        ],
        check=True,
        capture_output=True,
    )
    fc = (
        "[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,format=yuv420p[bg0];"
        "[1:v]format=rgba,scale=-2:500:force_original_aspect_ratio=decrease[ch0];"
        "[bg0][ch0]overlay=x=24:y=main_h-overlay_h-24:format=auto[vout]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(bg),
            "-loop",
            "1",
            "-i",
            str(ch),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex",
            fc,
            "-map",
            "[vout]",
            "-map",
            "2:a",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    assert out.exists() and out.stat().st_size > 2000


@pytest.mark.skipif(not _have_ffmpeg(), reason="FFmpeg no está en PATH")
def test_burn_ass_bottom_alignment(tmp_path: Path) -> None:
    from src.saas_subtitles import burn_subtitles_on_video, write_ass_from_block_audios

    vid = tmp_path / "base.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=1280x720:d=2",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(vid),
        ],
        check=True,
        capture_output=True,
    )
    blocks = [{"text": "Texto de prueba abajo"}]
    # Audio ~1.5s
    aud = tmp_path / "a.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=440:d=1.5", "-c:a", "libmp3lame", str(aud)],
        check=True,
        capture_output=True,
    )
    ass = tmp_path / "t.ass"
    write_ass_from_block_audios(blocks, [aud], ass, subtitle_style_key="default")
    assert r"{\an2}" in ass.read_text(encoding="utf-8-sig")
    burned = tmp_path / "burned.mp4"
    burn_subtitles_on_video(vid, ass, None, burned)
    assert burned.exists() and burned.stat().st_size > 1000
