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


def empty_life_progression() -> dict[str, Any]:
    return {k: [] for k in LIFE_PROGRESSION_KEYS}


def empty_reward() -> dict[str, Any]:
    return {"type": "", "description": "", "story_beat": ""}


def _norm(v: Any) -> str:
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


def normalize_escalation_ladder(raw: Any) -> list[str]:
    if isinstance(raw, list):
        items = [_norm(x) for x in raw if _norm(x)]
    elif isinstance(raw, str) and raw.strip():
        items = [_norm(x) for x in re.split(r"[\n;]|→|->", raw) if _norm(x)]
    else:
        items = []
    # strip leading "1." numbers
    cleaned = []
    for it in items:
        it = re.sub(r"^\d+[\).:\-]\s*", "", it).strip()
        if it:
            cleaned.append(it)
    return cleaned[:8]


def normalize_life_progression(raw: Any) -> dict[str, list[str]]:
    out = empty_life_progression()
    if not isinstance(raw, dict):
        return out
    for k in LIFE_PROGRESSION_KEYS:
        v = raw.get(k)
        if isinstance(v, list):
            out[k] = [_norm(x) for x in v if _norm(x)][:6]
        elif isinstance(v, str) and v.strip():
            out[k] = [_norm(x) for x in re.split(r"[;\n|]", v) if _norm(x)][:6]
    return out


