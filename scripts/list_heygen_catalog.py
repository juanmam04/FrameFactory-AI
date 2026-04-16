"""Lista avatares y talking photos de HeyGen usando HEYGEN_API_KEY del .env."""
from __future__ import annotations

import argparse
import json
import os
import sys

import requests
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(ROOT, ".env"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Listar avatares HeyGen (primeros N por defecto).")
    parser.add_argument("--limit", type=int, default=30, help="Máximo de avatares a imprimir (default 30).")
    parser.add_argument("--all", action="store_true", help="Imprimir todos los avatares (puede ser enorme).")
    args = parser.parse_args()
    api_key = os.getenv("HEYGEN_API_KEY", "").strip()
    if not api_key:
        print("Falta HEYGEN_API_KEY en .env (raíz del repo).", file=sys.stderr)
        return 1

    base = os.getenv("HEYGEN_BASE_URL", "https://api.heygen.com").rstrip("/")
    headers = {"X-Api-Key": api_key, "Accept": "application/json"}

    url = f"{base}/v2/avatars"
    r = requests.get(url, headers=headers, timeout=60)
    if r.status_code >= 400:
        print(f"Error {r.status_code}: {r.text[:500]}", file=sys.stderr)
        return 1

    body = r.json()
    if body.get("error"):
        print(f"API error: {body.get('error')}", file=sys.stderr)
        return 1

    data = body.get("data") or {}
    avatars = data.get("avatars") or []
    photos = data.get("talking_photos") or []
    total = len(avatars)
    limit = total if args.all else max(1, min(args.limit, total))
    shown = avatars[:limit]

    print("=== Avatares (usá el valor en HEYGEN_AVATAR_ID) ===\n")
    if not args.all and total > limit:
        print(f"(Mostrando {limit} de {total}. Usá --limit N o --all para ver más.)\n")
    for a in shown:
        aid = a.get("avatar_id")
        name = a.get("avatar_name", "")
        voice = a.get("default_voice_id") or ""
        print(f"  HEYGEN_AVATAR_ID={aid}")
        print(f"    nombre: {name}")
        if voice:
            print(f"    voz por defecto (HeyGen): {voice}")
        print()

    print("=== Talking photos / foto-avatar (id distinto) ===\n")
    print("Si tu cuenta solo muestra esto, puede que necesites un avatar de lista o")
    print("configurar en HeyGen Studio un photo avatar y volver a listar.\n")
    photo_limit = len(photos) if args.all else min(20, len(photos))
    for p in photos[:photo_limit]:
        pid = p.get("talking_photo_id")
        name = p.get("talking_photo_name", "")
        print(f"  talking_photo_id={pid}")
        print(f"    nombre: {name}")
        print()

    if not avatars and not photos:
        print("La API respondió OK pero no hay avatars ni talking_photos en data.")
        print("Respuesta cruda (primeros 800 chars):")
        print(json.dumps(body, ensure_ascii=False)[:800])
        return 2

    print("--- Copiar al .env (ejemplo) ---")
    if avatars:
        first = avatars[0].get("avatar_id", "")
        if first:
            print(f"HEYGEN_AVATAR_ID={first}")
    print("HEYGEN_USE_INPUT_AUDIO=true")
    print("CHARACTER_ANIMATOR_PROVIDER=heygen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
