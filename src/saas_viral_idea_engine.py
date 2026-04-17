"""Motor de idea viral para el flujo paquete automático (Creative Profile + sesión)."""
from __future__ import annotations

import json
import os
import random
from typing import Any

from .saas_creative_profile import merge_profile_disk, parse_llm_json_object, profile_to_script_context


def _as_list_topics(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [s.strip() for s in val.replace(";", ",").split(",") if s.strip()]
    return []


def _heuristic_pack(p: dict[str, Any], session_tail: str) -> dict[str, Any]:
    niche = (p.get("niche") or "tu vida cotidiana").strip()
    tone = (p.get("tone") or "tenso y emocional").strip()
    hook = (p.get("hook_style") or "curiosidad y shock suave").strip()
    pace = (p.get("pacing") or "Medio").strip()
    avoid = str(p.get("topics_to_avoid") or "").strip() or "clichés genéricos y intros largas"
    focus = _as_list_topics(p.get("topics_to_focus"))
    ig = p.get("idea_generation") if isinstance(p.get("idea_generation"), dict) else {}
    ig_favor = str(ig.get("angles_to_favor") or "").strip()
    who = str((p.get("audience") or {}).get("who") or "adultos jóvenes").strip()
    seeds = [
        f"Abrís un mensaje y descubrís que {niche} nunca fue lo que creías.",
        f"Un familiar te mintió años sobre algo que te define; {tone}.",
        f"Algo que hiciste por lealtad te costó todo; ahora tenés que elegir.",
        f"Encontraste una prueba que cambia cómo ves a alguien que amás.",
        f"Te enteraste de un secreto de {niche} que no podés des-ver.",
    ]
    if focus:
        seeds.insert(0, f"Todo gira en torno a «{focus[0]}»: una traición que no viste venir.")
    if ig_favor:
        seeds.insert(0, f"{ig_favor[:120]}{'…' if len(ig_favor) > 120 else ''} — historia en segunda persona, {tone}.")
    random.shuffle(seeds)
    best = seeds[0]
    alts = [s for s in seeds[1:4] if s != best][:3]
    script_seed = (
        f"IDEA VIRAL (línea de gancho): {best}\n\n"
        f"PERFIL CREADOR (resumen): nicho «{niche}», tono {tone}, hook {hook}, ritmo {pace}, público {who}.\n"
        f"Temas a priorizar en la trama: {', '.join(focus) if focus else 'confianza rota, consecuencias, cierre fuerte'}.\n"
        f"Evitar en el guion: {avoid}.\n"
    )
    if ig_favor:
        script_seed += f"Ángulos preferidos (idea_generation): {ig_favor[:400]}\n"
    if session_tail:
        script_seed += (
            "\nCONTEXTO RECIENTE DE LA SESIÓN (inspiración, no copiar literal):\n"
            + session_tail[-3500:]
            + "\n"
        )
    script_seed += (
        "\nINSTRUCCIONES PARA EL GUION COMPLETO (otro modelo lo escribirá):\n"
        "- Formato historia viral YouTube / Reddit storytime, segunda persona (vos).\n"
        "- Primeras 2–4 frases: gancho máximo alineado al hook_style.\n"
        "- Frases cortas, habladas; tensión cada 1–2 líneas; cero relleno.\n"
        "- Arco claro: planteo → escalada → clímax → desenlace con emoción.\n"
        "- Sin tutorial ni consejos genéricos; es narrativa, no ensayo.\n"
    )
    return {
        "idea": best,
        "alternatives": alts,
        "script_seed": script_seed.strip(),
        "source": "heuristic",
    }


def generate_viral_idea_for_profile(
    profile: dict[str, Any] | None,
    session_context: str | None = None,
) -> dict[str, Any]:
    """
    Devuelve dict con: idea (mejor línea), alternatives (lista), script_seed (brief largo para generar_guion), source.
    """
    p = merge_profile_disk(profile or {})
    tail = (session_context or "").strip()[-8000:] if session_context else ""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _heuristic_pack(p, tail)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
    except Exception:
        return _heuristic_pack(p, tail)

    script_ctx = profile_to_script_context(p)[:12000]
    system = (
        "Sos estratega de ideas virales para YouTube (historias / storytime en español). "
        "Devolvé SOLO un JSON con claves exactas:\n"
        '{ "idea": string (una línea, muy clicable, emocional o misteriosa; estilo título-historia), '
        '"alternatives": [string, string, string] (otras líneas distintas), '
        '"script_seed": string (un briefing de 500–1500 caracteres para que otro LLM escriba el guion COMPLETO: '
        "personaje en segunda persona, conflicto, 3–5 giros posibles, tono, final deseado, temas a tocar y a evitar; "
        "no escribas el guion palabra por palabra de todo el video, sí el arco y beats claros) }\n"
        "Priorizá el Creative Profile (tone, hook_style, pacing, audience, topics_to_focus, topics_to_avoid, idea_generation). "
        "Nada de política partidaria ni contenido ilegal explícito. Evitá ideas genéricas tipo '10 consejos para…'."
    )
    user = json.dumps(
        {
            "perfil_creador": script_ctx,
            "contexto_sesion": tail[-6000:] if tail else "",
        },
        ensure_ascii=False,
    )
    try:
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.85,
            max_tokens=700,
        )
        raw = (r.choices[0].message.content or "").strip()
        data = parse_llm_json_object(raw) or {}
    except Exception:
        return _heuristic_pack(p, tail)

    idea = str(data.get("idea") or "").strip()
    alts_raw = data.get("alternatives")
    alts: list[str] = []
    if isinstance(alts_raw, list):
        alts = [str(x).strip() for x in alts_raw[:5] if str(x).strip()]
    seed = str(data.get("script_seed") or "").strip()
    if not idea or not seed:
        return _heuristic_pack(p, tail)
    out_alts = [a for a in alts if a != idea][:3]
    if len(out_alts) < 2:
        h = _heuristic_pack(p, tail)
        for x in list(h.get("alternatives") or []) + [str(h.get("idea") or "")]:
            xs = str(x).strip()
            if xs and xs != idea and xs not in out_alts:
                out_alts.append(xs)
            if len(out_alts) >= 3:
                break
    return {"idea": idea, "alternatives": out_alts[:3], "script_seed": seed[:12000], "source": "openai"}
