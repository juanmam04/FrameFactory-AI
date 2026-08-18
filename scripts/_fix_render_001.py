"""One-shot: clear cancel flag, pull assets, render episode 001 locally, push final."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PID = "001-the-47-billion-company-that-almost-collapsed-ove"


def load_env() -> None:
    env = ROOT / ".env.local"
    if not env.is_file():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def main() -> None:
    print("boot", flush=True)
    load_env()
    print("env loaded", flush=True)
    from src.documentary import cloud_sync
    from src.documentary.assemble_service import assemble_and_render, set_render_state
    from src.documentary.project import load_project, save_project, set_checkpoint
    from src.video_assembler import mp4_is_complete

    assert cloud_sync.configured(), "cloud sync not configured"
    print("configured OK", flush=True)

    # Kill stale cancel that blocks every new render on Vercel.
    print("delete cancel.flag:", cloud_sync.delete_paths(PID, ["render/cancel.flag"]))
    flag = ROOT / "projects" / PID / "render" / "cancel.flag"
    flag.unlink(missing_ok=True)

    imgs = [r for r in cloud_sync.list_rel_paths(PID, "images/") if ".thumb." not in r]
    print(f"cloud images: {len(imgs)}", flush=True)
    audio_rels = [r for r in cloud_sync.list_rel_paths(PID, "audio/") if r.endswith(".mp3")]
    print(f"cloud audio: {audio_rels}", flush=True)

    local_imgs = [p for p in (ROOT / "projects" / PID / "images").glob("*.jpg") if ".thumb." not in p.name]
    narr = ROOT / "projects" / PID / "audio" / "narration.mp3"
    if len(local_imgs) >= 40 and narr.is_file():
        print(f"skip pull — local images={len(local_imgs)} audio={narr.stat().st_size}", flush=True)
    else:
        must = ["project.json", *audio_rels, *imgs]
        written = 0
        for rel in must:
            try:
                if cloud_sync.pull_one(PID, rel, force=False):
                    written += 1
                    print("  pulled", rel, flush=True)
            except Exception as e:
                print("  FAIL", rel, e, flush=True)
        print(f"pull done written={written}", flush=True)

    local_imgs = [p for p in (ROOT / "projects" / PID / "images").glob("*.jpg") if ".thumb." not in p.name]
    print(f"local images: {len(local_imgs)}", flush=True)
    print(f"local audio bytes: {narr.stat().st_size if narr.is_file() else 0}", flush=True)

    p = load_project(PID)
    if isinstance(p.get("render"), dict):
        p["render"]["cancelled"] = False
        p["render"]["need_continue"] = False
    set_checkpoint(p, "images_imported", True)
    set_render_state(p, "running", message="Render local (fix pipeline)")
    p = load_project(PID)

    print("assemble_and_render starting…")
    result = assemble_and_render(p, resume=False)
    print("result:", result)

    p = load_project(PID)
    out = ROOT / "projects" / PID / "render" / "final.mp4"
    print("final complete:", mp4_is_complete(out), "size:", out.stat().st_size if out.is_file() else 0)
    print("render state:", (p.get("render") or {}).get("state"), (p.get("render") or {}).get("message"))
    print("captions:", p.get("captions"))

    if mp4_is_complete(out):
        push = cloud_sync.push_paths(
            PID,
            [
                "project.json",
                "render/final.mp4",
                "render/final_master.mp4",
                "render/final_captions.mp4",
                "render/captions.srt",
            ],
        )
        print("pushed:", push)
    else:
        raise SystemExit("final.mp4 missing/incomplete")


if __name__ == "__main__":
    main()
