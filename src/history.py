"""Sistema de historial para guardar información de videos generados."""
import json
from datetime import datetime
from pathlib import Path

from .config_loader import BASE

HISTORY_FILE = BASE / "output" / "historial.json"


def guardar_en_historial(
    nombre_proyecto: str,
    tema: str,
    guion_texto: str,
    video_path: Path,
    metadata_path: Path | None = None,
    thumbnail_path: Path | None = None,
    audio_path: Path | None = None,
    word_count: int = 0,
    estimated_minutes: float = 0.0,
    target_words: int = 0,
    width: int = 1920,
    height: int = 1080,
    velocidad_voz: float = 1.0,
    segundos_por_imagen: float = 5.0,
) -> dict:
    """
    Guarda información del video generado en el historial.
    Retorna el registro guardado.
    """
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Cargar historial existente
    historial = cargar_historial()
    
    # Crear registro
    registro = {
        "id": len(historial) + 1,
        "fecha": datetime.now().isoformat(),
        "nombre_proyecto": nombre_proyecto,
        "tema": tema,
        "guion_texto": guion_texto,
        "video_path": str(video_path) if video_path else None,
        "metadata_path": str(metadata_path) if metadata_path else None,
        "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
        "audio_path": str(audio_path) if audio_path else None,
        "word_count": word_count,
        "estimated_minutes": estimated_minutes,
        "target_words": target_words,
        "width": width,
        "height": height,
        "velocidad_voz": velocidad_voz,
        "segundos_por_imagen": segundos_por_imagen,
    }
    
    # Agregar al historial (más reciente primero)
    historial.insert(0, registro)
    
    # Guardar historial (mantener solo los últimos 100 para no hacer el archivo muy grande)
    if len(historial) > 100:
        historial = historial[:100]
    
    HISTORY_FILE.write_text(
        json.dumps(historial, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    return registro


def cargar_historial() -> list[dict]:
    """Carga el historial completo."""
    if not HISTORY_FILE.exists():
        return []
    
    try:
        contenido = HISTORY_FILE.read_text(encoding="utf-8")
        return json.loads(contenido)
    except Exception:
        return []


def obtener_video_por_id(video_id: int) -> dict | None:
    """Obtiene un video específico del historial por su ID."""
    historial = cargar_historial()
    for registro in historial:
        if registro.get("id") == video_id:
            return registro
    return None


def eliminar_del_historial(video_id: int) -> bool:
    """Elimina un video del historial."""
    historial = cargar_historial()
    historial_original = len(historial)
    historial = [r for r in historial if r.get("id") != video_id]
    
    if len(historial) < historial_original:
        HISTORY_FILE.write_text(
            json.dumps(historial, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return True
    return False
