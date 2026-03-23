"""Tests para enriquecimiento de locaciones abstractas."""

import pytest

from src.location_visual_enrichment import (
    enrich_location_prompt,
    location_has_concrete_visual_cues,
    needs_location_visual_enrichment,
)


def test_concrete_location_not_flagged_for_enrichment():
    assert location_has_concrete_visual_cues("calle oscura con neones")
    assert not needs_location_visual_enrichment("dormitorio pequeño con cama y escritorio")


def test_fictional_name_needs_enrichment():
    assert needs_location_visual_enrichment("Campo de Arkenvale")
    assert not location_has_concrete_visual_cues("Campo de Arkenvale")


def test_enrich_heuristic_keeps_name():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("OPENAI_API_KEY", "")
        out = enrich_location_prompt("Campo de Arkenvale")
    assert out.startswith("Campo de Arkenvale")
    assert " — " in out
    assert len(out) > len("Campo de Arkenvale") + 5


def test_enrich_skips_when_already_visual():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("OPENAI_API_KEY", "")
        out = enrich_location_prompt("kitchen with steel counters and morning light")
    assert out == "kitchen with steel counters and morning light"


def test_enrich_skips_when_already_has_em_dash_layer():
    layered = "X — grassy hills and sky"
    assert not needs_location_visual_enrichment(layered)
