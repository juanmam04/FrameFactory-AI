"""Deterministic story-quality, magnitude, diversity, and penalty helpers (Fase 1.6.1)."""
from __future__ import annotations

import math
import re
from typing import Any

from src.documentary.formats.check_als.editorial import FANTASY_DIVERSITY, STORY_ENGINE_KEYS

_MONEY_RE = re.compile(
    r"\$\s*([\d][\d.,]*)\s*(millones?|mds?|mm\b|[kmb]\b)?"
    r"|([\d][\d.,]*)\s*(millones?)",
    re.I,
)
_EMP_RE = re.compile(r"(\d[\d.,]*)\s*(emplead|employees|personas)", re.I)
_COUNTRY_RE = re.compile(
    r"(\d+)\s*(pa[ií]ses|countries)|operaciones en\s+(\d+)|presencia en\s+(\d+)",
    re.I,
)
_MONTHLY_RE = re.compile(
    r"\$\s*[\d][\d.,]*\s*(?:/\s*mes|al mes|mensuales?|mrr)|ingresos mensuales[^\d$]{0,12}\$\s*[\d][\d.,]*",
    re.I,
)

GENERIC_PHYSICAL_PRODUCTS = (
    "productos sostenibles",
    "productos biodegradables",
    "productos ecológicos",
    "productos ecologicos",
    "productos eco",
    "eco-innovación",
    "eco-innovacion",
    "línea similar",
    "linea similar",
    "productos premium",
)

AD_THUMB_TEXT = (
    r"^¡?\s*descubre\b",
    r"^¡?\s*convi[eé]rtete\b",
    r"^¡?\s*transforma tu mundo\b",
    r"eco-innovaci[oó]n",
    r"en acci[oó]n",
    r"^¡?\s*el futuro de\b",
)

INDUSTRY_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ticket_resale", ("entrada", "reventa", "concierto", "ticket", "scalp")),
    (
        "lodging",
        (
            "cabaña",
            "cabana",
            "eco-resort",
            "ecoresort",
            "eco resort",
            "hotel",
            "motel",
            "hospedaje",
            "ecoturismo",
            "eco-turismo",
            "glamping",
            "alojamiento",
        ),
    ),
    ("laundry", ("lavander", "lavadero")),
    ("food_delivery", ("cena gourmet", "cenas gourmet", "a domicilio", "meal kit", "suscripción de cenas", "suscripcion de cenas")),
    ("sports_ip", ("merchandising", "derechos de un equipo", "licencias su merchand", "licenciamiento de marca")),
    ("eco_goods", ("biodegradable", "productos sostenibles", "productos ecol", "fábrica de productos", "fabrica de productos")),
    ("workshop_saas", ("recepcionista ia", "saas de suscripción para reservas", "saas de suscripcion para reservas", "gestión de talleres", "gestion de talleres")),
    ("music_rights", ("derechos de música", "derechos de musica", "catálogo musical", "catalogo musical")),
    ("marketplace", ("marketplace",)),
    ("logistics", ("entregas", "logíst", "logistic", "última milla", "ultima milla")),
    ("real_estate", ("inmobil", "edificio", "terreno")),
    ("manufacturing", ("fábrica", "fabrica", "manufactur")),
    ("software_saas", ("saas", "software", "plataforma", "app ")),
    ("sports_team", ("equipo deportivo", "club de fútbol", "club de futbol", "liga")),
    ("food_service", ("restaurante", "cafeter", "gourmet")),
)

MODEL_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("arbitrage", ("reventa", "arbitraje", "arbitrage")),
    ("subscription", ("suscrip", "saas", "$99", "mensual")),
    ("franchise", ("franquic",)),
    ("licensing", ("licenc", "regalías", "regalias", "royalt")),
    ("marketplace", ("marketplace",)),
    ("acquisition", ("compras", "adquieres", "$1")),
    ("real_estate", ("terreno", "edificio", "inmobil")),
    ("manufacturing", ("fábrica", "fabrica", "producc")),
    ("hospitality", ("hotel", "cabaña", "cabana", "resort", "motel")),
)

START_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("vacant_land", ("terreno baldío", "terreno baldio", "lote vacío", "lote vacio")),
    ("dead_shop", ("quiebra", "cerrada", "muerta", "en crisis")),
    ("day_job", ("9 a 5", "tiempo completo", "empleo a tiempo", "trabajo de tiempo")),
    ("front_desk", ("recepción", "recepcion", "mostrador", "contestas el teléfono", "contestas el telefono")),
    ("side_hustle", ("tiempo parcial", "pocos ahorros", "$500")),
)


def _norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def _low(v: Any) -> str:
    return _norm(v).lower()


