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
    if concept.get("user_proposed") or project.get("user_proposed"):
        return "freeform"
    stored = str(project.get("vehicle_type") or concept.get("vehicle_type") or "").strip()
    if stored == "freeform":
        return "freeform"
    topic = str(project.get("topic") or project.get("title") or concept.get("title") or "").strip()
    premise = str(concept.get("premise") or concept.get("one_line_fantasy") or "").strip()
    blob = f"{premise} {topic}".lower()
    channel = any(k in blob for k in ("canal", "youtube", "youtuber", "suscriptor"))
    sports_title = any(k in blob for k in ("equipo de básquet", "equipo deportivo", "playoff", "estadio"))
    if channel and not sports_title:
        return "creator"
    if stored:
        try:
            from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES

            if stored in UNIVERSAL_VEHICLES or stored in ("sports_team", "business"):
                return stored
        except ImportError:
            if stored in ("sports_team", "business"):
                return stored

    category = str(concept.get("story_category") or idea.get("content_pillar") or "").strip()
    return detect_vehicle_type(premise, topic, category)


def default_open_loops(mode: str) -> list[dict[str, Any]]:
    """Genera open loops dinámicos basados en el tipo de vehículo."""
    if mode == "freeform":
        return [
            {"id": "start", "question": "¿empiezas el reto?", "opened_at": "start", "status": "open", "important": True},
            {"id": "clock", "question": "¿llegas al final del plazo?", "opened_at": "start", "status": "open", "important": True},
            {"id": "how_far", "question": "¿cómo termina?", "opened_at": "start", "status": "open", "important": False, "intentional_unresolved": True},
        ]
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
            {"id": "yes", "question": "¿vas a decir que sí?", "opened_at": "start", "status": "open", "important": True},
            {"id": "crowd", "question": "¿el lugar se va a llenar?", "opened_at": "start", "status": "open", "important": True},
            {"id": "quit", "question": "¿vas a dejar la oficina?", "opened_at": "start", "status": "open", "important": True},
            {"id": "how_far", "question": "¿cómo termina esta vida?", "opened_at": "start", "status": "open", "important": False, "intentional_unresolved": True},
        ]
    return [
        {"id": "yes", "question": "¿vas a animarte a empezar?", "opened_at": "start", "status": "open", "important": True},
        {"id": "people", "question": "¿va a llegar gente de verdad?", "opened_at": "start", "status": "open", "important": True},
        {"id": "quit", "question": "¿vas a dejar el trabajo de antes?", "opened_at": "start", "status": "open", "important": True},
        {"id": "how_far", "question": "¿cómo termina esta vida?", "opened_at": "start", "status": "open", "important": False, "intentional_unresolved": True},
    ]


def phase_specs(mode: str, ending_type: str) -> list[tuple[str, str]]:
    """Genera specs de fases dinámicas basadas en el vehículo."""
    if mode == "freeform":
        return [
            ("p1", "Parte 1: entra en la idea del usuario y déjala correr. Respeta el tema, el plazo y el reto. El ritmo puede saltar, frenar o irse de lado. Nada de equipo, empresa u oficio si la idea no lo es."),
            ("p2", f"Parte 2: la misma fantasía sigue, con una curva y un cierre {ending_type}. Que se sienta continua, no un formulario de pasos."),
        ]
    try:
        from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES
        
        vehicle_info = UNIVERSAL_VEHICLES.get(mode)
        if vehicle_info and mode not in ("sports_team", "business"):
            # Vehículo personalizado - estructura genérica adaptable
            vehicle_name = vehicle_info["vehicle"]
            acquisition = vehicle_info["acquisition"]
            progression = vehicle_info["progression"]
            
            return [
                ("p1", f"Parte 1: la película es {vehicle_name} ({acquisition}). Tú, en esa vida. Prohibido equipo de básquet, gimnasio, playoffs, estadio y dueño del equipo. El tiempo avanza (meses y años), nunca todo el día 1."),
                ("p2", f"Parte 2: sigue siendo {vehicle_name}. Una curva y este cierre: {ending_type}. El tiempo sigue avanzando. Cero deporte de equipo."),
            ]
    except ImportError:
        pass
    
    # Fallback tradicional
    if mode == "sports_team":
        return [
            ("p1", "Parte 1: entras al equipo (op oculta acquire_team, sin cifras) y la historia fluye. Puede haber silencio, una noche rara, un salto. Nada de planilla ni de campeonato anunciado."),
            ("p2", f"Parte 2: el tiempo corre con ritmo propio (advance_time, season_stretch si hace falta un año entero). La vida se mueve sin un checklist. Cierre {ending_type}."),
        ]
    return [
        ("p1", "Parte 1: empiezas (op oculta launch_company o acquire_team, sin cifras) y dejas que la historia encuentre su curva. Cero deporte."),
        ("p2", f"Parte 2: sigue con ritmo, un tropiezo que nace de lo anterior, y cierra en {ending_type}. Prohibido básquet, playoffs y campeonato."),
    ]


_FREEFORM_BLUEPRINT = """
La premisa del usuario ES la película. Adáptate y déjala fluir.
Si pide 7 días para gastar una fortuna, pueden ser saltos, una pausa a las tres de la mañana, un gasto absurdo y un silencio. Sigue siendo ese gasto, no una empresa.
Si pide otra fantasía, inventa la curva que esa fantasía pide. No la traduzcas a básquet, startup ni a una lista de pasos.
Español de tú. Escenas concretas. El final llega como escena, no como resumen.
Return ONLY JSON: blueprint + initial_world. En blueprint guarda user_premise con la idea original.
NO escribas synopsis.
""".strip()

