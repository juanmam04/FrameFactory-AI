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
    if target_words > 3000:
        target_words = 3000
    
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
        # Para guiones largos (>1500 palabras) ser muy explícito: debe aproximarse al número
        longitud_guidance = ""
        if target_words >= 1500:
            paginas_aprox = max(2, target_words // 600)
            longitud_guidance = f"""
IMPORTANTE - EXTENSIÓN OBLIGATORIA: Este guion debe tener APROXIMADAMENTE {target_words} palabras (unas {paginas_aprox} páginas).
No escribas una historia corta. Desarrollá bien la trama: varias escenas, descripciones concretas, tensión, reacciones.
Si escribís menos de {int(target_words * 0.7)} palabras no cumple. Acercate siempre al objetivo de {target_words} palabras."""
        
        prompt_borrador = f"""Escribe la VIDA COMPLETA del personaje, no una escena ni un resumen. El guion debe sentirse como una mini-película POV.
Regla clave: {frase_clave}
- Empieza SIEMPRE con "Este eres tú." (el espectador es el protagonista).
- ESPAÑOL NEUTRO OBLIGATORIO: usa tuteo (tú, tienes, sabes, eres, estás, puedes). NUNCA voseo (vos, tenés, sabés, sos, podés) ni regionalismos. El guion debe ser comprensible en toda Hispanoamérica y España.
- Cuenta todo el recorrido: infancia, dificultades, rechazos, sacrificios, debut, fama, presión, decisiones difíciles, gloria, caídas. Escenas concretas (lugares, horarios, dinero, titulares), crudo y realista. Sin frases motivacionales ni intros promocionales ("este video te llevará…", "no te pierdas…"). No resumir momentos clave; narrarlos en escena.
Narración en segunda persona (tú), concreta, sin poesía ni moralejas. Objetivo: ~{target_words} palabras. No uses encabezados ni listas; solo texto fluido.
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
Si necesitas acortar, elimina detalles y escenas secundarias, pero conserva el desenlace.
Si necesitas expandir, agrega detalles concretos y tensión sin inventar subtramas largas. APROXIMATE al número objetivo.
Devuelve solo el texto final.

HISTORIA:
{texto_para_ajustar}"""
            
            max_tokens_ajuste = int(target_words * 1.3 * 1.4)
            max_tokens_ajuste = max(1000, min(max_tokens_ajuste, 16000))
            
            r2 = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "Eres un editor de guiones experto. Ajustas historias al número de palabras indicado. Si el objetivo es mayor al texto actual, expandís; si es menor, recortás. Siempre te aproximás al objetivo."},
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
Si necesitas acortar, elimina detalles y escenas secundarias, pero conserva el desenlace.
Devuelve solo el texto final.

HISTORIA ORIGINAL:
{borrador}"""
                
                r3 = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": "Eres un editor de guiones experto. Ajustas historias a números exactos de palabras manteniendo coherencia y final completo."},
                        {"role": "user", "content": prompt_ajuste_estricto},
                    ],
                    max_tokens=int(target_words * 1.15 * 1.3),  # 15% de margen para evitar cortes
                    temperature=0.2,  # Temperatura aún más baja
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
        
        # Verificar que termine con punto o signo de puntuación
        if guion_final.strip() and not guion_final.strip()[-1] in ".!?":
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
