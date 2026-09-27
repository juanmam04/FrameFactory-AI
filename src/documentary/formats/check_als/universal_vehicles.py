"""
UNIVERSAL VEHICLES - Check puede generar fantasías de CUALQUIER tema
No solo sports team o business - infinitos tipos de aspiraciones
"""

from typing import Any

# ============================================================================
# VEHICLE TEMPLATES - Infinitos tipos posibles
# ============================================================================

UNIVERSAL_VEHICLES = {
    # DEPORTES
    "sports_team": {
        "name": "Dueño de Equipo Deportivo",
        "vehicle": "equipo deportivo profesional",
        "acquisition": "comprar equipo en crisis",
        "progression": "temporadas",
        "metrics": ["asistencia", "record", "playoffs", "valuación"],
        "life_changes": ["renunciar oficina", "estadio propio", "sold out"],
    },
    
    # NEGOCIOS TRADICIONALES
    "business": {
        "name": "Fundador de Empresa",
        "vehicle": "empresa/startup",
        "acquisition": "lanzar o comprar",
        "progression": "años",
        "metrics": ["clientes", "revenue", "empleados", "valuación"],
        "life_changes": ["renunciar trabajo", "oficina propia", "contratos grandes"],
    },
    
    # MÚSICA
    "musician": {
        "name": "Músico Profesional",
        "vehicle": "carrera musical",
        "acquisition": "firmar primer contrato / lanzar primer álbum",
        "progression": "álbumes/giras",
        "metrics": ["streams", "conciertos", "tours sold out", "premios"],
        "life_changes": ["dejar trabajo día", "primera gira", "estadios llenos", "disco de oro"],
    },
    
    # CINE/CONTENIDO
    "filmmaker": {
        "name": "Director de Cine",
        "vehicle": "carrera como director",
        "acquisition": "primera película indie / primer corto viral",
        "progression": "películas/proyectos",
        "metrics": ["box office", "festivales", "premios", "presupuestos"],
        "life_changes": ["dejar publicidad", "primer largometraje", "estreno Cannes", "deal con estudio"],
    },
    
    # GASTRONOMÍA
    "chef": {
        "name": "Chef con Restaurante",
        "vehicle": "restaurante propio",
        "acquisition": "abrir primer restaurante",
        "progression": "años/locales",
        "metrics": ["reservas", "críticas", "estrellas Michelin", "expansión"],
        "life_changes": ["dejar cocina ajena", "restaurante lleno", "estrella Michelin", "cadena"],
    },
    
    # INFLUENCER/CREADOR
    "creator": {
        "name": "Creador de Contenido",
        "vehicle": "canal/marca personal",
        "acquisition": "primer video viral / primer sponsor",
        "progression": "años/hitos de suscriptores",
        "metrics": ["suscriptores", "views", "sponsors", "revenue por mes"],
        "life_changes": ["dejar trabajo", "YouTube full-time", "1M subs", "marca propia"],
    },
    
    # MODA
    "fashion_designer": {
        "name": "Diseñador de Moda",
        "vehicle": "marca de ropa propia",
        "acquisition": "primera colección / primera tienda",
        "progression": "colecciones/fashion weeks",
        "metrics": ["ventas", "boutiques", "fashion week", "celebs usando tu ropa"],
        "life_changes": ["dejar trabajar para otros", "atelier propio", "París Fashion Week", "celebs"],
    },
    
    # DEPORTES INDIVIDUALES
    "athlete": {
        "name": "Atleta Profesional",
        "vehicle": "carrera deportiva",
        "acquisition": "primer contrato profesional",
        "progression": "temporadas/torneos",
        "metrics": ["rankings", "torneos ganados", "sponsors", "récords"],
        "life_changes": ["dejar amateur", "primer gran torneo", "top 10 mundial", "endorsements"],
    },
    
    # ESCRITOR
    "author": {
        "name": "Escritor Bestseller",
        "vehicle": "carrera como autor",
        "acquisition": "primer libro publicado",
        "progression": "libros/años",
        "metrics": ["copias vendidas", "bestseller lists", "traducciones", "adaptaciones"],
        "life_changes": ["dejar trabajo día", "bestseller", "tour de libros", "película de tu libro"],
    },
    
    # TECH/GAMING
    "game_dev": {
        "name": "Desarrollador de Videojuegos",
        "vehicle": "estudio de juegos indie",
        "acquisition": "lanzar primer juego",
        "progression": "juegos/años",
        "metrics": ["descargas", "revenue", "premios", "publishers"],
        "life_changes": ["dejar AAA studio", "juego viral", "estudio propio", "deal con Steam/Epic"],
    },
    
    # BIENES RAÍCES
    "real_estate": {
        "name": "Inversionista Inmobiliario",
        "vehicle": "portfolio de propiedades",
        "acquisition": "primera propiedad para rentar",
        "progression": "propiedades/años",
        "metrics": ["propiedades", "ingreso mensual", "valuación portfolio", "edificios"],
        "life_changes": ["primera propiedad", "renunciar trabajo", "10 propiedades", "edificio completo"],
    },
    
    # ARTE
    "artist": {
        "name": "Artista Visual",
        "vehicle": "carrera como artista",
        "acquisition": "primera exhibición / primera venta importante",
        "progression": "exhibiciones/años",
        "metrics": ["ventas", "galerías", "coleccionistas", "museos"],
        "life_changes": ["dejar freelance", "galería propia", "coleccionista importante", "museo"],
    },
    
    # FOTOGRAFÍA
    "photographer": {
        "name": "Fotógrafo Profesional",
        "vehicle": "estudio/agencia de fotografía",
        "acquisition": "primer cliente grande / primer estudio",
        "progression": "años/clientes",
        "metrics": ["clientes", "campañas", "premios", "revenue anual"],
        "life_changes": ["dejar asistente", "estudio propio", "campaña internacional", "agencia"],
    },
    
    # PODCAST
    "podcaster": {
        "name": "Podcaster",
        "vehicle": "podcast exitoso",
        "acquisition": "primer episodio viral / primer sponsor",
        "progression": "temporadas/episodios",
        "metrics": ["oyentes", "sponsors", "charts", "libro/tour"],
        "life_changes": ["hobby a full-time", "sponsors grandes", "Top 10 charts", "media company"],
    },
    
    # BOXEO/MMA
    "fighter": {
        "name": "Peleador Profesional",
        "vehicle": "carrera en boxeo/MMA",
        "acquisition": "primer contrato profesional",
        "progression": "peleas/años",
        "metrics": ["record", "rankings", "títulos", "pay-per-view"],
        "life_changes": ["dejar amateur", "main card", "pelea por título", "campeón mundial"],
    },
    
    # MÚSICA ELECTRÓNICA
    "dj_producer": {
        "name": "DJ/Productor",
        "vehicle": "carrera como DJ/productor",
        "acquisition": "primer hit / primer festival",
        "progression": "años/tracks/tours",
        "metrics": ["streams", "festivales", "residencias", "label propio"],
        "life_changes": ["dejar bedroom", "Tomorrowland", "residencia Vegas", "label propio"],
    },
    
    # E-SPORTS
    "esports_player": {
        "name": "Jugador Profesional de E-Sports",
        "vehicle": "carrera en e-sports",
        "acquisition": "primer contrato con equipo",
        "progression": "temporadas/torneos",
        "metrics": ["torneos", "prize money", "sponsors", "stream viewers"],
        "life_changes": ["dejar estudios", "primer major", "top team", "StreamerHouse"],
    },
    
    # ARQUITECTURA
    "architect": {
        "name": "Arquitecto",
        "vehicle": "estudio de arquitectura",
        "acquisition": "primer proyecto importante / estudio propio",
        "progression": "proyectos/años",
        "metrics": ["proyectos", "premios", "clientes", "edificios icónicos"],
        "life_changes": ["dejar trabajar para otros", "estudio propio", "premio arquitectura", "edificio icónico"],
    },
}

