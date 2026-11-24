"""Almacén del conector de voces: MP3 generados (servidos por URL firmada) y voces guardadas.

Con DATABASE_URL usa la tabla ff_blobs de Supabase (proyecto "_mcp_voz"), así funciona en
Vercel aunque cada pedido caiga en otra instancia. Sin base de datos usa output/mcp_voz en disco.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path

PROJECT = "_mcp_voz"
VOICES_PATH = "voces.json"
AUDIO_TTL = 7 * 24 * 3600  # los MP3 quedan 7 días


def _local_root() -> Path:
    try:
        from src.voice_generator import _audio_root

        root = _audio_root().parent / "mcp_voz"
    except Exception:  # noqa: BLE001
        root = Path("/tmp") / "mcp_voz"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cloud():
    try:
        from src.documentary import cloud_sync

        if cloud_sync.configured():
            cloud_sync.ensure_schema()
            return cloud_sync
    except Exception:  # noqa: BLE001 - sin nube se usa disco
        return None
    return None


def persistente() -> bool:
    """True si lo guardado sobrevive entre instancias (hay base de datos o no estamos en Vercel)."""
    return _cloud() is not None or not os.getenv("VERCEL")


def _put(rel: str, data: bytes) -> None:
    cs = _cloud()
    if cs is None:
        p = _local_root() / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return
    with cs._connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ff_blobs (project_id, rel_path, sha256, content, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (project_id, rel_path) DO UPDATE SET
              sha256 = EXCLUDED.sha256, content = EXCLUDED.content, updated_at = NOW()
            """,
            (PROJECT, rel, hashlib.sha256(data).hexdigest(), data),
        )
        if rel.startswith("audio/"):
            cur.execute(
                "DELETE FROM ff_blobs WHERE project_id = %s AND rel_path LIKE 'audio/%%' "
                "AND updated_at < NOW() - make_interval(secs => %s)",
                (PROJECT, AUDIO_TTL),
            )
        conn.commit()


def _get(rel: str) -> bytes | None:
    cs = _cloud()
    if cs is None:
        p = _local_root() / rel
        return p.read_bytes() if p.is_file() else None
    with cs._connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT content FROM ff_blobs WHERE project_id = %s AND rel_path = %s", (PROJECT, rel))
        row = cur.fetchone()
    return bytes(row[0]) if row else None


# ── audio ────────────────────────────────────────────────────────────────────

def _key() -> bytes:
    return ("voz-url:" + (os.getenv("FF_MCP_TOKEN") or "").strip()).encode()


def _sig(name: str, exp: int) -> str:
    return hmac.new(_key(), f"{name}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def guardar_audio(job: str, data: bytes, extra: dict[str, bytes] | None = None) -> None:
    _put(f"audio/{job}.mp3", data)
    for name, blob in (extra or {}).items():
        _put(f"audio/{job}.{name}", blob)


def url_firmada(base: str, name: str) -> str:
    exp = int(time.time()) + AUDIO_TTL
    return f"{base.rstrip('/')}/voz/{name}?exp={exp}&sig={_sig(name, exp)}"


def leer_archivo_firmado(name: str, exp: str, sig: str) -> bytes | None:
    if not re.fullmatch(r"[a-f0-9]{12}\.(mp3|json)", name or ""):
        return None
    try:
        e = int(exp)
    except (TypeError, ValueError):
        return None
    if e < time.time() or not hmac.compare_digest(_sig(name, e), str(sig or "")):
        return None
    return _get(f"audio/{name}")


# ── voces guardadas ──────────────────────────────────────────────────────────

# Voces que ya estaban en Voice Lab antes de existir guardar_voz.
_BASE_VOICES = [{"nombre": "Juanma", "voice_id": "YKUjKbMlejgvkOZlnnvt"}]


def _guardadas() -> list[dict]:
    raw = _get(VOICES_PATH)
    if not raw:
        return []
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return []
    return [v for v in data if isinstance(v, dict) and v.get("voice_id")]


def listar_voces() -> list[dict]:
    """Voces del catálogo + las de Voice Lab + las guardadas con guardar_voz (sin repetir IDs)."""
    from src.catalog_service import VOICES

    out: list[dict] = []
    seen: set[str] = set()

    def add(nombre: str, vid: str, origen: str) -> None:
        if vid and vid not in seen:
            seen.add(vid)
            out.append({"nombre": nombre, "voice_id": vid, "origen": origen})

    default = (os.getenv("ELEVENLABS_VOICE_ID") or "").strip()
    if default:
        add("Voz por defecto (ELEVENLABS_VOICE_ID)", default, "env")
    for v in VOICES.values():
        if v.get("provider") == "elevenlabs" and v.get("elevenlabs_voice_id"):
            add(v["name"], v["elevenlabs_voice_id"], "catalogo")
    for v in _BASE_VOICES:
        add(v["nombre"], v["voice_id"], "voice_lab")
    for v in _guardadas():
        add(str(v.get("nombre") or v["voice_id"]), str(v["voice_id"]), "guardada")
    return out


def guardar_voz(nombre: str, voice_id: str) -> list[dict]:
    """Agrega o renombra una voz guardada. Devuelve la lista guardada completa."""
    items = [v for v in _guardadas() if v.get("voice_id") != voice_id]
    items.append({"nombre": nombre, "voice_id": voice_id, "guardada_en": int(time.time())})
    _put(VOICES_PATH, json.dumps(items, ensure_ascii=False, indent=1).encode("utf-8"))
    return items
