"""Estructura del paquete completo (idea, escenas export, publicación) para SaaS."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def blocks_to_scenes_export(blocks: list[dict[str, Any]], *, words_per_minute: float = 140.0) -> list[dict[str, Any]]:
    """Escenas ligeras para API/UX: texto, intención visual y duración estimada (segundos) por palabras."""
    wpm = max(60.0, min(220.0, float(words_per_minute)))
    out: list[dict[str, Any]] = []
    for b in blocks or []:
        text = (b.get("text") or "").strip()
        wc = len(text.split()) if text else 0
        dur = (wc / wpm) * 60.0 if wpm else 4.0
        dur = max(2.0, min(55.0, float(dur)))
        parts = [b.get("visual_direction"), b.get("b_roll_suggestion")]
        visual = " · ".join(str(x).strip() for x in parts if str(x).strip())
        if not visual:
            visual = "b-roll atmosférico que acompaña la narración"
        sid = b.get("id")
        row: dict[str, Any] = {"text": text, "visual": visual[:500], "duration": round(dur, 1)}
        if sid:
            row["id"] = sid
        out.append(row)
    return out


def write_saas_full_package(
    output_dir: Path,
    *,
    viral_meta: dict[str, Any] | None,
    script_text: str,
    blocks: list[dict[str, Any]],
    pub_bundle: dict[str, Any],
    final_video: Path,
    words_per_minute: float = 140.0,
) -> Path:
    """Escribe saas_full_package.json en el directorio de salida del render."""
    scenes = blocks_to_scenes_export(blocks, words_per_minute=words_per_minute)
    idea_line = ""
    alt_ideas: list[str] = []
    if viral_meta and isinstance(viral_meta, dict):
        idea_line = str(viral_meta.get("idea") or "").strip()
        al = viral_meta.get("alternatives")
        if isinstance(al, list):
            alt_ideas = [str(x).strip() for x in al if str(x).strip()][:5]
    payload: dict[str, Any] = {
        "idea": idea_line or (script_text or "").split("\n")[0][:240],
        "alt_ideas": alt_ideas,
        "viral_meta": viral_meta,
        "script": script_text,
        "scenes": scenes,
        "title": pub_bundle.get("title"),
        "alt_titles": pub_bundle.get("alt_titles"),
        "description": pub_bundle.get("description"),
        "thumbnail": pub_bundle.get("thumbnail"),
        "video_path": str(final_video.resolve()).replace("\\", "/"),
    }
    path = output_dir / "saas_full_package.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
