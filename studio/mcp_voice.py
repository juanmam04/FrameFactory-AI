"""Conector MCP de voces (Streamable HTTP, sin estado) para usar Voice Lab desde Claude.

URL del conector: https://<tu-dominio>/mcp/<FF_MCP_TOKEN>
La clave va en la ruta porque los conectores personalizados de claude.ai sin OAuth
no mandan encabezados. Si FF_MCP_TOKEN no está configurada, el endpoint no existe (404).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter()

SERVER_INFO = {"name": "framefactory-voces", "version": "1.1.0"}
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
MAX_CHARS = 4000  # ~4-5 minutos de narración; el MP3 vuelve en base64 dentro de la respuesta

TOOLS = [
    {
        "name": "generar_voz",
        "title": "Generar voz",
        "description": (
            "Convierte un texto de narración en un MP3 con la voz de ElevenLabs configurada en FrameFactory "
            "(la misma que usa Voice Lab). Devuelve el audio en base64 en structuredContent.audio_base64. "
            f"Máximo {MAX_CHARS} caracteres por pedido. Gasta créditos de ElevenLabs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "texto": {"type": "string", "description": "Texto exacto a narrar."},
                "voice_id": {"type": "string", "description": "ID de voz de ElevenLabs. Si se omite, usa la voz por defecto."},
                "velocidad": {"type": "number", "description": "0.7 a 1.5. Por defecto 1.1."},
            },
            "required": ["texto"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "estado_voces",
        "title": "Estado de voces",
        "description": "Dice si ElevenLabs está configurado y cuál es la voz por defecto. No gasta créditos.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    },
]


from studio import mcp_claude, mcp_youtube  # noqa: E402

TOOLS = TOOLS + mcp_youtube.TOOLS + mcp_claude.TOOLS


def _token_ok(token: str) -> bool:
    expected = (os.getenv("FF_MCP_TOKEN") or "").strip()
    if len(expected) < 24:
        return False
    return hmac.compare_digest(token.encode(), expected.encode())


def _ok(rid: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _err(rid: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def _tool_error(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": True}


def _default_voice() -> str:
    return (os.getenv("ELEVENLABS_VOICE_ID") or "").strip() or "21m00Tcm4TlvDq8ikWAM"


def _estado() -> dict:
    from src.documentary.openai_key import reload_env

    reload_env()
    key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    ok = bool(key) and len(key) >= 20 and "your-elevenlabs" not in key.lower()
    data = {"elevenlabs_ok": ok, "voz_por_defecto": _default_voice()}
    return {"content": [{"type": "text", "text": ("ElevenLabs listo." if ok else "Falta ELEVENLABS_API_KEY.") + f" Voz por defecto: {data['voz_por_defecto']}."}], "structuredContent": data}


def _generar(args: dict) -> dict:
    from src.documentary.openai_key import reload_env
    from src.voice_generator import generar_voz

    texto = str(args.get("texto") or "").strip()
    if len(texto) < 2:
        return _tool_error("El texto está vacío.")
    if len(texto) > MAX_CHARS:
        return _tool_error(f"El texto tiene {len(texto)} caracteres; el máximo es {MAX_CHARS}. Partilo en tramos.")
    reload_env()
    key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    if len(key) < 20:
        return _tool_error("Falta ELEVENLABS_API_KEY en el servidor.")
    voice_id = re.sub(r"[^A-Za-z0-9]", "", str(args.get("voice_id") or "")) or _default_voice()
    try:
        speed = float(args.get("velocidad") or 1.1)
    except (TypeError, ValueError):
        speed = 1.1
    speed = max(0.7, min(1.5, speed))
    job = hashlib.sha1(f"{time.time()}-{len(texto)}".encode()).hexdigest()[:12]
    prev = os.environ.get("ELEVENLABS_SOLO")
    os.environ["ELEVENLABS_SOLO"] = "1"
    try:
        path = generar_voz(
            texto,
            nombre_archivo=f"mcp-{job}",
            formato="mp3",
            velocidad=speed,
            elevenlabs_voice_id=voice_id,
            voice_catalog={"provider": "elevenlabs", "elevenlabs_voice_id": voice_id},
        )
    except Exception as e:  # noqa: BLE001 - se devuelve al cliente como error de herramienta
        return _tool_error(f"ElevenLabs falló: {str(e)[:300]}")
    finally:
        if prev is None:
            os.environ.pop("ELEVENLABS_SOLO", None)
        else:
            os.environ["ELEVENLABS_SOLO"] = prev
    p = Path(path) if path else None
    if not p or not p.is_file() or p.stat().st_size <= 0:
        return _tool_error("ElevenLabs no devolvió audio.")
    raw = p.read_bytes()
    try:
        p.unlink()
    except OSError:
        pass
    data = {
        "ok": True,
        "mime": "audio/mpeg",
        "bytes": len(raw),
        "palabras": len(texto.split()),
        "voice_id": voice_id,
        "velocidad": speed,
        "audio_base64": base64.b64encode(raw).decode("ascii"),
    }
    return {
        "content": [{"type": "text", "text": f"Voz generada: {len(raw)} bytes, {data['palabras']} palabras. El MP3 está en structuredContent.audio_base64."}],
        "structuredContent": data,
    }


def _handle(msg: Any) -> dict | None:
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
        return _err(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")
    rid, method, params = msg.get("id"), msg["method"], msg.get("params") or {}
    if rid is None:  # notificación
        return None
    if method == "initialize":
        asked = params.get("protocolVersion")
        return _ok(rid, {
            "protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": "Voces de FrameFactory (ElevenLabs) y subida a YouTube. Usá generar_voz con el texto exacto de la narración. Para subir un video: youtube_iniciar_subida y después youtube_subir_parte por partes.",
        })
    if method == "ping":
        return _ok(rid, {})
    if method == "tools/list":
        return _ok(rid, {"tools": TOOLS})
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name == "generar_voz":
            return _ok(rid, _generar(args))
        if name == "estado_voces":
            return _ok(rid, _estado())
        if name in mcp_youtube.NAMES:
            return _ok(rid, mcp_youtube.call(name, args))
        if name in mcp_claude.NAMES:
            return _ok(rid, mcp_claude.call(name, args))
        return _err(rid, -32602, f"Herramienta desconocida: {name}")
    return _err(rid, -32601, f"Método no soportado: {method}")


@router.post("/mcp/{token}")
async def mcp_post(token: str, request: Request):
    if not _token_ok(token):
        raise HTTPException(404, "Not Found")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_err(None, -32700, "Parse error"), status_code=400)
    if isinstance(body, list):
        out = [r for r in (_handle(m) for m in body) if r is not None]
        return JSONResponse(out) if out else Response(status_code=202)
    res = _handle(body)
    return JSONResponse(res) if res is not None else Response(status_code=202)


@router.get("/mcp/{token}")
async def mcp_get(token: str):
    if not _token_ok(token):
        raise HTTPException(404, "Not Found")
    return Response(status_code=405, headers={"Allow": "POST"})


@router.delete("/mcp/{token}")
async def mcp_delete(token: str):
    if not _token_ok(token):
        raise HTTPException(404, "Not Found")
    return Response(status_code=405, headers={"Allow": "POST"})
