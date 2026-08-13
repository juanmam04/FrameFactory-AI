"""Story architecture pass — design the gripping true story BEFORE writing narration.

Nonfiction only: architecture organizes research; it must not invent facts.
"""
from __future__ import annotations

import json
import os
from typing import Any

from src.documentary.editorial import DOCUMENTARY_INVARIANTS, STORY_CRAFT_BIBLE
from src.documentary.openai_key import require_openai_api_key
from src.documentary.project import append_log, project_dir, save_project
from src.saas_creative_profile import parse_llm_json_object


def build_story_architecture(project: dict[str, Any], *, use_llm: bool = True) -> dict[str, Any]:
    """Create/save story architecture from topic + research. Does not write the script."""
    topic = str(project.get("topic") or "").strip()
    if not topic:
        raise ValueError("Choose a story before building architecture.")

    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    title = str(project.get("title") or idea.get("title_concept") or topic).strip()
    notes = str(project.get("research_notes") or "").strip()
    sources = project.get("sources") or []

    if not use_llm:
        arch = _mock_architecture(topic, title, idea, notes)
    else:
        require_openai_api_key("Story architecture")
        arch = _llm_architecture(topic, title, idea, notes, sources)

    project["story_architecture"] = arch
    save_project(project)

    root = project_dir(str(project["id"]))
    (root / "script" / "story_architecture.json").write_text(
        json.dumps(arch, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md = architecture_to_markdown(arch)
    (root / "script" / "story_architecture.md").write_text(md, encoding="utf-8")
    append_log(str(project["id"]), "story architecture built")
    return arch


def architecture_to_markdown(arch: dict[str, Any]) -> str:
    lines = [
        "# Story architecture",
        "",
        f"## Story engine\n{arch.get('story_engine') or ''}",
        "",
        f"## Cold open\n{arch.get('cold_open') or ''}",
        "",
        f"## Emotional spine\n{arch.get('emotional_spine') or ''}",
        "",
        "## Characters (desire / pressure)",
    ]
    for c in arch.get("characters") or []:
        if isinstance(c, dict):
            lines.append(
                f"- {c.get('name', '?')}: wants {c.get('desire', '?')}; "
                f"pressure: {c.get('pressure', '?')}"
            )
        else:
            lines.append(f"- {c}")
    lines.extend(["", "## Beat sheet (true events only)"])
    for i, b in enumerate(arch.get("beat_sheet") or [], 1):
        if isinstance(b, dict):
            lines.append(
                f"{i}. [{b.get('function', 'beat')}] {b.get('moment', '')} "
                f"— curiosity: {b.get('curiosity_payoff', '')}"
            )
        else:
            lines.append(f"{i}. {b}")
    lines.extend(
        [
            "",
            "## Withholds / reveals",
            *(f"- {x}" for x in (arch.get("withholds_and_reveals") or [])),
            "",
            "## Must-include specifics",
            *(f"- {x}" for x in (arch.get("must_include_specifics") or [])),
            "",
            "## Do not invent",
            *(f"- {x}" for x in (arch.get("do_not_invent") or [])),
            "",
            f"## Ending image\n{arch.get('ending_image') or ''}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def architecture_prompt_block(arch: dict[str, Any] | None) -> str:
    if not isinstance(arch, dict) or not arch:
        return ""
    return (
        "STORY ARCHITECTURE (follow this structure; do not invent beyond research):\n"
        + architecture_to_markdown(arch)
    )


def _llm_architecture(
    topic: str,
    title: str,
    idea: dict[str, Any],
    notes: str,
    sources: list[Any],
) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=require_openai_api_key("Story architecture"))
    system = f"""You are the lead story architect for world-class TRUE company documentaries.
{DOCUMENTARY_INVARIANTS}

{STORY_CRAFT_BIBLE}

Your job is ARCHITECTURE ONLY — not the final narration.
Design the most gripping true-story structure possible from the research.
If research is thin, keep beats fewer and mark gaps in do_not_invent.

Return ONLY JSON:
{{
  "story_engine": "one sentence",
  "cold_open": "the single best true opening moment (concrete)",
  "emotional_spine": "what the audience feels chasing beat to beat",
  "characters": [{{"name": "...", "desire": "...", "pressure": "..."}}],
  "beat_sheet": [
    {{"function": "hook|setup|desire|progress|obstacle|escalation|turn|consequence|resolution",
      "moment": "true event / situation",
      "curiosity_payoff": "what question this raises or answers"}}
  ],
  "withholds_and_reveals": ["plant X early / reveal later — grounded in facts"],
  "must_include_specifics": ["names, numbers, filings, headlines from research — no inventing"],
  "do_not_invent": ["UNKNOWN or thin areas"],
  "ending_image": "haunting true consequence / image — not a lesson"
}}
"""
    user = json.dumps(
        {
            "working_title": title,
            "topic": topic,
            "idea": {
                "story": idea.get("story"),
                "hook": idea.get("hook"),
                "primary_entity": idea.get("primary_entity"),
            },
            "research_notes": notes or "(empty)",
            "sources": sources,
        },
        ensure_ascii=False,
    )
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.55,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = (r.choices[0].message.content or "{}").strip()
    data = parse_llm_json_object(raw) or {}
    if not str(data.get("story_engine") or "").strip():
        data["story_engine"] = f"The true story of {topic}"
    return data


def _mock_architecture(
    topic: str,
    title: str,
    idea: dict[str, Any],
    notes: str,
) -> dict[str, Any]:
    entity = str(idea.get("primary_entity") or title or topic)[:80]
    return {
        "story_engine": f"What happens when {entity} pushes a dream past reality.",
        "cold_open": f"Open on the highest-stakes public moment around {entity}, then rewind.",
        "emotional_spine": "Awe → belief → unease → rupture → aftermath.",
        "characters": [
            {
                "name": entity,
                "desire": str(idea.get("hook") or "to win at impossible scale")[:120],
                "pressure": "markets, money, and belief",
            }
        ],
        "beat_sheet": [
            {"function": "hook", "moment": "Cold-open rupture", "curiosity_payoff": "How did we get here?"},
            {"function": "setup", "moment": "Origin desire", "curiosity_payoff": "What did they want?"},
            {"function": "escalation", "moment": "Bigger bets", "curiosity_payoff": "What could go wrong?"},
            {"function": "turn", "moment": "The break", "curiosity_payoff": "What does it cost?"},
            {"function": "resolution", "moment": "Aftermath", "curiosity_payoff": "What remains?"},
        ],
        "withholds_and_reveals": ["Plant the central contradiction early; explain late."],
        "must_include_specifics": [
            line.strip("- ").strip()
            for line in (notes or "").splitlines()
            if line.strip().startswith("-")
        ][:8]
        or ["Use only research specifics when available"],
        "do_not_invent": ["Any date, dollar figure, or quote marked UNKNOWN"],
        "ending_image": "Leave on consequence, not a moral.",
    }
