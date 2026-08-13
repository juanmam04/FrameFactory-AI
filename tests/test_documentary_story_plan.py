"""Story Plan + editorial quality tests for Documentary."""
from __future__ import annotations

import pytest

from src.documentary.channel import business_documentary_profile, target_words_from_profile
from src.documentary.project import DEFAULT_PROJECT, PROGRESS_STEPS, create_project, derive_progress
from src.documentary.script_quality import heuristic_script_quality
from src.documentary.script_validation import validate_documentary_script
from src.documentary.story_plan import (
    EMPTY_STORY_PLAN,
    generate_story_plan,
    get_story_plan,
    save_story_plan,
    selected_beats,
)
from src.script_generator import get_plantillas_guion


@pytest.fixture()
def tmp_projects(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    return root


def test_progress_steps_include_topic_and_story():
    assert PROGRESS_STEPS[0] == "topic"
    assert "story" in PROGRESS_STEPS
    assert PROGRESS_STEPS.index("story") < PROGRESS_STEPS.index("script")


def test_documentary_default_words_2000():
    assert DEFAULT_PROJECT["target_words"] == 2000
    assert DEFAULT_PROJECT["target_duration_min"] == [11, 15]
    prof = business_documentary_profile()
    assert target_words_from_profile(prof) == 2000


def test_legacy_plantilla_still_resolves():
    plants = get_plantillas_guion()
    plantillas = plants.get("plantillas") if isinstance(plants, dict) else {}
    assert isinstance(plantillas, dict)
    assert "business_documentary_en" in plantillas
    # Legacy templates must still resolve (not removed by Documentary changes).
    assert "reddit_stories" in plantillas or "storytime" in plantillas or len(plantillas) >= 2


def test_story_plan_schema_mock(tmp_projects):
    p = create_project("WeWork rise and IPO collapse", title="WeWork", research_notes="Adam Neumann. SoftBank. IPO 2019.")
    out = generate_story_plan(p, use_llm=False)
    plan = get_story_plan(out)
    for key in EMPTY_STORY_PLAN:
        assert key in plan
    assert plan["central_story"]
    assert plan["beats"]
    assert selected_beats(plan)
    # persist reload
    from src.documentary.project import load_project

    reloaded = load_project(out["id"])
    assert get_story_plan(reloaded)["central_story"] == plan["central_story"]


def test_empty_research_warning(tmp_projects):
    p = create_project("Thin topic", title="Thin", research_notes="")
    out = generate_story_plan(p, use_llm=False)
    warnings = get_story_plan(out).get("warnings") or []
    assert any("thin" in w.lower() or "missing" in w.lower() for w in warnings)


def test_generic_filler_quality_detects():
    bad = (
        "The meteoric rise of the company was fueled by strategic marketing and charismatic leadership. "
        "The excitement was palpable. The stark reality was a cautionary tale of unchecked ambition. "
        "It underscored the necessity of balancing ambition with pragmatism. "
        "In the years to come entrepreneurs can learn from this indelible mark and navigate its path forward. "
        "The broader implications serve as a reminder of lessons learned in ever-evolving markets. "
    ) * 3
    hq = heuristic_script_quality(bad, target_words=2000)
    assert hq["banned_hits"] or hq["generic_hits"]
    assert not hq["pass"] or len(hq["problems"]) >= 1


def test_repetition_quality_detects():
    para = (
        "The collapse taught startups that ambition must be balanced with pragmatism in every decision. "
        "Investors learned that valuation without economics is fragile.\n\n"
    )
    text = para * 5
    hq = heuristic_script_quality(text, target_words=2000)
    assert hq["scores"]["repetition"] < 0.8 or "Repetitive" in " ".join(hq["problems"])


def test_first_person_still_blocked():
    ok, reasons = validate_documentary_script(
        "I walked into the office and I knew something was wrong. I discovered the truth alone.",
        language="en",
        target_words=2000,
        allow_short_if_thin_research=True,
    )
    assert not ok
    assert any("first-person" in r.lower() for r in reasons)


def test_spanish_still_blocked():
    ok, reasons = validate_documentary_script(
        "El jefe de la empresa no debió ignorarlo. La tensión subía y me cuesta respirar sin poder parar.",
        language="en",
        target_words=2000,
        allow_short_if_thin_research=True,
    )
    assert not ok


def test_story_beats_save_reload(tmp_projects):
    p = create_project("Company X", title="X", research_notes="Founded in 2010. Raised money. Collapsed in 2019.")
    p = generate_story_plan(p, use_llm=False)
    plan = get_story_plan(p)
    plan["central_story"] = "Edited central story for tests"
    plan["selected_beat_ids"] = [1, 2]
    p = save_story_plan(p, plan)
    from src.documentary.project import load_project

    again = get_story_plan(load_project(p["id"]))
    assert again["central_story"] == "Edited central story for tests"
    assert again["selected_beat_ids"] == [1, 2]


def test_derive_progress_story_gate(tmp_projects):
    p = create_project("Y", title="Y", research_notes="Enough research text here to not be empty for flags.")
    prog = derive_progress(p)
    assert prog["flags"]["topic"] is True
    assert prog["flags"]["research"] is True
    assert prog["flags"]["story"] is False