# ============================================================================
# BEAT STRUCTURES POR TIPO DE VEHÍCULO
# ============================================================================

def get_vehicle_structure(vehicle_type: str) -> dict[str, Any]:
    """
    Retorna la estructura de beats específica para cada tipo de vehículo.
    Si el vehículo no existe, usa una estructura genérica.
    """
    
    vehicle_info = UNIVERSAL_VEHICLES.get(vehicle_type, {
        "name": "Profesional Exitoso",
        "vehicle": "carrera/proyecto",
        "acquisition": "primer gran paso",
        "progression": "años/hitos",
        "metrics": ["progreso", "reconocimiento", "éxito"],
        "life_changes": ["cambio significativo", "momento peak", "reconocimiento"],
    })
    
    # Estructura genérica de beats adaptable a cualquier vehículo
    return {
        "vehicle_info": vehicle_info,
        "beat_structure": {
            "cold_open": {
                "template": f"Tienes [EDAD] años. [SITUACIÓN ACTUAL]. "
                           f"Y acabas de descubrir que puedes [OPORTUNIDAD en {vehicle_info['vehicle']}].",
                "duration": "0:00-0:30",
                "words": "75-100",
            },
            "acquisition": {
                "template": f"[{vehicle_info['acquisition']}]. "
                           f"[NÚMEROS ESPECÍFICOS]. "
                           f"[PRIMER MOMENTO REAL].",
                "duration": "0:30-2:00",
                "words": "200-300",
                "payoff": "SIEMPRE incluir números/% si aplica",
            },
            "grind": {
                "template": "Los primeros meses/años son brutales. "
                           "[LISTA DE PROBLEMAS ESPECÍFICOS]. "
                           "Todavía [TRABAJO ANTERIOR] mientras construyes esto.",
                "duration": "2:00-4:00",
                "words": "300-400",
            },
            "first_win": {
                "template": f"[PRIMER {vehicle_info['metrics'][0]} IMPORTANTE]. "
                           f"Números concretos. "
                           f"Por primera vez sientes que tal vez funcione.",
                "duration": "4:00-5:30",
                "words": "250-350",
            },
            "progression": {
                "template": f"[PROGRESIÓN POR {vehicle_info['progression']}]. "
                           f"Cada {vehicle_info['progression'].split('/')[0]} con números específicos. "
                           f"Mix de wins y losses.",
                "duration": "5:30-8:00",
                "words": "400-500",
            },
            "life_changes": {
                "template": "Tu vida cambia. "
                           "[3+ CAMBIOS CONCRETOS de la lista life_changes]. "
                           "Momentos específicos con personas reales.",
                "duration": "8:00-9:30",
                "words": "250-350",
            },
            "peak": {
                "template": f"[MOMENTO PEAK específico del vehículo]. "
                           f"≥3 beats sensoriales: "
                           f"[lugar/status upgrade, reconocimiento, familia, momento masivo, lujo]. "
                           f"DESPUÉS: En papel vales [X]. En cuenta: [Y bajo].",
                "duration": "9:30-11:00",
                "words": "300-400",
                "critical": "IMPACTO ASPIRACIONAL - que el viewer ENVIDE",
            },
            "ending": {
                "template": "Tienes [EDAD FINAL] años. "
                           "[CONTRASTE: Hace X años estabas...]. "
                           "[ESCENA FINAL: oferta/oportunidad/decisión]. "
                           "Bloqueas. Mañana lo lees/decides.",
                "duration": "11:00-12:00",
                "words": "200-300",
            },
        },
        "forbidden": get_forbidden_elements(vehicle_type),
        "required_numbers": get_required_numbers(vehicle_type),
    }

