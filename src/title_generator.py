"""Generador de TÍTULOS con IA (POV / virales) usando instrucciones de config."""
import os
from typing import List

from .config_loader import get_instrucciones_titulo


def sugerir_titulos_virales(
    tema: str,
    guion_resumen: str | None = None,
    notas_creador: str | None = None,
    titulo_actual: str | None = None,
) -> List[str]:
    """Devuelve una lista de títulos propuestos (ideas de contenido diversas, no similares al título actual)."""
    tema = (tema or "").strip()
    guion_resumen = (guion_resumen or "").strip()
    notas_creador = (notas_creador or "").strip()
    titulo_actual = (titulo_actual or "").strip()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    # Si no hay tema, usar un contexto genérico para brainstorming
    if not tema:
        tema = "ideas de video POV diversas (varias vidas y roles distintos)"

    instrucciones = get_instrucciones_titulo()
    system_prompt = instrucciones.get("system_prompt", "").strip()
    user_template = instrucciones.get("user_prompt_template", "").strip()
    if not user_template:
        return []

    # Si no hay título actual, indicarlo para que la IA no repita un concepto que el usuario ya tiene
    titulo_actual_para_prompt = titulo_actual if titulo_actual else "(ninguno — generá 10 ideas de categorías distintas)"

    user_prompt = user_template.format(
        tema=tema,
        guion_resumen=guion_resumen or tema,
        notas_creador=notas_creador or "",
        titulo_actual=titulo_actual_para_prompt,
    )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt or "Eres un generador de títulos para videos."},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=450,
            temperature=0.9,
        )
        texto = (r.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"⚠️ Error al generar títulos con IA: {e}")
        return []

    # Procesar líneas: quitar numeración/bullets si el modelo los agrega igualmente
    titulos: List[str] = []
    for line in texto.splitlines():
        l = line.strip()
        if not l:
            continue
        # Quitar prefijos tipo "1. " o "- "
        if l[0].isdigit() and "." in l[:4]:
            l = l.split(".", 1)[1].strip()
        if l.startswith("- "):
            l = l[2:].strip()
        if not l:
            continue
        # Asegurar prefijo POV:
        if not l.lower().startswith("pov:"):
            l = "POV: " + l.lstrip(": ").lstrip()
        titulos.append(l[:120])
    # Devolver únicos preservando orden
    vistos = set()
    unicos: List[str] = []
    for t in titulos:
        if t not in vistos:
            vistos.add(t)
            unicos.append(t)
    return unicos


