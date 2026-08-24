"""Continuity + story-quality validators for Check ALS Fase 2."""
from __future__ import annotations

import re
from typing import Any

from src.documentary.formats.check_als.story_arch import (
    MONEY_WORDS,
    PROGRESSION_KEYS,
    apply_world_delta,
    collect_named_entities,
    format_money,
    metric_value,
    world_snapshot,
)
from src.documentary.formats.check_als.story_sim import PURPLE_PROSE, championship_allowed, ledger_total

MORAL_PATTERNS = (
    r"aprendiste que",
    r"la lecci[oó]n",
    r"con esfuerzo todo",
    r"nunca te rindas",
    r"todo es posible",
    r"el verdadero premio",
    r"lo importante es el viaje",
    r"cre[eé] en ti",
    r"si quieres puedes",
)

GENERIC_COMPETITOR = (
    r"aparece un competidor grande",
    r"un competidor gigante",
    r"una gran cadena llega",
    r"un fondo de inversi[oó]n aparece",
    r"un rival millonario aparece",
)

TELEPORT_PURPOSES = {"championship", "campeonato", "exit", "sale_50m"}


def _txt(beat: dict[str, Any]) -> str:
    return " ".join(
        str(beat.get(k) or "")
        for k in ("cause", "event", "consequence", "story_purpose", "viewer_question")
    ).lower()


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def transformation_diff(initial: dict[str, Any], final: dict[str, Any], beats: list[dict[str, Any]]) -> dict[str, Any]:
    il = (initial or {}).get("life") if isinstance((initial or {}).get("life"), dict) else {}
    fl = (final or {}).get("life") if isinstance((final or {}).get("life"), dict) else {}
    io = _num(((initial or {}).get("ownership_ledger") or {}).get("protagonist"))
    fo = _num(((final or {}).get("ownership_ledger") or {}).get("protagonist"))
    if fo > 100 or fo < 0:
        fo = 0  # ignore corrupt
    dims = {
        "wealth": (_num(il.get("personal_net_worth")), _num(fl.get("personal_net_worth"))),
        "ownership": (io, fo),
        "work": (str(il.get("job") or ""), str(fl.get("job") or "")),
        "home": (str(il.get("home") or ""), str(fl.get("home") or "")),
        "freedom": (_num(il.get("freedom")), _num(fl.get("freedom"))),
        "status": (_num(il.get("status")), _num(fl.get("status"))),
        "network": (_num(il.get("network")), _num(fl.get("network"))),
        "family": (_num(il.get("family_support")), _num(fl.get("family_support"))),
        "environment": (str(il.get("home") or ""), str(fl.get("home") or "")),
        "responsibility": (_num(il.get("weekly_work_hours")), _num(fl.get("weekly_work_hours"))),
    }
    changed = []
    for k, (a, b) in dims.items():
        if a != b:
            changed.append(k)
    earned = any(
        (b.get("ops") or b.get("aspirational_payoffs"))
        for b in beats or []
    )
    ok = (
        "ownership" in changed
        and ("work" in changed or "home" in changed)
        and ("wealth" in changed or "status" in changed)
        and earned
        and fo <= 100
    )
    missing = [k for k in ("ownership", "work", "home", "wealth") if k not in changed]
    return {
        "ok": ok,
        "changed": changed,
        "dims": {k: {"from": a, "to": b} for k, (a, b) in dims.items()},
        "detail": None if ok else ("sin cambio ganado en: " + ", ".join(missing or ["vida"])),
    }


