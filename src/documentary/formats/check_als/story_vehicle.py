"""Vehicle mode: detección automática de cualquier tipo de fantasía."""
from __future__ import annotations

from typing import Any

# Import universal vehicle system
try:
    from src.documentary.formats.check_als.universal_vehicles import detect_vehicle_type
except ImportError:
    # Fallback durante transición
    def detect_vehicle_type(premise: str, topic: str = "", category: str = "") -> str:
        text = f"{premise} {topic} {category}".lower()
        if any(h in text for h in ("equipo", "estadio", "playoff", "liga deportiva")):
            return "sports_team"
        return "business"


def vehicle_mode(project: dict[str, Any]) -> str:
    """
    Detecta el tipo de vehículo aspiracional basado en el contenido.
    Retorna el tipo específico (sports_team, musician, chef, etc.) o 'business' como default.
    """
    concept = project.get("concept") if isinstance(project.get("concept"), dict) else {}
    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    
    # Reunir todo el texto relevante
    category = str(concept.get("story_category") or idea.get("content_pillar") or "").strip()
    premise = str(concept.get("premise") or concept.get("one_line_fantasy") or "").strip()
    topic = str(project.get("topic") or project.get("title") or concept.get("title") or "").strip()
    
    # Usar el detector universal
    return detect_vehicle_type(premise, topic, category)


def default_open_loops(mode: str) -> list[dict[str, Any]]:
    """Genera open loops dinámicos basados en el tipo de vehículo."""
    try:
        from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES
        
        vehicle_info = UNIVERSAL_VEHICLES.get(mode)
        if vehicle_info:
            # Loops personalizados según el vehículo
            vehicle_name = vehicle_info["vehicle"]
            return [
                {"id": "start", "question": f"¿realmente podrás {vehicle_info['acquisition']}?", "opened_at": "start", "status": "open", "important": True},
                {"id": "survive", "question": "¿sobrevivirás el primer año?", "opened_at": "start", "status": "open", "important": True},
                {"id": "compete", "question": "¿podrás competir contra los grandes?", "opened_at": "start", "status": "open", "important": True},
                {"id": "success", "question": "¿llegará el reconocimiento real?", "opened_at": "start", "status": "open", "important": True},
                {"id": "how_far", "question": "¿qué tan lejos puede llegar esto?", "opened_at": "start", "status": "open", "important": False, "intentional_unresolved": True},
            ]
    except ImportError:
        pass
    
    # Fallback a sports/business tradicional
    if mode == "sports_team":
        return [
            {"id": "buy", "question": "¿realmente podrás comprarlo?", "opened_at": "start", "status": "open", "important": True},
            {"id": "save_team", "question": "¿podrás evitar que cierre?", "opened_at": "start", "status": "open", "important": True},
            {"id": "debt", "question": "¿la deuda dejará de amenazar al club?", "opened_at": "start", "status": "open", "important": True},
            {"id": "compete", "question": "¿puede competir de verdad?", "opened_at": "start", "status": "open", "important": True},
            {"id": "how_far", "question": "¿qué tan lejos puede llegar?", "opened_at": "start", "status": "open", "important": False, "intentional_unresolved": True},
        ]
    return [
        {"id": "launch", "question": "¿podrás convertir la idea en un negocio real?", "opened_at": "start", "status": "open", "important": True},
        {"id": "cash", "question": "¿te alcanza el cash para aguantar el primer año?", "opened_at": "start", "status": "open", "important": True},
        {"id": "growth", "question": "¿escala o se queda en un side hustle?", "opened_at": "start", "status": "open", "important": True},
        {"id": "quit", "question": "¿renunciarás al trabajo seguro?", "opened_at": "start", "status": "open", "important": True},
        {"id": "how_far", "question": "¿hasta dónde llega esto?", "opened_at": "start", "status": "open", "important": False, "intentional_unresolved": True},
    ]


