"""Viewer-oriented regressions: diagnose filler and preserve visual meaning."""
from src.documentary.viewer_editorial import review_script, VIEWER_BRIEF


def test_generic_success_story_is_not_a_good_ending():
    draft = ('Con una visión clara lanzas tu negocio. La aventura apenas comienza. '
             'Cada pequeño paso cuenta. El futuro está lleno de posibilidades. '
             'Eres el arquitecto de tu destino.')
    report = review_script(draft)
    assert report['needs_rewrite']
    assert {f['code'] for f in report['findings']} >= {'generic_filler', 'unearned_ending'}
    assert 'score' not in report
    assert report['requires_human_review']


def test_meaningful_quiet_scene_is_not_rejected_for_being_quiet():
    draft = ('El utilero deja las llaves sobre la mesa. No te da la mano: espera el sueldo atrasado. '
             'Ibas a pintar la tribuna. Guardas el presupuesto de pintura y llamas al contador. '
             'La primera compra como dueño será pagarle a alguien que todavía no confía en ti.')
    assert not review_script(draft)['needs_rewrite']


def test_repeated_words_are_evidence_not_a_fake_viral_score():
    line = 'La hora siguiente no trae ninguna decisión nueva ni una consecuencia distinta. '
    report = review_script(line * 4)
    assert report['needs_rewrite']
    finding = next(f for f in report['findings'] if f['code'] == 'repetition')
    assert 'ninguna decisión' in finding['evidence'][0]


def test_master_prompt_prioritizes_viewer_over_duration():
    from src.documentary.formats.check_als.storytelling_check import get_check_master_prompt
    from src.documentary.storytelling_engine import get_master_prompt
    assert get_check_master_prompt('{}', vehicle_mode='business').endswith(VIEWER_BRIEF)
    assert get_master_prompt('Available research only.').endswith(VIEWER_BRIEF)


def test_scene_preserves_place_age_and_does_not_invent_luxury():
    from src.documentary.formats.check_als.visuals import apply_check_visual_layer, compose_image_prompt
    plan = {'visuals': [
        {'number': 1, 'narration_segment': 'Tienes 24 años. Editas tu primer video.',
         'action': 'protagonist cutting a video on an old laptop', 'environment': 'small bedroom studio in Lima'},
        {'number': 2, 'narration_segment': 'No saliste de ese cuarto. El cliente rechaza el video.',
         'action': 'same protagonist sees the rejected delivery', 'environment': 'same small bedroom studio in Lima'},
    ], 'visual_bible': {}, 'flow_batches': [], 'stats': {}}
    out = apply_check_visual_layer({'id': 'creator'}, plan)
    assert out['visuals'][1]['protagonist_age'] == 24
    assert out['visuals'][1]['environment'] == 'same small bedroom studio in Lima'
    assert 'paper millionaire' not in out['visuals'][1]['prompt']
    debt = compose_image_prompt({'action': 'protagonist facing a million-dollar debt',
                                 'moment_id': 'crack', 'environment': 'same office'},
                                {'protagonist_age': 24})
    assert 'PEAK LIFESTYLE IMPACT' not in debt


def test_failed_online_generation_preserves_previous_script(monkeypatch, tmp_path):
    from src.documentary import project
    from src.documentary.formats.check_als import script as scripts
    from src.documentary.formats.check_als.story_architect import finalize_architecture, approve_check_story
    from tests.test_check_als_story_architecture import _pilot_payload
    import pytest
    monkeypatch.setenv('FRAMEFACTORY_PROJECTS_DIR', str(tmp_path / 'projects'))
    monkeypatch.setattr(project, 'PROJECTS_ROOT', tmp_path / 'projects')
    p = project.create_project('Basket', content_format='check_als', project_id='preserve-script')
    p = finalize_architecture(p, _pilot_payload())
    p = approve_check_story(p)
    p['script'] = 'Previous usable story.'
    project.save_project(p)
    monkeypatch.setattr(scripts, 'openai_api_key', lambda: '')
    with pytest.raises(RuntimeError, match='Conservamos el anterior'):
        scripts.generate_check_script(p, use_llm=True)
    assert project.load_project(p['id'])['script'] == 'Previous usable story.'