def validate_synopsis(synopsis: str, blueprint: dict[str, Any], initial: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    flags: list[dict[str, Any]] = []
    text = synopsis or ""
    words = len(re.findall(r"\S+", text))
    low = text.lower()
    needed = {
        "acquisition": ("peso", "$1", "deuda", "51", "porcentaje", "inversores", "seller", "financi", "asumi"),
        "personal": ("renunci", "departamento", "padres", "oficina", "mud"),
        "setback": ("deuda", "crisis", "vence", "sponsor", "lesion", "lesión", "multa", "instal"),
        "payoff": ("playoff", "lleno", "sold", "palco", "dueño", "valor"),
        "final_life": ("años", "age", "ahora", "hoy", "estadio"),
    }
    for name, keys in needed.items():
        if not any(k in low for k in keys):
            flags.append({"code": "synopsis_missing", "detail": f"falta {name} concreto"})
    for pat in PURPLE_PROSE:
        if re.search(pat, low):
            flags.append({"code": "synopsis_purple", "detail": pat, "hard": True})
            break
    sports = (final or {}).get("sports") or {}
    champs = int(sports.get("championships") or 0)
    if any(w in low for w in ("campeonat", "campeón", "campeon", "anillo")) and champs < 1:
        flags.append({"code": "championship_inconsistent", "detail": "synopsis dice campeonato y sports_state no", "hard": True})
    hist = sports.get("season_history") or []
    if 900 <= words <= 1200 and not any(f.get("code") == "synopsis_missing" for f in flags):
        ok = True
    else:
        ok = False
        if words < 850 or words > 1200:
            flags.append({"code": "synopsis_length", "detail": f"{words} palabras (objetivo 900–1200)", "hard": words < 850})
    return {"ok": ok, "flags": flags, "words": words, "season_history": hist}


def validate_hard_gates(
    beats: list[dict[str, Any]],
    *,
    initial_world: dict[str, Any],
    final_world: dict[str, Any],
    blueprint: dict[str, Any],
) -> dict[str, Any]:
    fails: list[dict[str, Any]] = []
    start = initial_world or {}
    end = final_world or {}
    start_own = _num((start.get("ownership_ledger") or {}).get("protagonist"))
    if start_own > 0.5:
        fails.append({"code": "start_already_owner", "detail": f"ownership inicial={start_own}", "hard": True})
    acquired = False
    champ_text = False
    equity_sale = False
    for beat in beats or []:
        bid = str(beat.get("beat_id") or "")
        after = beat.get("world_state_after") or {}
        before = beat.get("world_state_before") or {}
        ledger = after.get("ownership_ledger") or {}
        total = ledger_total(ledger) if ledger else 100.0
        if ledger and abs(total - 100.0) > 0.6:
            fails.append({"code": "ownership_total", "beat_id": bid, "detail": f"sum={total}", "hard": True})
        if _num((before.get("ownership_ledger") or {}).get("protagonist")) <= 0.5 and _num(ledger.get("protagonist")) >= 40:
            acquired = True
        blob = _txt(beat)
        if any(w in blob for w in ("campeonat", "campeón", "campeon ", "anillo")):
            champ_text = True
            sports = after.get("sports") or {}
            if not championship_allowed(after) and _num(sports.get("championships")) < 1:
                fails.append({"code": "championship_inconsistent", "beat_id": bid, "detail": "campeonato sin temporada", "hard": True})
        ops = beat.get("ops") or []
        if any(str((o or {}).get("op")) in ("equity_sale", "sell_equity", "dilution") for o in ops if isinstance(o, dict)):
            equity_sale = True
            bown = _num((before.get("ownership_ledger") or {}).get("protagonist"))
            aown = _num(ledger.get("protagonist"))
            bcash = _num(((before.get("life") or {}).get("personal_cash")))
            acash = _num(((after.get("life") or {}).get("personal_cash")))
            tc = _num(((after.get("finance") or {}).get("team_cash"))) - _num(((before.get("finance") or {}).get("team_cash")))
            if abs(bown - aown) < 0.2 or (abs(acash - bcash) < 1 and abs(tc) < 1):
                fails.append({"code": "equity_sale_no_delta", "beat_id": bid, "detail": "venta de equity sin ledger/cash", "hard": True})
        cash = _num(((after.get("finance") or {}).get("team_cash")))
        financing = False
        fin_after = after.get("finance") or {}
        if fin_after.get("overdraft_allowed") or fin_after.get("financing_open") or _num(fin_after.get("credit_line")) > 0:
            financing = True
        types = {str(e.get("type") or "") for e in (after.get("financial_events") or []) if isinstance(e, dict)}
        if types & {"credit_line", "overdraft", "bridge_loan", "owner_injection", "investor_injection"}:
            financing = True
        if cash < -1 and not financing:
            fails.append({"code": "negative_cash", "beat_id": bid, "detail": f"team_cash={cash} sin financiamiento", "hard": True})
        money_ops = {
            "acquire_team",
            "sponsor_deal",
            "sponsor",
            "ticket_night",
            "media_deal",
            "sign_player",
            "signing",
            "facility_upgrade",
            "pay_debt",
            "equity_sale",
            "buyback",
            "owner_draw",
            "credit_line",
            "bridge_loan",
            "owner_injection",
            "investor_injection",
        }
        if any(str((o or {}).get("op")) in money_ops for o in ops if isinstance(o, dict)):
            before_n = len(before.get("financial_events") or [])
            after_n = len(after.get("financial_events") or [])
            if after_n <= before_n:
                fails.append({"code": "missing_financial_event", "beat_id": bid, "detail": "transacción sin financial_events", "hard": True})
        debt_b = _num(((before.get("finance") or {}).get("team_debt")))
        debt_a = _num(((after.get("finance") or {}).get("team_debt")))
        if abs(debt_a - debt_b) > 1:
            debt_ops = {
                "acquire_team",
                "pay_debt",
                "credit_line",
                "bridge_loan",
                "loan",
                "overdraft",
                "advance_time",
                "advance_months",
            }
            if not any(str((o or {}).get("op")) in debt_ops for o in ops if isinstance(o, dict)):
                fails.append({"code": "unexplained_debt", "beat_id": bid, "detail": f"deuda {debt_b}→{debt_a}", "hard": True})
        age_b = _num(((before.get("time") or {}).get("protagonist_age")))
        age_a = _num(((after.get("time") or {}).get("protagonist_age")))
        if age_a + 0.01 < age_b:
            fails.append({"code": "age_backwards", "beat_id": bid, "detail": f"{age_b}→{age_a}", "hard": True})

    if not acquired:
        fails.append({"code": "acquisition_missing", "detail": "nunca pasa ownership 0→control", "hard": True})
    val0 = _num(((start.get("team") or {}).get("valuation")))
    val1 = _num(((end.get("team") or {}).get("valuation")))
    att0 = _num(((start.get("team") or {}).get("attendance")))
    att1 = _num(((end.get("team") or {}).get("attendance")))
    if att1 >= max(att0 * 3, 3000) and val1 < val0 * 1.25 and val1 > 0:
        fails.append({"code": "frozen_valuation", "detail": f"asistencia {att0}→{att1} valuation {val0}→{val1}", "hard": True})
    debt0 = _num(((start.get("finance") or {}).get("team_debt") or (start.get("team") or {}).get("debt")))
    debt1 = _num(((end.get("finance") or {}).get("team_debt") or (end.get("team") or {}).get("debt")))
    paid_debt = any(
        any(str((o or {}).get("op")) == "pay_debt" for o in (b.get("ops") or []) if isinstance(o, dict))
        for b in beats or []
    )
    if paid_debt and abs(debt1 - debt0) < 1:
        fails.append({"code": "frozen_debt", "detail": "hubo pago de deuda y debt no se movió", "hard": True})
    age0 = _num(((start.get("time") or {}).get("protagonist_age")) or 22)
    age1 = _num(((end.get("time") or {}).get("protagonist_age")) or age0)
    if age1 < age0 + 2:
        fails.append({"code": "time_too_short", "detail": f"edad {age0}→{age1} (hace falta una vida de varios años)", "hard": True})
    if champ_text:
        rec = (end.get("sports") or {})
        hist = rec.get("season_history") or []
        hist_champ = any(bool(h.get("championship")) for h in hist if isinstance(h, dict))
        if _num(rec.get("championships")) < 1 and str(rec.get("playoff_status")) != "champion" and not hist_champ:
            fails.append({"code": "championship_inconsistent", "detail": "texto de campeonato vs sports_state", "hard": True})
    sports_end = end.get("sports") or {}
    rec_games = _num(sports_end.get("games_played"))
    rec_w = _num(sports_end.get("wins"))
    rec_l = _num(sports_end.get("losses"))
    if rec_games and abs(rec_games - (rec_w + rec_l)) > 0.5:
        fails.append({"code": "season_record_inconsistent", "detail": f"{rec_w}-{rec_l} vs games={rec_games}", "hard": True})
    hist = sports_end.get("season_history") or []
    playoff_narrated = any("playoff" in _txt(b).lower() for b in beats or [])
    if playoff_narrated and rec_games <= 0 and not hist:
        fails.append({"code": "season_record_inconsistent", "detail": "playoffs narrados sin temporada en sports_state", "hard": True})
    ledger_end = end.get("ownership_ledger") or {}
    if ledger_end and abs(ledger_total(ledger_end) - 100.0) > 0.6:
        fails.append({"code": "ownership_total", "detail": f"final sum={ledger_total(ledger_end)}", "hard": True})
    return {"ok": not fails, "fails": fails}


def validate_continuity(beats: list[dict[str, Any]], *, initial_world: dict[str, Any] | None = None) -> dict[str, Any]:
    flags: list[dict[str, Any]] = []
    prev_age = None
    prev_elapsed = None
    prev_chars: set[str] = set()
    prev_locs: set[str] = set()
    if initial_world:
        prev_chars, prev_locs = collect_named_entities(initial_world)
        prev_age = _num((initial_world.get("time") or {}).get("protagonist_age"))
        prev_elapsed = _num((initial_world.get("time") or {}).get("elapsed_days"))

    for beat in beats or []:
        bid = str(beat.get("beat_id") or "")
        before = beat.get("world_state_before") if isinstance(beat.get("world_state_before"), dict) else {}
        after = beat.get("world_state_after") if isinstance(beat.get("world_state_after"), dict) else {}
        delta = beat.get("world_delta") if isinstance(beat.get("world_delta"), dict) else {}
        recomputed = apply_world_delta(before, delta) if before else after

        own = _num((after.get("ownership_ledger") or {}).get("protagonist"))
        total = sum(_num(v) for v in (after.get("ownership_ledger") or {}).values())
        if after.get("ownership_ledger") and abs(total - 100) > 0.6:
            flags.append({"code": "ownership_invalid", "beat_id": bid, "detail": f"ledger_total={total}"})
        if own < -0.1 or own > 100.1:
            flags.append({"code": "ownership_invalid", "beat_id": bid, "detail": f"ownership={own}"})

        cash = _num((after.get("personal") or {}).get("cash"))
        team_debt = _num((after.get("team") or {}).get("debt"))
        att = _num((after.get("team") or {}).get("attendance"))
        if team_debt < 0:
            flags.append({"code": "debt_negative", "beat_id": bid, "detail": f"team_debt={team_debt}"})
        if att < 0:
            flags.append({"code": "attendance_negative", "beat_id": bid, "detail": f"attendance={att}"})

        rec = (after.get("team") or {}).get("season_record") or {}
        if isinstance(rec, dict):
            if _num(rec.get("wins")) < 0 or _num(rec.get("losses")) < 0:
                flags.append({"code": "record_invalid", "beat_id": bid, "detail": str(rec)})

        age = _num((after.get("time") or {}).get("protagonist_age"), prev_age or 0)
        elapsed = _num((after.get("time") or {}).get("elapsed_days"), prev_elapsed or 0)
        if prev_age is not None and age + 0.01 < prev_age:
            flags.append({"code": "age_backwards", "beat_id": bid, "detail": f"{prev_age} → {age}"})
        if prev_age is not None and age - prev_age > 3:
            flags.append({"code": "age_jump", "beat_id": bid, "detail": f"{prev_age} → {age}"})
        if prev_elapsed is not None and elapsed + 0.01 < prev_elapsed:
            flags.append({"code": "time_backwards", "beat_id": bid, "detail": f"{prev_elapsed} → {elapsed}"})

        cash_before = _num((before.get("personal") or {}).get("cash"))
        cash_delta = cash - cash_before
        if abs(cash_delta) >= 5000:
            blob = _txt(beat)
            if not any(w in blob for w in MONEY_WORDS):
                flags.append(
                    {
                        "code": "money_unexplained",
                        "beat_id": bid,
                        "detail": f"cash {format_money(cash_before)} → {format_money(cash)}",
                    }
                )

        val_b = _num((before.get("team") or {}).get("valuation"))
        val_a = _num((after.get("team") or {}).get("valuation"))
        if val_b > 0 and val_a > val_b * 3:
            flags.append(
                {
                    "code": "valuation_teleport",
                    "beat_id": bid,
                    "detail": f"{format_money(val_b)} → {format_money(val_a)}",
                }
            )

        chars, locs = collect_named_entities(after)
        new_chars = chars - prev_chars
        intro = {str(x).strip().lower() for x in (after.get("introduced_characters") or []) if str(x).strip()}
        delta_intro = set()
        raw_intro = delta.get("introduced_characters")
        if isinstance(raw_intro, list):
            delta_intro = {str(x).strip().lower() for x in raw_intro if str(x).strip()}
        elif isinstance(raw_intro, dict):
            added = raw_intro.get("add") or raw_intro.get("set") or []
            if isinstance(added, list):
                delta_intro = {str(x).strip().lower() for x in added if str(x).strip()}
        for name in new_chars:
            if name and name not in intro and name not in delta_intro and name not in _txt(beat):
                flags.append({"code": "character_unintroduced", "beat_id": bid, "detail": name})
        new_locs = locs - prev_locs
        for loc in new_locs:
            if loc and loc not in _txt(beat) and loc not in {
                str(x).strip().lower() for x in (after.get("introduced_locations") or []) if str(x).strip()
            }:
                flags.append({"code": "location_unintroduced", "beat_id": bid, "detail": loc})

        # LLM after vs reconstructed after (key metrics)
        if before:
            for path_label, getter in (
                ("cash", lambda w: _num((w.get("personal") or {}).get("cash"))),
                ("ownership", lambda w: _num((w.get("team") or {}).get("ownership_percentage"))),
            ):
                a = getter(after)
                r = getter(recomputed)
                if abs(a - r) > 1:
                    flags.append(
                        {
                            "code": "delta_mismatch",
                            "beat_id": bid,
                            "detail": f"{path_label} after={a} reconstructed={r}",
                        }
                    )

        prev_age, prev_elapsed = age, elapsed
        prev_chars, prev_locs = chars, locs

    return {"ok": not flags, "flags": flags}


def validate_story_quality(
    *,
    blueprint: dict[str, Any],
    beats: list[dict[str, Any]],
    synopsis: str,
    initial_world: dict[str, Any],
    final_world: dict[str, Any],
    initial_prog: dict[str, Any],
    final_prog: dict[str, Any],
) -> dict[str, Any]:
    flags: list[dict[str, Any]] = []
    scores: dict[str, Any] = {}

    n = len(beats or [])
    if n < 45:
        flags.append({"code": "beat_count_low", "detail": f"{n} beats (objetivo 45–70)"})
    if n > 70:
        flags.append({"code": "beat_count_high", "detail": f"{n} beats (objetivo 45–70)"})

    missing_cause = 0
    rewards = 0
    setbacks = 0
    purposes: list[str] = []
    loop_opens = 0
    loop_closes = 0
    metric_reveals = 0
    env_changes = 0
    generic_comp = 0
    dead_windows = 0

    for beat in beats or []:
        cause = str(beat.get("cause") or "").strip()
        event = str(beat.get("event") or "").strip()
        if not cause or not event:
            missing_cause += 1
        kind = str(beat.get("reward_or_setback") or "").lower()
        if "reward" in kind or "recompensa" in kind:
            rewards += 1
        if "setback" in kind or "revés" in kind or "reves" in kind or "crisis" in kind:
            setbacks += 1
        purposes.append(str(beat.get("story_purpose") or "").strip().lower())
        action = beat.get("open_loop_action") if isinstance(beat.get("open_loop_action"), dict) else {}
        op = str(action.get("action") or "").lower()
        if op in ("open", "reopen"):
            loop_opens += 1
        if op in ("close", "pay", "paid", "payoff"):
            loop_closes += 1
        reveals = beat.get("metric_reveal") or []
        if isinstance(reveals, list) and reveals:
            metric_reveals += 1
        vis = str(beat.get("visual_opportunity") or "").lower()
        if any(w in vis for w in ("casa", "oficina", "estadio", "viaje", "auto", "departamento", "arena")):
            env_changes += 1
        blob = _txt(beat)
        if any(re.search(p, blob) for p in GENERIC_COMPETITOR):
            generic_comp += 1

    scores["causality"] = "pass" if missing_cause <= max(2, n * 0.08) else "flag"
    if missing_cause:
        flags.append({"code": "missing_cause", "detail": f"{missing_cause} beats sin causa/evento"})

    scores["conflict"] = "pass"
    if generic_comp:
        scores["conflict"] = "flag"
        flags.append({"code": "generic_competitor", "detail": f"{generic_comp} beats con competidor genérico"})

    # Escalation: problems/rewards should grow — compare first vs second half setback/reward intensity via valuation/attendance
    att0 = _num(metric_value(initial_world, "ATTENDANCE"))
    att1 = _num(metric_value(final_world, "ATTENDANCE"))
    val0 = _num(metric_value(initial_world, "TEAM_VALUE"))
    val1 = _num(metric_value(final_world, "TEAM_VALUE"))
    scores["escalation"] = "pass" if (att1 > att0 or val1 > val0) and setbacks >= 2 else "flag"
    if setbacks < 2:
        flags.append({"code": "few_setbacks", "detail": f"{setbacks} reversos (hace falta trayectoria no lineal)"})
    if rewards < 4:
        flags.append({"code": "few_rewards", "detail": f"{rewards} recompensas visibles"})

    # Linear dopamine: long reward streaks
    streak = 0
    max_reward_streak = 0
    for beat in beats or []:
        kind = str(beat.get("reward_or_setback") or "").lower()
        if "reward" in kind:
            streak += 1
            max_reward_streak = max(max_reward_streak, streak)
        else:
            streak = 0
    if max_reward_streak >= 6:
        flags.append({"code": "linear_dopamine", "detail": f"{max_reward_streak} recompensas seguidas"})

    # Transformation — real life state, ignoring corrupt ownership >100
    scores["transformation"] = "pass"
    t_report = transformation_diff(initial_world, final_world, beats)
    if not t_report.get("ok"):
        scores["transformation"] = "fail"
        flags.append({"code": "weak_transformation", "detail": t_report.get("detail") or "la vida final no se distingue del inicio"})


    # Retention windows ~30-45s
    window: list[dict[str, Any]] = []
    window_s = 0.0
    for beat in beats or []:
        dur = _num(beat.get("duration_target_s"), 15)
        window.append(beat)
        window_s += dur
        if window_s >= 40:
            if not _window_has_change(window):
                dead_windows += 1
                flags.append(
                    {
                        "code": "dead_stretch",
                        "detail": f"~{int(window_s)}s sin cambio importante ({window[0].get('beat_id')}–{window[-1].get('beat_id')})",
                    }
                )
            window, window_s = [], 0.0
    scores["retention"] = "pass" if dead_windows <= 2 else "flag"

    # Repetition of purpose
    repeat_runs = 0
    run = 1
    for i in range(1, len(purposes)):
        if purposes[i] and purposes[i] == purposes[i - 1]:
            run += 1
            if run >= 4:
                repeat_runs += 1
        else:
            run = 1
    scores["repetition"] = "pass" if repeat_runs == 0 else "flag"
    if repeat_runs:
        flags.append({"code": "repetitive_beats", "detail": f"{repeat_runs} rachas del mismo tipo de beat"})

    # Open loops
    loops: dict[str, dict[str, Any]] = {}
    for beat in beats or []:
        story_after = beat.get("story_state_after") if isinstance(beat.get("story_state_after"), dict) else {}
        for loop in story_after.get("open_loops") or []:
            if isinstance(loop, dict) and loop.get("id"):
                loops[str(loop["id"])] = loop
        action = beat.get("open_loop_action") if isinstance(beat.get("open_loop_action"), dict) else {}
        lid = str(action.get("loop_id") or action.get("id") or "")
        op = str(action.get("action") or "").lower()
        if lid and op in ("open", "reopen"):
            loops.setdefault(lid, {"id": lid, "status": "open", "opened_at": beat.get("beat_id")})
        if lid and op in ("close", "pay", "paid", "payoff"):
            row = dict(loops.get(lid) or {"id": lid})
            row["status"] = "paid"
            row["closed_at"] = beat.get("beat_id")
            loops[lid] = row
    open_left = [l for l in loops.values() if str(l.get("status") or "open") == "open"]
    paid = [l for l in loops.values() if str(l.get("status") or "") in ("paid", "closed")]
    scores["open_loops"] = "pass"
    important_open = [
        l
        for l in open_left
        if l.get("important", True) and not l.get("intentional_unresolved")
    ]
    intentional = [l for l in open_left if l.get("intentional_unresolved")]
    if important_open:
        scores["open_loops"] = "fail"
        flags.append(
            {
                "code": "loops_unpaid",
                "detail": f"{len(important_open)} loops importantes sin payoff",
                "hard": True,
            }
        )
    allowed = blueprint.get("intentional_unresolved_loops") or []
    if len(intentional) > max(1, len(allowed) or 1):
        flags.append({"code": "too_many_open_loops", "detail": f"{len(intentional)} loops intencionales"})

    ending = " ".join(
        str(blueprint.get(k) or "")
        for k in ("ending", "final_state", "unresolved_or_bittersweet_element")
    )
    syn = (synopsis or "").lower()
    if any(re.search(p, ending.lower()) or re.search(p, syn[-800:] if syn else "") for p in MORAL_PATTERNS):
        scores["ending"] = "flag"
        flags.append({"code": "moral_ending", "detail": "el final suena a moraleja, no a escena/estado"})
    else:
        scores["ending"] = "pass" if str(blueprint.get("ending") or "").strip() else "flag"
        if not str(blueprint.get("ending") or "").strip():
            flags.append({"code": "missing_ending", "detail": "no hay escena/estado final"})

    words = len(re.findall(r"\S+", synopsis or ""))
    syn_rep = validate_synopsis(synopsis, blueprint, initial_world, final_world)
    if syn_rep.get("flags"):
        flags.extend(syn_rep["flags"])
    scores["synopsis"] = "pass" if syn_rep.get("ok") else "fail"

    env_start = str(((initial_world.get("life") or {}).get("home")) or ((initial_world.get("locations") or {}).get("home") or ""))
    env_end = str(((final_world.get("life") or {}).get("home")) or ((final_world.get("locations") or {}).get("home") or ""))
    scores["progression"] = "pass" if env_changes >= 4 or env_start != env_end else "flag"
    if env_changes < 3 and env_start == env_end:
        flags.append({"code": "life_not_visual", "detail": "pocos cambios visibles de vida/entorno"})

    hard = validate_hard_gates(beats, initial_world=initial_world, final_world=final_world, blueprint=blueprint)
    flags.extend(hard["fails"])
    scores["continuity"] = "pass" if hard["ok"] else "fail"
    soft = validate_continuity(beats, initial_world=initial_world)
    for f in soft.get("flags") or []:
        if f.get("code") not in {x.get("code") for x in hard["fails"]}:
            flags.append(f)

    hard_codes = {f.get("code") for f in flags if f.get("hard")}
    return {
        "scores": scores,
        "flags": flags,
        "hard_fails": [f for f in flags if f.get("hard")],
        "transformation": t_report,
        "stats": {
            "beats": n,
            "rewards": rewards,
            "setbacks": setbacks,
            "loop_opens": loop_opens,
            "loop_closes": loop_closes,
            "open_loops_final": len(open_left),
            "paid_loops": len(paid),
            "metric_reveals": metric_reveals,
            "env_changes": env_changes,
            "synopsis_words": words,
            "max_reward_streak": max_reward_streak,
        },
        "ok": not any(s in ("flag", "fail") for s in scores.values()) and not hard_codes,
    }


def _window_has_change(window: list[dict[str, Any]]) -> bool:
    trivial = {"elapsed_days", "date_or_period", "label"}
    for beat in window:
        if str(beat.get("reward_or_setback") or "").strip():
            return True
        if beat.get("metric_reveal"):
            return True
        action = beat.get("open_loop_action") if isinstance(beat.get("open_loop_action"), dict) else {}
        if action.get("action"):
            return True
        if str(beat.get("viewer_question") or "").strip():
            return True
        purpose = str(beat.get("story_purpose") or "").lower()
        if any(p in purpose for p in ("decision", "crisis", "reversal", "reward", "inciting", "climax", "commitment", "proof")):
            return True
        vis = str(beat.get("visual_opportunity") or "").lower()
        if any(w in vis for w in ("casa", "oficina", "estadio", "viaje", "nuevo", "departamento", "arena")):
            return True
        wd = beat.get("world_delta") if isinstance(beat.get("world_delta"), dict) else {}
        if _meaningful_delta(wd, trivial):
            return True
    return False


def _meaningful_delta(delta: dict[str, Any], trivial: set[str]) -> bool:
    if not delta:
        return False
    for k, v in delta.items():
        key = str(k).split(".")[-1]
        if key in trivial or k in ("time",):
            if isinstance(v, dict) and _meaningful_delta(v, trivial):
                return True
            continue
        if v not in (None, "", {}, []):
            return True
    return False


def assemble_review(payload: dict[str, Any]) -> dict[str, Any]:
    blueprint = payload.get("blueprint") if isinstance(payload.get("blueprint"), dict) else {}
    beats = payload.get("beats") if isinstance(payload.get("beats"), list) else []
    initial_world = payload.get("initial_world") or {}
    final_world = payload.get("final_world") or (beats[-1]["world_state_after"] if beats else {})
    quality = payload.get("quality") if isinstance(payload.get("quality"), dict) else {}
    synopsis = str(payload.get("synopsis") or "")

    timeline = []
    rewards = []
    setbacks = []
    major = []
    for beat in beats:
        snap = beat.get("world_snapshot") or world_snapshot(beat.get("world_state_after") or {})
        row = {
            "beat_id": beat.get("beat_id"),
            "age": snap.get("age"),
            "time": beat.get("time") or snap.get("time"),
            "event": beat.get("event"),
            "cash": snap.get("cash"),
            "net_worth": snap.get("net_worth"),
            "job": snap.get("job"),
            "home": snap.get("home"),
            "ownership": snap.get("ownership"),
            "team_value": snap.get("team_value"),
            "team_debt": snap.get("team_debt"),
            "team_cash": snap.get("team_cash"),
            "revenue": snap.get("revenue"),
            "attendance": snap.get("attendance"),
            "record": snap.get("record"),
            "sporting_status": snap.get("sporting_status") or snap.get("sports_status"),
            "debt_risk_state": snap.get("debt_risk_state"),
            "life_change": _life_change(beat),
            "metric_reveal": beat.get("metric_reveal") or [],
        }
        if row["metric_reveal"] or row["life_change"] or str(beat.get("reward_or_setback") or "").strip():
            timeline.append(row)
        kind = str(beat.get("reward_or_setback") or "").lower()
        if "reward" in kind or "recompensa" in kind:
            rewards.append({"beat_id": beat.get("beat_id"), "time": beat.get("time"), "event": beat.get("event"), "kind": kind})
        if any(x in kind for x in ("setback", "revés", "reves", "crisis", "mistake")):
            cat = kind.split(":", 1)[-1] if ":" in kind else "unspecified"
            setbacks.append(
                {
                    "beat_id": beat.get("beat_id"),
                    "time": beat.get("time"),
                    "event": beat.get("event"),
                    "kind": kind,
                    "category": cat,
                }
            )
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
        } or kind:
            major.append(
                {
                    "beat_id": beat.get("beat_id"),
                    "purpose": beat.get("story_purpose"),
                    "event": beat.get("event"),
                    "time": beat.get("time"),
                }
            )

    loops = []
    if beats:
        final_story = beats[-1].get("story_state_after") or {}
        seen: dict[str, dict[str, Any]] = {}
        for beat in beats:
            after = beat.get("story_state_after") or {}
            for loop in after.get("open_loops") or []:
                if isinstance(loop, dict) and loop.get("id"):
                    seen[str(loop["id"])] = loop
            action = beat.get("open_loop_action") if isinstance(beat.get("open_loop_action"), dict) else {}
            if action.get("loop_id") or action.get("id"):
                lid = str(action.get("loop_id") or action.get("id"))
                row = dict(seen.get(lid) or {"id": lid, "question": action.get("question") or ""})
                if str(action.get("action") or "").lower() in ("open", "reopen"):
                    row["opened_at"] = beat.get("beat_id")
                    row["status"] = "open"
                if str(action.get("action") or "").lower() in ("close", "pay", "paid", "payoff"):
                    row["closed_at"] = beat.get("beat_id")
                    row["status"] = "paid"
                seen[lid] = row
        loops = list(seen.values()) or list(final_story.get("open_loops") or [])

    fw = final_world if isinstance(final_world, dict) else {}
    personal = fw.get("personal") or {}
    team = fw.get("team") or {}
    loc = fw.get("locations") or {}
    life = fw.get("life") or {}
    sports = fw.get("sports") or {}
    fin = fw.get("finance") or {}
    payoffs = []
    sports_prog = []
    for beat in beats:
        for p in beat.get("aspirational_payoffs") or []:
            payoffs.append({"beat_id": beat.get("beat_id"), "time": beat.get("time"), **(p if isinstance(p, dict) else {"scene": p})})
        sa = (beat.get("world_state_after") or {}).get("sports") or {}
        sb = (beat.get("world_state_before") or {}).get("sports") or {}
        if sa.get("wins") != sb.get("wins") or sa.get("season") != sb.get("season") or sa.get("playoff_status") != sb.get("playoff_status"):
            sports_prog.append(
                {
                    "beat_id": beat.get("beat_id"),
                    "time": beat.get("time"),
                    "season": sa.get("season_label") or sa.get("season"),
                    "record": f"{sa.get('wins')}-{sa.get('losses')}",
                    "status": sa.get("playoff_status"),
                    "event": beat.get("event"),
                }
            )
    acq = fw.get("acquisition") or (blueprint.get("business_or_vehicle") or {}).get("acquisition") or {}
    return {
        "overview": {
            "protagonist": (blueprint.get("protagonist") or {}),
            "fantasy": (blueprint.get("fantasy") or {}),
            "vehicle": (blueprint.get("business_or_vehicle") or {}),
            "world": (blueprint.get("fiction_world") or {}),
            "ending_type": blueprint.get("ending_type"),
            "ending": blueprint.get("ending"),
            "final_state": blueprint.get("final_state"),
            "unresolved": blueprint.get("unresolved_or_bittersweet_element"),
        },
        "acquisition": acq,
        "timeline": timeline,
        "major_events": major,
        "rewards": rewards,
        "setbacks": setbacks,
        "aspirational_payoffs": payoffs,
        "open_loops": loops,
        "ownership_ledger": fw.get("ownership_ledger") or {},
        "equity_events": fw.get("equity_events") or [],
        "financial_events": fw.get("financial_events") or [],
        "season_history": sports.get("season_history") or [],
        "debt_risk_history": fw.get("debt_risk_history") or [],
        "debt_risk_state": fin.get("debt_risk_state"),
        "sports_progression": sports_prog,
        "ending": {
            "scene": blueprint.get("ending"),
            "final_state": blueprint.get("final_state"),
            "type": blueprint.get("ending_type"),
            "unresolved": blueprint.get("unresolved_or_bittersweet_element"),
        },
        "final_world": {
            "age": (fw.get("time") or {}).get("protagonist_age"),
            "period": (fw.get("time") or {}).get("date_or_period") or (fw.get("time") or {}).get("label"),
            "cash": life.get("personal_cash") or personal.get("cash"),
            "net_worth": life.get("personal_net_worth"),
            "job": life.get("job") or personal.get("working_status"),
            "home": life.get("home") or loc.get("home"),
            "ownership": (fw.get("ownership_ledger") or {}).get("protagonist"),
            "ledger": fw.get("ownership_ledger"),
            "team_value": team.get("valuation"),
            "team_debt": fin.get("team_debt") or team.get("debt"),
            "team_cash": fin.get("team_cash"),
            "revenue": fin.get("annual_revenue"),
            "attendance": team.get("attendance"),
            "record": team.get("season_record") or {"wins": sports.get("wins"), "losses": sports.get("losses")},
            "sports": sports,
            "life": life,
            "team_name": team.get("name"),
            "debt_risk_state": fin.get("debt_risk_state"),
            "championships": sports.get("championships"),
            "season_history": sports.get("season_history") or [],
        },
        "world_progression": [
            {"beat_id": b.get("beat_id"), "time": b.get("time"), **(b.get("world_snapshot") or {})}
            for b in beats
            if b.get("metric_reveal") or b.get("ops")
        ],
        "life_progression": [
            {
                "beat_id": b.get("beat_id"),
                "time": b.get("time"),
                "life": _life_change(b),
                "progression": b.get("progression_after") or {},
            }
            for b in beats
            if _life_change(b)
        ],
        "quality_flags": quality.get("flags") or [],
        "quality_scores": quality.get("scores") or {},
        "hard_fails": quality.get("hard_fails") or [],
        "synopsis": synopsis,
    }


