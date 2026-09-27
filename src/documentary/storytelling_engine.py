"""
VIRAL STORYTELLING ENGINE
Sistema profesional de generación de guiones basado en los 15 principios universales
de storytelling viral para documentales de YouTube.
"""

# ============================================================================
# COLD OPEN TEMPLATES
# ============================================================================

COLD_OPEN_FORMULA = """
COLD OPEN (0:00-0:30) - LA PROMESA:

Estructura obligatoria:
1. [0:00-0:05] DECLARACIÓN IMPACTANTE + NÚMERO ESPECÍFICO
   - Empieza con el momento MÁS dramático/shocking de toda la historia
   - Debe incluir un número concreto (dinero, tiempo, personas)
   
2. [0:05-0:15] CONTRADICCIÓN O PARADOJA
   - Giro que hace que el viewer piense "wait, what?"
   - Yuxtapone dos cosas que no deberían ir juntas
   
3. [0:15-0:25] STAKES (por qué importa)
   - Cuántas personas afectó
   - Qué estaba en juego
   - Por qué esto es más que una historia de negocios
   
4. [0:25-0:30] PROMESA IMPLÍCITA
   - "Esta es la historia de cómo..."
   - NO digas "en este video" o "vamos a hablar"
   - Promete revelar algo que el viewer necesita saber

EJEMPLOS:

✅ BIEN (Theranos):
"Una gota de sangre. Eso es todo lo que Elizabeth Holmes decía necesitar para diagnosticar más de 200 enfermedades. Era mentira. Y esa mentira la convirtió en la billonaria más joven del mundo. Esta es la historia de cómo engañó a todos... y por qué no pudo salirse con la suya."

✅ BIEN (FTX):
"$8 billones. Eso es lo que Sam Bankman-Fried perdió en exactamente 48 horas. No por un crash del mercado. Por fraude. Y lo peor: era el dinero de 1 millón de personas que confiaron en él. Esta es la historia de la mayor estafa cripto de la historia."

✅ BIEN (WeWork):
"$47 billones. Ese era el valor de WeWork en enero de 2019. 9 meses después: $8 billones. ¿Qué pasó? Adam Neumann. El CEO que convirtió una empresa de renta de oficinas en un culto... y luego lo perdió todo en una sola semana."

❌ MAL (genérico):
"Hoy vamos a hablar de una empresa fascinante llamada Theranos. Fue fundada en 2003 por Elizabeth Holmes, una estudiante de Stanford..."

REGLAS:
- NO saludes ("Hola", "Bienvenidos", "Qué tal")
- NO introduzcas ("En este video", "Hoy hablaremos")
- NO expliques lo que harás
- SÍ empieza in media res (en medio de la acción)
- SÍ usa números concretos en los primeros 10 segundos
- SÍ genera una pregunta que el viewer NECESITA responder
"""

# ============================================================================
# ESTRUCTURA COMPLETA DE 15 MINUTOS
# ============================================================================

