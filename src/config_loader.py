"""Carga de configuración: biblia visual y plantillas."""
from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE / "config"


def load_yaml(name: str) -> dict:
    path = CONFIG_DIR / name
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_visual_bible() -> dict:
    return load_yaml("visual_bible.yaml")


def get_plantillas_guion() -> dict:
    return load_yaml("plantillas_guion.yaml")


def get_duracion_por_imagen() -> int:
    vb = get_visual_bible()
    return int(vb.get("duracion_por_imagen_segundos", 5))


def get_estilo_base() -> str:
    vb = get_visual_bible()
    return vb.get("estilo_base", "stickman 2D cinematográfico")


def get_narrative_rules() -> dict:
    return load_yaml("narrative_rules.yaml")


def get_negative_prompt() -> str:
    vb = get_visual_bible()
    return vb.get("negative_prompt", "blurry, low quality, distorted, text, watermark")


def get_prohibido_en_imagen() -> str:
    """Texto que se añade a los prompts para prohibir UI de reproductor/editor y mantener estilo único."""
    vb = get_visual_bible()
    return vb.get("prohibido_en_imagen", "Sin reproductor de video, sin barra de reproducción, sin interfaz de editor. Solo contenido de la escena.")


def get_background_music_path() -> Path | None:
    """Ruta opcional a música de fondo desde .env (BACKGROUND_MUSIC_PATH)."""
    import os
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
    p = os.getenv("BACKGROUND_MUSIC_PATH")
    if not p:
        return None
    path = Path(p)
    return path if path.is_absolute() else BASE / path


def get_instrucciones_descripcion() -> dict:
    """Carga instrucciones para generar descripción de YouTube."""
    return load_yaml("instrucciones_descripcion.yaml")


def get_instrucciones_miniatura() -> dict:
    """Carga instrucciones para generar prompt de miniatura."""
    return load_yaml("instrucciones_miniatura.yaml")


def get_instrucciones_imagenes() -> dict:
    """Carga instrucciones para generación masiva de imágenes."""
    return load_yaml("instrucciones_imagenes.yaml")


def get_instrucciones_descripcion_escenas() -> dict:
    """Carga instrucciones para generar descripción visual por escena (para coherencia de imágenes)."""
    return load_yaml("instrucciones_descripcion_escenas.yaml")