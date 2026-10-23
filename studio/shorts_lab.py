"""Standalone Shorts pack: script → Flow prompts + viral captions (+ optional TTS)."""
from __future__ import annotations

import json
import os
import re
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from src.config_loader import BASE
from src.documentary.openai_key import reload_env, require_openai_api_key

OUTPUT = BASE / "output" / "shorts-lab"


def _client():
    from openai import OpenAI

    return OpenAI(api_key=require_openai_api_key("Shorts Lab"))


def _words(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _estimate_duration_sec(script: str, *, wpm: int = 155) -> float:
    return max(8.0, _words(script) / max(1, wpm) * 60.0)


def _chunk_captions(script: str, *, max_words: int = 5) -> list[str]:
    """Fallback viral-ish lines if LLM fails: short punchy chunks."""
    words = re.findall(r"\S+", script or "")
    lines: list[str] = []
    buf: list[str] = []
    for w in words:
        buf.append(w)
        end = w.endswith((".", "!", "?", "…"))
        if len(buf) >= max_words or end:
            line = " ".join(buf).strip()
            if line:
                lines.append(line.upper() if len(buf) <= 3 else line)
            buf = []
    if buf:
        lines.append(" ".join(buf))
    return lines or [script.strip()[:80] or "WATCH THIS"]


def _to_srt(lines: list[dict[str, Any]]) -> str:
    blocks = []
    for i, row in enumerate(lines, 1):
        start = float(row.get("start") or 0)
        end = float(row.get("end") or start + 1.2)
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        blocks.append(f"{i}\n{_ts(start)} --> {_ts(end)}\n{text}\n")
    return "\n".join(blocks).strip() + ("\n" if blocks else "")


def _ts(sec: float) -> str:
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _llm_pack(script: str, *, language: str, duration_sec: float, still_count: int) -> dict[str, Any]:
    lang = "Spanish" if str(language).startswith("es") else "English"
    system = (
        "You are a viral short-form video packager for vertical 9:16 YouTube/TikTok shorts. "
        "Return ONLY JSON with keys: "
        "hooks (array of 3 short hook titles), "
        "captions (array of {start, end, text} covering the whole narration with punchy on-screen lines — "
        "max 6 words per cue, high retention, no hashtags inside cues), "
        "flow_prompts (array of {n, beat, prompt} — exactly still_count items), "
        "hashtags (array of 8), "
        "cta (one short end CTA). "
        "Visual style LOCK: modern 2D stickman animation, round white head, black-dot eyes, bold outlines, "
        "cinematic lighting, vertical 9:16, no photoreal people, no readable tiny text. "
        "Each Flow prompt must be a single copy-paste paragraph for Google Flow / image gen. "
        "Language of captions/hooks/cta: " + lang + "."
    )
    user = {
        "script": script[:45000],
        "target_duration_sec": round(duration_sec, 1),
        "still_count": still_count,
        "language": language,
    }
    raw = (
        _client()
        .chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.55,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        )
        .choices[0]
        .message.content
        or "{}"
    )
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Respuesta inválida del modelo")
    return data


def _normalize_pack(data: dict[str, Any], script: str, *, duration_sec: float, still_count: int) -> dict[str, Any]:
    captions = data.get("captions") if isinstance(data.get("captions"), list) else []
    cues: list[dict[str, Any]] = []
    for row in captions:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        cues.append(
            {
                "start": float(row.get("start") or 0),
                "end": float(row.get("end") or 0),
                "text": text[:120],
            }
        )
    if not cues:
        lines = _chunk_captions(script)
        step = duration_sec / max(1, len(lines))
        cues = [
            {"start": i * step, "end": min(duration_sec, (i + 1) * step), "text": line}
            for i, line in enumerate(lines)
        ]
    # Fix overlapping / zero lengths
    fixed: list[dict[str, Any]] = []
    for i, c in enumerate(cues):
        start = max(0.0, float(c["start"]))
        end = float(c["end"])
        if end <= start:
            end = start + max(0.8, duration_sec / max(8, len(cues)))
        if fixed and start < fixed[-1]["end"]:
            start = fixed[-1]["end"]
        fixed.append({"start": round(start, 2), "end": round(min(duration_sec + 0.5, end), 2), "text": c["text"]})
    if fixed:
        fixed[-1]["end"] = max(fixed[-1]["end"], round(duration_sec, 2))

    prompts_raw = data.get("flow_prompts") if isinstance(data.get("flow_prompts"), list) else []
    prompts: list[dict[str, Any]] = []
    for i in range(1, still_count + 1):
        row = prompts_raw[i - 1] if i - 1 < len(prompts_raw) and isinstance(prompts_raw[i - 1], dict) else {}
        beat = str(row.get("beat") or f"Beat {i}").strip()[:120]
        prompt = str(row.get("prompt") or "").strip()
        if not prompt:
            prompt = (
                f"Vertical 9:16 modern 2D stickman cinematic still, beat {i}/{still_count}: {beat}. "
                "Round white head, black-dot eyes, bold outlines, dramatic light, no photoreal people, "
                "no tiny readable text. Single clear subject, high contrast."
            )
        prompts.append({"n": i, "beat": beat, "prompt": prompt})

    hooks = [str(h).strip() for h in (data.get("hooks") or []) if str(h).strip()][:5]
    if not hooks:
        hooks = ["POV: esto cambia todo", "Nadie te contó esto", "En 30 segundos…"]
    hashtags = [str(h).strip().lstrip("#") for h in (data.get("hashtags") or []) if str(h).strip()][:12]
    cta = str(data.get("cta") or "Seguí para la parte 2").strip()[:160]

    return {
        "hooks": hooks,
        "captions": fixed,
        "srt": _to_srt(fixed),
        "flow_prompts": prompts,
        "hashtags": hashtags,
        "cta": cta,
        "duration_sec": round(duration_sec, 1),
        "still_count": still_count,
        "word_count": _words(script),
    }


