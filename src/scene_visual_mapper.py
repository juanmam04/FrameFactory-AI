"""Mapeo de escenas / beats a metadata visual estructurada para generación de imágenes.

Salida estándar:
{
  "scene_type": "...",
  "scene_characters": [...],
  "location": "...",
  "action": "...",
  "mood": "...",
  "key_visual": "...",
  "camera": "...",                 # sugerida (puede ser sobrescrita por prompt_builder)
  "character_overrides": {
    "protagonist": {"body_preset": "kid", "outfit_base": "kid_basic"},
    "villain_main": {"outfit_base": "dark_criminal"}
  }
}
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List

from .scene_splitter import Escena
from .visual_beats import VisualBeat


@dataclass
class VisualMeta:
    scene_type: str
    scene_characters: list[str]
    location: str
    action: str
    mood: str
    key_visual: str
    camera: str | None = None
    character_overrides: Dict[str, Dict[str, str]] | None = None
    scene_mode: str = "present"  # present, memory, flashback, dream, news

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_type": self.scene_type,
            "scene_characters": self.scene_characters,
            "location": self.location,
            "action": self.action,
            "mood": self.mood,
            "key_visual": self.key_visual,
            "camera": self.camera,
            "character_overrides": self.character_overrides or {},
            "scene_mode": self.scene_mode,
        }


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _guess_scene_type(text: str) -> str:
    t = text.lower()
    if _contains_any(t, ["videojuego", "video juegos", "gaming", "playstation", "xbox", "pc gamer", "consola"]):
        return "gaming_room"
    if _contains_any(t, ["oficina", "negocio", "empresa", "corporativa", "reunión", "reunion", "boardroom", "meeting room"]):
        return "office_meeting"
    if _contains_any(t, ["almacén", "almacen", "warehouse", "depósito", "deposito", "galpón", "galpon"]):
        if _contains_any(t, ["enfrenta", "se enfrenta", "encara", "amenaza", "discute", "negocio sucio", "trato"]):
            return "warehouse_conflict"
        return "warehouse_generic"
    if _contains_any(t, ["guerra", "batalla", "militar", "explosión", "explosion", "tanque", "bombardeo"]):
        return "war_street"
    if _contains_any(t, ["conferencia de prensa", "rueda de prensa", "reportero", "periodista", "micrófono", "microfono", "podio", "podium"]):
        return "press_conference"
    if _contains_any(t, ["clase", "aula", "escuela", "colegio", "profesor", "maestro"]):
        return "classroom"
    if _contains_any(t, ["living", "sala de estar", "sofá", "sofa", "comedor"]):
        return "home_living_room"
    if _contains_any(t, ["calle", "ciudad", "avenida", "tráfico", "trafico", "peatones", "street", "urban"]):
        return "city_street"
    if _contains_any(t, ["cuarto", "habitación", "habitacion", "dormitorio", "interior", "sala"]):
        return "generic_interior"
    if _contains_any(t, ["exterior", "al aire libre", "parque", "plaza"]):
        return "generic_exterior"
    return "generic_interior"


def _location_from_scene_type(scene_type: str) -> str:
    if scene_type == "gaming_room":
        return "bedroom with gaming setup, bed, desk and TV or monitor"
    if scene_type == "office_meeting":
        return "modern office with desk, computer, office chair and window with city skyline"
    if scene_type == "warehouse_conflict":
        return "dark warehouse interior with metal shelves, concrete floor and a parked car"
    if scene_type == "warehouse_generic":
        return "warehouse interior with shelves, boxes and concrete floor"
    if scene_type == "war_street":
        return "war-torn urban street with smoke, ruined buildings and broken cars"
    if scene_type == "press_conference":
        return "press conference room with podium, microphones, cameras and lights"
    if scene_type == "classroom":
        return "classroom with desks, chairs, blackboard and windows"
    if scene_type == "home_living_room":
        return "apartment living room with sofa, coffee table and TV"
    if scene_type == "city_street":
        return "city street with buildings, sidewalk and parked cars"
    if scene_type == "generic_exterior":
        return "urban exterior with sidewalk, buildings, streetlights and parked cars"
    # generic_interior y fallback
    return "simple private room or apartment room with bed, desk, chair, window and dim light"


def _guess_location(scene_type: str) -> str:
    return _location_from_scene_type(scene_type)


def _guess_mood(text: str) -> str:
    t = text.lower()
    # calm, focused, tense, suspicious, sad, happy, angry, triumphant, chaotic, lonely
    if _contains_any(t, ["miedo", "terror", "pánico", "panico", "nervioso", "tenso", "tensa", "amenaza", "peligro"]):
        return "tense"
    if _contains_any(t, ["sospecha", "sospechoso", "conspiración", "conspiracion", "secreto"]):
        return "suspicious"
    if _contains_any(t, ["enojo", "ira", "rabia", "furioso", "furiosa", "discutiendo"]):
        return "angry"
    if _contains_any(t, ["soledad", "solo", "sola"]):
        return "lonely"
    if _contains_any(t, ["triste", "tristeza", "llora", "llorando", "depresivo"]):
        return "sad"
    if _contains_any(t, ["feliz", "alegría", "alegria", "contento", "riendo", "risa", "celebra", "celebrando"]):
        return "happy"
    if _contains_any(t, ["triunfo", "triunfante", "victoria", "ganó", "gano", "logro"]):
        return "triumphant"
    if _contains_any(t, ["guerra", "batalla", "caos", "explosión", "explosion", "sirenas", "disturbios"]):
        return "chaotic"
    if _contains_any(t, ["concentrado", "enfocado", "focado", "se centra", "se concentra"]):
        return "focused"
    return "calm"


def _guess_scene_mode(text: str) -> str:
    """present / memory / flashback / dream / news"""
    t = text.lower()
    if _contains_any(t, ["sueño", "soñando", "soñado", "onírico", "onirico"]):
        return "dream"
    if _contains_any(
        t,
        [
            "recuerda",
            "recuerdo",
            "recordando",
            "memoria",
            "flashback",
            "pasado lejano",
            "años atrás",
            "años atras",
        ],
    ):
        return "memory"
    if _contains_any(t, ["noticias", "noticiero", "breaking news", "informativo", "cobertura en vivo"]):
        return "news"
    return "present"


def _key_visual_from_scene_type(scene_type: str, text: str) -> str:
    """2–4 elementos del lugar + opcional 1 elemento de acción, sin mezclar contextos."""
    t = text.lower()
    base: List[str] = []

    if scene_type == "gaming_room":
        base = ["TV or monitor", "game console or PC", "bed", "posters on the wall"]
    elif scene_type == "office_meeting":
        base = ["desk with computer", "office chair", "papers on desk", "window with city skyline"]
    elif scene_type in ("warehouse_conflict", "warehouse_generic"):
        base = ["hanging lamp", "metal shelves", "concrete floor", "closed metal door"]
    elif scene_type == "press_conference":
        base = ["podium with microphones", "cameras in front", "bright lights", "audience rows"]
    elif scene_type == "war_street":
        base = ["smoke clouds", "ruined buildings", "broken cars", "debris on the street"]
    elif scene_type == "classroom":
        base = ["rows of desks", "chairs", "blackboard", "windows"]
    elif scene_type == "home_living_room":
        base = ["sofa", "coffee table", "TV", "lamp"]
    elif scene_type == "city_street":
        base = ["buildings", "sidewalk", "parked cars", "street lights"]
    elif scene_type == "generic_exterior":
        base = ["open space", "ground texture", "distant buildings or trees"]
    else:  # generic_interior
        base = ["walls", "floor", "door or window"]

    base = base[:4]

    action_element: str | None = None
    if _contains_any(t, ["juega", "jugando", "videojuego", "gaming"]):
        action_element = "controller in protagonist's hands"
    elif _contains_any(t, ["escribe", "tipea", "teclea", "teclado", "computadora", "ordenador", "pc"]):
        action_element = "hands near keyboard or mouse"
    elif _contains_any(t, ["enfrenta", "se enfrenta", "encara", "discute", "apunta", "apuntando"]):
        action_element = "characters facing each other in the center"
    elif _contains_any(t, ["habla por micrófono", "habla al microfono", "hablando al microfono", "micrófono", "microfono"]):
        action_element = "character speaking into a microphone"

    visuals = base.copy()
    if action_element:
        visuals.append(action_element)

    return ", ".join(visuals[:5])


def _guess_characters(text: str) -> list[str]:
    t = text.lower()
    chars: List[str] = ["protagonist"]
    if _contains_any(t, ["amigo", "amiga", "friend", "compañero", "companero"]):
        chars.append("friend_main")
    # Villano presente solo si es encuentro físico, no recuerdo
    if "villano" in t or "enemigo" in t or "antagonista" in t:
        if not _contains_any(
            t,
            [
                "recuerdo del villano",
                "recuerda al villano",
                "recordando al villano",
                "piensa en el villano",
                "pensar en el villano",
            ],
        ):
            chars.append("villain_main")
    if _contains_any(t, ["policía", "policia", "patrulla", "police"]):
        chars.append("police_officer")
    if _contains_any(t, ["reportero", "periodista", "reporter", "micrófono", "microfono"]):
        chars.append("reporter")
    if _contains_any(t, ["soldado", "militar", "ejército", "ejercito", "army", "guerra"]):
        chars.append("soldier")
    if _contains_any(t, ["guardaespaldas", "bodyguard"]):
        chars.append("bodyguard")
    if _contains_any(
        t,
        [
            "multitud",
            "gente",
            "gente alrededor",
            "crowd",
            "público",
            "publico",
            "audiencia",
            "auditorio",
            "ejecutivos alrededor",
            "conferencia",
            "reunión",
            "reunion",
            "periodistas",
        ],
    ):
        chars.append("extras")
    # Quitar duplicados preservando orden
    seen = set()
    result: List[str] = []
    for c in chars:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _guess_character_overrides(
    scene_type: str, text: str, scene_characters: list[str]
) -> Dict[str, Dict[str, str]]:
    """Overrides por personaje: {'protagonist': {'body_preset': 'kid', 'outfit_base': 'kid_basic'}, ...}"""
    t = text.lower()
    overrides: Dict[str, Dict[str, str]] = {}

    # Body preset del protagonista
    if "protagonist" in scene_characters:
        body: str | None = None
        if _contains_any(t, ["niño", "nino", "chico", "chica", "kid", "child"]):
            body = "kid"
        elif _contains_any(t, ["adolescente", "teen", "juvenil"]):
            body = "teen"
        elif _contains_any(t, ["hombre grande", "musculoso", "fornido"]):
            body = "adult_wide"
        if body:
            overrides.setdefault("protagonist", {})["body_preset"] = body

    # Outfits del protagonista por contexto
    if "protagonist" in scene_characters:
        if scene_type == "gaming_room":
            body = overrides.get("protagonist", {}).get("body_preset", "teen")
            outfit = "kid_basic" if body == "kid" else "casual_dark"
            overrides.setdefault("protagonist", {})["outfit_base"] = outfit
        elif scene_type == "office_meeting":
            overrides.setdefault("protagonist", {})["outfit_base"] = "formal_dark"
        elif scene_type == "press_conference":
            overrides.setdefault("protagonist", {})["outfit_base"] = "formal_dark"

    # Villano principal en warehouse_conflict
    if "villain_main" in scene_characters and scene_type in ("warehouse_conflict", "warehouse_generic"):
        overrides.setdefault("villain_main", {})["outfit_base"] = "dark_criminal"

    # Roles funcionales con uniforms fijos
    if "soldier" in scene_characters:
        overrides.setdefault("soldier", {})["outfit_base"] = "military_uniform"
    if "police_officer" in scene_characters:
        overrides.setdefault("police_officer", {})["outfit_base"] = "police_uniform"
    if "bodyguard" in scene_characters:
        overrides.setdefault("bodyguard", {})["outfit_base"] = "black_suit"

    # Reportero en conferencia de prensa
    if "reporter" in scene_characters and scene_type == "press_conference":
        overrides.setdefault("reporter", {})["outfit_base"] = "formal_light"

    return overrides


def map_escena_to_visual_meta(escena: Escena, descripcion_visual: str | None = None) -> Dict[str, Any]:
    """
    Transforma una escena en metadata visual.
    Usa texto de escena + descripción opcional de IA para extraer campos útiles.
    """
    base_text = " ".join(
        x for x in [(escena.texto or ""), (descripcion_visual or "")] if x
    ).strip()
    if not base_text:
        base_text = "Escena narrativa donde el protagonista realiza una acción clave."
    scene_type = _guess_scene_type(base_text)
    location = _guess_location(scene_type)
    action = (descripcion_visual or escena.texto or "").replace("\n", " ").strip()
    if not action:
        action = "simple visible action that matches the script."
    action = action[:220]
    mood = _guess_mood(base_text)
    key_visual = _key_visual_from_scene_type(scene_type, base_text)
    scene_characters = _guess_characters(base_text)
    character_overrides = _guess_character_overrides(scene_type, base_text, scene_characters)
    scene_mode = _guess_scene_mode(base_text)
    meta = VisualMeta(
        scene_type=scene_type,
        scene_characters=scene_characters,
        location=location,
        action=action,
        mood=mood,
        key_visual=key_visual,
        camera=None,
        character_overrides=character_overrides,
        scene_mode=scene_mode,
    )
    return meta.to_dict()


def map_beat_to_visual_meta(beat: VisualBeat) -> Dict[str, Any]:
    """
    Versión para beats visuales.
    Usa original_text + action + context + location del beat.
    """
    text_parts = [
        getattr(beat, "original_text", "") or "",
        getattr(beat, "action", "") or "",
        getattr(beat, "context", "") or "",
        getattr(beat, "location", "") or "",
    ]
    base_text = " ".join(x for x in text_parts if x).strip()
    if not base_text:
        base_text = "Escena narrativa donde el protagonista realiza una acción clave."
    scene_type = _guess_scene_type(base_text)
    raw_beat_loc = (getattr(beat, "location", None) or "").strip()
    if raw_beat_loc:
        location = raw_beat_loc
    else:
        location = _guess_location(scene_type)
    action = (beat.action or beat.original_text or "").replace("\n", " ").strip() or base_text
    action = action[:220]
    mood = _guess_mood(base_text)
    key_visual = _key_visual_from_scene_type(scene_type, base_text)
    scene_characters = _guess_characters(base_text)
    character_overrides = _guess_character_overrides(scene_type, base_text, scene_characters)
    scene_mode = _guess_scene_mode(base_text)
    meta = VisualMeta(
        scene_type=scene_type,
        scene_characters=scene_characters,
        location=location,
        action=action,
        mood=mood,
        key_visual=key_visual,
        camera=None,
        character_overrides=character_overrides,
        scene_mode=scene_mode,
    )
    return meta.to_dict()


# === Ejemplos de salida del mapper (sin ejecutar) ===
#
# 1) Niño jugando videojuegos en su cuarto:
#   Escena.texto ~ "Un niño juega videojuegos en su cuarto, concentrado frente a la pantalla."
#   -> location: "teen bedroom with gaming setup, bed, desk and TV or monitor"
#   -> scene_characters: ["protagonist"]
#   -> mood: "happy and energetic mood" (si menciona diversión) o "neutral cinematic mood"
#   -> key_visual: "TV or monitor, game console or PC, bed, posters on the wall"
#
# 2) Protagonista en oficina de negocios:
#   texto ~ "El protagonista está en una reunión en una gran oficina de negocios..."
#   -> location: "modern office with desk, computer, office chair and window with city skyline"
#   -> outfit_override: "formal_dark"
#
# 3) Enfrentamiento en warehouse con villano:
#   texto ~ "En un oscuro almacén, el protagonista se enfrenta al villano principal cerca de un auto estacionado."
#   -> location: "dark warehouse interior with metal shelves, concrete floor and a parked car"
#   -> scene_characters: ["protagonist", "villain_main"]
#   -> key_visual: "hanging lamp, parked car, metal shelves, closed metal door"
#
# 4) Conferencia de prensa con reportero:
#   texto ~ "En una conferencia de prensa, un reportero hace preguntas frente a los micrófonos..."
#   -> location: "press conference room with podium, microphones, cameras and lights"
#   -> scene_characters: ["protagonist", "reporter", "extras"]
#
# 5) Escena de guerra o caos urbano:
#   texto ~ "En medio de la guerra, las calles de la ciudad están destruidas..."
#   -> location: "war-torn urban street with smoke, ruined buildings and broken cars"
#   -> scene_characters: ["protagonist", "soldier", "extras"]
#   -> key_visual: "smoke clouds, ruined buildings, broken cars, debris on the street"

