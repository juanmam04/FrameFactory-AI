"""Editorial invariants for Check ALS Concept Engine V2 (format pack — not engine)."""
from __future__ import annotations

CHANNEL_NAME = "Check — Aspirational Life Simulations"
CHANNEL_ONE_LINER = "Fantasías cinematográficas en segunda persona de vidas extraordinarias."
EDITORIAL_PRINCIPLE = "Progresión sobre consejos. Fantasía con suficiente realismo para sentirse vivible."

# Public content language (configurable later; Check default is Spanish)
CONTENT_LANGUAGE = "es"
NARRATION_LANGUAGE = "es"
TITLE_LANGUAGE = "es"
HOOK_LANGUAGE = "es"
SCRIPT_LANGUAGE = "es"
OVERLAY_LANGUAGE = "es"
# Visual model prompts stay English when that yields better generations
IMAGE_PROMPT_LANGUAGE = "en"

VISUAL_STYLE_ID = "check_2d_cinematic"
VISUAL_DIRECTION = (
    "2D cinematic illustrated storytelling: clean linework, expressive simple characters, "
    "detailed environments, strong lighting, readable silhouettes, consistent proportions. "
    "Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism."
)

DEFAULT_CATEGORIES = (
    "entrepreneurship",
    "wealth",
    "career",
    "acquisition",
    "empire",
    "technology",
    "freedom",
    "power",
    "sports_business",
    "comeback",
    "rise_and_fall",
)

MECHANISM_DIVERSITY = (
    "subscription",
    "acquisition",
    "turnaround",
    "arbitrage",
    "marketplace",
    "franchise",
    "real_estate",
    "licensing",
    "media",
    "sports_ownership",
    "manufacturing",
    "logistics",
    "creator_economy",
    "software",
    "physical_retail",
    "hospitality",
    "unusual_local_business",
)

FANTASY_DIVERSITY = (
    "wealth",
    "freedom",
    "status",
    "family",
    "revenge_comeback",
    "ownership",
    "competition",
    "empire",
    "escape",
    "legacy",
)

STORY_ENGINE_KEYS = (
    "specific_opportunity",
    "why_protagonist_notices_it",
    "initial_action",
    "first_customer_or_break",
    "business_or_progress_mechanism",
    "why_it_works",
    "growth_mechanism",
    "first_proof",
    "first_major_reward",
    "primary_opposition",
    "mid_story_complication",
    "major_threat",
    "big_decision",
    "stakes",
    "possible_cost",
    "escalation_path",
    "endgame",
)

MECHANISM_REQUIRED = (
    "opportunity",
    "mechanism",
    "first_action",
    "growth_engine",
    "major_threat",
    "stakes",
)

MECHANISM_FIELD_MAP = {
    "opportunity": "specific_opportunity",
    "mechanism": "business_or_progress_mechanism",
    "first_action": "initial_action",
    "growth_engine": "growth_mechanism",
    "major_threat": "major_threat",
    "stakes": "stakes",
}

# Vague / filler (ES + EN). Prefer semantic concreteness over keyword lists alone.
VAGUE_PHRASES = (
    # ES
    "oportunidad",
    "startup",
    "gran empresa",
    "desafíos",
    "decisiones difíciles",
    "contratiempos inesperados",
    "dilemas éticos",
    "sacrificios personales",
    "app revolucionaria",
    "cambiar el mundo",
    "cambia el mundo",
    "única en la vida",
    "trabajar duro",
    "eventualmente",
    "construir algo grande",
    "competidores poderosos",
    "dilemas morales",
    "enfrentar la adversidad",
    "contra todo pronóstico",
    "navegar los desafíos",
    "embarcarte en un viaje",
    "cambiará tu vida para siempre",
    "imperio tecnológico",
    "marca global",
    "de cero a héroe",
    "grandes corporaciones",
    "revolucionar la industria",
    "la próxima gran cosa",
    "desafíos inesperados",
    # EN (legacy / mixed output)
    "opportunity",
    "big company",
    "challenges",
    "tough decisions",
    "unexpected setbacks",
    "ethical dilemmas",
    "personal sacrifices",
    "revolutionary app",
    "changes the world",
    "change the world",
    "once-in-a-lifetime",
    "work hard",
    "eventually make",
    "build something big",
    "powerful competitors",
    "moral dilemmas",
    "face adversity",
    "against all odds",
    "unexpected challenges",
    "navigate challenges",
    "tech empire",
    "global brand",
    "from zero to hero",
    "revolutionary",
    "disrupt the industry",
    "next big thing",
)

