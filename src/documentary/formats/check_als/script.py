"""Check ALS script: Spanish second-person YouTube narration from approved Story Architecture."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from src.documentary.formats.check_als.story_arch import load_architecture
from src.documentary.formats.check_als.story_architect import is_check_project
from src.documentary.formats.check_als.story_vehicle import vehicle_mode
from src.documentary.openai_key import openai_api_key
from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.script_generator import count_words

TARGET_WORDS = 1800
MIN_WORDS = 1100
WORD_RANGE = (MIN_WORDS, 2300)
WPM = 150  # spoken Spanish TTS pacing

VOSEO_FIXES = (
    ("tenés", "tienes"),
    ("podés", "puedes"),
    ("querés", "quieres"),
    ("mirás", "miras"),
    ("firmás", "firmas"),
    ("mudás", "mudas"),
    ("trabajás", "trabajas"),
    ("vivís", "vives"),
    ("lanzás", "lanzas"),
    ("creás", "creas"),
    ("armás", "armas"),
    ("cerrás", "cierras"),
    ("sos", "eres"),
    ("andá ", "ve "),
    ("decís", "dices"),
    ("venís", "vienes"),
    ("salís", "sales"),
    ("entrás", "entras"),
    ("comprás", "compras"),
    ("pagás", "pagas"),
    ("dejás", "dejas"),
    ("llegás", "llegas"),
)

VOSEO_FIXES = tuple((a, b) for a, b in VOSEO_FIXES if a.lower() != b.lower())

BANNED_OPENERS = (
    "¿te imaginas",
    "te imaginas",
    "en este video",
    "esta es la historia",
    "hoy te voy a contar",
    "en el video de hoy",
)
BANNED_MORAL = (
    "aprendiste que",
    "el verdadero éxito",
    "con esfuerzo",
    "la lección",
    "la moraleja",
    "al final aprendes",
    "al final aprendiste",
)
BANNED_CTA = (
    "suscrib",
    "dale like",
    "deja tu like",
    "comenta ",
    "comentá",
    "sígueme",
    "no olvides",
    "link en",
)
BANNED_FLUFF = (
    "tu corazón late",
    "el corazón te late",
    "el corazón latiendo",
    "la emoción es indescriptible",
    "la emoción es palpable",
    "te llenas de orgullo",
    "sientes orgullo",
    "te sientes orgulloso",
    "todo tu esfuerzo vale la pena",
    "emoción palpable",
    "camino de rosas",
)

SCRIPT_SYSTEM_SHARED = """Eres el guionista de Check: fantasías en segunda persona para YouTube (VO / TTS).

ESCRIBÍ SOLO EL TEXTO QUE SE ESCUCHA. Nada más.

FORMATO OBLIGATORIO:
- Solo narración en segunda persona (tú/te/tienes/tu).
- Párrafos cortos. Español neutro.
- PROHIBIDO: INT./EXT., encabezados de escena, nombres de personajes, diálogos con "JOVEN:", "NARRADOR (V.O.)", acotaciones entre asteriscos, FADE OUT, títulos, markdown, guiones de cine.
- PROHIBIDO: nombres de ops internas (launch_company, quit_job, advance_time, first_client, etc.).
- PROHIBIDO: instrucciones meta ("NO moraleja", "Edad final del state", "vehicle_mode").
- NO es un guion de película. NO es un documental. Es VO que lee una IA en voz alta.

IMPACTO ASPIRACIONAL (crítico para el viewer):
- Cuando el state llega a millonario / sold-out / major_success / ownership real, el VO DEBE hacer SENTIR el salto.
- No alcanza con decir "vales X millones". El viewer tiene que VER/OÍR el contraste con el día 1.
- Obligatorio en el pico (≥3 beats sensoriales concretos, ganados por la trama): casa/departamento nuevo vs el de antes,
  ropa o status distinto, padres/familia en un lugar que antes no podían, auto o viaje ganado, cena/lugar que antes
  no te salía, estadio/oficina/estudio lleno, gente que ahora te busca.
- Podés mantener la ironía cash-bajo vs paper-alto, PERO primero mostrá el lujo/status ganado; después el contraste.
- PROHIBIDO: flex vacío repetido (Lamborghini/jet en cada párrafo). SÍ: 1–2 momentos de lujo extremo que duelan de envidia.
- Si el state dice éxito extremo y el VO sigue en oficina gris / depto triste / cara de derrota, FALLASTE.

FORMA:
- Mínimo 1100 palabras. Rango 1100–2300. Target 1800.
- Cold open directo con edad / situación / cifra.
- Escenas concretas del JSON. Números locked = ley.
- Final en escena (teléfono / oferta). Sin moraleja. Sin CTA.

Return ONLY the spoken narration text."""

SCRIPT_SYSTEM_SPORTS = (
    SCRIPT_SYSTEM_SHARED
    + """

VEHÍCULO: compra de equipo deportivo.
HOOK temprano: precio + deuda + tu cash → tu %.
Usá season_history exacta. No inventes campeonato si championships=0.
"""
)

SCRIPT_SYSTEM_BUSINESS = (
    SCRIPT_SYSTEM_SHARED
    + """