def normalize_rewards(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for row in raw:
        if isinstance(row, str) and row.strip():
            out.append({"type": "financial", "description": _norm(row), "story_beat": ""})
            continue
        if not isinstance(row, dict):
            continue
        typ = _low(row.get("type") or "financial")
        if typ not in REWARD_TYPES:
            # map spanish
            mapping = {
                "financiera": "financial",
                "dinero": "financial",
                "estilo_de_vida": "lifestyle",
                "familia": "family",
                "estatus": "status",
                "libertad": "freedom",
                "propiedad": "ownership",
                "experiencia": "experience",
                "relación": "relationship",
                "relacion": "relationship",
                "entorno": "environment",
            }
            typ = mapping.get(typ, "financial")
        desc = _norm(row.get("description") or row.get("text") or "")
        if not desc:
            continue
        out.append(
            {
                "type": typ,
                "description": desc,
                "story_beat": _norm(row.get("story_beat") or ""),
            }
        )
    # dedupe by description
    seen = set()
    uniq = []
    for r in out:
        key = r["description"].lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq[:8]


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
    scale = normalize_scale_ceiling(package.get("scale_ceiling"))
    blob = " ".join(
        [
            _low(package.get("premise")),
            _low(package.get("end_state")),
            _low(package.get("core_transformation")),
            _low((package.get("story_engine") or {}).get("endgame")),
            _low((package.get("story_engine") or {}).get("escalation_path")),
            " ".join(normalize_escalation_ladder(package.get("escalation_ladder"))),
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
    ladder = normalize_escalation_ladder(package.get("escalation_ladder"))
    life = normalize_life_progression(package.get("life_progression"))
    rewards = normalize_rewards(package.get("rewards"))
    scale = normalize_scale_ceiling(package.get("scale_ceiling"))
    contrast = normalize_start_end_contrast(package.get("start_end_contrast"))
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}

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
    if is_concrete_scale_language(engine.get("major_threat") or ""):
        biz_signals += 1
        evidence.append("amenaza competitiva de escala")
    if any(x in _low(engine.get("endgame")) for x in ("imperio", "exit", "venta", "nacional", "internacional", "franquicia")):
        biz_signals += 1
        evidence.append(f"endgame de negocio: {_norm(engine.get('endgame'))[:80]}")
    if len(ladder) >= 5:
        biz_signals += 1
        evidence.append(f"escalation_ladder con {len(ladder)} niveles")
    if scale in NATIONAL_PLUS:
        biz_signals += 2
        evidence.append(f"scale_ceiling={scale}")
    elif scale == "regional":
        biz_signals += 1
        evidence.append("scale_ceiling=regional")

    # Ownership / control cues
    blob_all = " ".join(
        [
            _low(package.get("premise")),
            _low(package.get("end_state")),
            _low(package.get("one_line_fantasy")),
            " ".join(ladder),
            " ".join(sum(life.values(), [])),
        ]
    )
    if any(x in blob_all for x in ("dueño", "dueña", "owner", "equity", "socio", "controlas", "posees", "adquieres")):
        biz_signals += 1
        evidence.append("fantasía de ownership/control")

    # Life fantasy signals
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

    # Contrast strength
    has_contrast = bool(contrast.get("start") and contrast.get("end") and len(contrast["start"]) > 20 and len(contrast["end"]) > 20)
    if has_contrast:
        life_signals += 1
        evidence.append("start_end_contrast presente")

    # Concrete end_state (not "successful business owner")
    end = _low(package.get("end_state"))
    vague_end = end in {"", "successful business owner", "dueño exitoso", "negocio exitoso", "emprendedor exitoso"}
    concrete_end = (not vague_end) and (
        bool(re.search(r"\$|\d", end))
        or any(x in end for x in ("empleados", "locales", "países", "paises", "patrimonio", "valuación", "valuacion", "edad", "age"))
    )
    if concrete_end:
        life_signals += 1
        evidence.append("end_state concreto")
    else:
        evidence.append("end_state débil/abstracto")

    # Luxury filler penalty (not ban)
    lux = [x for x in _LUXURY_FILLER if x in blob_all]
    if lux and len(reward_types) <= 2:
        evidence.append("lujo genérico sin diversidad de rewards: " + ", ".join(lux[:3]))

    # Scores 1–10
    aspirational_strength = max(1, min(10, 2 + biz_signals + life_signals // 2))
    life_transformation = max(1, min(10, 1 + life_signals + (2 if has_contrast and concrete_end else 0)))
    scale_potential = SCALE_RANK.get(scale, 3)
    if len(ladder) >= 7:
        scale_potential = min(10, scale_potential + 1)
    if len(ladder) < 4:
        scale_potential = max(1, scale_potential - 2)
    reward_density = max(1, min(10, len(rewards) * 2 + len(reward_types)))

    # Button test proxy
    would_press = (
        scale in NATIONAL_PLUS
        and life_transformation >= 6
        and aspirational_strength >= 6
        and len(rewards) >= 3
        and concrete_end
    ) or (
        life_transformation >= 8 and aspirational_strength >= 7 and has_contrast and len(rewards) >= 3
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

    # Gates: national+ preferred; regional/local only with extraordinary life fantasy
    has_aspirational_transformation = (
        aspirational_strength >= 6
        and life_transformation >= 6
        and (
            scale in NATIONAL_PLUS
            or (scale == "regional" and life_transformation >= 8)
            or (scale == "local" and life_transformation >= 9 and would_press)
        )
    )
    has_life_progression = filled_stages >= 3 and concrete_end
    has_scale_progression = len(ladder) >= 5 and scale_potential >= 5
    has_visible_rewards = len(rewards) >= 3 and len(reward_types) >= 2

    if scale == "local" and life_transformation < 9:
        has_aspirational_transformation = False
        evidence.append("techo local sin life fantasy extraordinaria")

    return {
        "business_fantasy": {
            "score": max(1, min(10, 1 + biz_signals)),
            "evidence": [e for e in evidence if "negocio" in e or "crecimiento" in e or "scale" in e or "ownership" in e or "ladder" in e or "amenaza" in e or "endgame" in e][
                :6
            ]
            or evidence[:3],
        },
        "life_fantasy": {
            "score": max(1, min(10, 1 + life_signals)),
            "evidence": [e for e in evidence if "vida" in e or "reward" in e or "life_" in e or "contrast" in e or "end_state" in e][:6]
            or evidence[:3],
        },
        "aspirational_score": aspirational_score,
        "aspirational_evidence": evidence[:10],
        "aspirational_strength": aspirational_strength,
        "life_transformation": life_transformation,
        "scale_potential": scale_potential,
        "reward_density": reward_density,
        "scale_ceiling": scale,
        "would_press_button": would_press,
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
            "taller",
            "franquic",
            "marketplace",
            "logíst",
            "logistic",
            "estadio",
            "motel",
            "hotel",
            "fitness",
            "app",
            "retail",
            "media",
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
        "la revolución de ",
        "la revolucion de ",
    )
    if any(t.startswith(b) or t.startswith("pov: " + b) for b in bad_starts):
        return True
    if re.search(r"\b(ebook|curso|masterclass|linkedin)\b", t):
        return True
    return False
