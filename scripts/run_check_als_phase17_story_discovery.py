"""Fase 1.7 console test: Story Discovery → packaging. Does not change the engine after results."""
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


def _txt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, indent=2)
    return str(v).strip()


def _life_block(life: Any) -> str:
    if not isinstance(life, dict):
        return _txt(life) or "(vacío)"
    lines: list[str] = []
    stages = life.get("stages") if isinstance(life.get("stages"), list) else []
    if stages:
        for row in stages:
            if not isinstance(row, dict):
                lines.append(f"- {row}")
                continue
            lines.append(
                f"- {row.get('stage')}: {row.get('age_or_time')} · {row.get('living_situation')} · "
                f"{row.get('financial_state')} · libertad={row.get('freedom')} · status={row.get('status')} · "
                f"familia={row.get('family_effect')} · entorno={row.get('environment')}"
            )
        return "\n".join(lines)
    for k in ("start", "early_reward", "mid_reward", "major_reward", "late_state"):
        vals = life.get(k) or []
        if isinstance(vals, list):
            body = "; ".join(str(x) for x in vals if str(x).strip())
        else:
            body = str(vals)
        lines.append(f"{k}: {body}")
    return "\n".join(lines)


def _rewards_block(rewards: Any) -> str:
    if not isinstance(rewards, list) or not rewards:
        return "(vacío)"
    lines = []
    for r in rewards:
        if isinstance(r, dict):
            extra = r.get("moment") or r.get("story_beat") or ""
            sig = r.get("story_significance") or ""
            lines.append(
                f"- [{r.get('type')}] {r.get('description')}"
                + (f" ({extra})" if extra else "")
                + (f" — {sig}" if sig else "")
            )
        else:
            lines.append(f"- {r}")
    return "\n".join(lines)


def _list_block(items: Any) -> str:
    if isinstance(items, list):
        lines = []
        for i, x in enumerate(items, 1):
            if isinstance(x, dict) and x.get("event"):
                delta = f" — {x.get('world_delta')}" if x.get("world_delta") else ""
                lines.append(f"{x.get('level') or i}. {x.get('event')}{delta}")
            elif isinstance(x, dict):
                lines.append(f"{i}. {json.dumps(x, ensure_ascii=False)}")
            else:
                lines.append(f"{i}. {x}")
        return "\n".join(lines) if lines else "(vacío)"
    return _txt(items) or "(vacío)"


def _blind_section(shortlist: list[dict[str, Any]]) -> str:
    ordered = sorted(shortlist, key=lambda x: str(x.get("id") or ""))
    blocks = [
        "TOP 15 STORY SPINES — BLIND EDITORIAL REVIEW",
        "",
        "Sin scores. Sin ranking. Sin títulos. Juzgar como espectador.",
        "",
    ]
    for row in ordered:
        blocks.extend(
            [
                "-" * 72,
                f"ID\n{row.get('id') or ''}",
                "",
                f"STORY SPINE\n{row.get('story_spine') or ''}",
                "",
            ]
        )
    return "\n".join(blocks).rstrip() + "\n"


def _system_ranking(shortlist: list[dict[str, Any]], ranked: list[dict[str, Any]]) -> str:
    by_id = {str(x.get("id")): x for x in shortlist}
    lines = ["SYSTEM RANKING", ""]
    ordered = sorted(shortlist, key=lambda x: float(x.get("story_score") or 0), reverse=True)
    for i, row in enumerate(ordered, 1):
        subs = row.get("story_scores") or {}
        pkg = by_id.get(str(row.get("id"))) or row
        pack = next((p for p in ranked if p.get("id") == row.get("id")), None)
        pack_score = (pack or pkg).get("packaging_score")
        lines.append(f"{i}. {row.get('id')}")
        lines.append(f"   story_score: {row.get('story_score')}")
        lines.append(f"   would_watch: {subs.get('would_watch')}")
        lines.append(f"   causal_strength: {subs.get('causal_strength')}")
        lines.append(f"   mechanism_strength: {subs.get('mechanism_strength')}")
        lines.append(f"   progression_strength: {subs.get('progression_strength')}")
        lines.append(f"   aspirational_strength: {subs.get('aspirational_strength')}")
        lines.append(f"   conflict_strength: {subs.get('conflict_strength')}")
        lines.append(f"   distinctiveness: {subs.get('distinctiveness')}")
        lines.append(f"   packaging_score: {pack_score}")
        lines.append("")
    lines.append("FINAL TOP 10 ORDER")
    for i, p in enumerate(ranked, 1):
        lines.append(
            f"{i}. {p.get('id')}  story={p.get('story_score')}  pack={p.get('packaging_score')}  "
            f"rank={p.get('rank_score')}"
        )
    return "\n".join(lines) + "\n"


