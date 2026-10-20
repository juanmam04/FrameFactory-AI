"""Exercise Studio upload, voice, render, resume status and downloadable MP4.

External paid providers use fixtures; media encoding and HTTP endpoints are real.
"""
import io
import json
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='requires FFmpeg')
@pytest.mark.parametrize('editorial', [False, True])
def test_episode_upload_voice_render_download(monkeypatch, tmp_path, editorial):
    from src.documentary import project, voice_service, captions, assemble_service
    from src.documentary.channel import business_documentary_profile
    from src.documentary.flow_pack import export_flow_pack, load_shot_list
    from src.documentary.script_service import generate_documentary_script, approve_script
    from studio.server import create_app

    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.delenv('VERCEL_ENV', raising=False)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_DB_URL', raising=False)
    monkeypatch.setenv('FRAMEFACTORY_PROJECTS_DIR', str(tmp_path / 'projects'))
    monkeypatch.setattr(project, 'PROJECTS_ROOT', tmp_path / 'projects')
    p = project.create_project('WeWork story', project_id='episode-test', target_words=800,
                               creative_profile=business_documentary_profile())
    p = generate_documentary_script(p, use_llm=False)
    if editorial:
        from studio.editorial import fresh
        from tests.test_editorial_end_to_end import stages
        ed=fresh()
        ed["stages"]["brief"]={"data":{"language":"es","premise":"Comprás un hotel", "narration":"segunda persona", "tone":"cinematográfico", "duration_min":[20,25]},"approved":True}
        for stage, data in stages().items():
            ed["stages"][stage]={"data":data,"approved":True}
        p["editorial"]=ed
        p["editorial_audit"]={"verdict":"pass"}
        p["language"]="es"
        project.save_project(p)
    approve_script(p)
    export_flow_pack(project.load_project(p['id']), use_llm=False, rebuild_visuals=True)
    shots = load_shot_list(p['id'])['shots']
    client = TestClient(create_app())
    url = f"/api/projects/{p['id']}"
    files = []
    for shot in shots:
        buf = io.BytesIO()
        Image.new('RGB', (640, 360), (int(shot['number']) * 7 % 255, 40, 100)).save(buf, format='PNG')
        files.append(('files', (f"{int(shot['number']):03d}.png", buf.getvalue(), 'image/png')))
    uploaded = client.post(url + '/images/upload', files=files)
    assert uploaded.status_code == 200, uploaded.text

    audio = tmp_path / 'fixture.mp3'
    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100',
                    '-t', '6', str(audio)], check=True, capture_output=True)
    monkeypatch.setattr(voice_service, 'generar_voz', lambda *a, **k: audio)
    # The fixture tone is not speech; only external speech verification is stubbed.
    monkeypatch.setattr(voice_service, '_assert_voice_follows_script', lambda *a, **k: None)
    monkeypatch.setattr(captions, 'whisper_srt_from_audio',
                        lambda *a, **k: '1\n00:00:00,000 --> 00:00:06,000\nWeWork story.\n')
    monkeypatch.setattr(assemble_service, '_encode_profile',
                        lambda **k: (640, 360, 24, 23, 'veryfast', None, 'test 360p'))
    voiced = client.post(url + '/voice')
    assert voiced.status_code == 200, voiced.text
    rendered = client.post(url + '/render')
    assert rendered.status_code == 200, rendered.text
    saved = project.load_project(p['id'])
    assert saved['checkpoints']['render_ready']
    assert saved['render']['state'] == 'done'
    status = client.get(url + '/video/status')
    assert status.status_code == 200, status.text
    download = client.get(url + '/video?download=1')
    assert download.status_code == 200, download.text
    assert 'attachment' in download.headers['content-disposition']
    output = tmp_path / 'download.mp4'
    output.write_bytes(download.content)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                            'format=duration:stream=codec_type', '-of', 'json', str(output)],
                            check=True, capture_output=True, text=True)
    media = json.loads(probe.stdout)
    assert abs(float(media['format']['duration']) - 6) < 0.5
    assert {s['codec_type'] for s in media['streams']} == {'video', 'audio'}
