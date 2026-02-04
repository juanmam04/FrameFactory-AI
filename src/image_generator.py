"""FASE 6: Generación masiva de imágenes con Stable Diffusion (API local/cloud)."""
import base64
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from .config_loader import BASE, get_negative_prompt, get_instrucciones_imagenes
from .scene_splitter import Escena

load_dotenv(BASE / ".env")

OUTPUT_IMAGES = BASE / "output" / "imagenes"
MAX_REINTENTOS = 3  # Default, se carga dinámicamente
PAUSA_REINTENTO = 5  # Default, se carga dinámicamente


def generar_imagen(prompt: str, escena_num: int, carpeta: Path, width: int | None = None, height: int | None = None) -> Path | None:
    """
    Envía prompt a Stable Diffusion (Automatic1111) y guarda la imagen.
    Reintentos automáticos si falla.
    width/height: Si se proporcionan, sobrescriben la configuración.
    """
    url = os.getenv("SD_API_URL", "http://127.0.0.1:7860").rstrip("/")
    endpoint = f"{url}/sdapi/v1/txt2img"
    
    # Cargar parámetros desde configuración
    instrucciones = get_instrucciones_imagenes()
    params = instrucciones.get("parametros_sd", {})
    reintentos_config = instrucciones.get("reintentos", {})
    max_reintentos = reintentos_config.get("max_reintentos", MAX_REINTENTOS)
    pausa_reintento = reintentos_config.get("pausa_segundos", PAUSA_REINTENTO)
    
    # Usar width/height proporcionados o los de la configuración
    img_width = width if width is not None else params.get("width", 1024)
    img_height = height if height is not None else params.get("height", 576)
    
    payload = {
        "prompt": prompt,
        "negative_prompt": get_negative_prompt(),
        "steps": params.get("steps", 25),
        "width": img_width,
        "height": img_height,
        "cfg_scale": params.get("cfg_scale", 7),
    }
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = f"escena_{escena_num:04d}.png"
    path = carpeta / nombre

    for intento in range(max_reintentos):
        try:
            r = requests.post(endpoint, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            img_b64 = data.get("images", [None])[0]
            if not img_b64:
                raise ValueError("No image in response")
            path.write_bytes(base64.b64decode(img_b64))
            return path
        except Exception as e:
            if intento < max_reintentos - 1:
                time.sleep(pausa_reintento)
            else:
                # Guardar placeholder o fallar según prefieras
                raise RuntimeError(f"Falló generación escena {escena_num}: {e}") from e
    return None


def generar_lote(
    escenas_con_prompts: list[tuple[Escena, str]],
    subcarpeta: str = "default",
    width: int | None = None,
    height: int | None = None,
) -> list[Path]:
    """Genera todas las imágenes y las guarda con nombre de escena."""
    carpeta = OUTPUT_IMAGES / subcarpeta
    rutas = []
    for escena, prompt in escenas_con_prompts:
        path = generar_imagen(prompt, escena.numero, carpeta, width=width, height=height)
        if path:
            rutas.append(path)
    return rutas
