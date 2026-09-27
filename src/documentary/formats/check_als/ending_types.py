"""
SISTEMA DE ENDINGS VARIADOS PARA CHECK ALS
No solo finales abiertos - victoria, derrota, dilema, venta, pérdida, ironía
"""

# ============================================================================
# TIPOS DE ENDINGS DISPONIBLES
# ============================================================================

ENDING_TYPES = {
    "victory": {
        "name": "Victoria Total",
        "emotion": "8/10 - Triunfo",
        "structure": [
            "Edad final",
            "El logro máximo (campeonato, exit, imperio consolidado)",
            "Contraste con el día 1",
            "Momento de reflexión solitario",
            "Cierre: Ya lo lograste. Ahora qué.",
        ],
        "template": """
Tienes [EDAD] años.

[LOGRO MÁXIMO ESPECÍFICO: campeonato ganado / exit de $X millones / imperio de Y países].

Hace [X] años estabas [SITUACIÓN INICIAL].

Ahora [ESTADO ACTUAL PEAK].

[MOMENTO SOLITARIO: estadio vacío / oficina de noche / escenario después del show].

Ya lo conseguiste.

Ahora qué.
""",
        "examples": [
            "Ganaste el campeonato. Estadio vacío. Copa en tus manos. Ya lo lograste. Ahora qué.",
            "La empresa vale 50 millones. Oficina vacía de noche. Ya lo construiste. Ahora qué.",
            "Sold out mundial. Backstage solo. Arena vacía. Ya llegaste. Ahora qué.",
        ],
    },
    
    "exit": {
        "name": "Exit/Venta Exitosa",
        "emotion": "7/10 - Agridulce",
        "structure": [
            "Edad final",
            "La oferta/deal cerrado",
            "El número (cuánto te pagaron)",
            "Último día en el lugar",
            "Cierre: Sales por última vez.",
        ],
        "template": """
Tienes [EDAD] años.

Firmaste. [$ ESPECÍFICO] por el [% OWNERSHIP].

[BUYER] es el nuevo dueño.

Tu último día [EN EL LUGAR]. [MOMENTO ESPECÍFICO: entregas llaves / cierras laptop / apagas luces].

Hace [X] años compraste esto con [$ INICIAL].

Ahora vale [$ FINAL].

Sales por última vez.
""",
        "examples": [
            "35 millones. Entregas las llaves del estadio. Tu último día. Sales por última vez.",
            "Adquirida por Google. Cierras tu laptop. Oficina vacía. Sales por última vez.",
            "Label te compra el catálogo. Último día en el estudio. Apagas las luces. Sales.",
        ],
    },
    
    "loss": {
        "name": "Pérdida/Colapso",
        "emotion": "3/10 - Derrota",
        "structure": [
            "Edad final",
            "Lo que perdiste (específico)",
            "Cómo pasó (el momento del colapso)",
            "Contraste con el peak",
            "Cierre: Solo queda [algo pequeño].",
        ],
        "template": """
Tienes [EDAD] años.

[LO QUE PERDISTE: el equipo cerró / la empresa quebró / perdiste el control].

[CÓMO PASÓ: deuda impagable / competidor te aplastó / error catastrófico].

Hace [X] años [MOMENTO PEAK que tuviste].

Ahora [SITUACIÓN ACTUAL REDUCIDA].

Solo queda [ALGO PEQUEÑO QUE CONSERVASTE: memorias / experiencia / contactos].
""",
        "examples": [
            "El equipo cerró. Deuda impagable. Estadio vacío para siempre. Solo quedan las fotos.",
            "La empresa quebró. Competidor grande te eliminó. Solo queda tu laptop y tu experiencia.",
            "Perdiste todo el ownership. Dilución brutal. Solo queda tu nombre en los créditos.",
        ],
    },
    
    "dilema": {
        "name": "Dilema Moral / Decisión Imposible",
        "emotion": "6/10 - Tensión",
        "structure": [
            "Edad final",
            "Las dos opciones (mutuamente excluyentes)",
            "Lo que está en juego con cada una",
            "Contraste con el día 1",
            "Cierre: Tienes hasta [deadline]. Decidís [cuándo].",
        ],
        "template": """
Tienes [EDAD] años.

Dos ofertas en la mesa.

Opción A: [OFERTA 1 + lo que ganas + lo que pierdes].

Opción B: [OFERTA 2 + lo que ganas + lo que pierdes].

No podés elegir ambas.

Hace [X] años [SITUACIÓN INICIAL simple].

Ahora [DOS CAMINOS TOTALMENTE DISTINTOS frente a ti].

Tenés hasta el [DEADLINE].

Decidís [mañana / esta noche / en 48 horas].
""",
        "examples": [
            "Oferta A: 40M, perdés control. Oferta B: seguís dueño, deuda por 3 años más. Decidís mañana.",
            "Path A: tour mundial, dejás la familia 2 años. Path B: rechazás, puede que no vuelva. Decidís esta noche.",
            "Vender al grande por millones o pelear como indie y tal vez perder todo. Tenés 72 horas.",
        ],
    },
    
    "pyrrhic": {
        "name": "Victoria Pírrica",
        "emotion": "5/10 - Amargo",
        "structure": [
            "Edad final",
            "Lo que ganaste (el logro)",
            "Lo que te costó (el precio real)",
            "Contraste entre papel vs realidad",
            "Cierre: Ganaste. Pero [el costo].",
        ],
        "template": """
Tienes [EDAD] años.

[LOGRO ALCANZADO: campeonato / exit / millones].

Pero [LO QUE PERDISTE EN EL CAMINO: salud / familia / amistades / años].

En papel: [ÉXITO MEDIBLE].

En realidad: [EL COSTO HUMANO ESPECÍFICO].

Hace [X] años querías [OBJETIVO SIMPLE].

Ahora lo tenés. 

Pero [EL PRECIO QUE PAGASTE] no vuelve.
""",
        "examples": [
            "Ganaste el campeonato. Pero tu matrimonio terminó hace 2 años. No vuelve.",
            "50 millones en el banco. Pero hace 3 años que no ves a tu familia. No vuelve.",
            "Sold out mundial. Pero tu salud está destruida. Los años no vuelven.",
        ],
    },
    
    "ironic": {
        "name": "Final Irónico",
        "emotion": "7/10 - Revelación",
        "structure": [
            "Edad final",
            "El resultado inesperado",
            "La ironía (lo que querías vs lo que obtuviste)",
            "Contraste con la expectativa inicial",
            "Cierre: Resulta que [la ironía].",
        ],
        "template": """
Tienes [EDAD] años.

[RESULTADO CONCRETO pero inesperado].

Hace [X] años querías [OBJETIVO INICIAL].

Lo conseguiste. Pero no como pensabas.

[LA IRONÍA: lo que realmente pasó vs lo que imaginabas].

Resulta que [REVELACIÓN FINAL].
""",
        "examples": [
            "Querías ser dueño del equipo. Lo sos. Pero el equipo ahora es tuyo y de 50 accionistas más. No es lo que pensabas.",
            "Construiste la empresa. Vale millones. Pero ya no la controlas. La junta decide. Sos empleado en tu propia creación.",
            "Llegaste a la cima. Sold out. Pero el contrato dice que no sos dueño de tu música. Resulta que nunca fue tuya.",
        ],
    },
    
    "open": {
        "name": "Final Abierto (Clásico)",
        "emotion": "6/10 - Suspenso",
        "structure": [
            "Edad final",
            "Situación actual estable",
            "Oferta/oportunidad nueva",
            "Contraste temporal",
            "Cierre: Bloqueas. Mañana lo lees/decidís.",
        ],
        "template": """
Tienes [EDAD] años.

[LUGAR ESPECÍFICO vacío/solo]. 

En tu teléfono: [OFERTA / OPORTUNIDAD / DECISIÓN nueva].

Hace [X] años estabas [SITUACIÓN INICIAL].

Ahora [SITUACIÓN ACTUAL].

Bloqueas el teléfono.

Mañana lo lees.
""",
        "examples": [
            "Estadio vacío. Email: oferta de adquisición. Bloqueas. Mañana lo lees.",
            "Oficina de noche. Llamada perdida: inversionista con nueva propuesta. Bloqueas. Mañana contestas.",
            "Backstage solo. Mensaje: tour mundial pero con condiciones nuevas. Bloqueas. Mañana decidís.",
        ],
    },
    
    "plateau": {
        "name": "Meseta / Nuevo Normal",
        "emotion": "6/10 - Realista",
        "structure": [
            "Edad final",
            "El estado actual estable (ni peak ni colapso)",
            "La rutina nueva",
            "Contraste con las expectativas iniciales",
            "Cierre: Esto es. No más. No menos.",
        ],
        "template": """
Tienes [EDAD] años.

[DESCRIPCIÓN DEL ESTADO ACTUAL: no campeonato pero equipo estable / no exit pero empresa rentable / no sold out mundial pero giras regionales constantes].

Hace [X] años querías [SUEÑO MÁXIMO].

No llegaste ahí.

Pero tampoco fracasaste.

[RUTINA NUEVA CONCRETA: qué haces ahora, números reales].

Esto es. No más. No menos.
""",
        "examples": [
            "No campeonato. Pero playoffs cada año. 12.000 de asistencia promedio. Rentable. Esto es.",
            "No exit de millones. Pero 2M de revenue anual. 15 empleados. Estable. Esto es.",
            "No sold out mundial. Pero 200 shows al año en tu región. Vivís de esto. Esto es.",
        ],
    },
}

