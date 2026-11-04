"""Puente a la API de Anthropic para la oficina CHECK.

La oficina corre dentro de claude.ai y no puede llamar a api.anthropic.com directo, así que manda
cada paso de la charla por el conector de FrameFactory y este servidor lo reenvía con la API key de
Juanma (ANTHROPIC_API_KEY o FF_ANTHROPIC_API_KEY). El bucle de herramientas lo hace la oficina.
"""
from __future__ import annotations

import os
from typing import Any

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODELOS = {"claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"}
DEFAULT = "claude-sonnet-5-5"

TOOLS = [
    {
        "name": "claude_mensajes",
        "title": "Claude con mi API key",
        "description": (
            "Manda una conversación a la API de Anthropic con la API key configurada en FrameFactory y devuelve "
            "la respuesta tal cual (content, stop_reason, usage). Acepta herramientas: si stop_reason es tool_use, "
            "el cliente ejecuta las herramientas y vuelve a llamar con los resultados."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "enum": sorted(MODELOS)},
                "system": {"type": "string"},
                "messages": {"type": "array", "items": {"type": "object"}},
                "tools": {"type": "array", "items": {"type": "object"}},
                "max_tokens": {"type": "integer"},
            },
            "required": ["messages"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "claude_estado",
        "title": "Estado de la API key",
        "description": "Dice si hay una API key de Anthropic configurada en FrameFactory. No gasta nada.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    },
]
NAMES = {t["name"] for t in TOOLS}


def _key() -> str:
    return (os.getenv("FF_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()


def _text(t: str, data: dict | None = None, error: bool = False) -> dict:
    out: dict = {"content": [{"type": "text", "text": t}]}
    if data is not None:
        out["structuredContent"] = data
    if error:
        out["isError"] = True
    return out


def _cache_first(messages: list) -> list:
    """Marca el primer mensaje largo (las instrucciones del agente) para el caché de prompts."""
    if not messages:
        return messages
    m0 = dict(messages[0])
    c = m0.get("content")
    if isinstance(c, str) and len(c) > 4000:
        m0["content"] = [{"type": "text", "text": c, "cache_control": {"type": "ephemeral"}}]
        return [m0] + list(messages[1:])
    return messages


def mensajes(args: dict) -> dict:
    key = _key()
    if not key:
        return _text("Falta ANTHROPIC_API_KEY en el servidor de FrameFactory.", {"ok": False, "falta": "ANTHROPIC_API_KEY"}, error=True)
    msgs = args.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return _text("Faltan los mensajes.", error=True)
    model = str(args.get("model") or DEFAULT)
    if model not in MODELOS:
        model = DEFAULT
    try:
        mt = max(1, min(16000, int(args.get("max_tokens") or 4000)))
    except (TypeError, ValueError):
        mt = 4000
    body: dict[str, Any] = {"model": model, "max_tokens": mt, "messages": _cache_first(msgs)}
    if args.get("system"):
        body["system"] = [{"type": "text", "text": str(args["system"]), "cache_control": {"type": "ephemeral"}}]
    tools = args.get("tools")
    if isinstance(tools, list) and tools:
        body["tools"] = tools
    try:
        r = requests.post(API_URL, json=body, timeout=280, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    except Exception as e:  # noqa: BLE001
        return _text(f"No se pudo hablar con la API de Anthropic: {e}", {"ok": False}, error=True)
    if r.status_code != 200:
        code = "rate_limited" if r.status_code == 429 else "overloaded" if r.status_code == 529 else "api_error"
        return _text(f"La API de Anthropic respondió {r.status_code}: {r.text[:400]}", {"ok": False, "http": r.status_code, "codigo": code}, error=True)
    d = r.json()
    out = {"ok": True, "model": d.get("model"), "content": d.get("content") or [], "stop_reason": d.get("stop_reason"), "usage": d.get("usage") or {}}
    txt = "".join(b.get("text", "") for b in out["content"] if b.get("type") == "text")
    return _text(txt[:2000] or f"({out['stop_reason']})", out)


def estado() -> dict:
    k = _key()
    return _text("API key de Anthropic configurada." if k else "No hay API key de Anthropic.", {"ok": bool(k), "termina_en": k[-4:] if k else None})


def call(name: str, args: dict) -> dict:
    if name == "claude_mensajes":
        return mensajes(args)
    if name == "claude_estado":
        return estado()
    raise KeyError(name)