def _life_change(beat: dict[str, Any]) -> str:
    before = beat.get("world_state_before") or {}
    after = beat.get("world_state_after") or {}
    bits = []
    bp, ap = before.get("personal") or {}, after.get("personal") or {}
    bl, al = before.get("locations") or {}, after.get("locations") or {}
    if bp.get("living_situation") != ap.get("living_situation") and ap.get("living_situation"):
        bits.append(str(ap.get("living_situation")))
    if bp.get("working_status") != ap.get("working_status") and ap.get("working_status"):
        bits.append(str(ap.get("working_status")))
    if bl.get("home") != al.get("home") and al.get("home"):
        bits.append(f"casa: {al.get('home')}")
    if bl.get("office") != al.get("office") and al.get("office"):
        bits.append(f"oficina: {al.get('office')}")
    if bl.get("arena") != al.get("arena") and al.get("arena"):
        bits.append(f"arena: {al.get('arena')}")
    blife, alife = before.get("life") or {}, after.get("life") or {}
    if blife.get("job") != alife.get("job") and alife.get("job"):
        bits.append(str(alife.get("job")))
    if blife.get("home") != alife.get("home") and alife.get("home"):
        bits.append(str(alife.get("home")))
    vis = str(beat.get("visual_opportunity") or "")
    if not bits and any(w in vis.lower() for w in ("casa", "departamento", "oficina", "viaje")):
        bits.append(vis[:80])
    return " · ".join(bits)


