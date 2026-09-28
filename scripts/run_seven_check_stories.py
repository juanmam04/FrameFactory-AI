"""Siete historias distintas, de la idea al guion, leídas como espectador."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.documentary.formats.check_als.offline_movie import MOVIES, architecture_for
from src.documentary.formats.check_als.plain_language import sports_bleed
from src.documentary.formats.check_als.script import MIN_WORDS, generate_check_script
from src.documentary.formats.check_als.story_architect import approve_check_story, generate_check_story, public_architecture
from src.documentary.project import PROJECTS_ROOT, create_project
from src.script_generator import count_words

CASES = [
    {
        "id": "canal-exito",
        "mode": "creator",
        "ending": "victory",
        "title": "POV: Conviertes un canal chico en una marca",
        "premise": "Conviertes un canal chico de YouTube en una marca, grabando de noche en Madrid.",
        "name": "TechVibe",
        "city": "Madrid",
        "need": ("canal", "video", "patrocin"),
        "ban": ("playoff", "gimnasio", "básquet", "basquet", "utilero", "dueño del equipo"),
        "close": "lo logras",
    },
    {
        "id": "equipo-exito",
        "mode": "sports_team",
        "ending": "victory",
        "title": "POV: Compras un equipo deportivo en crisis",
        "premise": "Compras un equipo al borde del cierre y lo llevas a una noche llena.",
        "name": "Halcones",
        "city": "Puerto Norte",
        "need": ("equipo", "gimnasio"),
        "ban": ("subasta", "canal de youtube"),
        "close": "lo logras",
    },
    {
        "id": "equipo-perdida",
        "mode": "sports_team",
        "ending": "loss",
        "title": "POV: Compras un equipo y lo pierdes",
        "premise": "Compras un equipo cansado y la etapa se cierra en una subasta.",
        "name": "Halcones",
        "city": "Puerto Norte",
        "need": ("subasta", "gimnasio"),
        "ban": ("lo logras",),
        "close": "se cae",
    },
    {
        "id": "siete-dias",
        "mode": "freeform",
        "ending": "victory",
        "title": "POV: Tienes 7 días para gastar un billón de dólares",
        "premise": "Tienes 7 días para gastar un billón de dólares y volver a tu calle.",
        "name": "siete días",
        "city": "",
        "need": ("día", "gast"),
        "ban": ("playoff", "gimnasio", "básquet", "equipo pasa", "startup"),
        "close": "lo logras",
        "user_proposed": True,
    },
    {
        "id": "cocina-cara",
        "mode": "chef",
        "ending": "pyrrhic",
        "title": "POV: Abres un restaurante y llegas arriba",
        "premise": "Abres un restaurante chico y la sala se llena, y el domingo en familia no vuelve.",
        "name": "la esquina",
        "city": "Lima",
        "need": ("cocina", "restaur"),
        "ban": ("playoff", "gimnasio", "básquet", "dueño del equipo"),
        "close": "no vuelve",
    },
    {
        "id": "cancion-ironica",
        "mode": "musician",
        "ending": "ironic",
        "title": "POV: Tu canción se vuelve famosa",
        "premise": "Tu canción de la cocina termina en un anuncio y la gente la canta sin saber tu nombre.",
        "name": "la canción",
        "city": "Buenos Aires",
        "need": ("canción", "anuncio"),
        "ban": ("playoff", "gimnasio", "básquet", "dueño del equipo"),
        "close": "no es como lo imaginabas",
    },
    {
        "id": "estudio-meseta",
        "mode": "business",
        "ending": "plateau",
        "title": "POV: Dejas la oficina y te quedas con un estudio chico",
        "premise": "Dejas la oficina y tu estudio se queda chico, y es tuyo.",
        "name": "el estudio",
        "city": "Ciudad de México",
        "need": ("estudio", "oficina"),
        "ban": ("playoff", "gimnasio", "básquet", "dueño del equipo"),
        "close": "se queda",
    },
]


def _spectator(case: dict, synopsis: str, script: str, times: list[str]) -> list[str]:
    fails: list[str] = []
    blob = f"{synopsis}\n{script}".lower()
    script_l = script.lower()
    for word in case["need"]:
        if word not in script_l:
            fails.append(f"al guion le falta «{word}»")
    for word in case["ban"]:
        if word in blob:
            fails.append(f"aparece «{word}» y esta historia no es eso")
    if case["close"] not in script_l:
        fails.append(f"el cierre no se siente como «{case['close']}»")
    if case["mode"] != "sports_team" and sports_bleed(script):
        fails.append("el guion se va al básquet")
    if re.search(r"\b(tenés|tenes|sos|vos)\b", script_l) or any(
        v in script_l for v in ("equity", "51%", "servicio de la deuda")
    ):
        fails.append("voseo o planilla")
    if "bloqueas" in script_l and case["ending"] != "open":
        fails.append("el final se volvió el teléfono de mañana")
    if len(times) < 5:
        fails.append("la línea de tiempo quedó corta")
    if times and len(set(times)) < 3:
        fails.append("el tiempo no avanza")
    if count_words(script) < MIN_WORDS:
        fails.append(f"el guion es corto para un video largo ({count_words(script)} palabras)")
    # La sinopsis tiene que hablar de lo mismo que el guion.
    if case["need"][0] not in synopsis.lower() and case["mode"] != "business":
        fails.append("la sinopsis no cuenta la misma película")
    return fails


def main() -> int:
    root = ROOT / "data" / "seven-stories"
    if root.exists():
        import shutil

        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    import os

    os.environ["FRAMEFACTORY_PROJECTS_DIR"] = str(root)
    import src.documentary.project as project_mod

    project_mod.PROJECTS_ROOT = root

    opened = []
    failed = 0
    print("SIETE HISTORIAS — idea, arquitectura, sinopsis, tiempo, guion\n")
    for i, case in enumerate(CASES, start=1):
        print("=" * 72)
        print(f"{i}. {case['title']}")
        arch = architecture_for(
            mode=case["mode"],
            ending=case["ending"],
            title=case["title"],
            premise=case["premise"],
            name=case["name"],
            city=case["city"],
        )
        project = create_project(
            case["premise"],
            title=case["title"],
            content_format="check_als",
            language="es",
            project_id=case["id"],
        )
        project["vehicle_type"] = case["mode"]
        project["check_ending_type"] = case["ending"]
        project["concept"] = {
            "title": case["title"],
            "premise": case["premise"],
            "vehicle_type": case["mode"],
            "ending_type": case["ending"],
            "user_proposed": bool(case.get("user_proposed")),
        }
        if case.get("user_proposed"):
            project["user_proposed"] = True
        print(f"  paso idea     vehículo={case['mode']}  final={case['ending']}")
        project = generate_check_story(project, architecture=arch)
        public = public_architecture(project)
        synopsis = str(public.get("synopsis") or "")
        timeline = (public.get("review") or {}).get("timeline") or []
        times = [str(row.get("time") or "") for row in timeline]
        events = [str(row.get("event") or "")[:90] for row in timeline[:6]]
        print(f"  paso historia beats={public.get('beat_count')}  sinopsis={count_words(synopsis)} palabras")
        print(f"  paso tiempo   {' · '.join(times[:8])}")
        for ev in events:
            print(f"    · {ev}")
        project = approve_check_story(project)
        project = generate_check_script(project, use_llm=False)
        script = str(project.get("script") or "")
        public = public_architecture(project)
        flags = (public.get("quality") or {}).get("flags") or []
        scores = (public.get("quality") or {}).get("scores") or {}
        script_warn = [w for w in (project.get("script_warnings") or []) if w]
        print(f"  paso guion    {count_words(script)} palabras")
        print(f"  paso calidad  flags={len(flags)}  scores={scores}")
        fails = _spectator(case, synopsis, script, times)
        for f in flags:
            fails.append(f"error [{f.get('code')}] {f.get('detail')}")
        for key, val in scores.items():
            if val in ("flag", "fail"):
                fails.append(f"marca {key}={val}")
        for w in script_warn:
            if "LLM fallback" in str(w):
                continue
            fails.append(f"guion {w}")
        # Que no sea la misma película que otra.
        head = " ".join(script.split()[:28])
        if head in opened:
            fails.append("empieza igual que otra historia")
        opened.append(head)
        if fails:
            failed += 1
            print("  ESPECTADOR    no me quedo:")
            for f in fails:
                print(f"    - {f}")
        else:
            print("  ESPECTADOR    me quedo. Es esta vida, con este cierre.")
        print()
        out = root / f"{case['id']}.txt"
        out.write_text(synopsis + "\n\n----- GUION -----\n\n" + script, encoding="utf-8")
    print("=" * 72)
    if failed:
        print(f"SIGUE MAL: {failed} de {len(CASES)} no pasan como espectador.")
        return 1
    print(f"LISTO: las {len(CASES)} se leen como películas distintas hasta el guion.")
    print("biblioteca", len(MOVIES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
