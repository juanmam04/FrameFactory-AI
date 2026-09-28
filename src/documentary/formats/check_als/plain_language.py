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
ENFOQUE: una película corta de una vida, para cualquiera.
Una sola línea, fácil de seguir: vives normal, aparece una chance, dices que sí, al principio cuesta, tu vida cambia en cosas que se ven, hay un tropiezo que se entiende sin saber de negocios, y cierra en una escena.
TODA la historia son 8 a 14 escenas. Cada escena se puede filmar: una puerta, una fila, una renuncia, una cena, una noche llena, tus padres ahí.
Los años pasan en una frase ("pasan dos años"). No armes una planilla de temporadas, socios, contratos ni crisis encadenadas.
Un tropiezo, no cinco problemas de categorías distintas.
El dinero entra una sola vez y en palabras de todos los días: pones lo que tienes ahorrado. El trato es simple.
Prohibido como trama: porcentajes, equity, seller financing, servicio de deuda, facturación, valuación, caja, patrimonio, rondas, varios socios con cifras, "millonario en papel".
Si el motor pide ops, son invisibles: una sola vez acquire_team o launch_company, advance_time para que pasen los años, y como mucho season_stretch o new_season para resumir un año en UNA escena. quit_job y move_home cuando la vida cambia.
No uses equity_sale, bridge_loan, pay_debt ni credit_line como argumento. Si aparecen en ops, el texto de la escena sigue siendo vida.
Español de tú (tienes, firmas, vives). Prohibido el voseo.
""".strip()

PUBLIC_EVENT_RULES = """
IDIOMA DE CADA ESCENA (event, cause, consequence, visual_opportunity):
Una frase de vida, en tú. La entiende un chico que sueña y un adulto que quiere pasar un rato ahí.
Prohibido: equity, porcentaje, %, valuación, facturación, caja, ingresos, servicio de la deuda, seller financing, patrimonio, "51%", "millonario", voseo.
El dinero, si sale, es: "pones tus ahorros" o "pagas la cena".
""".strip()


_KEEP_ACCENT = {"además", "atrás", "después", "francés", "inglés", "interés", "país", "maíz", "raíz"}


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
        if picked >= 4:
            break
        line = plain_event(str(beat.get("event") or ""), sports=False)
        if not line or has_jargon(line) or line in " ".join(paras):
            continue
        paras.append(line if line.endswith(".") else line + ".")
        picked += 1
    ending = str(blueprint.get("ending") or "").strip()
    if ending and not has_jargon(ending):
        paras.append(to_tu(ending if ending.endswith(".") else ending + "."))
    else:
        paras.append("El plazo se acaba. Queda una última escena, y ahí se cierra.")
    body = re.sub(r"\s+", " ", " ".join(paras)).strip()
    words = _words(body)
    if len(words) > 520:
        body = " ".join(words[:500]).rstrip(" ,;:") + "."
    return to_tu(body)


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
    picked = 0
    for beat in beats or []:
        if picked >= 4:
            break
        raw = str(beat.get("event") or "").strip()
        if not raw or raw in used:
            continue
        line = plain_event(raw, sports=sports)
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

    if sports:
        paras.append(
            "Pasan los años. Renuncias a la oficina, te mudas más cerca y tus padres vienen a verte. "
            "Hay un tropiezo: el equipo arranca flojo y cuesta dormir. "
            "Después llega una noche en la que el lugar se llena. Desde el túnel los ves arriba."
        )
    else:
        paras.append(
            "Pasan los años. Renuncias al trabajo de antes y te mudas a un cuarto que ya es tuyo. "
            "Tus padres vienen, aunque no entiendan cada detalle. Hay un mes flojo. "
            "Después llega una noche con gente de verdad."
        )
    today = f"Hoy tienes {age1} años. " if age1 else "Hoy "
    paras.append(
        f"{today}Tu día es {job1}. Vives en {home1}. "
        f"{'El estadio' if sports else 'El lugar'} ya no es el cuarto del primer mes."
    )
    body = re.sub(r"\s+", " ", " ".join(paras)).strip()
    words = _words(body)
    if len(words) > 520:
        body = " ".join(words[:500]).rstrip(" ,;:") + "."
    return to_tu(body)
