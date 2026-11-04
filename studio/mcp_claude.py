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


# ---------- OpenAI (la key que ya usa FrameFactory) ----------
import json as _json  # noqa: E402
import re as _re  # noqa: E402

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_DEFAULT = os.getenv("OPENAI_AGENT_MODEL") or "gpt-5-mini"

TOOLS.append({
    "name": "openai_mensajes",
    "title": "Agentes con la API de OpenAI",
    "description": (
        "Igual que claude_mensajes pero con la OPENAI_API_KEY de FrameFactory. Recibe y devuelve el formato de "
        "Anthropic (messages con bloques text/image/tool_use/tool_result y tools con input_schema) y lo traduce a "
        "Chat Completions de OpenAI."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "model": {"type": "string", "description": "modelo de OpenAI, por ejemplo gpt-5-mini"},
            "messages": {"type": "array", "items": {"type": "object"}},
            "tools": {"type": "array", "items": {"type": "object"}},
            "max_tokens": {"type": "integer"},
        },
        "required": ["messages"],
    },
    "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
})
NAMES.add("openai_mensajes")


def _openai_key() -> str:
    try:
        from src.documentary.openai_key import openai_api_key

        return openai_api_key()
    except Exception:  # noqa: BLE001
        return (os.getenv("OPENAI_API_KEY") or "").strip()


def _to_openai(messages: list) -> list:
    out: list = []
    for m in messages:
        role, c = m.get("role"), m.get("content")
        if isinstance(c, str):
            out.append({"role": "assistant" if role == "assistant" else "user", "content": c})
            continue
        blocks = c if isinstance(c, list) else []
        if role == "assistant":
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            calls = [{"id": b.get("id"), "type": "function", "function": {"name": b.get("name"), "arguments": _json.dumps(b.get("input") or {}, ensure_ascii=False)}}
                     for b in blocks if b.get("type") == "tool_use"]
            msg: dict = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
            continue
        parts: list = []
        for b in blocks:
            t = b.get("type")
            if t == "tool_result":
                cont = b.get("content")
                if isinstance(cont, list):
                    cont = "".join(x.get("text", "") for x in cont if isinstance(x, dict))
                out.append({"role": "tool", "tool_call_id": b.get("tool_use_id"), "content": str(cont or "")})
            elif t == "text":
                parts.append({"type": "text", "text": b.get("text", "")})
            elif t == "image":
                src = b.get("source") or {}
                if src.get("type") == "base64":
                    parts.append({"type": "image_url", "image_url": {"url": f"data:{src.get('media_type', 'image/jpeg')};base64,{src.get('data', '')}"}})
        if parts:
            out.append({"role": "user", "content": parts})
    return out


def openai_mensajes(args: dict) -> dict:
    key = _openai_key()
    if not key or len(key) < 20:
        return _text("Falta OPENAI_API_KEY en el servidor de FrameFactory.", {"ok": False, "falta": "OPENAI_API_KEY"}, error=True)
    msgs = args.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return _text("Faltan los mensajes.", error=True)
    model = str(args.get("model") or OPENAI_DEFAULT)
    if not _re.match(r"^(gpt|o\d|chatgpt)[\w.\-]*$", model):
        model = OPENAI_DEFAULT
    try:
        mt = max(1, min(16000, int(args.get("max_tokens") or 4000)))
    except (TypeError, ValueError):
        mt = 4000
    body: dict[str, Any] = {"model": model, "messages": _to_openai(msgs), "max_completion_tokens": mt}
    tools = args.get("tools")
    if isinstance(tools, list) and tools:
        body["tools"] = [{"type": "function", "function": {"name": t.get("name"), "description": t.get("description", "")[:1000],
                                                           "parameters": t.get("input_schema") or {"type": "object", "properties": {}}}} for t in tools if t.get("name")]
    try:
        r = requests.post(OPENAI_URL, json=body, timeout=280, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    except Exception as e:  # noqa: BLE001
        return _text(f"No se pudo hablar con OpenAI: {e}", {"ok": False}, error=True)
    if r.status_code != 200:
        code = "rate_limited" if r.status_code == 429 else "api_error"
        return _text(f"OpenAI respondió {r.status_code}: {r.text[:400]}", {"ok": False, "http": r.status_code, "codigo": code}, error=True)
    d = r.json()
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    content: list = []
    if msg.get("content"):
        content.append({"type": "text", "text": msg["content"]})
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            inp = _json.loads(fn.get("arguments") or "{}")
        except ValueError:
            inp = {}
        content.append({"type": "tool_use", "id": tc.get("id"), "name": fn.get("name"), "input": inp})
    fr = ch.get("finish_reason")
    stop = "tool_use" if (fr == "tool_calls" or any(b["type"] == "tool_use" for b in content)) else "max_tokens" if fr == "length" else "end_turn"
    u = d.get("usage") or {}
    cached = ((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0
    usage = {"input_tokens": (u.get("prompt_tokens") or 0) - cached, "cache_read_input_tokens": cached, "output_tokens": u.get("completion_tokens") or 0}
    out = {"ok": True, "model": d.get("model"), "content": content, "stop_reason": stop, "usage": usage}
    return _text((msg.get("content") or "")[:2000] or f"({stop})", out)


_call_prev = call


def call(name: str, args: dict) -> dict:  # noqa: F811
    if name == "openai_mensajes":
        return openai_mensajes(args)
    return _call_prev(name, args)
