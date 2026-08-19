"""Console test: real Check Generate Concepts path. Does not change the engine."""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


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


def _prior_from_previous_batches() -> list[dict[str, Any]]:
    """Avoid recycling titles/hooks already shown in 1.5 / 1.6 docs."""
    prior: list[dict[str, Any]] = []
    for name in (
        "check-als-phase1-6-final-console-test.json",
        "check-als-phase1-6-editorial-batch-es.json",
        "check-als-phase1-6-top10-es.json",
        "check-als-phase1-5-editorial-batch-es.json",
        "check-als-phase1-5-top10-es.json",
    ):
        path = ROOT / "docs" / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for key in ("top10", "eligible", "rejected"):
            for row in data.get(key) or []:
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or "").strip()
                if not title:
                    continue
                prior.append(
                    {
                        "title": title,
                        "topic": str(row.get("premise") or row.get("specific_mechanism") or "")[:180],
                        "idea": {"title_concept": title, "check_concept": row},
                    }
                )
    return prior


def _txt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, indent=2)
    return str(v).strip()


def _engine(p: dict[str, Any], key: str) -> str:
    eng = p.get("story_engine") if isinstance(p.get("story_engine"), dict) else {}
    return str(eng.get(key) or "").strip()


def _list_block(items: Any) -> str:
    if isinstance(items, list):
        lines = []
        for i, x in enumerate(items, 1):
            if isinstance(x, dict):
                if x.get("event"):
                    delta = f" — {x.get('world_delta')}" if x.get("world_delta") else ""
                    lines.append(f"{x.get('level') or i}. {x.get('event')}{delta}")
                else:
                    lines.append(f"{i}. {json.dumps(x, ensure_ascii=False)}")
            else:
                lines.append(f"{i}. {x}")
        return "\n".join(lines) if lines else "(vacío)"
    return _txt(items) or "(vacío)"


def _life_block(life: Any) -> str:
    if not isinstance(life, dict):
        return _txt(life) or "(vacío)"
    lines = []
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
            lines.append(
                f"- [{r.get('type')}] {r.get('description')}"
                + (f" ({r.get('story_beat')})" if r.get("story_beat") else "")
            )
        else:
            lines.append(f"- {r}")
    return "\n".join(lines)


def _contrast_block(c: Any) -> str:
    if not isinstance(c, dict):
        return _txt(c)
    return f"START:\n{c.get('start') or ''}\n\nEND:\n{c.get('end') or ''}".strip()


