"""Fase 1.7 — Story Discovery: validation, scoring, ranking, schemas."""
from __future__ import annotations

from src.documentary.formats.check_als.aspirational import (
    normalize_life_progression,
    normalize_rewards,
)
from src.documentary.formats.check_als.concepts import (
    _finalize_story_batch,
    _fixture_package,
    normalize_concept_package,
)
from src.documentary.formats.check_als.quality import is_same_movie
from src.documentary.formats.check_als.story_discovery import (
    is_same_story,
    mechanic_story_fixture,
    packaging_score,
    score_story,
    synthesize_hook_from_core,
    validate_story,
    vague_success_story,
    word_count,
)
from src.documentary.formats.check_als.validators import validate_hook


def test_mechanic_story_passes_validation_and_scores_high():
    fx = mechanic_story_fixture()
    gate = validate_story(fx["story_core"], fx["story_spine"])
    assert gate["pass"] is True, gate["reasons"]
    assert 150 <= word_count(fx["story_spine"]) <= 250
    assert fx["story_score"] >= 7.5
    assert fx["story_scores"]["would_watch"] >= 7
    assert fx["story_scores"]["causal_strength"] >= 7


def test_vague_teleport_story_is_rejected():
    raw = vague_success_story()
    gate = validate_story(raw["story_core"], raw["story_spine"])
    assert gate["pass"] is False
    assert any("teleport" in r or "vago" in r or "causal" in r for r in gate["reasons"])


def test_abstract_millions_does_not_beat_mechanic_story():
    gold = mechanic_story_fixture()
    hollow = score_story(vague_success_story()["story_core"], vague_success_story()["story_spine"])
    assert gold["story_score"] > hollow["story_score"]


def test_restaurant_franchise_skins_are_same_movie():
    a = {
        "id": "rest-1",
        "story_core": {
            "starting_situation": "Trabajas en un restaurante familiar en crisis",
            "core_mechanism": "Compras el local y lo conviertes en franquicia",
            "causal_growth_path": "Primer restaurante → manual → franquicias nacionales",
            "major_reversal": "Una cadena nacional te copia el formato",
            "ending_direction": "Vender la marca o pelear",
        },
        "story_spine": "Compras un restaurante quebrado y lo escalas a una franquicia nacional.",
        "premise": "Restaurante en quiebra que se vuelve franquicia.",
    }
    b = {
        "id": "rest-2",
        "story_core": {
            "starting_situation": "Heredas un restaurante gourmet casi vacío",
            "core_mechanism": "Estandarizas recetas y vendes franquicias gourmet",
            "causal_growth_path": "Local gourmet → segunda sucursal → franquicias",
            "major_reversal": "Un grupo hotelero lanza un formato parecido",
            "ending_direction": "Vender o pelear por la marca",
        },
        "story_spine": "Conviertes un restaurante gourmet en una franquicia.",
        "premise": "Restaurante gourmet que se vuelve franquicia.",
    }
    assert is_same_story(a, b) is True


def test_two_software_stories_are_not_automatically_clones():
    a = mechanic_story_fixture()
    b = {
        "id": "media-rights",
        "story_core": {
            "starting_situation": "Trabajas en una radio local catalogando canciones sin dueño claro",
            "specific_opportunity": "Nadie cobra licencias de fondos musicales para podcasts locales",
            "why_you_notice_it": "Un locutor usa un tema y recibe una amenaza legal",
            "first_action": "Armas un catálogo con derechos claros y un precio mensual",
            "first_proof": "Tres emisoras pagan $79 al mes el primer trimestre",
            "core_mechanism": "Licencias prepago de música para radio y podcasts",
            "causal_growth_path": (
                "Las tres emisoras te recomiendan a una red regional. Estandarizas contratos. "
                "Un grupo con 12 radios firma. Eso te permite negociar con sellos. "
                "Llegas a operación nacional."
            ),
            "first_meaningful_reward": "Dejas la radio y alquilas un cuarto propio",
            "life_transformation": "Pasas de archivista a dueño de un catálogo que las radios necesitan",
            "major_reversal": "Un sello grande ofrece las mismas pistas gratis con publicidad",
            "big_decision": "Vender el catálogo o especializarte en emisoras independientes",
            "stakes": "Puedes perder el catálogo y a las radios chicas",
            "ending_direction": "Capa especializada o venta",
        },
        "story_spine": (
            "Tienes 23 años y archivas discos en una radio de pueblo. Un locutor usa un tema "
            "sin papeles y llega una carta de un abogado. Armas un catálogo con derechos claros "
            "y cobras $79 al mes. Tres emisoras pagan. Te recomiendan a una red regional. "
            "Estandarizas contratos. Un grupo de 12 radios firma y eso te abre la puerta a sellos. "
            "Dejas el archivo, alquilas un cuarto y empiezas a controlar tu tiempo. Entonces un "
            "sello grande suelta las mismas pistas gratis con publicidad. Tienes que vender el "
            "catálogo o convertirte en la capa de las emisoras que no pueden depender de un sello."
        ),
    }
    assert is_same_story(a, b) is False


