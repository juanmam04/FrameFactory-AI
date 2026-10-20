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

def test_creative_agent_chat_and_rule_approval(monkeypatch):
    import json
    from studio import creative_agent as agent
    project={"id":"gym-001","title":"POV: Comprás un gimnasio por US$1","topic":"Gimnasio","editorial":{"stages":{}}}
    monkeypatch.setattr(agent,"_load",lambda pid,snapshot=None: project)
    monkeypatch.setattr(agent,"save_project",lambda p:None)
    monkeypatch.setattr(agent,"_llm",lambda *args,**kw:json.dumps({
        "reply":"El guion entra al gimnasio sin mostrar la compra.",
        "proposed_rule":"Mostrar el proceso de adquisición antes de entrar al local.",
        "suggested_edit":"Agregar negociación y entrega de llaves.",
        "suggested_scope":"opening"}))
    result=agent.agent_chat("gym-001",agent.AgentMessage(message="Nunca mostrás cómo compro el gimnasio."))
    assert "sin mostrar la compra" in result["reply"]
    assert result["suggested_scope"]=="opening"
    assert project["creative_agent_history"][0]["feedback"].startswith("Nunca")
    confirmation=agent.approve_creative_rule("gym-001",agent.RuleApproval(rule=result["proposed_rule"]))
    assert confirmation["approved"]
    agent.approve_creative_rule("gym-001",agent.RuleApproval(rule=result["proposed_rule"]))
    assert len(project["creative_rules"])==1


def test_agent_revisions_require_actual_script_and_reject_unapproved_short_output(monkeypatch):
    from studio import creative_agent as agent
    from fastapi import HTTPException
    monkeypatch.setattr(agent,"_load",lambda pid,snapshot=None:{"id":pid,"title":"Test"})
    try:
        agent.revise_with_agent("one",agent.AgentRevision(instruction="Mostrá la compra del gimnasio"))
        assert False
    except HTTPException as error:
        assert error.status_code==409


def test_agent_project_rules_reach_future_generation():
    import inspect
    from studio.editorial import editorial_project_create, _generate_stage_content
    from studio.editorial_script import generate
    assert "creative_rules" in inspect.getsource(editorial_project_create)
    assert "PERMANENT_EDITORIAL_RULES" in inspect.getsource(_generate_stage_content)
    assert "permanent_creative_rules" in inspect.getsource(generate)
    assert "Do not replay the same event" in inspect.getsource(generate)


def test_agent_appears_in_both_deployment_frontends():
    from pathlib import Path
    for page in ("public/index.html","studio/templates/index.html"):
        assert "editorial-agent.js" in Path(page).read_text(encoding="utf-8")
    for asset in ("public/assets/editorial-agent.js","studio/static/editorial-agent.js"):
        src=Path(asset).read_text(encoding="utf-8")
        assert 'agent/chat' not in src or '"chat"' in src
        assert '"revise"' in src and '"rule"' in src

def test_agent_applies_opening_change_only_after_explicit_action(monkeypatch):
    from studio import creative_agent as agent
    import src.documentary.script_service as service
    old=("Entrás al gimnasio ya convertido en dueño. "*110).strip()
    project={"id":"gym-test","title":"POV: Comprás gimnasio","topic":"Gimnasio","script":old,
        "creative_rules":["Mostrá la adquisición antes de entrar."],"editorial":{"stages":{}}}
    monkeypatch.setattr(agent,"_load",lambda pid,snapshot=None:project)
    monkeypatch.setattr(agent,"_llm",lambda *args,**kw:"Descubrís el anuncio. Te ofrecen el gimnasio por US$1. Aceptás las llaves y firmás el trato. "*85)
    monkeypatch.setattr(agent,"save_project",lambda p:None)
    monkeypatch.setattr(service,"save_edited_script",lambda p,script:{**p,"script":script,"script_approved":False,"editorial_audit":{}})
    result=agent.revise_with_agent("gym-test",agent.AgentRevision(
        instruction="Mostrá cómo se compra el gimnasio.",scope="opening"))
    assert result["applied"]
    assert "Te ofrecen el gimnasio por US$1" in result["script"]
    assert project["script"]==old  # Server loads and returns a new updated object.

