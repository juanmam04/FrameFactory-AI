"""Documentary script generation (English factual business documentary)."""
from __future__ import annotations

import json
import logging
from typing import Any

from src.documentary.channel import documentary_script_context, language_from_profile
from src.documentary.editorial import DOCUMENTARY_INVARIANTS
from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.documentary.script_validation import strip_metadata_leaks, validate_documentary_script
from src.script_generator import count_words, generar_guion

logger = logging.getLogger(__name__)

TEMPLATE_ID = "business_documentary_en"


def research_is_thin(project: dict[str, Any]) -> bool:
    notes = str(project.get("research_notes") or "").strip()
    sources = project.get("sources") or []
    if len(notes) < 80 and len(sources) == 0:
        return True
    if len(notes) < 40:
        return True
    return False


def build_documentary_tema(project: dict[str, Any]) -> str:
    """User payload for the model — subject + research only (no Working title leak)."""
    topic = str(project.get("topic") or "").strip()
    notes = str(project.get("research_notes") or "").strip()
    sources = project.get("sources") or []
    src_txt = "\n".join(f"- {s}" for s in sources) if sources else "- (none listed yet)"
    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    entity = str(idea.get("primary_entity") or "").strip()
    subject_line = topic
    if entity and entity.lower() not in topic.lower():
        subject_line = f"{topic}\nPrimary subject: {entity}"
    return (
        f"SUBJECT:\n{subject_line}\n\n"
        f"RESEARCH NOTES (use only these facts; if unknown, omit — NEVER invent):\n"
        f"{notes or '(empty — keep claims minimal and clearly general; prefer a shorter script)'}\n\n"
        f"SOURCES:\n{src_txt}"
    )


def log_pre_generation_debug(project: dict[str, Any], *, target: int, research_chars: int) -> None:
    snap = project.get("creative_profile_snapshot") if isinstance(project.get("creative_profile_snapshot"), dict) else {}
    lang = language_from_profile(snap) if snap else str(project.get("language") or "en")
    msg = (
        f"Workflow: documentary | Template: {TEMPLATE_ID} | Language: {lang} | "
        f"POV: third_person | Factuality: nonfiction | "
        f"Topic: {(project.get('topic') or '')[:80]!r} | Target words: {target} | "
        f"Research chars: {research_chars} | Sources: {len(project.get('sources') or [])} | "
        f"Legacy storytime context: NONE"
    )
    logger.info(msg)
    print(f"[documentary-script] {msg}")
    append_log(str(project["id"]), msg)


def generate_documentary_script(project: dict[str, Any], *, use_llm: bool = True) -> dict[str, Any]:
    """Generate or refresh script into project workspace. Does not auto-approve."""
    topic = str(project.get("topic") or "").strip()
    if not topic:
        raise ValueError("Choose a story before generating a script.")

    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    notes = str(project.get("research_notes") or "").strip()
    thin = research_is_thin(project)
    tema = build_documentary_tema(project)
    target = int(project.get("target_words") or 1500)
    snap = project.get("creative_profile_snapshot") if isinstance(project.get("creative_profile_snapshot"), dict) else {}
    lang = language_from_profile(snap) if snap else str(project.get("language") or "en")
    creative_context = DOCUMENTARY_INVARIANTS + "\n\n" + documentary_script_context(snap or None, idea=idea or None)

    log_pre_generation_debug(project, target=target, research_chars=len(notes))

    if use_llm:
        script, wc, _mins = generar_guion(
            tema,
            target_words=target,
            plantilla=TEMPLATE_ID,
            creative_context=creative_context,
            force_este_eres_tu_opening=False,
        )
    else:
        script = _mock_script(topic, target, research_notes=notes)
        wc = count_words(script)

    script = strip_metadata_leaks(script)
    ok, reasons = validate_documentary_script(
        script,
        language=lang,
        target_words=target,
        allow_short_if_thin_research=thin or (not use_llm),
    )
    if not ok:
        append_log(str(project["id"]), f"script REJECTED: {'; '.join(reasons)}")
        raise ValueError(
            "Generated script failed Documentary quality checks:\n- "
            + "\n- ".join(reasons)
            + "\n\nFix research/API keys and click Regenerate. The invalid draft was NOT saved as approved."
        )

    project["script"] = script
    project["script_approved"] = False
    project["fact_check_status"] = "pending"
    project["ui_step"] = "script"
    project["script_warnings"] = (
        ["Little research provided — script kept factual and may be shorter than the word target."]
        if thin
        else []
    )
    set_checkpoint(project, "script_ready", True)
    set_checkpoint(project, "flow_pack_ready", False)

    root = project_dir(str(project["id"]))
    (root / "script" / "script.txt").write_text(script, encoding="utf-8")
    (root / "script" / "script_meta.json").write_text(
        json.dumps(
            {
                "word_count": wc,
                "target_words": target,
                "template": TEMPLATE_ID,
                "language": lang,
                "workflow": "documentary",
                "pov": "third_person",
                "factuality": "nonfiction",
                "research_thin": thin,
                "legacy_storytime_context": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    save_project(project)
    append_log(str(project["id"]), f"script generated words={wc} template={TEMPLATE_ID}")
    return project


def save_edited_script(project: dict[str, Any], script: str) -> dict[str, Any]:
    script = strip_metadata_leaks((script or "").strip())
    if not script:
        raise ValueError("Script is empty.")
    snap = project.get("creative_profile_snapshot") if isinstance(project.get("creative_profile_snapshot"), dict) else {}
    lang = language_from_profile(snap) if snap else str(project.get("language") or "en")
    ok, reasons = validate_documentary_script(
        script,
        language=lang,
        target_words=int(project.get("target_words") or 1500),
        allow_short_if_thin_research=True,
    )
    if not ok:
        raise ValueError("Edited script failed Documentary checks:\n- " + "\n- ".join(reasons))
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


def _mock_script(topic: str, target_words: int, *, research_notes: str = "") -> str:
    """English third-person offline placeholder — never Spanish confession."""
    base = (
        f"[DOGFOOD MOCK — NOT FOR PUBLICATION] {topic}. "
        "This is a placeholder third-person English documentary narration used only to verify the pipeline. "
        "In production, replace with a fact-checked English script grounded in research. "
    )
    if research_notes.strip():
        base += "Research notes were provided and must constrain any real generation. "
    words = base.split()
    filler = (
        "The company grew quickly, raised capital, expanded offices, then faced a public reckoning "
        "as numbers failed to match the story sold to investors and the press. "
    ).split()
    while len(words) < max(80, int(target_words * 0.3)):
        words.extend(filler)
    return " ".join(words[: max(80, int(target_words * 0.35))])
