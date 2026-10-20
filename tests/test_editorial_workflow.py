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
    assert "ONE ALREADY APPROVED STORY" in source
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

def test_generated_bible_visual_and_production_work_with_wrappers(monkeypatch):
    import json
    from types import SimpleNamespace
    import studio.editorial as editorial
    import src.documentary.openai_key as keys
    import openai
    ed=editorial.fresh()
    ed["stages"]["brief"]["data"]={"language":"es","premise":"Rescatar un negocio","duration_min":[20,25]}
    ed["stages"]["concepts"]["data"]={"options":[{"id":"A","title":"POV: Salvas restaurantes","premise":"Restaurantes"}],"selected":"A"}
    ed["stages"]["packaging"]["data"]={"options":[{"id":"A","title":"POV: US$1","hook":"Arranque"}],"selected":"A"}
    project={"id":"test","topic":"Restaurantes","editorial":ed}
    responses={
      "bible":{"narrative_bible":{"setting":{"location":"Ciudad"},"characters":[{"name":"Prota"}],"timeline":[{"day":"1"}],"economics":{"debt":"enorme"},"ending":{"resolution":"victoria"}}},
      "visual":{"visual_bible":{"style":"modern_2d_animation","characters":[{"name":"Prota"}],"locations":[{"name":"Local"}]}},
      "production":{"production_plan":{"script_plan":{"opening":"Shock"},"continuity_checks":[{"check":"Todos los locales"}]}}
    }
    monkeypatch.setattr(keys,"require_openai_api_key",lambda *_:"dummy")
    for stage,payload in responses.items():
        class FakeClient:
            def __init__(self,**kwargs): self.chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])))
        monkeypatch.setattr(openai,"OpenAI",FakeClient)
        data=editorial._generate_stage_content(stage,project,"")
        editorial._validate(stage,data)
        assert data
        if stage=="bible": assert data["setting"]["location"]=="Ciudad"
        if stage=="visual": assert data["style"]=="modern_2d_animation"
        if stage=="production": assert data["script_plan"]["opening"]=="Shock"


def test_edited_forms_and_404_recovery_cover_every_stage():
    from pathlib import Path
    code=Path("public/assets/creative-studio.js").read_text(encoding="utf8")
    assert 'function details(data)' in code
    assert 'project_snapshot:snapshot' in code
    assert 'async function editorialRequest(' in code
    assert 'editorialRequest(active.id,"/"+step+"/generate"' in code
    assert 'editorialRequest(active.id,"/"+step,"PUT"' in code
    assert 'JSON.stringify(value,null,2)' not in code

def test_missing_project_recovers_inside_same_api_request(monkeypatch):
    from studio import editorial
    stored={}
    def load(pid):
        if pid not in stored: raise FileNotFoundError(pid)
        return stored[pid]
    monkeypatch.setattr(editorial,"load_project",load)
    monkeypatch.setattr(editorial,"save_project",lambda p:stored.update({p["id"]:p}))
    original=editorial.fresh()
    original["stages"]["brief"]["data"]={"language":"es","premise":"Historia","narration":"segunda persona","tone":"cine","duration_min":[20,25]}
    recovered=editorial._load("same-video",{"id":"same-video","title":"POV: una empresa","editorial":original})
    assert recovered["id"]=="same-video"
    assert recovered["topic"]=="Historia"
    assert editorial._load("same-video")["editorial"]["stages"]["brief"]["data"]["language"]=="es"
    from fastapi import HTTPException
    try:
        editorial._load("other-video",{"id":"wrong-video","title":"Wrong","editorial":original})
        assert False
    except HTTPException as err:
        assert err.status_code==422


def test_bible_visual_production_approve_routes(monkeypatch):
    from studio import editorial
    project={"id":"sample","title":"POV: un cine","topic":"Cine","editorial":editorial.fresh()}
    stages=project["editorial"]["stages"]
    for key in ("brief","concepts","packaging","structure"):
        stages[key]["approved"]=True
    monkeypatch.setattr(editorial,"_load",lambda pid,snapshot=None:project)
    monkeypatch.setattr(editorial,"save_project",lambda p:None)
    payloads={
       "bible":{"setting":{"city":"Roma"},"characters":[{"name":"Luz"}],"timeline":[{"day":1}],"economics":{"risk":"grave"},"ending":{"resolution":"reabre"}},
       "visual":{"style":"modern_2d_animation","characters":[{"name":"Luz"}],"locations":[{"name":"Cine"}]},
       "production":{"script_plan":{"opening":"Empieza"},"continuity_checks":[{"check":"mismo traje"}]}
    }
    for key,payload in payloads.items():
        result=editorial.update_editorial("sample",key,editorial.StageUpdate(data=payload,approve=True))
        assert result["editorial"]["stages"][key]["approved"] is True
    assert result["ready_for_script"] is True
    assert project["ui_step"]=="script"
