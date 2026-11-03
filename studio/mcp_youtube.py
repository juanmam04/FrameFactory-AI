"""Subida a YouTube para el conector MCP de FrameFactory (API oficial YouTube Data v3).

Sin estado, para que funcione en Vercel: la subida es "resumable" y la URL de sesión que
devuelve Google viaja de vuelta al cliente, que manda el video por partes.

Variables de entorno:
  YT_CLIENT_ID, YT_CLIENT_SECRET  -> credenciales OAuth (Google Cloud, tipo "Aplicación web")
  YT_REFRESH_TOKEN                -> se obtiene una sola vez en /youtube/conectar/<FF_MCP_TOKEN>
  YT_REDIRECT_URI (opcional)      -> por defecto https://<host>/youtube/callback

Ojo: mientras el proyecto de Google Cloud no pase la auditoría de YouTube, todo lo que se
sube por la API queda en privado aunque se pida público.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import os
import re
import urllib.parse
from datetime import datetime
from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

SCOPE = "https://www.googleapis.com/auth/youtube"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
UPLOAD_INIT = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
UPLOAD_PREFIX = "https://www.googleapis.com/upload/youtube/v3/videos?"
API = "https://www.googleapis.com/youtube/v3"
CHUNK = 256 * 1024  # las partes intermedias tienen que ser múltiplo de 256 KB
MAX_PART = 4 * 1024 * 1024  # el cuerpo de una función de Vercel tiene tope de ~4,5 MB
PRIVACY = ("private", "unlisted", "public")

TOOLS = [
    {
        "name": "youtube_estado",
        "title": "Estado de YouTube",
        "description": "Dice si la subida a YouTube está configurada y a qué canal sube. No sube nada.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "youtube_iniciar_subida",
        "title": "Iniciar subida a YouTube",
        "description": (
            "Abre una subida de video a YouTube y devuelve upload_url. Después mandá el MP4 en partes con "
            "youtube_subir_parte (partes de 1 MB o 2 MB, múltiplo de 256 KB salvo la última). "
            "Por defecto queda en privado. Con publicar_en (fecha ISO) queda programado: privado hasta esa hora."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "titulo": {"type": "string", "description": "Título (máximo 100 caracteres). Para Shorts sumá #Shorts."},
                "descripcion": {"type": "string"},
                "etiquetas": {"type": "array", "items": {"type": "string"}},
                "privacidad": {"type": "string", "enum": list(PRIVACY), "description": "private (por defecto), unlisted o public."},
                "publicar_en": {"type": "string", "description": "Fecha y hora ISO 8601 con zona, por ejemplo 2026-11-04T18:00:00-03:00."},
                "bytes": {"type": "integer", "description": "Tamaño exacto del MP4 en bytes."},
                "idioma": {"type": "string", "description": "Idioma del video, por defecto es."},
            },
            "required": ["titulo", "bytes"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "youtube_subir_parte",
        "title": "Subir parte del video",
        "description": (
            "Manda una parte del MP4 a una subida abierta. inicio = byte donde empieza esta parte; total = tamaño "
            "del archivo. Devuelve siguiente (byte desde el que seguir) o, en la última parte, video_id y url."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "upload_url": {"type": "string"},
                "inicio": {"type": "integer"},
                "total": {"type": "integer"},
                "datos_base64": {"type": "string"},
            },
            "required": ["upload_url", "inicio", "total", "datos_base64"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "youtube_cambiar_privacidad",
        "title": "Cambiar privacidad",
        "description": "Cambia la privacidad de un video del canal (private, unlisted, public) o lo programa con publicar_en.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "video_id": {"type": "string"},
                "privacidad": {"type": "string", "enum": list(PRIVACY)},
                "publicar_en": {"type": "string"},
            },
            "required": ["video_id"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
]
NAMES = {t["name"] for t in TOOLS}


def _text(t: str, data: dict | None = None, error: bool = False) -> dict:
    out: dict = {"content": [{"type": "text", "text": t}]}
    if data is not None:
        out["structuredContent"] = data
    if error:
        out["isError"] = True
    return out


def _cfg() -> tuple[str, str, str]:
    return (
        (os.getenv("YT_CLIENT_ID") or "").strip(),
        (os.getenv("YT_CLIENT_SECRET") or "").strip(),
        (os.getenv("YT_REFRESH_TOKEN") or "").strip(),
    )


def _access_token() -> str:
    cid, sec, ref = _cfg()
    if not (cid and sec):
        raise RuntimeError("Faltan YT_CLIENT_ID y YT_CLIENT_SECRET en el servidor.")
    if not ref:
        raise RuntimeError("Falta YT_REFRESH_TOKEN: conectá el canal en /youtube/conectar/<clave>.")
    r = requests.post(TOKEN_URL, data={"client_id": cid, "client_secret": sec, "refresh_token": ref, "grant_type": "refresh_token"}, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Google no renovó el acceso ({r.status_code}): {r.text[:200]}")
    return r.json()["access_token"]


def _iso(s: Any) -> str | None:
    if not s:
        return None
    s = str(s).strip()
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"publicar_en «{s}» no es una fecha ISO 8601.")
    if d.tzinfo is None:
        raise ValueError("publicar_en tiene que llevar zona horaria, por ejemplo -03:00.")
    return d.isoformat()


def _status(privacy: Any, publish_at: Any) -> dict:
    p = str(privacy or "private")
    if p not in PRIVACY:
        raise ValueError(f"privacidad «{p}» no existe: private, unlisted o public.")
    st: dict = {"privacyStatus": p, "selfDeclaredMadeForKids": False}
    at = _iso(publish_at)
    if at:
        st["privacyStatus"] = "private"  # YouTube solo programa videos privados
        st["publishAt"] = at
    return st


def estado() -> dict:
    cid, sec, ref = _cfg()
    if not (cid and sec and ref):
        falta = [n for n, v in (("YT_CLIENT_ID", cid), ("YT_CLIENT_SECRET", sec), ("YT_REFRESH_TOKEN", ref)) if not v]
        return _text("YouTube no está configurado. Falta: " + ", ".join(falta) + ".", {"ok": False, "falta": falta})
    try:
        tok = _access_token()
        r = requests.get(f"{API}/channels", params={"part": "snippet", "mine": "true"}, headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        items = (r.json().get("items") or []) if r.status_code == 200 else []
    except Exception as e:  # noqa: BLE001
        return _text(f"YouTube configurado pero falló: {e}", {"ok": False}, error=True)
    if not items:
        return _text("La cuenta conectada no tiene canal.", {"ok": False})
    ch = items[0]
    return _text(f"Listo para subir a «{ch['snippet']['title']}».", {"ok": True, "canal": ch["snippet"]["title"], "canal_id": ch["id"]})


def iniciar(args: dict) -> dict:
    titulo = str(args.get("titulo") or "").strip()
    if not titulo:
        return _text("Falta el título.", error=True)
    if len(titulo) > 100:
        return _text(f"El título tiene {len(titulo)} caracteres; YouTube acepta 100.", error=True)
    try:
        size = int(args.get("bytes") or 0)
        st = _status(args.get("privacidad"), args.get("publicar_en"))
    except (TypeError, ValueError) as e:
        return _text(str(e), error=True)
    if size <= 0 or size > 2 * 1024**3:
        return _text("bytes tiene que ser el tamaño real del MP4.", error=True)
    tags = [str(t)[:60] for t in (args.get("etiquetas") or [])][:30]
    lang = re.sub(r"[^a-zA-Z-]", "", str(args.get("idioma") or "es"))[:8] or "es"
    body = {
        "snippet": {"title": titulo, "description": str(args.get("descripcion") or "")[:5000], "tags": tags, "categoryId": "27",
                    "defaultLanguage": lang, "defaultAudioLanguage": lang},
        "status": st,
    }
    try:
        tok = _access_token()
        r = requests.post(UPLOAD_INIT, json=body, timeout=30, headers={
            "Authorization": f"Bearer {tok}", "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4",
            "Content-Type": "application/json; charset=UTF-8"})
    except Exception as e:  # noqa: BLE001
        return _text(f"No se pudo abrir la subida: {e}", error=True)
    loc = r.headers.get("Location") or r.headers.get("location")
    if r.status_code != 200 or not loc:
        return _text(f"YouTube rechazó la subida ({r.status_code}): {r.text[:300]}", error=True)
    return _text("Subida abierta. Mandá el video con youtube_subir_parte desde el byte 0.",
                 {"ok": True, "upload_url": loc, "total": size, "parte_sugerida": 2 * 1024 * 1024, "privacidad": st["privacyStatus"], "publicar_en": st.get("publishAt")})


def subir_parte(args: dict) -> dict:
    url = str(args.get("upload_url") or "")
    if not url.startswith(UPLOAD_PREFIX) or "upload_id=" not in url:
        return _text("upload_url no es una sesión de subida de YouTube.", error=True)
    try:
        start, total = int(args.get("inicio")), int(args.get("total"))
        raw = base64.b64decode(str(args.get("datos_base64") or ""), validate=True)
    except Exception:  # noqa: BLE001
        return _text("inicio, total o datos_base64 no son válidos.", error=True)
    end = start + len(raw)
    if not raw or start < 0 or end > total:
        return _text("La parte no entra en el archivo (revisá inicio y total).", error=True)
    if len(raw) > MAX_PART:
        return _text(f"La parte pesa {len(raw)} bytes; el máximo es {MAX_PART}.", error=True)
    if end < total and len(raw) % CHUNK:
        return _text("Las partes que no son la última tienen que medir un múltiplo de 262144 bytes.", error=True)
    try:
        r = requests.put(url, data=raw, timeout=120, headers={"Content-Length": str(len(raw)), "Content-Range": f"bytes {start}-{end - 1}/{total}"})
    except Exception as e:  # noqa: BLE001
        return _text(f"Se cortó la subida de esta parte: {e}. Reintentá la misma parte.", {"ok": False, "siguiente": start}, error=True)
    if r.status_code == 308:
        rng = r.headers.get("Range") or r.headers.get("range") or ""
        m = re.search(r"bytes=0-(\d+)", rng)
        nxt = int(m.group(1)) + 1 if m else 0
        return _text(f"Parte recibida. Seguí desde el byte {nxt} de {total}.", {"ok": True, "terminado": False, "siguiente": nxt, "total": total})
    if r.status_code in (200, 201):
        v = r.json()
        vid = v.get("id")
        st = v.get("status") or {}
        return _text(f"Video subido: https://youtu.be/{vid} ({st.get('privacyStatus', '?')}).",
                     {"ok": True, "terminado": True, "video_id": vid, "url": f"https://youtu.be/{vid}", "privacidad": st.get("privacyStatus"),
                      "publicar_en": st.get("publishAt"), "estado_subida": st.get("uploadStatus")})
    return _text(f"YouTube rechazó la parte ({r.status_code}): {r.text[:300]}", {"ok": False, "siguiente": start}, error=True)


def cambiar_privacidad(args: dict) -> dict:
    vid = re.sub(r"[^A-Za-z0-9_-]", "", str(args.get("video_id") or ""))
    if not vid:
        return _text("Falta video_id.", error=True)
    try:
        st = _status(args.get("privacidad"), args.get("publicar_en"))
        tok = _access_token()
        r = requests.put(f"{API}/videos", params={"part": "status"}, json={"id": vid, "status": st}, headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    except Exception as e:  # noqa: BLE001
        return _text(str(e), error=True)
    if r.status_code != 200:
        return _text(f"YouTube no lo cambió ({r.status_code}): {r.text[:300]}", error=True)
    s = r.json().get("status") or {}
    return _text(f"Listo: {s.get('privacyStatus')}" + (f", programado para {s.get('publishAt')}" if s.get("publishAt") else "") + ".", {"ok": True, **s})


def call(name: str, args: dict) -> dict:
    if name == "youtube_estado":
        return estado()
    if name == "youtube_iniciar_subida":
        return iniciar(args)
    if name == "youtube_subir_parte":
        return subir_parte(args)
    if name == "youtube_cambiar_privacidad":
        return cambiar_privacidad(args)
    raise KeyError(name)


# ---------- conexión del canal (una sola vez) ----------

def _state_sig() -> str:
    key = (os.getenv("FF_MCP_TOKEN") or "").encode()
    return hmac.new(key, b"youtube-connect", hashlib.sha256).hexdigest()[:32]


def _redirect_uri(request: Request) -> str:
    fixed = (os.getenv("YT_REDIRECT_URI") or "").strip()
    if fixed:
        return fixed
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"https://{host}/youtube/callback"


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>{html.escape(title)}</title>"
                        f"<body style='font-family:system-ui;max-width:640px;margin:40px auto;padding:0 16px;line-height:1.5'><h2>{html.escape(title)}</h2>{body}</body>")


@router.get("/youtube/conectar/{token}")
async def conectar(token: str, request: Request):
    from studio.mcp_voice import _token_ok

    if not _token_ok(token):
        raise HTTPException(404, "Not Found")
    cid, sec, _ = _cfg()
    if not (cid and sec):
        return _page("Falta configurar Google", "<p>Cargá <b>YT_CLIENT_ID</b> y <b>YT_CLIENT_SECRET</b> en Vercel y volvé a abrir esta página.</p>")
    q = {"client_id": cid, "redirect_uri": _redirect_uri(request), "response_type": "code", "scope": SCOPE,
         "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true", "state": _state_sig()}
    return RedirectResponse(AUTH_URL + "?" + urllib.parse.urlencode(q))


@router.get("/youtube/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return _page("No se conectó", f"<p>Google respondió: {html.escape(error)}</p>")
    if not code or not hmac.compare_digest(state.encode(), _state_sig().encode()):
        raise HTTPException(400, "Pedido inválido")
    cid, sec, _ = _cfg()
    r = requests.post(TOKEN_URL, data={"code": code, "client_id": cid, "client_secret": sec, "redirect_uri": _redirect_uri(request), "grant_type": "authorization_code"}, timeout=20)
    if r.status_code != 200:
        return _page("No se conectó", f"<p>Google no dio el acceso ({r.status_code}).</p><pre>{html.escape(r.text[:400])}</pre>")
    ref = r.json().get("refresh_token")
    if not ref:
        return _page("Falta el permiso permanente", "<p>Google no devolvió refresh token. Quitá el acceso de la app en myaccount.google.com/permissions y volvé a conectar.</p>")
    return _page("Canal conectado", "<p>Copiá este valor y cargalo en Vercel como <b>YT_REFRESH_TOKEN</b> (Settings → Environment Variables), después hacé Redeploy. "
                 "Es una contraseña: no lo compartas.</p>"
                 f"<textarea readonly style='width:100%;height:110px;font-family:monospace' onclick='this.select()'>{html.escape(ref)}</textarea>")
