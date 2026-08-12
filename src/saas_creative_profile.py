"""Perfil creativo SaaS: esquema enriquecido, fusión con disco y texto para prompts."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .catalog_service import VOICES

# Ideas sugeridas / viral: núcleo entretenimiento no sea glorificación narco; el tono del canal es oscuro y adictivo.
DEFAULT_IDEAS_ANGLES_TO_AVOID = (
    "Glorificar narcotráfico, carteles, sicarios, balaceras o narconovela como núcleo de diversión; "
    "corrupción-política-mejor-tráfico como premisa central; cuentos infantiles, fantasía épica, tono poético o ‘historia bonita’; "
    "relleno tipo ChatGPT, intros de youtuber, moralejas edulcoradas."
)


def default_creative_profile() -> dict[str, Any]:
    return {
        "style": "",
        "content_type": "reddit_dark_storytime",
        # workflow: "studio" | "documentary" — Documentary channel sessions set "documentary"
        "workflow": "studio",
        "avoid": [],
        "niche": "",
        "audience": {
            "who": "",
            "pain_points": "",
            "reading_level": "general",
        },
        "tone": "",
        "hook_style": "",
        "pacing": "Medio",
        "narrator_preference": list(VOICES.keys())[0],
        "language_register": "Español neutro, tuteo",
        "topics_to_avoid": "",
        "topics_to_focus": [],
        "title_style": "",
        "thumbnail_style": "",
        "channel": {
            "name": "",
            "tagline": "",
            "content_pillars": "",
            "goal_count": 0,
            "language": "",
            "target_words": 0,
            "target_duration_min": [],
            "visual_provider": "",
        },
        "script": {
            "structure_preference": "",
            "forbidden_phrases": "",
            "cta_style": "",
            "opening_style": "",
        },
        "video": {
            "primary_format": "youtube_long_16_9",
            "target_length_category": "medium",
            "aspect_notes": "",
            "content_type": "",
            "narration_format": "",
        },
        "visual": {
            "look": "",
            "color_mood": "",
            "shot_preferences": "",
            "b_roll_style": "",
            "reference_moodboards": "",
        },
        "editing": {
            "cut_rhythm": "medio",
            "transitions_default": "corte limpio",
            "lower_thirds": "no",
            "subtitles_intent": "ninguno_en_mvp",
            "music_role": "bajo_voz",
            "pacing_visual": "",
            "notes_for_ai_director": "",
        },
        # Guía para «Ideas sugeridas» en Nuevo video (planner IA + heurística).
        "idea_generation": {
            "brief": "",
            "angles_to_favor": "",
            "angles_to_avoid": DEFAULT_IDEAS_ANGLES_TO_AVOID,
        },
        "notes_freeform": "",
    }


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for k, v in incoming.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _is_empty_value(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return True
    if isinstance(v, dict) and not any(not _is_empty_value(x) for x in v.values()):
        return True
    return False


def deep_merge_skip_empty(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Fusiona patch sobre base sin pisar con strings vacíos ni dicts vacíos."""
    for k, v in patch.items():
        if _is_empty_value(v):
            continue
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            deep_merge_skip_empty(base[k], v)
        else:
            base[k] = v
    return base


def parse_llm_json_object(raw: str) -> dict[str, Any] | None:
    """Extrae un objeto JSON de la salida del modelo (markdown, texto alrededor, etc.)."""
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) >= 2 else text
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    text = text.strip()
    try:
        out = json.loads(text)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        pass
    i = text.find("{")
    j = text.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        out = json.loads(text[i : j + 1])
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        return None


def merge_profile_disk(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Combina perfil guardado con defaults (nuevas claves sin perder datos)."""
    out = deepcopy(default_creative_profile())
    if not raw or not isinstance(raw, dict):
        return out
    merged = _deep_merge(out, raw)
    ig = merged.get("idea_generation")
    if isinstance(ig, dict) and not str(ig.get("angles_to_avoid") or "").strip():
        ig["angles_to_avoid"] = DEFAULT_IDEAS_ANGLES_TO_AVOID
    return merged


def merge_profile_updates(existing: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Aplica parches del asistente sobre un perfil ya fusionado con defaults (no borra con vacíos)."""
    base = merge_profile_disk(existing)
    if isinstance(updates, dict):
        deep_merge_skip_empty(base, updates)
    pace = base.get("pacing")
    if isinstance(pace, str):
        pl = pace.strip().lower()
        pace_map = {"lento": "Lento", "medio": "Medio", "rápido": "Rápido", "rapido": "Rápido"}
        if pl in pace_map:
            base["pacing"] = pace_map[pl]
    if base.get("pacing") not in ("Lento", "Medio", "Rápido"):
        base["pacing"] = "Medio"
    if base.get("narrator_preference") not in VOICES:
        base["narrator_preference"] = list(VOICES.keys())[0]
    return base


def profile_to_script_context(profile: dict[str, Any]) -> str:
    """Bloque de texto para inyectar en generación de guion."""
    p = merge_profile_disk(profile)
    return (
        "PERFIL DEL CREADOR (prioridad alta; adaptá el guion a esto)\n"
        + json.dumps(p, ensure_ascii=False, indent=2)
        + "\n\nSi el nicho o el tono piden registro educativo, informativo, infantil o corporativo serio, "
        "NO fuerces violencia, gore ni crudeza innecesaria: priorizá coherencia con el público y el nicho. "
        "Si el perfil pide otro tipo de apertura distinta a la plantilla por defecto del sistema, "
        "respetá script.opening_style y hook_style del perfil."
    )


def profile_to_edit_planner_context(profile: dict[str, Any]) -> str:
    p = merge_profile_disk(profile)
    return json.dumps(
        {
            "style": p.get("style", ""),
            "content_type": p.get("content_type", ""),
            "avoid": p.get("avoid", []),
            "visual": p.get("visual", {}),
            "editing": p.get("editing", {}),
            "video": p.get("video", {}),
            "tone": p.get("tone", ""),
            "hook_style": p.get("hook_style", ""),
            "pacing": p.get("pacing", ""),
            "niche": p.get("niche", ""),
            "audience": p.get("audience", {}),
        },
        ensure_ascii=False,
        indent=2,
    )
