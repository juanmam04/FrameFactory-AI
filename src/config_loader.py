"""Carga de configuración: biblia visual y plantillas."""
import json
import os
from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE / "config"
META_DIR = BASE / "output" / "meta"
FEEDBACK_APRENDIZAJE_PATH = META_DIR / "feedback_aprendizaje.json"


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
    """
    Devuelve el style lock global para imágenes.
    Compatibilidad: si existe 'estilo_base' se usa; si no, 'style_lock'.
    """
    vb = get_visual_bible()
    return vb.get("estilo_base") or vb.get("style_lock", "Flat 2D storyboard illustration.")


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


def get_instrucciones_titulo() -> dict:
    """Carga instrucciones para generar TÍTULOS de YouTube / Shorts."""
    return load_yaml("instrucciones_titulo.yaml")


def get_instrucciones_imagenes() -> dict:
    """Carga instrucciones para generación masiva de imágenes."""
    return load_yaml("instrucciones_imagenes.yaml")


def get_instrucciones_descripcion_escenas() -> dict:
    """Carga instrucciones para generar descripción visual por escena (para coherencia de imágenes)."""
    return load_yaml("instrucciones_descripcion_escenas.yaml")


def get_subtitle_styles() -> dict:
    """Estilos de subtítulos (ASS force_style) para shorts / reels / videos."""
    return load_yaml("subtitle_styles.yaml")


def get_character_references() -> dict:
    """Devuelve rutas relativas a las imágenes de referencia del personaje."""
    vb = get_visual_bible()
    return vb.get("character_reference", {})


def get_character_reference_mode() -> str:
    """
    Cómo interpretar el PNG del protagonista para Kontext.
    ``identity_sheet`` (default): ancla identidad, no composición/fondo de la ficha.
    ``scene_reference``: el input ya es una escena; no se añade el bloque anti–model-sheet.
    """
    from .kontext_prompt import normalize_character_reference_mode

    return normalize_character_reference_mode(os.getenv("CHARACTER_REFERENCE_MODE"))


def get_kontext_context_instruction() -> str:
    """
    Instrucción corta para modelos imagen+texto (ej. FLUX Kontext) cuando hay referencia de personaje.
    Si no está en visual_bible, usa un texto por defecto alineado al style_lock actual.
    """
    vb = get_visual_bible()
    raw = (vb.get("kontext_context_instruction") or "").strip()
    if raw:
        return raw
    return (
        "Cinematic cartoon storyboard style. Same visual language as the reference image. "
        "Keep character identity from the reference (head shape, eyes, body proportions, line work, lighting). "
        "Adapt pose, expression and outfit to this scene while keeping the character recognizable. "
        "Clear readable action and location. No UI, no text, no photorealism."
    )


def get_visual_references() -> dict:
    """
    Referencias visuales mínimas del proyecto (si existen).
    En la nueva arquitectura pueden ser solo:
    - character_front.png
    - character_side.png
    - character_closeup.png
    - outfit_sheet.png
    """
    vb = get_visual_bible()
    return vb.get("visual_reference", {})


def get_visual_reference_rules() -> str:
    """Reglas opcionales asociadas a las referencias visuales (puede estar vacío en la nueva arquitectura)."""
    vb = get_visual_bible()
    return (vb.get("visual_reference_rules") or "").strip()


def has_any_visual_reference() -> bool:
    """True si al menos una imagen de referencia visual existe en disco (para activar las reglas en el prompt)."""
    for rel in get_visual_references().values():
        if rel and (BASE / rel).exists() and (BASE / rel).stat().st_size > 0:
            return True
    return False


def get_outfit_library() -> dict:
    """Carga la biblioteca de outfits y props (outfit_library.yaml)."""
    return load_yaml("outfit_library.yaml")


def get_character_bible() -> dict:
    """Carga la biblia de personajes persistentes (character_bible.yaml)."""
    return load_yaml("character_bible.yaml")


def get_role_library() -> dict:
    """Carga la librería de roles funcionales (role_library.yaml)."""
    return load_yaml("role_library.yaml")


def get_visual_motifs() -> dict:
    """Carga motivos visuales (visual_motifs.yaml)."""
    return load_yaml("visual_motifs.yaml")


def get_preferencias_aprendidas(max_entradas: int = 25) -> str:
    """Preferencias guardadas al regenerar con feedback. Desactivado: no se inyectan en prompts de imagen
    para evitar contradicciones y errores (anatomía, estilo). El feedback se sigue guardando para la regeneración
    individual, pero no se reutiliza en generaciones nuevas."""
    return ""
