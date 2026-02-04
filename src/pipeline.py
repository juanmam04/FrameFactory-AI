"""FASE 11: Script maestro – ejecuta todo el pipeline con un solo comando."""
import argparse
import re
from pathlib import Path

from .config_loader import BASE

try:
    from .config_loader import get_background_music_path
except ImportError:
    def get_background_music_path():
        return None
from .script_generator import generar_guion, guardar_guion
from .scene_splitter import dividir_en_escenas, escenas_a_texto_continuo
from .prompt_builder import prompts_para_escenas
from .image_generator import generar_lote, OUTPUT_IMAGES
from .voice_generator import generar_voz
from .video_assembler import montar_video
from .regeneration import guardar_prompts_por_escena
from .metadata_youtube import generar_metadata_completa


def _recortar_audio_por_duracion(audio_path: Path, duracion_max_segundos: float) -> Path:
    """Recorta el audio para que no exceda la duración máxima usando FFmpeg."""
    import subprocess
    import shutil
    
    if not shutil.which("ffmpeg"):
        return audio_path
    
    try:
        # Crear archivo temporal
        audio_recortado = audio_path.parent / f"{audio_path.stem}_recortado{audio_path.suffix}"
        
        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-t", str(duracion_max_segundos),  # Limitar duración
            "-c", "copy",  # Copiar sin re-encodear si es posible
            str(audio_recortado),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Reemplazar el archivo original
        if audio_recortado.exists():
            audio_path.unlink()
            audio_recortado.rename(audio_path)
        
        return audio_path
    except Exception as e:
        print(f"⚠️ Error al recortar audio: {e}, usando audio original")
        return audio_path


def sanitizar_nombre_proyecto(nombre: str) -> str:
    """
    Sanitiza el nombre del proyecto eliminando caracteres inválidos para Windows.
    Caracteres inválidos: < > : " | ? * \
    """
    # Caracteres inválidos en Windows
    caracteres_invalidos = r'[<>:"|?*\\]'
    # Reemplazar caracteres inválidos con guión bajo
    nombre_limpio = re.sub(caracteres_invalidos, '_', nombre)
    # Reemplazar espacios múltiples con uno solo
    nombre_limpio = re.sub(r'\s+', '_', nombre_limpio)
    # Eliminar guiones bajos múltiples
    nombre_limpio = re.sub(r'_+', '_', nombre_limpio)
    # Eliminar guiones bajos al inicio y final
    nombre_limpio = nombre_limpio.strip('_')
    # Limitar longitud y asegurar que no esté vacío
    if not nombre_limpio:
        nombre_limpio = "proyecto"
    return nombre_limpio[:50]  # Limitar a 50 caracteres


