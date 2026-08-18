"""Eligibility gates + weighted overall scoring for Check Concept Engine V2/1.6."""
from __future__ import annotations

from typing import Any

from src.documentary.formats.check_als.aspirational import (
    apply_batch_diversity,
    evaluate_aspirational,
    title_looks_like_blog,
)
from src.documentary.formats.check_als.editorial import (
    ELIGIBILITY_GATES,
    MAX_LOCAL_TURNAROUND_IN_TOP,
    SPECIFICITY_THRESHOLD,
    WEIGHTS,
)
from src.documentary.formats.check_als.validators import (
    ConcreteMechanismValidator,
    count_cliches,
    estimate_filmability,
    evaluate_coherence_v2,
    extract_specificity_signals,
    repair_category,
    story_engine_strength,
    validate_category,
    validate_hook,
    validate_open_loops,
    validate_story_question,
    validate_thumbnail,
    validate_titles,
    validate_world_seeds,
)


def _clamp(n: float) -> int:
    try:
        v = int(round(float(n)))
    except (TypeError, ValueError):
        v = 5
    return max(1, min(10, v))


def evaluate_eligibility(package: dict[str, Any]) -> dict[str, Any]:
    """Layer A — hard gates. Ineligible concepts cannot rank #1."""
    mech = ConcreteMechanismValidator.evaluate(package)
    spec = extract_specificity_signals(package)
    hook = validate_hook(package.get("hook"))
    seeds = validate_world_seeds(package.get("world_seeds") if isinstance(package.get("world_seeds"), dict) else {})
    cat = validate_category(package)
    if not cat["pass"] and cat.get("suggested"):
        package["story_category"] = cat["suggested"]
        cat = validate_category(package)
        cat["repaired"] = True
    elif not cat["pass"]:
        package["story_category"] = repair_category(package)
        cat = validate_category(package)
        cat["repaired"] = True

    coh = evaluate_coherence_v2(package)
    sq = validate_story_question(package.get("central_story_question"))
    loops = validate_open_loops(package.get("open_loops"))
    thumb = validate_thumbnail(package.get("thumbnail_concept") if isinstance(package.get("thumbnail_concept"), dict) else {})
    titles = validate_titles(
        str(package.get("title") or ""),
        list(package.get("title_options") or []),
    )
    # Drop blog/LinkedIn titles
    if titles.get("options"):
        cleaned = []
        for opt in titles["options"]:
            text = str(opt.get("text") if isinstance(opt, dict) else opt)
            if title_looks_like_blog(text):
                continue
            cleaned.append(opt if isinstance(opt, dict) else {"text": text})
        if cleaned:
            titles["options"] = cleaned
            if title_looks_like_blog(str(titles.get("title") or "")):
                titles["title"] = str((cleaned[0].get("text") if isinstance(cleaned[0], dict) else cleaned[0]))
            titles["pass"] = True
        else:
            titles["pass"] = False
    if titles.get("title"):
        package["title"] = titles["title"]
    if titles.get("options"):
        package["title_options"] = titles["options"]

    asp = evaluate_aspirational(package)
    # Write normalized aspirational fields back onto package for persistence
    norm = asp.get("normalized") or {}
    package["escalation_ladder"] = norm.get("escalation_ladder") or package.get("escalation_ladder") or []
    package["life_progression"] = norm.get("life_progression") or package.get("life_progression") or {}
    package["rewards"] = norm.get("rewards") or package.get("rewards") or []
    package["start_end_contrast"] = norm.get("start_end_contrast") or package.get("start_end_contrast") or {}
    package["scale_ceiling"] = norm.get("scale_ceiling") or package.get("scale_ceiling") or "local"
    package["aspirational"] = asp
    package["aspirational_score"] = asp.get("aspirational_score")
    package["aspirational_evidence"] = asp.get("aspirational_evidence")
    package["business_fantasy"] = asp.get("business_fantasy")
    package["life_fantasy"] = asp.get("life_fantasy")

    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    has_engine = sum(1 for v in engine.values() if str(v or "").strip()) >= 10
    asp_gates = asp.get("gates") or {}

    gates = {
        "has_specific_opportunity": mech["has_specific_opportunity"],
        "has_specific_mechanism": mech["has_specific_mechanism"],
        "has_growth_engine": mech["has_growth_engine"],
        "has_major_threat": mech["has_major_threat"],
        "has_stakes": mech["has_stakes"],
        "has_story_question": sq["pass"],
        "has_valid_hook": hook["pass"],
        "has_valid_world_seeds": seeds["pass"],
        "category_matches": cat["pass"],
        "coherence_pass": coh["pass"],
        "has_story_engine": has_engine and mech["pass"],
        "specificity_ok": spec["ok"],
        "thumbnail_concrete": thumb["pass"],
        "has_open_loops": loops["pass"],
        "has_first_action": mech.get("has_first_action", False),
        "titles_ok": titles["pass"] and not title_looks_like_blog(str(package.get("title") or "")),
        "has_aspirational_transformation": bool(asp_gates.get("has_aspirational_transformation")),
        "has_life_progression": bool(asp_gates.get("has_life_progression")),
        "has_scale_progression": bool(asp_gates.get("has_scale_progression")),
        "has_visible_rewards": bool(asp_gates.get("has_visible_rewards")),
    }
    critical = (
        "has_specific_opportunity",
        "has_specific_mechanism",
        "has_growth_engine",
        "has_major_threat",
        "has_stakes",
        "has_story_question",
        "has_valid_hook",
        "has_valid_world_seeds",
        "category_matches",
        "coherence_pass",
        "has_story_engine",
        "specificity_ok",
        "thumbnail_concrete",
        "has_open_loops",
        "has_first_action",
        "has_aspirational_transformation",
        "has_life_progression",
        "has_scale_progression",
        "has_visible_rewards",
    )
    failed = [k for k in critical if not gates.get(k)]
    reasons: list[str] = []
    if mech["missing"]:
        reasons.append(f"mechanism missing: {', '.join(mech['missing'])}")
    if mech["vague"]:
        reasons.append(f"mechanism vague: {', '.join(mech['vague'])}")
    if not hook["pass"]:
        reasons.append("hook: " + "; ".join(hook["reasons"]))
    if not seeds["pass"]:
        reasons.append("world_seeds missing: " + ", ".join(seeds["missing"]))
    if not cat["pass"]:
        reasons.append("category: " + str(cat.get("reason") or "mismatch"))
    if not coh["pass"]:
        reasons.append("coherence: " + (coh.get("notes") or "fail"))
    if not sq["pass"]:
        reasons.append(sq.get("reason") or "story question")
    if not loops["pass"]:
        reasons.append(loops.get("reason") or "open_loops")
    if not thumb["pass"]:
        reasons.append("thumbnail: " + "; ".join(thumb["reasons"]))
    if not spec["ok"]:
        reasons.append(f"specificity {spec['score']} < {SPECIFICITY_THRESHOLD}")
    if titles.get("rejected"):
        reasons.append("bad titles removed: " + "; ".join(titles["rejected"][:3]))
    if not gates["titles_ok"]:
        reasons.append("título con tono blog/curso/LinkedIn")
    if not gates["has_aspirational_transformation"]:
        reasons.append("aspirational: transformación no suficientemente deseable / techo demasiado bajo")
    if not gates["has_life_progression"]:
        reasons.append("life_progression incompleta o end_state abstracto")
    if not gates["has_scale_progression"]:
        reasons.append("escalation_ladder corta o scale_potential bajo")
    if not gates["has_visible_rewards"]:
        reasons.append("rewards insuficientes o poco diversos")

    eligible = len(failed) == 0
    return {
        "eligible": eligible,
        "gates": {k: bool(gates.get(k)) for k in ELIGIBILITY_GATES},
        "gates_extra": gates,
        "failed_gates": failed,
        "reasons": reasons,
        "mechanism": mech,
        "specificity": spec,
        "hook": hook,
        "world_seeds": seeds,
        "category": cat,
        "coherence": coh,
        "story_question": sq,
        "open_loops": loops,
        "thumbnail": thumb,
        "titles": titles,
        "aspirational": asp,
    }