CLICHE_PHRASES = (
    # ES
    "app revolucionaria",
    "cambiar el mundo",
    "cambia el mundo",
    "imperio tecnológico",
    "marca global",
    "de cero a héroe",
    "dilemas éticos",
    "contratiempos inesperados",
    "grandes corporaciones se defienden",
    "oportunidad única en la vida",
    "única en la vida",
    "revolucionar la ia",
    "revolucionar la industria",
    "libertad financiera para todos",
    "futuro sostenible",
    "trabajar duro y eventualmente",
    "embarcarte en un viaje",
    "contra todo pronóstico",
    "cambiará tu vida para siempre",
    "navegar los desafíos",
    "enfrentarte a dilemas éticos",
    "construir un imperio desde cero",
    # EN
    "revolutionary app",
    "change the world",
    "changes the world",
    "tech empire",
    "global brand",
    "from zero to hero",
    "ethical dilemmas",
    "unexpected setbacks",
    "once-in-a-lifetime",
    "revolutionize ai",
    "work hard and eventually",
)

THUMBNAIL_PLACEHOLDERS = (
    "key story location",
    "one symbolic object",
    "before vs after stakes",
    "young you, mid-transformation",
    "simple two-zone contrast",
    "cinematic contrast",
    "simplified",
    "medium shot",
    "tension",
    "ubicación clave de la historia",
    "un objeto simbólico",
    "antes vs después",
    "tú joven, a mitad de la transformación",
    "contraste simple de dos zonas",
    "contraste cinematográfico",
    "simplificado",
    "plano medio",
    "tensión",
)

BANNED_TITLE_PATTERNS = (
    r"somehow\s+you",
    r"\byou\s+chase\b",
    r"pov:\s*you\s+somehow",
    r"de alguna manera",
    r"\bpersigues\b",
    r"pov:\s*t[uú]\s+de alguna manera",
    r"^desafiando\b",
    r"^transformando\b",
    r"^convi[eé]rtete\b",
    r"^conquista\b",
    r"^tu camino\b",
    r"^el arte de\b",
    r"^c[oó]mo\b",
    r"^pov:\s*desafiando\b",
    r"^pov:\s*transformando\b",
    r"^pov:\s*convi[eé]rtete\b",
    r"^pov:\s*conquista\b",
)

BANNED_HOOK_OPENERS = (
    "today we're going to",
    "in this video",
    "imagine if",
    "welcome back",
    "hey guys",
    "what's up",
    "let me tell you",
    "hoy vamos a",
    "en este video",
    "imagina si",
    "imagina que",
    "imagina ",
    "imagínate si",
    "imagínate que",
    "imagínate ",
    "imaginate si",
    "imaginate que",
    "imaginate ",
    "bienvenidos de nuevo",
    "hola a todos",
    "qué tal",
    "dejame contarte",
    "déjame contarte",
)

SCORE_KEYS = (
    "specificity",
    "story_engine_strength",
    "aspirational_strength",
    "life_transformation",
    "scale_potential",
    "reward_density",
    "curiosity",
    "fantasy_strength",
    "filmability",
    "thumbnail_potential",
    "originality",
)

