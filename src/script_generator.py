"""FASE 3: Generador de guiones automático con API de modelo de lenguaje."""
import os
from pathlib import Path

from dotenv import load_dotenv

from .config_loader import get_plantillas_guion, get_narrative_rules, BASE

load_dotenv(BASE / ".env")


def generar_guion(
    tema: str,
    duracion_min: int | None = None,
    duracion_max: int | None = None,
    plantilla: str = "explicativo",
    segundos_por_imagen: float = 5.0,
) -> str:
    """
    Genera un guion largo a partir de un tema usando la API configurada.
    Recorta automáticamente el guion para respetar la duración exacta.
    """
    from .config_loader import get_duracion_por_imagen
    
    plantillas = get_plantillas_guion()
    templates = plantillas.get("plantillas", {})
    t = templates.get(plantilla, templates.get("explicativo", {}))
    duracion_min = duracion_min or plantillas.get("duracion_default_minutos", 2)
    
    # Si no se especifica duracion_max, usar duracion_min como máximo (duración exacta)
    if duracion_max is None:
        duracion_max = duracion_min
    if duracion_max < duracion_min:
        duracion_max = duracion_min
    
    # Calcular número exacto de escenas necesarias
    seg_por_imagen = segundos_por_imagen or get_duracion_por_imagen()
    escenas_objetivo = int((duracion_max * 60) / seg_por_imagen)
    escenas_objetivo = max(1, escenas_objetivo)  # Mínimo 1 escena
    
    # Calcular palabras objetivo (aproximadamente 150 palabras por minuto de narración)
    palabras_por_minuto = 150
    palabras_objetivo = int(duracion_max * palabras_por_minuto)
    palabras_por_escena = int(palabras_objetivo / escenas_objetivo) if escenas_objetivo > 0 else palabras_objetivo
    
    # Calcular max_tokens ANTES de usarlo en el prompt
    # Aproximadamente 1.3 tokens por palabra en español
    max_tokens_estimado = int(palabras_objetivo * 1.1 * 1.3)  # Solo 10% de margen - muy restrictivo
    max_tokens_estimado = max(100, min(max_tokens_estimado, 4000))  # Entre 100 y 4000 tokens
    
    # Formatear prompt con ambas duraciones y número exacto de escenas
    prompt_template = t.get("usuario", "")
    try:
        # Intentar formatear con duracion_max si está en el template
        prompt_usuario = prompt_template.format(
            tema=tema, 
            duracion_min=duracion_min,
            duracion_max=duracion_max
        )
    except KeyError:
        # Si el template no tiene duracion_max, usar solo duracion_min
        prompt_usuario = prompt_template.format(
            tema=tema, 
            duracion_min=duracion_min
        )
    
    # Agregar instrucciones MUY específicas con cálculos exactos
    minuto_texto = "minuto" if duracion_min == 1 else "minutos"
    if duracion_min == duracion_max:
        prompt_usuario += f"\n\n" + "="*60 + "\n"
        prompt_usuario += f"⚠️ DURACIÓN EXACTA REQUERIDA - LEE CON ATENCIÓN:\n"
        prompt_usuario += "="*60 + "\n"
        prompt_usuario += f"OBJETIVO: El video DEBE durar EXACTAMENTE {duracion_min} {minuto_texto} ({duracion_min * 60} segundos).\n\n"
        prompt_usuario += f"CÁLCULOS EXACTOS:\n"
        prompt_usuario += f"- Número de escenas/párrafos: EXACTAMENTE {escenas_objetivo} párrafos\n"
        prompt_usuario += f"- Duración por párrafo: {seg_por_imagen} segundos cada uno\n"
        prompt_usuario += f"- Palabras objetivo totales: aproximadamente {palabras_objetivo} palabras\n"
        prompt_usuario += f"- Palabras por párrafo: aproximadamente {palabras_por_escena} palabras por párrafo\n\n"
        prompt_usuario += f"REGLAS CRÍTICAS (OBLIGATORIAS - NO IGNORAR):\n"
        prompt_usuario += f"1. ⚠️⚠️⚠️ Escribe EXACTAMENTE {escenas_objetivo} párrafos. NI MÁS, NI MENOS. Esto es CRÍTICO y NO NEGOCIABLE.\n"
        prompt_usuario += f"2. ⚠️⚠️⚠️ Cada párrafo debe tener aproximadamente {palabras_por_escena} palabras (total: ~{palabras_objetivo} palabras).\n"
        prompt_usuario += f"3. ⚠️⚠️⚠️ Debes contar la historia COMPLETA (inicio + desarrollo + final) en esos {escenas_objetivo} párrafos.\n"
        prompt_usuario += f"4. ⚠️⚠️⚠️ Ajusta el DETALLE, NO la CANTIDAD de párrafos:\n"
        prompt_usuario += f"   - Si es 1 minuto: historia completa pero MUY breve (solo eventos esenciales, sin detalles)\n"
        prompt_usuario += f"   - Si es 5 minutos: historia completa con más detalle (desarrolla escenas clave)\n"
        prompt_usuario += f"   - Si es 20 minutos: historia completa con MUCHO detalle (desarrolla cada momento)\n"
        prompt_usuario += f"5. ⚠️⚠️⚠️ NO agregues párrafos extra bajo ninguna circunstancia. Si necesitas más espacio, aumenta palabras por párrafo.\n"
        prompt_usuario += f"6. ⚠️⚠️⚠️ NO cortes la historia. Debe tener inicio, desarrollo y final completo.\n"
        prompt_usuario += f"7. ⚠️⚠️⚠️ La respuesta está limitada a {max_tokens_estimado} tokens. Usa ese límite sabiamente para escribir EXACTAMENTE {escenas_objetivo} párrafos.\n\n"
        prompt_usuario += f"EJEMPLO para {duracion_min} minuto{'s' if duracion_min != 1 else ''}:\n"
        prompt_usuario += f"- Párrafo 1: Inicio (gancho) - ~{palabras_por_escena} palabras\n"
        prompt_usuario += f"- Párrafos 2-{max(2, escenas_objetivo-1)}: Desarrollo - ~{palabras_por_escena} palabras cada uno\n"
        prompt_usuario += f"- Párrafo {escenas_objetivo}: Final - ~{palabras_por_escena} palabras\n"
        prompt_usuario += "="*60 + "\n"
    else:
        prompt_usuario += f"\n\n⚠️ DURACIÓN Y HISTORIA COMPLETA:\n"
        prompt_usuario += f"- El video debe durar entre {duracion_min} y {duracion_max} minutos.\n"
        prompt_usuario += f"- Escribe entre {int((duracion_min * 60) / seg_por_imagen)} y {escenas_objetivo} párrafos (escenas).\n"
        prompt_usuario += f"- Palabras objetivo: aproximadamente {palabras_objetivo} palabras totales.\n"
        prompt_usuario += f"- Debes contar la historia COMPLETA desde el inicio hasta el final.\n"
        prompt_usuario += f"- Ajusta el nivel de detalle según la duración disponible.\n"
        prompt_usuario += f"- NO cortes la historia. La historia debe tener inicio, desarrollo y final completo.\n"
        prompt_usuario += f"- NO excedas los {escenas_objetivo} párrafos."
    
    rules = get_narrative_rules()
    system_base = t.get("sistema", "Eres un guionista para videos. Un párrafo por escena de 5 segundos.")
    system_extra = (rules.get("system_extra") or "").strip()
    
    # Agregar instrucciones críticas al system prompt también
    system_critico = ""
    if duracion_min == duracion_max:
        system_critico = f"\n\n⚠️ REGLA CRÍTICA: Debes escribir EXACTAMENTE {escenas_objetivo} párrafos para una duración de {duracion_min} minutos. "
        system_critico += f"Cada párrafo debe tener aproximadamente {palabras_por_escena} palabras. "
        system_critico += f"NO escribas más párrafos. Ajusta el nivel de detalle, no la cantidad de párrafos. "
        system_critico += f"La historia debe ser COMPLETA (inicio + desarrollo + final) pero ajustada a esta duración exacta."
    
    system = f"{system_base}\n\n{system_extra}{system_critico}" if system_extra or system_critico else system_base

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _guion_fallback(tema, duracion_min, escenas_objetivo)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Usar max_tokens para limitar FÍSICAMENTE la longitud de la respuesta
        # Aproximadamente 1.3 tokens por palabra en español
        # Usar un margen MUY pequeño para forzar la duración exacta
        max_tokens_estimado = int(palabras_objetivo * 1.1 * 1.3)  # Solo 10% de margen - muy restrictivo
        max_tokens_estimado = max(100, min(max_tokens_estimado, 4000))  # Entre 100 y 4000 tokens
        
        print(f"🔒 Limitando respuesta a {max_tokens_estimado} tokens (objetivo: ~{int(palabras_objetivo * 1.3)} tokens)")
        
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt_usuario},
            ],
            max_tokens=max_tokens_estimado,  # Limitar tokens para forzar duración exacta
            temperature=0.3,  # Temperatura muy baja para máxima precisión y menos creatividad
        )
        guion_generado = (r.choices[0].message.content or "").strip()
        
        # Validar y contar escenas generadas (solo para logging, NO recortar)
        escenas_generadas = len([p for p in guion_generado.split("\n\n") if p.strip()])
        palabras_generadas = len(guion_generado.split())
        
        print(f"📊 Guion generado: {escenas_generadas} escenas (objetivo: {escenas_objetivo}), {palabras_generadas} palabras (objetivo: ~{palabras_objetivo})")
        
        # NO recortar - confiar en que la IA generó el tamaño correcto
        # Si excede mucho, solo advertir pero no cortar
        if escenas_generadas > escenas_objetivo * 1.2:
            print(f"⚠️ ADVERTENCIA: Guion tiene {escenas_generadas} escenas, objetivo: {escenas_objetivo}. La IA debería haber generado el tamaño correcto.")
        
        return guion_generado
    except Exception as e:
        print(f"⚠️ Error al generar guion: {e}")
        return _guion_fallback(tema, duracion_min, escenas_objetivo)


