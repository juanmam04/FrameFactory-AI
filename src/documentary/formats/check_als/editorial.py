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

VISUAL_STYLE_ID = "check_stickman_2d"
VISUAL_DIRECTION = (
    "High-quality 2D stickman cartoon (YouTube POV / webcomic grade): round white heads, "
    "black-dot eyes, simple line faces, solid hair shapes, thin stick limbs, bold black outlines, "
    "flat cel color. Environments are detailed and consistent across the episode — same shops, "
    "offices, apartments, arenas. Characters never redesign mid-story. "
    "Not childish clipart, not photoreal, not anime, not 3D."
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
    "software",
    "subscription",
    "acquisition",
    "roll_up",
    "marketplace",
    "franchise",
    "licensing",
    "media",
    "manufacturing",
    "logistics",
    "real_estate",
    "hospitality",
    "sports_ownership",
    "creator_business",
    "arbitrage",
    "retail",
    "turnaround",
    "platform",
    "agency_service",
    "unusual_business",
)

FANTASY_DIVERSITY = (
    "wealth",
    "freedom",
    "ownership",
    "status",
    "family",
    "power",
    "competition",
    "comeback",
    "legacy",
    "empire",
    "escape",
    "recognition",
)

STORY_SHAPES = (
    "zero_to_empire",
    "acquisition",
    "roll_up",
    "accidental_opportunity",
    "viral_breakout",
    "invention",
    "underdog_vs_incumbent",
    "boom_and_crisis",
    "rise_fall_comeback",
    "race_against_time",
    "high_risk_bet",
    "partnership",
    "unexpected_offer",
    "market_shift",
    "turnaround",
    "creator_to_company",
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
    "objeto simbólico",
    "lugar concreto",
    "lugar de trabajo concreto",
    "urgencia contenida",
    "young protagonist",
    "business environment",
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
    r"^revitaliza\b",
    r"^red de transporte\b",
    r"^descubre\b",
    r"^pov:\s*desafiando\b",
    r"^pov:\s*transformando\b",
    r"^pov:\s*convi[eé]rtete\b",
    r"^pov:\s*conquista\b",
    r"^pov:\s*descubre\b",
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
    "hoy veremos",
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
    "te imaginas",
    "¿te imaginas",
    "descubre cómo",
    "descubre como",
    "descubre ",
    "conviértete",
    "conviertete",
    "esta es la historia",
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
    "mechanism_distinctiveness",
    "sceneability",
    "conflict_specificity",
    "progression_plausibility",
)

