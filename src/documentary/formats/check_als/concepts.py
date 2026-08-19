"""Check ALS Concept Engine V2: seed → expand → validate → score → rank."""
from __future__ import annotations

import json
import os
import random
import re
import time
import uuid
from copy import deepcopy
from typing import Any

from src.saas_creative_profile import merge_profile_disk, parse_llm_json_object
from src.documentary.formats.check_als.editorial import (
    DEFAULT_CATEGORIES,
    EXPAND_SYSTEM,
    FANTASY_DIVERSITY,
    HOOK_REGEN_SYSTEM,
    MECHANISM_DIVERSITY,
    PACKAGING_FROM_STORY_SYSTEM,
    SEED_SYSTEM,
    STORY_CORE_SYSTEM,
    STORY_ENGINE_KEYS,
    STORY_SHAPES,
    TITLE_SCORE_KEYS,
    WEIGHTS,
)
from src.documentary.formats.check_als.aspirational import (
    empty_life_progression,
    fill_escalation_ladder,
    fill_rewards_if_thin,
    normalize_escalation_ladder,
    normalize_life_progression,
    normalize_rewards,
    normalize_scale_ceiling,
    normalize_start_end_contrast,
)
from src.documentary.formats.check_als.quality import (
    fill_thumbnail_gaps,
    needs_ceiling_repair,
    repair_scale_consistency,
    select_diverse_top,
    strip_ad_thumbnail_text,
)
from src.documentary.formats.check_als.scoring import apply_scoring, finalize_ranked_batch
from src.documentary.formats.check_als.story_discovery import (
    classify_story_shape,
    hook_needs_regen,
    normalize_story_core,
    normalize_story_shape,
    normalize_story_spine,
    packaging_score,
    score_story,
    select_diverse_stories,
    story_core_to_engine,
    structural_template,
    synthesize_hook_from_core,
    validate_story,
)
from src.documentary.formats.check_als.validators import (
    parse_world_seeds,
    validate_titles,
)
from src.documentary.formats.check_als.fixtures_es import CONCRETE_FIXTURES as _CONCRETE_FIXTURES

REGENERABLE_PARTS = ("concept", "title", "thumbnail", "hook")


def empty_thumbnail_concept() -> dict[str, Any]:
    return {
        "main_visual": "",
        "protagonist_state": "",
        "environment": "",
        "central_contrast": "",
        "emotion": "",
        "key_object": "",
        "composition": "",
        "camera": "",
        "lighting": "",
        "background": "",
        "text_if_any": "",
        "thumbnail_prompt": "",
    }


def empty_story_engine() -> dict[str, Any]:
    return {k: "" for k in STORY_ENGINE_KEYS}


def empty_title_option() -> dict[str, Any]:
    return {
        "text": "",
        "scores": {k: 0 for k in TITLE_SCORE_KEYS},
        "overall_score": 0.0,
    }


def empty_world_seeds() -> dict[str, Any]:
    return {
        "starting_age": None,
        "starting_cash": "",
        "starting_location": "",
        "starting_status": "",
        "target_outcome": "",
        "business_or_career_type": "",
        "timeline_scale": "",
    }


def empty_concept_package() -> dict[str, Any]:
    from src.documentary.formats.check_als.editorial import (
        CONTENT_LANGUAGE,
        IMAGE_PROMPT_LANGUAGE,
    )

    return {
        "id": "",
        "content_format": "check_als",
        "language": CONTENT_LANGUAGE,
        "content_language": CONTENT_LANGUAGE,
        "image_prompt_language": IMAGE_PROMPT_LANGUAGE,
        "premise": "",
        "title": "",
        "title_options": [],
        "one_line_fantasy": "",
        "starting_state": "",
        "end_state": "",
        "core_transformation": "",
        "story_category": "",
        "ending_direction": "victory",
        "story_engine": empty_story_engine(),
        "central_story_question": "",
        "open_loops": [],
        "scores": {k: 0 for k in WEIGHTS},
        "score_evidence": {},
        "overall_score": 0.0,
        "specificity_score": 0,
        "filmability": 0,
        "eligible": False,
        "eligibility": {},
        "thumbnail_concept": empty_thumbnail_concept(),
        "hook": "",
        "hook_seconds_target": [15, 30],
        "world_seeds": empty_world_seeds(),
        "coherence": {
            "title_matches_thumbnail": False,
            "hook_fulfills_promise": False,
            "transformation_aligned": False,
            "notes": "",
            "pass": False,
        },
        "escalation_ladder": [],
        "life_progression": empty_life_progression(),
        "rewards": [],
        "scale_ceiling": "",
        "start_end_contrast": {"start": "", "end": "", "one_line": ""},
        "business_fantasy": "",
        "life_fantasy": "",
        "aspirational_score": 0.0,
        "aspirational_evidence": [],
        "story_core": {},
        "story_spine": "",
        "story_score": 0.0,
        "story_scores": {},
        "story_eligible": False,
        "packaging_score": 0.0,
        "packaging_scores": {},
    }


def generate_concept_packages(
    profile: dict[str, Any] | None,
    *,
    prior_videos: list[dict[str, Any]] | None = None,
    count: int = 5,
    categories: list[str] | None = None,
    use_llm: bool = True,
    raw_seed_count: int | None = None,
    story_select_count: int | None = None,
) -> list[dict[str, Any]]:
    """Public API: return up to `count` eligible ranked concepts (may be fewer)."""
    result = generate_concepts_v2(
        profile,
        prior_videos=prior_videos,
        count=count,
        categories=categories,
        use_llm=use_llm,
        raw_seed_count=raw_seed_count,
        story_select_count=story_select_count,
    )
    return list(result.get("eligible_ranked") or [])[:count]


