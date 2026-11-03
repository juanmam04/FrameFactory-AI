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

    def fake(texto, nombre_archivo="x", formato="mp3", velocidad=1.1, **kw):
        p = Path(tmp_path) / f"{nombre_archivo}.mp3"
        p.write_bytes(b"ID3fakeaudio")
        return p

    monkeypatch.setattr("src.voice_generator.generar_voz", fake)
    app = FastAPI()
    app.include_router(mcp_voice.router)
    return TestClient(app)


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
    assert names == ["generar_voz", "estado_voces"]


def test_notification_is_202(client):
    r = client.post(f"/mcp/{TOKEN}", json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert r.status_code == 202


def test_generar_voz_returns_base64(client):
    r = rpc(client, "tools/call", {"name": "generar_voz", "arguments": {"texto": "Hola, esto es una prueba de voz."}}).json()
    sc = r["result"]["structuredContent"]
    assert base64.b64decode(sc["audio_base64"]) == b"ID3fakeaudio"
    assert sc["mime"] == "audio/mpeg" and not r["result"].get("isError")


def test_too_long_is_tool_error(client):
    r = rpc(client, "tools/call", {"name": "generar_voz", "arguments": {"texto": "a" * 5000}}).json()
    assert r["result"]["isError"] is True
