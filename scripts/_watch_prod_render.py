"""Poll / resume production render until final.mp4 is ready."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE = "https://frame-factory-ai-three.vercel.app"
PID = "001-the-47-billion-company-that-almost-collapsed-ove"


def get(path: str, timeout: float = 60) -> dict:
    req = urllib.request.Request(f"{BASE}{path}", headers={"User-Agent": "ff-watch"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path: str, timeout: float = 320) -> dict | str:
    req = urllib.request.Request(
        f"{BASE}{path}",
        method="POST",
        data=b"{}",
        headers={"Content-Type": "application/json", "User-Agent": "ff-watch"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            try:
                return json.loads(raw)
            except Exception:
                return raw[:500]
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    last = ""
    while True:
        st = get(f"/api/projects/{PID}/video/status")
        line = (
            f"{st.get('state')} {st.get('percent')}% "
            f"{st.get('kb_done')}/{st.get('kb_total')} "
            f"stage={st.get('stage')} cont={st.get('need_continue')} "
            f"ready={st.get('ready')} | {st.get('message')}"
        )
        if line != last:
            print(line, flush=True)
            last = line
        if st.get("ready") and st.get("state") == "done":
            print("DONE", flush=True)
            # HEAD check size
            req = urllib.request.Request(
                f"{BASE}/api/projects/{PID}/video", method="HEAD", headers={"User-Agent": "ff-watch"}
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                print("video headers", dict(r.headers), flush=True)
            return
        if st.get("state") == "error":
            print("ERROR", st.get("error") or st.get("message"), flush=True)
            print("restarting…", flush=True)
            print(post(f"/api/projects/{PID}/render"), flush=True)
        elif st.get("need_continue") or (
            st.get("state") == "running"
            and int(st.get("elapsed_sec") or 0) > 200
            and not str(st.get("stage") or "").startswith("preview")
        ):
            print(">> resume", flush=True)
            print(post(f"/api/projects/{PID}/render?resume=1"), flush=True)
        elif st.get("state") in ("idle",) and not st.get("ready"):
            print(">> start", flush=True)
            print(post(f"/api/projects/{PID}/render"), flush=True)
        time.sleep(12)


if __name__ == "__main__":
    main()
