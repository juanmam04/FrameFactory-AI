"""FASE 5: Conversión de escenas / beats a prompts visuales (acción + estilo + cámara)."""
import re
import random
from .config_loader import get_visual_bible, get_instrucciones_imagenes, get_prohibido_en_imagen
from .scene_splitter import Escena
from .visual_beats import VisualBeat

# Cuando el plano es POV, esta instrucción se añade para forzar primera persona (lo que ve el personaje, sin mostrarlo).
_INSTRUCCION_POV = (
    "Vista en PRIMERA PERSONA (POV): la imagen debe mostrar exactamente lo que VE el personaje, "
    "como si la cámara fueran sus ojos. NO mostrar al personaje en cuadro; solo el escenario desde su mirada. "
    "First person view, no third person. No character body visible."
)

# Palabras que indican que una preferencia habla del diseño del personaje; esas se filtran para no pisar character_lock.
_PALABRAS_PERSONAJE_PREF = (
    "stickman", "personaje", "cuerpo", "cabeza", "figura tipo", "humano", "humanoide", "torso",
    "brazos", "piernas", "líneas simples", "muñeco", "palitos", "ropa", "pelo", "manos", "pies",
    "ovalados", "contorno", "cartoon", "caricatura", "no debe tener", "debe ser un",
)

# Mapeo emoción del beat → clave de referencia en character_reference (para Kontext)
_EMOTION_TO_EXPRESSION_KEY: dict[str, str] = {
    "alegría": "happy",
    "alegria": "happy",
    "happy": "happy",
    "joy": "happy",
    "felicidad": "happy",
    "determinación": "determined",
    "determinacion": "determined",
    "determined": "determined",
    "sorpresa": "surprised",
    "surprised": "surprised",
    "sorprendido": "surprised",
    "miedo": "scared",
    "scared": "scared",
    "fear": "scared",
    "asustado": "scared",
    "enojo": "angry",
    "angry": "angry",
    "ira": "angry",
    "rabia": "angry",
    "shock": "shocked",
    "shocked": "shocked",
    "neutral": "neutral",
    "calma": "neutral",
    "calm": "neutral",
    "tensión": "neutral",
    "tension": "neutral",
    "intensidad": "neutral",
    "conflicto": "neutral",
    "duda": "neutral",
    "decisión": "determined",
    "decision": "determined",
    "resolución": "neutral",
    "resolucion": "neutral",
}


def emotion_to_expression_key(emotion: str | None) -> str | None:
    """Devuelve la clave de referencia de expresión para Kontext (happy, determined, surprised, etc.) o None (usar front)."""
    if not (emotion or "").strip():
        return None
    e = emotion.strip().lower()
    return _EMOTION_TO_EXPRESSION_KEY.get(e)


def _es_plano_pov(plano: str) -> bool:
    """True si el plano pedido es POV (punto de vista del personaje)."""
    if not (plano or "").strip():
        return False
    p = plano.strip().upper()
    return "POV" in p or "PUNTO DE VISTA" in p or "PRIMERA PERSONA" in p