def phase_specs(mode: str, ending_type: str) -> list[tuple[str, str]]:
    """Genera specs de fases dinámicas basadas en el vehículo."""
    try:
        from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES
        
        vehicle_info = UNIVERSAL_VEHICLES.get(mode)
        if vehicle_info and mode not in ("sports_team", "business"):
            # Vehículo personalizado - estructura genérica adaptable
            vehicle_name = vehicle_info["vehicle"]
            acquisition = vehicle_info["acquisition"]
            progression = vehicle_info["progression"]
            
            return [
                ("p1", f"Tramo 1 AGE 22-23: vida ordinaria → oportunidad → {acquisition}. 14-16 beats. Primeros pasos, realidad golpea."),
                ("p2", f"Tramo 2 AGE 23-24: primeros logros reales, setbacks, la vida empieza a cambiar. Progresión por {progression}. 14-16 beats."),
                ("p3", f"Tramo 3 AGE 24-26: apuesta grande, crisis, decisión crítica. Gran salto de progreso. Primer gran payoff de vida. 14-18 beats."),
                ("p4", f"Tramo 4 AGE 26-28: estabilidad, reconocimiento, cambios de vida peak. ending_type={ending_type}. 14-18 beats."),
            ]
    except ImportError:
        pass
    
    # Fallback tradicional
    if mode == "sports_team":
        return [
            ("p1", "Tramo 1 AGE 22: vida ordinaria → oportunidad → CÓMO se compra (ops: acquire_team) → sos dueño. 14-16 beats. Temporada 1 puede arrancar mal. NO campeonato."),
            ("p2", "Tramo 2 AGE 22-23: reality hits, first proof, la vida EMPIEZA a cambiar. Cerrá Temporada 1 con season_stretch + record real. 14-16 beats."),
            ("p3", "Tramo 3 AGE 23-25: apuesta de dueño, owner_crisis, decisión. Progreso deportivo (new_season + season_stretch). Primer gran payoff de vida. 14-18 beats."),
            ("p4", f"Tramo 4 AGE 25-27: recovery, playoffs/final si el state lo gana, debt_risk manageable. Payoff de vida. ending_type={ending_type}. 14-18 beats."),
        ]
    return [
        ("p1", "Tramo 1 AGE 22-23: vida ordinaria → oportunidad → LANZÁS la empresa (ops: launch_company o acquire_team con deuda baja). 14-16 beats. Primeros clientes/views. NO campeonato ni deporte."),
        ("p2", "Tramo 2 AGE 23-24: primeras ventas, primer empleado, setback financiero, la vida empieza a cambiar (quit_job, move_home). 14-16 beats."),
        ("p3", "Tramo 3 AGE 24-26: apuesta cara (equipo, ads, oficina), owner_crisis, decisión (inyectar / vender equity / recortar). Gran hit de crecimiento. 14-18 beats."),
        ("p4", f"Tramo 4 AGE 26-28: empresa estable, sponsor o contrato grande, mudanza, familia/status. ending_type={ending_type}. 14-18 beats. PROHIBIDO básquet, playoffs, campeonato."),
    ]


def blueprint_system(mode: str) -> str:
    """Retorna el system prompt de blueprint adaptado al vehículo."""
    try:
        from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES, get_universal_vehicle_prompt
        
        vehicle_info = UNIVERSAL_VEHICLES.get(mode)
        if vehicle_info and mode not in ("sports_team", "business"):
            # Vehículo personalizado - genera prompt universal
            return _generate_universal_blueprint(mode, vehicle_info)
    except ImportError:
        pass
    
    # Fallback tradicional
    if mode == "sports_team":
        return _BLUEPRINT_SPORTS
    return _BLUEPRINT_BUSINESS


def beats_system(mode: str) -> str:
    """Retorna el system prompt de beats adaptado al vehículo."""
    try:
        from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES
        
        vehicle_info = UNIVERSAL_VEHICLES.get(mode)
        if vehicle_info and mode not in ("sports_team", "business"):
            # Vehículo personalizado - genera beats universal
            return _generate_universal_beats(mode, vehicle_info)
    except ImportError:
        pass
    
    # Fallback tradicional
    if mode == "sports_team":
        return _BEATS_SPORTS
    return _BEATS_BUSINESS


