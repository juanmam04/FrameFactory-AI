#!/usr/bin/env python3
"""Offline smoke: Session channel → ideas → project → flow → import → auto-status → mock voice skip → preview.

Does not spend API credits. Uses mock script + heuristic Flow Pack.
Optional: set SMOKE_RENDER=1 to attempt FFmpeg if ffmpeg + silent mp3 available.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from src.documentary.channel import business_documentary_profile, is_documentary_profile
from src.documentary.flow_pack import export_flow_pack, load_shot_list
from src.documentary.ideas import generate_story_ideas
from src.documentary.import_images import import_images, sync_shot_statuses_from_images
from src.documentary.project import (
    PROJECTS_ROOT,
    create_project,
    derive_progress,
    load_project,
    project_dir,
    session_stats,
)
from src.documentary.script_service import approve_script, generate_documentary_script


def main() -> int:
    sid = "smoke-100-days-session"
    profile = business_documentary_profile()
    assert is_documentary_profile(profile)

    ideas = generate_story_ideas(profile, prior_videos=[], count=5, use_llm=False)
    print(f"ideas={len(ideas)} first={ideas[0]['title_concept'][:60]}")

    idea = ideas[0]
    pid = "smoke-daily-001"
    # clean prior smoke project
    import shutil

    target = PROJECTS_ROOT / pid
    if target.exists():
        shutil.rmtree(target)

    project = create_project(
        idea.get("story") or idea["title_concept"],
        title=idea["title_concept"],
        project_id=pid,
        target_words=400,
        research_notes="MOCK: SoftBank invested. IPO attempt collapsed in 2019. UNKNOWN: exact peak valuation.",
        sources=["Public reporting (mock)"],
        session_id=sid,
        creative_profile=profile,
        idea=idea,
        episode_number=1,
    )
    print(f"created {project['id']} session={project['session_id']}")

    generate_documentary_script(project, use_llm=False)
    approve_script(load_project(pid))
    export_flow_pack(load_project(pid), use_llm=False, rebuild_visuals=True)
    shots = load_shot_list(pid)["shots"]
    print(f"shots={len(shots)} progress={derive_progress(load_project(pid))['current']}")

    src = project_dir(pid) / "flow-import"
    src.mkdir(parents=True, exist_ok=True)
    for s in shots:
        n = int(s["number"])
        Image.new("RGB", (1280, 720), color=(n * 5 % 255, 60, 90)).save(src / f"{n:03d}.png")
    report = import_images(load_project(pid), src)
    sync_shot_statuses_from_images(pid)
    data = load_shot_list(pid)
    generated = sum(1 for s in data["shots"] if s.get("status") == "generated")
    print(f"import ready={report['ready']}/{report['expected']} auto_generated_status={generated}")

    stats = session_stats(sid, 100)
    print(f"session_stats={json.dumps(stats)}")

    # Mock voice file (silent) for preview path — skip TTS APIs
    audio = project_dir(pid) / "audio" / "narration.mp3"
    audio.parent.mkdir(parents=True, exist_ok=True)
    # Minimal valid-ish bytes; assemble may need real audio — only write placeholder
    audio.write_bytes(b"ID3" + b"\x00" * 64)
    p = load_project(pid)
    p["voice"] = {"path": "audio/narration.mp3", "duration_sec": 12.0, "speed": 1.0}
    from src.documentary.project import set_checkpoint, save_project

    set_checkpoint(p, "voice_ready", True)
    save_project(p)

    from src.documentary.assemble_service import build_preview

    prev = build_preview(load_project(pid))
    print(f"preview ready_to_assemble={prev.get('ready_to_assemble')} warnings={prev.get('warnings')}")

    if os.getenv("SMOKE_RENDER") == "1":
        # Attempt real silent audio via ffmpeg then render
        import subprocess
        import shutil as sh

        if sh.which("ffmpeg"):
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=44100:cl=mono",
                    "-t",
                    "8",
                    str(audio),
                ],
                check=True,
                capture_output=True,
            )
            from src.documentary.assemble_service import assemble_and_render

            out = assemble_and_render(load_project(pid), allow_missing=False, transiciones_suaves=False)
            print(f"rendered={out}")
        else:
            print("SMOKE_RENDER set but ffmpeg missing")

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
