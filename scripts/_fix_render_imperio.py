"""Pull imperio episode assets, render final.mp4 locally (no Vercel deadline), push result."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PID = "001-pov-construyes-tu-imperio-como-creador-de-conten"


def load_env() -> None:
    for name in (".env.local", ".env"):
        env = ROOT / name
        if not env.is_file():
            continue
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
    from src.documentary import cloud_sync
    from src.documentary.assemble_service import assemble_and_render, set_render_state
    from src.documentary.project import load_project, set_checkpoint
    from src.video_assembler import mp4_is_complete

    assert cloud_sync.configured(), "cloud sync not configured"
    print("configured OK", flush=True)

    print("delete cancel.flag:", cloud_sync.delete_paths(PID, ["render/cancel.flag"]))
    flag = ROOT / "projects" / PID / "render" / "cancel.flag"
    flag.unlink(missing_ok=True)

    cloud_sync.pull_one(PID, "project.json", force=True)
    imgs = [r for r in cloud_sync.list_rel_paths(PID, "images/") if ".thumb." not in r]
    audio_rels = [r for r in cloud_sync.list_rel_paths(PID, "audio/") if r.endswith(".mp3")]
    print(f"cloud images={len(imgs)} audio={audio_rels}", flush=True)

    local_root = ROOT / "projects" / PID
    local_imgs = [p for p in (local_root / "images").glob("*") if p.is_file() and ".thumb." not in p.name]
    narr = local_root / "audio" / "narration.mp3"
    if len(local_imgs) >= 40 and narr.is_file() and narr.stat().st_size > 0:
        print(f"skip full pull — local images={len(local_imgs)} audio={narr.stat().st_size}", flush=True)
    else:
        must = ["project.json", *audio_rels, *imgs]
        # Also captions / music if present
        for extra in ("render/captions.srt", "audio/music.mp3", "audio/bed.mp3"):
            try:
                if extra in cloud_sync.list_rel_paths(PID, extra.rsplit("/", 1)[0] + "/"):
                    must.append(extra)
            except Exception:
                pass
        written = 0
        for i, rel in enumerate(must):
            try:
                if cloud_sync.pull_one(PID, rel, force=False):
                    written += 1
                if (i + 1) % 10 == 0 or i == 0:
                    print(f"  pull {i + 1}/{len(must)} {rel}", flush=True)
            except Exception as e:
                print("  FAIL", rel, e, flush=True)
        print(f"pull done written={written}", flush=True)

    local_imgs = [p for p in (local_root / "images").glob("*") if p.is_file() and ".thumb." not in p.name]
    print(f"local images={len(local_imgs)} audio={narr.stat().st_size if narr.is_file() else 0}", flush=True)

    p = load_project(PID)
    if isinstance(p.get("render"), dict):
        p["render"]["cancelled"] = False
        p["render"]["need_continue"] = False
        p["render"]["state"] = "running"
    set_checkpoint(p, "images_imported", True)
    set_render_state(p, "running", message="Render local (sin límite Vercel)")
    p = load_project(PID)

    print("assemble_and_render starting…", flush=True)
    result = assemble_and_render(p, resume=False)
    print("result:", result, flush=True)

    p = load_project(PID)
    out = local_root / "render" / "final.mp4"
    print(
        "final complete:",
        mp4_is_complete(out),
        "size:",
        out.stat().st_size if out.is_file() else 0,
        flush=True,
    )
    print("render:", (p.get("render") or {}).get("state"), (p.get("render") or {}).get("message"), flush=True)

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
        print("pushed:", push, flush=True)
    else:
        raise SystemExit("final.mp4 missing/incomplete")


if __name__ == "__main__":
    main()