def _generate_universal_blueprint(mode: str, vehicle_info: dict) -> str:
    """Genera blueprint system para vehículo personalizado."""
    vehicle_name = vehicle_info["vehicle"]
    acquisition = vehicle_info["acquisition"]
    metrics = ", ".join(vehicle_info["metrics"])
    
    return f"""
Eres Story Architect de Check: ficción aspiracional en ESPAÑOL. El espectador ES el protagonista (tú/te).

Esta fantasía es {vehicle_name.upper()} — construcción de {vehicle_name}.
PROHIBIDO: equipos de básquet, playoffs, campeonatos (a menos que sea el vehículo específico).

REGLAS:
- Empieza ANTES de {acquisition}. ownership/control inicial = 0.
- El vehículo es {vehicle_name} con métricas claras: {metrics}.
- Adquisición o lanzamiento con cifras: cash tuyo, inversores, deuda (si aplica), % equity/control.
- Varios años (4-6). La vida personal CAMBIA: trabajo → carrera propia, departamento → upgrade.
- Setbacks variados (financiero, profesional, personal). NO forzar deporte si no aplica.
- Final = escena/estado concreto, nunca moraleja.

Return ONLY JSON:
{{
  "blueprint": {{
    protagonist, fantasy, business_or_vehicle{{what_is_being_built_or_owned, core_mechanism, economic_engine,
      acquisition_structure, acquisition{{...}}}},
    fiction_world{{company_name/stage_name/vehicle_name, industry/field, city, disclaimer}},
    ending_type, opening, inciting_incident, first_commitment, escalation, midpoint,
    major_success, major_reversal, crisis, decision, climax, ending, final_state,
    intentional_unresolved_loops[], causal_chain[10-16]
  }},
  "initial_world": {{
    life.job empleado/freelancer, life.home departamento/habitación, life.personal_cash 8000-25000,
    ownership_ledger {{protagonist:0, investors:0, seller:100}}, acquisition.closed=false,
    team.name = {vehicle_name}, team.league = industry/field, sports vacío si no aplica,
    finance.team_debt bajo o 0 (startup), time.protagonist_age 22-26
  }}
}}
NO escribas synopsis. Adaptá métricas al vehículo específico.
""".strip()


def _generate_universal_beats(mode: str, vehicle_info: dict) -> str:
    """Genera beats system para vehículo personalizado."""
    vehicle_name = vehicle_info["vehicle"]
    progression = vehicle_info["progression"]
    
    return f"""
Eres Beat Planner de Check — MODO {vehicle_name.upper()}.

Ops permitidas (adaptadas al vehículo):
launch_company, acquire_team (compra de {vehicle_name}),
equity_sale, buyback, sponsor_deal, sponsor_cut, first_client/fan/audience,
viral_hit, hire_employee, sign_contract, product_launch/album_launch/show_launch,
owner_crisis, owner_injection, investor_injection, credit_line, bridge_loan, pay_debt,
quit_job, move_home, help_family, advance_time, facility_upgrade, media_deal,
media_crisis, regulatory_fine, personal_crisis

PROHIBIDO ops deportivas si no aplica: game_played, championship, playoffs, injury, coach, season_stretch.

Cada transacción de plata DEBE tener ops con montos.
equity_sale SIEMPRE incluye pct y cash.

Métricas vía team.valuation, team.attendance (clientes/fans/audiencia), finance.team_cash.
Progresión por {progression}. 3-4 años. Payoffs de vida: renuncia, mudanza, upgrade, reconocimiento.

Return ONLY JSON: {{"beats":[...]}} — 14-18 beats por tramo.
""".strip()


_BLUEPRINT_SPORTS = """
Eres Story Architect de Check: ficción aspiracional en ESPAÑOL. El espectador ES el protagonista (tú/te).
Check NO es moraleja. Es simulación de vida construyendo un EQUIPO DE BÁSQUET ficticio.
Empieza ANTES de ser dueño. ownership inicial = 0. Adquisición con cifras concretas.
3-5 temporadas de básquet simuladas. La vida personal CAMBIA con el equipo.
Return ONLY JSON: blueprint + initial_world (ownership_ledger protagonist:0, seller:100, acquisition.closed=false).
fiction_world: team_name, league_name, city. NO escribas synopsis.
""".strip()