def get_forbidden_elements(vehicle_type: str) -> list[str]:
    """Elementos que NO deben aparecer según el vehículo"""
    base_forbidden = [
        "moraleja",
        "lección",
        "aprendiste que",
        "el éxito se logra con",
        "CTA (suscríbete, like, comenta)",
        "voseo (vos, sos, tenés)",
        "fluff emocional (corazón late, emoción palpable)",
    ]
    
    # Prohibiciones específicas según vehículo
    specific_forbidden = {
        "sports_team": [],  # Puede tener todo deportivo
        "business": ["básquet", "playoffs", "campeonato", "estadio", "entrenador"],
        "musician": ["básquet", "playoffs", "empresa SaaS", "pitch deck"],
        "filmmaker": ["básquet", "startup pitch", "liga deportiva"],
        "chef": ["básquet", "playoffs", "rounds de inversión"],
        "creator": ["básquet", "campeonato", "liga deportiva"],
        # Agregar más según necesidad
    }
    
    return base_forbidden + specific_forbidden.get(vehicle_type, [
        "NO mezclar con otros vehículos sin sentido",
        "NO inventar elementos deportivos si no es sports",
    ])

def get_required_numbers(vehicle_type: str) -> list[str]:
    """Números que DEBEN aparecer según el vehículo"""
    base_numbers = [
        "Edad inicial (ej: 22 años)",
        "Edad final (ej: 27 años)",
        "Tu inversión inicial (si aplica)",
        "Tu % de ownership (si aplica)",
    ]
    
    vehicle = UNIVERSAL_VEHICLES.get(vehicle_type, {})
    metrics = vehicle.get("metrics", [])
    
    # Agregar métricas específicas del vehículo
    specific_numbers = [f"Números de: {', '.join(metrics)}"]
    
    return base_numbers + specific_numbers

# ============================================================================
# DETECTOR DE VEHÍCULO (expandido)
# ============================================================================

