"""Daily story ideas for Documentary channel (LLM, no web research)."""
from __future__ import annotations

import json
import os
from typing import Any

from src.saas_creative_profile import merge_profile_disk, parse_llm_json_object


def _history_block(prior_videos: list[dict[str, Any]]) -> str:
    lines = []
    for v in prior_videos[-80:]:
        title = str(v.get("title") or v.get("topic") or "").strip()
        topic = str(v.get("topic") or "").strip()
        idea = v.get("idea") if isinstance(v.get("idea"), dict) else {}
        company = str(idea.get("primary_entity") or idea.get("content_pillar") or "").strip()
        lines.append(
            f"- id={v.get('id')} title={title} topic={topic} entity={company} "
            f"pillar={idea.get('content_pillar','')}"
        )
    return "\n".join(lines) if lines else "(none yet)"


def generate_story_ideas(
    profile: dict[str, Any] | None,
    *,
    prior_videos: list[dict[str, Any]] | None = None,
    memory_summary: str = "",
    count: int = 5,
    use_llm: bool = True,
) -> list[dict[str, Any]]:
    """Return list of idea dicts. Offline → deterministic mocks."""
    p = merge_profile_disk(profile)
    prior = list(prior_videos or [])
    if not use_llm or not (os.getenv("OPENAI_API_KEY") or "").strip():
        return _mock_ideas(p, prior, count)

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    ig = p.get("idea_generation") if isinstance(p.get("idea_generation"), dict) else {}
    ch = p.get("channel") if isinstance(p.get("channel"), dict) else {}
    system = (
        "You are the editorial brain for a YouTube channel of English cinematic business documentaries. "
        "Return ONLY JSON: {\"ideas\": [ ... ]}. Each idea object MUST have: "
        "title_concept, story, hook, why_it_works, content_pillar, visual_potential "
        "(High|Medium|Low), research_risk (Easy|Medium|Hard), primary_entity "
        "(main company or person name for de-duplication). "
        "Do NOT propose the same company, person, or core event already listed in prior videos. "
        "No fabricated ultra-specific dollar figures in titles unless widely known; keep concepts honest. "
        f"Produce exactly {int(count)} ideas."
    )
    user = {
        "channel": ch.get("name"),
        "niche": p.get("niche"),
        "pillars": p.get("topics_to_focus") or ch.get("content_pillars"),
        "audience": p.get("audience"),
        "tone": p.get("tone"),
        "title_style": p.get("title_style"),
        "idea_brief": ig.get("brief"),
        "angles_to_favor": ig.get("angles_to_favor"),
        "angles_to_avoid": ig.get("angles_to_avoid"),
        "topics_to_avoid": p.get("topics_to_avoid"),
        "session_memory": (memory_summary or "")[:4000],
        "prior_videos": _history_block(prior),
    }
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.85,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    )
    raw = (r.choices[0].message.content or "{}").strip()
    parsed = parse_llm_json_object(raw) or {}
    ideas = parsed.get("ideas") if isinstance(parsed, dict) else None
    if not isinstance(ideas, list) or not ideas:
        return _mock_ideas(p, prior, count)
    out = []
    for it in ideas[:count]:
        if not isinstance(it, dict):
            continue
        out.append(_normalize_idea(it))
    while len(out) < count:
        out.extend(_mock_ideas(p, prior, count - len(out)))
        break
    return out[:count]


def _normalize_idea(it: dict[str, Any]) -> dict[str, Any]:
    return {
        "title_concept": str(it.get("title_concept") or it.get("title") or "Untitled story").strip(),
        "story": str(it.get("story") or "").strip(),
        "hook": str(it.get("hook") or "").strip(),
        "why_it_works": str(it.get("why_it_works") or "").strip(),
        "content_pillar": str(it.get("content_pillar") or "").strip(),
        "visual_potential": str(it.get("visual_potential") or "Medium").strip(),
        "research_risk": str(it.get("research_risk") or "Medium").strip(),
        "primary_entity": str(it.get("primary_entity") or "").strip(),
    }