def _ajustar_guion_con_ia(
    client, guion_original: str, escenas_objetivo: int, palabras_objetivo: int, 
    palabras_por_escena: int, duracion_min: int
) -> str | None:
    """
    Pide a la IA que ajuste el guion a la duración exacta manteniendo la historia completa.
    """
    try:
        prompt_ajuste = f"""El siguiente guion es demasiado largo. Necesito que lo ajustes a EXACTAMENTE {escenas_objetivo} párrafos manteniendo la historia COMPLETA.

GUION ORIGINAL:
{guion_original}

INSTRUCCIONES:
1. Mantén la historia COMPLETA (inicio + desarrollo + final)
2. Reduce a EXACTAMENTE {escenas_objetivo} párrafos
3. Cada párrafo debe tener aproximadamente {palabras_por_escena} palabras
4. Ajusta el nivel de detalle, no cortes la historia
5. Si es 1 minuto: cuenta breve pero completa
6. Si es más tiempo: puedes mantener más detalle

Escribe SOLO el guion ajustado, sin explicaciones."""
        
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Eres un editor de guiones experto. Ajustas guiones a duraciones exactas manteniendo la historia completa."},
                {"role": "user", "content": prompt_ajuste},
            ],
            max_tokens=int(palabras_objetivo * 1.2 * 1.3),
            temperature=0.3,  # Muy baja temperatura para precisión
        )
        guion_ajustado = (r.choices[0].message.content or "").strip()
        
        # Validar que el ajuste sea mejor
        escenas_ajustadas = len([p for p in guion_ajustado.split("\n\n") if p.strip()])
        if abs(escenas_ajustadas - escenas_objetivo) < abs(len([p for p in guion_original.split("\n\n") if p.strip()]) - escenas_objetivo):
            print(f"✅ Guion ajustado: {escenas_ajustadas} escenas (objetivo: {escenas_objetivo})")
            return guion_ajustado
        
        return None
    except Exception as e:
        print(f"⚠️ Error al ajustar guion con IA: {e}")
        return None
    except Exception:
        return _guion_fallback(tema, duracion_min, escenas_objetivo)