WEIGHTS = {
    "specificity": 0.12,
    "story_engine_strength": 0.12,
    "aspirational_strength": 0.14,
    "life_transformation": 0.12,
    "scale_potential": 0.11,
    "reward_density": 0.08,
    "curiosity": 0.08,
    "fantasy_strength": 0.07,
    "filmability": 0.06,
    "thumbnail_potential": 0.05,
    "originality": 0.05,
}

TITLE_SCORE_KEYS = (
    "clarity",
    "curiosity",
    "fantasy",
    "scale",
    "instant_understanding",
    "promise_match",
)

SPECIFICITY_THRESHOLD = 6
MIN_OPEN_LOOPS = 2
MAX_OPEN_LOOPS = 5
MIN_LADDER_STEPS = 5
MIN_REWARDS = 3
MAX_LOCAL_TURNAROUND_IN_TOP = 2

ELIGIBILITY_GATES = (
    "has_specific_opportunity",
    "has_specific_mechanism",
    "has_growth_engine",
    "has_major_threat",
    "has_stakes",
    "has_story_question",
    "has_valid_hook",
    "has_valid_world_seeds",
    "category_matches",
    "coherence_pass",
    "has_story_engine",
    "specificity_ok",
    "thumbnail_concrete",
    "has_aspirational_transformation",
    "has_life_progression",
    "has_scale_progression",
    "has_visible_rewards",
)

CATEGORY_CUES: dict[str, tuple[str, ...]] = {
    "technology": (
        "software", "saas", "app", "código", "codigo", "ia", "ai", "plataforma", "api", "desarrollador",
    ),
    "sports_business": (
        "equipo", "franquicia", "estadio", "liga", "dueño", "dueño", "atleta", "club", "plantilla",
        "team", "stadium", "owner",
    ),
    "acquisition": (
        "compras", "adquieres", "compra", "deuda", "$1", "adquisición", "adquisicion", "buy", "bought",
    ),
    "empire": ("imperio", "cadena", "locales", "expandes", "franquicia", "portfolio", "empire", "chain"),
    "hospitality": ("hotel", "motel", "restaurante", "hospitalidad", "habitaciones", "rooms"),
    "comeback": ("regreso", "reconstruyes", "perdiste", "quiebra", "fallaste", "vuelves", "comeback", "rebuild"),
    "rise_and_fall": ("colapso", "lo pierdes todo", "caída", "caida", "sobreendeudas", "crash", "collapse"),
    "career": ("trabajo", "ascenso", "carrera", "sueldo", "empleador", "oficina", "socio", "job", "salary"),
    "wealth": ("patrimonio", "millones", "efectivo", "riqueza", "dinero", "fortuna", "net worth", "million"),
    "freedom": ("jubilar", "libertad", "renuncias", "escapar", "independiente", "tiempo", "retire", "freedom"),
    "power": ("control", "consejo", "poder", "influencia", "política", "politica", "alcalde", "board"),
    "entrepreneurship": (
        "cliente", "negocio", "vendes", "producto", "servicio", "lanzas", "customer", "business", "sell",
    ),
}

CATEGORY_MISMATCH: dict[str, tuple[str, ...]] = {
    "technology": ("motel", "imperio hotelero", "hospitalidad", "hotel empire", "highway motel"),
    "acquisition": (
        "jubilas a tus padres",
        "agencia a base de esfuerzo",
        "solo negocio de servicios",
        "retire your parents",
        "service business only",
    ),
    "sports_business": (
        "atleta aspirante",
        "alfombra roja",
        "solo fama deportiva",
        "aspiring athlete",
        "red carpet",
    ),
}

