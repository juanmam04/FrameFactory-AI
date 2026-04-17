"""Detección del modo «historias estilo Reddit» y parámetros derivados del perfil."""
from __future__ import annotations

from typing import Any

from .saas_creative_profile import merge_profile_disk


def is_reddit_story_profile(profile: dict[str, Any] | None) -> bool:
    """True si el perfil pide narración tipo Reddit / historia viral sin personaje en pantalla."""
    p = merge_profile_disk(profile or {})
    ct = str(p.get("content_type") or "").strip().lower()
    vt = str((p.get("video") or {}).get("content_type") or "").strip().lower()
    nm = str((p.get("video") or {}).get("narration_format") or "").strip().lower()
    if "reddit" in ct or "reddit" in vt:
        return True
    if nm in ("reddit_background", "reddit_stories", "story_background"):
        return True
    return False


def words_per_reddit_segment(profile: dict[str, Any] | None) -> int:
    """Palabras por bloque (~2–4 s de TTS en español según pacing)."""
    p = merge_profile_disk(profile or {})
    pacing = str(p.get("pacing") or "Medio").strip().lower()
    if pacing in ("rápido", "rapido", "fast"):
        return 10
    if pacing in ("lento", "slow"):
        return 16
    return 12
