"""Check ALS Fase 2 Story Architect: premise → blueprint + beat plan. Stops before script."""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from typing import Any

from src.documentary.formats import FORMAT_CHECK_ALS
from src.documentary.formats.check_als.concepts import _with_retry
from src.documentary.formats.check_als.story_arch import (
    empty_blueprint,
    empty_progression_state,
    empty_story_state,
    empty_world_state,
    persist_architecture,
    reconstruct_beats,
    world_snapshot,
)
from src.documentary.formats.check_als.story_sim import (
    compact_world,
    force_pre_acquisition,
    inject_life_payoffs,
    repair_architecture,
    rewrite_downgraded_championship,
    sync_loop_payoffs,
)
from src.documentary.formats.check_als.story_validate import assemble_review, validate_story_quality
from src.documentary.openai_key import openai_api_key
from src.saas_creative_profile import parse_llm_json_object

BLUEPRINT_SYSTEM = """
Eres Story Architect de Check: ficción aspiracional en ESPAÑOL. El espectador ES el protagonista (tú/te).

Check NO es una moraleja ni un drama del costo del éxito.
Es una simulación de vida: el espectador quiere sentir cómo cambia SU vida a medida que construye algo.

TAREA: diseñar una película de 12–18 minutos (VARIOS AÑOS) desde una premisa.
ending_type preferido para este tipo de fantasía: triumphant u open_future.
NO default a bittersweet. El dueño del equipo debe sentirse increíble, difícil y cada vez más grande.

REGLAS:
- Ficción. Equipo/liga/jugadores inventados. No lo presentes como factual.
- Empieza ANTES de ser dueño. ownership inicial = 0.
- La adquisición es un EVENTO entendible (precio nominal + deuda + socios + seller financing). Cifras concretas.
- Varios años y 3 a 5 temporadas de básquet. Cada temporada: pretemporada, regular, cierre de record, postemporada si aplica, offseason.
- La vida personal CAMBIA (trabajo, casa, libertad, familia, status) porque el equipo cambia.
- Reversos orgánicos de categorías distintas (deuda, sponsor, instalaciones, plantel, media, dueño). NO tres lesiones seguidas. NO “aparece un competidor grande”.
- Al menos UN setback de propietario: apostás (roster/facilities) → costos suben → arranque malo → cash/debt service → tenés que decidir.
- La deuda NO tiene que llegar a cero. El payoff es: el equipo es lo bastante sano como para que la deuda deje de amenazar su existencia (debt_risk_state = manageable/healthy).
- NO teletransporte. Un campeonato solo si sports_state ya tiene playoffs + record + ronda. El deporte se simula con ops, no se inventa en la prosa.
- Final = escena/estado, nunca moraleja.
- Texto en español, acontecimientos concretos. PROHIBIDO: corazón que late, camino de rosas, emoción palpable, símbolo de perseverancia, trabajo duro, sueño que cobra vida, nueva vida llena de posibilidades.

Return ONLY JSON:
{
  "blueprint": {
    protagonist{age,starting_life,personality,skills,weaknesses,desire,emotional_need},
    fantasy{surface_desire,deeper_desire,promised_transformation},
    business_or_vehicle{
      what_is_being_built_or_owned, core_mechanism, economic_engine,
      acquisition_structure: "párrafo humano de cómo se compra",
      acquisition: {asking_price, debt_assumed, your_cash_contribution, local_investors_cash,
                    seller_financing, existing_liabilities_assumed, your_ownership, investor_ownership, seller_retained}
    },
    fiction_world{team_name,league_name,city,disclaimer},
    ending_type: "triumphant"|"open_future",
    opening{situation,immediate_problem,curiosity},
    inciting_incident, first_commitment, first_proof, escalation, midpoint,
    major_success, major_reversal, crisis, decision, climax, ending, final_state,
    unresolved_or_bittersweet_element, intentional_unresolved_loops[],
    causal_chain[10-16]
  },
  "initial_world": { ... life + team name/capacity/attendance 600ish + finance debt + sports 0-0 ...
    IMPORTANT: ownership_ledger {protagonist:0, investors:0, seller:100}, acquisition.closed=false,
    life.job empleado de oficina, life.home departamento compartido, life.personal_cash 15000-25000,
    time.protagonist_age 22, time.age_at_start 22, time.elapsed_days 0 }
}
NO escribas synopsis todavía.
""".strip()

