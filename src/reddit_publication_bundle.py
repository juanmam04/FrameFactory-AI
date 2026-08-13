"""Título, descripción y miniatura alineados al Creative Profile (historias virales)."""
from __future__ import annotations

import json
import os
from typing import Any

from .config_loader import get_narrative_rules
from .saas_creative_profile import merge_profile_disk, profile_to_script_context


def generar_bundle_publicacion_youtube(
    *,
    topic: str,
    script_text: str,
    scenes: list[dict[str, Any]],
    profile: dict[str, Any] | None,
    packaging_mode: str = "default",
) -> dict[str, Any]:
    """
    Devuelve dict con: title, alt_titles (2), description, thumbnail{text, image_prompt, layout}.
    Sin API: valores heurísticos razonables.
    """
    p = merge_profile_disk(profile or {})
    api_key = os.getenv("OPENAI_API_KEY")
    script_ctx = profile_to_script_context(p)
    preview = (script_text or "").strip()[:1200]
    scene_titles = " | ".join((s.get("text") or "")[:80] for s in (scenes or [])[:8])

    fallback = {
        "title": (topic or "Historia")[:100],
        "alt_titles": [],
        "description": _fallback_description(topic, preview, p),
        "thumbnail": {
            "text": (topic or "Historia")[:28],
            "image_prompt": _fallback_thumb_prompt(p, topic),
            "layout": "subject_left_dark_right",
        },
    }

    if not api_key:
        fallback["alt_titles"] = _fallback_alt_titles(topic, p)
        return fallback

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
    except Exception:
        fallback["alt_titles"] = _fallback_alt_titles(topic, p)
        return fallback

    _nr = get_narrative_rules()
    _bpub = (_nr.get("channel_dark_confession_bible") or "").strip()
    _bpub = (_bpub[:3500] + "…") if len(_bpub) > 3500 else _bpub
    system = (
        "Sos estratega de contenidos YouTube (español). Devolvé SOLO un JSON con claves exactas:\n"
        '{ "title": str, "alt_titles": [str, str], "description": str, '
        '"thumbnail": { "text": str (3-5 palabras), "image_prompt": str (inglés o español, sin texto en imagen), '
        '"layout": str (sugerencia corta: ej. big_text_left, faceless_mood, split_tone) } }\n'
        "Canal: historias ficticias oscuras en primera persona, confesión incómoda, adictivas — NO títulos genéricos de clickbait, "
        "NO tono ‘IA amable’, NO miniaturas alegres de stock. "
        "Título: personal, oscuro, específico, curiosidad inmediata (estilo «Algo pasaba con…», «No debí…», «Nunca volví a…»). "
        "thumbnail.text: pocas palabras, tensión (ej. «LO VI», «CALLÓ TODO», «NO ERA ÉL»). "
        "image_prompt: escena sombría realista (móvil en la oscuridad, pasillo, puerta entreabierta, silueta sin rostro), "
        "coherente con el guion; sin texto legible en la imagen. "
        "Descripción: primera línea = gancho inquietante; 2 frases de tensión; CTA que invite a comentar la parte más incómoda; 3-6 hashtags. "
        "Respetá perfil (tone, hook_style, title_style, thumbnail_style, topics_to_focus). "
        "Prohibido plantilla genérica de IA."
        + (f"\n\n=== BIBLIA DEL CANAL (títulos / miniatura alineados al guion) ===\n{_bpub}" if _bpub else "")
    )
    if str(packaging_mode or "").strip().lower() in ("viral_gameplay", "viral", "high_impact"):
        system += (
            "\nMODO VIRAL GAMEPLAY: título ultra clicable (sin MAYÚSCULAS sostenidas enteras), "
            "1 emoción fuerte o pregunta imposible de ignorar. thumbnail.text: máximo 3 palabras, "
            "impacto dramático (ej. «NUNCA VOLVI», «ME MINTIERON»). Descripción: primera línea = gancho emocional; "
            "luego 2 frases de tensión; CTA que invite a comentar la parte más polémica; hashtags storytime/reddit."
        )
    ttf = p.get("topics_to_focus")
    if not isinstance(ttf, list):
        ttf = []
    user = json.dumps(
        {
            "tema": topic,
            "perfil_creador": script_ctx[:8000],
            "guion_extracto": preview,
            "beats_visuales": scene_titles[:2000],
            "title_style": str(p.get("title_style") or "").strip(),
            "thumbnail_style": str(p.get("thumbnail_style") or "").strip(),
            "topics_to_focus": [str(x).strip() for x in ttf[:24] if str(x).strip()],
        },
        ensure_ascii=False,
    )
    try:
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.75,
            max_tokens=900,
        )
        raw = (r.choices[0].message.content or "").strip()
        blob = raw[raw.find("{") : raw.rfind("}") + 1] if "{" in raw else "{}"
        data = json.loads(blob)
        if not isinstance(data, dict):
            raise ValueError("not dict")
        title = str(data.get("title") or "").strip()[:120]
        alts = data.get("alt_titles")
        if not isinstance(alts, list):
            alts = []
        alts_s = [str(x).strip()[:120] for x in alts[:2] if str(x).strip()]
        desc = str(data.get("description") or "").strip()
        th = data.get("thumbnail") if isinstance(data.get("thumbnail"), dict) else {}
        thumb = {
            "text": str(th.get("text") or "")[:40],
            "image_prompt": str(th.get("image_prompt") or "")[:500],
            "layout": str(th.get("layout") or "subject_left_dark_right")[:80],
        }
        if not title:
            raise ValueError("empty title")
        if len(alts_s) < 2:
            alts_s = (_fallback_alt_titles(topic, p) + alts_s)[:2]
        if not desc:
            desc = _fallback_description(topic, preview, p)
        if not thumb["text"]:
            thumb["text"] = (topic or "Historia")[:28]
        if not thumb["image_prompt"]:
            thumb["image_prompt"] = _fallback_thumb_prompt(p, topic)
        return {"title": title, "alt_titles": alts_s[:2], "description": desc, "thumbnail": thumb}
    except Exception:
        out = fallback
        out["alt_titles"] = _fallback_alt_titles(topic, p)
        return out


def _fallback_alt_titles(topic: str, prof: dict[str, Any]) -> list[str]:
    base = (topic or "algo que no encajaba").strip()[:72]
    return [
        f"No debí ignorarlo: {base}",
        f"Todavía no sé si fui cobarde o listo · {base}",
    ]


def _fallback_description(topic: str, preview: str, prof: dict[str, Any]) -> str:
    tone = str(prof.get("tone") or "intenso").strip()
    hook = (preview[:220] + "…") if len(preview) > 220 else preview
    return (
        f"{hook}\n\n"
        f"Historia narrada en tono {tone} sobre: {topic.strip()[:180]}.\n\n"
        "Dejá tu comentario: ¿qué harías vos?\n\n"
        "#storytime #redditstories #narración"
    )


def _fallback_thumb_prompt(prof: dict[str, Any], topic: str) -> str:
    look = str((prof.get("visual") or {}).get("look") or prof.get("style") or "dark cinematic").strip()
    return (
        f"YouTube thumbnail, {look}, night interior or phone glow in darkness, hallway tension, "
        f"faceless figure or hands only, no readable text, no logos, 16:9, uneasy mood, theme: {topic[:120]}"
    )
