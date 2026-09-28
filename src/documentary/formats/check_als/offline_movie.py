"""Películas cortas para cuando no hay modelo, y para probar el camino hasta el guion.

Cada una es un hilo distinto. El cierre es el que eligió la persona.
"""
from __future__ import annotations

from typing import Any

from src.documentary.formats.check_als.plain_language import PUBLIC_CLOSES

MOVIES: dict[tuple[str, str], list[str]] = {
    ("creator", "victory"): [
        "Tienes 24 años y vives en un departamento pequeño en Madrid. De día contestas mails en una oficina que huele a café recalentado. De noche armas el trípode entre la cama y la ventana, y el canal se llama TechVibe. Anoche lo vieron once personas. Tres eran tus primos.",
        "Subes el video a la una de la mañana. La luz del aro se cae a la mitad de la toma y lo dejas así, porque si lo repites no lo publicas. El comentario que te importa llega a las tres: alguien de tu ciudad dice que por fin entendió algo. Te quedas mirando esa línea más de la cuenta.",
        "El canal sigue chico. Un martes el vecino golpea la pared porque estás grabando el mismo párrafo por cuarta vez. Apagas, te sientas en el suelo y grabas igual, más bajo. Al día siguiente ese video, el torpe, es el que la gente se queda a ver.",
        "Pasan unos meses. Dejas de contar de a uno. Una tarde el número salta mientras estás en el metro y no puedes gritar. Llegas a casa, abres la puerta con el teléfono todavía en la mano y el cuarto se ve distinto, aunque no moviste nada.",
        "Te ofrecen un patrocinio de una empresa chica. El mail está en spam. Lo lees dos veces y contestas con condiciones: dices el producto si lo usas, y si no, no. Esa noche grabas la respuesta como si le hablaras a una sola persona, no a una marca.",
        "Hay una semana floja. El video que te costó el domingo no despega, y vuelves a la oficina con la sensación de haber inventado un mundo que solo existe para ti. En el almuerzo escribes el siguiente título en una servilleta y la guardas en el bolsillo.",
        "Renuncias un jueves, sin discurso. El último café de la máquina lo tomas de pie. En el cuarto, esa noche, el aro de luz ya no se cae. TechVibe deja de ser un secreto que cabe en el teléfono.",
        "Año siguiente. La gente te escribe desde otras ciudades para decirte en qué minuto entendieron. Tus padres vienen, se sientan en la cama porque no hay otra silla, y miran un video sin interrumpirte. No aplauden. Se quedan.",
        "Una marca más grande te pide que cambies el tono, que hables más rápido, que parezcas otro canal. Grabas la prueba y la borras antes de exportarla. TechVibe sigue sonando a tu cuarto, con la calle de Madrid detrás de la ventana.",
        "Hay un viernes en el que el número no se mueve en todo el día. Cierras la laptop, caminas hasta el final de la manzana y vuelves con el mismo título que tenías a la mañana. Lo grabas igual. A la noche alguien lo mira entero.",
        "Al final lo logras. El canal es tuyo, la luz es la de tu cuarto, y esa vida te queda.",
    ],
    ("sports_team", "victory"): [
        "Tienes 26 años. Trabajas en una oficina y los sábados juegas cuando la cancha todavía está abierta. En Puerto Norte, los Halcones están a punto de desaparecer. El gimnasio huele a humedad y el utilero es la única persona que llega antes que tú.",
        "Firmas. Pones lo que tienes ahorrado. Unas personas de la ciudad ponen el resto. La entrada es casi un regalo y el club llega cansado. Te dan unas llaves que no abren todas las puertas.",
        "El primer mes el lugar está vacío. Una noche cuentas diecisiete personas y una de ellas se va en el primer tiempo. Igual te quedas hasta que apagan las luces, recogiendo una cinta del piso.",
        "Pasan los meses. El equipo pierde seguido y tú aprendes los nombres de los que se quedan. Una jugadora te dice, en el pasillo, que si vuelves a prometer cosas que no puedes pagar, se va. No prometes. Compras hielo y cintas.",
        "Año segundo. Dejas la oficina un lunes. La caja de tus cosas cabe en un asiento. Tus padres vienen un viernes y se sientan donde antes no había nadie. Tu madre pregunta si esto es de verdad. Le dices que sí, bajito.",
        "Hay una racha floja que cuesta dormir. El marcador duele y el gimnasio vuelve a sonar a hueco. Esa semana no inventas un discurso. Abres igual el sábado, y está la misma gente de siempre, la que no se fue.",
        "Después, sin que lo anotes, una noche la fila dobla la esquina. Alguien que no conoces guarda un lugar. Desde el túnel ves las gradas de arriba ocupadas y te tiembla la mano en el marco de la puerta.",
        "Viajas en el autobús a un pueblo de al lado. Llueve contra el vidrio y nadie habla. Pierden por dos puntos. En el regreso una jugadora se duerme con la cabeza en la ventana y tú piensas que esto, el viaje, también es el equipo.",
        "Un miércoles se cae una gotera sobre el banquillo. Pones un balde y sigues el entrenamiento. El utilero te mira y no dice nada. A la semana siguiente la gotera sigue, y también la gente que ya conoce el camino.",
        "Al final lo logras. El lugar se llena y el equipo sigue siendo tuyo.",
    ],
    ("sports_team", "loss"): [
        "Tienes 29 años cuando compras un equipo que ya venía cansado. Siempre quisiste esto. El día de la firma hace frío y el gimnasio tiene una gotera justo arriba del banquillo.",
        "Los primeros partidos crees que con presencia alcanza. Te sientas cerca, aprendes los nombres, pagas el autobús cuando no hay otra forma de llegar al pueblo de al lado.",
        "La gente no vuelve. Una noche juegan y oyes tu propia voz rebotar. El marcador se inclina y los jugadores dejan de mirarte al terminar. No es rabia. Es cansancio.",
        "Pasan dos años. Vendes el auto para cubrir una semana. Tus padres te dicen que pares y tú les contestas que el sábado se acomoda. El sábado no se acomoda.",
        "Hay un partido que ganan de local y por una noche el gimnasio suena lleno. Crees que el año se da vuelta. A la semana siguiente vuelven a jugar y cuentan los mismos doce de siempre. La noche buena no alcanza para cambiar la calle.",
        "Pagas tarde. Lo dices mirando la mesa, no el techo. Nadie grita. Alguien deja las zapatillas en el locker y no vuelve el jueves. Entiendes el silencio mejor que cualquier número.",
        "Llega una oferta que no es una oferta: es una subasta. Lees el papel en la cocina, de pie, con el abrigo puesto. Cierras el gimnasio una última tarde y dejas las llaves sobre el escritorio del utilero.",
        "Al final se cae. Se cierra esa etapa. Te quedas con el ruido de una pelota en un lugar vacío, y con la certeza de que lo intentaste hasta que ya no daba.",
    ],
    ("freeform", "victory"): [
        "Tienes 27 años y te despiertas con un mensaje que no parece real: tienes siete días para gastar un billón de dólares. El reloj del teléfono marca 9:14. Afuera tu vida sigue igual, la misma calle, el mismo café.",
        "El primer día no puedes decidir ni el desayuno. Pagas la cuenta de todo el bar y la gente se ríe porque cree que es un chiste. Tú miras el comprobante y el número no cabe en la pantalla.",
        "El segundo día compras silencio: una casa vacía al lado del mar, sin muebles. Te sientas en el suelo y escuchas el agua. El dinero no hace ruido. Eso te asusta más que la cifra.",
        "A mitad de semana el gasto se vuelve absurdo y después se vuelve concreto. Pagas deudas de gente que no te pidió nada, un hospital, el alquiler de tu edificio, el taller de la esquina que iba a cerrar el viernes.",
        "Hay una noche, la quinta, en la que te detienes. Son las tres de la mañana y no has dormido. El reloj sigue. Entiendes que gastar también es elegir qué no se compra: no compras una vida distinta para escapar de la tuya.",
        "El sexto día vuelves a tu calle. Dejas el café de siempre pagado por un año y no se lo dices a nadie. El dueño te mira raro cuando dejas el sobre y te vas antes de que pregunte.",
        "También compras algo ridículo: un piano que no sabes tocar, que cabe apenas en el pasillo. A las dos horas lo entiendes y lo dejas en una escuela, de noche, con una nota sin firma. El gasto que te gusta es el que no te queda a ti.",
        "El cuarto día te sientas en un banco y miras pasar gente que no sabe nada. El reloj sigue. Tienes más de lo que se puede gastar con las manos, y al mismo tiempo solo tienes esas horas. Caminas hasta que te duelen los pies, como cualquier tarde.",
        "El séptimo día el plazo se acaba a las 9:14. Queda un resto que ya no puedes tocar. Te sientas en tu cama de siempre. Al final lo logras: gastaste, volviste, y esa vida te queda.",
    ],
    ("chef", "pyrrhic"): [
        "Tienes 31 años y cocinas en un restaurante que no es tuyo, en un turno que termina cuando la ciudad ya duerme. Un local chico en la esquina se desocupa. Las llaves pesan más que la sartén.",
        "Abres con doce cubiertos y un menú que cabe en una hoja. La primera noche vienen tus amigos y un señor que se equivocó de puerta. Se queda por el olor del ajo.",
        "Los meses siguientes la sala se llena de verdad. Una reseña dice tu nombre. Dejas de ver la luz del día. El domingo, que era el almuerzo en casa de tus padres, pasa a ser el servicio más largo.",
        "Llega una estrella, o algo que se le parece: una crítica que cambia la reserva de un mes. Brindas en la cocina con el equipo, de pie, con el delantal puesto. Nadie se sienta.",
        "Tu padre cumple años ese domingo y tú estás emplatando. Le mandas una foto del postre. Él contesta con un punto. Nada más.",
        "Una noche el servicio se cae: se quema una salsa, se va la luz diez minutos, alguien se queja en voz alta. Recuperas el ritmo y al final aplauden. Tú estás en la puerta de la cocina con las manos temblando, y no hay nadie de tu casa para verlo.",
        "A la una de la mañana la sala queda vacía y huele a limón y a hierro de la plancha. Apagas tú las luces. El local es tuyo. La silla de tu padre, en la otra casa, quedó vacía otra vez.",
        "Llegas arriba. La sala está llena, la crítica está en la puerta, y el almuerzo de los domingos no vuelve. Al final llegas, y algo de tu vida se queda en esa cocina.",
    ],
    ("musician", "ironic"): [
        "Tienes 23 años y tu canción vive en el teléfono, en notas de voz que nadie pidió. Una noche la tocas en un bar donde la gente habla más fuerte que tú. Igual terminas.",
        "Alguien del fondo te escribe al otro día. No es un sello. Es una marca de bebidas. Quieren esa melodía, la que escribiste en la cocina, para un anuncio de quince segundos.",
        "Firmas porque el alquiler vence el jueves. Grabas la versión corta en un estudio que huele a cables. Cuando la escuchas con la voz en off del producto, no la reconoces, y al mismo tiempo es tuya.",
        "El anuncio está en todas partes. En el colectivo, en el mercado, en la radio del bar donde tocaste. La gente tararea. Nadie sabe tu nombre. Saben el estribillo y el nombre de la bebida.",
        "Te llaman para una gira de veranos en shoppings. El sonido es bueno. El público canta. Tú miras sus bocas y escuchas el comercial, no la noche en la cocina.",
        "Escribes otra canción, de noche, sin marca y sin estribillo fácil. La tocas una vez en el mismo bar de la primera noche. Tres personas callan. El resto sigue hablando. Esa es la canción que querías, y no la pone nadie en el colectivo.",
        "Tu madre tiene la radio prendida mientras lava un vaso. Entra el anuncio. Ella tararea y te mira, orgullosa. Tú sonríes y sientes el golpe justo ahí: te reconoce el estribillo, no la cocina donde la escribiste.",
        "Consigues lo que querías, y no es como lo imaginabas. La canción es famosa. Tú sales por la puerta de servicio con la funda del instrumento golpeándote la pierna.",
    ],
    ("business", "plateau"): [
        "Tienes 28 años y diseñas de noche, en la mesa de la cocina, para clientes que a veces pagan. Un día dejas la oficina y te quedas con tres encargos y el miedo concreto de fin de mes.",
        "El primer año no es una película de despegue. Es una fila de mails. Uno dice que sí. Otro se enfría. Aprendes a cobrar antes de prometer la luna.",
        "Armas un estudio chico con una socia. El letrero es de papel los primeros meses. Después es de verdad, y todavía se ve chico desde la vereda, y eso te gusta más de lo que admites.",
        "Hay un mes en el que un cliente grande quiere comprarte el estudio entero. Cenas con esa oferta en el bolsillo. Al otro día dices que no. No por un discurso. Porque te gusta abrir la puerta tú, a la mañana.",
        "Pasan cuatro años. No hay imperio. Hay una calle que ya te ubica, una mesa que es tuya, y trabajo que alcanza para vivir sin volver a la oficina de antes.",
        "Un mes entero vive de un solo cliente. Apagas la luz temprano para no mirar la bandeja. Al otro mes entran dos encargos chicos, de gente de la cuadra, y con eso pagas el alquiler. No es una cima. Es poder quedarte.",
        "Llueve y el letrero de papel, el primero, ya no existe. El de verdad se moja igual en el borde. Lo secas con la manga y abres. Afuera pasa alguien que ya no pregunta qué hay ahí dentro, porque lo sabe.",
        "No explota ni se cae. Se queda, y es tuyo.",
    ],
}


