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
        "thumbnail_text": str(pack.get("thumbnail_text") or "").strip()[:32],
        "thumbnail_prompt": str(pack.get("thumbnail_prompt") or "").strip()[:2000],
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
    who = _lead_name(project)
    return {
        "title": title,
        "alt_titles": [],
        "description": (
            f"{topic}\n\n"
            "A cinematic true story about a company, the people inside it, and the moment everything changed.\n\n"
            "Story first. Business second."
        ),
        "thumbnail_text": _short_overlay(title),
        "thumbnail_prompt": _fallback_thumb_prompt(topic, who),
    }


def _lead_name(project: dict[str, Any]) -> str:
    plan = project.get("story_plan") if isinstance(project.get("story_plan"), dict) else {}
    for c in plan.get("characters") or []:
        name = str(c.get("name") or "").strip() if isinstance(c, dict) else ""
        if name:
            return name
    return ""


def _fallback_thumb_prompt(topic: str, who: str) -> str:
    face = who or "the founder from this true story"
    return (
        "YouTube thumbnail, 16:9, designed to get taps on a phone — not a documentary still. "
        f"CLOSE-UP of {face}: face fills 50% of the frame, eyes readable at 160px, "
        "emotion = the moment the empire cracks (shock / rage / hollow grin). "
        "Other half: ONE story object that makes you ask what happened "
        f"(the wreckage of: {topic[:140]}). "
        "High contrast, cinematic grade, rim light, shallow depth of field, photoreal, period-accurate. "
        "Leave the left OR right third relatively clean for overlay text later. "
        "NO text, NO logos, NO arrows, NO collage, NO crowded office, NO laptop, NO handshake, NO skyline stock."
    )


def _short_overlay(title: str) -> str:
    words = [w for w in title.replace("—", " ").split() if w]
    pick = [w for w in words if any(ch.isdigit() for ch in w) or w.upper() in {"IPO", "CEO", "SOLD", "BROKE", "FELL"}]
    if pick:
        return " ".join((pick + words)[:3]).upper()[:28]
    return " ".join(words[:3]).upper()[:28] or "THE FALL"


def _generate_llm(project: dict[str, Any], api_key: str) -> dict[str, Any] | None:
    from openai import OpenAI

    title0 = str(project.get("title") or "").strip()
    topic = str(project.get("topic") or title0).strip()
    script = str(project.get("script") or "").strip()[:3500]
    plan = project.get("story_plan") or {}
    central = str(plan.get("central_story") or "").strip()[:800]
    people = [
        str(c.get("name") or "").strip()
        for c in (plan.get("characters") or [])
        if isinstance(c, dict) and str(c.get("name") or "").strip()
    ]
    client = OpenAI(api_key=api_key)
    system = (
        "You write YouTube packaging for an English cinematic business-documentary channel: "
        "100 Days — Business Documentaries. Story first. Business second. The job is VIEWS.\n"
        "Return ONLY JSON with keys: title, alt_titles (2 strings), description, "
        "thumbnail_text, thumbnail_prompt.\n"
        "title: highly clickable without lying; a name + a number + a contradiction when true "
        "(e.g. The $47B Company That Died in 6 Weeks). No 'Welcome back', no lesson-list clickbait.\n"
        "description: English. First line = hook that could be the title. Then 2 short paragraphs. "
        "No subscribe CTA. End with: Story first. Business second.\n"
        "thumbnail_text: 2–4 words for OVERLAY, ALL CAPS, readable on a phone. Prefer a number or a punch "
        "($47B, IPO KILLED, HE RAN). Not the full title. Not a sentence.\n"
        "thumbnail_prompt: English prompt for Google Flow. This is a YOUTUBE THUMBNAIL, not a still from the film. "
        "It must generate clicks. Compose for 16:9, designed to work at 160px wide.\n"
        "MANDATORY:\n"
        "- Named protagonist FACE fills 40–60% of the frame (left or right). Emotion must slap: "
        "shock, rage, smug collapse, hollow victory — one emotion, exaggerated but photoreal.\n"
        "- The other side: ONE story-specific object/place that creates a question "
        "(For Sale sign at night, shredded filing, empty floor, a jet, a courtroom door). "
        "If you could swap it into another episode, it is wrong.\n"
        "- Extreme contrast, cinematic grade, rim light, shallow DOF, photoreal, period-accurate wardrobe.\n"
        "- Leave one third of the frame relatively clean for overlay text (we add text later).\n"
        "- No text, logos, arrows, circles, collage, split-screen comic, YouTube UI in the image.\n"
        "- Forbidden stock: crowded coworking, laptops, handshake, generic skyline, CEO at desk, abstract money.\n"
        "Write the prompt as a single dense paragraph a generator can follow."
    )
    user = json.dumps(
        {
            "working_title": title0,
            "topic": topic,
            "central_story": central,
            "protagonists": people[:6],
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
        temperature=0.75,
        max_tokens=1100,
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
        "thumbnail_text": str(data.get("thumbnail_text") or "").strip()[:32],
        "thumbnail_prompt": str(data.get("thumbnail_prompt") or "").strip()[:2000],
    }
