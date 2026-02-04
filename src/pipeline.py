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
            duracion_max = duracion_min + 3  # Default: 3 minutos más que el mínimo
        if duracion_max < duracion_min:
            duracion_max = duracion_min
        
        guion_texto = generar_guion(
            tema, 
            duracion_min=duracion_min, 
            duracion_max=duracion_max,
            plantilla=plantilla
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

    escenas = dividir_en_escenas(guion_texto)
    escenas_con_prompts = prompts_para_escenas(escenas)
    guardar_prompts_por_escena(escenas_con_prompts, proy)

    if not skip_imagenes:
        generar_lote(escenas_con_prompts, subcarpeta=proy, width=width, height=height)
    lista_imagenes = sorted((OUTPUT_IMAGES / proy).glob("escena_*.png"))

    texto_narracion = escenas_a_texto_continuo(escenas)
    audio_path = None
    if not skip_voz:
        audio_path = generar_voz(texto_narracion, nombre_archivo=proy, velocidad=velocidad_voz)
        if audio_path.exists() and audio_path.stat().st_size == 0:
            audio_path = None

    # Música: parámetro > .env BACKGROUND_MUSIC_PATH
    if musica_fondo is None:
        musica_fondo = get_background_music_path()
    if musica_fondo is not None and not musica_fondo.exists():
        musica_fondo = None

    video_path = montar_video(
        lista_imagenes=lista_imagenes,
        audio_narracion=audio_path,
        musica_fondo=musica_fondo,
        nombre_salida=proy,
        segundos_por_imagen=segundos_por_imagen,
        width=width,
        height=height,
    )

    metadata_path = None
    thumbnail_path = None
    if generar_metadata:
        metadata_path, thumbnail_path = generar_metadata_completa(
            proy, tema or proy, escenas, guion_texto,
            usar_ia_descripcion=True,
            generar_miniatura=not skip_miniatura,  # Generar miniatura si no se salta (usa DALL-E, no necesita Stable Diffusion)
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