def _format_top10(rank: int, p: dict[str, Any]) -> str:
    thumb = p.get("thumbnail_concept") if isinstance(p.get("thumbnail_concept"), dict) else {}
    engine = p.get("story_engine") if isinstance(p.get("story_engine"), dict) else {}
    return "\n".join(
        [
            "=" * 72,
            f"RANK {rank}",
            f"ID\n{p.get('id') or ''}",
            "",
            f"TITLE\n{p.get('title') or ''}",
            "",
            f"STORY SCORE\n{p.get('story_score')}",
            f"STORY SUBSCORES\n{_txt(p.get('story_scores'))}",
            f"PACKAGING SCORE\n{p.get('packaging_score')}",
            f"PACKAGING SUBSCORES\n{_txt(p.get('packaging_scores'))}",
            "",
            f"STORY SPINE\n{p.get('story_spine') or p.get('premise') or ''}",
            "",
            f"HOOK\n{p.get('hook') or ''}",
            "",
            f"END STATE\n{p.get('end_state') or ''}",
            "",
            f"SCALE CEILING\n{p.get('scale_ceiling') or ''}",
            "",
            f"MECHANISM\n{engine.get('business_or_progress_mechanism') or ''}",
            "",
            f"MAJOR THREAT\n{engine.get('major_threat') or ''}",
            "",
            f"BIG DECISION\n{engine.get('big_decision') or ''}",
            "",
            f"ESCALATION LADDER\n{_list_block(p.get('escalation_ladder'))}",
            "",
            f"LIFE PROGRESSION\n{_life_block(p.get('life_progression'))}",
            "",
            f"REWARDS\n{_rewards_block(p.get('rewards'))}",
            "",
            f"THUMBNAIL CONCEPT\n{_txt(thumb)}",
            "",
            f"WORLD SEEDS\n{_txt(p.get('world_seeds'))}",
            "",
        ]
    )


def _metrics(orch: dict[str, Any], runtime: float, model: str) -> str:
    return "\n".join(
        [
            "MÉTRICAS DE EJECUCIÓN",
            f"raw requested: {orch.get('raw_requested')}",
            f"raw generated: {orch.get('raw_generated')}",
            f"raw unique: {orch.get('raw_unique')}",
            f"story cores generated: {orch.get('story_cores_generated')}",
            f"story cores rejected: {orch.get('story_cores_rejected')}",
            f"story cores eligible: {orch.get('story_cores_eligible')}",
            f"story shortlist: {orch.get('story_shortlist')}",
            f"packaging attempted: {orch.get('packaging_attempted')}",
            f"packaging repaired: {orch.get('packaging_repaired')}",
            f"packaging failed: {orch.get('packaging_failed')}",
            f"semantic duplicates removed: {orch.get('semantic_duplicates_removed')}",
            f"LLM calls: {orch.get('llm_calls')}",
            f"retries: {orch.get('retries')}",
            f"failures: {orch.get('llm_failures')}",
            f"runtime_sec: {round(runtime, 1)}",
            f"model: {model}",
            "",
        ]
    )


def _slim(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": p.get("id"),
        "title": p.get("title"),
        "story_spine": p.get("story_spine"),
        "story_core": p.get("story_core"),
        "story_score": p.get("story_score"),
        "story_scores": p.get("story_scores"),
        "packaging_score": p.get("packaging_score"),
        "packaging_scores": p.get("packaging_scores"),
        "rank_score": p.get("rank_score"),
        "hook": p.get("hook"),
        "end_state": p.get("end_state"),
        "scale_ceiling": p.get("scale_ceiling"),
        "story_engine": p.get("story_engine"),
        "escalation_ladder": p.get("escalation_ladder"),
        "life_progression": p.get("life_progression"),
        "rewards": p.get("rewards"),
        "thumbnail_concept": p.get("thumbnail_concept"),
        "world_seeds": p.get("world_seeds"),
        "eligible": p.get("eligible"),
        "story_eligible": p.get("story_eligible"),
    }


def main() -> int:
    _load_env()
    if not (os.getenv("OPENAI_API_KEY") or "").strip():
        print("OPENAI_API_KEY missing", file=sys.stderr)
        return 2

    from src.documentary.formats.check_als.concepts import generate_concepts_v2
    from src.documentary.formats.check_als.profile import check_als_profile

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    t0 = time.time()
    result = generate_concepts_v2(
        check_als_profile(),
        count=10,
        raw_seed_count=40,
        story_select_count=15,
        use_llm=True,
    )
    runtime = time.time() - t0
    shortlist = list(result.get("story_shortlist") or [])
    ranked = list(result.get("eligible_ranked") or [])
    orch = dict(result.get("orchestration") or {})

    txt = "\n".join(
        [
            "CHECK ALS — FASE 1.7 STORY DISCOVERY",
            f"model={model}",
            "",
            _blind_section(shortlist),
            "",
            _system_ranking(shortlist, ranked),
            "",
            "TOP 10 COMPLETOS",
            "",
            "\n".join(_format_top10(i, p) for i, p in enumerate(ranked, 1)),
            "",
            _metrics(orch, runtime, model),
        ]
    )
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "check-als-phase1-7-story-discovery.txt").write_text(txt, encoding="utf-8")
    payload = {
        "model": model,
        "runtime_sec": round(runtime, 1),
        "orchestration": orch,
        "story_shortlist": [
            {
                "id": s.get("id"),
                "story_spine": s.get("story_spine"),
                "story_score": s.get("story_score"),
                "story_scores": s.get("story_scores"),
                "story_eligible": s.get("story_eligible"),
            }
            for s in shortlist
        ],
        "top10": [_slim(p) for p in ranked],
        "counts": result.get("counts"),
        "all_stories": [
            {
                "id": s.get("id"),
                "story_spine": s.get("story_spine"),
                "story_score": s.get("story_score"),
                "story_scores": s.get("story_scores"),
                "story_eligible": s.get("story_eligible"),
                "story_validation": s.get("story_validation"),
            }
            for s in list(result.get("stories") or [])
        ],
    }
    (docs / "check-als-phase1-7-story-discovery.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(txt)
    print(f"\nWrote docs/check-als-phase1-7-story-discovery.txt ({round(runtime, 1)}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
