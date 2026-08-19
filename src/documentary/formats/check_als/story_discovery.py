"""Stage A — Story Discovery for Check (Fase 1.7).

Discover filmable stories before spending tokens on Concept Packaging.
Story quality is independent of titles, hooks, and thumbnails.
"""
from __future__ import annotations

import re
from typing import Any

from src.documentary.formats.check_als.editorial import FANTASY_DIVERSITY, STORY_ENGINE_KEYS, STORY_SHAPES
from src.documentary.formats.check_als.quality import (
    INDUSTRY_FAMILIES,
    MODEL_FAMILIES,
    START_FAMILIES,
    _family_from,
    _jaccard,
    _low,
    _norm,
)

STORY_CORE_KEYS = (
    "starting_situation",
    "specific_opportunity",
    "why_you_notice_it",
    "first_action",
    "first_proof",
    "core_mechanism",
    "causal_growth_path",
    "first_meaningful_reward",
    "life_transformation",
    "major_reversal",
    "big_decision",
    "stakes",
    "ending_direction",
)

STORY_SCORE_KEYS = (
    "would_watch",
    "causal_strength",
    "mechanism_strength",
    "progression_strength",
    "aspirational_strength",
    "conflict_strength",
    "distinctiveness",
)

STORY_SCORE_WEIGHTS = {
    "would_watch": 0.22,
    "causal_strength": 0.18,
    "mechanism_strength": 0.16,
    "progression_strength": 0.12,
    "aspirational_strength": 0.14,
    "conflict_strength": 0.10,
    "distinctiveness": 0.08,
}

CORE_TO_ENGINE = {
    "specific_opportunity": "specific_opportunity",
    "why_you_notice_it": "why_protagonist_notices_it",
    "first_action": "initial_action",
    "first_proof": "first_customer_or_break",
    "core_mechanism": "business_or_progress_mechanism",
    "causal_growth_path": "growth_mechanism",
    "first_meaningful_reward": "first_major_reward",
    "major_reversal": "major_threat",
    "big_decision": "big_decision",
    "stakes": "stakes",
    "ending_direction": "endgame",
}

VAGUE_ONLY = (
    "creces rápidamente",
    "creces rapidamente",
    "te vuelves exitoso",
    "te vuelves millonario",
    "te haces millonario",
    "expandes el negocio",
    "expandes internacionalmente",
    "enfrentas desafíos",
    "enfrentas desafios",
    "competidores aparecen",
    "aparecen competidores",
    "tu vida cambia",
    "el negocio crece",
    "escalas globalmente",
    "trabajas duro",
    "decisiones difíciles",
    "decisiones dificiles",
    "contratiempos inesperados",
    "desafíos inesperados",
    "desafios inesperados",
    "oportunidad única",
    "oportunidad unica",
    "cambias el mundo",
    "construyes un imperio",
    "te conviertes en líder",
    "te conviertes en lider",
)

GENERIC_OPPORTUNITY = (
    "hay demanda",
    "gran demanda",
    "creciente demanda",
    "falta atención personalizada",
    "falta atencion personalizada",
    "servicios personalizados",
    "atención personalizada",
    "atencion personalizada",
    "mejores experiencias",
    "experiencias más auténticas",
    "experiencias mas autenticas",
    "necesidad insatisfecha",
    "las personas quieren",
    "la gente quiere",
    "buscan alternativas",
    "quieren mejores",
)

GENERIC_INVENTION = (
    "dispositivo inteligente",
    "dispositivos inteligentes",
    "inteligencia artificial",
    "plataforma educativa",
    "plataforma en línea",
    "plataforma en linea",
    "cursos interactivos",
    "app que conecta",
    "aplicación que conecta",
    "aplicacion que conecta",
    "productos únicos",
    "productos unicos",
    "productos sostenibles",
    "personalizar el aprendizaje",
)

GENERIC_CONFLICT = (
    "aparece un competidor",
    "un competidor grande",
    "competidor más grande",
    "competidor mas grande",
    "competidor local",
    "una gran cadena",
    "cadena hotelera",
    "baja sus precios",
    "bajan sus precios",
    "precios más bajos",
    "precios mas bajos",
    "precio o calidad",
    "precios o mantener",
    "bajar tus precios",
    "bajar precios",
    "competir en precio",
    "lanza un servicio similar",
    "lanza una función similar",
    "lanza una funcion similar",
    "lanza un producto similar",
    "copia tu modelo",
    "copiar tu modelo",
    "copia tu idea",
)

SPECIFIC_CONFLICT_CUES = (
    "copia la función",
    "copia la funcion",
    "la incluye gratis",
    "la regala",
    "regala gratis",
    "te demanda",
    "te bloquea",
    "te echa",
    "te quita el",
    "el proveedor",
    "te ofrece comprarte",
    "oferta de compra",
    "se incendia",
    "se hace viral",
    "un cliente con",
    "el contrato de",
    "private equity",
    "incumbente",
    "18 sucursales",
    "después de las 18",
    "despues de las 18",
)

GENERIC_ENDING = (
    "te conviertes en referente",
    "te conviertes en un referente",
    "referente en",
    "consolidas tu marca",
    "consolidación de tu marca",
    "consolidacion de tu marca",
    "crecimiento sostenible",
    "sueños en realidad",
    "suenos en realidad",
    "líder indiscutido",
    "lider indiscutido",
    "referencia en la industria",
    "referencia nacional",
    "referencia del sector",
    "destino icónico",
    "destino iconico",
    "prosperar en un mercado",
)

