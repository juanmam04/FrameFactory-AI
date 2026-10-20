"""Exercise real HTTP gates and persistence without paid generation providers."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("FRAMEFACTORY_PROJECTS_DIR", str(tmp_path / "projects"))
    monkeypatch.delenv("VERCEL", raising=False)
    from studio.server import create_app
    return TestClient(create_app())


def create(client):
    r = client.post('/api/projects/editorial/create', json={
        'title': 'Comprás un hotel', 'premise': 'Comprás un hotel por un dólar con una deuda millonaria',
        'language': 'es', 'duration_min': [20, 25]})
    assert r.status_code == 200, r.text
    return '/api/projects/' + r.json()['project_id']


def stages():
    options = [{'id': x, 'title': 'El hotel por un dólar ' + x,
                'premise': 'Comprás un hotel con una deuda millonaria', 'thumbnail': 'Hotel abandonado'} for x in 'ABC']
    return {
        'concepts': {'options': options, 'selected': 'A'},
        'packaging': {'options': options, 'selected': 'B'},
        'structure': {'acts': [{'title': 'Compra'}, {'title': 'Crisis'}, {'title': 'Recuperación'}]},
        'bible': {'setting': 'Hotel', 'characters': [{'name': 'Ana'}], 'timeline': ['día 1'],
                  'economics': {'debt': 1000000}, 'ending': 'Recuperación completa'},
        'visual': {'style': 'modern_2d_animation', 'characters': [{'name': 'Ana', 'visual': 'stickman azul'}],
                   'locations': [{'name': 'Hotel', 'visual': 'fachada amarilla'}]},
        'production': {'continuity_checks': ['Deuda coherente'], 'script_plan': 'Tres actos'},
    }


def test_full_approval_save_audit_and_reopen(client, monkeypatch):
    from src.documentary.project import load_project, save_project
    url = create(client)
    pid = url.split('/')[-1]
    assert load_project(pid)['target_words'] == 3038
    assert client.patch(url+'/step', json={'step':'flow'}).status_code == 409
    data = stages()
    # Saving three proposals without a selection is valid; approval requires one.
    draft = {**data['concepts'], 'selected': ''}
    assert client.put(url+'/editorial/concepts', json={'data':draft}).status_code == 200
    assert client.put(url+'/editorial/concepts', json={'data':draft, 'approve': True}).status_code == 422
    for stage, value in data.items():
        r = client.put(url+'/editorial/'+stage, json={'data':value, 'approve':True})
        assert r.status_code == 200, r.text
    p = client.get(url).json()['project']
    assert p['title'].endswith('B')
    assert p['editorial']['stages']['production']['approved']
    assert client.patch(url+'/step', json={'step':'script'}).json()['project']['ui_step'] == 'script'
    # Fiction in first person must survive the old nonfiction validator.
    script = ('I walked into the hotel. I knew the debt would become my problem. '
              'I felt the cold air and I saw the broken door. ') * 5
    assert client.put(url+'/script', json={'script': script}).status_code == 200
    assert client.post(url+'/script/approve').status_code == 409
    assert client.patch(url+'/step', json={'step':'voice'}).status_code == 409
    p = load_project(pid)
    p['editorial_audit'] = {'verdict':'pass'}
    save_project(p)
    # Re-saving unchanged text must preserve the audit.
    assert client.put(url+'/script', json={'script':script}).status_code == 200
    assert client.post(url+'/script/approve').status_code == 200
    assert client.patch(url+'/step', json={'step':'flow'}).status_code == 200
    assert client.post(url+'/editorial/reopen/concepts').status_code == 200
    p = load_project(pid)
    assert not p['script_approved'] and not p['editorial_audit']
    assert all(not value for value in p['checkpoints'].values())
    assert client.post(url+'/script/approve').status_code == 409
    assert client.patch(url+'/step', json={'step':'render'}).status_code == 409


@pytest.mark.parametrize('duration', [[], [25], [30,20], [0,20], [20,100]])
def test_invalid_brief_duration_is_rejected(client, duration):
    url = create(client)
    brief = client.get(url+'/editorial').json()['editorial']['stages']['brief']['data']
    brief['duration_min'] = duration
    assert client.put(url+'/editorial/brief', json={'data':brief, 'approve':True}).status_code == 422


def test_duplicate_options_rejected(client):
    url = create(client)
    assert client.put(url+'/editorial/concepts', json={'data':{
        'options':[{'id':'A'}]*3, 'selected':'A'}, 'approve':True}).status_code == 422


def test_static_assets_match_source():
    from pathlib import Path
    for asset in ['studio.js', 'creative-studio.js', 'studio.css', 'creative-studio.css']:
        assert Path('studio/static', asset).read_bytes() == Path('public/assets', asset).read_bytes()


@pytest.mark.parametrize("language", ["es", "en"])
def test_script_generation_keeps_locked_story_full_outline_and_duration(client, monkeypatch, language):
    import json
    from types import SimpleNamespace
    from studio import editorial_script
    from src.documentary.project import load_project
    url = create(client)
    pid = url.split('/')[-1]
    brief=client.get(url+'/editorial').json()['editorial']['stages']['brief']['data']
    brief['language']=language
    assert client.put(url+'/editorial/brief',json={'data':brief,'approve':True}).status_code==200
    data = stages()
    for stage, value in data.items():
        assert client.put(url+'/editorial/'+stage, json={'data':value, 'approve':True}).status_code == 200
    # Architect and independent editorial review are exercised in dedicated tests.
    # This integration test exercises the real HTTP route and persisted writer output.
    from studio import story_architect
    monkeypatch.setattr(story_architect, "model_json", lambda client, system, payload: {
        "acts":[{"new_events":["Compra","Llaves"],"irreversible_change":"Propiedad adquirida","ending_state":"adquirida"},
                {"new_events":["Crisis","Negociación"],"irreversible_change":"Plazo extendido","ending_state":"plazo"},
                {"new_events":["Reapertura"],"irreversible_change":"Hotel salvado","ending_state":"salvado"}]})
    monkeypatch.setattr(story_architect, "evaluate", lambda *a,**kw:{"verdict":"pass","issues":[]})
    monkeypatch.setattr(story_architect, "final_review",lambda *a,**kw:{"verdict":"pass","issues":[]})
    calls = []
    class Completions:
        def create(self, **kwargs):
            payload = json.loads(kwargs['messages'][1]['content'])
            assert ("Spanish" if language=="es" else "English") in kwargs['messages'][0]['content']
            calls.append(payload)
            # A controlled provider response; real persistence/invalidation remain exercised.
            text = ("Te ofrecen comprar el hotel por un dólar. Firmás y recibís las llaves. "
                    + " ".join(f"decisión{len(calls)}acción{j}" for j in range(970)))
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])
    monkeypatch.setattr(editorial_script, 'require_openai_api_key', lambda *a: 'fixture')
    monkeypatch.setattr(editorial_script, 'OpenAI', lambda **k: SimpleNamespace(chat=SimpleNamespace(completions=Completions())))
    result = client.post(url+'/script/generate')
    assert result.status_code == 200, result.text
    assert len(calls) == 3
    assert calls[0]['target_words_this_act'] == 1013
    assert calls[0]['locked_story']['id'] == 'A'
    assert calls[0]['selected_packaging']['id'] == 'B'
    assert len(calls[0]['complete_structure']['acts']) == 3
    assert calls[1]['preceding_script']
    assert calls[-1]['final_act']
    p = load_project(pid)
    assert p['script'] and not p['script_approved']
    from pathlib import Path
    from src.documentary.project import project_dir
    assert (project_dir(pid)/'script/script.txt').read_text() == p['script']


def test_editorial_visual_plan_preserves_approved_stickman_cast(client):
    from src.documentary.project import load_project, save_project
    from src.documentary.visual_plan import build_visual_plan, load_visual_plan
    url = create(client)
    pid = url.split('/')[-1]
    for stage, value in stages().items():
        assert client.put(url+'/editorial/'+stage, json={'data':value, 'approve':True}).status_code == 200
    p = load_project(pid)
    p['script'] = '\n\n'.join(f'Ana abre la puerta del hotel número {i} y revisa el contrato.' for i in range(120))
    p['script_approved'] = True
    save_project(p)
    plan = build_visual_plan(p, use_llm=False)
    assert plan['visual_bible']['characters'][0]['name'] == 'Ana'
    assert 'stickman' in plan['visual_bible']['global_style']
    assert load_visual_plan(pid)['visual_bible']['characters'][0]['name'] == 'Ana'


def test_new_editorial_project_syncs_real_id(client, monkeypatch):
    from src.documentary import cloud_sync
    pushed = []
    monkeypatch.setattr(cloud_sync, 'configured', lambda:True)
    monkeypatch.setattr(cloud_sync, 'push_paths', lambda pid, paths:pushed.append((pid,paths)))
    monkeypatch.setattr(cloud_sync, 'push_project', lambda pid, **kwargs:pushed.append((pid,['all'])))
    url = create(client)
    pid = url.split('/')[-1]
    assert (pid,['project.json']) in pushed
    assert not any(row[0]=='editorial' for row in pushed)


def test_cloud_outage_does_not_lose_created_project(client, monkeypatch):
    from src.documentary import cloud_sync
    from src.documentary.project import load_project
    monkeypatch.setattr(cloud_sync, 'configured', lambda:True)
    monkeypatch.setattr(cloud_sync, 'push_paths', lambda *a:(_ for _ in ()).throw(RuntimeError('unavailable')))
    url = create(client)
    assert load_project(url.split('/')[-1])['editorial']['stages']['brief']['approved']
