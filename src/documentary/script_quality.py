"""Heuristic + optional LLM quality review for Documentary scripts."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from src.documentary.openai_key import openai_api_key, require_openai_api_key
from src.saas_creative_profile import parse_llm_json_object

BANNED_OR_DISCOURAGED = (
    "meteoric rise",
    "staggering revelation",
    "shocking disclosure",
    "the excitement was palpable",
    "excitement was palpable",
    "the stark reality",
    "haunting image",
    "shattered ambitions",
    "indelible mark",
    "cautionary tale",
    "unchecked ambition",
    "delicate balance",
    "broader implications",
    "ever-evolving",
    "serves as a reminder",
    "lessons learned",
    "in the years to come",
    "the world watched",
    "navigate its path forward",
    "balancing ambition with pragmatism",
    "balance ambition with pragmatism",
    "extended far beyond its own walls",
    "underscored the necessity",
)

_GENERIC_CORPORATE = (
    "strategic marketing",
    "charismatic leadership",
    "cultural shift",
    "flexible work environments",
    "rapid expansion",
    "subsequent collapse",
    "entrepreneurs can learn",
    "in today's fast-paced",
    "the importance of",
    "ultimately reminds us",
    "a powerful reminder",
)


_ESSAY_TAIL_MARKERS = (
    "underscores the",
    "underscored the",
    "serves as a",
    "broader trends",
    "entrepreneurial landscape",
    "startup ecosystem",
    "startup world",
    "in conclusion",
    "lessons learned",
    "ambition must be balanced",
    "balancing ambition",
    "unchecked ambition",
    "resonates across",
    "modern entrepreneurship",
    "sound business principles",
    "implications of its story",
    "extended beyond its own walls",
    "as the world adapts",
    "the narrative of",
    "reflects the broader",
    "illustrates the",
    "intricate dance",
    "reevaluation of investment",
    "cautionary tale",
    "the importance of",
    "volatile nature",
    "fast-paced world",
    "stark reminder",
    "fortunes can change",
)


_ABRUPT_TAILS = (
    "uncertain future",
    "remains to be seen",
    "time will tell",
    "highlighted the",
    "inherent in its business model",
    "raising questions about",
    "the future of",
    "what would come next",
    "only time",
    "prompting a reevaluation",
    "the tide began to turn",
    "the dust settled",
)


def ending_is_abrupt(script: str, ending_state: str = "") -> bool:
    """True when the draft stops mid-aftermath instead of landing ending_state."""
    text = (script or "").strip()
    if not text:
        return True
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    last = (paras[-1] if paras else text).lower()
    if last.rstrip().endswith("?"):
        return True
    state = (ending_state or "").strip()
    tail = " ".join(paras[-3:] if len(paras) >= 3 else paras).lower()
    if state:
        years = re.findall(r"\b(?:19|20)\d{2}\b", state)
        money = re.findall(r"\$[\d,.]+|\b\d+(?:\.\d+)?\s*(?:billion|million)\b", state.lower())
        keys = re.findall(r"\b(spac|merger|bankruptcy|acquired|listed|public|bailed|rescue)\b", state.lower())
        hits = 0
        for y in years:
            if re.search(rf"\b{re.escape(y)}\b", tail):
                hits += 1
        for m in money:
            compact = m.replace(" ", "").replace(",", "")
            if m in tail or compact in tail.replace(" ", "").replace(",", ""):
                hits += 1
        for k in keys:
            if re.search(rf"\b{re.escape(k)}\b", tail):
                hits += 1
        if hits >= 1:
            return False
        if years or money or keys:
            return True
    return any(m in last for m in _ABRUPT_TAILS)


def close_script_ending(
    script: str,
    *,
    ending_state: str,
    hook: str = "",
    research_notes: str = "",
) -> str:
    """Append 1–2 closing paragraphs from ending_state. Does not rewrite the body."""
    text = (script or "").strip()
    state = (ending_state or "").strip()
    if not text or not state or not ending_is_abrupt(text, state):
        return text
    fallback = (
        f"What happened next was already on the record: {state.rstrip('.')}. "
        "That is where this story landed."
    )
    try:
        require_openai_api_key("Script ending")
        from openai import OpenAI

        client = OpenAI(api_key=openai_api_key())
        prompt = f"""The narration below STOPS too early. Write ONLY 1-2 final paragraphs to append.