GENERIC_ARC_BEATS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("trapped_job", ("atrapado", "sin futuro", "rutina", "mediocre", "largas horas", "desperdicia")),
    ("vague_opportunity", GENERIC_OPPORTUNITY),
    ("soft_proof", ("comentarios positivos", "reacción es sorprendente", "reaccion es sorprendente", "boca a boca")),
    ("smooth_growth", ("tu negocio crece", "abres un segundo", "franquicias en otras", "se expande")),
    ("swap_competitor", ("competidor grande", "gran cadena", "competidor local", "competidor más grande", "competidor mas grande")),
    ("price_vs_quality", ("precio o calidad", "bajar precios", "competir en precio", "precios más bajos", "precios mas bajos")),
    ("innovate_win", ("decides innovar", "experiencias únicas", "experiencias unicas", "mantener la calidad", "centarte en la calidad")),
    ("generic_ending", GENERIC_ENDING),
)

CAUSAL_CUES = (
    "entonces",
    "por eso",
    "porque",
    "eso hace",
    "eso cambia",
    "gracias a",
    "a partir de",
    "después de eso",
    "despues de eso",
    "ya no puedes",
    "te recomienda",
    "te recomiendan",
    "descubres que",
    "el mismo problema",
    "estandariz",
    "con eso",
    "habilita",
    "provoca",
    "eso te permite",
    "dejan de",
    "empieza a",
    "empiezan a",
    "contratas",
    "uno de esos",
    "ese cliente",
    "esa prueba",
    "con el dinero",
    "con esos",
    "con el tiempo",
    "después",
    "despues",
    "luego",
    "a medida que",
    "te permite",
    "abre la puerta",
    "otros ",
    "eso te",
)

LIFE_CUES = (
    "casa",
    "departamento",
    "apartamento",
    "padres",
    "familia",
    "horario",
    "tiempo",
    "libertad",
    "autonomía",
    "autonomia",
    "status",
    "reconocimiento",
    "mudas",
    "oficina",
    "viaj",
    "controlas",
    "dueño",
    "dueña",
    "entorno",
    "barrio",
    "habitación",
    "habitacion",
)

SCENE_CUES = (
    "años",
    "tarde",
    "mañana",
    "noche",
    "cierras",
    "teléfono",
    "telefono",
    "mostrador",
    "taller",
    "local",
    "cocina",
    "calle",
    "oficina",
    "puerta",
    "llaman",
    "suena",
    "ves ",
    "estás",
    "estas",
    "tienes",
)

GENERIC_FRANCHISE_LOCAL = (
    "franquicia",
    "franquic",
    "negocio local",
    "local quebrado",
    "compras el local",
    "lo compras",
)

_NUMBER_RE = re.compile(r"\d")
_SECOND_PERSON_RE = re.compile(
    r"\b(tú|tu|te|tienes|eres|estás|estas|trabajas|compras|construyes|descubres|notas|ves|"
    r"dejas|contratas|pagas|empiezas|vives|decides|logras|sientes|abres|cierras|notas|"
    r"dueño|dueña|tu lavander|tu taller|tu negocio)\b",
    re.I,
)
_WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9$]+")
_MONEY_BIG_RE = re.compile(
    r"\$\s*[\d][\d.,]*\s*(millones?|[mb]\b)|[\d][\d.,]*\s*millones",
    re.I,
)


def empty_story_core() -> dict[str, str]:
    return {k: "" for k in STORY_CORE_KEYS}


def empty_story_scores() -> dict[str, int]:
    return {k: 1 for k in STORY_SCORE_KEYS}


def _clamp(n: float) -> int:
    try:
        v = int(round(float(n)))
    except (TypeError, ValueError):
        v = 5
    return max(1, min(10, v))


def _as_text(value: Any) -> str:
    if isinstance(value, dict):
        for k in ("text", "description", "summary", "value"):
            if value.get(k):
                return _norm(value.get(k))
        return _norm(" ".join(str(v) for v in value.values() if v))
    if isinstance(value, list):
        return _norm(" ".join(_as_text(x) for x in value if x))
    return _norm(value)


def word_count(text: Any) -> int:
    return len(_WORD_RE.findall(_as_text(text)))


def normalize_story_core(raw: Any) -> dict[str, str]:
    src = raw if isinstance(raw, dict) else {}
    nested = src.get("story_core") if isinstance(src.get("story_core"), dict) else {}
    out = empty_story_core()
    for k in STORY_CORE_KEYS:
        out[k] = _as_text(src.get(k) or nested.get(k) or "")
    return out


def normalize_story_spine(raw: Any) -> str:
    if isinstance(raw, dict):
        return _as_text(raw.get("story_spine") or raw.get("spine") or raw.get("text") or "")
    return _as_text(raw)


def story_blob(core: dict[str, Any], spine: str = "") -> str:
    parts = [_as_text(core.get(k)) for k in STORY_CORE_KEYS]
    parts.append(_as_text(spine))
    return " ".join(p for p in parts if p)


def is_vague_only(text: str) -> bool:
    t = _low(text)
    if len(t) < 18:
        return True
    if any(p == t or t.startswith(p) and len(t) < len(p) + 18 for p in VAGUE_ONLY):
        return True
    hits = [p for p in VAGUE_ONLY if p in t]
    if hits and len(t) < 70 and not _NUMBER_RE.search(t):
        return True
    return False


def _step_count(text: str) -> int:
    bits = [b.strip() for b in re.split(r"[\n.;]|→|->", _as_text(text)) if len(b.strip()) > 12]
    return len(bits)


def _has_causal_language(text: str) -> bool:
    t = _low(text)
    return sum(1 for c in CAUSAL_CUES if c in t) >= 1


def _looks_like_teleport(text: str) -> bool:
    t = _low(text)
    if _MONEY_BIG_RE.search(t) and _step_count(t) < 4:
        return True
    if "expandes internacionalmente" in t and _step_count(t) < 5:
        return True
    if "el negocio crece" in t and "millones" in t and not _has_causal_language(t):
        return True
    return False