def build_shorts_pack(
    script: str,
    *,
    language: str = "es",
    still_count: int | None = None,
    duration_sec: float | None = None,
) -> dict[str, Any]:
    reload_env()
    text = (script or "").strip()
    if len(text) < 40:
        raise ValueError("Pegá un guion más largo (mínimo ~40 caracteres).")
    if len(text) > 80_000:
        raise ValueError("Máximo ~80k caracteres por short.")
    dur = float(duration_sec) if duration_sec else _estimate_duration_sec(text)
    dur = max(8.0, min(180.0, dur))
    # ~1 still every 2.5–3.5s for shorts
    n = int(still_count) if still_count else max(4, min(24, int(round(dur / 3.0))))
    try:
        raw = _llm_pack(text, language=language, duration_sec=dur, still_count=n)
        pack = _normalize_pack(raw, text, duration_sec=dur, still_count=n)
        pack["source"] = "llm"
    except Exception as err:
        # Offline / soft fallback so the tool never returns empty.
        lines = _chunk_captions(text, max_words=4)
        step = dur / max(1, len(lines))
        cues = [
            {"start": round(i * step, 2), "end": round(min(dur, (i + 1) * step), 2), "text": ln}
            for i, ln in enumerate(lines)
        ]
        prompts = [
            {
                "n": i,
                "beat": f"Momento {i}",
                "prompt": (
                    f"Vertical 9:16 2D stickman short still {i}/{n}, dramatic cinematic light, "
                    f"story beat from narration chunk {i}. Bold outlines, no photoreal people."
                ),
            }
            for i in range(1, n + 1)
        ]
        pack = {
            "hooks": ["Mirá esto", "Nadie habla de esto", "En segundos…"],
            "captions": cues,
            "srt": _to_srt(cues),
            "flow_prompts": prompts,
            "hashtags": ["shorts", "viral", "storytime"],
            "cta": "Seguí para más",
            "duration_sec": round(dur, 1),
            "still_count": n,
            "word_count": _words(text),
            "source": "fallback",
            "warning": str(err)[:220],
        }
    job = f"{int(time.time())}-{_words(text)}"
    OUT_DIR = OUTPUT / job
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "script.txt").write_text(text + "\n", encoding="utf-8")
    (OUT_DIR / "captions.srt").write_text(pack["srt"], encoding="utf-8")
    (OUT_DIR / "hooks.txt").write_text("\n".join(pack["hooks"]) + "\n", encoding="utf-8")
    (OUT_DIR / "hashtags.txt").write_text(" ".join("#" + h for h in pack["hashtags"]) + "\n", encoding="utf-8")
    prompts_dir = OUT_DIR / "flow-prompts"
    prompts_dir.mkdir(exist_ok=True)
    for row in pack["flow_prompts"]:
        (prompts_dir / f"{int(row['n']):03d}.txt").write_text(row["prompt"] + "\n", encoding="utf-8")
    all_prompts = "\n\n".join(
        f"=== STILL {int(r['n']):03d} · {r['beat']} ===\n{r['prompt']}" for r in pack["flow_prompts"]
    )
    (OUT_DIR / "ALL-PROMPTS.txt").write_text(all_prompts + "\n", encoding="utf-8")
    (OUT_DIR / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    pack["job"] = job
    pack["files"] = {
        "srt": f"/api/shorts-lab/file/{job}/captions.srt",
        "prompts": f"/api/shorts-lab/file/{job}/ALL-PROMPTS.txt",
        "zip": f"/api/shorts-lab/zip/{job}",
        "hooks": f"/api/shorts-lab/file/{job}/hooks.txt",
    }
    return pack


def job_dir(job: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "", job)[:64]
    path = OUTPUT / safe
    if not path.is_dir():
        raise FileNotFoundError(job)
    return path


def zip_job(job: str) -> bytes:
    root = job_dir(job)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(root).as_posix())
    return buf.getvalue()