_BLUEPRINT_BUSINESS = """
Eres Story Architect de Check: ficción aspiracional en ESPAÑOL. El espectador ES el protagonista (tú/te).

Esta fantasía es NEGOCIO / EMPRESA / CREADOR DE CONTENIDO — NO es básquet ni deporte profesional.
PROHIBIDO: equipos de básquet, playoffs, campeonatos, estadios, ligas deportivas, entrenadores, plantel.
Construí una empresa ficticia (media, SaaS, agencia, marca, estudio) en una ciudad concreta.

REGLAS:
- Empieza ANTES de ser fundador/controlador. ownership inicial = 0.
- El vehículo es una EMPRESA con mecanismo económico claro (clientes, suscriptores, contratos, producto).
- Adquisición o lanzamiento con cifras: cash tuyo, inversores, deuda asumida (si aplica), % equity.
- Varios años (4-6). La vida personal CAMBIA: trabajo → full-time founder, departamento → oficina/casa propia.
- Setbacks de categorías distintas (cash, cliente, equipo, producto, legal, personal). NO deporte.
- Final = escena/estado concreto, nunca moraleja.

Return ONLY JSON:
{
  "blueprint": {
    protagonist, fantasy, business_or_vehicle{what_is_being_built_or_owned, core_mechanism, economic_engine,
      acquisition_structure, acquisition{...}},
    fiction_world{company_name, industry, city, disclaimer},
    ending_type, opening, inciting_incident, first_commitment, escalation, midpoint,
    major_success, major_reversal, crisis, decision, climax, ending, final_state,
    intentional_unresolved_loops[], causal_chain[10-16]
  },
  "initial_world": {
    life.job empleado/freelancer, life.home departamento/habitación, life.personal_cash 8000-25000,
    ownership_ledger {protagonist:0, investors:0, seller:100}, acquisition.closed=false,
    team.name = company_name, team.league = industry (NO liga deportiva), sports vacío/0-0,
    finance.team_debt bajo o 0 (startup), time.protagonist_age 22-26
  }
}
NO escribas synopsis. NO uses team_name/league_name deportivos.
""".strip()

_BEATS_SPORTS = """
Eres Beat Planner de Check — MODO DEPORTE (equipo de básquet).
Ops: acquire_team, season_stretch, new_season, playoffs, sponsor_deal, equity_sale, quit_job, move_home, advance_time...
SPORTS STATE es la fuente de verdad. championship_won SOLO si el snapshot lo permite.
Return ONLY JSON: {"beats":[...]}
""".strip()

_BEATS_BUSINESS = """
Eres Beat Planner de Check — MODO NEGOCIO (empresa / creador / startup). NO BÁSQUET.

Ops permitidas:
launch_company, acquire_team (solo compra de negocio existente, NO equipo deportivo),
equity_sale, buyback, sponsor_deal, sponsor_cut, first_client, viral_hit, hire_employee,
sign_contract, product_launch, ad_spend, owner_crisis, owner_injection, investor_injection,
credit_line, bridge_loan, pay_debt, quit_job, move_home, help_family, advance_time,
facility_upgrade, media_deal, media_crisis, regulatory_fine, personal_crisis

PROHIBIDO en eventos y ops: game_played, championship, playoffs, injury, coach, season_stretch, new_season.
Cada transacción de plata DEBE tener ops con montos (your_cash, investor_cash, pct, cash).
equity_sale SIEMPRE incluye pct y cash y mueve ownership_ledger.

Métricas de negocio vía team.valuation, team.attendance (= clientes/suscriptores activos), finance.team_cash.
3-4 años. Payoffs de vida: renuncia, mudanza, oficina, contrato grande, familia en evento.

Return ONLY JSON: {"beats":[...]} — 14-18 beats por tramo.
""".strip()
