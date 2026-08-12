"""Documentary script generation (English factual business documentary)."""
from __future__ import annotations

from typing import Any

from src.documentary.channel import script_context_from_session
from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.script_generator import count_words, generar_guion


def generate_documentary_script(project: dict[str, Any], *, use_llm: bool = True) -> dict[str, Any]:
    """Generate or refresh script into project workspace. Does not auto-approve."""
    topic = str(project.get("topic") or "").strip()
    if not topic:
        raise ValueError("Choose a story before generating a script.")
    notes = str(project.get("research_notes") or "").strip()
    sources = project.get("sources") or []
    src_txt = "\n".join(f"- {s}" for s in sources) if sources else "- (none listed yet)"

    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    brief_bits = []
    if idea.get("title_concept"):
        brief_bits.append(f"Working title: {idea.get('title_concept')}")
    if idea.get("story"):
        brief_bits.append(f"Story: {idea.get('story')}")
    if idea.get("hook"):
        brief_bits.append(f"Hook direction: {idea.get('hook')}")
    brief = "\n".join(brief_bits)

    tema = (
        f"{topic}\n\n"
        f"{brief}\n\n" if brief else f"{topic}\n\n"
    )
    tema += (
        f"RESEARCH NOTES (use only these facts; if something is unknown, say so or omit — NEVER invent):\n"
        f"{notes or '(empty — keep claims minimal and clearly general)'}\n\n"
        f"SOURCES:\n{src_txt}"
    )
    target = int(project.get("target_words") or 1500)
    snap = project.get("creative_profile_snapshot") if isinstance(project.get("creative_profile_snapshot"), dict) else {}
    creative_context = script_context_from_session(snap or None, idea=idea or None)

    if use_llm:
        script, wc, _mins = generar_guion(
            tema,
            target_words=target,
            plantilla="business_documentary_en",
            creative_context=creative_context,
            force_este_eres_tu_opening=False,
        )
    else:
        script = _mock_script(topic, target)
        wc = count_words(script)

    project["script"] = script
    project["script_approved"] = False
    project["fact_check_status"] = "pending"
    project["ui_step"] = "script"
    set_checkpoint(project, "script_ready", True)
    set_checkpoint(project, "flow_pack_ready", False)

    root = project_dir(str(project["id"]))
    (root / "script" / "script.txt").write_text(script, encoding="utf-8")
    (root / "script" / "script_meta.json").write_text(
        __import__("json").dumps({"word_count": wc, "target_words": target}, indent=2),
        encoding="utf-8",
    )
    save_project(project)
    append_log(str(project["id"]), f"script generated words={wc}")
    return project


def save_edited_script(project: dict[str, Any], script: str) -> dict[str, Any]:
    script = (script or "").strip()
    if not script:
        raise ValueError("Script is empty.")
    project["script"] = script
    project["script_approved"] = False
    project["fact_check_status"] = "pending"
    set_checkpoint(project, "script_ready", True)
    set_checkpoint(project, "flow_pack_ready", False)
    root = project_dir(str(project["id"]))
    (root / "script" / "script.txt").write_text(script, encoding="utf-8")
    save_project(project)
    append_log(str(project["id"]), f"script edited words={count_words(script)}")
    return project


def approve_script(project: dict[str, Any]) -> dict[str, Any]:
    if not (project.get("script") or "").strip():
        raise ValueError("No script to approve yet.")
    project["script_approved"] = True
    project["fact_check_status"] = "approved"
    project["ui_step"] = "flow"
    set_checkpoint(project, "script_ready", True)
    save_project(project)
    append_log(str(project["id"]), "script APPROVED")
    return project


def _mock_script(topic: str, target_words: int) -> str:
    """Deterministic filler for offline dogfood (clearly marked non-publishable)."""
    base = (
        f"[DOGFOOD MOCK — NOT FOR PUBLICATION] {topic}. "
        "This is a placeholder documentary narration used only to verify the pipeline. "
        "In production, replace with a fact-checked English script. "
    )
    words = base.split()
    while len(words) < max(80, int(target_words * 0.3)):
        words.extend(
            "The company grew quickly, raised capital, expanded offices, then faced a public reckoning "
            "as numbers failed to match the story sold to investors and the press. ".split()
        )
    return " ".join(words[: max(80, int(target_words * 0.35))])
