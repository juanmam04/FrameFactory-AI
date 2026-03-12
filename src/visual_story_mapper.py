"""Capa de storytelling visual: transforma metadata base en metadata narrativa.

Input (base_meta típico de scene_visual_mapper):
{
  "scene_type": "...",
  "scene_mode": "...",
  "scene_characters": [...],
  "location": "...",
  "action": "...",
  "mood": "...",
  "key_visual": "...",
  "camera": "...",
  "character_overrides": {...}
}

Output (enriquecido):
{
  ...lo anterior...,
  "thematic_context": "...",
  "visual_device": "...",
  "symbolic_tags": [...],          # tags internos
  "symbolic_descriptions": [...],  # listo para prompt
  "narrative_representation_mode": "...",
  "scene_focus": "...",
  "camera_priority": "..."
}
"""
from __future__ import annotations

from typing import Dict, Any, List

from .config_loader import get_visual_motifs


_MOTIFS = get_visual_motifs()


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _resolve_thematic_context(base_meta: Dict[str, Any], video_theme: str | None) -> str | None:
    """Elige contexto temático global."""
    themes = _MOTIFS.get("themes") or {}
    if video_theme and video_theme in themes:
        return video_theme

    action = (base_meta.get("action") or "").lower()
    scene_type = base_meta.get("scene_type", "")

    if "fútbol" in action or "futbol" in action or "balón" in action or "balon" in action:
        if "carrera" in action or "sueña" in action or "sueña con" in action:
            return "football_career"
        if "industria" in action or "negocio" in action or "contrato" in action:
            return "football_industry"
        return "football"
    if scene_type.startswith("war_"):
        return "war"
    if "policía" in action or "policia" in action:
        return "crime_pressure"
    if "oficina" in action or "negocio" in action:
        return "business_power"

    return None


def _pick_visual_device(base_meta: Dict[str, Any], thematic_context: str | None) -> str:
    """Elige el dispositivo visual principal usando scene_type + modo + theme + action."""
    action = (base_meta.get("action") or "").lower()
    scene_type = base_meta.get("scene_type", "")
    scene_mode = base_meta.get("scene_mode", "present")

    # Sueños / recuerdos
    if scene_mode in ("memory", "dream"):
        if thematic_context and thematic_context.startswith("football"):
            return "football_glory"
        return "empty_room_tension"

    # Escenas de prensa
    if scene_type == "press_conference":
        return "press_scene"

    # Llamadas / mensajes
    if _contains_any(action, ["llamada", "telefono", "teléfono", "sonó el teléfono", "recibe una llamada"]):
        return "phone_call"
    if _contains_any(action, ["mensaje", "notificación", "notificacion"]):
        return "message_reveal"

    # Amenaza / policía en interiores
    if thematic_context == "crime_pressure" and _contains_any(
        action, ["acecha", "vigila", "lo buscan", "presión", "presion", "amenaza"]
    ):
        return "police_lights"

    # Contrato / industria fútbol o negocios
    if _contains_any(action, ["contrato", "carpeta", "documento", "firma", "oferta"]):
        return "contract_moment"

    # Investigación en escritorio
    if _contains_any(action, ["investiga", "lee documentos", "revisa papeles", "en su escritorio"]):
        return "desk_research"

    # Escenas claramente futboleras de gloria
    if thematic_context and thematic_context.startswith("football") and _contains_any(
        action, ["estadio", "hinchada", "tribuna", "aficion", "afición", "canta la hinchada", "anota un gol"]
    ):
        return "football_glory"

    # Fallback por tipo de escena
    if scene_type == "office_meeting":
        return "desk_research"
    if scene_type.startswith("warehouse"):
        return "shadow_threat"

    # Fallback genérico
    return "empty_room_tension"


def _collect_theme_symbols(thematic_context: str | None) -> List[str]:
    if not thematic_context:
        return []
    themes = _MOTIFS.get("themes") or {}
    data = themes.get(thematic_context) or {}
    return list(data.get("recurring_symbols") or [])


def _collect_device_elements(visual_device: str) -> List[str]:
    devices = _MOTIFS.get("scene_devices") or {}
    data = devices.get(visual_device) or {}
    return list(data.get("preferred_elements") or [])


def _build_symbolic_tags(
    thematic_context: str | None,
    visual_device: str,
) -> List[str]:
    """Devuelve hasta 4 tags internos, priorizando una idea dominante."""
    tags: List[str] = []

    # 1) Dominante: dispositivo visual
    tags.append(visual_device)

    # 2) Símbolos de tema global (enriquece pero no invade)
    theme_syms = _collect_theme_symbols(thematic_context)
    for s in theme_syms:
        if len(tags) >= 4:
            break
        if s not in tags:
            tags.append(s)

    # 3) Elementos específicos del device
    device_elems = _collect_device_elements(visual_device)
    for s in device_elems:
        if len(tags) >= 4:
            break
        if s not in tags:
            tags.append(s)

    return tags[:4]


