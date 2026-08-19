"""Aspirational Engine for Check Concept packages (Phase 1.6)."""
from __future__ import annotations

import re
from typing import Any

REWARD_TYPES = (
    "financial",
    "lifestyle",
    "family",
    "status",
    "freedom",
    "ownership",
    "experience",
    "relationship",
    "environment",
)

SCALE_CEILINGS = (
    "local",
    "regional",
    "national",
    "international",
    "category_leader",
    "major_exit",
    "empire",
)

SCALE_RANK = {
    "local": 3,
    "regional": 5,
    "national": 7,
    "international": 8,
    "category_leader": 9,
    "major_exit": 9,
    "empire": 10,
}

NATIONAL_PLUS = {"national", "international", "category_leader", "major_exit", "empire"}

LIFE_PROGRESSION_KEYS = ("start", "early_reward", "mid_reward", "major_reward", "late_state")
LIFE_STAGE_FIELDS = (
    "stage",
    "age_or_time",
    "living_situation",
    "financial_state",
    "freedom",
    "status",
    "family_effect",
    "environment",
)

# Soft local-turnaround pattern (batch diversity)
_LOCAL_RESCUE_CUES = (
    "local en quiebra",
    "negocio local",
    "sobrevive",
    "competidor local",
    "tienda del barrio",
    "único local",
    "un solo local",
    "rescue",
    "turnaround local",
)

_LUXURY_FILLER = (
    "lamborghini",
    "jet privado",
    "mansión",
    "mansion",
    "rolex",
    "dubai",
    "yate",
    "ferrari",
)

_COMMUNITY_SAVIOR = (
    "empoder",
    "revives comunidades",
    "revive comunidades",
    "revitaliz",
    "salvar a tu barrio",
    "salvar el barrio",
    "comunidad local",
    "productores locales",
    "centro creativo",
    "espacios creativos",
)

_GENERIC_COMPETITOR = (
    "la competencia",
    "un competidor",
    "competidores poderosos",
    "un gigante",
    "la gran empresa",
    "grandes corporaciones",
)


def empty_life_stage(stage: str = "start") -> dict[str, str]:
    return {k: (stage if k == "stage" else "") for k in LIFE_STAGE_FIELDS}


def empty_life_progression() -> dict[str, Any]:
    out: dict[str, Any] = {k: [] for k in LIFE_PROGRESSION_KEYS}
    out["stages"] = [empty_life_stage(k) for k in LIFE_PROGRESSION_KEYS]
    return out


def empty_reward() -> dict[str, Any]:
    return {"type": "", "moment": "", "description": "", "story_significance": "", "story_beat": ""}


def _norm(v: Any) -> str:
    if isinstance(v, dict):
        for k in ("description", "text", "summary", "living_situation", "value"):
            if v.get(k):
                return re.sub(r"\s+", " ", str(v.get(k) or "")).strip()
        return re.sub(r"\s+", " ", " ".join(str(x) for x in v.values() if x)).strip()
    if isinstance(v, list):
        return re.sub(r"\s+", " ", " ".join(_norm(x) for x in v if x)).strip()
    return re.sub(r"\s+", " ", str(v or "")).strip()


def _low(v: Any) -> str:
    return _norm(v).lower()


def normalize_scale_ceiling(raw: Any) -> str:
    s = _low(raw).replace(" ", "_").replace("-", "_")
    aliases = {
        "nacional": "national",
        "internacional": "international",
        "lider_de_categoria": "category_leader",
        "líder_de_categoría": "category_leader",
        "categoryleader": "category_leader",
        "exit": "major_exit",
        "salida": "major_exit",
        "ipo": "major_exit",
        "regional_": "regional",
        "local_": "local",
    }
    for a, b in aliases.items():
        if s == a or s.startswith(a):
            return b
    if s in SCALE_CEILINGS:
        return s
    # infer from text
    blob = s
    if any(x in blob for x in ("imperio", "empire", "120 local", "franquicia nacional")):
        return "empire"
    if any(x in blob for x in ("exit", "venta", "adquisición por", "adquisicion por", "$100m", "valuación")):
        return "major_exit"
    if any(x in blob for x in ("internacional", "international", "países", "paises", "countries")):
        return "international"
    if any(x in blob for x in ("nacional", "national", "país", "pais")):
        return "national"
    if any(x in blob for x in ("regional", "varios estados", "multi-ciudad", "multi ciudad")):
        return "regional"
    if any(x in blob for x in ("categoría", "categoria", "category", "líder", "lider")):
        return "category_leader"
    return "local" if s else "local"


