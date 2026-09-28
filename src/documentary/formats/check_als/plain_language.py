"""Texto que lee la gente en Check: una vida en tú, sin planilla."""
from __future__ import annotations

import re
from typing import Any

_VOSEO = (
    (r"\bTenés\b", "Tienes"),
    (r"\btenés\b", "tienes"),
    (r"\bTenes\b", "Tienes"),
    (r"\btenes\b", "tienes"),
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

SIMPLE_STORY_BRIEF = """
ENFOQUE: una película corta que se entiende, y que fluye.
Hay un hilo claro, pero no es una lista. El ritmo cambia: una escena lenta, un salto de tiempo, un detalle chico, una vuelta que no estaba anunciada.
Cada escena sale de la anterior. Puede torcerse. No repitas el mismo molde (oficina, firmas, vacío, padres, noche llena) si la idea pide otra curva.
Unas 8 a 14 escenas en total, las que la historia necesite. Cada una se puede filmar.
El tiempo pasa dentro de la escena ("a la semana", "dos años después", "esa misma noche"), no como un informe.
Un tropiezo que se siente, no cinco crisis de manual.
La gente se queda porque esa vida tiene peso de verdad. Un video con visitas, un contrato o un mueble son EJEMPLOS del tipo de detalle. No son una lista para repetir en todas las historias, y no alcanzan solos.
Inventas los detalles que ESA vida tendría, muchos y distintos en cada escena. Mezcla, según el oficio: una hora exacta, alguien con nombre y un tic, una comida, un audio, un objeto gastado, el camino de esa mañana, el clima, el cuerpo (una mancha, una quemadura, el sueño), una mentira chica, quién te reconoce y quién no, la plata pequeña además de la cifra grande, lo que queda en la mesa al apagar, la ropa que se repite, el grupo del teléfono, un olor, una canción, un número de camiseta, cómo tu madre dice mal el nombre. Si una escena ya mostró la casa, la siguiente muestra otra cosa.
El dinero de esa vida se dice con cifras de todos los días. No manda la trama: la trama es la vida.
Prohibido como trama: porcentajes, equity, equity_sale, seller financing, servicio de deuda, facturación, valuación, caja, patrimonio, rondas, "millonario en papel". Nada de planilla.
Ops invisibles y pocas. El texto es vida, en tú. Prohibido el voseo.
""".strip()

PUBLIC_EVENT_RULES = """
IDIOMA DE CADA ESCENA (event, cause, consequence, visual_opportunity):
Una frase de vida, en tú. La entiende un chico que sueña y un adulto que quiere pasar un rato ahí.
Prohibido: equity, porcentaje, %, valuación, facturación, caja, ingresos, servicio de la deuda, seller financing, patrimonio, "51%", "millonario", voseo.
El dinero de la vida sí se dice, en la escala de esa historia: una cifra grande y también la chica (el café, el bus, el alquiler de esa semana).
Cada escena suma un detalle filmable distinto del anterior. Inventalo para ESA vida: un nombre, una hora, un tic, un audio, una mancha, un olor, un camino, el clima, la ropa, lo que alguien dice mal. No copies de memoria el mismo sofá, el mismo setup y la misma foto.
""".strip()


_KEEP_ACCENT = {
    "además",
    "atrás",
    "después",
    "estás",
    "francés",
    "inglés",
    "interés",
    "más",
    "país",
    "maíz",
    "raíz",
}


def to_tu(text: str) -> str:
    out = str(text or "")
    for pat, rep in _VOSEO:
        out = re.sub(pat, rep, out)

    def _end(match: re.Match[str]) -> str:
        word = match.group(0)
        if word.lower() in _KEEP_ACCENT:
            return word
        stem, end = match.group(1), match.group(2)
        if end == "ás":
            return stem + "as"
        if end == "és":
            return stem + "es"
        return stem + "es"

    return re.sub(r"\b(\w{2,})(ás|és|ís)\b", _end, out)


def has_jargon(text: str) -> bool:
    return bool(_JARGON.search(str(text or "")))


_SPORTS_BLEED = re.compile(
    r"equipo pasa a ser|gimnasio|playoffs?|básquet|basquet|dueño del equipo|dueño del club|"
    r"mejores jugadores|utilería|cuentas pesadas|el club llega|juegas al básquet|juegas al basquet|"
    r"el equipo cierra|el equipo arranca|no hay playoffs|canasta|vestuario",
    re.I,
)


def sports_bleed(text: str) -> bool:
    return bool(_SPORTS_BLEED.search(str(text or "")))


def drop_sports_bleed(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", str(text or "").strip())
    kept = [p.strip() for p in parts if p.strip() and not _SPORTS_BLEED.search(p)]
    return " ".join(kept).strip()


def clean_non_sports(text: str) -> str:
    t = drop_sports_bleed(text)
    t = re.sub(r"cuarto de utilería en el estadio", "cuarto de grabación", t, flags=re.I)
    t = re.sub(r"dueño del equipo|dueño del club", "tu propio trabajo", t, flags=re.I)
    t = re.sub(r"a cuatro cuadras de la arena", "propio", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


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


def _freeform_synopsis(
    blueprint: dict[str, Any],
    beats: list[dict[str, Any]],
) -> str:
    seed = str(
        blueprint.get("user_premise")
        or (blueprint.get("opening") or {}).get("situation")
        or (blueprint.get("fantasy") or {}).get("surface_desire")
        or ""
    ).strip()
    paras = []
    if seed:
        paras.append(to_tu(seed if seed.endswith(".") else seed + "."))
    else:
        paras.append("Empieza el reto tal como lo pensaste.")
    picked = 0
    for beat in beats or []:
        if picked >= 8:
            break
        line = plain_event(str(beat.get("event") or ""), sports=False)
        if not line or has_jargon(line) or line in " ".join(paras):
            continue
        paras.append(line if line.endswith(".") else line + ".")
        picked += 1
    ending_key = str(blueprint.get("narrative_ending") or "").strip().lower()
    close = PUBLIC_CLOSES.get(ending_key)
    ending = str(blueprint.get("ending") or "").strip()
    if close:
        paras.append(close)
    elif ending and not has_jargon(ending):
        paras.append(to_tu(ending if ending.endswith(".") else ending + "."))
    elif picked == 0:
        paras.append("La historia encuentra su curva y se cierra en una escena, no en un resumen.")
    body = re.sub(r"\s+", " ", " ".join(paras)).strip()
    words = _words(body)
    if len(words) > 1500:
        body = " ".join(words[:1450]).rstrip(" ,;:") + "."
    return to_tu(body)


PUBLIC_CLOSES = {
    "victory": "Al final lo logras. El lugar se llena y esa vida sigue siendo tuya.",
    "exit": "Al final lo vendes en tus términos y te vas.",
    "loss": "Al final se cae. Se cierra esa etapa.",
    "dilema": "Al final hay dos caminos. Decides mañana.",
    "pyrrhic": "Llegas arriba, y algo de lo que dejas atrás no vuelve.",
    "ironic": "Consigues lo que querías, y no es como lo imaginabas.",
    "open": "Queda algo abierto. Mañana lo miras.",
    "plateau": "No explota ni se cae. Se queda, y es tuyo.",
}


def public_life_synopsis(
    blueprint: dict[str, Any],
    beats: list[dict[str, Any]],
    initial: dict[str, Any],
    final: dict[str, Any],
    *,
    vehicle_mode: str = "sports_team",
) -> str:
    if vehicle_mode == "freeform" or blueprint.get("freeform"):
        return _freeform_synopsis(blueprint, beats)
    sports_state = (final or {}).get("sports") or {}
    sports = vehicle_mode == "sports_team"
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

    if sports:
        paras = [open_para, plain_deal_sentence(sports=True)]
    elif vehicle_mode == "creator":
        paras = [
            open_para,
            "Grabas en tu cuarto. El canal es chico y casi nadie comenta. Sigues subiendo igual.",
        ]
    else:
        paras = [open_para, plain_deal_sentence(sports=False)]
    used: set[str] = set()
    picked = 0
    for beat in beats or []:
        if picked >= 8:
            break
        raw = str(beat.get("event") or "").strip()
        if not raw or raw in used:
            continue
        line = plain_event(raw, sports=sports)
        if not sports:
            line = clean_non_sports(line)
        if not line or has_jargon(line) or line in " ".join(paras):
            continue
        if line == plain_deal_sentence(sports=sports):
            continue
        paras.append(line if line.endswith(".") else line + ".")
        used.add(raw)
        picked += 1

    hist = [h for h in (sports_state.get("season_history") or []) if isinstance(h, dict)]
    seasons = _season_lines(hist, sports=sports)
    if len(seasons) > 2:
        seasons = [seasons[0], seasons[-1]]
    paras.extend(seasons)

    ending_key = str(blueprint.get("narrative_ending") or "").strip().lower()
    close = PUBLIC_CLOSES.get(ending_key)
    rich = picked >= 4
    if rich:
        paras = paras[2:] if len(paras) > 2 else paras
        if close and close.lower() not in " ".join(paras).lower():
            paras.append(close)
        body = re.sub(r"\s+", " ", " ".join(paras)).strip()
        words = _words(body)
        if len(words) > 1500:
            body = " ".join(words[:1450]).rstrip(" ,;:") + "."
        return to_tu(body)
    if sports:
        if ending_key == "loss":
            paras.append(
                "No todo llega en orden. Una tarde renuncias sin discurso, otra tus padres aparecen en la puerta, "
                "hay una semana floja que cuesta, y el lugar se vacía."
            )
        else:
            paras.append(
                "No todo llega en orden. Una tarde renuncias sin discurso, otra tus padres aparecen en la puerta, "
                "hay una semana floja que cuesta, y de pronto el lugar se llena sin que lo hubieras anotado."
            )
    else:
        paras.append(
            "No todo llega en orden. Renuncias un martes cualquiera, tus padres aparecen cuando no los esperabas, "
            "hay un mes flojo, y una noche entra gente de verdad."
        )
    today = f"Hoy tienes {age1} años. " if age1 else "Hoy "
    paras.append(
        f"{today}Tu día es {job1}. Vives en {home1}. "
        f"{'El estadio' if sports else 'El lugar'} ya no es el cuarto del primer mes."
    )
    if close:
        paras.append(close)
    body = re.sub(r"\s+", " ", " ".join(paras)).strip()
    words = _words(body)
    if len(words) > 1500:
        body = " ".join(words[:1450]).rstrip(" ,;:") + "."
    return to_tu(body)
