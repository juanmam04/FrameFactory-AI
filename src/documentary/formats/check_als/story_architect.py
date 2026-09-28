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
    expand_synopsis_to_min_words,
    force_pay_important_loops,
    force_pre_acquisition,
    inject_life_payoffs,
    repair_architecture,
    repair_beat_ops,
    rewrite_downgraded_championship,
    scrub_sports_text,
    strip_sports_narrative,
    sync_loop_payoffs,
)
from src.documentary.formats.check_als.plain_language import (
    PUBLIC_CLOSES,
    PUBLIC_EVENT_RULES,
    plain_event,
    public_life_synopsis,
)
from src.documentary.formats.check_als.story_vehicle import (
    beats_system,
    blueprint_system,
    default_open_loops,
    phase_specs,
    vehicle_mode,
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
- """ + PUBLIC_EVENT_RULES + """
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
    vmode = vehicle_mode(project)
    concept = project.get("concept") if isinstance(project.get("concept"), dict) else {}
    narrative_ending = str(
        project.get("check_ending_type") or concept.get("ending_type") or "open"
    ).strip().lower()
    if narrative_ending not in ("victory", "exit", "loss", "dilema", "pyrrhic", "ironic", "open", "plateau"):
        narrative_ending = "open"
    user_ctx["vehicle_mode"] = vmode
    user_ctx["narrative_ending"] = narrative_ending
    if vmode == "freeform":
        mode_line = (
            " MODO IDEA DEL USUARIO: la premisa es intocable. "
            "No la conviertas en equipo, empresa, restaurante ni otro oficio. "
            "Adapta las escenas, el plazo y el cierre a ESA fantasía."
        )
    elif vmode == "creator":
        mode_line = (
            " MODO CANAL: la película es ese canal de YouTube. "
            "Prohibido equipo, club, gimnasio, playoffs, estadio, básquet y dueño del equipo. "
            "Di qué video es y una cifra que cierre con visitas reales: en tecnología, unos 20 a 40 dólares cada 1.000 visitas. "
            "Un intermedio: se ve, y no es un inventario."
        )
    elif vmode == "sports_team":
        mode_line = (
            " MODO DEPORTE: equipo de básquet ficticio, con nombre, un jugador y cifras que cierren entre sí. "
            "El sueldo de un año tiene que caber varias veces en lo que otro club pagaría por él. "
            "Un par de detalles de vida, no un inventario del club."
        )
    elif vmode == "business":
        mode_line = " MODO NEGOCIO: empresa/creator — cero básquet/playoffs/campeonato."
    else:
        mode_line = (
            f" MODO {vmode}: la fantasía es ESE vehículo, no un equipo de básquet ni una startup genérica. "
            "Prohibido playoffs, estadio y campeonato salvo que el vehículo sea deporte."
        )
    close_line = PUBLIC_CLOSES.get(narrative_ending) or PUBLIC_CLOSES["open"]
    ending_line = (
        f" FINAL NARRATIVO OBLIGATORIO: {narrative_ending}. "
        f"La última escena y blueprint.ending tienen que decir, en la vida cotidiana: {close_line} "
        "Si la premisa escrita termina de otra forma (subasta, pérdida, éxito, lecciones), "
        "ignora ese cierre y usa este. "
        "No lo conviertas en 'bloqueas, mañana lo lees' si el tipo no es open."
    )
    user_ctx["instruction"] += mode_line + ending_line

    raw_bp = _chat_json(client, model, blueprint_system(vmode), user_ctx, temperature=0.8, timeout=180.0, max_tokens=7000)
    blueprint, _syn_unused, initial_world, initial_story, initial_prog = _extract_blueprint_bundle(raw_bp)
    if vmode == "freeform":
        blueprint["user_premise"] = str(user_ctx.get("premise") or "")
        blueprint["freeform"] = True
    blueprint["narrative_ending"] = narrative_ending
    blueprint["ending"] = close_line
    initial_world = force_pre_acquisition(initial_world, mode=vmode)
    if not (initial_story.get("open_loops") or []):
        initial_story["open_loops"] = default_open_loops(vmode)
    ending_type = str(blueprint.get("ending_type") or "triumphant").lower()
    if ending_type not in ("triumphant", "open_future", "comeback", "empire_continues"):
        blueprint["ending_type"] = "triumphant"
        ending_type = "triumphant"

    phase_specs_list = phase_specs(vmode, close_line)
    beats: list[dict[str, Any]] = []
    world = deepcopy(initial_world)
    story = deepcopy(initial_story)
    prog = deepcopy(initial_prog)
    start_id = 1
    beats_sys = beats_system(vmode)
    for phase_id, brief in phase_specs_list:
        payload = {
            "phase": phase_id,
            "brief": brief,
            "start_beat_number": start_id,
            "ending_type": ending_type,
            "narrative_ending": narrative_ending,
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
        if phase_id == "p2":
            payload["closing_sentence"] = close_line
        raw = _chat_json(client, model, beats_sys, payload, temperature=0.7, timeout=180.0, max_tokens=12000)
        act_beats = _extract_beats(raw, start_id, sports=vmode == "sports_team")
        if len(act_beats) < 5:
            raw = _chat_json(
                client,
                model,
                beats_sys + "\nDevolvé unas 6 a 8 escenas que se causen y cambien de ritmo. No es una lista de pasos iguales.",
                payload,
                temperature=0.5,
                timeout=180.0,
                max_tokens=6000,
            )
            act_beats = _extract_beats(raw, start_id, sports=vmode == "sports_team")
        if vmode != "sports_team":
            act_beats = strip_sports_narrative(act_beats)
        rebuilt = reconstruct_beats(world, story, prog, act_beats)
        beats.extend(act_beats)
        if rebuilt:
            world = deepcopy(rebuilt[-1]["world_state_after"])
            story = deepcopy(rebuilt[-1]["story_state_after"])
            prog = deepcopy(rebuilt[-1]["progression_after"])
        if phase_id == "p1" and vmode == "sports_team":
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
    vmode = vehicle_mode(project)
    blueprint = architecture.get("blueprint") if isinstance(architecture.get("blueprint"), dict) else empty_blueprint()
    # Business blueprints must not carry basketball acquisition debt.
    if vmode != "sports_team":
        bv = dict(blueprint.get("business_or_vehicle") or {})
        acq = dict(bv.get("acquisition") or {})
        if _num(acq.get("debt_assumed")) >= 100000:
            acq["debt_assumed"] = 0
            acq["seller_financing"] = 0
            acq["existing_liabilities_assumed"] = 0
            bv["acquisition"] = acq
            blueprint["business_or_vehicle"] = bv
    initial_world = force_pre_acquisition(_merge(empty_world_state(), architecture.get("initial_world")), mode=vmode)
    initial_story = _merge(empty_story_state(), architecture.get("initial_story"))
    initial_prog = _merge(empty_progression_state(), architecture.get("initial_progression"))
    raw_beats = architecture.get("beats") if isinstance(architecture.get("beats"), list) else []
    raw_beats = repair_beat_ops(raw_beats, mode=vmode)
    raw_beats = repair_architecture(blueprint=blueprint, beats=raw_beats, mode=vmode)
    if vmode != "sports_team":
        raw_beats = strip_sports_narrative(raw_beats)
    beats = reconstruct_beats(initial_world, initial_story, initial_prog, raw_beats)
    final_world = beats[-1]["world_state_after"] if beats else initial_world
    patched = inject_life_payoffs(raw_beats, final_world)
    if patched != raw_beats:
        raw_beats = patched
        if vmode != "sports_team":
            raw_beats = strip_sports_narrative(raw_beats)
        beats = reconstruct_beats(initial_world, initial_story, initial_prog, raw_beats)
        final_world = beats[-1]["world_state_after"] if beats else initial_world
    if vmode != "sports_team":
        beats = strip_sports_narrative(beats)
    beats = rewrite_downgraded_championship(beats)
    beats = sync_loop_payoffs(beats, mode=vmode)
    beats = force_pay_important_loops(beats)
    final_world = beats[-1]["world_state_after"] if beats else initial_world
    final_story = beats[-1]["story_state_after"] if beats else initial_story
    final_prog = beats[-1]["progression_after"] if beats else initial_prog

    synopsis = str(architecture.get("synopsis") or "")
    client = architecture.get("_client")
    model = architecture.get("_model")
    if client and model:
        synopsis = _write_synopsis(
            client, model, blueprint, beats, initial_world, final_world, vehicle_mode=vmode
        )
    elif not synopsis:
        synopsis = _fallback_synopsis(blueprint, beats, initial_world, final_world, vehicle_mode=vmode)
    else:
        synopsis = _ground_synopsis(synopsis, blueprint, beats, initial_world, final_world, vehicle_mode=vmode)

    synopsis = _polish_synopsis_for_mode(synopsis, beats, vmode)

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
        vehicle_mode=vmode,
    )
    hard = quality.get("hard_fails") or [f for f in (quality.get("flags") or []) if f.get("hard")]
    if hard:
        # Deterministic repair pass — never hand the UI a broken "final" story.
        raw_beats = repair_beat_ops(raw_beats, mode=vmode)
        raw_beats = repair_architecture(blueprint=blueprint, beats=raw_beats, mode=vmode)
        if vmode != "sports_team":
            raw_beats = strip_sports_narrative(raw_beats)
        raw_beats = inject_life_payoffs(raw_beats, final_world)
        extra_ops = []
        if vmode != "freeform" and any(f.get("code") == "time_too_short" for f in hard):
            extra_ops.append({"op": "advance_time", "months": 36})
        if vmode != "freeform" and any(f.get("code") == "acquisition_missing" for f in hard) and raw_beats:
            # Nuclear inject on beat 4 (or last) if still missing after repair_architecture.
            idx = min(3, len(raw_beats) - 1)
            ops = list(raw_beats[idx].get("ops") or [])
            names = {str((o or {}).get("op") or (o or {}).get("type") or "") for o in ops if isinstance(o, dict)}
            if "launch_company" not in names and "acquire_team" not in names:
                if vmode != "sports_team":
                    ops.insert(0, {"op": "launch_company", "your_cash": 8000, "investor_cash": 40000, "your_pct": 60, "investor_pct": 40, "debt_assumed": 0})
                else:
                    ops.insert(0, {"op": "acquire_team", "your_cash": 15000, "investor_cash": 85000, "your_pct": 51, "investor_pct": 39, "seller_pct": 10, "debt_assumed": 650000, "asking_price": 1})
                raw_beats[idx]["ops"] = ops
        if extra_ops and raw_beats:
            ops = list(raw_beats[-1].get("ops") or [])
            ops.extend(extra_ops)
            raw_beats[-1]["ops"] = ops
        beats = reconstruct_beats(initial_world, initial_story, initial_prog, raw_beats)
        if vmode != "sports_team":
            beats = strip_sports_narrative(beats)
        beats = rewrite_downgraded_championship(beats)
        beats = sync_loop_payoffs(beats, mode=vmode)
        beats = force_pay_important_loops(beats)
        final_world = beats[-1]["world_state_after"] if beats else initial_world
        final_story = beats[-1]["story_state_after"] if beats else initial_story
        final_prog = beats[-1]["progression_after"] if beats else initial_prog
        if client and model:
            synopsis = _write_synopsis(
                client, model, blueprint, beats, initial_world, final_world, vehicle_mode=vmode
            )
        synopsis = _polish_synopsis_for_mode(synopsis, beats, vmode)
        quality = validate_story_quality(
            blueprint=blueprint,
            beats=beats,
            synopsis=synopsis,
            initial_world=initial_world,
            final_world=final_world,
            initial_prog=initial_prog,
            final_prog=final_prog,
            vehicle_mode=vmode,
        )
        hard = quality.get("hard_fails") or [f for f in (quality.get("flags") or []) if f.get("hard")]
        if hard:
            # Last resort: scrub + pad + force loops, then revalidate (should clear soft-hard gates).
            beats = force_pay_important_loops(beats)
            synopsis = _polish_synopsis_for_mode(synopsis, beats, vmode)
            quality = validate_story_quality(
                blueprint=blueprint,
                beats=beats,
                synopsis=synopsis,
                initial_world=initial_world,
                final_world=final_world,
                initial_prog=initial_prog,
                final_prog=final_prog,
                vehicle_mode=vmode,
            )

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
    payload["review"] = assemble_review(payload, vehicle_mode=vmode)
    persist_architecture(project, payload)
    return project


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _polish_synopsis_for_mode(synopsis: str, beats: list[dict[str, Any]], mode: str) -> str:
    text = str(synopsis or "").strip()
    if mode == "business":
        text = scrub_sports_text(text)
    text = expand_synopsis_to_min_words(text, beats, min_words=180)
    if mode == "business":
        text = scrub_sports_text(text)
    return text


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
    summary["generated"] = True
    project["check_story"] = summary
    project["ui_step"] = "script"
    # Keep documentary step-gate happy (set_step still checks story_plan_approved).
    project["story_plan_approved"] = True
    save_project(project)
    append_log(str(project.get("id") or ""), "check_story APPROVED — script unlocked (no voice/render yet)")
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
            "Construye una película mejor. Ficción. "
            + (
                "Si la idea no es comprar ni fundar algo, no inventes una adquisición. "
                if concept.get("user_proposed")
                else "Adquisición plausible. "
            )
            + "12-18 minutos."
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


def _extract_beats(raw: dict[str, Any], start_id: int, *, sports: bool = True) -> list[dict[str, Any]]:
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
        for key in ("event", "cause", "consequence", "visual_opportunity"):
            if beat.get(key):
                beat[key] = plain_event(str(beat.get(key) or ""), sports=sports)
        out.append(beat)
    return out


def _beats_summary(beats: list[dict[str, Any]]) -> list[str]:
    lines = []
    for b in beats[-12:]:
        lines.append(f"{b.get('beat_id')} {b.get('time')}: {b.get('event')}")
    return lines


def _write_synopsis(
    client: Any,
    model: str,
    blueprint: dict[str, Any],
    beats: list[dict[str, Any]],
    initial: dict[str, Any],
    final: dict[str, Any],
    *,
    vehicle_mode: str = "sports_team",
) -> str:
    # La película que lee la gente sale de la vida simulada, en español de todos los días.
    # Los números siguen en el mundo; no se vuelcan a la synopsis.
    del client, model
    return _ground_synopsis("", blueprint, beats, initial, final, vehicle_mode=vehicle_mode)




def _fallback_synopsis(
    blueprint: dict[str, Any],
    beats: list[dict[str, Any]],
    initial: dict[str, Any],
    final: dict[str, Any],
    *,
    vehicle_mode: str = "sports_team",
) -> str:
    return _ground_synopsis("", blueprint, beats, initial, final, vehicle_mode=vehicle_mode)


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


def _ground_synopsis(
    text: str,
    blueprint: dict[str, Any],
    beats: list[dict[str, Any]],
    initial: dict[str, Any],
    final: dict[str, Any],
    *,
    vehicle_mode: str = "sports_team",
) -> str:
    del text
    body = public_life_synopsis(blueprint, beats, initial, final, vehicle_mode=vehicle_mode)
    return _strip_purple(body)


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
    from src.documentary.formats.check_als.plain_language import has_jargon, plain_event, public_life_synopsis, sports_bleed
    from src.documentary.formats.check_als.story_arch import load_architecture
    from src.documentary.formats.check_als.story_vehicle import vehicle_mode as _vehicle_mode

    arch = load_architecture(project)
    mode = _vehicle_mode(project)
    review = assemble_review(arch, vehicle_mode=mode) if arch.get("generated") else {}
    synopsis = str(arch.get("synopsis") or "")
    if has_jargon(synopsis) or (mode != "sports_team" and sports_bleed(synopsis)):
        shown = dict(arch.get("blueprint") or {})
        concept = project.get("concept") if isinstance(project.get("concept"), dict) else {}
        shown["narrative_ending"] = str(
            project.get("check_ending_type") or concept.get("ending_type") or shown.get("narrative_ending") or ""
        ).strip().lower()
        synopsis = public_life_synopsis(
            shown,
            arch.get("beats") or [],
            arch.get("initial_world") or {},
            arch.get("final_world") or {},
                vehicle_mode=mode,
        )
    quality = arch.get("quality") or {}
    if arch.get("generated") and (arch.get("beats") or []):
        quality = validate_story_quality(
            blueprint=arch.get("blueprint") or {},
            beats=arch.get("beats") or [],
            synopsis=synopsis,
            initial_world=arch.get("initial_world") or {},
            final_world=arch.get("final_world") or {},
            initial_prog=arch.get("initial_progression") or {},
            final_prog=arch.get("final_progression") or {},
            vehicle_mode=mode,
        )
    compact_beats = []
    for b in arch.get("beats") or []:
        compact_beats.append(
            {
                "beat_id": b.get("beat_id"),
                "time": b.get("time"),
                "duration_target_s": b.get("duration_target_s"),
                "cause": plain_event(str(b.get("cause") or ""), sports=mode == "sports_team"),
                "event": plain_event(str(b.get("event") or ""), sports=mode == "sports_team"),
                "consequence": plain_event(str(b.get("consequence") or ""), sports=mode == "sports_team"),
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
        "synopsis": synopsis,
        "beats": compact_beats,
        "beat_count": len(compact_beats),
        "quality": quality,
        "review": review,
        "final_world": arch.get("final_world") or {},
        "final_progression": arch.get("final_progression") or {},
        "pipeline_stop": "script_visuals" if (arch.get("approved") or project.get("check_story_approved")) else "human_review",
        "next_locked": (
            ["voice", "music", "render"]
            if (arch.get("approved") or project.get("check_story_approved"))
            else ["script", "visuals", "voice", "render"]
        ),
    }