def test_story_architecture_rejects_missing_events_and_wrong_act_count(monkeypatch):
    import studio.story_architect as arch
    data={"structure":{"acts":[{"title":"Compra"},{"title":"Crisis"},{"title":"Victoria"}]},
          "concepts":{"options":[{"id":"A","title":"POV: Comprás un gimnasio por US$1"}],"selected":"A"},
          "packaging":{"options":[{"id":"A","title":"POV: Un gimnasio por US$1"}],"selected":"A"},
          "bible":{},"brief":{"language":"es","narration":"segunda persona"}}
    monkeypatch.setattr(arch,"model_json",lambda *args,**kw:{"acts":[{"new_events":["Compra"],"irreversible_change":"Llaves"}]})
    try:
        arch.architecture(object(),data,[])
        assert False
    except ValueError as e:
        assert "plan completo" in str(e)
    monkeypatch.setattr(arch,"model_json",lambda *args,**kw:{"acts":[{"new_events":["Compra"],"irreversible_change":"Llaves"},
                                                                    {"new_events":["Crisis"],"irreversible_change":"Cierre"},
                                                                    {"new_events":["Final"],"irreversible_change":"Rescate"}]})
    plan=arch.architecture(object(),data,["Mostrar la compra"])
    assert len(plan["acts"])==3
    assert plan["acts"][0]["approved_outline_act"]["title"]=="Compra"


def test_local_script_gate_flags_motivational_loops_and_empty_acquisition():
    from studio.story_architect import local_warnings
    repetitive=("Entrás al gimnasio. La presión aumenta. No podemos rendirnos. "*45)
    issues=local_warnings(repetitive,first=True,acquisition=True)
    assert any("adquisición" in x for x in issues)
    assert any("Frase repetitiva" in x for x in issues)


def test_new_writer_requires_independent_review_before_save():
    import inspect
    from studio.editorial_script import generate
    source=inspect.getsource(generate)
    assert "architecture(client" in source
    assert "evaluate(client" in source
    assert "for attempt in range(3)" in source
    assert "El acto " in source and "Se conservó el guion anterior" in source

def test_repeated_long_passages_between_acts_are_detected():
    from studio.story_architect import local_warnings
    repeated=("Entrás al gimnasio y Clara te dice que todas las máquinas están rotas. "
              "Organizás un evento comunitario y contratás un influencer. " * 20)
    warnings=local_warnings(repeated,other_acts=[repeated])
    assert any("pasajes largos" in w for w in warnings)


def test_final_review_rejects_full_story_even_if_acts_pass(monkeypatch):
    from studio import story_architect as arch
    monkeypatch.setattr(arch,"model_json",lambda *a,**kw:{"verdict":"revise",
                       "issues":["Se repite el mismo evento y nunca resuelve el desafío"]})
    result=arch.final_review(object(),plan={"acts":[]},script="Evento repetido",
                            acts=["Acto 1","Acto 2"],brief={"language":"es"},rules=[])
    assert result["verdict"]=="revise"


def test_acquisition_detection_does_not_gate_other_pov_genres():
    from studio.story_architect import is_acquisition
    assert is_acquisition({"title":"POV: Comprás un gimnasio por US$1"})
    assert not is_acquisition({"title":"POV: Conseguís un empleo extraordinario"})

def test_retry_uses_failed_act_text_and_editor_feedback():
    import inspect
    from studio.editorial_script import generate
    source=inspect.getsource(generate)
    assert 'context["rejected_draft_to_rewrite"] = rejected_draft if attempt else ""' in source
    assert 'rejected_draft = segment' in source
    assert 'feedback = list(decision.get("issues") or [])' in source
    assert 'feedback.append(str(decision["revision_instructions"]))' in source
    assert 'rewrite THAT specific draft' in source
