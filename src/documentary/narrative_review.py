"""Evidence-based review of the complete narration against its approved source.

No view predictions or numeric quality scores. Online generation fails closed if
review cannot run; the saved draft is not replaced until all checks finish.
"""
from __future__ import annotations

import json
import os
from typing import Any

from src.documentary.openai_key import openai_api_key
from src.documentary.viewer_editorial import VIEWER_BRIEF

REVIEW_SYSTEM = VIEWER_BRIEF + """
You are reviewing, not writing. Compare the COMPLETE draft with its approved source.
Check: specific opening promise, early payoff, causal progression, meaningful scene
changes, repetition/padding, continuity of people/time/money, fidelity to the premise,
ending payoff, and whether the scenes can be illustrated for this story.
For nonfiction, unsupported factual assertions are blockers; do not use outside
knowledge to fill research gaps. For fiction, modest staging is allowed but new major
events, unexplained wealth and contradictions of the architecture are blockers.
Return a JSON object with exactly `findings` (list). Each finding has:
`criterion`, `severity` (blocker or review), `evidence` (an EXACT nonempty quote
from the draft), `source_evidence` (quote from supplied source, or 'not supplied'),
and `instruction` (a specific feasible fix using supplied material).
Only material defects are blockers. A quiet scene, short length, unresolved real-life
outcome or absence of a money hook is not itself a defect. No quotas for findings.
Use an empty findings list when you find no concrete defects. No scores or claims of virality.
""".strip()


def review_narrative(script: str, source: dict[str, Any], *, fiction: bool) -> dict[str, Any]:
    from openai import OpenAI

    key = openai_api_key()
    if not key:
        raise RuntimeError("Falta la clave de IA para revisar el guion; conservamos el anterior.")
    response = OpenAI(api_key=key).chat.completions.create(
        model=os.getenv("FRAMEFACTORY_EDITOR_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "system", "content": REVIEW_SYSTEM},
                  {"role": "user", "content": json.dumps(
                      {"fiction": fiction, "approved_source": source, "draft": script}, ensure_ascii=False)}],
        response_format={"type": "json_object"}, temperature=0.2,
        max_tokens=2400, timeout=90.0,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    if not isinstance(data, dict) or not isinstance(data.get("findings"), list):
        raise ValueError("La revisión editorial devolvió una respuesta incompleta; conservamos el anterior.")
    findings = []
    for row in data["findings"]:
        if not isinstance(row, dict):
            raise ValueError("Revisión editorial inválida.")
        evidence = str(row.get("evidence") or "").strip()
        if (row.get("severity") not in ("blocker", "review") or not evidence
                or evidence not in script or not str(row.get("instruction") or "").strip()
                or not str(row.get("criterion") or "").strip()
                or not str(row.get("source_evidence") or "").strip()):
            raise ValueError("La revisión editorial no citó evidencia verificable del guion.")
        findings.append(row)
    return {"method": "source_grounded_editor", "findings": findings,
            "needs_rewrite": any(f["severity"] == "blocker" for f in findings),
            "requires_human_review": True}


def narrative_revision_prompt(script: str, source: dict[str, Any], review: dict[str, Any], target: int) -> str:
    return (VIEWER_BRIEF + "\nRewrite the complete narration, fixing every cited blocker. "
            "The approved source owns the facts, premise, chronology and ending. "
            "Preserve language and point of view. Do not fix defects by inventing new events. "
            f"Aim for {target} words only when substance supports it.\n"
            + json.dumps({"approved_source": source, "findings": review["findings"], "draft": script},
                         ensure_ascii=False))