def run(
    tema: str | None = None,
    guion_path: Path | None = None,
    duracion_min: int = 2,
    duracion_max: int | None = None,
    plantilla: str = "explicativo",
    nombre_proyecto: str | None = None,
    skip_imagenes: bool = False,
    skip_voz: bool = False,
    musica_fondo: Path | None = None,
    generar_metadata: bool = True,
    velocidad_voz: float = 1.0,
    segundos_por_imagen: float | None = None,
    width: int = 1920,
    height: int = 1080,
    skip_miniatura: bool = False,
) -> tuple[Path, Path | None]:
    """
    Pipeline completo:
    Entrada: tema (para generar guion) o ruta a guion existente.
    Salida: (video_path, metadata_path). metadata_path es None si generar_metadata=False.
    """
    if tema:
        # Asegurar que duracion_max >= duracion_min
        if duracion_max is None:
            duracion_max = duracion_min  # Por defecto, duración exacta
        if duracion_max < duracion_min:
            duracion_max = duracion_min
        
        # Obtener segundos por imagen para calcular escenas exactas
        seg_por_img = segundos_por_imagen or 5.0
        
        guion_texto = generar_guion(
            tema, 
            duracion_min=duracion_min, 
            duracion_max=duracion_max,
            plantilla=plantilla,
            segundos_por_imagen=seg_por_img,
        )
        proy = nombre_proyecto or tema[:30].replace(" ", "_")
        proy = sanitizar_nombre_proyecto(proy)
        guardar_guion(guion_texto, proy)
    elif guion_path and guion_path.exists():
        guion_texto = guion_path.read_text(encoding="utf-8")
        proy = nombre_proyecto or guion_path.stem
        proy = sanitizar_nombre_proyecto(proy)
    else:
        raise ValueError("Indica --tema o --guion con un archivo existente.")

    escenas = dividir_en_escenas(guion_texto, segundos_por_imagen=seg_por_img)
    
    # NO recortar escenas - la IA debe generar la duración correcta
    # Solo validar y advertir si es muy diferente
    if tema and duracion_max is not None:
        duracion_max_segundos = duracion_max * 60
        duracion_total = sum(e.duracion_segundos for e in escenas)
        
        if duracion_total > duracion_max_segundos * 1.2:
            print(f"⚠️ ADVERTENCIA: Guion tiene {duracion_total:.1f}s, objetivo: {duracion_max_segundos:.1f}s. La IA debería haber generado el tamaño correcto.")
    
    escenas_con_prompts = prompts_para_escenas(escenas)
    guardar_prompts_por_escena(escenas_con_prompts, proy)

    if not skip_imagenes:
        generar_lote(escenas_con_prompts, subcarpeta=proy, width=width, height=height)
    lista_imagenes = sorted((OUTPUT_IMAGES / proy).glob("escena_*.png"))

    texto_narracion = escenas_a_texto_continuo(escenas)
    audio_path = None
    if not skip_voz:
        audio_path = generar_voz(texto_narracion, nombre_archivo=proy, velocidad=velocidad_voz)
        if audio_path.exists() and audio_path.stat().st_size > 0:
            # NO recortar audio - el guion debe ser del tamaño correcto
            # Solo validar duración del audio
            if tema and duracion_max is not None:
                import subprocess
                import shutil
                if shutil.which("ffprobe"):
                    try:
                        cmd_probe = [
                            "ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
                        ]
                        result = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
                        duracion_audio = float(result.stdout.strip())
                        if duracion_audio > (duracion_max * 60 * 1.2):
                            print(f"⚠️ ADVERTENCIA: Audio tiene {duracion_audio:.1f}s, objetivo: {duracion_max * 60:.1f}s. El guion debería haber sido del tamaño correcto.")
                    except Exception:
                        pass
        else:
            audio_path = None

    # Música: parámetro > .env BACKGROUND_MUSIC_PATH
    if musica_fondo is None:
        musica_fondo = get_background_music_path()
    if musica_fondo is not None and not musica_fondo.exists():
        musica_fondo = None

    # NO limitar duración del video - el guion debe ser del tamaño correcto
    video_path = montar_video(
        lista_imagenes=lista_imagenes,
        audio_narracion=audio_path,
        musica_fondo=musica_fondo,
        nombre_salida=proy,
        segundos_por_imagen=segundos_por_imagen,
        width=width,
        height=height,
        duracion_maxima_segundos=None,  # No limitar - confiar en que el guion es del tamaño correcto
    )

    metadata_path = None
    thumbnail_path = None
    if generar_metadata:
        metadata_path, thumbnail_path = generar_metadata_completa(
            proy, tema or proy, escenas, guion_texto,
            usar_ia_descripcion=True,
            generar_miniatura_flag=not skip_miniatura,  # Generar miniatura si no se salta (usa DALL-E, no necesita Stable Diffusion)
        )

    return video_path, metadata_path, thumbnail_path


def main():
    parser = argparse.ArgumentParser(description="FrameFactory-AI: pipeline de video desde guion o tema")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--tema", type=str, help="Tema para generar guion y video")
    g.add_argument("--guion", type=Path, help="Ruta a archivo de guion .txt")
    parser.add_argument("--duracion", type=int, default=2, help="Duración objetivo en minutos (solo con --tema)")
    parser.add_argument("--plantilla", type=str, default="explicativo", choices=["explicativo", "historia", "listado"])
    parser.add_argument("--nombre", type=str, help="Nombre del proyecto (carpetas y archivos de salida)")
    parser.add_argument("--skip-imagenes", action="store_true", help="No generar imágenes (usar las existentes)")
    parser.add_argument("--skip-voz", action="store_true", help="No generar voz")
    parser.add_argument("--musica", type=Path, help="Ruta a archivo de música de fondo")
    args = parser.parse_args()

    musica = args.musica if args.musica and args.musica.exists() else None
    video_path, metadata_path = run(
        tema=args.tema,
        guion_path=args.guion,
        duracion_min=args.duracion,
        plantilla=args.plantilla,
        nombre_proyecto=args.nombre,
        skip_imagenes=args.skip_imagenes,
        skip_voz=args.skip_voz,
        musica_fondo=musica,
    )
    print(f"Video generado: {video_path}")
    if metadata_path:
        print(f"Metadata YouTube: {metadata_path}")


if __name__ == "__main__":
    main()
