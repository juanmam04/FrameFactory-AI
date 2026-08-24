"""Canonical Creative Profile for Check ALS."""
from __future__ import annotations

from typing import Any

from src.saas_creative_profile import merge_profile_disk
from src.documentary.formats.check_als.editorial import (
    CHANNEL_NAME,
    CHANNEL_ONE_LINER,
    CONTENT_LANGUAGE,
    DEFAULT_CATEGORIES,
    EDITORIAL_PRINCIPLE,
    HOOK_LANGUAGE,
    IMAGE_PROMPT_LANGUAGE,
    NARRATION_LANGUAGE,
    OVERLAY_LANGUAGE,
    SCRIPT_LANGUAGE,
    TITLE_LANGUAGE,
    VISUAL_DIRECTION,
    VISUAL_STYLE_ID,
)


def check_als_profile() -> dict[str, Any]:
    return merge_profile_disk(
        {
            "workflow": "check_als",
            "content_format": "check_als",
            "content_type": "check_als",
            "language": CONTENT_LANGUAGE,
            "narration_language": NARRATION_LANGUAGE,
            "title_language": TITLE_LANGUAGE,
            "hook_language": HOOK_LANGUAGE,
            "script_language": SCRIPT_LANGUAGE,
            "overlay_language": OVERLAY_LANGUAGE,
            "image_prompt_language": IMAGE_PROMPT_LANGUAGE,
            "style": "simulaciones aspiracionales de vida — ficción cinematográfica en segunda persona",
            "niche": (
                "Historias ficticias en segunda persona donde vives una vida extraordinaria: "
                "construir empresas, riqueza, imperios, carreras, poder, libertad y regresos. "
                "Progresión y fantasía — no consejos."
            ),
            "avoid": [
                "educación de negocios / tutoriales para enriquecerse",
                "encuadre documental / historia real",
                "biografías de personas reales como columna vertebral",
                "gritos motivacionales / tono MrBeast",
                "relleno genérico de IA y jerga corporativa",
                "morales obvias / finales de lecciones aprendidas",
                "aperturas Hoy vamos a / En este video / Bienvenidos de nuevo",
                "estética de cartoon infantil",
                "slideshow de mansiones sin historia",
                "español de traducción (embarcarte en un viaje, navegar los desafíos, etc.)",
            ],
            "audience": {
                "who": "Espectadores de YouTube en español que quieren sentir una vida extraordinaria, no un curso",
                "pain_points": "Aburridos de los consejos; con hambre de progresión y riesgo",
                "reading_level": "general",
            },
            "tone": "calmado, seguro, cinematográfico, cercano, ligeramente dramático",
            "hook_style": (
                "Entra en la vida de inmediato en segunda persona (tú): edad, dinero, casa, "
                "luego oportunidad/problema. Sin intro de canal."
            ),
            "pacing": "Algo significativo cada 20–40 segundos",
            "language_register": (
                "Español internacional/natural (LatAm + España), oraciones cortas, "
                "cadencia hablada. Tú/te/tienes/eres. No vos por defecto."
            ),
            "topics_to_focus": list(DEFAULT_CATEGORIES),
            "topics_to_avoid": "Biografías reales como trama; tutoriales para enriquecerse; lujo vacío sin decisiones",
            "title_style": (
                "Títulos en español nativo para YouTube; POV: + verbo en segunda persona cuando suene natural; "
                "fantasía clara; sin claims documentales falsos"
            ),
            "thumbnail_style": (
                "Una situación, un estado del protagonista, un contraste, pocos elementos, lectura instantánea. "
                "Campos editoriales en español; thumbnail_prompt en inglés. Solo prompt — Check no genera imágenes."
            ),
            "channel": {
                "name": CHANNEL_NAME,
                "tagline": EDITORIAL_PRINCIPLE + " · " + CHANNEL_ONE_LINER,
                "content_format": "check_als",
                "content_pillars": ", ".join(DEFAULT_CATEGORIES),
                "goal_count": 100,
                "language": CONTENT_LANGUAGE,
                "narration_language": NARRATION_LANGUAGE,
                "title_language": TITLE_LANGUAGE,
                "hook_language": HOOK_LANGUAGE,
                "script_language": SCRIPT_LANGUAGE,
                "overlay_language": OVERLAY_LANGUAGE,
                "image_prompt_language": IMAGE_PROMPT_LANGUAGE,
                "narration_perspective": "second_person",
                "target_words": 1800,
                "target_duration_min": [12, 18],
                "visual_style": VISUAL_STYLE_ID,
                "visual_provider": "external_manual",
            },
            "script": {
                "structure_preference": "bucle de dopamina: deseo → esfuerzo → progreso → recompensa → problema → decisión → progreso mayor",
                "forbidden_phrases": (
                    "Bienvenidos de nuevo; En este video; Hoy vamos a; Imagina si; "
                    "Aquí van cinco lecciones; Suscríbete; historia con moraleja; lecciones aprendidas; "
                    "embarcarte en un viaje; navegar los desafíos; contra todo pronóstico"
                ),
                "cta_style": "ninguno en narración",
                "opening_style": "Cold open en segunda persona: estado de vida + oportunidad",
                "narration_perspective": "second_person",
                "language": SCRIPT_LANGUAGE,
            },
            "video": {
                "primary_format": "youtube_long_16_9",
                "target_length_category": "long_12_18",
                "aspect_notes": "16:9",
                "content_type": "check_als",
                "content_format": "check_als",
                "narration_format": "second_person_als",
                "visual_style": VISUAL_STYLE_ID,
                "language": CONTENT_LANGUAGE,
            },
            "visual": {
                "look": VISUAL_DIRECTION,
                "color_mood": "Progresivo: grind apagado al inicio → luz/éxito más ricos después",
                "shot_preferences": "establishing / wide / medium / close / OTS / POV insert / detail — nunca el mismo stare centrado",
                "b_roll_style": "Recompensas de estilo de vida ganadas por la historia: casa, auto, oficina, viaje — no lujo aleatorio",
                "reference_moodboards": "Avatar del protagonista + masters de locación antes del batch de escenas",
                "image_prompt_language": IMAGE_PROMPT_LANGUAGE,
            },
            "editing": {
                "cut_rhythm": "dirigido por progresión; cambio cada 20–40s",
                "transitions_default": "ken burns suave + fades cortos",
                "lower_thirds": "overlays de métricas solo en hitos (Fase 5); display_value vs spoken_value",
                "subtitles_intent": "burned_optional",
                "music_role": "arco emocional (fase posterior)",
                "pacing_visual": "Anclado a la voz; stills siguen beats",
                "notes_for_ai_director": (
                    "Check no genera imágenes in-app. Exporta prompts (EN) para ilustración externa. "
                    "Continuidad de avatar + locaciones es obligatoria. Contenido/voz/captions en español."
                ),
            },
            "idea_generation": {
                "brief": "Paquetes de concepto completos en español: idea + títulos + thumbnail + hook, una fantasía.",
                "angles_to_favor": "Transformación de vida medible; decisiones; crisis; recompensas visibles",
                "angles_to_avoid": "Consejos; documental; biografía; flex vacío sin progresión",
                "categories": list(DEFAULT_CATEGORIES),
            },
            "notes_freeform": (
                "CONTENT LANGUAGE = es. Image prompts = en si conviene al modelo. "
                "IDs/schemas internos = en. "
                "PHASE 2 NOTE: world_state es la fuente de verdad para beats, hechos del script, métricas, "
                "overlays y prompts visuales. Cualquier contradicción debe fallar QC. "
                "Overlays futuros: display_value (pantalla) vs spoken_value (TTS natural)."
            ),
        }
    )
