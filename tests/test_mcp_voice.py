import base64
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from studio import mcp_voice

TOKEN = "t" * 32


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("FF_MCP_TOKEN", TOKEN)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k" * 40)
    monkeypatch.setattr("src.documentary.openai_key.reload_env", lambda *a, **k: None)

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr("studio.voice_store._local_root", lambda: tmp_path)
    calls = []

    def fake_tts(texto, voice_id, api_key, *, model_id=None, voice_settings=None, timeout=None):
        calls.append({"texto": texto, "voice_id": voice_id, "model_id": model_id, "voice_settings": voice_settings})
        chars = list(texto)
        starts = [i * 0.1 for i in range(len(chars))]
        ends = [s + 0.1 for s in starts]
        al = {"characters": chars, "character_start_times_seconds": starts, "character_end_times_seconds": ends}
        sent = dict(voice_settings or {})
        if model_id == "eleven_v3" and "stability" in sent:
            sent["stability"] = min((0.0, 0.5, 1.0), key=lambda v: abs(v - sent["stability"]))
        return b"ID3fakeaudio", al, {"model_id": model_id or "eleven_multilingual_v2", **sent}

    # velocidad: sin FFmpeg en tests, el helper devuelve el original (1.0 aplicada)
    monkeypatch.setattr("src.voice_generator.elevenlabs_tts_con_tiempos", fake_tts)
    monkeypatch.setattr("src.voice_generator._aplicar_velocidad_audio", lambda src, v, dst: src)
    app = FastAPI()
    app.include_router(mcp_voice.router)
    c = TestClient(app)
    c.calls = calls
    return c


def rpc(c, method, params=None, rid=1, token=TOKEN):
    return c.post(f"/mcp/{token}", json={"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})


def test_wrong_token_is_404(client):
    assert rpc(client, "tools/list", token="x" * 32).status_code == 404


def test_missing_token_env_is_404(client, monkeypatch):
    monkeypatch.delenv("FF_MCP_TOKEN")
    assert rpc(client, "tools/list").status_code == 404


def test_initialize_and_list(client):
    r = rpc(client, "initialize", {"protocolVersion": "2025-06-18"}).json()
    assert r["result"]["protocolVersion"] == "2025-06-18"
    names = [t["name"] for t in rpc(client, "tools/list").json()["result"]["tools"]]
    assert names[:4] == ["generar_voz", "listar_voces", "guardar_voz", "estado_voces"]


def test_notification_is_202(client):
    r = client.post(f"/mcp/{TOKEN}", json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert r.status_code == 202


def test_generar_voz_returns_base64(client):
    r = rpc(client, "tools/call", {"name": "generar_voz", "arguments": {"texto": "Hola, esto es una prueba de voz.", "entrega": "base64"}}).json()
    sc = r["result"]["structuredContent"]
    assert base64.b64decode(sc["audio_base64"]) == b"ID3fakeaudio"
    assert sc["mime"] == "audio/mpeg" and not r["result"].get("isError")


def test_too_long_is_tool_error(client):
    r = rpc(client, "tools/call", {"name": "generar_voz", "arguments": {"texto": "a" * 5000}}).json()
    assert r["result"]["isError"] is True


def test_generar_voz_base64_en_texto_opcional(client):
    r = rpc(client, "tools/call", {"name": "generar_voz", "arguments": {"texto": "Hola, esto es una prueba de voz.", "entrega": "base64"}}).json()
    assert len(r["result"]["content"]) == 1
    r = rpc(client, "tools/call", {"name": "generar_voz", "arguments": {"texto": "Hola, esto es una prueba de voz.", "base64_en_texto": True}}).json()
    blocks = r["result"]["content"]
    assert len(blocks) == 1 and "AUDIO_MP3_BASE64:" in blocks[0]["text"]
    assert base64.b64decode(blocks[0]["text"].split("AUDIO_MP3_BASE64:", 1)[1]) == b"ID3fakeaudio"


def test_generar_voz_url_tiempos_y_modelo(client):
    args = {
        "texto": "[laughs] Hola che",
        "voice_id": "TiySrlWKKU0DJXlzSyO0",
        "model_id": "eleven_v3",
        "voice_settings": {"stability": 0.35, "style": 0.5, "use_speaker_boost": True},
        "velocidad": 1,
    }
    r = rpc(client, "tools/call", {"name": "generar_voz", "arguments": args}).json()["result"]
    assert not r.get("isError"), r
    sc = r["structuredContent"]
    assert "audio_base64" not in sc and sc["model_id"] == "eleven_v3"
    assert sc["voice_settings"]["stability"] == 0.5  # v3 redondea a 0 / 0.5 / 1
    assert client.calls[-1]["voice_settings"] == {"stability": 0.35, "style": 0.5, "use_speaker_boost": True}
    assert [w["palabra"] for w in sc["tiempos"]] == ["[laughs]", "Hola", "che"]
    assert sc["tiempos"][0]["marca"] is True
    assert sc["tiempos"][1] == {"palabra": "Hola", "inicio": 0.9, "fin": 1.3}
    path = sc["audio_url"].split("testserver", 1)[1]
    assert client.get(path).content == b"ID3fakeaudio"
    assert client.get(sc["tiempos_url"].split("testserver", 1)[1]).json()["tiempos"][2]["palabra"] == "che"
    assert client.get(path.replace("sig=", "sig=0")).status_code == 404


def test_voice_settings_invalidos(client):
    r = rpc(client, "tools/call", {"name": "generar_voz", "arguments": {"texto": "Hola", "voice_settings": {"stabilty": 0.3}}}).json()
    assert r["result"]["isError"] is True


def test_listar_y_guardar_voz(client, monkeypatch):
    class R:
        status_code, ok = 200, True

        @staticmethod
        def json():
            return {"name": "Servo"}

    monkeypatch.setattr("studio.mcp_voice.requests.get", lambda *a, **k: R())
    r = rpc(client, "tools/call", {"name": "guardar_voz", "arguments": {"nombre": "Prueba", "voice_id": "abcdefghijABCDEFGHIJ"}}).json()
    assert r["result"]["structuredContent"]["verificada"] is True
    voces = rpc(client, "tools/call", {"name": "listar_voces", "arguments": {}}).json()["result"]["structuredContent"]["voces"]
    ids = {v["voice_id"]: v["nombre"] for v in voces}
    assert ids["abcdefghijABCDEFGHIJ"] == "Prueba"
    assert ids["TiySrlWKKU0DJXlzSyO0"] == "Voz reels servo hombre"


def test_guardar_voz_id_inexistente(client, monkeypatch):
    class R:
        status_code, ok = 404, False

    monkeypatch.setattr("studio.mcp_voice.requests.get", lambda *a, **k: R())
    r = rpc(client, "tools/call", {"name": "guardar_voz", "arguments": {"nombre": "X", "voice_id": "TiySrIWKKU0DJXlzSyO0"}}).json()
    assert r["result"]["isError"] is True and "l minúscula" in r["result"]["content"][0]["text"]