_SYMBOL_TAG_PHRASES: Dict[str, str] = {
    "phone_call": "glowing phone screen with important caller ID visible",
    "phone_screen": "phone screen with clear caller name",
    "notification_icon": "notification icon on phone screen",
    "football_contract": "football contract folder on the desk",
    "director_call": "phone call from sports director",
    "sports_documents": "stack of football-related documents on the desk",
    "sports_office": "sports director office desk with football notes",
    "trophy": "trophy on a small shelf",
    "trophy_cabinet": "trophy cabinet in the background",
    "stadium": "football stadium environment",
    "stadium_crowd": "crowd in a football stadium",
    "flags": "team flags waving in the stands",
    "spotlight": "bright spotlight from above",
    "siren_reflection": "red and blue police lights reflected on the wall",
    "shadow_in_window": "shadowy silhouette hinted through the window",
    "parked_car": "parked car suggested outside the window",
    "empty_chair": "empty chair facing the protagonist",
    "single_lamp": "single desk lamp as main light source",
    "long_shadows": "long shadows stretching across the room",
    "podium": "press podium with microphones",
    "microphones": "cluster of microphones in front of the protagonist",
    "audience_rows": "blurred audience rows in the background",
    "folder": "closed folder on the desk",
    "documents": "open documents on the desk",
    "desk": "simple desk surface",
    "lamp": "desk lamp casting warm light",
    "coffee_mug": "coffee mug near the edge of the desk",
}


def _symbol_tag_to_phrase(tag: str) -> str:
    return _SYMBOL_TAG_PHRASES.get(tag, tag.replace("_", " "))


def _pick_representation_mode(base_meta: Dict[str, Any], visual_device: str, thematic_context: str | None) -> str:
    scene_mode = base_meta.get("scene_mode", "present")
    action = (base_meta.get("action") or "").lower()
    scene_type = base_meta.get("scene_type", "")

    if scene_mode == "memory":
        return "emotional"
    if visual_device in ("phone_call", "message_reveal"):
        return "symbolic"
    if _contains_any(action, ["acecha", "vigila", "lo buscan", "presión", "presion", "amenaza"]) and scene_type.endswith(
        "interior"
    ):
        return "indirect"
    if visual_device == "football_glory":
        return "literal"
    if thematic_context == "crime_pressure":
        return "indirect"
    return "literal"


def _pick_scene_focus(base_meta: Dict[str, Any], visual_device: str) -> str:
    if visual_device in ("phone_call", "message_reveal"):
        return "phone_screen"
    if visual_device == "police_lights":
        return "lights_through_window"
    if visual_device == "football_glory":
        return "stadium_scale"
    if visual_device == "contract_moment":
        return "documents_on_desk"
    if visual_device == "press_scene":
        return "microphones_and_podium"
    if visual_device == "desk_research":
        return "desk_research"
    if visual_device == "shadow_threat":
        return "villain_presence"
    if visual_device == "empty_room_tension":
        return "protagonist_face"
    return "protagonist_face"


def _pick_camera_priority(scene_focus: str) -> str:
    if scene_focus == "protagonist_face":
        return "close up"
    if scene_focus == "phone_screen":
        return "close up"
    if scene_focus == "trophy_cabinet":
        return "medium shot"
    if scene_focus == "stadium_scale":
        return "wide shot"
    if scene_focus == "villain_presence":
        return "medium shot"
    if scene_focus == "lights_through_window":
        return "rear view"
    if scene_focus == "documents_on_desk":
        return "over the shoulder"
    if scene_focus == "desk_research":
        return "over the shoulder"
    if scene_focus == "microphones_and_podium":
        return "medium shot"
    return "medium shot"


def enrich_scene_visual_meta(base_meta: Dict[str, Any], video_theme: str | None = None) -> Dict[str, Any]:
    """Capa narrativa para escenas normales."""
    meta = dict(base_meta)
    thematic_context = _resolve_thematic_context(meta, video_theme)
    visual_device = _pick_visual_device(meta, thematic_context)
    symbolic_tags = _build_symbolic_tags(thematic_context, visual_device)
    symbolic_desc = [_symbol_tag_to_phrase(tag) for tag in symbolic_tags]
    representation_mode = _pick_representation_mode(meta, visual_device, thematic_context)
    scene_focus = _pick_scene_focus(meta, visual_device)
    camera_priority = _pick_camera_priority(scene_focus)

    meta["thematic_context"] = thematic_context
    meta["visual_device"] = visual_device
    meta["symbolic_tags"] = symbolic_tags
    meta["symbolic_descriptions"] = symbolic_desc
    meta["narrative_representation_mode"] = representation_mode
    meta["scene_focus"] = scene_focus
    meta["camera_priority"] = camera_priority
    return meta


def enrich_beat_visual_meta(base_meta: Dict[str, Any], video_theme: str | None = None) -> Dict[str, Any]:
    """Igual que enrich_scene_visual_meta pero para beats."""
    return enrich_scene_visual_meta(base_meta, video_theme=video_theme)

