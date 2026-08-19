"""Eligibility gates + weighted overall scoring for Check Concept Engine V2/1.6."""
from __future__ import annotations

from typing import Any

from src.documentary.formats.check_als.aspirational import (
    apply_batch_diversity,
    evaluate_aspirational,
    fill_escalation_ladder,
    has_community_savior_bias,
    named_antagonist,
    synthesize_hook,
    title_looks_like_blog,
    unique_money_mentions,
)
from src.documentary.formats.check_als.editorial import (
    ELIGIBILITY_GATES,
    MAX_LOCAL_TURNAROUND_IN_TOP,
    SPECIFICITY_THRESHOLD,
    WEIGHTS,
)
from src.documentary.formats.check_als.quality import (
    combine_overall,
    compute_penalties,
    evaluate_progression_plausibility,
    evaluate_story_quality,
    fill_thumbnail_gaps,
    has_visualizable_object,
    hook_opening_key,
    hooks_structurally_similar,
    needs_specific_physical_object,
    repair_scale_consistency,
    select_diverse_top,
    strip_ad_thumbnail_text,
    title_is_truthful,
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
    if not hook["pass"]:
        synthesized = synthesize_hook(package)
        retry = validate_hook(synthesized)
        if retry["pass"]:
            package["hook"] = synthesized
            hook = retry
            hook = {**hook, "repaired": True}
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
    fill_thumbnail_gaps(package)
    if isinstance(package.get("thumbnail_concept"), dict):
        package["thumbnail_concept"] = strip_ad_thumbnail_text(package["thumbnail_concept"])
    thumb = validate_thumbnail(package.get("thumbnail_concept") if isinstance(package.get("thumbnail_concept"), dict) else {})
    if isinstance(thumb.get("thumbnail"), dict):
        package["thumbnail_concept"] = thumb["thumbnail"]
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

    title_truth = title_is_truthful(package)
    object_ok = (not needs_specific_physical_object(package)) or has_visualizable_object(package)

    asp = evaluate_aspirational(package)
    # Write normalized aspirational fields back onto package for persistence
    norm = asp.get("normalized") or {}
    package["escalation_ladder"] = norm.get("escalation_ladder") or fill_escalation_ladder(package)
    package["life_progression"] = norm.get("life_progression") or package.get("life_progression") or {}
    package["rewards"] = list(norm.get("rewards") or [])
    package["start_end_contrast"] = norm.get("start_end_contrast") or package.get("start_end_contrast") or {}
    package["scale_ceiling"] = norm.get("scale_ceiling") or package.get("scale_ceiling") or "local"
    repair_scale_consistency(package)
    package["aspirational"] = asp
    package["aspirational_score"] = asp.get("aspirational_score")
    package["aspirational_evidence"] = asp.get("aspirational_evidence")
    package["life_progression_completeness"] = asp.get("life_progression_completeness")
    # Keep editorial copy separate from the evaluation object
    if not str(package.get("business_fantasy") or "").strip() or isinstance(package.get("business_fantasy"), dict):
        ev = asp.get("business_fantasy") if isinstance(asp.get("business_fantasy"), dict) else {}
        package["business_fantasy"] = "; ".join(ev.get("evidence") or [])[:280]
    if not str(package.get("life_fantasy") or "").strip() or isinstance(package.get("life_fantasy"), dict):
        ev = asp.get("life_fantasy") if isinstance(asp.get("life_fantasy"), dict) else {}
        package["life_fantasy"] = "; ".join(ev.get("evidence") or [])[:280]
    package["business_fantasy_eval"] = asp.get("business_fantasy")
    package["life_fantasy_eval"] = asp.get("life_fantasy")

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
        "title_truthful": bool(title_truth.get("pass")),
        "specific_object_ok": bool(object_ok),
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
        "title_truthful",
        "specific_object_ok",
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
    if not title_truth.get("pass"):
        reasons.append("título no respaldado: " + str(title_truth.get("reason") or ""))
    if not object_ok:
        reasons.append("producto físico sin objeto visualizable")

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
    """Layer B — weighted score. overall ALWAYS in code. LLM hints are notes only (no clustering)."""
    hints_in = llm_hints if isinstance(llm_hints, dict) else {}

    spec = extract_specificity_signals(package)
    strength = story_engine_strength(package)
    film = estimate_filmability(package)
    cliches = count_cliches(package)
    asp = package.get("aspirational") if isinstance(package.get("aspirational"), dict) else evaluate_aspirational(package)
    engine = package.get("story_engine") if isinstance(package.get("story_engine"), dict) else {}
    thumb = package.get("thumbnail_concept") if isinstance(package.get("thumbnail_concept"), dict) else {}

    # Deterministic curiosity from actual loops/question/hook — never the LLM's 8.0
    loops = [str(x) for x in (package.get("open_loops") or []) if str(x).strip()]
    q = str(package.get("central_story_question") or "")
    hook_len = len(str(package.get("hook") or ""))
    curiosity = 3.5 + min(3.0, len(loops) * 0.65)
    if "?" in q and len(q) > 48:
        curiosity += 1.1
    if hook_len >= 140:
        curiosity += 0.7
    elif hook_len < 90:
        curiosity -= 0.6
    curiosity = max(1, min(10, round(curiosity)))

    fantasy_strength = max(
        1,
        min(10, round(2 + float(asp.get("life_transformation") or 5) * 0.55 + float(asp.get("aspirational_strength") or 5) * 0.25)),
    )

    thumb_filled = sum(1 for k in ("main_visual", "key_object", "central_contrast", "environment") if len(str(thumb.get(k) or "")) > 24)
    thumbnail_potential = max(1, min(10, 3 + thumb_filled + (1 if str(thumb.get("thumbnail_prompt") or "").startswith("2D") else 0)))

    originality = 7.5
    if cliches:
        originality -= min(4, len(cliches) + (0 if spec["score"] >= 8 else 1))
    if has_community_savior_bias(package):
        originality -= 1.4
    if not named_antagonist(str(engine.get("major_threat") or "")):
        originality -= 0.6
    if unique_money_mentions(package) <= 1:
        originality -= 0.4
    originality = max(1, min(10, round(originality)))

    # Specificity: complete packages should not all sit at 10
    spec_bonus = 0
    if unique_money_mentions(package) >= 2:
        spec_bonus += 1
    if named_antagonist(str(engine.get("major_threat") or "")):
        spec_bonus += 1
    if int(asp.get("end_state_facts") or 0) >= 4:
        spec_bonus += 1
    spec_score = max(1, min(10, min(8, int(spec.get("signal_count") or 0)) + spec_bonus))

    se_concrete = int(strength.get("concrete_fields") or 0)
    se_score = max(1, min(10, round(4.2 + se_concrete * 0.32)))

    film_score = int(film["score"])
    if len(package.get("escalation_ladder") or []) >= 7:
        film_score = min(10, film_score + 1)

    quality = evaluate_story_quality(package)
    plaus = evaluate_progression_plausibility(package)

    scores = {
        "specificity": spec_score,
        "story_engine_strength": se_score,
        "aspirational_strength": int(asp.get("aspirational_strength") or 5),
        "life_transformation": int(asp.get("life_transformation") or 5),
        "scale_potential": int(asp.get("scale_potential") or 3),
        "reward_density": int(asp.get("reward_density") or 3),
        "curiosity": int(curiosity),
        "fantasy_strength": int(fantasy_strength),
        "filmability": film_score,
        "thumbnail_potential": int(thumbnail_potential),
        "originality": int(originality),
        "mechanism_distinctiveness": int(quality["mechanism_distinctiveness"]),
        "sceneability": int(quality["sceneability"]),
        "conflict_specificity": int(quality["conflict_specificity"]),
        "causal_chain_strength": int(quality["causal_chain_strength"]),
        "progression_plausibility": int(plaus["progression_plausibility"]),
    }

    evidence = {
        "specificity": {"score": scores["specificity"], "evidence": spec["evidence"] + ([f"bonus={spec_bonus}"] if spec_bonus else [])},
        "story_engine_strength": {"score": scores["story_engine_strength"], "evidence": strength["evidence"]},
        "aspirational_strength": {
            "score": scores["aspirational_strength"],
            "evidence": list(asp.get("aspirational_evidence") or [])[:6],
        },
        "life_transformation": {
            "score": scores["life_transformation"],
            "evidence": (list((asp.get("life_fantasy") or {}).get("evidence") or [])[:3] or [])
            + [f"completeness={asp.get('life_progression_completeness')}"],
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
        "curiosity": {"score": scores["curiosity"], "evidence": [f"{len(loops)} open_loops", f"hook_len={hook_len}"]},
        "fantasy_strength": {"score": scores["fantasy_strength"], "evidence": list(asp.get("aspirational_evidence") or [])[:3]},
        "thumbnail_potential": {
            "score": scores["thumbnail_potential"],
            "evidence": [f"{thumb_filled}/4 thumbnail fields concrete"],
        },
        "mechanism_distinctiveness": {"score": scores["mechanism_distinctiveness"], "evidence": quality["evidence"]["mechanism_distinctiveness"]},
        "sceneability": {"score": scores["sceneability"], "evidence": quality["evidence"]["sceneability"]},
        "conflict_specificity": {"score": scores["conflict_specificity"], "evidence": quality["evidence"]["conflict_specificity"]},
        "progression_plausibility": {"score": scores["progression_plausibility"], "evidence": plaus["reasons"][:3]},
    }

    penalties = compute_penalties(package)
    mixed = combine_overall(scores, penalties=penalties)
    residual = min(
        0.28,
        unique_money_mentions(package) * 0.04
        + int(asp.get("end_state_facts") or 0) * 0.03
        + len(str(package.get("premise") or "")) / 2500.0,
    )
    if has_community_savior_bias(package):
        residual -= 0.35
    overall = round(max(1.0, min(10.0, mixed["overall_score"] + residual)), 2)

    return {
        "scores": scores,
        "score_evidence": evidence,
        "overall_score": overall,
        "overall_raw": mixed["linear"],
        "ranking": mixed,
        "penalties": penalties,
        "weights": dict(WEIGHTS),
        "aspirational_score": asp.get("aspirational_score"),
        "llm_hints_ignored": sorted(str(k) for k in hints_in.keys()) if hints_in else [],
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
    package["penalties"] = scored.get("penalties") or {}
    package["ranking"] = scored.get("ranking") or {}
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
    _repair_duplicate_hooks(generated)
    generated = [apply_scoring(dict(p)) if p.get("hook_batch_repaired") else p for p in generated]
    rejected = [p for p in generated if not p.get("eligible")]
    eligible = [p for p in generated if p.get("eligible")]
    diversified = apply_batch_diversity(eligible, max_local_turnaround=MAX_LOCAL_TURNAROUND_IN_TOP)
    eligible_ranked = select_diverse_top(diversified, target)
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


def _repair_duplicate_hooks(packages: list[dict[str, Any]]) -> None:
    seen: list[str] = []
    for p in packages:
        hook = str(p.get("hook") or "")
        if hook and any(hooks_structurally_similar(hook, prev) for prev in seen):
            alt = synthesize_hook(p)
            if alt and hook_opening_key(alt) != hook_opening_key(hook):
                p["hook"] = alt
                p["hook_batch_repaired"] = True
                hook = alt
        if hook:
            seen.append(hook)


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
