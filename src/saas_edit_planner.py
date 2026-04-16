"""Plan de montaje por bloque (IA + perfil) para el MVP SaaS."""
from __future__ import annotations

import json
import os
from typing import Any

from .saas_creative_profile import merge_profile_disk, profile_to_edit_planner_context

ALLOWED_MOTION = frozenset({"static", "slow_push"})
ALLOWED_TRANSITION = frozenset({"none", "fade"})


def _sanitize_block_fields(b: dict[str, Any]) -> dict[str, Any]:
    m = str(b.get("motion") or "static").strip().lower()
    if m not in ALLOWED_MOTION:
        m = "static"
    tin = str(b.get("transition_in") or "none").strip().lower()
    tout = str(b.get("transition_out") or "none").strip().lower()
    if tin not in ALLOWED_TRANSITION:
        tin = "none"
    if tout not in ALLOWED_TRANSITION:
        tout = "none"
    out = dict(b)
    out["motion"] = m
    out["transition_in"] = tin
    out["transition_out"] = tout
    for key in ("visual_direction", "b_roll_suggestion", "on_screen_text"):
        v = b.get(key)
        out[key] = (str(v).strip()[:500] if v is not None else "")
    return out


def _heuristic_annotate(blocks: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    p = merge_profile_disk(profile)
    rhythm = str(p.get("editing", {}).get("cut_rhythm") or "medio").lower()
    push_every = 2 if rhythm in ("rápido", "rapido", "fast") else 3 if rhythm in ("medio", "medium") else 4
    out: list[dict[str, Any]] = []
    for i, block in enumerate(blocks):
        row = dict(block)
        use_push = (i % max(1, push_every) == 1) and rhythm not in ("lento", "slow")
        row["motion"] = "slow_push" if use_push else "static"
        row["transition_in"] = "fade" if i == 0 else "none"
        row["transition_out"] = "fade" if i == len(blocks) - 1 else "none"
        row.setdefault("visual_direction", "")
        row.setdefault("b_roll_suggestion", "")
        row.setdefault("on_screen_text", "")
        out.append(_sanitize_block_fields(row))
    return out


def annotate_blocks_with_editing(
    blocks: list[dict[str, Any]],
    profile: dict[str, Any] | None,
    session_context: str | None = None,
) -> list[dict[str, Any]]:
    """
    Enriquece cada bloque con dirección de montaje coherente con el perfil.
    Claves: motion, transition_in, transition_out, visual_direction, b_roll_suggestion, on_screen_text
    """
    if not blocks:
        return []
    prof = merge_profile_disk(profile or {})

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _heuristic_annotate(blocks, prof)

    try:
        from openai import OpenAI
    except Exception:
        return _heuristic_annotate(blocks, prof)

    client = OpenAI(api_key=api_key)
    compact = [
        {"id": b.get("id"), "text": (b.get("text") or "")[:320]}
        for b in blocks
    ]
    system = (
        "Sos director de montaje para YouTube. Español. "
        "Devolvé SOLO JSON válido con forma: {\"blocks\": [ ... ]}. "
        "Cada elemento debe tener: id (igual al entrante), motion (static|slow_push), "
        "transition_in (none|fade), transition_out (none|fade), "
        "visual_direction (1 frase: plano, luz, encuadre sugerido para ilustrar o B-roll), "
        "b_roll_suggestion (idea concreta de insert o overlay), "
        "on_screen_text (máx. 6 palabras o cadena vacía si no aplica). "
        "Respetá el ritmo de corte del perfil: cut_rhythm lento = más static y fades suaves; "
        "rápido = alterná slow_push y static. No inventes IDs. "
        "Si el JSON del usuario trae contexto_sesion, alineá el montaje con esas decisiones y matices."
    )
    payload: dict[str, Any] = {
        "perfil_montaje": profile_to_edit_planner_context(prof),
        "bloques": compact,
    }
    if session_context and session_context.strip():
        payload["contexto_sesion"] = session_context.strip()[:12000]
    user = json.dumps(payload, ensure_ascii=False)
    try:
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.35,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        raw = (r.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.lower().startswith("json"):
                raw = raw[4:].lstrip()
        parsed = json.loads(raw)
        ann = parsed.get("blocks") if isinstance(parsed, dict) else None
        if not isinstance(ann, list):
            return _heuristic_annotate(blocks, prof)
        by_id = {str(x.get("id")): x for x in ann if isinstance(x, dict)}
        merged: list[dict[str, Any]] = []
        keys = (
            "motion",
            "transition_in",
            "transition_out",
            "visual_direction",
            "b_roll_suggestion",
            "on_screen_text",
        )
        for i, b in enumerate(blocks):
            bid = str(b.get("id", ""))
            extra: dict[str, Any] = {}
            if i < len(ann) and isinstance(ann[i], dict):
                extra = ann[i]
            if bid and bid in by_id:
                extra = {**extra, **by_id[bid]}
            row = dict(b)
            for k in keys:
                if k in extra and extra[k] is not None:
                    row[k] = extra[k]
            merged.append(_sanitize_block_fields(row))
        return merged
    except Exception:
        return _heuristic_annotate(blocks, prof)
