"""Editorial batch: 20 raw seeds → eligibility → top 10. Phase 1.5 deliverable."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def main() -> None:
    _load_env()
    os.environ.setdefault("PYTHONPATH", str(ROOT))

    from src.documentary.channel import check_als_profile
    from src.documentary.formats.check_als.concepts import generate_concepts_v2

    print("starting Phase 1.5 batch ES (20 seeds → eligibility → top 10)...", flush=True)
    print("content_language=es image_prompt_language=en", flush=True)
    print("has_openai_key", bool(os.getenv("OPENAI_API_KEY")), flush=True)
    print("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), flush=True)
    result = generate_concepts_v2(
        check_als_profile(),
        count=10,
        raw_seed_count=20,
        use_llm=True,
        max_rounds=2,
    )
    out = {
        "counts": result["counts"],
        "content_language": "es",
        "image_prompt_language": "en",
        "rejected": [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "premise": (p.get("premise") or "")[:240],
                "eligible": False,
                "failed_gates": (p.get("eligibility") or {}).get("failed_gates"),
                "reasons": (p.get("eligibility") or {}).get("reasons"),
                "overall_score": p.get("overall_score"),
            }
            for p in result["rejected"]
        ],
        "eligible": [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "overall_score": p.get("overall_score"),
                "story_category": p.get("story_category"),
            }
            for p in result["eligible"]
        ],
        "top10": result["eligible_ranked"][:10],
    }
    path = ROOT / "docs" / "check-als-phase1-5-editorial-batch-es.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    # also refresh top10 export
    top_path = ROOT / "docs" / "check-als-phase1-5-top10-es.json"
    keys = [
        "title", "premise", "story_engine", "central_story_question", "open_loops", "hook",
        "thumbnail_concept", "world_seeds", "scores", "score_evidence", "eligibility",
        "overall_score", "story_category", "one_line_fantasy", "starting_state", "end_state",
        "core_transformation", "ending_direction", "specificity_score", "filmability",
        "title_options", "eligible", "language", "content_language",
    ]
    top_out = {
        "counts": result["counts"],
        "content_language": "es",
        "rejected": out["rejected"],
        "top10": [{k: p.get(k) for k in keys} for p in result["eligible_ranked"][:10]],
    }
    top_path.write_text(json.dumps(top_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("counts", json.dumps(result["counts"]))
    print("rejected", len(result["rejected"]))
    print("eligible", len(result["eligible"]))
    for i, p in enumerate(result["eligible_ranked"][:10], 1):
        print(f"{i}. [{p.get('overall_score')}] {p.get('title')}")
    print("wrote", path)
    print("wrote", top_path)


if __name__ == "__main__":
    main()
