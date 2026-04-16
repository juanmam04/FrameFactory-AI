"""Planificador mínimo de escenas para SaaS MVP."""
from __future__ import annotations

import re


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