_FREEFORM_BEATS = """
Beat planner. Obedeces la idea del usuario y le das ritmo.
Unas 6 a 8 escenas que se causan entre sí. Puedes frenar, saltar o irte un momento de lado si vuelve al hilo.
Ops invisibles y pocas: advance_time según el plazo real de la idea.
No uses acquire_team ni launch_company si la idea no es comprar o fundar algo.
El texto de event es vida, en tú, sin porcentajes.
Return ONLY JSON: {"beats":[...]}
""".strip()


def blueprint_system(mode: str) -> str:
    """Retorna el system prompt de blueprint adaptado al vehículo."""
    if mode == "freeform":
        from src.documentary.formats.check_als.plain_language import PUBLIC_EVENT_RULES, SIMPLE_STORY_BRIEF

        return SIMPLE_STORY_BRIEF + "\n" + _FREEFORM_BLUEPRINT + "\n" + PUBLIC_EVENT_RULES
    try:
        from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES, get_universal_vehicle_prompt
        
        vehicle_info = UNIVERSAL_VEHICLES.get(mode)
        if vehicle_info and mode not in ("sports_team", "business"):
            from src.documentary.formats.check_als.plain_language import PUBLIC_EVENT_RULES, SIMPLE_STORY_BRIEF

            return SIMPLE_STORY_BRIEF + "\n" + _generate_universal_blueprint(mode, vehicle_info) + "\n" + PUBLIC_EVENT_RULES
    except ImportError:
        pass
    
    from src.documentary.formats.check_als.plain_language import PUBLIC_EVENT_RULES, SIMPLE_STORY_BRIEF

    # Fallback tradicional
    if mode == "sports_team":
        return SIMPLE_STORY_BRIEF + "\n" + _BLUEPRINT_SPORTS + "\n" + PUBLIC_EVENT_RULES
    return SIMPLE_STORY_BRIEF + "\n" + _BLUEPRINT_BUSINESS + "\n" + PUBLIC_EVENT_RULES


def beats_system(mode: str) -> str:
    """Retorna el system prompt de beats adaptado al vehículo."""
    if mode == "freeform":
        from src.documentary.formats.check_als.plain_language import PUBLIC_EVENT_RULES, SIMPLE_STORY_BRIEF

        return SIMPLE_STORY_BRIEF + "\n" + _FREEFORM_BEATS + "\n" + PUBLIC_EVENT_RULES
    try:
        from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES
        
        vehicle_info = UNIVERSAL_VEHICLES.get(mode)
        if vehicle_info and mode not in ("sports_team", "business"):
            from src.documentary.formats.check_als.plain_language import PUBLIC_EVENT_RULES, SIMPLE_STORY_BRIEF

            return SIMPLE_STORY_BRIEF + "\n" + _generate_universal_beats(mode, vehicle_info) + "\n" + PUBLIC_EVENT_RULES
    except ImportError:
        pass

    from src.documentary.formats.check_als.plain_language import PUBLIC_EVENT_RULES, SIMPLE_STORY_BRIEF

    # Fallback tradicional
    if mode == "sports_team":
        return SIMPLE_STORY_BRIEF + "\n" + _BEATS_SPORTS + "\n" + PUBLIC_EVENT_RULES
    return SIMPLE_STORY_BRIEF + "\n" + _BEATS_BUSINESS + "\n" + PUBLIC_EVENT_RULES


def _generate_universal_blueprint(mode: str, vehicle_info: dict) -> str:
    """Genera blueprint system para vehículo personalizado."""
    vehicle_name = vehicle_info["vehicle"]
    acquisition = vehicle_info["acquisition"]

    return f"""
Eres Story Architect de Check. El espectador ES el protagonista (tú).
La película es SOLO esto: {vehicle_name}. El arranque es {acquisition}.
Prohibido convertirla en equipo, club, gimnasio, estadio, playoffs, básquet o dueño de un equipo.
Si es un canal, se graba, se sube, llegan comentarios, un video crece, aparece un patrocinio. Nada de cancha.
Español de tú. Unos años, con el tiempo adentro de las escenas. Sin planilla ni porcentajes.
Return ONLY JSON con blueprint (fiction_world.vehicle_name, city, opening, ending) e initial_world
(life.job, life.home, age). sports vacío. finance.team_debt = 0. team.attendance = 0.
NO escribas synopsis.
""".strip()


def _generate_universal_beats(mode: str, vehicle_info: dict) -> str:
    """Genera beats system para vehículo personalizado."""
    vehicle_name = vehicle_info["vehicle"]
    progression = vehicle_info["progression"]

    return f"""
Beat planner. La película sigue siendo {vehicle_name}. Progresión: {progression}.
6 a 8 escenas en tú. Cada una nace de la anterior. El tiempo salta meses o años (advance_time). El campo time NO puede ser "DAY 1" en todas.
Ops: launch_company con debt_assumed 0, advance_time, quit_job, move_home, sponsor_deal. Nada más.
Prohibido acquire_team, game_played, season_stretch, playoffs, championship, injury, coach.
Prohibido texto de equipo, club, gimnasio, estadio, jugadores, playoffs o dueño del equipo.
Si es un canal: títulos, visitas, suscriptores y una cifra, y además horas, nombres, audios, el camino y lo gastado. Inventa detalles distintos en cada escena.
Return ONLY JSON: {{"beats":[...]}}
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
