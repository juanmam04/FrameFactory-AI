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
