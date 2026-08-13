"""Reuse uploaded stills with editorial judgment when slots or duration are short."""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any

from src.documentary.import_images import still_file
from src.documentary.project import append_log, project_dir

_MOMENT_OK: dict[str, tuple[str, ...]] = {
    "rise": ("rise", "peak"),
    "peak": ("peak", "rise"),
    "crack": ("crack", "peak", "collapse"),
    "collapse": ("collapse", "crack", "aftermath"),
    "aftermath": ("aftermath", "collapse"),
}
_STOP = {
    "this", "that", "with", "from", "they", "them", "their", "have", "been",
    "were", "into", "about", "when", "what", "then", "than", "also", "just",
    "over", "after", "before", "there", "here", "would", "could", "should",
    "which", "while", "where", "your", "ours", "itself", "himself", "still",
}


def plan_still_timeline(
    project: dict[str, Any],
    duration_sec: float | None,
    max_sec: float = 7.0,
) -> tuple[list[Path], float, dict[str, Any]]:
    """Full timeline of stills. Own uploads stay; gaps are filled with AI (or heuristic)."""
    pid = str(project["id"])
    catalog, shots = _catalog(pid)
    if not catalog:
        return [], 6.0, {"method": "none", "filled": 0}
    dur = float(duration_sec or 0)
    max_sec = min(7.0, max(4.0, float(max_sec)))
    n_needed = len(catalog)
    if dur > 0:
        n_needed = max(n_needed, int(math.ceil(dur / max_sec)))
    slots = _needed_slots(project, shots, n_needed)
    locked, gaps = _lock_own(slots, catalog)
    info: dict[str, Any] = {
        "available": len(catalog),
        "needed": n_needed,
        "gaps": len(gaps),
        "method": "own",
        "filled": 0,
    }
    if not gaps:
        seq = _paths_from_nums(locked, catalog)
        sec = (dur / len(seq)) if dur > 0 else min(max_sec, 6.0)
        return seq, min(max_sec, max(2.8, sec)), info

    fills = _ask_openai(project, catalog, gaps) or {}
    method = "ai" if fills else "heuristic"
    if not fills:
        fills = _heuristic_fills(catalog, gaps, locked)
    merged = list(locked)
    used = 0
    for g in gaps:
        i = int(g["slot"])
        pick = int(fills.get(i) or 0)
        if pick not in catalog:
            pick = _heuristic_one(catalog, g, merged, i)
        if pick in catalog:
            merged[i] = pick
            used += 1
    for i, num in enumerate(merged):
        if not num:
            merged[i] = _heuristic_one(catalog, slots[i], merged, i)
    seq = _paths_from_nums(merged, catalog)
    if not seq:
        seq = [row["path"] for row in catalog.values()]
        seq = [seq[i % len(seq)] for i in range(n_needed)]
    sec = (dur / len(seq)) if dur > 0 else min(max_sec, 6.0)
    info.update({"method": method, "filled": used})
    append_log(pid, f"still reuse method={method} gaps={len(gaps)} filled={used} needed={n_needed}")
    return seq, min(max_sec, max(2.8, sec)), info


def _catalog(project_id: str) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    img_root = project_dir(project_id) / "images"
    shots: list[dict[str, Any]] = []
    try:
        from src.documentary.flow_pack import load_shot_list

        shots = list(load_shot_list(project_id).get("shots") or [])
    except Exception:
        shots = []
    by_num: dict[int, dict[str, Any]] = {}
    for s in shots:
        try:
            n = int(s.get("number") or 0)
        except (TypeError, ValueError):
            continue
        if n <= 0:
            continue
        by_num[n] = s
    catalog: dict[int, dict[str, Any]] = {}
    nums = sorted(by_num) or []
    if img_root.is_dir():
        extra = []
        for p in img_root.iterdir():
            if not p.is_file() or p.name.endswith(".thumb.jpg"):
                continue
            stem = p.stem
            if stem.isdigit():
                extra.append(int(stem))
        for n in extra:
            if n not in nums:
                nums.append(n)
        nums = sorted(set(nums))
    for n in nums:
        path = still_file(img_root, n)
        if path is None:
            continue
        s = by_num.get(n) or {}
        catalog[n] = {
            "number": n,
            "path": path,
            "moment": str(s.get("moment_id") or "rise"),
            "label": str(s.get("moment_label") or ""),
            "prompt": _clip(
                s.get("flow_prompt") or s.get("prompt") or s.get("action") or s.get("description") or ""
            ),
            "vo": _clip(s.get("narration_segment") or s.get("narration") or ""),
            "emotion": _clip(s.get("emotion") or "", 40),
        }
    return catalog, shots


def _needed_slots(
    project: dict[str, Any],
    shots: list[dict[str, Any]],
    n_needed: int,
) -> list[dict[str, Any]]:
    script_bits = _script_chunks(str(project.get("script") or ""), n_needed)
    n_shots = max(1, len(shots))
    slots: list[dict[str, Any]] = []
    for i in range(n_needed):
        s = shots[min(i, n_shots - 1)] if shots else {}
        try:
            own = int(s.get("number") or 0) if i < n_shots else 0
        except (TypeError, ValueError):
            own = 0
        slots.append(
            {
                "slot": i,
                "own": own if i < len(shots) else 0,
                "moment": str(s.get("moment_id") or "rise"),
                "prompt": _clip(
                    s.get("flow_prompt") or s.get("prompt") or s.get("action") or ""
                ),
                "vo": _clip(s.get("narration_segment") or s.get("narration") or script_bits[i]),
            }
        )
    return slots