Rules:
- Use ONLY these facts. Do not invent.
- Paragraph 1: ENDING STATE as what happened next (year, number, names).
- Paragraph 2: one image that answers the cold open. No lessons. No "in conclusion".
- Third person. Spoken English. Return ONLY the new paragraphs — not the whole script.

ENDING STATE:
{state}

COLD OPEN / HOOK:
{(hook or "")[:500]}

RESEARCH (optional extra facts, do not invent beyond this):
{(research_notes or "")[-2500:]}

CURRENT LAST PARAGRAPHS:
{" ".join(text.split()[-180:])}
"""
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.35,
            max_tokens=420,
            messages=[
                {
                    "role": "system",
                    "content": "You close factual English documentaries. Events only. No morals.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        add = (r.choices[0].message.content or "").strip()
        add = re.sub(r"^```(?:\w+)?\s*|\s*```$", "", add).strip()
        if add and len(add.split()) >= 20:
            low = add.lower()
            if any(m in low for m in ("in conclusion", "lesson", "underscores", "entrepreneurs can")):
                add = fallback
            return text + "\n\n" + add
    except Exception:
        pass
    return text + "\n\n" + fallback


def strip_essay_tail(script: str) -> str:
    """Drop trailing moral/essay paragraphs that pad after the story has ended.

    Never remove more than ~25% of the draft — better a slightly soft ending than a stub.
    """
    text = (script or "").strip()
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) < 6:
        return text
    original_wc = len(text.split())
    cut = len(paras)
    # Only inspect the last ~20% of paragraphs
    min_keep = max(5, int(len(paras) * 0.8))
    while cut > min_keep:
        low = paras[cut - 1].lower()
        if any(m in low for m in _ESSAY_TAIL_MARKERS):
            cut -= 1
            continue
        break
    out = "\n\n".join(paras[:cut]).strip()
    if len(out.split()) < int(original_wc * 0.75):
        return text
    return out


def heuristic_script_quality(script: str, *, target_words: int = 2000) -> dict[str, Any]:
    text = (script or "").strip()
    low = text.lower()
    words = text.split()
    wc = len(words)
    problems: list[str] = []
    scores: dict[str, float] = {}

    # banned/discouraged density
    banned_hits = [p for p in BANNED_OR_DISCOURAGED if p in low]
    generic_hits = [p for p in _GENERIC_CORPORATE if p in low]
    scores["filler_language"] = max(0.0, 1.0 - 0.15 * len(banned_hits) - 0.1 * len(generic_hits))
    if len(banned_hits) + len(generic_hits) >= 4:
        problems.append(
            "Too much generic corporate / AI filler language ("
            + ", ".join((banned_hits + generic_hits)[:6])
            + ")."
        )

    # fact-ish density: capitals names, years, $ amounts
    years = len(re.findall(r"\b(?:19|20)\d{2}\b", text))
    money = len(re.findall(r"\$[\d,.]+|\b\d+(?:\.\d+)?\s*(?:billion|million|thousand)\b", low))
    proper = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text))
    scores["specificity"] = min(1.0, (years + money + proper / 3) / 12)
    if scores["specificity"] < 0.35 and wc > 600:
        problems.append(
            "Low fact density — few concrete years, amounts, or named people/places. "
            "Paragraphs may be interchangeable across startups."
        )

    # repetition: similar paragraph starts / high Jaccard between paragraphs
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    rep = 0
    for i in range(len(paras)):
        wi = set(re.findall(r"[a-z0-9']+", paras[i].lower()))
        if len(wi) < 8:
            continue
        for j in range(i + 1, len(paras)):
            wj = set(re.findall(r"[a-z0-9']+", paras[j].lower()))
            if len(wj) < 8:
                continue
            inter = len(wi & wj)
            union = len(wi | wj) or 1
            if inter / union >= 0.55:
                rep += 1
    scores["repetition"] = max(0.0, 1.0 - 0.2 * rep)
    if rep >= 2:
        problems.append("Repetitive paragraphs — same conclusion/moral restated.")

    # moralizing ending
    tail = " ".join(words[-int(max(40, wc * 0.12)) :]) if wc else ""
    tail_l = tail.lower()
    if any(
        x in tail_l
        for x in (
            "lesson",
            "entrepreneurs",
            "reminder",
            "ambition with pragmatism",
            "in the years to come",
            "navigate",
        )
    ):
        problems.append("Ending leans toward a forced business lesson — close the story instead.")
        scores["ending"] = 0.35
    elif ending_is_abrupt(text):
        problems.append("Ending is abrupt — story stops mid-aftermath instead of landing.")
        scores["ending"] = 0.4
    else:
        scores["ending"] = 0.8

    # length flexibility 1800–2200 preferred, soft
    if wc < 900:
        problems.append(f"Script is short (~{wc} words).")
        scores["length"] = 0.4
    elif wc > 2800:
        problems.append(f"Script is long (~{wc} words) — may be padded.")
        scores["length"] = 0.5
    else:
        # sweet spot around target
        dist = abs(wc - target_words) / max(target_words, 1)
        scores["length"] = max(0.55, 1.0 - dist)

    scores["overall"] = sum(scores.values()) / max(1, len(scores))
    passed = len(problems) == 0 or (scores["overall"] >= 0.62 and len(problems) <= 1)
    revisions = []
    if not passed:
        revisions = [
            "Replace generalizations with concrete events, names, amounts, and decisions from the Story Plan beats.",
            "Cut repeated morals / identical conclusions.",
            "Land the Story Plan ending_state as events (year, number), then answer the cold open. Do not stop mid-aftermath.",
            "Keep spoken English; short paragraphs; causality (A enables B).",
        ]
    return {
        "pass": passed,
        "scores": scores,
        "problems": problems,
        "revision_instructions": revisions,
        "word_count": wc,
        "banned_hits": banned_hits,
        "generic_hits": generic_hits,
    }


def revise_script_once(
    script: str,
    *,
    story_plan_block: str,
    research_notes: str,
    review: dict[str, Any],
    target_words: int = 2000,
) -> str:
    """Single directed revision call. No loops."""
    require_openai_api_key("Script quality revision")
    from openai import OpenAI

    client = OpenAI(api_key=openai_api_key())
    problems = "\n".join(f"- {p}" for p in (review.get("problems") or []))
    instr = "\n".join(f"- {p}" for p in (review.get("revision_instructions") or []))
    prompt = f"""Revise this TRUE documentary narration ONCE.

