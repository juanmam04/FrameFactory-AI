"""
Enriquece nombres de locación abstractos o ficticios con una descripción visual concreta
para generación de imágenes, sin eliminar el nombre original.
"""
from __future__ import annotations

import os
import re

# Palabras que ya sugieren un entorno dibujable (ES/EN); si hay match, no enriquecemos.
_CONCRETE_VISUAL_TOKENS = frozenset(
    {
        # interiores / arquitectura
        "room", "kitchen", "bedroom", "bathroom", "office", "hall", "corridor", "hallway",
        "stairs", "window", "door", "ceiling", "floor", "wall", "desk", "chair", "table",
        "sofa", "bed", "shelf", "garage", "basement", "attic", "elevator", "lobby",
        "cuarto", "habitación", "habitacion", "cocina", "baño", "bano", "oficina", "pasillo",
        "escalera", "ventana", "puerta", "techo", "suelo", "pared", "escritorio", "silla",
        "mesa", "sofá", "sofa", "cama", "estante", "cochera", "sótano", "ascensor",
        "sala", "living", "comedor", "dormitorio",
        # exteriores / naturaleza
        "street", "road", "alley", "sidewalk", "bridge", "park", "forest", "woods", "beach",
        "ocean", "river", "lake", "mountain", "hill", "field", "meadow", "grass", "sand",
        "sky", "sunset", "sunrise", "rain", "snow", "fog", "night", "daylight",
        "calle", "avenida", "camino", "puente", "parque", "bosque", "playa", "mar", "río",
        "rio", "lago", "montaña", "montana", "colina", "pradera", "césped", "cesped", "arena",
        "cielo", "atardecer", "amanecer", "lluvia", "nieve", "niebla", "noche", "día", "dia",
        # urbano / lugares comunes
        "city", "building", "tower", "rooftop", "subway", "train", "station", "airport",
        "hospital", "school", "church", "temple", "shop", "store", "mall", "restaurant",
        "bar", "café", "cafe", "warehouse", "factory", "parking",
        "ciudad", "edificio", "torre", "azotea", "metro", "tren", "estación", "estacion",
        "aeropuerto", "hospital", "escuela", "iglesia", "templo", "tienda", "restaurante",
        "almacén", "almacen", "fábrica", "fabrica",
        # iluminación / atmósfera explícita
        "neon", "lamp", "lámpara", "lampara", "candle", "vela", "smoke", "humo", "fire",
        "fuego", "interior", "exterior", "outdoor", "indoor",
    }
)

# Patrones de nombre propio ficticio típico (p. ej. "Campo de Arkenvale", "Torre de X")
_PROPER_PLACE_PATTERN = re.compile(
    r"^\s*[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+de\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñA-Za-záéíóúñ\s'-]+)+\s*$"
)


def location_has_concrete_visual_cues(text: str) -> bool:
    """True si el texto ya describe algo claramente visualizable."""
    t = (text or "").strip().lower()
    if not t:
        return False
    if " — " in text or (" - " in text and len(text) > 40):
        # Ya enriquecido o descripción larga con separador
        return True
    tokens = re.findall(r"[a-záéíóúñ]+", t)
    return any(tok in _CONCRETE_VISUAL_TOKENS for tok in tokens)


def needs_location_visual_enrichment(location_prompt: str) -> bool:
    """True si conviene añadir capa visual obligatoria."""
    loc = (location_prompt or "").strip()
    if len(loc) < 3:
        return False
    if location_has_concrete_visual_cues(loc):
        return False
    # Nombres cortos o solo proper-noun suelen ser ficticios
    if len(loc.split()) <= 5:
        return True
    if _PROPER_PLACE_PATTERN.match(loc):
        return True
    return not location_has_concrete_visual_cues(loc)


def _heuristic_visual_suffix(location_prompt: str) -> str:
    low = location_prompt.lower()
    if any(w in low for w in ("campo", "field", "pradera", "prairie", "vale", "valle")):
        return (
            "wide open grassy field, soft sunlight, distant hills, clear sky, "
            "readable horizon, cinematic cartoon depth"
        )
    if any(w in low for w in ("torre", "tower", "castillo", "castle", "palacio", "palace", "citadel")):
        return (
            "imposing stone architecture, dramatic sky, strong perspective, "
            "clear materials and lighting, cinematic cartoon readability"
        )
    if any(w in low for w in ("bosque", "forest", "wood", "selva", "jungle")):
        return (
            "trees and undergrowth layers, dappled light, clear ground path, "
            "atmospheric depth, cinematic cartoon style"
        )
    if any(w in low for w in ("mar", "ocean", "océano", "oceano", "playa", "beach", "costa", "coast")):
        return (
            "open water and sky, horizon line, wet sand or rocks, natural light, "
            "readable scale, cinematic cartoon illustration"
        )
    if any(w in low for w in ("ciudad", "city", "pueblo", "town", "villa")):
        return (
            "readable streets or rooftops, buildings with clear silhouettes, "
            "ambient light, depth and scale cues, cinematic cartoon"
        )
    return (
        "concrete readable environment: clear ground plane, walls or horizon, "
        "motivated lighting, spatial depth, cinematic cartoon storyboard style"
    )


def _enrich_with_llm(location_prompt: str, context: str) -> str | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    if os.getenv("LOCATION_VISUAL_ENRICH_LLM", "1").strip().lower() in ("0", "false", "no"):
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        user = (
            f"Place name (keep verbatim): {location_prompt!r}\n"
            f"Story context (optional): {(context or '')[:500]}\n\n"
            "Reply with ONE line only. Format: EXACT place name, then ' — ', then a concrete "
            "English visual environment for a 16:9 cinematic cartoon storyboard (lighting, materials, "
            "horizon or architecture, readable depth). Do not add new proper nouns. "
            "Do not remove or translate the place name."
        )
        r = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You output a single line: original location name + em dash + concrete "
                        "visual description for image generation."
                    ),
                },
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        out = (r.choices[0].message.content or "").strip()
        if " — " in out or " – " in out:
            return out.replace(" – ", " — ", 1) if " — " not in out else out
        if out:
            return f"{location_prompt.strip()} — {out}"
    except Exception:
        return None
    return None


def enrich_location_prompt(location_prompt: str, context: str = "") -> str:
    """
    Si la locación es abstracta, devuelve ``nombre — descripción visual concreta``.
    Si ya es visualizable, devuelve el string sin cambios.
    """
    loc = (location_prompt or "").strip()
    if not needs_location_visual_enrichment(loc):
        return loc
    llm = _enrich_with_llm(loc, context)
    if llm:
        return llm[:2000]
    suffix = _heuristic_visual_suffix(loc)
    return f"{loc} — {suffix}"


def maybe_enrich_location_prompt(
    location_prompt: str,
    *,
    context: str = "",
    scene_type: str = "",
) -> str:
    """
    Punto de entrada desde el pipeline de continuidad.
    ``scene_type`` reservado para futuras reglas (ej. exteriores).
    """
    _ = scene_type  # noqa: F841
    return enrich_location_prompt(location_prompt, context)
