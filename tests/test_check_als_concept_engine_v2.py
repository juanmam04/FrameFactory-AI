"""Editorial regression tests for Check Concept Engine V2 (Spanish-first)."""
from __future__ import annotations

from src.documentary.formats.check_als.concepts import (
    _fixture_package,
    normalize_concept_package,
)
from src.documentary.formats.check_als.editorial import CONTENT_LANGUAGE
from src.documentary.formats.check_als.scoring import apply_scoring, evaluate_eligibility
from src.documentary.formats.check_als.validators import ConcreteMechanismValidator


def _generic_ai() -> dict:
    return normalize_concept_package(
        {
            "id": "generic-ai",
            "title": "POV: Revolucionas la tecnología de IA",
            "premise": (
                "Creas una empresa revolucionaria de IA, enfrentas dilemas éticos "
                "y eventualmente cambias el mundo."
            ),
            "one_line_fantasy": "Revolucionas la IA y cambias el mundo",
            "core_transformation": "Desarrollador → visionario tech",
            "story_category": "technology",
            "central_story_question": "¿Puedes cambiar el mundo?",
            "open_loops": ["¿Funcionará?", "¿Y la ética?"],
            "hook": "Sueñas con construir algo grande.",
            "story_engine": {
                "specific_opportunity": "oportunidad",
                "why_protagonist_notices_it": "notas una oportunidad",
                "initial_action": "empiezas una startup",
                "first_customer_or_break": "aparecen los primeros clientes",
                "business_or_progress_mechanism": "app revolucionaria",
                "why_it_works": "cambia el mundo",
                "growth_mechanism": "escala globalmente",
                "first_proof": "tracción",
                "first_major_reward": "éxito",
                "primary_opposition": "competidores poderosos",
                "mid_story_complication": "contratiempos inesperados",
                "major_threat": "desafíos inesperados",
                "big_decision": "decisiones difíciles",
                "stakes": "todo",
                "possible_cost": "sacrificios personales",
                "escalation_path": "startup a imperio tecnológico",
                "endgame": "marca global",
            },
            "world_seeds": {
                "starting_age": 30,
                "starting_cash": "$10,000",
                "starting_location": "Silicon Valley",
                "starting_status": "desarrollador",
                "target_outcome": "cambiar el mundo",
                "business_or_career_type": "IA",
                "timeline_scale": "5 años",
            },
            "thumbnail_concept": {
                "main_visual": "tú joven, a mitad de la transformación",
                "protagonist_state": "tú joven, a mitad de la transformación",
                "environment": "ubicación clave de la historia",
                "central_contrast": "antes vs después",
                "emotion": "tensión",
                "key_object": "un objeto simbólico",
                "composition": "contraste simple de dos zonas",
                "camera": "plano medio",
                "lighting": "contraste cinematográfico",
                "background": "simplificado",
                "thumbnail_prompt": "a visionary changes the world",
            },
        }
    )