def test_online_draft_never_uses_deterministic_length_padding(monkeypatch, tmp_path):
    import openai
    from src.documentary import project
    from src.documentary.formats.check_als import script as scripts
    from src.documentary.formats.check_als.story_architect import finalize_architecture, approve_check_story
    from tests.test_check_als_story_architecture import _pilot_payload
    monkeypatch.setenv('FRAMEFACTORY_PROJECTS_DIR', str(tmp_path / 'projects'))
    monkeypatch.setattr(project, 'PROJECTS_ROOT', tmp_path / 'projects')
    p = project.create_project('Basket', content_format='check_als', project_id='no-padding')
    p = approve_check_story(finalize_architecture(p, _pilot_payload()))
    # A short but substantive draft; fixed target length alone must not invoke padding.
    draft = 'Tienes 22 años. ' + ' '.join(
        f'En el día {i} revisas el pedido {i}, corriges su costo y entregas la copia al cliente {i}.'
        for i in range(1, 70))
    monkeypatch.setattr(scripts, 'openai_api_key', lambda: 'test-key')
    monkeypatch.setattr(openai, 'OpenAI', lambda **k: object())
    monkeypatch.setattr(scripts, '_chat_text', lambda *a, **k: draft)
    monkeypatch.setattr('src.documentary.narrative_review.review_narrative',
                        lambda *a, **k: {'findings': [], 'needs_rewrite': False})
    monkeypatch.setattr(scripts, 'validate_check_script', lambda *a, **k: (True, [], []))
    def forbid(*a, **k):
        raise AssertionError('Online generation must never pad a story')
    monkeypatch.setattr(scripts, 'lengthen_life_script', forbid)
    monkeypatch.setattr(scripts, 'pad_script_from_beats', forbid)
    result = scripts.generate_check_script(p, use_llm=True)
    assert not result['script_quality']['offline_fixture']
    assert 'esta vida pide ese sorbo' not in result['script']


def test_repeated_visual_changes_framing_not_the_story():
    from src.documentary.visual_plan import _dedupe_stills
    shot = dict(visual_type='FLOW_REENACTMENT', action='protagonist opens the overdue invoice',
                description='protagonist opens the overdue invoice', location='same shop counter')
    visuals = [dict(shot, number=1), dict(shot, number=2)]
    _dedupe_stills(visuals, {})
    assert visuals[1]['action'] == shot['action']
    assert visuals[1]['location'] == shot['location']
    assert visuals[1]['description'] != visuals[0]['description']


def test_story_design_has_viewer_priority_for_every_vehicle():
    from src.documentary.formats.check_als.story_vehicle import blueprint_system, beats_system
    from src.documentary.viewer_editorial import STORY_DESIGN_BRIEF
    for mode in ['sports_team', 'business', 'creator', 'freeform']:
        assert blueprint_system(mode).endswith(STORY_DESIGN_BRIEF)
        assert beats_system(mode).endswith(STORY_DESIGN_BRIEF)


def test_packaging_model_sees_actual_ending_and_promise_contract(monkeypatch):
    import json
    import openai
    from types import SimpleNamespace
    from src.documentary.youtube_pack import _generate_llm_check, _generate_llm
    from src.documentary.viewer_editorial import PACKAGING_BRIEF
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({'title': 'Specific story', 'alt_titles': [], 'description': '',
                                'thumbnail_text': '', 'thumbnail_prompt': ''})))])
    monkeypatch.setattr(openai, 'OpenAI', lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    ending = 'EL NEGOCIO NO SE VENDE: EL PROTAGONISTA RECHAZA LA OFERTA.'
    p = {'title': 'Story', 'script': 'A long opening. ' * 1100 + ending, 'content_format': 'check_als'}
    _generate_llm_check(p, 'test-key')
    p['content_format'] = 'documentary'
    _generate_llm(p, 'test-key')
    assert len(calls) == 2
    for call in calls:
        assert call['messages'][0]['content'].endswith(PACKAGING_BRIEF)
        data = json.loads(call['messages'][1]['content'])
        assert ending in data['script_ending']


def test_freeform_sports_premise_is_not_rewritten_as_a_creator(monkeypatch, tmp_path):
    from src.documentary import project
    from src.documentary.formats.check_als.story_architect import finalize_architecture, public_architecture
    from src.documentary.formats.check_als.story_sim import repair_architecture
    monkeypatch.setenv('FRAMEFACTORY_PROJECTS_DIR', str(tmp_path / 'projects'))
    monkeypatch.setattr(project, 'PROJECTS_ROOT', tmp_path / 'projects')
    p = project.create_project('Compras un club de básquet', content_format='check_als', project_id='free-club',
                               concept={'user_proposed': True, 'vehicle_type': 'freeform', 'premise': 'Compras un club de básquet.'})
    beats = [dict(beat_id=f'b{i:02d}', event=event, cause='Tu decisión anterior', consequence='Debes actuar', ops=[])
             for i, event in enumerate(['Entras al estadio vacío.', 'El utilero te da las llaves del vestuario.',
                                       'Los jugadores entrenan en la cancha.', 'Arreglas el techo antes del partido.',
                                       'La temporada termina y el club sigue abierto.'],1)]
    assert repair_architecture(blueprint={}, beats=beats, mode='freeform') == beats
    p = finalize_architecture(p, {'blueprint':{'user_premise':'Compras un club de básquet.', 'freeform':True}, 'beats':beats})
    shown = public_architecture(p)
    events = ' '.join(b['event'] for b in shown['beats'])
    assert 'estadio' in events
    assert 'vestuario' in events
    assert 'cancha' in events
    assert 'sala de edición' not in events