def _script_chunks(script: str, n: int) -> list[str]:
    words = (script or "").split()
    if n <= 0:
        return []
    if not words:
        return [""] * n
    out: list[str] = []
    for i in range(n):
        a = int(i * len(words) / n)
        b = int((i + 1) * len(words) / n)
        out.append(_clip(" ".join(words[a:b]) or " ".join(words[-12:])))
    return out


def _lock_own(
    slots: list[dict[str, Any]],
    catalog: dict[int, dict[str, Any]],
) -> tuple[list[int], list[dict[str, Any]]]:
    locked = [0] * len(slots)
    gaps: list[dict[str, Any]] = []
    for s in slots:
        own = int(s.get("own") or 0)
        if own in catalog:
            locked[int(s["slot"])] = own
        else:
            gaps.append(s)
    return locked, gaps


def _ask_openai(
    project: dict[str, Any],
    catalog: dict[int, dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> dict[int, int] | None:
    if not gaps:
        return {}
    try:
        from src.documentary.openai_key import openai_api_key, is_placeholder_key
        from openai import OpenAI
    except Exception:
        return None
    key = openai_api_key()
    if not key or is_placeholder_key(key):
        return None
    avail = [
        {
            "n": n,
            "moment": row["moment"],
            "still": row["prompt"],
            "vo": row["vo"],
        }
        for n, row in sorted(catalog.items())
    ]
    need = [
        {
            "slot": int(g["slot"]),
            "moment": g["moment"],
            "need": g["prompt"] or g["vo"],
            "vo": g["vo"],
        }
        for g in gaps[:80]
    ]
    system = (
        "You are the picture editor of a cinematic English business documentary. "
        "Some timeline slots have no still. Reuse an UPLOADED still that fits that beat. "
        "Return ONLY JSON: {\"fills\":[{\"slot\":int,\"image\":int},...]}.\n"
        "Rules:\n"
        "- image must be an n from AVAILABLE.\n"
        "- Prefer the same moment (rise/peak/crack/collapse/aftermath).\n"
        "- Never put collapse/aftermath stills on rise/peak hope beats.\n"
        "- Never put celebratory rise stills on collapse/aftermath.\n"
        "- Match people, places, objects in the VO to the still description.\n"
        "- Do not repeat the same image in consecutive slots if another fit exists.\n"
        "- Spread reuses; do not dump one photo across the whole gap.\n"
        "- If nothing is perfect, pick the least-wrong still from a neighboring moment."
    )
    user = json.dumps(
        {"topic": str(project.get("topic") or "")[:160], "available": avail, "gaps": need},
        ensure_ascii=False,
    )
    try:
        client = OpenAI(api_key=key, timeout=20.0)
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=900,
        )
        raw = (r.choices[0].message.content or "").strip()
        blob = raw[raw.find("{") : raw.rfind("}") + 1] if "{" in raw else ""
        data = json.loads(blob) if blob else {}
        fills: dict[int, int] = {}
        for row in data.get("fills") or []:
            if not isinstance(row, dict):
                continue
            slot = int(row.get("slot") or -1)
            image = int(row.get("image") or 0)
            if slot >= 0 and image in catalog:
                fills[slot] = image
        return fills or None
    except Exception:
        return None


def _heuristic_fills(
    catalog: dict[int, dict[str, Any]],
    gaps: list[dict[str, Any]],
    locked: list[int],
) -> dict[int, int]:
    out: dict[int, int] = {}
    merged = list(locked)
    for g in gaps:
        i = int(g["slot"])
        pick = _heuristic_one(catalog, g, merged, i)
        if pick:
            out[i] = pick
            merged[i] = pick
    return out


def _heuristic_one(
    catalog: dict[int, dict[str, Any]],
    gap: dict[str, Any],
    merged: list[int],
    index: int,
) -> int:
    want = str(gap.get("moment") or "rise")
    ok = _MOMENT_OK.get(want, (want,))
    prev = merged[index - 1] if index > 0 else 0
    need_tok = _tokens(f"{gap.get('prompt') or ''} {gap.get('vo') or ''}")
    used: dict[int, int] = {}
    for n in merged:
        if n:
            used[n] = used.get(n, 0) + 1
    best = 0
    best_score = -10_000.0
    for n, row in catalog.items():
        score = 0.0
        mom = row["moment"]
        if mom == want:
            score += 6
        elif mom in ok:
            score += 3
        else:
            score -= 8
        score += 2.0 * len(need_tok & _tokens(f"{row['prompt']} {row['vo']}"))
        score -= used.get(n, 0) * 1.5
        if n == prev:
            score -= 5
        if score > best_score:
            best_score = score
            best = n
    if best:
        return best
    nums = list(catalog)
    return nums[index % len(nums)]


def _paths_from_nums(nums: list[int], catalog: dict[int, dict[str, Any]]) -> list[Path]:
    out: list[Path] = []
    fallback = next(iter(catalog.values()))["path"]
    for n in nums:
        row = catalog.get(int(n or 0))
        out.append(row["path"] if row else fallback)
    return out


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z]{4,}", (text or "").lower())
    return {w for w in words if w not in _STOP}


def _clip(text: Any, n: int = 140) -> str:
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t if len(t) <= n else t[: n - 1] + "…"
