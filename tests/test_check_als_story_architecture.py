"""Check ALS Fase 2: story architecture deltas, continuity, quality, persistence."""
from __future__ import annotations

import pytest

from src.documentary.formats.check_als.story_arch import (
    apply_world_delta,
    empty_progression_state,
    empty_story_state,
    empty_world_state,
    load_architecture,
    reconstruct_beats,
)
from src.documentary.formats.check_als.story_architect import (
    approve_check_story,
    finalize_architecture,
)
from src.documentary.formats.check_als.story_sim import apply_ops, force_pre_acquisition, ledger_total
from src.documentary.formats.check_als.story_validate import validate_continuity, validate_hard_gates, validate_story_quality
from src.documentary.project import create_project, derive_progress, load_project
from src.documentary.script_service import generate_documentary_script


@pytest.fixture()
def tmp_projects(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setenv("FRAMEFACTORY_PROJECTS_DIR", str(root))
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    return root


def test_acquisition_delta_example():
    world = force_pre_acquisition(empty_world_state())
    world["life"]["personal_cash"] = 18400
    world["life"]["job"] = "empleado de oficina"
    after = apply_ops(
        world,
        [{
            "op": "acquire_team",
            "your_cash": 12000,
            "investor_cash": 85000,
            "your_pct": 51,
            "investor_pct": 39,
            "seller_pct": 10,
            "debt_assumed": 640000,
        }],
    )
    assert after["life"]["personal_cash"] == 6400
    assert after["ownership_ledger"]["protagonist"] == 51
    assert after["team"]["ownership_percentage"] == 51
    assert after["finance"]["team_debt"] == 640000
    assert abs(ledger_total(after["ownership_ledger"]) - 100) < 0.2
    assert after["life"]["job"] == "empleado de oficina"


def test_reconstruct_beats_chain():
    initial = force_pre_acquisition(empty_world_state())
    initial["life"]["personal_cash"] = 18400
    beats = reconstruct_beats(
        initial,
        empty_story_state(),
        empty_progression_state(),
        [
            {
                "beat_id": "b01",
                "event": "firmás el acuerdo de compra del equipo",
                "ops": [{
                    "op": "acquire_team",
                    "your_cash": 12000,
                    "your_pct": 51,
                    "investor_pct": 39,
                    "seller_pct": 10,
                    "debt_assumed": 640000,
                }],
                "open_loop_action": {"action": "open", "loop_id": "debt", "question": "¿podrás pagar la deuda?"},
            },
            {
                "beat_id": "b02",
                "event": "bajas entradas y sube el público",
                "ops": [{"op": "ticket_night", "attendance": 2184}],
                "open_loop_action": {"action": "close", "loop_id": "debt", "question": "¿podrás pagar la deuda?"},
            },
        ],
    )
    assert beats[0]["world_state_after"]["life"]["personal_cash"] == 6400
    assert beats[0]["world_state_after"]["ownership_ledger"]["protagonist"] == 51
    assert beats[1]["world_state_before"]["life"]["personal_cash"] == 6400
    assert beats[1]["world_state_after"]["team"]["attendance"] == 2184
    loops = beats[1]["story_state_after"]["open_loops"]
    assert loops and loops[0]["status"] == "paid"
    assert loops[0]["closed_at"] == "b02"


def test_ledger_always_100():
    w = force_pre_acquisition(empty_world_state())
    w = apply_ops(w, [{"op": "acquire_team", "your_pct": 51, "investor_pct": 39, "seller_pct": 10, "your_cash": 12000}])
    assert abs(ledger_total(w["ownership_ledger"]) - 100) < 0.2
    w = apply_ops(w, [{"op": "equity_sale", "from": "protagonist", "to": "investors", "pct": 80, "cash": 20000}])
    assert w["ownership_ledger"]["protagonist"] <= 51
    assert abs(ledger_total(w["ownership_ledger"]) - 100) < 0.2


def test_championship_requires_season():
    w = force_pre_acquisition(empty_world_state())
    w = apply_ops(w, [{"op": "acquire_team", "your_cash": 12000}])
    early = apply_ops(w, [{"op": "championship"}])
    assert early["sports"]["championships"] == 0
    later = apply_ops(
        w,
        [
            {"op": "season_stretch", "wins": 18, "losses": 8, "attendance": 4200},
            {"op": "playoff_berth"},
            {"op": "championship"},
        ],
    )
    assert later["sports"]["championships"] >= 1
    assert later["team"]["valuation"] > w["team"]["valuation"]


def test_unexplained_money_flags():
    initial = empty_world_state()
    initial["life"]["personal_cash"] = 1000
    beats = reconstruct_beats(
        initial,
        empty_story_state(),
        empty_progression_state(),
        [{"cause": "estás en casa", "event": "mirás el techo", "world_delta": {"cash": 20000}}],
    )
    report = validate_continuity(beats, initial_world=initial)
    assert any(f["code"] == "money_unexplained" for f in report["flags"])


def test_age_cannot_go_backwards():
    initial = empty_world_state()
    initial["time"]["protagonist_age"] = 22
    initial["time"]["age_at_start"] = 22
    beats = reconstruct_beats(
        initial,
        empty_story_state(),
        empty_progression_state(),
        [{"event": "salto raro", "world_delta": {"time": {"protagonist_age": {"set": 19}}}}],
    )
    assert beats[0]["world_state_after"]["time"]["protagonist_age"] >= 22


def test_moral_ending_flags():
    bp = {"ending": "Y aprendiste que con esfuerzo todo es posible.", "final_state": "feliz"}
    report = validate_story_quality(
        blueprint=bp,
        beats=[],
        synopsis="aprendiste que con esfuerzo todo es posible " * 40,
        initial_world=empty_world_state(),
        final_world=empty_world_state(),
        initial_prog=empty_progression_state(),
        final_prog=empty_progression_state(),
    )
    assert any(f["code"] == "moral_ending" for f in report["flags"])
    assert report["scores"]["ending"] == "flag"


def test_generic_competitor_flags():
    beats = reconstruct_beats(
        empty_world_state(),
        empty_story_state(),
        empty_progression_state(),
        [
            {
                "cause": "el equipo crece",
                "event": "aparece un competidor grande con millones",
                "consequence": "te asustás",
                "reward_or_setback": "setback:competidor",
            }
        ],
    )
    report = validate_story_quality(
        blueprint={"ending": "mirás el estadio lleno"},
        beats=beats,
        synopsis="x " * 900,
        initial_world=empty_world_state(),
        final_world=beats[-1]["world_state_after"],
        initial_prog=empty_progression_state(),
        final_prog=empty_progression_state(),
    )
    assert any(f["code"] == "generic_competitor" for f in report["flags"])


def _pilot_payload(n: int = 48) -> dict:
    initial = force_pre_acquisition(empty_world_state())
    initial["time"] = {"protagonist_age": 22, "age_at_start": 22, "date_or_period": "marzo 2024", "elapsed_days": 0, "label": "DAY 1"}
    initial["life"]["personal_cash"] = 18400
    initial["life"]["job"] = "empleado de oficina"
    initial["life"]["home"] = "departamento compartido"
    initial["team"]["name"] = "Halcones de Puerto Norte"
    initial["team"]["attendance"] = 612
    beats = []
    for i in range(n):
        bid = f"b{i+1:02d}"
        delta: dict = {}
        ops: list = []
        story_delta: dict = {}
        kind = ""
        purpose = "texture"
        loop = {}
        reveal = []
        visual = "pasillo de oficinas"
        life_event = f"seguís empujando el equipo ({i+1})"
        if i == 0:
            purpose = "opening"
            visual = "departamento compartido"
            ops = [{"op": "advance_time", "months": 0}]
        elif i == 2:
            purpose = "inciting_incident"
            ops = [{
                "op": "acquire_team",
                "your_cash": 12000,
                "investor_cash": 85000,
                "your_pct": 51,
                "investor_pct": 39,
                "seller_pct": 10,
                "debt_assumed": 640000,
                "asking_price": 1,
                "seller_financing": 200000,
            }]
            loop = {"action": "open", "loop_id": "debt", "question": "¿podrás pagar la deuda?"}
            reveal = ["CASH", "OWNERSHIP"]
            kind = "setback:asumís deuda"
            life_event = "firmás la compra del equipo por un peso y asumís la deuda"
        elif i == 8:
            purpose = "first_proof"
            ops = [{"op": "season_stretch", "wins": 4, "losses": 3, "attendance": 2184}, {"op": "sponsor_deal", "annual": 40000}]
            reveal = ["ATTENDANCE"]
            kind = "reward:primer público real"
            visual = "estadio con 2100 personas"
            life_event = "bajas entradas y el gimnasio se llena"
        elif i == 16:
            purpose = "midpoint"
            ops = [{"op": "quit_job"}, {"op": "advance_time", "months": 8}]
            kind = "reward:first office"
            visual = "oficina improvisada en el estadio"
            life_event = "dejás el trabajo de oficina y te instalás en el estadio"
        elif i == 24:
            purpose = "major_success"
            ops = [{"op": "season_stretch", "wins": 12, "losses": 6, "attendance": 4600}, {"op": "ticket_night", "attendance": 4800}]
            reveal = ["ATTENDANCE", "RECORD"]
            kind = "reward:primer sold-out"
            visual = "estadio sold out"
            life_event = "el gimnasio se agota y un sponsor local llama"
        elif i == 30:
            purpose = "major_reversal"
            ops = [{"op": "pay_debt", "amount": 40000}, {"op": "injury"}]
            kind = "setback:la deuda vence"
            loop = {"action": "open", "loop_id": "due", "question": "¿llegás al vencimiento?"}
            life_event = "vence una cuota de la deuda y pagás con lo último de caja"
        elif i == 36:
            purpose = "crisis"
            ops = [{"op": "injury"}, {"op": "advance_time", "months": 6}]
            kind = "setback:lesión de la estrella"
            life_event = "la estrella se lesiona y cae la asistencia"
        elif i == 40:
            purpose = "decision"
            ops = [{"op": "buyback", "from": "investors", "pct": 9, "cash": 25000, "paid_by": "team"}]
            loop = {"action": "close", "loop_id": "debt"}
            kind = "reward:ownership increase"
            life_event = "rechazás vender y recomprás porcentaje"
        elif i == 45:
            purpose = "climax"
            ops = [
                {"op": "season_stretch", "wins": 8, "losses": 4, "attendance": 4700},
                {"op": "playoff_berth"},
                {"op": "advance_time", "months": 10},
            ]
            reveal = ["TEAM_VALUE"]
            kind = "reward:valuation milestone"
            visual = "estadio lleno desde el túnel"
            life_event = "el equipo vale más y el estadio vuelve a llenarse"
        elif i == n - 1:
            purpose = "ending"
            ops = [
                {"op": "move_home", "home": "departamento propio cerca de la arena", "cost": 4000},
                {"op": "help_family", "amount": 4000},
                {"op": "owner_draw", "amount": 12000},
                {"op": "advance_time", "months": 8},
            ]
            visual = "casa nueva y túnel del estadio"
            kind = "reward:moving out"
            loop = {"action": "close", "loop_id": "due"}
            life_event = "cobrás el primer sueldo real de dueño y te mudás"
        beats.append(
            {
                "beat_id": bid,
                "time": f"BEAT {i+1}",
                "duration_target_s": 16,
                "cause": "el estado anterior lo fuerza",
                "event": life_event,
                "consequence": "el mundo se mueve un milímetro",
                "story_purpose": purpose,
                "world_delta": delta,
                "ops": ops,
                "story_delta": story_delta,
                "progression_delta": {"wealth_level": 1} if i in (8, 24, 40, n - 1) else {},
                "emotional_goal": "pressure",
                "viewer_question": "¿aguanta?" if i % 5 == 0 else "",
                "open_loop_action": loop,
                "reward_or_setback": kind,
                "metric_reveal": reveal,
                "visual_opportunity": visual,
                "transition_to_next": "sigue",
                "contribution": "world change",
            }
        )
    bp = {
        "protagonist": {"age": 22, "starting_life": "oficina", "desire": "tener un equipo"},
        "fantasy": {"surface_desire": "comprar el equipo", "deeper_desire": "ser tomado en serio"},
        "business_or_vehicle": {
            "what_is_being_built_or_owned": "Halcones",
            "acquisition_structure": "$1 + asunción de deuda + 51% con inversores locales",
            "acquisition": {
                "asking_price": 1,
                "debt_assumed": 640000,
                "your_cash_contribution": 12000,
                "local_investors_cash": 85000,
                "seller_financing": 200000,
                "your_ownership": 51,
                "investor_ownership": 39,
                "seller_retained": 10,
            },
        },
        "fiction_world": {"team_name": "Halcones de Puerto Norte", "league_name": "Liga Sur", "city": "Puerto Norte"},
        "ending_type": "open_future",
        "inciting_incident": "te ofrecen el club insolvente",
        "ending": "AGE 26. El estadio está lleno. Mirás desde el túnel. El teléfono vibra con una oferta. Esta vez la vas a leer mañana.",
        "final_state": "dueño, casa propia, equipo vivo",
        "intentional_unresolved_loops": ["offer"],
    }
    synopsis = (
        "Tenés 22 años y un trabajo de oficina. Firmás la compra: un peso, la deuda, el 51% con inversores. "
        "Renunciás. Te mudás a un departamento cerca de la arena. Llevás a tus padres al palco. "
        "Hay lesión, la deuda vence, pagás. El estadio se llena, hay playoffs, el valor del equipo sube. "
        "Hoy el club es tuyo y tu vida ya no es la de la oficina. "
    ) * 18
    return {
        "blueprint": bp,
        "synopsis": synopsis,
        "initial_world": initial,
        "initial_story": empty_story_state(),
        "initial_progression": empty_progression_state(),
        "beats": beats,
    }


def test_persist_and_human_gate_stop(tmp_projects):
    p = create_project(
        "POV: Compras un equipo de básquet al borde de la quiebra",
        title="POV: Compras un equipo de básquet al borde de la quiebra",
        content_format="check_als",
        language="es",
        concept={"title": "POV: Compras un equipo de básquet al borde de la quiebra", "premise": "compras un equipo"},
        project_id="pilot-test-basket",
    )
    assert p["ui_step"] == "story"
    payload = _pilot_payload()
    out = finalize_architecture(p, payload)
    assert out["ui_step"] == "story"
    assert out["check_story"]["generated"] is True
    assert out["story_plan_approved"] is False
    arch = load_architecture(out)
    assert len(arch["beats"]) == 48
    assert arch["beats"][0]["world_state_after"]["team"]["ownership_percentage"] == 0
    # beat 3 is index 2
    assert arch["beats"][2]["world_state_after"]["team"]["ownership_percentage"] == 51
    approved = approve_check_story(load_project(out["id"]))
    assert approved["check_story_approved"] is True
    assert approved["ui_step"] == "script"
    assert approved["story_plan_approved"] is False
    prog = derive_progress(approved)
    assert prog["current"] == "script"
    assert prog["flags"]["script"] is False
    with pytest.raises(ValueError, match="Aprobá la Story Architecture"):
        generate_documentary_script({**approved, "check_story_approved": False}, use_llm=False)
    generated = generate_documentary_script(load_project(out["id"]), use_llm=False)
    assert generated.get("script")
    assert "tienes" in generated["script"].lower()
    assert "vos" not in generated["script"].lower()


def test_quality_on_causal_chain():
    payload = _pilot_payload()
    beats = reconstruct_beats(
        payload["initial_world"],
        payload["initial_story"],
        payload["initial_progression"],
        payload["beats"],
    )
    q = validate_story_quality(
        blueprint=payload["blueprint"],
        beats=beats,
        synopsis=payload["synopsis"],
        initial_world=payload["initial_world"],
        final_world=beats[-1]["world_state_after"],
        initial_prog=payload["initial_progression"],
        final_prog=beats[-1]["progression_after"],
    )
    assert q["scores"]["ending"] == "pass"
    assert q["scores"]["causality"] == "pass"
    assert q["stats"]["beats"] == 48


def test_new_season_keeps_history_and_titles():
    w = force_pre_acquisition(empty_world_state())
    w = apply_ops(
        w,
        [
            {"op": "acquire_team", "your_cash": 12000},
            {"op": "season_stretch", "wins": 18, "losses": 8, "attendance": 4200},
            {"op": "playoff_berth"},
            {"op": "championship_won"},
            {"op": "new_season"},
        ],
    )
    assert w["sports"]["championships"] == 1
    assert w["sports"]["wins"] == 0
    assert w["sports"]["losses"] == 0
    assert w["sports"]["playoff_status"] == "regular"
    hist = w["sports"]["season_history"]
    assert hist
    assert hist[0]["record"] == "18-8"
    assert hist[0]["championship"] is True


def test_pre_acquisition_time_does_not_burn_team_cash():
    w = force_pre_acquisition(empty_world_state())
    w["finance"]["annual_revenue"] = 100000
    w["finance"]["annual_expenses"] = 400000
    w["finance"]["team_cash"] = 0
    after = apply_ops(w, [{"op": "advance_time", "months": 6}])
    assert after["finance"]["team_cash"] >= 0
    assert after["acquisition"]["closed"] is False


def test_debt_risk_payoff_without_zero_debt():
    from src.documentary.formats.check_als.story_sim import compute_debt_risk

    fin = {
        "team_debt": 437000,
        "team_cash": 3360000,
        "annual_revenue": 2180000,
        "annual_expenses": 900000,
        "debt_service": 35000,
    }
    assert compute_debt_risk(fin) in ("manageable", "healthy")
    broke = {
        "team_debt": 650000,
        "team_cash": 2000,
        "annual_revenue": 180000,
        "annual_expenses": 320000,
        "debt_service": 52000,
    }
    assert compute_debt_risk(broke) == "critical"


def test_acquire_writes_financial_events():
    w = force_pre_acquisition(empty_world_state())
    w["life"]["personal_cash"] = 18400
    after = apply_ops(w, [{"op": "acquire_team", "your_cash": 12000, "investor_cash": 85000, "debt_assumed": 640000}])
    types = {e["type"] for e in after["financial_events"]}
    assert "acquisition" in types
    assert after["finance"]["team_cash"] > 0
    assert after["finance"]["team_cash"] < 200000


def test_negative_cash_without_financing_is_hard_fail():
    initial = force_pre_acquisition(empty_world_state())
    beats = reconstruct_beats(
        initial,
        empty_story_state(),
        empty_progression_state(),
        [
            {"event": "firmás", "ops": [{"op": "acquire_team", "your_cash": 12000}]},
            {"event": "caja roja sin crédito", "world_delta": {"finance": {"team_cash": {"set": -5000}}}},
        ],
    )
    report = validate_hard_gates(
        beats,
        initial_world=initial,
        final_world=beats[-1]["world_state_after"],
        blueprint={},
    )
    assert any(f["code"] == "negative_cash" for f in report["fails"])
