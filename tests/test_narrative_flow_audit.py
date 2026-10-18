"""Regression cases discovered in the ten-pass story → Flow audit."""
import json
from types import SimpleNamespace

import pytest

from src.scene_splitter import Escena, compactar_escenas
from src.documentary.narrative_review import review_narrative


def test_budget_preserves_every_word_and_ending():
    scenes = [Escena(i, f'Event {i}. Unique outcome {i}.', 3) for i in range(1, 124)]
    compact = compactar_escenas(scenes, 17)
    assert len(compact) == 17
    assert ' '.join(e.texto for e in compact) == ' '.join(e.texto for e in scenes)
    assert sum(e.duracion_segundos for e in compact) == 369
    assert compact[-1].texto.endswith('Unique outcome 123.')


def test_extra_model_beats_cannot_consume_later_scenes(monkeypatch):
    from src import visual_beats as module
    scenes = [Escena(i, f'Source scene {i}.', 5) for i in range(1, 6)]
    def generate(scene, act, topic, offset, **kwargs):
        beat = module._beats_por_escena_fallback(scene, act, offset)[0]
        beat.scene = 999
        beat.original_text = 'Model paraphrase loses source words.'
        return [beat, beat]
    monkeypatch.setattr(module, '_beats_por_escena_llm', generate)
    beats = module.generar_beats_para_escenas(scenes, 'Story', max_beats_total=5)
    assert [b.scene for b in beats] == list(range(1, 6))
    assert [b.original_text for b in beats] == [s.texto for s in scenes]


def test_check_batches_keep_style_identity_and_original_ids():
    from src.documentary.visual_plan import format_batch_prompt, format_single_prompt
    visuals = [dict(number=n, visual_type='FLOW_REENACTMENT', action=f'protagonist seals parcel {n}',
                    environment='same small shop', protagonist_age=26, moment_id='rise') for n in [2, 14]]
    bible = {'format': 'check_als'}
    prompt = format_batch_prompt({'visual_numbers': [2, 14], 'moment_id': 'rise'}, visuals, bible)
    assert 'IMAGE 014 — save as 014.png' in prompt
    assert 'photoreal, period-accurate' not in prompt
    for v in visuals:
        assert format_single_prompt(v, bible) in prompt


def test_cached_check_prompt_cannot_override_edited_scene():
    from src.documentary.formats.check_als.visuals import format_check_prompt
    visual = dict(action='protagonist returns the unsigned contract', environment='same bakery counter',
                  image_prompt='OLD SCENE: protagonist buys a yacht. TEXT HARD BAN')
    prompt = format_check_prompt(visual)
    assert 'returns the unsigned contract' in prompt
    assert 'buys a yacht' not in prompt
    assert 'same bakery counter' in prompt


def test_blank_scene_edit_is_rejected_before_loading():
    from src.documentary.visual_plan import update_visual_description
    with pytest.raises(ValueError, match='vacía'):
        update_visual_description('unused', 1, '   ')


def _fake_review(monkeypatch, data):
    from src.documentary import narrative_review as module
    import openai
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(data)))])
    monkeypatch.setattr(module, 'openai_api_key', lambda: 'test')
    monkeypatch.setattr(openai, 'OpenAI', lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    return calls


def test_editor_sees_complete_story_and_source_not_only_opening(monkeypatch):
    calls = _fake_review(monkeypatch, {'findings': []})
    script = 'Opens shop. ' * 2000 + 'Rejects the buyout and keeps the shop.'
    report = review_narrative(script, {'ending': 'rejects buyout'}, fiction=True)
    payload = json.loads(calls[0]['messages'][1]['content'])
    assert payload['draft'] == script
    assert payload['approved_source']['ending'] == 'rejects buyout'
    assert not report['needs_rewrite']
    assert 'score' not in report


@pytest.mark.parametrize('data', [{}, {'findings': 'pass'}, {'findings': [
    dict(criterion='ending', severity='blocker', evidence='quote that does not exist',
         source_evidence='not supplied', instruction='Repair the ending')]}])
def test_invalid_or_invented_review_is_not_a_quality_pass(monkeypatch, data):
    _fake_review(monkeypatch, data)
    with pytest.raises(ValueError):
        review_narrative('The shop remains open.', {}, fiction=True)


def test_editor_returns_actionable_blocker_with_evidence(monkeypatch):
    _fake_review(monkeypatch, {'findings': [dict(criterion='ending', severity='blocker',
        evidence='You sell the shop.', source_evidence='Rejects the buyout.',
        instruction='Keep ownership and show the rejected contract.')]})
    report = review_narrative('You sell the shop.', {'ending': 'Rejects the buyout.'}, fiction=True)
    assert report['needs_rewrite']
    assert report['findings'][0]['instruction'].startswith('Keep ownership')


def test_online_storyboard_failure_does_not_export_canned_success(monkeypatch):
    import openai
    from src.documentary.visual_plan import _rewrite_stills
    monkeypatch.setattr('src.documentary.openai_key.require_openai_api_key', lambda *a: 'test')
    def fail(**kwargs):
        raise ConnectionError('offline')
    monkeypatch.setattr(openai, 'OpenAI', lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fail))))
    with pytest.raises(RuntimeError, match='storyboard'):
        _rewrite_stills([dict(number=1, visual_type='FLOW_REENACTMENT',
                             action='founder closes the shop door', narration_segment='The shop closes.')],
                       {}, 'Shop', use_llm=True)


def test_locked_facts_keep_late_payoff_and_causal_links():
    from src.documentary.formats.check_als.script import facts_for_llm
    beats = [dict(beat_id=str(i), event=f'Concrete event number {i}',
                  cause=f'Choice {i-1}', consequence=f'Consequence {i}') for i in range(55)]
    source = facts_for_llm({'beats': beats, 'ending_direction': 'Keeps ownership.'})
    assert len(source['beats']) == 55
    assert source['beats'][-1]['event'] == 'Concrete event number 54'
    assert source['beats'][-1]['consequence'] == 'Consequence 54'
    assert source['ending_scene'] == 'Keeps ownership.'


def test_tab_navigation_cannot_approve_a_pending_script(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from src.documentary import project
    from studio.server import create_app
    monkeypatch.setattr(project, 'PROJECTS_ROOT', tmp_path)
    monkeypatch.delenv('SUPABASE_DB_URL', raising=False)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    p = project.create_project('Shop', project_id='pending-tab')
    p.update(script='Pending narration.', story_plan_approved=True, script_approved=False)
    project.save_project(p)
    response = TestClient(create_app()).patch('/api/projects/pending-tab/step', json={'step': 'flow'})
    assert response.status_code == 200
    saved = project.load_project(p['id'])
    assert saved['ui_step'] == 'script'
    assert not saved['script_approved']


def test_directed_office_action_is_not_replaced_by_a_canned_jet_scene():
    from src.documentary.visual_plan import _concretize_visual, _story_description
    shot = dict(number=8, visual_type='FLOW_REENACTMENT', direction_source='llm',
                action='A group of workers evacuates the conference room after the alarm.',
                description='A group of workers evacuates the conference room after the alarm.',
                location='the established workshop conference room')
    before = dict(shot)
    _concretize_visual(shot, {})
    assert shot == before
    assert _story_description(shot, {}) == before['description']