def format_concept(rank: int, p: dict[str, Any]) -> str:
    thumb = p.get("thumbnail_concept") if isinstance(p.get("thumbnail_concept"), dict) else {}
    scores = p.get("scores") if isinstance(p.get("scores"), dict) else {}
    evidence = p.get("score_evidence") if isinstance(p.get("score_evidence"), dict) else {}
    elig = p.get("eligibility") if isinstance(p.get("eligibility"), dict) else {}
    asp_ev = p.get("aspirational_evidence")
    if not asp_ev:
        asp = p.get("aspirational") if isinstance(p.get("aspirational"), dict) else {}
        asp_ev = asp.get("aspirational_evidence")
    breakdown = []
    for k, v in scores.items():
        ev = evidence.get(k) if isinstance(evidence.get(k), dict) else {}
        bits = ev.get("evidence") if isinstance(ev, dict) else []
        extra = "; ".join(str(x) for x in (bits or [])[:4])
        breakdown.append(f"  {k}: {v}" + (f" — {extra}" if extra else ""))
    return "\n".join(
        [
            "=" * 72,
            f"RANK {rank}",
            f"TITLE\n{p.get('title') or ''}",
            "",
            f"OVERALL SCORE\n{p.get('overall_score')}",
            "",
            f"PREMISE\n{p.get('premise') or ''}",
            "",
            f"START\n{p.get('starting_state') or ''}",
            "",
            f"END\n{p.get('end_state') or ''}",
            "",
            f"SPECIFIC OPPORTUNITY\n{_engine(p, 'specific_opportunity')}",
            "",
            f"MECHANISM\n{_engine(p, 'business_or_progress_mechanism')}",
            "",
            f"GROWTH ENGINE\n{_engine(p, 'growth_mechanism')}",
            "",
            f"MAJOR THREAT\n{_engine(p, 'major_threat')}",
            "",
            f"BIG DECISION\n{_engine(p, 'big_decision')}",
            "",
            f"STAKES\n{_engine(p, 'stakes')}",
            "",
            f"ESCALATION LADDER\n{_list_block(p.get('escalation_ladder'))}",
            "",
            f"LIFE PROGRESSION\n{_life_block(p.get('life_progression'))}",
            "",
            f"REWARDS\n{_rewards_block(p.get('rewards'))}",
            "",
            f"SCALE CEILING\n{p.get('scale_ceiling') or ''}",
            "",
            f"START → END CONTRAST\n{_contrast_block(p.get('start_end_contrast'))}",
            "",
            f"CENTRAL STORY QUESTION\n{p.get('central_story_question') or ''}",
            "",
            f"OPEN LOOPS\n{_list_block(p.get('open_loops'))}",
            "",
            f"HOOK\n{p.get('hook') or ''}",
            "",
            f"THUMBNAIL CONCEPT\n{_txt(thumb)}",
            "",
            f"WORLD SEEDS\n{_txt(p.get('world_seeds'))}",
            "",
            f"ASPIRATIONAL SCORE\n{p.get('aspirational_score')}",
            "",
            f"ASPIRATIONAL EVIDENCE\n{_list_block(asp_ev)}",
            "",
            "SCORE BREAKDOWN\n" + ("\n".join(breakdown) if breakdown else "(vacío)"),
            "",
            f"ELIGIBILITY\n{_txt(elig)}",
            "",
        ]
    )


def _mech_bucket(p: dict[str, Any]) -> str:
    blob = " ".join(
        [
            str(p.get("title") or ""),
            str(p.get("premise") or ""),
            _engine(p, "business_or_progress_mechanism"),
        ]
    ).lower()
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
        "liga",
        "música",
        "musica",
        "inmobil",
        "entrada",
        "reventa",
        "fábrica",
        "fabrica",
        "media",
        "youtube",
        "hotel",
        "motel",
    ):
        if token in blob:
            return token
    return (blob[:40] or "other")


def diversity_report(top: list[dict[str, Any]]) -> str:
    from src.documentary.formats.check_als.quality import concept_fingerprint, is_same_movie

    cats = Counter(str(p.get("story_category") or "?") for p in top)
    scales = Counter(str(p.get("scale_ceiling") or "?") for p in top)
    endings = Counter(str(p.get("ending_direction") or "?") for p in top)
    mechs = Counter(_mech_bucket(p) for p in top)
    families = Counter(concept_fingerprint(p).get("industry") or "?" for p in top)
    models = Counter(concept_fingerprint(p).get("business_model") or "?" for p in top)
    fantasies = Counter(concept_fingerprint(p).get("fantasy_type") or "?" for p in top)
    industries = []
    for p in top:
        ws = p.get("world_seeds") if isinstance(p.get("world_seeds"), dict) else {}
        industries.append(str(ws.get("business_or_career_type") or p.get("story_category") or "?"))
    ind = Counter(industries)
    one_liners = Counter(str(p.get("one_line_fantasy") or "")[:80] for p in top)
    lines = [
        "DIVERSITY REPORT",
        "",
        "categorías:",
        *[f"  {k}: {v}" for k, v in cats.most_common()],
        "",
        "industry families:",
        *[f"  {k}: {v}" for k, v in families.most_common()],
        "",
        "business_model:",
        *[f"  {k}: {v}" for k, v in models.most_common()],
        "",
        "mecanismos (bucket):",
        *[f"  {k}: {v}" for k, v in mechs.most_common()],
        "",
        "industrias (world_seeds.business_or_career_type):",
        *[f"  {k}: {v}" for k, v in ind.most_common()],
        "",
        "fantasy_type:",
        *[f"  {k}: {v}" for k, v in fantasies.most_common()],
        "",
        "one_line_fantasy:",
        *[f"  {k}: {v}" for k, v in one_liners.most_common()],
        "",
        "ending_directions:",
        *[f"  {k}: {v}" for k, v in endings.most_common()],
        "",
        "scale_ceilings:",
        *[f"  {k}: {v}" for k, v in scales.most_common()],
        "",
        "similitudes detectadas en Top 10:",
    ]
    clones = []
    for i, a in enumerate(top):
        for b in top[i + 1 :]:
            if is_same_movie(a, b):
                clones.append((a.get("title"), b.get("title")))
    if not clones:
        lines.append("  ninguna pareja del Top 10 es la misma película.")
    else:
        for a, b in clones:
            lines.append(f"  CLON: {a} ↔ {b}")
    return "\n".join(lines)