def generate_concepts_v2(
    profile: dict[str, Any] | None,
    *,
    prior_videos: list[dict[str, Any]] | None = None,
    count: int = 10,
    categories: list[str] | None = None,
    use_llm: bool = True,
    raw_seed_count: int | None = None,
    max_rounds: int = 8,
    story_select_count: int | None = None,
    discovery_only: bool = False,
) -> dict[str, Any]:
    """
    Fase 1.7 pipeline:
    raw seeds → story core/spine → validate → story score → top ~15 →
    packaging → repair → semantic diversity → top N.
    Story score dominates ranking. Packaging never buries a great film.
    """
    p = merge_profile_disk(profile)
    cats = _categories(p, categories)
    prior = list(prior_videos or [])
    target = max(1, int(count))
    seed_target = int(raw_seed_count) if raw_seed_count is not None else (40 if target >= 10 else max(target * 4, 16))
    shortlist_n = int(story_select_count) if story_select_count is not None else (15 if target >= 10 else min(15, max(target + 3, 8)))
    stats: dict[str, Any] = {
        "raw_requested": seed_target,
        "raw_generated": 0,
        "raw_unique": 0,
        "story_cores_generated": 0,
        "story_cores_rejected": 0,
        "story_cores_eligible": 0,
        "story_shortlist": 0,
        "packaging_attempted": 0,
        "packaging_repaired": 0,
        "packaging_failed": 0,
        "semantic_duplicates_removed": 0,
        "llm_calls": 0,
        "retries": 0,
        "llm_failures": 0,
        "expansion_attempts": 0,
        "expansion_success": 0,
        "expansion_failed": 0,
        "replacement_seeds": 0,
    }

    if not use_llm or not (os.getenv("OPENAI_API_KEY") or "").strip():
        fixtures = [_fixture_package(i, cats) for i in range(max(seed_target, target))]
        out = _finalize_batch(fixtures, target)
        out["orchestration"] = {**stats, "expansion_success": len(fixtures), "raw_unique": len(fixtures)}
        out["story_shortlist"] = []
        return out

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    seeds = _collect_unique_seeds(client, model, p, cats, prior, seed_target, max_rounds, stats)
    stats["raw_unique"] = len(seeds)

    stories: list[dict[str, Any]] = []
    for idx, seed in enumerate(seeds, 1):
        print(f"[v2] story core {idx}/{len(seeds)}", flush=True)
        story = _discover_story_resilient(client, model, seed, stats)
        if story is None:
            continue
        stories.append(story)
        stats["story_cores_generated"] = len(stories)
        if story.get("story_eligible"):
            stats["story_cores_eligible"] = int(stats["story_cores_eligible"]) + 1
        else:
            stats["story_cores_rejected"] = int(stats["story_cores_rejected"]) + 1

    eligible_stories = [s for s in stories if s.get("story_eligible")]
    shortlist, skipped = select_diverse_stories(eligible_stories, shortlist_n)
    stats["semantic_duplicates_removed"] = int(stats.get("semantic_duplicates_removed") or 0) + skipped
    stats["story_shortlist"] = len(shortlist)

    if discovery_only:
        return {
            "generated": stories,
            "rejected": [s for s in stories if not s.get("story_eligible")],
            "eligible": eligible_stories,
            "eligible_ranked": [],
            "stories": stories,
            "story_shortlist": shortlist,
            "orchestration": dict(stats),
            "counts": {
                "generated": len(stories),
                "rejected": int(stats["story_cores_rejected"]),
                "eligible": int(stats["story_cores_eligible"]),
                "returned": len(stories),
            },
        }

    ranked_eligible = sorted(eligible_stories, key=lambda x: float(x.get("story_score") or 0), reverse=True)
    backup = [s for s in ranked_eligible if s.get("id") not in {x.get("id") for x in shortlist}]
    queue = list(shortlist)
    packages: list[dict[str, Any]] = []
    while len(packages) < shortlist_n and (queue or backup):
        story = queue.pop(0) if queue else backup.pop(0)
        pkg = _package_story_resilient(client, model, p, cats, story, stats)
        if pkg is None:
            continue
        packages.append(pkg)
        print(
            f"[v2] packaged {len(packages)}/{shortlist_n} "
            f"story={pkg.get('story_score')} pack={pkg.get('packaging_score')} "
            f"id={pkg.get('id')}",
            flush=True,
        )

    result = _finalize_story_batch(packages, target)
    result["orchestration"] = dict(stats)
    result["orchestration"]["semantic_duplicates_removed"] = int(stats.get("semantic_duplicates_removed") or 0) + int(
        (result.get("counts") or {}).get("semantic_duplicates_removed") or 0
    )
    result["story_shortlist"] = shortlist
    result["stories"] = stories
    return result


def _finalize_batch(packages: list[dict[str, Any]], target: int) -> dict[str, Any]:
    generated = [normalize_concept_package(p) for p in packages]
    return finalize_ranked_batch(generated, target)


def _finalize_story_batch(packages: list[dict[str, Any]], target: int) -> dict[str, Any]:
    """Rank by story_score. Packaging is a tie-breaker, never a burial."""
    generated = []
    for raw in packages:
        pkg = normalize_concept_package(raw)
        pkg = apply_scoring(pkg)
        core = normalize_story_core(pkg.get("story_core") or {})
        spine = normalize_story_spine(pkg.get("story_spine") or "")
        if any(core.values()) and not pkg.get("story_score"):
            scored = score_story(core, spine)
            pkg.update(scored)
        pack = packaging_score(pkg)
        pkg["packaging_score"] = pack["packaging_score"]
        pkg["packaging_scores"] = pack["packaging_scores"]
        story_n = float(pkg.get("story_score") or 0)
        pack_n = float(pkg.get("packaging_score") or 0)
        pkg["rank_score"] = story_n * 10.0 + pack_n * 0.3
        generated.append(pkg)
    rejected = [p for p in generated if not p.get("story_eligible")]
    eligible = [p for p in generated if p.get("story_eligible")]
    pool = eligible or generated
    before = len(pool)
    ranked = select_diverse_top(pool, target)
    skipped = max(0, before - len(ranked))
    return {
        "generated": generated,
        "rejected": rejected,
        "eligible": eligible,
        "eligible_ranked": ranked,
        "counts": {
            "generated": len(generated),
            "rejected": len(rejected),
            "eligible": len(eligible),
            "returned": min(target, len(ranked)),
            "semantic_duplicates_removed": skipped,
        },
    }


def _collect_unique_seeds(
    client: Any,
    model: str,
    profile: dict[str, Any],
    cats: list[str],
    prior: list[dict[str, Any]],
    target: int,
    max_rounds: int,
    stats: dict[str, Any],
) -> list[dict[str, Any]]:
    hard_limit = max(target, min(56, target + 16))
    seen_hooks: set[str] = set()
    out: list[dict[str, Any]] = []
    fail_rounds = 0
    while len(out) < target and fail_rounds < max_rounds and stats.get("raw_generated", 0) < hard_limit * 3:
        need = min(12, max(target - len(out), 2))
        print(f"[v2] seeds {len(out)}/{target}; requesting {need}", flush=True)
        try:
            batch = _llm_raw_seeds(
                client,
                model,
                profile,
                cats,
                prior,
                need,
                avoid_hooks=list(seen_hooks),
                stats=stats,
            )
        except Exception as exc:  # noqa: BLE001
            fail_rounds += 1
            print(f"[v2] seed generation failed: {exc}", flush=True)
            time.sleep(min(12.0, 2.0 ** fail_rounds))
            continue
        if not batch:
            fail_rounds += 1
            print("[v2] empty seed batch", flush=True)
            time.sleep(min(8.0, 1.5 ** fail_rounds))
            continue
        fail_rounds = 0
        for seed in batch:
            hook = str(seed.get("concrete_hook") or "").strip().lower()
            if not hook or hook in seen_hooks:
                continue
            seen_hooks.add(hook)
            out.append(seed)
            if len(out) >= target:
                break
        if len(out) >= hard_limit:
            break
    return out[:target]