VEHÍCULO: negocio / creador / startup (NO deporte, NO estadio, NO playoffs).
HOOK temprano: lanzás la empresa / firmás con socios → tu % exacto del state.
PROHIBIDO inventar básquet/liga/anillo.
"""
)


def script_system(mode: str) -> str:
    return SCRIPT_SYSTEM_SPORTS if mode == "sports_team" else SCRIPT_SYSTEM_BUSINESS


RETENTION_SYSTEM = """Eres editor de retención de YouTube para Check (segunda persona, tú/te).

Reescribí el guion SIN agregar relleno y SIN cambiar hechos/números.
Cada ~30–45 segundos (≈75–110 palabras) un cambio. Tú/te. Nunca vos. Mínimo 1100 palabras. Solo el guion."""


def locked_story_facts(arch: dict[str, Any], *, mode: str = "sports_team") -> dict[str, Any]:
    """Compact source of truth for the script model. Never invent outside this."""
    bp = arch.get("blueprint") if isinstance(arch.get("blueprint"), dict) else {}
    iw = arch.get("initial_world") if isinstance(arch.get("initial_world"), dict) else {}
    fw = arch.get("final_world") if isinstance(arch.get("final_world"), dict) else {}
    review = arch.get("review") if isinstance(arch.get("review"), dict) else {}
    vehicle = bp.get("business_or_vehicle") if isinstance(bp.get("business_or_vehicle"), dict) else {}
    acq = vehicle.get("acquisition") if isinstance(vehicle.get("acquisition"), dict) else {}
    if not acq:
        acq = review.get("acquisition") if isinstance(review.get("acquisition"), dict) else {}
    if not acq and isinstance(fw.get("acquisition"), dict):
        acq = fw["acquisition"]
    fiction = bp.get("fiction_world") if isinstance(bp.get("fiction_world"), dict) else {}
    life0 = iw.get("life") if isinstance(iw.get("life"), dict) else {}
    life1 = fw.get("life") if isinstance(fw.get("life"), dict) else {}
    per0 = iw.get("personal") if isinstance(iw.get("personal"), dict) else {}
    per1 = fw.get("personal") if isinstance(fw.get("personal"), dict) else {}
    fin0 = iw.get("finance") if isinstance(iw.get("finance"), dict) else {}
    fin1 = fw.get("finance") if isinstance(fw.get("finance"), dict) else {}
    team0 = iw.get("team") if isinstance(iw.get("team"), dict) else {}
    team1 = fw.get("team") if isinstance(fw.get("team"), dict) else {}
    sp1 = fw.get("sports") if isinstance(fw.get("sports"), dict) else {}
    ledger = fw.get("ownership_ledger") if isinstance(fw.get("ownership_ledger"), dict) else {}
    beats = []
    for b in arch.get("beats") or []:
        if not isinstance(b, dict):
            continue
        beats.append(
            {
                "beat_id": b.get("beat_id"),
                "time": b.get("time"),
                "event": b.get("event"),
                "consequence": b.get("consequence"),
                "story_purpose": b.get("story_purpose"),
                "visual_opportunity": b.get("visual_opportunity"),
                "reward_or_setback": b.get("reward_or_setback"),
            }
        )

    if mode == "business":
        default_own, default_inv, default_seller = 60, 40, 0
        default_debt, default_your_cash, default_inv_cash, default_price = 0, 8000, 40000, 0
        must = [
            "cold open: edad / trabajo / casa / cash / oportunidad de negocio",
            f"payoff lanzamiento temprano: tu cash + inversores → ownership {acq.get('your_ownership') or default_own}%",
            "primer cliente / primera tracción real",
            "crisis o setback (caja, dilución, burnout)",
            "renuncia o mudanza si existen en el state",
            "escala concreta sin inventar deporte",
            "IMPACTO DE CIMA: ≥3 beats sensoriales de éxito ganado (oficina/casa/status/viajes/gente que te busca) antes del final",
            "final: oferta/tracción/decisión abierta — sin moraleja",
        ]
        ending = (
            "Estás solo un momento. En el teléfono alguien quiere comprarte o asociarse. "
            "Bloqueas. Mañana lo lees."
        )
        job_end = "dueño de tu empresa"
        name = fiction.get("team_name") or team1.get("name") or vehicle.get("name") or "tu empresa"
        league = fiction.get("league_name") or ""
    else:
        default_own, default_inv, default_seller = 51, 39, 10
        default_debt, default_your_cash, default_inv_cash, default_price = 650000, 15000, 85000, 1
        must = [
            "cold open: 22 / oficina / depto / ~$20k / equipo a $1 / deuda grande",
            "payoff compra temprano: $1 + deuda + tu cash → 51%",
            "primera entrada / utilero / llaves",
            "mal arranque + deuda",
            "progresión deportiva EXACTA por temporada",
            "sold out / renuncia / mudanza en el tiempo real del state",
            "IMPACTO DE CIMA: ≥3 beats sensoriales de éxito ganado (casa nueva, status, familia, packed venue, gente que te busca) — no solo el número de millones",
            "después del impacto: millonario en papel vs cash personal bajo (ironía), sin borrar el lujo ya mostrado",
            "final: estadio vacío, mail de oferta, bloqueas",
        ]
        ending = (
            "El estadio está vacío. En el teléfono, un correo: oferta de adquisición. "
            "Bloqueas. Mañana lo lees."
        )
        job_end = "dueño del equipo"
        name = fiction.get("team_name") or team1.get("name") or "Los Halcones de la Ciudad"
        league = fiction.get("league_name") or team1.get("league") or ""

    own = acq.get("your_ownership")
    if own is None and ledger.get("protagonist") is not None:
        own = ledger.get("protagonist")
    inv = acq.get("investor_ownership")
    if inv is None and ledger.get("investors") is not None:
        inv = ledger.get("investors")
    seller = acq.get("seller_retained")
    if seller is None and ledger.get("seller") is not None:
        seller = ledger.get("seller")
    debt = acq.get("debt_assumed")
    if debt is None:
        debt = default_debt

    return {
        "vehicle_mode": mode,
        "team_name": name,
        "league_name": league,
        "city": fiction.get("city") or team1.get("city") or "",
        "acquisition": {
            "asking_price": acq.get("asking_price") if acq.get("asking_price") is not None else default_price,
            "debt_assumed": debt,
            "your_cash_contribution": acq.get("your_cash_contribution")
            if acq.get("your_cash_contribution") is not None
            else default_your_cash,
            "local_investors_cash": acq.get("local_investors_cash")
            if acq.get("local_investors_cash") is not None
            else default_inv_cash,
            "seller_financing": acq.get("seller_financing")
            if acq.get("seller_financing") is not None
            else (0 if mode == "business" else 200000),
            "your_ownership": own if own is not None else default_own,
            "investor_ownership": inv if inv is not None else default_inv,
            "seller_retained": seller if seller is not None else default_seller,
            "summary": acq.get("summary") or vehicle.get("acquisition_structure") or "",
        },
        "life_start": {
            "age": (iw.get("time") or {}).get("protagonist_age") or (bp.get("protagonist") or {}).get("age") or 22,
            "job": life0.get("job") or per0.get("working_status") or "empleado de oficina",
            "home": life0.get("home") or per0.get("living_situation") or "departamento compartido",
            "personal_cash": life0.get("personal_cash") if life0.get("personal_cash") is not None else per0.get("cash"),
            "net_worth": life0.get("personal_net_worth") if life0.get("personal_net_worth") is not None else per0.get("net_worth"),
        },
        "life_end": {
            "age": (fw.get("time") or {}).get("protagonist_age") or 27,
            "job": life1.get("job") or per1.get("working_status") or job_end,
            "home": life1.get("home") or per1.get("living_situation") or "",
            "personal_cash": life1.get("personal_cash") if life1.get("personal_cash") is not None else per1.get("cash"),
            "net_worth": life1.get("personal_net_worth") if life1.get("personal_net_worth") is not None else per1.get("net_worth"),
        },
        "team_start": {
            "valuation": team0.get("valuation"),
            "debt": team0.get("debt") or fin0.get("team_debt"),
            "attendance": team0.get("attendance"),
            "capacity": team0.get("capacity") or (0 if mode == "business" else 4800),
            "cash": team0.get("cash") or fin0.get("team_cash"),
        },
        "team_end": {
            "valuation": team1.get("valuation"),
            "debt": team1.get("debt") or fin1.get("team_debt"),
            "attendance": team1.get("attendance"),
            "capacity": team1.get("capacity") or (0 if mode == "business" else 4800),
            "cash": team1.get("cash") or fin1.get("team_cash"),
            "annual_revenue": fin1.get("annual_revenue"),
            "debt_risk_state": fin1.get("debt_risk_state"),
        },
        "ownership_ledger": ledger
        or {
            "protagonist": own if own is not None else default_own,
            "investors": inv if inv is not None else default_inv,
            "seller": seller if seller is not None else default_seller,
        },
        "championships": int((sp1.get("championships") or 0) or 0) if mode == "sports_team" else 0,
        "season_history": list(sp1.get("season_history") or review.get("season_history") or [])
        if mode == "sports_team"
        else [],
        "aspirational_payoffs": list(review.get("aspirational_payoffs") or []),
        "major_events": list(review.get("major_events") or [])[:24],
        "open_loops": [
            {
                "id": l.get("id"),
                "question": l.get("question"),
                "status": l.get("status"),
                "payoff": l.get("payoff"),
            }
            for l in (review.get("open_loops") or [])
            if isinstance(l, dict)
        ],
        "must_include_scenes": must,
        "ending_direction": ending,
        "beats": beats,
        "disclaimer": "Ficción. No presentar como factual.",
    }


EXPAND_SYSTEM = """Eres guionista de Check. El guion (VO) está CORTO.