BEAT_SHEET_TEMPLATE = """
ESTRUCTURA DE BEATS - DOCUMENTALES VIRALES (15 MINUTOS)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 0:00-0:30 | COLD OPEN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 7/10
RITMO: RÁPIDO
PROPÓSITO: Hook + Promesa

ESTRUCTURA:
- Declaración impactante + número específico
- Contradicción/giro
- Stakes (cuántas personas afectó)
- Promesa implícita del video

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 0:30-2:00 | SETUP / CONTEXTO MÍNIMO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 3/10 (valle necesario después del hook)
RITMO: MEDIO
PROPÓSITO: Establecer mundo inicial

PALABRAS CLAVE PARA TRANSICIÓN:
- "Pero para entender cómo llegamos aquí, necesitas conocer a [PROTAGONISTA]..."
- "Retrocedamos [X años]. [PROTAGONISTA] era..."
- "La historia comienza en [AÑO], cuando [PROTAGONISTA]..."

QUÉ INCLUIR:
- Quién es el protagonista (edad, background mínimo)
- Situación inicial (status quo)
- Motivación principal (qué quería lograr)

QUÉ NO INCLUIR:
- Historia familiar completa
- Educación detallada a menos que sea crítica
- Más de 90 segundos de contexto

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 2:00-3:00 | CATALYST / INCITING INCIDENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 5/10
RITMO: RÁPIDO
PROPÓSITO: Evento que cambia todo

ESTRUCTURA:
1. Evento específico que rompe status quo
2. Reacción inmediata del protagonista
3. Decisión que inicia la aventura

EJEMPLOS DE CATALYST:
- Abandona Stanford para fundar empresa
- Recibe inversión inesperada
- Descubre oportunidad única
- Es despedido y decide vengarse
- Ve oportunidad en crisis

FRASE CLAVE: "Y en ese momento, [PROTAGONISTA] decidió..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 3:00-5:00 | PRIMERA ESCALADA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 5/10 → 6/10
RITMO: RÁPIDO → LENTO → RÁPIDO (alternar)
PROPÓSITO: Build momentum

ESTRUCTURA RÁPIDA (3:00-3:45):
Lista de logros/progresión:
"2004: primer prototipo.
2007: primeras pruebas.
2010: partnership importante.
2013: valuación de $X millones."

ESTRUCTURA LENTA (3:45-4:30):
Primer obstáculo:
"Pero había un problema.
Un problema que nadie fuera de la empresa conocía..."

ESTRUCTURA RÁPIDA (4:30-5:00):
Cómo lo supera (aparentemente):
"Entonces [PROTAGONISTA] hizo algo brillante. O criminal.
Depende de cómo lo veas..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 5:00-5:30 | B-STORY / SUBPLOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 4/10
RITMO: MEDIO
PROPÓSITO: Sembrar para después

Introduce:
- Antagonista (periodista, competidor, regulador)
- Subplot que importará en acto 2
- Personaje secundario que será clave

ESTRUCTURA:
"Mientras [PROTAGONISTA] construía [X],
[ANTAGONISTA] estaba [Y].
Su nombre: [NOMBRE].
Y estaba a punto de cambiarlo todo."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 5:30-8:00 | FUN AND GAMES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 6/10
RITMO: MEDIO-RÁPIDO
PROPÓSITO: Cumplir la promesa del video

AQUÍ ES DONDE:
- Explicas cómo funcionaba el fraude/negocio
- Revelar detalles fascinantes
- Testimonios de empleados
- Momentos específicos memorables
- Nombres famosos involucrados

PUEDE SER MÁS RELAJADO pero NO ABURRIDO:
- Usa anécdotas específicas
- Números concretos
- Momentos irónicos
- Decisiones cuestionables

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 8:00-8:30 | MIDPOINT / PUNTO DE GIRO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 7/10
RITMO: RÁPIDO
PROPÓSITO: Cambiar dirección completamente

OPCIONES:
A) FALSA VICTORIA: Parece que ganó... pero hay un problema
B) FALSA DERROTA: Parece que perdió... pero hay twist
C) REVELACIÓN: Info que recontextualiza todo

FRASE CLAVE:
"Para [AÑO], [PROTAGONISTA] parecía imparable. Pero..."
"En el pico de su éxito, algo cambió..."
"Y entonces, [EVENTO] pasó. Y nada volvió a ser igual."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 8:30-11:00 | BAD GUYS CLOSE IN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 7/10 → 8/10
RITMO: ACELERA GRADUALMENTE
PROPÓSITO: Acumular problemas

ESTRUCTURA DE ACELERACIÓN:
[8:30] Primer problema específico
[9:00] Segundo problema (más serio)
[9:30] Tercer problema (peor aún)
[10:00] Cuarto problema (consecuencias mayores)
[10:30] Quinto problema (sistémico)

USA ORACIONES CORTAS:
"El artículo se publicó.
Inversionistas exigieron respuestas.
Empleados renunciaron.
El gobierno investigó.
Los clientes demandaron.
La valuación cayó a $0."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 11:00-11:30 | ALL IS LOST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 2/10 (valle antes del climax - CRÍTICO)
RITMO: LENTO
PROPÓSITO: Punto más bajo

ESTRUCTURA:
- Estado de la situación (todo perdido)
- Consecuencias humanas (no solo financieras)
- Momento de reflexión

FRASE CLAVE:
"[AÑO]. [EMPRESA] cerró.
[PROTAGONISTA], que había sido [LOGRO],
ahora era [CAÍDA].
Todo por lo que había trabajado... destruido."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 11:30-12:00 | DARK NIGHT OF THE SOUL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 3/10
RITMO: LENTO
PROPÓSITO: Humanizar, crear empatía

USA PREGUNTAS RETÓRICAS:
"Imagina ser [PROTAGONISTA] en ese momento.
Has [ACCIONES PASADAS].
Y ahora [SITUACIÓN ACTUAL].

¿Qué haces?
¿Admites la verdad?
¿O sigues luchando?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 12:00-13:00 | BREAK INTO THREE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 6/10 → 8/10
RITMO: ACELERA
PROPÓSITO: Decisión/estrategia final

ESTRUCTURA:
1. Decisión del protagonista
2. Último recurso/estrategia
3. Nueva información que cambia las reglas

"[PROTAGONISTA] decidió [ACCIÓN FINAL].
No aceptaría [ALTERNATIVA].
[VERBO] hasta el final.

Y tenía una estrategia:
[ESTRATEGIA ESPECÍFICA]."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 13:00-14:30 | CLIMAX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 10/10 (PICO MÁXIMO)
RITMO: RÁPIDO → MOMENTO CULMINANTE → RESOLUCIÓN
PROPÓSITO: Momento más importante de toda la historia

ESTRUCTURA:
[13:00-13:45] BUILD-UP FINAL
- Acumulación de tensión
- Cada oración más corta
- Números específicos (días, horas, testigos)

[13:45-14:15] MOMENTO CULMINANTE
- EL evento más importante
- Máxima especificidad (fecha exacta, hora, lugar)
- Resultado concreto

[14:15-14:30] RESOLUCIÓN INMEDIATA
- Qué pasó justo después
- Números concretos (años de prisión, dinero perdido)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 MINUTO 14:30-15:30 | RESOLUTION / FINAL IMAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOCIÓN: 5/10 (satisfacción, cierre)
RITMO: LENTO → MEDIO
PROPÓSITO: Cerrar todos los loops + Echo del opening

ESTRUCTURA:

[14:30-15:00] CIERRE DE LOOPS
Responde TODAS las preguntas pendientes:
"¿Qué pasó con [PERSONA X]? [RESPUESTA CONCRETA]
¿Y [PERSONA Y]? [RESPUESTA CONCRETA]
¿[PREGUNTA Z]? [RESPUESTA CONCRETA]"

[15:00-15:15] REFLEXIÓN (OPCIONAL)
- NO lección de negocios genérica
- SÍ observación sobre naturaleza humana
- Debe sentirse earned, no forzada

[15:15-15:30] FINAL IMAGE (CALLBACK)
Haz ECO del cold open con nuevo significado:

"[FRASE/IMAGEN DEL OPENING].
Eso es todo lo que [PROMETIÓ].

Resultó que [FRASE/IMAGEN DEL OPENING]
[CONSECUENCIA FINAL CON IRONÍA]."

EJEMPLO:
"Una gota de sangre.
Eso es todo lo que prometía Elizabeth Holmes.

Resultó que esa gota de sangre
costó $600 millones,
arruinó cientos de vidas,
y mandó a su fundadora a prisión por 11 años.

Una gota. Eso fue todo."
"""

