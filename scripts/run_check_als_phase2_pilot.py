"""Fase 2 console test: Story Architecture on the basketball pilot. Does not continue to script."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_env() -> None:
    for name in (".env", ".env.local"):
        env = ROOT / name
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if not k:
                continue
            if name.endswith(".local") or k not in os.environ:
                os.environ[k] = v


def main() -> int:
    _load_env()
    from src.documentary.formats.check_als.story_arch import load_architecture
    from src.documentary.formats.check_als.story_architect import generate_check_story
    from src.documentary.formats.check_als.story_validate import assemble_review, format_pilot_report
    from src.documentary.project import create_project, load_project, project_dir, save_project

    title = "POV: Compras un equipo de básquet al borde de la quiebra"
    premise = (
        "Eres joven. Tienes una vida normal. Sueñas con tener un equipo. "
        "Aparece la oportunidad de adquirir uno casi quebrado. Te conviertes en propietario. "
        "Intentas reconstruirlo. El equipo y tu vida evolucionan."
    )
    concept = {
        "title": title,
        "premise": premise,
        "one_line_fantasy": "Comprar un equipo de básquet al borde de la quiebra y reconstruirlo",
        "starting_state": "22 años, trabajo de oficina, ahorros modestos, fanático del básquet",
        "end_state": "propietario de un equipo vivo, vida distinta, sin moraleja",
        "story_core_id": "del-basket-a-la-primera",
        "story_engine": {
            "note": "NO reutilizar un spine previo. Conservar solo la fantasía central."
        },
    }
    pid = "pilot-fase2-basket"
    try:
        project = create_project(
            premise,
            title=title,
            project_id=pid,
            language="es",
            content_format="check_als",
            concept=concept,
            target_duration_min=[12, 18],
            target_words=2200,
        )
    except FileExistsError:
        project = load_project(pid)
        project["concept"] = concept
        project["title"] = title
        project["topic"] = premise
        project["content_format"] = "check_als"
        project["check_story_approved"] = False
        project["check_story"] = {}
        project["story_plan_approved"] = False
        project["ui_step"] = "story"
        save_project(project)
        meta = project_dir(pid) / "metadata"
        for name in (
            "story_blueprint.json",
            "world_state.json",
            "story_state.json",
            "progression_state.json",
            "beats.json",
            "story_quality.json",
            "story_review.json",
            "story_synopsis.md",
        ):
            path = meta / name
            if path.exists():
                path.unlink()

    print("Generando Story Architecture Fase 2.2 (blueprint + beats + sports/finance)…", flush=True)
    t0 = time.time()
    project = generate_check_story(project, use_llm=True)
    elapsed = time.time() - t0
    project = load_project(pid)
    arch = load_architecture(project)
    review = arch.get("review") or assemble_review(arch)
    report = format_pilot_report(arch, review)

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "check-als-phase2-pilot.txt").write_text(report, encoding="utf-8")
    (docs / "check-als-phase2-pilot.json").write_text(
        json.dumps(
            {
                "project_id": pid,
                "elapsed_s": round(elapsed, 1),
                "beat_count": len(arch.get("beats") or []),
                "synopsis_words": len((arch.get("synopsis") or "").split()),
                "quality": arch.get("quality") or {},
                "final_world": review.get("final_world"),
                "pipeline_stop": "human_review",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(report)
    print(f"\nTiempo: {elapsed:.1f}s", flush=True)
    print(f"Proyecto: {project_dir(pid)}", flush=True)
    print("STOP. No script. No visuals. No voice. No render.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
