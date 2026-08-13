"""Supabase Postgres sync for documentary projects across PCs."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.config_loader import BASE
from src.documentary.project import PROJECTS_ROOT, projects_root
from src.saas_sessions import OUTPUT_DIR, SESSIONS_PATH

# Skip huge / regenerable artifacts by default.
_SKIP_DIR_NAMES = {".git", "__pycache__", ".DS_Store"}
_SKIP_SUFFIXES = {".pyc", ".pyo"}
_MAX_FILE_BYTES = 90 * 1024 * 1024  # 90 MB (final.mp4)
_schema_ok = False


def _load_env() -> None:
    load_dotenv(BASE / ".env")
    for path in (BASE / ".env.local", BASE / "env.local"):
        if path.is_file():
            load_dotenv(path, override=True)


def database_url() -> str:
    _load_env()
    return (os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or "").strip()


def configured() -> bool:
    return bool(database_url())


def _connect_url(url: str) -> str:
    """Supabase requires TLS; pooler hangs without sslmode=require."""
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def _connect():
    import psycopg

    url = database_url()
    if not url:
        raise RuntimeError("DATABASE_URL no configurada (.env.local)")
    # Supabase pooler works better with prepare_threshold=None (PgBouncer).
    return psycopg.connect(
        _connect_url(url),
        prepare_threshold=None,
        connect_timeout=8,
    )


def ensure_schema() -> None:
    global _schema_ok
    if _schema_ok:
        return
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ff_blobs (
                  project_id TEXT NOT NULL,
                  rel_path TEXT NOT NULL,
                  sha256 TEXT NOT NULL,
                  content BYTEA NOT NULL,
                  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  PRIMARY KEY (project_id, rel_path)
                );
                CREATE TABLE IF NOT EXISTS ff_sessions_store (
                  id TEXT PRIMARY KEY DEFAULT 'default',
                  payload JSONB NOT NULL,
                  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        conn.commit()
    _schema_ok = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iter_project_files(root: Path) -> list[Path]:
    out: list[Path] = []
    if not root.is_dir():
        return out
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() in _SKIP_SUFFIXES:
            continue
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        out.append(path)
    return out


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _upsert_files(project_id: str, files: list[Path], root: Path) -> tuple[int, int]:
    uploaded = 0
    skipped = 0
    with _connect() as conn:
        with conn.cursor() as cur:
            for path in files:
                rel = path.relative_to(root).as_posix()
                data = path.read_bytes()
                digest = _sha256(data)
                cur.execute(
                    """
                    INSERT INTO ff_blobs (project_id, rel_path, sha256, content, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (project_id, rel_path) DO UPDATE SET
                      sha256 = EXCLUDED.sha256,
                      content = EXCLUDED.content,
                      updated_at = NOW()
                    """,
                    (project_id, rel, digest, data),
                )
                uploaded += 1
        conn.commit()
    return uploaded, skipped


def delete_paths(project_id: str, rel_paths: list[str]) -> dict[str, Any]:
    """Remove specific files from Supabase so deletes actually stick."""
    ensure_schema()
    rels = [str(p).replace("\\", "/") for p in rel_paths if str(p).strip()]
    if not rels:
        return {"ok": True, "deleted": 0, "at": _utc_now()}
    with _connect() as conn:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(rels))
            cur.execute(
                f"DELETE FROM ff_blobs WHERE project_id = %s AND rel_path IN ({placeholders})",
                (project_id, *rels),
            )
            n = cur.rowcount or 0
        conn.commit()
    return {"ok": True, "deleted": n, "at": _utc_now()}


def delete_image_blobs(project_id: str) -> dict[str, Any]:
    ensure_schema()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM ff_blobs WHERE project_id = %s AND rel_path LIKE %s",
                (project_id, "images/%"),
            )
            n = cur.rowcount or 0
        conn.commit()
    return {"ok": True, "deleted": n, "at": _utc_now()}


def push_paths(project_id: str, rel_paths: list[str]) -> dict[str, Any]:
    """Upload only the given relative files (e.g. project.json, images/007.png)."""
    ensure_schema()
    root = projects_root() / project_id
    files = [root / rel for rel in rel_paths if (root / rel).is_file()]
    uploaded, skipped = _upsert_files(project_id, files, root) if files else (0, 0)
    return {
        "project_id": project_id,
        "uploaded": uploaded,
        "unchanged": skipped,
        "total_local": len(files),
        "at": _utc_now(),
    }


def push_project(project_id: str, *, include_images: bool = False) -> dict[str, Any]:
    ensure_schema()
    root = projects_root() / project_id
    if not root.is_dir():
        raise FileNotFoundError(f"Proyecto no encontrado: {project_id}")
    files = _iter_project_files(root)
    if not include_images:
        files = [p for p in files if "images" not in p.relative_to(root).parts]
    uploaded, skipped = _upsert_files(project_id, files, root)
    return {
        "project_id": project_id,
        "uploaded": uploaded,
        "unchanged": skipped,
        "total_local": len(files),
        "at": _utc_now(),
    }


_LIGHT_PREFIXES = (
    "project.json",
    "script/",
    "metadata/",
    "flow-pack/shot-list.json",
    "flow-pack/visual-plan.json",
    "flow-pack/story-bible.json",
)


def pull_project(project_id: str, *, light: bool = False) -> dict[str, Any]:
    ensure_schema()
    root = projects_root() / project_id
    root.mkdir(parents=True, exist_ok=True)
    written = 0
    with _connect() as conn:
        with conn.cursor() as cur:
            if light:
                cur.execute(
                    """
                    SELECT rel_path, sha256, content FROM ff_blobs
                    WHERE project_id = %s
                      AND (
                        rel_path = 'project.json'
                        OR rel_path LIKE 'script/%%'
                        OR rel_path LIKE 'metadata/%%'
                        OR rel_path IN (
                          'flow-pack/shot-list.json',
                          'flow-pack/visual-plan.json',
                          'flow-pack/story-bible.json'
                        )
                      )
                    """,
                    (project_id,),
                )
            else:
                cur.execute(
                    "SELECT rel_path, sha256, content FROM ff_blobs WHERE project_id = %s",
                    (project_id,),
                )
            rows = cur.fetchall()
    for rel, digest, content in rows:
        rel_s = str(rel)
        if light and not any(rel_s == p or rel_s.startswith(p) for p in _LIGHT_PREFIXES):
            continue
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            existing = path.read_bytes()
            if _sha256(existing) == digest:
                continue
        path.write_bytes(bytes(content))
        written += 1
    return {
        "project_id": project_id,
        "written": written,
        "total_remote": len(rows),
        "at": _utc_now(),
    }


def push_sessions() -> dict[str, Any]:
    ensure_schema()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SESSIONS_PATH.is_file():
        payload: dict[str, Any] = {"sessions": [], "active_id": None}
    else:
        payload = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ff_sessions_store (id, payload, updated_at)
                VALUES ('default', %s::jsonb, NOW())
                ON CONFLICT (id) DO UPDATE SET
                  payload = EXCLUDED.payload,
                  updated_at = NOW()
                """,
                (json.dumps(payload),),
            )
        conn.commit()
    return {"ok": True, "sessions": len(payload.get("sessions") or []), "at": _utc_now()}


