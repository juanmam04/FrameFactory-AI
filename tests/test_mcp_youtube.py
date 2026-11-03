import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from studio import mcp_voice, mcp_youtube

TOKEN = "t" * 32
SESSION = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status&upload_id=abc"


class R:
    def __init__(self, status, js=None, headers=None, text=""):
        self.status_code, self._js, self.headers, self.text = status, js or {}, headers or {}, text

    def json(self):
        return self._js


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("FF_MCP_TOKEN", TOKEN)
    monkeypatch.setenv("YT_CLIENT_ID", "cid")
    monkeypatch.setenv("YT_CLIENT_SECRET", "sec")
    monkeypatch.setenv("YT_REFRESH_TOKEN", "ref")
    calls = []

    def post(url, **kw):
        calls.append(("POST", url, kw))
        if url == mcp_youtube.TOKEN_URL:
            return R(200, {"access_token": "acc", "refresh_token": "nuevo"})
        return R(200, headers={"Location": SESSION})

    def put(url, **kw):
        calls.append(("PUT", url, kw))
        if url.startswith(mcp_youtube.API):
            return R(200, {"status": {"privacyStatus": "private", "publishAt": "2026-11-04T21:00:00Z"}})
        rng = kw["headers"]["Content-Range"]
        end, total = rng.split(" ")[1].split("-")[1].split("/")
        if int(end) + 1 < int(total):
            return R(308, headers={"Range": f"bytes=0-{end}"})
        return R(200, {"id": "VID123", "status": {"privacyStatus": "private", "uploadStatus": "uploaded"}})

    def get(url, **kw):
        return R(200, {"items": [{"id": "UC1", "snippet": {"title": "CHECK"}}]})

    monkeypatch.setattr(mcp_youtube.requests, "post", post)
    monkeypatch.setattr(mcp_youtube.requests, "put", put)
    monkeypatch.setattr(mcp_youtube.requests, "get", get)
    app = FastAPI()
    app.include_router(mcp_voice.router)
    app.include_router(mcp_youtube.router)
    return TestClient(app, follow_redirects=False), calls


def call(c, name, args):
    r = c.post(f"/mcp/{TOKEN}", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})
    assert r.status_code == 200
    return r.json()["result"]


def test_tools_listed(env):
    c, _ = env
    r = c.post(f"/mcp/{TOKEN}", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).json()
    names = {t["name"] for t in r["result"]["tools"]}
    assert {"generar_voz", "youtube_iniciar_subida", "youtube_subir_parte", "youtube_estado", "youtube_cambiar_privacidad"} <= names


def test_estado(env):
    c, _ = env
    assert call(c, "youtube_estado", {})["structuredContent"]["canal"] == "CHECK"


def test_estado_sin_config(env, monkeypatch):
    c, _ = env
    monkeypatch.delenv("YT_REFRESH_TOKEN")
    r = call(c, "youtube_estado", {})
    assert r["structuredContent"]["falta"] == ["YT_REFRESH_TOKEN"]


def test_full_upload_scheduled(env):
    c, calls = env
    data = bytes(range(256)) * 4096 + b"fin"  # 1 MB + 3 bytes
    r = call(c, "youtube_iniciar_subida", {"titulo": "Prueba #Shorts", "bytes": len(data), "publicar_en": "2026-11-04T18:00:00-03:00"})
    sc = r["structuredContent"]
    assert sc["upload_url"] == SESSION and sc["privacidad"] == "private" and sc["publicar_en"].startswith("2026-11-04T18:00")
    body = [k for m, u, k in calls if m == "POST" and u == mcp_youtube.UPLOAD_INIT][0]["json"]
    assert body["status"]["publishAt"] and body["status"]["privacyStatus"] == "private"
    part = 512 * 1024
    pos = 0
    while True:
        chunk = data[pos:pos + part]
        out = call(c, "youtube_subir_parte", {"upload_url": SESSION, "inicio": pos, "total": len(data), "datos_base64": base64.b64encode(chunk).decode()})["structuredContent"]
        if out["terminado"]:
            break
        pos = out["siguiente"]
    assert out["video_id"] == "VID123"


def test_rechaza_url_ajena(env):
    c, _ = env
    r = call(c, "youtube_subir_parte", {"upload_url": "https://evil.example/x?upload_id=1", "inicio": 0, "total": 3, "datos_base64": "YWJj"})
    assert r["isError"]


def test_parte_no_multiplo(env):
    c, _ = env
    r = call(c, "youtube_subir_parte", {"upload_url": SESSION, "inicio": 0, "total": 10_000, "datos_base64": base64.b64encode(b"x" * 1000).decode()})
    assert r["isError"] and "262144" in r["content"][0]["text"]


def test_fecha_sin_zona(env):
    c, _ = env
    r = call(c, "youtube_iniciar_subida", {"titulo": "x", "bytes": 10, "publicar_en": "2026-11-04T18:00:00"})
    assert r["isError"]


def test_cambiar_privacidad(env):
    c, _ = env
    assert call(c, "youtube_cambiar_privacidad", {"video_id": "VID123", "publicar_en": "2026-11-04T18:00:00-03:00"})["structuredContent"]["ok"]


def test_conectar_y_callback(env):
    c, _ = env
    assert c.get("/youtube/conectar/" + "x" * 32).status_code == 404
    r = c.get(f"/youtube/conectar/{TOKEN}", headers={"host": "ff.example"})
    assert r.status_code in (302, 307) and "accounts.google.com" in r.headers["location"] and "ff.example%2Fyoutube%2Fcallback" in r.headers["location"]
    assert c.get("/youtube/callback?code=a&state=malo").status_code == 400
    ok = c.get(f"/youtube/callback?code=a&state={mcp_youtube._state_sig()}", headers={"host": "ff.example"})
    assert "nuevo" in ok.text
