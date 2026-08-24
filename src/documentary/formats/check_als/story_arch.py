"""Check ALS Fase 2: world / story / progression state, deltas, persistence, review."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from src.documentary.project import append_log, project_dir, save_project

METADATA_FILES = {
    "story_blueprint": "story_blueprint.json",
    "world_state": "world_state.json",
    "story_state": "story_state.json",
    "progression_state": "progression_state.json",
    "beats": "beats.json",
    "story_quality": "story_quality.json",
    "story_review": "story_review.json",
}

PROGRESSION_KEYS = (
    "wealth_level",
    "ownership_level",
    "business_scale",
    "status_level",
    "freedom_level",
    "lifestyle_level",
    "family_impact",
    "environment_level",
    "network_level",
    "power_level",
)

METRIC_PATHS = {
    "AGE": "time.protagonist_age",
    "CASH": "personal.cash",
    "TEAM_VALUE": "team.valuation",
    "OWNERSHIP": "team.ownership_percentage",
    "TEAM_DEBT": "team.debt",
    "ATTENDANCE": "team.attendance",
    "RECORD": "team.season_record",
    "REVENUE": "team.revenue_monthly",
}

DELTA_ALIASES = {
    "cash": "life.personal_cash",
    "net_worth": "life.personal_net_worth",
    "income": "life.salary",
    "personal_debt": "personal.debt",
    "team_debt": "finance.team_debt",
    "team_cash": "finance.team_cash",
    "revenue": "finance.annual_revenue",
    "expenses": "finance.annual_expenses",
    "attendance": "team.attendance",
    "employees": "team.employees",
    "age": "time.protagonist_age",
    "elapsed_days": "time.elapsed_days",
}

MONEY_WORDS = (
    "pago",
    "paga",
    "firma",
    "deuda",
    "sueldo",
    "salario",
    "sponsor",
    "patrocin",
    "venta",
    "préstamo",
    "prestamo",
    "caja",
    "efectivo",
    "ahorro",
    "inversión",
    "inversion",
    "cheque",
    "contrato",
    "anticipo",
    "earn-out",
    "earnout",
    "financi",
    "ticket",
    "entrada",
    "taquilla",
    "tv",
    "derechos",
    "bonus",
    "nómina",
    "nomina",
)


def empty_world_state() -> dict[str, Any]:
    return {
        "time": {
            "protagonist_age": 22,
            "date_or_period": "",
            "elapsed_days": 0,
            "label": "DAY 1",
        },
        "personal": {
            "cash": 0,
            "net_worth": 0,
            "income_monthly": 0,
            "debt": 0,
            "living_situation": "",
            "working_status": "",
            "free_time": "",
        },
        "team": {
            "name": "",
            "league": "",
            "city": "",
            "ownership_percentage": 0,
            "valuation": 0,
            "debt": 0,
            "cash": 0,
            "revenue_monthly": 0,
            "expenses_monthly": 0,
            "attendance": 0,
            "capacity": 0,
            "season_record": {"wins": 0, "losses": 0},
            "league_position": "",
            "employees": 0,
            "roster_quality": 0,
            "facilities_quality": 0,
            "fanbase": 0,
            "sponsors": 0,
        },
        "assets": {
            "properties": [],
            "vehicles": [],
            "investments": [],
            "ownerships": [],
        },
        "relationships": {
            "family": [],
            "business_partners": [],
            "coach": "",
            "key_players": [],
            "rivals": [],
        },
        "locations": {
            "home": "",
            "office": "",
            "arena": "",
            "training_facility": "",
            "important_places": [],
        },
        "introduced_characters": [],
        "introduced_locations": [],
        "ownership_ledger": {"protagonist": 0.0, "investors": 0.0, "seller": 100.0},
        "finance": {
            "team_cash": 0,
            "team_debt": 650000,
            "annual_revenue": 220000,
            "annual_expenses": 310000,
            "ticket_revenue": 140000,
            "sponsorship_revenue": 20000,
            "merch_revenue": 15000,
            "media_revenue": 0,
            "payroll": 210000,
            "facility_costs": 90000,
            "debt_service": 52000,
            "debt_risk_state": "critical",
            "credit_line": 0,
            "overdraft_allowed": False,
            "financing_open": False,
        },
        "sports": {
            "current_season": 1,
            "season": 1,
            "season_year": 1,
            "season_label": "Temporada 1",
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "win_pct": 0.0,
            "win_percentage": 0.0,
            "league_position": "fondo de tabla",
            "regular_season_status": "preseason",
            "playoff_status": "regular",
            "playoff_round": "",
            "championships": 0,
            "coach": "interino",
            "coach_quality": 2,
            "roster_quality": 2,
            "star_players": [],
            "injuries": [],
            "team_morale": 4,
            "recent_form": "",
            "season_history": [],
            "playoff_history": [],
            "historical_records": [],
        },
        "life": {
            "home": "departamento compartido",
            "job": "empleado de oficina",
            "salary": 10800,
            "personal_cash": 18400,
            "personal_net_worth": 18400,
            "weekly_work_hours": 45,
            "freedom": 2,
            "family_support": 5,
            "status": 1,
            "network": 2,
            "transport": "colectivo y a pie",
            "lifestyle": "vida normal, básquet los fines de semana",
        },
        "acquisition": {
            "asking_price": 1,
            "debt_assumed": 650000,
            "your_cash_contribution": 0,
            "local_investors_cash": 0,
            "seller_financing": 0,
            "existing_liabilities_assumed": 0,
            "your_ownership": 0,
            "investor_ownership": 0,
            "seller_retained": 100,
            "closed": False,
            "summary": "",
        },
        "milestones": [],
        "equity_events": [],
        "financial_events": [],
        "debt_risk_history": [],
    }


def empty_story_state() -> dict[str, Any]:
    return {
        "current_goal": "",
        "current_problem": "",
        "current_stakes": "",
        "active_conflicts": [],
        "open_loops": [],
        "promises_to_viewer": [],
        "pending_decisions": [],
        "threats": [],
        "opportunities": [],
        "relationships_in_tension": [],
        "information_protagonist_knows": [],
        "information_viewer_knows": [],
        "emotional_state": "",
        "momentum": "",
    }


def empty_progression_state() -> dict[str, Any]:
    return {k: 0 for k in PROGRESSION_KEYS}


def empty_open_loop(loop_id: str, question: str, opened_at: str, payoff_target: str = "") -> dict[str, Any]:
    return {
        "id": loop_id,
        "question": question,
        "opened_at": opened_at,
        "status": "open",
        "payoff_target": payoff_target,
        "closed_at": "",
        "expected_payoff_window": "",
        "paid_at": "",
        "payoff": "",
        "important": True,
        "intentional_unresolved": False,
    }


def empty_blueprint() -> dict[str, Any]:
    return {
        "protagonist": {
            "age": 22,
            "starting_life": "",
            "personality": "",
            "skills": [],
            "weaknesses": [],
            "desire": "",
            "emotional_need": "",
        },
        "fantasy": {
            "surface_desire": "",
            "deeper_desire": "",
            "promised_transformation": "",
        },
        "business_or_vehicle": {
            "what_is_being_built_or_owned": "",
            "core_mechanism": "",
            "economic_engine": "",
            "acquisition_structure": "",
            "acquisition": {},
        },
        "fiction_world": {
            "team_name": "",
            "league_name": "",
            "city": "",
            "disclaimer": "Ficción aspiracional. Equipo, liga y hechos son inventados.",
        },
        "opening": {"situation": "", "immediate_problem": "", "curiosity": ""},
        "inciting_incident": "",
        "first_commitment": "",
        "first_proof": "",
        "escalation": "",
        "midpoint": "",
        "major_success": "",
        "major_reversal": "",
        "crisis": "",
        "decision": "",
        "climax": "",
        "ending": "",
        "final_state": "",
        "unresolved_or_bittersweet_element": "",
        "ending_type": "triumphant",
        "intentional_unresolved_loops": [],
        "causal_chain": [],
    }


def empty_beat(beat_id: str = "b01") -> dict[str, Any]:
    return {
        "beat_id": beat_id,
        "time": "",
        "duration_target_s": 15,
        "cause": "",
        "event": "",
        "consequence": "",
        "story_purpose": "",
        "world_delta": {},
        "ops": [],
        "story_delta": {},
        "progression_delta": {},
        "world_state_before": {},
        "world_state_after": {},
        "story_state_before": {},
        "story_state_after": {},
        "progression_before": {},
        "progression_after": {},
        "emotional_goal": "",
        "viewer_question": "",
        "open_loop_action": {},
        "reward_or_setback": "",
        "metric_reveal": [],
        "visual_opportunity": "",
        "transition_to_next": "",
        "aspirational_payoffs": [],
        "contribution": "",
    }


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _get_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _set_path(obj: dict[str, Any], path: str, value: Any) -> None:
    parts = [p for p in path.split(".") if p]
    cur: dict[str, Any] = obj
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    if parts:
        cur[parts[-1]] = value


def resolve_delta_path(key: str) -> str:
    raw = str(key or "").strip()
    if not raw:
        return raw
    return DELTA_ALIASES.get(raw, raw)


def apply_field(current: Any, delta_val: Any, *, path: str = "") -> Any:
    if delta_val is None:
        return current
    if isinstance(delta_val, dict) and any(k in delta_val for k in ("set", "add", "remove")):
        if "set" in delta_val:
            return deepcopy(delta_val["set"])
        out = deepcopy(current)
        if "add" in delta_val:
            added = delta_val["add"]
            if _is_number(out) and _is_number(added):
                out = out + added
            elif isinstance(out, list):
                items = added if isinstance(added, list) else [added]
                for item in items:
                    if item not in out:
                        out.append(deepcopy(item))
            elif isinstance(out, str) and added:
                out = str(added)
            else:
                out = deepcopy(added)
        if "remove" in delta_val and isinstance(out, list):
            rm = delta_val["remove"]
            items = rm if isinstance(rm, list) else [rm]
            out = [x for x in out if x not in items]
        return out
    if isinstance(delta_val, dict) and isinstance(current, dict):
        out = deepcopy(current)
        for k, v in delta_val.items():
            out[k] = apply_field(out.get(k), v, path=f"{path}.{k}" if path else k)
        return out
    if path.endswith("protagonist_age") or path == "time.protagonist_age":
        return _apply_age(current, delta_val)
    if _is_number(delta_val) and _is_number(current):
        return current + delta_val
    if isinstance(delta_val, list) and isinstance(current, list):
        out = deepcopy(current)
        for item in delta_val:
            if item not in out:
                out.append(deepcopy(item))
        return out
    return deepcopy(delta_val)


def _apply_age(current: Any, delta_val: Any) -> int:
    cur = int(current or 0)
    if isinstance(delta_val, dict) and "set" in delta_val:
        return int(delta_val["set"])
    if not _is_number(delta_val):
        return cur
    d = int(delta_val)
    if 16 <= d <= 80 and abs(d - cur) <= 12:
        return d
    return cur + d


def normalize_world_delta(delta: Any) -> dict[str, Any]:
    if not isinstance(delta, dict):
        return {}
    nested: dict[str, Any] = {}
    for key, val in delta.items():
        path = resolve_delta_path(key)
        if "." in path or path in (
            "time",
            "personal",
            "team",
            "assets",
            "relationships",
            "locations",
            "finance",
            "sports",
            "life",
            "acquisition",
        ):
            if "." in path:
                _set_path(nested, path, deepcopy(val))
            else:
                cur = nested.get(path)
                if isinstance(cur, dict) and isinstance(val, dict):
                    nested[path] = {**cur, **deepcopy(val)}
                else:
                    nested[path] = deepcopy(val)
        else:
            nested[path] = deepcopy(val)
    return nested


def apply_world_delta(state: dict[str, Any], delta: Any) -> dict[str, Any]:
    base = deepcopy(state) if state else empty_world_state()
    nd = normalize_world_delta(delta)
    for key, val in nd.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict) and "set" not in val:
            base[key] = apply_field(base[key], val, path=key)
        else:
            base[key] = apply_field(base.get(key), val, path=key)
    return base


def apply_story_delta(state: dict[str, Any], delta: Any, *, beat_id: str = "") -> dict[str, Any]:
    base = deepcopy(state) if state else empty_story_state()
    if not isinstance(delta, dict):
        return base
    loops = list(base.get("open_loops") or [])
    action = delta.get("open_loop_action") if isinstance(delta.get("open_loop_action"), dict) else {}
    if action:
        loops = _apply_loop_action(loops, action, beat_id)
    for key, val in delta.items():
        if key in ("open_loop_action", "open_loops"):
            continue
        if key in (
            "active_conflicts",
            "promises_to_viewer",
            "pending_decisions",
            "threats",
            "opportunities",
            "relationships_in_tension",
            "information_protagonist_knows",
            "information_viewer_knows",
        ):
            base[key] = apply_field(base.get(key) or [], val, path=key)
        else:
            base[key] = apply_field(base.get(key), val, path=key)
    extra_loops = delta.get("open_loops")
    if isinstance(extra_loops, list):
        for loop in extra_loops:
            if isinstance(loop, dict) and loop.get("id"):
                loops = _upsert_loop(loops, loop, beat_id)
            elif isinstance(loop, str) and loop.strip():
                loops = _upsert_loop(
                    loops,
                    empty_open_loop(_slug(loop), loop.strip(), beat_id),
                    beat_id,
                )
    base["open_loops"] = loops
    return base


def apply_progression_delta(state: dict[str, Any], delta: Any) -> dict[str, Any]:
    base = empty_progression_state()
    if isinstance(state, dict):
        for k in PROGRESSION_KEYS:
            try:
                base[k] = int(state.get(k) or 0)
            except (TypeError, ValueError):
                base[k] = 0
    if not isinstance(delta, dict):
        return _clamp_progression(base)
    for k in PROGRESSION_KEYS:
        if k not in delta:
            continue
        val = delta[k]
        cur = base[k]
        if isinstance(val, dict) and "set" in val:
            base[k] = int(val["set"])
            continue
        if not _is_number(val):
            continue
        d = int(val)
        if abs(d) <= 3:
            base[k] = cur + d
        elif 0 <= d <= 10:
            base[k] = d
        else:
            base[k] = cur + d
    return _clamp_progression(base)


def _clamp_progression(state: dict[str, Any]) -> dict[str, Any]:
    out = dict(state)
    for k in PROGRESSION_KEYS:
        try:
            n = int(out.get(k) or 0)
        except (TypeError, ValueError):
            n = 0
        out[k] = max(0, min(10, n))
    return out


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:40] or "loop")


def _apply_loop_action(loops: list[dict[str, Any]], action: dict[str, Any], beat_id: str) -> list[dict[str, Any]]:
    kind = str(action.get("action") or action.get("op") or "").strip().lower()
    loop_id = str(action.get("loop_id") or action.get("id") or "").strip()
    question = str(action.get("question") or "").strip()
    if not loop_id and question:
        loop_id = _slug(question)
    if kind in ("open", "reopen", "update") or (not kind and (loop_id or question)):
        payload = empty_open_loop(
            loop_id or _slug(question or beat_id),
            question or loop_id,
            str(action.get("opened_at") or beat_id),
            str(action.get("payoff_target") or ""),
        )
        if kind == "reopen":
            payload["status"] = "open"
        return _upsert_loop(loops, payload, beat_id)
    if kind in ("close", "pay", "paid", "payoff") and loop_id:
        out = []
        for loop in loops:
            row = dict(loop)
            if str(row.get("id") or "") == loop_id:
                row["status"] = "paid"
                row["closed_at"] = beat_id
            out.append(row)
        return out
    if kind in ("abandon", "drop") and loop_id:
        out = []
        for loop in loops:
            row = dict(loop)
            if str(row.get("id") or "") == loop_id:
                row["status"] = "abandoned"
                row["closed_at"] = beat_id
            out.append(row)
        return out
    return loops


def _upsert_loop(loops: list[dict[str, Any]], payload: dict[str, Any], beat_id: str) -> list[dict[str, Any]]:
    lid = str(payload.get("id") or "").strip()
    out = []
    found = False
    for loop in loops:
        if str(loop.get("id") or "") == lid:
            row = dict(loop)
            row.update({k: v for k, v in payload.items() if v not in ("", None, [], {})})
            row["id"] = lid
            if not row.get("opened_at"):
                row["opened_at"] = beat_id
            out.append(row)
            found = True
        else:
            out.append(loop)
    if not found:
        row = dict(payload)
        row["id"] = lid
        row.setdefault("opened_at", beat_id)
        row.setdefault("status", "open")
        out.append(row)
    return out


def world_snapshot(world: dict[str, Any]) -> dict[str, Any]:
    from src.documentary.formats.check_als.story_sim import derive_world

    w = derive_world(world) if world else empty_world_state()
    sports = w.get("sports") or {}
    life = w.get("life") or {}
    fin = w.get("finance") or {}
    rec = f"{int(sports.get('wins') or 0)}-{int(sports.get('losses') or 0)}"
    hist = sports.get("season_history") or []
    sporting = sports.get("playoff_status")
    if int(sports.get("games_played") or 0) <= 0 and hist:
        rec = f"{hist[-1].get('record')} (offseason)"
        sporting = hist[-1].get("playoff_result") or sporting
    return {
        "age": (w.get("time") or {}).get("protagonist_age"),
        "time": (w.get("time") or {}).get("label") or (w.get("time") or {}).get("date_or_period"),
        "cash": life.get("personal_cash"),
        "net_worth": life.get("personal_net_worth"),
        "job": life.get("job"),
        "home": life.get("home"),
        "ownership": (w.get("ownership_ledger") or {}).get("protagonist"),
        "ledger": dict(w.get("ownership_ledger") or {}),
        "team_value": (w.get("team") or {}).get("valuation"),
        "team_debt": fin.get("team_debt"),
        "team_cash": fin.get("team_cash"),
        "revenue": fin.get("annual_revenue"),
        "attendance": (w.get("team") or {}).get("attendance"),
        "record": rec,
        "sports_status": sporting,
        "sporting_status": sporting,
        "season": sports.get("season_label") or sports.get("season"),
        "debt_risk_state": fin.get("debt_risk_state"),
        "championships": sports.get("championships"),
    }


def metric_value(world: dict[str, Any], name: str) -> Any:
    path = METRIC_PATHS.get(name.upper())
    if not path:
        return None
    val = _get_path(world, path)
    if name.upper() == "RECORD" and isinstance(val, dict):
        return f"{int(val.get('wins') or 0)}-{int(val.get('losses') or 0)}"
    return val


def reconstruct_beats(
    initial_world: dict[str, Any],
    initial_story: dict[str, Any],
    initial_prog: dict[str, Any],
    beats: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    from src.documentary.formats.check_als.story_sim import (
        _archive_season,
        apply_ops,
        derive_world,
        detect_payoffs,
        infer_ops_from_beat,
        sanitize_world_delta,
    )

    world = derive_world(deepcopy(initial_world) if initial_world else empty_world_state())
    story = deepcopy(initial_story) if initial_story else empty_story_state()
    prog = deepcopy(initial_prog) if initial_prog else empty_progression_state()
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(beats or []):
        beat = {**empty_beat(f"b{i+1:02d}"), **(raw if isinstance(raw, dict) else {})}
        beat_id = str(beat.get("beat_id") or f"b{i+1:02d}")
        beat["beat_id"] = beat_id
        loop_action = beat.get("open_loop_action") if isinstance(beat.get("open_loop_action"), dict) else {}
        story_delta = beat.get("story_delta") if isinstance(beat.get("story_delta"), dict) else {}
        if loop_action and "open_loop_action" not in story_delta:
            story_delta = {**story_delta, "open_loop_action": loop_action}
        ops = infer_ops_from_beat(beat, world)
        beat["ops"] = ops
        before_w, before_s, before_p = deepcopy(world), deepcopy(story), deepcopy(prog)
        world = apply_world_delta(world, sanitize_world_delta(beat.get("world_delta") or {}))
        world = apply_ops(world, ops, beat_id=beat_id)
        world = derive_world(world)
        if i == len(beats or []) - 1:
            _archive_season(world, major_event="estado final")
            world = derive_world(world)
        payoffs = detect_payoffs(before_w, world)
        if payoffs:
            beat["aspirational_payoffs"] = payoffs
            if not str(beat.get("reward_or_setback") or "").strip():
                beat["reward_or_setback"] = f"reward:{payoffs[0].get('id')}"
        story = apply_story_delta(story, story_delta, beat_id=beat_id)
        prog = apply_progression_delta(prog, beat.get("progression_delta") or {})
        beat["world_state_before"] = before_w
        beat["world_state_after"] = world
        beat["story_state_before"] = before_s
        beat["story_state_after"] = story
        beat["progression_before"] = before_p
        beat["progression_after"] = prog
        beat["world_snapshot"] = world_snapshot(world)
        out.append(beat)
    return out


def architecture_summary(payload: dict[str, Any]) -> dict[str, Any]:
    beats = payload.get("beats") if isinstance(payload.get("beats"), list) else []
    synopsis = str(payload.get("synopsis") or "")
    words = len(re.findall(r"\S+", synopsis))
    return {
        "generated": True,
        "beat_count": len(beats),
        "synopsis_words": words,
        "approved": bool(payload.get("approved")),
        "title": str((payload.get("blueprint") or {}).get("fiction_world", {}).get("team_name") or ""),
    }


def persist_architecture(project: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    pid = str(project.get("id") or "").strip()
    if not pid:
        raise ValueError("project.id required")
    root = project_dir(pid)
    meta = root / "metadata"
    meta.mkdir(parents=True, exist_ok=True)

    blueprint = payload.get("blueprint") if isinstance(payload.get("blueprint"), dict) else empty_blueprint()
    initial_world = payload.get("initial_world") if isinstance(payload.get("initial_world"), dict) else empty_world_state()
    initial_story = payload.get("initial_story") if isinstance(payload.get("initial_story"), dict) else empty_story_state()
    initial_prog = payload.get("initial_progression") if isinstance(payload.get("initial_progression"), dict) else empty_progression_state()
    beats = reconstruct_beats(initial_world, initial_story, initial_prog, payload.get("beats") or [])
    final_world = beats[-1]["world_state_after"] if beats else initial_world
    final_story = beats[-1]["story_state_after"] if beats else initial_story
    final_prog = beats[-1]["progression_after"] if beats else initial_prog
    quality = payload.get("quality") if isinstance(payload.get("quality"), dict) else {}
    synopsis = str(payload.get("synopsis") or "")
    review = payload.get("review") if isinstance(payload.get("review"), dict) else {}

    compact_beats = []
    for b in beats:
        compact_beats.append(
            {
                **{k: b.get(k) for k in (
                    "beat_id",
                    "time",
                    "duration_target_s",
                    "cause",
                    "event",
                    "consequence",
                    "story_purpose",
                    "world_delta",
                    "ops",
                    "story_delta",
                    "progression_delta",
                    "emotional_goal",
                    "viewer_question",
                    "open_loop_action",
                    "reward_or_setback",
                    "metric_reveal",
                    "visual_opportunity",
                    "transition_to_next",
                    "world_snapshot",
                    "aspirational_payoffs",
                    "contribution",
                )},
            }
        )

    files = {
        "story_blueprint.json": blueprint,
        "world_state.json": {"initial": initial_world, "final": final_world},
        "story_state.json": {"initial": initial_story, "final": final_story},
        "progression_state.json": {"initial": initial_prog, "final": final_prog},
        "beats.json": {
            "initial_world": initial_world,
            "initial_story": initial_story,
            "initial_progression": initial_prog,
            "beats": compact_beats,
        },
        "story_quality.json": quality,
        "story_review.json": review,
    }
    for name, data in files.items():
        (meta / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (meta / "story_synopsis.md").write_text(synopsis.strip() + "\n", encoding="utf-8")

    approved = bool(payload.get("approved") or project.get("check_story_approved"))
    summary = architecture_summary({**payload, "beats": beats, "synopsis": synopsis, "approved": approved})
    project["check_story"] = summary
    project["check_story_approved"] = approved
    project["ui_step"] = "story"
    project["story_plan_approved"] = False
    save_project(project)
    append_log(pid, f"check_story architecture beats={len(beats)} words={summary['synopsis_words']}")
    return project


def load_architecture(project: dict[str, Any]) -> dict[str, Any]:
    pid = str(project.get("id") or "").strip()
    empty = {
        "blueprint": empty_blueprint(),
        "initial_world": empty_world_state(),
        "initial_story": empty_story_state(),
        "initial_progression": empty_progression_state(),
        "beats": [],
        "quality": {},
        "review": {},
        "synopsis": "",
        "approved": bool(project.get("check_story_approved")),
        "generated": False,
    }
    if not pid:
        return empty
    meta = project_dir(pid) / "metadata"

    def _ensure_meta() -> None:
        # On Vercel, cold lambdas only have what we pull — story lives under metadata/.
        if (meta / "beats.json").is_file() or (meta / "story_synopsis.md").is_file():
            return
        try:
            from src.documentary.runtime import on_vercel
            from src.documentary import cloud_sync

            if on_vercel() and cloud_sync.configured():
                cloud_sync.pull_project(pid, light=True)
                for name in (
                    "beats.json",
                    "story_blueprint.json",
                    "world_state.json",
                    "story_synopsis.md",
                    "story_review.json",
                    "story_quality.json",
                ):
                    cloud_sync.pull_one(pid, f"metadata/{name}", force=False)
        except Exception:
            pass

    _ensure_meta()

    def _read(name: str, default: Any) -> Any:
        path = meta / name
        if not path.is_file():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    blueprint = _read("story_blueprint.json", {})
    world = _read("world_state.json", {})
    story = _read("story_state.json", {})
    prog = _read("progression_state.json", {})
    beats_file = _read("beats.json", {})
    quality = _read("story_quality.json", {})
    review = _read("story_review.json", {})
    syn_path = meta / "story_synopsis.md"
    synopsis = syn_path.read_text(encoding="utf-8") if syn_path.is_file() else ""

    initial_world = world.get("initial") if isinstance(world, dict) else None
    initial_story = story.get("initial") if isinstance(story, dict) else None
    initial_prog = prog.get("initial") if isinstance(prog, dict) else None
    raw_beats = beats_file.get("beats") if isinstance(beats_file, dict) else []
    if isinstance(beats_file, dict) and beats_file.get("initial_world"):
        initial_world = beats_file.get("initial_world")
        initial_story = beats_file.get("initial_story")
        initial_prog = beats_file.get("initial_progression")
    beats = reconstruct_beats(
        initial_world or empty_world_state(),
        initial_story or empty_story_state(),
        initial_prog or empty_progression_state(),
        raw_beats if isinstance(raw_beats, list) else [],
    )
    generated = bool(beats or (isinstance(blueprint, dict) and blueprint.get("inciting_incident")) or synopsis.strip())
    return {
        "blueprint": blueprint if isinstance(blueprint, dict) else empty_blueprint(),
        "initial_world": initial_world or empty_world_state(),
        "initial_story": initial_story or empty_story_state(),
        "initial_progression": initial_prog or empty_progression_state(),
        "final_world": (world.get("final") if isinstance(world, dict) else None) or (beats[-1]["world_state_after"] if beats else empty_world_state()),
        "final_story": (story.get("final") if isinstance(story, dict) else None) or (beats[-1]["story_state_after"] if beats else empty_story_state()),
        "final_progression": (prog.get("final") if isinstance(prog, dict) else None) or (beats[-1]["progression_after"] if beats else empty_progression_state()),
        "beats": beats,
        "quality": quality if isinstance(quality, dict) else {},
        "review": review if isinstance(review, dict) else {},
        "synopsis": synopsis,
        "approved": bool(project.get("check_story_approved")),
        "generated": generated,
    }


def format_money(n: Any) -> str:
    try:
        v = float(n)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000:
        return f"{sign}${v/1_000_000:.2f}M"
    if v >= 1000:
        return f"{sign}${v:,.0f}"
    return f"{sign}${v:,.0f}"


def collect_named_entities(world: dict[str, Any]) -> tuple[set[str], set[str]]:
    chars: set[str] = set()
    locs: set[str] = set()
    for item in world.get("introduced_characters") or []:
        if isinstance(item, str) and item.strip():
            chars.add(item.strip().lower())
        elif isinstance(item, dict) and item.get("name"):
            chars.add(str(item["name"]).strip().lower())
    rel = world.get("relationships") if isinstance(world.get("relationships"), dict) else {}
    for key, val in rel.items():
        if isinstance(val, str) and val.strip() and key != "coach":
            pass
        if isinstance(val, str) and val.strip():
            chars.add(val.strip().lower())
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.strip():
                    chars.add(item.strip().lower())
                elif isinstance(item, dict) and item.get("name"):
                    chars.add(str(item["name"]).strip().lower())
    for item in world.get("introduced_locations") or []:
        if isinstance(item, str) and item.strip():
            locs.add(item.strip().lower())
    loc = world.get("locations") if isinstance(world.get("locations"), dict) else {}
    for key, val in loc.items():
        if isinstance(val, str) and val.strip():
            locs.add(val.strip().lower())
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.strip():
                    locs.add(item.strip().lower())
    return chars, locs
