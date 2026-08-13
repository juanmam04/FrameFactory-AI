"""Verify OPENAI + ElevenLabs keys from .env / .env.local (never prints secrets)."""
from __future__ import annotations

import os
import sys
import urllib.request

from src.config_loader import BASE
from src.documentary.openai_key import is_placeholder_key, openai_api_key, reload_env


def main() -> int:
    reload_env()
    print("Files:")
    for name in (".env", ".env.local"):
        p = BASE / name
        print(f"  {p}: {'OK' if p.is_file() else 'missing'}")

    oa = openai_api_key()
    el = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    print(f"\nOPENAI_API_KEY: {'set' if oa else 'MISSING'} len={len(oa)} placeholder={is_placeholder_key(oa)}")
    print(f"ELEVENLABS_API_KEY: {'set' if el else 'MISSING'} len={len(el)}")

    ok = True
    print("\nLive checks:")
    if not oa or is_placeholder_key(oa):
        print("  OpenAI: FAIL — paste a real key into .env.local")
        ok = False
    else:
        try:
            from openai import OpenAI

            OpenAI(api_key=oa).models.list()
            print("  OpenAI: OK")
        except Exception as e:
            print("  OpenAI: FAIL — provider rejected this key (create a NEW one)")
            print(f"    {type(e).__name__}: {str(e)[:160]}")
            ok = False

    if not el:
        print("  ElevenLabs: not set (optional if OpenAI TTS works)")
    else:
        try:
            req = urllib.request.Request(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": el},
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                print(f"  ElevenLabs: OK ({r.status})")
        except Exception as e:
            print("  ElevenLabs: FAIL — provider rejected this key (create a NEW one)")
            print(f"    {type(e).__name__}: {str(e)[:160]}")
            ok = False

    print(
        "\nFix:\n"
        "  1) https://platform.openai.com/api-keys → Create new secret key\n"
        "  2) https://elevenlabs.io → Profile → API key\n"
        f"  3) Paste into {BASE / '.env.local'}\n"
        "  4) Save, then run: python scripts/verify_keys.py\n"
        "  5) In Studio click Recheck"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
