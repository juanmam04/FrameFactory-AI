"""Shared OpenAI API key resolution for Documentary / LLM calls."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

from src.config_loader import BASE

_PLACEHOLDER_MARKERS = (
    "sk-your-",
    "your-openai-key",
    "your_openai_key",
    "changeme",
    "replace-me",
    "xxx",
)


def env_candidate_paths() -> list[Path]:
    """Order: base then local overrides. Later files win."""
    return [
        BASE / ".env",
        BASE / ".env.local",
        BASE / "env.local",
    ]


def reload_env() -> None:
    """Load `.env` then `.env.local` / `env.local` (local wins). Re-reads every call."""
    for path in env_candidate_paths():
        if path.is_file():
            load_dotenv(path, override=True)


def openai_api_key() -> str:
    """Return stripped OPENAI_API_KEY or '' if missing/placeholder."""
    reload_env()
    return (os.getenv("OPENAI_API_KEY") or "").strip()


def is_placeholder_key(key: str) -> bool:
    k = (key or "").strip()
    if not k:
        return True
    low = k.lower()
    if any(m in low for m in _PLACEHOLDER_MARKERS):
        return True
    # Real OpenAI keys are long; example file is ~23 chars.
    if len(k) < 40:
        return True
    return False


def _key_status_report() -> str:
    lines = []
    for path in env_candidate_paths():
        if not path.is_file():
            lines.append(f"- `{path}`: missing")
            continue
        vals = dotenv_values(path)
        v = (vals.get("OPENAI_API_KEY") or "").strip()
        if not v:
            lines.append(f"- `{path}`: OPENAI_API_KEY empty / not set")
        elif is_placeholder_key(v):
            lines.append(f"- `{path}`: OPENAI_API_KEY is still a PLACEHOLDER (not a real key)")
        else:
            lines.append(f"- `{path}`: OPENAI_API_KEY looks set (len={len(v)})")
    return "\n".join(lines)


def require_openai_api_key(purpose: str = "This feature") -> str:
    """Return a usable key or raise a clear RuntimeError (never leak the key)."""
    key = openai_api_key()
    if not key or is_placeholder_key(key):
        local = BASE / ".env.local"
        raise RuntimeError(
            f"{purpose} needs a REAL OpenAI API key.\n\n"
            f"Checked env files:\n{_key_status_report()}\n\n"
            f"Put your real key in `{local}` like:\n"
            f"OPENAI_API_KEY=sk-proj-...\n\n"
            f"Save, then click the button again. "
            f"FrameFactory loads `.env` then `.env.local` (local wins)."
        )
    return key


def env_file_path() -> Path:
    """Preferred path for the user to edit secrets."""
    for path in (BASE / ".env.local", BASE / "env.local", BASE / ".env"):
        if path.is_file():
            return path
    return BASE / ".env.local"
