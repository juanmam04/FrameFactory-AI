"""Documentary Story Plan — extraction + beats BEFORE script prose.

One LLM call builds the full plan. Persist for reuse; do not regenerate on script comma edits.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any

from src.documentary.editorial import DOCUMENTARY_INVARIANTS, STORY_CRAFT_BIBLE
from src.documentary.openai_key import require_openai_api_key
from src.documentary.project import append_log, project_dir, save_project
from src.saas_creative_profile import parse_llm_json_object

STORY_PLAN_VERSION = 1
BEAT_PRIORITIES = ("essential", "strong", "optional", "distracting")


EMPTY_STORY_PLAN: dict[str, Any] = {
    "version": STORY_PLAN_VERSION,
    "central_story": "",
    "central_question": "",
    "core_contradiction": "",
    "stakes": "",
    "hook": "",
    "ending_state": "",
    "characters": [],
    "timeline": [],
    "key_events": [],
    "turning_points": [],
    "reveals": [],
    "consequences": [],
    "unknown_or_weakly_supported": [],
    "research_gaps": {
        "known_supported": [],
        "uncertain": [],
        "missing_but_important": [],
    },
    "beats": [],
    "selected_beat_ids": [],
    "approved": False,
    "warnings": [],
}


def get_story_plan(project: dict[str, Any]) -> dict[str, Any]:
    raw = project.get("story_plan")
    if isinstance(raw, dict) and raw:
        return _normalize_plan(raw)
    # Migrate legacy architecture if present
    arch = project.get("story_architecture")
    if isinstance(arch, dict) and arch:
        return _from_legacy_architecture(arch)
    return deepcopy(EMPTY_STORY_PLAN)


def story_plan_is_approved(project: dict[str, Any]) -> bool:
    plan = get_story_plan(project)
    return bool(plan.get("approved")) and bool(selected_beats(plan))


def selected_beats(plan: dict[str, Any]) -> list[dict[str, Any]]:
    beats = plan.get("beats") or []
    ids = plan.get("selected_beat_ids") or []
    if not ids:
        # default: essential + strong
        return [
            b
            for b in beats
            if isinstance(b, dict) and str(b.get("priority") or "strong").lower() in ("essential", "strong")
        ]
    idset = {int(i) for i in ids if str(i).isdigit() or isinstance(i, int)}
    out = []
    for b in beats:
        if not isinstance(b, dict):
            continue
        try:
            bid = int(b.get("id"))
        except (TypeError, ValueError):
            continue
        if bid in idset:
            out.append(b)
    return out


def _heuristic_missing_for_company_story(notes: str, plan: dict[str, Any]) -> list[str]:
    """Flag common story-arc gaps when research text does not mention them."""
    text = (notes or "").lower()
    checks = [
        ("early founding / antecedent business (e.g. Green Desk)", ("green desk", "founded", "co-founded", "cofounded")),
        ("major capital / SoftBank / Masayoshi Son relationship", ("softbank", "masayoshi", "masa son")),
        ("public filing / S-1 details beyond a single loss figure", ("s-1", "s1", "prospectus", "filing")),
        ("governance / dual-class / related-party / trademark controversies", ("governance", "dual-class", "trademark", "related-party", "we company")),
        ("IPO withdrawal mechanics and valuation reset", ("withdraw", "pulled", "cancelled", "canceled")),
        ("post-2019 outcome (rescue, SPAC, bankruptcy, exit)", ("2020", "2021", "2022", "2023", "2024", "spac", "bankruptcy", "chapter 11", "restructur")),
    ]
    missing: list[str] = []
    existing = {
        str(x).lower()
        for x in (plan.get("research_gaps") or {}).get("missing_but_important") or []
    }
    for label, needles in checks:
        if any(n in text for n in needles):
            continue
        if any(label.lower()[:20] in e for e in existing):
            continue
        missing.append(label)
    return missing


def research_gap_warnings(plan: dict[str, Any], *, research_chars: int) -> list[str]:
    warnings: list[str] = []
    gaps = plan.get("research_gaps") if isinstance(plan.get("research_gaps"), dict) else {}
    missing = list(gaps.get("missing_but_important") or [])
    if research_chars < 800:
        warnings.append(
            "Research is thin — Story Plan may lack early years, capital events, or post-crisis outcomes."
        )
    if missing:
        warnings.append(
            "Missing but important (do not invent): " + "; ".join(str(x) for x in missing[:10])
        )
    if len(selected_beats(plan)) < 6:
        warnings.append("Few selected story beats — script may feel thin or generalized.")
    central = str(plan.get("central_story") or "").lower()
    if any(x in central for x in ("unchecked ambition", "cautionary tale", "fragility of startup", "lessons")):
        warnings.append("Central story still reads like a business moral — rewrite as a concrete event sentence.")
    return warnings


def _ensure_beats_from_timeline(plan: dict[str, Any]) -> dict[str, Any]:
    """If the model returns too few beats, promote timeline/key_events into beats."""
    beats = list(plan.get("beats") or [])
    if len(beats) >= 6:
        return plan
    existing_events = {str(b.get("event") or "").strip().lower() for b in beats if isinstance(b, dict)}
    next_id = 1
    for b in beats:
        try:
            next_id = max(next_id, int(b.get("id") or 0) + 1)
        except (TypeError, ValueError):
            pass

    candidates: list[tuple[str, str]] = []
    for t in plan.get("timeline") or []:
        if isinstance(t, dict):
            when = str(t.get("when") or "").strip()
            what = str(t.get("what") or "").strip()
            if what:
                candidates.append((when, what))
    for ke in plan.get("key_events") or []:
        if isinstance(ke, str) and ke.strip():
            candidates.append(("", ke.strip()))

    for when, what in candidates:
        key = what.lower()
        if key in existing_events:
            continue
        if any(key in e or e in key for e in existing_events if e):
            continue
        # Mid/late crisis + capital beats are essential; early raises strong
        low = what.lower()
        if any(x in low for x in ("ipo", "s-1", "resign", "stepped down", "rescue", "valuation", "softbank", "spac", "loss")):
            pri = "essential"
        elif when:
            pri = "strong"
        else:
            pri = "strong"
        beats.append(
            {
                "id": next_id,
                "event": what,
                "why_it_matters": "Supported timeline event for causal storytelling",
                "new_information": what,
                "stakes_change": "",
                "characters": [],
                "time_period": when,
                "priority": pri,
                "source_support": [],
                "visual_potential": "",
                "transition_question": "",
                "visual_kind": "AI_REENACTMENT",
            }
        )
        existing_events.add(key)
        next_id += 1
        if len(beats) >= 14:
            break

    plan["beats"] = beats
    # Prefer essential+strong selection; clear thin selected_beat_ids if too short
    selected = [
        int(b["id"])
        for b in beats
        if str(b.get("priority") or "").lower() in ("essential", "strong")
    ]
    if len(plan.get("selected_beat_ids") or []) < 6:
        plan["selected_beat_ids"] = selected[:14]
    return plan


def _apply_gap_heuristics(plan: dict[str, Any], notes: str, *, expand_beats: bool = False) -> dict[str, Any]:
    gaps = plan.get("research_gaps") if isinstance(plan.get("research_gaps"), dict) else {}
    miss = list(gaps.get("missing_but_important") or [])
    for item in _heuristic_missing_for_company_story(notes, plan):
        if item not in miss:
            miss.append(item)
    gaps["missing_but_important"] = miss
    plan["research_gaps"] = gaps
    if expand_beats:
        plan = _ensure_beats_from_timeline(plan)
    # Soft-rewrite moral / generic central_story toward concrete hook
    central = str(plan.get("central_story") or "")
    if any(
        x in central.lower()
        for x in (
            "unchecked ambition",
            "cautionary tale",
            "volatility of startup",
            "lessons",
            "meteoric rise",
            "precarious nature",
            "illustrates the",
        )
    ):
        hook = str(plan.get("hook") or "").strip()
        if hook and len(hook) > 40:
            plan["central_story"] = hook
    return plan


def generate_story_plan(project: dict[str, Any], *, use_llm: bool = True) -> dict[str, Any]:
    """Build + persist story plan from topic + research. Does not write narration."""
    topic = str(project.get("topic") or "").strip()
    if not topic:
        raise ValueError("Choose a topic before generating a Story Plan.")
    notes = str(project.get("research_notes") or "").strip()
    sources = project.get("sources") or []
    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    title = str(project.get("title") or idea.get("title_concept") or topic).strip()

    if use_llm:
        require_openai_api_key("Story Plan generation")
        plan = _llm_story_plan(topic, title, idea, notes, sources)
    else:
        plan = _mock_story_plan(topic, title, idea, notes)

    plan = _normalize_plan(plan)
    plan = _apply_gap_heuristics(plan, notes, expand_beats=True)
    plan["warnings"] = research_gap_warnings(plan, research_chars=len(notes))
    plan["approved"] = False
    project["story_plan"] = plan
    project["story_plan_approved"] = False
    project["ui_step"] = "story"
    # Invalidate downstream script/flow when plan regenerates
    project["script_approved"] = False
    cps = dict(project.get("checkpoints") or {})
    cps["flow_pack_ready"] = False
    project["checkpoints"] = cps
    save_project(project)
    _persist_files(str(project["id"]), plan, title)
    append_log(str(project["id"]), f"story_plan generated beats={len(plan.get('beats') or [])}")
    return project


def save_story_plan(project: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    plan = _normalize_plan(plan)
    notes = str(project.get("research_notes") or "").strip()
    plan = _apply_gap_heuristics(plan, notes, expand_beats=False)
    plan["warnings"] = research_gap_warnings(plan, research_chars=len(notes))
    plan["approved"] = False
    project["story_plan"] = plan
    project["story_plan_approved"] = False
    project["script_approved"] = False
    cps = dict(project.get("checkpoints") or {})
    cps["flow_pack_ready"] = False
    project["checkpoints"] = cps
    save_project(project)
    _persist_files(str(project["id"]), plan, str(project.get("title") or project.get("topic") or ""))
    append_log(str(project["id"]), "story_plan edited")
    return project


def approve_story_plan(project: dict[str, Any]) -> dict[str, Any]:
    plan = get_story_plan(project)
    if not plan.get("central_story"):
        raise ValueError("Story Plan has no central story yet. Generate or edit first.")
    if not selected_beats(plan):
        raise ValueError("Select at least one Essential/Strong beat before approving.")
    plan["approved"] = True
    project["story_plan"] = plan
    project["story_plan_approved"] = True
    project["ui_step"] = "script"
    save_project(project)
    _persist_files(str(project["id"]), plan, str(project.get("title") or ""))
    append_log(str(project["id"]), "story_plan APPROVED")
    return project


def story_plan_prompt_block(plan: dict[str, Any] | None) -> str:
    if not isinstance(plan, dict) or not plan.get("central_story"):
        return ""
    beats = selected_beats(plan)
    lines = [
        "STORY PLAN (follow this; dramatize pacing only — never invent facts):",
        f"CENTRAL STORY: {plan.get('central_story')}",
        f"CENTRAL QUESTION: {plan.get('central_question')}",
        f"CORE CONTRADICTION: {plan.get('core_contradiction')}",
        f"STAKES: {plan.get('stakes')}",
        f"HOOK / COLD OPEN: {plan.get('hook')}",
        f"ENDING STATE: {plan.get('ending_state')}",
        "",
        "CHARACTERS (actions/goals only — no invented thoughts):",
    ]
    for c in plan.get("characters") or []:
        if isinstance(c, dict):
            lines.append(
                f"- {c.get('name')}: role={c.get('role_in_story')}; "
                f"goal/incentive={c.get('goal_or_incentive')}; "
                f"actions={c.get('important_actions')}"
            )
        else:
            lines.append(f"- {c}")
    lines.append("")
    lines.append("SELECTED STORY BEATS (tell THESE events with causality — A enables B):")
    for b in beats:
        lines.append(
            f"{b.get('id')}. [{b.get('priority')}] ({b.get('time_period') or '?'}) {b.get('event')} "
            f"— why: {b.get('why_it_matters')} — stakesΔ: {b.get('stakes_change')} "
            f"— loop: {b.get('transition_question') or ''}"
        )
    gaps = plan.get("research_gaps") or {}
    miss = gaps.get("missing_but_important") or []
    if miss:
        lines.append("")
        lines.append("DO NOT INVENT (missing/uncertain):")
        for m in miss:
            lines.append(f"- {m}")
    for u in plan.get("unknown_or_weakly_supported") or []:
        lines.append(f"- {u}")
    return "\n".join(lines)


def plan_to_markdown(plan: dict[str, Any]) -> str:
    plan = _normalize_plan(plan)
    lines = [
        "# Story Plan",
        "",
        f"## Central story\n{plan.get('central_story') or ''}",
        "",
        f"## Central question\n{plan.get('central_question') or ''}",
        "",
        f"## Core contradiction\n{plan.get('core_contradiction') or ''}",
        "",
        f"## Stakes\n{plan.get('stakes') or ''}",
        "",
        f"## Hook\n{plan.get('hook') or ''}",
        "",
        f"## Ending state\n{plan.get('ending_state') or ''}",
        "",
        "## Characters",
    ]
    for c in plan.get("characters") or []:
        if isinstance(c, dict):
            lines.append(
                f"- **{c.get('name')}** — {c.get('role_in_story')} | "
                f"{c.get('goal_or_incentive')} | {c.get('important_actions')}"
            )
        else:
            lines.append(f"- {c}")
    lines.extend(["", "## Story beats"])
    for b in plan.get("beats") or []:
        if not isinstance(b, dict):
            continue
        sel = "✓" if b.get("id") in (plan.get("selected_beat_ids") or []) or str(
            b.get("priority")
        ).lower() in ("essential", "strong") else "·"
        lines.append(
            f"{sel} {b.get('id')}. [{b.get('priority')}] {b.get('event')} "
            f"({b.get('time_period') or '?'})"
        )
        if b.get("why_it_matters"):
            lines.append(f"   why: {b.get('why_it_matters')}")
    gaps = plan.get("research_gaps") or {}
    if gaps.get("missing_but_important"):
        lines.extend(["", "## Missing but important"])
        for m in gaps["missing_but_important"]:
            lines.append(f"- {m}")
    if plan.get("warnings"):
        lines.extend(["", "## Warnings"])
        for w in plan["warnings"]:
            lines.append(f"- {w}")
    return "\n".join(lines).strip() + "\n"


def _persist_files(project_id: str, plan: dict[str, Any], title: str) -> None:
    root = project_dir(project_id)
    (root / "script").mkdir(parents=True, exist_ok=True)
    (root / "script" / "story_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "script" / "story_plan.md").write_text(plan_to_markdown(plan), encoding="utf-8")


def _normalize_plan(raw: dict[str, Any]) -> dict[str, Any]:
    plan = deepcopy(EMPTY_STORY_PLAN)
    plan.update({k: raw.get(k, plan.get(k)) for k in plan.keys()})
    plan["version"] = STORY_PLAN_VERSION
    beats = []
    for i, b in enumerate(raw.get("beats") or [], start=1):
        if not isinstance(b, dict):
            continue
        try:
            bid = int(b.get("id") or i)
        except (TypeError, ValueError):
            bid = i
        pri = str(b.get("priority") or "strong").lower().strip()
        if pri not in BEAT_PRIORITIES:
            pri = "strong"
        beats.append(
            {
                "id": bid,
                "event": str(b.get("event") or "").strip(),
                "why_it_matters": str(b.get("why_it_matters") or "").strip(),
                "new_information": str(b.get("new_information") or "").strip(),
                "stakes_change": str(b.get("stakes_change") or "").strip(),
                "characters": list(b.get("characters") or []) if isinstance(b.get("characters"), list) else [],
                "time_period": str(b.get("time_period") or "").strip(),
                "priority": pri,
                "source_support": list(b.get("source_support") or [])
                if isinstance(b.get("source_support"), list)
                else [],
                "visual_potential": str(b.get("visual_potential") or "").strip(),
                "transition_question": str(b.get("transition_question") or "").strip(),
                "visual_kind": str(b.get("visual_kind") or "AI_REENACTMENT").strip(),
            }
        )
    plan["beats"] = beats
    chars = []
    for c in raw.get("characters") or []:
        if isinstance(c, dict):
            chars.append(
                {
                    "name": str(c.get("name") or "").strip(),
                    "role_in_story": str(c.get("role_in_story") or c.get("role") or "").strip(),
                    "goal_or_incentive": str(c.get("goal_or_incentive") or c.get("desire") or "").strip(),
                    "important_actions": str(c.get("important_actions") or "").strip(),
                    "relationship_to_company": str(c.get("relationship_to_company") or "").strip(),
                    "relevant_period": str(c.get("relevant_period") or "").strip(),
                }
            )
    plan["characters"] = chars
    gaps = raw.get("research_gaps") if isinstance(raw.get("research_gaps"), dict) else {}
    plan["research_gaps"] = {
        "known_supported": list(gaps.get("known_supported") or []),
        "uncertain": list(gaps.get("uncertain") or []),
        "missing_but_important": list(gaps.get("missing_but_important") or []),
    }
    # selected ids
    sel = raw.get("selected_beat_ids")
    if isinstance(sel, list) and sel:
        plan["selected_beat_ids"] = [int(x) for x in sel if str(x).isdigit() or isinstance(x, int)]
    else:
        plan["selected_beat_ids"] = [
            int(b["id"]) for b in beats if b.get("priority") in ("essential", "strong") and b.get("event")
        ]
    plan["approved"] = bool(raw.get("approved"))
    plan["warnings"] = list(raw.get("warnings") or [])
    # map aliases
    if not plan.get("central_story") and raw.get("story_engine"):
        plan["central_story"] = str(raw.get("story_engine"))
    if not plan.get("hook") and raw.get("cold_open"):
        plan["hook"] = str(raw.get("cold_open"))
    return plan


def _from_legacy_architecture(arch: dict[str, Any]) -> dict[str, Any]:
    beats = []
    for i, b in enumerate(arch.get("beat_sheet") or [], start=1):
        if isinstance(b, dict):
            beats.append(
                {
                    "id": i,
                    "event": b.get("moment") or "",
                    "why_it_matters": b.get("curiosity_payoff") or "",
                    "priority": "strong",
                    "time_period": "",
                    "characters": [],
                    "new_information": "",
                    "stakes_change": "",
                    "source_support": [],
                    "visual_potential": "",
                    "transition_question": b.get("curiosity_payoff") or "",
                    "visual_kind": "AI_REENACTMENT",
                }
            )
    chars = []
    for c in arch.get("characters") or []:
        if isinstance(c, dict):
            chars.append(
                {
                    "name": c.get("name") or "",
                    "role_in_story": "",
                    "goal_or_incentive": c.get("desire") or "",
                    "important_actions": "",
                    "relationship_to_company": "",
                    "relevant_period": "",
                }
            )
    return _normalize_plan(
        {
            "central_story": arch.get("story_engine") or "",
            "hook": arch.get("cold_open") or "",
            "ending_state": arch.get("ending_image") or "",
            "characters": chars,
            "beats": beats,
            "unknown_or_weakly_supported": arch.get("do_not_invent") or [],
        }
    )


def _llm_story_plan(
    topic: str,
    title: str,
    idea: dict[str, Any],
    notes: str,
    sources: list[Any],
) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=require_openai_api_key("Story Plan generation"))
    system = f"""You are the Story Editor for a channel of FASCINATING TRUE STORIES ABOUT COMPANIES.
{DOCUMENTARY_INVARIANTS}

