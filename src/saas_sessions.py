"""Sesiones de trabajo: chat + perfil + memoria resumida; persistencia en disco."""
from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

import os

from dotenv import load_dotenv

from .config_loader import BASE
from .saas_creative_profile import merge_profile_disk

load_dotenv(BASE / ".env")
for _env_local in (BASE / ".env.local", BASE / "env.local"):
    if _env_local.is_file():
        load_dotenv(_env_local, override=True)


def _resolve_dir(env_name: str, default: Path) -> Path:
    raw = (os.getenv(env_name) or "").strip().strip('"').strip("'")
    if not raw:
        return default
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (BASE / p).resolve()
    return p


_WORKSPACE = _resolve_dir("FRAMEFACTORY_WORKSPACE", BASE)
if (os.getenv("FRAMEFACTORY_DATA_DIR") or "").strip():
    OUTPUT_DIR = _resolve_dir("FRAMEFACTORY_DATA_DIR", _WORKSPACE / "output")
else:
    OUTPUT_DIR = _WORKSPACE / "output"
SESSIONS_PATH = OUTPUT_DIR / "saas_sessions.json"
LEGACY_CHAT = OUTPUT_DIR / "saas_agent_chat.json"
LEGACY_PROFILE = OUTPUT_DIR / "saas_creative_profile.json"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_assistant_opening() -> list[dict[str, str]]:
    return [{"role": "assistant", "content": "Hola. ¿Qué tipo de videos querés publicar en esta sesión?"}]


def new_session_doc(title: str = "Nueva sesión", profile: dict[str, Any] | None = None) -> dict[str, Any]:
    sid = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"
    return {
        "id": sid,
        "title": (title or "Nueva sesión").strip()[:120] or "Nueva sesión",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "memory_summary": "",
        "messages": _default_assistant_opening(),
        "creative_profile": merge_profile_disk(profile),
    }


def load_store() -> dict[str, Any]:
    base: dict[str, Any] = {"version": 1, "active_id": None, "sessions": []}
    if not SESSIONS_PATH.exists():
        return dict(base)
    try:
        raw = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return dict(base)
        out = dict(base)
        out.update(raw)
        if not isinstance(out.get("sessions"), list):
            out["sessions"] = []
        return out
    except Exception:
        return dict(base)


