"""AI-assisted research brief for Documentary (model knowledge → editable notes).

Not a live web crawler. Produces structured facts + unknowns + suggested sources
for the user to verify before script generation.
"""
from __future__ import annotations

import json
import os
from typing import Any

from src.documentary.editorial import DOCUMENTARY_INVARIANTS, STORY_CRAFT_BIBLE
from src.documentary.openai_key import require_openai_api_key
from src.documentary.project import append_log, project_dir, save_project
from src.saas_creative_profile import parse_llm_json_object


def generate_research_brief(project: dict[str, Any], *, use_llm: bool = True) -> dict[str, Any]:
    """Fill project research_notes + sources from an AI research pass. Does not write the script."""
    topic = str(project.get("topic") or "").strip()
    if not topic:
        raise ValueError("Choose a story before generating research.")

    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    title = str(project.get("title") or idea.get("title_concept") or topic).strip()

    if not use_llm:
        notes, sources = _mock_research(topic, title, idea)
    else:
        require_openai_api_key("Research generation")
        notes, sources = _llm_research(topic, title, idea)

    project["research_notes"] = notes
    project["sources"] = sources
    project["research_skipped"] = False
    project["research_ai_generated"] = True
    project["ui_step"] = "research"
    save_project(project)

    root = project_dir(str(project["id"]))
    (root / "script" / "research_notes.md").write_text(
        f"# Research — {title}\n\n## Topic\n{topic}\n\n## Notes\n{notes}\n\n## Sources\n"
        + "\n".join(f"- {s}" for s in sources),
        encoding="utf-8",
    )
    (root / "script" / "research_meta.json").write_text(
        json.dumps(
            {
                "ai_generated": True,
                "source": "openai_model_knowledge",
                "warning": "Verify facts before approving the script. This is not live web search.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    append_log(str(project["id"]), f"research AI generated chars={len(notes)} sources={len(sources)}")
    return project


def _llm_research(topic: str, title: str, idea: dict[str, Any]) -> tuple[str, list[str]]:
    from openai import OpenAI

    api_key = require_openai_api_key("Research generation")
    client = OpenAI(api_key=api_key)
    system = f"""You are the research chief for the world's best TRUE company-story channel.
{DOCUMENTARY_INVARIANTS}

{STORY_CRAFT_BIBLE}

Your job is RESEARCH + STORY AMMUNITION — not the final narration.

Return ONLY JSON:
{{
  "story_engine": "one sentence: what makes THIS story inevitable / fascinating",
  "cold_open_candidates": ["2–4 concrete true moments that could open the film"],
  "protagonist_desire": "what the main character(s) chased — documented",
  "forces_of_pressure": ["market, rivals, money, belief, regulation — grounded"],
  "timeline": [{{"when": "...", "what": "...", "why_it_matters": "..."}}],
  "key_people": [{{"name": "...", "role": "...", "desire_or_pressure": "..."}}],
  "verified_or_well_known_facts": ["..."],
  "numbers_and_stakes": ["... — mark UNKNOWN if unsure"],
  "sensory_or_concrete_details": ["places, products, headlines, filings, rooms, launches — real"],
  "turning_points": ["..."],
  "true_ironies": ["promise vs reality / timing / contradiction — factual"],
  "contradictions_or_hooks": ["great cold-open angles grounded in facts"],
  "unknowns": ["things the script must NOT invent"],
  "suggested_sources": ["well-known publication / filing / book / documentary name — do NOT invent fake URLs"],
  "research_notes_markdown": "a dense markdown brief optimized for a gripping ~11–15 min / ~2000-word true story"
}}

Rules:
- Prefer well-established public knowledge about the company/people.
- If unsure of a date, dollar figure, or quote: write UNKNOWN — do not guess.
- Do not invent dialogue or private thoughts.
- Harvest MAXIMUM story ammunition: desire, pressure, irony, concrete moments, escalation.
- research_notes_markdown must be EVENT-DENSE: founding antecedents, product/model, named investors,
  capital amounts, valuation milestones, public filings, governance controversies, leadership exits,
  rescues/restructuring, later outcomes (SPAC/bankruptcy/recovery) when known — mark UNKNOWN if not.
- Ban MBA themes ("ambition vs pragmatism", "lessons for entrepreneurs") — facts and events only.
- Flag best cold open. Prefer names, dates, amounts, places, documents over adjectives.
"""
    user = json.dumps(
        {
            "working_title": title,
            "topic": topic,
            "idea": {
                "story": idea.get("story"),
                "hook": idea.get("hook"),
                "content_pillar": idea.get("content_pillar"),
                "primary_entity": idea.get("primary_entity"),
            },
        },
        ensure_ascii=False,
    )
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.25,
        max_tokens=4500,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": user
                + "\n\nHARD REQUIREMENT: research_notes_markdown must include a dense ## Timeline "
                "with at least 12 concrete dated events when publicly known (founding antecedents, "
                "capital raises, SoftBank/Masayoshi Son if relevant, valuation peaks, S-1/IPO, "
                "governance controversies, leadership exits, rescues, later public outcomes). "
                "Use UNKNOWN rather than invent. No moral essays.",
            },
        ],
    )
    raw = (r.choices[0].message.content or "{}").strip()
    data = parse_llm_json_object(raw) or {}
    notes = str(data.get("research_notes_markdown") or "").strip()
    if not notes:
        notes = _format_notes_from_parts(data, topic)
    sources = []
    for s in data.get("suggested_sources") or []:
        if isinstance(s, str) and s.strip():
            sources.append(s.strip())
    engine = str(data.get("story_engine") or "").strip()
    colds = data.get("cold_open_candidates") or []
    prepend_bits = []
    if engine and "story engine" not in notes.lower():
        prepend_bits.append(f"## Story engine\n{engine}")
    if colds and "cold-open" not in notes.lower() and "cold open" not in notes.lower():
        lines = ["## Cold-open candidates"]
        for c in colds:
            lines.append(f"- {c}")
        prepend_bits.append("\n".join(lines))
    if prepend_bits:
        notes = "\n\n".join(prepend_bits) + "\n\n" + notes
    header = (
        "AI RESEARCH BRIEF (model knowledge — verify before publishing)\n"
        "This is NOT live web search. Marked UNKNOWN items must stay unknown in the script.\n\n"
    )
    if not notes.startswith("AI RESEARCH"):
        notes = header + notes
    if not sources:
        sources = [
            "Verify with primary filings / reputable longform reporting before publish",
        ]
    return notes, sources


