"""Check ALS Fase 2.2: simulation engine. World state participates in the story."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

LEDGER_KEYS = ("protagonist", "investors", "seller")

ENDINGS_ASPIRATIONAL = ("triumphant", "open_future", "comeback", "empire_continues")

FINANCING_TYPES = (
    "credit_line",
    "overdraft",
    "bridge_loan",
    "owner_injection",
    "investor_injection",
    "loan",
)

PURPLE_PROSE = (
    r"tu coraz[oó]n late con fuerza",
    r"luz al final del t[uú]nel",
    r"pu[nñ]alada en el coraz[oó]n",
    r"cielo estrellado",
    r"sue[nñ]o tan lejano",
    r" explosi[oó]n de alegr[ií]a",
    r"herida abierta",
    r"sabor amargo se asienta",
    r"el camino no es de rosas",
    r"la emoci[oó]n es palpable",
    r"s[ií]mbolo de perseverancia",
    r"trabajo duro",
    r"tu sue[nñ]o cobra vida",
    r"una nueva vida llena de posibilidades",
    r"la emoci[oó]n es indescriptible",
    r"finalmente sent[ií]s que todo vali[oó] la pena",
    r"el coraz[oó]n late",
)

CHAMPIONSHIP_WORDS = (
    "campeonat",
    "campeón",
    "campeon",
    "anillo",
    "ganás la liga",
    "ganas la liga",
    "title",
)

SETBACK_CATEGORIES = (
    "sports",
    "financial",
    "ownership",
    "facilities",
    "staff",
    "media",
    "sponsor",
    "fanbase",
    "regulatory",
    "personal",
)

SETBACK_OP_CATEGORY = {
    "injury": "sports",
    "playoff_eliminated": "sports",
    "game_lost": "sports",
    "lose_game": "sports",
    "sponsor_cut": "sponsor",
    "sponsor_lost": "sponsor",
    "facility_issue": "facilities",
    "coach_fired": "staff",
    "staff_walk": "staff",
    "media_crisis": "media",
    "fan_unrest": "fanbase",
    "regulatory_fine": "regulatory",
    "owner_crisis": "ownership",
    "equity_sale": "ownership",
    "personal_crisis": "personal",
}


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v: Any, default: int = 0) -> int:
    return int(round(_num(v, default)))


def empty_ownership_ledger() -> dict[str, float]:
    return {"protagonist": 0.0, "investors": 0.0, "seller": 100.0}


def empty_finance() -> dict[str, Any]:
    return {
        "team_cash": 0,
        "team_debt": 0,
        "annual_revenue": 0,
        "annual_expenses": 0,
        "ticket_revenue": 0,
        "sponsorship_revenue": 0,
        "merch_revenue": 0,
        "media_revenue": 0,
        "payroll": 180000,
        "facility_costs": 90000,
        "debt_service": 0,
        "debt_risk_state": "critical",
        "credit_line": 0,
        "overdraft_allowed": False,
        "financing_open": False,
    }


def empty_sports() -> dict[str, Any]:
    return {
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
    }


def empty_life() -> dict[str, Any]:
    return {
        "home": "departamento compartido",
        "job": "empleado de oficina",
        "salary": 10800,
        "personal_cash": 18000,
        "personal_net_worth": 18000,
        "weekly_work_hours": 45,
        "freedom": 2,
        "family_support": 5,
        "status": 1,
        "network": 2,
        "transport": "colectivo y a pie",
        "lifestyle": "vida normal, básquet los fines de semana",
    }


def empty_acquisition() -> dict[str, Any]:
    return {
        "asking_price": 1,
        "debt_assumed": 0,
        "your_cash_contribution": 0,
        "local_investors_cash": 0,
        "seller_financing": 0,
        "existing_liabilities_assumed": 0,
        "your_ownership": 0,
        "investor_ownership": 0,
        "seller_retained": 0,
        "closed": False,
        "summary": "",
    }


def ledger_total(ledger: dict[str, Any]) -> float:
    return round(sum(_num(v) for v in (ledger or {}).values()), 4)


def normalize_ledger(ledger: dict[str, Any] | None) -> dict[str, float]:
    raw = dict(ledger or empty_ownership_ledger())
    out = {k: round(_num(raw.get(k)), 2) for k in LEDGER_KEYS}
    for k, v in raw.items():
        if k not in out:
            out[k] = round(_num(v), 2)
    total = ledger_total(out)
    if total <= 0:
        return empty_ownership_ledger()
    if abs(total - 100.0) > 0.2:
        factor = 100.0 / total
        for k in list(out):
            out[k] = round(out[k] * factor, 2)
        drift = round(100.0 - ledger_total(out), 2)
        pivot = "seller" if "seller" in out else next(iter(out))
        out[pivot] = round(out[pivot] + drift, 2)
    return out


def transfer_equity(ledger: dict[str, Any], src: str, dst: str, pct: float) -> dict[str, float]:
    out = normalize_ledger(ledger)
    src = str(src or "seller")
    dst = str(dst or "protagonist")
    if src not in out:
        out[src] = 0.0
    if dst not in out:
        out[dst] = 0.0
    take = min(max(_num(pct), 0.0), out[src])
    out[src] = round(out[src] - take, 2)
    out[dst] = round(out[dst] + take, 2)
    return normalize_ledger(out)


def estimate_valuation(world: dict[str, Any]) -> int:
    fin = world.get("finance") or empty_finance()
    sports = world.get("sports") or empty_sports()
    team = world.get("team") or {}
    ledger = world.get("ownership_ledger") or empty_ownership_ledger()
    rev = max(0.0, _num(fin.get("annual_revenue")))
    profit = rev - max(0.0, _num(fin.get("annual_expenses")))
    att = max(0.0, _num(team.get("attendance")))
    cap = max(1.0, _num(team.get("capacity") or 4500))
    fill = min(1.0, att / cap)
    value = 90000.0
    value += rev * (2.4 if profit > 0 else 0.7)
    value += max(0.0, profit) * 3.5
    value += fill * 850000
    value += _num(sports.get("championships")) * 1100000
    status = str(sports.get("playoff_status") or "regular")
    if status == "playoffs":
        value += 280000
    elif status == "finals":
        value += 520000
    elif status == "champion":
        value += 900000
    hist = sports.get("season_history") or []
    if any(h.get("championship") for h in hist if isinstance(h, dict)):
        value += 250000
    value += _num(sports.get("roster_quality")) * 65000
    value += _num(sports.get("coach_quality")) * 40000
    value += _num(team.get("facilities_quality")) * 70000
    value += _num(team.get("media_attention") or 0) * 45000
    value += _num(team.get("sponsorship_interest") or 0) * 35000
    value += _num(team.get("attendance_interest") or 0) * 25000
    value += _num(fin.get("media_revenue")) * 2.2
    value += _num(fin.get("sponsorship_revenue")) * 1.6
    value -= _num(fin.get("team_debt")) * 0.28
    if _num(ledger.get("protagonist")) <= 0:
        value = min(value, 180000)
    return int(max(40000, round(value, -3)))


def derive_world(world: dict[str, Any]) -> dict[str, Any]:
    w = deepcopy(world) if world else {}
    w.setdefault("time", {})
    w.setdefault("personal", {})
    w.setdefault("team", {})
    w.setdefault("locations", {})
    w.setdefault("milestones", [])
    w["ownership_ledger"] = normalize_ledger(w.get("ownership_ledger"))
    w["finance"] = {**empty_finance(), **(w.get("finance") if isinstance(w.get("finance"), dict) else {})}
    w["sports"] = {**empty_sports(), **(w.get("sports") if isinstance(w.get("sports"), dict) else {})}
    w["life"] = {**empty_life(), **(w.get("life") if isinstance(w.get("life"), dict) else {})}
    w["acquisition"] = {**empty_acquisition(), **(w.get("acquisition") if isinstance(w.get("acquisition"), dict) else {})}
    w.setdefault("equity_events", [])
    w.setdefault("financial_events", [])
    w.setdefault("debt_risk_history", [])

    fin = w["finance"]
    sports = w["sports"]
    life = w["life"]
    team = w["team"]
    personal = w["personal"]
    loc = w["locations"]
    time = w["time"]

    rev = (
        _num(fin.get("ticket_revenue"))
        + _num(fin.get("sponsorship_revenue"))
        + _num(fin.get("merch_revenue"))
        + _num(fin.get("media_revenue"))
    )
    if rev > 0:
        fin["annual_revenue"] = int(rev)
    fin["annual_expenses"] = int(
        max(
            _num(fin.get("annual_expenses")),
            _num(fin.get("payroll")) + _num(fin.get("facility_costs")) + _num(fin.get("debt_service")),
        )
    )
    fin["debt_service"] = int(max(_num(fin.get("debt_service")), round(_num(fin.get("team_debt")) * 0.08)))
    games = max(0, _i(sports.get("games_played")))
    wins = max(0, _i(sports.get("wins")))
    losses = max(0, _i(sports.get("losses")))
    if games < wins + losses:
        games = wins + losses
    sports["games_played"] = games
    sports["wins"] = wins
    sports["losses"] = losses
    sports["win_pct"] = round(wins / games, 3) if games else 0.0
    sports["win_percentage"] = sports["win_pct"]
    sports["current_season"] = _i(sports.get("current_season") or sports.get("season") or 1)
    sports["season"] = sports["current_season"]
    sports["season_year"] = _i(sports.get("season_year") or sports["current_season"])
    if not sports.get("season_label"):
        sports["season_label"] = f"Temporada {sports['current_season']}"
    if sports["playoff_status"] not in ("playoffs", "finals", "champion", "out", "regular"):
        sports["playoff_status"] = "regular"
    sports["league_position"] = _league_position(sports)
    if games <= 0:
        if sports.get("season_history"):
            sports["regular_season_status"] = sports.get("regular_season_status") or "offseason"
        else:
            sports["regular_season_status"] = sports.get("regular_season_status") or "preseason"
    elif sports["playoff_status"] in ("playoffs", "finals", "champion", "out"):
        sports["regular_season_status"] = "complete"
    else:
        sports["regular_season_status"] = "in_progress"
    if not isinstance(sports.get("season_history"), list):
        sports["season_history"] = []
    if not isinstance(sports.get("playoff_history"), list):
        sports["playoff_history"] = []
    if not isinstance(sports.get("star_players"), list):
        sports["star_players"] = []
    if not isinstance(sports.get("injuries"), list):
        sports["injuries"] = []
    sports["team_morale"] = max(1, min(10, _i(sports.get("team_morale") or 4)))
    fin["debt_risk_state"] = compute_debt_risk(fin)

    team["ownership_percentage"] = round(_num(w["ownership_ledger"].get("protagonist")), 2)
    team["debt"] = int(_num(fin.get("team_debt")))
    team["cash"] = int(_num(fin.get("team_cash")))
    team["revenue_monthly"] = int(_num(fin.get("annual_revenue")) / 12)
    team["expenses_monthly"] = int(_num(fin.get("annual_expenses")) / 12)
    team["season_record"] = {"wins": wins, "losses": losses}
    team["roster_quality"] = sports.get("roster_quality")
    team["valuation"] = estimate_valuation(w)

    elapsed = max(0, _i(time.get("elapsed_days")))
    start_age = _i(time.get("age_at_start") or 22)
    time["age_at_start"] = start_age
    from_elapsed = start_age + elapsed // 365
    stated = _i(time.get("protagonist_age") or from_elapsed)
    if stated > from_elapsed:
        elapsed = max(elapsed, (stated - start_age) * 365)
        from_elapsed = stated
    time["elapsed_days"] = elapsed
    time["protagonist_age"] = from_elapsed
    if not time.get("label") or str(time.get("label")).startswith("AGE"):
        time["label"] = f"AGE {time['protagonist_age']}"

    stake = _num(w["ownership_ledger"].get("protagonist")) / 100.0
    equity_value = stake * _num(team.get("valuation"))
    life["personal_net_worth"] = int(_num(life.get("personal_cash")) - _num(personal.get("debt") or 0) + equity_value)
    personal["cash"] = int(_num(life.get("personal_cash")))
    personal["net_worth"] = int(life["personal_net_worth"])
    personal["income_monthly"] = int(_num(life.get("salary")) / 12)
    personal["working_status"] = life.get("job") or personal.get("working_status") or ""
    personal["living_situation"] = life.get("home") or personal.get("living_situation") or ""
    loc["home"] = life.get("home") or loc.get("home") or ""
    team["attendance_interest"] = _i(team.get("attendance_interest") or 0)
    team["sponsorship_interest"] = _i(team.get("sponsorship_interest") or 0)
    team["media_attention"] = _i(team.get("media_attention") or 0)
    w["finance"] = fin
    w["sports"] = sports
    w["life"] = life
    w["team"] = team
    w["personal"] = personal
    w["time"] = time
    w["locations"] = loc
    return w


def compute_debt_risk(fin: dict[str, Any] | None) -> str:
    fin = fin or {}
    debt = max(0.0, _num(fin.get("team_debt")))
    cash = _num(fin.get("team_cash"))
    rev = max(0.0, _num(fin.get("annual_revenue")))
    expenses = max(0.0, _num(fin.get("annual_expenses")))
    service = max(1.0, _num(fin.get("debt_service")) or debt * 0.08)
    if debt <= 0:
        return "healthy"
    profit = rev - expenses
    cash_cover = cash / service
    leverage = debt / max(rev, 1.0)
    if cash < 0 and not (fin.get("overdraft_allowed") or fin.get("financing_open") or _i(fin.get("credit_line")) > 0):
        return "critical"
    if cash < service and (rev < expenses or cash_cover < 0.5 or leverage > 2.0):
        return "critical"
    if leverage > 1.2 or cash_cover < 1.5 or (profit < 0 and cash_cover < 3):
        return "dangerous"
    if leverage < 0.35 and cash_cover >= 4 and profit > 0:
        return "healthy"
    if leverage < 0.85 and cash_cover >= 2 and (profit >= 0 or cash > service * 3):
        return "manageable"
    return "dangerous"


def _league_position(sports: dict[str, Any]) -> str:
    games = _i(sports.get("games_played"))
    wp = _num(sports.get("win_pct") or sports.get("win_percentage"))
    status = str(sports.get("playoff_status") or "regular")
    if status == "champion":
        return "campeón"
    if status == "finals":
        return "finalista"
    if status == "playoffs":
        return "playoffs"
    if games <= 0:
        return str(sports.get("league_position") or "fondo de tabla")
    if wp < 0.30:
        return "fondo de tabla"
    if wp < 0.42:
        return "mitad baja"
    if wp < 0.52:
        return "mitad de tabla"
    if wp < 0.62:
        return "pelea por playoffs"
    return "tope de tabla"


def _financing_covers(world: dict[str, Any], projected_cash: int) -> bool:
    fin = world.get("finance") or {}
    if fin.get("overdraft_allowed") or fin.get("financing_open"):
        return True
    if projected_cash < 0 and _i(fin.get("credit_line")) > 0 and projected_cash >= -_i(fin.get("credit_line")):
        return True
    types = {str(e.get("type") or "") for e in (world.get("financial_events") or []) if isinstance(e, dict)}
    return bool(types & {"credit_line", "overdraft", "bridge_loan", "owner_injection", "investor_injection"}) and projected_cash < 0


def _log_fin(
    w: dict[str, Any],
    *,
    type: str,
    amount: int = 0,
    source: str = "",
    destination: str = "",
    reason: str = "",
    cash_delta: int = 0,
    debt_delta: int = 0,
    revenue_delta: int = 0,
    expense_delta: int = 0,
    beat_id: str = "",
) -> None:
    events = list(w.get("financial_events") or [])
    time = w.get("time") or {}
    events.append(
        {
            "id": f"fe{len(events) + 1:03d}",
            "time": time.get("label") or f"AGE {time.get('protagonist_age')}",
            "elapsed_days": time.get("elapsed_days"),
            "type": type,
            "amount": abs(amount or cash_delta or debt_delta or revenue_delta or expense_delta),
            "source": source,
            "destination": destination,
            "reason": reason,
            "cash_delta": int(cash_delta),
            "debt_delta": int(debt_delta),
            "revenue_delta": int(revenue_delta),
            "expense_delta": int(expense_delta),
            "beat_id": beat_id,
        }
    )
    w["financial_events"] = events


def _cash_add(w: dict[str, Any], delta: int, *, kind: str, reason: str, beat_id: str = "", source: str = "", destination: str = "team") -> int:
    fin = w["finance"]
    before = _i(fin.get("team_cash"))
    projected = before + int(delta)
    applied = int(delta)
    if projected < 0 and not _financing_covers(w, projected):
        projected = 0
        applied = projected - before
    fin["team_cash"] = projected
    if applied:
        _log_fin(
            w,
            type=kind,
            amount=abs(applied),
            source=source,
            destination=destination,
            reason=reason,
            cash_delta=applied,
            beat_id=beat_id,
        )
    return applied


def _debt_add(w: dict[str, Any], delta: int, *, kind: str, reason: str, beat_id: str = "") -> int:
    fin = w["finance"]
    before = max(0, _i(fin.get("team_debt")))
    after = max(0, before + int(delta))
    applied = after - before
    fin["team_debt"] = after
    if applied:
        _log_fin(w, type=kind, amount=abs(applied), reason=reason, debt_delta=applied, beat_id=beat_id)
    return applied


def _track_debt_risk(w: dict[str, Any], beat_id: str = "") -> None:
    state = compute_debt_risk(w.get("finance") or {})
    (w.get("finance") or {})["debt_risk_state"] = state
    hist = list(w.get("debt_risk_history") or [])
    prev = hist[-1]["state"] if hist else None
    if state != prev:
        hist.append(
            {
                "beat_id": beat_id,
                "state": state,
                "debt": _i((w.get("finance") or {}).get("team_debt")),
                "cash": _i((w.get("finance") or {}).get("team_cash")),
                "revenue": _i((w.get("finance") or {}).get("annual_revenue")),
            }
        )
        w["debt_risk_history"] = hist


def _archive_season(w: dict[str, Any], *, major_event: str = "") -> None:
    sports = w["sports"]
    fin = w["finance"]
    team = w["team"]
    games = _i(sports.get("games_played"))
    wins = _i(sports.get("wins"))
    losses = _i(sports.get("losses"))
    if games <= 0 and str(sports.get("playoff_status") or "regular") == "regular":
        return
    hist = list(sports.get("season_history") or [])
    season_no = _i(sports.get("current_season") or sports.get("season") or 1)
    if hist and _i(hist[-1].get("season")) == season_no and _i(hist[-1].get("games_played")) == games:
        row = dict(hist[-1])
        if major_event:
            events = list(row.get("major_events") or [])
            if major_event not in events:
                events.append(major_event)
            row["major_events"] = events
        hist[-1] = row
        sports["season_history"] = hist
        return
    champ = str(sports.get("playoff_status") or "") == "champion"
    playoff_result = {
        "champion": "campeón",
        "finals": "final — derrota",
        "playoffs": f"playoffs · {sports.get('playoff_round') or 'primera ronda'}",
        "out": "eliminado",
        "regular": "sin playoffs",
    }.get(str(sports.get("playoff_status") or "regular"), str(sports.get("playoff_status") or "regular"))
    hist.append(
        {
            "season": season_no,
            "season_year": _i(sports.get("season_year") or season_no),
            "record": f"{wins}-{losses}",
            "games_played": games,
            "wins": wins,
            "losses": losses,
            "league_position": sports.get("league_position") or _league_position(sports),
            "playoff_result": playoff_result,
            "playoff_status": sports.get("playoff_status"),
            "playoff_round": sports.get("playoff_round") or "",
            "championship": champ,
            "attendance_avg": _i(team.get("attendance")),
            "revenue": _i(fin.get("annual_revenue")),
            "team_value": _i(team.get("valuation")),
            "major_events": [major_event] if major_event else [],
        }
    )
    sports["season_history"] = hist
    sports["historical_records"] = [h.get("record") for h in hist]
    if str(sports.get("playoff_status") or "regular") != "regular":
        ph = list(sports.get("playoff_history") or [])
        ph.append(
            {
                "season": season_no,
                "result": playoff_result,
                "round": sports.get("playoff_round") or "",
                "championship": champ,
            }
        )
        sports["playoff_history"] = ph


def force_pre_acquisition(world: dict[str, Any]) -> dict[str, Any]:
    w = derive_world(world)
    w["ownership_ledger"] = empty_ownership_ledger()
    w["acquisition"]["closed"] = False
    w["acquisition"]["your_ownership"] = 0
    w["sports"]["wins"] = 0
    w["sports"]["losses"] = 0
    w["sports"]["games_played"] = 0
    w["sports"]["championships"] = 0
    w["sports"]["playoff_status"] = "regular"
    w["sports"]["playoff_round"] = ""
    w["sports"]["regular_season_status"] = "preseason"
    w["sports"]["season_history"] = []
    w["sports"]["playoff_history"] = []
    w["sports"]["historical_records"] = []
    w["sports"]["injuries"] = []
    w["milestones"] = []
    w["equity_events"] = []
    w["financial_events"] = []
    w["debt_risk_history"] = []
    w["finance"]["team_cash"] = 0
    w["finance"]["credit_line"] = 0
    w["finance"]["overdraft_allowed"] = False
    w["finance"]["financing_open"] = False
    if _num(w["life"].get("personal_cash")) <= 0:
        w["life"]["personal_cash"] = 18400
    if _i(w["team"].get("attendance")) <= 0:
        w["team"]["attendance"] = 620
    if _i(w["team"].get("capacity")) <= 0:
        w["team"]["capacity"] = 4800
    if _i(w["finance"].get("team_debt")) <= 0:
        w["finance"]["team_debt"] = 650000
        w["finance"]["debt_service"] = 52000
    if _i(w["finance"].get("payroll")) <= 0:
        w["finance"]["payroll"] = 210000
    return derive_world(w)


def sanitize_world_delta(delta: Any) -> dict[str, Any]:
    if not isinstance(delta, dict):
        return {}
    d = deepcopy(delta)
    banned = {
        "ownership",
        "ownership_percentage",
        "valuation",
        "team_value",
        "ownership_ledger",
    }
    for k in list(d):
        if k in banned or str(k).endswith("ownership_percentage") or str(k).endswith("valuation"):
            d.pop(k, None)
    team = d.get("team")
    if isinstance(team, dict):
        for k in ("ownership_percentage", "valuation", "season_record"):
            team.pop(k, None)
    return d


def apply_ops(world: dict[str, Any], ops: Any, *, beat_id: str = "") -> dict[str, Any]:
    w = derive_world(world)
    rows = ops if isinstance(ops, list) else []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        op = str(raw.get("op") or raw.get("type") or "").strip().lower()
        if not op:
            continue
        w = _apply_one_op(w, op, raw, beat_id)
        w = derive_world(w)
        _track_debt_risk(w, beat_id)
    return derive_world(w)


def _apply_one_op(w: dict[str, Any], op: str, raw: dict[str, Any], beat_id: str) -> dict[str, Any]:
    fin = w["finance"]
    sports = w["sports"]
    life = w["life"]
    team = w["team"]
    acq = w["acquisition"]
    time = w["time"]

    if op in ("advance_time", "advance_months", "time"):
        months = _i(raw.get("months") or raw.get("month") or 0)
        days = _i(raw.get("days") or 0) + months * 30
        if days <= 0:
            days = 30
        time["elapsed_days"] = _i(time.get("elapsed_days")) + days
        if not acq.get("closed"):
            return w
        burn = int((_num(fin.get("annual_revenue")) - _num(fin.get("annual_expenses"))) * (days / 365.0))
        if burn:
            kind = "ticket_sales" if burn > 0 else "payroll"
            _cash_add(w, burn, kind=kind, reason="burn operativo del período", beat_id=beat_id, source="ops", destination="team")
        service = int(_num(fin.get("debt_service")) * (days / 365.0))
        pay = min(service, max(0, _i(fin.get("team_cash"))), _i(fin.get("team_debt")))
        if pay:
            _cash_add(w, -pay, kind="debt_payment", reason="servicio de deuda", beat_id=beat_id, source="team", destination="creditors")
            _debt_add(w, -pay, kind="debt_payment", reason="servicio de deuda", beat_id=beat_id)
        return w

    if op == "acquire_team":
        if acq.get("closed"):
            return w
        your_cash = _i(raw.get("your_cash") or raw.get("your_cash_contribution") or 15000)
        inv_cash = _i(raw.get("investor_cash") or raw.get("local_investors_cash") or 85000)
        your_pct = _num(raw.get("your_pct") or raw.get("your_ownership") or 51)
        inv_pct = _num(raw.get("investor_pct") or raw.get("investor_ownership") or 39)
        seller_pct = _num(raw.get("seller_pct") or raw.get("seller_retained") or max(0, 100 - your_pct - inv_pct))
        if abs(your_pct + inv_pct + seller_pct - 100) > 0.5:
            seller_pct = max(0, 100 - your_pct - inv_pct)
        debt = _i(raw.get("debt_assumed") or fin.get("team_debt") or 650000)
        price = _i(raw.get("asking_price") or 1)
        seller_fin = _i(raw.get("seller_financing") or 200000)
        available = _i(life.get("personal_cash"))
        if your_cash > available:
            your_cash = max(1000, available - 2000) if available > 3000 else available
        life["personal_cash"] = available - your_cash
        incoming = inv_cash + your_cash - price
        fin["team_cash"] = max(0, incoming)
        _log_fin(
            w,
            type="acquisition",
            amount=incoming,
            source="owner+investors",
            destination="team",
            reason="cierre de compra",
            cash_delta=incoming,
            beat_id=beat_id,
        )
        if inv_cash:
            _log_fin(
                w,
                type="equity_investment",
                amount=inv_cash,
                source="investors",
                destination="team",
                reason="capital de inversores locales",
                cash_delta=inv_cash,
                beat_id=beat_id,
            )
        fin["team_debt"] = debt
        fin["debt_service"] = int(debt * 0.08)
        _log_fin(
            w,
            type="loan",
            amount=debt,
            source="assumed_liabilities",
            destination="team",
            reason="deuda asumida en la compra",
            debt_delta=debt,
            beat_id=beat_id,
        )
        w["ownership_ledger"] = {
            "protagonist": your_pct,
            "investors": inv_pct,
            "seller": seller_pct,
        }
        acq.update(
            {
                "asking_price": price,
                "debt_assumed": debt,
                "your_cash_contribution": your_cash,
                "local_investors_cash": inv_cash,
                "seller_financing": seller_fin,
                "existing_liabilities_assumed": max(0, debt - seller_fin),
                "your_ownership": your_pct,
                "investor_ownership": inv_pct,
                "seller_retained": seller_pct,
                "closed": True,
                "summary": (
                    f"${price} de precio + asunción de ${debt:,} de deuda. "
                    f"Vos ponés ${your_cash:,} y te quedás {your_pct:.0f}%. "
                    f"Inversores locales ponen ${inv_cash:,} por {inv_pct:.0f}%. "
                    f"El vendedor retiene {seller_pct:.0f}% y financia ${seller_fin:,}."
                ),
            }
        )
        w["equity_events"] = list(w.get("equity_events") or []) + [
            {
                "beat_id": beat_id,
                "op": "acquire_team",
                "ledger": dict(w["ownership_ledger"]),
                "note": acq["summary"],
            }
        ]
        _hit(w, "owns_team")
        loc = w.get("locations") or {}
        loc["office"] = loc.get("office") or "cuarto de utilería en el estadio"
        w["locations"] = loc
        life["network"] = min(10, _i(life.get("network")) + 2)
        life["status"] = min(10, _i(life.get("status")) + 2)
        life["responsibility"] = min(10, _i(life.get("responsibility") or 1) + 4)
        return w

    if op in ("equity_sale", "sell_equity", "dilution"):
        src = str(raw.get("from") or "protagonist")
        dst = str(raw.get("to") or "investors")
        pct = _num(raw.get("pct") or raw.get("percent") or 0)
        cash = _i(raw.get("cash") or 0)
        before = dict(w["ownership_ledger"])
        w["ownership_ledger"] = transfer_equity(w["ownership_ledger"], src, dst, pct)
        to_person = str(raw.get("cash_to") or "protagonist") == "protagonist"
        if cash > 0:
            if to_person:
                life["personal_cash"] = _i(life.get("personal_cash")) + cash
                _log_fin(w, type="equity_investment", amount=cash, source=dst, destination="protagonist", reason="venta de equity", cash_delta=0, beat_id=beat_id)
            else:
                _cash_add(w, cash, kind="equity_investment", reason="venta de equity al equipo", beat_id=beat_id, source=dst, destination="team")
        w["equity_events"] = list(w.get("equity_events") or []) + [
            {
                "beat_id": beat_id,
                "op": op,
                "from": src,
                "to": dst,
                "pct": pct,
                "cash": cash,
                "ledger_before": before,
                "ledger": dict(w["ownership_ledger"]),
            }
        ]
        return w

    if op in ("buyback", "buy_equity"):
        src = str(raw.get("from") or "investors")
        pct = _num(raw.get("pct") or 0)
        cash = _i(raw.get("cash") or 0)
        w["ownership_ledger"] = transfer_equity(w["ownership_ledger"], src, "protagonist", pct)
        payer = str(raw.get("paid_by") or "team")
        if payer == "protagonist":
            life["personal_cash"] = _i(life.get("personal_cash")) - cash
        elif cash:
            _cash_add(w, -cash, kind="equity_investment", reason="recompra de equity", beat_id=beat_id, source="team", destination=src)
        w["equity_events"] = list(w.get("equity_events") or []) + [
            {"beat_id": beat_id, "op": "buyback", "pct": pct, "cash": cash, "ledger": dict(w["ownership_ledger"])}
        ]
        return w

    if op in ("win_game", "game_won"):
        return _sport_stretch(w, wins=1, losses=0, attendance=_i(raw.get("attendance") or 0), beat_id=beat_id)
    if op in ("lose_game", "game_lost"):
        return _sport_stretch(w, wins=0, losses=1, attendance=_i(raw.get("attendance") or 0), beat_id=beat_id)
    if op in ("game_played",):
        won = bool(raw.get("won") or raw.get("win"))
        return _sport_stretch(w, wins=1 if won else 0, losses=0 if won else 1, attendance=_i(raw.get("attendance") or 0), beat_id=beat_id)
    if op in ("season_stretch", "games"):
        return _sport_stretch(
            w,
            wins=_i(raw.get("wins") or 0),
            losses=_i(raw.get("losses") or 0),
            attendance=_i(raw.get("attendance") or 0),
            beat_id=beat_id,
        )
    if op == "new_season":
        games = _i(sports.get("games_played"))
        if games < 12:
            time["elapsed_days"] = _i(time.get("elapsed_days")) + 20
            return w
        _archive_season(w, major_event="cierre de temporada")
        sports["current_season"] = _i(sports.get("current_season") or sports.get("season") or 1) + 1
        sports["season"] = sports["current_season"]
        sports["season_year"] = _i(sports.get("season_year") or 1) + 1
        sports["season_label"] = f"Temporada {sports['season']}"
        sports["games_played"] = 0
        sports["wins"] = 0
        sports["losses"] = 0
        sports["win_pct"] = 0.0
        sports["win_percentage"] = 0.0
        sports["playoff_status"] = "regular"
        sports["playoff_round"] = ""
        sports["regular_season_status"] = "preseason"
        sports["recent_form"] = ""
        sports["injuries"] = []
        sports["team_morale"] = min(10, max(3, _i(sports.get("team_morale") or 4)))
        time["elapsed_days"] = _i(time.get("elapsed_days")) + 80
        return w
    if op in ("playoff_berth", "playoffs_qualified"):
        games = _i(sports.get("games_played"))
        wp = (_i(sports.get("wins")) / games) if games else 0.0
        if games < 12 or wp < 0.40:
            sports["regular_season_status"] = "complete"
            return w
        if sports["playoff_status"] in ("regular", "out"):
            sports["playoff_status"] = "playoffs"
            sports["playoff_round"] = sports.get("playoff_round") or "first_round"
        sports["regular_season_status"] = "complete"
        _hit(w, "playoffs")
        team["attendance"] = max(_i(team.get("attendance")), int(_num(team.get("capacity") or 4800) * 0.72))
        team["attendance_interest"] = min(10, _i(team.get("attendance_interest")) + 1)
        return w
    if op == "playoff_round_won":
        if sports["playoff_status"] not in ("playoffs", "finals"):
            return w
        nxt = {"first_round": "semifinal", "semifinal": "final", "final": "final", "finals": "final"}.get(
            str(sports.get("playoff_round") or "first_round"), "semifinal"
        )
        sports["playoff_round"] = nxt
        if nxt == "final":
            sports["playoff_status"] = "finals"
            _hit(w, "finals")
        sports["team_morale"] = min(10, _i(sports.get("team_morale") or 5) + 1)
        return w
    if op == "playoff_eliminated":
        if sports["playoff_status"] in ("playoffs", "finals"):
            sports["playoff_status"] = "out"
            sports["team_morale"] = max(1, _i(sports.get("team_morale") or 5) - 2)
            _archive_season(w, major_event="eliminación")
        return w
    if op == "final_reached":
        if sports["playoff_status"] in ("playoffs", "finals", "champion"):
            sports["playoff_status"] = "finals"
            sports["playoff_round"] = "final"
            _hit(w, "finals")
        elif championship_allowed({**w, "sports": {**sports, "playoff_status": "playoffs", "playoff_round": "final"}}):
            sports["playoff_status"] = "finals"
            sports["playoff_round"] = "final"
            _hit(w, "finals")
        return w
    if op in ("championship", "win_championship", "championship_won"):
        if not championship_allowed(w):
            if _i(sports.get("games_played")) >= 12 and (_i(sports.get("wins")) / max(1, _i(sports.get("games_played")))) >= 0.48:
                sports["playoff_status"] = "playoffs" if sports["playoff_status"] == "regular" else sports["playoff_status"]
                sports["playoff_round"] = sports.get("playoff_round") or "first_round"
            return _sport_stretch(w, wins=1, losses=0, attendance=_i(raw.get("attendance") or 0), beat_id=beat_id)
        sports["playoff_status"] = "champion"
        sports["playoff_round"] = "champion"
        sports["championships"] = _i(sports.get("championships")) + 1
        sports["team_morale"] = 10
        sports["regular_season_status"] = "complete"
        cap = _i(team.get("capacity") or 4800)
        team["attendance"] = max(_i(team.get("attendance")), cap)
        team["attendance_interest"] = min(10, _i(team.get("attendance_interest")) + 3)
        team["sponsorship_interest"] = min(10, _i(team.get("sponsorship_interest")) + 3)
        team["media_attention"] = min(10, _i(team.get("media_attention")) + 3)
        life["status"] = min(10, _i(life.get("status")) + 2)
        fin["merch_revenue"] = _i(fin.get("merch_revenue")) + 180000
        _cash_add(w, 120000, kind="merch", reason="boom de merch por campeonato", beat_id=beat_id, source="fans", destination="team")
        _log_fin(w, type="merch", amount=180000, reason="merch de campeonato", revenue_delta=180000, beat_id=beat_id)
        _archive_season(w, major_event="campeonato")
        _hit(w, "championship")
        return w

    if op in ("injury",):
        sports["roster_quality"] = max(1, _i(sports.get("roster_quality")) - _i(raw.get("roster_delta") or 1))
        inj = list(sports.get("injuries") or [])
        who = str(raw.get("player") or raw.get("who") or "pieza del rotación")
        if who not in inj:
            inj.append(who)
        sports["injuries"] = inj
        sports["team_morale"] = max(1, _i(sports.get("team_morale") or 5) - 1)
        team["attendance"] = max(400, int(_i(team.get("attendance")) * 0.86))
        return w
    if op in ("player_released", "release_player"):
        sports["roster_quality"] = max(1, _i(sports.get("roster_quality")) - 1)
        sports["payroll"] = sports.get("payroll")
        cut = _i(raw.get("payroll") or 20000)
        fin["payroll"] = max(0, _i(fin.get("payroll")) - cut)
        return w
    if op in ("sign_player", "signing", "player_signed"):
        cost = _i(raw.get("cost") or 28000)
        payroll = _i(raw.get("payroll") or 45000)
        _cash_add(w, -cost, kind="player_signing", reason=str(raw.get("reason") or "ficha"), beat_id=beat_id, source="team", destination="player")
        fin["payroll"] = _i(fin.get("payroll")) + payroll
        _log_fin(w, type="player_signing", amount=payroll, reason="alta de payroll", expense_delta=payroll, beat_id=beat_id)
        sports["roster_quality"] = min(10, _i(sports.get("roster_quality")) + _i(raw.get("roster_delta") or 1))
        stars = list(sports.get("star_players") or [])
        name = str(raw.get("player") or raw.get("name") or "")
        if name and name not in stars:
            stars.append(name)
            sports["star_players"] = stars
        return w
    if op in ("hire_coach", "new_coach", "coach_hired"):
        sports["coach_quality"] = min(10, max(_i(raw.get("quality") or _i(sports.get("coach_quality")) + 2), 1))
        sports["coach"] = str(raw.get("coach") or raw.get("name") or "entrenador nuevo")
        cost = _i(raw.get("cost") or 12000)
        _cash_add(w, -cost, kind="coach_contract", reason="contrato de entrenador", beat_id=beat_id, source="team", destination="coach")
        fin["payroll"] = _i(fin.get("payroll")) + _i(raw.get("payroll") or 35000)
        _log_fin(w, type="coach_contract", amount=_i(raw.get("payroll") or 35000), reason="payroll coach", expense_delta=_i(raw.get("payroll") or 35000), beat_id=beat_id)
        return w
    if op in ("coach_fired",):
        sports["coach_quality"] = max(1, _i(sports.get("coach_quality")) - 2)
        sports["coach"] = "búsqueda de entrenador"
        sports["team_morale"] = max(1, _i(sports.get("team_morale") or 5) - 1)
        return w
    if op in ("sponsor_deal", "sponsor"):
        annual = _i(raw.get("annual") or 48000)
        fin["sponsorship_revenue"] = _i(fin.get("sponsorship_revenue")) + annual
        _cash_add(w, annual, kind="sponsor", reason=str(raw.get("reason") or "contrato de sponsor"), beat_id=beat_id, source="sponsor", destination="team")
        _log_fin(w, type="sponsor", amount=annual, reason="sponsor anual", revenue_delta=annual, beat_id=beat_id)
        team["sponsors"] = _i(team.get("sponsors")) + 1
        team["sponsorship_interest"] = min(10, _i(team.get("sponsorship_interest")) + 1)
        _hit(w, "first_sponsor")
        return w
    if op in ("sponsor_cut", "sponsor_lost"):
        annual = min(_i(raw.get("annual") or 40000), _i(fin.get("sponsorship_revenue")))
        fin["sponsorship_revenue"] = max(0, _i(fin.get("sponsorship_revenue")) - annual)
        team["sponsorship_interest"] = max(0, _i(team.get("sponsorship_interest")) - 2)
        return w
    if op in ("ticket_night", "attendance"):
        att = _i(raw.get("attendance") or _i(team.get("attendance")) + 400)
        cap = _i(team.get("capacity") or 4800)
        team["attendance"] = min(cap, max(att, 0))
        gate = int(team["attendance"] * _num(raw.get("ticket_price") or 14))
        fin["ticket_revenue"] = _i(fin.get("ticket_revenue")) + gate
        fin["merch_revenue"] = _i(fin.get("merch_revenue")) + int(team["attendance"] * 2.5)
        _cash_add(w, gate, kind="ticket_sales", reason="noche de partido", beat_id=beat_id, source="fans", destination="team")
        _log_fin(w, type="ticket_sales", amount=gate, reason="taquilla", revenue_delta=gate, beat_id=beat_id)
        if team["attendance"] >= cap * 0.98:
            _hit(w, "sold_out")
            team["attendance_interest"] = min(10, _i(team.get("attendance_interest")) + 1)
        return w
    if op in ("media_deal", "tv_deal"):
        annual = _i(raw.get("annual") or 120000)
        fin["media_revenue"] = _i(fin.get("media_revenue")) + annual
        _cash_add(w, int(annual * 0.5), kind="media", reason="adelanto de derechos", beat_id=beat_id, source="media", destination="team")
        _log_fin(w, type="media", amount=annual, reason="contrato de medios", revenue_delta=annual, beat_id=beat_id)
        team["media_attention"] = min(10, _i(team.get("media_attention")) + 2)
        _hit(w, "media")
        return w
    if op in ("media_crisis",):
        team["media_attention"] = max(0, _i(team.get("media_attention")) - 2)
        sports["team_morale"] = max(1, _i(sports.get("team_morale") or 5) - 1)
        return w
    if op in ("fan_unrest",):
        team["attendance"] = max(400, int(_i(team.get("attendance")) * 0.82))
        team["attendance_interest"] = max(0, _i(team.get("attendance_interest")) - 2)
        return w
    if op in ("facility_issue",):
        team["facilities_quality"] = max(1, _i(team.get("facilities_quality") or 3) - 1)
        cost = _i(raw.get("cost") or 18000)
        _cash_add(w, -cost, kind="facility_upgrade", reason="reparación de emergencia", beat_id=beat_id, source="team", destination="facilities")
        return w
    if op in ("regulatory_fine",):
        amount = _i(raw.get("amount") or 25000)
        _cash_add(w, -amount, kind="regulatory_fine", reason=str(raw.get("reason") or "multa"), beat_id=beat_id, source="team", destination="league")
        return w
    if op in ("personal_crisis",):
        life["family_support"] = max(1, _i(life.get("family_support")) - 1)
        life["personal_cash"] = max(0, _i(life.get("personal_cash")) - _i(raw.get("amount") or 800))
        return w
    if op in ("owner_crisis",):
        sports["recent_form"] = str(raw.get("form") or "arranque flojo")
        sports["team_morale"] = max(1, _i(sports.get("team_morale") or 5) - 2)
        return w
    if op in ("pay_debt",):
        amount = _i(raw.get("amount") or 40000)
        amount = min(amount, max(0, _i(fin.get("team_cash"))), max(0, _i(fin.get("team_debt"))))
        if amount:
            _cash_add(w, -amount, kind="debt_payment", reason="pago de deuda", beat_id=beat_id, source="team", destination="creditors")
            _debt_add(w, -amount, kind="debt_payment", reason="pago de deuda", beat_id=beat_id)
        return w
    if op in ("credit_line", "overdraft", "bridge_loan", "loan"):
        amount = _i(raw.get("amount") or 80000)
        fin["financing_open"] = True
        if op == "overdraft":
            fin["overdraft_allowed"] = True
        if op == "credit_line":
            fin["credit_line"] = max(_i(fin.get("credit_line")), amount)
        _cash_add(w, amount, kind=op, reason=str(raw.get("reason") or op), beat_id=beat_id, source="lender", destination="team")
        _debt_add(w, amount, kind=op, reason=str(raw.get("reason") or op), beat_id=beat_id)
        return w
    if op in ("owner_injection",):
        amount = min(_i(raw.get("amount") or 15000), max(0, _i(life.get("personal_cash"))))
        life["personal_cash"] = _i(life.get("personal_cash")) - amount
        fin["financing_open"] = True
        _cash_add(w, amount, kind="owner_injection", reason="inyección del dueño", beat_id=beat_id, source="protagonist", destination="team")
        return w
    if op in ("investor_injection",):
        amount = _i(raw.get("amount") or 40000)
        fin["financing_open"] = True
        _cash_add(w, amount, kind="investor_injection", reason="inyección de socios", beat_id=beat_id, source="investors", destination="team")
        return w
    if op in ("facility_upgrade", "arena"):
        cost = _i(raw.get("cost") or 80000)
        applied = _cash_add(w, -cost, kind="facility_upgrade", reason="inversión en instalaciones", beat_id=beat_id, source="team", destination="facilities")
        if applied:
            team["facilities_quality"] = min(10, _i(team.get("facilities_quality") or 3) + _i(raw.get("quality") or 1))
        cap = _i(raw.get("capacity") or 0)
        if cap:
            team["capacity"] = cap
        _hit(w, "arena")
        return w
    if op in ("quit_job",):
        life["job"] = str(raw.get("job") or "dueño del equipo")
        life["salary"] = _i(raw.get("salary") or max(24000, int(_num(fin.get("annual_revenue")) * 0.04)))
        life["weekly_work_hours"] = _i(raw.get("hours") or 65)
        life["freedom"] = min(10, _i(life.get("freedom")) + 3)
        life["status"] = min(10, _i(life.get("status")) + 2)
        _hit(w, "quit_job")
        return w
    if op in ("owner_draw", "salary_from_team", "owner_distribution"):
        amount = _i(raw.get("amount") or 8000)
        applied = _cash_add(w, -amount, kind="owner_distribution", reason="retiro del dueño", beat_id=beat_id, source="team", destination="protagonist")
        life["personal_cash"] = _i(life.get("personal_cash")) + abs(applied)
        life["salary"] = max(_i(life.get("salary")), abs(applied))
        return w
    if op in ("move_home", "move"):
        cost = _i(raw.get("cost") or 4000)
        life["personal_cash"] = _i(life.get("personal_cash")) - min(cost, _i(life.get("personal_cash")))
        life["home"] = str(raw.get("home") or "departamento propio cerca de la arena")
        life["lifestyle"] = str(raw.get("lifestyle") or "más espacio, más silencio, más estadio")
        life["freedom"] = min(10, _i(life.get("freedom")) + 1)
        _hit(w, "move_home")
        return w
    if op in ("help_family",):
        amount = _i(raw.get("amount") or 6000)
        life["personal_cash"] = _i(life.get("personal_cash")) - min(amount, max(0, _i(life.get("personal_cash"))))
        life["family_support"] = min(10, _i(life.get("family_support")) + 2)
        _hit(w, "help_family")
        return w
    if op in ("travel",):
        life["status"] = min(10, _i(life.get("status")) + 1)
        life["network"] = min(10, _i(life.get("network")) + 1)
        _hit(w, "travel")
        return w
    return w


def _sport_stretch(w: dict[str, Any], *, wins: int, losses: int, attendance: int, beat_id: str = "") -> dict[str, Any]:
    sports = w["sports"]
    fin = w["finance"]
    team = w["team"]
    cap = max(1, _i(team.get("capacity") or 4800))
    wins = max(0, wins)
    losses = max(0, losses)
    games = wins + losses
    already = _i(sports.get("games_played"))
    room = max(0, 32 - already)
    if games > room:
        if room <= 0:
            wins, losses, games = 0, 0, 0
        else:
            ratio = wins / games if games else 0.5
            wins = int(round(room * ratio))
            losses = room - wins
            games = wins + losses
    sports["wins"] = _i(sports.get("wins")) + wins
    sports["losses"] = _i(sports.get("losses")) + losses
    sports["games_played"] = already + games
    sports["recent_form"] = f"{max(0, wins)}-{max(0, losses)}"
    delta_morale = (1 if wins > losses else -1 if losses > wins else 0)
    sports["team_morale"] = max(1, min(10, _i(sports.get("team_morale") or 4) + delta_morale))
    if games:
        sports["regular_season_status"] = "in_progress"
    cur = _i(team.get("attendance") or 600)
    if attendance > 0:
        team["attendance"] = min(cap, attendance)
    else:
        bump = int((wins * 90) - (losses * 25))
        team["attendance"] = min(cap, max(350, cur + bump))
    gate = int(team["attendance"] * 13 * max(1, games))
    fin["ticket_revenue"] = _i(fin.get("ticket_revenue")) + gate
    merch = int(team["attendance"] * 2 * max(1, games))
    fin["merch_revenue"] = _i(fin.get("merch_revenue")) + merch
    cash_in = int(gate * 0.55)
    if cash_in:
        _cash_add(w, cash_in, kind="ticket_sales", reason="tramo de temporada", beat_id=beat_id, source="fans", destination="team")
    _log_fin(w, type="ticket_sales", amount=gate, reason="taquilla de tramo", revenue_delta=gate, beat_id=beat_id)
    if merch:
        _log_fin(w, type="merch", amount=merch, reason="merch de tramo", revenue_delta=merch, beat_id=beat_id)
    if sports["wins"] >= 1:
        _hit(w, "first_win")
    if team["attendance"] >= cap * 0.98:
        _hit(w, "sold_out")
        team["attendance_interest"] = min(10, _i(team.get("attendance_interest")) + 1)
    return w


def championship_allowed(world: dict[str, Any]) -> bool:
    sports = world.get("sports") or {}
    games = _i(sports.get("games_played"))
    wins = _i(sports.get("wins"))
    wp = (wins / games) if games else 0.0
    status = str(sports.get("playoff_status") or "regular")
    round_ = str(sports.get("playoff_round") or "")
    if games < 16 or wp < 0.50:
        return False
    if status not in ("playoffs", "finals", "champion"):
        return False
    if round_ not in ("first_round", "semifinal", "final", "finals", "champion") and status not in ("finals", "champion"):
        return False
    return True


def _hit(world: dict[str, Any], mid: str) -> None:
    ms = list(world.get("milestones") or [])
    if mid not in ms:
        ms.append(mid)
    world["milestones"] = ms


def infer_ops_from_beat(beat: dict[str, Any], world: dict[str, Any]) -> list[dict[str, Any]]:
    existing = beat.get("ops") if isinstance(beat.get("ops"), list) else []
    ops = [o for o in existing if isinstance(o, dict) and (o.get("op") or o.get("type"))]
    blob = " ".join(str(beat.get(k) or "") for k in ("cause", "event", "consequence", "story_purpose")).lower()
    names = {str(o.get("op") or o.get("type") or "").lower() for o in ops}

    def add(op: str, **kwargs: Any) -> None:
        if op in names:
            return
        names.add(op)
        ops.append({"op": op, **kwargs})

    if not (world.get("acquisition") or {}).get("closed"):
        if any(
            w in blob
            for w in ("firmás", "firmas la", "escritura", "adquirís", "adquiris", "comprás el equipo", "compras el equipo", "te convertís en dueño", "te conviertes en dueño")
        ):
            add("acquire_team")
    if "campeonat" in blob or "anillo" in blob or "ganás la liga" in blob or "ganas la liga" in blob:
        if championship_allowed(world):
            add("championship_won")
        elif any(str(o.get("op")) in ("championship", "championship_won", "win_championship") for o in ops):
            pass
        else:
            add("playoff_berth")
    elif "final" in blob and "playoff" in blob:
        add("final_reached")
    elif "playoff" in blob:
        add("playoff_berth")
    if "lesion" in blob or "lesión" in blob:
        add("injury")
    if any(w in blob for w in ("fich", "contratás a", "contratas a", "signing")):
        add("sign_player")
    if "entrenador" in blob or "coach" in blob:
        if "nuevo" in blob or "fich" in blob or "contrat" in blob:
            add("hire_coach")
    if "sponsor" in blob or "patrocin" in blob:
        add("sponsor_deal")
    if "sold out" in blob or "lleno" in blob or "se agota" in blob:
        cap = _i((world.get("team") or {}).get("capacity") or 4800)
        add("ticket_night", attendance=cap)
    if "renunci" in blob or "dejás el trabajo" in blob or "dejas el trabajo" in blob:
        add("quit_job")
    if "mudás" in blob or "mudas" in blob or "departamento propio" in blob or "te mudás" in blob or "te mudas" in blob:
        add("move_home")
    if "padres" in blob and ("palco" in blob or "ayud" in blob or "casa" in blob):
        add("help_family")
    if "deuda" in blob and any(w in blob for w in ("pag", "cuota", "venc")):
        add("pay_debt", amount=45000)
    if "viaj" in blob:
        add("travel")
    if re.search(r"\b(gan[aá]s|victoria|ganan)\b", blob) and "campeonat" not in blob:
        add("win_game")
    if re.search(r"\b(derrota|perdés|perdes|pierden)\b", blob):
        add("lose_game")
    if re.search(r"\b(mes|año|year|age 2[3-9])\b", blob) or "temporada" in blob:
        if "new_season" not in names and "advance_time" not in names:
            add("advance_time", months=2)
    if "playoff_berth" in names or "playoffs_qualified" in names or "final_reached" in names:
        gp = _i((world.get("sports") or {}).get("games_played"))
        if gp < 16 and "season_stretch" not in names:
            need = max(0, 26 - gp)
            wins = max(1, int(round(need * 0.54)))
            losses = max(0, need - wins)
            if need:
                att = _i(((world.get("team") or {}).get("attendance")) or 1800)
                ops.insert(0, {"op": "season_stretch", "wins": wins, "losses": losses, "attendance": att})
                names.add("season_stretch")
    if any(w in blob for w in ("vendés parte", "vendes parte", "cedés", "cedes", "dilu")):
        add("equity_sale", **{"from": "protagonist", "to": "investors", "pct": 8, "cash": 40000})
    champs = []
    rest = []
    for o in ops:
        if str(o.get("op") or "").lower() in ("championship", "championship_won", "win_championship"):
            champs.append(o)
        else:
            rest.append(o)
    return rest + champs


def detect_payoffs(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    team = (after.get("team") or {}).get("name") or "el equipo"
    bms = set(before.get("milestones") or [])
    ams = set(after.get("milestones") or [])
    new = [m for m in (after.get("milestones") or []) if m not in bms]
    scenes = {
        "owns_team": f"Entras por primera vez a TU estadio. El utilero te llama dueño. {team} es tuyo.",
        "first_win": "El primer silbato a favor. El vestuario grita y alguien te busca con los ojos.",
        "first_sponsor": "Un local pone su nombre en la camiseta. Hay plata que no salió de tu bolsillo.",
        "sold_out": "Hay fila dando la vuelta. Por primera vez no entra más gente.",
        "quit_job": "Entregas la renuncia. El badge de la oficina queda sobre el escritorio.",
        "move_home": "Mudás las cajas. El departamento viejo queda vacío a las 11 de la noche.",
        "help_family": "Llevás a tus padres al palco. Tu vieja no mira el partido: te mira a vos.",
        "playoffs": "Entras al vestuario antes de playoffs. El pizarrón tiene tu temporada escrita.",
        "championship": "El estadio dice tu nombre en la pantalla. El equipo que compraste casi gratis está vivo.",
        "media": "Te llaman de una radio que antes solo oías yendo al trabajo.",
        "arena": "La arena ya no parece un galpón. Hay luz nueva y un pasillo que es tuyo.",
        "travel": "Viajás con el equipo. El micro sale de noche y vos no pediste franco.",
    }
    for mid in new:
        out.append({"id": mid, "scene": scenes.get(mid, mid)})
    bl = before.get("life") or {}
    al = after.get("life") or {}
    if bl.get("job") != al.get("job") and al.get("job") and "quit_job" not in ams:
        out.append({"id": "job_change", "scene": f"Tu trabajo ahora es: {al.get('job')}."})
    bv = _num((before.get("team") or {}).get("valuation"))
    av = _num((after.get("team") or {}).get("valuation"))
    if bv and av >= 1_000_000 and bv < 1_000_000:
        out.append({"id": "valuation_million", "scene": "El equipo ahora vale una cifra que nunca habías visto junta."})
    if bv and av >= bv * 1.8 and av > 400000:
        out.append({"id": "valuation_jump", "scene": f"{team} ya no vale una miseria. El número cambió de verdad."})
    return out


def repair_architecture(
    *,
    blueprint: dict[str, Any],
    beats: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [dict(b) for b in beats or [] if isinstance(b, dict)]
    if not rows:
        return []
    has_acq = any(
        any(str((op or {}).get("op") or "") == "acquire_team" for op in (b.get("ops") or []) if isinstance(op, dict))
        or any(w in str(b.get("event") or "").lower() for w in ("firm", "compr", "adquir", "escritura"))
        for b in rows
    )
    acq = (blueprint.get("business_or_vehicle") or {}).get("acquisition") or {}
    if not has_acq and len(rows) >= 4:
        target = rows[3]
        ops = list(target.get("ops") or [])
        ops.insert(
            0,
            {
                "op": "acquire_team",
                "your_cash": acq.get("your_cash_contribution") or 15000,
                "investor_cash": acq.get("local_investors_cash") or 85000,
                "your_pct": acq.get("your_ownership") or 51,
                "investor_pct": acq.get("investor_ownership") or 39,
                "seller_pct": acq.get("seller_retained") or 10,
                "debt_assumed": acq.get("debt_assumed") or 650000,
                "asking_price": acq.get("asking_price") or 1,
                "seller_financing": acq.get("seller_financing") or 200000,
            },
        )
        target["ops"] = ops
        target["event"] = target.get("event") or "Firmás la compra: un peso, la deuda, y el 51%."
        target["story_purpose"] = "first_commitment"
        target["reward_or_setback"] = "reward:owns_team"
        target["metric_reveal"] = ["OWNERSHIP", "CASH", "TEAM_DEBT"]

    for i, b in enumerate(rows):
        ops = [o for o in (b.get("ops") or []) if isinstance(o, dict)]
        if not any(str(o.get("op") or "") in ("advance_time", "advance_months", "new_season") for o in ops):
            if i > 0 and i % 6 == 0:
                ops.append({"op": "advance_time", "months": 3})
        b["ops"] = ops
        if not str(b.get("contribution") or "").strip():
            if b.get("ops") or b.get("reward_or_setback"):
                b["contribution"] = "world change"
    return diversify_setbacks(rows)


def diversify_setbacks(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(b) for b in beats]
    injury_idxs = []
    cats_seen: set[str] = set()
    for i, b in enumerate(rows):
        ops = [o for o in (b.get("ops") or []) if isinstance(o, dict)]
        kind = str(b.get("reward_or_setback") or "").lower()
        for o in ops:
            op = str(o.get("op") or "")
            if op == "injury":
                injury_idxs.append(i)
            cat = SETBACK_OP_CATEGORY.get(op)
            if cat:
                cats_seen.add(cat)
                if "setback" not in kind:
                    b["reward_or_setback"] = f"setback:{cat}"
                    kind = b["reward_or_setback"]
        if kind.startswith("setback:"):
            token = kind.split(":", 1)[-1]
            for c in SETBACK_CATEGORIES:
                if c in token or token in c:
                    cats_seen.add(c)
    alt_ops = [
        ("sponsor_cut", "sponsor", "el sponsor local recorta el contrato"),
        ("facility_issue", "facilities", "se rompe una caldera del gimnasio"),
        ("media_crisis", "media", "un audio del vestuario sale en una radio"),
        ("fan_unrest", "fanbase", "el público silba al equipo en la salida"),
        ("regulatory_fine", "regulatory", "la liga multa al club por un papel mal presentado"),
        ("personal_crisis", "personal", "tu familia te pide que vuelvas a la oficina"),
    ]
    extra = injury_idxs[1:]
    for n, idx in enumerate(extra):
        op_name, cat, event = alt_ops[n % len(alt_ops)]
        ops = [o for o in (rows[idx].get("ops") or []) if isinstance(o, dict)]
        ops = [o for o in ops if str(o.get("op") or "") != "injury"]
        ops.append({"op": op_name})
        rows[idx]["ops"] = ops
        rows[idx]["reward_or_setback"] = f"setback:{cat}"
        if not any(w in str(rows[idx].get("event") or "").lower() for w in ("sponsor", "caldera", "radio", "silba", "multa", "familia")):
            rows[idx]["event"] = event
        cats_seen.add(cat)
    acquired_at = next(
        (
            i
            for i, b in enumerate(rows)
            if any(str((o or {}).get("op")) == "acquire_team" for o in (b.get("ops") or []) if isinstance(o, dict))
        ),
        None,
    )
    has_owner = "ownership" in cats_seen or any(
        "setback:owner" in str(b.get("reward_or_setback") or "").lower()
        or str((o or {}).get("op")) in ("owner_crisis", "equity_sale")
        for b in rows
        for o in (b.get("ops") or [])
        if isinstance(o, dict)
    )
    if acquired_at is not None and not has_owner and len(rows) > acquired_at + 8:
        idx = min(len(rows) - 5, max(acquired_at + 6, (len(rows) * 3) // 5))
        ops = [o for o in (rows[idx].get("ops") or []) if isinstance(o, dict)]
        if not any(str(o.get("op")) in ("sign_player", "facility_upgrade", "owner_crisis") for o in ops):
            ops.extend(
                [
                    {"op": "sign_player", "cost": 42000, "payroll": 55000},
                    {"op": "facility_upgrade", "cost": 70000},
                    {"op": "season_stretch", "wins": 2, "losses": 8},
                    {"op": "owner_crisis"},
                ]
            )
            rows[idx]["ops"] = ops
            rows[idx]["reward_or_setback"] = "setback:ownership"
            rows[idx]["story_purpose"] = rows[idx].get("story_purpose") or "major_reversal"
            if "dueño" not in str(rows[idx].get("event") or "").lower():
                rows[idx]["event"] = (
                    "Apostás por roster e instalaciones. El mes siguiente el equipo arranca 2-8 "
                    "y el servicio de la deuda vuelve a mirarte a la cara."
                )
    return rows


def inject_life_payoffs(beats: list[dict[str, Any]], final_world: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(b) for b in beats]
    if not rows:
        return rows
    life = (final_world or {}).get("life") or {}
    sports = (final_world or {}).get("sports") or {}
    fin = (final_world or {}).get("finance") or {}
    job = str(life.get("job") or "")
    profitable = _num(fin.get("annual_revenue")) > _num(fin.get("annual_expenses")) * 0.85
    owned = _num(((final_world or {}).get("ownership_ledger") or {}).get("protagonist")) >= 40
    if owned and profitable and "oficina" in job.lower() and "dueño" not in job.lower():
        idx = min(len(rows) - 4, max(8, len(rows) // 2))
        ops = list(rows[idx].get("ops") or [])
        if not any(str((o or {}).get("op")) == "quit_job" for o in ops if isinstance(o, dict)):
            ops.append({"op": "quit_job"})
            rows[idx]["ops"] = ops
            rows[idx]["reward_or_setback"] = rows[idx].get("reward_or_setback") or "reward:quit_job"
    home = str(life.get("home") or "")
    if owned and "compartid" in home.lower():
        idx = min(len(rows) - 3, max(10, (len(rows) * 2) // 3))
        ops = list(rows[idx].get("ops") or [])
        if not any(str((o or {}).get("op")) == "move_home" for o in ops if isinstance(o, dict)):
            ops.append({"op": "move_home", "home": "departamento propio a cuatro cuadras de la arena", "cost": 4500})
            rows[idx]["ops"] = ops
            rows[idx]["reward_or_setback"] = rows[idx].get("reward_or_setback") or "reward:move_home"
    risk = str((fin.get("debt_risk_state") or compute_debt_risk(fin)))
    if owned and risk in ("critical", "dangerous"):
        idx = min(len(rows) - 2, max(12, (len(rows) * 3) // 4))
        ops = list(rows[idx].get("ops") or [])
        if not any(str((o or {}).get("op")) in ("media_deal", "sponsor_deal") for o in ops if isinstance(o, dict)):
            ops.extend(
                [
                    {"op": "sponsor_deal", "annual": 160000},
                    {"op": "media_deal", "annual": 200000},
                    {"op": "ticket_night", "attendance": 4600},
                ]
            )
            rows[idx]["ops"] = ops
    if _i(sports.get("championships")) or str(sports.get("playoff_status")) in ("playoffs", "finals", "champion"):
        idx = min(len(rows) - 2, max(12, (len(rows) * 3) // 4))
        ops = list(rows[idx].get("ops") or [])
        if not any(str((o or {}).get("op")) == "help_family" for o in ops if isinstance(o, dict)):
            ops.append({"op": "help_family", "amount": 5000})
            rows[idx]["ops"] = ops
    return rows


def beat_contributes(beat: dict[str, Any]) -> bool:
    if beat.get("ops"):
        return True
    if str(beat.get("reward_or_setback") or "").strip():
        return True
    action = beat.get("open_loop_action") if isinstance(beat.get("open_loop_action"), dict) else {}
    if action.get("action"):
        return True
    if beat.get("aspirational_payoffs"):
        return True
    purpose = str(beat.get("story_purpose") or "").lower()
    if purpose in {
        "inciting_incident",
        "first_commitment",
        "first_proof",
        "midpoint",
        "major_success",
        "major_reversal",
        "crisis",
        "decision",
        "climax",
        "ending",
    }:
        return True
    return False


def compact_world(world: dict[str, Any]) -> dict[str, Any]:
    w = derive_world(world)
    return {
        "age": w["time"].get("protagonist_age"),
        "elapsed_days": w["time"].get("elapsed_days"),
        "label": w["time"].get("label"),
        "life": w.get("life"),
        "ownership_ledger": w.get("ownership_ledger"),
        "acquisition": w.get("acquisition"),
        "finance": w.get("finance"),
        "sports": w.get("sports"),
        "team": {
            "name": (w.get("team") or {}).get("name"),
            "valuation": (w.get("team") or {}).get("valuation"),
            "attendance": (w.get("team") or {}).get("attendance"),
            "capacity": (w.get("team") or {}).get("capacity"),
            "ownership_percentage": (w.get("team") or {}).get("ownership_percentage"),
        },
        "milestones": w.get("milestones") or [],
        "season_history": (w.get("sports") or {}).get("season_history") or [],
        "debt_risk_state": (w.get("finance") or {}).get("debt_risk_state"),
        "championships": (w.get("sports") or {}).get("championships"),
        "playoff_status": (w.get("sports") or {}).get("playoff_status"),
        "playoff_round": (w.get("sports") or {}).get("playoff_round"),
        "financial_events_tail": (w.get("financial_events") or [])[-8:],
    }


def rewrite_downgraded_championship(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for b in beats or []:
        row = dict(b)
        sports = (row.get("world_state_after") or {}).get("sports") or {}
        champs = _i(sports.get("championships"))
        status = str(sports.get("playoff_status") or "regular")
        replacement = {
            "champion": "campeonato",
            "finals": "final de conferencia",
            "playoffs": "clasificación a playoffs",
            "out": "eliminación en playoffs",
        }.get(status, "temporada regular")
        if champs < 1:
            for key in ("event", "consequence", "cause", "visual_opportunity"):
                text = str(row.get(key) or "")
                if any(w in text.lower() for w in CHAMPIONSHIP_WORDS):
                    text = re.sub(r"(?i)campeonato(s)?", replacement, text)
                    text = re.sub(r"(?i)campeón(es)?", "finalista" if status == "finals" else "equipo de playoffs", text)
                    text = re.sub(r"(?i)campeon(es)?", "equipo de playoffs", text)
                    text = re.sub(r"(?i)anillo", "entrada a playoffs", text)
                    row[key] = text
        out.append(row)
    return out


def sync_loop_payoffs(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pay important loops when the world already answered them."""
    rules = [
        (("comprarlo", "adquir", "podrás compr"), ("acquire_team", "owns_team"), "cerraste la compra"),
        (("cerrar", "quiebra", "salvar", "flote", "evitar que cierre"), ("owns_team", "acquire_team"), "el equipo no cerró: es tuyo"),
        (("entrenador", "coach"), ("hire_coach", "coach_hired", "first_win"), "el nuevo coach movió al equipo"),
        (("sponsor", "patrocin"), ("sponsor_deal", "first_sponsor"), "llegó un sponsor real"),
        (("estadio", "lleno", "asistencia"), ("sold_out", "ticket_night"), "el estadio se llena"),
        (("competir", "playoff", "de verdad"), ("playoffs", "playoff_berth", "playoffs_qualified", "championship", "finals"), "el equipo compitió de verdad"),
    ]
    seen_ops: set[str] = set()
    seen_ms: set[str] = set()
    for b in beats or []:
        for o in b.get("ops") or []:
            if isinstance(o, dict):
                seen_ops.add(str(o.get("op") or ""))
        seen_ms.update((b.get("world_state_after") or {}).get("milestones") or [])
        after = b.get("story_state_after") if isinstance(b.get("story_state_after"), dict) else {}
        loops = after.get("open_loops") if isinstance(after.get("open_loops"), list) else []
        risk = str((((b.get("world_state_after") or {}).get("finance") or {}).get("debt_risk_state") or ""))
        for loop in loops:
            if not isinstance(loop, dict):
                continue
            if loop.get("intentional_unresolved"):
                continue
            q = f"{loop.get('id') or ''} {loop.get('question') or ''}".lower()
            paid = False
            if any(k in q for k in ("deuda", "debt")) and risk in ("manageable", "healthy"):
                loop["status"] = "paid"
                loop["paid_at"] = b.get("beat_id")
                loop["closed_at"] = b.get("beat_id")
                loop["payoff"] = "la deuda sigue, pero ya no puede matar al equipo"
                paid = True
            if not paid:
                for keys, tokens, payoff in rules:
                    if any(k in q for k in keys) and (set(tokens) & (seen_ops | seen_ms)):
                        loop["status"] = "paid"
                        loop["paid_at"] = b.get("beat_id")
                        loop["closed_at"] = b.get("beat_id")
                        loop["payoff"] = payoff
                        paid = True
                        break
            if paid:
                action = b.get("open_loop_action") if isinstance(b.get("open_loop_action"), dict) else {}
                if not action.get("action"):
                    b["open_loop_action"] = {
                        "action": "pay",
                        "loop_id": loop.get("id"),
                        "question": loop.get("question"),
                    }
    return beats