def _generic_startup() -> dict:
    return normalize_concept_package(
        {
            "id": "generic-startup",
            "title": "POV: Conviertes $100 en $10 millones",
            "premise": "Empiezas una empresa con $100, trabajas duro y eventualmente haces $10 millones.",
            "one_line_fantasy": "De $100 a $10 millones",
            "core_transformation": "Sin plata → rico",
            "story_category": "wealth",
            "central_story_question": "¿Puedes hacer millones?",
            "open_loops": ["¿Harás dinero?", "¿Qué sigue?"],
            "hook": "Tienes $100 y sueños grandes.",
            "story_engine": {
                "specific_opportunity": "hacer dinero con una startup",
                "why_protagonist_notices_it": "quieres riqueza",
                "initial_action": "empiezas una empresa",
                "first_customer_or_break": "los clientes compran",
                "business_or_progress_mechanism": "crecimiento del negocio",
                "why_it_works": "trabajas duro",
                "growth_mechanism": "crece",
                "first_proof": "ventas",
                "first_major_reward": "ganancia",
                "primary_opposition": "desafíos",
                "mid_story_complication": "decisiones difíciles",
                "major_threat": "competidores",
                "big_decision": "seguir adelante",
                "stakes": "tu futuro",
                "possible_cost": "tiempo",
                "escalation_path": "de chico a grande",
                "endgame": "diez millones de dólares",
            },
            "world_seeds": {
                "starting_age": 21,
                "starting_cash": "$100",
                "starting_location": "departamento",
                "starting_status": " hustler",
                "target_outcome": "$10M",
                "business_or_career_type": "startup",
                "timeline_scale": "8 años",
            },
            "thumbnail_concept": {
                "main_visual": "persona con dinero",
                "protagonist_state": "ambicioso",
                "environment": "departamento",
                "central_contrast": "pobre vs rico",
                "emotion": "esperanza",
                "key_object": "billete de 100",
                "composition": "centro",
                "camera": "medio",
                "lighting": "brillante",
                "background": "ciudad",
                "thumbnail_prompt": "young founder with cash becoming rich",
            },
        }
    )


def _generic_comeback() -> dict:
    return normalize_concept_package(
        {
            "id": "generic-comeback",
            "title": "POV: Reconstruyes tu imperio",
            "premise": "Después de perderlo todo, trabajas duro y reconstruyes tu imperio.",
            "one_line_fantasy": "Lo pierdes todo, lo reconstruyes todo",
            "core_transformation": "Caído → restaurado",
            "story_category": "comeback",
            "central_story_question": "¿Puedes volver?",
            "open_loops": ["¿Reconstruirás?", "¿A qué costo?"],
            "hook": "Lo perdiste todo. Ahora lo quieres de vuelta.",
            "story_engine": {
                "specific_opportunity": "reconstruir después del fracaso",
                "why_protagonist_notices_it": "lo perdiste todo",
                "initial_action": "empiezas de nuevo",
                "first_customer_or_break": "una segunda oportunidad",
                "business_or_progress_mechanism": "trabajo duro",
                "why_it_works": "determinación",
                "growth_mechanism": "progreso constante",
                "first_proof": "pequeñas victorias",
                "first_major_reward": "momentum",
                "primary_opposition": "duda",
                "mid_story_complication": "contratiempos inesperados",
                "major_threat": "fallar otra vez",
                "big_decision": "seguir peleando",
                "stakes": "tu orgullo",
                "possible_cost": "sacrificios personales",
                "escalation_path": "de abajo hacia arriba",
                "endgame": "imperio restaurado",
            },
            "world_seeds": {
                "starting_age": 40,
                "starting_cash": "$500",
                "starting_location": "casa",
                "starting_status": "fundador fallido",
                "target_outcome": "imperio reconstruido",
                "business_or_career_type": "negocios",
                "timeline_scale": "5 años",
            },
            "thumbnail_concept": {
                "main_visual": "persona levantándose de las cenizas",
                "protagonist_state": "determinado",
                "environment": "ruinas",
                "central_contrast": "caída vs ascenso",
                "emotion": "garra",
                "key_object": "metáfora de fénix",
                "composition": "centro",
                "camera": "amplio",
                "lighting": "dramática",
                "background": "humo",
                "thumbnail_prompt": "founder rebuilding empire after collapse",
            },
        }
    )


def test_generic_ai_fails_eligibility():
    pkg = _generic_ai()
    assert pkg["eligible"] is False
    mech = ConcreteMechanismValidator.evaluate(pkg)
    assert mech["pass"] is False


def test_generic_startup_fails_eligibility():
    pkg = _generic_startup()
    assert pkg["eligible"] is False


def test_generic_comeback_fails_eligibility():
    pkg = _generic_comeback()
    assert pkg["eligible"] is False