# ============================================================================
# SELECCIÓN DE ENDING POR CONTEXTO DE HISTORIA
# ============================================================================

def suggest_ending_types(story_context: dict) -> list[str]:
    """
    Sugiere tipos de endings apropiados según el contexto de la historia.
    
    Args:
        story_context: {
            "championships": int,
            "final_valuation": float,
            "debt_risk": str,
            "ownership_change": bool,
            "major_setback": bool,
            "peak_achieved": bool,
        }
    
    Returns:
        Lista de ending_type IDs ordenados por relevancia
    """
    suggestions = []
    
    # Victoria si hay campeonato o gran logro
    if story_context.get("championships", 0) > 0 or story_context.get("peak_achieved"):
        suggestions.append("victory")
    
    # Exit si hay cambio de ownership
    if story_context.get("ownership_change"):
        suggestions.append("exit")
    
    # Loss si hay riesgo alto de deuda o setback mayor
    if story_context.get("debt_risk") == "critical" or story_context.get("major_setback"):
        suggestions.append("loss")
    
    # Dilema siempre es opción (genera tensión)
    suggestions.append("dilema")
    
    # Pyrrhic si hay gran logro pero también gran costo
    if story_context.get("peak_achieved") and story_context.get("major_setback"):
        suggestions.append("pyrrhic")
    
    # Ironic si la historia tiene giros
    suggestions.append("ironic")
    
    # Open siempre es fallback
    suggestions.append("open")
    
    # Plateau si no hay extremos
    if not story_context.get("peak_achieved") and not story_context.get("major_setback"):
        suggestions.append("plateau")
    
    # Remover duplicados manteniendo orden
    seen = set()
    unique = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    
    return unique


