"""FASE 5: Conversión de escenas a prompts visuales (acción + estilo + cámara)."""
import re
import random
from .config_loader import get_visual_bible, get_instrucciones_imagenes, get_prohibido_en_imagen, get_preferencias_aprendidas
from .scene_splitter import Escena


def construir_prompt(
    escena: Escena,
    indice_plan: int | None = None,
    descripcion_visual: str | None = None,
) -> str:
    """
    Prompt final de generación: variables plano, accion, emocion, momento.
    Style lock y character lock están en el template; se añaden prohibiciones y preferencias aprendidas.
    """
    vb = get_visual_bible()
    planos = vb.get("camara", {}).get("variedad_planos") or [
        "plano general", "plano medio", "primer plano", "plano detalle"
    ]
    idx = (indice_plan if indice_plan is not None else escena.numero - 1) % len(planos)
    plano = planos[idx]
    # Acción: descripción visual por escena (IA) o fallback al texto de la escena
    if descripcion_visual and descripcion_visual.strip():
        accion = descripcion_visual.strip().replace("\n", " ")
        for palabra in ("stickman", "2D", "ilustración", "ilustracion", "cinematográfico", "estilo limpio", "líneas negras", "mismo personaje consistente"):
            if palabra.lower() in accion.lower():
                accion = re.sub(rf"[^.]*{re.escape(palabra)}[^.]*\.?", "", accion, flags=re.IGNORECASE)
        accion = " ".join(accion.split()).strip()[:400] or escena.texto[:200].replace("\n", " ")
    else:
        accion = escena.texto[:200].replace("\n", " ")
    emociones_posibles = ["tensión", "determinación", "conflicto", "duda", "decisión", "intensidad", "calma", "sorpresa"]
    momentos_posibles = ["inicio de la historia", "desarrollo", "momento clave", "punto de inflexión", "clímax", "resolución"]
    # Ritmo: cada 3-5 imágenes algo visual (acción, reacción, detalle, cambio de plano)
    ritmo_beats = vb.get("ritmo_beats") or ["acción", "reacción", "detalle", "cambio de plano"]
    ciclo = max(1, vb.get("ciclo_beats_imagenes", 4))
    beat_idx = ((escena.numero - 1) // ciclo) % len(ritmo_beats)
    beat_visual = ritmo_beats[beat_idx]
    emocion_idx = (escena.numero - 1) % len(emociones_posibles)
    momento_idx = (escena.numero - 1) % len(momentos_posibles)
    instrucciones = get_instrucciones_imagenes()
    template = instrucciones.get("prompt_template", "{plano}, {accion}, {emocion}, {momento}. 16:9.")
    variables = {
        "plano": plano,
        "accion": accion,
        "emocion": emociones_posibles[emocion_idx],
        "momento": momentos_posibles[momento_idx],
        "beat_visual": beat_visual,
    }
    # Variables opcionales por si el template usa otros nombres
    variables_en_template = set(re.findall(r'\{(\w+)\}', template))
    if "estilo" in variables_en_template and "estilo" not in variables:
        variables["estilo"] = vb.get("estilo_base", "stickman 2D cinematográfico")
    if "fase_psicologica" in variables_en_template and "fase_psicologica" not in variables:
        variables["fase_psicologica"] = ["inicio", "desarrollo", "clímax", "resolución"][(escena.numero - 1) % 4]
    if "momento_de_la_historia" in variables_en_template and "momento_de_la_historia" not in variables:
        variables["momento_de_la_historia"] = variables["momento"]
    try:
        base = template.format(**variables).strip()
    except KeyError:
        base = f"{plano}, {accion}, {variables.get('emocion', 'tensión')}, {variables.get('momento', 'momento clave')}. Ritmo: {beat_visual}. 16:9."
    # Regla cinematográfica: cada imagen debe cambiar algo (posición/distancia/ángulo/composición/iluminación)
    regla_variacion = (vb.get("regla_variacion") or "").strip()
    if regla_variacion and regla_variacion not in base:
        base = base.rstrip() + "\n\n" + regla_variacion
    # Character lock (se agrega siempre): definición del personaje y prohibidos
    character_lock = (vb.get("character_lock") or "").strip()
    if character_lock and character_lock not in base:
        base = base.rstrip() + "\n\n" + character_lock
    # PROHIBIDO estilo (anime, pixar, etc.) + UI
    prohibido_estilo = vb.get("prohibido_estilo", "").strip()
    if prohibido_estilo and prohibido_estilo not in base:
        base = base.rstrip() + "\n\nPROHIBIDO: " + prohibido_estilo
    prohibido = get_prohibido_en_imagen()
    if prohibido and prohibido.strip() and prohibido.strip() not in base:
        base = base.rstrip() + "\n\n" + prohibido.strip()
    preferencias = get_preferencias_aprendidas()
    if preferencias:
        base = base.rstrip() + "\n\n" + preferencias
    return base


def _indices_planos_sin_repetir_consecutivo(
    n_escenas: int,
    planos: list[str],
    shuffle: bool = False,
) -> list[int]:
    """
    Asigna índice de plano a cada escena respetando la regla de oro:
    plano_actual != plano_anterior (evita video repetitivo).
    """
    if not planos or n_escenas == 0:
        return [0] * n_escenas
    n = len(planos)
    orden: list[int] = []
    for i in range(n_escenas):
        if i == 0:
            orden.append(random.randint(0, n - 1) if shuffle else 0)
        else:
            prev_idx = orden[i - 1]
            prev_plano = planos[prev_idx]
            # Elegir cualquier plano distinto al anterior
            otros = [j for j in range(n) if planos[j] != prev_plano]
            if not otros:
                otros = list(range(n))
            orden.append(random.choice(otros) if shuffle else otros[(i - 1) % len(otros)])
    return orden


def prompts_para_escenas(
    escenas: list[Escena],
    shuffle_planos: bool = False,
    tema: str | None = None,
    usar_descripciones_ia: bool = True,
) -> list[tuple[Escena, str]]:
    """
    Genera un prompt por escena. El plano de cámara es distinto al de la imagen anterior (regla de oro).
    Si usar_descripciones_ia=True, genera antes descripción visual por escena con IA.
    """
    descripciones: list[str] = []
    if usar_descripciones_ia and escenas:
        from .scene_descriptions import generar_descripciones_visuales_escenas
        descripciones = generar_descripciones_visuales_escenas(escenas, tema=tema, verificar_y_corregir=False)
        if descripciones:
            print(f"   Descripciones visuales generadas para {len(descripciones)} escenas.")

    vb = get_visual_bible()
    planos = vb.get("camara", {}).get("variedad_planos") or [
        "plano general", "plano medio", "primer plano", "plano detalle"
    ]
    # Regla de oro: si plano_actual == plano_anterior -> cambiar_plano()
    orden = _indices_planos_sin_repetir_consecutivo(len(escenas), planos, shuffle=shuffle_planos)
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
