"""Editorial batch: 30 raw seeds → aspirational gate → top 10. Phase 1.6 deliverable."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TOP_KEYS = [
    "title",
    "premise",
    "story_engine",
    "escalation_ladder",
    "life_progression",
    "rewards",
    "scale_ceiling",
    "start_end_contrast",
    "business_fantasy",
    "life_fantasy",
    "central_story_question",
    "open_loops",
    "hook",
    "thumbnail_concept",
    "world_seeds",
    "aspirational_score",
    "aspirational_evidence",
    "aspirational",
    "scores",
    "score_evidence",
    "eligibility",
    "overall_score",
    "rank_score",
    "story_category",
    "one_line_fantasy",
    "starting_state",
    "end_state",
    "core_transformation",
    "ending_direction",
    "specificity_score",
    "filmability",
    "title_options",
    "eligible",
    "language",
    "content_language",
    "diversity_note",
]


def _load_env() -> None:
    env = ROOT / ".env.local"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _mechanism_summary(p: dict) -> str:
    eng = p.get("story_engine") if isinstance(p.get("story_engine"), dict) else {}
    return str(eng.get("business_or_progress_mechanism") or "")[:200]


def main() -> None:
    _load_env()
    os.environ.setdefault("PYTHONPATH", str(ROOT))

    from src.documentary.channel import check_als_profile
    from src.documentary.formats.check_als.concepts import generate_concepts_v2

    print("starting Phase 1.6 batch ES (30 seeds → aspirational → top 10)...", flush=True)
    print("content_language=es image_prompt_language=en", flush=True)
    print("has_openai_key", bool(os.getenv("OPENAI_API_KEY")), flush=True)
    print("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), flush=True)
    result = generate_concepts_v2(
        check_als_profile(),
        count=10,
        raw_seed_count=30,
        use_llm=True,
        max_rounds=3,
    )
    rejected = [
        {
            "id": p.get("id"),
            "title": p.get("title"),
            "premise": (p.get("premise") or "")[:280],
            "scale_ceiling": p.get("scale_ceiling"),
            "eligible": False,
            "failed_gates": (p.get("eligibility") or {}).get("failed_gates"),
            "reasons": (p.get("eligibility") or {}).get("reasons"),
            "overall_score": p.get("overall_score"),
            "aspirational_score": p.get("aspirational_score"),
        }
        for p in result["rejected"]
    ]
    eligible = [
        {
            "id": p.get("id"),
            "title": p.get("title"),
            "overall_score": p.get("overall_score"),
            "aspirational_score": p.get("aspirational_score"),
            "scale_ceiling": p.get("scale_ceiling"),
            "story_category": p.get("story_category"),
            "specific_mechanism": _mechanism_summary(p),
        }
        for p in result["eligible"]
    ]
    top10 = []
    for p in result["eligible_ranked"][:10]:
        row = {k: p.get(k) for k in TOP_KEYS}
        row["specific_mechanism"] = _mechanism_summary(p)
        # Flatten aspirational display without dumping full nested noise twice
        asp = p.get("aspirational") if isinstance(p.get("aspirational"), dict) else {}
        row["business_fantasy_eval"] = asp.get("business_fantasy")
        row["life_fantasy_eval"] = asp.get("life_fantasy")
        top10.append(row)

    out = {
        "phase": "1.6",
        "counts": result["counts"],
        "content_language": "es",
        "image_prompt_language": "en",
        "generated": len(result["generated"]),
        "rejected": rejected,
        "eligible": eligible,
        "top10": top10,
    }
    path = ROOT / "docs" / "check-als-phase1-6-editorial-batch-es.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    top_path = ROOT / "docs" / "check-als-phase1-6-top10-es.json"
    top_path.write_text(
        json.dumps(
            {
                "phase": "1.6",
                "counts": result["counts"],
                "content_language": "es",
                "rejected": rejected,
                "top10": top10,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Human-readable digest
    lines = [
        "# Check ALS — Fase 1.6 Top 10 (Aspirational Engine)",
        "",
        f"generated={result['counts'].get('generated')} rejected={result['counts'].get('rejected')} "
        f"eligible={result['counts'].get('eligible')} returned={result['counts'].get('returned')}",
        "",
    ]
    for i, p in enumerate(top10, 1):
        lines.append(f"## {i}. [{p.get('overall_score')}] {p.get('title')}")
        lines.append(f"- scale_ceiling: {p.get('scale_ceiling')}")
        lines.append(f"- aspirational_score: {p.get('aspirational_score')}")
        lines.append(f"- mechanism: {p.get('specific_mechanism')}")
        lines.append(f"- contrast: {(p.get('start_end_contrast') or {}).get('start', '')[:80]} → "
                     f"{(p.get('start_end_contrast') or {}).get('end', '')[:80]}")
        lines.append("")
    lines.append("## Rejected (motivos)")
    for r in rejected[:40]:
        lines.append(f"- {r.get('title') or r.get('id')}: {', '.join((r.get('failed_gates') or [])[:6])}")
    txt_path = ROOT / "docs" / "check-als-phase1-6-top10-es.txt"
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print("counts", json.dumps(result["counts"]))
    print("rejected", len(result["rejected"]))
    print("eligible", len(result["eligible"]))
    for i, p in enumerate(result["eligible_ranked"][:10], 1):
        print(
            f"{i}. [{p.get('overall_score')}|asp={p.get('aspirational_score')}|{p.get('scale_ceiling')}] "
            f"{p.get('title')}",
            flush=True,
        )
    print("wrote", path)
    print("wrote", top_path)
    print("wrote", txt_path)


if __name__ == "__main__":
    main()