def test_story_score_outranks_bad_packaging():
    gold = mechanic_story_fixture()
    great = normalize_concept_package(
        {
            **_fixture_package(0, ["entrepreneurship"]),
            "id": "great-story-bad-hook",
            "story_core": gold["story_core"],
            "story_spine": gold["story_spine"],
            "story_score": gold["story_score"],
            "story_scores": gold["story_scores"],
            "story_eligible": True,
            "hook": "¿Te imaginas construir un imperio desde cero?",
            "title": "Descubre el futuro de los talleres",
        }
    )
    weak = normalize_concept_package(
        {
            **_fixture_package(1, ["acquisition"]),
            "id": "weak-story-pretty-pack",
            "story_core": vague_success_story()["story_core"],
            "story_spine": vague_success_story()["story_spine"],
            "story_score": 4.2,
            "story_scores": {"would_watch": 3},
            "story_eligible": True,
            "hook": "Tienes 22 años. Cierras la persiana de un motel vacío. El libro de reservas tiene tres nombres.",
            "title": "POV: Compras un motel y construyes una cadena",
        }
    )
    great["story_eligible"] = True
    weak["story_eligible"] = True
    great["story_score"] = gold["story_score"]
    weak["story_score"] = 4.2
    out = _finalize_story_batch([weak, great], 2)
    assert out["eligible_ranked"][0]["id"] == "great-story-bad-hook"
    pack = packaging_score(great)
    assert pack["packaging_score"] < 8
    assert float(out["eligible_ranked"][0]["rank_score"]) > float(out["eligible_ranked"][1]["rank_score"])


def test_bad_hook_is_regenerated_from_core_not_used_to_downrank():
    fx = mechanic_story_fixture()
    hook = synthesize_hook_from_core(fx["story_core"], {"starting_age": 20, "starting_location": "taller"})
    assert validate_hook(hook)["pass"] is True
    assert not hook.lower().startswith("¿te imaginas")
    assert "tienes 20" in hook.lower() or "taller" in hook.lower() or "teléfono" in hook.lower() or "telefono" in hook.lower()


def test_canonical_rewards_and_life_progression():
    rewards = normalize_rewards(
        {
            "financial": {"description": "Patrimonio de $5 millones", "moment": "late_state"},
            "family": "Pagas la casa de tus padres",
            "freedom": {"text": "Controlas tu horario"},
        }
    )
    assert len(rewards) >= 3
    for row in rewards:
        assert set(row) >= {"type", "moment", "description", "story_significance"}
        assert isinstance(row["description"], str)

    life = normalize_life_progression(
        {
            "stages": [
                {
                    "stage": "start",
                    "age_or_time": "20 años",
                    "living_situation": "habitación de tus padres",
                    "financial_state": "$180",
                    "freedom": "turnos ajenos",
                    "status": "recepcionista",
                    "family_effect": "dependes de ellos",
                    "environment": "taller de barrio",
                }
            ],
            "mid_reward": [{"description": "alquilar departamento"}],
        }
    )
    assert isinstance(life.get("stages"), list)
    assert life["stages"][0]["living_situation"] == "habitación de tus padres"
    assert life["start"]
    assert all(isinstance(x, str) for x in life["start"])


def test_imagina_hook_fails_validation():
    bad = validate_hook("¿Te imaginas dejar tu trabajo y volverte millonario en tres años?")
    assert bad["pass"] is False


def test_lodging_still_collapses_in_package_fingerprint():
    base = _fixture_package(0, ["entrepreneurship"])
    cabins = normalize_concept_package(
        {
            **base,
            "id": "eco-cabins",
            "title": "POV: Construyes cabañas ecológicas",
            "premise": "Compras un terreno baldío y construyes cabañas ecológicas de ecoturismo.",
            "one_line_fantasy": "De un terreno baldío a un imperio de cabañas ecológicas",
        }
    )
    resort = normalize_concept_package(
        {
            **base,
            "id": "eco-resort",
            "title": "POV: Transformas un terreno baldío en un eco-resort",
            "premise": "Transformas un terreno baldío en un eco-resort de turismo sostenible.",
            "one_line_fantasy": "De un lote vacío a una cadena de eco-resorts",
        }
    )
    assert is_same_movie(cabins, resort) is True


def test_taller_renovado_is_generic_structure_negative():
    from src.documentary.formats.check_als.story_discovery import (
        structural_template,
        taller_renovado_negative_fixture,
    )

    fx = taller_renovado_negative_fixture()
    gate = validate_story(fx["story_core"], fx["story_spine"])
    tmpl = structural_template(fx["story_core"], fx["story_spine"])
    assert gate["pass"] is False, gate["reasons"]
    assert tmpl["template"] == "generic_success_arc"
    assert tmpl["interchangeable_conflict"] is True
    assert any("plantilla" in r or "intercambiable" in r or "genéric" in r for r in gate["reasons"])


def test_generic_opportunity_and_invention_fail():
    from src.documentary.formats.check_als.story_discovery import is_generic_invention, is_generic_opportunity

    assert is_generic_opportunity("Hay una creciente demanda de mejores experiencias") is True
    gold = mechanic_story_fixture()
    assert is_generic_opportunity(gold["story_core"]["specific_opportunity"]) is False
    fake = {
        "starting_situation": "Eres ingeniero en una oficina.",
        "specific_opportunity": "Existe una necesidad insatisfecha en educación digital",
        "core_mechanism": "Una plataforma educativa personalizada con inteligencia artificial",
        "first_action": "Lanzas la plataforma",
        "first_proof": "Unos estudiantes se registran",
        "causal_growth_path": "Crece por boca a boca",
        "major_reversal": "Un competidor grande entra",
        "ending_direction": "Te vuelves referente",
    }
    assert is_generic_invention(fake, "Construyes una plataforma educativa personalizada") is True
    assert is_generic_invention(gold["story_core"], gold["story_spine"]) is False


def test_mechanic_still_beats_taller_renovado():
    from src.documentary.formats.check_als.story_discovery import taller_renovado_negative_fixture

    gold = mechanic_story_fixture()
    bad = taller_renovado_negative_fixture()
    hollow = score_story(bad["story_core"], bad["story_spine"])
    assert gold["story_score"] > hollow["story_score"]
    assert validate_story(gold["story_core"], gold["story_spine"])["pass"] is True