def normalize_story_shape(raw: Any) -> str:
    s = _low(raw).replace(" ", "_").replace("-", "_")
    aliases = {
        "zero_to_one": "zero_to_empire",
        "rollup": "roll_up",
        "roll-up": "roll_up",
        "viral": "viral_breakout",
        "invent": "invention",
        "underdog": "underdog_vs_incumbent",
        "boom_crisis": "boom_and_crisis",
        "comeback": "rise_fall_comeback",
        "race": "race_against_time",
        "bet": "high_risk_bet",
        "offer": "unexpected_offer",
        "shift": "market_shift",
        "creator": "creator_to_company",
    }
    if s in STORY_SHAPES:
        return s
    if s in aliases:
        return aliases[s]
    for name in STORY_SHAPES:
        if name in s or s in name:
            return name
    return ""


def classify_story_shape(core: dict[str, Any], spine: str = "", hinted: Any = "") -> str:
    hinted_n = normalize_story_shape(hinted)
    if hinted_n:
        return hinted_n
    blob = _low(story_blob(core, spine))
    cues = (
        ("roll_up", ("roll-up", "rollup", "segunda adquisición", "segunda adquisicion", "compras el segundo")),
        ("acquisition", ("compras ", "adquieres ", "por $1", "por 1 dólar")),
        ("viral_breakout", ("viral", "se vuelve viral", " explota en")),
        ("invention", ("construyes", "inventas", "prototipo", "patente")),
        ("underdog_vs_incumbent", ("incumbente", "copia la función", "copia la funcion", "la incluye gratis")),
        ("creator_to_company", ("canal", "audiencia", "creador", "suscriptores")),
        ("partnership", ("socio", "sociedad", "partner", "a medias")),
        ("unexpected_offer", ("te ofrecen comprar", "oferta de compra", "llegan con un cheque")),
        ("market_shift", ("cambia la ley", "la plataforma cambia", "el mercado se da vuelta")),
        ("boom_and_crisis", ("revienta", "quiebra el", "crisis", "se cae todo")),
        ("rise_fall_comeback", ("lo pierdes", "caes", "vuelves", "reconstruyes")),
        ("race_against_time", ("antes de que", "queda un mes", "deadline", "se vence")),
        ("high_risk_bet", ("apuestas todo", "hipotecas", "all-in", "te juegas")),
        ("turnaround", ("quiebra", "cerrada", "en crisis", "por $1")),
        ("accidental_opportunity", ("sin querer", "por accidente", "no buscabas")),
        ("zero_to_empire", ("desde cero", "imperio", "de la nada")),
    )
    for name, toks in cues:
        if any(t in blob for t in toks):
            return name
    return "turnaround"


def is_generic_opportunity(text: str) -> bool:
    t = _low(text)
    if not t:
        return True
    hits = [p for p in GENERIC_OPPORTUNITY if p in t]
    if not hits:
        return False
    concrete = _NUMBER_RE.search(t) or any(
        x in t for x in ("después de las", "despues de las", "llamadas", "por $", "$1", "18:00", "18h", "turno")
    )
    return not concrete


def looks_like_product_story(core: dict[str, Any], spine: str = "") -> bool:
    blob = _low(story_blob(core, spine))
    return any(
        x in blob
        for x in ("software", "app ", "aplicación", "aplicacion", "plataforma", "dispositivo", "prototipo", "saas", "producto")
    )


def is_generic_invention(core: dict[str, Any], spine: str = "") -> bool:
    if not looks_like_product_story(core, spine):
        return False
    blob = _low(story_blob(core, spine))
    generic_hits = [p for p in GENERIC_INVENTION if p in blob]
    if not generic_hits:
        return False
    concrete = any(
        x in blob
        for x in (
            "contesta",
            "agenda",
            "reserva",
            "cobra $",
            "$99",
            "después de las 18",
            "despues de las 18",
            "licencia",
            "catálogo",
            "catalogo",
        )
    )
    return not concrete


def is_interchangeable_conflict(core: dict[str, Any], spine: str = "") -> bool:
    """True if the reversal/decision could be pasted onto 20 other ideas."""
    blob = _low(
        " ".join(
            [
                _as_text(core.get("major_reversal")),
                _as_text(core.get("big_decision")),
                _as_text(spine),
            ]
        )
    )
    generic_hits = [p for p in GENERIC_CONFLICT if p in blob]
    if not generic_hits:
        return False
    if any(c in blob for c in SPECIFIC_CONFLICT_CUES):
        return False
    return True


def is_generic_ending(text: str) -> bool:
    t = _low(text)
    if not t:
        return True
    hits = [p for p in GENERIC_ENDING if p in t]
    if not hits:
        return False
    concrete = _NUMBER_RE.search(t) or any(
        x in t
        for x in (
            "vendes",
            "oferta",
            "juicio",
            "gratis",
            "te echan",
            "segundo local",
            "pivot",
            "pelear",
            "$",
        )
    )
    return not concrete


def generic_arc_beats(core: dict[str, Any], spine: str = "") -> list[str]:
    blob = _low(story_blob(core, spine))
    found: list[str] = []
    for name, cues in GENERIC_ARC_BEATS:
        if any(c in blob for c in cues):
            found.append(name)
    return found


def structural_template(core: dict[str, Any], spine: str = "") -> dict[str, Any]:
    beats = generic_arc_beats(core, spine)
    interchangeable = is_interchangeable_conflict(core, spine)
    return {
        "template": "generic_success_arc" if len(beats) >= 5 or (interchangeable and len(beats) >= 3) else "none",
        "beats": beats,
        "interchangeable_conflict": interchangeable,
        "generic_opportunity": is_generic_opportunity(_as_text(core.get("specific_opportunity"))),
        "generic_invention": is_generic_invention(core, spine),
        "generic_ending": is_generic_ending(_as_text(core.get("ending_direction")) + " " + _as_text(spine)[-280:]),
    }


