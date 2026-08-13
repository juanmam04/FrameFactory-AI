"""Tests for AI research brief + story architecture (offline)."""
from __future__ import annotations

import pytest

from src.documentary.editorial import STORY_CRAFT_BIBLE
from src.documentary.project import create_project, load_project
from src.documentary.research_service import generate_research_brief
from src.documentary.script_service import build_documentary_tema, generate_documentary_script


@pytest.fixture()
def tmp_projects(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    return root


def test_craft_bible_has_cold_open_and_engine():
    assert "STORY ENGINE" in STORY_CRAFT_BIBLE
    assert "COLD OPEN" in STORY_CRAFT_BIBLE
    assert "facts" in STORY_CRAFT_BIBLE.lower() or "invent" in STORY_CRAFT_BIBLE.lower()


def test_generate_research_mock_fills_notes(tmp_projects):
    p = create_project(
        "The rise and collapse of WeWork",
        title="WeWork",
        idea={"primary_entity": "WeWork", "hook": "A company valued like tech that was realty"},
    )
    out = generate_research_brief(p, use_llm=False)
    assert out["research_notes"]
    assert "Story engine" in out["research_notes"] or "STORY" in out["research_notes"].upper()
    assert out.get("research_ai_generated") is True
    assert len(out.get("sources") or []) >= 1
    reloaded = load_project(out["id"])
    assert reloaded["research_notes"] == out["research_notes"]


def test_story_plan_and_script_offline(tmp_projects):
    from src.documentary.story_plan import approve_story_plan, generate_story_plan, get_story_plan

    p = create_project(
        "The rise and collapse of WeWork",
        title="WeWork",
        target_words=400,
        research_notes=(
            "WeWork was co-founded by Adam Neumann. SoftBank was a major investor. "
            "The 2019 IPO attempt collapsed amid governance and valuation concerns."
        ),
        idea={"primary_entity": "WeWork"},
    )
    p = generate_story_plan(p, use_llm=False)
    plan = get_story_plan(p)
    assert plan.get("central_story")
    assert plan.get("hook")
    assert plan.get("beats")
    p = approve_story_plan(p)
    tema = build_documentary_tema(p)
    assert "STORY PLAN" in tema.upper() or "CENTRAL STORY" in tema.upper()
    out = generate_documentary_script(p, use_llm=False)
    assert out.get("story_plan") or get_story_plan(out).get("central_story")
    assert out.get("script")