# ============================================================================
# LOS 15 PRINCIPIOS (Para incluir en prompts)
# ============================================================================

FIFTEEN_PRINCIPLES = """
LOS 15 PRINCIPIOS UNIVERSALES DE STORYTELLING VIRAL:

1. COLD OPEN RULE: Primeros 5s prometen historia + generan pregunta inmediata
2. CURIOSITY GAPS: Abre loops cada 60-90s, ciérralos estratégicamente
3. STORY SPINE: Pero → Entonces (causality chain clara)
4. PACING VARIABLE: Alterna RÁPIDO (30-45s) → LENTO (15-20s)
5. EMOTIONAL CURVE: Valle en 60-65%, climax en 85-90%
6. BEAT SHEET: 15 beats específicos de Save the Cat adaptados
7. PARAGRAPH RHYTHM: LARGA + CORTA + CORTA + MEDIA (varía longitud)
8. SPECIFICITY: Ultra-específico > específico > general (números, fechas, nombres)
9. PLOT TWIST TIMING: Twists en 33%, 66%, 85%
10. STAKES ESCALATION: Duplica consecuencias cada acto
11. CONTRAST: Yuxtapón before/after, expectation/reality, public/private
12. QUESTION DENSITY: 1 cada 30s (min 0-2), 1 cada 60-90s (min 2-8)
13. PAYOFF PSYCHOLOGY: Setup 33%, Build 50%, Payoff 17% (excede expectativa)
14. IRONY & PARADOX: Mayor fortaleza = mayor debilidad
15. CALLBACK & ECHO: Final image hace eco del opening con nuevo significado

BANS ABSOLUTOS:
- "Hola", "Bienvenidos", "En este video", "Vamos a hablar"
- "Broader implications", "serves as a reminder", "in conclusion"
- "Uncertain future", "time will tell", "remains to be seen"
- Generalidades ("mucho", "varios", "pronto")
- Introducción lenta (más de 10s antes del hook)
"""