def _blob(package: dict[str, Any]) -> str:
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    ws = package.get("world_seeds") if isinstance(package.get("world_seeds"), dict) else {}
    core = package.get("story_core") if isinstance(package.get("story_core"), dict) else {}
    return " ".join(
        [
            _norm(package.get("title")),
            _norm(package.get("premise")),
            _norm(package.get("story_spine")),
            _norm(package.get("one_line_fantasy")),
            _norm(package.get("starting_state")),
            _norm(package.get("end_state")),
            _norm(ws.get("business_or_career_type")),
            _norm(engine.get("business_or_progress_mechanism")),
            _norm(engine.get("growth_mechanism")),
            _norm(engine.get("specific_opportunity")),
            _norm(core.get("starting_situation")),
            _norm(core.get("core_mechanism")),
            _norm(core.get("causal_growth_path")),
            _norm(core.get("major_reversal")),
            _norm(core.get("ending_direction")),
        ]
    )


def _parse_num(raw: str) -> float | None:
    s = (raw or "").replace(" ", "").replace(",", "")
    if s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_money_values(text: Any) -> list[float]:
    """Extract dollar-like magnitudes. Millions become 1e6 units."""
    t = str(text or "")
    out: list[float] = []
    for m in _MONEY_RE.finditer(t):
        if m.group(1) is not None:
            n = _parse_num(m.group(1))
            unit = (m.group(2) or "").lower()
        else:
            n = _parse_num(m.group(3) or "")
            unit = (m.group(4) or "").lower()
        if n is None:
            continue
        if unit.startswith("millon") or unit in {"m", "mm", "md", "mds"}:
            n *= 1_000_000
        elif unit == "k":
            n *= 1_000
        elif unit == "b":
            n *= 1_000_000_000
        if 0 < n < 1e15:
            out.append(n)
    return out


def parse_employees(text: Any) -> int:
    m = _EMP_RE.search(str(text or ""))
    if not m:
        return 0
    n = _parse_num(m.group(1))
    return int(n) if n else 0


def parse_countries(text: Any) -> int:
    t = str(text or "")
    m = _COUNTRY_RE.search(t)
    if m:
        for g in m.groups():
            if g and g.isdigit():
                return int(g)
    if re.search(r"\binternacional(?:mente)?\b|\b10 países\b|\bvarios países\b", t, re.I):
        return 2
    return 1 if t.strip() else 0


def endgame_money(package: dict[str, Any]) -> float:
    """Money that backs titles / ceiling — not early ladder proofs."""
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    contrast = package.get("start_end_contrast") if isinstance(package.get("start_end_contrast"), dict) else {}
    ws = package.get("world_seeds") if isinstance(package.get("world_seeds"), dict) else {}
    parts = [
        package.get("end_state"),
        contrast.get("end"),
        ws.get("target_outcome"),
        engine.get("endgame"),
    ]
    vals = parse_money_values(" ".join(_norm(x) for x in parts))
    blob = " ".join(_norm(x) for x in parts)
    for m in _MONTHLY_RE.finditer(blob):
        chunk_vals = parse_money_values(m.group(0))
        if chunk_vals:
            vals.append(max(chunk_vals) * 12)
    return max(vals) if vals else 0.0


def max_end_money(package: dict[str, Any]) -> float:
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    parts = [
        package.get("end_state"),
        (package.get("start_end_contrast") or {}).get("end") if isinstance(package.get("start_end_contrast"), dict) else "",
        (package.get("world_seeds") or {}).get("target_outcome") if isinstance(package.get("world_seeds"), dict) else "",
        engine.get("endgame"),
        engine.get("first_major_reward"),
        " ".join(ladder_event_texts(package.get("escalation_ladder"))),
    ]
    blob = " ".join(_norm(x) for x in parts)
    vals = parse_money_values(blob)
    monthly = 0.0
    for m in _MONTHLY_RE.finditer(blob):
        chunk_vals = parse_money_values(m.group(0))
        if chunk_vals:
            monthly = max(monthly, max(chunk_vals) * 12)
    if monthly:
        vals.append(monthly)
    return max(vals) if vals else 0.0


def start_money(package: dict[str, Any]) -> float:
    ws = package.get("world_seeds") if isinstance(package.get("world_seeds"), dict) else {}
    vals = parse_money_values(ws.get("starting_cash") or "") + parse_money_values(package.get("starting_state") or "")
    return min(vals) if vals else 0.0


def ladder_event_texts(raw: Any) -> list[str]:
    items = raw if isinstance(raw, list) else []
    out: list[str] = []
    for row in items:
        if isinstance(row, dict):
            ev = _norm(row.get("event") or row.get("nivel") or row.get("description") or row.get("text") or "")
            if not ev and isinstance(row.get("level"), str):
                ev = _norm(row.get("level"))
            delta = _norm(row.get("world_delta") or row.get("delta") or "")
            if ev and delta:
                out.append(f"{ev} — {delta}")
            elif ev:
                out.append(ev)
        elif _norm(row):
            out.append(_norm(row))
    return out


