"""Detect Vercel / cloud runtime and point workspace at ephemeral disk."""
from __future__ import annotations

import os
from pathlib import Path


def on_vercel() -> bool:
    return bool((os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or "").strip())


def configure_workspace() -> None:
    """Point project/session dirs at /tmp on Vercel (repo FS is read-only)."""
    if not on_vercel():
        return
    os.environ["FRAMEFACTORY_WORKSPACE"] = "/tmp/ff-workspace"
    os.environ["FRAMEFACTORY_PROJECTS_DIR"] = "/tmp/ff-projects"
    os.environ["FRAMEFACTORY_DATA_DIR"] = "/tmp/ff-data"
    for key in ("FRAMEFACTORY_WORKSPACE", "FRAMEFACTORY_PROJECTS_DIR", "FRAMEFACTORY_DATA_DIR"):
        Path(os.environ[key]).mkdir(parents=True, exist_ok=True)
    import sys

    proj = sys.modules.get("src.documentary.project")
    if proj is not None:
        proj.PROJECTS_ROOT = Path("/tmp/ff-projects")
        proj._WORKSPACE = Path("/tmp/ff-workspace")
    sess = sys.modules.get("src.saas_sessions")
    if sess is not None:
        sess.OUTPUT_DIR = Path("/tmp/ff-data")
        sess.SESSIONS_PATH = Path("/tmp/ff-data") / "saas_sessions.json"
        sess._WORKSPACE = Path("/tmp/ff-workspace")