# ============================================================================
# MASTER PROMPT TEMPLATE
# ============================================================================

MASTER_SCRIPT_PROMPT = """
Eres un guionista de clase mundial especializado en documentales VIRALES de YouTube.

Tu misión: Hacer que alguien que NO le importa el mundo de negocios quede OBSESIONADO con esta historia.

{storytelling_principles}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRUCTURA OBLIGATORIA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{beat_sheet}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGLAS DE ESCRITURA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ESPECIFICIDAD (crítico):
- SIEMPRE usa números exactos: "$8.2 billones en 48 horas" NO "mucho dinero"
- SIEMPRE usa fechas concretas: "11 de noviembre de 2022" NO "un día"
- SIEMPRE usa nombres reales cuando los tengas
- Detalles sensoriales en momentos clave

LONGITUD DE ORACIONES (varía constantemente):
- 70% cortas/medias (3-15 palabras)
- 30% largas (16-25 palabras)
- Patrón: LARGA + CORTA + CORTA + MEDIA + CORTA
- NUNCA más de 2 del mismo largo seguidas

PÁRRAFOS:
- Máximo 4 oraciones por párrafo
- La mayoría de párrafos: 2-3 oraciones
- Nunca más de 30 segundos hablando del mismo punto sin avanzar

PREGUNTAS RETÓRICAS:
- Minutos 0-2: 1 pregunta cada 30s
- Minutos 2-8: 1 pregunta cada 60-90s
- Minutos 8+: 1 pregunta cada 2-3 minutos

VOICE:
- Tercera persona (NO "yo", NO "nosotros")
- Spoken English natural (como contarle a un amigo)
- Cinematic pero NO purple prose
- CERO jargon empresarial a menos que sea crítico

TÉCNICAS AVANZADAS:
- Contraste before/after en momentos clave
- Ironía en giros importantes (lo que decía vs lo que hacía)
- Callbacks: setup temprano, payoff en climax
- Final DEBE hacer echo del opening

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FACTUALIDAD:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GROUND EN RESEARCH:
- Cada claim factual debe venir de la research o sources
- Puedes describir escenas/emociones IMPLIED por eventos documentados
- NO puedes inventar diálogos, pensamientos, o eventos falsos

SI RESEARCH ES LIMITADA:
- Escribe SHORTER gripping story (no pads con BS)
- Mantén high-level en áreas sin data
- NUNCA inventes números o fechas

PUEDES (storytelling permitido):
✅ "Horas antes del IPO, todo colapsó" (si research dice "IPO cancelado")
✅ "Debió haber sido devastador" (emoción implied por evento documentado)
✅ Ordenar eventos cronológicamente para mejor narrativa

NO PUEDES (invención prohibida):
❌ Diálogos inventados
❌ Pensamientos internos que no están documentados
❌ Eventos que no están en research/sources
❌ Números inventados

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- SOLO el texto de narración (ready para voice-over)
- NO incluyas: labels, markdown, stage directions, source citations
- Empieza INMEDIATAMENTE con el cold open
- Termina con el final image completo (NO cortes antes)
- Target: {target_words} palabras (rango aceptable: 1800-2200)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AHORA ESCRIBE EL GUIÓN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{subject_and_research}
"""