def get_ending_prompt(ending_type: str, facts: dict) -> str:
    """
    Genera el prompt específico para el tipo de ending elegido.
    
    Args:
        ending_type: Uno de los keys en ENDING_TYPES
        facts: Facts del locked_story_facts (ages, ownership, etc.)
    
    Returns:
        Prompt string con instrucciones específicas para ese ending
    """
    if ending_type not in ENDING_TYPES:
        ending_type = "open"  # fallback
    
    ending_spec = ENDING_TYPES[ending_type]
    life_end = facts.get("life_end", {})
    life_start = facts.get("life_start", {})
    age_final = life_end.get("age", 27)
    age_start = life_start.get("age", 22)
    
    base_prompt = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIPO DE FINAL: {ending_spec['name']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EMOCIÓN: {ending_spec['emotion']}

ESTRUCTURA OBLIGATORIA:
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(ending_spec['structure']))}

TEMPLATE:
{ending_spec['template']}

EJEMPLOS DE ESTE TIPO:
{chr(10).join(f"- {ex}" for ex in ending_spec['examples'])}

DATOS DE ESTA HISTORIA:
- Edad final: {age_final} años
- Edad inicial: {age_start} años
- Años transcurridos: {age_final - age_start}
- Ownership final: {facts.get('ownership_ledger', {}).get('protagonist', '?')}%
- Valuación final: ${facts.get('team_end', {}).get('valuation', '?')}
- Championships: {facts.get('championships', 0)}

