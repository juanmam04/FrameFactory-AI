"""FASE 5: Conversión de escenas a prompts visuales (acción + estilo + cámara)."""
import random
from .config_loader import get_visual_bible, get_instrucciones_imagenes
from .scene_splitter import Escena


def construir_prompt(escena: Escena, indice_plan: int | None = None) -> str:
    """
    Combina acción de la escena + estilo base + reglas de cámara.
    Varía el plano según el índice para evitar repetición.
    Usa el template configurado en instrucciones_imagenes.yaml
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
    
    # Usar template configurado o fallback
    instrucciones = get_instrucciones_imagenes()
    template = instrucciones.get("prompt_template", "{plano}, {accion}, {estilo}, luz suave, fondo simple, alta calidad")
    
    # Variables base requeridas
    variables = {
        "plano": plano,
        "accion": accion,
        "estilo": estilo,
    }
    
    # Variables opcionales (si están en el template, usar valores por defecto)
    # Estas se pueden extraer de la escena o usar valores genéricos
    emociones_posibles = ["tensión", "determinación", "conflicto", "duda", "decisión", "intensidad"]
    fases_posibles = ["inicio", "desarrollo", "clímax", "resolución"]
    momentos_posibles = ["momento clave", "punto de inflexión", "decisión importante", "conflicto central"]
    
    # Detectar qué variables opcionales necesita el template
    import re
    variables_en_template = set(re.findall(r'\{(\w+)\}', template))
    
    # Agregar variables opcionales si están en el template
    if "emocion" in variables_en_template:
        # Usar una emoción basada en el número de escena para variedad
        emocion_idx = (escena.numero - 1) % len(emociones_posibles)
        variables["emocion"] = emociones_posibles[emocion_idx]
    
    if "fase_psicologica" in variables_en_template:
        # Distribuir fases según el número de escena (aproximación simple)
        # Si no tenemos el total de escenas, usar distribución circular
        fase_idx = (escena.numero - 1) % len(fases_posibles)
        variables["fase_psicologica"] = fases_posibles[fase_idx]
    
    if "momento_de_la_historia" in variables_en_template:
        # Usar momento basado en la posición de la escena
        momento_idx = (escena.numero - 1) % len(momentos_posibles)
        variables["momento_de_la_historia"] = momentos_posibles[momento_idx]
    
    # Formatear el template con las variables disponibles
    try:
        return template.format(**variables)
    except KeyError as e:
        # Si falta alguna variable, usar el template simple
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
