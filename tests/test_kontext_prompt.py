"""Ensamblado del prompt Kontext (identidad vs composición); sin llamadas a Replicate."""
import pytest

from src.config_loader import get_character_reference_mode
from src.kontext_prompt import (
    KONTEXT_GUARD_TEST_SUBSTRINGS,
    MODE_SCENE_REFERENCE,
    build_kontext_prompt_for_replicate,
    kontext_identity_sheet_composition_guard,
    normalize_character_reference_mode,
)


def test_normalize_default_is_identity_sheet():
    assert normalize_character_reference_mode(None) == "identity_sheet"
    assert normalize_character_reference_mode("") == "identity_sheet"
    assert normalize_character_reference_mode("  ") == "identity_sheet"


def test_normalize_scene_reference_aliases():
    assert normalize_character_reference_mode("scene_reference") == MODE_SCENE_REFERENCE
    assert normalize_character_reference_mode("SCENE") == MODE_SCENE_REFERENCE


def test_identity_sheet_prompt_includes_composition_guard_markers():
    ctx = "Base kontext style instruction."
    scene = "Protagonist runs through a rainy alley at night."
    full = build_kontext_prompt_for_replicate(scene, ctx, "identity_sheet")
    for sub in KONTEXT_GUARD_TEST_SUBSTRINGS:
        assert sub in full, f"missing guard marker: {sub!r}"
    assert scene in full
    assert ctx in full


def test_scene_reference_omits_composition_guard_block():
    ctx = "Base kontext style instruction."
    scene = "Wide shot of a market square."
    full = build_kontext_prompt_for_replicate(scene, ctx, MODE_SCENE_REFERENCE)
    guard = kontext_identity_sheet_composition_guard()
    # El bloque completo del guard no debe estar (es mucho más largo que cualquier coincidencia casual)
    assert guard not in full
    for sub in KONTEXT_GUARD_TEST_SUBSTRINGS:
        assert sub not in full
    assert scene in full


def test_get_character_reference_mode_respects_env(monkeypatch):
    monkeypatch.delenv("CHARACTER_REFERENCE_MODE", raising=False)
    assert get_character_reference_mode() == "identity_sheet"
    monkeypatch.setenv("CHARACTER_REFERENCE_MODE", "scene_reference")
    assert get_character_reference_mode() == MODE_SCENE_REFERENCE


def test_guard_mentions_scene_background_not_reference_backdrop():
    g = kontext_identity_sheet_composition_guard()
    assert "CURRENT SCENE" in g
    assert "not the backdrop in the reference" in g
