"""Vercel Python entry — Documentary Studio only."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from src.documentary.runtime import configure_workspace

    configure_workspace()
    from studio.app import app  # noqa: E402
except Exception as exc:  # noqa: BLE001 — surface boot errors on Vercel
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse, PlainTextResponse

    app = FastAPI(title="FrameFactory boot error")
    _err = f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}"

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def _boot_failed(path: str = "") -> JSONResponse:
        return JSONResponse({"ok": False, "error": "boot_failed", "detail": _err}, status_code=500)

    @app.get("/")
    def _boot_failed_root() -> PlainTextResponse:
        return PlainTextResponse(_err, status_code=500)

__all__ = ["app"]
