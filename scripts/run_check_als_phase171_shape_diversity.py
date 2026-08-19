"""Fase 1.7.1: 20 Story Cores only. No packaging. No post-test prompt edits."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_env() -> None:
    for name in (".env", ".env.local"):
        env = ROOT / name
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if not k:
                continue
            if name.endswith(".local") or k not in os.environ:
                os.environ[k] = v


def main() -> int:
    _load_env()
    if not (os.getenv("OPENAI_API_KEY") or "").strip():
        print("OPENAI_API_KEY missing", file=sys.stderr)
        return 2

    from src.documentary.formats.check_als.concepts import generate_concepts_v2
    from src.documentary.formats.check_als.profile import check_als_profile
    from src.documentary.formats.check_als.story_discovery import structural_similarity_report

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    t0 = time.time()
    result = generate_concepts_v2(
        check_als_profile(),
        count=20,
        raw_seed_count=20,
        story_select_count=20,
        use_llm=True,
        discovery_only=True,
    )
    runtime = time.time() - t0
    stories = list(result.get("stories") or [])
    report = structural_similarity_report(stories)
    orch = dict(result.get("orchestration") or {})

    blocks = [
        "CHECK ALS — FASE 1.7.1 STORY SHAPE DIVERSITY",
        "20 Story Cores. SIN packaging. SIN scores en los spines.",
        f"model={model}",
        "",
        "20 STORY SPINES",
        "",
    ]
    for row in stories:
        blocks.extend(
            [
                "-" * 72,
                f"ID\n{row.get('id') or ''}",
                "",
                f"STORY SPINE\n{row.get('story_spine') or ''}",
                "",
            ]
        )
    blocks.extend(["", "STORY SHAPE (por ID)", ""])
    for row in report.get("rows") or []:
        blocks.append(f"{row.get('id')}: {row.get('story_shape')}")
    blocks.extend(
        [
            "",
            "SHAPE COUNTS",
            json.dumps(report.get("shape_counts") or {}, ensure_ascii=False, indent=2),
            "",
            "SIMILITUD ESTRUCTURAL DETECTADA",
            f"generic_success_arc share: {report.get('generic_success_arc_share')}",
            f"generic_success_arc ids: {', '.join(report.get('generic_success_arc_ids') or []) or '(ninguno)'}",
            f"dominant_shape_count: {report.get('dominant_shape_count')}",
            "",
        ]
    )
    for row in report.get("rows") or []:
        beats = ", ".join(row.get("beats") or []) or "—"
        blocks.append(
            f"{row.get('id')}: template={row.get('template')} · beats=[{beats}] · "
            f"conflicto_intercambiable={row.get('interchangeable_conflict')} · "
            f"oportunidad_genérica={row.get('generic_opportunity')} · "
            f"invento_genérico={row.get('generic_invention')} · "
            f"ending_genérico={row.get('generic_ending')}"
        )
    blocks.extend(
        [
            "",
            "MÉTRICAS",
            f"raw requested: {orch.get('raw_requested')}",
            f"raw generated: {orch.get('raw_generated')}",
            f"raw unique: {orch.get('raw_unique')}",
            f"story cores generated: {orch.get('story_cores_generated')}",
            f"story cores rejected: {orch.get('story_cores_rejected')}",
            f"story cores eligible: {orch.get('story_cores_eligible')}",
            f"LLM calls: {orch.get('llm_calls')}",
            f"retries: {orch.get('retries')}",
            f"failures: {orch.get('llm_failures')}",
            f"runtime_sec: {round(runtime, 1)}",
            "",
        ]
    )
    txt = "\n".join(blocks)
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "check-als-phase1-7-1-shape-diversity.txt").write_text(txt, encoding="utf-8")
    payload = {
        "model": model,
        "runtime_sec": round(runtime, 1),
        "orchestration": orch,
        "stories": [
            {
                "id": s.get("id"),
                "story_spine": s.get("story_spine"),
                "story_shape": s.get("story_shape"),
                "structural_template": s.get("structural_template"),
                "story_eligible": s.get("story_eligible"),
            }
            for s in stories
        ],
        "structural_similarity": report,
    }
    (docs / "check-als-phase1-7-1-shape-diversity.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(txt)
    print(f"\nWrote docs/check-als-phase1-7-1-shape-diversity.txt ({round(runtime, 1)}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