def fill_escalation_ladder(package: dict[str, Any]) -> list[dict[str, Any]]:
    """Prefer explicit ladder; fall back to story_engine.escalation_path. Canonical dicts."""
    ladder = normalize_escalation_ladder(package.get("escalation_ladder"))
    if len(ladder) >= 5:
        return [{**row, "level": i} for i, row in enumerate(ladder, 1)]
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    extra = normalize_escalation_ladder(engine.get("escalation_path"))
    seen = {_low(row.get("event")) for row in ladder}
    for step in extra:
        key = _low(step.get("event"))
        if key and key not in seen:
            ladder.append(step)
            seen.add(key)
    return [{**row, "level": i} for i, row in enumerate(ladder[:8], 1)]


def synthesize_hook(package: dict[str, Any]) -> str:
    """Cold open from concrete engine beats — used when the LLM hook fails the gate."""
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    ws = package.get("world_seeds") if isinstance(package.get("world_seeds"), dict) else {}
    age = ws.get("starting_age")
    loc = _norm(ws.get("starting_location") or "")
    notice = _norm(engine.get("why_protagonist_notices_it") or "")
    action = _norm(engine.get("initial_action") or "")
    proof = _norm(engine.get("first_proof") or "")
    cash = _norm(ws.get("starting_cash") or "")
    parts: list[str] = []
    if age:
        where = f" en {loc}" if loc else ""
        money = f" Tienes {cash} en la cuenta." if cash else ""
        parts.append(f"Tienes {age} años{where}.{money}".strip())
    elif loc:
        parts.append(f"Estás en {loc}.")
    else:
        status = _norm(ws.get("starting_status") or "")
        if status:
            parts.append(f"Trabajas como {status}.")
        else:
            parts.append("Empieza un turno que todavía no es tuyo.")
    for chunk in (notice, action, proof):
        if chunk and chunk.lower() not in " ".join(parts).lower():
            parts.append(chunk if chunk.endswith((".", "!", "?")) else chunk + ".")
    return "\n\n".join(parts).strip()


def count_end_state_facts(text: str) -> int:
    t = _low(text)
    n = 0
    if re.search(r"\b(edad|age)\b|\b(?:1[6-9]|[2-6]\d)\s*(años|years)?\b", t):
        n += 1
    if re.search(r"\$\s?\d|\b\d[\d.,]*\s*(millones|m)\b", t):
        n += 1
    if any(x in t for x in ("emplead", "employee", "locales", "franquicia")):
        n += 1
    if any(x in t for x in ("país", "pais", "countries", "estados", "ciudades")):
        n += 1
    if any(x in t for x in ("padres", "hipoteca", "departamento", "apartamento", "casa propia")):
        n += 1
    if any(x in t for x in ("horario", "tiempo", "agenda", "autonomía", "autonomia", "libertad")):
        n += 1
    return n


def named_antagonist(text: str) -> bool:
    t = _low(text)
    if not t or len(t) < 28:
        return False
    if any(g in t for g in _GENERIC_COMPETITOR) and not re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}", text or ""):
        # generic label only
        if not re.search(r"plataforma|incumbente|roll-up|pe\b|cadena pública|cadena publica|clon", t):
            return False
    return bool(
        re.search(
            r"plataforma|incumbente|roll-?up|private equity|\bpe\b|cadena|clon|"
            r"copia la función|copia la funcion|regala gratis|incluye gratis",
            t,
        )
    )


def has_community_savior_bias(package: dict[str, Any]) -> bool:
    blob = " ".join(
        [
            _low(package.get("premise")),
            _low(package.get("title")),
            _low(package.get("one_line_fantasy")),
            _low(package.get("core_transformation")),
        ]
    )
    return any(c in blob for c in _COMMUNITY_SAVIOR)


