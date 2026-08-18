"""Deterministic validators for Check Concept Engine V2."""
from __future__ import annotations

import ast
import json
import re
from typing import Any

from src.documentary.formats.check_als.editorial import (
    BANNED_HOOK_OPENERS,
    BANNED_TITLE_PATTERNS,
    CATEGORY_CUES,
    CATEGORY_MISMATCH,
    CLICHE_PHRASES,
    DEFAULT_CATEGORIES,
    MECHANISM_FIELD_MAP,
    MECHANISM_REQUIRED,
    MIN_OPEN_LOOPS,
    MAX_OPEN_LOOPS,
    SPECIFICITY_THRESHOLD,
    STORY_ENGINE_KEYS,
    THUMBNAIL_PLACEHOLDERS,
    VAGUE_PHRASES,
)

_MONEY_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s*(?:k|m|b|million|billion|millones?))?"
    r"|\b\d[\d.]*(?:\s*(?:dólares|dolares|euros|pesos|usd))\b",
    re.I,
)
_NUMBER_PROOF_RE = re.compile(
    r"\b\d{1,3}(?:,\d{3}|\.\d{3})*\b|"
    r"\b\d+\s*(?:trabajos|llamadas|clientes|talleres|tiendas|locales|habitaciones|"
    r"usuarios|meses|semanas|años|anos|%|por\s*ciento|jobs|calls|customers|shops|"
    r"stores|rooms|users|months|weeks|years|percent)\b",
    re.I,
)
_BAD_TITLE_RES = [re.compile(p, re.I) for p in BANNED_TITLE_PATTERNS]

_SECOND_PERSON_ES_RE = re.compile(
    r"\b("
    r"tú|tu|te|tuyo|tuya|tuyos|tuyas|"
    r"tienes|eres|estás|estas|haces|ves|miras|trabajas|vives|descubres|decides|"
    r"compras|vendes|construyes|creas|lanzas|notas|recibes|firmas|arriesgas|"
    r"pierdes|ganas|abres|cierras|contesto|contestas"
    r")\b",
    re.I,
)

_INDUSTRY_RE = re.compile(
    r"\b("
    r"saas|software|app|aplicación|aplicacion|marketplace|franquicia|franchise|"
    r"bienes\s+ra[ií]ces|real estate|motel|hotel|restaurante|restaurant|"
    r"taller|mecánico|mecanico|concesionario|dealership|logística|logistica|"
    r"almacén|almacen|warehouse|fábrica|fabrica|factory|granja|farm|"
    r"licencia|licensing|medios|media|creador|creator|retail|tienda|"
    r"lavandería|lavanderia|laundromat|lavadero|autolavado|car\s?wash|"
    r"gimnasio|gym|dojo|clínica|clinica|construcción|construccion|"
    r"camiones|trucking|suscripción|suscripcion|subscription|"
    r"cine|karaoke|estadio|stadium|floristería|floristeria"
    r")\b",
    re.I,
)

_CUSTOMER_RE = re.compile(
    r"\b("
    r"cliente|clientes|customer|shop|tienda|restaurante|dueño|dueno|owner|"
    r"concesionario|equipo|fans|aficionados|suscriptores|inquilinos|"
    r"pacientes|conductores|creadores|locales|tiendas"
    r")\b",
    re.I,
)

_SITUATION_RE = re.compile(
    r"\b("
    r"teléfono|telefono|phone|taller|shop|escritorio|desk|puerta|door|"
    r"correo|email|cliente|customer|alquiler|rent|dueño|dueno|owner|"
    r"turno|shift|llamada|call|factura|invoice|contrato|lease|"
    r"cuenta|dólares|dolares|máquina|maquina|mostrador|"
    r"local|locales|bar|café|cafe|plaza|vivero|floristería|floristeria|"
    r"gimnasio|app|reunión|reunion|amigos|noche|mañana|manana|"
    r"lavadora|asiento|palco|estadio|camión|camion|cocina|mostrador|"
    r"caja|efectivo|dólar|dolar|mes|semana|año|ano"
    r")\b",
    re.I,
)