def score_concept_package(package: dict[str, Any], *, llm_hints: dict[str, Any] | None = None) -> dict[str, Any]:
    """Layer B — weighted score. overall ALWAYS in code. Decompressed via 2-decimal + signal variance."""
    hints_in = llm_hints if isinstance(llm_hints, dict) else {}
    hints: dict[str, Any] = {}
    subjective = {"curiosity", "fantasy_strength", "thumbnail_potential", "originality"}
    for k, v in hints_in.items():
        if k not in subjective:
            continue
        if isinstance(v, dict) and "score" in v:
            hints[k] = v.get("score")
        elif not isinstance(v, dict):
            hints[k] = v

    spec = extract_specificity_signals(package)
    strength = story_engine_strength(package)
    film = estimate_filmability(package)
    cliches = count_cliches(package)
    asp = package.get("aspirational") if isinstance(package.get("aspirational"), dict) else evaluate_aspirational(package)

    def hint(key: str, default: int) -> int:
        if key not in hints or hints.get(key) in (None, "", 0):
            return default
        return _clamp(hints.get(key, default))

    # Deterministic curiosity/fantasy spreads to avoid LLM clustering at 8.0
    curiosity_base = 4 + min(4, len(package.get("open_loops") or [])) + (1 if package.get("central_story_question") else 0)
    curiosity = hint("curiosity", max(3, min(9, curiosity_base)))
    fantasy_base = 3 + int(asp.get("life_transformation") or 5) // 2
    fantasy_strength = hint("fantasy_strength", max(3, min(9, fantasy_base)))

    originality = hint("originality", 7)
    if cliches:
        penalty = min(4, len(cliches) + (0 if spec["score"] >= 8 else 1))
        originality = max(1, originality - penalty)
    elif originality <= 2 and "originality" not in hints_in:
        originality = 7

    scores = {
        "specificity": spec["score"],
        "story_engine_strength": strength["score"],
        "aspirational_strength": int(asp.get("aspirational_strength") or 5),
        "life_transformation": int(asp.get("life_transformation") or 5),
        "scale_potential": int(asp.get("scale_potential") or 3),
        "reward_density": int(asp.get("reward_density") or 3),
        "curiosity": curiosity,
        "fantasy_strength": fantasy_strength,
        "filmability": film["score"],
        "thumbnail_potential": hint("thumbnail_potential", 6),
        "originality": originality,
    }

    evidence = {
        "specificity": {"score": scores["specificity"], "evidence": spec["evidence"]},
        "story_engine_strength": {"score": scores["story_engine_strength"], "evidence": strength["evidence"]},
        "aspirational_strength": {
            "score": scores["aspirational_strength"],
            "evidence": list(asp.get("aspirational_evidence") or [])[:6],
        },
        "life_transformation": {
            "score": scores["life_transformation"],
            "evidence": list((asp.get("life_fantasy") or {}).get("evidence") or [])[:5],
        },
        "scale_potential": {
            "score": scores["scale_potential"],
            "evidence": [f"scale_ceiling={asp.get('scale_ceiling')}", f"ladder_n={len(package.get('escalation_ladder') or [])}"],
        },
        "reward_density": {
            "score": scores["reward_density"],
            "evidence": [f"{len(package.get('rewards') or [])} rewards"],
        },
        "filmability": {"score": scores["filmability"], "evidence": film["evidence"]},
        "originality": {
            "score": scores["originality"],
            "evidence": ([f"cliché: {c}" for c in cliches] or ["sin cliché mayor"]),
        },
        "curiosity": {"score": scores["curiosity"], "evidence": _hint_evidence(hints_in, "curiosity")},
        "fantasy_strength": {"score": scores["fantasy_strength"], "evidence": _hint_evidence(hints_in, "fantasy_strength")},
        "thumbnail_potential": {
            "score": scores["thumbnail_potential"],
            "evidence": _hint_evidence(hints_in, "thumbnail_potential"),
        },
    }

    # Keep 2-decimal display; add micro-spread from field richness so ranking separates
    # near-ties without fake precision theater
    richness = (
        len(str(package.get("premise") or "")) // 120
        + len(package.get("escalation_ladder") or [])
        + len(package.get("rewards") or [])
        + int(asp.get("aspirational_strength") or 0)
        + int(asp.get("scale_potential") or 0)
        + int(scores.get("specificity") or 0)
        + int(scores.get("story_engine_strength") or 0)
    )
    raw_overall = 0.0
    for k, w in WEIGHTS.items():
        raw_overall += float(scores.get(k, 5)) * float(w)
    # Sub-point spread from richness (±0.35 range typical) — not artificial decimals on identical inputs
    raw_overall = raw_overall + min(0.35, richness * 0.01) - 0.1
    overall = round(raw_overall, 2)

    return {
        "scores": scores,
        "score_evidence": evidence,
        "overall_score": overall,
        "overall_raw": raw_overall,
        "weights": dict(WEIGHTS),
        "aspirational_score": asp.get("aspirational_score"),
    }


