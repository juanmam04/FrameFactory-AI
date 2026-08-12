"""Credential preflight for Documentary — clear status, never leak secrets."""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal

from src.documentary.openai_key import (
    env_candidate_paths,
    is_placeholder_key,
    openai_api_key,
    reload_env,
)

Status = Literal["ok", "missing", "placeholder", "rejected", "unchecked", "error"]


@dataclass(frozen=True)
class KeyCheck:
    name: str
    status: Status
    detail: str


def check_openai(*, live: bool = True) -> KeyCheck:
    reload_env()
    key = openai_api_key()
    if not key:
        return KeyCheck("OpenAI", "missing", "OPENAI_API_KEY not set in .env / .env.local")
    if is_placeholder_key(key):
        return KeyCheck("OpenAI", "placeholder", "OPENAI_API_KEY is still the example placeholder")
    if not live:
        return KeyCheck("OpenAI", "unchecked", f"Present (len={len(key)}) — not live-checked")
    try:
        from openai import OpenAI

        OpenAI(api_key=key).models.list()
        return KeyCheck("OpenAI", "ok", "Authenticated")
    except Exception as e:
        msg = str(e)
        if "401" in msg or "invalid_api_key" in msg.lower() or "incorrect api key" in msg.lower():
            return KeyCheck(
                "OpenAI",
                "rejected",
                "OpenAI rejected this key (401). Create a new key at platform.openai.com/api-keys",
            )
        return KeyCheck("OpenAI", "error", f"Could not verify: {type(e).__name__}")


def check_elevenlabs(*, live: bool = True) -> KeyCheck:
    reload_env()
    key = (os.getenv("ELEVENLABS_API_KEY") or "").strip().strip('"').strip("'")
    if not key:
        return KeyCheck(
            "ElevenLabs",
            "missing",
            "Optional for voice — without it, OpenAI TTS is used if OpenAI works",
        )
    if key.startswith("sk_your") or "your-elevenlabs" in key.lower() or len(key) < 20:
        return KeyCheck("ElevenLabs", "placeholder", "ELEVENLABS_API_KEY looks like a placeholder")
    if not key.startswith("sk_"):
        return KeyCheck(
            "ElevenLabs",
            "rejected",
            "That value is not a secret key (must start with sk_). You pasted a key ID.",
        )
    if not live:
        return KeyCheck("ElevenLabs", "unchecked", f"Present (len={len(key)}) — not live-checked")

    # Restricted keys often lack user_read — probe TTS instead of /v1/user.
    import json

    voice = (os.getenv("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM").strip()
    body = json.dumps({"text": "ok", "model_id": "eleven_multilingual_v2"}).encode()
    try:
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
            data=body,
            headers={
                "xi-api-key": key,
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if resp.status == 200 and len(raw) > 100:
                return KeyCheck("ElevenLabs", "ok", "TTS authenticated")
            return KeyCheck("ElevenLabs", "error", f"Unexpected TTS response HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")[:240]
        except Exception:
            detail = str(e)
        low = detail.lower()
        if e.code == 402 or "payment_required" in low or "quota" in low:
            return KeyCheck(
                "ElevenLabs",
                "rejected",
                "Key is valid but ElevenLabs returned 402 Payment Required — add credits / fix billing.",
            )
        if e.code == 401 or "invalid_api_key" in low or "api_key_id_used" in low:
            return KeyCheck(
                "ElevenLabs",
                "rejected",
                "ElevenLabs rejected this key. Create a new secret key starting with sk_.",
            )
        if e.code == 404:
            return KeyCheck(
                "ElevenLabs",
                "error",
                "Voice ID not found — check ELEVENLABS_VOICE_ID in .env.local",
            )
        return KeyCheck("ElevenLabs", "error", f"HTTP {e.code}: {detail[:120]}")
    except Exception as e:
        return KeyCheck("ElevenLabs", "error", f"Could not verify: {type(e).__name__}")


def credential_report(*, live: bool = True) -> dict:
    oa = check_openai(live=live)
    el = check_elevenlabs(live=live)
    files = []
    for p in env_candidate_paths():
        files.append({"path": str(p), "exists": p.is_file()})
    ready_research = oa.status == "ok"
    ready_voice = oa.status == "ok" or el.status == "ok"
    return {
        "openai": oa,
        "elevenlabs": el,
        "files": files,
        "ready_research": ready_research,
        "ready_script": ready_research,
        "ready_voice": ready_voice,
    }


def format_auth_error(exc: BaseException, *, feature: str = "This step") -> str | None:
    """Map provider auth failures to a direct operator message. None = not an auth error."""
    msg = str(exc)
    low = msg.lower()
    if "402" in msg or "payment_required" in low or ("payment required" in low):
        return (
            f"{feature} failed: ElevenLabs Payment Required (402).\n"
            "Your key is recognized but the account has no credits / active plan. "
            "Top up at https://elevenlabs.io or leave ELEVENLABS_API_KEY empty to use OpenAI TTS."
        )
    if "401" in msg or "invalid_api_key" in low or "incorrect api key" in low:
        if "elevenlabs" in low or "xi-api-key" in low:
            return (
                f"{feature} failed: ElevenLabs rejected your API key.\n"
                "Use a secret key starting with sk_ (not the key ID), "
                "put it in `.env` + `.env.local`, save, Recheck."
            )
        return (
            f"{feature} failed: OpenAI rejected your API key (401).\n"
            "The key in `.env` / `.env.local` is expired, revoked, or wrong.\n"
            "1) https://platform.openai.com/api-keys → Create new secret key\n"
            "2) Paste into `.env.local` as OPENAI_API_KEY=sk-...\n"
            "3) Save the file (don't keep an old empty editor tab open)\n"
            "4) Click again — FrameFactory reloads keys automatically"
        )
    if "insufficient_quota" in low or "billing" in low:
        return (
            f"{feature} failed: OpenAI billing/quota issue. "
            "Check https://platform.openai.com/account/billing"
        )
    return None