def structural_similarity_report(stories: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    shape_counts: dict[str, int] = {}
    template_ids: list[str] = []
    for s in stories:
        core = normalize_story_core(s.get("story_core") or s)
        spine = normalize_story_spine(s.get("story_spine") or "")
        shape = classify_story_shape(core, spine, s.get("story_shape") or (s.get("seed") or {}).get("story_shape"))
        tmpl = structural_template(core, spine)
        sid = str(s.get("id") or "")
        rows.append({"id": sid, "story_shape": shape, **tmpl})
        shape_counts[shape] = int(shape_counts.get(shape) or 0) + 1
        if tmpl["template"] == "generic_success_arc":
            template_ids.append(sid)
    dominant = max(shape_counts.values()) if shape_counts else 0
    return {
        "shape_counts": shape_counts,
        "dominant_shape_count": dominant,
        "generic_success_arc_ids": template_ids,
        "generic_success_arc_share": round(len(template_ids) / max(1, len(stories)), 2),
        "rows": rows,
    }


def validate_story(core: dict[str, Any], spine: str = "") -> dict[str, Any]:
    """Hard editorial gates for a Check story. Reject hollow success arcs."""
    c = normalize_story_core(core)
    spine_text = normalize_story_spine(spine)
    reasons: list[str] = []

    required = {
        "starting_situation": 24,
        "specific_opportunity": 24,
        "first_action": 20,
        "first_proof": 18,
        "core_mechanism": 24,
        "causal_growth_path": 60,
        "life_transformation": 28,
        "major_reversal": 24,
        "big_decision": 20,
        "stakes": 18,
    }
    for key, min_len in required.items():
        val = c.get(key) or ""
        if len(val) < min_len:
            reasons.append(f"falta {key}")
        elif is_vague_only(val):
            reasons.append(f"{key} es vago")

    if not _NUMBER_RE.search(c.get("first_proof") or "") and len(c.get("first_proof") or "") < 40:
        reasons.append("first_proof sin prueba concreta")

    growth = c.get("causal_growth_path") or ""
    if is_vague_only(growth) or _looks_like_teleport(growth) or _looks_like_teleport(spine_text):
        reasons.append("teletransportación narrativa")
    elif _step_count(growth) < 3 and not _has_causal_language(growth + " " + spine_text):
        reasons.append("crecimiento sin causalidad")

    life = _low(c.get("life_transformation") or "") + " " + _low(spine_text)
    if not any(x in life for x in LIFE_CUES):
        reasons.append("transformación de vida ausente (solo negocio/números)")

    reversal = _low(c.get("major_reversal") or "")
    if any(p in reversal for p in ("competidores aparecen", "aparecen competidores", "desafíos", "desafios")) and len(reversal) < 80:
        reasons.append("reversal genérico")
    if is_generic_opportunity(c.get("specific_opportunity") or ""):
        reasons.append("oportunidad genérica")
    if is_generic_invention(c, spine_text):
        reasons.append("producto/software genérico")
    if is_interchangeable_conflict(c, spine_text):
        reasons.append("conflicto intercambiable")
    if is_generic_ending((c.get("ending_direction") or "") + " " + spine_text[-280:]):
        reasons.append("ending genérico")
    tmpl = structural_template(c, spine_text)
    if tmpl["template"] == "generic_success_arc":
        reasons.append("plantilla trabajo→competidor→precio/calidad")

    wc = word_count(spine_text)
    if wc < 110:
        reasons.append("story_spine demasiado corto")
    elif wc > 340:
        reasons.append("story_spine demasiado largo")
    if spine_text and not _SECOND_PERSON_RE.search(spine_text):
        reasons.append("story_spine no está en segunda persona")

    blob = _low(story_blob(c, spine_text))
    if "creces rápidamente" in blob and "millones" in blob and not _has_causal_language(blob):
        reasons.append("arco de éxito hueco")

    return {"pass": not reasons, "reasons": reasons, "word_count": wc}


def _score_would_watch(core: dict[str, str], spine: str) -> tuple[int, list[str]]:
    ev: list[str] = []
    n = 4
    blob = story_blob(core, spine)
    low = _low(blob)
    if any(c in low for c in SCENE_CUES):
        n += 2
        ev.append("escenas concretas")
    if _NUMBER_RE.search(core.get("first_proof") or ""):
        n += 1
        ev.append("primera prueba numerada")
    if len(core.get("major_reversal") or "") > 40 and not is_vague_only(core.get("major_reversal") or ""):
        n += 1
        ev.append("reversal específico")
    if any(x in _low(core.get("life_transformation") or "") for x in LIFE_CUES):
        n += 1
        ev.append("quieres vivir esa vida")
    if "vender" in _low(core.get("big_decision") or "") or "pelear" in _low(core.get("big_decision") or "") or " o " in _low(core.get("big_decision") or ""):
        n += 1
        ev.append("decisión con bifurcación")
    wc = word_count(spine)
    if 150 <= wc <= 250:
        n += 1
        ev.append("spine de película comprimida")
    if "saas" in low and "valuación" in low and not any(x in low for x in SCENE_CUES):
        n -= 2
        ev.append("suena a pitch, no a película")
    return _clamp(n), ev


def _score_causal(core: dict[str, str], spine: str) -> tuple[int, list[str]]:
    ev: list[str] = []
    growth = (core.get("causal_growth_path") or "") + " " + spine
    n = 3
    cues = sum(1 for c in CAUSAL_CUES if c in _low(growth))
    n += min(4, cues)
    if cues:
        ev.append(f"{cues} conectores causales")
    steps = _step_count(core.get("causal_growth_path") or "")
    if steps >= 6:
        n += 2
        ev.append(f"{steps} peldaños")
    elif steps >= 4:
        n += 1
    if _looks_like_teleport(growth):
        n -= 4
        ev.append("salto sin explicación")
    return _clamp(n), ev


def _score_mechanism(core: dict[str, str]) -> tuple[int, list[str]]:
    ev: list[str] = []
    mech = core.get("core_mechanism") or ""
    n = 3
    if len(mech) >= 40:
        n += 2
        ev.append("mecanismo descrito")
    if _NUMBER_RE.search(mech) or "$" in mech:
        n += 2
        ev.append("precio o métrica en el mecanismo")
    if any(x in _low(mech) for x in ("suscrip", "saas", "$99", "marketplace", "licenc", "roll-up", "rollup", "franquic")):
        n += 1
    if is_vague_only(mech) or _low(mech) in {"negocio", "startup", "app", "plataforma"}:
        n = 2
        ev.append("mecanismo abstracto")
    return _clamp(n), ev


def _score_progression(core: dict[str, str], spine: str) -> tuple[int, list[str]]:
    ev: list[str] = []
    blob = story_blob(core, spine)
    n = 3
    steps = max(_step_count(core.get("causal_growth_path") or ""), _step_count(spine))
    n += min(4, max(0, steps - 3))
    ev.append(f"{steps} niveles de progreso")
    start = _low(core.get("starting_situation") or "")
    ordinary = any(x in start for x in ("taller", "lavander", "restaurante", "hotel", "habitación", "habitacion", "padres", "food truck", "tienda", "mostrador", "turno"))
    ceiling = _low(core.get("ending_direction") or "") + " " + _low(spine)
    if ordinary:
        n += 1
        ev.append("comienzo ordinario")
        if any(x in start for x in ("mejor", "un poco")) and not any(x in ceiling for x in ("franquic", "nacional", "cadena", "incumbente", "roll")):
            n -= 3
            ev.append("techo = el mismo local un poco mejor")
    return _clamp(n), ev


def _score_aspirational(core: dict[str, str], spine: str) -> tuple[int, list[str]]:
    ev: list[str] = []
    blob = _low(story_blob(core, spine))
    n = 3
    hits = [c for c in LIFE_CUES if c in blob]
    n += min(4, len(hits))
    if hits:
        ev.append("vida: " + ", ".join(hits[:5]))
    money_only = ("mrr" in blob or "valuación" in blob or "valuation" in blob) and len(hits) < 2
    if money_only:
        n -= 2
        ev.append("fantasía casi solo financiera")
    reward = _low(core.get("first_meaningful_reward") or "")
    if any(x in reward for x in LIFE_CUES):
        n += 1
        ev.append("primera recompensa vivida")
    return _clamp(n), ev


def _score_conflict(core: dict[str, str]) -> tuple[int, list[str]]:
    ev: list[str] = []
    rev = core.get("major_reversal") or ""
    n = 3
    if len(rev) >= 40 and not is_vague_only(rev):
        n += 2
        ev.append("amenaza concreta")
    if is_interchangeable_conflict(core, ""):
        n = min(n, 3)
        ev.append("conflicto pegable en otras 20 ideas")
    elif any(x in _low(rev) for x in ("copia la función", "copia la funcion", "gratis", "incumbente", "private equity", "roll-up", "te quita", "regala")):
        n += 2
        ev.append("antagonista con movimiento específico")
    if is_vague_only(rev) or "competidores" in _low(rev) and len(rev) < 50:
        n = 2
        ev.append("conflicto genérico")
    if len(core.get("stakes") or "") >= 30:
        n += 1
    if " o " in _low(core.get("big_decision") or ""):
        n += 1
        ev.append("decisión real")
    return _clamp(n), ev


def _score_distinctiveness(core: dict[str, str], spine: str) -> tuple[int, list[str]]:
    ev: list[str] = []
    blob = _low(story_blob(core, spine))
    n = 6
    local_franchise = sum(1 for p in GENERIC_FRANCHISE_LOCAL if p in blob)
    tmpl = structural_template(core, spine)
    if tmpl["template"] == "generic_success_arc":
        n -= 4
        ev.append("plantilla de éxito genérica")
    if is_generic_opportunity(core.get("specific_opportunity") or ""):
        n -= 2
        ev.append("oportunidad intercambiable")
    if is_generic_invention(core, spine):
        n -= 2
        ev.append("producto que no se puede explicar")
    if is_generic_ending((core.get("ending_direction") or "") + " " + _low(spine)[-200:]):
        n -= 2
        ev.append("ending de referente/marca")
    if local_franchise >= 3 and "roll-up" not in blob and "sistema operativo" not in blob:
        n -= 3
        ev.append("piel de negocio local → franquicia")
    if _NUMBER_RE.search(core.get("first_proof") or "") and len(core.get("core_mechanism") or "") > 40:
        n += 1
        ev.append("detalle difícil de clonar")
    if any(x in blob for x in ("software", "licenc", "marketplace", "logíst", "logistic", "media", "club", "manufact")):
        n += 1
    if "productos sostenibles" in blob or "revolucion" in blob:
        n -= 2
        ev.append("idea genérica")
    return _clamp(n), ev


def score_story(core: dict[str, Any], spine: str = "") -> dict[str, Any]:
    """Code-owned film quality. Packaging cannot change these numbers."""
    c = normalize_story_core(core)
    s = normalize_story_spine(spine)
    subs: dict[str, int] = {}
    evidence: dict[str, list[str]] = {}
    fns = {
        "would_watch": lambda: _score_would_watch(c, s),
        "causal_strength": lambda: _score_causal(c, s),
        "mechanism_strength": lambda: _score_mechanism(c),
        "progression_strength": lambda: _score_progression(c, s),
        "aspirational_strength": lambda: _score_aspirational(c, s),
        "conflict_strength": lambda: _score_conflict(c),
        "distinctiveness": lambda: _score_distinctiveness(c, s),
    }
    for key, fn in fns.items():
        val, ev = fn()
        subs[key] = val
        evidence[key] = ev
    overall = sum(subs[k] * STORY_SCORE_WEIGHTS[k] for k in STORY_SCORE_KEYS)
    return {
        "story_score": round(float(overall), 2),
        "story_scores": subs,
        "story_score_evidence": evidence,
    }


def story_core_to_engine(core: dict[str, Any]) -> dict[str, str]:
    c = normalize_story_core(core)
    engine = {k: "" for k in STORY_ENGINE_KEYS}
    for src, dest in CORE_TO_ENGINE.items():
        engine[dest] = c.get(src) or ""
    engine["first_proof"] = c.get("first_proof") or ""
    engine["why_it_works"] = c.get("core_mechanism") or ""
    engine["escalation_path"] = c.get("causal_growth_path") or ""
    engine["possible_cost"] = c.get("stakes") or ""
    engine["primary_opposition"] = c.get("major_reversal") or ""
    engine["mid_story_complication"] = c.get("major_reversal") or ""
    return engine


def story_fingerprint(item: dict[str, Any]) -> dict[str, str]:
    core = normalize_story_core(item.get("story_core") or item)
    spine = normalize_story_spine(item.get("story_spine") or "")
    blob = story_blob(core, spine)
    if item.get("premise") or item.get("story_engine"):
        engine = item.get("story_engine") if isinstance(item.get("story_engine"), dict) else {}
        blob = " ".join(
            [
                blob,
                _norm(item.get("premise")),
                _norm(item.get("starting_state")),
                _norm(engine.get("business_or_progress_mechanism")),
                _norm(engine.get("growth_mechanism")),
            ]
        )
    fantasy = "other"
    low = _low(blob)
    for ft in FANTASY_DIVERSITY:
        token = ft.replace("_", " ")
        if token in low or ft in low:
            fantasy = ft
            break
    reversal = _low(core.get("major_reversal") or item.get("ending_direction") or "")[:80]
    ending = _low(core.get("ending_direction") or item.get("ending_direction") or "")[:80]
    return {
        "industry": _family_from(blob, INDUSTRY_FAMILIES),
        "starting_situation": _family_from(blob, START_FAMILIES) or _family_from(core.get("starting_situation") or "", START_FAMILIES),
        "core_mechanism": _low(core.get("core_mechanism") or "")[:80],
        "growth_mechanism": _low(core.get("causal_growth_path") or "")[:80],
        "business_model": _family_from(blob, MODEL_FAMILIES),
        "fantasy": fantasy,
        "major_reversal": reversal,
        "ending_direction": ending,
    }


def _restaurant_franchise(fp: dict[str, str], blob: str) -> bool:
    food = fp.get("industry") in {"food_service", "food_delivery"} or any(
        x in blob for x in ("restaurante", "gourmet", "cafeter", "cocina")
    )
    franchise = fp.get("business_model") == "franchise" or "franquic" in blob
    return food and franchise


def is_same_story(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Same film, different skin — keyword families + semantic overlap."""
    fa, fb = story_fingerprint(a), story_fingerprint(b)
    blob_a = _low(story_blob(normalize_story_core(a.get("story_core") or a), normalize_story_spine(a.get("story_spine") or a.get("premise") or "")))
    blob_b = _low(story_blob(normalize_story_core(b.get("story_core") or b), normalize_story_spine(b.get("story_spine") or b.get("premise") or "")))

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
    if _restaurant_franchise(fa, blob_a) and _restaurant_franchise(fb, blob_b):
        return True

    matched = 0
    for k in ("industry", "starting_situation", "business_model", "fantasy", "ending_direction"):
        if fa.get(k) and fa.get(k) == fb.get(k) and fa.get(k) not in {"", "other"}:
            matched += 1
    if matched >= 3 and _jaccard(fa["core_mechanism"], fb["core_mechanism"]) >= 0.28:
        return True
    if _jaccard(fa["core_mechanism"], fb["core_mechanism"]) >= 0.55:
        return True
    if _jaccard(fa["growth_mechanism"], fb["growth_mechanism"]) >= 0.50 and fa["industry"] == fb["industry"] and fa["industry"] != "other":
        return True
    if _jaccard(blob_a[:500], blob_b[:500]) >= 0.42:
        return True
    if fa["major_reversal"] and fa["major_reversal"] == fb["major_reversal"] and fa["industry"] == fb["industry"] and fa["industry"] != "other":
        return True
    return False


def select_diverse_stories(stories: list[dict[str, Any]], target: int) -> tuple[list[dict[str, Any]], int]:
    ranked = sorted(
        stories,
        key=lambda x: float(x.get("story_score") or 0),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    skipped = 0
    for row in ranked:
        if any(is_same_story(row, s) for s in selected):
            skipped += 1
            continue
        selected.append(row)
        if len(selected) >= target:
            break
    return selected, skipped


def packaging_score(package: dict[str, Any]) -> dict[str, Any]:
    """Measure how the film is sold. Never used to bury a great story."""
    from src.documentary.formats.check_als.aspirational import title_looks_like_blog
    from src.documentary.formats.check_als.quality import title_is_truthful
    from src.documentary.formats.check_als.validators import (
        validate_hook,
        validate_thumbnail,
        validate_titles,
    )

    hook = validate_hook(package.get("hook"))
    titles = validate_titles(str(package.get("title") or ""), list(package.get("title_options") or []))
    thumb = validate_thumbnail(
        package.get("thumbnail_concept") if isinstance(package.get("thumbnail_concept"), dict) else {}
    )
    title_text = str(package.get("title") or "")
    title_n = 8 if titles.get("pass") else 3
    if title_looks_like_blog(title_text):
        title_n = 2
    if not title_is_truthful(package):
        title_n = min(title_n, 4)
    hook_n = 8 if hook.get("pass") else 3
    if hook.get("repaired"):
        hook_n = max(hook_n, 6)
    thumb_n = 8 if thumb.get("pass") else 3
    core = normalize_story_core(package.get("story_core") or {})
    promise = 7
    low_title = _low(title_text)
    if core.get("starting_situation") and not any(
        tok in low_title for tok in _low(core.get("starting_situation")).split()[:6] if len(tok) > 4
    ):
        # Title may still be good if it names the mechanism
        if core.get("core_mechanism") and any(
            tok in low_title for tok in _low(core.get("core_mechanism")).split() if len(tok) > 5
        ):
            promise = 8
    if "millonario" in low_title and "500" in _low(package.get("end_state") or ""):
        promise = 2
    subs = {
        "title": _clamp(title_n),
        "hook": _clamp(hook_n),
        "thumbnail": _clamp(thumb_n),
        "promise_coherence": _clamp(promise),
    }
    overall = sum(subs.values()) / 4.0
    return {"packaging_score": round(overall, 2), "packaging_scores": subs}


def hook_needs_regen(hook: Any) -> bool:
    from src.documentary.formats.check_als.validators import validate_hook

    return not validate_hook(hook).get("pass")


def synthesize_hook_from_core(core: dict[str, Any], world_seeds: dict[str, Any] | None = None) -> str:
    c = normalize_story_core(core)
    ws = world_seeds if isinstance(world_seeds, dict) else {}
    parts: list[str] = []
    start = c.get("starting_situation") or ""
    if start:
        parts.append(start if start.endswith((".", "!", "?")) else start + ".")
    notice = c.get("why_you_notice_it") or ""
    if notice and _low(notice) not in _low(" ".join(parts)):
        parts.append(notice if notice.endswith((".", "!", "?")) else notice + ".")
    proof = c.get("first_proof") or ""
    if proof:
        line = proof if proof.endswith((".", "!", "?")) else proof + "."
        if not line.lower().startswith("mañana"):
            parts.append("Mañana eso deja de ser un detalle: " + line)
        else:
            parts.append(line)
    if not parts:
        age = ws.get("starting_age")
        loc = _norm(ws.get("starting_location") or "")
        if age:
            parts.append(f"Tienes {age} años{(' y estás en ' + loc) if loc else '.'}")
        parts.append(_as_text(c.get("first_action") or "Das el primer paso concreto."))
    return "\n\n".join(parts).strip()


def mechanic_story_fixture() -> dict[str, Any]:
    """Positive editorial fixture — quality DNA, not a business template."""
    core = {
        "starting_situation": (
            "Tienes 20 años y contestas el teléfono en la recepción de un taller mecánico "
            "mientras vives en la habitación de tus padres."
        ),
        "specific_opportunity": (
            "Después de las 18:00 las llamadas del taller quedan sin contestar y esos clientes "
            "reservan el trabajo en otro lado."
        ),
        "why_you_notice_it": (
            "Son las seis de la tarde, ves al dueño cerrar la persiana y el teléfono sigue sonando. "
            "Nadie lo atiende."
        ),
        "first_action": (
            "En un fin de semana construyes una recepcionista de IA tosca que contesta, toma el dato "
            "del auto y agenda el turno."
        ),
        "first_proof": (
            "El dueño acepta pagarte $99 al mes si agenda trabajos reales. El primer mes agenda 43 trabajos."
        ),
        "core_mechanism": (
            "Software de suscripción para reservas fuera de horario: $99 es más barato que perder "
            "un solo trabajo de frenos."
        ),
        "causal_growth_path": (
            "Esos 43 trabajos hacen que el dueño te recomiende a tres talleres amigos. Descubres que "
            "los cuatro pierden llamadas después del cierre. Estandarizas lo que construiste y empiezas "
            "a cobrar la misma suscripción. Los dueños te mencionan en asociaciones del sector. Ya no "
            "puedes atender el soporte solo y contratas a tu primera persona. Uno de esos clientes "
            "pertenece a un grupo con 18 sucursales; el tamaño de los contratos cambia. Escalas a "
            "grupos de concesionarios y a operación nacional."
        ),
        "first_meaningful_reward": (
            "Dejas el mostrador, alquilas tu primer departamento y empiezas a controlar tu horario."
        ),
        "life_transformation": (
            "Pasas de contestador anónimo en casa de tus padres a dueño de un producto que talleres "
            "de varios estados necesitan. Pagas la hipoteca de tus padres. Tu entorno, tu tiempo y "
            "quién te conoce cambian."
        ),
        "major_reversal": (
            "La plataforma más grande de gestión de talleres copia la función de recepción y la incluye gratis."
        ),
        "big_decision": "Vender al incumbente, pivotar a una capa especializada, o pelear como producto propio.",
        "stakes": (
            "Puedes perder el producto, a los talleres independientes que dependen de ti, y años de "
            "trabajo absorbidos en la página de un competidor."
        ),
        "ending_direction": (
            "Quedas como capa especializada nacional o aceptas una compra en malas condiciones."
        ),
    }
    spine = (
        "Tienes 20 años y contestas el teléfono en un taller mecánico. Vives en la habitación de tus "
        "padres y cierras el local cuando el dueño baja la persiana. A las seis de la tarde el teléfono "
        "sigue sonando. Nadie responde. Al día siguiente descubres que esa llamada era un trabajo de "
        "casi mil dólares que se fue a otro taller. Construyes en un fin de semana una recepcionista "
        "de IA tosca. El dueño paga $99 al mes si agenda turnos de verdad. El primer mes agenda 43 "
        "trabajos. Te recomienda a tres talleres amigos. Los cuatro tienen exactamente el mismo agujero "
        "después del cierre. Estandarizas el sistema y cobras suscripción. Las asociaciones del sector "
        "empiezan a pasarte cuentas. Ya no das abasto y contratas a tu primera persona. Un cliente "
        "pertenece a un grupo con 18 sucursales: el tamaño de los contratos cambia. Dejas el mostrador, "
        "alquilas departamento y pagas la hipoteca de tus padres. Entonces la plataforma dominante "
        "copia la función y la regala gratis. Tienes que decidir si vendes, pivotas o peleas. El final "
        "no es un número: es si todavía controlas lo que construiste."
    )
    scored = score_story(core, spine)
    return {
        "id": "mechanic-ai-receptionist",
        "story_core": normalize_story_core(core),
        "story_spine": spine,
        "story_eligible": True,
        "story_shape": "underdog_vs_incumbent",
        **scored,
    }


def taller_renovado_negative_fixture() -> dict[str, Any]:
    """Regression negative: interchangeable generic-success arc. Workshop start is not the problem."""
    core = {
        "starting_situation": (
            "Eres el dueño de un taller mecánico familiar que ha estado en la misma ubicación "
            "durante décadas, pero las ventas han caído drásticamente."
        ),
        "specific_opportunity": (
            "Observas que muchos de tus clientes se quejan de la falta de servicios personalizados "
            "en el sector automotriz."
        ),
        "why_you_notice_it": "Te das cuenta de que la mayoría de los talleres están más enfocados en las ganancias rápidas.",
        "first_action": "Decides implementar un servicio de atención al cliente excepcional.",
        "first_proof": "Después de unos meses recibes comentarios positivos y vuelven más clientes.",
        "core_mechanism": "Atención personalizada y un sistema de seguimiento y fidelización.",
        "causal_growth_path": (
            "Los comentarios positivos aumentan. Creas un sistema de fidelización. Con el tiempo "
            "abres sucursales en otras ciudades. Duplicas ingresos."
        ),
        "first_meaningful_reward": "Te sientes admirado por tu comunidad.",
        "life_transformation": "Pasas de dueño en crisis a referente local con varias sucursales.",
        "major_reversal": "Un competidor local decide copiar tu modelo y ofrece precios más bajos.",
        "big_decision": "Debes decidir si bajar tus precios o mantener la calidad de tu servicio.",
        "stakes": "Puedes perder clientes y el taller familiar.",
        "ending_direction": "Consolidación de tu marca y un crecimiento sostenible.",
    }
    spine = (
        "Eres el dueño de un taller mecánico familiar que ha estado en la misma ubicación durante "
        "décadas, pero las ventas han caído drásticamente. Observas que muchos de tus clientes se "
        "quejan de la falta de servicios personalizados en el sector automotriz. Te das cuenta de "
        "que la mayoría de los talleres están más enfocados en las ganancias rápidas. Decides "
        "implementar un servicio de atención al cliente excepcional, ofreciendo una experiencia "
        "única a cada cliente. Después de unos meses, comienzas a recibir comentarios positivos, "
        "lo que aumenta el número de clientes que regresan. Creas un sistema de seguimiento y "
        "fidelización que permite a tus clientes programar mantenciones. Con el tiempo, esto lleva "
        "a abrir nuevas sucursales en otras ciudades. Logras duplicar tus ingresos y te sientes "
        "admirado por tu comunidad. Sin embargo, un competidor local decide copiar tu modelo y "
        "ofrece precios más bajos. Debes decidir si bajar tus precios o mantener la calidad de tu "
        "servicio. Te decides por la calidad y la lealtad de tus clientes, lo que resulta en una "
        "consolidación de tu marca y un crecimiento sostenible."
    )
    return {
        "id": "taller_renovado",
        "story_core": normalize_story_core(core),
        "story_spine": spine,
        "story_shape": "turnaround",
    }


def vague_success_story() -> dict[str, Any]:
    core = {
        "starting_situation": "Tienes una idea de negocio.",
        "specific_opportunity": "Hay una oportunidad en el mercado.",
        "why_you_notice_it": "Quieres ser exitoso.",
        "first_action": "Empiezas una empresa.",
        "first_proof": "Consigues tu primer cliente.",
        "core_mechanism": "El negocio crece.",
        "causal_growth_path": (
            "Consigues tu primer cliente. El negocio crece. Expandes internacionalmente. "
            "Tu empresa vale $20 millones."
        ),
        "first_meaningful_reward": "Te vuelves exitoso.",
        "life_transformation": "Tu vida cambia y te haces millonario.",
        "major_reversal": "Competidores aparecen.",
        "big_decision": "Enfrentas desafíos y tomas decisiones difíciles.",
        "stakes": "Todo.",
        "ending_direction": "Construyes un imperio.",
    }
    spine = (
        "Empiezas una empresa. Consigues tu primer cliente. El negocio crece. Expandes "
        "internacionalmente. Te vuelves exitoso. Tu empresa vale veinte millones de dólares. "
        "Competidores aparecen. Enfrentas desafíos. Tu vida cambia. Te haces millonario."
    )
    return {"id": "vague-success", "story_core": normalize_story_core(core), "story_spine": spine}
