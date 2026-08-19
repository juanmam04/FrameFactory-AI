"""Check ALS script: Spanish second-person YouTube narration from approved Story Architecture."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from src.documentary.formats.check_als.story_arch import load_architecture
from src.documentary.formats.check_als.story_architect import is_check_project
from src.documentary.openai_key import openai_api_key
from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.script_generator import count_words

TARGET_WORDS = 2100
WORD_RANGE = (1900, 2300)
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
    ("sos", "eres"),
    ("estás viviendo", "estás viviendo"),
    ("andá ", "ve "),
    ("decís", "dices"),
    ("venís", "vienes"),
    ("salís", "sales"),
    ("entrás", "entras"),
    ("ves ", "ves "),
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

SCRIPT_SYSTEM = """Eres el guionista de Check: fantasías cinematográficas en segunda persona para YouTube.

ESCRIBES UN GUION PARA SER ESCUCHADO. Español de España/Latino neutro. Tú/te/tu/tienes. NUNCA vos/tenés/podés.

El espectador ES el protagonista. No un documental. No un profesor. No un narrador motivacional. No ChatGPT. No un artículo. No un resumen empresarial.

FORMA:
- 1900–2300 palabras. Target 2100. 12–15 minutos. Preferí 13 minutos excelentes, no 18 inflados.
- Párrafos cortos (1–4 oraciones). Escenas, no inventario.
- Segunda persona constante.
- Cifras: cuando den dopamina o tensión. Spoken in Spanish in the VO ("seiscientos cincuenta mil dólares"). No saturar.

COLD OPEN (20–30s): entrar directo. Nivel:
Tienes 22 años. Trabajas en una oficina y compartes departamento. Tienes veinte mil dólares ahorrados. Y acabas de descubrir que un equipo profesional de básquet se vende por un dólar. Hay una razón. También tiene seiscientos cincuenta mil dólares de deuda.
NO copies palabra por palabra. SÍ ese nivel de claridad.
PROHIBIDO abrir con ¿te imaginas / en este video / esta es la historia.

HOOK PAYOFF PRONTO: después del dólar, explicar la compra YA (no a los 5 minutos):
precio $1 + deuda $650k + tus $15k → 51%. Inversores $85k → 39%. Vendedor 10% + seller financing $200k.

PROGRESIÓN = MOMENTOS, no lista de métricas. Convertí hitos del STATE en escenas.
NO: "La asistencia aumenta y consigues patrocinadores."
SÍ: "Dos meses después, miras desde el túnel y por primera vez no ves huecos entre las primeras filas."

EMOCIÓN POR EVENTOS (utilero con llaves, badge sobre el escritorio), nunca "te emocionas".

DEPORTES: usa season_history EXACTA. championships=0. NO inventes campeonato. La gracia es que todavía NO ganaste.
Progresión: equipo muerto → competitivo → playoffs → finales → contender habitual.

CONFLICTO real: deuda, mal arranque, costo de roster, instalaciones, owner injection, derrotas, millonario en papel / cash ~0.
No abusar de lesiones.

MOMENTOS ASPIRACIONALES: darles ESPACIO (no una oración): primera entrada como dueño, reunión, primer sponsor (en el tiempo REAL del state), playoffs, sold out, renuncia, mudanza, media, valuation, familia.

MILLONARIO EN PAPEL: cash personal ≈ $0, net worth ≈ cifra final. Sin dramatizar de más.

FINAL: escena. Estadio vacío. Correo de oferta de adquisición en el teléfono. Bloqueas. Mañana lo lees.
Sin moraleja. Sin CTA. Sin "aprendiste que".

LOS HECHOS DEL JSON SON LEY. Podés mejorar CÓMO se cuentan. NO cambies números, records, ownership, championships, ni el orden real de payoffs.

Return ONLY the script text. No title. No headings. No markdown. No notes."""

RETENTION_SYSTEM = """Eres editor de retención de YouTube para Check (segunda persona, tú/te).

Reescribí el guion SIN agregar relleno y SIN cambiar hechos/números/records.

