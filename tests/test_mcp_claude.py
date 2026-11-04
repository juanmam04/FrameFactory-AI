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


def test_openai_roundtrip(c, monkeypatch):
    cl, _ = c
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-" + "x" * 30)
    monkeypatch.setattr("src.documentary.openai_key.reload_env", lambda *a, **k: None)
    sent = {}

    def post(url, json=None, headers=None, timeout=None):
        sent.update(url=url, body=json)
        return R(200, {"model": json["model"], "choices": [{"finish_reason": "tool_calls", "message": {"content": "Miro.", "tool_calls": [
            {"id": "call_1", "type": "function", "function": {"name": "get_status", "arguments": "{\"x\":1}"}}]}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 5, "prompt_tokens_details": {"cached_tokens": 40}}})

    monkeypatch.setattr(mcp_claude.requests, "post", post)
    msgs = [{"role": "user", "content": "reglas"},
            {"role": "assistant", "content": [{"type": "text", "text": "a"}, {"type": "tool_use", "id": "t0", "name": "ver_plan", "input": {}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t0", "content": "{\"ok\":true}"}]}]
    r = call(cl, "openai_mensajes", {"model": "gpt-5-mini", "messages": msgs, "tools": [{"name": "get_status", "description": "d", "input_schema": {"type": "object", "properties": {}}}]})
    sc = r["structuredContent"]
    assert sc["stop_reason"] == "tool_use" and sc["content"][1] == {"type": "tool_use", "id": "call_1", "name": "get_status", "input": {"x": 1}}
    assert sc["usage"]["cache_read_input_tokens"] == 40
    b = sent["body"]
    assert sent["url"].startswith("https://api.openai.com") and b["tools"][0]["function"]["name"] == "get_status"
    assert b["messages"][1]["tool_calls"][0]["id"] == "t0" and b["messages"][2] == {"role": "tool", "tool_call_id": "t0", "content": "{\"ok\":true}"}
