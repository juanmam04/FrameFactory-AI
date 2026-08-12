"""Session = channel helpers for Documentary workflow (reuse creative_profile)."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.saas_creative_profile import merge_profile_disk

CHANNEL_TITLE = "100 Days — Business Documentaries"


def is_documentary_profile(profile: dict[str, Any] | None) -> bool:
    p = merge_profile_disk(profile)
    if str(p.get("workflow") or "").strip().lower() == "documentary":
        return True
    if str(p.get("content_type") or "").strip() == "business_documentary":
        return True
    video = p.get("video") if isinstance(p.get("video"), dict) else {}
    return str(video.get("content_type") or "").strip() == "business_documentary"


def target_words_from_profile(profile: dict[str, Any] | None, fallback: int = 1500) -> int:
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
    return [8, 12]


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
        "target_words": ch.get("target_words") or 1500,
        "target_duration_min": ch.get("target_duration_min") or [8, 12],
        "narration_format": "third_person_documentary",
        "forbidden_legacy": [
            "reddit_dark_storytime",
            "first_person_confession",
            "POV_este_eres_tu",
            "Spanish storytime",
        ],
    }
    parts = [
        "DOCUMENTARY CHANNEL CONTEXT (tone/audience only — do NOT override nonfiction/third-person invariants):\n"
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
    return (
        "Premium cinematic documentary reenactment mixed with real archival material when useful. "
        "16:9, naturalistic lighting, restrained grade, photoreal stills. No cartoon, no meme text."
    )


def business_documentary_profile() -> dict[str, Any]:
    """Canonical Creative Profile for the 100 Days challenge."""
    return merge_profile_disk(
        {
            "workflow": "documentary",
            "style": "cinematic narrative business documentary",
            "content_type": "business_documentary",
            "niche": (
                "Extraordinary true stories about companies, founders, money, power, ambition, "
                "fraud, competition, spectacular success and catastrophic failure."
            ),
            "avoid": [
                "school-essay tone",
                "generic business motivation",
                "listicles",
                "fake drama",
                "fabricated facts",
                "repetitive narration",
                "unnecessary jargon",
                "Welcome back / In today's video / subscribe CTAs",
            ],
            "audience": {
                "who": "General English-speaking YouTube audience. No business expertise required.",
                "pain_points": "Wants gripping true stories, not MBA lectures.",
                "reading_level": "general",
            },
            "tone": "intelligent, cinematic, curious, entertaining, confident, clear",
            "hook_style": "Start directly with the extraordinary situation — no channel intros.",
            "pacing": "Medio",
            "language_register": "English, accessible, concrete",
            "topics_to_avoid": (
                "Fabricated quotes or numbers; pure motivation content; dry textbook summaries; "
                "same company/story already covered in this session."
            ),
            "topics_to_focus": [
                "Rise & Fall",
                "Corporate Disasters",
                "Fraud & Scams",
                "Founder Stories",
                "Business Wars",
                "Billion-Dollar Mistakes",
                "Hidden Empires / Monopolies",
                "Strange Business History",
                "Products That Changed or Destroyed Companies",
                "Unexpected Success Stories",
            ],
            "title_style": "Highly clickable without being misleading; specific stakes or numbers when true.",
            "thumbnail_style": "Cinematic faces / moments / contrast; readable emotion; no spammy arrows.",
            "channel": {
                "name": CHANNEL_TITLE,
                "tagline": "Story first, business lesson second.",
                "content_pillars": (
                    "Rise & Fall; Corporate Disasters; Fraud & Scams; Founder Stories; Business Wars; "
                    "Billion-Dollar Mistakes; Hidden Empires / Monopolies; Strange Business History; "
                    "Products That Changed or Destroyed Companies; Unexpected Success Stories"
                ),
                "goal_count": 100,
                "language": "en",
                "target_words": 1500,
                "target_duration_min": [8, 12],
                "visual_provider": "google_flow_manual",
            },
            "script": {
                "structure_preference": "HOOK → CONTEXT → SETUP → ESCALATION → TURNING POINT → CONSEQUENCES → ENDING/TAKEAWAY",
                "forbidden_phrases": "Welcome back; In today's video; Make sure to subscribe; Like and comment",
                "cta_style": "none in narration",
                "opening_style": "Cold open on the extraordinary situation",
            },
            "video": {
                "primary_format": "youtube_long_16_9",
                "target_length_category": "long_8_12",
                "aspect_notes": "16:9",
                "content_type": "business_documentary",
                "narration_format": "third_person_documentary",
            },
            "visual": {
                "look": "Premium cinematic documentary reenactment + archival when useful",
                "color_mood": "Restrained, serious, naturalistic",
                "shot_preferences": "Recurring character/location references; stills every few seconds",
                "b_roll_style": "Offices, press, documents, city skylines, period-accurate details",
                "reference_moodboards": "Google Flow masters for CHAR/LOC/OBJ before shot batch",
            },
            "editing": {
                "cut_rhythm": "steady documentary",
                "transitions_default": "soft ken burns + short fades",
                "lower_thirds": "no",
                "subtitles_intent": "optional_later",
                "music_role": "bajo_voz",
                "pacing_visual": "Equal still duration locked to voice length",
                "notes_for_ai_director": "Prefer continuity refs; avoid reinventing wardrobe/architecture",
            },
            "idea_generation": {
                "brief": (
                    "Propose extraordinary true business stories for a daily English YouTube documentary channel. "
                    "Storytelling before education. Prefer famous stakes, clear villains/heroes, and visualizable moments."
                ),
                "angles_to_favor": (
                    "Rise & Fall, frauds, founder myths, corporate wars, monopoly stories, "
                    "products that remade or ruined companies, unexpected successes."
                ),
                "angles_to_avoid": (
                    "Generic hustle advice; listicles; fake drama; invented facts; "
                    "repeating a company/story already produced in this channel; school-essay framing."
                ),
            },
            "notes_freeform": (
                "Publish one video per day for 100 days. Images via Google Flow manually. "
                "FrameFactory handles script, flow prompts, import, voice, render."
            ),
        }
    )


def profile_snapshot(profile: dict[str, Any] | None) -> dict[str, Any]:
    return deepcopy(merge_profile_disk(profile))
