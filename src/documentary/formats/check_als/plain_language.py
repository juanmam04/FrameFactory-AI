"""Texto que lee la gente en Check: una vida en tú, sin planilla."""
from __future__ import annotations

import re
from typing import Any

_VOSEO = (
    (r"\bTenés\b", "Tienes"),
    (r"\btenés\b", "tienes"),
    (r"\bTrabajás\b", "Trabajas"),
    (r"\btrabajás\b", "trabajas"),
    (r"\bVivís\b", "Vives"),
    (r"\bvivís\b", "vives"),
    (r"\bjugás\b", "juegas"),
    (r"\bJugás\b", "Juegas"),
    (r"\bComprás\b", "Compras"),
    (r"\bcomprás\b", "compras"),
    (r"\bFirmás\b", "Firmas"),
    (r"\bfirmás\b", "firmas"),
    (r"\bBajás\b", "Bajas"),
    (r"\bbajás\b", "bajas"),
    (r"\bRenunciás\b", "Renuncias"),
    (r"\brenunciás\b", "renuncias"),
    (r"\bTe mudás\b", "Te mudas"),
    (r"\bte mudás\b", "te mudas"),
    (r"\bmudás\b", "mudas"),
    (r"\bApostás\b", "Apuestas"),
    (r"\bapostás\b", "apuestas"),
    (r"\bSeguís\b", "Sigues"),
    (r"\bseguís\b", "sigues"),
    (r"\bsentís\b", "sientes"),
    (r"\bPodés\b", "Puedes"),
    (r"\bpodés\b", "puedes"),
    (r"\bSos\b", "Eres"),
    (r"\bsos\b", "eres"),
    (r"\bcontás\b", "cuentas"),
    (r"\bPagás\b", "Pagas"),
    (r"\bpagás\b", "pagas"),
    (r"\bSalís\b", "Sales"),
    (r"\bsalís\b", "sales"),
    (r"\bMirás\b", "Miras"),
    (r"\bmirás\b", "miras"),
    (r"\bPonés\b", "Pones"),
    (r"\bponés\b", "pones"),
    (r"\bte quedás\b", "te quedas"),
    (r"\bquedás\b", "quedas"),
    (r"\bVos\b", "Tú"),
    (r"\bvos\b", "tú"),
    (r"\bcobrás\b", "cobras"),
    (r"\bLlevás\b", "Llevas"),
    (r"\bllevás\b", "llevas"),
    (r"\bGanás\b", "Ganas"),
    (r"\bganás\b", "ganas"),
    (r"\bquerés\b", "quieres"),
    (r"\bQuerés\b", "Quieres"),
    (r"\bhacés\b", "haces"),
    (r"\bHacés\b", "Haces"),
    (r"\bsabés\b", "sabes"),
    (r"\bentrás\b", "entras"),
    (r"\bEntrás\b", "Entras"),
    (r"\bdecís\b", "dices"),
    (r"\bDecís\b", "Dices"),
)

_JARGON = re.compile(
    r"equity|valuaci|factur|servicio de la deuda|seller financing|ownership|"
    r"patrimonio|porcentaje|inversores|millonario|"
    r"\b\d+\s*%|%\s*\.|caja\s+\d|ingresos\s+\d|"
    r"asistencia media|deuda del club|net worth|"
    r"\b51\b|\b39\b",
    re.I,
)

_DEAL = re.compile(
    r"\$?\d[\d,\.]*\s*de precio.{0,400}?financia\s+\$?[\d,\.]+",
    re.I,
)

