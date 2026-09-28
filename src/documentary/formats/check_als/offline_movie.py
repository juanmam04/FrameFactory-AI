"""Películas cortas para cuando no hay modelo, y para probar el camino hasta el guion.

Cada una es un hilo distinto. El cierre es el que eligió la persona.
"""
from __future__ import annotations

from typing import Any

from src.documentary.formats.check_als.plain_language import PUBLIC_CLOSES

def _movies_from_catalog() -> dict[tuple[str, str], list[str]]:
    from src.documentary.formats.check_als.offline_catalog import CATALOG

    out: dict[tuple[str, str], list[str]] = {}
    for item in CATALOG:
        out.setdefault((item["mode"], item["ending"]), item["paras"])
    return out


MOVIES: dict[tuple[str, str], list[str]] = _movies_from_catalog()



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
    paras: list[str] | None = None,
) -> dict[str, Any]:
    paras = list(paras) if paras is not None else list(MOVIES[(mode, ending)])
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
