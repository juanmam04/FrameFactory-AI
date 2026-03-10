"""FASE 3: Generador de guiones automático con API de modelo de lenguaje."""
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from .config_loader import get_plantillas_guion, get_narrative_rules, BASE

load_dotenv(BASE / ".env")


def count_words(text: str) -> int:
    """
    Cuenta palabras de forma robusta.
    - Trim
    - Split por espacios múltiples / saltos de línea
    - Ignora strings vacías
    """
    if not text or not text.strip():
        return 0
    # Normalizar espacios y saltos de línea
    text = re.sub(r'\s+', ' ', text.strip())
    # Split por espacios y filtrar vacíos
    words = [w for w in text.split() if w.strip()]
    return len(words)


def generar_guion(
    tema: str,
    target_words: int,
    min_words: int | None = None,
    max_words: int | None = None,
    plantilla: str = "explicativo",
    segundos_por_imagen: float = 5.0,
) -> tuple[str, int, float]:
    """
    Genera un guion con un número objetivo de palabras usando generación en 2 pasos.
    
    Args:
        tema: Tema o idea del video
        target_words: Número objetivo de palabras (requerido)
        min_words: Mínimo de palabras (opcional, por defecto 80% de target_words)
        max_words: Máximo de palabras (opcional, por defecto 120% de target_words)
        plantilla: Plantilla de guion a usar
        segundos_por_imagen: Segundos por imagen/escena
    
    Returns:
        tuple[str, int, float]: (guion_texto, word_count, estimated_minutes)
    """
    # Validar target_words
    if target_words < 80:
        target_words = 80
    if target_words > 5000:
        target_words = 5000
    
    # Calcular min/max si no se proporcionan
    if min_words is None:
        min_words = int(target_words * 0.8)
    if max_words is None:
        max_words = int(target_words * 1.2)
    
    # Asegurar que min <= target <= max
    if min_words > target_words:
        min_words = target_words
    if max_words < target_words:
        max_words = target_words
    
    plantillas = get_plantillas_guion()
    templates = plantillas.get("plantillas", {})
    t = templates.get(plantilla, templates.get("explicativo", {}))
    
    rules = get_narrative_rules()
    system_base = t.get("sistema", "Eres un guionista para videos. Narración continua, concreta, sin poesía ni moralejas explícitas.")
    system_extra = (rules.get("system_extra") or "").strip()
    
    # Agregar instrucciones de estilo al system prompt
    style_instructions = """
Narración continua, concreta, sin poesía ni moralejas explícitas.
POV en segunda persona hablándole al espectador.
Tono cinematográfico, oscuro y tenso cuando aplique.
Hechos específicos (no generalidades tipo "ganas campeonatos" sin describir).
Mucha crudeza: muestra decisiones duras, fracasos, traiciones, violencia implícita, consecuencias reales (cárcel, muerte, ruina, soledad), sin edulcorar ni hacer moralejas.
No seas políticamente correcto: los personajes pueden cometer errores graves, ser egoístas, ambiciosos o crueles; tu trabajo es contar la historia como una película intensa y entretenida, no juzgarla.
Evita solo el gore gráfico o descripciones extremadamente detalladas de daño físico; enfócate en la tensión, el impacto emocional y las consecuencias.
"""
    
    system = f"{system_base}\n\n{system_extra}\n\n{style_instructions}" if system_extra else f"{system_base}\n\n{style_instructions}"
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        guion_fallback = _guion_fallback_words(tema, target_words)
        word_count = count_words(guion_fallback)
        estimated_minutes = word_count / 140.0
        return guion_fallback, word_count, estimated_minutes
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # ─── PASO 1: Generar borrador completo ───────────────────────────────────
        print(f"📝 Paso 1: Generando borrador completo (objetivo: ~{target_words} palabras)...")
        
        # Frase clave desde config (mejora mucho el resultado)
        frase_clave = (rules.get("frase_clave") or "No escribas una escena. Escribe la vida completa del personaje.").strip()
        # Para guiones largos (>1000 palabras) ser muy explícito: debe aproximarse al número
        longitud_guidance = ""
        if target_words >= 1000:
            paginas_aprox = max(2, target_words // 600)
            longitud_guidance = f"""
IMPORTANTE - EXTENSIÓN OBLIGATORIA: Este guion debe tener APROXIMADAMENTE {target_words} palabras (unas {paginas_aprox} páginas).
No escribas una historia corta. Desarrollá bien la trama: varias escenas, descripciones concretas, tensión, reacciones.
Si escribís menos de {int(target_words * 0.7)} palabras no cumple. Acercate siempre al objetivo de {target_words} palabras."""
        
        prompt_borrador = f"""Escribe la VIDA COMPLETA del personaje, no una escena ni un resumen. El guion debe sentirse como una PELÍCULA DE CINE: una historia con TRAMA CONCRETA.

TRAMA COMO PELÍCULA (OBLIGATORIO):
- Inventá una historia concreta, no una vida genérica. Que algo PASE: una misión, un objetivo claro, un conflicto que se resuelve (o no).
- Ejemplos: si el tema es "hacker" → una misión concreta (ej. infiltrar un sistema, un ataque a la Casa Blanca, el día que todo salió mal). Si es "futbolista" → la final decisiva, el fichaje que cambió todo, la lesión que lo puso en duda. Si es "cirujano" → la operación de su vida, el paciente que no podía fallar.
- La historia debe tener un ARCO CLARO: inicio (situación), desarrollo (obstáculos, tensión), clímax y desenlace. Como una película: específica, entretenida, con cosas concretas que ocurren.
- Evitá "eres un X y vivís tu vida". Preferí "eres un X y ESTO es lo que pasa: esta misión, este día, esta decisión".

Regla clave: {frase_clave}

APERTURA OBLIGATORIA (NO NEGOCIABLE):
- La PRIMERA oración del guion debe ser exactamente "Este eres tú." (o "Este eres tú,") seguida de la primera escena. Ejemplo: "Este eres tú. Tienes 9 años y el balón es demasiado grande para tus pies."
- PROHIBIDO empezar con: "Hoy vamos a hablar de...", "En este video...", "Te invito a...", "¿Alguna vez te preguntaste...?", "En el día de hoy...", o cualquier intro de youtuber o presentador. El espectador ES el protagonista desde la primera palabra; no hay presentación del tema.
- Si el tema incluye un título o descripción, NO lo repitas como intro; empieza directo con "Este eres tú." y la primera escena de la vida del personaje.

- ESPAÑOL NEUTRO OBLIGATORIO: usa tuteo (tú, tienes, sabes, eres, estás, puedes). NUNCA voseo (vos, tenés, sabés, sos, podés) ni regionalismos. El guion debe ser comprensible en toda Hispanoamérica y España.
- Cuenta todo el recorrido: infancia, dificultades, rechazos, sacrificios, debut, fama, presión, decisiones difíciles, gloria, caídas. Escenas concretas (lugares, horarios, dinero, titulares), crudo y realista. Sin frases motivacionales ni intros promocionales ("este video te llevará…", "no te pierdas…"). No resumir momentos clave; narrarlos en escena.
- Narración en segunda persona (tú), concreta, sin poesía ni moralejas. Objetivo: ~{target_words} palabras. No uses encabezados ni listas; solo texto fluido.
- La historia DEBE tener SIEMPRE un final completo (desenlace, cierre). NUNCA la cortes a la mitad de una frase. Adaptá la cantidad de escenas al largo pedido, pero siempre terminá la historia con una última oración que cierre.

RESTRICCIONES SOBRE EL TEMA (OBLIGATORIO):
- El TEMA define QUIÉN eres, DÓNDE estás y EN QUÉ ÉPOCA vives. NO puedes cambiar eso.
- Si el tema dice que eres X (por ejemplo "el jefe de una mafia en los 80", "un futbolista fracasado", "un cocinero de un cartel"), entonces:
  * SIEMPRE eres ese mismo personaje (no puede aparecer otro protagonista con otra profesión o nombre ajeno al contexto).
  * El entorno principal debe ser coherente con ese mundo (ciudad, época, tipo de trabajo, nivel de peligro, etc.). No inventes pueblos genéricos ni vidas que no tengan nada que ver con el tema.
  * Los nombres, lugares y eventos deben encajar con ese universo concreto.
- PROHIBIDO escribir historias genéricas que ignoren el tema (ej.: "En un pequeño pueblo, un joven llamado Lucas..." cuando el tema habla de un jefe de mafia, un jugador profesional, un narco, etc.).

Tu trabajo es imaginar la vida COMPLETA del personaje que describe el tema, SIEMPRE dentro de ese rol, ese lugar y esa época.

{longitud_guidance}

Tema: {tema}"""
        
        # Calcular max_tokens para el borrador: permitir salida larga (hasta 4096+ para 3000 palabras)
        tokens_por_palabra = 1.4  # español
        max_tokens_borrador = int(target_words * tokens_por_palabra * 1.4)  # margen 40%
        max_tokens_borrador = max(1000, min(max_tokens_borrador, 16000))  # mínimo 1000, máximo 16k para guiones largos
        
        r1 = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt_borrador},
            ],
            max_tokens=max_tokens_borrador,
            temperature=0.7,  # Más creatividad en el borrador
        )
        borrador = (r1.choices[0].message.content or "").strip()
        # Forzar apertura POV: si el modelo puso "Hoy vamos a hablar..." u otra intro, quitarla y empezar con "Este eres tú."
        borrador_lower = borrador.lower()
        intro_prohibida = (
            borrador_lower.startswith("hoy vamos a hablar")
            or borrador_lower.startswith("en este video")
            or borrador_lower.startswith("te invito a")
            or (borrador_lower.startswith("¿alguna vez") and "preguntaste" in borrador_lower[:80])
        )
        empieza_con_este_eres_tu = borrador_lower.startswith("este eres tú") or borrador_lower.startswith("este eres tu")
        if intro_prohibida:
            first_line = borrador.split("\n")[0].strip() if borrador else ""
            rest = borrador[len(first_line):].lstrip() if len(first_line) > 5 else borrador
            borrador = f"Este eres tú. {rest}"
        elif not empieza_con_este_eres_tu and borrador:
            borrador = f"Este eres tú. {borrador}"
        word_count_borrador = count_words(borrador)
        
        print(f"📊 Borrador generado: {word_count_borrador} palabras (objetivo: {target_words})")
        
        # ─── PASO 2: Ajustar solo si es necesario (más flexible) ──────────────────
        print(f"✂️ Paso 2: Verificando ajuste (objetivo: ~{target_words} palabras)...")
        
        # Determinar si necesitamos expandir o reducir
        necesita_expandir = word_count_borrador < min_words
        necesita_reducir = word_count_borrador > max_words
        
        # Solo ajustar si está FUERA del rango aceptable o muy lejos del objetivo
        # No forzar ajustes pequeños que arruinen el guion
        diferencia_objetivo = abs(word_count_borrador - target_words)
        necesita_ajustar = False
        
        if necesita_expandir or necesita_reducir:
            # Fuera del rango, definitivamente ajustar
            necesita_ajustar = True
            print(f"   📊 Borrador fuera de rango ({word_count_borrador} palabras, rango: {min_words}-{max_words})")
        elif diferencia_objetivo > 100:  # Solo ajustar si está a más de 100 palabras del objetivo
            # Muy lejos del objetivo, ajustar suavemente
            necesita_ajustar = True
            print(f"   📊 Borrador lejos del objetivo ({word_count_borrador} vs {target_words}, diferencia: {diferencia_objetivo})")
        else:
            # Está cerca del objetivo, no ajustar para no arruinar el guion
            necesita_ajustar = False
            print(f"   ✅ Borrador está cerca del objetivo ({word_count_borrador} palabras, diferencia: {diferencia_objetivo}), no se ajustará")
        
        if necesita_ajustar:
            # Siempre apuntar al objetivo; si hay que expandir mucho, ser muy explícito
            objetivo_ajuste = target_words
            texto_para_ajustar = borrador
            word_count_actual = word_count_borrador

            # Si el borrador está muy corto, pedir expansión explícita primero
            if necesita_expandir and (target_words - word_count_borrador) > 500:
                print(f"   📈 Borrador corto ({word_count_borrador} palabras). Expandiendo hacia {target_words}...")
                prompt_expandir_primero = f"""La siguiente historia tiene actualmente unas {word_count_borrador} palabras. DEBE quedar con al menos {min_words} palabras y el objetivo es {target_words} palabras.

REQUISITO: Añade contenido hasta acercarte a {target_words} palabras. Mantén la misma trama y el mismo final.
- Expande escenas con más descripciones, reacciones del personaje, detalles del entorno y tensión.
- No inventes subtramas largas ni cambies el desenlace.
- El resultado debe ser la misma historia pero más desarrollada, con aproximadamente {target_words} palabras.
Devuelve solo el texto completo de la historia, sin explicaciones.

HISTORIA ACTUAL:
{borrador}"""
                max_tokens_exp = int(target_words * 1.4 * 1.4)
                max_tokens_exp = max(1000, min(max_tokens_exp, 16000))
                try:
                    r_exp = client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=[
                            {"role": "system", "content": "Eres un editor de guiones. Expandes historias hasta alcanzar el número de palabras pedido, manteniendo coherencia y final."},
                            {"role": "user", "content": prompt_expandir_primero},
                        ],
                        max_tokens=max_tokens_exp,
                        temperature=0.4,
                    )
                    texto_exp = (r_exp.choices[0].message.content or "").strip()
                    if count_words(texto_exp) > word_count_borrador:
                        texto_para_ajustar = texto_exp
                        word_count_actual = count_words(texto_para_ajustar)
                        print(f"   📊 Tras expandir: {word_count_actual} palabras")
                except Exception:
                    pass

            prompt_ajuste = f"""Reescribe la historia siguiente para que tenga aproximadamente {objetivo_ajuste} palabras (entre {min_words} y {max_words}).
Actualmente tiene unas {word_count_actual} palabras. Objetivo: {target_words} palabras.
Debe mantener coherencia total, historia completa y final claro.
Si necesitas acortar, elimina detalles y escenas secundarias, pero CONSERVA SIEMPRE EL DESENLACE: la historia DEBE terminar con un final completo (cierre de la trama). NUNCA cortes a la mitad de una frase ni dejes la historia incompleta.
Si necesitas expandir, agrega detalles concretos y tensión sin inventar subtramas largas. APROXIMATE al número objetivo.
OBLIGATORIO: La última oración debe ser un cierre (punto final). Devuelve solo el texto final.

HISTORIA:
{texto_para_ajustar}"""
            
            max_tokens_ajuste = int(target_words * 1.3 * 1.4)
            max_tokens_ajuste = max(1000, min(max_tokens_ajuste, 16000))
            
            r2 = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "Eres un editor de guiones experto. Ajustas historias al número de palabras indicado. Si acortas, quitas escenas o detalles pero SIEMPRE conservas el desenlace: la historia debe terminar con un final completo, nunca cortada a la mitad de una frase."},
                    {"role": "user", "content": prompt_ajuste},
                ],
                max_tokens=max_tokens_ajuste,
                temperature=0.3,
            )
            guion_ajustado = (r2.choices[0].message.content or "").strip()
            word_count_ajustado = count_words(guion_ajustado)
            
            print(f"📊 Guion ajustado: {word_count_ajustado} palabras (objetivo: {target_words})")
            
            # Si sigue corto, hasta 2 intentos más de expansión
            for intento_extra in range(2):
                if word_count_ajustado >= min_words:
                    break
                faltan = target_words - word_count_ajustado
                print(f"   📈 Sigue corto ({word_count_ajustado} palabras). Intentando expandir de nuevo (+{faltan} palabras)...")
                prompt_extra = f"""El siguiente guion tiene {word_count_ajustado} palabras. DEBE tener al menos {min_words} palabras (objetivo {target_words}).
Añade aproximadamente {faltan} palabras: más descripciones de escenas, reacciones, detalles, tensión. NO cambies el final ni la trama.
Devuelve solo el texto completo ampliado, sin explicaciones.

GUION ACTUAL:
{guion_ajustado}"""
                try:
                    r_extra = client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=[
                            {"role": "system", "content": "Expandes guiones hasta alcanzar el número de palabras pedido. Mantienes la misma historia y el mismo final."},
                            {"role": "user", "content": prompt_extra},
                        ],
                        max_tokens=int(target_words * 1.4 * 1.4),
                        temperature=0.35,
                    )
                    guion_ajustado = (r_extra.choices[0].message.content or "").strip()
                    word_count_ajustado = count_words(guion_ajustado)
                    print(f"   📊 Tras intento {intento_extra + 1}: {word_count_ajustado} palabras")
                except Exception:
                    break
            
            # Validar resultado
            if word_count_ajustado > max_words:
                # Reintentar con instrucción más estricta (máximo 2 intentos)
                print(f"⚠️ Guion excede {max_words} palabras. Reintentando con instrucción más estricta...")
                prompt_ajuste_estricto = f"""Reescribe la historia siguiente para que tenga EXACTAMENTE {target_words} palabras (MÁXIMO {max_words}, NO MÁS).
Debe mantener coherencia total, historia completa y final claro.
Si necesitas acortar, elimina detalles y escenas secundarias, pero CONSERVA SIEMPRE EL DESENLACE. La historia DEBE terminar con un final completo; NUNCA la cortes a la mitad de una oración.
Devuelve solo el texto final. La última frase debe ser un cierre con punto final.

HISTORIA ORIGINAL:
{borrador}"""
                
                r3 = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": "Eres un editor de guiones experto. Ajustas historias al número de palabras indicado. SIEMPRE entregas una historia con final completo; nunca cortes a la mitad de una frase."},
                        {"role": "user", "content": prompt_ajuste_estricto},
                    ],
                    max_tokens=max(1200, int(target_words * 1.6 * 1.4)),  # margen suficiente para no truncar el final
                    temperature=0.2,
                )
                guion_final = (r3.choices[0].message.content or "").strip()
                word_count_final = count_words(guion_final)
                
                if word_count_final <= max_words:
                    guion_ajustado = guion_final
                    word_count_ajustado = word_count_final
                    print(f"✅ Guion ajustado correctamente: {word_count_ajustado} palabras")
                else:
                    print(f"⚠️ Guion aún excede {max_words} palabras ({word_count_ajustado}). Usando versión anterior.")
            
            # Validar que no quede muy corto: última pasada de expansión sobre el guion ya ajustado
            if word_count_ajustado < min_words:
                faltan = target_words - word_count_ajustado
                print(f"⚠️ Guion sigue corto ({word_count_ajustado} palabras). Última expansión hacia {target_words} (+{faltan} palabras)...")
                prompt_expandir = f"""El guion siguiente tiene {word_count_ajustado} palabras. DEBE quedar con al menos {min_words} palabras; objetivo final: {target_words} palabras.
Faltan aproximadamente {faltan} palabras. Añade: más descripciones de escenas, reacciones del personaje, detalles del entorno, tensión. Mantén la misma trama y el mismo final.
Devuelve solo el texto completo ampliado.

GUION ACTUAL:
{guion_ajustado}"""
                
                try:
                    r4 = client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=[
                            {"role": "system", "content": "Eres un editor de guiones. Expandes el texto hasta alcanzar el número de palabras pedido. Siempre mantienes la misma historia y el mismo final."},
                            {"role": "user", "content": prompt_expandir},
                        ],
                        max_tokens=int(target_words * 1.5 * 1.4),
                        temperature=0.4,
                    )
                    guion_expandido = (r4.choices[0].message.content or "").strip()
                    word_count_expandido = count_words(guion_expandido)
                    if word_count_expandido > word_count_ajustado:
                        guion_ajustado = guion_expandido
                        word_count_ajustado = word_count_expandido
                        print(f"✅ Guion expandido: {word_count_ajustado} palabras")
                except Exception as e:
                    print(f"⚠️ Error en expansión final: {e}")
            
            guion_final = guion_ajustado
            word_count_final = word_count_ajustado
        else:
            guion_final = borrador
            word_count_final = word_count_borrador
        
        # Calcular minutos estimados (base, sin velocidad)
        words_per_minute = 140
        estimated_minutes = word_count_final / words_per_minute
        
        # Verificar que el guion no esté cortado
        if len(guion_final.strip()) < 100:
            print(f"⚠️ ADVERTENCIA: Guion parece muy corto ({len(guion_final)} caracteres)")
        
        # Si termina sin puntuación (cortado a la mitad), recortar hasta la última oración completa
        guion_stripped = guion_final.strip()
        if guion_stripped and guion_stripped[-1] not in ".!?":
            print(f"⚠️ Guion cortado a la mitad. Recortando hasta la última oración completa...")
            last_punto = max(guion_stripped.rfind(". "), guion_stripped.rfind("."))
            last_excl = guion_stripped.rfind("!")
            last_inter = guion_stripped.rfind("?")
            ultimo_fin = max(last_punto, last_excl, last_inter)
            if ultimo_fin > 50:
                guion_final = guion_stripped[: ultimo_fin + 1]
                word_count_final = count_words(guion_final)
                print(f"   ✅ Guion recortado a oración completa: {word_count_final} palabras")
            else:
                print(f"⚠️ ADVERTENCIA: Guion puede estar cortado (no termina con puntuación)")
        
        print(f"✅ Guion final: {word_count_final} palabras, ≈ {estimated_minutes:.1f} minutos (base, sin velocidad)")
        print(f"   Longitud del texto: {len(guion_final)} caracteres")
        
        return guion_final, word_count_final, estimated_minutes
        
    except Exception as e:
        print(f"⚠️ Error al generar guion: {e}")
        guion_fallback = _guion_fallback_words(tema, target_words)
        word_count = count_words(guion_fallback)
        estimated_minutes = word_count / 140.0
        return guion_fallback, word_count, estimated_minutes


def _guion_fallback_words(tema: str, target_words: int) -> str:
    """Guion de ejemplo cuando no hay API configurada."""
    palabras_por_parrafo = 50
    num_parrafos = max(1, target_words // palabras_por_parrafo)
    
    lineas = [
        f"En este video hablaremos sobre: {tema}.",
        "La idea central es muy importante para entender el tema.",
        "Veamos los puntos clave uno por uno.",
    ]
    while len(lineas) < num_parrafos:
        lineas.append(f"Aquí desarrollamos otro aspecto de {tema}.")
    return "\n\n".join(lineas[:num_parrafos])


def guardar_guion(contenido: str, nombre: str = "guion") -> Path:
    out = BASE / "output" / "guiones"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{nombre}.txt"
    path.write_text(contenido, encoding="utf-8")
    return path