_LOCATION_RE = re.compile(
    r"\b("
    r"habitación|habitacion|bedroom|taller|shop|oficina|office|"
    r"almacén|almacen|warehouse|estadio|stadium|motel|hotel|fábrica|fabrica|"
    r"granja|farm|clínica|clinica|sala\s+de\s+juntas|boardroom|"
    r"tribunal|court|departamento|apartment|hq|aeropuerto|airport|"
    r"cocina|kitchen|concesionario|dealership|estudio|studio|"
    r"gimnasio|gym|dojo|calle|street|garage|cine|bar|tienda"
    r")\b",
    re.I,
)


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _low(text: Any) -> str:
    return _norm(text).lower()


def is_vague_text(text: Any, *, min_len: int = 28) -> bool:
    """True if text is empty, too short, or only vague/cliché content."""
    t = _norm(text)
    if len(t) < min_len:
        return True
    low = t.lower()
    # Entire field is essentially a vague phrase
    for phrase in VAGUE_PHRASES:
        if low == phrase or low == f"the {phrase}" or low == f"some {phrase}":
            return True
    # Mostly vague: short and contains vague without concrete anchors
    has_money = bool(_MONEY_RE.search(t))
    has_number = bool(_NUMBER_PROOF_RE.search(t))
    has_named_noun = bool(_INDUSTRY_RE.search(t))
    vague_hits = sum(1 for p in VAGUE_PHRASES if p in low and len(p) > 8)
    if vague_hits >= 2 and not (has_money or has_number or has_named_noun):
        return True
    if re.search(r"trabajar duro y eventualmente|work hard and eventually", low):
        return True
    if re.search(r"revolucionari[oa]\s+(ia|app|empresa|tecnolog[ií]a)|revolutionary\s+(ai|app|company)", low) and not has_named_noun:
        return True
    if re.search(r"perderlo todo.*reconstru|reconstru.*imperio|losing everything.*rebuild|rebuild.*empire", low) and len(t) < 120:
        return True
    return False


def is_concrete_field(text: Any, *, min_len: int = 32) -> bool:
    return not is_vague_text(text, min_len=min_len)


class ConcreteMechanismValidator:
    """Reject packages without concrete opportunity/mechanism/action/growth/threat/stakes."""

    REQUIRED = MECHANISM_REQUIRED

    @classmethod
    def evaluate(cls, package: dict[str, Any]) -> dict[str, Any]:
        engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
        details: dict[str, Any] = {}
        missing: list[str] = []
        vague: list[str] = []
        for logical in cls.REQUIRED:
            field = MECHANISM_FIELD_MAP[logical]
            value = engine.get(field) or package.get(field) or ""
            ok = is_concrete_field(value)
            details[logical] = {"field": field, "value": _norm(value)[:200], "concrete": ok}
            if not _norm(value):
                missing.append(logical)
            elif not ok:
                vague.append(logical)
        passed = not missing and not vague
        return {
            "pass": passed,
            "missing": missing,
            "vague": vague,
            "details": details,
            "has_specific_opportunity": "opportunity" not in missing and "opportunity" not in vague,
            "has_specific_mechanism": "mechanism" not in missing and "mechanism" not in vague,
            "has_growth_engine": "growth_engine" not in missing and "growth_engine" not in vague,
            "has_major_threat": "major_threat" not in missing and "major_threat" not in vague,
            "has_stakes": "stakes" not in missing and "stakes" not in vague,
            "has_first_action": "first_action" not in missing and "first_action" not in vague,
        }


