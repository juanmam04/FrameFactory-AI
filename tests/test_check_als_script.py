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
        "vehicle_mode": "sports_team",
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
        "Te mudas a un departamento propio. Sold out: el estadio está lleno y tus padres están en el palco. "
        "Cenas en un lugar que antes no te salía. En el papel vales 45 millones. "
        "Alguien manda una oferta. Quieren comprarte. Bloqueas el teléfono."
    )
    ok2, hard2, _ = validate_check_script(fixed, facts, strict_length=False)
    assert ok2, hard2


def test_millionaire_peak_requires_lifestyle_impact():
    facts = {
        "vehicle_mode": "sports_team",
        "acquisition": {"asking_price": 1, "debt_assumed": 650000, "your_ownership": 51},
        "championships": 0,
        "life_end": {"net_worth": 45_000_000},
    }
    thin = (
        "Tienes 22 años. Firmas el 51 por ciento. La deuda es 650000. "
        "En el papel vales 45 millones de dólares. Alguien manda una oferta. Bloqueas."
    )
    ok, hard, _ = validate_check_script(thin, facts, strict_length=False)
    assert not ok
    assert any("impacto de vida" in h.lower() for h in hard)


def test_business_facts_no_basket_defaults():
    from src.documentary.formats.check_als.script import locked_story_facts, pad_script_from_beats
    from src.script_generator import count_words

    arch = {
        "blueprint": {"business_or_vehicle": {"acquisition": {"your_ownership": 60, "debt_assumed": 0}}},
        "final_world": {
            "ownership_ledger": {"protagonist": 60, "investors": 40, "seller": 0},
            "acquisition": {"closed": True, "your_ownership": 60},
        },
        "beats": [{"beat_id": "b01", "time": "DÍA 1", "event": f"Evento {i} del negocio"} for i in range(30)],
    }
    facts = locked_story_facts(arch, mode="business")
    assert facts["acquisition"]["debt_assumed"] == 0
    assert float(facts["acquisition"]["your_ownership"]) == 60
    assert "estadio" not in " ".join(facts["must_include_scenes"]).lower()
    padded = pad_script_from_beats("Tienes 22 años. Lanzas la empresa.", facts, min_words=1100)
    assert count_words(padded) >= 1100
    low = padded.lower()
    assert "launch_company" not in low
    assert "no moraleja" not in low
    assert "int." not in low


def test_strip_screenplay_and_ops():
    from src.documentary.formats.check_als.script import strip_script_chrome

    raw = """
**Título: Creative Hub**

**INT. DEPARTAMENTO - DÍA**

*El joven mira la pantalla.*

**NARRADOR (V.O.)**
Tienes 25 años. Eres creador en Madrid.

**JOVEN**
Hola inversores.

launch_company.
first_client.
advance_time.

Edad final del state. NO moraleja.
"""
    out = strip_script_chrome(raw)
    low = out.lower()
    assert "tienes 25" in low
    assert "int." not in low
    assert "launch_company" not in low
    assert "narrador" not in low
    assert "no moraleja" not in low


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
    low = prompt.lower()
    assert "stickman" in low
    assert "white" in low and "head" in low
    assert "keys" in low
    assert "young entrepreneur in basketball arena" not in low
    assert "photoreal" in low  # in AVOID list
    assert "text hard ban" in low
    assert "subtitle" in low
    assert "face lock" in low
    assert "suicidal" in low


def test_check_prompt_appends_text_ban_to_cached_prompt():
    from src.documentary.formats.check_als.visuals import format_check_prompt

    out = format_check_prompt(
        {
            "image_prompt": "stickman in office, medium shot",
            "action": "Los primeros días son desafiantes y sientes miedo.",
        },
        {},
    )
    assert "TEXT HARD BAN" in out
    assert "stickman in office" in out


def test_vo_like_action_is_not_painted_literally():
    prompt = compose_image_prompt(
        {
            "action": "Los primeros días son desafiantes. Sientes que has tomado una decisión audaz.",
            "camera": "medium shot",
            "environment": "rainy city park bench at night",
            "moment_id": "rise",
            "moment_label": "Le va bien",
            "emotion": "hopeful determination, slight smile",
        },
        {"protagonist_age": 22, "protagonist_state": "early days", "story_time": "AGE 22"},
    )
    assert "do NOT write these words on the image" in prompt
    assert "TEXT HARD BAN" in prompt
    assert "FACE LOCK" in prompt
    assert "hopeful" in prompt.lower() or "smile" in prompt.lower()


def test_peak_prompt_forbids_sad_default_face():
    prompt = compose_image_prompt(
        {
            "action": "stickman on packed arena stands",
            "moment_id": "peak",
            "moment_label": "En la cima",
            "emotion": "proud joy",
            "environment": "sold-out Halcones arena",
        },
        {"protagonist_age": 26, "protagonist_state": "owner", "story_time": "AGE 26"},
    )
    assert "FACE LOCK" in prompt
    assert "smile" in prompt.lower()
    assert "FORBIDDEN" in prompt
    assert "En la cima" in prompt
    assert "PEAK LIFESTYLE IMPACT" in prompt
    assert "cubicle gloom" in prompt.lower() or "envy" in prompt.lower()


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
        assert "stickman" in s["image_prompt"].lower()
        assert "Location lock:" in s["continuity_notes"]