def format_pilot_report(payload: dict[str, Any], review: dict[str, Any]) -> str:
    bp = payload.get("blueprint") or {}
    q = payload.get("quality") or {}
    fw = review.get("final_world") or {}
    acq = review.get("acquisition") or {}
    hard = q.get("hard_fails") or review.get("hard_fails") or []
    ready = not hard
    lines = [
        "CHECK ALS — FASE 2.2 PILOTO",
        "=" * 72,
        "",
        f"REVIEW READY: {'YES' if ready else 'NO — hard fails, no listo para aprobación'}",
        "",
        "## 1. STORY SYNOPSIS",
        "",
        str(payload.get("synopsis") or "").strip() or "(vacía)",
        "",
        "## 2. ACQUISITION STRUCTURE",
        "",
        acq.get("summary") or (bp.get("business_or_vehicle") or {}).get("acquisition_structure") or json_block(acq),
        json_block({k: acq.get(k) for k in (
            "asking_price", "debt_assumed", "your_cash_contribution", "local_investors_cash",
            "seller_financing", "existing_liabilities_assumed", "your_ownership", "investor_ownership", "seller_retained",
        ) if acq}),
        "",
        "## 3. LIFE TIMELINE",
        "",
    ]
    for row in review.get("timeline") or []:
        lines.append(
            f"- AGE {row.get('age')} | JOB {row.get('job') or '—'} | HOME {row.get('home') or '—'} "
            f"| PERSONAL CASH {format_money(row.get('cash'))} | NET WORTH {format_money(row.get('net_worth'))} "
            f"| OWNERSHIP {row.get('ownership')}% | TEAM VALUE {format_money(row.get('team_value'))} "
            f"| TEAM DEBT {format_money(row.get('team_debt'))} | TEAM CASH {format_money(row.get('team_cash'))} "
            f"| REVENUE {format_money(row.get('revenue'))} | ATTENDANCE {row.get('attendance')} "
            f"| SPORTING {row.get('record')} {row.get('sporting_status') or ''} "
            + (f"| LIFE {row.get('life_change')}" if row.get("life_change") else "")
            + f" | {row.get('event')}"
        )
    lines += ["", "## 4. SEASON HISTORY", ""]
    seasons = review.get("season_history") or fw.get("season_history") or []
    if not seasons:
        lines.append("(sin temporadas archivadas)")
    for s in seasons:
        if not isinstance(s, dict):
            continue
        lines.append(
            f"- SEASON {s.get('season')} | RECORD {s.get('record')} | POS {s.get('league_position')} "
            f"| PLAYOFF {s.get('playoff_result')} | CHAMPIONSHIP {s.get('championship')} "
            f"| AVG ATT {s.get('attendance_avg')} | TEAM VALUE {format_money(s.get('team_value'))} "
            f"| REVENUE {format_money(s.get('revenue'))} | {', '.join(s.get('major_events') or []) or '—'}"
        )
    lines += ["", "## 5. OWNERSHIP LEDGER", "", json_block(review.get("ownership_ledger") or fw.get("ledger") or {})]
    for ev in review.get("equity_events") or []:
        lines.append(f"- [{ev.get('beat_id')}] {ev.get('op')} {ev.get('note') or ev.get('pct')} → {ev.get('ledger')}")
    lines += ["", "## 6. FINANCIAL LEDGER — HIGHLIGHTS", ""]
    highlights = [
        e
        for e in (review.get("financial_events") or [])
        if isinstance(e, dict)
        and str(e.get("type") or "") in {
            "acquisition",
            "equity_investment",
            "sponsor",
            "media",
            "player_signing",
            "coach_contract",
            "facility_upgrade",
            "debt_payment",
            "loan",
            "credit_line",
            "bridge_loan",
            "owner_injection",
            "investor_injection",
            "owner_distribution",
        }
    ]
    if not highlights:
        highlights = (review.get("financial_events") or [])[-12:]
    for e in highlights:
        lines.append(
            f"- [{e.get('id')}] {e.get('type')} {format_money(e.get('amount'))} "
            f"cash {e.get('cash_delta')} debt {e.get('debt_delta')} · {e.get('reason')} ({e.get('beat_id')})"
        )
    lines += ["", "## 7. DEBT PROGRESSION", ""]
    drh = review.get("debt_risk_history") or []
    if not drh:
        lines.append(f"- final debt_risk_state: {review.get('debt_risk_state') or fw.get('debt_risk_state') or '—'}")
    for row in drh:
        lines.append(
            f"- [{row.get('beat_id')}] {row.get('state')} · debt {format_money(row.get('debt'))} "
            f"cash {format_money(row.get('cash'))} rev {format_money(row.get('revenue'))}"
        )
    lines += ["", "## 8. ASPIRATIONAL PAYOFFS", ""]
    for r in review.get("aspirational_payoffs") or []:
        lines.append(f"- [{r.get('beat_id')}] {r.get('id')}: {r.get('scene')}")
    if not review.get("aspirational_payoffs"):
        lines.append("(ninguna)")
    lines += ["", "## 9. SETBACKS", ""]
    for r in review.get("setbacks") or []:
        lines.append(f"- [{r.get('beat_id')}] category={r.get('category') or r.get('kind')} | {r.get('event')}")
    lines += ["", "## 10. OPEN LOOPS", ""]
    for loop in review.get("open_loops") or []:
        lines.append(
            f"- question: {loop.get('question')} | opened: {loop.get('opened_at')} | "
            f"paid: {loop.get('status')} | payoff: {loop.get('payoff') or loop.get('paid_at') or loop.get('closed_at') or '—'}"
        )
    lines += ["", "## 11. FINAL WORLD STATE", ""]
    for k, v in fw.items():
        if k in ("life", "sports", "ledger", "season_history"):
            lines.append(f"- {k}: {json_block(v) if isinstance(v, (dict, list)) else v}")
        else:
            lines.append(f"- {k}: {v}")
    lines += ["", "## 12. QUALITY REPORT", ""]
    scores = q.get("scores") or review.get("quality_scores") or {}
    for k, v in scores.items():
        lines.append(f"- {k}: {v}")
    if q.get("transformation"):
        lines.append(f"- transformation_dims: {q.get('transformation')}")
    lines += ["", "## 13. HARD VALIDATION", ""]
    if not hard:
        lines.append("ALL GREEN")
    for f in hard:
        lines.append(f"- HARD FAIL [{f.get('code')}] {f.get('detail')} {f.get('beat_id') or ''}")
    lines += ["", "## FLAGS", ""]
    flags = q.get("flags") or review.get("quality_flags") or []
    if not flags:
        lines.append("(ninguno)")
    for f in flags:
        if f.get("hard"):
            continue
        lines.append(f"- [{f.get('code')}] {f.get('detail')} {('· ' + str(f.get('beat_id'))) if f.get('beat_id') else ''}")
    lines.append("")
    lines.append("STOP. No script. No visuals. No voice. No render. No Concept Engine.")
    return "\n".join(lines)


def json_block(data: Any) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, indent=2)