def apply_scoring(package: dict[str, Any]) -> dict[str, Any]:
    """Mutate package with eligibility + scores. Never trusts LLM overall_score."""
    elig = evaluate_eligibility(package)
    scored = score_concept_package(package, llm_hints=package.get("llm_score_hints"))
    package["scores"] = scored["scores"]
    package["score_evidence"] = scored["score_evidence"]
    package["overall_score"] = scored["overall_score"] if elig["eligible"] else min(scored["overall_score"], 4.9)
    package["aspirational_score"] = scored.get("aspirational_score")
    package["eligible"] = elig["eligible"]
    package["eligibility"] = {
        "eligible": elig["eligible"],
        "gates": elig["gates"],
        "failed_gates": elig["failed_gates"],
        "reasons": elig["reasons"],
    }
    package["coherence"] = {
        "pass": elig["coherence"]["pass"],
        "title_matches_thumbnail": elig["coherence"].get("title_matches_thumbnail", False),
        "hook_fulfills_promise": elig["coherence"].get("hook_fulfills_promise", False),
        "transformation_aligned": elig["coherence"].get("transformation_aligned", False),
        "checks": elig["coherence"].get("checks", {}),
        "notes": elig["coherence"].get("notes", ""),
        "aux_lexical_title_thumb": elig["coherence"].get("aux_lexical_title_thumb", False),
    }
    package["specificity_score"] = scored["scores"]["specificity"]
    package["filmability"] = scored["scores"]["filmability"]
    # Rank uses higher precision + aspirational bonus for separation
    asp_bonus = float(package.get("aspirational_score") or 0) * 0.01
    package["rank_score"] = (
        (package["overall_score"] + asp_bonus) if elig["eligible"] else package["overall_score"] - 100.0
    )
    return package


def finalize_ranked_batch(packages: list[dict[str, Any]], target: int) -> dict[str, Any]:
    generated = [apply_scoring(dict(p)) for p in packages]
    rejected = [p for p in generated if not p.get("eligible")]
    eligible = [p for p in generated if p.get("eligible")]
    diversified = apply_batch_diversity(eligible, max_local_turnaround=MAX_LOCAL_TURNAROUND_IN_TOP)
    eligible_ranked = diversified[:target]
    return {
        "generated": generated,
        "rejected": rejected,
        "eligible": eligible,
        "eligible_ranked": eligible_ranked,
        "counts": {
            "generated": len(generated),
            "rejected": len(rejected),
            "eligible": len(eligible),
            "returned": min(target, len(eligible_ranked)),
        },
    }


def _hint_evidence(hints: dict[str, Any], key: str) -> list[str]:
    v = hints.get(key)
    if isinstance(v, dict):
        ev = v.get("evidence")
        if isinstance(ev, list):
            return [str(x) for x in ev][:4]
        if v.get("evidence"):
            return [str(v.get("evidence"))]
    if key in hints:
        return [f"partial hint {key}={hints.get(key)}"]
    return [f"derived_{key}"]
