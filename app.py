"""Vercel FastAPI entrypoint. Ping never imports Studio."""
from __future__ import annotations

import os
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="FrameFactory")


@app.get("/api/ping")
def ping():
    return {
        "ok": True,
        "entry": "app.py",
        "vercel": bool(os.getenv("VERCEL")),
        "has_openai": bool((os.getenv("OPENAI_API_KEY") or "").strip()),
        "has_database": bool((os.getenv("DATABASE_URL") or "").strip()),
    }


@app.get("/health")
def health():
    return {"ok": True, "app": "framefactory", "entry": "app.py"}


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def studio_proxy(full_path: str, request: Request):
    try:
        from src.vercel_bridge import dispatch

        body = await request.body()
        headers = [(str(k), str(v)) for k, v in request.headers.items()]
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"
        status, raw, ctype = dispatch(request.method, path, body, headers)
        return Response(content=raw, status_code=status, media_type=ctype)
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        if "bootstrap" in (full_path or ""):
            from src.vercel_bridge import json_bytes, minimal_bootstrap

            status, raw, ctype = json_bytes(minimal_bootstrap(err), 200)
            return Response(content=raw, status_code=status, media_type=ctype)
        return JSONResponse({"detail": err}, status_code=500)
