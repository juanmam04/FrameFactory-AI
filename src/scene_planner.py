"""Planificador mínimo de escenas para SaaS MVP."""
from __future__ import annotations

import re


def plan_scenes_reddit_segments(script_text: str, words_per_segment: int = 12) -> list[dict]:
    """
    Divide el guion en segmentos cortos (~2–4 s de TTS) por conteo de palabras,
    pensado para historias estilo Reddit con cambios visuales frecuentes.
    """
    raw = (script_text or "").strip()
    if not raw:
        return []
    words = raw.split()
    wps = max(6, min(28, int(words_per_segment)))
    blocks: list[dict] = []
    i = 0
    seg = 0
    while i < len(words):
        chunk = words[i : i + wps]
        txt = " ".join(chunk).strip()
        if txt:
            seg += 1
            blocks.append({"id": f"scene_{seg:04d}", "text": txt})
        i += wps
    return blocks


def plan_scenes(script_text: str) -> list[dict]:
    """
    Divide el guion en frases y devuelve bloques mínimos:
    [{"id": "...", "text": "..."}]
    """
    raw = (script_text or "").strip()
    if not raw:
        return []

    parts = re.split(r"(?<=[.!?])\s+", raw)
    blocks: list[dict] = []
    for i, part in enumerate(parts, start=1):
        txt = (part or "").strip()
        if not txt:
            continue
        blocks.append(
            {
                "id": f"scene_{i:04d}",
                "text": txt,
            }
        )
    return blocks
