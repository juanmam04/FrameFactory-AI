"""Una idea del usuario se vuelve un episodio, aunque no sea el formato de siempre."""
from __future__ import annotations

import os
import re
from typing import Any

from src.documentary.formats.check_als.plain_language import to_tu

_ENDINGS = ("victory", "exit", "loss", "dilema", "pyrrhic", "ironic", "open", "plateau")


def user_pov_title(text: str) -> str:
    """Conserva la frase del usuario. Solo la pasa a tú y le pone POV:."""
    raw = re.sub(r"^(pov)\s*[:\-–—]\s*", "", (text or "").strip(), flags=re.I).strip(" .")
    raw = to_tu(raw).strip()
    raw = re.sub(r"\s+", " ", raw)
    if not raw:
        return "POV: Vives esta fantasía"
    raw = raw[0].upper() + raw[1:]
    return f"POV: {raw}"


def adapt_user_idea(text: str, *, use_llm: bool = True) -> dict[str, Any]:
    """Arma un concepto Check fiel a lo que la persona escribió."""
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if len(raw) < 8:
        raise ValueError("Escribe la idea del video, aunque sea una frase.")
    title = user_pov_title(raw)
    package = _fallback_package(raw, title)
    if use_llm and (os.getenv("OPENAI_API_KEY") or "").strip():
        try:
            adapted = _llm_package(raw, title)
            if adapted:
                package.update({k: v for k, v in adapted.items() if v not in (None, "", [], {})})
        except Exception as exc:  # noqa: BLE001
            print(f"[user-idea] llm failed: {exc}", flush=True)
    spoken = to_tu(re.sub(r"^(pov)\s*[:\-–—]\s*", "", raw, flags=re.I)).strip()
    premise = str(package.get("premise") or "")
    if spoken[:48].lower() not in premise.lower():
        package["premise"] = (spoken.rstrip(".") + ". " + premise).strip()
    package["title"] = title
    package["vehicle_type"] = "freeform"
    package["user_proposed"] = True
    ending = str(package.get("ending_type") or "open").strip().lower()
    package["ending_type"] = ending if ending in _ENDINGS else "open"
    if not str(package.get("premise") or "").strip():
        package["premise"] = _fallback_package(raw, package["title"])["premise"]
    package["one_line_fantasy"] = package["title"]
    return package


def _fallback_package(raw: str, title: str) -> dict[str, Any]:
    spoken = to_tu(re.sub(r"^(pov)\s*[:\-–—]\s*", "", raw, flags=re.I)).strip()
    premise = (
        f"{spoken.rstrip('.')}. "
        "La película es exactamente esta idea, en segunda persona. "
        "No la cambies por un equipo, una empresa ni otro oficio. "
        "Empieza en el primer momento, respeta el plazo y las reglas del título, "
        "y cierra cuando el reto se acaba."
    )
    return {
        "id": "user-idea",
        "vehicle_type": "freeform",
        "user_proposed": True,
        "ending_type": "open",
        "title": title,
        "one_line_fantasy": title,
        "premise": premise,
        "hook": spoken,
        "story_category": "idea propia",
        "core_transformation": "Vives el reto hasta el final.",
        "starting_state": "El momento antes de que empiece.",
        "end_state": "El plazo o el reto se acaba.",
        "central_story_question": "¿cómo se siente vivir esto hasta el final?",
    }


def _llm_package(raw: str, title: str) -> dict[str, Any]:
    import json

    from openai import OpenAI

    from src.saas_creative_profile import parse_llm_json_object

    system = (
        "Adaptas una idea suelta a un episodio de Check. "
        "La idea del usuario manda, aunque no sea 'construyes un negocio' ni 'compras un equipo'. "
        "Ejemplo: si dice que tiene 7 días para gastar una fortuna, la historia son esos 7 días gastando, "
        "no una startup ni un club. "
        "Español de tú (tienes, gastas, vives). Prohibido voseo y prohibido planilla (porcentajes, equity, deuda). "
        "La premisa puede fluir: saltos, pausas, una curva. No la escribas como pasos 1, 2 y 3. "
        "Devuelve SOLO JSON con: title, premise (80-140 palabras, segunda persona, fiel a la idea), "
        "hook (3 líneas cortas separadas por \\n\\n), ending_type "
        "(victory|exit|loss|dilema|pyrrhic|ironic|open|plateau, el que mejor calce), "
        "core_transformation, central_story_question. "
        "El title conserva el reto y empieza con 'POV:'."
    )
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        temperature=0.7,
        response_format={"type": "json_object"},
        timeout=45.0,
        max_tokens=1200,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps({"idea": raw, "title_seed": title}, ensure_ascii=False)},
        ],
    )
    parsed = parse_llm_json_object((response.choices[0].message.content or "{}").strip()) or {}
    if not isinstance(parsed, dict):
        return {}
    return parsed