def unique_money_mentions(package: dict[str, Any]) -> int:
    from src.documentary.formats.check_als.quality import ladder_event_texts

    blob = " ".join(
        [
            str(package.get("premise") or ""),
            str(package.get("end_state") or ""),
            " ".join(ladder_event_texts(normalize_escalation_ladder(package.get("escalation_ladder")))),
            " ".join(str(v) for v in ((package.get("story_engine") or {}) if isinstance(package.get("story_engine"), dict) else {}).values()),
        ]
    )
    found = re.findall(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s*(?:k|m|millones?))?", blob, flags=re.I)
    return len({re.sub(r"\s+", "", x.lower()) for x in found})


def normalize_escalation_ladder(raw: Any) -> list[dict[str, Any]]:
    """Canonical ladder: [{level, event, world_delta}, ...]. Accepts strings/dicts."""
    items: list[Any]
    if isinstance(raw, list):
        items = list(raw)
    elif isinstance(raw, str) and raw.strip():
        items = [_norm(x) for x in re.split(r"[\n;]|→|->", raw) if _norm(x)]
    elif isinstance(raw, dict):
        items = [raw]
    else:
        items = []
    cleaned: list[dict[str, Any]] = []
    for i, it in enumerate(items, 1):
        row = _coerce_ladder_item(it, i)
        if row["event"]:
            cleaned.append(row)
    return cleaned[:8]


def _coerce_ladder_item(raw: Any, index: int) -> dict[str, Any]:
    if isinstance(raw, dict):
        level_raw = raw.get("level")
        event = _norm(
            raw.get("event")
            or raw.get("description")
            or raw.get("nivel")
            or raw.get("text")
            or (level_raw if isinstance(level_raw, str) else "")
        )
        if isinstance(level_raw, str) and _norm(raw.get("description") or raw.get("event")):
            event = _norm(raw.get("event") or raw.get("description") or "")
        try:
            level = int(level_raw) if isinstance(level_raw, (int, float)) else index
        except (TypeError, ValueError):
            level = index
        event = re.sub(r"^\d+[\).:\-]\s*", "", event).strip()
        return {
            "level": level,
            "event": event,
            "world_delta": _norm(raw.get("world_delta") or raw.get("delta") or ""),
        }
    text = _norm(raw)
    text = re.sub(r"^\d+[\).:\-]\s*", "", text).strip()
    return {"level": index, "event": text, "world_delta": ""}


def _coerce_life_stage(raw: Any, stage: str) -> dict[str, str]:
    row = empty_life_stage(stage)
    if isinstance(raw, dict):
        for k in LIFE_STAGE_FIELDS:
            if k == "stage":
                row["stage"] = _norm(raw.get("stage") or stage) or stage
            else:
                row[k] = _norm(raw.get(k) or "")
        if not any(row[k] for k in LIFE_STAGE_FIELDS if k != "stage"):
            row["living_situation"] = _norm(raw)
        return row
    text = _norm(raw)
    if text:
        row["living_situation"] = text
    return row


def _legacy_bits_from_stage(stage: dict[str, str]) -> list[str]:
    bits = []
    for k in ("living_situation", "financial_state", "freedom", "status", "family_effect", "environment", "age_or_time"):
        val = _norm(stage.get(k) or "")
        if val:
            bits.append(val)
    return bits[:6]


def normalize_life_progression(raw: Any) -> dict[str, Any]:
    """Canonical stages + legacy start/early/mid/major/late string lists."""
    out = empty_life_progression()
    stages_in: list[Any] = []
    src = raw
    if isinstance(raw, dict) and isinstance(raw.get("stages"), list):
        stages_in = list(raw.get("stages") or [])
        src = raw
    elif isinstance(raw, list):
        stages_in = list(raw)
        src = {}
    elif isinstance(raw, dict):
        src = raw
    else:
        return out

    if stages_in:
        built = []
        for i, row in enumerate(stages_in[:5]):
            stage_name = LIFE_PROGRESSION_KEYS[i] if i < len(LIFE_PROGRESSION_KEYS) else f"stage_{i}"
            built.append(_coerce_life_stage(row, stage_name))
        while len(built) < 5:
            built.append(empty_life_stage(LIFE_PROGRESSION_KEYS[len(built)]))
        out["stages"] = built
        for i, key in enumerate(LIFE_PROGRESSION_KEYS):
            out[key] = _legacy_bits_from_stage(built[i])
        return out

    for i, k in enumerate(LIFE_PROGRESSION_KEYS):
        v = src.get(k) if isinstance(src, dict) else None
        if isinstance(v, list):
            bits = [_norm(x) for x in v if _norm(x)][:6]
        elif isinstance(v, dict):
            stage = _coerce_life_stage(v, k)
            out["stages"][i] = stage
            bits = _legacy_bits_from_stage(stage)
        elif isinstance(v, str) and v.strip():
            bits = [_norm(x) for x in re.split(r"[;\n|]", v) if _norm(x)][:6]
        else:
            bits = []
        out[k] = bits
        if bits and not any(out["stages"][i].get(f) for f in LIFE_STAGE_FIELDS if f != "stage"):
            out["stages"][i]["living_situation"] = bits[0]
            if len(bits) > 1:
                out["stages"][i]["financial_state"] = bits[1]
            if len(bits) > 2:
                out["stages"][i]["freedom"] = bits[2]
            if len(bits) > 3:
                out["stages"][i]["status"] = bits[3]
            if len(bits) > 4:
                out["stages"][i]["family_effect"] = bits[4]
            if len(bits) > 5:
                out["stages"][i]["environment"] = bits[5]
    return out