Cada ~30–45 segundos (≈75–110 palabras) tiene que haber un cambio o una pregunta que el espectador quiera pagar.
Si un tramo no cambia nada: recortar o reordenar.
Conservá cold open, payoff de la compra temprano, momentos aspiracionales, millonario-en-papel, final del teléfono.
Tú/te. Nunca vos. 1900–2300 palabras. Solo el guion."""


def locked_story_facts(arch: dict[str, Any]) -> dict[str, Any]:
    """Compact source of truth for the script model. Never invent outside this."""
    bp = arch.get("blueprint") if isinstance(arch.get("blueprint"), dict) else {}
    iw = arch.get("initial_world") if isinstance(arch.get("initial_world"), dict) else {}
    fw = arch.get("final_world") if isinstance(arch.get("final_world"), dict) else {}
    review = arch.get("review") if isinstance(arch.get("review"), dict) else {}
    vehicle = bp.get("business_or_vehicle") if isinstance(bp.get("business_or_vehicle"), dict) else {}
    acq = vehicle.get("acquisition") if isinstance(vehicle.get("acquisition"), dict) else {}
    if not acq:
        acq = review.get("acquisition") if isinstance(review.get("acquisition"), dict) else {}
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
    return {
        "team_name": fiction.get("team_name") or team1.get("name") or "Los Halcones de la Ciudad",
        "league_name": fiction.get("league_name") or team1.get("league") or "",
        "city": fiction.get("city") or team1.get("city") or "",
        "acquisition": {
            "asking_price": acq.get("asking_price", 1),
            "debt_assumed": acq.get("debt_assumed", 650000),
            "your_cash_contribution": acq.get("your_cash_contribution", 15000),
            "local_investors_cash": acq.get("local_investors_cash", 85000),
            "seller_financing": acq.get("seller_financing", 200000),
            "your_ownership": acq.get("your_ownership", 51),
            "investor_ownership": acq.get("investor_ownership", 39),
            "seller_retained": acq.get("seller_retained", 10),
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
            "job": life1.get("job") or per1.get("working_status") or "dueño del equipo",
            "home": life1.get("home") or per1.get("living_situation") or "",
            "personal_cash": life1.get("personal_cash") if life1.get("personal_cash") is not None else per1.get("cash"),
            "net_worth": life1.get("personal_net_worth") if life1.get("personal_net_worth") is not None else per1.get("net_worth"),
        },
        "team_start": {
            "valuation": team0.get("valuation"),
            "debt": team0.get("debt") or fin0.get("team_debt"),
            "attendance": team0.get("attendance"),
            "capacity": team0.get("capacity") or 4800,
            "cash": team0.get("cash") or fin0.get("team_cash"),
        },
        "team_end": {
            "valuation": team1.get("valuation"),
            "debt": team1.get("debt") or fin1.get("team_debt"),
            "attendance": team1.get("attendance"),
            "capacity": team1.get("capacity") or 4800,
            "cash": team1.get("cash") or fin1.get("team_cash"),
            "annual_revenue": fin1.get("annual_revenue"),
            "debt_risk_state": fin1.get("debt_risk_state"),
        },
        "ownership_ledger": ledger or {"protagonist": 51, "investors": 39, "seller": 10},
        "championships": int((sp1.get("championships") or 0) or 0),
        "season_history": list(sp1.get("season_history") or review.get("season_history") or []),
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
        "must_include_scenes": [
            "cold open: 22 / oficina / depto compartido / ~$20k / equipo a $1 / deuda grande",
            "payoff compra temprano: $1 + deuda + tu cash → 51%",
            "primera entrada al estadio / utilero / llaves / 'jefe'",
            "mal arranque + deuda",
            "owner injection de $5,000 si existe en financial_events",
            "progresión deportiva EXACTA por temporada (records y playoff_result)",
            "sold out 4,800 en el tiempo real del state",
            "renuncia (badge) y mudanza a depto propio — en el tiempo real del state",
            "primer sponsor en el tiempo real del state",
            "millonario en papel vs cash personal ~0",
            "final: 27 años, estadio vacío, mail de oferta de adquisición, bloqueas el teléfono, mañana lo lees",
        ],
        "ending_direction": (
            "27 años. El estadio está vacío. El personal ya se fue. En el teléfono, un correo: oferta de adquisición. "
            "Cinco años antes estabas en una oficina. Ahora alguien quiere comprarte el equipo. Bloqueas. Mañana lo lees. "
            "NO venden. NO moraleja. El loop 'qué tan lejos puede llegar' queda abierto."
        ),
        "beats": beats,
        "disclaimer": "Ficción. No presentar como factual.",
    }


EXPAND_SYSTEM = """Eres guionista de Check. El guion está CORTO.