PUBLIC_EVENT_RULES = """
IDIOMA QUE LEE LA GENTE (event, cause, consequence, visual_opportunity):
Español de tú: tienes, firmas, compras, vives. Prohibido el voseo (tenés, firmás, comprás, sos, vos).
Esas frases son una escena de vida que entiende un chico que sueña y un adulto que quiere pasar un rato ahí.
Prohibido en esas frases: equity, porcentaje, %, valuación, facturación, caja, ingresos, servicio de la deuda, seller financing, patrimonio, "51%", "millonario".
El dinero, si aparece, se dice así: "pones tus ahorros", "la entrada es casi un regalo", "pagas la cena". Sin planilla.
Los números (pct, debt, cash) viven solo en ops. No los copies al texto.
""".strip()


def to_tu(text: str) -> str:
    out = str(text or "")
    for pat, rep in _VOSEO:
        out = re.sub(pat, rep, out)
    return out


def has_jargon(text: str) -> bool:
    return bool(_JARGON.search(str(text or "")))


def plain_deal_sentence(*, sports: bool = True) -> str:
    if sports:
        return (
            "Firmas y el equipo pasa a ser tuyo. Pones lo que tienes ahorrado. "
            "Unas personas de la ciudad ponen el resto y el dueño anterior se queda con una parte chica. "
            "La entrada es casi un regalo. El club llega cansado, con las cuentas pesadas."
        )
    return (
        "Empiezas lo tuyo. Pones lo que tienes ahorrado. "
        "Unas personas cercanas ponen el resto. "
        "Al principio cabe en una habitación y todavía no te paga un sueldo."
    )


def plain_event(event: str, *, sports: bool = True) -> str:
    ev = to_tu(str(event or "").strip())
    if not ev:
        return ""
    low = ev.lower()
    if _DEAL.search(ev) or (
        re.search(r"compr|adquir|firm", low) and re.search(r"deuda|%|51|peso|equity|inversor|financia", low)
    ):
        return plain_deal_sentence(sports=sports)
    if re.search(r"lanz", low) and re.search(r"inversor|%|equity|cash|60", low):
        return plain_deal_sentence(sports=False)
    if "servicio de la deuda" in low or "equity" in low:
        if re.search(r"roster|plantel|instal|jugador", low):
            return (
                "Apuestas por mejores jugadores y por arreglar el lugar. "
                "El mes siguiente el equipo arranca flojo y cuesta dormir."
                if sports
                else "Apuestas más de la cuenta. El mes siguiente el trabajo se traba y cuesta dormir."
            )
        return "Las cuentas aprietan un mes, y sigues al mando."
    if has_jargon(ev):
        kept = []
        for sentence in re.split(r"(?<=[.!?])\s+", ev):
            if sentence and not has_jargon(sentence):
                kept.append(sentence.strip())
        return " ".join(kept).strip()
    return ev


def _words(text: str) -> list[str]:
    return re.findall(r"\S+", text or "")


_CLOSER = (
    "Pasa un año y el lugar ya te reconoce la cara. Pasa otro y la gente te espera en la puerta. "
    "Hay martes vacíos y viernes que no caben. Aprendes los nombres, el olor del piso mojado, "
    "el silencio de después. Un día caminas a casa y esta vida ya es la tuya. "
    "Se entiende en la fila, en la cena, en tus padres sentados donde antes no había sitio."
)


def _fit(body: str, extras: list[str], *, lo: int = 920, hi: int = 1185) -> str:
    text = re.sub(r"\s+", " ", body).strip()
    if _CLOSER not in text:
        text = f"{text} {_CLOSER}".strip()
    i = 0
    while len(_words(text)) < lo and i < len(extras) * 2:
        line = extras[i % len(extras)] if extras else ""
        i += 1
        if not line or line in text:
            if i > len(extras):
                break
            continue
        text = f"{text} {line}".strip()
    if len(_words(text)) < lo:
        text += (
            " Al otro día vuelves. Abres la puerta, prendes la luz y hay alguien que ya te estaba esperando."
            " Esa es la vida: llegar, quedarte, y que el lugar se sienta tuyo."
        )
    words = _words(text)
    if len(words) > hi:
        text = " ".join(words[:hi]).rstrip(" ,;:") + "."
    return text