def _filtrar_preferencias_solo_fondo_estilo(texto: str) -> str:
    """Quita de las preferencias aprendidas las que describen al personaje, para no contradecir character_lock."""
    if not (texto or "").strip():
        return ""
    # Quitar el prefijo "Preferencias del usuario (aplicar): " si existe
    t = re.sub(r"^Preferencias del usuario \(aplicar\):\s*", "", texto, flags=re.IGNORECASE).strip()
    if not t:
        return ""
    # Dividir por ; o . y quedarnos solo con fragmentos que NO hablan del personaje
    fragmentos = re.split(r"[.;]\s*", t)
    buenos = []
    for frag in fragmentos:
        frag = frag.strip()
        if not frag or len(frag) < 10:
            continue
        lower = frag.lower()
        if any(pal in lower for pal in _PALABRAS_PERSONAJE_PREF):
            continue
        buenos.append(frag)
    if not buenos:
        return ""
    return "; ".join(buenos)


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
    if "lugar" in variables_en_template and "lugar" not in variables:
        variables["lugar"] = "entorno detallado que muestre claramente dónde ocurre la acción"
    try:
        base = template.format(**variables).strip()
    except KeyError:
        base = f"{plano}, {accion}, {variables.get('emocion', 'tensión')}, {variables.get('momento', 'momento clave')}. Lugar claro. Ritmo: {beat_visual}. 16:9."
    base = "OBLIGATORIO: Mismo personaje siempre. POV = primera persona sin personaje en cuadro. Cada imagen = momento distinto. No repetir.\n\n" + base
    # POV: instrucción explícita de primera persona (lo que ve el personaje, sin mostrarlo en cuadro)
    if _es_plano_pov(plano):
        base = base.rstrip() + "\n\n" + _INSTRUCCION_POV
    # Regla cinematográfica: cada imagen debe cambiar algo (posición/distancia/ángulo/composición/iluminación)
    regla_variacion = (vb.get("regla_variacion") or "").strip()
    if regla_variacion and regla_variacion not in base:
        base = base.rstrip() + "\n\n" + regla_variacion
    regla_variedad = (vb.get("regla_variedad_composicion") or "").strip()
    if regla_variedad and regla_variedad not in base:
        base = base.rstrip() + "\n\n" + regla_variedad
    continuidad = (vb.get("continuidad_y_errores") or "").strip()
    if continuidad and continuidad not in base:
        base = base.rstrip() + "\n\n" + continuidad
    # Character lock (ÚNICA fuente de verdad del personaje; tiene prioridad sobre preferencias)
    character_lock = (vb.get("character_lock") or "").strip()
    if character_lock and character_lock not in base:
        base = base.rstrip() + "\n\nOBLIGATORIO (prioridad sobre todo lo demás): " + character_lock
    # PROHIBIDO estilo (anime, pixar, etc.) + UI
    prohibido_estilo = vb.get("prohibido_estilo", "").strip()
    if prohibido_estilo and prohibido_estilo not in base:
        base = base.rstrip() + "\n\nPROHIBIDO: " + prohibido_estilo
    prohibido = get_prohibido_en_imagen()
    if prohibido and prohibido.strip() and prohibido.strip() not in base:
        base = base.rstrip() + "\n\n" + prohibido.strip()
    # No inyectar preferencias aprendidas de feedbacks pasados (generaban errores y contradicciones)
    base = base.rstrip() + "\n\nOBLIGATORIO: Máximo sentido común e inteligencia lógica—imagen coherente y creíble, sin absurdos. Misma identidad de personaje; edad y ropa según contexto. Incluir lugar claro y qué está pasando. Anatomía correcta; objetos lógicos. No repetir."
    return base


