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

SCRIPT_SYSTEM_SHARED = """Eres el guionista de Check: fantasías cinematográficas en segunda persona para YouTube.

ESCRIBES UN GUION PARA SER ESCUCHADO. Español de España/Latino neutro. Tú/te/tu/tienes. NUNCA vos/tenés/podés/lanzás.

El espectador ES el protagonista. No un documental. No un profesor. No un narrador motivacional. No ChatGPT. No un artículo. No un resumen empresarial.

FORMA:
- Mínimo 1100 palabras. Rango 1100–2300. Target 1800. ~12–15 minutos. Preferí un guion denso, no inflado.
- Párrafos cortos (1–4 oraciones). Escenas, no inventario.
- Segunda persona constante.
- Cifras: cuando den dopamina o tensión. Spoken in Spanish in the VO. No saturar.

COLD OPEN (20–30s): entrar directo con edad / trabajo / cash / oportunidad concreta.
PROHIBIDO abrir con ¿te imaginas / en este video / esta es la historia.

PROGRESIÓN = MOMENTOS, no lista de métricas. EMOCIÓN POR EVENTOS, nunca "te emocionas".
FINAL: escena concreta del state. Sin moraleja. Sin CTA. Sin "aprendiste que".

LOS HECHOS DEL JSON SON LEY. Mejorá CÓMO se cuentan. NO cambies números ni ownership.

Return ONLY the script text. No title. No headings. No markdown. No notes."""

SCRIPT_SYSTEM_SPORTS = (
    SCRIPT_SYSTEM_SHARED
    + """

VEHÍCULO: compra de equipo deportivo.
HOOK PAYOFF PRONTO: precio + deuda + tu cash → tu %. Inversores → su %.
DEPORTES: season_history EXACTA. championships=0 salvo que el state diga lo contrario. NO inventes campeonato.
CONFLICTO: deuda, mal arranque, roster, derrotas, millonario en papel / cash ~0.
MOMENTOS: dueño, utilero/llaves, sponsor, playoffs, sold out, renuncia, mudanza.
"""
)

SCRIPT_SYSTEM_BUSINESS = (
    SCRIPT_SYSTEM_SHARED
    + """

VEHÍCULO: negocio / creador / startup / empresa (NO deporte, NO estadio, NO playoffs, NO campeonato, NO deuda 650k de básquet).
HOOK PAYOFF PRONTO: lanzás la empresa / firmás con socios → tu ownership % exacto del state + cash de inversores.
PROGRESIÓN: primeros clientes/views → escala → crisis → payoff de vida → oferta/tracción final.
PROHIBIDO inventar: básquet, liga, playoffs, estadio, utilero, anillo, temporada deportiva.
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
            "final: oferta/tracción/decisión abierta — sin moraleja",
        ]
        ending = (
            "Edad final del state. Estás solo un momento. En el teléfono: alguien quiere comprarte o asociarse. "
            "Bloqueas. Mañana lo lees. NO moraleja."
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
            "millonario en papel vs cash personal ~0",
            "final: estadio vacío, mail de oferta, bloqueas",
        ]
        ending = (
            "27 años. Estadio vacío. Correo de oferta de adquisición. Bloqueas. Mañana lo lees. NO moraleja."
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


EXPAND_SYSTEM = """Eres guionista de Check. El guion está CORTO.

Expandí con ESCENAS concretas del state (no relleno, no moraleja, no inventario).
Más momentos concretos de la historia aprobada: lanzamiento/compra, setbacks, payoffs de vida, decisiones, final.
Tú/te. Nunca vos. Conservá TODOS los números y hechos locked.
Si vehicle_mode=business: PROHIBIDO deporte/estadio/playoffs.
Mínimo 1100 palabras. Target ~1800. Devolvé el guion completo, no un parche.
Solo el texto del guion."""


def facts_for_llm(facts: dict[str, Any]) -> dict[str, Any]:
    out = dict(facts)
    beats = []
    for b in (facts.get("beats") or [])[:40]:
        if not isinstance(b, dict):
            continue
        beats.append(
            {
                "id": b.get("beat_id"),
                "time": b.get("time"),
                "event": b.get("event"),
                "purpose": b.get("story_purpose"),
            }
        )
    out["beats"] = beats
    return out


def _norm(text: str) -> str:
    return (text or "").lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


def strip_script_chrome(script: str) -> str:
    text = (script or "").strip()
    text = re.sub(r"^```(?:text|markdown|md)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Drop a leading title line if the model adds one
    lines = text.splitlines()
    if lines and lines[0].startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def apply_tuteo_fixes(script: str) -> str:
    out = script
    for src, dst in VOSEO_FIXES:
        out = re.sub(rf"\b{re.escape(src)}\b", dst, out, flags=re.IGNORECASE)
    out = re.sub(r"\b[Vv]os\b", "tú", out)
    return out


def pad_script_from_beats(script: str, facts: dict[str, Any], *, min_words: int = MIN_WORDS) -> str:
    """Deterministic scene pad so generation never dies on word floor alone."""
    text = (script or "").strip()
    if count_words(text) >= min_words:
        return text
    acq = facts.get("acquisition") or {}
    own = int(float(acq.get("your_ownership") or 0) or 0)
    chunks = [text] if text else []
    for b in facts.get("beats") or []:
        if not isinstance(b, dict):
            continue
        event = str(b.get("event") or "").strip()
        if not event:
            continue
        when = str(b.get("time") or "").strip()
        cons = str(b.get("consequence") or "").strip()
        line = f"{when + '. ' if when else ''}{event}."
        if cons:
            line += f" {cons}."
        joined = " ".join(chunks)
        if own and own >= 40 and f"{own}" not in joined:
            line += f" Todavía tienes el {own}%."
        chunks.append(line)
        if count_words("\n\n".join(chunks)) >= min_words:
            break
    if count_words("\n\n".join(chunks)) < min_words:
        life1 = facts.get("life_end") or {}
        end = str(facts.get("ending_direction") or "").strip()
        filler = " ".join(
            x
            for x in (
                f"Tienes {life1.get('age') or 27} años.",
                f"Trabajas como {life1.get('job')}." if life1.get("job") else "",
                end,
                "Miras el teléfono. Bloqueas. Mañana lo lees.",
            )
            if x
        )
        while count_words("\n\n".join(chunks)) < min_words:
            chunks.append(filler)
            if len(chunks) > 80:
                break
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
    if end_nw and float(end_nw) >= 1_000_000:
        if "millon" not in low and "45" not in text:
            warn.append("el payoff millonario-en-papel puede estar débil")

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
                        f"Escribí el guion COMPLETO de YouTube. OBLIGATORIO: mínimo {MIN_WORDS} palabras "
                        f"(target {target}, máximo {WORD_RANGE[1]}). vehicle_mode={mode}. "
                        "Escenas, no resumen. Solo texto del VO."
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
            if str(arch.get("synopsis") or "").strip():
                script = (script + "\n\n" + str(arch.get("synopsis"))).strip()

    if not (script or "").strip():
        script = apply_tuteo_fixes(_mock_check_script(facts))
        if str(arch.get("synopsis") or "").strip():
            script = (script + "\n\n" + str(arch.get("synopsis"))).strip()

    if count_words(script) < MIN_WORDS:
        script = pad_script_from_beats(script, facts, min_words=MIN_WORDS)
        quality["padded_from_beats"] = True

    script = apply_tuteo_fixes(strip_script_chrome(script))
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