def normalize_rewards(raw: Any) -> list[dict[str, Any]]:
    rows: list[Any]
    if isinstance(raw, dict):
        if isinstance(raw.get("rewards"), list):
            rows = list(raw.get("rewards") or [])
        else:
            rows = []
            for k, v in raw.items():
                if k in {"rewards", "items"}:
                    continue
                if isinstance(v, dict):
                    rows.append({"type": v.get("type") or k, **v})
                else:
                    rows.append({"type": k, "description": v})
    elif isinstance(raw, list):
        rows = list(raw)
    else:
        rows = []

    mapping = {
        "financiera": "financial",
        "dinero": "financial",
        "estilo_de_vida": "lifestyle",
        "estilo de vida": "lifestyle",
        "familia": "family",
        "estatus": "status",
        "libertad": "freedom",
        "propiedad": "ownership",
        "experiencia": "experience",
        "relación": "relationship",
        "relacion": "relationship",
        "entorno": "environment",
    }
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, str) and row.strip():
            out.append(
                {
                    "type": _infer_reward_type(row, "financial"),
                    "description": _norm(row),
                    "moment": "",
                    "story_significance": "",
                    "story_beat": "",
                }
            )
            continue
        if not isinstance(row, dict):
            continue
        if "description" not in row and "text" not in row and len(row) == 1:
            k, v = next(iter(row.items()))
            row = {"type": k, "description": v if not isinstance(v, dict) else v.get("description") or v}
        typ = _low(row.get("type") or "financial").replace(" ", "_")
        if typ not in REWARD_TYPES:
            typ = mapping.get(typ, mapping.get(_low(row.get("type")), "financial"))
        desc = _norm(row.get("description") or row.get("text") or "")
        if not desc:
            continue
        if typ == "financial":
            typ = _infer_reward_type(desc, "financial")
        moment = _norm(row.get("moment") or row.get("story_beat") or "")
        out.append(
            {
                "type": typ,
                "description": desc,
                "moment": moment,
                "story_significance": _norm(row.get("story_significance") or row.get("why_it_matters") or ""),
                "story_beat": moment,
            }
        )
    seen = set()
    uniq = []
    for r in out:
        key = r["description"].lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    types = {r["type"] for r in uniq}
    if len(uniq) >= 3 and len(types) < 2:
        for r in uniq:
            r["type"] = _infer_reward_type(r["description"], r["type"])
    return uniq[:8]


