"""Content format packs: documentary (legacy) vs check_als (Aspirational Life Simulations).

ENGINE (reusable): projects, checkpoints, sync, TTS, stills, FFmpeg, captions, media.
FORMAT PACK: editorial, prompts, schemas, validators, idea/story/visual rules, UI copy.
"""
from __future__ import annotations

from typing import Any

FORMAT_DOCUMENTARY = "documentary"
FORMAT_CHECK_ALS = "check_als"
KNOWN_FORMATS = (FORMAT_DOCUMENTARY, FORMAT_CHECK_ALS)


def normalize_content_format(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in (
        "check",
        "als",
        "check_als",
        "aspirational",
        "life_sim",
        "life_simulation",
    ):
        return FORMAT_CHECK_ALS
    if raw in ("documentary", "business_documentary", "doc", "business_doc"):
        return FORMAT_DOCUMENTARY
    return FORMAT_DOCUMENTARY


def content_format_from_profile(profile: dict[str, Any] | None) -> str:
    p = profile if isinstance(profile, dict) else {}
    ch = p.get("channel") if isinstance(p.get("channel"), dict) else {}
    video = p.get("video") if isinstance(p.get("video"), dict) else {}
    for cand in (
        p.get("content_format"),
        ch.get("content_format"),
        video.get("content_format"),
        p.get("workflow"),
        p.get("content_type"),
        video.get("content_type"),
    ):
        if not cand:
            continue
        s = str(cand).strip().lower()
        if s in ("check_als", "check", "als") or "check_als" in s:
            return FORMAT_CHECK_ALS
        if s in ("documentary", "business_documentary") or "documentary" in s:
            return FORMAT_DOCUMENTARY
    return FORMAT_DOCUMENTARY


def is_check_als_profile(profile: dict[str, Any] | None) -> bool:
    return content_format_from_profile(profile) == FORMAT_CHECK_ALS
