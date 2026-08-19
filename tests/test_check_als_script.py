"""Check ALS script generation from approved story architecture."""
from __future__ import annotations

from src.documentary.formats.check_als.script import apply_tuteo_fixes, validate_check_script
from src.documentary.formats.check_als.visuals import apply_check_visual_layer, compose_image_prompt
from src.documentary.project import create_project
from src.documentary.script_service import generate_documentary_script


def test_unapproved_story_blocks_script(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setenv("FRAMEFACTORY_PROJECTS_DIR", str(root))
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    p = create_project("x", title="x", content_format="check_als", language="es", project_id="c1")
    import pytest

    with pytest.raises(ValueError, match="Aprobá la Story Architecture"):
        generate_documentary_script(p, use_llm=False)


def test_tuteo_and_championship_validation():
    facts = {
        "acquisition": {
            "asking_price": 1,
            "debt_assumed": 650000,
            "your_cash_contribution": 15000,
            "your_ownership": 51,
        },
        "championships": 0,
        "life_end": {"net_worth": 45_000_000},
    }
    bad = "Vos tenés un equipo. Ganaste el campeonato. El anillo es tuyo."
    ok, hard, _ = validate_check_script(bad, facts, strict_length=False)
    assert not ok
    assert any("vos" in h.lower() or "voseo" in h.lower() or "POV" in h for h in hard)
    fixed = apply_tuteo_fixes(
        "Tienes 22 años. Firmas. Te quedas con el 51 por ciento. "
        "La deuda es de 650000 dólares. Todavía no hay campeonato. "
        "Alguien manda una oferta. Bloqueas el teléfono."
    )
    ok2, hard2, _ = validate_check_script(fixed, facts, strict_length=False)
    assert ok2, hard2


def test_check_image_prompt_is_specific():
    prompt = compose_image_prompt(
        {
            "action": "equipment manager hands a ring of keys to the 22-year-old owner in a peeling locker room",
            "camera": "medium shot",
            "lighting": "yellowed practicals",
            "environment": "run-down Halcones locker room",
            "important_objects": ["ring of old arena keys"],
        },
        {"protagonist_age": 22, "protagonist_state": "new owner", "story_time": "AGE 22"},
    )
    assert "2D cinematic illustrated" in prompt
    assert "Not anime" in prompt
    assert "keys" in prompt.lower()
    assert "young entrepreneur in basketball arena" not in prompt.lower()


def test_apply_check_visual_layer_schema(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    proj = root / "p1"
    (proj / "flow-pack").mkdir(parents=True)
    monkeypatch.setenv("FRAMEFACTORY_PROJECTS_DIR", str(root))
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    plan = {
        "visuals": [
            {
                "number": 1,
                "narration_segment": "Tienes 22 años. Trabajas en una oficina.",
                "action": "young man at a cubicle looking at a phone",
                "duration_target": 6,
            },
            {
                "number": 2,
                "narration_segment": "El utilero te entrega las llaves.",
                "action": "equipment man handing keys",
                "duration_target": 6,
            },
        ],
        "visual_bible": {},
        "stats": {"flow": 2},
        "flow_batches": [{"visual_numbers": [1, 2]}],
    }
    out = apply_check_visual_layer({"id": "p1"}, plan)
    scenes = out["image_prompts"]
    assert len(scenes) == 2
    for s in scenes:
        for key in (
            "scene_id",
            "script_text",
            "story_time",
            "duration_target",
            "location",
            "characters",
            "action",
            "emotion",
            "protagonist_age",
            "protagonist_state",
            "camera",
            "shot_type",
            "composition",
            "lighting",
            "important_objects",
            "continuity_notes",
            "image_prompt",
        ):
            assert key in s
        assert "2D cinematic" in s["image_prompt"]