{STORY_CRAFT_BIBLE}

Build a STORY PLAN only — not narration prose.

Rules:
- Use ONLY facts supported by the research notes. If a major beat is not in the notes, put it in
  research_gaps.missing_but_important — NEVER invent it into beats.
- central_story must be EVENT-SPECIFIC (who did what / what belief formed / what broke). Ban morals:
  no "fragility of startup success", "unchecked ambition", "cautionary tale", "lessons".
- Prefer EVENTS over generalizations. Aim for 8–16 beats when research supports them.
- Characters must have documented actions/incentives — never invent thoughts.
- Beats must show causality (A enables/causes B), not a bare year list.
- Mark each beat priority: essential | strong | optional | distracting.
- selected_beat_ids = essential + strong only (usually 8–14).
- Ending state must use the LATEST supported outcome in the notes (not freeze at IPO year if later exists).
- If research skips early years, SoftBank/capital, S-1/governance specifics, or post-crisis fate:
  list those under missing_but_important.
- visual_kind one of: AI_REENACTMENT, ARCHIVAL, LOGO, DOCUMENT, HEADLINE, MAP, CHART, PRODUCT, SCREENSHOT

Return ONLY JSON matching this schema:
{{
  "central_story": "one tight sentence: what is fascinating about THIS company story (events, not morals)",
  "central_question": "the narrative question that unifies the episode",
  "core_contradiction": "true contradiction if supported",
  "stakes": "...",
  "hook": "best cold-open moment (concrete)",
  "ending_state": "where the story lands factually",
  "characters": [{{"name":"","role_in_story":"","goal_or_incentive":"","important_actions":"","relationship_to_company":"","relevant_period":""}}],
  "timeline": [{{"when":"","what":""}}],
  "key_events": ["..."],
  "turning_points": ["..."],
  "reveals": ["..."],
  "consequences": ["..."],
  "unknown_or_weakly_supported": ["..."],
  "research_gaps": {{
    "known_supported": ["..."],
    "uncertain": ["..."],
    "missing_but_important": ["..."]
  }},
  "beats": [
    {{
      "id": 1,
      "event": "concrete event",
      "why_it_matters": "",
      "new_information": "",
      "stakes_change": "",
      "characters": ["..."],
      "time_period": "",
      "priority": "essential",
      "source_support": ["..."],
      "visual_potential": "",
      "transition_question": "",
      "visual_kind": "AI_REENACTMENT"
    }}
  ],
  "selected_beat_ids": [1,2,3]
}}
"""
    user = json.dumps(
        {
            "working_title": title,
            "topic": topic,
            "idea": idea,
            "research_notes": notes or "(empty)",
            "sources": sources,
        },
        ensure_ascii=False,
    )
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.45,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = (r.choices[0].message.content or "{}").strip()
    data = parse_llm_json_object(raw) or {}
    return data


def _mock_story_plan(topic: str, title: str, idea: dict[str, Any], notes: str) -> dict[str, Any]:
    entity = str(idea.get("primary_entity") or title or topic)[:80]
    return {
        "central_story": f"What happens when {entity} sells a dream that outruns its reality.",
        "central_question": f"How did {entity} convince the world — and what exposed the gap?",
        "core_contradiction": "Extraordinary valuation vs fragile underlying economics (if research supports).",
        "stakes": "Belief, capital, and public scrutiny.",
        "hook": "Open on the highest-stakes public rupture, then rewind.",
        "ending_state": "Aftermath / current consequence supported by research.",
        "characters": [
            {
                "name": entity,
                "role_in_story": "central company / founder cluster",
                "goal_or_incentive": str(idea.get("hook") or "scale belief")[:120],
                "important_actions": "See research notes",
                "relationship_to_company": "core",
                "relevant_period": "",
            }
        ],
        "timeline": [],
        "key_events": [],
        "turning_points": [],
        "reveals": [],
        "consequences": [],
        "unknown_or_weakly_supported": ["Any figure marked UNKNOWN in research"],
        "research_gaps": {
            "known_supported": [line.strip("- ").strip() for line in notes.splitlines() if line.strip().startswith("-")][:6],
            "uncertain": [],
            "missing_but_important": [
                "Early founding details",
                "Major capital events",
                "Post-crisis outcomes",
            ]
            if len(notes) < 400
            else [],
        },
        "beats": [
            {
                "id": 1,
                "event": "Cold-open rupture",
                "why_it_matters": "Creates curiosity",
                "priority": "essential",
                "time_period": "",
                "characters": [],
                "new_information": "",
                "stakes_change": "high",
                "source_support": [],
                "visual_potential": "peak moment",
                "transition_question": "How did we get here?",
                "visual_kind": "AI_REENACTMENT",
            },
            {
                "id": 2,
                "event": "Origin desire / founding",
                "why_it_matters": "Setup",
                "priority": "essential",
                "time_period": "",
                "characters": [],
                "new_information": "",
                "stakes_change": "",
                "source_support": [],
                "visual_potential": "origin",
                "transition_question": "What did they want?",
                "visual_kind": "AI_REENACTMENT",
            },
            {
                "id": 3,
                "event": "Escalation / bigger bets",
                "why_it_matters": "Raises stakes",
                "priority": "strong",
                "time_period": "",
                "characters": [],
                "new_information": "",
                "stakes_change": "up",
                "source_support": [],
                "visual_potential": "expansion",
                "transition_question": "What could go wrong?",
                "visual_kind": "AI_REENACTMENT",
            },
            {
                "id": 4,
                "event": "Public break / reveal",
                "why_it_matters": "Belief collapses",
                "priority": "essential",
                "time_period": "",
                "characters": [],
                "new_information": "",
                "stakes_change": "down",
                "source_support": [],
                "visual_potential": "document/headline",
                "transition_question": "What does it cost?",
                "visual_kind": "DOCUMENT",
            },
            {
                "id": 5,
                "event": "Aftermath / ending state",
                "why_it_matters": "Closes the story",
                "priority": "essential",
                "time_period": "",
                "characters": [],
                "new_information": "",
                "stakes_change": "",
                "source_support": [],
                "visual_potential": "consequence",
                "transition_question": "",
                "visual_kind": "AI_REENACTMENT",
            },
        ],
        "selected_beat_ids": [1, 2, 3, 4, 5],
    }