Fix these problems:
{problems}

Instructions:
{instr}

Hard rules:
- Do NOT invent facts, quotes, thoughts, or events.
- Prefer Story Plan beats + research only.
- Target roughly {target_words} words (acceptable ~1800–2200). Do not pad with morals.
- DELETE any closing essay about lessons, ambition, entrepreneurship, ecosystems, or "broader trends".
- The last two paragraphs MUST be the ending_state as what happened next, then a callback to the cold open.
- Do not stop at "uncertain future" or a pandemic cliff.
- Third person. English. Narration only. No markdown. Short paragraphs. Events > adjectives.

STORY PLAN:
{story_plan_block}

RESEARCH (spine):
{(research_notes or '')[:8000]}

CURRENT NARRATION:
{script}
"""
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.4,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a ruthless editor of factual English company documentaries. "
                    "Events over generalizations. No business lessons. Narration only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=int(target_words * 1.6),
    )
    return (r.choices[0].message.content or "").strip() or script


def llm_quality_scores(script: str) -> dict[str, Any] | None:
    """Optional light score object — skip if no key."""
    key = openai_api_key()
    if not key:
        return None
    from openai import OpenAI

    client = OpenAI(api_key=key)
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "Score a documentary narration. Return JSON only.",
            },
            {
                "role": "user",
                "content": (
                    "Score 0-1 for hook, story, specificity, causality, repetition, filler, "
                    "factuality_guess, ending, voice. Also pass bool and problems[].\n\n"
                    + script[:12000]
                ),
            },
        ],
    )
    return parse_llm_json_object((r.choices[0].message.content or "{}").strip())
