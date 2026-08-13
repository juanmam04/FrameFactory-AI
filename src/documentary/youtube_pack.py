"""YouTube packaging for a documentary episode: title, description, thumbnail prompt."""
from __future__ import annotations

import json
import os
from typing import Any

from src.documentary.project import project_dir, save_project


def generate_youtube_pack(project: dict[str, Any]) -> dict[str, Any]:
    pack = _fallback(project)
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if key:
        try:
            pack = _generate_llm(project, key) or pack
        except Exception:
            pass
    project["youtube"] = pack
    project["ui_step"] = "publish"
    root = project_dir(str(project["id"]))
    (root / "metadata").mkdir(parents=True, exist_ok=True)
    (root / "metadata" / "youtube.json").write_text(
        json.dumps(pack, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_project(project)
    return pack


def save_youtube_pack(project: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    clean = {
        "title": str(pack.get("title") or "").strip()[:120],
        "alt_titles": [str(x).strip()[:120] for x in (pack.get("alt_titles") or []) if str(x).strip()][:3],
        "description": str(pack.get("description") or "").strip()[:4000],
        "thumbnail_text": str(pack.get("thumbnail_text") or "").strip()[:40],
        "thumbnail_prompt": str(pack.get("thumbnail_prompt") or "").strip()[:1200],
    }
    project["youtube"] = clean
    root = project_dir(str(project["id"]))
    (root / "metadata").mkdir(parents=True, exist_ok=True)
    (root / "metadata" / "youtube.json").write_text(
        json.dumps(clean, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_project(project)
    return clean


def _fallback(project: dict[str, Any]) -> dict[str, Any]:
    title = str(project.get("title") or project.get("topic") or "True story").strip()[:100]
    topic = str(project.get("topic") or title).strip()
    return {
        "title": title,
        "alt_titles": [],
        "description": (
            f"{topic}\n\n"
            "A cinematic true story about a company, the people inside it, and the moment everything changed.\n\n"
            "Story first. Business second."
        ),
        "thumbnail_text": _short_overlay(title),
        "thumbnail_prompt": (
            "Cinematic 16:9 documentary still, photoreal, no text, no logos, no watermark. "
            f"The single most loaded image from this story: {topic}. "
            "One clear subject, high contrast, naturalistic light, serious mood. "
            "Avoid handshake, laptop, generic skyline, CEO staring at camera."
        ),
    }


def _short_overlay(title: str) -> str:
    words = [w for w in title.replace("—", " ").split() if w]
    return " ".join(words[:3]).upper()[:28] or "THE DEAL"


def _generate_llm(project: dict[str, Any], api_key: str) -> dict[str, Any] | None:
    from openai import OpenAI

    title0 = str(project.get("title") or "").strip()
    topic = str(project.get("topic") or title0).strip()
    script = str(project.get("script") or "").strip()[:3500]
    plan = project.get("story_plan") or {}
    central = str(plan.get("central_story") or "").strip()[:800]
    client = OpenAI(api_key=api_key)
    system = (
        "You write YouTube packaging for an English cinematic business-documentary channel: "
        "100 Days — Business Documentaries. Story first. Business second.\n"
        "Return ONLY JSON with keys: title, alt_titles (2 strings), description, "
        "thumbnail_text, thumbnail_prompt.\n"
        "title: highly clickable without lying; specific stakes, a number, a name, or a contradiction when true; "
        "no 'Welcome back', no 'in this video', no lesson-list clickbait.\n"
        "description: English. First line = hook. Then 2 short paragraphs of the true story. "
        "No subscribe CTA. End with: Story first. Business second.\n"
        "thumbnail_text: 2-4 words for overlay, uppercase, not a full sentence.\n"
        "thumbnail_prompt: English, one cinematic 16:9 still to generate in Google Flow. "
        "Photoreal documentary look. No text in the image, no logos, no watermark, no arrows. "
        "Show a concrete moment from the story (a person doing something, a place, a consequence). "
        "Avoid generic stock: handshake, laptop, CEO at desk, abstract money."
    )
    user = json.dumps(
        {
            "working_title": title0,
            "topic": topic,
            "central_story": central,
            "script_excerpt": script,
        },
        ensure_ascii=False,
    )
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=900,
    )
    raw = (r.choices[0].message.content or "").strip()
    blob = raw[raw.find("{") : raw.rfind("}") + 1] if "{" in raw else ""
    data = json.loads(blob) if blob else {}
    if not isinstance(data, dict) or not str(data.get("title") or "").strip():
        return None
    alts = data.get("alt_titles") if isinstance(data.get("alt_titles"), list) else []
    return {
        "title": str(data.get("title") or "").strip()[:120],
        "alt_titles": [str(x).strip()[:120] for x in alts if str(x).strip()][:3],
        "description": str(data.get("description") or "").strip()[:4000],
        "thumbnail_text": str(data.get("thumbnail_text") or "").strip()[:40],
        "thumbnail_prompt": str(data.get("thumbnail_prompt") or "").strip()[:1200],
    }
