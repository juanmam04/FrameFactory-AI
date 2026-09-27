"""Studio batch: 5 Check concepts in one or two LLM calls, always diverse."""
from __future__ import annotations

import json
import os
import random
from typing import Any

from src.saas_creative_profile import parse_llm_json_object

ENDING_TAILS = {
    "victory": (
        "Años después llegas al tope. El lugar queda en silencio después del logro. "
        "Ya lo conseguiste. Ahora qué."
    ),
    "exit": (
        "Al final firmas la venta. Entregas las llaves el último día. "
        "Sales por última vez."
    ),
    "loss": (
        "Al final se cae. La deuda o el competidor te saca del mapa. "
        "Solo quedan las fotos y lo que aprendiste haciendo, no una moraleja."
    ),
    "dilema": (
        "Al final hay dos ofertas que no se pueden tener juntas. "
        "Tienes un plazo corto. Decides mañana."
    ),
    "pyrrhic": (
        "Llegas a la cima, pero el costo personal ya no se recupera. "
        "Ganaste. Eso que perdiste no vuelve."
    ),
    "ironic": (
        "Consigues exactamente lo que querías, pero no como lo imaginabas. "
        "Resulta que el control no era tuyo."
    ),
    "open": (
        "El lugar queda vacío. En el teléfono hay una oferta nueva. "
        "Bloqueas. Mañana lo lees."
    ),
    "plateau": (
        "No es el imperio que soñabas ni un fracaso. Es estable, concreto, repetible. "
        "Esto es. No más. No menos."
    ),
}


def generate_fast_concept_batch(
    profile: dict[str, Any] | None,
    *,
    prior_videos: list[dict[str, Any]] | None = None,
    count: int = 5,
    use_llm: bool = True,
) -> list[dict[str, Any]]:
    """Return exactly `count` concepts. Distinct vehicles and distinct endings."""
    target = max(1, min(8, int(count)))
    slots = _slots(target, list(prior_videos or []))
    raw_rows: list[dict[str, Any]] = []
    if use_llm and (os.getenv("OPENAI_API_KEY") or "").strip():
        try:
            raw_rows = _llm_packages(profile or {}, slots, list(prior_videos or []))
        except Exception as exc:  # noqa: BLE001
            print(f"[fast-concepts] llm failed: {exc}", flush=True)
            raw_rows = []
    packages = []
    for i, slot in enumerate(slots):
        row = raw_rows[i] if i < len(raw_rows) and isinstance(raw_rows[i], dict) else {}
        if _too_thin(row):
            row = _fallback_package(slot, i)
        row["vehicle_type"] = slot["vehicle_type"]
        row["ending_type"] = slot["ending_type"]
        row["id"] = str(row.get("id") or f"{slot['vehicle_type']}-{slot['ending_type']}-{i+1}")
        from src.documentary.formats.check_als.concepts import normalize_concept_package

        packages.append(normalize_concept_package(row))
    return packages


def _slots(count: int, prior: list[dict[str, Any]]) -> list[dict[str, str]]:
    from src.documentary.formats.check_als.ending_types import ENDING_TYPES
    from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES

    used = " ".join(
        str((v.get("title") or "") + " " + str(v.get("topic") or ""))
        for v in prior[-30:]
    ).lower()
    vehicles = list(UNIVERSAL_VEHICLES.keys())
    random.shuffle(vehicles)
    fresh = [v for v in vehicles if v.replace("_", " ") not in used]
    ordered = fresh + [v for v in vehicles if v not in fresh]
    endings = list(ENDING_TYPES.keys())
    random.shuffle(endings)
    return [
        {"vehicle_type": ordered[i % len(ordered)], "ending_type": endings[i % len(endings)]}
        for i in range(count)
    ]


