"""La historia que lee la gente es una vida, no una planilla."""
from src.documentary.formats.check_als.plain_language import has_jargon, plain_event, public_life_synopsis
from src.documentary.formats.check_als.story_validate import validate_synopsis


SHOT = (
    "el gimnasio huele a humedad y las gradas no se llenan. $1 de precio + asunción de $650,000 de deuda. "
    "Vos ponés $15,000 y te quedás 51%. Inversores locales ponen $85,000 por 39%. "
    "El vendedor retiene 10% y financia $220,000. Firmás la compra: un peso, la deuda, y el 51%. "
    "Apostás por roster e instalaciones. El mes siguiente el equipo arranca 2-8 y el servicio de la deuda vuelve a mirarte a la cara. "
    "Temporada 1: el pizarrón cierra 2-8. Sin playoffs. Asistencia media 4600. El club factura 700900 y vale 4578000. "
    "La deuda del club queda en 590169, con caja 503341 e ingresos 700900. "
    "Sos millonario en equity y seguís mirando la cuenta antes de una cena. "
    "portfolio es tuyo en un 51.0%."
)


def test_user_idea_stays_the_users_challenge():
    from src.documentary.formats.check_als.concepts import package_to_project_fields
    from src.documentary.formats.check_als.plain_language import public_life_synopsis
    from src.documentary.formats.check_als.story_vehicle import phase_specs, vehicle_mode
    from src.documentary.formats.check_als.user_idea import adapt_user_idea, user_pov_title

    raw = "POV: Tenes 7 dias para gastar 1.000.000.000.000 de dolares"
    title = user_pov_title(raw)
    assert title.lower().startswith("pov:")
    assert "tienes" in title.lower()
    assert "1.000.000.000.000" in title
    assert "equipo" not in title.lower()

    pkg = adapt_user_idea(raw, use_llm=False)
    fields = package_to_project_fields(pkg)
    project = {
        "title": fields["title"],
        "topic": fields["topic"],
        "vehicle_type": fields["vehicle_type"],
        "user_proposed": True,
        "concept": fields["concept"],
    }
    assert vehicle_mode(project) == "freeform"
    assert len(phase_specs("freeform", "open")) == 2
    synopsis = public_life_synopsis(
        {"user_premise": fields["concept"]["premise"], "freeform": True},
        [{"event": "El segundo día compras una isla y la dejas vacía."}],
        {},
        {},
        vehicle_mode="freeform",
    )
    low = synopsis.lower()
    assert "tienes" in low or "gast" in low
    assert "básquet" not in low
    assert "equity" not in low
    assert "51" not in low


def test_generator_plans_a_short_life():
    from src.documentary.formats.check_als.plain_language import SIMPLE_STORY_BRIEF
    from src.documentary.formats.check_als.story_vehicle import phase_specs

    phases = phase_specs("sports_team", "open")
    assert len(phases) == 2
    brief = " ".join(text for _, text in phases).lower()
    assert "ritmo" in brief or "fluya" in brief or "curva" in brief
    assert "planilla" in SIMPLE_STORY_BRIEF.lower()
    assert "equity_sale" in SIMPLE_STORY_BRIEF


def test_screenshot_is_jargon():
    assert has_jargon(SHOT)


def test_purchase_event_is_a_life():
    line = plain_event("Firmás la compra: un peso, la deuda, y el 51%.")
    low = line.lower()
    assert "firmas" in low
    assert "51" not in low
    assert "deuda" not in low
    assert "equity" not in low
    assert "tenés" not in low
    assert "firmás" not in low


def test_life_synopsis_has_no_ledger():
    bp = {"fiction_world": {"team_name": "Halcones", "city": "Puerto Norte"}}
    initial = {
        "time": {"protagonist_age": 22},
        "life": {"job": "empleado de oficina", "home": "un departamento compartido"},
    }
    final = {
        "time": {"protagonist_age": 26},
        "life": {"job": "dueño del club", "home": "un departamento cerca del estadio"},
        "team": {"name": "Halcones"},
        "finance": {"debt_risk_state": "manageable"},
        "sports": {
            "season_history": [
                {"season": 1, "record": "8-24", "playoff_result": "Sin playoffs", "attendance_avg": 900},
                {"season": 2, "record": "22-10", "playoff_result": "Final de conferencia", "attendance_avg": 6100, "championship": False},
            ]
        },
    }
    beats = [
        {
            "event": "Firmás la compra: un peso, la deuda, y el 51%.",
            "story_purpose": "first_commitment",
            "reward_or_setback": "reward:owns_team",
        }
    ]
    text = public_life_synopsis(bp, beats, initial, final, vehicle_mode="sports_team")
    low = text.lower()
    assert not has_jargon(text), text[:400]
    assert "tienes 22" in low
    assert "tenés" not in low
    assert "firmás" not in low
    assert "padres" in low
    assert "renuncias" in low
    words = len(text.split())
    assert 180 <= words <= 650, words
    report = validate_synopsis(text, bp, initial, final, vehicle_mode="sports_team")
    assert report["ok"], report
