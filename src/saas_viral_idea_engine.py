"""Motor de ideas virales oscuras (storytime): 3 opciones + selección → brief para el guion."""
from __future__ import annotations

import json
import os
import random
import re
from typing import Any

from .config_loader import get_narrative_rules
from .saas_creative_profile import merge_profile_disk, parse_llm_json_object, profile_to_script_context

# Ideas y briefs alineados a la biblia del canal (confesión oscura, adictiva, realista).
REDDIT_STORYTIME_IDEA_RULES = (
    "Ideas: ficción oscura creíble, adictiva, incómoda — confesión personal, secreto familiar, traición, manipulación, "
    "engaño, obsesión, mentiras, daño emocional, horror realista, descubrimientos inquietantes. "
    "Primera persona (yo); gancho inmediato; ritmo rápido; cero relleno tipo ChatGPT; cierre inquietante permitido. "
    "PROHIBIDO como núcleo de entretenimiento: glorificar narcotráfico, carteles, sicarios, balaceras, narconovela, "
    "corrupción-política-mejor-tráfico, extorsión mafiosa. "
    "Evitá fantasía épica, paranormal barato irreal, monstruos, fantasmas cliché, cuentos infantiles, tono literario."
)


def _viral_channel_bible_snippet(max_chars: int = 4500) -> str:
    b = (get_narrative_rules().get("channel_dark_confession_bible") or "").strip()
    if not b:
        return ""
    if len(b) > max_chars:
        b = b[:max_chars] + "…"
    return "\n\n=== BIBLIA DEL CANAL ===\n" + b


