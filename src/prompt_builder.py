"""FASE 5: Conversión de escenas a prompts visuales (acción + estilo + cámara)."""
import re
import random
from .config_loader import get_visual_bible, get_instrucciones_imagenes, get_prohibido_en_imagen
from .scene_splitter import Escena


def construir_prompt(
    escena: Escena,
    indice_plan: int | None = None,
    descripcion_visual: str | None = None,
) -> str:
    """
    Combina acción de la escena + estilo base + reglas de cámara.
    Si se pasa descripcion_visual (generada por IA por escena), se usa como acción para máxima coherencia.
    """
    vb = get_visual_bible()
    estilo = vb.get("estilo_base", "stickman 2D cinematográfico")
    planos = vb.get("camara", {}).get("variedad_planos") or [
        "plano general", "plano medio", "primer plano", "plano detalle"
    ]
    idx = (indice_plan if indice_plan is not None else escena.numero - 1) % len(planos)
    plano = planos[idx]
    # Acción: descripción visual por escena (IA) o fallback al texto de la escena (solo contenido variable; el estilo es regla general)
    if descripcion_visual and descripcion_visual.strip():
        accion = descripcion_visual.strip().replace("\n", " ")
        # Quitar frases que describan estilo (stickman, 2D, ilustración, etc.) para no duplicar ni contradecir la regla general
        for palabra in ("stickman", "2D", "ilustración", "ilustracion", "cinematográfico", "estilo limpio", "líneas negras", "mismo personaje consistente"):
            if palabra.lower() in accion.lower():
                accion = re.sub(rf"[^.]*{re.escape(palabra)}[^.]*\.?", "", accion, flags=re.IGNORECASE)
        accion = " ".join(accion.split()).strip()[:400] or escena.texto[:200].replace("\n", " ")
    else:
        accion = escena.texto[:200].replace("\n", " ")
    
    # Usar template configurado o fallback
    instrucciones = get_instrucciones_imagenes()
    template = instrucciones.get("prompt_template", "{plano}, {accion}, {estilo}, 16:9.")
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
    
    # Formatear el template (solo contenido variable; el estilo es regla general)
    try:
        contenido_variable = template.format(**variables)
    except KeyError:
        contenido_variable = f"{plano}, {accion}, luz suave, fondo simple, alta calidad"
    # Regla general: estilo aplicado UNA vez desde config, no repetido en cada prompt
    regla_general = estilo.strip()
    base = regla_general + "\n\n" + contenido_variable.strip()
    # Prohibición de UI (también regla general)
    prohibido = get_prohibido_en_imagen()
    if prohibido and prohibido.strip() and prohibido.strip() not in base:
        base = base.rstrip() + "\n\n" + prohibido.strip()
    return base


def prompts_para_escenas(
    escenas: list[Escena],
    shuffle_planos: bool = False,
    tema: str | None = None,
    usar_descripciones_ia: bool = True,
) -> list[tuple[Escena, str]]:
    """
    Genera un prompt por escena con variedad de planos.
    Si usar_descripciones_ia=True (por defecto), genera antes una descripción visual por escena
    con IA para que cada imagen refleje esa escena concreta del guion (máxima coherencia).
    """
    descripciones: list[str] = []
    if usar_descripciones_ia and escenas:
        from .scene_descriptions import generar_descripciones_visuales_escenas
        descripciones = generar_descripciones_visuales_escenas(escenas, tema=tema, verificar_y_corregir=False)
        if descripciones:
            print(f"   Descripciones visuales generadas para {len(descripciones)} escenas.")

    vb = get_visual_bible()
    planos = vb.get("camara", {}).get("variedad_planos") or []
    n_planos = len(planos) or 4
    orden = list(range(n_planos)) * (len(escenas) // n_planos + 1)
    if shuffle_planos:
        random.shuffle(orden)
    return [
        (
            e,
            construir_prompt(
                e,
                orden[i],
                descripcion_visual=descripciones[i] if i < len(descripciones) else None,
            ),
        )
        for i, e in enumerate(escenas)
    ]