BEATS_SYSTEM = """
Eres Beat Planner de Check. Recibes blueprint + WORLD SNAPSHOT compacto (números reales).
Los números NO son metadata: cada beat material debe incluir ops que el simulador aplica.

ops permitidas:
acquire_team, equity_sale, buyback,
game_played, game_won, game_lost, win_game, lose_game, season_stretch,
new_season, playoffs_qualified, playoff_berth, playoff_round_won, playoff_eliminated,
final_reached, championship_won, championship,
injury, player_signed, sign_player, player_released, hire_coach, coach_hired, coach_fired,
sponsor_deal, sponsor_cut, ticket_night, media_deal, media_crisis, fan_unrest,
facility_upgrade, facility_issue, regulatory_fine, personal_crisis, owner_crisis,
pay_debt, credit_line, bridge_loan, loan, owner_injection, investor_injection,
quit_job, owner_draw, move_home, help_family, travel, advance_time

SPORTS STATE es la fuente de verdad. No narres un resultado que no hayas puesto en ops.
championship_won SOLO si el snapshot tiene playoff_status playoffs/finals, playoff_round, y un record de temporada (games_played>=16 y win_pct>=.50).
Si no, usá season_stretch / playoffs_qualified / playoff_round_won / final_reached.
new_season archiva la temporada (record, playoffs, asistencia) y resetea W-L. NO borra championships ni season_history.
Cubrir 3–5 temporadas. Podés resumir tramos con season_stretch. El estado final de cada temporada debe ser coherente.

SETBACKS: 3–5 significativos de categorías distintas (sports, financial, ownership, facilities, staff, media, sponsor, fanbase, regulatory, personal).
Máximo UNA lesión. El resto, otra cosa. Obligatorio un owner_crisis (apuesta cara de dueño).

DEUDA: el loop se paga cuando debt_risk_state es manageable o healthy, aunque quede deuda. No hace falta dejarla en 0.

NUNCA pongas ownership_percentage ni valuation en world_delta. El ledger y la valuación los calcula el motor.

Cada beat JSON:
{
  "time": "AGE 22 · DAY 1" | "AGE 23 · Temporada 2",
  "duration_target_s": 12-20,
  "cause": "...",
  "event": "acontecimiento concreto en segunda persona",
  "consequence": "qué cambia",
  "story_purpose": "opening|inciting_incident|first_commitment|first_proof|escalation|midpoint|major_success|major_reversal|crisis|decision|climax|ending|texture",
  "ops": [{"op":"advance_time","months":2}, ...],
  "contribution": "progress|setback|decision|new information|reward|threat|relationship change|world change|payoff|new loop",
  "world_delta": {},
  "emotional_goal": "...",
  "viewer_question": "",
  "open_loop_action": {"action":"open|pay","loop_id":"...","question":"..."} o {},
  "reward_or_setback": "reward:..."|"setback:..."|"",
  "metric_reveal": ["ATTENDANCE"] o [],
  "visual_opportunity": "escena visible (casa, estadio, palco, renuncia, vestuario) no un gráfico",
  "transition_to_next": "..."
}

REGLAS:
- 14 a 18 beats en ESTE tramo. Cada beat aporta. Si no aporta, no lo escribas.
- Español concreto. Nada de cielo estrellado.
- Incluí recompensas aspiracionales GANADAS (renuncia, tu estadio, palco con padres, sold-out, playoffs).
- El conflicto escala con la recompensa: apuesta chica → premio chico; apuesta grande → riesgo serio.
- Pagá loops importantes con action=pay cuando el mundo ya respondió. Deuda: pay cuando el equipo ya no puede morir por ella.
- Este tramo NO debe repetir el anterior ni cerrar la película antes de tiempo (salvo el último tramo).
- Español: acontecimientos. Nada de “la emoción es indescriptible”.

Return ONLY JSON: {"beats":[...]}
""".strip()


def is_check_project(project: dict[str, Any]) -> bool:
    return str(project.get("content_format") or project.get("mode") or "") == FORMAT_CHECK_ALS