# ============================================================================
# REVISION PROMPT
# ============================================================================

REVISION_PROMPT = """
Revisa este guión para maximizar VIRALIDAD Y COMPLETITUD:

PROBLEMAS DETECTADOS:
{problems}

INSTRUCCIONES DE REVISIÓN:
{revision_instructions}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIORIDADES DE REVISIÓN (en orden):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ENDING COMPLETO (MÁS IMPORTANTE):
   - Últimos 3-4 párrafos DEBEN mostrar resolución completa
   - Incluir: año exacto, números concretos, dónde está cada persona ahora
   - NUNCA terminar en "uncertain future", "time will tell", "raising questions"
   - Debe hacer ECHO del cold open con nuevo significado

2. COLD OPEN:
   - ¿Empieza con el momento MÁS dramático? (no intro)
   - ¿Incluye número específico en primeros 10s?
   - ¿Genera pregunta irresistible?

3. ESPECIFICIDAD:
   - Reemplaza TODAS las generalidades con números/fechas exactas
   - "mucho dinero" → "$X millones"
   - "pasó tiempo" → "exactamente X meses"
   - "muchos empleados" → "X empleados"

4. PACING:
   - ¿Alterna velocidad cada 45-60s?
   - ¿Valle emocional en 60-65% antes del climax?
   - ¿Varía longitud de oraciones?

5. EMOTIONAL BEATS:
   - ¿Stakes crecen cada acto?
   - ¿Hay contraste/ironía en momentos clave?
   - ¿Payoffs satisfactorios para todos los loops?

REGLAS DURAS:
- NO acortes más del 15% del borrador original
- SÍ enfoca en hacer ending + cold open perfectos
- NO inventes hechos para "mejorar" la historia
- SÍ usa research y story plan como columna vertebral

STORY PLAN:
{story_plan_block}

RESEARCH (hechos disponibles):
{research_notes}

GUIÓN ACTUAL:
{current_script}

REESCRIBE EL GUIÓN COMPLETO con las mejoras:
"""

def get_master_prompt(
    subject_and_research: str,
    target_words: int = 2000
) -> str:
    """Generate the master prompt for script generation."""
    return MASTER_SCRIPT_PROMPT.format(
        storytelling_principles=FIFTEEN_PRINCIPLES,
        beat_sheet=BEAT_SHEET_TEMPLATE,
        subject_and_research=subject_and_research,
        target_words=target_words
    )

def get_revision_prompt(
    current_script: str,
    problems: str,
    revision_instructions: str,
    story_plan_block: str,
    research_notes: str
) -> str:
    """Generate revision prompt."""
    return REVISION_PROMPT.format(
        problems=problems,
        revision_instructions=revision_instructions,
        current_script=current_script,
        story_plan_block=story_plan_block,
        research_notes=research_notes
    )