def fill_rewards_if_thin(package: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic reward fill from life_progression / end_state when LLM omits typed rewards."""
    rewards = normalize_rewards(package.get("rewards"))
    types = {r["type"] for r in rewards}
    if len(rewards) >= 3 and len(types) >= 2:
        return rewards
    life = normalize_life_progression(package.get("life_progression"))
    extras: list[dict[str, Any]] = []
    stage_defaults = (
        ("early_reward", "financial"),
        ("mid_reward", "lifestyle"),
        ("major_reward", "family"),
        ("late_state", "status"),
    )
    for stage, default in stage_defaults:
        bits = life.get(stage) or []
        if not bits:
            continue
        desc = bits[0] if isinstance(bits, list) else str(bits)
        extras.append(
            {
                "type": _infer_reward_type(str(desc), default),
                "description": _norm(desc),
                "moment": stage,
                "story_significance": "",
                "story_beat": stage,
            }
        )
    end = _norm(package.get("end_state"))
    if end:
        extras.append(
            {
                "type": _infer_reward_type(end, "financial"),
                "description": end[:180],
                "moment": "late_state",
                "story_significance": "",
                "story_beat": "late_state",
            }
        )
    merged = rewards + extras
    return normalize_rewards(merged)


def _infer_reward_type(text: str, default: str = "financial") -> str:
    t = _low(text)
    cues = (
        ("padres", "family"),
        ("familia", "family"),
        ("hipoteca", "family"),
        ("horario", "freedom"),
        ("libertad", "freedom"),
        ("autonomía", "freedom"),
        ("autonomia", "freedom"),
        ("dueño", "ownership"),
        ("dueno", "ownership"),
        ("equity", "ownership"),
        ("posees", "ownership"),
        ("casa", "lifestyle"),
        ("departamento", "lifestyle"),
        ("apartamento", "lifestyle"),
        ("playa", "lifestyle"),
        ("reconoc", "status"),
        ("líder", "status"),
        ("lider", "status"),
        ("referente", "status"),
        ("invitan", "status"),
        ("viaj", "experience"),
        ("concierto", "experience"),
    )
    for cue, typ in cues:
        if cue in t:
            return typ
    return default if default in REWARD_TYPES else "financial"


def normalize_start_end_contrast(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {
            "start": _norm(raw.get("start") or ""),
            "end": _norm(raw.get("end") or ""),
            "one_line": _norm(raw.get("one_line") or ""),
        }
    if isinstance(raw, str) and raw.strip():
        parts = re.split(r"\n\s*[↓→\-]+\s*\n|\n\n", raw.strip(), maxsplit=1)
        if len(parts) == 2:
            return {"start": _norm(parts[0]), "end": _norm(parts[1]), "one_line": ""}
        return {"start": "", "end": "", "one_line": _norm(raw)}
    return {"start": "", "end": "", "one_line": ""}


def is_local_turnaround_pattern(package: dict[str, Any]) -> bool:
    """Detect small-business rescue that stays local."""
    from src.documentary.formats.check_als.quality import ladder_event_texts

    scale = normalize_scale_ceiling(package.get("scale_ceiling"))
    ladder = normalize_escalation_ladder(package.get("escalation_ladder"))
    blob = " ".join(
        [
            _low(package.get("premise")),
            _low(package.get("end_state")),
            _low(package.get("core_transformation")),
            _low((package.get("story_engine") or {}).get("endgame")),
            _low((package.get("story_engine") or {}).get("escalation_path")),
            " ".join(ladder_event_texts(ladder)),
        ]
    )
    localish = scale == "local" or scale == "regional"
    rescue = any(c in blob for c in _LOCAL_RESCUE_CUES) or (
        ("compra" in blob or "compras" in blob or "quiebra" in blob)
        and ("sobrevive" in blob or "rentable" in blob)
        and not any(x in blob for x in ("franquicia", "nacional", "imperio", "arr", "mrr", "millones", "países", "paises"))
    )
    ladder = normalize_escalation_ladder(package.get("escalation_ladder"))
    short_ladder = len(ladder) < 5
    return bool(localish and (rescue or short_ladder))


def evaluate_aspirational(package: dict[str, Any]) -> dict[str, Any]:
    """Deterministic aspirational evaluation + gates. No generic LLM self-score."""
    from src.documentary.formats.check_als.quality import evaluate_life_magnitude, ladder_event_texts, repair_scale_consistency

    repair_scale_consistency(package)
    ladder = fill_escalation_ladder(package)
    life = normalize_life_progression(package.get("life_progression"))
    rewards = fill_rewards_if_thin({**package, "life_progression": life})
    scale = normalize_scale_ceiling(package.get("scale_ceiling"))
    contrast = normalize_start_end_contrast(package.get("start_end_contrast"))
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    community = has_community_savior_bias(package)
    end_facts = count_end_state_facts(str(package.get("end_state") or contrast.get("end") or ""))
    money_n = unique_money_mentions({**package, "escalation_ladder": ladder})

    # Fill contrast from states if missing
    if not contrast.get("start"):
        contrast["start"] = _norm(package.get("starting_state"))
    if not contrast.get("end"):
        contrast["end"] = _norm(package.get("end_state"))

    evidence: list[str] = []
    biz_signals = 0
    life_signals = 0

    # Business fantasy signals
    if is_concrete_scale_language(engine.get("growth_mechanism") or ""):
        biz_signals += 1
        evidence.append("mecanismo de crecimiento concreto")
    if named_antagonist(str(engine.get("major_threat") or "")):
        biz_signals += 1
        evidence.append("amenaza competitiva nombrada / de escala")
    elif is_concrete_scale_language(engine.get("major_threat") or ""):
        biz_signals += 1
        evidence.append("amenaza competitiva de escala")
    if any(x in _low(engine.get("endgame")) for x in ("imperio", "exit", "venta", "nacional", "internacional", "franquicia")):
        biz_signals += 1
        evidence.append(f"endgame de negocio: {_norm(engine.get('endgame'))[:80]}")
    if len(ladder) >= 5:
        biz_signals += 1
        evidence.append(f"escalation_ladder con {len(ladder)} niveles")
    if len(ladder) >= 7:
        biz_signals += 1
    if scale in NATIONAL_PLUS:
        biz_signals += 2
        evidence.append(f"scale_ceiling={scale}")
    elif scale == "regional":
        biz_signals += 1
        evidence.append("scale_ceiling=regional")
    if money_n >= 2:
        biz_signals += 1
        evidence.append(f"{money_n} cifras distintas en la progresión")

    blob_all = " ".join(
        [
            _low(package.get("premise")),
            _low(package.get("end_state")),
            _low(package.get("one_line_fantasy")),
            " ".join(ladder_event_texts(ladder)),
            " ".join(
                _norm(x)
                for k in LIFE_PROGRESSION_KEYS
                for x in (life.get(k) or [] if isinstance(life.get(k), list) else [])
            ),
        ]
    )
    if any(x in blob_all for x in ("dueño", "dueña", "owner", "equity", "socio", "controlas", "posees", "adquieres")):
        biz_signals += 1
        evidence.append("fantasía de ownership/control")

    filled_stages = sum(1 for k in LIFE_PROGRESSION_KEYS if life.get(k))
    if filled_stages >= 4:
        life_signals += 2
        evidence.append(f"life_progression con {filled_stages} etapas")
    elif filled_stages >= 2:
        life_signals += 1

    reward_types = {r["type"] for r in rewards}
    if len(rewards) >= 3:
        life_signals += 1
        evidence.append(f"{len(rewards)} recompensas tipadas")
    if len(reward_types) >= 3:
        life_signals += 1
        evidence.append(f"tipos de reward: {', '.join(sorted(reward_types))}")

    life_cues = (
        "libertad",
        "jubil",
        "padres",
        "mudas",
        "oficina",
        "viaj",
        "autonomía",
        "autonomia",
        "patrimonio",
        "independencia",
        "horario",
        "status",
        "reconocimiento",
        "departamento",
        "apartamento",
    )
    life_hits = [c for c in life_cues if c in blob_all]
    if life_hits:
        life_signals += min(3, len(life_hits))
        evidence.append("vida deseable: " + ", ".join(life_hits[:5]))

    has_contrast = bool(contrast.get("start") and contrast.get("end") and len(contrast["start"]) > 20 and len(contrast["end"]) > 20)
    if has_contrast:
        life_signals += 1
        evidence.append("start_end_contrast presente")

    end = _low(package.get("end_state"))
    vague_end = end in {"", "successful business owner", "dueño exitoso", "negocio exitoso", "emprendedor exitoso"}
    concrete_end = (not vague_end) and end_facts >= 3
    if concrete_end:
        life_signals += 1
        evidence.append(f"end_state concreto ({end_facts} hechos)")
    else:
        evidence.append("end_state débil/abstracto")

    lux = [x for x in _LUXURY_FILLER if x in blob_all]
    if lux and len(reward_types) <= 2:
        evidence.append("lujo genérico sin diversidad de rewards: " + ", ".join(lux[:3]))
        life_signals = max(0, life_signals - 1)

    if community:
        evidence.append("sesgo community-savior / barrio (penaliza fantasía Check)")
        life_signals = max(0, life_signals - 2)
        biz_signals = max(0, biz_signals - 1)

    # Float-ish 1–10 that does not saturate at 10 for every eligible package
    aspirational_strength = max(
        1,
        min(
            10,
            round(
                2.0
                + min(4.0, biz_signals * 0.55)
                + min(3.0, life_signals * 0.35)
                + (0.6 if scale in {"international", "category_leader", "major_exit", "empire"} else 0)
            ),
        ),
    )
    life_progression_completeness = max(
        1,
        min(
            10,
            round(1.5 + life_signals * 0.7 + (1.5 if has_contrast and concrete_end else 0) + min(2, end_facts * 0.4)),
        ),
    )
    mag = evaluate_life_magnitude({**package, "escalation_ladder": ladder, "scale_ceiling": scale})
    life_transformation = int(mag.get("life_transformation_strength") or 5)
    evidence.extend(list(mag.get("evidence") or [])[:4])
    scale_potential = SCALE_RANK.get(scale, 3)
    if len(ladder) >= 7 and money_n >= 2:
        scale_potential = min(10, scale_potential + 1)
    if len(ladder) < 4:
        scale_potential = max(1, scale_potential - 2)
    if community and scale in {"national", "regional", "local"}:
        scale_potential = max(1, scale_potential - 1)
    reward_density = max(1, min(10, len(rewards) + len(reward_types) + (1 if "freedom" in reward_types or "ownership" in reward_types else 0)))

    would_press = (
        scale in NATIONAL_PLUS
        and life_transformation >= 6
        and life_progression_completeness >= 6
        and aspirational_strength >= 6
        and len(rewards) >= 3
        and concrete_end
        and not community
    ) or (
        life_transformation >= 8 and aspirational_strength >= 7 and has_contrast and len(rewards) >= 3 and end_facts >= 4
    )

    aspirational_score = round(
        (
            aspirational_strength * 0.35
            + life_transformation * 0.30
            + scale_potential * 0.20
            + reward_density * 0.15
        ),
        2,
    )

    # Evidence for the button test must name concrete desirable aspects
    if would_press:
        evidence.append(
            "fantasy test: una parte del público Check pulsaría vivir esto por "
            + "; ".join([e for e in evidence if e][:3])
        )
    else:
        evidence.append("fantasy test: transformación insuficiente o techo demasiado bajo / community-savior")

    has_aspirational_transformation = (
        aspirational_strength >= 6
        and life_progression_completeness >= 6
        and not community
        and (
            scale in NATIONAL_PLUS
            or (scale == "regional" and life_progression_completeness >= 8 and end_facts >= 4)
            or (scale == "local" and life_progression_completeness >= 9 and would_press and end_facts >= 5)
        )
    )
    has_life_progression = filled_stages >= 3 and concrete_end
    has_scale_progression = len(ladder) >= 5 and scale_potential >= 5
    has_visible_rewards = len(rewards) >= 3 and len(reward_types) >= 2 and not (
        reward_types <= {"financial"} and len(reward_types) == 1
    )

    if scale == "local" and life_progression_completeness < 9:
        has_aspirational_transformation = False
        evidence.append("techo local sin life fantasy extraordinaria")
    if community:
        has_aspirational_transformation = False

    biz_ev = [e for e in evidence if any(x in e.lower() for x in ("negocio", "crecimiento", "scale", "ownership", "ladder", "amenaza", "endgame", "cifras"))]
    life_ev = [e for e in evidence if any(x in e.lower() for x in ("vida", "reward", "life_", "contrast", "end_state", "fantasía", "fantasy"))]

    return {
        "business_fantasy": {
            "score": max(1, min(10, round(1.5 + biz_signals * 0.7))),
            "evidence": (biz_ev or evidence)[:6],
        },
        "life_fantasy": {
            "score": max(1, min(10, round(1.5 + life_signals * 0.7))),
            "evidence": (life_ev or evidence)[:6],
        },
        "aspirational_score": aspirational_score,
        "aspirational_evidence": evidence[:10],
        "aspirational_strength": aspirational_strength,
        "life_transformation": life_transformation,
        "life_progression_completeness": life_progression_completeness,
        "scale_potential": scale_potential,
        "reward_density": reward_density,
        "scale_ceiling": scale,
        "would_press_button": would_press,
        "community_savior_bias": community,
        "end_state_facts": end_facts,
        "gates": {
            "has_aspirational_transformation": bool(has_aspirational_transformation),
            "has_life_progression": bool(has_life_progression),
            "has_scale_progression": bool(has_scale_progression),
            "has_visible_rewards": bool(has_visible_rewards),
        },
        "normalized": {
            "escalation_ladder": ladder,
            "life_progression": life,
            "rewards": rewards,
            "start_end_contrast": contrast,
            "scale_ceiling": scale,
        },
        "is_local_turnaround": is_local_turnaround_pattern({**package, "scale_ceiling": scale, "escalation_ladder": ladder}),
    }


def is_concrete_scale_language(text: str) -> bool:
    t = _low(text)
    if len(t) < 24:
        return False
    return bool(
        re.search(
            r"\d+|franquicia|nacional|internacional|arr|mrr|locales|empleados|"
            r"adquis|concesionario|marketplace|serie a|valuaci|millones",
            t,
        )
    )


def apply_batch_diversity(
    packages: list[dict[str, Any]],
    *,
    max_local_turnaround: int = 2,
    max_similar_mechanism: int = 2,
) -> list[dict[str, Any]]:
    """Penalize / drop near-duplicates and excess local turnarounds before Top N."""
    kept: list[dict[str, Any]] = []
    local_n = 0
    mech_counts: dict[str, int] = {}

    def mech_key(p: dict[str, Any]) -> str:
        eng = p.get("story_engine") if isinstance(p.get("story_engine"), dict) else {}
        blob = _low(eng.get("business_or_progress_mechanism") or p.get("premise") or "")
        # coarse bucket
        for token in (
            "saas",
            "suscrip",
            "lavander",
            "restaur",
            "cafeter",
            "taller",
            "franquic",
            "marketplace",
            "logíst",
            "logistic",
            "estadio",
            "liga",
            "baloncesto",
            "música",
            "musica",
            "motel",
            "hotel",
            "inmobil",
            "entrada",
            "reventa",
            "fábrica",
            "fabrica",
            "sostenib",
            "artesan",
            "fitness",
            "app",
            "retail",
            "media",
            "youtube",
            "creación",
            "creador",
        ):
            if token in blob:
                return token
        return blob[:40]

    ranked = sorted(
        packages,
        key=lambda x: float(x.get("rank_score") or x.get("overall_score") or 0),
        reverse=True,
    )
    for p in ranked:
        asp = p.get("aspirational") if isinstance(p.get("aspirational"), dict) else {}
        local = bool(asp.get("is_local_turnaround") or is_local_turnaround_pattern(p))
        if local:
            if local_n >= max_local_turnaround:
                p = dict(p)
                p["diversity_penalized"] = True
                p["rank_score"] = float(p.get("rank_score") or 0) - 15.0
                p["diversity_note"] = "exceso de local_turnaround en el batch"
            else:
                local_n += 1
        mk = mech_key(p)
        mech_counts[mk] = mech_counts.get(mk, 0) + 1
        if mech_counts[mk] > max_similar_mechanism:
            p = dict(p)
            p["diversity_penalized"] = True
            p["rank_score"] = float(p.get("rank_score") or 0) - 8.0
            p["diversity_note"] = f"mecanismo repetido: {mk}"
        kept.append(p)
    return sorted(kept, key=lambda x: float(x.get("rank_score") or 0), reverse=True)


def title_looks_like_blog(title: str) -> bool:
    t = _low(title)
    bad_starts = (
        "desafiando ",
        "transformando ",
        "conviértete ",
        "conviertete ",
        "conquista ",
        "tu camino ",
        "el arte de ",
        "cómo ",
        "como ",
        "guía ",
        "guia ",
        "secretos ",
        "descubre ",
        "la revolución de ",
        "la revolucion de ",
        "red de transporte ",
        "revitaliza ",
    )
    if any(t.startswith(b) or t.startswith("pov: " + b) for b in bad_starts):
        return True
    if re.search(r"\b(ebook|curso|masterclass|linkedin|empoderas|revives comunidades)\b", t):
        return True
    if re.search(r"transforma(s|ndo)? el mundo", t):
        return True
    return False