def test_concrete_mechanic_fixture_passes():
    pkg = _fixture_package(0, ["entrepreneurship"])
    assert pkg["eligible"] is True
    assert pkg.get("language") == CONTENT_LANGUAGE or pkg.get("content_language") == CONTENT_LANGUAGE
    assert pkg["overall_score"] >= 6.0
    assert pkg["specificity_score"] >= 6
    assert "gratis" in pkg["story_engine"]["major_threat"].lower() or "free" in pkg["story_engine"]["major_threat"].lower()
    assert pkg["hook"]
    assert "tienes" in pkg["hook"].lower() or "tú" in pkg["hook"].lower() or "eres" in pkg["hook"].lower()
    assert "?" in pkg["central_story_question"]
    assert 2 <= len(pkg["open_loops"]) <= 5


def test_overall_score_not_overridden_by_llm():
    raw = _fixture_package(0, ["entrepreneurship"])
    raw["overall_score"] = 99.0
    pkg = apply_scoring(normalize_concept_package({**raw, "overall_score": 99.0}))
    assert pkg["overall_score"] <= 10.0
    assert pkg["overall_score"] != 99.0


def test_category_mismatch_hotel_as_technology_fails_or_repairs():
    base = _fixture_package(1, ["acquisition"])
    pkg = normalize_concept_package(
        {
            **base,
            "story_category": "technology",
            "premise": (
                "Compras un motel de carretera barato, renovas habitaciones y construyes una cadena "
                "de hospitalidad hasta que la deuda colapsa el imperio."
            ),
            "world_seeds": {
                "starting_age": 22,
                "starting_cash": "$2100",
                "starting_location": "pueblo de motel de carretera",
                "starting_status": "comprador primerizo",
                "target_outcome": "imperio hotelero y luego colapso",
                "business_or_career_type": "hospitalidad / real estate",
                "timeline_scale": "9 años",
            },
            "story_engine": {
                **base["story_engine"],
                "specific_opportunity": "Comprar un motel de carretera descuidado y renovar habitaciones para viajeros",
                "business_or_progress_mechanism": "Turnaround de hospitalidad vía renovación y ocupación",
                "major_threat": "Deuda a tasa variable y un bypass que mata el tráfico",
            },
        }
    )
    assert pkg["story_category"] != "technology"


def test_bad_titles_stripped():
    pkg = normalize_concept_package(
        {
            **_fixture_package(0, ["entrepreneurship"]),
            "title_options": [
                {"text": "POV: Tú de alguna manera construyes un imperio"},
                {"text": "POV: Persigues millones"},
                {"text": "POV: Conviertes llamadas perdidas en una empresa"},
            ],
        }
    )
    texts = " ".join(t["text"] for t in pkg["title_options"]).lower()
    assert "de alguna manera" not in texts
    assert "persigues" not in texts


def test_world_seeds_recover_from_stringified_dict():
    pkg = normalize_concept_package(
        {
            **_fixture_package(0, ["entrepreneurship"]),
            "world_seeds": {},
            "starting_state": str(
                {
                    "starting_age": 20,
                    "starting_cash": "$180",
                    "starting_location": "taller mecánico",
                    "starting_status": "recepcionista",
                    "target_outcome": "empresa de software",
                    "business_or_career_type": "SaaS",
                    "timeline_scale": "4 años",
                }
            ),
        }
    )
    elig = evaluate_eligibility(pkg)
    assert pkg["world_seeds"]["starting_age"] == 20
    assert pkg["world_seeds"]["starting_location"]
    assert elig["gates_extra"]["has_valid_world_seeds"] or pkg["world_seeds"]["starting_cash"]


def test_profile_defaults_spanish():
    from src.documentary.formats.check_als.profile import check_als_profile

    p = check_als_profile()
    assert p.get("language") == "es"
    assert (p.get("channel") or {}).get("language") == "es"
    assert (p.get("channel") or {}).get("image_prompt_language") == "en"