def _family_from(blob: str, table: tuple[tuple[str, tuple[str, ...]], ...]) -> str:
    low = blob.lower()
    for name, cues in table:
        if any(c in low for c in cues):
            return name
    return "other"


def concept_fingerprint(package: dict[str, Any]) -> dict[str, str]:
    blob = _blob(package)
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    core = package.get("story_core") if isinstance(package.get("story_core"), dict) else {}
    fantasy = _low(package.get("one_line_fantasy") or package.get("life_fantasy") or "")
    fantasy_type = "other"
    for ft in FANTASY_DIVERSITY:
        if ft.replace("_", " ") in fantasy or ft in fantasy:
            fantasy_type = ft
            break
    if "imperio" in blob.lower() or "empire" in blob.lower():
        fantasy_type = "empire" if fantasy_type == "other" else fantasy_type
    return {
        "industry": _family_from(blob, INDUSTRY_FAMILIES),
        "business_model": _family_from(blob, MODEL_FAMILIES),
        "core_mechanism": _low(engine.get("business_or_progress_mechanism") or core.get("core_mechanism"))[:80],
        "starting_situation": _family_from(
            _norm(package.get("starting_state"))
            + " "
            + _norm(package.get("premise"))
            + " "
            + _norm(core.get("starting_situation")),
            START_FAMILIES,
        ),
        "growth_engine": _low(engine.get("growth_mechanism") or core.get("causal_growth_path"))[:80],
        "fantasy_type": fantasy_type,
        "major_reversal": _low(core.get("major_reversal") or engine.get("major_threat"))[:80],
        "ending_direction": _low(core.get("ending_direction") or package.get("ending_direction"))[:80],
    }


def _token_set(text: str) -> set[str]:
    stop = {
        "para", "como", "este", "esta", "estos", "con", "una", "unos", "del", "los", "las",
        "por", "que", "and", "the", "your", "with", "from",
    }
    return {w for w in re.findall(r"[a-záéíóúñü0-9$]+", _low(text)) if len(w) > 3 and w not in stop}


