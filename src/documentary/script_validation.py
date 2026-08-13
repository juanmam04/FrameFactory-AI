"""Post-generation guardrails for Documentary narration scripts."""
from __future__ import annotations

import re
from typing import Any

# Strong Spanish / confession / POV contamination markers (legacy Reddit fallback).
_LEGACY_ES_MARKERS = (
    "no debí ignorarlo",
    "no debi ignorarlo",
    "lo dejé pasar",
    "lo deje pasar",
    "me cuesta respirar",
    "sin poder parar",
    "este eres tú",
    "este eres tu",
    "la tensión subía",
    "la tension subia",
)

_METADATA_LEAKS = (
    "working title:",
    "research notes:",
    "hook direction:",
    "today's story brief",
    "creator context:",
    "instructions:",
    "sources:",
    "section:",
)

# First-person narrative patterns (outside quotes) — cheap heuristic.
_FIRST_PERSON_NARR = re.compile(
    r"(?i)\b(?:i\s+(?:walked|knew|couldn't|could not|discovered|kept|believed|thought|felt|saw|heard|realized)|"
    r"i'm|i’ve|i've|my friend told|as i\s)\b"
)

_QUOTED = re.compile(r'[“"][^”"]*[”"]')


def validate_documentary_script(
    script: str,
    *,
    language: str = "en",
    target_words: int = 2000,
    allow_short_if_thin_research: bool = False,
    enforce_editorial_heuristics: bool = False,
) -> tuple[bool, list[str]]:
    """Return (ok, human-readable reasons).

    Hard fails: empty, Spanish/legacy, metadata leaks, first-person narrator, too short.
    Soft filler/repetition only hard-fails when enforce_editorial_heuristics=True
    (AI generation). Manual Save keeps drafts and surfaces warnings in the UI.
    """
    text = (script or "").strip()
    reasons: list[str] = []
    if not text or len(text) < 40:
        return False, ["Script is empty or too short to be usable."]

    low = text.lower()
    for m in _LEGACY_ES_MARKERS:
        if m in low:
            reasons.append(
                "Script looks like the old Spanish confession/storytime fallback — not a business documentary."
            )
            break

    lang = (language or "en").strip().lower()
    if lang.startswith("en"):
        es_hits = len(re.findall(r"\b(el|la|los|las|que|de|en|y|no|me|se|por|una|un|del|es|fue|era)\b", low))
        en_hits = len(re.findall(r"\b(the|and|of|to|in|was|were|a|that|for|with|as|on|by|from)\b", low))
        words = max(1, len(text.split()))
        if es_hits > en_hits and es_hits / words > 0.08:
            reasons.append("Script appears to be mostly Spanish, but this Documentary session expects English.")

    for leak in _METADATA_LEAKS:
        if leak in low:
            reasons.append(f"Script contains internal metadata (“{leak.strip()}”) — narration must be TTS-only.")
            break

    unquoted = _QUOTED.sub(" ", text)
    fp_hits = _FIRST_PERSON_NARR.findall(unquoted)
    i_count = len(re.findall(r"(?i)(?<![A-Za-z])I(?![A-Za-z])", unquoted))
    if len(fp_hits) >= 1 or i_count >= 6:
        reasons.append(
            "Script uses a fictional first-person narrator. Business documentaries must be third-person "
            "(except real attributed quotes)."
        )

    wc = len(text.split())
    if not allow_short_if_thin_research and target_words >= 800 and wc < int(target_words * 0.35):
        reasons.append(
            f"Script is only ~{wc} words (target ~{target_words}). Too short for a reliable documentary draft."
        )

    if enforce_editorial_heuristics:
        reasons.extend(_soft_editorial_failures(text, target_words=target_words))

    return (len(reasons) == 0), reasons


def editorial_warnings(script: str, *, target_words: int = 2000) -> list[str]:
    """Non-blocking editorial issues for UI banners."""
    return _soft_editorial_failures(script, target_words=target_words)


def _soft_editorial_failures(text: str, *, target_words: int) -> list[str]:
    out: list[str] = []
    try:
        from src.documentary.script_quality import heuristic_script_quality

        hq = heuristic_script_quality(text, target_words=target_words)
        if len(hq.get("banned_hits") or []) + len(hq.get("generic_hits") or []) >= 5:
            out.append(
                "Script is overloaded with generic corporate filler — rewrite from Story Plan events."
            )
        if (hq.get("scores") or {}).get("repetition", 1) < 0.4:
            out.append("Script repeats the same conclusions across paragraphs.")
        for p in hq.get("problems") or []:
            if p not in out and "filler" not in p.lower():
                # Surface other heuristic problems as warnings too
                if "Ending leans" in p or "Low fact density" in p:
                    out.append(p)
    except Exception:
        pass
    return out


def strip_metadata_leaks(script: str) -> str:
    """Best-effort removal of obvious leaked labels (does not invent content)."""
    lines = []
    for line in (script or "").splitlines():
        low = line.strip().lower()
        if any(low.startswith(p) for p in _METADATA_LEAKS):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