Expandí SOLO con narración hablada en segunda persona (tú/te).
PROHIBIDO: INT/EXT, diálogos con nombres, acotaciones, ops (launch_company…), meta ("NO moraleja").
Si vehicle_mode=business: PROHIBIDO deporte/estadio/playoffs.
Mínimo 1100 palabras. Target ~1800. Devolvé el guion completo hablado, nada más.
Solo el texto del VO."""


_OP_NAME_RE = re.compile(
    r"^(launch_company|acquire_team|first_client|viral_hit|hire_employee|owner_crisis|"
    r"pay_debt|quit_job|move_home|ad_spend|sign_contract|owner_injection|advance_time|"
    r"media_deal|sponsor_deal|product_launch|media_crisis|family_crisis|ending|"
    r"help_family|equity_sale|new_season|season_stretch|win_game|lose_game)s?$",
    re.I,
)
_META_LEAK_RE = re.compile(
    r"(?i)\b(no moraleja|edad final del state|vehicle_mode|locked_facts|must_include|"
    r"story_purpose|ops:|fade out|int\.|ext\.|narrador\s*\(v\.?o\.?\)|"
    r"launch_company|first_client|advance_time|quit_job)\b"
)


def facts_for_llm(facts: dict[str, Any]) -> dict[str, Any]:
    out = dict(facts)
    beats = []
    for b in (facts.get("beats") or [])[:40]:
        if not isinstance(b, dict):
            continue
        event = str(b.get("event") or "").strip()
        if not event or _OP_NAME_RE.match(event) or len(event) < 8:
            continue
        beats.append(
            {
                "id": b.get("beat_id"),
                "time": b.get("time"),
                "event": event,
                "purpose": b.get("story_purpose"),
            }
        )
    out["beats"] = beats
    # Hint only — model must not copy instructional wording.
    out["ending_scene"] = str(facts.get("ending_direction") or "")
    out.pop("ending_direction", None)
    out.pop("must_include_scenes", None)
    out.pop("disclaimer", None)
    return out


def _norm(text: str) -> str:
    return (text or "").lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


def strip_script_chrome(script: str) -> str:
    """Keep only spoken VO — strip screenplay chrome, ops, and meta leaks."""
    text = (script or "").strip()
    text = re.sub(r"^```(?:text|markdown|md|screenplay)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    cleaned: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        # Drop screenplay / markdown chrome.
        if line.startswith("#") or line.startswith("---"):
            continue
        if re.match(r"(?i)^(int\.|ext\.|fade\s+(in|out)|cut to|título:|title:)", line):
            continue
        if re.match(r"(?i)^(narrador|narrator)\b.*:", line):
            # Keep the dialogue after the header if present on same line.
            after = re.sub(r"(?i)^(narrador|narrator)\s*(\(v\.?o\.?\))?\s*[:：]\s*", "", line).strip()
            if after and not after.startswith("*"):
                cleaned.append(after)
            continue
        if re.match(r"^\*{1,2}.+\*{1,2}$", line) or (line.startswith("*") and line.endswith("*")):
            continue
        if re.match(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]{1,40}:\s*", line) and not re.match(
            r"(?i)^(tienes|te |tu |eres|miras|firmas)", line
        ):
            # CHARACTER: dialogue — keep spoken part only if second person-ish, else drop.
            after = re.sub(r"^[^:]+:\s*", "", line).strip()
            if re.search(r"(?i)\b(tú|te |tienes|tu )\b", after):
                cleaned.append(after)
            continue
        if _OP_NAME_RE.match(line.rstrip(".")):
            continue
        if _META_LEAK_RE.search(line) and not re.search(r"(?i)\b(tienes|te |firmas|lanzas)\b", line):
            continue
        # Strip leftover stage-direction wrappers mid-line lightly.
        line = re.sub(r"^\*[^*]+\*\s*", "", line).strip()
        if not line:
            continue
        cleaned.append(line)
    # Collapse blank runs
    out_lines: list[str] = []
    for line in cleaned:
        if line == "" and out_lines and out_lines[-1] == "":
            continue
        out_lines.append(line)
    return "\n".join(out_lines).strip()


def apply_tuteo_fixes(script: str) -> str:
    out = script
    for src, dst in VOSEO_FIXES:
        out = re.sub(rf"\b{re.escape(src)}\b", dst, out, flags=re.IGNORECASE)
    out = re.sub(r"\b[Vv]os\b", "tú", out)
    return out


def _event_to_vo(event: str, *, when: str = "", own: int = 0) -> str:
    """Turn a beat event into a short second-person VO beat (never dump ops)."""
    ev = str(event or "").strip().rstrip(".")
    if not ev or _OP_NAME_RE.match(ev) or len(ev) < 8:
        return ""
    if _META_LEAK_RE.search(ev):
        return ""
    low = ev.lower()
    if re.search(r"\b(tienes|te |tu |eres|lanzas|firmas|miras|decides)\b", low):
        body = ev[0].upper() + ev[1:] if ev else ev
    else:
        body = f"Llega el momento: {ev[0].lower() + ev[1:] if ev else ev}"
    parts: list[str] = []
    if when and len(when) < 40 and not _OP_NAME_RE.match(when):
        parts.append(when.rstrip(".") + ".")
    parts.append(body if body.endswith(".") else body + ".")
    if own >= 40:
        parts.append(f"Todavía tienes el {own}%.")
    return " ".join(parts)


def pad_script_from_beats(script: str, facts: dict[str, Any], *, min_words: int = MIN_WORDS) -> str:
    """Deterministic VO pad — never dumps ops, screenplay, or meta instructions."""
    text = strip_script_chrome(script or "")
    if count_words(text) >= min_words:
        return text
    acq = facts.get("acquisition") or {}
    own = int(float(acq.get("your_ownership") or 0) or 0)
    life0 = facts.get("life_start") or {}
    life1 = facts.get("life_end") or {}
    chunks = [text] if text else []
    if not text:
        age = life0.get("age") or 22
        job = life0.get("job") or "creador independiente"
        cash = life0.get("personal_cash")
        cash_bit = f" Tienes {cash} en la cuenta." if cash is not None else ""
        chunks.append(f"Tienes {age} años. Eres {job}.{cash_bit}")

    for b in facts.get("beats") or []:
        if not isinstance(b, dict):
            continue
        vo = _event_to_vo(str(b.get("event") or ""), when=str(b.get("time") or ""), own=0)
        if not vo:
            cons = _event_to_vo(str(b.get("consequence") or ""))
            vo = cons
        if not vo:
            continue
        chunks.append(vo)
        if count_words("\n\n".join(chunks)) >= min_words:
            break

    if count_words("\n\n".join(chunks)) < min_words:
        end_age = life1.get("age") or 27
        end_job = life1.get("job") or "dueño de tu empresa"
        end_scene = str(facts.get("ending_direction") or "").strip()
        end_scene = re.sub(r"(?i)\bNO moraleja\.?\b", "", end_scene).strip()
        end_scene = re.sub(r"(?i)Edad final del state\.?\s*", "", end_scene).strip()
        if not end_scene:
            end_scene = "Estás solo un momento. En el teléfono alguien quiere comprarte. Bloqueas. Mañana lo lees."
        filler_pool = [
            f"Tienes {end_age} años. Trabajas como {end_job}.",
            "Los días se alargan. Revisas números, contestas mensajes, y vuelves a empezar antes de que amanezca.",
            "Hay semanas buenas y semanas donde la caja aprieta. Igual seguís. Igual contestás. Igual mandás otra propuesta.".replace(
                "seguís", "sigues"
            ).replace("contestás", "contestas").replace("mandás", "mandas"),
            "Un cliente nuevo aparece. Otro se enfría. Aprendés a no celebrar demasiado pronto.".replace("Aprendés", "Aprendes"),
            end_scene,
            "Miras el teléfono otra vez. Todavía no abres el mensaje. Dejás que suene en silencio un rato.".replace(
                "Dejás", "Dejas"
            ),
            "Salís a caminar dos cuadras y volvés con la cabeza más clara, aunque la duda sigue ahí.".replace(
                "Salís", "Sales"
            ).replace("volvés", "vuelves"),
        ]
        if own >= 40:
            filler_pool.insert(1, f"Sigues con el {own}% y eso todavía te pesa de forma buena.")
        i = 0
        while count_words("\n\n".join(chunks)) < min_words and i < 200:
            chunks.append(filler_pool[i % len(filler_pool)])
            i += 1
    return apply_tuteo_fixes(strip_script_chrome("\n\n".join(c for c in chunks if c)).strip())


def validate_check_script(
    script: str,
    facts: dict[str, Any],
    *,
    strict_length: bool = True,
) -> tuple[bool, list[str], list[str]]:
    """Return (ok, hard_fails, warnings)."""
    hard: list[str] = []
    warn: list[str] = []
    text = script or ""
    low = _norm(text)
    wc = count_words(text)

    if not text.strip():
        hard.append("script vacío")
        return False, hard, warn

    if re.search(r"\bvos\b", text, re.I):
        hard.append("POV: aparece 'vos' — Check usa tú/te")
    voseo_hits = [a for a, _ in VOSEO_FIXES if re.search(rf"\b{re.escape(a)}\b", text, re.I)]
    if voseo_hits:
        hard.append("POV voseo: " + ", ".join(sorted(set(voseo_hits))))
    if not re.search(r"\b(tienes|te |tu |tus |compras|decides|entras)\b", low):
        hard.append("POV: no se siente segunda persona (tú/te/tienes)")

    for phrase in BANNED_OPENERS:
        if phrase in low[:400]:
            hard.append(f"cold open débil: '{phrase}'")
    for phrase in BANNED_MORAL:
        if phrase in low:
            hard.append(f"moraleja: '{phrase}'")
    for phrase in BANNED_CTA:
        if phrase in low:
            hard.append(f"CTA: '{phrase}'")
    for phrase in BANNED_FLUFF:
        if phrase in low:
            warn.append(f"fluff emocional: '{phrase}'")

    acq = facts.get("acquisition") or {}
    mode = str(facts.get("vehicle_mode") or "sports_team")
    own = acq.get("your_ownership")
    if own is not None:
        own_i = int(float(own))
        own_ok = (
            str(own_i) in text
            or f"{own_i}%" in text
            or f"{own_i} por ciento" in low
            or f"{own_i} porciento" in low
        )
        if not own_ok:
            # Soft for business drafts — still surface, but don't block delivery alone.
            (hard if mode == "sports_team" else warn).append(f"falta ownership {own_i}%")
    debt = acq.get("debt_assumed")
    if debt and float(debt) > 0:
        debt_s = str(int(debt))
        spoken_ok = "seiscientos cincuenta mil" in low or "650" in text.replace(",", "").replace(".", "")
        if debt_s not in text.replace(",", "").replace(".", "") and not spoken_ok:
            (hard if mode == "sports_team" else warn).append("falta la deuda de adquisición")
    if mode == "sports_team" and "51" not in text and own and float(own) == 51:
        hard.append("falta el 51%")

    champs = int(facts.get("championships") or 0)
    if mode == "sports_team" and champs == 0:
        if re.search(r"\b(ganaste|ganaron|son|eres)\s+(el\s+)?campeon", low) or re.search(r"\bel anillo\b", low):
            hard.append("contradice championships=0 (no inventar campeonato)")
    if mode == "business" and re.search(r"\b(playoff|campeonato|estadio|basquet|básquet|anillo)\b", low):
        warn.append("posible spill deportivo en guion business")

    end_nw = (facts.get("life_end") or {}).get("net_worth")
    try:
        nw_val = float(str(end_nw).replace(",", "").replace("$", "").strip()) if end_nw not in (None, "") else 0.0
    except (TypeError, ValueError):
        nw_val = 0.0
    if nw_val >= 1_000_000:
        if "millon" not in low and "45" not in text:
            warn.append("el payoff millonario-en-papel puede estar débil")
        lifestyle_hits = sum(
            1
            for k in (
                "departamento",
                "casa",
                "mud",
                "palco",
                "sold out",
                "lleno",
                "padres",
                "familia",
                "cena",
                "auto",
                "traje",
                "oficina propia",
                "viaje",
                "primera clase",
                "penthouse",
                "suite",
                "chofer",
                "te buscan",
                "quieren comprarte",
                "te llaman",
            )
            if k in low
        )
        if lifestyle_hits < 2:
            hard.append(
                "pico millonario sin impacto de vida: faltan beats sensoriales "
                "(casa/status/familia/venue lleno/gente que te busca). El número solo no alcanza."
            )
        elif lifestyle_hits < 3:
            warn.append("pico de éxito poco sensorial — sumá un beat más de contraste día-1 vs ahora")

    if strict_length:
        lo, hi = WORD_RANGE
        if wc < MIN_WORDS:
            hard.append(f"corto: {wc} palabras (mínimo {MIN_WORDS}, target {lo}–{hi})")
        elif wc > hi + 150:
            hard.append(f"largo: {wc} palabras (target {lo}–{hi})")
        elif wc > hi:
            warn.append(f"un poco largo: {wc} palabras")
    elif wc < MIN_WORDS:
        warn.append(f"draft corto: {wc} palabras (mínimo {MIN_WORDS})")

    if "oferta" not in low and "comprarte" not in low:
        warn.append("el final de la oferta de adquisición puede faltar")

    return (not hard), hard, warn


def estimate_duration_min(word_count: int) -> float:
    return round(word_count / float(WPM), 2)


def script_sections(script: str) -> list[dict[str, Any]]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", script or "") if p.strip()]
    labels = [
        ("cold_open", ("22 años", "un dolar", "un dólar", "oficina")),
        ("purchase", ("51", "quince mil", "15.000", "15,000", "deuda")),
        ("first_owner", ("estadio", "utilero", "llaves", "jefe")),
        ("season_grind", ("temporada", "derrota", "playoff")),
        ("life_change", ("renuncia", "badge", "mud", "departamento")),
        ("paper_millionaire", ("papel", "cuenta personal", "millones")),
        ("ending", ("27 años", "teléfono", "telefono", "oferta", "bloque")),
    ]
    found: dict[str, str] = {}
    for p in paras:
        low = _norm(p)
        for key, keys in labels:
            if key in found:
                continue
            if any(k in low for k in keys):
                found[key] = p[:160]
                break
    out = [{"id": k, "hit": found.get(k, "")} for k, _ in labels]
    out.append({"id": "paragraphs", "count": len(paras)})
    return out


def retention_flags(script: str) -> list[str]:
    """Soft flags: stretches of ~100 words without a turn."""
    words = (script or "").split()
    flags: list[str] = []
    turn = re.compile(
        r"pero |hasta que |entonces |por primera vez |esa noche |al día siguiente |"
        r"y entonces |de pronto |cinco años |dos meses |un año",
        re.I,
    )
    step = 90
    for i in range(0, max(0, len(words) - step), step):
        chunk = " ".join(words[i : i + step])
        if not turn.search(chunk) and len(chunk) > 200:
            flags.append(f"tramo ~{i}-{i+step} palabras sin giro evidente")
    return flags[:8]


def _chat_text(
    client: Any,
    model: str,
    system: str,
    user: str,
    *,
    temperature: float = 0.65,
    max_tokens: int = 8000,
    timeout: float = 180.0,
) -> str:
    r = client.chat.completions.create(
        model=model,
        temperature=temperature,
        timeout=timeout,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return strip_script_chrome((r.choices[0].message.content or "").strip())


def _mock_check_script(facts: dict[str, Any]) -> str:
    acq = facts.get("acquisition") or {}
    life0 = facts.get("life_start") or {}
    life1 = facts.get("life_end") or {}
    team = facts.get("team_name") or "Los Halcones"
    debt = int(acq.get("debt_assumed") or 650000)
    cash = int(acq.get("your_cash_contribution") or 15000)
    own = int(float(acq.get("your_ownership") or 51))
    start_cash = int(life0.get("personal_cash") or 20000)
    age0 = int(life0.get("age") or 22)
    age1 = int(life1.get("age") or 27)
    nw = int(float(life1.get("net_worth") or 45000000))
    seasons = facts.get("season_history") or []
    season_lines = []
    for s in seasons:
        season_lines.append(
            f"Temporada {s.get('season')}: cierras {s.get('record')}. Playoffs: {s.get('playoff_result')}. "
            f"Asistencia {s.get('attendance_avg')}."
        )
    if not season_lines:
        season_lines = ["La primera temporada duele. Llegas a playoffs. No hay campeonato."]
    body = f"""Tienes {age0} años.

