"""Enriquece bloques de guion con intención visual (B-roll) alineada al perfil."""
from __future__ import annotations

import json
import os
from typing import Any

from .saas_creative_profile import merge_profile_disk, parse_llm_json_object, profile_to_edit_planner_context


def enrich_blocks_with_visual_intent(blocks: list[dict[str, Any]], profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    """
    Añade clave ``visual`` (1 frase: ambiente / acción sin rostros) por bloque.
    Sin API o si falla el modelo, usa heurística a partir del texto del bloque.
    """
    if not blocks:
        return []
    prof = merge_profile_disk(profile or {})
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _heuristic_visuals(blocks, prof)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
    except Exception:
        return _heuristic_visuals(blocks, prof)

    compact = [{"id": b.get("id"), "text": (b.get("text") or "")[:400]} for b in blocks]
    system = (
        "Sos director de fotografía para videos storytime / Reddit. Español.\n"
        "Devolvé SOLO JSON: {\"visuals\": [ {\"id\": \"...\", \"visual\": \"...\" }, ... ]}.\n"
        "La lista visuals debe tener EXACTAMENTE la misma longitud y mismos ids que los bloques entrantes.\n"
        "Cada \"visual\" es UNA frase corta de intención de plano B-roll: ambiente, objeto, manos genéricas, silueta lejana, clima, luz, textura. "
        "Sin caras reconocibles, sin personaje protagonista en primer plano, sin texto en imagen.\n"
        "Alineá mood con el perfil del creador (tone, style, visual.look, pacing)."
    )
    user = json.dumps(
        {"perfil": profile_to_edit_planner_context(prof), "bloques": compact},
        ensure_ascii=False,
    )
    try:
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.55,
            max_tokens=min(4000, 120 + 80 * len(blocks)),
        )
        raw = (r.choices[0].message.content or "").strip()
        data = parse_llm_json_object(raw) or {}
        arr = data.get("visuals") if isinstance(data, dict) else None
        if not isinstance(arr, list) or len(arr) != len(blocks):
            return _heuristic_visuals(blocks, prof)
        by_id = {str(x.get("id")): str(x.get("visual") or "").strip()[:220] for x in arr if isinstance(x, dict)}
        out: list[dict[str, Any]] = []
        for b in blocks:
            row = dict(b)
            vid = str(row.get("id") or "")
            v = by_id.get(vid) or _one_heuristic_visual(str(row.get("text") or ""), prof)
            row["visual"] = v
            out.append(row)
        return out
    except Exception:
        return _heuristic_visuals(blocks, prof)


def _one_heuristic_visual(text: str, prof: dict[str, Any]) -> str:
    mood = str(prof.get("tone") or prof.get("style") or "tensión").strip()[:40]
    snippet = (text or "").strip().replace("\n", " ")[:90]
    if snippet:
        return f"Ambiente cinematográfico ({mood}): {snippet} — sin rostros, plano amplio o detalle de objetos."
    return f"Plano ambiental abstracto, luz dramática, sensación {mood}."


def _heuristic_visuals(blocks: list[dict[str, Any]], prof: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in blocks:
        row = dict(b)
        row["visual"] = _one_heuristic_visual(str(row.get("text") or ""), prof)
        out.append(row)
    return out