def main() -> None:
    _load_env()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    stats: dict[str, Any] = {
        "llm_calls": 0,
        "retries": 0,
        "failures": 0,
        "repaired": 0,
        "raw_requested": 0,
        "raw_received": 0,
        "unique_after_dedupe": 0,
        "expand_failures": 0,
    }

    import openai as openai_mod

    real_openai = openai_mod.OpenAI

    class CountingOpenAI(real_openai):  # type: ignore[valid-type,misc]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            orig = self.chat.completions.create

            def wrapped(*a: Any, **k: Any):
                stats["llm_calls"] += 1
                try:
                    return orig(*a, **k)
                except Exception:
                    stats["failures"] += 1
                    raise

            self.chat.completions.create = wrapped  # type: ignore[method-assign]

    openai_mod.OpenAI = CountingOpenAI  # type: ignore[misc]

    from src.documentary.formats.check_als import concepts as concepts_mod
    from src.documentary.channel import check_als_profile
    from src.documentary.formats.check_als.concepts import generate_concepts_v2

    orig_seeds = concepts_mod._llm_raw_seeds
    orig_repair = concepts_mod._llm_repair_package
    orig_expand = concepts_mod._llm_expand_seeds

    def seeds_wrap(client, model, profile, cats, prior, count, avoid_titles=None, avoid_hooks=None, stats=None):
        out = orig_seeds(
            client,
            model,
            profile,
            cats,
            prior,
            count,
            avoid_titles=avoid_titles,
            avoid_hooks=avoid_hooks,
            stats=stats,
        )
        return out

    def repair_wrap(client, model, pkg):
        stats["retries"] += 1
        stats["repaired"] += 1
        return orig_repair(client, model, pkg)

    def expand_wrap(client, model, profile, seeds, cats):
        out = []
        for idx, seed in enumerate(seeds, 1):
            try:
                out.extend(orig_expand(client, model, profile, [seed], cats))
            except Exception as exc:  # noqa: BLE001
                stats["expand_failures"] += 1
                stats["failures"] += 1
                print(f"[expand] seed {idx} failed: {exc}", flush=True)
        return out

    concepts_mod._llm_raw_seeds = seeds_wrap
    concepts_mod._llm_repair_package = repair_wrap
    # keep orig expand so repair wrap on module is used by orig_expand
    # Don't wrap expand — orig_expand already calls _llm_repair_package which we patched.

    prior = _prior_from_previous_batches()
    print("CHECK ALS — FINAL CONCEPT TEST", flush=True)
    print("content_format=check_als", flush=True)
    print("has_openai_key", bool(os.getenv("OPENAI_API_KEY")), flush=True)
    print("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), flush=True)
    print("prior_avoided", len(prior), flush=True)
    print("raw_seed_target=30 top=10 use_llm=True mocks=False", flush=True)

    t0 = time.monotonic()
    result = generate_concepts_v2(
        check_als_profile(),
        prior_videos=prior,
        count=10,
        raw_seed_count=30,
        use_llm=True,
        max_rounds=8,
    )
    runtime = time.monotonic() - t0
    orch = result.get("orchestration") if isinstance(result.get("orchestration"), dict) else {}

    generated = result.get("generated") or []
    rejected = result.get("rejected") or []
    eligible = result.get("eligible") or []
    top = list(result.get("eligible_ranked") or [])[:10]

    gate_counts: Counter[str] = Counter()
    for p in rejected:
        failed = (p.get("eligibility") or {}).get("failed_gates") or []
        if failed:
            for g in failed:
                gate_counts[str(g)] += 1
        else:
            gate_counts["(no failed_gates listed)"] += 1

    header = [
        "CHECK ALS — FINAL CONCEPT TEST",
        "",
        f"Raw generated: {orch.get('raw_generated', stats.get('raw_generated', 0))}",
        f"Raw unique: {orch.get('raw_unique', stats.get('unique_after_dedupe', 0))}",
        f"Expansion attempts: {orch.get('expansion_attempts', 0)}",
        f"Expansion success: {orch.get('expansion_success', len(generated))}",
        f"Expansion failed: {orch.get('expansion_failed', stats.get('expand_failures', 0))}",
        f"Replacement seeds: {orch.get('replacement_seeds', 0)}",
        "",
        f"Raw requested: {orch.get('raw_generated', stats.get('raw_requested', 0))}",
        f"Raw received: {orch.get('raw_unique', stats.get('raw_received', 0))}",
        f"Unique after dedupe: {orch.get('raw_unique', stats.get('unique_after_dedupe', 0))}",
        f"Expanded: {orch.get('expansion_success', len(generated))}",
        f"Repaired: {stats['repaired']}",
        f"Rejected: {len(rejected)}",
        f"Eligible: {len(eligible)}",
        f"Top returned: {len(top)}",
        "",
        f"LLM calls: {stats['llm_calls']}",
        f"Retries: {stats['retries']}",
        f"Failures: {stats['failures']}",
        f"Total runtime: {runtime:.1f}s ({runtime / 60:.1f} min)",
        "",
        f"model: {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}",
        f"content_format: check_als",
        "",
        "REJECTION BREAKDOWN",
        "",
    ]
    if not gate_counts:
        header.append("(ningún rechazo)")
    else:
        for g, n in gate_counts.most_common():
            header.append(f"{g} → {n}")
        header.append("")
        header.append("Rejected titles:")
        for p in rejected:
            failed = ", ".join((p.get("eligibility") or {}).get("failed_gates") or [])
            header.append(f"- {p.get('title')}: {failed}")

    chunks = ["\n".join(header), "", "TOP 10", ""]
    for i, p in enumerate(top, 1):
        chunks.append(format_concept(i, p))
    chunks.append("")
    chunks.append(diversity_report(top))
    chunks.append("")
    chunks.append(
        "EDITORIAL SELF-CHECK\n\n"
        "(se completa en el informe de corrida tras leer cada paquete; el motor no auto-aprueba calidad editorial.)"
    )

    text = "\n".join(chunks)
    out_txt = ROOT / "docs" / "check-als-phase1-6-1-console-test.txt"
    out_json = ROOT / "docs" / "check-als-phase1-6-1-console-test.json"
    out_txt.write_text(text, encoding="utf-8")
    out_json.write_text(
        json.dumps(
            {
                "orchestration": orch,
                "stats": {**stats, "runtime_sec": runtime, **orch},
                "counts": result.get("counts"),
                "gate_counts": dict(gate_counts),
                "rejected": [
                    {
                        "title": p.get("title"),
                        "failed_gates": (p.get("eligibility") or {}).get("failed_gates"),
                        "reasons": (p.get("eligibility") or {}).get("reasons"),
                        "rewards_n": len(p.get("rewards") or []),
                        "reward_types": sorted({str((r or {}).get("type")) for r in (p.get("rewards") or []) if isinstance(r, dict)}),
                    }
                    for p in rejected
                ],
                "top10": top,
                "generated_titles": [p.get("title") for p in generated],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(text)
    print("wrote", out_txt)
    print("wrote", out_json)


if __name__ == "__main__":
    main()
