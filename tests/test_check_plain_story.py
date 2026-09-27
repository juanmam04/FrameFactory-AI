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
    assert 900 <= words <= 1200, words
    report = validate_synopsis(text, bp, initial, final, vehicle_mode="sports_team")
    assert report["ok"], report
