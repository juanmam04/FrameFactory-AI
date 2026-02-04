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
) -> str:
    """Genera un guion largo a partir de un tema usando la API configurada."""
    plantillas = get_plantillas_guion()
    templates = plantillas.get("plantillas", {})
    t = templates.get(plantilla, templates.get("explicativo", {}))
    duracion_min = duracion_min or plantillas.get("duracion_default_minutos", 2)
    
    # Si no se especifica duracion_max, usar duracion_min + 3 como default
    if duracion_max is None:
        duracion_max = duracion_min + 3
    if duracion_max < duracion_min:
        duracion_max = duracion_min
    
    # Formatear prompt con ambas duraciones
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
        # Agregar instrucción sobre duración máxima al final del prompt
        prompt_usuario += f"\n\nIMPORTANTE: El video debe durar entre {duracion_min} y {duracion_max} minutos. No excedas los {duracion_max} minutos."
    rules = get_narrative_rules()
    system_base = t.get("sistema", "Eres un guionista para videos. Un párrafo por escena de 5 segundos.")
    system_extra = (rules.get("system_extra") or "").strip()
    system = f"{system_base}\n\n{system_extra}" if system_extra else system_base

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _guion_fallback(tema, duracion_min)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt_usuario},
            ],
        )
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return _guion_fallback(tema, duracion_min)


def _guion_fallback(tema: str, duracion_min: int) -> str:
    """Guion de ejemplo cuando no hay API configurada."""
    escenas = max(1, (duracion_min * 60) // 5)
    lineas = [
        f"En este video hablaremos sobre: {tema}.",
        "La idea central es muy importante para entender el tema.",
        "Veamos los puntos clave uno por uno.",
    ]
    while len(lineas) < escenas:
        lineas.append(f"Aquí desarrollamos otro aspecto de {tema}.")
    return "\n\n".join(lineas[:escenas])


def guardar_guion(contenido: str, nombre: str = "guion") -> Path:
    out = BASE / "output" / "guiones"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{nombre}.txt"
    path.write_text(contenido, encoding="utf-8")
    return path