Expandí con ESCENAS concretas del state (no relleno, no moraleja, no inventario).
Más momentos: reunión de compra, utilero, mal arranque, inyección, un partido, playoffs, sold out, renuncia, mudanza, familia, millonario-en-papel, final del teléfono.
Tú/te. Nunca vos. Conservá TODOS los números y records. championships=0.
Target 2050–2250 palabras. Devolvé el guion completo, no un parche.
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
    own = acq.get("your_ownership")
    if own is not None and str(int(float(own))) not in text and f"{float(own):.0f}%" not in text:
        hard.append(f"falta ownership {own}%")
    debt = acq.get("debt_assumed")
    if debt:
        debt_s = str(int(debt))
        spoken_ok = "seiscientos cincuenta mil" in low or "650" in text.replace(",", "").replace(".", "")
        if debt_s not in text.replace(",", "").replace(".", "") and not spoken_ok:
            hard.append("falta la deuda de adquisición")
    if "51" not in text and own and float(own) == 51:
        hard.append("falta el 51%")

    champs = int(facts.get("championships") or 0)
    if champs == 0:
        if re.search(r"\b(ganaste|ganaron|son|eres)\s+(el\s+)?campeon", low) or re.search(r"\bel anillo\b", low):
            hard.append("contradice championships=0 (no inventar campeonato)")

    end_nw = (facts.get("life_end") or {}).get("net_worth")
    if end_nw and float(end_nw) >= 1_000_000:
        if "millon" not in low and "45" not in text:
            warn.append("el payoff millonario-en-papel puede estar débil")

    if strict_length:
        lo, hi = WORD_RANGE
        if wc < lo:
            hard.append(f"corto: {wc} palabras (target {lo}–{hi})")
        elif wc > hi + 150:
            hard.append(f"largo: {wc} palabras (target {lo}–{hi})")
        elif wc > hi:
            warn.append(f"un poco largo: {wc} palabras")
    elif wc < 80:
        warn.append(f"draft corto: {wc} palabras")

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
    if not arch.get("generated") and not (arch.get("beats") or []):
        raise ValueError("No hay Story Architecture persistida.")
    facts = locked_story_facts(arch)
    target = int(project.get("target_words") or TARGET_WORDS)
    target = max(WORD_RANGE[0], min(WORD_RANGE[1], target))

    quality: dict[str, Any] = {"revised": False, "retention_pass": False}

    if use_llm:
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
                    f"Escribí el guion COMPLETO de YouTube. OBLIGATORIO: {target} palabras "
                    f"(mínimo {WORD_RANGE[0]}, máximo {WORD_RANGE[1]}). "
                    "Escenas, no resumen. Solo texto del VO."
                ),
                "locked_facts": slim,
            },
            ensure_ascii=False,
        )
        script = _chat_text(client, model, SCRIPT_SYSTEM, user, temperature=0.7, max_tokens=9000)
        script = apply_tuteo_fixes(script)
        wc = count_words(script)
        if wc < WORD_RANGE[0]:
            script = _chat_text(
                client,
                model,
                EXPAND_SYSTEM,
                json.dumps(
                    {
                        "note": f"Tiene {wc} palabras. Llevalo a {target}. No inventes campeonato.",
                        "script": script,
                        "locked_facts": slim,
                    },
                    ensure_ascii=False,
                ),
                temperature=0.55,
                max_tokens=9000,
            )
            script = apply_tuteo_fixes(script)
            quality["revised"] = True
        wc = count_words(script)
        if wc >= 1600:
            kept = script
            revised = _chat_text(
                client,
                model,
                RETENTION_SYSTEM + f"\nNO bajes de {WORD_RANGE[0]} palabras. Si recortás, reemplazá con otra escena real.",
                json.dumps(
                    {
                        "note": f"Pasada de retención. Palabras actuales: {count_words(script)}. Piso {WORD_RANGE[0]}.",
                        "script": script,
                        "locked_facts": {k: slim[k] for k in slim if k != "beats"},
                    },
                    ensure_ascii=False,
                ),
                temperature=0.3,
                max_tokens=9000,
            )
            revised = apply_tuteo_fixes(revised)
            if count_words(revised) >= WORD_RANGE[0]:
                script = revised
                quality["retention_pass"] = True
            else:
                script = kept
                quality["retention_discarded_shrink"] = True
        wc = count_words(script)
        if wc < WORD_RANGE[0]:
            script = _chat_text(
                client,
                model,
                EXPAND_SYSTEM,
                json.dumps(
                    {
                        "note": f"Todavía corto ({wc}). Target {target}. Más escenas del state.",
                        "script": script,
                        "locked_facts": slim,
                    },
                    ensure_ascii=False,
                ),
                temperature=0.5,
                max_tokens=9000,
            )
            script = apply_tuteo_fixes(script)
            quality["expanded_twice"] = True
    else:
        script = apply_tuteo_fixes(_mock_check_script(facts))

    script = apply_tuteo_fixes(strip_script_chrome(script))
    ok, hard, warn = validate_check_script(script, facts, strict_length=use_llm)
    wc = count_words(script)
    if not ok and use_llm:
        append_log(str(project["id"]), "check_script REJECTED: " + "; ".join(hard))
        _persist_script(project, script, facts, wc, quality, hard, warn, approved=False)
        raise ValueError(
            "El guion de Check no pasó validación:\n- "
            + "\n- ".join(hard)
            + ("\n\nAvisos:\n- " + "\n- ".join(warn) if warn else "")
        )

    _persist_script(project, script, facts, wc, quality, hard, warn, approved=False)
    append_log(str(project["id"]), f"check_script generated words={wc} duration_min={estimate_duration_min(wc)}")
    return project


def save_check_script(project: dict[str, Any], script: str) -> dict[str, Any]:
    arch = load_architecture(project)
    facts = locked_story_facts(arch)
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