VEHICLE_KEYWORDS = {
    "sports_team": [
        "equipo de básquet", "equipo deportivo", "franquicia", "estadio",
        "dueño del equipo", "playoff", "liga deportiva",
    ],
    "musician": [
        "músico", "banda", "álbum", "disco", "concierto", "gira",
        "spotify", "streams", "disquera", "sello discográfico",
    ],
    "filmmaker": [
        "director", "película", "cine", "film", "corto", "largometraje",
        "festival", "guión", "producción audiovisual",
    ],
    "chef": [
        "chef", "restaurante", "cocina", "gastronom", "michelin",
        "estrella", "menú", "comensal",
    ],
    "creator": [
        "youtuber", "influencer", "creador de contenido", "canal de youtube",
        "suscriptores", "views", "contenido digital",
    ],
    "fashion_designer": [
        "diseñador de moda", "fashion", "colección", "pasarela",
        "fashion week", "atelier", "marca de ropa",
    ],
    "athlete": [
        "atleta", "deportista profesional", "competir", "torneo profesional",
        "olimpiadas", "mundial", "ranking mundial",
    ],
    "author": [
        "escritor", "autor", "libro", "novela", "bestseller",
        "editorial", "publicar libro",
    ],
    "game_dev": [
        "videojuego", "game dev", "desarrollador de juegos", "estudio indie",
        "steam", "juego indie",
    ],
    "real_estate": [
        "bienes raíces", "inmobiliaria", "propiedades", "inversión inmobiliaria",
        "departamentos", "rentar", "portfolio inmobiliario",
    ],
    "artist": [
        "artista visual", "pintor", "escultor", "galería de arte",
        "exhibición", "obra de arte",
    ],
    "photographer": [
        "fotógrafo", "fotografía profesional", "estudio fotográfico",
        "sesión fotográfica", "campaña publicitaria",
    ],
    "podcaster": [
        "podcast", "podcaster", "episodios", "oyentes",
        "spotify podcasts", "apple podcasts",
    ],
    "fighter": [
        "peleador", "boxeador", "MMA", "UFC", "pelea",
        "combate", "round", "knockout",
    ],
    "dj_producer": [
        "DJ", "productor musical", "beatmaker", "festival electrónico",
        "Tomorrowland", "residencia DJ",
    ],
    "esports_player": [
        "esports", "e-sports", "jugador profesional", "equipo gaming",
        "torneo gaming", "streamer profesional",
    ],
    "architect": [
        "arquitecto", "estudio de arquitectura", "proyecto arquitectónico",
        "diseño arquitectónico", "edificio",
    ],
}

def detect_vehicle_type(premise: str, topic: str = "", category: str = "") -> str:
    """
    Detecta el tipo de vehículo basado en keywords del premise/topic.
    Si no detecta nada específico, retorna 'business' como default.
    """
    text = f"{premise} {topic} {category}".lower()
    
    # Chequear cada tipo de vehículo
    for vehicle_type, keywords in VEHICLE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return vehicle_type
    
    # Default a business si no detecta nada
    return "business"

# ============================================================================
# GENERADOR DE PROMPT UNIVERSAL
# ============================================================================

def get_universal_vehicle_prompt(vehicle_type: str, premise: str = "") -> str:
    """
    Genera el prompt específico para cualquier tipo de vehículo.
    """
    structure = get_vehicle_structure(vehicle_type)
    vehicle_info = structure["vehicle_info"]
    beats = structure["beat_structure"]
    forbidden = structure["forbidden"]
    required = structure["required_numbers"]
    
    prompt = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VEHÍCULO: {vehicle_info['name']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FANTASÍA: El viewer SE IMAGINA siendo {vehicle_info['name']}.

VEHÍCULO: {vehicle_info['vehicle']}
PROGRESIÓN: {vehicle_info['progression']}
MÉTRICAS CLAVE: {', '.join(vehicle_info['metrics'])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRUCTURA DE BEATS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEAT 1 - COLD OPEN ({beats['cold_open']['duration']}):
{beats['cold_open']['template']}

BEAT 2 - ACQUISITION ({beats['acquisition']['duration']}):
{beats['acquisition']['template']}
{beats['acquisition'].get('payoff', '')}

BEAT 3 - GRIND ({beats['grind']['duration']}):
{beats['grind']['template']}

BEAT 4 - FIRST WIN ({beats['first_win']['duration']}):
{beats['first_win']['template']}

BEAT 5-7 - PROGRESSION ({beats['progression']['duration']}):
{beats['progression']['template']}

BEAT 8 - LIFE CHANGES ({beats['life_changes']['duration']}):
{beats['life_changes']['template']}
Cambios de vida típicos: {', '.join(vehicle_info['life_changes'])}

BEAT 9 - PEAK ({beats['peak']['duration']}):
{beats['peak']['template']}
⚠️ CRÍTICO: {beats['peak'].get('critical', '')}

BEAT 10 - ENDING ({beats['ending']['duration']}):
{beats['ending']['template']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NÚMEROS OBLIGATORIOS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join('- ' + n for n in required)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROHIBIDO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join('❌ ' + f for f in forbidden)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PREMISA DEL USUARIO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{premise if premise else '(Genera fantasía aspiracional basada en este vehículo)'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return prompt.strip()