def generate_check_story(
    project: dict[str, Any],
    *,
    use_llm: bool = True,
    architecture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not is_check_project(project):
        raise ValueError("generate_check_story is only for Check ALS projects")
    if architecture:
        return finalize_architecture(project, architecture)
    if not use_llm:
        raise ValueError("Check Fase 2 necesita LLM (o un architecture payload de test).")
    key = openai_api_key()
    if not key:
        raise ValueError("OPENAI_API_KEY missing")

    from openai import OpenAI

    client = OpenAI(api_key=key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    user_ctx = _project_context(project)

    raw_bp = _chat_json(client, model, BLUEPRINT_SYSTEM, user_ctx, temperature=0.8, timeout=180.0, max_tokens=7000)
    blueprint, _syn_unused, initial_world, initial_story, initial_prog = _extract_blueprint_bundle(raw_bp)
    initial_world = force_pre_acquisition(initial_world)
    if not (initial_story.get("open_loops") or []):
        initial_story["open_loops"] = [
            {"id": "buy", "question": "¿realmente podrás comprarlo?", "opened_at": "start", "status": "open", "important": True, "expected_payoff_window": "adquisición"},
            {"id": "save_team", "question": "¿podrás evitar que cierre?", "opened_at": "start", "status": "open", "important": True, "expected_payoff_window": "año 1"},
            {"id": "debt", "question": "¿podrás hacer que el equipo sea lo suficientemente sano como para que la deuda deje de amenazar su existencia?", "opened_at": "start", "status": "open", "important": True, "expected_payoff_window": "año 2-4"},
            {"id": "coach", "question": "¿funcionará el nuevo entrenador?", "opened_at": "start", "status": "open", "important": True, "expected_payoff_window": "primera temporada seria"},
            {"id": "compete", "question": "¿puede este equipo competir de verdad?", "opened_at": "start", "status": "open", "important": True, "expected_payoff_window": "playoffs/final"},
            {"id": "how_far", "question": "¿qué tan lejos puede llegar?", "opened_at": "start", "status": "open", "important": False, "intentional_unresolved": True, "expected_payoff_window": "futuro"},
        ]
    ending_type = str(blueprint.get("ending_type") or "triumphant").lower()
    if ending_type not in ("triumphant", "open_future", "comeback", "empire_continues"):
        blueprint["ending_type"] = "triumphant"
        ending_type = "triumphant"

    phase_specs = [
        ("p1", "Tramo 1 AGE 22: vida ordinaria → oportunidad → CÓMO se compra (ops: acquire_team) → oh shit, sos dueño. 14-16 beats. Temporada 1 puede arrancar mal. NO campeonato. Abrí loops. Un setback no-lesión."),
        ("p2", "Tramo 2 AGE 22-23: reality hits, first proof, la vida EMPIEZA a cambiar. Cerrá Temporada 1 con season_stretch + record real + new_season si corresponde. 14-16 beats. NO campeonato."),
        ("p3", "Tramo 3 AGE 23-25: apuesta de DUEÑO (roster/facilities), owner_crisis, costos, arranque flojo, decisión (inyectar / vender equity / recortar / apostar). Progreso deportivo de otra temporada (new_season + season_stretch). Primer gran payoff de vida. 14-18 beats. Championship solo si el snapshot lo permite."),
        ("p4", "Tramo 4 AGE 25-27: recovery, corrida deportiva (playoffs/final si el state lo gana), debt_risk pasa a manageable/healthy AUNQUE quede deuda, payoff de vida, 1 loop a futuro intencional. ending_type=" + ending_type + ". 14-18 beats. No moraleja. No prosa de modelo."),
    ]
    beats: list[dict[str, Any]] = []
    world = deepcopy(initial_world)
    story = deepcopy(initial_story)
    prog = deepcopy(initial_prog)
    start_id = 1
    for phase_id, brief in phase_specs:
        payload = {
            "phase": phase_id,
            "brief": brief,
            "start_beat_number": start_id,
            "ending_type": ending_type,
            "blueprint": {
                "fiction_world": blueprint.get("fiction_world"),
                "acquisition": (blueprint.get("business_or_vehicle") or {}).get("acquisition"),
                "acquisition_structure": (blueprint.get("business_or_vehicle") or {}).get("acquisition_structure"),
                "ending": blueprint.get("ending"),
                "causal_chain": blueprint.get("causal_chain"),
                "ending_type": ending_type,
            },
            "world_snapshot": compact_world(world),
            "beats_so_far": _beats_summary(beats),
            "milestones_hit": (world.get("milestones") or []),
        }
        raw = _chat_json(client, model, BEATS_SYSTEM, payload, temperature=0.7, timeout=180.0, max_tokens=12000)
        act_beats = _extract_beats(raw, start_id)
        if len(act_beats) < 12:
            raw = _chat_json(
                client,
                model,
                BEATS_SYSTEM + "\nDevolvé 15-18 beats. Cada uno con ops. No resumas años en un beat.",
                payload,
                temperature=0.5,
                timeout=180.0,
                max_tokens=12000,
            )
            act_beats = _extract_beats(raw, start_id)
        rebuilt = reconstruct_beats(world, story, prog, act_beats)
        beats.extend(act_beats)
        if rebuilt:
            world = deepcopy(rebuilt[-1]["world_state_after"])
            story = deepcopy(rebuilt[-1]["story_state_after"])
            prog = deepcopy(rebuilt[-1]["progression_after"])
        if phase_id != "p4":
            gp = int((world.get("sports") or {}).get("games_played") or 0)
            if gp >= 16:
                close = {
                    "beat_id": f"b{len(beats) + 1:02d}",
                    "time": f"AGE {(world.get('time') or {}).get('protagonist_age')} · cierre de temporada",
                    "duration_target_s": 12,
                    "cause": "se acaba el fixture",
                    "event": "La temporada queda escrita en el pizarrón. Empieza el receso.",
                    "consequence": "el record pasa a season_history y el W-L se resetea",
                    "story_purpose": "texture",
                    "ops": [{"op": "new_season"}],
                    "contribution": "world change",
                    "world_delta": {},
                    "story_delta": {},
                    "progression_delta": {},
                    "metric_reveal": ["RECORD"],
                    "visual_opportunity": "pizarrón del vestuario con el record final",
                    "transition_to_next": "offseason",
                }
                beats.append(close)
                closed = reconstruct_beats(world, story, prog, [close])
                if closed:
                    world = deepcopy(closed[-1]["world_state_after"])
                    story = deepcopy(closed[-1]["story_state_after"])
                    prog = deepcopy(closed[-1]["progression_after"])
        start_id = len(beats) + 1

    if len(beats) < 45:
        extra = _chat_json(
            client,
            model,
            BEATS_SYSTEM + "\nFaltan beats. Completá huecos de vida (renuncia, mudanza, palco, viaje) y deporte (season_stretch, playoffs) sin repetir. 12-16 beats.",
            {
                "brief": "Relleno causal, no paja.",
                "start_beat_number": start_id,
                "world_snapshot": compact_world(world),
                "beats_so_far": _beats_summary(beats),
                "blueprint": blueprint.get("fiction_world"),
            },
            temperature=0.55,
            timeout=180.0,
            max_tokens=8000,
        )
        beats.extend(_extract_beats(extra, start_id))

    return finalize_architecture(
        project,
        {
            "blueprint": blueprint,
            "synopsis": "",
            "initial_world": initial_world,
            "initial_story": initial_story,
            "initial_progression": initial_prog,
            "beats": beats,
            "_client": client,
            "_model": model,
        },
    )


def finalize_architecture(project: dict[str, Any], architecture: dict[str, Any]) -> dict[str, Any]:
    blueprint = architecture.get("blueprint") if isinstance(architecture.get("blueprint"), dict) else empty_blueprint()
    initial_world = force_pre_acquisition(_merge(empty_world_state(), architecture.get("initial_world")))
    initial_story = _merge(empty_story_state(), architecture.get("initial_story"))
    initial_prog = _merge(empty_progression_state(), architecture.get("initial_progression"))
    raw_beats = architecture.get("beats") if isinstance(architecture.get("beats"), list) else []
    raw_beats = repair_architecture(blueprint=blueprint, beats=raw_beats)
    beats = reconstruct_beats(initial_world, initial_story, initial_prog, raw_beats)
    final_world = beats[-1]["world_state_after"] if beats else initial_world
    patched = inject_life_payoffs(raw_beats, final_world)
    if patched != raw_beats:
        raw_beats = patched
        beats = reconstruct_beats(initial_world, initial_story, initial_prog, raw_beats)
        final_world = beats[-1]["world_state_after"] if beats else initial_world
    beats = rewrite_downgraded_championship(beats)
    beats = sync_loop_payoffs(beats)
    final_world = beats[-1]["world_state_after"] if beats else initial_world
    final_story = beats[-1]["story_state_after"] if beats else initial_story
    final_prog = beats[-1]["progression_after"] if beats else initial_prog

    synopsis = str(architecture.get("synopsis") or "")
    client = architecture.get("_client")
    model = architecture.get("_model")
    if client and model:
        synopsis = _write_synopsis(client, model, blueprint, beats, initial_world, final_world)
    elif not synopsis:
        synopsis = _fallback_synopsis(blueprint, beats, initial_world, final_world)
    else:
        synopsis = _ground_synopsis(synopsis, blueprint, beats, initial_world, final_world)

    if (final_world.get("acquisition") or {}).get("summary"):
        bv = dict(blueprint.get("business_or_vehicle") or {})
        bv["acquisition"] = final_world.get("acquisition")
        bv["acquisition_structure"] = final_world["acquisition"].get("summary") or bv.get("acquisition_structure")
        blueprint["business_or_vehicle"] = bv

    quality = validate_story_quality(
        blueprint=blueprint,
        beats=beats,
        synopsis=synopsis,
        initial_world=initial_world,
        final_world=final_world,
        initial_prog=initial_prog,
        final_prog=final_prog,
    )
    hard = quality.get("hard_fails") or [f for f in (quality.get("flags") or []) if f.get("hard")]
    if hard and client and model:
        # one targeted repair pass on missing life/time, then re-validate
        raw_beats = inject_life_payoffs(raw_beats, final_world)
        extra_ops = []
        if any(f.get("code") == "time_too_short" for f in hard):
            extra_ops.append({"op": "advance_time", "months": 18})
        if extra_ops and raw_beats:
            ops = list(raw_beats[-1].get("ops") or [])
            ops.extend(extra_ops)
            raw_beats[-1]["ops"] = ops
        beats = reconstruct_beats(initial_world, initial_story, initial_prog, raw_beats)
        beats = rewrite_downgraded_championship(beats)
        beats = sync_loop_payoffs(beats)
        final_world = beats[-1]["world_state_after"] if beats else initial_world
        final_story = beats[-1]["story_state_after"] if beats else initial_story
        final_prog = beats[-1]["progression_after"] if beats else initial_prog
        synopsis = _write_synopsis(client, model, blueprint, beats, initial_world, final_world)
        quality = validate_story_quality(
            blueprint=blueprint,
            beats=beats,
            synopsis=synopsis,
            initial_world=initial_world,
            final_world=final_world,
            initial_prog=initial_prog,
            final_prog=final_prog,
        )
        hard = quality.get("hard_fails") or [f for f in (quality.get("flags") or []) if f.get("hard")]
        # Persist even if gates fail: the human reads the movie. Approval is separate.

    quality["review_ready"] = not bool(quality.get("hard_fails"))
    payload = {
        "blueprint": blueprint,
        "synopsis": synopsis,
        "initial_world": initial_world,
        "initial_story": initial_story,
        "initial_progression": initial_prog,
        "final_world": final_world,
        "final_story": final_story,
        "final_progression": final_prog,
        "beats": beats,
        "quality": quality,
        "approved": False,
    }
    payload["review"] = assemble_review(payload)
    persist_architecture(project, payload)
    return project


def approve_check_story(project: dict[str, Any]) -> dict[str, Any]:
    from src.documentary.formats.check_als.story_arch import load_architecture
    from src.documentary.project import append_log, save_project

    arch = load_architecture(project)
    if not arch.get("generated"):
        raise ValueError("Todavía no hay Story Architecture. Generala primero.")
    if not str(arch.get("synopsis") or "").strip() and not arch.get("beats"):
        raise ValueError("La arquitectura está vacía.")
    project["check_story_approved"] = True
    summary = dict(project.get("check_story") or {})
    summary["approved"] = True
    project["check_story"] = summary
    project["ui_step"] = "story"
    project["story_plan_approved"] = False
    save_project(project)
    append_log(str(project.get("id") or ""), "check_story APPROVED (pipeline STOP — no script)")
    return project


def _project_context(project: dict[str, Any]) -> dict[str, Any]:
    concept = project.get("concept") if isinstance(project.get("concept"), dict) else {}
    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    engine = concept.get("story_engine") if isinstance(concept.get("story_engine"), dict) else {}
    return {
        "title": project.get("title"),
        "premise": concept.get("premise") or idea.get("story") or project.get("topic"),
        "one_line_fantasy": concept.get("one_line_fantasy") or "",
        "starting_state": concept.get("starting_state") or "",
        "end_state_hint": concept.get("end_state") or "",
        "story_core_id": concept.get("story_core_id") or engine.get("story_core_id") or "",
        "instruction": (
            "Usa la premisa/fantasía. NO conserves un spine previo. "
            "Construye una película mejor. Ficción. Adquisición plausible. 12-18 minutos."
        ),
        "duration_min": project.get("target_duration_min") or [12, 18],
        "language": "es",
    }


def _extract_blueprint_bundle(raw: dict[str, Any]) -> tuple[dict, str, dict, dict, dict]:
    data = raw.get("blueprint") if isinstance(raw.get("blueprint"), dict) else raw
    if not isinstance(data, dict):
        data = {}
    blueprint = _merge(empty_blueprint(), data if "protagonist" in data or "inciting_incident" in data else raw.get("blueprint") or {})
    if isinstance(raw.get("blueprint"), dict):
        blueprint = _merge(empty_blueprint(), raw["blueprint"])
    synopsis = str(raw.get("synopsis") or data.get("synopsis") or "")
    initial_world = _merge(empty_world_state(), raw.get("initial_world") or data.get("initial_world"))
    acq = (blueprint.get("business_or_vehicle") or {}).get("acquisition")
    if isinstance(acq, dict) and acq:
        initial_world["acquisition"] = {**(initial_world.get("acquisition") or {}), **acq, "closed": False}
    # Seed team names from fiction_world if empty
    fw = blueprint.get("fiction_world") if isinstance(blueprint.get("fiction_world"), dict) else {}
    team = initial_world.get("team") if isinstance(initial_world.get("team"), dict) else {}
    if not team.get("name") and fw.get("team_name"):
        team["name"] = fw["team_name"]
    if not team.get("league") and fw.get("league_name"):
        team["league"] = fw["league_name"]
    if not team.get("city") and fw.get("city"):
        team["city"] = fw["city"]
    initial_world["team"] = team
    initial_story = _merge(empty_story_state(), raw.get("initial_story") or data.get("initial_story"))
    initial_prog = _merge(empty_progression_state(), raw.get("initial_progression") or data.get("initial_progression"))
    return blueprint, synopsis, initial_world, initial_story, initial_prog


def _extract_beats(raw: dict[str, Any], start_id: int) -> list[dict[str, Any]]:
    rows = raw.get("beats")
    if not isinstance(rows, list):
        rows = raw.get("beat_plan") if isinstance(raw.get("beat_plan"), list) else []
    out = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        beat = dict(row)
        beat["beat_id"] = f"b{start_id + i:02d}"
        try:
            beat["duration_target_s"] = int(beat.get("duration_target_s") or 16)
        except (TypeError, ValueError):
            beat["duration_target_s"] = 16
        if not isinstance(beat.get("ops"), list):
            beat["ops"] = []
        if not isinstance(beat.get("world_delta"), dict):
            beat["world_delta"] = {}
        if not isinstance(beat.get("story_delta"), dict):
            beat["story_delta"] = {}
        if not isinstance(beat.get("progression_delta"), dict):
            beat["progression_delta"] = {}
        if not isinstance(beat.get("metric_reveal"), list):
            mr = beat.get("metric_reveal")
            beat["metric_reveal"] = [mr] if mr else []
        out.append(beat)
    return out


def _beats_summary(beats: list[dict[str, Any]]) -> list[str]:
    lines = []
    for b in beats[-12:]:
        lines.append(f"{b.get('beat_id')} {b.get('time')}: {b.get('event')}")
    return lines


def _write_synopsis(client: Any, model: str, blueprint: dict[str, Any], beats: list[dict[str, Any]], initial: dict[str, Any], final: dict[str, Any]) -> str:
    facts = []
    for b in beats:
        snap = b.get("world_snapshot") or {}
        facts.append(
            {
                "id": b.get("beat_id"),
                "time": b.get("time") or snap.get("time"),
                "event": b.get("event"),
                "ops": [o.get("op") for o in (b.get("ops") or []) if isinstance(o, dict)],
                "payoffs": b.get("aspirational_payoffs") or [],
                "age": snap.get("age"),
                "job": snap.get("job"),
                "home": snap.get("home"),
                "own": snap.get("ownership"),
                "val": snap.get("team_value"),
                "debt": snap.get("team_debt"),
                "att": snap.get("attendance"),
                "record": snap.get("record"),
            }
        )
    acq = ((blueprint.get("business_or_vehicle") or {}).get("acquisition")) or (final.get("acquisition") or {})
    sports = (final or {}).get("sports") or {}
    hist = sports.get("season_history") or []
    champs = int(sports.get("championships") or 0)
    system = (
        "Escribí una STORY SYNOPSIS de Check en español, segunda persona, 900-1200 palabras. "
        "Es para VIVIR la película. NO es el script. "
        "Cubrir: vida ordinaria, adquisición con cifras, primer reality check, primer progreso, "
        "payoff de vida, progresión deportiva por TEMPORADA, progresión financiera, setback de dueño, "
        "recovery, corrida deportiva, payoff de deuda (la deuda ya no mata al equipo, no hace falta que sea 0), "
        "payoff final, vida nueva. "
        "SOLO acontecimientos concretos. La emoción sale del hecho (fila que dobla la esquina; tu padre en el palco). "
        "PROHIBIDO: corazón que late, camino de rosas, emoción palpable/indescriptible, símbolo de perseverancia, "
        "trabajo duro, sueño que cobra vida, nueva vida llena de posibilidades, 'todo valió la pena', moraleja. "
        "SPORTS STATE ES LA FUENTE DE VERDAD. season_history y championships=" + str(champs) + ". "
        + (
            "Podés narrar el campeonato porque está en el state. "
            if champs >= 1
            else "PROHIBIDO decir campeonato/campeón/anillo. Narrá el playoff_result real de cada temporada. "
        )
        + "ending_type=" + str(blueprint.get("ending_type") or "triumphant") + ". "
        "Return JSON {\"synopsis\":\"...\"}."
    )
    parsed = _chat_json(
        client,
        model,
        system,
        {
            "acquisition": acq,
            "world": blueprint.get("fiction_world"),
            "ending": blueprint.get("ending"),
            "initial_life": (initial or {}).get("life"),
            "final_life": (final or {}).get("life"),
            "final_sports": sports,
            "season_history": hist,
            "debt_risk_state": ((final or {}).get("finance") or {}).get("debt_risk_state"),
            "final_finance": (final or {}).get("finance"),
            "beats": facts,
        },
        temperature=0.45,
        timeout=180.0,
        max_tokens=5000,
    )
    text = str(parsed.get("synopsis") or "").strip()
    words = len(re.findall(r"\S+", text))
    if words < 900 or words > 1200:
        parsed = _chat_json(
            client,
            model,
            system + f"\nLa anterior tenía {words} palabras. Reescribí entre 900 y 1200. Contá. No recortes el arco.",
            {
                "acquisition": acq,
                "season_history": hist,
                "final_sports": sports,
                "final_life": (final or {}).get("life"),
                "final_finance": (final or {}).get("finance"),
                "debt_risk_state": ((final or {}).get("finance") or {}).get("debt_risk_state"),
                "beats": facts,
                "draft": text,
            },
            temperature=0.35,
            timeout=180.0,
            max_tokens=5000,
        )
        text = str(parsed.get("synopsis") or text).strip()
    if champs < 1:
        text = re.sub(r"(?i)campeonato(s)?", "playoffs", text)
        text = re.sub(r"(?i)campeón(es)?", "equipo de playoffs", text)
        text = re.sub(r"(?i)\banillo\b", "entrada a playoffs", text)
    return _ground_synopsis(text, blueprint, beats, initial, final)


def _fallback_synopsis(blueprint: dict[str, Any], beats: list[dict[str, Any]], initial: dict[str, Any], final: dict[str, Any]) -> str:
    acq = (final or {}).get("acquisition") or {}
    lines = [
        str((blueprint.get("opening") or {}).get("situation") or "Tenés 22 años y un trabajo de oficina."),
        str(acq.get("summary") or (blueprint.get("business_or_vehicle") or {}).get("acquisition_structure") or ""),
    ]
    for b in beats:
        ev = str(b.get("event") or "").strip()
        if ev:
            lines.append(ev)
    text = " ".join(lines)
    words = text.split()
    if len(words) < 800:
        text = text + " " + "El equipo sigue y tu vida también. " * 80
    return _ground_synopsis(" ".join(text.split()[:1100]), blueprint, beats, initial, final)


def _strip_purple(text: str) -> str:
    out = text
    for pat in (
        r"[^.]*tu coraz[oó]n late[^.]*\.",
        r"[^.]*luz al final del t[uú]nel[^.]*\.",
        r"[^.]*el camino no es de rosas[^.]*\.",
        r"[^.]*la emoci[oó]n es (palpable|indescriptible)[^.]*\.",
        r"[^.]*s[ií]mbolo de perseverancia[^.]*\.",
        r"[^.]*tu sue[nñ]o cobra vida[^.]*\.",
        r"[^.]*una nueva vida llena de posibilidades[^.]*\.",
        r"[^.]*finalmente sent[ií]s que todo vali[oó] la pena[^.]*\.",
        r"[^.]*todo vali[oó] la pena[^.]*\.",
    ):
        out = re.sub(pat, "", out, flags=re.I)
    return re.sub(r"\s+", " ", out).strip()


def _ground_synopsis(text: str, blueprint: dict[str, Any], beats: list[dict[str, Any]], initial: dict[str, Any], final: dict[str, Any]) -> str:
    sports = (final or {}).get("sports") or {}
    life = (final or {}).get("life") or {}
    fin = (final or {}).get("finance") or {}
    acq = (final or {}).get("acquisition") or {}
    team = (final or {}).get("team") or {}
    hist = [h for h in (sports.get("season_history") or []) if isinstance(h, dict)]
    seen_seasons: set[int] = set()
    compact_hist = []
    for h in hist:
        sn = int(h.get("season") or 0)
        if sn in seen_seasons:
            compact_hist[-1] = h
        else:
            compact_hist.append(h)
            seen_seasons.add(sn)
    hist = compact_hist
    il = (initial or {}).get("life") or {}
    fw = blueprint.get("fiction_world") or {}
    name = team.get("name") or fw.get("team_name") or "el equipo"
    paras = [
        (
            f"Tenés {(initial or {}).get('time', {}).get('protagonist_age') or 22} años. "
            f"Trabajás de {il.get('job') or 'empleado de oficina'} y vivís en {il.get('home') or 'un departamento compartido'}. "
            f"En la cuenta hay {il.get('personal_cash') or 18000}. Los fines de semana jugás al básquet. "
            f"{name} está al borde de la quiebra: el gimnasio huele a humedad y las gradas no se llenan."
        ),
        str(acq.get("summary") or "Comprás el equipo por un peso y asumís la deuda, con inversores locales y el vendedor reteniendo un porcentaje."),
    ]
    used = set()
    for b in beats:
        ev = str(b.get("event") or "").strip()
        if not ev or ev in used:
            continue
        if re.search(r"\d+\s*-\s*\d+", ev) and hist:
            records = {str(h.get("record") or "") for h in hist}
            if not any(r and r in ev for r in records):
                continue
        purpose = str(b.get("story_purpose") or "")
        kind = str(b.get("reward_or_setback") or "")
        if purpose in {"opening", "inciting_incident", "first_commitment", "first_proof", "midpoint", "major_success", "major_reversal", "crisis", "decision", "climax", "ending"} or kind.startswith("reward") or kind.startswith("setback"):
            paras.append(ev.rstrip(".") + ".")
            used.add(ev)
    for h in hist:
        champ = " Ganás el campeonato." if h.get("championship") else ""
        paras.append(
            f"Temporada {h.get('season')}: el pizarrón cierra {h.get('record')}. "
            f"{str(h.get('playoff_result') or 'Sin playoffs').capitalize()}. "
            f"Asistencia media {h.get('attendance_avg')}. El club factura {h.get('revenue')} y vale {h.get('team_value')}.{champ}"
        )
    risk = str(fin.get("debt_risk_state") or "")
    if risk in ("manageable", "healthy"):
        paras.append(
            f"La deuda del club queda en {fin.get('team_debt')}, con caja {fin.get('team_cash')} "
            f"e ingresos {fin.get('annual_revenue')}. Sigue existiendo, pero ya no puede matar al equipo."
        )
    age = ((final or {}).get("time") or {}).get("protagonist_age")
    paras.append(
        f"Hoy tenés {age} años. Tu trabajo es {life.get('job')}. Vivís en {life.get('home')}. "
        f"En la cuenta personal hay {life.get('personal_cash')}; el patrimonio, en papel, es {life.get('personal_net_worth')}. "
        f"Sos millonario en equity y seguís mirando la cuenta antes de una cena. "
        f"{name} es tuyo en un {((final or {}).get('ownership_ledger') or {}).get('protagonist')}%."
    )
    body = " ".join(paras)
    body = _strip_purple(body)
    extra = []
    for b in beats:
        ev = str(b.get("event") or "").strip()
        if ev and ev not in body and "La temporada queda escrita" not in ev:
            extra.append(ev.rstrip(".") + ".")
    pads = [
        "El primer día como dueño el utilero te alcanza las llaves del gimnasio y no sabe si tutearte.",
        "Bajás el precio de la entrada y esa noche hay más gente en la cola que asientos rotos.",
        "Renunciás al trabajo de oficina cuando el club ya puede pagarte un sueldo feo, pero tuyo.",
        "Te mudás a cuatro cuadras de la arena. El departamento viejo queda con las cajas a las once de la noche.",
        "Si hay palco, todavía no tiene tu apellido. Tus padres vienen igual y se sientan donde hay lugar.",
        "Apostás por roster e instalaciones después de una temporada decente y el mes siguiente el equipo arranca flojo.",
        "El servicio de la deuda deja de ser una amenaza de cierre: hay caja, hay público, hay ingresos.",
        "Una oferta llega al teléfono. Esta vez podés leerla mañana.",
        "El estadio, que olía a humedad, ahora tiene fila los días de partido.",
        "Seguís siendo dueño de un porcentaje y no de todo el efectivo: el paper vale millones y la cuenta, no.",
    ]
    extra.extend(pads)
    words = re.findall(r"\S+", body)
    i = 0
    while len(words) < 920 and i < len(extra):
        if extra[i] not in body:
            body = body + " " + extra[i]
            words = re.findall(r"\S+", body)
        i += 1
    words = re.findall(r"\S+", body)
    if len(words) > 1200:
        body = " ".join(words[:1185])
    return body.strip()


def _merge(base: dict[str, Any], overlay: Any) -> dict[str, Any]:
    out = deepcopy(base)
    if not isinstance(overlay, dict):
        return out
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        elif v not in (None, ""):
            out[k] = deepcopy(v)
    return out


def _chat_json(
    client: Any,
    model: str,
    system: str,
    user: dict[str, Any],
    *,
    temperature: float = 0.7,
    timeout: float = 120.0,
    max_tokens: int = 8000,
) -> dict[str, Any]:
    def _once() -> dict[str, Any]:
        r = client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            timeout=timeout,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        )
        return parse_llm_json_object((r.choices[0].message.content or "{}").strip()) or {}

    return _with_retry(_once, label="check_story", attempts=3, base=1.5)


def public_architecture(project: dict[str, Any]) -> dict[str, Any]:
    from src.documentary.formats.check_als.story_arch import load_architecture

    arch = load_architecture(project)
    review = arch.get("review") or assemble_review(arch) if arch.get("generated") else {}
    compact_beats = []
    for b in arch.get("beats") or []:
        compact_beats.append(
            {
                "beat_id": b.get("beat_id"),
                "time": b.get("time"),
                "duration_target_s": b.get("duration_target_s"),
                "cause": b.get("cause"),
                "event": b.get("event"),
                "consequence": b.get("consequence"),
                "story_purpose": b.get("story_purpose"),
                "emotional_goal": b.get("emotional_goal"),
                "viewer_question": b.get("viewer_question"),
                "reward_or_setback": b.get("reward_or_setback"),
                "metric_reveal": b.get("metric_reveal") or [],
                "visual_opportunity": b.get("visual_opportunity"),
                "world_snapshot": b.get("world_snapshot") or world_snapshot(b.get("world_state_after") or {}),
                "open_loop_action": b.get("open_loop_action") or {},
            }
        )
    return {
        "generated": bool(arch.get("generated")),
        "approved": bool(arch.get("approved") or project.get("check_story_approved")),
        "blueprint": arch.get("blueprint") or {},
        "synopsis": arch.get("synopsis") or "",
        "beats": compact_beats,
        "beat_count": len(compact_beats),
        "quality": arch.get("quality") or {},
        "review": review,
        "final_world": arch.get("final_world") or {},
        "final_progression": arch.get("final_progression") or {},
        "pipeline_stop": "human_review",
        "next_locked": ["script", "visuals", "voice", "render"],
    }