Trabajas en una oficina y compartes departamento.

Tienes {start_cash} dólares ahorrados.

Y acabas de descubrir que un equipo profesional de básquet se vende por un dólar.

Hay una razón.

También tiene {debt} dólares de deuda.

Te sientas con el vendedor. El precio de compra es un dólar. Tú pones {cash} dólares y te quedas con el {own} por ciento. Inversores locales ponen el resto. El vendedor retiene el diez por ciento.

Firmas.

Entras a tu estadio. El utilero te entrega las llaves. Hace una pausa. "¿Dónde quiere que deje esto, jefe?"

{chr(10).join(season_lines)}

Todavía no hay campeonato. El equipo ya no está muerto.

Entregas la renuncia. El badge queda sobre el escritorio. Después mudas las cajas a un departamento propio.

En el papel vales {nw} dólares. En tu cuenta personal no queda prácticamente nada. Sigues pensando dos veces antes de pagar una cena.

Tienes {age1} años.

El estadio está vacío después del partido. El personal ya se fue. En la pantalla de tu teléfono aparece un correo. Oferta de adquisición.

Cinco años antes estabas sentado en una oficina.

Ahora alguien quiere comprarte {team}.

Bloqueas el teléfono.

Mañana lo lees.
"""
    # Pad mock so offline tests can opt into strict_length=False
    return body.strip()


def generate_check_script(project: dict[str, Any], *, use_llm: bool = True) -> dict[str, Any]:
    if not is_check_project(project):
        raise ValueError("generate_check_script is only for Check ALS projects")
    if not project.get("check_story_approved"):
        raise ValueError(
            "Aprobá la Story Architecture primero. El script de Check usa esa historia como única verdad."
        )
    arch = load_architecture(project)
    if not arch.get("generated") and not (arch.get("beats") or []) and not str(arch.get("synopsis") or "").strip():
        # Last chance: pull + reload (cold Vercel lambda).
        try:
            from src.documentary import cloud_sync
            from src.documentary.runtime import on_vercel

            if on_vercel() and cloud_sync.configured():
                cloud_sync.pull_project(str(project.get("id") or ""), light=True)
                arch = load_architecture(project)
        except Exception:
            pass
    if not arch.get("generated") and not (arch.get("beats") or []) and not str(arch.get("synopsis") or "").strip():
        raise ValueError(
            "No hay Story Architecture en disco (metadata). Regenerá la historia y volvé a Generate script."
        )
    mode = vehicle_mode(project)
    facts = locked_story_facts(arch, mode=mode)
    # If beats empty but synopsis exists, seed pad material from synopsis sentences.
    if not (facts.get("beats") or []) and str(arch.get("synopsis") or "").strip():
        syn = str(arch.get("synopsis") or "")
        facts["beats"] = [
            {"beat_id": f"s{i:02d}", "time": "", "event": sent.strip(), "consequence": ""}
            for i, sent in enumerate(re.split(r"(?<=[.!?])\s+", syn)[:40], start=1)
            if sent.strip()
        ]
        facts["ending_direction"] = facts.get("ending_direction") or syn[-400:]
    target = int(project.get("target_words") or TARGET_WORDS)
    target = max(WORD_RANGE[0], min(WORD_RANGE[1], target))

    quality: dict[str, Any] = {"revised": False, "retention_pass": False, "vehicle_mode": mode}
    script = ""

    if use_llm:
        try:
            key = openai_api_key()
            if not key:
                raise ValueError("OPENAI_API_KEY missing")
            from openai import OpenAI

            client = OpenAI(api_key=key)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            slim = facts_for_llm(facts)
            user = json.dumps(
                {
                    "instruction": (
                        f"Escribí SOLO el VO hablado (mínimo {MIN_WORDS} palabras, target {target}). "
                        f"vehicle_mode={mode}. Segunda persona tú/te. "
                        "PROHIBIDO: INT/EXT, NARRADOR, diálogos con nombres, ops (launch_company), meta. "
                        "Solo el texto que lee la IA en voz alta. "
                        "IMPACTO: cuando llegás a millonario / sold-out / major_success, "
                        "mostrá ≥3 beats sensoriales de lujo/status GANADO (contraste con el día 1). "
                        "No digas solo el número de millones — el viewer tiene que ENVIDIAR la vida."
                    ),
                    "locked_facts": slim,
                },
                ensure_ascii=False,
            )
            script = _chat_text(
                client, model, script_system(mode), user, temperature=0.7, max_tokens=7000, timeout=90.0
            )
            script = apply_tuteo_fixes(script)
            wc = count_words(script)
            if wc < MIN_WORDS:
                script = _chat_text(
                    client,
                    model,
                    EXPAND_SYSTEM,
                    json.dumps(
                        {
                            "note": (
                                f"Tiene {wc} palabras. MÍNIMO {MIN_WORDS}. Target {target}. "
                                f"vehicle_mode={mode}. Agregá escenas reales del state."
                            ),
                            "script": script,
                            "locked_facts": slim,
                        },
                        ensure_ascii=False,
                    ),
                    temperature=0.55,
                    max_tokens=7000,
                    timeout=90.0,
                )
                script = apply_tuteo_fixes(script)
                quality["revised"] = True
                quality["expand_tries"] = 1
        except Exception as e:
            quality["llm_error"] = str(e)[:400]
            append_log(str(project.get("id") or ""), f"check_script LLM fallback: {e}")
            script = apply_tuteo_fixes(_mock_check_script(facts))

    if not (script or "").strip():
        script = apply_tuteo_fixes(_mock_check_script(facts))

    # Always purge screenplay / ops / meta — VO only for TTS.
    script = apply_tuteo_fixes(strip_script_chrome(script))
    if (
        re.search(r"(?i)\b(int\.|ext\.|narrador\s*\(|fade out)\b", script)
        or re.search(r"(?i)\b(launch_company|advance_time|quit_job)\b", script)
        or count_words(script) < max(200, MIN_WORDS // 3)
    ):
        quality["stripped_screenplay_or_ops"] = True
        script = pad_script_from_beats("", facts, min_words=MIN_WORDS)
    elif count_words(script) < MIN_WORDS:
        script = pad_script_from_beats(script, facts, min_words=MIN_WORDS)
        quality["padded_from_beats"] = True

    script = apply_tuteo_fixes(strip_script_chrome(script))
    # Drop residual meta leaks one more time.
    script = "\n".join(
        ln
        for ln in script.splitlines()
        if not _OP_NAME_RE.match(ln.strip().rstrip("."))
        and "NO moraleja" not in ln
        and "Edad final del state" not in ln
    ).strip()
    if count_words(script) < MIN_WORDS:
        script = pad_script_from_beats(script, facts, min_words=MIN_WORDS)

    ok, hard, warn = validate_check_script(script, facts, strict_length=False)
    wc = count_words(script)
    if not ok:
        append_log(str(project["id"]), "check_script WARN: " + "; ".join(hard))
        quality["validation_soft_fail"] = True
        warn = list(warn) + [f"(revisar) {h}" for h in hard]
        hard = []
    if quality.get("llm_error"):
        warn = list(warn) + [f"LLM fallback: {quality['llm_error']}"]
    _persist_script(project, script, facts, wc, quality, hard, warn, approved=False)
    append_log(
        str(project["id"]),
        f"check_script generated words={wc} mode={mode} duration_min={estimate_duration_min(wc)}",
    )
    return project


def save_check_script(project: dict[str, Any], script: str) -> dict[str, Any]:
    arch = load_architecture(project)
    facts = locked_story_facts(arch, mode=vehicle_mode(project))
    script = apply_tuteo_fixes(strip_script_chrome(script or ""))
    if not script:
        raise ValueError("Script is empty.")
    ok, hard, warn = validate_check_script(script, facts, strict_length=False)
    if not ok:
        raise ValueError("Edited Check script failed:\n- " + "\n- ".join(hard))
    wc = count_words(script)
    _persist_script(project, script, facts, wc, {}, hard, warn, approved=False)
    append_log(str(project["id"]), f"check_script edited words={wc}")
    return project


def _persist_script(
    project: dict[str, Any],
    script: str,
    facts: dict[str, Any],
    wc: int,
    quality: dict[str, Any],
    hard: list[str],
    warn: list[str],
    *,
    approved: bool,
) -> None:
    project["script"] = script
    project["script_approved"] = bool(approved)
    project["fact_check_status"] = "pending" if not approved else "approved"
    project["ui_step"] = "script"
    project["script_quality"] = quality
    project["script_warnings"] = list(hard) + list(warn)
    project["script_editorial_notes"] = warn
    project["target_words"] = TARGET_WORDS
    project["target_duration_min"] = [12, 15]
    set_checkpoint(project, "script_ready", True)
    set_checkpoint(project, "flow_pack_ready", False)
    from src.documentary.voice_script_sync import invalidate_voice_for_script_change

    invalidate_voice_for_script_change(project, reason="check script regenerated")
    root = project_dir(str(project["id"]))
    (root / "script").mkdir(parents=True, exist_ok=True)
    (root / "script" / "script.txt").write_text(script, encoding="utf-8")
    meta = {
        "word_count": wc,
        "target_words": TARGET_WORDS,
        "target_range": list(WORD_RANGE),
        "estimated_duration_min": estimate_duration_min(wc),
        "template": "check_als_es",
        "language": "es",
        "workflow": "check_als",
        "pov": "second_person",
        "factuality": "fiction",
        "sections": script_sections(script),
        "retention_flags": retention_flags(script),
        "validation_hard": hard,
        "validation_warnings": warn,
        "quality": quality,
        "locked_numbers": {
            "acquisition": facts.get("acquisition"),
            "championships": facts.get("championships"),
            "life_end": facts.get("life_end"),
            "season_history": [
                {
                    "season": s.get("season"),
                    "record": s.get("record"),
                    "playoff_result": s.get("playoff_result"),
                    "attendance_avg": s.get("attendance_avg"),
                    "team_value": s.get("team_value"),
                }
                for s in (facts.get("season_history") or [])
                if isinstance(s, dict)
            ],
        },
    }
    (root / "script" / "script_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    save_project(project)
