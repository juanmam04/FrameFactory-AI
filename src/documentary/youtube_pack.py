"""YouTube packaging: title, description, thumbnail prompt (documentary + Check ALS)."""
from __future__ import annotations

import json
import os
from typing import Any

from src.documentary.project import project_dir, save_project


def _is_check(project: dict[str, Any]) -> bool:
    return str(project.get("content_format") or project.get("mode") or "") == "check_als"


def _check_concept(project: dict[str, Any]) -> dict[str, Any]:
    for key in ("check_concept", "selected_concept", "idea"):
        raw = project.get(key)
        if isinstance(raw, dict) and (raw.get("title") or raw.get("thumbnail_concept") or raw.get("hook")):
            return raw
    cs = project.get("check_story") if isinstance(project.get("check_story"), dict) else {}
    for key in ("concept", "selected_concept", "seed"):
        raw = cs.get(key)
        if isinstance(raw, dict) and (raw.get("title") or raw.get("thumbnail_concept")):
            return raw
    return {}


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
    if _is_check(project):
        return _fallback_check(project)
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


def _fallback_check(project: dict[str, Any]) -> dict[str, Any]:
    concept = _check_concept(project)
    thumb = concept.get("thumbnail_concept") if isinstance(concept.get("thumbnail_concept"), dict) else {}
    title = str(
        concept.get("title") or project.get("title") or project.get("topic") or "POV Check"
    ).strip()[:120]
    alts = []
    for x in concept.get("title_options") or concept.get("alt_titles") or []:
        if isinstance(x, dict):
            t = str(x.get("text") or x.get("title") or "").strip()
        else:
            t = str(x or "").strip()
        if t and t != title:
            alts.append(t[:120])
    hook = ""
    for h in concept.get("hook_options") or []:
        if isinstance(h, dict):
            hook = str(h.get("text") or h.get("hook") or "").strip()
        else:
            hook = str(h or "").strip()
        if hook:
            break
    if not hook:
        hook = str(concept.get("hook") or concept.get("concrete_hook") or "").strip()
    fantasy = str(concept.get("life_transformation") or concept.get("end_state") or "").strip()
    desc_bits = [hook or title, "", fantasy or str(project.get("topic") or "").strip(), "", "Check — fantasía en segunda persona."]
    overlay = str(thumb.get("text_if_any") or "").strip() or _short_overlay(title)
    prompt = str(thumb.get("thumbnail_prompt") or "").strip() or _fallback_check_thumb(title, thumb)
    return {
        "title": title,
        "alt_titles": alts[:3],
        "description": "\n".join(b for b in desc_bits if b is not None).strip()[:4000],
        "thumbnail_text": overlay[:32],
        "thumbnail_prompt": prompt[:2000],
    }


def _fallback_check_thumb(title: str, thumb: dict[str, Any]) -> str:
    main = str(thumb.get("main_visual") or title).strip()[:160]
    contrast = str(thumb.get("central_contrast") or "").strip()[:120]
    obj = str(thumb.get("key_object") or "").strip()[:80]
    return (
        "YouTube thumbnail, 16:9, high-quality 2D stickman cartoon (round white head, black-dot eyes, "
        "spiky black hair, bold outlines). CLOSE-UP of YOU the stickman filling ~50% of the frame, "
        f"emotion readable at phone size. Beat: {main}. "
        f"{('Contrast: ' + contrast + '. ') if contrast else ''}"
        f"{('Key object: ' + obj + '. ') if obj else ''}"
        "Rich detailed environment, strong contrast, envy/curiosity slap. "
        "Leave one third clean for overlay text later. "
        "NO burned-in text, logos, collage, photoreal faces, anime."
    )


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
    pick = [
        w
        for w in words
        if any(ch.isdigit() for ch in w)
        or w.upper() in {"IPO", "CEO", "SOLD", "BROKE", "FELL", "POV", "$1", "MILLÓN", "MILLON"}
    ]
    if pick:
        return " ".join((pick + words)[:3]).upper()[:28]
    return " ".join(words[:3]).upper()[:28] or "POV"


def _generate_llm(project: dict[str, Any], api_key: str) -> dict[str, Any] | None:
    from openai import OpenAI

    if _is_check(project):
        return _generate_llm_check(project, api_key)

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


def _generate_llm_check(project: dict[str, Any], api_key: str) -> dict[str, Any] | None:
    from openai import OpenAI

    concept = _check_concept(project)
    thumb = concept.get("thumbnail_concept") if isinstance(concept.get("thumbnail_concept"), dict) else {}
    title0 = str(concept.get("title") or project.get("title") or "").strip()
    topic = str(project.get("topic") or title0).strip()
    script = str(project.get("script") or "").strip()[:3000]
    client = OpenAI(api_key=api_key)
    system = (
        "Escribís el pack de YouTube para Check: fantasías aspiracionales en segunda persona (tú/te), canal español.\n"
        "Return ONLY JSON: title, alt_titles (2 strings), description, thumbnail_text, thumbnail_prompt.\n"
        "title: español, clickable, POV cuando ayude, número o contraste si es verdad. Sin mentir. Sin 'suscribite'.\n"
        "description: español. Primera línea = gancho. 2 párrafos cortos. Sin CTA de suscripción.\n"
        "thumbnail_text: 2–4 palabras overlay (puede ser número/$). MAYÚSCULAS. No la frase entera del título.\n"
        "thumbnail_prompt: INGLÉS para Google Flow. Miniatura YouTube 16:9, stickman 2D "
        "(round white head, black-dot eyes, spiky black hair, bold outlines) — NOT photoreal. "
        "Cara grande ~50% del frame + un objeto/contraste de ESTA historia. "
        "Sin texto quemado, logos ni collage. Dejá un tercio limpio para overlay."
    )
    user = json.dumps(
        {
            "working_title": title0,
            "topic": topic,
            "concept_title": concept.get("title"),
            "hook": concept.get("hook") or concept.get("concrete_hook"),
            "end_state": concept.get("end_state"),
            "life_transformation": concept.get("life_transformation"),
            "thumbnail_concept": thumb,
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
