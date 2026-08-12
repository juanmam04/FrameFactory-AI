#!/usr/bin/env python3
"""Dogfood: create non-production project 100-days-test (WeWork) and walk the pipeline offline."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.documentary.assemble_service import assemble_and_render, build_preview
from src.documentary.flow_pack import export_flow_pack
from src.documentary.import_images import import_images
from src.documentary.project import create_project, load_project, project_dir, projects_root
from src.documentary.script_service import approve_script, generate_documentary_script


def main() -> int:
    pid = "100-days-test"
    root = projects_root() / pid
    if root.exists():
        shutil.rmtree(root)
        print(f"Removed previous {root}")

    p = create_project(
        "The Rise and Fall of WeWork",
        title="The Rise and Fall of WeWork",
        project_id=pid,
        target_words=400,
        research_notes=(
            "WeWork was co-founded by Adam Neumann. SoftBank was a major investor. "
            "The 2019 IPO attempt collapsed amid governance and valuation concerns. "
            "UNKNOWN: exact private valuation peaks — do not invent."
        ),
        sources=["Public reporting on WeWork IPO attempt (2019)"],
    )
    print("created", p["id"])

    generate_documentary_script(p, use_llm=False)
    p = load_project(pid)
    approve_script(p)
    p = load_project(pid)
    export_flow_pack(p, use_llm=False, rebuild_visuals=True)
    p = load_project(pid)
    n = int((p.get("flow_pack") or {}).get("shot_count") or 0)
    print("shots", n)

    src = project_dir(pid) / "flow-import"
    src.mkdir(parents=True, exist_ok=True)
    for i in range(1, n + 1):
        Image.new("RGB", (1280, 720), color=(20 + i * 3, 30, 40)).save(src / f"{i:03d}.png")
    report = import_images(p, src)
    print("import", report["ready"], "/", report["expected"])

    # Silent WAV-like tiny mp3 is hard; create empty skip — voice needs API.
    # For dogfood assemble we synthesize a short silent audio via ffmpeg if available.
    audio = project_dir(pid) / "audio" / "narration.mp3"
    audio.parent.mkdir(parents=True, exist_ok=True)
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
                str(max(3, n * 0.4)),
                "-q:a",
                "9",
                str(audio),
            ],
            check=True,
            capture_output=True,
        )
        from src.documentary.project import set_checkpoint, save_project

        p = load_project(pid)
        p["voice"] = {"path": "audio/narration.mp3", "duration_sec": float(max(3, n * 0.4)), "speed": 1.0}
        set_checkpoint(p, "voice_ready", True)
        save_project(p)
        prev = build_preview(load_project(pid))
        print("preview", prev)
        out = assemble_and_render(load_project(pid), allow_missing=False, transiciones_suaves=False)
        print("RENDER OK", out)
        assert out.exists() and out.stat().st_size > 0
    else:
        print("ffmpeg missing — skipped assemble; structure OK")

    print("DOGFOOD PASS", project_dir(pid))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