def save_store(store: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    store = dict(store)
    store["version"] = 1
    SESSIONS_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def _session_by_id(store: dict[str, Any], sid: str | None) -> dict[str, Any] | None:
    if not sid:
        return None
    for s in store.get("sessions") or []:
        if isinstance(s, dict) and str(s.get("id")) == str(sid):
            return s
    return None


def get_session(store: dict[str, Any], sid: str | None) -> dict[str, Any] | None:
    return _session_by_id(store, sid)


def migrate_legacy_into_store(store: dict[str, Any]) -> dict[str, Any]:
    """Si no hay sesiones, importa chat/perfil legacy a la primera sesión."""
    if store.get("sessions"):
        return store
    messages = None
    profile = None
    if LEGACY_CHAT.exists():
        try:
            raw = json.loads(LEGACY_CHAT.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("messages"), list) and raw["messages"]:
                messages = raw["messages"]
        except Exception:
            pass
    if LEGACY_PROFILE.exists():
        try:
            raw = json.loads(LEGACY_PROFILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("profile"), dict):
                profile = raw["profile"]
        except Exception:
            pass
    doc = new_session_doc("Sesión importada", profile)
    if messages:
        doc["messages"] = messages
    store["sessions"] = [doc]
    store["active_id"] = doc["id"]
    save_store(store)
    return store


def ensure_store() -> dict[str, Any]:
    store = load_store()
    store = migrate_legacy_into_store(store)
    if not store.get("sessions"):
        doc = new_session_doc("Sesión 1", None)
        store["sessions"] = [doc]
        store["active_id"] = doc["id"]
        save_store(store)
    if not store.get("active_id") or not _session_by_id(store, store.get("active_id")):
        first = (store.get("sessions") or [None])[0]
        if isinstance(first, dict) and first.get("id"):
            store["active_id"] = first["id"]
            save_store(store)
    return store


def persist_session(store: dict[str, Any], sid: str, messages: list[dict], profile: dict[str, Any]) -> dict[str, Any]:
    prof = merge_profile_disk(profile)
    for s in store.get("sessions") or []:
        if not isinstance(s, dict):
            continue
        if str(s.get("id")) != str(sid):
            continue
        s["messages"] = list(messages)
        s["creative_profile"] = prof
        s["updated_at"] = _now_iso()
        break
    save_store(store)
    return store


def persist_session_summary(store: dict[str, Any], sid: str, summary: str) -> dict[str, Any]:
    for s in store.get("sessions") or []:
        if not isinstance(s, dict):
            continue
        if str(s.get("id")) != str(sid):
            continue
        s["memory_summary"] = str(summary).strip()[:12000]
        s["updated_at"] = _now_iso()
        break
    save_store(store)
    return store


def set_active_session(store: dict[str, Any], sid: str) -> dict[str, Any] | None:
    if not _session_by_id(store, sid):
        return None
    store["active_id"] = sid
    save_store(store)
    return _session_by_id(store, sid)


def add_session(store: dict[str, Any], title: str, seed_profile: dict[str, Any] | None) -> tuple[dict[str, Any], str]:
    doc = new_session_doc(title, seed_profile)
    sessions = list(store.get("sessions") or [])
    sessions.insert(0, doc)
    store["sessions"] = sessions[:80]
    store["active_id"] = doc["id"]
    save_store(store)
    return store, doc["id"]


def rename_session(store: dict[str, Any], sid: str, title: str) -> bool:
    for s in store.get("sessions") or []:
        if isinstance(s, dict) and str(s.get("id")) == str(sid):
            s["title"] = (title or "").strip()[:120] or s.get("title", "Sesión")
            s["updated_at"] = _now_iso()
            save_store(store)
            return True
    return False


def build_pipeline_session_context(session: dict[str, Any] | None, max_user_snippets: int = 12, max_chars_per_msg: int = 900) -> str:
    """Texto compacto para guion + plan de montaje (congelado al disparar render)."""
    if not session or not isinstance(session, dict):
        return ""
    parts: list[str] = []
    summ = (session.get("memory_summary") or "").strip()
    if summ:
        parts.append("RESUMEN DE LA SESIÓN (memoria larga):\n" + summ[:8000])
    users = [m for m in session.get("messages") or [] if isinstance(m, dict) and m.get("role") == "user"]
    tail = users[-max_user_snippets:]
    if tail:
        lines = []
        for m in tail:
            c = (m.get("content") or "").strip().replace("\r\n", "\n")
            if len(c) > max_chars_per_msg:
                c = c[:max_chars_per_msg] + "…"
            lines.append(c)
        parts.append("PEDIDOS Y ACLARACIONES DEL USUARIO (orden cronológico, últimos):\n" + "\n---\n".join(lines))
    asst = [m for m in session.get("messages") or [] if isinstance(m, dict) and m.get("role") == "assistant"]
    tail_a = asst[-6:]
    if tail_a:
        lines_a = []
        for m in tail_a:
            c = (m.get("content") or "").strip().replace("\r\n", "\n")
            if len(c) > max_chars_per_msg:
                c = c[:max_chars_per_msg] + "…"
            lines_a.append(c)
        parts.append("COMPROMISOS / ORIENTACIÓN DE LA IA (últimas respuestas):\n" + "\n---\n".join(lines_a))
    return "\n\n".join(parts).strip()


def summarize_session_messages(client: Any, messages: list[dict], previous_summary: str) -> str:
    """Condensa el historial para memoria larga (no reemplaza mensajes en disco)."""
    import os

    system = (
        "Sos un archivero de contexto para producción de video. Español. "
        "Condensá en texto claro (viñetas o párrafos cortos) TODO lo relevante acordado: "
        "nicho, tono, decisiones de estilo, formato, montaje, prohibiciones, nombres propios, fechas, "
        "números y promesas hechas al usuario. No inventes. Máximo 3500 caracteres. "
        "Si hay resumen previo, fusioná sin duplicar; priorizá lo más reciente."
    )
    payload = {
        "resumen_previo": (previous_summary or "").strip()[:6000],
        "mensajes": messages[-80:],
    }
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.25,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    return (r.choices[0].message.content or "").strip()[:12000]
