"""Voice replacement must preserve a good take if verification fails."""
from pathlib import Path
import pytest
from src.documentary import project, voice_service
from src.documentary.voice_script_sync import word_overlap


@pytest.fixture()
def episode(monkeypatch, tmp_path):
    monkeypatch.setenv('FRAMEFACTORY_PROJECTS_DIR', str(tmp_path / 'projects'))
    monkeypatch.setattr(project, 'PROJECTS_ROOT', tmp_path / 'projects')
    p = project.create_project('Una vida', project_id='voice-test', language='es')
    p.update(script='Tienes veinte años y empiezas tu negocio.', script_approved=True)
    project.save_project(p)
    dest = project.project_dir(p['id']) / 'audio' / 'narration.mp3'
    dest.write_bytes(b'previous-good-take')
    return p, dest


def test_verification_failure_keeps_previous_take(monkeypatch, tmp_path, episode):
    p, dest = episode
    new = tmp_path / 'new.mp3'
    new.write_bytes(b'wrong-new-take')
    monkeypatch.setattr(voice_service, 'generar_voz', lambda *a, **k: new)
    def reject(*a, **k):
        assert k['language'] == 'es'
        raise RuntimeError('wrong script')
    monkeypatch.setattr(voice_service, '_assert_voice_follows_script', reject)
    with pytest.raises(RuntimeError, match='wrong script'):
        voice_service.generate_project_voice(p)
    assert dest.read_bytes() == b'previous-good-take'
    assert not project.load_project(p['id'])['checkpoints']['voice_ready']


def test_verified_spanish_take_is_saved(monkeypatch, tmp_path, episode):
    p, dest = episode
    new = tmp_path / 'new.mp3'
    new.write_bytes(b'new-good-take')
    languages = []
    monkeypatch.setattr(voice_service, 'generar_voz', lambda *a, **k: new)
    monkeypatch.setattr(voice_service, '_assert_voice_follows_script', lambda *a, **k: languages.append(k['language']))
    monkeypatch.setattr(voice_service, '_probe_duration', lambda _: 6.0)
    voice_service.generate_project_voice(p)
    saved = project.load_project(p['id'])
    assert languages == ['es']
    assert dest.read_bytes() == b'new-good-take'
    assert saved['checkpoints']['voice_ready']
    assert saved['voice']['duration_sec'] == 6


def test_accented_words_are_not_split_into_false_matches():
    assert word_overlap('años más', 'anos mas') == 0
    assert word_overlap('AÑOS más', 'años más') == 1
