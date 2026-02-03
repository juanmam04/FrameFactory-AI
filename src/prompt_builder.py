"""FASE 5: Conversión de escenas a prompts visuales (acción + estilo + cámara)."""
import random
from .config_loader import get_visual_bible
from .scene_splitter import Escena


def construir_prompt(escena: Escena, indice_plan: int | None = None) -> str:
    """
    Combina acción de la escena + estilo base + reglas de cámara.
    Varía el plano según el índice para evitar repetición.
    """
    vb = get_visual_bible()
    estilo = vb.get("estilo_base", "stickman 2D cinematográfico")
    planos = vb.get("camara", {}).get("variedad_planos") or [
        "plano general", "plano medio", "primer plano", "plano detalle"
    ]
    idx = (indice_plan if indice_plan is not None else escena.numero - 1) % len(planos)
    plano = planos[idx]
    # Acción descriptiva para la imagen (resumir escena en una frase visual)
    accion = escena.texto[:200].replace("\n", " ")
    return f"{plano}, {accion}, {estilo}, luz suave, fondo simple, alta calidad"


def prompts_para_escenas(escenas: list[Escena], shuffle_planos: bool = False) -> list[tuple[Escena, str]]:
    """Genera un prompt por escena con variedad de planos."""
    vb = get_visual_bible()
    planos = vb.get("camara", {}).get("variedad_planos") or []
    n_planos = len(planos) or 4
    orden = list(range(n_planos)) * (len(escenas) // n_planos + 1)
    if shuffle_planos:
        random.shuffle(orden)
    return [
        (e, construir_prompt(e, orden[i]))
        for i, e in enumerate(escenas)
    ]
