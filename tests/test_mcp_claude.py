import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from studio import mcp_claude, mcp_voice

TOKEN = "t" * 32


class R:
    def __init__(self, status, js=None, text=""):
        self.status_code, self._js, self.text = status, js or {}, text

    def json(self):
        return self._js


@pytest.fixture()
def c(monkeypatch):
    monkeypatch.setenv("FF_MCP_TOKEN", TOKEN)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-1234")
    sent = {}

    def post(url, json=None, headers=None, timeout=None):
        sent.update(url=url, body=json, headers=headers)
        return R(200, {"model": json["model"], "content": [{"type": "text", "text": "hola"}], "stop_reason": "end_turn", "usage": {"input_tokens": 10}})

    monkeypatch.setattr(mcp_claude.requests, "post", post)
    app = FastAPI()
    app.include_router(mcp_voice.router)
    return TestClient(app), sent


def call(cl, name, args):
    return cl.post(f"/mcp/{TOKEN}", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}).json()["result"]


def test_mensajes_forwards_with_key_and_cache(c):
    cl, sent = c
    big = "x" * 5000
    r = call(cl, "claude_mensajes", {"model": "claude-haiku-5-5", "messages": [{"role": "user", "content": big}], "tools": [{"name": "t", "input_schema": {"type": "object"}}]})
    assert r["structuredContent"]["content"][0]["text"] == "hola"
    assert sent["headers"]["x-api-key"] == "sk-ant-test-1234"
    assert sent["body"]["model"] == "claude-haiku-5-5" and sent["body"]["tools"]
    assert sent["body"]["messages"][0]["content"][0]["cache_control"]["type"] == "ephemeral"


def test_bad_model_defaults(c):
    cl, sent = c
    call(cl, "claude_mensajes", {"model": "gpt", "messages": [{"role": "user", "content": "hola"}]})
    assert sent["body"]["model"] == mcp_claude.DEFAULT


def test_sin_key(c, monkeypatch):
    cl, _ = c
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    r = call(cl, "claude_mensajes", {"messages": [{"role": "user", "content": "hola"}]})
    assert r["isError"] and r["structuredContent"]["falta"] == "ANTHROPIC_API_KEY"


def test_estado(c):
    cl, _ = c
    assert call(cl, "claude_estado", {})["structuredContent"]["termina_en"] == "1234"