def _llm_packages(
    profile: dict[str, Any],
    slots: list[dict[str, str]],
    prior: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    from openai import OpenAI

    from src.documentary.formats.check_als.ending_types import ENDING_TYPES
    from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES

    assignments = []
    for i, slot in enumerate(slots, 1):
        vehicle = UNIVERSAL_VEHICLES[slot["vehicle_type"]]
        ending = ENDING_TYPES[slot["ending_type"]]
        assignments.append(
            {
                "index": i,
                "vehicle_type": slot["vehicle_type"],
                "vehicle_name": vehicle["name"],
                "vehicle": vehicle["vehicle"],
                "acquisition": vehicle["acquisition"],
                "metrics": vehicle["metrics"][:4],
                "ending_type": slot["ending_type"],
                "ending_name": ending["name"],
                "ending_beat": ENDING_TAILS[slot["ending_type"]],
            }
        )
    system = (
        "Escribes paquetes de Check: fantasías aspiracionales en ESPAÑOL, segunda persona (tú/te/tienes). "
        "Nunca vos/sos/tenés. Nunca moraleja ni CTA. "
        "Devuelve SOLO JSON: {\"packages\": [ ... ]} con EXACTAMENTE un package por assignment, en el mismo orden. "
        "Cada package usa SU vehicle_type y SU ending_type. No los repitas ni los cambies. "
        "La premisa tiene que ser de ESE oficio (si es chef, cocina; si es músico, música; prohibido meter básquet "
        "salvo vehicle_type=sports_team). El último tramo de la premisa es el cierre indicado, no un final abierto genérico. "
        "Campos por package: id, vehicle_type, ending_type, title, one_line_fantasy, premise (120-180 palabras), "
        "hook (4 líneas cortas separadas por \\n\\n), starting_state, end_state, core_transformation, story_category, "
        "thumbnail_concept {main_visual, central_contrast, emotion, thumbnail_prompt en inglés, una frase}."
    )
    user = {
        "assignments": assignments,
        "avoid_repeating": [
            str(v.get("title") or v.get("topic") or "")[:80] for v in prior[-12:]
        ],
        "channel": (profile.get("channel") or {}).get("name") if isinstance(profile.get("channel"), dict) else "",
    }
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    parsed = _once(client, model, system, user, timeout=120.0)
    rows = _rows(parsed)
    if len(rows) < len(slots):
        missing = assignments[len(rows) :]
        try:
            extra = _once(
                client,
                model,
                system,
                {"assignments": missing, "note": "Solo estos huecos. Mismo formato."},
                timeout=90.0,
            )
            rows.extend(_rows(extra))
        except Exception as exc:  # noqa: BLE001
            print(f"[fast-concepts] fill failed: {exc}", flush=True)
    return rows


def _once(client: Any, model: str, system: str, user: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        temperature=0.9,
        timeout=timeout,
        max_tokens=6500,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    )
    return parse_llm_json_object((response.choices[0].message.content or "{}").strip()) or {}


def _rows(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    rows = parsed.get("packages") if isinstance(parsed, dict) else None
    if not isinstance(rows, list):
        rows = parsed.get("concepts") if isinstance(parsed, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _too_thin(row: dict[str, Any]) -> bool:
    premise = str(row.get("premise") or row.get("story") or "").strip()
    title = str(row.get("title") or row.get("title_concept") or "").strip()
    return len(premise.split()) < 40 or len(title) < 8


def _fallback_package(slot: dict[str, str], index: int) -> dict[str, Any]:
    from src.documentary.formats.check_als.universal_vehicles import UNIVERSAL_VEHICLES

    vehicle = UNIVERSAL_VEHICLES[slot["vehicle_type"]]
    ending = slot["ending_type"]
    name = vehicle["name"]
    thing = vehicle["vehicle"]
    start = vehicle["acquisition"]
    metric = vehicle["metrics"][0] if vehicle["metrics"] else "progreso"
    tail = ENDING_TAILS[ending]
    title = f"POV: {name} — de cero a {metric}"
    premise = (
        f"Tienes 23 años. Trabajas en algo que no es tuyo y compartes departamento. "
        f"Tienes 12.000 dólares ahorrados. Aparece la chance de {start} en {thing}. "
        f"Pones tu plata, consigues socios y te quedas con el 60%. "
        f"El primer año es largo: clientes que no pagan, noches cortas, el trabajo de día todavía ahí. "
        f"Después llega la primera prueba real, con números, no con discursos. "
        f"Pasan cuatro años. Renuncias. Te mudas. La gente empieza a buscarte. "
        f"En papel el proyecto vale millones. En tu cuenta personal queda poco. "
        f"{tail}"
    )
    hook = (
        f"Tienes 23 años.\n\n"
        f"Compartes departamento y tienes 12.000 dólares.\n\n"
        f"Alguien te ofrece {start}.\n\n"
        f"Firmas."
    )
    return {
        "id": f"fallback-{slot['vehicle_type']}-{ending}-{index+1}",
        "vehicle_type": slot["vehicle_type"],
        "ending_type": ending,
        "title": title[:90],
        "one_line_fantasy": f"Pasas de empleado a {name.lower()} y el cierre es {ending}.",
        "premise": premise,
        "hook": hook,
        "starting_state": "23 años · departamento compartido · 12.000 dólares · trabajo de otros",
        "end_state": f"{name}. Cuatro años después. Cierre: {ending}.",
        "core_transformation": f"De empleado anónimo a {name.lower()}, con un cierre de tipo {ending}.",
        "story_category": slot["vehicle_type"],
        "thumbnail_concept": {
            "main_visual": f"Protagonista stickman al inicio de {thing}, contraste con el resultado final",
            "central_contrast": "departamento compartido contra el lugar del éxito",
            "emotion": "ambición concreta",
            "thumbnail_prompt": (
                f"High-quality 2D stickman cartoon, {thing}, bold outlines, detailed environment, no text."
            ),
        },
    }
