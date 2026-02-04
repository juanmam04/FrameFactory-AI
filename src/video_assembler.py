"""FASE 9: Montaje automático de video con FFmpeg (imágenes + narración + música opcional)."""
import subprocess
import shutil
from pathlib import Path

from .config_loader import BASE, get_duracion_por_imagen

OUTPUT_VIDEO = BASE / "output" / "videos"


def verificar_ffmpeg() -> bool:
    """Verifica si FFmpeg está instalado y disponible en el PATH."""
    return shutil.which("ffmpeg") is not None


def verificar_ffprobe() -> bool:
    """Verifica si ffprobe está instalado y disponible en el PATH."""
    return shutil.which("ffprobe") is not None


def montar_video(
    lista_imagenes: list[Path],
    audio_narracion: Path | None,
    musica_fondo: Path | None = None,
    segundos_por_imagen: float | None = None,
    nombre_salida: str = "video_final",
    width: int = 1920,
    height: int = 1080,
    duracion_maxima_segundos: float | None = None,
) -> Path:
    """
    Une imágenes en secuencia (duración por imagen configurable),
    agrega narración como pista principal y música de fondo opcional.
    Si no hay imágenes, genera un video negro con la duración del audio.
    """
    seg = segundos_por_imagen or get_duracion_por_imagen()
    OUTPUT_VIDEO.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_VIDEO / f"{nombre_salida}.mp4"

    # Verificar FFmpeg antes de continuar
    if not verificar_ffmpeg():
        raise RuntimeError(
            "FFmpeg no está instalado o no está en el PATH del sistema.\n\n"
            "Para instalar FFmpeg en Windows:\n"
            "1. Descarga desde: https://ffmpeg.org/download.html\n"
            "2. O usa: winget install ffmpeg\n"
            "3. O usa: choco install ffmpeg\n"
            "4. IMPORTANTE: Agrega FFmpeg al PATH del sistema\n\n"
            "Después de instalar, reinicia la aplicación."
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
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-r", "24",  # 24 fps; cada imagen dura seg segundos
            "-pix_fmt", "yuv420p",
            str(video_solo),
        ]
        subprocess.run(cmd_video, check=True, capture_output=True)
        
        # Limpiar archivo temporal
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
                "-filter_complex", "[0:a]volume=1[a1];[1:a]volume=0.2[a2];[a1][a2]amix=inputs=2:duration=first",
                "-shortest", str(mix),
            ]
            subprocess.run(cmd_mix, check=True, capture_output=True)
            audio_final = mix
        else:
            audio_final = audio_narracion

        # Limitar duración si se especifica
        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(video_solo),
            "-i", str(audio_final),
            "-c:v", "copy", "-c:a", "aac",
        ]
        
        # Si hay duración máxima, limitar el video
        if duracion_maxima_segundos is not None:
            cmd_final.extend(["-t", str(duracion_maxima_segundos)])
        else:
            cmd_final.append("-shortest")
        
        cmd_final.append(str(out))
        subprocess.run(cmd_final, check=True, capture_output=True)
    else:
        # Si no hay audio, copiar el video solo (negro o con imágenes)
        out.write_bytes(video_solo.read_bytes())

    return out
