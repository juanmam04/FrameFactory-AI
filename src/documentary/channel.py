"""Session = channel helpers for Documentary workflow (reuse creative_profile)."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.saas_creative_profile import merge_profile_disk
from src.documentary.editorial import (
    CHANNEL_ONE_LINER,
    EDITORIAL_PRINCIPLE,
    IDEA_SYSTEM_EXTRA,
    VISUAL_DIRECTION,
)
from src.documentary.formats import (
    FORMAT_CHECK_ALS,
    FORMAT_DOCUMENTARY,
    content_format_from_profile,
    is_check_als_profile,
    normalize_content_format,
)
from src.documentary.formats.check_als.profile import check_als_profile

CHANNEL_TITLE = "100 Days — Business Documentaries"

__all__ = [
    "CHANNEL_TITLE",
    "FORMAT_CHECK_ALS",
    "FORMAT_DOCUMENTARY",
    "business_documentary_profile",
    "check_als_profile",
    "channel_display_name",
    "content_format_from_profile",
    "documentary_script_context",
    "duration_range_from_profile",
    "goal_count_from_profile",
    "is_check_als_profile",
    "is_documentary_profile",
    "language_from_profile",
    "normalize_content_format",
    "profile_snapshot",
    "script_context_from_session",
    "target_words_from_profile",
    "visual_style_from_profile",
]


def is_documentary_profile(profile: dict[str, Any] | None) -> bool:
    if is_check_als_profile(profile):
        return False
    p = merge_profile_disk(profile)
    if str(p.get("workflow") or "").strip().lower() == "documentary":
        return True
    if str(p.get("content_type") or "").strip() == "business_documentary":
        return True
    video = p.get("video") if isinstance(p.get("video"), dict) else {}
    return str(video.get("content_type") or "").strip() == "business_documentary"


def target_words_from_profile(profile: dict[str, Any] | None, fallback: int = 2000) -> int:
    p = merge_profile_disk(profile)
    ch = p.get("channel") if isinstance(p.get("channel"), dict) else {}
    tw = ch.get("target_words")
    try:
        n = int(tw)
        if 800 <= n <= 2500:
            return n
    except (TypeError, ValueError):
        pass
    return int(fallback)


def duration_range_from_profile(profile: dict[str, Any] | None) -> list[int]:
    p = merge_profile_disk(profile)
    ch = p.get("channel") if isinstance(p.get("channel"), dict) else {}
    raw = ch.get("target_duration_min")
    if isinstance(raw, list) and len(raw) >= 2:
        try:
            return [int(raw[0]), int(raw[1])]
        except (TypeError, ValueError):
            pass
    if is_check_als_profile(p):
        return [12, 18]
    return [11, 15]


def language_from_profile(profile: dict[str, Any] | None) -> str:
    p = merge_profile_disk(profile)
    ch = p.get("channel") if isinstance(p.get("channel"), dict) else {}
    lang = str(ch.get("language") or "").strip()
    if lang:
        return lang
    reg = str(p.get("language_register") or "").lower()
    if "english" in reg or reg.startswith("en"):
        return "en"
    return "en"


def goal_count_from_profile(profile: dict[str, Any] | None, fallback: int = 100) -> int:
    p = merge_profile_disk(profile)
    ch = p.get("channel") if isinstance(p.get("channel"), dict) else {}
    try:
        n = int(ch.get("goal_count") or fallback)
        return max(1, n)
    except (TypeError, ValueError):
        return fallback


def channel_display_name(profile: dict[str, Any] | None, session_title: str = "") -> str:
    p = merge_profile_disk(profile)
    ch = p.get("channel") if isinstance(p.get("channel"), dict) else {}
    name = str(ch.get("name") or "").strip()
    if name:
        return name
    return (session_title or CHANNEL_TITLE).strip() or CHANNEL_TITLE


def script_context_from_session(
    profile: dict[str, Any] | None,
    *,
    memory_summary: str = "",
    idea: dict[str, Any] | None = None,
) -> str:
    """Documentary-safe creative context — never dump Reddit/storytime semantics."""
    return documentary_script_context(profile, memory_summary=memory_summary, idea=idea)


def documentary_script_context(
    profile: dict[str, Any] | None,
    *,
    memory_summary: str = "",
    idea: dict[str, Any] | None = None,
) -> str:
    """
    Precedence for Documentary editorial context (invariants live in plantilla + script_service):
    SESSION CREATIVE PROFILE (safe fields) → VIDEO IDEA → (research is in user tema separately)
    Explicitly ignores legacy reddit_dark_storytime / POV / confession fields.
    """
    p = merge_profile_disk(profile)
    ch = p.get("channel") if isinstance(p.get("channel"), dict) else {}
    aud = p.get("audience") if isinstance(p.get("audience"), dict) else {}
    safe = {
        "workflow": "documentary",
        "content_type": "business_documentary",
        "editorial": CHANNEL_ONE_LINER,
        "principle": EDITORIAL_PRINCIPLE,
        "language": ch.get("language") or "en",
        "channel_name": ch.get("name") or "",
        "niche": p.get("niche") or "",
        "tone": p.get("tone") or "",
        "hook_style": p.get("hook_style") or "",
        "pacing": p.get("pacing") or "",
        "audience": aud.get("who") or "",
        "title_style": p.get("title_style") or "",
        "topics_to_focus": p.get("topics_to_focus") or [],
        "topics_to_avoid": p.get("topics_to_avoid") or "",
        "avoid": p.get("avoid") or [],
        "target_words": ch.get("target_words") or 2000,
        "target_duration_min": ch.get("target_duration_min") or [11, 15],
        "narration_format": "third_person_documentary",
        "forbidden_legacy": [
            "reddit_dark_storytime",
            "first_person_confession",
            "POV_este_eres_tu",
            "Spanish storytime",
            "business_education_lecture",
            "corporate_analysis_explainer",
            "five_lessons_listicle",
        ],
    }
    parts = [
        "DOCUMENTARY CHANNEL CONTEXT (tone/audience only — do NOT override editorial invariants):\n"
        + __import__("json").dumps(safe, ensure_ascii=False, indent=2)
    ]
    mem = (memory_summary or "").strip()
    if mem:
        parts.append("SESSION MEMORY:\n" + mem[:4000])
    if idea and isinstance(idea, dict):
        parts.append(
            "EPISODE BRIEF (do not print these labels in the narration):\n"
            + __import__("json").dumps(
                {
                    "title_concept": idea.get("title_concept"),
                    "story": idea.get("story"),
                    "hook": idea.get("hook"),
                    "content_pillar": idea.get("content_pillar"),
                    "why_it_works": idea.get("why_it_works"),
                    "primary_entity": idea.get("primary_entity"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return "\n\n".join(parts)


def visual_style_from_profile(profile: dict[str, Any] | None) -> str:
    p = merge_profile_disk(profile)
    vis = p.get("visual") if isinstance(p.get("visual"), dict) else {}
    bits = [
        str(vis.get("look") or "").strip(),
        str(vis.get("color_mood") or "").strip(),
        str(vis.get("shot_preferences") or "").strip(),
        str(vis.get("b_roll_style") or "").strip(),
    ]
    joined = " ".join(b for b in bits if b)
    if joined:
        return joined
    return VISUAL_DIRECTION


def business_documentary_profile() -> dict[str, Any]:
    """Canonical Creative Profile for the 100 Days challenge."""
    return merge_profile_disk(
        {
            "workflow": "documentary",
            "style": "fascinating true stories about companies — cinematic narrative documentary",
            "content_type": "business_documentary",
            "niche": (
                "Fascinating true stories about companies, founders, products, and the people around them — "
                "origins, rivalries, inventions, frauds, obsessions, mistakes, monopolies, failures, comebacks. "
                "Story first. Business second."
            ),
            "avoid": [
                "business education / MBA lecture tone",
                "corporate analysis explainers",
                "business advice / five lessons",
                "school-essay tone",
                "generic business motivation",
                "listicles",
                "fake drama",
                "fabricated facts",
                "forced rise-and-fall template on every story",
                "Wikipedia definition openings",
                "Welcome back / In today's video / subscribe CTAs",
                "Reddit confession / first-person fiction",
            ],
            "audience": {
                "who": (
                    "General English-speaking YouTube audience with no required business interest — "
                    "they should stay for the story."
                ),
                "pain_points": "Bored by lectures; hungry for what happened next.",
                "reading_level": "general",
            },
            "tone": "intelligent, cinematic, curious, entertaining, confident, clear, agile",
            "hook_style": (
                "Cold-open on the central contradiction or stakes (e.g. $47B valuation vs renting desks), "
                "then rewind. Never open with a definition or model-of-business lecture."
            ),
            "pacing": "Medio",
            "language_register": "English, natural, accessible, concrete — not academic",
            "topics_to_avoid": (
                "Fabricated quotes or numbers; hustle advice; dry textbook summaries; "
                "same company/story already covered in this session; forced morals."
            ),
            "topics_to_focus": [
                "Origins / unlikely beginnings",
                "Rise",
                "Fall",
                "Comeback",
                "Rivalry / corporate war",
                "Invention / transformation",
                "Fraud / obsession",
                "Huge mistake / strange decision",
                "Survival / monopoly / expansion",
                "Failed or brilliant product",
                "Hidden empire",
                "Founder story",
            ],
            "title_style": "Highly clickable without being misleading; specific stakes or numbers when true.",
            "thumbnail_style": (
                "YouTube CTR thumbnail: one named face filling half the frame, emotion readable on a phone, "
                "one story object on the other side, high contrast. No crowded offices, no arrows, no stock."
            ),
            "channel": {
                "name": CHANNEL_TITLE,
                "tagline": EDITORIAL_PRINCIPLE + " · " + CHANNEL_ONE_LINER,
                "content_pillars": (
                    "Origins; Rise; Fall; Comeback; Rivalry; Invention; Fraud; Obsession; "
                    "Mistakes; Monopoly; Products; Hidden Empires; Founder Stories — "
                    "only when there is a great true story"
                ),
                "goal_count": 100,
                "language": "en",
                "target_words": 2000,
                "target_duration_min": [11, 15],
                "visual_provider": "google_flow_manual",
            },
            "script": {
                "structure_preference": (
                    "Story Plan first: central story + beats + causality; "
                    "events over generalizations; no forced rise-and-fall lecture"
                ),
                "forbidden_phrases": (
                    "Welcome back; In today's video; Make sure to subscribe; Like and comment; "
                    "Here are five lessons; Let's dive into the business model; "
                    "cautionary tale; meteoric rise; lessons learned; balancing ambition with pragmatism"
                ),
                "cta_style": "none in narration",
                "opening_style": "Cold open on stakes/contradiction; then rewind if needed",
            },
            "video": {
                "primary_format": "youtube_long_16_9",
                "target_length_category": "long_11_15",
                "aspect_notes": "16:9",
                "content_type": "business_documentary",
                "narration_format": "third_person_documentary",
            },
            "visual": {
                "look": VISUAL_DIRECTION,
                "color_mood": "Restrained, serious, naturalistic, cinematic",
                "shot_preferences": (
                    "Protagonists doing something; places; products; events; consequences; "
                    "establishing / wide / close-up / environmental storytelling"
                ),
                "b_roll_style": (
                    "Offices, factories, stores, cities, meetings, period-accurate details — "
                    "avoid handshake/laptop/generic skyscraper/abstract money"
                ),
                "reference_moodboards": "Google Flow masters for recurring people/places/objects before shot batch",
            },
            "editing": {
                "cut_rhythm": "curious, story-driven documentary",
                "transitions_default": "soft ken burns + short fades",
                "lower_thirds": "no",
                "subtitles_intent": "optional_later",
                "music_role": "bajo_voz",
                "pacing_visual": "Equal still duration locked to voice length",
                "notes_for_ai_director": (
                    "FrameFactory is DIRECTOR; Flow is illustrator. "
                    "Ask for the scene that advances the story moment — not stock business clichés."
                ),
            },
            "idea_generation": {
                "brief": IDEA_SYSTEM_EXTRA,
                "angles_to_favor": (
                    "Any extraordinary true company story with a clear story engine: "
                    "origin, rivalry, invention, fraud, obsession, mistake, monopoly, "
                    "failed/brilliant product, founder, survival, comeback."
                ),
                "angles_to_avoid": (
                    "Business advice; listicles; MBA explainers; fake drama; invented facts; "
                    "forcing rise-and-fall when that isn't the story; repeating a company already produced."
                ),
            },
            "notes_freeform": (
                "Publish one fascinating true company story per day for 100 days. "
                "Images via Google Flow manually. FrameFactory directs: script, flow prompts, import, voice, render."
            ),
        }
    )


def profile_snapshot(profile: dict[str, Any] | None) -> dict[str, Any]:
    return deepcopy(merge_profile_disk(profile))
