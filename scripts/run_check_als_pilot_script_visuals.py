"""Check production: approved story → ES script → visual plan + image prompts. STOP (no voice/render)."""
from __future__ import annotations

import json
import os
import sys
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
    from src.documentary.flow_pack import export_flow_pack
    from src.documentary.formats.check_als.script import (
        estimate_duration_min,
        retention_flags,
        script_sections,
        validate_check_script,
        locked_story_facts,
    )
    from src.documentary.formats.check_als.story_arch import load_architecture
    from src.documentary.formats.check_als.story_architect import approve_check_story
    from src.documentary.project import load_project, project_dir, save_project
    from src.documentary.script_service import approve_script, generate_documentary_script
    from src.script_generator import count_words

    pid = os.environ.get("CHECK_PILOT_ID", "pilot-fase2-basket")
    p = load_project(pid)
    print(f"project={pid} story_generated={bool((p.get('check_story') or {}).get('generated'))}", flush=True)

    if not p.get("check_story_approved"):
        print("Aprobando Story Architecture (sin regenerar)…", flush=True)
        p = approve_check_story(p)
    else:
        print("Story ya aprobada.", flush=True)

    print("Generando script ES (tú/te)…", flush=True)
    p = generate_documentary_script(p, use_llm=True)
    script = str(p.get("script") or "")
    wc = count_words(script)
    print(f"script words={wc} duration_min≈{estimate_duration_min(wc)}", flush=True)

    arch = load_architecture(p)
    facts = locked_story_facts(arch)
    ok, hard, warn = validate_check_script(script, facts, strict_length=True)
    print("validation", "OK" if ok else "FAIL", hard, warn, flush=True)
    if not ok:
        print("STOP: script no pasó validación. No visual plan.", flush=True)
        return 1

    print("Aprobando script internamente y construyendo Visual Plan + prompts…", flush=True)
    p = approve_script(load_project(pid))
    p = export_flow_pack(p, use_llm=True, rebuild_visuals=True)
    p = load_project(pid)

    root = project_dir(pid)
    plan_path = root / "flow-pack" / "visual-plan.json"
    prompts_path = root / "flow-pack" / "image-prompts.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    scenes = json.loads(prompts_path.read_text(encoding="utf-8")) if prompts_path.exists() else plan.get("image_prompts") or []
    stats = plan.get("stats") or {}
    qc = plan.get("qc") or {}

    report = {
        "stop": "SCRIPT + VISUAL PLAN + IMAGE PROMPTS. No voice. No music. No render. No captions.",
        "script": {
            "words": wc,
            "estimated_duration_min": estimate_duration_min(wc),
            "sections": script_sections(script),
            "retention_flags": retention_flags(script),
            "validation_hard": hard,
            "validation_warnings": warn,
        },
        "visual_plan_summary": {
            "scene_count": stats.get("scene_count") or len(scenes),
            "unique_locations": stats.get("unique_locations"),
            "characters": stats.get("characters"),
            "timeline": stats.get("timeline"),
        },
        "qc": {
            "script_continuity": hard,
            "numbers": facts.get("acquisition"),
            "championships": facts.get("championships"),
            "pov": "second_person_tu",
            "visual": qc,
        },
        "paths": {
            "script": "script/script.txt",
            "script_meta": "script/script_meta.json",
            "visual_plan": "flow-pack/visual-plan.json",
            "image_prompts": "flow-pack/image-prompts.json",
            "shot_list": "flow-pack/shot-list.json",
        },
    }
    (root / "script" / "production_qc.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    p["ui_step"] = "flow"
    save_project(p)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    print("STOP. Revisá el guion y los prompts. No se genera voz ni stills.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
