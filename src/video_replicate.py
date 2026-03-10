"""Generación de CLIPS DE VIDEO a partir de IMÁGENES usando Replicate (google/veo-3-fast por defecto)."""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from .config_loader import BASE

load_dotenv(BASE / ".env")


def _get_replicate_video_model() -> str:
    """Modelo de video en Replicate. Por defecto google/veo-3-fast."""
    return os.getenv("REPLICATE_VIDEO_MODEL", "google/veo-3-fast").strip()


def generar_clip_desde_imagen(
    imagen_path: Path,
    prompt: str,
    proyecto: str,
    escena_num: int,
    duracion_segundos: int = 6,
    aspect_ratio: str = "16:9",
    resolution: str = "1080p",
) -> Path:
    """
    Genera un clip de video corto a partir de una imagen existente usando Replicate (Veo).

    - imagen_path: PNG de la escena (ya generada).
    - prompt: descripción visual de la escena (texto).
    - proyecto: nombre sanitizado del proyecto (para carpeta de salida).
    - escena_num: número de escena (para nombre de archivo).
    """
    import replicate as replicate_client

    imagen_path = Path(imagen_path)
    if not imagen_path.exists() or imagen_path.stat().st_size == 0:
        raise FileNotFoundError(f"No se encontró la imagen para la escena: {imagen_path}")

    prompt = (prompt or "").strip()
    if not prompt:
        prompt = "A short cinematic shot in the same style as the reference image."

    model = _get_replicate_video_model()
    output_dir = BASE / "output" / "clips" / proyecto
    output_dir.mkdir(parents=True, exist_ok=True)
    destino = output_dir / f"escena_{escena_num:04d}.mp4"

    # Limitar duración a valores razonables (4–10)
    duracion = max(4, min(int(duracion_segundos or 6), 10))

    with open(imagen_path, "rb") as f:
        try:
            output = replicate_client.run(
                model,
                input={
                    "prompt": prompt,
                    "image": f,
                    "duration": duracion,
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                    "generate_audio": False,
                },
            )
        except Exception as e:
            raise RuntimeError(f"Replicate video ({model}) no pudo generar el clip: {e}") from e

    if not output:
        raise RuntimeError("Replicate video no devolvió ninguna salida.")

    url = output[0] if isinstance(output, (list, tuple)) else output
    if hasattr(url, "read"):
        data = url.read()
    elif isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        data = r.content
    else:
        raise RuntimeError(f"Salida inesperada de Replicate video: {url!r}")

    destino.write_bytes(data)
    return destino

