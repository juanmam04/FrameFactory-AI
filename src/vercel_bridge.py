"""Run Studio FastAPI inside a Vercel BaseHTTPRequestHandler."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_inner = None


def studio_app():
    global _inner
    if _inner is None:
        from src.documentary.runtime import configure_workspace

        configure_workspace()
        from studio.server import studio_app as inner

        _inner = inner
    return _inner


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        except Exception:
            pass
        asyncio.set_event_loop(None)


def invoke(
    method: str,
    path: str,
    body: bytes = b"",
    header_list: list[tuple[bytes, bytes]] | None = None,
) -> dict[str, Any]:
    parsed = urlparse(path)
    result: dict[str, Any] = {"status": 500, "headers": [], "body": b""}

    async def receive():
        return {"type": "http.request", "body": body or b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            result["status"] = int(message.get("status") or 500)
            result["headers"] = list(message.get("headers") or [])
        elif message["type"] == "http.response.body":
            result["body"] = result.get("body", b"") + (message.get("body") or b"")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "https",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": (parsed.query or "").encode("utf-8"),
        "headers": header_list or [(b"host", b"localhost")],
        "client": ("127.0.0.1", 0),
        "server": ("127.0.0.1", 443),
    }
    _run(studio_app()(scope, receive, send))
    return result


def json_bytes(obj: Any, status: int = 200) -> tuple[int, bytes, str]:
    raw = json.dumps(obj, default=str).encode()
    return status, raw, "application/json"


def minimal_bootstrap(err: str | None = None) -> dict[str, Any]:
    return {
        "runtime": {"vercel": True, "voice_render": False},
        "channel": {
            "name": "FrameFactory",
            "session_id": "",
            "tagline": (err[:240] if err else "100 Days Studio"),
        },
        "workspace": {
            "projects_dir": "/tmp/ff-projects",
            "data_dir": "/tmp/ff-data",
            "synced": False,
            "supabase": bool((os.getenv("DATABASE_URL") or "").strip()),
        },
        "stats": {"day": 1, "goal": 100, "completed": 0, "in_progress": 0, "remaining": 100},
        "projects": [],
        "credentials": {
            "openai": {"status": "error" if err else "unchecked", "detail": err or ""},
            "elevenlabs": {"status": "unchecked", "detail": ""},
            "ready_research": False,
            "ready_voice": False,
        },
        "boot_error": err,
    }


def dispatch(method: str, path: str, body: bytes, raw_headers: list[tuple[str, str]]) -> tuple[int, bytes, str]:
    headers = [(k.lower().encode(), v.encode()) for k, v in raw_headers]
    try:
        out = invoke(method, path, body, headers)
        status = int(out.get("status") or 500)
        payload = out.get("body") or b""
        ctype = "application/json"
        for k, v in out.get("headers") or []:
            if k.decode().lower() == "content-type":
                ctype = v.decode()
                break
        return status, payload, ctype
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        if "bootstrap" in path:
            return json_bytes(minimal_bootstrap(err), 200)
        return json_bytes({"detail": err}, 500)


def resolve_path(raw_path: str, headers: list[tuple[str, str]]) -> str:
    parsed = urlparse(raw_path)
    pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k != "__p"]
    orig = None
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        if k == "__p" and v.startswith("/"):
            orig = v
            break
    if not orig:
        for key, val in headers:
            if key.lower() in {"x-forwarded-uri", "x-invoke-path", "x-vercel-original-path"}:
                candidate = urlparse(val).path
                if candidate.startswith("/api/") and candidate not in {"/api", "/api/"}:
                    orig = candidate
                    break
    path = orig or parsed.path
    if path in {"/api", "/api/", "/api/index.py", "/api/index"}:
        path = orig or path
    query = urlencode(pairs)
    return urlunparse(("", "", path, "", query, ""))


def make_handler():
    class handler(BaseHTTPRequestHandler):
        def _read_body(self) -> bytes:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0:
                return b""
            return self.rfile.read(n)

        def _headers(self) -> list[tuple[str, str]]:
            return [(str(k), str(v)) for k, v in self.headers.items()]

        def _reply(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _go(self, method: str, body: bytes = b"") -> None:
            headers = self._headers()
            path = resolve_path(self.path, headers)
            status, raw, ctype = dispatch(method, path, body, headers)
            self._reply(status, raw, ctype)

        def do_GET(self):
            self._go("GET")

        def do_POST(self):
            self._go("POST", self._read_body())

        def do_PUT(self):
            self._go("PUT", self._read_body())

        def do_PATCH(self):
            self._go("PATCH", self._read_body())

        def do_DELETE(self):
            self._go("DELETE")

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def log_message(self, fmt, *args):
            return

    return handler
