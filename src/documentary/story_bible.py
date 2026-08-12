"""Light story bible extraction for Flow consistency (no image generation)."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from src.config_loader import get_estilo_base


GLOBAL_STYLE_DEFAULT = (
    "Documentary cinematic realism, 16:9, naturalistic lighting, restrained color grade, "
    "photoreal still suitable for a serious YouTube business documentary. "
    "No cartoon, no meme text, no watermark, no logo soup."
)


def build_story_bible(
    topic: str,
    script: str,
    shots: list[dict[str, Any]],
    *,
    use_llm: bool = True,
) -> dict[str, Any]:
    bible = {
        "global_style": f"{GLOBAL_STYLE_DEFAULT} Style lock hint: {get_estilo_base()[:180]}",
        "characters": [],
        "locations": [],
        "important_objects": [],
        "timeline_periods": [],
    }
    if use_llm and (os.getenv("OPENAI_API_KEY") or "").strip():
        try:
            extracted = _llm_extract(topic, script)
            for k in ("characters", "locations", "important_objects", "timeline_periods"):
                if isinstance(extracted.get(k), list):
                    bible[k] = extracted[k]
            if extracted.get("global_style"):
                bible["global_style"] = str(extracted["global_style"]).strip()
        except Exception:
            bible = _heuristic_bible(topic, script, shots, bible)
    else:
        bible = _heuristic_bible(topic, script, shots, bible)

    _attach_shot_appearances(bible, shots)
    return bible


def _llm_extract(topic: str, script: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    system = (
        "Extract a LIGHT story bible for a factual business documentary. "
        "Return ONLY JSON with keys: global_style, characters, locations, important_objects, timeline_periods. "
        "Each entity: id (CHAR_001/LOC_001/OBJ_001/TIME_001), name, description, visual_description. "
        "Do NOT invent people or places not supported by the script. "
        "Omit characters if the story is mostly institutions/products."
    )
    user = json.dumps({"topic": topic, "script": script[:12000]}, ensure_ascii=False)
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = (r.choices[0].message.content or "{}").strip()
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def _heuristic_bible(topic: str, script: str, shots: list[dict], base: dict) -> dict:
    # Proper nouns heuristic (very light)
    names = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", script)
    skip = {
        "The", "This", "That", "When", "After", "Before", "In", "On", "By", "And", "But",
        "January", "February", "March", "April", "May", "June", "July", "August",
        "September", "October", "November", "December", "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday", "Sunday",
    }
    counts: dict[str, int] = {}
    for n in names:
        if n.split()[0] in skip:
            continue
        counts[n] = counts.get(n, 0) + 1
    top = sorted(counts.items(), key=lambda x: -x[1])[:5]
    chars = []
    for i, (name, _) in enumerate(top, start=1):
        chars.append(
            {
                "id": f"CHAR_{i:03d}",
                "name": name,
                "description": f"Recurring figure related to: {topic}",
                "visual_description": f"Realistic adult, period-appropriate wardrobe, documentary still of {name}",
                "appears_in_shots": [],
            }
        )
    locs = [
        {
            "id": "LOC_001",
            "name": "Corporate office",
            "description": "Generic corporate interior for business scenes",
            "visual_description": "Open-plan office, glass walls, cool daylight, documentary realism",
            "appears_in_shots": [],
        },
        {
            "id": "LOC_002",
            "name": "Press / public stage",
            "description": "Public-facing corporate moment",
            "visual_description": "Conference stage or media scrum, microphones, shallow depth of field",
            "appears_in_shots": [],
        },
    ]
    objs = [
        {
            "id": "OBJ_001",
            "name": "Financial document",
            "description": "Balance sheet / pitch deck / report",
            "visual_description": "Printed financial report or laptop screen with charts, no readable logos",
            "appears_in_shots": [],
        }
    ]
    years = sorted(set(re.findall(r"\b(19\d{2}|20\d{2})\b", script)))
    periods = [
        {
            "id": f"TIME_{i:03d}",
            "name": y,
            "description": f"Period around {y}",
            "visual_description": f"Wardrobe, tech and interiors consistent with {y}",
            "appears_in_shots": [],
        }
        for i, y in enumerate(years[:6], start=1)
    ]
    base["characters"] = chars
    base["locations"] = locs
    base["important_objects"] = objs
    base["timeline_periods"] = periods
    return base


def _attach_shot_appearances(bible: dict, shots: list[dict]) -> None:
    for shot in shots:
        refs = shot.get("references") or []
        num = int(shot.get("number") or 0)
        for group in ("characters", "locations", "important_objects", "timeline_periods"):
            for ent in bible.get(group) or []:
                if ent.get("id") in refs:
                    arr = list(ent.get("appears_in_shots") or [])
                    if num and num not in arr:
                        arr.append(num)
                    ent["appears_in_shots"] = arr
