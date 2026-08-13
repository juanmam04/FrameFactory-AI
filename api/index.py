"""Vercel Python API — must import without crashing.

Do not import studio/server at module load. `/api/ping` stays alive even if Studio fails.
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app = FastAPI(title="FrameFactory API")


def _minimal_bootstrap(err: str | None = None) -> dict:
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
        "stats": {
            "day": 1,
            "goal": 100,
            "completed": 0,
            "in_progress": 0,
            "remaining": 100,
        },
        "projects": [],
        "credentials": {
            "openai": {
                "status": "unchecked" if not err else "error",
                "detail": err or "OpenAI is configured in Vercel env",
            },
            "elevenlabs": {"status": "unchecked", "detail": ""},
            "ready_research": False,
            "ready_voice": False,
        },
        "boot_error": err,
    }


@app.get("/api/ping")
@app.get("/ping")
@app.get("/api")
def ping():
    return {
        "ok": True,
        "entry": "api/index.py",
        "vercel": bool(os.getenv("VERCEL")),
        "has_openai": bool((os.getenv("OPENAI_API_KEY") or "").strip()),
        "has_database": bool((os.getenv("DATABASE_URL") or "").strip()),
    }


@app.get("/api/bootstrap")
@app.get("/bootstrap")
def bootstrap():
    try:
        from src.documentary.runtime import configure_workspace

        configure_workspace()
        from studio.server import create_app

        inner = create_app()
        for route in inner.routes:
            if getattr(route, "path", None) == "/api/bootstrap" and hasattr(route, "endpoint"):
                return route.endpoint()
        return _minimal_bootstrap("Studio loaded but /api/bootstrap route missing")
    except Exception as exc:  # noqa: BLE001
        return _minimal_bootstrap(f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def other(path: str, request: Request):
    if request.method == "OPTIONS":
        return JSONResponse({"ok": True})
    if path in {"api/ping", "ping", "api", ""}:
        return ping()
    if "bootstrap" in path:
        return bootstrap()
    return JSONResponse(
        {
            "detail": f"API route not wired on Vercel yet: /{path}",
            "hint": "Home/bootstrap should work. Other steps: use npm run dev on your Mac.",
        },
        status_code=404,
    )