def test_aspirational_fields_present_on_fixture():
    pkg = _fixture_package(0, ["entrepreneurship"])
    assert pkg["eligible"] is True
    assert len(pkg.get("escalation_ladder") or []) >= 5
    assert len(pkg.get("rewards") or []) >= 3
    assert pkg.get("scale_ceiling") in {
        "national",
        "international",
        "category_leader",
        "major_exit",
        "empire",
    }
    assert (pkg.get("life_progression") or {}).get("start")
    assert (pkg.get("start_end_contrast") or {}).get("start")
    assert (pkg.get("start_end_contrast") or {}).get("end")
    assert float(pkg.get("aspirational_score") or 0) >= 5.0
    scores = pkg.get("scores") or {}
    assert "aspirational_strength" in scores
    assert "life_transformation" in scores
    assert "scale_potential" in scores
    assert "reward_density" in scores


def test_local_only_rescue_fails_aspirational_gate():
    """Small-business rescue that stays local must not pass Check aspirational gates."""
    pkg = normalize_concept_package(
        {
            **_fixture_package(1, ["acquisition"]),
            "id": "local-laundromat-only",
            "scale_ceiling": "local",
            "end_state": "dueño exitoso de la lavandería del barrio",
            "escalation_ladder": [
                "Compras lavandería quebrada",
                "Reparás máquinas",
                "Negocio rentable del barrio",
                "Competidor local aparece",
                "Sobrevives",
            ],
            "life_progression": {
                "start": ["sin plata"],
                "early_reward": ["primer mes en positivo"],
                "mid_reward": [],
                "major_reward": [],
                "late_state": ["lavandería rentable"],
            },
            "rewards": [
                {"type": "financial", "description": "más dinero del local"},
                {"type": "financial", "description": "más caja"},
                {"type": "financial", "description": "más ingresos"},
            ],
            "start_end_contrast": {
                "start": "lavandería quebrada",
                "end": "lavandería rentable del barrio",
            },
            "story_engine": {
                **(_fixture_package(1, ["acquisition"])["story_engine"]),
                "growth_mechanism": "conseguir más clientes del barrio",
                "escalation_path": "local roto → local rentable",
                "endgame": "negocio local sobrevive",
                "major_threat": "competidor local abre al lado",
            },
        }
    )
    assert pkg["eligible"] is False
    failed = pkg.get("eligibility", {}).get("failed_gates") or []
    assert any(
        g in failed
        for g in (
            "has_aspirational_transformation",
            "has_life_progression",
            "has_scale_progression",
            "has_visible_rewards",
        )
    )


def test_blog_titles_rejected():
    pkg = normalize_concept_package(
        {
            **_fixture_package(0, ["entrepreneurship"]),
            "title": "Desafiando a los gigantes del software",
            "title_options": [
                {"text": "Transformando Palcos Vacíos en Fortunas"},
                {"text": "Conviértete en el dueño del club"},
                {"text": "POV: Construyes software de talleres desde un mostrador"},
            ],
        }
    )
    texts = " ".join([pkg.get("title") or ""] + [t["text"] for t in pkg.get("title_options") or []]).lower()
    assert "desafiando" not in texts
    assert "transformando" not in texts
    assert "conviértete" not in texts and "conviertete" not in texts


def test_score_separation_possible():
    """Overall should not collapse all eligibles to the same 8.0 bucket."""
    a = _fixture_package(0, ["entrepreneurship"])
    b = _fixture_package(1, ["acquisition"])
    c = _fixture_package(2, ["sports_business"])
    scores = sorted({round(float(x["overall_score"]), 2) for x in (a, b, c)})
    # At least some spread OR distinct rank_scores
    ranks = sorted({round(float(x.get("rank_score") or 0), 3) for x in (a, b, c)})
    assert len(scores) >= 2 or len(ranks) >= 2
    assert all(isinstance(x["overall_score"], float) for x in (a, b, c))