def _mock_ideas(profile: dict[str, Any], prior: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    used = set()
    for v in prior:
        idea = v.get("idea") if isinstance(v.get("idea"), dict) else {}
        for key in ("primary_entity", "topic", "title"):
            val = str(idea.get("primary_entity") or v.get(key) or "").strip().lower()
            if val:
                used.add(val)
        used.add(str(v.get("topic") or "").strip().lower())

    pool = [
        {
            "title_concept": "THE $47 BILLION COMPANY THAT ALMOST COLLAPSED OVERNIGHT",
            "story": (
                "WeWork's rise from coworking startup to one of the world's most valuable private companies "
                "— and the IPO filing that changed everything."
            ),
            "hook": "In January 2019, WeWork looked unstoppable. By fall, the IPO was dead.",
            "why_it_works": "Famous company + absurd valuation + dramatic collapse.",
            "content_pillar": "Rise & Fall",
            "visual_potential": "High",
            "research_risk": "Easy",
            "primary_entity": "WeWork",
        },
        {
            "title_concept": "THE THERANOS MIRAGE",
            "story": "How a blood-testing startup sold a revolutionary machine that never worked — and fooled Silicon Valley.",
            "hook": "She promised a drop of blood could replace a laboratory.",
            "why_it_works": "Fraud + charisma + media theater.",
            "content_pillar": "Fraud & Scams",
            "visual_potential": "High",
            "research_risk": "Easy",
            "primary_entity": "Theranos",
        },
        {
            "title_concept": "WHEN BOEING BET THE COMPANY",
            "story": "The 737 MAX crisis: software, deadlines, and a trust collapse that grounded a global fleet.",
            "hook": "Two crashes. One jet. An entire industry grounded.",
            "why_it_works": "Corporate disaster with human stakes.",
            "content_pillar": "Corporate Disasters",
            "visual_potential": "High",
            "research_risk": "Medium",
            "primary_entity": "Boeing",
        },
        {
            "title_concept": "THE SODA WARS THAT REWROTE MARKETING",
            "story": "Coke vs Pepsi — decades of rivalry that turned soft drinks into cultural warfare.",
            "hook": "It started as sugar water. It became a cold war.",
            "why_it_works": "Business war everyone recognizes.",
            "content_pillar": "Business Wars",
            "visual_potential": "Medium",
            "research_risk": "Easy",
            "primary_entity": "Coca-Cola vs Pepsi",
        },
        {
            "title_concept": "THE MAN WHO SHORTENED THE INTERNET BUBBLE",
            "story": "How Michael Burry saw the housing collapse coming — and forced Wall Street to pay attention.",
            "hook": "He wasn't predicting rain. He was buying umbrellas for a flood.",
            "why_it_works": "Founder/outsider vs system + known drama.",
            "content_pillar": "Founder Stories",
            "visual_potential": "Medium",
            "research_risk": "Medium",
            "primary_entity": "Michael Burry",
        },
        {
            "title_concept": "ENRON: THE EMPIRE BUILT ON PAPER",
            "story": "Mark-to-market dreams, offshore entities, and the fastest fall of an American energy giant.",
            "hook": "On paper, Enron was worth tens of billions. On the ground, the numbers were fiction.",
            "why_it_works": "Archetypal corporate fraud.",
            "content_pillar": "Fraud & Scams",
            "visual_potential": "High",
            "research_risk": "Easy",
            "primary_entity": "Enron",
        },
        {
            "title_concept": "BLOCKBUSTER'S LAST CHANCE",
            "story": "How a video rental monopoly watched Netflix rise — and said no to the future.",
            "hook": "They owned the Friday night. Then they owned nothing.",
            "why_it_works": "Familiar brand + avoidable disaster.",
            "content_pillar": "Billion-Dollar Mistakes",
            "visual_potential": "High",
            "research_risk": "Easy",
            "primary_entity": "Blockbuster",
        },
        {
            "title_concept": "THE RISE OF COSTCO'S QUIET EMPIRE",
            "story": "A warehouse club that rejected typical retail tricks — and built a membership fortress.",
            "hook": "They don't try to trick you at checkout. That's the trick.",
            "why_it_works": "Unexpected success / counterintuitive strategy.",
            "content_pillar": "Unexpected Success Stories",
            "visual_potential": "Medium",
            "research_risk": "Medium",
            "primary_entity": "Costco",
        },
    ]
    out = []
    for idea in pool:
        ent = idea["primary_entity"].lower()
        if any(ent in u or u in ent for u in used if u):
            continue
        out.append(idea)
        if len(out) >= count:
            break
    # pad if needed
    i = 0
    while len(out) < count:
        out.append(
            {
                "title_concept": f"MOCK STORY {i+1}: A COMPANY AT THE EDGE",
                "story": "Placeholder idea for offline testing — replace with a real true story.",
                "hook": "Something extraordinary was about to go public.",
                "why_it_works": "Offline mock only.",
                "content_pillar": "Rise & Fall",
                "visual_potential": "Medium",
                "research_risk": "Easy",
                "primary_entity": f"MockCo-{i+1}",
            }
        )
        i += 1
    return out[:count]
