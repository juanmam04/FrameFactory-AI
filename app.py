"""Vercel FastAPI entrypoint (Documentary Studio)."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from src.documentary.runtime import configure_workspace

    configure_workspace()
    from studio.server import create_app

    app = create_app()
except Exception as exc:  # noqa: BLE001
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    app = FastAPI(title="FrameFactory boot error")
    _err = f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}"

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def _boot_failed(path: str = "") -> PlainTextResponse:
        return PlainTextResponse(_err, status_code=500)

try:
    from mangum import Mangum

    handler = Mangum(app)
except Exception:
    handler = app