_LANGUAGE_RULES = """
IDIOMA (OBLIGATORIO):
- Todo el contenido público nace en ESPAÑOL: premise, fantasy, story_engine, titles, hook,
  open_loops, central_story_question, starting/end state, thumbnail editorial fields (main_visual, etc.).
- NO generes en inglés para después traducir. Piensa y escribe directamente en español de YouTube.
- Español internacional/natural (LatAm + España). Usa tú/te/tu/tienes/eres. NO uses vos como default.
- Evita español de traducción: "embarcarte en un viaje", "contra todo pronóstico",
  "cambiará tu vida para siempre", "navegar los desafíos", "oportunidad única en la vida",
  "revolucionar la industria", "dilemas éticos", "construir un imperio desde cero" como relleno.
- La historia puede ocurrir en cualquier ciudad del mundo. La MONEDA sigue al mundo de la historia
  (si es EE.UU.: $312, $99/mes, $10 millones). No conviertas todo a euros automáticamente.
- thumbnail_prompt / image prompts: en INGLÉS (mejor para modelos visuales). text_if_any de thumbnail: español.
- Claves JSON internas en inglés (story_engine, world_seeds, etc.).
"""

SEED_SYSTEM = f"""Inventas semillas (raw seeds) para Check — Aspirational Life Simulations.
Ficción en segunda persona. NO documentales. NO consejos.
{_LANGUAGE_RULES}

Check NO es un canal de turnarounds de small business que se quedan locales.
Un taller/lavandería/restaurante puede ser el INICIO, pero la vida final debe sentirse extraordinaria:
escala nacional+, ownership, libertad, status, imperio, exit — no solo "negocio rentable del barrio".

Cada seed debe nombrar: industria concreta, problema concreto, mecanismo
(subscription, acquisition, turnaround, arbitrage, marketplace, franchise, real estate,
licensing, media, sports ownership, manufacturing, logistics, creator economy, software,
retail, hospitality, unusual local business), fantasía (wealth, freedom, status, family,
comeback, ownership, competition, empire, escape, legacy) y scale_hint
(national / international / empire / major_exit preferidos).

concrete_hook en ESPAÑOL:
- "En un taller se pierden trabajos tras las 18h; vendes IA a $99/mes y apuntas a concesionarios nacionales."
- "Compras lavandería por $1; el techo es franquiciar 120 locales y pelear con una cadena nacional."
- "Palcos vacíos → licencias prepago → ownership minoritario de un club."

Diversifica mecanismos. Evita batches solo de rescates locales.
NUNCA: Imagina que…, dilemas éticos, revolucionar la industria, Lamborghini/jet en todas.

Return ONLY JSON."""

EXPAND_SYSTEM = f"""Expandes una seed de Check a un Concept Package COMPLETO (Fase 1.6 Aspirational Engine).
{_LANGUAGE_RULES}

Emoción: "¿Querría vivir esta transformación?"
Necesitas las TRES: historia específica + fantasía aspiracional + escalera de progresión.

OBLIGATORIO además del story_engine:
- escalation_ladder: 5–8 niveles concretos (salario mínimo → MRR → empleados → escala nacional → amenaza gigante…)
- life_progression: {{start, early_reward, mid_reward, major_reward, late_state}} listas de bullets concretos
- rewards: ≥3 objetos {{type, description, story_beat}} types: financial|lifestyle|family|status|freedom|ownership|experience|relationship|environment
- scale_ceiling: local|regional|national|international|category_leader|major_exit|empire
  (preferir national+; local solo si la life fantasy es extraordinaria)
- start_end_contrast: {{start, end}} contraste legible en segundos
- end_state CONCRETO (edad, patrimonio, valuación, empleados, países, padres, vivienda, control del tiempo)
  NUNCA "dueño exitoso" / "successful business owner"
- business_fantasy / life_fantasy: frases cortas de qué se desea construir vs qué vida se desea vivir

Títulos: YouTube natural en español. Preferir "POV: Construyes/Compras/Conviertes/Empiezas/Heredas/Pierdes…"
EVITAR tono blog/LinkedIn/curso: "Desafiando…", "Transformando…", "Conviértete…", "Conquista…"

NO inventes overall_score. thumbnail_prompt en INGLÉS; resto público en español.
Pequeño negocio de entrada OK; techo de la historia NO debe ser el mismo local arreglado.

Return ONLY JSON matching the schema."""

CONCEPT_SYSTEM = EXPAND_SYSTEM