def _discover_story_resilient(
    client: Any,
    model: str,
    seed: dict[str, Any],
    stats: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        parsed = _llm_story_from_seed(client, model, seed, stats)
    except Exception as exc:  # noqa: BLE001
        print(f"[story] seed failed: {exc}", flush=True)
        return None
    core = normalize_story_core(parsed.get("story_core") or parsed)
    spine = normalize_story_spine(parsed.get("story_spine") or "")
    if not any(core.values()):
        return None
    gate = validate_story(core, spine)
    scored = score_story(core, spine)
    sid = str(parsed.get("id") or seed.get("id") or seed.get("concrete_hook") or "")[:48]
    shape = classify_story_shape(core, spine, parsed.get("story_shape") or seed.get("story_shape"))
    tmpl = structural_template(core, spine)
    return {
        "id": sid or f"story-{uuid.uuid4().hex[:8]}",
        "seed": seed,
        "story_core": core,
        "story_spine": spine,
        "story_shape": shape,
        "structural_template": tmpl,
        "story_eligible": bool(gate["pass"]),
        "story_validation": gate,
        **scored,
    }


def _package_story_resilient(
    client: Any,
    model: str,
    profile: dict[str, Any],
    cats: list[str],
    story: dict[str, Any],
    stats: dict[str, Any],
) -> dict[str, Any] | None:
    stats["packaging_attempted"] = int(stats.get("packaging_attempted") or 0) + 1
    try:
        raw = _llm_package_from_story(client, model, story, cats, stats)
    except Exception as exc:  # noqa: BLE001
        stats["packaging_failed"] = int(stats.get("packaging_failed") or 0) + 1
        print(f"[pack] failed: {exc}", flush=True)
        return None
    pkg = _merge_story_into_package(raw, story)
    pkg = normalize_concept_package(pkg)
    repaired = False
    if hook_needs_regen(pkg.get("hook")):
        try:
            regenerated = _llm_regen_hook(client, model, pkg, stats)
            if regenerated.get("hook"):
                pkg["hook"] = regenerated["hook"]
            if regenerated.get("hook_options"):
                pkg["hook_options"] = regenerated["hook_options"]
            repaired = True
        except Exception as exc:  # noqa: BLE001
            print(f"[pack] hook regen failed: {exc}", flush=True)
        pkg["hook"] = _clean_hook(str(pkg.get("hook") or ""))
        if hook_needs_regen(pkg.get("hook")):
            pkg["hook"] = synthesize_hook_from_core(story.get("story_core") or {}, pkg.get("world_seeds"))
            repaired = True
        pkg = normalize_concept_package(pkg)
    if needs_ceiling_repair(pkg):
        try:
            pkg = normalize_concept_package(_llm_repair_ceiling(client, model, pkg, stats=stats))
            repaired = True
        except Exception as exc:  # noqa: BLE001
            print(f"[pack] ceiling repair failed: {exc}", flush=True)
    if not pkg.get("eligible"):
        try:
            pkg = normalize_concept_package(_llm_repair_package(client, model, pkg, stats=stats))
            repaired = True
        except Exception as exc:  # noqa: BLE001
            print(f"[pack] package repair failed: {exc}", flush=True)
    if hook_needs_regen(pkg.get("hook")):
        pkg["hook"] = synthesize_hook_from_core(story.get("story_core") or {}, pkg.get("world_seeds"))
        pkg["hook"] = _clean_hook(pkg["hook"])
        repaired = True
        pkg = normalize_concept_package(pkg)
    if repaired:
        stats["packaging_repaired"] = int(stats.get("packaging_repaired") or 0) + 1
    pkg = _merge_story_into_package(pkg, story)
    pack = packaging_score(pkg)
    pkg["packaging_score"] = pack["packaging_score"]
    pkg["packaging_scores"] = pack["packaging_scores"]
    pkg["rank_score"] = float(pkg.get("story_score") or 0) * 10.0 + float(pkg.get("packaging_score") or 0) * 0.3
    return pkg


def _merge_story_into_package(raw: dict[str, Any], story: dict[str, Any]) -> dict[str, Any]:
    pkg = dict(raw or {})
    core = normalize_story_core(story.get("story_core") or pkg.get("story_core") or {})
    spine = normalize_story_spine(story.get("story_spine") or pkg.get("story_spine") or "")
    pkg["id"] = story.get("id") or pkg.get("id")
    pkg["story_core"] = core
    pkg["story_spine"] = spine
    pkg["story_score"] = story.get("story_score") or pkg.get("story_score") or 0
    pkg["story_scores"] = story.get("story_scores") or pkg.get("story_scores") or {}
    pkg["story_score_evidence"] = story.get("story_score_evidence") or {}
    pkg["story_eligible"] = bool(story.get("story_eligible"))
    pkg["story_validation"] = story.get("story_validation") or {}
    engine = story_core_to_engine(core)
    existing = pkg.get("story_engine") if isinstance(pkg.get("story_engine"), dict) else {}
    merged_engine = dict(engine)
    for k, v in existing.items():
        if str(v or "").strip():
            merged_engine[k] = v
    # Story core wins over packaging inventions for engine beats
    for k, v in engine.items():
        if str(v or "").strip():
            merged_engine[k] = v
    pkg["story_engine"] = merged_engine
    if not pkg.get("premise"):
        pkg["premise"] = spine
    if not pkg.get("ending_direction"):
        pkg["ending_direction"] = core.get("ending_direction") or "victory"
    return pkg


def _llm_story_from_seed(client: Any, model: str, seed: dict[str, Any], stats: dict[str, Any] | None = None) -> dict[str, Any]:
    parsed = _chat_json(
        client,
        model,
        STORY_CORE_SYSTEM,
        {
            "seed": seed,
            "story_shape": seed.get("story_shape"),
            "negative_structure": (
                "PROHIBIDO el arco taller_renovado: mejor atención → clientes → sucursales → "
                "competidor barato → mantienes calidad / te vuelves referente."
            ),
            "instruction": (
                "Escribe story_core + story_spine para ESTA seed. Honra su story_shape. "
                "Conflicto orgánico (no pegable en otras 20 ideas). Oportunidad concreta. "
                "Si hay producto, que se pueda explicar qué hace. Ending = estado o evento. "
                "Incluye un giro inesperado plausible. No copies el negocio del ejemplo de calidad."
            ),
        },
        temperature=0.75,
        stats=stats,
    )
    if isinstance(parsed.get("story_core"), dict):
        return parsed
    if isinstance(parsed.get("package"), dict):
        return parsed["package"]
    return parsed


def _llm_package_from_story(
    client: Any,
    model: str,
    story: dict[str, Any],
    cats: list[str],
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = _chat_json(
        client,
        model,
        PACKAGING_FROM_STORY_SYSTEM,
        {
            "story_id": story.get("id"),
            "story_core": story.get("story_core"),
            "story_spine": story.get("story_spine"),
            "prefer_categories": cats,
            "do_not_invent_a_new_story": True,
        },
        temperature=0.55,
        stats=stats,
    )
    pkg = parsed.get("package") if isinstance(parsed.get("package"), dict) else parsed
    return pkg if isinstance(pkg, dict) else {}


def _llm_regen_hook(
    client: Any,
    model: str,
    pkg: dict[str, Any],
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = _chat_json(
        client,
        model,
        HOOK_REGEN_SYSTEM,
        {
            "story_core": pkg.get("story_core"),
            "story_spine": pkg.get("story_spine"),
            "bad_hook": pkg.get("hook"),
        },
        temperature=0.6,
        stats=stats,
    )
    return parsed if isinstance(parsed, dict) else {}


def regenerate_concept_part(
    package: dict[str, Any],
    part: str,
    *,
    profile: dict[str, Any] | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    part = str(part or "").strip().lower()
    if part not in REGENERABLE_PARTS:
        raise ValueError(f"part must be one of {REGENERABLE_PARTS}")
    base = normalize_concept_package(package)
    if not use_llm or not (os.getenv("OPENAI_API_KEY") or "").strip():
        return apply_scoring(_local_regenerate(base, part))

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    system = EXPAND_SYSTEM + (
        f" Regenerate ONLY the '{part}' for this existing package. "
        "Keep the same story_engine fantasy. Return JSON {\"package\": {partial or full fields to merge}}."
    )
    user = {"part": part, "package": base}
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.85,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    )
    raw = (r.choices[0].message.content or "{}").strip()
    parsed = parse_llm_json_object(raw) or {}
    patch = parsed.get("package") if isinstance(parsed, dict) else None
    if not isinstance(patch, dict):
        patch = parsed if isinstance(parsed, dict) else {}
    merged = deepcopy(base)
    if part == "concept":
        for k in (
            "premise",
            "one_line_fantasy",
            "starting_state",
            "end_state",
            "core_transformation",
            "story_category",
            "ending_direction",
            "story_engine",
            "central_story_question",
            "open_loops",
            "world_seeds",
            "llm_score_hints",
            "scores",
            "escalation_ladder",
            "life_progression",
            "rewards",
            "scale_ceiling",
            "start_end_contrast",
            "business_fantasy",
            "life_fantasy",
        ):
            if k in patch:
                merged[k] = patch[k]
    elif part == "title":
        if patch.get("title_options"):
            merged["title_options"] = patch["title_options"]
        if patch.get("title"):
            merged["title"] = patch["title"]
        elif merged.get("title_options"):
            merged["title"] = str((merged["title_options"][0] or {}).get("text") or merged["title"])
    elif part == "thumbnail":
        if isinstance(patch.get("thumbnail_concept"), dict):
            merged["thumbnail_concept"] = patch["thumbnail_concept"]
    elif part == "hook":
        if patch.get("hook"):
            merged["hook"] = patch["hook"]
    return apply_scoring(normalize_concept_package(merged))


def normalize_concept_package(raw: dict[str, Any]) -> dict[str, Any]:
    out = empty_concept_package()
    out["id"] = str(raw.get("id") or raw.get("slug") or uuid.uuid4().hex[:10]).strip()
    from src.documentary.formats.check_als.editorial import CONTENT_LANGUAGE, IMAGE_PROMPT_LANGUAGE

    out["language"] = str(raw.get("language") or raw.get("content_language") or CONTENT_LANGUAGE).strip() or CONTENT_LANGUAGE
    out["content_language"] = out["language"]
    out["image_prompt_language"] = str(raw.get("image_prompt_language") or IMAGE_PROMPT_LANGUAGE).strip() or IMAGE_PROMPT_LANGUAGE
    out["premise"] = str(raw.get("premise") or raw.get("story") or "").strip()
    out["one_line_fantasy"] = str(raw.get("one_line_fantasy") or raw.get("fantasy") or "").strip()
    out["starting_state"] = _stringify_state(raw.get("starting_state"))
    out["end_state"] = _stringify_state(raw.get("end_state"))
    out["core_transformation"] = str(raw.get("core_transformation") or raw.get("transformation") or "").strip()
    out["story_category"] = str(raw.get("story_category") or raw.get("content_pillar") or "entrepreneurship").strip()
    out["ending_direction"] = str(raw.get("ending_direction") or "victory").strip()
    out["central_story_question"] = str(raw.get("central_story_question") or raw.get("story_question") or "").strip()
    loops = raw.get("open_loops") if isinstance(raw.get("open_loops"), list) else []
    out["open_loops"] = [str(x).strip() for x in loops if str(x).strip()][:5]

    engine_in = _coerce_mapping(raw.get("story_engine"))
    engine = empty_story_engine()
    for k in STORY_ENGINE_KEYS:
        engine[k] = str(engine_in.get(k) or raw.get(k) or "").strip()
    out["story_engine"] = engine

    titles = raw.get("title_options") if isinstance(raw.get("title_options"), list) else []
    norm_titles = []
    for t in titles[:5]:
        if isinstance(t, str):
            norm_titles.append(_normalize_title_option({"text": t}))
        elif isinstance(t, dict):
            norm_titles.append(_normalize_title_option(t))
    title_seed = str(raw.get("title") or raw.get("title_concept") or "").strip()
    tv = validate_titles(title_seed, norm_titles)
    out["title_options"] = [
        _normalize_title_option(t if isinstance(t, dict) else {"text": t}) for t in (tv.get("options") or [])
    ]
    out["title"] = tv.get("title") or (out["title_options"][0]["text"] if out["title_options"] else title_seed)

    # Preserve LLM partial hints but never trust overall
    hints = {}
    scores_in = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
    for k, v in scores_in.items():
        if isinstance(v, dict) and "score" in v:
            hints[k] = v
        else:
            hints[k] = v
    # Accept curiosity_score / fantasy_strength_score flat keys from sloppy LLM output
    for k in WEIGHTS:
        alt = f"{k}_score"
        if alt in raw and k not in hints:
            hints[k] = raw[alt]
        if k in raw and k not in hints and not isinstance(raw.get(k), (dict, list)):
            hints[k] = raw[k]
    if isinstance(raw.get("llm_score_hints"), dict):
        hints.update(raw["llm_score_hints"])
    if isinstance(raw.get("score_evidence"), dict):
        for k, v in raw["score_evidence"].items():
            if isinstance(v, dict) and "score" in v:
                hints.setdefault(k, v)
    out["llm_score_hints"] = hints

    thumb = raw.get("thumbnail_concept") if isinstance(raw.get("thumbnail_concept"), dict) else {}
    out["thumbnail_concept"] = {
        **empty_thumbnail_concept(),
        **{k: str(thumb.get(k) or "").strip() for k in empty_thumbnail_concept()},
    }
    out["thumbnail_concept"] = strip_ad_thumbnail_text(out["thumbnail_concept"])
    out["hook"] = _clean_hook(str(raw.get("hook") or ""))
    out["world_seeds"] = parse_world_seeds(raw.get("world_seeds"), raw)

    # Aspirational Engine fields (Phase 1.6)
    out["escalation_ladder"] = normalize_escalation_ladder(raw.get("escalation_ladder"))
    out["escalation_ladder"] = fill_escalation_ladder(out)
    out["life_progression"] = normalize_life_progression(raw.get("life_progression"))
    out["rewards"] = normalize_rewards(raw.get("rewards"))
    if len(out["rewards"]) < 3:
        out["rewards"] = fill_rewards_if_thin(out)
    out["scale_ceiling"] = normalize_scale_ceiling(raw.get("scale_ceiling"))
    out["start_end_contrast"] = normalize_start_end_contrast(raw.get("start_end_contrast"))
    bf = raw.get("business_fantasy")
    if isinstance(bf, dict):
        out["business_fantasy"] = str(bf.get("summary") or bf.get("text") or "").strip()
    else:
        out["business_fantasy"] = str(bf or "").strip()
    lf = raw.get("life_fantasy")
    if isinstance(lf, dict):
        out["life_fantasy"] = str(lf.get("summary") or lf.get("text") or "").strip()
    else:
        out["life_fantasy"] = str(lf or "").strip()

    # Derive starting/end display strings if empty
    ws = out["world_seeds"]
    if not out["starting_state"] and ws.get("starting_age"):
        out["starting_state"] = (
            f"AGE {ws.get('starting_age')} · CASH {ws.get('starting_cash')} · "
            f"{ws.get('starting_location')} · {ws.get('starting_status')}"
        )
    if not out["end_state"] and ws.get("target_outcome"):
        out["end_state"] = str(ws.get("target_outcome"))

    fill_thumbnail_gaps(out)
    repair_scale_consistency(out)

    core = normalize_story_core(raw.get("story_core") or {})
    out["story_core"] = core
    out["story_spine"] = normalize_story_spine(raw.get("story_spine") or "")
    if any(core.values()):
        engine = dict(out.get("story_engine") or {})
        mapped = story_core_to_engine(core)
        for k, v in mapped.items():
            if v and not str(engine.get(k) or "").strip():
                engine[k] = v
        out["story_engine"] = engine
    if isinstance(raw.get("story_scores"), dict):
        out["story_scores"] = raw["story_scores"]
    if raw.get("story_score") not in (None, ""):
        out["story_score"] = raw.get("story_score")
    elif out.get("story_spine") or any(core.values()):
        scored = score_story(core, out.get("story_spine") or "")
        out["story_score"] = scored["story_score"]
        out["story_scores"] = scored["story_scores"]
        out["story_score_evidence"] = scored["story_score_evidence"]
    if "story_eligible" in raw:
        out["story_eligible"] = bool(raw.get("story_eligible"))
    elif out.get("story_spine") or any(core.values()):
        out["story_eligible"] = bool(validate_story(core, out.get("story_spine") or "").get("pass"))
    if isinstance(raw.get("packaging_scores"), dict):
        out["packaging_scores"] = raw["packaging_scores"]
    if raw.get("packaging_score") not in (None, ""):
        out["packaging_score"] = raw.get("packaging_score")

    return apply_scoring(out)


def package_to_project_fields(package: dict[str, Any]) -> dict[str, Any]:
    from src.documentary.formats.check_als.editorial import CONTENT_LANGUAGE

    pkg = normalize_concept_package(package)
    title = pkg["title"]
    topic = pkg["one_line_fantasy"] or pkg["premise"] or title
    idea_legacy = {
        "title_concept": title,
        "story": pkg["premise"],
        "hook": pkg["hook"],
        "why_it_works": pkg["core_transformation"],
        "content_pillar": pkg["story_category"],
        "visual_potential": "High" if pkg["scores"].get("visual_variety", 0) >= 7 else "Medium",
        "research_risk": "n/a",
        "primary_entity": "Tú",
        "check_concept": pkg,
    }
    return {
        "title": title,
        "topic": topic,
        "idea": idea_legacy,
        "content_format": "check_als",
        "concept": pkg,
        "language": CONTENT_LANGUAGE,
        "target_duration_min": [12, 18],
        "target_words": 2200,
    }


def _llm_raw_seeds(
    client: Any,
    model: str,
    profile: dict[str, Any],
    cats: list[str],
    prior: list[dict[str, Any]],
    count: int,
    avoid_titles: list[str] | None = None,
    avoid_hooks: list[str] | None = None,
    stats: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Fetch raw seeds in chunks until we reach `count` (LLM often under-delivers)."""
    target = max(1, int(count))
    out: list[dict[str, Any]] = []
    seen_hooks: set[str] = set(str(h).strip().lower() for h in (avoid_hooks or []) if str(h).strip())
    avoid = list(avoid_titles or [])
    attempts = 0
    max_attempts = max(8, (target // 5) + 3)
    cap = 2 if target <= 24 else 3
    shape_counts: dict[str, int] = {}
    while len(out) < target and attempts < max_attempts:
        attempts += 1
        chunk = min(12, target - len(out), 10 if target - len(out) > 10 else target - len(out))
        chunk = max(chunk, min(8, target - len(out)))
        remaining_shapes = [s for s in STORY_SHAPES if int(shape_counts.get(s) or 0) < cap]
        if not remaining_shapes:
            remaining_shapes = list(STORY_SHAPES)
        batch = _llm_raw_seeds_once(
            client,
            model,
            profile,
            cats,
            prior,
            chunk,
            avoid_titles=avoid,
            avoid_hooks=list(seen_hooks),
            stats=stats,
            required_story_shapes=remaining_shapes[: max(chunk, 8)],
            shape_cap=cap,
        )
        if stats is not None:
            stats["raw_generated"] = int(stats.get("raw_generated") or 0) + len(batch)
        if not batch:
            break
        for row in batch:
            hook = str(row.get("concrete_hook") or "").strip().lower()
            if not hook or hook in seen_hooks:
                continue
            shape = normalize_story_shape(row.get("story_shape") or "")
            if not shape:
                shape = remaining_shapes[len(out) % max(1, len(remaining_shapes))] if remaining_shapes else ""
                row["story_shape"] = shape
            if shape and int(shape_counts.get(shape) or 0) >= cap:
                continue
            seen_hooks.add(hook)
            if shape:
                shape_counts[shape] = int(shape_counts.get(shape) or 0) + 1
            out.append(row)
            if len(out) >= target:
                break
        print(f"[v2] seeds accumulated {len(out)}/{target} (attempt {attempts})", flush=True)
    return out[:target]


def _llm_raw_seeds_once(
    client: Any,
    model: str,
    profile: dict[str, Any],
    cats: list[str],
    prior: list[dict[str, Any]],
    count: int,
    avoid_titles: list[str] | None = None,
    avoid_hooks: list[str] | None = None,
    stats: dict[str, Any] | None = None,
    required_story_shapes: list[str] | None = None,
    shape_cap: int = 2,
) -> list[dict[str, Any]]:
    system = SEED_SYSTEM + (
        f' JSON: {{"seeds":[{{"id":"slug","mechanism_type":"...","fantasy_type":"...",'
        f'"story_shape":"...","industry":"...","scale_hint":"national|international|empire|major_exit",'
        f'"concrete_hook":"una frase vivida EN ESPAÑOL","suggested_category":"..."}}]}} '
        f"Produce EXACTLY {int(count)} seeds (no fewer). concrete_hook MUST be Spanish. "
        f"CADA seed usa un story_shape DISTINTO tomado de required_story_shapes. "
        f"Máximo {int(shape_cap)} seeds con la misma story_shape. "
        f"Diversidad orgánica de mechanism_type y fantasy_type. "
        f"Prefer scale_hint national+. Prohibido community-savior y el arco precio-vs-calidad genérico."
    )
    user = {
        "channel": (profile.get("channel") or {}).get("name"),
        "categories": cats,
        "mechanism_diversity": list(MECHANISM_DIVERSITY),
        "fantasy_diversity": list(FANTASY_DIVERSITY),
        "story_shapes": list(STORY_SHAPES),
        "required_story_shapes": list(required_story_shapes or STORY_SHAPES[: max(1, int(count))]),
        "avoid": profile.get("avoid"),
        "prior": _prior_block(prior),
        "avoid_titles": avoid_titles or [],
        "avoid_hooks": (avoid_hooks or [])[:40],
        "forbidden_arc": (
            "trabajo mediocre → demanda/atención personalizada → prueba → crecimiento → "
            "competidor grande → precio vs calidad → innovación → referente"
        ),
    }
    r = _with_retry(
        lambda: client.chat.completions.create(
            model=model,
            temperature=0.95,
            response_format={"type": "json_object"},
            timeout=90.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        ),
        label="raw_seeds",
        stats=stats,
    )
    parsed = parse_llm_json_object((r.choices[0].message.content or "{}").strip()) or {}
    rows = parsed.get("seeds") if isinstance(parsed, dict) else None
    out = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and str(row.get("concrete_hook") or "").strip():
                out.append(row)
    return out


_FEWSHOT_ENGINE = {
    "id": "mechanic-ai-receptionist",
    "premise": (
        "A los 20 trabajas en la recepción de un taller mecánico. Después de las 18h las llamadas "
        "quedan sin contestar. Construyes una recepcionista IA tosca, cobras $99/mes, agendas 43 "
        "trabajos el primer mes, escalas a grupos de concesionarios y entonces la plataforma más "
        "grande de talleres copia la función y la regala gratis."
    ),
    "story_engine": {
        "specific_opportunity": "Los talleres pierden trabajos después de las 18h porque nadie contesta el teléfono",
        "why_protagonist_notices_it": "Ves al dueño cerrar mientras el teléfono sigue sonando",
        "initial_action": "Construyes una recepcionista IA tosca en un fin de semana",
        "first_customer_or_break": "Tu dueño paga $99/mes si agenda trabajos reales",
        "business_or_progress_mechanism": "SaaS de suscripción para reservas fuera de horario en talleres",
        "why_it_works": "$99 es más barato que perder un solo trabajo de frenos",
        "growth_mechanism": "Referidos entre dueños y luego grupos multi-local de concesionarios",
        "first_proof": "43 trabajos agendados el primer mes",
        "first_major_reward": "Suficiente MRR para dejar el mostrador",
        "primary_opposition": "Dueños que desconfían de una recepción con IA",
        "mid_story_complication": "Una mala transcripción casi hace perder la cuenta piloto",
        "major_threat": "La plataforma más grande de gestión de talleres copia la función y la incluye gratis",
        "big_decision": "Vender al incumbente o pelear como especialista",
        "stakes": "Tus usuarios y si los talleres independientes siguen teniendo opción",
        "possible_cost": "Años de trabajo absorbidos en la página de producto de un competidor",
        "escalation_path": "1 taller → 5 → 50 → concesionarios → guerra del clon gratis",
        "endgame": "Sobrevivir como capa especializada o ser comprado en malas condiciones",
    },
}


def _is_retryable(exc: BaseException) -> bool:
    msg = str(exc).lower()
    name = type(exc).__name__.lower()
    return any(
        x in msg or x in name
        for x in (
            "connection",
            "timeout",
            "timed out",
            "rate limit",
            "429",
            "502",
            "503",
            "504",
            "temporarily",
            "unavailable",
            "reset by peer",
            "connect error",
            "api connection",
        )
    )


def _with_retry(fn, *, attempts: int = 4, base: float = 1.0, label: str = "llm", stats: dict[str, Any] | None = None):
    last: BaseException | None = None
    for i in range(attempts):
        try:
            if stats is not None:
                stats["llm_calls"] = int(stats.get("llm_calls") or 0) + 1
            return fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            retryable = _is_retryable(exc) and i < attempts - 1
            if retryable and stats is not None:
                stats["retries"] = int(stats.get("retries") or 0) + 1
            if (not _is_retryable(exc)) or i == attempts - 1:
                if stats is not None:
                    stats["llm_failures"] = int(stats.get("llm_failures") or 0) + 1
                raise
            delay = min(16.0, base * (2 ** i)) + random.random() * 0.3
            print(f"[retry] {label} {i + 1}/{attempts} failed: {exc}; sleep {delay:.1f}s", flush=True)
            time.sleep(delay)
    assert last is not None
    raise last


def _expand_seed_resilient(
    client: Any,
    model: str,
    profile: dict[str, Any],
    seed: dict[str, Any],
    cats: list[str],
    stats: dict[str, Any],
) -> dict[str, Any] | None:
    stats["expansion_attempts"] = int(stats.get("expansion_attempts") or 0) + 1
    try:
        return _expand_one_seed(client, model, profile, seed, cats)
    except Exception as exc:  # noqa: BLE001
        stats["expansion_failed"] = int(stats.get("expansion_failed") or 0) + 1
        print(f"[expand] seed failed after retries: {exc}", flush=True)
        return None


def _expand_one_seed(
    client: Any,
    model: str,
    profile: dict[str, Any],
    seed: dict[str, Any],
    cats: list[str],
) -> dict[str, Any]:
    engine_pkg = _llm_expand_engine(client, model, seed)
    full = _llm_expand_package(client, model, seed, engine_pkg, cats)
    pkg = normalize_concept_package(full)
    if not pkg.get("eligible"):
        pkg = normalize_concept_package(_llm_repair_package(client, model, pkg))
    if needs_ceiling_repair(pkg):
        pkg = normalize_concept_package(_llm_repair_ceiling(client, model, pkg))
    return pkg


def _replacement_seed(
    client: Any,
    model: str,
    profile: dict[str, Any],
    cats: list[str],
    prior: list[dict[str, Any]],
    seen_titles: set[str],
    seen_hooks: set[str],
    stats: dict[str, Any],
) -> dict[str, Any] | None:
    stats["replacement_seeds"] = int(stats.get("replacement_seeds") or 0) + 1
    try:
        batch = _llm_raw_seeds(
            client,
            model,
            profile,
            cats,
            prior,
            1,
            avoid_titles=list(seen_titles),
            avoid_hooks=list(seen_hooks),
            stats=stats,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[v2] replacement seed failed: {exc}", flush=True)
        return None
    if not batch:
        return None
    hook = str(batch[0].get("concrete_hook") or "").strip().lower()
    if hook:
        seen_hooks.add(hook)
    return batch[0]


def _llm_repair_ceiling(client: Any, model: str, pkg: dict[str, Any], stats: dict[str, Any] | None = None) -> dict[str, Any]:
    """Causal ceiling extension for great story + weak end. Does not invent a new business."""
    system = (
        "Reparas SOLO el techo aspiracional de un concepto Check con buen story engine. "
        "NO cambies el mecanismo ni la prueba temprana. Extiende el MISMO mecanismo de forma causal: "
        "p.ej. 50 talleres → grupos de concesionarios → miles de locales → $5M ARR → "
        "expansión internacional → el incumbente ataca → oferta de acquisition o pelea. "
        "Prohibido inflar cifras arbitrarias sin peldaños. "
        "Return JSON {\"package\": {escalation_ladder, end_state, scale_ceiling, "
        "life_progression, rewards, growth_mechanism, endgame, start_end_contrast, "
        "world_seeds.target_outcome, story_engine.endgame, story_engine.escalation_path}}. "
        "escalation_ladder = array {level, event, world_delta}. "
        "end_state concreto (edad, patrimonio, valuación, empleados, países). "
        "scale_ceiling coherente con países/valuación."
    )
    parsed = _chat_json(
        client,
        model,
        system,
        {"package": pkg, "reason": "great_story_engine + weak_end_ceiling"},
        temperature=0.4,
        stats=stats,
    )
    patch = parsed.get("package") if isinstance(parsed.get("package"), dict) else parsed
    if not isinstance(patch, dict):
        return pkg
    merged = deepcopy(pkg)
    for k, v in patch.items():
        if k == "story_engine" and isinstance(v, dict):
            se = dict(merged.get("story_engine") or {})
            se.update({kk: vv for kk, vv in v.items() if str(vv or "").strip()})
            merged["story_engine"] = se
        elif k == "world_seeds" and isinstance(v, dict):
            merged["world_seeds"] = {**(merged.get("world_seeds") or {}), **v}
        elif k == "life_progression" and isinstance(v, dict):
            merged["life_progression"] = {**(merged.get("life_progression") or {}), **v}
        elif k == "start_end_contrast" and isinstance(v, dict):
            merged["start_end_contrast"] = {**(merged.get("start_end_contrast") or {}), **v}
        elif v not in (None, "", [], {}):
            merged[k] = v
    merged["ceiling_repaired"] = True
    return merged


def _llm_expand_seeds(
    client: Any,
    model: str,
    profile: dict[str, Any],
    seeds: list[dict[str, Any]],
    cats: list[str],
) -> list[dict[str, Any]]:
    """Two-phase expand per seed: story_engine → full package → normalize."""
    out: list[dict[str, Any]] = []
    dummy = {"expansion_attempts": 0, "expansion_failed": 0}
    for idx, seed in enumerate(seeds, 1):
        pkg = _expand_seed_resilient(client, model, profile, seed, cats, dummy)
        if pkg is None:
            continue
        out.append(pkg)
        print(
            f"[expand] {idx}/{len(seeds)} eligible={pkg.get('eligible')} "
            f"score={pkg.get('overall_score')} title={str(pkg.get('title') or '')[:60]}",
            flush=True,
        )
    return out


def _chat_json(
    client: Any,
    model: str,
    system: str,
    user: dict[str, Any],
    *,
    temperature: float = 0.7,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def _once() -> dict[str, Any]:
        r = client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            timeout=90.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        )
        return parse_llm_json_object((r.choices[0].message.content or "{}").strip()) or {}

    return _with_retry(_once, label="expand", stats=stats)


def _llm_expand_engine(client: Any, model: str, seed: dict[str, Any]) -> dict[str, Any]:
    system = (
        "Expandes una seed cruda de Check a premise + story_engine SOLAMENTE. "
        "TODO el texto público en ESPAÑOL (tú/te/tienes). No traduzcas desde inglés. "
        "story_engine DEBE ser un objeto JSON con estas claves exactas: "
        + ", ".join(STORY_ENGINE_KEYS)
        + ". Cada valor: oración concreta (nada de 'desafíos', 'app revolucionaria', "
        "'contratiempos inesperados', 'decisiones difíciles'). Incluye números, precios, "
        "tipos de cliente y una amenaza/competidor específico. "
        "Return JSON: id, premise, story_category, ending_direction, "
        "central_story_question, open_loops (2-5 strings), story_engine (object)."
    )
    parsed = _chat_json(
        client,
        model,
        system,
        {"seed": seed, "example_quality": _FEWSHOT_ENGINE},
        temperature=0.7,
    )
    if "package" in parsed and isinstance(parsed["package"], dict):
        parsed = parsed["package"]
    # Force story_engine to mapping
    se = _coerce_mapping(parsed.get("story_engine"))
    if not se and isinstance(parsed.get("story_engine"), dict):
        se = parsed["story_engine"]
    # Sometimes model nests fields at root
    if not se:
        se = {k: parsed.get(k) for k in STORY_ENGINE_KEYS if parsed.get(k)}
    parsed["story_engine"] = {k: str(se.get(k) or "").strip() for k in STORY_ENGINE_KEYS}
    return parsed


def _llm_expand_package(
    client: Any,
    model: str,
    seed: dict[str, Any],
    engine_pkg: dict[str, Any],
    cats: list[str],
) -> dict[str, Any]:
    system = (
        EXPAND_SYSTEM
        + " Te dan una seed Y un story_engine/premise ya escritos. "
        "Completa el paquete FULL. NO debilites el story_engine. "
        "OBLIGATORIO: hook multilínea en español (segunda persona, concreto), world_seeds como OBJETO, "
        "title + 3 title_options en español (estilo POV: Construyes/Compras/…; nunca blog/LinkedIn), "
        "thumbnail editorial en español + thumbnail_prompt en INGLÉS, "
        "one_line_fantasy, starting_state, end_state CONCRETO, core_transformation, "
        "escalation_ladder como array de objetos {level, event, world_delta} (5-8, cada peldaño causa el siguiente), "
        "start_end_contrast, business_fantasy, life_fantasy, llm_score_hints. "
        "Return JSON {\"package\": {...}}."
    )
    parsed = _chat_json(
        client,
        model,
        system,
        {
            "seed": seed,
            "engine_package": engine_pkg,
            "prefer_categories": cats,
            "example_hook": (
                "Tienes 20 años y contestas el teléfono en un taller mecánico.\n\n"
                "A las 18:00 ves al dueño cerrar la puerta.\n\n"
                "El teléfono sigue sonando.\n\nNadie contesta."
            ),
        },
        temperature=0.65,
    )
    pkg = parsed.get("package") if isinstance(parsed.get("package"), dict) else parsed
    if not isinstance(pkg, dict):
        pkg = {}
    # Merge engine fields if the second pass omitted them
    merged = {**engine_pkg, **pkg}
    if isinstance(engine_pkg.get("story_engine"), dict):
        se = dict(engine_pkg["story_engine"])
        if isinstance(pkg.get("story_engine"), dict):
            se.update({k: v for k, v in pkg["story_engine"].items() if str(v or "").strip()})
        merged["story_engine"] = se
    for k in ("premise", "central_story_question", "open_loops", "story_category", "ending_direction"):
        if not merged.get(k) and engine_pkg.get(k):
            merged[k] = engine_pkg[k]
    return merged


def _llm_repair_package(client: Any, model: str, pkg: dict[str, Any], stats: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fill only failed critical fields; keep concrete engine intact."""
    failed = list((pkg.get("eligibility") or {}).get("failed_gates") or [])
    reasons = list((pkg.get("eligibility") or {}).get("reasons") or [])
    system = (
        "Reparas un concept package de Check (Fase 1.6). Mantén story_engine concreto en ESPAÑOL. "
        "Return JSON {\"package\": {campos a mergear}}. "
        "Si falta hook: cold open 15–30s en segunda persona (tú) ligado al mecanismo. "
        "Si faltan world_seeds: completa starting_age(int), starting_cash, starting_location, "
        "starting_status, target_outcome, business_or_career_type, timeline_scale como OBJETO. "
        "Si el thumbnail es débil: reescribe main_visual/central_contrast/key_object en español "
        "y thumbnail_prompt en inglés. "
        "Si story_engine es vago/falta: reescribe SOLO esos campos con detalle concreto. "
        "Si fallan gates aspiracionales: completa escalation_ladder como array "
        "{level, event, world_delta} (5-8, cada peldaño causa el siguiente), life_progression "
        "(start/early/mid/major/late), rewards (>=3 tipos distintos), scale_ceiling coherente "
        "con end_state (3 países → international), "
        "start_end_contrast, end_state concreto (edad, patrimonio, empleados, ownership). "
        "Si faltan campos de thumbnail (protagonist_state, environment, emotion…): rellenalos. "
        "text_if_any vacío salvo un número/precio corto. "
        "Nunca techo = 'local arreglado'. Nunca placeholders ni Lamborghini/jet genéricos."
    )
    parsed = _chat_json(
        client,
        model,
        system,
        {"failed_gates": failed, "reasons": reasons, "package": pkg},
        temperature=0.5,
        stats=stats,
    )
    patch = parsed.get("package") if isinstance(parsed.get("package"), dict) else parsed
    if not isinstance(patch, dict):
        return pkg
    merged = deepcopy(pkg)
    for k, v in patch.items():
        if k == "story_engine" and isinstance(v, dict):
            se = dict(merged.get("story_engine") or {})
            se.update({kk: vv for kk, vv in v.items() if str(vv or "").strip()})
            merged["story_engine"] = se
        elif k == "world_seeds" and isinstance(v, dict):
            merged["world_seeds"] = {**(merged.get("world_seeds") or {}), **v}
        elif k == "thumbnail_concept" and isinstance(v, dict):
            merged["thumbnail_concept"] = {**(merged.get("thumbnail_concept") or {}), **v}
        elif k == "life_progression" and isinstance(v, dict):
            merged["life_progression"] = {**(merged.get("life_progression") or {}), **v}
        elif k == "rewards":
            merged["rewards"] = v if isinstance(v, (list, dict)) else merged.get("rewards")
        elif k == "escalation_ladder" and isinstance(v, list):
            merged["escalation_ladder"] = v
        elif k == "start_end_contrast" and isinstance(v, dict):
            merged["start_end_contrast"] = {**(merged.get("start_end_contrast") or {}), **v}
        elif v not in (None, "", [], {}):
            merged[k] = v
    return merged


def _coerce_mapping(value: Any) -> dict[str, Any]:
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
                    import ast

                    parsed = ast.literal_eval(s)
                    if isinstance(parsed, dict):
                        return parsed
                except (SyntaxError, ValueError):
                    return {}
    return {}


def _normalize_title_option(t: dict[str, Any]) -> dict[str, Any]:
    scores_in = t.get("scores") if isinstance(t.get("scores"), dict) else {}
    scores = {k: _score(scores_in.get(k, t.get(k))) for k in TITLE_SCORE_KEYS}
    overall = round(sum(scores.values()) / max(1, len(TITLE_SCORE_KEYS)), 1)
    return {
        "text": str(t.get("text") or t.get("title") or "").strip(),
        "scores": scores,
        "overall_score": overall,
    }


def _score(v: Any) -> int:
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        n = 5
    return max(1, min(10, n))


def _clean_hook(hook: str) -> str:
    from src.documentary.formats.check_als.editorial import BANNED_HOOK_OPENERS

    t = re.sub(r"\r\n?", "\n", (hook or "").strip())
    t = re.sub(r"^[¿¡\"']+\s*", "", t)
    # Strip banned openers repeatedly (Imagina que… / En este video…)
    for _ in range(3):
        low = re.sub(r"^[¿¡\"'\s]+", "", t.lower())
        stripped = False
        for ban in BANNED_HOOK_OPENERS:
            if low.startswith(ban):
                # drop first sentence / clause
                parts = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)
                t = parts[1] if len(parts) > 1 else re.sub(r"^[^.\n]+[.\n]\s*", "", t, count=1)
                stripped = True
                break
        if not stripped:
            break
    return t.strip()


def _stringify_state(value: Any) -> str:
    if isinstance(value, dict):
        parts = [f"{k}: {v}" for k, v in value.items() if v not in (None, "")]
        return " · ".join(parts)
    s = str(value or "").strip()
    if s.startswith("{") and s.endswith("}"):
        seeds = parse_world_seeds(s, {})
        if seeds.get("starting_age") or seeds.get("target_outcome"):
            return (
                f"AGE {seeds.get('starting_age')} · CASH {seeds.get('starting_cash')} · "
                f"{seeds.get('starting_location')} · {seeds.get('starting_status')}"
                if seeds.get("starting_age")
                else str(seeds.get("target_outcome") or s)
            )
    return s


def _categories(profile: dict[str, Any], override: list[str] | None) -> list[str]:
    if override:
        return [str(c).strip() for c in override if str(c).strip()]
    ig = profile.get("idea_generation") if isinstance(profile.get("idea_generation"), dict) else {}
    cats = ig.get("categories")
    if isinstance(cats, list) and cats:
        return [str(c).strip() for c in cats if str(c).strip()]
    return list(DEFAULT_CATEGORIES)


def _prior_block(prior: list[dict[str, Any]]) -> str:
    lines = []
    for v in prior[-60:]:
        idea = v.get("idea") if isinstance(v.get("idea"), dict) else {}
        concept = idea.get("check_concept") if isinstance(idea.get("check_concept"), dict) else v
        if not isinstance(concept, dict):
            concept = {}
        title = str(v.get("title") or idea.get("title_concept") or concept.get("title") or "").strip()
        fantasy = str(concept.get("one_line_fantasy") or idea.get("story") or v.get("topic") or "").strip()
        lines.append(f"- {title} | {fantasy[:120]}")
    return "\n".join(lines) if lines else "(none yet)"


def _local_regenerate(base: dict[str, Any], part: str) -> dict[str, Any]:
    pkg = deepcopy(base)
    if part == "title":
        mech = (pkg.get("story_engine") or {}).get("business_or_progress_mechanism") or "proyecto paralelo"
        pkg["title"] = f"POV: Conviertes {mech[:40]} en un imperio"
        pkg["title_options"] = [
            _normalize_title_option({"text": pkg["title"], "scores": {k: 8 for k in TITLE_SCORE_KEYS}}),
            _normalize_title_option(
                {
                    "text": pkg.get("title_options", [{}])[0].get("text")
                    if pkg.get("title_options")
                    else pkg["title"]
                }
            ),
        ]
    elif part == "hook":
        eng = pkg.get("story_engine") or {}
        pkg["hook"] = (
            f"{eng.get('why_protagonist_notices_it') or 'Algo caro se está desperdiciando frente a ti.'}\n\n"
            f"{eng.get('initial_action') or 'Decides arreglarlo tú mismo esta noche.'}\n\n"
            f"{eng.get('first_proof') or 'La primera prueba llega más rápido de lo que esperabas.'}"
        )
    elif part == "thumbnail":
        eng = pkg.get("story_engine") or {}
        pkg["thumbnail_concept"] = {
            **empty_thumbnail_concept(),
            "main_visual": eng.get("specific_opportunity") or pkg.get("premise") or "escena de trabajo concreta",
            "protagonist_state": "concentrado, en acción",
            "environment": (pkg.get("world_seeds") or {}).get("starting_location") or "lugar de trabajo",
            "central_contrast": f"comienzo pequeño vs {(pkg.get('world_seeds') or {}).get('target_outcome') or 'escala'}",
            "emotion": "urgencia tranquila",
            "key_object": eng.get("first_proof") or "prueba de tracción",
            "composition": "sujeto a la izquierda, futuro a la derecha",
            "camera": "plano medio amplio",
            "lighting": "luz práctica del lugar de trabajo",
            "background": "desorden específico del trabajo",
            "text_if_any": "",
            "thumbnail_prompt": (
                f"2D cinematic illustration: {eng.get('specific_opportunity') or pkg.get('premise')}. "
                "Simple expressive protagonist, strong contrast, few elements, detailed environment, no busy text."
            ),
        }
    elif part == "concept":
        eng = dict(pkg.get("story_engine") or {})
        eng["mid_story_complication"] = (eng.get("mid_story_complication") or "") + " Un socio de confianza amenaza con irse."
        pkg["story_engine"] = eng
    return normalize_concept_package(pkg)


def _fixture_package(i: int, categories: list[str]) -> dict[str, Any]:
    """Offline concrete fixtures for tests — not recycled abstract mocks."""
    cat = categories[i % len(categories)] if categories else "entrepreneurship"
    pool = _CONCRETE_FIXTURES
    base = deepcopy(pool[i % len(pool)])
    base["story_category"] = base.get("story_category") or cat
    return normalize_concept_package(base)


# Back-compat name used by older tests/docs
def evaluate_coherence(package: dict[str, Any]) -> dict[str, Any]:
    from src.documentary.formats.check_als.validators import evaluate_coherence_v2

    return evaluate_coherence_v2(package)
