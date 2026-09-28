"""Veinte vidas, de la idea al guion, leídas como si fueran la tuya."""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.documentary.formats.check_als.offline_catalog import CATALOG
from src.documentary.formats.check_als.offline_movie import architecture_for
from src.documentary.formats.check_als.plain_language import sports_bleed
from src.documentary.formats.check_als.script import generate_check_script
from src.documentary.formats.check_als.story_architect import approve_check_story, generate_check_story, public_architecture
from src.documentary.project import create_project
from src.script_generator import count_words


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
    if not re.search(r"\d", script):
        fails.append("no hay una sola cifra")
    if len(times) < 5:
        fails.append("la línea de tiempo quedó corta")
    if times and len(set(times)) < 3:
        fails.append("el tiempo no avanza")
    if count_words(script) < 320:
        fails.append("el guion es demasiado corto para quedarse")
    if case["need"][0] not in synopsis.lower():
        fails.append("la sinopsis no cuenta la misma película")
    return fails


def main() -> int:
    root = ROOT / "data" / "twenty-stories"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    os.environ["FRAMEFACTORY_PROJECTS_DIR"] = str(root)
    import src.documentary.project as project_mod

    project_mod.PROJECTS_ROOT = root

    opened = []
    failed = 0
    print(f"VEINTE VIDAS — {len(CATALOG)} ideas, de la premisa al guion\n")
    for i, case in enumerate(CATALOG, start=1):
        print("=" * 72)
        print(f"{i}. {case['title']}")
        arch = architecture_for(
            mode=case["mode"],
            ending=case["ending"],
            title=case["title"],
            premise=case["premise"],
            name=case["name"],
            city=case["city"],
            paras=case["paras"],
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
        project = generate_check_story(project, architecture=arch)
        public = public_architecture(project)
        synopsis = str(public.get("synopsis") or "")
        timeline = (public.get("review") or {}).get("timeline") or []
        times = [str(row.get("time") or "") for row in timeline]
        project = approve_check_story(project)
        project = generate_check_script(project, use_llm=False)
        script = str(project.get("script") or "")
        public = public_architecture(project)
        flags = (public.get("quality") or {}).get("flags") or []
        scores = (public.get("quality") or {}).get("scores") or {}
        script_warn = [w for w in (project.get("script_warnings") or []) if w]
        print(f"  guion {count_words(script)} palabras  flags={len(flags)}")
        fails = _spectator(case, synopsis, script, times)
        for f in flags:
            fails.append(f"error [{f.get('code')}] {f.get('detail')}")
        for key, val in scores.items():
            if val in ("flag", "fail"):
                fails.append(f"marca {key}={val}")
        for w in script_warn:
            if "LLM fallback" in str(w) or "draft corto" in str(w):
                continue
            fails.append(f"guion {w}")
        head = " ".join(script.split()[:24])
        if head in opened:
            fails.append("empieza igual que otra historia")
        opened.append(head)
        if fails:
            failed += 1
            print("  NO ME QUEDO")
            for f in fails:
                print(f"    - {f}")
        else:
            print("  me quedo")
        out = root / f"{i:02d}-{case['id']}.txt"
        out.write_text(synopsis + "\n\n----- GUION -----\n\n" + script, encoding="utf-8")
    print("=" * 72)
    if failed:
        print(f"SIGUE MAL: {failed} de {len(CATALOG)}")
        return 1
    print(f"LISTO: las {len(CATALOG)} se sienten como vidas distintas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
