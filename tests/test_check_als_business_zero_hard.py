"""Business-mode story must ship with zero hard fails after polish."""
from __future__ import annotations

import pytest

from src.documentary.formats.check_als.story_architect import finalize_architecture
from src.documentary.formats.check_als.story_sim import (
    expand_synopsis_to_min_words,
    force_pay_important_loops,
    force_pre_acquisition,
    repair_beat_ops,
    scrub_sports_text,
)
from src.documentary.formats.check_als.story_arch import empty_world_state
from src.documentary.formats.check_als.story_vehicle import vehicle_mode


@pytest.fixture
def tmp_projects(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setenv("FRAMEFACTORY_PROJECTS_DIR", str(root))
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    return root


def test_scrub_sports_removes_playoffs():
    text = scrub_sports_text("Ganás el campeonato en el estadio y vas a playoffs de básquet")
    low = text.lower()
    assert "campeonato" not in low
    assert "playoff" not in low
    assert "estadio" not in low
    assert "básquet" not in low and "basquet" not in low


def test_text_only_lanz_gets_launch_op_injected():
    from src.documentary.formats.check_als.story_sim import repair_architecture

    beats = [
        {"beat_id": "b01", "event": "Arrancás el día", "ops": []},
        {"beat_id": "b02", "event": "Ves la oportunidad", "ops": []},
        {"beat_id": "b03", "event": "Hablás con inversores", "ops": []},
        {"beat_id": "b04", "event": "Lanzás la empresa y firmás con socios", "ops": []},  # text only — no op
        {"beat_id": "b05", "event": "Crece", "ops": [{"op": "advance_time", "months": 3}]},
    ]
    fixed = repair_architecture(blueprint={"business_or_vehicle": {"acquisition": {}}}, beats=beats, mode="business")
    ops4 = [str(o.get("op")) for o in (fixed[3].get("ops") or []) if isinstance(o, dict)]
    assert "launch_company" in ops4, ops4
    assert float(fixed[3]["ops"][0].get("your_pct") or 0) >= 40


def test_business_force_pre_wipes_650k_debt():
    w = empty_world_state()
    assert float((w.get("finance") or {}).get("team_debt") or 0) == 650000
    cleaned = force_pre_acquisition(w, mode="business")
    assert float((cleaned.get("finance") or {}).get("team_debt") or 0) == 0


def test_repair_beat_ops_zeros_business_debt():
    beats = [
        {
            "beat_id": "b01",
            "ops": [{"op": "acquire_team", "debt_assumed": 650000, "your_cash": 8000}],
        }
    ]
    fixed = repair_beat_ops(beats, mode="business")
    assert fixed[0]["ops"][0]["debt_assumed"] == 0


def test_expand_synopsis_reaches_900():
    short = "Empezás. Firmás. Crece."
    beats = [{"time": f"DÍA {i}", "event": f"Evento concreto número {i} del negocio"} for i in range(40)]
    out = expand_synopsis_to_min_words(short, beats, min_words=900)
    assert len(out.split()) >= 900


def test_force_pay_closes_important_loops():
    beats = [
        {
            "beat_id": "b01",
            "story_state_after": {
                "open_loops": [
                    {"id": "launch", "question": "¿arranca?", "status": "open", "important": True},
                    {"id": "how_far", "question": "¿hasta dónde?", "status": "open", "important": False, "intentional_unresolved": True},
                ]
            },
        }
    ]
    out = force_pay_important_loops(beats)
    loops = out[-1]["story_state_after"]["open_loops"]
    by_id = {l["id"]: l for l in loops}
    assert by_id["launch"]["status"] == "paid"
    assert by_id["how_far"].get("intentional_unresolved") is True


def test_business_finalize_offline_zero_hard_fails(tmp_projects):
    from src.documentary.project import create_project, load_project
    from src.documentary.formats.check_als.story_arch import load_architecture

    p = create_project(
        "De videos en tu habitación a media company",
        title="POV: Construyes tu imperio como creador de contenido",
        project_id="test-creator-zero-hard",
        language="es",
        content_format="check_als",
        concept={
            "story_category": "entrepreneurship",
            "premise": "Lanzas Creador Co. y construís un imperio de contenido",
            "one_line_fantasy": "De habitación a imperio",
        },
    )
    assert vehicle_mode(p) == "business"

    beats = []
    for i in range(48):
        ops = []
        if i == 3:
            ops = [{"op": "launch_company", "your_cash": 8000, "investor_cash": 40000, "your_pct": 60, "investor_pct": 40, "debt_assumed": 0}]
        elif i == 10:
            ops = [{"op": "quit_job"}]
        elif i == 20:
            ops = [{"op": "move_home"}]
        elif i == 30:
            ops = [{"op": "sponsor_deal", "amount": 48000}]
        elif i % 6 == 0:
            ops = [{"op": "advance_time", "months": 3}]
        beats.append(
            {
                "beat_id": f"b{i+1:02d}",
                "time": f"AGE {22 + i // 12} · DÍA {i*30}",
                "cause": "porque el negocio lo pide",
                "event": f"Paso {i+1}: publicás, cobrás, decidís el siguiente movimiento.",
                "consequence": "la vida se mueve",
                "story_purpose": "escalation" if i % 2 else "first_proof",
                "ops": ops,
                "reward_or_setback": "reward:progress" if i % 3 else "setback:cash",
                "duration_target_s": 16,
                "world_delta": {},
                "story_delta": {},
                "progression_delta": {},
                "metric_reveal": ["CASH"] if ops else [],
                "visual_opportunity": "tu habitación convertida en set",
            }
        )

    arch = {
        "blueprint": {
            "ending_type": "triumphant",
            "ending": "Mirás la oficina. El correo espera.",
            "final_state": "dueño de Creador Co.",
            "fiction_world": {"company_name": "Creador Co.", "industry": "contenido", "city": "Madrid"},
            "business_or_vehicle": {
                "what_is_being_built_or_owned": "media company",
                "acquisition": {
                    "asking_price": 0,
                    "debt_assumed": 0,
                    "your_cash_contribution": 8000,
                    "local_investors_cash": 40000,
                    "your_ownership": 60,
                    "investor_ownership": 40,
                    "seller_retained": 0,
                },
            },
            "intentional_unresolved_loops": ["how_far"],
        },
        "initial_world": {
            "life": {"job": "freelancer", "home": "habitación", "personal_cash": 12000},
            "finance": {"team_debt": 650000},
        },
        "initial_story": {
            "open_loops": [
                {"id": "launch", "question": "¿podrás lanzar?", "status": "open", "important": True},
                {"id": "cash", "question": "¿te alcanza?", "status": "open", "important": True},
                {"id": "how_far", "question": "¿hasta dónde?", "status": "open", "important": False, "intentional_unresolved": True},
            ]
        },
        "initial_progression": {},
        "beats": beats,
        "synopsis": (
            "Empezás en Madrid. Lanzas Creador Co. Firmás con inversores. Crece. "
            "Renunciás. Te mudás. Crisis de cash. Sponsor. Hoy sos dueño. "
            "Ganás el campeonato en el estadio de básquet."  # must be scrubbed
        ),
    }

    out = finalize_architecture(p, arch)
    loaded = load_architecture(out)
    hard = (loaded.get("quality") or {}).get("hard_fails") or []
    assert hard == [], f"expected zero hard fails, got {hard}"
    assert (loaded.get("quality") or {}).get("review_ready") is True
    syn = loaded.get("synopsis") or ""
    assert len(syn.split()) >= 850
    low = syn.lower()
    assert "playoff" not in low
    assert "básquet" not in low and "basquet" not in low
    assert "estadio" not in low
    assert "campeonato" not in low
    debt = float((((loaded.get("final_world") or {}).get("finance") or {}).get("team_debt") or 0))
    assert debt < 1000, f"business final debt should be ~0, got {debt}"
