from fastapi import HTTPException
from studio.editorial import STAGE_IDS, DEFAULT_VISUAL, _validate, current, fresh


def test_fresh_workflow_has_all_seven_unapproved_stages():
    ed = fresh()
    assert len(STAGE_IDS) == 7
    assert all(not ed["stages"][name]["approved"] for name in STAGE_IDS)
    assert ed["active_stage"] == "brief"


def test_every_project_gets_independent_copy():
    one, two = fresh(), fresh()
    one["stages"]["brief"]["data"]["language"] = "es"
    assert not two["stages"]["brief"]["data"]


def test_bilingual_brief_requires_explicit_original_channel():
    _validate("brief", {"language": "en", "premise": "New story", "narration": "second", "tone": "dramatic", "duration_min": [20, 25]})
    try:
        _validate("brief", {"language": "fr", "premise": "story", "narration": "second", "tone": "cinematic", "duration_min": [20, 25]})
        assert False
    except HTTPException as exc:
        assert exc.status_code == 422


def test_package_needs_three_distinct_candidates():
    try:
        _validate("packaging", {"options": [{"id": "A"}, {"id": "B"}], "selected": "A"})
        assert False
    except HTTPException as exc:
        assert exc.status_code == 422


def test_visual_defaults_are_modern_2d():
    assert DEFAULT_VISUAL["style"] == "modern_2d_animation"
    assert DEFAULT_VISUAL["photorealistic_people"] is False


def test_legacy_editorial_read_does_not_mutate_project():
    project = {"title": "Legacy"}
    ed = current(project)
    assert len(ed["stages"]) == 7
    assert "editorial" not in project

def test_editorial_create_route_registered():
    from studio.server import studio_app
    from fastapi.testclient import TestClient
    client=TestClient(studio_app)
    assert client.post("/api/projects/editorial/create",json={}).status_code == 422
    assert client.get("/api/projects/editorial/list").status_code == 200
    assert client.get("/editorial").status_code == 200


def test_editorial_route_is_part_of_existing_studio():
    from fastapi.testclient import TestClient
    from studio.server import studio_app
    client=TestClient(studio_app)
    res=client.get("/editorial")
    assert res.status_code == 200
    assert res.url.path == "/"
    assert "Nuevo video" in res.text
    assert "creative-studio.css" in res.text

def test_proposals_allow_unselected_drafts_but_require_human_selection_to_approve():
    from studio.editorial import StageUpdate
    assert StageUpdate(data={"options": [{"id": "A"}, {"id": "B"}, {"id": "C"}], "selected": ""}, approve=False)
    try:
        _validate("concepts", {"options": [{"id": "A"}, {"id": "B"}, {"id": "C"}], "selected": ""})
        assert False
    except HTTPException as exc:
        assert exc.status_code == 422

def test_editorial_three_option_generator_contract_is_present():
    import inspect
    from studio.editorial import _generate_stage_content
    code = inspect.getsource(_generate_stage_content)
    assert "REQUIRED TOP-LEVEL JSON SHAPE" in code
    assert "ideas" in code and "proposals" in code
    assert "for attempt in range(2)" in code

def test_story_locked_for_packaging_generator():
    import inspect
    from studio.editorial import _generate_stage_content
    source = inspect.getsource(_generate_stage_content)
    assert "LOCKED_STORY" in source
    assert "PREVIOUSLY APPROVED FICTIONAL STORY" in source
    assert "grandparents" in source
    assert "example.com" in source


def test_packaging_screen_hides_duplicate_premise():
    from pathlib import Path
    js = Path("public/assets/creative-studio.js").read_text(encoding="utf-8")
    assert 'step==="packaging"?["thumbnail","hook","retention","risks"]' in js

def test_pov_titles_and_story_structure_repair_contract():
    import inspect
    from studio.editorial import _generate_stage_content
    source=inspect.getsource(_generate_stage_content)
    assert 'startswith("pov:")' in source
    assert 'stage == "structure"' in source
    assert '"chapters", "segments"' in source
    assert 'Restructure this exact approved story' in source


def test_structure_is_displayed_as_act_cards():
    from pathlib import Path
    text=Path("public/assets/creative-studio.js").read_text(encoding="utf-8")
    assert 'step==="structure"&&Array.isArray(draft.acts)' in text

def test_business_turnaround_decisions_are_explicit_in_pipeline():
    import inspect
    from studio.editorial import _generate_stage_content, audit_script
    from studio.editorial_script import generate
    generator = inspect.getsource(generate)
    editorial = inspect.getsource(_generate_stage_content)
    audit = inspect.getsource(audit_script)
    assert "clever concrete actions" in generator
    assert "ENTERTAINMENT FIRST" in generator
    assert "decision_ledger" in editorial
    assert "Prioritize surprising entertainment" in editorial
    assert "set verdict to revise" in audit


def test_entertainment_first_symbolic_acquisitions():
    import inspect
    from studio.editorial import _generate_stage_content
    from studio.editorial_script import generate
    assert "SYMBOLIC ONE DOLLAR" in inspect.getsource(_generate_stage_content)
    assert "real-world financial logic" in inspect.getsource(_generate_stage_content)
    assert "not an" in inspect.getsource(generate)


def test_packaging_uses_same_story_but_alternative_titles():
    import inspect
    from studio.editorial import _generate_stage_content
    source = inspect.getsource(_generate_stage_content)
    assert "DO NOT REPEAT the exact prior concept title" in source
    assert "title B sells the immediate 30-day countdown" in source
    assert "concept_key in keys" in source
    assert "retry_messages = messages +" in source
