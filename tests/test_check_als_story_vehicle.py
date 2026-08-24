"""Vehicle mode: business vs sports team story routing."""
from __future__ import annotations

from src.documentary.formats.check_als.story_vehicle import vehicle_mode


def test_content_creator_is_business_not_basketball():
    p = {
        "title": "POV: Construyes tu imperio como creador de contenido",
        "topic": "Transformar tu hobby en un negocio próspero",
        "concept": {
            "story_category": "entrepreneurship",
            "premise": "Eres creador independiente. Lanzas Creador Co. y escalas una media company.",
            "one_line_fantasy": "De videos en tu habitación a imperio de contenido",
        },
    }
    assert vehicle_mode(p) == "business"


def test_basketball_pilot_is_sports():
    p = {
        "title": "POV: Compras un equipo de básquet al borde de la quiebra",
        "concept": {"story_category": "sports_business", "premise": "Comprar un equipo de básquet"},
    }
    assert vehicle_mode(p) == "sports_team"