def _format_notes_from_parts(data: dict[str, Any], topic: str) -> str:
    lines = [f"# Research brief — {topic}", ""]
    for key, label in [
        ("story_engine", "Story engine"),
        ("cold_open_candidates", "Cold-open candidates"),
        ("protagonist_desire", "Protagonist desire"),
        ("forces_of_pressure", "Forces of pressure"),
        ("timeline", "Timeline"),
        ("key_people", "Key people"),
        ("verified_or_well_known_facts", "Facts"),
        ("numbers_and_stakes", "Numbers & stakes"),
        ("sensory_or_concrete_details", "Concrete details"),
        ("turning_points", "Turning points"),
        ("true_ironies", "True ironies"),
        ("contradictions_or_hooks", "Hooks"),
        ("unknowns", "Unknowns — do not invent"),
    ]:
        val = data.get(key)
        if not val:
            continue
        lines.append(f"## {label}")
        if isinstance(val, list):
            for item in val:
                lines.append(f"- {json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else item}")
        else:
            lines.append(str(val))
        lines.append("")
    return "\n".join(lines).strip()


def _mock_research(topic: str, title: str, idea: dict[str, Any]) -> tuple[str, list[str]]:
    entity = str(idea.get("primary_entity") or topic)[:80]
    notes = (
        f"AI RESEARCH BRIEF (OFFLINE MOCK — NOT FOR PUBLICATION)\n\n"
        f"## Story engine\nA gripping true arc around {entity}.\n\n"
        f"## Topic\n{topic}\n\n"
        f"## Facts (placeholder)\n"
        f"- Replace this mock with Generate research (AI) once OPENAI_API_KEY is set.\n"
        f"- UNKNOWN: specific dollar figures — do not invent.\n"
    )
    sources = ["Offline mock — run AI research with a real API key"]
    return notes, sources
