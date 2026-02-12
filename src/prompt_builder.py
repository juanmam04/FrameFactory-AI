"""FASE 5: Conversión de escenas a prompts visuales (acción + estilo + cámara).
Usa el Prompt Maestro: stickman 2D plano, cámara distinta cada imagen, escena = guion."""
import random
from .config_loader import get_visual_bible, get_instrucciones_imagenes, get_prompt_maestro
from .scene_splitter import Escena


def construir_prompt(escena: Escena, indice_plan: int | None = None) -> str:
    """
    Combina Prompt Maestro + cámara (distinta por escena) + acción de la escena + estilo.
    Cada imagen: misma cámara prohibida que la anterior; escena = lo que dice el guion.
    """
    vb = get_visual_bible()
    estilo = vb.get("estilo_base", "stickman 2D cinematográfico")
    maestro = get_prompt_maestro()
    variedad_camara = maestro.get("variedad_camara") or []
    if not variedad_camara:
        planos = vb.get("camara", {}).get("variedad_planos") or [
            "plano general", "plano medio", "primer plano", "plano detalle"
        ]
        variedad_camara = planos
    idx = (indice_plan if indice_plan is not None else escena.numero - 1) % len(variedad_camara)
    camera_esta_imagen = variedad_camara[idx]
    accion = escena.texto[:200].replace("\n", " ")
    prefijo = (maestro.get("prefijo_prompt") or "").strip()
    objetivo = (maestro.get("objetivo") or "Frame claro, acción visible, emoción coherente.").strip()

    instrucciones = get_instrucciones_imagenes()
    template = instrucciones.get("prompt_template", "{plano}, {accion}, {estilo}, 16:9.")
    variables = {
        "plano": camera_esta_imagen,
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
    
    try:
        cuerpo = template.format(**variables)
    except KeyError:
        cuerpo = f"{camera_esta_imagen}, {accion}, {estilo}, 16:9."
    if prefijo:
        cuerpo = f"{prefijo} {camera_esta_imagen}. {cuerpo} {objetivo}"
    return cuerpo


def prompts_para_escenas(escenas: list[Escena], shuffle_planos: bool = False) -> list[tuple[Escena, str]]:
    """Un prompt por escena; cámara distinta cada vez (variedad_camara del Prompt Maestro)."""
    maestro = get_prompt_maestro()
    n_camaras = len(maestro.get("variedad_camara") or [])
    if not n_camaras:
        vb = get_visual_bible()
        n_camaras = len(vb.get("camara", {}).get("variedad_planos") or ["p"]) or 4
    indices = list(range(n_camaras)) * (len(escenas) // n_camaras + 1)
    if shuffle_planos:
        random.shuffle(indices)
    return [
        (e, construir_prompt(e, indices[i]))
        for i, e in enumerate(escenas)
    ]