def _jaccard(a: str, b: str) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def is_same_movie(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """True if a viewer would read these as the same video with another skin."""
    fa, fb = concept_fingerprint(a), concept_fingerprint(b)
    blob_a, blob_b = _low(_blob(a)), _low(_blob(b))
    narrow = {
        "ticket_resale",
        "laundry",
        "lodging",
        "workshop_saas",
        "music_rights",
        "eco_goods",
        "sports_ip",
    }
    if fa["industry"] in narrow and fa["industry"] == fb["industry"]:
        return True
    food_a = fa["industry"] in {"food_service", "food_delivery"} or any(
        x in blob_a for x in ("restaurante", "gourmet", "cafeter")
    )
    food_b = fb["industry"] in {"food_service", "food_delivery"} or any(
        x in blob_b for x in ("restaurante", "gourmet", "cafeter")
    )
    fran_a = fa["business_model"] == "franchise" or "franquic" in blob_a
    fran_b = fb["business_model"] == "franchise" or "franquic" in blob_b
    if food_a and food_b and fran_a and fran_b:
        return True
    matched = 0
    for k in ("industry", "business_model", "starting_situation", "fantasy_type"):
        if fa[k] == fb[k] and fa[k] not in {"", "other"}:
            matched += 1
    if matched >= 3 and _jaccard(fa["core_mechanism"], fb["core_mechanism"]) >= 0.28:
        return True
    if _jaccard(fa["core_mechanism"], fb["core_mechanism"]) >= 0.55:
        return True
    if (
        fa.get("major_reversal")
        and fa.get("major_reversal") == fb.get("major_reversal")
        and fa["industry"] == fb["industry"]
        and fa["industry"] != "other"
    ):
        return True
    if _jaccard(_blob(a)[:400], _blob(b)[:400]) >= 0.42:
        return True
    return False


def hook_opening_key(hook: Any) -> str:
    text = _norm(hook).replace("\r\n", "\n")
    first = re.split(r"\n+", text, maxsplit=1)[0]
    first = re.sub(r"[.!?].*$", "", first)
    return re.sub(r"\s+", " ", first.lower()).strip()[:80]


def hooks_structurally_similar(a: Any, b: Any) -> bool:
    ka, kb = hook_opening_key(a), hook_opening_key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    return _jaccard(ka, kb) >= 0.72 and abs(len(ka) - len(kb)) < 24


def evaluate_life_magnitude(package: dict[str, Any]) -> dict[str, Any]:
    """MAGNITUDE of life change — not field completeness."""
    end_txt = " ".join(
        [
            _norm(package.get("end_state")),
            _norm((package.get("start_end_contrast") or {}).get("end"))
            if isinstance(package.get("start_end_contrast"), dict)
            else "",
        ]
    )
    start_txt = " ".join(
        [
            _norm(package.get("starting_state")),
            _norm((package.get("start_end_contrast") or {}).get("start"))
            if isinstance(package.get("start_end_contrast"), dict)
            else "",
        ]
    )
    end_cash = max_end_money(package)
    start_cash = start_money(package)
    emp = parse_employees(end_txt)
    countries = parse_countries(end_txt)
    low_end = _low(end_txt)
    evidence: list[str] = []

    if end_cash >= 20_000_000:
        financial = 9.0
    elif end_cash >= 8_000_000:
        financial = 8.0
    elif end_cash >= 3_000_000:
        financial = 7.0
    elif end_cash >= 1_000_000:
        financial = 6.0
    elif end_cash >= 500_000:
        financial = 4.2
    elif end_cash >= 150_000:
        financial = 3.0
    elif end_cash > 0:
        financial = 2.2
    else:
        financial = 3.5 if any(x in low_end for x in ("imperio", "nacional", "internacional")) else 2.0
    evidence.append(f"end_money≈{int(end_cash)}" if end_cash else "end_money ausente")

    if start_cash > 0 and end_cash / max(start_cash, 1) >= 10_000:
        financial = min(10.0, financial + 1.0)
        evidence.append("delta financiero extremo")
    elif start_cash > 0 and end_cash / max(start_cash, 1) >= 1_000:
        financial = min(10.0, financial + 0.4)

    autonomy = 1.5
    if any(x in low_end for x in ("horario", "libertad", "20 horas", "controlas tu tiempo", "dejas el")):
        autonomy = 7.0
        evidence.append("delta de autonomía")
    if any(x in _low(start_txt) for x in ("mostrador", "recepción", "9 a 5", "tiempo parcial", "recepcion")):
        autonomy = min(10.0, autonomy + 1.5)

    status = 2.0
    if any(x in low_end for x in ("líder", "lider", "referente", "reconocid", "ceo", "dueño de una red")):
        status = 6.5
        evidence.append("delta de status")
    if countries >= 3 or emp >= 80:
        status = min(10.0, status + 2.0)
    elif emp >= 40 or countries >= 2:
        status = min(10.0, status + 1.0)

    environment = 2.0
    if any(x in low_end for x in ("casa", "departamento", "apartamento", "playa", "oficina", "vivienda")):
        environment = 6.0
        evidence.append("delta de entorno")
    if countries >= 2:
        environment = min(10.0, environment + 1.5)

    family = 1.0
    if any(x in low_end for x in ("padres", "hipoteca", "familia")):
        family = 7.0
        evidence.append("family impact")

    ownership = 2.0
    if any(x in low_end for x in ("posees", "dueño", "dueno", "equity", "controlas", "adquieres")):
        ownership = 7.0
        evidence.append("ownership")

    power = 2.0
    if emp >= 100:
        power = 8.0
    elif emp >= 40:
        power = 6.5
    elif emp >= 10:
        power = 4.0
    if countries >= 3:
        power = min(10.0, power + 1.5)
    if power >= 6:
        evidence.append(f"escala de responsabilidad emp={emp} países={countries}")

    strength = (
        financial * 0.34
        + autonomy * 0.12
        + status * 0.12
        + environment * 0.10
        + family * 0.08
        + ownership * 0.12
        + power * 0.12
    )
    # Absolute ceiling cap: small end states cannot reach 10
    if end_cash and end_cash < 1_000_000:
        strength = min(strength, 5.6)
        evidence.append("techo < $1M: magnitud limitada")
    elif end_cash and end_cash < 3_000_000 and countries < 2 and emp < 40:
        strength = min(strength, 7.2)
    strength = max(1, min(10, round(strength)))
    return {
        "life_transformation_strength": int(strength),
        "end_money": end_cash,
        "start_money": start_cash,
        "employees": emp,
        "countries": max(countries, 1),
        "evidence": evidence,
    }


def evaluate_story_quality(package: dict[str, Any]) -> dict[str, Any]:
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    hook = _norm(package.get("hook"))
    mech = _norm(engine.get("business_or_progress_mechanism"))
    opp = _norm(engine.get("specific_opportunity"))
    proof = _norm(engine.get("first_proof"))
    threat = _norm(engine.get("major_threat"))
    decision = _norm(engine.get("big_decision"))
    notice = _norm(engine.get("why_protagonist_notices_it"))
    action = _norm(engine.get("initial_action"))
    growth = _norm(engine.get("growth_mechanism"))
    price = bool(parse_money_values(mech + proof + _norm(engine.get("first_customer_or_break"))))
    numbered_proof = bool(re.search(r"\d", proof))

    distinct = 3.0
    if len(mech) >= 40:
        distinct += 1.5
    if price:
        distinct += 2.0
    if re.search(r"saas|suscrip|regal[ií]as|franquic|licenc|arbitraje|reventa|adquir", _low(mech)):
        distinct += 1.0
    if re.search(r"materiales locales|actividades de ecoturismo|servicios personalizados", _low(mech)):
        distinct -= 2.5
    if re.search(r"productos (sostenibles|biodegradables|ecol)", _low(mech)):
        distinct -= 3.0
    distinct = max(1, min(10, round(distinct + (1.5 if numbered_proof else 0))))

    scene = 2.0
    if re.search(r"\b(18:00|18h|noche|mañana|manana|turno|puerta|tel[eé]fono|mostrador|contrato|lavadora)\b", _low(hook + " " + notice)):
        scene += 3.5
    if re.search(r"\b(ves|escuchas|sostienes|suena|cierras|firmas|contestas)\b", _low(hook + " " + notice + " " + action)):
        scene += 2.0
    if len(hook) >= 160:
        scene += 1.0
    if re.search(r"turismo sostenible está en auge|creciente demanda", _low(opp)):
        scene -= 2.0
    scene = max(1, min(10, round(scene)))

    conflict = 3.0
    if len(threat) >= 40:
        conflict += 1.5
    if re.search(r"copia|regala gratis|incluye gratis|roll-?up|plataforma más grande|plataforma mas grande", _low(threat)):
        conflict += 3.0
    elif re.search(r"precios más bajos|precios mas bajos|mitad de precio|tarifas más bajas", _low(threat)):
        conflict += 1.0
    if re.search(r"^una cadena hotelera|^una gran marca|^grandes corporaciones|^la competencia", _low(threat)):
        conflict -= 1.5
    if len(decision) >= 30 and " o " in _low(decision):
        conflict += 1.0
    conflict = max(1, min(10, round(conflict)))

    causal = 3.0
    if numbered_proof and price:
        causal += 2.0
    if growth and mech and _jaccard(growth, mech) < 0.95:
        causal += 1.0
    ladder = ladder_event_texts(package.get("escalation_ladder"))
    if len(ladder) >= 6:
        causal += 1.0
    # Jump detector: tiny early money then huge end with few causal verbs
    early_money = parse_money_values(" ".join(ladder[:3]) + " " + proof)
    end_money = max_end_money(package)
    if early_money and end_money:
        early_max = max(early_money)
        if early_max > 0 and end_money / early_max >= 500 and len(ladder) < 7:
            causal -= 2.5
    if action and proof:
        causal += 1.0
    causal = max(1, min(10, round(causal)))

    return {
        "mechanism_distinctiveness": int(distinct),
        "sceneability": int(scene),
        "conflict_specificity": int(conflict),
        "causal_chain_strength": int(causal),
        "evidence": {
            "mechanism_distinctiveness": [mech[:90]],
            "sceneability": [notice[:90] or hook[:90]],
            "conflict_specificity": [threat[:90]],
            "causal_chain_strength": [proof[:90], f"ladder_n={len(ladder)}"],
        },
    }


def evaluate_progression_plausibility(package: dict[str, Any]) -> dict[str, Any]:
    """Aspirational fiction can be large; it cannot teleport."""
    ladder = ladder_event_texts(package.get("escalation_ladder"))
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    steps_money: list[float] = []
    for step in ladder:
        vals = parse_money_values(step)
        if vals:
            steps_money.append(max(vals))
    end_cash = max_end_money(package)
    if end_cash:
        steps_money.append(end_cash)
    score = 7.0
    reasons: list[str] = []
    for i in range(1, len(steps_money)):
        prev, cur = steps_money[i - 1], steps_money[i]
        if prev <= 0:
            continue
        ratio = cur / prev
        if ratio >= 400:
            score -= 3.0
            reasons.append(f"salto {prev:.0f}→{cur:.0f} (x{ratio:.0f})")
        elif ratio >= 80:
            score -= 1.5
            reasons.append(f"salto grande {prev:.0f}→{cur:.0f}")
    start = start_money(package)
    if start and end_cash and end_cash / max(start, 1) >= 2000 and len(ladder) < 6:
        score -= 2.0
        reasons.append("delta total enorme con ladder corta")
    # $10k/month vs $10M valuation with 3 countries and no path
    monthly = 0.0
    blob = _blob(package) + " " + " ".join(ladder)
    for m in _MONTHLY_RE.finditer(blob):
        vs = parse_money_values(m.group(0))
        if vs:
            monthly = max(monthly, max(vs))
    countries = parse_countries(package.get("end_state") or "")
    if monthly and monthly <= 15_000 and end_cash >= 5_000_000:
        score -= 2.5
        reasons.append("ingresos chicos vs valuación enorme")
    growth_blob = _low((engine.get("growth_mechanism") or "") + " " + (engine.get("escalation_path") or ""))
    if monthly and monthly <= 20_000 and countries >= 3 and not re.search(
        r"franquic|concesionario|plataforma|licenc|arr\b|mrr",
        growth_blob,
    ):
        score -= 1.5
        reasons.append("3 países sin motor de escala en el growth engine")
    score = max(1, min(10, round(score)))
    return {"progression_plausibility": int(score), "reasons": reasons or ["progresión causal aceptable"]}


def weak_end_ceiling(package: dict[str, Any]) -> bool:
    mag = evaluate_life_magnitude(package)
    scale = _low(package.get("scale_ceiling"))
    return bool(
        mag["end_money"] and mag["end_money"] < 1_000_000
        or (mag["end_money"] < 3_000_000 and mag["employees"] and mag["employees"] < 25 and mag["countries"] < 2)
        or scale in {"local", "regional"}
        or mag["life_transformation_strength"] <= 5
    )


def great_story_engine(package: dict[str, Any]) -> bool:
    q = evaluate_story_quality(package)
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    filled = sum(1 for k in STORY_ENGINE_KEYS if len(_norm(engine.get(k))) >= 28)
    return (
        q["sceneability"] >= 7
        and q["mechanism_distinctiveness"] >= 6
        and q["conflict_specificity"] >= 6
        and filled >= 12
    )


def needs_ceiling_repair(package: dict[str, Any]) -> bool:
    return great_story_engine(package) and weak_end_ceiling(package)


def infer_scale_from_package(package: dict[str, Any]) -> str:
    end = _low(package.get("end_state")) + " " + _low(
        (package.get("start_end_contrast") or {}).get("end") if isinstance(package.get("start_end_contrast"), dict) else ""
    )
    countries = parse_countries(package.get("end_state") or "")
    if countries >= 2 or any(x in end for x in ("internacional", "países", "paises", "countries")):
        return "international"
    if any(x in end for x in ("imperio", "franquicias", "120 local")):
        return "empire"
    if any(x in end for x in ("nacional", "todo el país", "todo el pais", "estados")):
        return "national"
    if any(x in end for x in ("exit", "adquisición", "adquisicion", "buyout")):
        return "major_exit"
    return _low(package.get("scale_ceiling") or "local") or "local"


def repair_scale_consistency(package: dict[str, Any]) -> dict[str, Any]:
    from src.documentary.formats.check_als.aspirational import SCALE_RANK, normalize_scale_ceiling

    declared = normalize_scale_ceiling(package.get("scale_ceiling"))
    inferred = normalize_scale_ceiling(infer_scale_from_package(package))
    if SCALE_RANK.get(inferred, 0) > SCALE_RANK.get(declared, 0):
        package["scale_ceiling"] = inferred
        package["scale_repaired"] = True
    else:
        package["scale_ceiling"] = declared
    return package


def title_claimed_money(title: str) -> float | None:
    t = _low(title)
    vals = parse_money_values(title)
    if vals:
        return max(vals)
    if re.search(r"millonari[oa]|millones|millón\b|millon\b", t):
        return 1_000_000.0
    return None


def title_is_truthful(package: dict[str, Any]) -> dict[str, Any]:
    title = _norm(package.get("title"))
    claimed = title_claimed_money(title)
    if claimed is None:
        return {"pass": True, "reason": ""}
    end = endgame_money(package)
    if claimed >= 1_000_000 and end and end < 1_000_000:
        return {"pass": False, "reason": f"título promete ≥$1M pero end≈{int(end)}"}
    if end and claimed > end * 3:
        return {"pass": False, "reason": f"título {claimed:.0f} vs end {end:.0f}"}
    if claimed >= 1_000_000 and end <= 0 and not re.search(r"millon|valuaci|patrimonio|\$", _low(package.get("end_state"))):
        return {"pass": False, "reason": "título millonario sin respaldo en end_state"}
    return {"pass": True, "reason": ""}


def needs_specific_physical_object(package: dict[str, Any]) -> bool:
    blob = _blob(package).lower()
    if any(g in blob for g in GENERIC_PHYSICAL_PRODUCTS):
        return True
    if any(x in blob for x in ("saas", "software", "plataforma", "app ", "recepcionista ia")):
        return False
    if any(x in blob for x in ("entrada", "concierto", "lavander", "hotel", "cabaña", "cabana")):
        return False
    return any(
        x in blob
        for x in (
            "productos",
            "fábrica",
            "fabrica",
            "biodegradable",
            "sostenible",
            "manufactur",
            "packaging",
            "envases",
        )
    )


def has_visualizable_object(package: dict[str, Any]) -> bool:
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    thumb = package.get("thumbnail_concept") if isinstance(package.get("thumbnail_concept"), dict) else {}
    blob = " ".join(
        [
            _norm(engine.get("business_or_progress_mechanism")),
            _norm(package.get("premise")),
            _norm(thumb.get("key_object")),
        ]
    ).lower()
    if any(g in blob for g in GENERIC_PHYSICAL_PRODUCTS) and not re.search(
        r"packaging|envase|botella|botellas|compostable|textil|jab[oó]n|detergente|panel|ladrillo|cápsula|capsula",
        blob,
    ):
        return False
    if re.search(
        r"packaging|envase|botella|compostable|textil|jab[oó]n|detergente|panel solar|"
        r"ladrillo|cápsula|capsula|cubierto|bolsa de|film |film\b|vaso |pallets?",
        blob,
    ):
        return True
    # If we required an object and only generic product language is present, fail
    return not needs_specific_physical_object(package)


def strip_ad_thumbnail_text(thumb: dict[str, Any] | None) -> dict[str, Any]:
    t = dict(thumb or {})
    text = _norm(t.get("text_if_any"))
    if not text:
        t["text_if_any"] = ""
        return t
    low = text.lower()
    if any(re.search(p, low) for p in AD_THUMB_TEXT):
        t["text_if_any"] = ""
        return t
    if "!" in text or len(text) > 28:
        t["text_if_any"] = ""
        return t
    # Keep only very short curiosity (price / number)
    if parse_money_values(text) or re.search(r"\d", text):
        t["text_if_any"] = text
        return t
    t["text_if_any"] = ""
    return t


def fill_thumbnail_gaps(package: dict[str, Any]) -> dict[str, Any]:
    thumb = package.get("thumbnail_concept") if isinstance(package.get("thumbnail_concept"), dict) else {}
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    ws = package.get("world_seeds") if isinstance(package.get("world_seeds"), dict) else {}
    core = package.get("story_core") if isinstance(package.get("story_core"), dict) else {}
    out = dict(thumb)
    placeholders = (
        "lugar de trabajo concreto",
        "urgencia contenida",
        "lugar concreto",
        "objeto simbólico",
        "un objeto simbólico",
        "young protagonist",
        "business environment",
        "prueba tangible",
    )

    def _usable(val: Any, min_len: int) -> bool:
        t = _norm(val)
        return len(t) >= min_len and _low(t) not in placeholders

    if not _usable(out.get("main_visual"), 24):
        out["main_visual"] = _norm(
            core.get("why_you_notice_it") or engine.get("specific_opportunity") or package.get("premise")
        )[:180]
    if not _usable(out.get("protagonist_state"), 8):
        out["protagonist_state"] = _norm(core.get("starting_situation") or engine.get("why_protagonist_notices_it"))[:120]
    if not _usable(out.get("environment"), 8):
        out["environment"] = _norm(
            ws.get("starting_location") or core.get("starting_situation") or ""
        )[:80]
    if not _usable(out.get("central_contrast"), 12):
        out["central_contrast"] = f"{_norm(package.get('starting_state'))[:60]} vs {_norm(package.get('end_state'))[:60]}"
    if not _usable(out.get("emotion"), 4):
        out["emotion"] = _norm(core.get("stakes") or engine.get("stakes") or "concentración en un instante irreversible")[:80]
    if not _usable(out.get("key_object"), 8):
        out["key_object"] = _norm(
            engine.get("first_proof") or core.get("first_proof") or engine.get("first_customer_or_break") or ""
        )[:80]
    if not _usable(out.get("composition"), 6):
        out["composition"] = "sujeto a la izquierda, consecuencia a la derecha"
    if not _usable(out.get("camera"), 4):
        out["camera"] = "plano medio amplio"
    if not _usable(out.get("lighting"), 4):
        out["lighting"] = "luz práctica del lugar"
    if not _usable(out.get("background"), 6):
        out["background"] = _norm(ws.get("starting_location") or core.get("starting_situation") or "")[:80]
    if len(_norm(out.get("thumbnail_prompt"))) < 40:
        out["thumbnail_prompt"] = (
            f"2D cinematic illustration: {_norm(out.get('main_visual'))[:120]}. "
            "Simple expressive protagonist, strong contrast, detailed environment, no busy text."
        )
    package["thumbnail_concept"] = strip_ad_thumbnail_text(out)
    return package


THUMBNAIL_REQUIRED = (
    "main_visual",
    "protagonist_state",
    "environment",
    "central_contrast",
    "emotion",
    "key_object",
)


def thumbnail_fields_complete(thumb: dict[str, Any] | None) -> dict[str, Any]:
    t = thumb if isinstance(thumb, dict) else {}
    missing = [k for k in THUMBNAIL_REQUIRED if len(_norm(t.get(k))) < (24 if k == "main_visual" else 8 if k != "central_contrast" else 12)]
    if len(_norm(t.get("emotion"))) < 4 and "emotion" not in missing:
        missing.append("emotion")
    return {"pass": not missing, "missing": missing}


def compute_penalties(package: dict[str, Any], *, duplicate: bool = False) -> dict[str, float]:
    q = evaluate_story_quality(package)
    plaus = evaluate_progression_plausibility(package)
    mag = evaluate_life_magnitude(package)
    thumb = package.get("thumbnail_concept") if isinstance(package.get("thumbnail_concept"), dict) else {}
    penalties = {
        "duplicate_penalty": 1.8 if duplicate else 0.0,
        "weak_mechanism_penalty": 0.7 if q["mechanism_distinctiveness"] <= 4 else (0.35 if q["mechanism_distinctiveness"] <= 5 else 0.0),
        "weak_ceiling_penalty": 0.9 if mag["life_transformation_strength"] <= 5 else (0.45 if mag["end_money"] and mag["end_money"] < 1_000_000 else 0.0),
        "progression_gap_penalty": 0.8 if plaus["progression_plausibility"] <= 4 else (0.4 if plaus["progression_plausibility"] <= 6 else 0.0),
        "generic_conflict_penalty": 0.45 if q["conflict_specificity"] <= 4 else 0.0,
        "incomplete_visual_penalty": 0.5 if not thumbnail_fields_complete(thumb)["pass"] else 0.0,
    }
    return penalties


def combine_overall(
    scores: dict[str, float],
    *,
    penalties: dict[str, float] | None = None,
) -> dict[str, float]:
    """Mix linear (texture) with geometric bottleneck of story × aspiration × progression."""
    story = _mean(
        [
            scores.get("story_engine_strength", 5),
            scores.get("mechanism_distinctiveness", 5),
            scores.get("causal_chain_strength", 5),
            scores.get("sceneability", 5),
            scores.get("conflict_specificity", 5),
            scores.get("filmability", 5),
        ]
    )
    aspiration = _mean(
        [
            scores.get("life_transformation", 5),
            scores.get("aspirational_strength", 5),
            scores.get("scale_potential", 5),
        ]
    )
    progression = _mean(
        [
            scores.get("progression_plausibility", 5),
            scores.get("causal_chain_strength", 5),
        ]
    )
    story = max(1.0, min(10.0, story))
    aspiration = max(1.0, min(10.0, aspiration))
    progression = max(1.0, min(10.0, progression))
    geo = (story * aspiration * progression) ** (1.0 / 3.0)
    floor = min(story, aspiration, progression)
    if floor < 5.5:
        geo *= max(0.55, floor / 5.5)

    from src.documentary.formats.check_als.editorial import WEIGHTS

    linear = 0.0
    wsum = 0.0
    for k, w in WEIGHTS.items():
        if k in scores:
            linear += float(scores[k]) * float(w)
            wsum += float(w)
    if wsum and abs(wsum - 1.0) > 0.02:
        linear = linear / wsum * 1.0

    mixed = 0.52 * geo + 0.48 * linear
    penalty_total = sum((penalties or {}).values())
    overall = max(1.0, min(10.0, mixed - penalty_total))
    return {
        "overall_score": round(overall, 2),
        "story_quality": round(story, 2),
        "aspiration_pillar": round(aspiration, 2),
        "progression_pillar": round(progression, 2),
        "geometric": round(geo, 2),
        "linear": round(linear, 2),
        "penalty_total": round(penalty_total, 2),
    }


def _mean(vals: list[float]) -> float:
    nums = [float(x) for x in vals if x is not None]
    return sum(nums) / max(1, len(nums))


def select_diverse_top(packages: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    """Hard skip clones. Do not put two skins of the same movie in Top N."""
    ranked = sorted(
        packages,
        key=lambda x: float(x.get("rank_score") or x.get("overall_score") or 0),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    for p in ranked:
        if any(is_same_movie(p, s) for s in selected):
            q = dict(p)
            q["diversity_skipped"] = True
            q["diversity_note"] = "misma película que un concepto ya seleccionado"
            continue
        if any(hooks_structurally_similar(p.get("hook"), s.get("hook")) for s in selected):
            q = dict(p)
            q["hook_duplicate"] = True
            q["rank_score"] = float(q.get("rank_score") or 0) - 0.35
            # still skip if openings are identical
            if hook_opening_key(p.get("hook")) and any(
                hook_opening_key(p.get("hook")) == hook_opening_key(s.get("hook")) for s in selected
            ):
                continue
            p = q
        selected.append(p)
        if len(selected) >= target:
            break
    return selected
