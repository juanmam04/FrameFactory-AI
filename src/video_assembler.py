"""FASE 9: Montaje automático de video con FFmpeg (imágenes + narración + música opcional)."""
import subprocess
from pathlib import Path

from .config_loader import BASE, get_duracion_por_imagen

OUTPUT_VIDEO = BASE / "output" / "videos"


def montar_video(
    lista_imagenes: list[Path],
    audio_narracion: Path | None,
    musica_fondo: Path | None = None,
    segundos_por_imagen: float | None = None,
    nombre_salida: str = "video_final",
) -> Path:
    """
    Une imágenes en secuencia (duración por imagen configurable),
    agrega narración como pista principal y música de fondo opcional.
    """
    seg = segundos_por_imagen or get_duracion_por_imagen()
    OUTPUT_VIDEO.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_VIDEO / f"{nombre_salida}.mp4"

    # Lista de archivos para concat (FFmpeg)
    list_file = out.with_suffix(".list.txt")
    with open(list_file, "w") as f:
        for p in lista_imagenes:
            if p.exists():
                f.write(f"file '{p.absolute()}'\nduration {seg}\n")
        if lista_imagenes:
            # Última entrada sin duration para que FFmpeg calcule bien
            f.write(f"file '{lista_imagenes[-1].absolute()}'\n")

    # Video solo desde imágenes
    video_solo = out.with_stem(out.stem + "_solo_video")
    cmd_video = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-r", "24",  # 24 fps; cada imagen dura seg segundos
        "-pix_fmt", "yuv420p",
        str(video_solo),
    ]
    subprocess.run(cmd_video, check=True, capture_output=True)

    # Mezclar con audio
    if audio_narracion and audio_narracion.exists() and audio_narracion.stat().st_size > 0:
        if musica_fondo and musica_fondo.exists():
            # Dos pistas: narración + música baja
            mix = out.with_stem(out.stem + "_mix")
            cmd_mix = [
                "ffmpeg", "-y",
                "-i", str(audio_narracion),
                "-i", str(musica_fondo),
                "-filter_complex", "[0:a]volume=1[a1];[1:a]volume=0.2[a2];[a1][a2]amix=inputs=2:duration=first",
                "-shortest", str(mix),
            ]
            subprocess.run(cmd_mix, check=True, capture_output=True)
            audio_final = mix
        else:
            audio_final = audio_narracion

        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(video_solo),
            "-i", str(audio_final),
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            str(out),
        ]
        subprocess.run(cmd_final, check=True, capture_output=True)
    else:
        out.write_bytes(video_solo.read_bytes())

    if list_file.exists():
        list_file.unlink()
    return out
