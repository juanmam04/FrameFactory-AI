#!/usr/bin/env python3
"""Check ALS: full console production ending in final.mp4 with black placeholder stills."""
from __future__ import annotations

import json
import os
import shutil
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


def _step(label: str) -> None:
    print(f"\n{'=' * 60}\n{label}\n{'=' * 60}", flush=True)


def _black_stills(pid: str, n: int) -> Path:
    from PIL import Image

    from src.documentary.project import project_dir

    dest = project_dir(pid) / "flow-import"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for i in range(1, n + 1):
        Image.new("RGB", (1920, 1080), color=(0, 0, 0)).save(dest / f"{i:03d}.png")
    print(f"Wrote {n} black stills → {dest}", flush=True)
    return dest


def _run_existing_pilot(pid: str) -> int:
    from src.documentary.assemble_service import assemble_and_render
    from src.documentary.flow_pack import load_shot_list
    from src.documentary.import_images import import_images, sync_shot_statuses_from_images
    from src.documentary.project import load_project, project_dir, save_project, set_checkpoint
    from src.documentary.voice_service import generate_project_voice
    from src.script_generator import count_words

    p = load_project(pid)
    if not p.get("script_approved"):
        raise SystemExit(f"{pid}: script not approved — run script phase first")
    if not p.get("check_story_approved"):
        raise SystemExit(f"{pid}: story not approved")

    shots = load_shot_list(pid)["shots"]
    n = len(shots)
    script = str(p.get("script") or "")
    print(f"project={pid} shots={n} script_words={count_words(script)}", flush=True)

    _step(f"5/7 Black placeholders ({n} stills)")
    src = _black_stills(pid, n)

    _step("6/7 Import stills")
    report = import_images(load_project(pid), src)
    sync_shot_statuses_from_images(pid)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if int(report.get("ready") or 0) < int(report.get("expected") or n):
        raise SystemExit(f"Import incomplete: {report}")

    _step("7/7 Voice + render")
    p = load_project(pid)
    t0 = time.time()
    audio = generate_project_voice(p)
    print(f"voice → {audio} ({time.time() - t0:.0f}s)", flush=True)

    p = load_project(pid)
    p["ui_step"] = "render"
    set_checkpoint(p, "images_imported", True)
    save_project(p)

    t1 = time.time()
    out = assemble_and_render(load_project(pid))
    print(f"render → {out} ({time.time() - t1:.0f}s)", flush=True)
    if not out or not Path(out).is_file():
        raise SystemExit("Render failed — no final.mp4")
    print(f"\n✅ VIDEO LISTO: {out}", flush=True)
    return 0


def _run_from_scratch(pid: str) -> int:
    from src.documentary.flow_pack import export_flow_pack, load_shot_list
    from src.documentary.formats.check_als.concepts import generate_concept_packages, package_to_project_fields
    from src.documentary.formats.check_als.profile import check_als_profile
    from src.documentary.formats.check_als.script import locked_story_facts, validate_check_script
    from src.documentary.formats.check_als.story_arch import load_architecture
    from src.documentary.formats.check_als.story_architect import approve_check_story, generate_check_story
    from src.documentary.project import create_project, list_projects, load_project, project_dir
    from src.documentary.script_service import approve_script, generate_documentary_script
    from src.script_generator import count_words

    root = project_dir(pid)
    if root.exists():
        shutil.rmtree(root)

    profile = check_als_profile()
    prior = [p for p in list_projects() if str(p.get("id")) != pid]

    _step("1/7 Generating top concept (LLM)")
    packages = generate_concept_packages(
        profile,
        prior_videos=prior,
        count=3,
        use_llm=True,
        raw_seed_count=24,
        story_select_count=10,
    )
    if not packages:
        raise SystemExit("No concepts returned")
    concept = max(packages, key=lambda x: float(x.get("overall_score") or x.get("rank_score") or 0))
    print(f"title={concept.get('title')} score={concept.get('overall_score')}", flush=True)

    fields = package_to_project_fields(concept)
    create_project(
        fields["topic"],
        title=fields["title"],
        project_id=pid,
        language=fields["language"],
        target_duration_min=fields["target_duration_min"],
        target_words=fields["target_words"],
        content_format=fields["content_format"],
        concept=fields["concept"],
        idea=fields["idea"],
    )

    _step("2/7 Story Architecture")
    generate_check_story(load_project(pid), use_llm=True)
    approve_check_story(load_project(pid))

    _step("3/7 Script ES")
    generate_documentary_script(load_project(pid), use_llm=True)
    p = load_project(pid)
    script = str(p.get("script") or "")
    arch = load_architecture(p)
    facts = locked_story_facts(arch)
    ok, hard, warn = validate_check_script(script, facts, strict_length=True)
    print(f"validation={'OK' if ok else 'WARN'} words={count_words(script)} hard={hard} warn={warn}", flush=True)
    approve_script(load_project(pid))

    _step("4/7 Visual plan + Flow pack")
    export_flow_pack(load_project(pid), use_llm=True, rebuild_visuals=True)
    n = len(load_shot_list(pid)["shots"])
    print(f"shots={n}", flush=True)

    return _run_existing_pilot(pid)


def main() -> int:
    _load_env()
    mode = (os.environ.get("CHECK_FULL_MODE") or "pilot").strip().lower()
    pid = os.environ.get("CHECK_FULL_ID") or (
        "pilot-fase2-basket" if mode == "pilot" else "check-console-full-001"
    )
    if mode == "scratch":
        return _run_from_scratch(pid)
    return _run_existing_pilot(pid)


if __name__ == "__main__":
    raise SystemExit(main())
