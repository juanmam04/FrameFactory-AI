"""Detección de duración en brief/tema para alinear target_words (SaaS UI)."""
import pytest


def test_parse_range_spanish():
    from src.saas_ui import _parse_duration_hint_max_minutes

    assert _parse_duration_hint_max_minutes("entre 15 y 20 minutos") == 20
    assert _parse_duration_hint_max_minutes("Duración: 15-20 min") == 20
    assert _parse_duration_hint_max_minutes("de 10 a 12 minutos") == 12


def test_parse_range_english():
    from src.saas_ui import _parse_duration_hint_max_minutes

    assert _parse_duration_hint_max_minutes("between 15 and 20 minutes") == 20


def test_floor_respects_topic_over_short_slider():
    from src.saas_ui import _target_words_floor_from_topic_duration

    topic = "Historia intensa. El video debe ser entre 15 y 20 minutos."
    assert _target_words_floor_from_topic_duration(topic, "", 420) == 20 * 140
    assert _target_words_floor_from_topic_duration(topic, "", 3000) == 3000


def test_no_hint_keeps_current():
    from src.saas_ui import _target_words_floor_from_topic_duration

    assert _target_words_floor_from_topic_duration("solo tema sin minutos", "", 560) == 560


def test_ignore_hint_allows_short_target():
    from src.saas_ui import _target_words_floor_from_topic_duration

    topic = "Historia. El video debe ser entre 15 y 20 minutos."
    assert (
        _target_words_floor_from_topic_duration(topic, "", 420, ignore_topic_duration_hint=True) == 420
    )