def _season_lines(hist: list[dict[str, Any]], *, sports: bool) -> list[str]:
    lines = []
    seen: set[int] = set()
    ordered: list[dict[str, Any]] = []
    for raw in hist:
        if not isinstance(raw, dict):
            continue
        sn = int(raw.get("season") or 0)
        if sn in seen and ordered:
            ordered[-1] = raw
        else:
            ordered.append(raw)
            seen.add(sn)
    for h in ordered:
        record = str(h.get("record") or "").strip()
        result = str(h.get("playoff_result") or "").strip()
        champ = bool(h.get("championship"))
        try:
            crowd = int(float(h.get("attendance_avg") or 0))
        except (TypeError, ValueError):
            crowd = 0
        if sports:
            bits = [f"En el año {h.get('season') or ''} el equipo cierra {record or 'un año raro'}."]
            if champ:
                bits.append("Ese año levantas el título. El lugar tiembla.")
            elif result:
                low = result.lower()
                if "sin playoff" in low or low in {"none", "regular"}:
                    bits.append("Ese año no hay playoffs.")
                else:
                    bits.append(f"Después llega esto: {result.rstrip('.')}.")
            if crowd >= 4000:
                bits.append("Hay noches en las que la gente no entra y se queda en la puerta.")
            elif crowd > 0:
                bits.append("El gimnasio sigue a medias: más asientos vacíos que gritos.")
            lines.append(" ".join(bits))
        else:
            if crowd >= 1000:
                lines.append("Un año la gente de verdad llega. El trabajo deja de ser un secreto.")
            else:
                lines.append("Hay un año flojo. Trabajas igual, con la luz de la cocina prendida tarde.")
    return lines