def _beats_are_a_movie(beats: list[dict[str, Any]]) -> bool:
    texts = [str(b.get("event") or "").strip() for b in beats if isinstance(b, dict)]
    texts = [t for t in texts if len(t) > 40]
    return len(texts) >= 5


def script_from_facts(facts: dict[str, Any]) -> str:
    beats = facts.get("beats") if isinstance(facts.get("beats"), list) else []
    if _beats_are_a_movie(beats):
        parts = [str(b.get("event") or "").strip() for b in beats if isinstance(b, dict)]
        parts = [p for p in parts if p]
        return "\n\n".join(parts).strip()
    mode = str(facts.get("vehicle_mode") or "")
    ending = str(facts.get("ending_type") or "open")
    paras = MOVIES.get((mode, ending))
    if not paras:
        return ""
    return "\n\n".join(paras).strip()


def architecture_for(
    *,
    mode: str,
    ending: str,
    title: str,
    premise: str,
    name: str,
    city: str,
    age0: int = 24,
    age1: int = 29,
) -> dict[str, Any]:
    paras = MOVIES[(mode, ending)]
    times = [
        "Mes 1",
        "Mes 2",
        "Mes 5",
        "Mes 8",
        "Año 2",
        "Año 3",
        "Año 4",
        "Año 5",
        "Año 6",
        "Año 7",
    ]
    beats = []
    for i, text in enumerate(paras):
        ops: list[dict[str, Any]] = []
        if i == 1:
            if mode == "sports_team":
                ops.append(
                    {
                        "op": "acquire_team",
                        "your_cash": 15000,
                        "investor_cash": 85000,
                        "your_pct": 51,
                        "investor_pct": 39,
                        "seller_pct": 10,
                        "debt_assumed": 0,
                        "asking_price": 1,
                    }
                )
            elif mode != "freeform":
                ops.append(
                    {
                        "op": "launch_company",
                        "your_cash": 8000,
                        "investor_cash": 0,
                        "your_pct": 100,
                        "investor_pct": 0,
                        "debt_assumed": 0,
                    }
                )
        if i in (3, 5, 7):
            ops.append({"op": "advance_time", "months": 10})
        beats.append(
            {
                "beat_id": f"b{i+1:02d}",
                "time": times[i] if i < len(times) else f"Año {i}",
                "duration_target_s": 20,
                "event": text,
                "cause": "",
                "consequence": "",
                "story_purpose": "escalation" if i else "opening",
                "reward_or_setback": "setback" if i in (2, 5) else "reward",
                "ops": ops,
                "metric_reveal": ["CASH"] if ops else [],
            }
        )
    close = PUBLIC_CLOSES.get(ending) or PUBLIC_CLOSES["open"]
    blueprint = {
        "fiction_world": {"vehicle_name": name, "team_name": name, "city": city},
        "ending": close,
        "narrative_ending": ending,
        "fantasy": {"surface_desire": premise},
        "protagonist": {"age": age0, "starting_life": premise},
        "user_premise": premise,
        "freeform": mode == "freeform",
        "business_or_vehicle": {"what_is_being_built_or_owned": name},
    }
    world = {
        "time": {"protagonist_age": age0},
        "life": {
            "job": "empleado de oficina",
            "home": "un departamento pequeño",
            "personal_cash": 12000,
        },
        "team": {"name": name, "city": city},
    }
    return {
        "blueprint": blueprint,
        "synopsis": "",
        "initial_world": world,
        "beats": beats,
        "final_age_hint": age1,
        "title": title,
    }