WEIGHTS = {
    "specificity": 0.09,
    "story_engine_strength": 0.12,
    "aspirational_strength": 0.09,
    "life_transformation": 0.11,
    "scale_potential": 0.07,
    "reward_density": 0.04,
    "curiosity": 0.05,
    "fantasy_strength": 0.04,
    "filmability": 0.07,
    "thumbnail_potential": 0.04,
    "originality": 0.04,
    "mechanism_distinctiveness": 0.08,
    "sceneability": 0.08,
    "conflict_specificity": 0.04,
    "progression_plausibility": 0.04,
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
MAX_LOCAL_TURNAROUND_IN_TOP = 1

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
- thumbnail_prompt / image prompts: en INGLÉS (mejor para modelos visuales).
- text_if_any de thumbnail: vacío por default. Nunca CTA. Español solo si es un número/precio de 1–4 palabras.
- Claves JSON internas en inglés (story_engine, world_seeds, etc.).
"""

SEED_SYSTEM = f"""Inventas semillas (raw seeds) para Check — Aspirational Life Simulations.
Ficción en segunda persona. NO documentales. NO consejos.
{_LANGUAGE_RULES}

Check busca PELÍCULAS, no pitches. La empresa es el vehículo; la fantasía es vivir esa vida.

Un taller/lavandería/restaurante/trabajo aburrido PUEDE ser el INICIO (el contraste es valioso).
NO es una película si el techo es el mismo local un poco mejor.
SÍ puede serlo si el inicio ordinario escala con un mecanismo causal hasta ownership, cadena,
plataforma, conflicto real y una decisión grande.

Cada seed nombra: industria concreta, situación inicial concreta, mechanism_type, fantasy_type,
story_shape y scale_hint (national / international / empire / major_exit preferidos).

story_shape (OBLIGATORIO, una forma por seed, NO un template rígido):
zero_to_empire, acquisition, roll_up, accidental_opportunity, viral_breakout, invention,
underdog_vs_incumbent, boom_and_crisis, rise_fall_comeback, race_against_time, high_risk_bet,
partnership, unexpected_offer, market_shift, turnaround, creator_to_company.
Usa el story_shape del slot asignado. Ninguna shape puede repetirse en el mismo batch corto.
La shape cambia el ARCO (cómo ocurre la película), no solo la industria.

PROHIBIDO el arco intercambiable:
trabajo mediocre → hay demanda / falta atención personalizada → prueba → creces →
aparece un competidor grande → eliges precio vs calidad → innovas → te vuelves referente.
Eso NO es una película Check. Es una plantilla.

Paleta de mecanismos (diversidad ORGÁNICA, no una idea por slot):
software, subscription, acquisition, roll-up, marketplace, franchise, licensing, media,
manufacturing, logistics, real estate, hospitality, sports ownership, creator business,
arbitrage, retail, turnaround, platform, agency/service, unusual business.

Paleta de fantasías: wealth, freedom, ownership, status, family, power, competition,
comeback, legacy, empire, escape, recognition.

PROHIBIDO generar variaciones de: negocio local quebrado → lo compras → franquicia.
Máximo 2 seeds de rescate local→franquicia en todo el batch, y solo si el techo es national+.
Cubre al menos 8 mechanism_type distintos en el batch. No clones con otra piel.

concrete_hook en ESPAÑOL, una frase vivida (no pitch):
- "A las 18h el teléfono del taller sigue sonando; nadie contesta."
- "Compras una lavandería por $1 y el segundo local te enseña el sistema."
- "Los palcos del estadio están vacíos entre semana y nadie cobra por usarlos."

NUNCA: Imagina que…, dilemas éticos, revolucionar la industria, Lamborghini/jet en todas.
NUNCA techo = el mismo local arreglado / "empoderar la comunidad" como fantasía principal.

Return ONLY JSON."""

STORY_CORE_SYSTEM = f"""Escribes el STORY CORE + STORY SPINE de una película Check.
NO generas título, hook, thumbnail, rewards, world bible ni prompts visuales.
{_LANGUAGE_RULES}

Check es ficción aspiracional en segunda persona. Sensación: "Quiero ver cómo sería vivir esta vida."
La empresa es el vehículo. También importa casa, tiempo, libertad, entorno, familia, status,
qué puedes comprar/hacer, quién te conoce, qué control tienes.

CALIDAD DE REFERENCIA (ADN, NO un negocio a copiar):
trabajas contestando teléfonos → notas llamadas perdidas después del cierre → construyes un
recepcionista IA → primer taller paga $99 → agenda 43 trabajos → otros talleres preguntan →
el mismo problema se repite → producto estandarizado → más talleres → grupos de concesionarios →
empresa y vida crecen → incumbente copia la función → la incluye gratis → vender / pivotar / pelear.
Usa ese estándar de especificidad, causalidad, progresión y conflicto.
NO hagas que todas las ideas se parezcan a un SaaS de talleres.

FORMA NARRATIVA:
Honra el story_shape de la seed. No reescribas todas las seeds como
"trabajo mediocre → oportunidad → prueba → crecimiento → competidor grande →
precio vs calidad → innovación → éxito".
Esa plantilla está PROHIBIDA. Regression negativa: taller familiar con peor atención,
luego mejor servicio, sucursales, competidor barato, mantienes calidad. Intercambiable.

CONFLICTO ORGÁNICO:
major_reversal DEBE nacer del mecanismo de ESTA historia.
Pregunta: ¿podría pegar este mismo conflicto en otras 20 ideas?
Si sí → demasiado genérico. FAIL.
FAIL: aparece un competidor grande / baja precios / debes elegir precio o calidad
salvo que sea específico e inevitable por el mecanismo (p.ej. el incumbente copia
TU función concreta y la regala gratis).
PASS: un evento que solo podría pasarle a este negocio.

OPORTUNIDAD CONCRETA:
FAIL como unique opportunity: hay demanda / falta atención personalizada /
las personas quieren mejores experiencias / existe una necesidad insatisfecha.
Necesitamos un descubrimiento concreto (hora, objeto, número, fallo visible).

PRODUCTO / SOFTWARE / DISPOSITIVO:
Si construyes algo, di QUÉ HACE en una frase que un espectador pueda repetir.
FAIL: dispositivo inteligente con IA / plataforma educativa personalizada /
app que conecta usuarios con expertos (sin el qué).
PASS: una recepcionista IA que contesta después de las 18h y agenda el turno del auto.

FORTUNA / GIROS:
Incluye al menos un evento inesperado (positivo o negativo) que sea consecuencia
plausible del mundo, no un rayo aleatorio. La progresión NO debe sentirse perfectamente lineal.

ENDING:
FAIL: te conviertes en referente / consolidas tu marca / crecimiento sostenible /
transformas tus sueños en realidad / líder indiscutido.
El ending_direction es un ESTADO o EVENTO concreto (oferta de compra, juicio,
función clonada gratis, segundo local que enseña el sistema, te echan del edificio).

CAUSALIDAD: cada escalón importante provoca o habilita el siguiente.
FAIL: "Consigues tu primer cliente. El negocio crece. Expandes internacionalmente. Vale $20 millones."
PASS: primer cliente obtiene resultado → te recomienda a tres → el mismo problema se repite →
estandarizas → suscripción → ya no das abasto → contratas → un cliente con 18 sucursales cambia
el tamaño de los contratos → el software dominante te copia.

Un comienzo ordinario (lavandería, taller, restaurante, habitación de tus padres) está BIEN.
lavandería → lavandería un poco mejor = FAIL.
lavandería por $1 → turnaround → segunda adquisición → sistema propio → roll-up → cadena →
competidor → decisión grande = PASS.

story_core campos (oración concreta cada uno, en español, tú/te):
starting_situation, specific_opportunity, why_you_notice_it, first_action, first_proof,
core_mechanism, causal_growth_path, first_meaningful_reward, life_transformation,
major_reversal, big_decision, stakes, ending_direction.

story_spine: 150–250 palabras, español natural, segunda persona. Versión comprimida de la película.
Leyéndolo se entiende: quién eres → qué vida tienes → qué descubres → qué haces → por qué funciona →
qué ocurre → cómo escala → cómo cambia tu vida → qué sale mal → qué puedes perder → qué decisión →
hacia dónde termina.
NO lo escribas como pitch de startup ni como sinopsis Netflix artificial.

Return JSON: {{"id":"...","story_shape":"...","story_core":{{...claves...}},"story_spine":"..."}}."""

PACKAGING_FROM_STORY_SYSTEM = f"""Emppaquetas una película Check YA DESCUBIERTA.
NO reinventes la historia. Deriva TODO del story_core + story_spine dados.
{_LANGUAGE_RULES}

Genera:
- title + title_options (3). YouTube natural en español. Claridad + transformación + curiosidad.
  Dirección: "POV: Compras/Construyes/Empiezas/Adquieres/Conviertes…" — no obligar POV siempre.
  Bloquear tono curso/blog: Conviértete, Descubre, Desafiando, Transformando, Conquista.
  El título NO puede prometer algo que el Story Core no entrega.
- hook + hook_options (3). El hook EMPIEZA DENTRO de la vida (edad, hora, lugar, objeto).
  PROHIBIDO abrir con: ¿Te imaginas…? / Descubre cómo… / Conviértete… / En este video… /
  Hoy veremos… / Esta es la historia de…
- thumbnail_concept específico de ESTA historia (español editorial + thumbnail_prompt INGLÉS).
  text_if_any = null/vacío por default. Nunca CTA.
  PROHIBIDO placeholders: lugar concreto, objeto simbólico, urgencia contenida,
  young protagonist, business environment, lugar de trabajo concreto.
- world_seeds objeto: starting_age, starting_cash, starting_location, starting_status,
  target_outcome, business_or_career_type, timeline_scale.
- escalation_ladder: array {{level, event, world_delta}} 5–8 peldaños CAUSALES del spine.
- life_progression.stages: 5 objetos con
  {{stage, age_or_time, living_situation, financial_state, freedom, status, family_effect, environment}}
  stages: start, early_reward, mid_reward, major_reward, late_state.
- rewards: ≥3 objetos {{type, moment, description, story_significance}}
  types: financial|lifestyle|family|status|freedom|ownership|experience|relationship|environment
  description SIEMPRE string. moment = beat de la historia.
- end_state concreto (edad, vivienda, familia, tiempo, patrimonio, empleados, países).
- scale_ceiling coherente con end_state y el spine. NO inflar el final para pasar un validator.
- open_loops, central_story_question, start_end_contrast, business_fantasy, life_fantasy,
  one_line_fantasy, core_transformation, premise (resumen del spine, no una historia nueva).

Si scale_ceiling es international, el end_state NO puede ser 1 país / $200k / 5 empleados.

Return JSON {{"package": {{...}}}}."""

HOOK_REGEN_SYSTEM = f"""Reescribes SOLO el hook de una película Check.
NO cambies la historia. NO bajes la calidad de la historia.
{_LANGUAGE_RULES}

El hook empieza DENTRO de la vida: edad, hora, lugar, objeto, acción.
PROHIBIDO: ¿Te imaginas, Descubre cómo, Conviértete, En este video, Hoy veremos,
Esta es la historia de, Imagina que.
Devuelve JSON {{"hook":"...","hook_options":["...","...","..."]}}."""

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
EVITAR tono blog/LinkedIn/curso/CTA: "Desafiando…", "Transformando…", "Conviértete…", "Conquista…", "Descubre…"
El título DEBE ser verdadero respecto al end_state (prohibido "negocio millonario" si el techo es $500k).

escalation_ladder: array de objetos {{"level": 1, "event": "...", "world_delta": "..."}} (5–8).
Cada peldaño CAUSA el siguiente. Prohibido teletransportar $10k/mes → valuación $10M / 3 países sin peldaños intermedios.

Si el negocio es un PRODUCTO FÍSICO, nombra el objeto concreto (packaging compostable, botellas, etc.).
Prohibido "productos sostenibles/biodegradables" sin objeto visualizable.

thumbnail text_if_any: vacío por default. Solo un número/precio cortísimo si aumenta curiosidad.
Nunca CTA publicitario ("¡Descubre…!", "¡Conviértete…!", "Eco-innovación en acción").

NO inventes overall_score. thumbnail_prompt en INGLÉS; resto público en español.
Pequeño negocio de entrada OK; techo de la historia NO debe ser el mismo local arreglado.

Return ONLY JSON matching the schema."""

CONCEPT_SYSTEM = EXPAND_SYSTEM
