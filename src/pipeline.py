"""FASE 11: Script maestro – ejecuta todo el pipeline con un solo comando."""
import argparse
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


def run(
    tema: str | None = None,
    guion_path: Path | None = None,
    duracion_min: int = 2,
    plantilla: str = "explicativo",
    nombre_proyecto: str | None = None,
    skip_imagenes: bool = False,
    skip_voz: bool = False,
    musica_fondo: Path | None = None,
    generar_metadata: bool = True,
) -> tuple[Path, Path | None]:
    """
    Pipeline completo:
    Entrada: tema (para generar guion) o ruta a guion existente.
    Salida: (video_path, metadata_path). metadata_path es None si generar_metadata=False.
    """
    if tema:
        guion_texto = generar_guion(tema, duracion_min=duracion_min, plantilla=plantilla)
        proy = nombre_proyecto or tema[:30].replace(" ", "_")
        guardar_guion(guion_texto, proy)
    elif guion_path and guion_path.exists():
        guion_texto = guion_path.read_text(encoding="utf-8")
        proy = nombre_proyecto or guion_path.stem
    else:
        raise ValueError("Indica --tema o --guion con un archivo existente.")

    escenas = dividir_en_escenas(guion_texto)
    escenas_con_prompts = prompts_para_escenas(escenas)
    guardar_prompts_por_escena(escenas_con_prompts, proy)

    if not skip_imagenes:
        generar_lote(escenas_con_prompts, subcarpeta=proy)
    lista_imagenes = sorted((OUTPUT_IMAGES / proy).glob("escena_*.png"))

    texto_narracion = escenas_a_texto_continuo(escenas)
    audio_path = None
    if not skip_voz:
        audio_path = generar_voz(texto_narracion, nombre_archivo=proy)
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
    )

    metadata_path = None
    if generar_metadata:
        metadata_path = generar_metadata_completa(proy, tema or proy, escenas, guion_texto)

    return video_path, metadata_path


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
