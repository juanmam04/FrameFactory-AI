"""Concrete Spanish offline fixtures for Check Concept Engine V2."""
from __future__ import annotations

from typing import Any

CONCRETE_FIXTURES: list[dict[str, Any]] = [
    {
        "id": "mechanic-ai-receptionist",
        "premise": (
            "A los 20 trabajas en la recepción de un taller mecánico. Cada noche después de las 18h "
            "las llamadas quedan sin contestar y los clientes reservan en otro lado. Construyes una "
            "recepcionista IA tosca en un fin de semana y convences al dueño de pagarte $99/mes si "
            "agenda citas. Agenda 43 trabajos el primer mes. Vendes el mismo sistema a cinco talleres "
            "cercanos, luego a cincuenta, luego a grupos de concesionarios. Tres años después tu "
            "software maneja millones de llamadas — y la plataforma más grande de talleres copia la "
            "función y la regala gratis."
        ),
        "title": "POV: Conviertes llamadas perdidas en $100 millones",
        "title_options": [
            {"text": "POV: Conviertes llamadas perdidas en $100 millones"},
            {"text": "POV: Tu proyecto de $99 se vuelve software de talleres"},
            {"text": "POV: Construyes un imperio de reservas desde un mostrador"},
        ],
        "one_line_fantasy": "De chico del mostrador sin sueldo a dueño del software que todo taller necesita.",
        "starting_state": "EDAD 20 · CAJA $180 · recepción de taller · desconocido",
        "end_state": (
            "EDAD 24 · patrimonio $18M · empresa $48M valuation · 140 empleados · "
            "operaciones en 3 países · padres sin hipoteca · controlas tu horario"
        ),
        "core_transformation": "Recepcionista → fundador peleando contra quien clonó tu producto",
        "story_category": "entrepreneurship",
        "ending_direction": "victory_with_cost",
        "scale_ceiling": "national",
        "business_fantasy": "Poseer el software que todo taller del país necesita y pelear contra el incumbente.",
        "life_fantasy": "Dejar el mostrador, pagar la casa de tus padres y controlar tu tiempo mientras construyes.",
        "escalation_ladder": [
            "Contestas teléfonos en un taller por salario mínimo.",
            "El dueño paga $99/mes si agendas trabajos reales.",
            "5 talleres cercanos usan el sistema.",
            "Llegas a $20k MRR y dejas el mostrador.",
            "Contratas a tus primeros empleados de soporte.",
            "Grupos de concesionarios adoptan el producto a escala nacional.",
            "Tu empresa supera $5M ARR.",
            "El gigante de gestión de talleres copia la función y la regala gratis.",
        ],
        "life_progression": {
            "start": ["casa de tus padres", "$180", "laptop vieja", "sin status", "sin autonomía"],
            "early_reward": ["primer mes con 43 citas agendadas", "primer $99 recurrente"],
            "mid_reward": ["dejas el mostrador", "alquilar tu primer departamento"],
            "major_reward": ["pagas la hipoteca de tus padres", "primera oficina", "viajas a cerrar deals"],
            "late_state": [
                "independencia financiera",
                "ownership mayoritario",
                "entorno de alto status",
                "libertad sobre tu tiempo",
            ],
        },
        "rewards": [
            {"type": "freedom", "description": "Dejas el trabajo del mostrador", "story_beat": "first_major_reward"},
            {"type": "family", "description": "Pagas la hipoteca de tus padres", "story_beat": "major_reward"},
            {"type": "ownership", "description": "Mantienes equity frente a la oferta del incumbente", "story_beat": "big_decision"},
            {"type": "status", "description": "Pasas de recepcionista a CEO reconocido en la industria", "story_beat": "late_state"},
            {"type": "financial", "description": "Patrimonio de ocho cifras bajo presión competitiva", "story_beat": "endgame"},
        ],
        "start_end_contrast": {
            "start": "20 años · habitación de infancia · $180 · nadie conoce tu nombre",
            "end": "24 años · empresa nacional · $18M patrimonio · 140 empleados · padres retirados · libertad de horario",
        },
        "central_story_question": (
            "¿Puedes mantener viva la empresa cuando el gigante contra el que compites "
            "regala tu producto entero gratis?"
        ),
        "open_loops": [
            "¿El primer taller pagará de verdad $99/mes?",
            "¿Hasta dónde escala una herramienta de un solo taller?",
            "¿Qué pasa cuando el incumbente te nota?",
            "¿Vendes o peleas?",
        ],
        "story_engine": {
            "specific_opportunity": "Los talleres pierden trabajos después de las 18h porque nadie contesta el teléfono",
            "why_protagonist_notices_it": "Contestas todo el día y ves al dueño cerrar mientras el teléfono sigue sonando",
            "initial_action": "Construyes una recepcionista IA tosca en un fin de semana que contesta y agenda citas",
            "first_customer_or_break": "El dueño de tu taller acepta $99/mes si agenda trabajos reales",
            "business_or_progress_mechanism": "SaaS de suscripción mensual para reservas fuera de horario en talleres",
            "why_it_works": "Los talleres ya pierden ingresos por llamadas perdidas; $99 es más barato que un trabajo de frenos",
            "growth_mechanism": "Referidos entre dueños y luego grupos multi-local de concesionarios",
            "first_proof": "43 trabajos agendados el primer mes",
            "first_major_reward": "Cinco talleres de pago, luego cincuenta: suficiente para dejar el mostrador",
            "primary_opposition": "Dueños que desconfían de la 'IA' y quieren recepción humana",
            "mid_story_complication": "Una mala transcripción agenda el auto equivocado y casi pierdes la cuenta piloto",
            "major_threat": "La plataforma más grande de gestión de talleres copia la función y la incluye gratis",
            "big_decision": "Vender al incumbente o levantar capital y pelear en flujo de trabajo especializado",
            "stakes": "Tus usuarios, tu identidad como fundador y si los talleres independientes siguen teniendo opción",
            "possible_cost": "Años de trabajo absorbidos en la página de producto de otro",
            "escalation_path": "1 taller → 5 → 50 → concesionarios → volumen nacional → guerra del clon gratis",
            "endgame": "Sobrevivir como capa especializada o ser comprado en peores condiciones",
        },
        "hook": (
            "Tienes 20 años y contestas el teléfono en un taller mecánico.\n\n"
            "A las 18:00 ves al dueño cerrar la puerta.\n\n"
            "El teléfono sigue sonando.\n\n"
            "Nadie contesta.\n\n"
            "Para el lunes, tres de esas llamadas ya reservaron en otro lado."
        ),
        "world_seeds": {
            "starting_age": 20,
            "starting_cash": "$180",
            "starting_location": "recepción de un taller mecánico local",
            "starting_status": "recepcionista",
            "target_outcome": "empresa de software nacional bajo ataque del incumbente · patrimonio $18M",
            "business_or_career_type": "SaaS / software para talleres",
            "timeline_scale": "4 años",
        },
        "thumbnail_concept": {
            "main_visual": "Protagonista de 19 años en una recepción diminuta de taller mientras notificaciones de llamadas sin contestar llenan el monitor",
            "protagonist_state": "cansado, alerta, contando oportunidades perdidas",
            "environment": "taller mecánico local de noche, recepción grasienta",
            "central_contrast": "taller chico vs reflejo tenue de un HQ de software de vidrio",
            "emotion": "urgencia tranquila",
            "key_object": "teléfono de escritorio con 17 llamadas perdidas",
            "composition": "sujeto a la izquierda, reflejo del HQ a la derecha",
            "camera": "plano medio amplio, ángulo ligeramente bajo",
            "lighting": "fluorescente del taller + brillo del teléfono",
            "background": "llantas, tickets de trabajo a mano",
            "text_if_any": "",
            "thumbnail_prompt": (
                "2D cinematic illustration, young receptionist at cluttered mechanic desk at night, "
                "phone showing 17 missed calls, faint reflection of a glass HQ, clean linework, "
                "detailed shop environment, dramatic lighting, no cluttered text, YouTube thumbnail"
            ),
        },
        "llm_score_hints": {
            "curiosity": 9,
            "fantasy_strength": 8,
            "thumbnail_potential": 9,
            "originality": 8,
        },
    },
    {
        "id": "dollar-laundromat-chain",
        "premise": (
            "Compras una lavandería en quiebra por $1 creyendo que las 'deudas' son chicas. No lo son: "
            "máquinas rotas, un landlord listo para echarte y un barrio que dejó de confiar. Reparas "
            "tres lavadoras con YouTube y repuestos, bajas precios para enfermeras del turno noche y "
            "conviertes las cámaras en un livestream antirobo. El flujo de caja vuelve en 11 semanas. "
            "Repites el playbook, abres un sistema operativo propio de locales, franquicias a nivel "
            "nacional y pelearás con una cadena pública — entonces un PE roll-up ofrece comprarte si "
            "también te comes sus peores locales."
        ),
        "title": "POV: Compras una lavandería muerta por $1",
        "title_options": [
            {"text": "POV: Compras una lavandería muerta por $1"},
            {"text": "POV: Construyes una cadena nacional con máquinas rotas"},
            {"text": "POV: Tu local de $1 se vuelve un imperio de franquicias"},
        ],
        "one_line_fantasy": "De comprador de un dólar a dueño de una red nacional de lavanderías.",
        "starting_state": "EDAD 27 · CAJA $4,200 · lavandería muerta · comprador primerizo",
        "end_state": (
            "EDAD 34 · patrimonio $22M · 86 locales + franquicias en 12 estados · "
            "cadena rival nacional · padres en casa propia · controlas adquisiciones"
        ),
        "core_transformation": "Operador sin nada → dueño de red nacional frente a ultimátum de PE",
        "story_category": "acquisition",
        "ending_direction": "empire",
        "scale_ceiling": "national",
        "business_fantasy": "Construir un sistema operativo de lavanderías y franquiciar a escala nacional.",
        "life_fantasy": "Ownership real, familia segura y poder de decidir si vendes o pelearas el imperio.",
        "escalation_ladder": [
            "Firmas un local muerto por $1 con máquinas rotas.",
            "Flujo de caja positivo en 11 semanas.",
            "Segunda y tercera adquisición con caja del primero.",
            "Sistema operativo propio para abrir locales más rápido.",
            "15 locales propios en la región.",
            "Franquicias y 80+ puntos a escala nacional.",
            "Competidor nacional y oferta de PE con locales tóxicos.",
            "Decides vender limpio o pelear el imperio.",
        ],
        "life_progression": {
            "start": ["departamento compartido", "$4,200", "sin equity", "nadie te toma en serio"],
            "early_reward": ["primer mes en positivo", "mejores herramientas"],
            "mid_reward": ["dejas el segundo empleo", "alquiler propio", "primer empleado"],
            "major_reward": ["padres en casa propia", "oficina pequeña", "viajes de expansión"],
            "late_state": ["independencia financiera", "ownership de red nacional", "poder de negociación con PE"],
        },
        "rewards": [
            {"type": "ownership", "description": "Pasas de inquilino de un local a dueño de una red", "story_beat": "growth"},
            {"type": "family", "description": "Compras casa para tus padres", "story_beat": "major_reward"},
            {"type": "freedom", "description": "Dejas el segundo empleo y controlas tu tiempo", "story_beat": "mid_reward"},
            {"type": "status", "description": "Negocias de igual a igual con un PE nacional", "story_beat": "endgame"},
            {"type": "financial", "description": "Patrimonio de ocho cifras atado a locales y franquicias", "story_beat": "late_state"},
        ],
        "start_end_contrast": {
            "start": "27 años · $4,200 · un local muerto · landlord listo para echarte",
            "end": "34 años · $22M · 86 locales nacionales · oferta de PE · familia segura",
        },
        "central_story_question": "¿Vendes la cadena que reconstruiste o arriesgas envenenarla con los locales tóxicos del PE?",
        "open_loops": [
            "¿Tres lavadoras reparadas reinician de verdad el flujo de caja?",
            "¿El landlord renueva después del casi desalojo?",
            "¿Qué pasa cuando el PE exige que absorbas locales fallidos?",
        ],
        "story_engine": {
            "specific_opportunity": "Una lavandería en quiebra se compra por $1 si asumes deuda de máquinas y riesgo de lease",
            "why_protagonist_notices_it": "Lavas ahí cada semana y ves la mitad de las máquinas con cartel FUERA DE SERVICIO desde hace meses",
            "initial_action": "Firmas la compra de $1 y pasas dos noches reconstruyendo tres lavadoras con repuestos",
            "first_customer_or_break": "Las enfermeras del turno noche llenan la madrugada después de que descuentas después de las 22h",
            "business_or_progress_mechanism": "Adquirir lavanderías en crisis, reparar, sistematizar y franquiciar el playbook",
            "why_it_works": "La demanda nunca se fue: se fueron la confianza y las máquinas que funcionan",
            "growth_mechanism": "Playbook reparación+confianza → multi-local → sistema operativo → franquicias nacionales",
            "first_proof": "Flujo de caja positivo en 11 semanas",
            "first_major_reward": "Cuatro locales más y luego escala a franquicias",
            "primary_opposition": "Presión de desalojo del landlord y vandalismo en máquinas sin atención",
            "mid_story_complication": "Una inundación arruina el segundo local recién abierto la semana en que estiras la caja",
            "major_threat": "Un roll-up de PE ofrece buyout solo si también tomas sus peores locales",
            "big_decision": "Vender limpio y salir, o aceptar el deal y arriesgar re-envenenar la marca nacional",
            "stakes": "Tu red nacional y si el playbook sobrevive al capital institucional",
            "possible_cost": "Perder la propiedad o heredar una bomba de deuda disfrazada de crecimiento",
            "escalation_path": "Local de $1 → 5 → 15 → franquicias nacionales → presión del PE",
            "endgame": "Cadena nacional independiente o absorbida por un roll-up",
        },
        "hook": (
            "Sostienes un contrato de una página bajo luz fluorescente.\n\n"
            "Precio de compra: un dólar.\n\n"
            "La mitad de las lavadoras están muertas.\n\n"
            "El landlord quiere echarte en sesenta días.\n\n"
            "Firmas igual."
        ),
        "world_seeds": {
            "starting_age": 27,
            "starting_cash": "$4,200",
            "starting_location": "lavandería de barrio",
            "starting_status": "comprador primerizo",
            "target_outcome": "cadena nacional de lavanderías bajo presión de PE",
            "business_or_career_type": "adquisición / franquicia de lavanderías",
            "timeline_scale": "7 años",
        },
        "thumbnail_concept": {
            "main_visual": "Firmas un contrato de $1 frente a una fila de lavadoras FUERA DE SERVICIO",
            "protagonist_state": "sonrisa nerviosa, grasa en las manos",
            "environment": "lavandería fluorescente de noche",
            "central_contrast": "local roto vs mapa nacional de locales brillando en el reflejo del vidrio",
            "emotion": "esperanza temeraria",
            "key_object": "billete de un dólar clipado al contrato",
            "composition": "contrato en primer plano, máquinas muertas al medio",
            "camera": "plano medio",
            "lighting": "fluorescente duro",
            "background": "sillas de plástico, pizarra de precios a mano",
            "text_if_any": "",
            "thumbnail_prompt": (
                "2D cinematic illustration, young buyer signing contract beside broken washers, "
                "one-dollar bill on paperwork, reflection of national laundry chain map in glass, "
                "detailed laundromat, no busy text"
            ),
        },
        "llm_score_hints": {
            "curiosity": 9,
            "fantasy_strength": 8,
            "thumbnail_potential": 9,
            "originality": 9,
        },
    },
    {
        "id": "stadium-seat-license",
        "premise": (
            "Un club de fútbol de media tabla se ahoga en deuda. Notas que los palcos corporativos "
            "están vacíos entre semana mientras empresas locales siguen comprando LEDs del estadio. "
            "Creas un producto de licencia de asiento transferible: las empresas prepagan 40 partidos, "
            "financias arreglos del estadio y los fans revenden asientos sin usar en tu app. "
            "Las primeras 12 licencias refinancian el techo. Expandes el modelo a otros clubes de la "
            "liga. Entonces la liga amenaza con bloquear la reventa como 'reventa ilegal' y el board "
            "vota si te echa o te hace socio minoritario con proyección internacional."
        ),
        "title": "POV: Salvas un club de fútbol con licencias de asiento",
        "title_options": [
            {"text": "POV: Salvas un club de fútbol con licencias de asiento"},
            {"text": "POV: Conviertes palcos vacíos en ownership de un club"},
            {"text": "POV: Tu app de tickets te mete en el palco del dueño"},
        ],
        "one_line_fantasy": "De nadie en la tribuna a decidir el futuro del club desde el palco del dueño.",
        "starting_state": "EDAD 31 · CAJA $9,500 · ops de partido · desconocido",
        "end_state": (
            "EDAD 36 · patrimonio $14M · socio minoritario · modelo licenciado en 8 clubes · "
            "viajes de liga · padres seguros · agenda propia"
        ),
        "core_transformation": "Staff de match-day → arquitecto de licencias forzado a una pelea de ownership",
        "story_category": "sports_business",
        "ending_direction": "comeback",
        "scale_ceiling": "international",
        "business_fantasy": "Licenciar el modelo de asientos a clubes y ganar equity en el que salvaste.",
        "life_fantasy": "Pasar de staff invisible a socio con voz, viajes de liga y libertad de agenda.",
        "escalation_ladder": [
            "Trabajas ops de partido bajo un techo que gotea.",
            "Cierras las primeras 12 licencias corporativas.",
            "Refinancias el préstamo del techo.",
            "El board te mete a reuniones de reestructuración.",
            "Licencias el modelo a otros clubes de la liga.",
            "La liga amenaza con banear la reventa.",
            "Voto de ownership minoritario vs expulsión.",
            "Expansión internacional del playbook de estadios.",
        ],
        "life_progression": {
            "start": ["departamento cerca del estadio", "$9,500", "sin voz", "horario de partido"],
            "early_reward": ["primeras 12 licencias", "respeto del board junior"],
            "mid_reward": ["acceso a reuniones de dueños", "mejor salario", "viajes de liga"],
            "major_reward": ["equity minoritario", "padres con seguridad", "oficina en el estadio"],
            "late_state": ["poder de voto", "modelo multi-club", "libertad geográfica parcial"],
        },
        "rewards": [
            {"type": "status", "description": "Pasas de staff a voz en el board", "story_beat": "first_major_reward"},
            {"type": "ownership", "description": "Equity minoritario en el club", "story_beat": "endgame"},
            {"type": "experience", "description": "Viajas con la liga cerrando licencias", "story_beat": "growth"},
            {"type": "family", "description": "Estabilidad económica familiar", "story_beat": "major_reward"},
            {"type": "freedom", "description": "Dejas el grind de match-day por agenda propia", "story_beat": "late_state"},
        ],
        "start_end_contrast": {
            "start": "31 años · $9,500 · suite oscura · nadie te escucha",
            "end": "36 años · socio minoritario · $14M · 8 clubes · padres seguros · agenda propia",
        },
        "central_story_question": "¿La liga mata tu modelo de reventa antes de que el board te haga socio?",
        "open_loops": [
            "¿Las empresas prepagarán de verdad 40 partidos?",
            "¿La reventa sobrevive a un ban de la liga?",
            "¿El board te echa o te da equity?",
        ],
        "story_engine": {
            "specific_opportunity": "Palcos vacíos + empresas que ya compran LEDs = mercado de licencias prepago",
            "why_protagonist_notices_it": "Trabajas ops de partido y ves suites oscuras mientras la cinta LED se agota",
            "initial_action": "Pitcheas una licencia transferible de 40 partidos que prepaga deuda de arreglos",
            "first_customer_or_break": "Una logística local compra las primeras 12 licencias en una semana",
            "business_or_progress_mechanism": "Licencias corporativas prepago + fee del marketplace secundario",
            "why_it_works": "Las empresas quieren hospitalidad garantizada; el club necesita plata ya; los fans quieren liquidez",
            "growth_mechanism": "Más inventario de licencias + 8% de fee + licenciar el modelo a otros clubes",
            "first_proof": "Las primeras 12 licencias refinancian el préstamo del techo",
            "first_major_reward": "El board te mete a las reuniones de reestructuración",
            "primary_opposition": "Miembros viejos del board que odian 'financierizar' al hincha",
            "mid_story_complication": "Un no-show viral deja a un VIP sin asiento y los sponsors amenazan con irse",
            "major_threat": "La liga marca la reventa como scalping y amenaza con bloquear el producto",
            "big_decision": "Matar la reventa para aplacar a la liga, o pelear y arriesgar sanción al club",
            "stakes": "Solvencia del club, tu reputación y un voto de ownership minoritario",
            "possible_cost": "Ban de estadios de la liga y blacklist en deals deportivos",
            "escalation_path": "Palcos vacíos → licencias → techo → multi-club → amenaza de ban → ownership",
            "endgame": "Socio minoritario con modelo internacional o chivo expiatorio de un experimento fallido",
        },
        "hook": (
            "Es miércoles a la noche bajo un techo de estadio que gotea.\n\n"
            "Los palcos corporativos están a oscuras.\n\n"
            "Los LEDs todavía iluminan el césped.\n\n"
            "Te das cuenta de que la plata no falta: está en el producto equivocado."
        ),
        "world_seeds": {
            "starting_age": 31,
            "starting_cash": "$9,500",
            "starting_location": "estadio de fútbol de media tabla",
            "starting_status": "staff de operaciones de partido",
            "target_outcome": "ownership minoritario + modelo multi-club internacional",
            "business_or_career_type": "sports ownership / monetización de estadio",
            "timeline_scale": "5 años",
        },
        "thumbnail_concept": {
            "main_visual": "Estás solo en un palco corporativo oscuro mirando un césped iluminado con LEDs encendidos",
            "protagonist_state": "calculando, abrigo todavía puesto",
            "environment": "estadio de media tabla de noche, con goteras",
            "central_contrast": "suite vacía vs futuro palco del dueño abarrotado",
            "emotion": "claridad hambrienta",
            "key_object": "clipboard de facturas impagas del techo",
            "composition": "estadio amplio, figura chica en el palco",
            "camera": "ángulo alto desde el palco",
            "lighting": "luces del campo vs suite oscura",
            "background": "asientos vacíos, lluvia en el concreto",
            "text_if_any": "",
            "thumbnail_prompt": (
                "2D cinematic illustration, lone figure in dark corporate soccer suite, "
                "bright pitch and LED ribbon below, clipboard of invoices, dramatic contrast, no busy text"
            ),
        },
        "llm_score_hints": {
            "curiosity": 9,
            "fantasy_strength": 9,
            "thumbnail_potential": 9,
            "originality": 9,
        },
    },
]
