"""Detect Vercel / cloud runtime and point workspace at ephemeral disk."""
from __future__ import annotations

import os
from pathlib import Path


def on_vercel() -> bool:
    return bool((os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or "").strip())


def configure_workspace() -> None:
    """Must run before importing project/saas_sessions path constants."""
    if not on_vercel():
        return
    os.environ.setdefault("FRAMEFACTORY_WORKSPACE", "/tmp/ff-workspace")
    os.environ.setdefault("FRAMEFACTORY_PROJECTS_DIR", "/tmp/ff-projects")
    os.environ.setdefault("FRAMEFACTORY_DATA_DIR", "/tmp/ff-data")
    for key in ("FRAMEFACTORY_WORKSPACE", "FRAMEFACTORY_PROJECTS_DIR", "FRAMEFACTORY_DATA_DIR"):
        Path(os.environ[key]).mkdir(parents=True, exist_ok=True)