def _life_bits(initial: dict[str, Any], final: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    il = (initial or {}).get("life") or {}
    life = (final or {}).get("life") or {}
    age0 = ((initial or {}).get("time") or {}).get("protagonist_age") or 22
    age1 = ((final or {}).get("time") or {}).get("protagonist_age") or ""
    job0 = il.get("job") or "empleado de oficina"
    home0 = il.get("home") or "un departamento compartido"
    job1 = life.get("job") or "el trabajo que elegiste"
    home1 = life.get("home") or "un lugar que ya es tuyo"
    return str(age0), str(age1), str(job0), str(home0), str(job1), str(home1)


def public_life_synopsis(
    blueprint: dict[str, Any],
    beats: list[dict[str, Any]],
    initial: dict[str, Any],
    final: dict[str, Any],
    *,
    vehicle_mode: str = "sports_team",
) -> str:
    sports_state = (final or {}).get("sports") or {}
    sports = vehicle_mode == "sports_team" or (
        vehicle_mode != "business" and bool(sports_state.get("season_history") or sports_state.get("games_played"))
    )
    if vehicle_mode == "business":
        sports = False
    fw = blueprint.get("fiction_world") or {}
    team = (final or {}).get("team") or {}
    name = (
        team.get("name")
        or fw.get("team_name")
        or fw.get("company_name")
        or fw.get("vehicle_name")
        or fw.get("stage_name")
        or "lo tuyo"
    )
    city = str(fw.get("city") or "").strip()
    where = f" en {city}" if city else ""
    age0, age1, job0, home0, job1, home1 = _life_bits(initial, final)
    place = f"{name}{where}"

    if sports:
        open_para = (
            f"Tienes {age0} años. Trabajas de {job0} y vives en {home0}. "
            f"Los fines de semana juegas al básquet cuando la cancha todavía está abierta. "
            f"{place} está a punto de desaparecer: el gimnasio huele a humedad, las gradas están vacías "
            f"y el utilero es la única persona que llega antes que tú."
        )
    else:
        open_para = (
            f"Tienes {age0} años. Trabajas de {job0} y vives en {home0}. "
            f"Por la noche, cuando el resto de la casa ya duerme, sigues con {place}. "
            f"Todavía no es una vida. Es una idea que te cabe en el teléfono y en la mesa de la cocina."
        )

    paras = [open_para, plain_deal_sentence(sports=sports)]
    used: set[str] = set()
    for beat in beats or []:
        raw = str(beat.get("event") or "").strip()
        if not raw or raw in used:
            continue
        purpose = str(beat.get("story_purpose") or "")
        kind = str(beat.get("reward_or_setback") or "")
        if purpose not in {
            "opening",
            "inciting_incident",
            "first_commitment",
            "first_proof",
            "midpoint",
            "major_success",
            "major_reversal",
            "crisis",
            "decision",
            "climax",
            "ending",
        } and not kind.startswith("reward") and not kind.startswith("setback"):
            continue
        line = plain_event(raw, sports=sports)
        if not line or has_jargon(line) or line in used:
            continue
        paras.append(line if line.endswith(".") else line + ".")
        used.add(raw)
        used.add(line)

    hist = [h for h in (sports_state.get("season_history") or []) if isinstance(h, dict)]
    paras.extend(_season_lines(hist, sports=sports))

    risk = str(((final or {}).get("finance") or {}).get("debt_risk_state") or "")
    if sports and risk in ("manageable", "healthy"):
        paras.append(
            "El club sigue debiendo favores y noches, pero ya no está a punto de cerrar. "
            "Hay gente. Hay partidos. Hay una llave que ya es tuya."
        )
    elif not sports and risk in ("manageable", "healthy"):
        paras.append("Las cuentas dejan de ahogarte. No eres rico de un día para el otro. Puedes seguir.")

    today = f"Hoy tienes {age1} años. " if age1 else "Hoy la vida ya es otra. "
    if sports:
        paras.append(
            "Renuncias al trabajo de oficina cuando esto ya puede pagarte un sueldo chico, pero tuyo. "
            "Te mudas más cerca. Tus padres vienen y se sientan donde hay lugar. "
            "Una noche el lugar se llena y desde el túnel los ves arriba."
        )
    else:
        paras.append(
            "Renuncias cuando lo tuyo ya puede pagarte. Te mudas a un cuarto que es oficina y casa. "
            "Tus padres vienen a verlo, aunque no entiendan cada detalle."
        )
    paras.append(
        f"{today}Tu día a día es {job1}. Vives en {home1}. "
        f"{'El estadio' if sports else 'El lugar'} ya no es el cuarto del primer mes."
    )

    if sports:
        extras = [
            "El primer día el utilero te alcanza las llaves del gimnasio y no sabe si llamarte jefe.",
            "Bajas el precio de la entrada. Esa noche hay más gente en la cola que asientos rotos.",
            "Renuncias al trabajo de oficina cuando el club ya puede pagarte un sueldo feo, pero tuyo.",
            "Te mudas a unas cuadras del estadio. El departamento viejo queda con las cajas a las once de la noche.",
            "Si hay palco, todavía no tiene tu apellido. Tus padres vienen igual y se sientan donde hay lugar.",
            "Una noche no queda un asiento libre. Desde el túnel ves a tus padres arriba, en mejores butacas que el primer año.",
            "Cenas en un lugar que a los 22 ni mirabas la carta. Pagas. Todavía miras el ticket antes de salir.",
            "Sales con un traje que no es de oficina. El utilero te dice jefe y esta vez no es una broma.",
            "Apuestas por el plantel y por arreglar el gimnasio. El mes siguiente el equipo arranca flojo y cuesta dormir.",
            "Una oferta llega al teléfono. Esta vez puedes leerla mañana.",
            "El estadio, que olía a humedad, ahora tiene fila los días de partido.",
            "Un jugador se lastima y el vestuario se queda callado. Aprendes el nombre del médico antes que el del marcador.",
            "Un sponsor local recorta lo que había prometido. Igual abres las puertas el viernes.",
            "Se rompe una caldera. El partido se juega con la gente en campera. Nadie se va.",
            "La radio saca un audio del vestuario. Al día siguiente miras a los jugadores a los ojos y sigues.",
            "El público silba en la salida. Te quedas en el túnel hasta que se vacía la calle.",
            "Tu familia te pide que vuelvas a la oficina. Esa noche duermes en el estadio, en el sillón del utilero.",
            "Contratas a alguien que de verdad sabe dirigir. La primera práctica es un silencio raro, de los buenos.",
            "Viajas a un partido lejos. El micro huele a café y a cinta. Miras la ciudad de noche por la ventana.",
            "Tus padres entran por la puerta de los jugadores. Tu madre guarda el ticket aunque nadie se lo pide.",
            "Hay un mes en el que cuentas las entradas una por una. Al siguiente, la fila dobla la esquina.",
            "El cuarto de utilería deja de ser tu oficina. Te mudas a un cuarto con una ventana al campo.",
            "Un chico te pide una foto en la puerta. Todavía llevas la mochila del trabajo viejo.",
            "Pierdes un partido que dolía. Al otro día abres igual, porque el gimnasio no se abre solo.",
            "Ganas uno que nadie esperaba. En el vestuario nadie grita el número. Se ríen, nada más.",
            "La ciudad empieza a decir el nombre del equipo en el colectivo, sin que tú lo pidas.",
            "Compras camisetas nuevas cuando las viejas ya no dan más. Huelen a tela, no a humedad.",
            "Te sientas en la grada vacía un martes y escuchas el rebote. Ese sonido ya es tu casa.",
            "Alguien del barrio te dice que llevó a su hijo. El hijo quiere volver el viernes.",
            "Cierras la noche con la luz del tablero todavía prendida. Apagas tú. Te vas caminando.",
        ]
    else:
        extras = [
            "El primer cliente llega por un mensaje a medianoche. Respondes antes de pensarlo dos veces.",
            "Renuncias cuando lo tuyo ya puede pagarte un sueldo feo, pero tuyo.",
            "Te mudas a un cuarto donde cabe una mesa de trabajo. Las cajas quedan a las once de la noche.",
            "Tus padres vienen a verlo. No entienden todo. Se quedan igual, y eso alcanza.",
            "Una noche el lugar se llena. Gente de verdad, no solo tus amigos.",
            "Cenas en un sitio que antes ni mirabas. Pagas. Todavía miras el ticket.",
            "Hay un mes malo. Un encargo se cae. Duermes poco y al día siguiente abres igual.",
            "Alguien quiere comprarte lo que armaste. Lees el mensaje y lo dejas para mañana.",
            "Contratas a la primera persona que no eres tú. Le muestras dónde está el café.",
            "Un trabajo grande sale mal en público. Al día siguiente llamas, pides perdón y lo rehaces.",
            "Tu familia te pide que vuelvas al empleo fijo. Esa noche sigues, con la luz de la cocina.",
            "Viajas a una reunión que antes veías en fotos. El asiento de la ventanilla es tuyo.",
            "Guardas el primer mensaje de gracias. Lo lees en los meses flojos.",
            "El cuarto chico se queda chico. Pasas a un lugar con puerta y con tu nombre discreto.",
            "Un desconocido recomienda lo que haces. No le pagaste. Vuelve con otra persona.",
            "Apuestas de más en un proyecto. El mes siguiente se traba y cuesta dormir.",
            "Aprendes a decir que no a un encargo que te quedaba grande.",
            "Hay una fila, chica, en la puerta. Te tiembla la mano al abrir.",
            "Terminas el día caminando a casa. El teléfono vibra y esta vez sonríes antes de mirar.",
            "Alguien de tu edad te dice que quiere una vida como la tuya. Te ríes, y después te callas.",
        ]
    body = _fit(" ".join(paras), extras)
    return to_tu(body)
