from src.documentary.formats.check_als.asset_reuse import (
    AUTO_REUSE,
    REVIEW_REUSE,
    compatibility_score,
    hard_reject,
    plan_coverage,
    slot_semantics,
    virtual_assets_from_semantics,
)


def _sem(**kwargs):
    base = {
        "slot": 10,
        "mood": "pressure",
        "story_function": "crisis",
        "intensity": "medium",
        "location": "owner_office",
        "location_family": "office",
        "protagonist_era": "struggling_owner",
        "protagonist_age": 22,
        "visual_subject": "documents",
        "action_family": "reading",
        "crowd_state": "empty",
        "wealth_state": "cash_poor",
        "business_state": "debt_risk",
        "reusable": True,
        "reuse_priority": "high",
        "hero_shot": False,
        "hero_id": None,
        "support_shot": True,
        "must_have_unique_asset": False,
        "max_reuse_count": 3,
        "minimum_reuse_distance": 8,
        "primary_asset": "still_010",
    }
    base.update(kwargs)
    return base


def test_employee_era_does_not_reuse_owner_wardrobe_era():
    need = _sem(protagonist_era="ordinary_life", location="cubicle", business_state="pre_acquisition")
    have = _sem(protagonist_era="early_owner", location="cubicle", slot=40)
    assert hard_reject(need, have) == "wrong protagonist era"
    score, _ = compatibility_score(need, have)
    assert score == 0.0


def test_sold_out_does_not_reuse_empty_arena():
    need = _sem(crowd_state="sold_out", location="stands", location_family="arena", mood="glory", story_function="payoff")
    have = _sem(crowd_state="sparse", location="stands", location_family="arena", mood="failure", slot=20)
    assert "sold-out" in (hard_reject(need, have) or "") or "empty arena" in (hard_reject(need, have) or "")


def test_glory_bankruptcy_mood_incompatible():
    need = _sem(mood="glory", story_function="payoff")
    have = _sem(mood="bankruptcy", story_function="crisis", slot=30)
    score, why = compatibility_score(need, have)
    assert score == 0.0
    assert "mood" in why or "incompatible" in why


def test_neighbor_mood_can_pass_auto_reuse():
    need = _sem(mood="anxiety", story_function="crisis")
    have = _sem(mood="pressure", story_function="setback", slot=40)
    score, _ = compatibility_score(need, have)
    assert score >= AUTO_REUSE


def test_hero_requires_own_slot():
    need = _sem(slot=17, hero_shot=True, must_have_unique_asset=True, primary_asset="still_017")
    have = _sem(slot=18)
    assert hard_reject(need, have) == "hero requires unique asset"


def test_plan_keeps_100_slots_and_clusters_with_spacing():
    semantics = []
    for i in range(1, 101):
        semantics.append(
            _sem(
                slot=i,
                primary_asset=f"still_{i:03d}",
                hero_shot=i in (7, 17),
                must_have_unique_asset=i in (7, 17),
                reusable=i not in (7, 17),
                max_reuse_count=1 if i in (7, 17) else 3,
            )
        )
    assets = virtual_assets_from_semantics(semantics)
    cov = plan_coverage(semantics, assets)
    assert cov["total_slots"] == 100
    assert len(cov["slot_plan"]) == 100
    assert cov["must_have_unique"] == 2
    assert cov["recommended_unique"] < 100
    assert cov["simulation_recommended"]["missing"] == 0
    groups = [g for g in cov["reuse_groups"] if g["size"] >= 2]
    for g in groups:
        slots = sorted(g["slots"])
        for a, b in zip(slots, slots[1:]):
            assert b - a >= 8


def test_review_band_between_thresholds():
    need = _sem(mood="neutral", story_function="setup", visual_subject="city", action_family="walking")
    have = _sem(
        mood="progress",
        story_function="proof",
        visual_subject="protagonist",
        action_family="thinking",
        slot=50,
        intensity="high",
    )
    score, _ = compatibility_score(need, have)
    assert 0.0 <= score < AUTO_REUSE


def test_slot_semantics_marks_listing_hero():
    visual = {
        "number": 7,
        "protagonist_age": 22,
        "protagonist_state": "office employee, not yet owner",
        "script_text": "El precio de compra es un dólar.",
        "continuity_notes": "Location lock: city",
        "narration": "El precio de compra es un dólar.",
    }
    sem = slot_semantics(visual)
    assert sem["hero_shot"] is True
    assert sem["hero_id"] == "dollar_listing"
    assert sem["reusable"] is False
    assert sem["must_have_unique_asset"] is True


def test_real_coverage_only_uses_existing_assets():
    from src.documentary.formats.check_als.asset_reuse import match_real_coverage, virtual_assets_from_semantics

    semantics = []
    for i in range(1, 21):
        semantics.append(
            _sem(
                slot=i,
                primary_asset=f"still_{i:03d}",
                hero_shot=i == 7,
                must_have_unique_asset=i == 7,
                reusable=i != 7,
            )
        )
    assets = virtual_assets_from_semantics(semantics)
    for a in assets:
        a["exists"] = int(a["source_shot"]) in {7, 10}
    real = match_real_coverage(semantics, assets)
    rc = real["real_coverage"]
    assert rc["imported_unique"] == 2
    assert rc["EXACT"] == 2
    assert rc["EXACT"] + rc["AUTO_REUSE"] + rc["REVIEW_REUSE"] + rc["MISSING"] == 20
    assert all(r["status"] != "EXACT" or r["assigned_asset"] in {"still_007", "still_010"} for r in real["slot_plan"])
    for rev in real["reuse_reviews"]:
        assert "source_asset" in rev and "target_slot" in rev and "reuse_score" in rev
        assert "semantic_reason" in rev and "reuse_count" in rev
    assert "NEXT_REQUIRED" in real["next_queue"]
    p2_like = set(range(1, 21)) - {7, 10}
    required_slots = {x["slot"] for x in real["next_queue"]["NEXT_REQUIRED"]}
    assert required_slots != p2_like


def test_next_queue_empty_before_import():
    from src.documentary.formats.check_als.asset_reuse import match_real_coverage, production_progress, virtual_assets_from_semantics

    semantics = [_sem(slot=1, primary_asset="still_001")]
    assets = virtual_assets_from_semantics(semantics)
    real = match_real_coverage(semantics, assets)
    prog = production_progress(semantics, assets, real["slot_plan"])
    assert prog["missing_exact_assets"] == 1
    assert prog["imported_exact"] == 0
    assert prog["fallback_coverage_available"] == 0
    assert "fallback only" in prog["policy"].lower()