def _as_list_topics(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [s.strip() for s in val.replace(";", ",").split(",") if s.strip()]
    return []


def _heuristic_score_idea(text: str) -> int:
    """Mayor = mejor candidata a selección (curiosidad, cercanía, realismo)."""
    s = (text or "").strip()
    if not s:
        return -999
    score = 0
    low = s.lower()
    if "?" in s:
        score += 3
    for w in (" yo ", " yo,", "yo ", " mi ", " mi,", "mi ", "me ", "mí ", "él", "ella", "alguien", "nadie"):
        if w in low:
            score += 2
    if len(s) <= 220:
        score += 1
    if len(s) > 320:
        score -= 2
    bad = (
        "monstruo",
        "fantasma",
        "demonio",
        "zombie",
        "historia de terror gen",
        "una historia sobre",
        "te voy a contar",
        "en este video",
    )
    for b in bad:
        if b in low:
            score -= 6
    return score


def _resolve_selected_among_ideas(ideas: list[str], selected_raw: str) -> str:
    ideas = [str(x).strip() for x in ideas if str(x).strip()]
    if not ideas:
        return (selected_raw or "").strip()
    sel = (selected_raw or "").strip()
    if sel in ideas:
        return sel
    for it in ideas:
        if sel and (sel in it or it in sel):
            return it
    return max(ideas, key=_heuristic_score_idea)


def _build_script_seed_from_selected(selected_idea: str, p: dict[str, Any], session_tail: str) -> str:
    """Brief largo para generar_guion: ancla todo en la idea elegida (una sola premisa fuerte)."""
    niche = (p.get("niche") or "relaciones y vida cotidiana").strip()
    tone = (p.get("tone") or "tenso, incómodo, realista").strip()
    hook = (p.get("hook_style") or "brecha de curiosidad inmediata").strip()
    pace = (p.get("pacing") or "Medio").strip()
    avoid = str(p.get("topics_to_avoid") or "").strip() or "clichés genéricos, relleno IA, intros de youtuber"
    focus = _as_list_topics(p.get("topics_to_focus"))
    ig = p.get("idea_generation") if isinstance(p.get("idea_generation"), dict) else {}
    ig_favor = str(ig.get("angles_to_favor") or "").strip()
    who = str((p.get("audience") or {}).get("who") or "adultos jóvenes").strip()
    core = (selected_idea or "").strip()
    lines = [
        "IDEA SELECCIONADA (núcleo del video — el guion debe girar ENTORNO a esto, sin sustituirla por otra premisa):",
        core,
        "",
        f"PERFIL: nicho «{niche}», tono {tone}, hook {hook}, ritmo {pace}, público {who}.",
        f"Priorizar en la trama: {', '.join(focus) if focus else 'traición, secreto, miedo, manipulación, vigilancia, algo raro en alguien cercano'}.",
        f"Evitar: {avoid}.",
        REDDIT_STORYTIME_IDEA_RULES,
    ]
    if ig_favor:
        lines.append(f"Ángulos preferidos (idea_generation): {ig_favor[:500]}")
    if session_tail.strip():
        lines.extend(
            [
                "",
                "CONTEXTO DE SESIÓN (inspiración; no copiar literal si contradice la idea seleccionada):",
                session_tail.strip()[-3500:],
            ]
        )
    lines.extend(
        [
            "",
            "INSTRUCCIONES PARA EL GUION COMPLETO (vos lo escribís en el siguiente paso):",
            "- Primera persona (yo). Oraciones cortas, oral, adictivo.",
            "- Estructura: GANCHO (ya insinuado en la idea) → SOSPECHA → ESCALADA (cada 1–2 líneas empeora o revela) → GIRO → CIERRE INQUIETANTE.",
            "- Nada de paranormal irreal ni monstruos; nada de moraleja final ni tono cuento infantil.",
            "- Desarrollá la idea seleccionada con detalles concretos (objetos, horarios, gestos, mensajes).",
        ]
    )
    return "\n".join(lines).strip()


def _seed_pool(p: dict[str, Any]) -> list[str]:
    focus = _as_list_topics(p.get("topics_to_focus"))
    ig = p.get("idea_generation") if isinstance(p.get("idea_generation"), dict) else {}
    ig_favor = str(ig.get("angles_to_favor") or "").strip()
    base = [
        "Descubrí que mi hermano llevaba meses escondiendo algo en su habitación y nadie quería hablar de ello.",
        "Mi novia dijo que vivía sola, pero de noche oía a otra persona moverse cuando yo estaba de espaldas.",
        "Alguien usaba mi ordenador mientras dormía; los historiales no cuadraban con lo que yo había hecho.",
        "Revisé su teléfono y vi un hilo con mi nombre en un grupo al que yo nunca me uní.",
        "Mi padre desapareció tres días y cuando volvió seguía siendo él… pero no del todo.",
        "Confié en él, pero cada noche escondía el móvil bajo la almohada y apagaba el sonido.",
        "Pensé que estaba solo en casa, pero los pasos en el piso de arriba seguían un patrón que no era el mío.",
        "Encontré mensajes borrados que empezaban con mi nombre y terminaban en una dirección que no reconozco.",
    ]
    if focus:
        base.insert(
            0,
            f"Todo se descontrola cuando entendés que «{focus[0]}» no era lo que creías: alguien cercano te mintió en la cara.",
        )
    if ig_favor:
        base.insert(0, f"{ig_favor[:200]}{'…' if len(ig_favor) > 200 else ''} — tenía que salir mal, y salió peor.")
    return base


def _heuristic_dark_viral_pack(p: dict[str, Any], session_tail: str) -> dict[str, Any]:
    pool = _seed_pool(p)
    random.shuffle(pool)
    ideas = pool[:3]
    while len(ideas) < 3:
        ideas.append(random.choice(_seed_pool(p)))
    ideas = ideas[:3]
    selected = max(ideas, key=_heuristic_score_idea)
    script_seed = _build_script_seed_from_selected(selected, p, session_tail)
    alts = [x for x in ideas if x != selected][:2]
    return {
        "ideas": list(ideas),
        "selected_idea": selected,
        "idea": selected,
        "alternatives": alts,
        "script_seed": script_seed,
        "source": "heuristic_dark_viral",
        "best_index": ideas.index(selected) if selected in ideas else 0,
        "ideas_pool": list(ideas),
    }


def _dark_viral_idea_engine_llm(p: dict[str, Any], session_tail: str) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
    except Exception:
        return None

    script_ctx = profile_to_script_context(p)[:12000]
    system = (
        "Sos el VIRAL IDEA ENGINE de un canal de historias oscuras en YouTube (español). "
        "Tu salida define el éxito del video: si la idea es floja, el guion fallará.\n\n"
        "Devolvé SOLO un JSON con EXACTAMENTE estas claves:\n"
        '{ "ideas": [string, string, string], "selected_idea": string }\n\n'
        "REQUISITOS DE CADA IDEA (las tres):\n"
        "- 1 o 2 oraciones máximo cada una.\n"
        "- Primera persona (yo / mi / me): persona cercana + situación cotidiana + algo que NO cierra (secreto implícito).\n"
        "- Concretas, personales, incómodas, con misterio integrado; deben sonar a 'esto podría pasar'.\n"
        "- Brecha de curiosidad inmediata: el lector debe preguntarse '¿y qué pasó?'.\n\n"
        "BUENAS (estilo deseado):\n"
        "- 'Descubrí que mi hermano escondía algo en su cuarto durante meses y nadie quería hablar del tema.'\n"
        "- 'Mi novia juraba que vivía sola, pero yo oía a otra persona de madrugada cuando fingía dormir.'\n\n"
        "MALAS (nunca las escribas):\n"
        "- Temas genéricos: 'una historia de terror', 'una historia de infidelidad' sin detalle.\n"
        "- Fantasía: monstruos, demonios, fantasmas cliché, casas embrujadas baratas.\n"
        "- Romance dramático genérico, tono cuento infantil, explicación larga del concepto.\n\n"
        "selected_idea:\n"
        "- Debe ser EXACTAMENTE una de las tres cadenas del array ideas (copia literal).\n"
        "- Elegí la que tenga mayor brecha de curiosidad, más tensión emocional, más realismo creíble, "
        "más fácil de visualizar y menos genericidad.\n\n"
        + REDDIT_STORYTIME_IDEA_RULES
        + _viral_channel_bible_snippet(3800)
    )
    user = json.dumps(
        {
            "perfil_creador": script_ctx,
            "contexto_sesion": session_tail[-6000:] if session_tail else "",
        },
        ensure_ascii=False,
    )
    try:
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.92,
            max_tokens=1100,
        )
        raw = (r.choices[0].message.content or "").strip()
        data = parse_llm_json_object(raw) or {}
    except Exception:
        return None

    ideas_raw = data.get("ideas")
    ideas: list[str] = []
    if isinstance(ideas_raw, list):
        ideas = [re.sub(r"\s+", " ", str(x).strip()) for x in ideas_raw if str(x).strip()][:3]
    selected_raw = str(data.get("selected_idea") or "").strip()
    if len(ideas) < 3:
        return None
    # Normalizar longitud (1–2 frases): recortar tercera oración si hay mucho texto
    ideas_norm: list[str] = []
    for it in ideas:
        parts = re.split(r"(?<=[.!?])\s+", it)
        if len(parts) > 2:
            it = " ".join(parts[:2]).strip()
        if len(it) > 420:
            it = it[:417].rsplit(" ", 1)[0] + "…"
        ideas_norm.append(it)
    ideas = ideas_norm
    selected = _resolve_selected_among_ideas(ideas, selected_raw)
    script_seed = _build_script_seed_from_selected(selected, p, session_tail)
    alts = [x for x in ideas if x != selected][:2]
    try:
        bi = ideas.index(selected)
    except ValueError:
        bi = 0
    return {
        "ideas": ideas,
        "selected_idea": selected,
        "idea": selected,
        "alternatives": alts,
        "script_seed": script_seed,
        "source": "openai_dark_viral_engine",
        "best_index": bi,
        "ideas_pool": list(ideas),
    }


def _dark_viral_idea_engine(p: dict[str, Any], session_context: str | None) -> dict[str, Any]:
    tail = (session_context or "").strip()[-8000:] if session_context else ""
    out = _dark_viral_idea_engine_llm(p, tail)
    if out is not None:
        return out
    return _heuristic_dark_viral_pack(p, tail)


def generate_viral_idea_for_profile(
    profile: dict[str, Any] | None,
    session_context: str | None = None,
) -> dict[str, Any]:
    """
    Motor viral oscuro: 3 ideas + selección + script_seed derivado de la idea ganadora.
    Claves: idea, alternatives, script_seed, ideas, selected_idea, source.
    """
    p = merge_profile_disk(profile or {})
    return _dark_viral_idea_engine(p, session_context)


def generate_viral_story_idea_three_pick_best(
    profile: dict[str, Any] | None,
    session_context: str | None = None,
) -> dict[str, Any]:
    """Alias del mismo motor (gameplay / paquete automático). Misma forma de salida."""
    p = merge_profile_disk(profile or {})
    return _dark_viral_idea_engine(p, session_context)
