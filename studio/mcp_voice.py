"""Conector MCP de voces (Streamable HTTP, sin estado) para usar Voice Lab desde Claude.

URL del conector: https://<tu-dominio>/mcp/<FF_MCP_TOKEN>
La clave va en la ruta porque los conectores personalizados de claude.ai sin OAuth
no mandan encabezados. Si FF_MCP_TOKEN no está configurada, el endpoint no existe (404).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter()

SERVER_INFO = {"name": "framefactory-voces", "version": "1.2.0"}
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
MAX_CHARS = 4000  # ~4-5 minutos de narración en un solo pedido a ElevenLabs

MODELOS = ("eleven_v3", "eleven_multilingual_v2", "eleven_turbo_v2_5", "eleven_flash_v2_5")

TOOLS = [
    {
        "name": "generar_voz",
        "title": "Generar voz",
        "description": (
            "Convierte un texto en un MP3 con ElevenLabs (el mismo motor que Voice Lab). "
            "Devuelve structuredContent.audio_url (link al MP3, vale 7 días) y structuredContent.tiempos: "
            "cada palabra con inicio y fin en segundos, para sincronizar subtítulos y animación. "
            "Con model_id eleven_v3 el texto acepta marcas de actuación como [laughs], [sighs], [whispers], [excited] "
            "y suena más humano; en v3 stability solo toma 0 (creativa), 0.5 (natural) o 1 (robusta) y se redondea a la más cercana. "
            f"Máximo {MAX_CHARS} caracteres por pedido. Gasta créditos de ElevenLabs. "
            "Usá listar_voces para ver los IDs guardados."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "texto": {"type": "string", "description": "Texto exacto a narrar (con marcas [..] si usás eleven_v3)."},
                "voice_id": {"type": "string", "description": "ID de voz de ElevenLabs (ver listar_voces). Si se omite, usa la voz por defecto."},
                "model_id": {
                    "type": "string",
                    "description": (
                        "Modelo de ElevenLabs. eleven_v3: el más expresivo, acepta [laughs] etc. "
                        "eleven_multilingual_v2: estable, el de siempre (por defecto). "
                        "eleven_turbo_v2_5 / eleven_flash_v2_5: rápidos y baratos."
                    ),
                    "examples": list(MODELOS),
                },
                "voice_settings": {
                    "type": "object",
                    "description": "Ajustes de la voz. Lo que no mandes queda como lo tiene la voz en ElevenLabs.",
                    "properties": {
                        "stability": {"type": "number", "description": "0 a 1. Baja (0.3-0.45) suena suelta y variada; alta suena leída."},
                        "similarity_boost": {"type": "number", "description": "0 a 1. Cuánto se pega al timbre original."},
                        "style": {"type": "number", "description": "0 a 1. 0.3-0.6 le da más actuación (más latencia)."},
                        "use_speaker_boost": {"type": "boolean", "description": "Refuerza el parecido con la voz original."},
                    },
                },
                "velocidad": {
                    "type": "number",
                    "description": "0.7 a 1.5. Por defecto 1.1. Se aplica después con FFmpeg; los tiempos ya vienen corregidos. 1 = sin tocar.",
                },
                "tiempos": {"type": "boolean", "description": "Devolver inicio y fin de cada palabra. Por defecto true."},
                "tiempos_por_caracter": {"type": "boolean", "description": "Además devolver la alineación cruda por carácter. Por defecto false."},
                "entrega": {
                    "type": "string",
                    "enum": ["url", "base64"],
                    "description": "url (por defecto): link al MP3. base64: el MP3 adentro de la respuesta, como antes.",
                },
                "base64_en_texto": {
                    "type": "boolean",
                    "description": "Con entrega base64: poner también el MP3 en el bloque de texto (clientes que no leen structuredContent).",
                },
            },
            "required": ["texto"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "listar_voces",
        "title": "Listar voces",
        "description": (
            "Devuelve las voces guardadas en FrameFactory con nombre y voice_id (catálogo, Voice Lab y guardar_voz). "
            "Con incluir_cuenta true también trae las voces de la cuenta de ElevenLabs. No gasta créditos."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"incluir_cuenta": {"type": "boolean", "description": "Sumar las voces de la cuenta de ElevenLabs. Por defecto false."}},
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "guardar_voz",
        "title": "Guardar voz",
        "description": (
            "Da de alta (o renombra) una voz en FrameFactory: aparece en listar_voces y en Voice Lab. "
            "Antes de guardar comprueba en ElevenLabs que el ID exista. No gasta créditos."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre para reconocerla, p. ej. Voz reels servo hombre."},
                "voice_id": {"type": "string", "description": "ID de voz de ElevenLabs."},
            },
            "required": ["nombre", "voice_id"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    },
    {
        "name": "estado_voces",
        "title": "Estado de voces",
        "description": "Dice si ElevenLabs está configurado, cuál es la voz y el modelo por defecto. No gasta créditos.",
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


def _default_model() -> str:
    from src.voice_generator import ELEVENLABS_DEFAULT_MODEL

    return (os.getenv("ELEVENLABS_MODEL_ID") or "").strip() or ELEVENLABS_DEFAULT_MODEL


def _api_key() -> str:
    from src.documentary.openai_key import reload_env

    reload_env()
    return (os.getenv("ELEVENLABS_API_KEY") or "").strip()


def _clean_id(v: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(v or ""))


def _estado() -> dict:
    key = _api_key()
    ok = bool(key) and len(key) >= 20 and "your-elevenlabs" not in key.lower()
    data = {"elevenlabs_ok": ok, "voz_por_defecto": _default_voice(), "modelo_por_defecto": _default_model()}
    text = ("ElevenLabs listo." if ok else "Falta ELEVENLABS_API_KEY.") + f" Voz por defecto: {data['voz_por_defecto']}. Modelo por defecto: {data['modelo_por_defecto']}."
    return {"content": [{"type": "text", "text": text}], "structuredContent": data}


def _voice_settings(raw: Any) -> dict | str:
    """Valida voice_settings. Devuelve el dict limpio o un mensaje de error."""
    if raw in (None, "", {}):
        return {}
    if not isinstance(raw, dict):
        return "voice_settings tiene que ser un objeto."
    out: dict = {}
    for k in ("stability", "similarity_boost", "style"):
        if raw.get(k) is None:
            continue
        try:
            v = float(raw[k])
        except (TypeError, ValueError):
            return f"voice_settings.{k} tiene que ser un número entre 0 y 1."
        out[k] = round(max(0.0, min(1.0, v)), 3)
    if raw.get("use_speaker_boost") is not None:
        out["use_speaker_boost"] = raw["use_speaker_boost"] in (True, "true", "True", 1, "1")
    unknown = set(raw) - {"stability", "similarity_boost", "style", "use_speaker_boost"}
    if unknown:
        return f"voice_settings no reconoce: {', '.join(sorted(unknown))}."
    return out


def _truthy(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    return v in (True, "true", "True", 1, "1")


def _generar(args: dict, base_url: str = "") -> dict:
    from src.voice_generator import (
        _aplicar_velocidad_audio,
        _audio_root,
        elevenlabs_tts_con_tiempos,
        palabras_desde_alineacion,
    )
    from studio import voice_store

    texto = str(args.get("texto") or "").strip()
    if len(texto) < 2:
        return _tool_error("El texto está vacío.")
    if len(texto) > MAX_CHARS:
        return _tool_error(f"El texto tiene {len(texto)} caracteres; el máximo es {MAX_CHARS}. Partilo en tramos.")
    key = _api_key()
    if len(key) < 20:
        return _tool_error("Falta ELEVENLABS_API_KEY en el servidor.")
    voice_id = _clean_id(args.get("voice_id")) or _default_voice()
    model_id = re.sub(r"[^a-z0-9_]", "", str(args.get("model_id") or "").lower()) or _default_model()
    settings = _voice_settings(args.get("voice_settings"))
    if isinstance(settings, str):
        return _tool_error(settings)
    try:
        speed = float(args.get("velocidad") or 1.1)
    except (TypeError, ValueError):
        speed = 1.1
    speed = max(0.7, min(1.5, speed))

    try:
        raw, alignment, enviados = elevenlabs_tts_con_tiempos(
            texto, voice_id, key, model_id=model_id, voice_settings=settings
        )
    except Exception as e:  # noqa: BLE001 - se devuelve al cliente como error de herramienta
        msg = str(e)[:400]
        if "voice_not_found" in msg or "404" in msg:
            msg += " Revisá el voice_id con listar_voces (ojo con l / I)."
        return _tool_error(f"ElevenLabs falló: {msg}")
    if not raw:
        return _tool_error("ElevenLabs no devolvió audio.")

    job = hashlib.sha1(f"{time.time()}-{voice_id}-{len(texto)}".encode()).hexdigest()[:12]
    applied = 1.0
    if abs(speed - 1.0) >= 0.01:
        root = _audio_root()
        src_p, dst_p = root / f"mcp-{job}-src.mp3", root / f"mcp-{job}.mp3"
        src_p.write_bytes(raw)
        try:
            res = Path(_aplicar_velocidad_audio(src_p, speed, dst_p))
            if res == dst_p and dst_p.is_file() and dst_p.stat().st_size > 0:
                raw, applied = dst_p.read_bytes(), round(speed, 2)
        finally:
            for f in (src_p, dst_p):
                try:
                    f.unlink()
                except OSError:
                    pass

    factor = 1.0 / applied
    want_times = _truthy(args.get("tiempos"), True)
    palabras = palabras_desde_alineacion(alignment, factor) if want_times else []
    duracion = None
    if alignment and alignment.get("character_end_times_seconds"):
        duracion = round(float(alignment["character_end_times_seconds"][-1]) * factor, 3)

    data: dict[str, Any] = {
        "ok": True,
        "mime": "audio/mpeg",
        "bytes": len(raw),
        "palabras": len(texto.split()),
        "voice_id": voice_id,
        "model_id": enviados.get("model_id", model_id),
        "voice_settings": {k: v for k, v in enviados.items() if k not in ("model_id", "sin_tiempos")},
        "velocidad": applied,
        "duracion_seg": duracion,
    }
    if enviados.get("sin_tiempos"):
        data["aviso_tiempos"] = f"ElevenLabs no dio tiempos con este modelo ({enviados['sin_tiempos']})."
    if speed != applied:
        data["aviso"] = f"No se pudo aplicar velocidad {speed} (falta FFmpeg); el audio va a 1.0."
    if want_times:
        data["tiempos"] = palabras
    if _truthy(args.get("tiempos_por_caracter")) and alignment:
        data["alineacion_caracteres"] = {
            "characters": alignment.get("characters"),
            "inicio": [round(float(t) * factor, 3) for t in alignment.get("character_start_times_seconds") or []],
            "fin": [round(float(t) * factor, 3) for t in alignment.get("character_end_times_seconds") or []],
        }

    entrega = str(args.get("entrega") or "").strip().lower()
    if _truthy(args.get("base64_en_texto")):
        entrega = "base64"
    entrega = entrega if entrega in ("url", "base64") else "url"
    if entrega == "url":
        try:
            if not base_url or not voice_store.persistente():
                raise RuntimeError("sin almacenamiento compartido (configurá DATABASE_URL)")
            tiempos_json = json.dumps(
                {k: data[k] for k in ("voice_id", "model_id", "velocidad", "duracion_seg") if k in data}
                | {"texto": texto, "tiempos": palabras},
                ensure_ascii=False,
            ).encode("utf-8")
            voice_store.guardar_audio(job, raw, {"json": tiempos_json})
            data["audio_url"] = voice_store.url_firmada(base_url, f"{job}.mp3")
            data["tiempos_url"] = voice_store.url_firmada(base_url, f"{job}.json")
            data["vence_en_dias"] = voice_store.AUDIO_TTL // 86400
        except Exception as e:  # noqa: BLE001 - sin almacenamiento, se manda base64
            entrega = "base64"
            data["aviso_entrega"] = f"No se pudo guardar el MP3 para dar un link ({str(e)[:160]}); va en base64."
    if entrega == "base64":
        data["audio_base64"] = base64.b64encode(raw).decode("ascii")

    dur = f", {duracion:.1f} s" if duracion else ""
    resumen = f"Voz generada con {data['model_id']}: {len(raw)} bytes{dur}, {data['palabras']} palabras."
    for k in ("aviso", "aviso_tiempos", "aviso_entrega"):
        if data.get(k):
            resumen += f" Aviso: {data[k]}"
    if "audio_url" in data:
        text = f"{resumen} MP3: {data['audio_url']}"
        if want_times:
            text += f" Tiempos por palabra en structuredContent.tiempos y en {data['tiempos_url']}"
    elif _truthy(args.get("base64_en_texto")):
        # Un solo bloque de texto: algunos clientes solo muestran el primero.
        text = f"{resumen} AUDIO_MP3_BASE64:{data['audio_base64']}"
    else:
        text = f"{resumen} El MP3 está en structuredContent.audio_base64."
    return {"content": [{"type": "text", "text": text}], "structuredContent": data}


def _listar(args: dict) -> dict:
    from studio import voice_store

    try:
        voces = voice_store.listar_voces()
    except Exception as e:  # noqa: BLE001
        return _tool_error(f"No se pudieron leer las voces guardadas: {str(e)[:200]}")
    data: dict[str, Any] = {"voces": voces, "voz_por_defecto": _default_voice()}
    if _truthy(args.get("incluir_cuenta")):
        key = _api_key()
        try:
            r = requests.get(
                "https://api.elevenlabs.io/v2/voices",
                params={"page_size": 100},
                headers={"xi-api-key": key},
                timeout=20,
            )
            r.raise_for_status()
            data["voces_cuenta"] = [
                {"nombre": v.get("name"), "voice_id": v.get("voice_id"), "categoria": v.get("category")}
                for v in r.json().get("voices") or []
            ]
        except Exception as e:  # noqa: BLE001
            data["aviso"] = f"No se pudieron traer las voces de ElevenLabs: {str(e)[:200]}"
    lines = [f"- {v['nombre']}: {v['voice_id']}" for v in voces]
    for v in data.get("voces_cuenta") or []:
        lines.append(f"- [cuenta] {v['nombre']}: {v['voice_id']}")
    text = "Voces de FrameFactory:\n" + "\n".join(lines)
    if data.get("aviso"):
        text += f"\nAviso: {data['aviso']}"
    return {"content": [{"type": "text", "text": text}], "structuredContent": data}


def _guardar(args: dict) -> dict:
    from studio import voice_store

    nombre = re.sub(r"\s+", " ", str(args.get("nombre") or "")).strip()[:80]
    raw_id = str(args.get("voice_id") or "").strip()
    voice_id = _clean_id(raw_id)
    if not nombre:
        return _tool_error("Falta el nombre.")
    if not voice_id or voice_id != raw_id or not (15 <= len(voice_id) <= 40):
        return _tool_error(f"El voice_id '{raw_id}' no tiene forma de ID de ElevenLabs (letras y números, ~20).")
    if not voice_store.persistente():
        return _tool_error("El servidor no tiene base de datos (DATABASE_URL): la voz no quedaría guardada.")
    key = _api_key()
    nombre_el = None
    if len(key) >= 20:
        try:
            r = requests.get(f"https://api.elevenlabs.io/v1/voices/{voice_id}", headers={"xi-api-key": key}, timeout=20)
        except requests.RequestException:
            r = None
        if r is not None and r.status_code in (400, 404):
            return _tool_error(
                f"ElevenLabs no encuentra la voz {voice_id}. Revisá letra por letra (l minúscula vs I mayúscula, 0 vs O)."
            )
        if r is not None and r.ok:
            nombre_el = (r.json() or {}).get("name")
    try:
        voice_store.guardar_voz(nombre, voice_id)
    except Exception as e:  # noqa: BLE001
        return _tool_error(f"No se pudo guardar: {str(e)[:200]}")
    data = {"ok": True, "nombre": nombre, "voice_id": voice_id, "nombre_en_elevenlabs": nombre_el, "verificada": nombre_el is not None}
    extra = f" (en ElevenLabs se llama '{nombre_el}')" if nombre_el else " (no se pudo verificar en ElevenLabs)"
    return {"content": [{"type": "text", "text": f"Guardada: {nombre} = {voice_id}{extra}."}], "structuredContent": data}


def _handle(msg: Any, base_url: str = "") -> dict | None:
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
            "instructions": "Voces de FrameFactory (ElevenLabs) y subida a YouTube. Usá listar_voces para ver los IDs y generar_voz con el texto exacto de la narración (model_id eleven_v3 para marcas como [laughs]); devuelve un link al MP3 y los tiempos de cada palabra. Para subir un video: youtube_iniciar_subida y después youtube_subir_parte por partes.",
        })
    if method == "ping":
        return _ok(rid, {})
    if method == "tools/list":
        return _ok(rid, {"tools": TOOLS})
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name == "generar_voz":
            return _ok(rid, _generar(args, base_url))
        if name == "listar_voces":
            return _ok(rid, _listar(args))
        if name == "guardar_voz":
            return _ok(rid, _guardar(args))
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
    base = _base_url(request)
    if isinstance(body, list):
        out = [r for r in (_handle(m, base) for m in body) if r is not None]
        return JSONResponse(out) if out else Response(status_code=202)
    res = _handle(body, base)
    return JSONResponse(res) if res is not None else Response(status_code=202)


def _base_url(request: Request) -> str:
    env = (os.getenv("FF_PUBLIC_URL") or "").strip().rstrip("/")
    if env:
        return env
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    return f"{proto}://{host.split(',')[0].strip()}" if host else ""


@router.get("/voz/{name}")
def voz_archivo(name: str, exp: str = "", sig: str = ""):
    from studio import voice_store

    data = voice_store.leer_archivo_firmado(name, exp, sig)
    if data is None:
        raise HTTPException(404, "Not Found")
    if name.endswith(".json"):
        return Response(data, media_type="application/json; charset=utf-8", headers={"Cache-Control": "private, max-age=86400"})
    return Response(
        data,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'inline; filename="{name}"', "Cache-Control": "private, max-age=86400"},
    )


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
