"""Generación de metadata para YouTube: descripción optimizada y capítulos con timestamps."""
import os
from pathlib import Path

from dotenv import load_dotenv

from .config_loader import BASE, get_instrucciones_descripcion, get_instrucciones_miniatura
from .scene_splitter import Escena

load_dotenv(BASE / ".env")

OUTPUT_META = BASE / "output" / "metadata"
OUTPUT_THUMBNAILS = BASE / "output" / "thumbnails"


def _segundos_a_timestamp(seg: float) -> str:
    """Convierte segundos a formato 00:00 para YouTube."""
    m = int(seg // 60)
    s = int(seg % 60)
    return f"{m:02d}:{s:02d}"


def generar_capítulos(escenas: list[Escena]) -> str:
    """Genera texto de capítulos con timestamps (00:00, 00:05, ...). Cumple reglas YouTube."""
    lineas = []
    t_acum = 0.0
    for e in escenas:
        lineas.append(f"{_segundos_a_timestamp(t_acum)} {e.texto[:60]}{'…' if len(e.texto) > 60 else ''}")
        t_acum += e.duracion_segundos
    return "\n".join(lineas)


def generar_descripcion(
    titulo: str,
    guion_resumen: str,
    capítulos_texto: str,
    hook: str = "",
    cta: str = "Suscribite para más videos.",
    usar_ia: bool = True,
) -> str:
    """
    Genera descripción optimizada para YouTube usando IA con instrucciones claras.
    Si usar_ia=False, usa plantilla simple.
    """
    if usar_ia:
        return _generar_descripcion_con_ia(titulo, guion_resumen, capítulos_texto, hook, cta)
    
    # Fallback: plantilla simple
    partes = []
    if hook:
        partes.append(hook.strip())
    partes.append(guion_resumen[:500].strip() + ("..." if len(guion_resumen) > 500 else ""))
    partes.append("\n--- Capítulos ---\n")
    partes.append(capítulos_texto)
    if cta:
        partes.append("\n---\n" + cta.strip())
    return "\n\n".join(partes)


def _generar_descripcion_con_ia(
    titulo: str,
    guion_resumen: str,
    capítulos_texto: str,
    hook: str,
    cta: str,
) -> str:
    """Genera descripción optimizada para YouTube usando OpenAI con instrucciones claras."""
    import os
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fallback si no hay API
        return generar_descripcion(titulo, guion_resumen, capítulos_texto, hook, cta, usar_ia=False)
    
    # Cargar instrucciones desde configuración
    instrucciones = get_instrucciones_descripcion()
    system_prompt = instrucciones.get("system_prompt", """Eres un experto en SEO y marketing para YouTube. Genera descripciones optimizadas.""")
    user_template = instrucciones.get("user_prompt_template", "Genera una descripción para: {titulo}")
    
    user_prompt = user_template.format(
        titulo=titulo,
        guion_resumen=guion_resumen[:1000],
        capítulos_texto=capítulos_texto,
        hook=hook if hook else "Crear uno potente basado en el tema",
        cta=cta,
    )
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        descripcion = (response.choices[0].message.content or "").strip()
        # Asegurar que incluya los capítulos si no los tiene
        if "capítulo" not in descripcion.lower() and capítulos_texto:
            descripcion += f"\n\n--- Capítulos ---\n{capítulos_texto}"
        return descripcion
    except Exception:
        # Fallback si falla la IA
        return generar_descripcion(titulo, guion_resumen, capítulos_texto, hook, cta, usar_ia=False)


def guardar_metadata(
    nombre_proyecto: str,
    titulo: str,
    descripcion: str,
    capítulos: str,
    ruta_miniatura: Path | None = None,
) -> Path:
    """Guarda descripción y capítulos en un archivo para copiar a YouTube."""
    OUTPUT_META.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_META / f"{nombre_proyecto}_youtube.txt"
    contenido = f"# Título\n{titulo}\n\n# Descripción\n{descripcion}\n\n# Capítulos (copiar en descripción)\n{capítulos}"
    if ruta_miniatura:
        contenido += f"\n\n# Miniatura\nRuta: {ruta_miniatura}"
    path.write_text(contenido, encoding="utf-8")
    return path


def generar_metadata_completa(
    nombre_proyecto: str,
    tema: str,
    escenas: list[Escena],
    guion_texto: str,
    usar_ia_descripcion: bool = True,
    generar_miniatura_flag: bool = True,
) -> tuple[Path, Path | None]:
    """
    Genera descripción + capítulos + miniatura y los guarda.
    Retorna: (ruta_metadata, ruta_miniatura)
    """
    capítulos = generar_capítulos(escenas)
    titulo = tema[:100] if tema else nombre_proyecto
    descripcion = generar_descripcion(
        titulo=titulo,
        guion_resumen=guion_texto[:800],
        capítulos_texto=capítulos,
        hook=f"Video sobre: {tema[:200]}." if tema else "",
        cta="Suscribite para más videos.",
        usar_ia=usar_ia_descripcion,
    )
    
    # Generar miniatura si está habilitado
    ruta_miniatura = None
    if generar_miniatura_flag:
        ruta_miniatura = generar_miniatura(
            nombre_proyecto=nombre_proyecto,
            titulo=titulo,
            tema=tema,
            guion_resumen=guion_texto[:800],
            usar_ia=True,
        )
    
    metadata_path = guardar_metadata(nombre_proyecto, titulo, descripcion, capítulos, ruta_miniatura)
    return metadata_path, ruta_miniatura


def generar_prompt_miniatura(
    titulo: str,
    tema: str,
    guion_resumen: str,
    usar_ia: bool = True,
) -> str:
    """
    Genera un prompt optimizado para crear la miniatura del video usando IA.
    El prompt debe ser visual, llamativo y representar el tema del video.
    """
    if usar_ia:
        return _generar_prompt_miniatura_con_ia(titulo, tema, guion_resumen)
    
    # Fallback: prompt simple
    return f"Miniatura de YouTube sobre {tema}, diseño llamativo, colores vibrantes, texto legible"


def _generar_prompt_miniatura_con_ia(
    titulo: str,
    tema: str,
    guion_resumen: str,
) -> str:
    """Genera prompt para miniatura usando OpenAI con instrucciones claras."""
    import os
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return generar_prompt_miniatura(titulo, tema, guion_resumen, usar_ia=False)
    
    # Cargar instrucciones desde configuración
    instrucciones = get_instrucciones_miniatura()
    system_prompt = instrucciones.get("system_prompt", """Eres un experto en diseño de miniaturas para YouTube.""")
    user_template = instrucciones.get("user_prompt_template", "Genera un prompt para: {titulo}")
    
    user_prompt = user_template.format(
        titulo=titulo,
        tema=tema,
        guion_resumen=guion_resumen[:500],
    )
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
        )
        prompt = (response.choices[0].message.content or "").strip()
        # Limpiar el prompt si tiene comillas o explicaciones
        prompt = prompt.strip('"').strip("'")
        if prompt.startswith("Prompt:"):
            prompt = prompt.replace("Prompt:", "").strip()
        return prompt
    except Exception:
        return generar_prompt_miniatura(titulo, tema, guion_resumen, usar_ia=False)


def generar_miniatura(
    nombre_proyecto: str,
    titulo: str,
    tema: str,
    guion_resumen: str,
    usar_ia: bool = True,
) -> Path | None:
    """
    Miniatura: ya no usa DALL-E (muy caro). Retorna None; podés usar un frame del video
    o generar la miniatura con ComfyUI por separado.
    """
    return None