def extract_specificity_signals(package: dict[str, Any]) -> dict[str, Any]:
    """Count concrete narrative signals — not an LLM self-score."""
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    blob = " ".join(
        [
            str(package.get("premise") or ""),
            str(package.get("hook") or ""),
            str(package.get("one_line_fantasy") or ""),
            *[str(engine.get(k) or "") for k in STORY_ENGINE_KEYS],
        ]
    )
    low = blob.lower()
    evidence: list[str] = []
    signals: dict[str, bool] = {}

    def mark(name: str, ok: bool, label: str) -> None:
        signals[name] = ok
        if ok:
            evidence.append(label)

    industry = bool(_INDUSTRY_RE.search(blob))
    mark("named_industry_or_model", industry, "industria/modelo de negocio nombrado")

    customer = bool(_CUSTOMER_RE.search(low)) and is_concrete_field(
        engine.get("first_customer_or_break") or "", min_len=20
    )
    mark(
        "concrete_customer",
        customer,
        f"cliente/ruptura concreta: {_norm(engine.get('first_customer_or_break'))[:80]}",
    )

    problem = is_concrete_field(engine.get("specific_opportunity") or package.get("premise"), min_len=40)
    mark("concrete_problem", problem, "problema/oportunidad concreta")

    transaction = bool(_MONEY_RE.search(blob)) or bool(
        re.search(r"\b\d+\s*/\s*mes|al mes|per month|depósito|deposito|cuota|fee|nómina|nomina\b", low)
    )
    mark("concrete_transaction", transaction, "transacción/precio concreto")

    growth = is_concrete_field(engine.get("growth_mechanism"), min_len=28)
    mark("concrete_growth", growth, "mecanismo de crecimiento concreto")

    threat = is_concrete_field(engine.get("major_threat"), min_len=28)
    mark("concrete_threat", threat, "competidor/amenaza concreta")

    proof = bool(_NUMBER_PROOF_RE.search(str(engine.get("first_proof") or ""))) or is_concrete_field(
        engine.get("first_proof"), min_len=24
    )
    mark("measurable_first_proof", proof, f"primera prueba: {_norm(engine.get('first_proof'))[:80]}")

    reward = is_concrete_field(engine.get("first_major_reward"), min_len=20)
    mark("tangible_reward", reward, "primera recompensa tangible")

    decision = is_concrete_field(engine.get("big_decision"), min_len=24)
    mark("consequential_decision", decision, "decisión con consecuencias")

    count = sum(1 for v in signals.values() if v)
    # Map 0–9 signals → score 1–10
    score = max(1, min(10, 1 + count))
    return {
        "score": score,
        "signal_count": count,
        "signals": signals,
        "evidence": evidence,
        "ok": score >= SPECIFICITY_THRESHOLD,
    }


def estimate_filmability(package: dict[str, Any]) -> dict[str, Any]:
    """Can this sustain 12–18 minutes of distinct events/visuals?"""
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    evidence: list[str] = []
    points = 0

    filled = [k for k in STORY_ENGINE_KEYS if is_concrete_field(engine.get(k), min_len=20)]
    if len(filled) >= 12:
        points += 3
        evidence.append(f"{len(filled)} concrete story_engine beats")
    elif len(filled) >= 8:
        points += 2
        evidence.append(f"{len(filled)} concrete story_engine beats")
    elif len(filled) >= 5:
        points += 1

    blob = " ".join(str(engine.get(k) or "") for k in STORY_ENGINE_KEYS).lower()
    loc_hits = len(set(_LOCATION_RE.findall(blob)))
    if loc_hits >= 3:
        points += 2
        evidence.append(f"~{loc_hits} señales de locación distintas")
    elif loc_hits >= 2:
        points += 1
        evidence.append(f"~{loc_hits} señales de locación")

    status_fields = ("first_major_reward", "mid_story_complication", "major_threat", "endgame", "big_decision")
    status_n = sum(1 for k in status_fields if is_concrete_field(engine.get(k), min_len=20))
    if status_n >= 4:
        points += 2
        evidence.append("multiple status/crisis beats")
    elif status_n >= 2:
        points += 1

    # Penalize single-mechanism repetition (same short phrase recycled)
    vals = [_low(engine.get(k)) for k in STORY_ENGINE_KEYS if _norm(engine.get(k))]
    uniq = len(set(vals))
    if vals and uniq / max(1, len(vals)) < 0.55:
        points = max(0, points - 2)
        evidence.append("low beat diversity (repeated mechanism language)")
    else:
        points += 1
        evidence.append("distinct escalation language across beats")

    score = max(1, min(10, 2 + points))
    return {"score": score, "evidence": evidence}


