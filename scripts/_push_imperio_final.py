"""Wait for Supabase recovery, purge clips, push imperio final.mp4 + project.json."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PID = "001-pov-construyes-tu-imperio-como-creador-de-conten"


def main() -> None:
    from src.documentary.cloud_sync import _connect, purge_render_clips, push_paths
    from src.documentary.project import load_project
    from src.video_assembler import mp4_is_complete

    out = ROOT / "projects" / PID / "render" / "final.mp4"
    if not mp4_is_complete(out):
        raise SystemExit(f"missing final: {out}")

    for attempt in range(60):
        try:
            with _connect(autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    print("db up", attempt, flush=True)
            break
        except Exception as e:
            print("wait", attempt, type(e).__name__, str(e)[:120], flush=True)
            time.sleep(15)
    else:
        raise SystemExit("db never recovered")

    print("purge clips…", flush=True)
    try:
        print(purge_render_clips(keep_project_id=None), flush=True)
    except Exception as e:
        print("purge fail", e, flush=True)
        # Fallback: delete one clip at a time to reclaim WAL space gradually.
        with _connect(autocommit=True) as conn:
            with conn.cursor() as cur:
                for i in range(200):
                    cur.execute(
                        """
                        DELETE FROM ff_blobs
                        WHERE ctid IN (
                          SELECT ctid FROM ff_blobs
                          WHERE rel_path LIKE 'render/clips/%%'
                          LIMIT 1
                        )
                        """
                    )
                    if not cur.rowcount:
                        break
                    if i % 10 == 0:
                        print("  deleted clip", i, flush=True)
                cur.execute("SELECT pg_database_size(current_database())")
                print("db size", cur.fetchone()[0], flush=True)

    # Also drop duplicate masters / previews that waste space
    with _connect(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM ff_blobs
                WHERE rel_path IN (
                  'render/final_master.mp4',
                  'render/final_captions.mp4',
                  'render/final_burn.mp4',
                  'render/preview.mp4',
                  'render/preview_captions.mp4'
                )
                """
            )
            print("deleted extras", cur.rowcount, flush=True)
            cur.execute("SELECT pg_database_size(current_database())")
            print("db size", cur.fetchone()[0], flush=True)

    p = load_project(PID)
    print("local render state", (p.get("render") or {}).get("state"), flush=True)

    print("pushing project.json + captions + final…", flush=True)
    # project.json first (tiny), then captions, then final
    for rel in ("project.json", "render/captions.srt", "render/final.mp4"):
        try:
            print(rel, push_paths(PID, [rel]), flush=True)
        except Exception as e:
            print("FAIL", rel, e, flush=True)
            raise
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