def list_rel_paths(project_id: str, prefix: str = "") -> list[str]:
    ensure_schema()
    with _connect() as conn:
        with conn.cursor() as cur:
            if prefix:
                cur.execute(
                    "SELECT rel_path FROM ff_blobs WHERE project_id = %s AND rel_path LIKE %s",
                    (project_id, prefix + "%"),
                )
            else:
                cur.execute(
                    "SELECT rel_path FROM ff_blobs WHERE project_id = %s",
                    (project_id,),
                )
            return [str(r[0]) for r in cur.fetchall()]


def pull_one(project_id: str, rel_path: str) -> bool:
    """Download a single blob to disk. Used for still thumbnails."""
    ensure_schema()
    dest = projects_root() / project_id / rel_path
    if dest.is_file() and dest.stat().st_size > 0:
        return True
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content FROM ff_blobs WHERE project_id = %s AND rel_path = %s",
                (project_id, rel_path),
            )
            row = cur.fetchone()
    if not row:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(bytes(row[0]))
    return True


def pull_sessions() -> dict[str, Any]:
    ensure_schema()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT payload FROM ff_sessions_store WHERE id = 'default'")
            row = cur.fetchone()
    if not row:
        return {"ok": True, "written": False, "at": _utc_now()}
    payload = row[0]
    if isinstance(payload, str):
        payload = json.loads(payload)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "written": True,
        "sessions": len((payload or {}).get("sessions") or []),
        "at": _utc_now(),
    }


def list_remote_projects() -> list[str]:
    ensure_schema()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT project_id FROM ff_blobs ORDER BY project_id")
            return [r[0] for r in cur.fetchall()]


def push_all() -> dict[str, Any]:
    ensure_schema()
    root = projects_root()
    local_ids = [p.name for p in sorted(root.iterdir()) if p.is_dir() and (p / "project.json").is_file()]
    results = [push_project(pid) for pid in local_ids]
    sess = push_sessions()
    return {
        "ok": True,
        "projects": results,
        "sessions": sess,
        "projects_root": str(PROJECTS_ROOT),
        "at": _utc_now(),
    }


def pull_all(*, light: bool = False) -> dict[str, Any]:
    ensure_schema()
    remote = list_remote_projects()
    results = [pull_project(pid, light=light) for pid in remote]
    sess = pull_sessions()
    return {
        "ok": True,
        "projects": results,
        "sessions": sess,
        "remote_ids": remote,
        "projects_root": str(PROJECTS_ROOT),
        "at": _utc_now(),
    }


def status() -> dict[str, Any]:
    _load_env()
    ok = configured()
    info: dict[str, Any] = {
        "configured": ok,
        "projects_root": str(PROJECTS_ROOT),
        "supabase_url": (os.getenv("SUPABASE_URL") or "").strip() or None,
    }
    if not ok:
        info["detail"] = "Falta DATABASE_URL en .env.local"
        return info
    try:
        ensure_schema()
        remote = list_remote_projects()
        info["ok"] = True
        info["remote_projects"] = remote
        info["remote_count"] = len(remote)
        info["detail"] = "Conectado a Supabase"
    except Exception as exc:  # noqa: BLE001 — surface to Studio UI
        info["ok"] = False
        info["detail"] = str(exc)
    return info
