"""End-to-end console proof: voice fingerprint must flow into preview."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.documentary.assemble_service import assemble_preview_clip
from src.documentary.pipeline_invalidate import (
    narration_fingerprint,
    preview_matches_voice,
    stamp_voice_fingerprint,
    wipe_voice_derived,
)
from src.documentary.project import load_project, project_dir, save_project
from src.documentary.voice_script_sync import script_hash, voice_matches_script
from src.video_assembler import mp4_is_complete


def main() -> int:
    pid = sys.argv[1] if len(sys.argv) > 1 else "001-the-47-billion-company-that-almost-collapsed-ove"
    p = load_project(pid)
    script = str(p.get("script") or "").strip()
    audio = project_dir(pid) / "audio" / "narration.mp3"
    print("project", pid)
    print("script_words", len(script.split()), "audio_bytes", audio.stat().st_size if audio.is_file() else 0)

    if not script:
        print("FAIL: no script")
        return 2
    if not audio.is_file() or audio.stat().st_size < 1000:
        print("FAIL: no narration.mp3 — generate voice first")
        return 3

    # Bind current take to current script for this console run (local dogfood).
    voice = dict(p.get("voice") or {})
    voice["script_hash"] = script_hash(script)
    voice["stale"] = False
    p["voice"] = voice
    stamp_voice_fingerprint(p)
    p["script_approved"] = True
    save_project(p)
    print("voice_matches_script", voice_matches_script(p), "audio_sha", (p.get("voice") or {}).get("audio_sha"))

    print("wipe derived…")
    wipe_voice_derived(p, reason="console proof")
    save_project(p)
    prev = project_dir(pid) / "render" / "preview.mp4"
    print("preview after wipe", prev.is_file())

    print("assemble preview…")
    out = assemble_preview_clip(load_project(pid))
    p2 = load_project(pid)
    print("preview path", out, "complete", mp4_is_complete(out), "size", out.stat().st_size)
    meta = ((p2.get("render") or {}).get("preview_meta") or {})
    print("preview_meta.voice_script_hash", meta.get("voice_script_hash"))
    print("preview_meta.audio_sha", meta.get("audio_sha"))
    print("voice.audio_sha", (p2.get("voice") or {}).get("audio_sha"))
    print("preview_matches_voice", preview_matches_voice(p2))
    fp = narration_fingerprint(pid)
    ok = (
        preview_matches_voice(p2)
        and str(meta.get("audio_sha") or "") == str(fp.get("audio_sha") or "")
        and mp4_is_complete(out)
    )
    print("RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