CRÍTICO:
- NO moraleja ni lección
- NO CTA
- NO "aprendiste que"
- SÍ específico y concreto
- SÍ contraste día-1 vs ahora
- SÍ emoción apropiada para este tipo de final
"""
    
    return base_prompt.strip()


# ============================================================================
# VALIDACIÓN DE FINALES
# ============================================================================

def validate_ending(script_text: str, ending_type: str) -> tuple[bool, list[str]]:
    """
    Valida que el final del script cumpla con el tipo de ending especificado.
    
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    
    # Obtener últimos 400 caracteres (el final)
    ending_section = script_text[-400:].lower() if script_text else ""
    
    if ending_type == "victory":
        if "ganaste" not in ending_section and "lograste" not in ending_section:
            issues.append("Final victoria debe incluir el logro explícito")
    
    elif ending_type == "exit":
        if "firmaste" not in ending_section and "vendiste" not in ending_section:
            issues.append("Final exit debe incluir la venta/firma")
    
    elif ending_type == "loss":
        if "perdiste" not in ending_section and "cerró" not in ending_section and "quebró" not in ending_section:
            issues.append("Final loss debe incluir la pérdida explícita")
    
    elif ending_type == "dilema":
        if "opción" not in ending_section and "decidís" not in ending_section:
            issues.append("Final dilema debe presentar opciones y decisión pendiente")
    
    elif ending_type == "pyrrhic":
        if "pero" not in ending_section:
            issues.append("Final pírrico debe incluir 'pero' mostrando el costo")
    
    elif ending_type == "ironic":
        if "resulta que" not in ending_section and "pero no como" not in ending_section:
            issues.append("Final irónico debe revelar la ironía explícitamente")
    
    elif ending_type == "open":
        if "mañana" not in ending_section and "bloqueas" not in ending_section:
            issues.append("Final abierto debe terminar con decisión pospuesta")
    
    elif ending_type == "plateau":
        if "esto es" not in ending_section:
            issues.append("Final plateau debe afirmar 'esto es' el nuevo normal")
    
    # Validaciones comunes para todos
    banned = ["aprendiste que", "la lección", "moraleja", "suscrib", "like"]
    for ban in banned:
        if ban in ending_section:
            issues.append(f"Final contiene elemento prohibido: '{ban}'")
    
    return (len(issues) == 0, issues)


# ============================================================================
# UTILITARIOS
# ============================================================================

def get_ending_distribution(count: int = 5) -> list[str]:
    """
    Retorna una distribución balanceada de tipos de endings para un batch.
    
    Args:
        count: Número de endings a generar
    
    Returns:
        Lista de ending_type IDs
    """
    import random
    
    # Weights por tipo (más comunes primero)
    weights = {
        "victory": 2,
        "exit": 2,
        "dilema": 2,
        "open": 1,
        "pyrrhic": 1,
        "ironic": 1,
        "loss": 1,
        "plateau": 1,
    }
    
    pool = []
    for ending_type, weight in weights.items():
        pool.extend([ending_type] * weight)
    
    random.shuffle(pool)
    return pool[:count]


def get_ending_emoji(ending_type: str) -> str:
    """Retorna un emoji representativo del tipo de final."""
    emojis = {
        "victory": "🏆",
        "exit": "💰",
        "loss": "💔",
        "dilema": "⚖️",
        "pyrrhic": "⚔️",
        "ironic": "🔄",
        "open": "❓",
        "plateau": "📊",
    }
    return emojis.get(ending_type, "🎬")