def construir_prompt_desde_beat(
    beat: VisualBeat,
    indice_plan: int | None = None,
    indice_imagen: int | None = None,
) -> str:
    """
    Versión para beats visuales:
    - Usa camera_type del beat como plano base.
    - Acción/emoción/contexto salen del propio beat.
    - indice_imagen se usa para que cada prompt sea único (evitar mismo texto cada N fotos).
    """
    vb = get_visual_bible()
    planos = vb.get("camara", {}).get("variedad_planos") or [
        "plano general", "plano medio", "primer plano", "plano detalle"
    ]
    # Mapear camera_type (POV, wide_shot, etc.) a descripción legible
    camera_map = {
        "POV": "POV (punto de vista del personaje)",
        "over_the_shoulder": "plano sobre el hombro",
        "wide_shot": "plano amplio cinematográfico",
        "medium_shot": "plano medio",
        "close_up": "primer plano / close-up",
        "side_angle": "ángulo lateral",
        "top_down": "vista desde arriba (top down)",
        "low_angle": "ángulo bajo (low angle)",
        "rear_view": "vista desde atrás",
        "environment_shot": "plano de entorno (environment shot)",
    }
    plano_from_camera = camera_map.get(beat.camera_type, "plano medio")
    if indice_plan is not None and 0 <= indice_plan < len(planos):
        plano = planos[indice_plan]
    else:
        plano = plano_from_camera

    accion = (beat.action or beat.original_text or "").replace("\n", " ").strip()[:400]
    if not accion:
        accion = "momento clave de la escena"
    emocion = (beat.emotion or "tensión").strip()
    momento = (beat.context or "momento clave de la historia").strip()
    shot_role = (beat.shot_role or "action").strip()
    time_of_day = (beat.time_of_day or "").strip() or "momento indefinido del día"

    instrucciones = get_instrucciones_imagenes()
    template = instrucciones.get("prompt_template", "{plano}, {accion}, {emocion}, {momento}. 16:9.")
    lugar = (beat.location or "entorno que muestre claramente dónde ocurre la escena").strip()
    variables = {
        "plano": plano,
        "accion": accion,
        "emocion": emocion,
        "momento": momento,
        "beat_visual": beat.importance or "acción",
        "shot_role": shot_role,
        "time_of_day": time_of_day,
        "lugar": lugar,
    }
    variables_en_template = set(re.findall(r'\{(\w+)\}', template))
    if "estilo" in variables_en_template and "estilo" not in variables:
        variables["estilo"] = vb.get("estilo_base", "stickman 2D cinematográfico")
    if "lugar" in variables_en_template and "lugar" not in variables:
        variables["lugar"] = lugar

    try:
        base = template.format(**variables).strip()
    except KeyError:
        base = f"{plano}, {accion}, {emocion}, {momento}. Lugar: {lugar}. 16:9."
    base = "OBLIGATORIO: Mismo personaje siempre. POV = primera persona sin personaje en cuadro. Cada imagen = momento distinto. No repetir.\n\n" + base
    # POV: instrucción explícita de primera persona
    if _es_plano_pov(plano):
        base = base.rstrip() + "\n\n" + _INSTRUCCION_POV
    # Regla cinematográfica: cada imagen debe cambiar algo
    regla_variacion = (vb.get("regla_variacion") or "").strip()
    if regla_variacion and regla_variacion not in base:
        base = base.rstrip() + "\n\n" + regla_variacion
    regla_variedad = (vb.get("regla_variedad_composicion") or "").strip()
    if regla_variedad and regla_variedad not in base:
        base = base.rstrip() + "\n\n" + regla_variedad
    continuidad = (vb.get("continuidad_y_errores") or "").strip()
    if continuidad and continuidad not in base:
        base = base.rstrip() + "\n\n" + continuidad
    # Character lock (ÚNICA fuente de verdad del personaje)
    character_lock = (vb.get("character_lock") or "").strip()
    if character_lock and character_lock not in base:
        base = base.rstrip() + "\n\nOBLIGATORIO (prioridad sobre todo lo demás): " + character_lock
    # PROHIBIDO estilo + UI
    prohibido_estilo = vb.get("prohibido_estilo", "").strip()
    if prohibido_estilo and prohibido_estilo not in base:
        base = base.rstrip() + "\n\nPROHIBIDO: " + prohibido_estilo
    prohibido = get_prohibido_en_imagen()
    if prohibido and prohibido.strip() and prohibido.strip() not in base:
        base = base.rstrip() + "\n\n" + prohibido.strip()
    # No inyectar preferencias aprendidas de feedbacks pasados (generaban errores y contradicciones)
    # Unicidad
    frame_id = indice_imagen if indice_imagen is not None else (beat.beat_id if beat else 0)
    base = base.rstrip() + f"\n\nFrame {frame_id} de la secuencia. Esta imagen debe ser visualmente distinta."
    # Repetir instrucción crítica al final (los modelos de imagen atienden más al inicio y al final)
    base = base.rstrip() + "\n\nOBLIGATORIO: Máximo sentido común e inteligencia—imagen 100% coherente y creíble. Misma identidad de personaje; edad y ropa según contexto (bebé/niño/adulto, traje/fútbol/casual). Lugar claro y acción visible. Anatomía correcta; objetos y cantidades lógicas. No repetir escena."
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


def prompts_para_beats(
    beats: list[VisualBeat],
    shuffle_planos: bool = True,
) -> list[tuple[VisualBeat, str]]:
    """
    Genera prompts a partir de beats visuales.
    Respeta el sistema de cámara y rota los planos para no repetir la posición.
    Cada prompt incluye un frame id para que nunca se repita el mismo texto (evitar mismo prompt cada 3 fotos).
    """
    if not beats:
        return []
    vb = get_visual_bible()
    planos = vb.get("camara", {}).get("variedad_planos") or [
        "plano general", "plano medio", "primer plano", "plano detalle"
    ]
    orden = _indices_planos_sin_repetir_consecutivo(len(beats), planos, shuffle=shuffle_planos)
    resultados: list[tuple[VisualBeat, str]] = []
    for i, beat in enumerate(beats):
        prompt = construir_prompt_desde_beat(beat, indice_plan=orden[i], indice_imagen=i + 1)
        # Si por algún motivo el prompt salió igual al anterior, forzar variación
        if resultados and resultados[-1][1] == prompt:
            prompt = prompt.rstrip() + " Variación alternativa: ángulo o encuadre distinto."
        resultados.append((beat, prompt))
    return resultados