def validate_hook(hook: Any) -> dict[str, Any]:
    text = _norm(hook).replace("\r\n", "\n")
    reasons: list[str] = []
    if not text:
        return {"pass": False, "reasons": ["hook vacío"]}
    low = text.lower()
    has_es = bool(_SECOND_PERSON_ES_RE.search(low))
    has_en = bool(re.search(r"\byou\b", low))
    if not has_es and not has_en:
        reasons.append("no es segunda persona (falta tú/te/tienes/eres…)")
    for ban in BANNED_HOOK_OPENERS:
        if low.startswith(ban):
            reasons.append(f"apertura prohibida: {ban}")
    if re.search(r"sueñas con construir algo grande|you dream of building something big", low):
        reasons.append("apertura genérica de sueño")
    if len(text) < 70:
        reasons.append("hook demasiado corto para cold open de 15–30s")
    if is_vague_text(text, min_len=70):
        reasons.append("hook demasiado abstracto")
    if not (
        _MONEY_RE.search(text)
        or _NUMBER_PROOF_RE.search(text)
        or _SITUATION_RE.search(low)
        or _INDUSTRY_RE.search(low)
    ):
        reasons.append("hook sin detalle situacional concreto")
    return {"pass": not reasons, "reasons": reasons}


def parse_world_seeds(raw: Any, package: dict[str, Any] | None = None) -> dict[str, Any]:
    """Strict world_seeds parse — recover from stringified dicts / misplaced fields."""
    keys = (
        "starting_age",
        "starting_cash",
        "starting_location",
        "starting_status",
        "target_outcome",
        "business_or_career_type",
        "timeline_scale",
    )
    out = {k: None if k == "starting_age" else "" for k in keys}
    src: dict[str, Any] = {}

    def _coerce_dict(value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            s = value.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    parsed = json.loads(s.replace("'", '"'))
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    try:
                        parsed = ast.literal_eval(s)
                        if isinstance(parsed, dict):
                            return parsed
                    except (SyntaxError, ValueError):
                        return None
        return None

    seeds = raw if isinstance(raw, dict) else {}
    coerced = _coerce_dict(raw)
    if coerced:
        seeds = coerced
    src.update(seeds)

    pkg = package or {}
    for field in ("starting_state", "end_state"):
        d = _coerce_dict(pkg.get(field))
        if d:
            for k in keys:
                if k in d and not src.get(k):
                    src[k] = d[k]
    for k in keys:
        if k in pkg and not src.get(k):
            src[k] = pkg[k]

    if src.get("starting_age") is not None:
        try:
            out["starting_age"] = int(src["starting_age"])
        except (TypeError, ValueError):
            m = re.search(r"\d+", str(src.get("starting_age")))
            out["starting_age"] = int(m.group()) if m else None
    for k in keys:
        if k == "starting_age":
            continue
        val = src.get(k)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            # Cash often comes as bare int — keep digit string so validation passes
            out[k] = str(val) if k != "starting_cash" else (f"${val}" if float(val) >= 0 else str(val))
        else:
            out[k] = _norm(val or "")
    return out


def validate_world_seeds(seeds: dict[str, Any]) -> dict[str, Any]:
    missing = []
    if not isinstance(seeds.get("starting_age"), int) or not (14 <= int(seeds["starting_age"]) <= 80):
        missing.append("starting_age")
    for k in (
        "starting_cash",
        "starting_location",
        "starting_status",
        "target_outcome",
        "business_or_career_type",
        "timeline_scale",
    ):
        if len(_norm(seeds.get(k))) < 2:
            missing.append(k)
    return {"pass": not missing, "missing": missing}


def validate_category(package: dict[str, Any]) -> dict[str, Any]:
    cat = _low(package.get("story_category"))
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    blob = " ".join(
        [
            str(package.get("premise") or ""),
            str(package.get("core_transformation") or ""),
            str(package.get("one_line_fantasy") or ""),
            str((package.get("world_seeds") or {}).get("business_or_career_type") or ""),
            *[str(engine.get(k) or "") for k in STORY_ENGINE_KEYS],
        ]
    ).lower()

    if not cat:
        return {"pass": False, "reason": "missing story_category", "suggested": "entrepreneurship"}

    # Hard mismatches
    for bad_cat, cues in CATEGORY_MISMATCH.items():
        if cat == bad_cat and any(c in blob for c in cues):
            suggested = _suggest_category(blob)
            return {
                "pass": False,
                "reason": f"category '{cat}' mismatches story cues",
                "suggested": suggested,
            }

    # Special cases from editorial brief
    if cat == "technology" and re.search(r"\b(motel|hotel|hospitalidad|hospitality)\b", blob) and not re.search(
        r"\b(software|saas|app|plataforma|platform|código|codigo|code)\b", blob
    ):
        return {"pass": False, "reason": "historia hotelera etiquetada como technology", "suggested": "empire"}
    if cat == "acquisition" and re.search(
        r"jubilas a tus padres|retire your parents|negocio de servicios|service business", blob
    ) and not re.search(r"\b(compras|compra|adquieres|buy|bought|acquire|purchase|\$1)\b", blob):
        return {"pass": False, "reason": "grind de servicios etiquetado como acquisition", "suggested": "entrepreneurship"}
    if cat == "sports_business" and re.search(
        r"atleta aspirante|aspiring athlete|estrellato|athletic stardom|alfombra roja|red carpet", blob
    ) and not re.search(r"\b(dueño|dueno|owner|franquicia|franchise|adquieres|plantilla|roster|estadio|stadium)\b", blob):
        return {"pass": False, "reason": "fama de atleta etiquetada como sports_business", "suggested": "career"}

    cues = CATEGORY_CUES.get(cat) or CATEGORY_CUES.get("entrepreneurship", ())
    if cues and not any(c in blob for c in cues):
        suggested = _suggest_category(blob)
        # Soft fail only if we can suggest something clearly better
        if suggested and suggested != cat:
            return {
                "pass": False,
                "reason": f"category '{cat}' not supported by story content",
                "suggested": suggested,
            }
    if cat not in DEFAULT_CATEGORIES and cat not in CATEGORY_CUES:
        # allow close custom categories if content is coherent
        pass
    return {"pass": True, "reason": "", "suggested": cat}


def _suggest_category(blob: str) -> str:
    scores: dict[str, int] = {}
    for cat, cues in CATEGORY_CUES.items():
        scores[cat] = sum(1 for c in cues if c in blob)
    best = max(scores, key=scores.get) if scores else "entrepreneurship"
    return best if scores.get(best, 0) > 0 else "entrepreneurship"


def repair_category(package: dict[str, Any]) -> str:
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    blob = " ".join(
        [
            str(package.get("premise") or ""),
            str((package.get("world_seeds") or {}).get("business_or_career_type") or ""),
            *[str(engine.get(k) or "") for k in STORY_ENGINE_KEYS],
        ]
    ).lower()
    return _suggest_category(blob)


def validate_titles(title: str, options: list[dict[str, Any]]) -> dict[str, Any]:
    from src.documentary.formats.check_als.aspirational import title_looks_like_blog

    cleaned: list[dict[str, Any]] = []
    rejected: list[str] = []
    for opt in options:
        text = _norm(opt.get("text") if isinstance(opt, dict) else opt)
        if not text:
            continue
        if any(r.search(text) for r in _BAD_TITLE_RES) or title_looks_like_blog(text):
            rejected.append(text)
            continue
        cleaned.append(opt if isinstance(opt, dict) else {"text": text})
    title_ok = bool(title) and not any(r.search(title) for r in _BAD_TITLE_RES) and not title_looks_like_blog(title)
    if not title_ok and cleaned:
        title = _norm(cleaned[0].get("text") if isinstance(cleaned[0], dict) else cleaned[0])
        title_ok = True
    return {
        "pass": title_ok and len(cleaned) >= 1,
        "title": title if title_ok else "",
        "options": cleaned,
        "rejected": rejected,
    }


def validate_thumbnail(thumb: dict[str, Any] | None) -> dict[str, Any]:
    t = thumb if isinstance(thumb, dict) else {}
    placeholders_hit: list[str] = []
    for key in ("main_visual", "protagonist_state", "environment", "central_contrast", "emotion", "key_object", "background"):
        val = _low(t.get(key))
        if not val:
            continue
        for p in THUMBNAIL_PLACEHOLDERS:
            # Exact/near-exact placeholder only — avoid false positives like "plano medio amplio"
            if val == p or val == f"un {p}" or val.startswith(p + "…") or val.startswith(p + "..."):
                placeholders_hit.append(f"{key}:{p}")
    main = _norm(t.get("main_visual"))
    contrast = _norm(t.get("central_contrast"))
    key_obj = _norm(t.get("key_object"))
    prompt = _norm(t.get("thumbnail_prompt"))
    reasons = []
    if placeholders_hit:
        reasons.append(f"placeholders: {', '.join(placeholders_hit)}")
    if len(main) < 24:
        reasons.append("main_visual too thin")
    if len(contrast) < 12:
        reasons.append("central_contrast too thin")
    if len(key_obj) < 8:
        reasons.append("key_object too thin")
    if len(prompt) < 40:
        reasons.append("thumbnail_prompt too thin")
    return {"pass": not reasons, "reasons": reasons}


def validate_story_question(q: Any) -> dict[str, Any]:
    text = _norm(q)
    if len(text) < 20:
        return {"pass": False, "reason": "missing/short central_story_question"}
    if not text.endswith("?") and "?" not in text:
        return {"pass": False, "reason": "story question must be a question"}
    if is_vague_text(text, min_len=20):
        return {"pass": False, "reason": "story question too vague"}
    return {"pass": True, "reason": ""}


def validate_open_loops(loops: Any) -> dict[str, Any]:
    if not isinstance(loops, list):
        return {"pass": False, "reason": "open_loops must be a list", "loops": []}
    cleaned = [_norm(x) for x in loops if _norm(x)]
    cleaned = cleaned[:MAX_OPEN_LOOPS]
    if len(cleaned) < MIN_OPEN_LOOPS:
        return {"pass": False, "reason": f"need {MIN_OPEN_LOOPS}–{MAX_OPEN_LOOPS} open_loops", "loops": cleaned}
    return {"pass": True, "reason": "", "loops": cleaned}


def evaluate_coherence_v2(package: dict[str, Any]) -> dict[str, Any]:
    """Semantic-ish coherence: shared concrete anchors across package surfaces."""
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    thumb = package.get("thumbnail_concept") if isinstance(package.get("thumbnail_concept"), dict) else {}

    surfaces = {
        "title": _low(package.get("title")),
        "fantasy": _low(package.get("one_line_fantasy")),
        "premise": _low(package.get("premise")),
        "story_engine": _low(" ".join(str(engine.get(k) or "") for k in STORY_ENGINE_KEYS)),
        "thumbnail": _low(
            " ".join(str(thumb.get(k) or "") for k in ("main_visual", "central_contrast", "key_object", "thumbnail_prompt"))
        ),
        "hook": _low(package.get("hook")),
        "transformation": _low(package.get("core_transformation")),
        "end_state": _low(package.get("end_state")),
    }

    def tokens(s: str) -> set[str]:
        stop = {
            "that", "this", "with", "from", "your", "have", "into", "when", "then",
            "they", "them", "their", "about", "after", "before", "while",
            "para", "como", "esta", "este", "estos", "estas", "donde", "cuando",
            "tiene", "tienes", "eres", "estas", "estás", "pero", "porque", "sobre",
            "entre", "hasta", "desde", "después", "despues", "antes", "todo", "toda",
            "una", "unos", "unas", "del", "los", "las", "por", "con", "sin",
        }
        return {w for w in re.findall(r"[a-z0-9áéíóúñü$]+", s) if len(w) > 3 and w not in stop}

    core = tokens(surfaces["premise"]) | tokens(surfaces["story_engine"])
    notes: list[str] = []
    checks: dict[str, bool] = {}

    # If story_engine is rich, require other surfaces to share at least one content token with it
    for name in ("title", "fantasy", "thumbnail", "hook", "transformation", "end_state"):
        text = surfaces[name]
        if not text:
            checks[name] = False
            notes.append(f"{name} empty")
            continue
        tset = tokens(text)
        overlap = len(core & tset) if core else 0
        ok = overlap >= 1
        # Title/hook can pass with money or shared industry word even if stemming differs
        if not ok and name in ("title", "hook", "fantasy"):
            ok = bool(
                _INDUSTRY_RE.search(text)
                and _INDUSTRY_RE.search(surfaces["story_engine"] + " " + surfaces["premise"])
            )
        checks[name] = ok
        if not ok:
            notes.append(f"{name} diverges from premise/story_engine")

    aux_overlap = len(tokens(surfaces["title"]) & tokens(surfaces["thumbnail"])) >= 1
    passed = (
        bool(surfaces["premise"])
        and bool(surfaces["story_engine"])
        and checks.get("hook", False)
        and checks.get("title", False)
        and checks.get("transformation", False)
        and checks.get("thumbnail", False)
    )
    # fantasy/end_state soft: warn but don't hard-fail if core narrative aligns
    if not checks.get("fantasy"):
        notes.append("fantasy weak overlap (soft)")
    if not checks.get("end_state"):
        notes.append("end_state weak overlap (soft)")

    return {
        "pass": passed,
        "checks": checks,
        "aux_lexical_title_thumb": aux_overlap,
        "title_matches_thumbnail": checks.get("thumbnail", False) and checks.get("title", False),
        "hook_fulfills_promise": checks.get("hook", False),
        "transformation_aligned": checks.get("transformation", False),
        "notes": "; ".join(notes),
    }


def count_cliches(package: dict[str, Any]) -> list[str]:
    blob = " ".join(
        [
            str(package.get("premise") or ""),
            str(package.get("title") or ""),
            str(package.get("one_line_fantasy") or ""),
            str(package.get("hook") or ""),
        ]
    ).lower()
    return [c for c in CLICHE_PHRASES if c in blob]


def story_engine_strength(package: dict[str, Any]) -> dict[str, Any]:
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    evidence = []
    concrete_n = 0
    for k in STORY_ENGINE_KEYS:
        if is_concrete_field(engine.get(k), min_len=24):
            concrete_n += 1
            if k in ("specific_opportunity", "growth_mechanism", "major_threat", "big_decision", "first_proof"):
                evidence.append(f"{k}: {_norm(engine.get(k))[:90]}")
    score = max(1, min(10, round(concrete_n / max(1, len(STORY_ENGINE_KEYS)) * 10)))
    return {"score": score, "evidence": evidence[:6], "concrete_fields": concrete_n}