def _recortar_guion_por_duracion(guion: str, duracion_max_minutos: int, segundos_por_imagen: float) -> str:
    """
    Recorta el guion para que no exceda la duración máxima.
    Divide por párrafos y elimina los que excedan.
    """
    from .scene_splitter import dividir_en_escenas
    
    # Dividir en escenas
    escenas = dividir_en_escenas(guion, segundos_por_imagen)
    
    # Calcular duración máxima en segundos
    duracion_max_segundos = duracion_max_minutos * 60
    
    # Calcular duración acumulada y encontrar el punto de corte
    duracion_acumulada = 0.0
    escenas_finales = []
    
    for escena in escenas:
        if duracion_acumulada + escena.duracion_segundos <= duracion_max_segundos:
            escenas_finales.append(escena)
            duracion_acumulada += escena.duracion_segundos
        else:
            # Si agregar esta escena excedería, no la incluimos
            break
    
    # Si no hay escenas, al menos devolver la primera
    if not escenas_finales and escenas:
        escenas_finales = [escenas[0]]
    
    # Reconstruir el guion desde las escenas seleccionadas
    return "\n\n".join(e.texto for e in escenas_finales)


def _guion_fallback(tema: str, duracion_min: int, escenas_objetivo: int | None = None) -> str:
    """Guion de ejemplo cuando no hay API configurada."""
    if escenas_objetivo is None:
        escenas_objetivo = max(1, (duracion_min * 60) // 5)
    lineas = [
        f"En este video hablaremos sobre: {tema}.",
        "La idea central es muy importante para entender el tema.",
        "Veamos los puntos clave uno por uno.",
    ]
    while len(lineas) < escenas_objetivo:
        lineas.append(f"Aquí desarrollamos otro aspecto de {tema}.")
    return "\n\n".join(lineas[:escenas_objetivo])


def guardar_guion(contenido: str, nombre: str = "guion") -> Path:
    out = BASE / "output" / "guiones"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{nombre}.txt"
    path.write_text(contenido, encoding="utf-8")
    return path
