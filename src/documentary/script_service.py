"""Documentary script generation (English factual business documentary)."""
from __future__ import annotations

import json
import logging
from typing import Any

from src.documentary.channel import documentary_script_context, language_from_profile
from src.documentary.editorial import DOCUMENTARY_INVARIANTS, STORY_CRAFT_BIBLE
from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.documentary.script_quality import (
    close_script_ending,
    ending_is_abrupt,
    heuristic_script_quality,
    revise_script_once,
    strip_essay_tail,
)
from src.documentary.script_validation import editorial_warnings, strip_metadata_leaks, validate_documentary_script
from src.documentary.story_plan import (
    get_story_plan,
    story_plan_is_approved,
    story_plan_prompt_block,
)
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
    """User payload — subject + research + approved story plan (no Working title leak)."""
    topic = str(project.get("topic") or "").strip()
    notes = str(project.get("research_notes") or "").strip()
    sources = project.get("sources") or []
    src_txt = "\n".join(f"- {s}" for s in sources) if sources else "- (none listed yet)"
    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    entity = str(idea.get("primary_entity") or "").strip()
    subject_line = topic
    if entity and entity.lower() not in topic.lower():
        subject_line = f"{topic}\nPrimary subject: {entity}"
    plan = get_story_plan(project)
    plan_block = story_plan_prompt_block(plan)
    parts = [
        f"SUBJECT:\n{subject_line}",
        f"RESEARCH NOTES (factual spine — use only these facts; if unknown, omit — NEVER invent):\n"
        f"{notes or '(empty — keep claims minimal and clearly general; prefer a shorter script)'}",
        f"SOURCES:\n{src_txt}",
    ]
    if plan_block:
        parts.append(plan_block)
    parts.append(
        "STORYTELLING BRIEF:\n"
        "Write ENTERTAINING true-story narration from SELECTED STORY BEATS — not an essay.\n"
        "Each paragraph should move an event, decision, or consequence forward.\n"
        "Use real names (people, companies, investors) when research supports them.\n"
        "Causality: A enables B. Cold open on the hook.\n"
        "The LAST two paragraphs must be the ENDING STATE as events (year, number, who is left),\n"
        "then one image that answers the cold open. Do not stop at 'uncertain future' or a lecture.\n"
        "HARD BAN: 'underscores', 'broader implications', 'in conclusion', 'lessons', 'highlighted the vulnerabilities'.\n"
        "Spoken English. Short paragraphs. Do not invent facts."
    )
    return "\n\n".join(parts)


def log_pre_generation_debug(project: dict[str, Any], *, target: int, research_chars: int) -> None:
    snap = project.get("creative_profile_snapshot") if isinstance(project.get("creative_profile_snapshot"), dict) else {}
    lang = language_from_profile(snap) if snap else str(project.get("language") or "en")
    plan = get_story_plan(project)
    msg = (
        f"Workflow: documentary | Template: {TEMPLATE_ID} | Language: {lang} | "
        f"POV: third_person | Factuality: nonfiction | StoryPlan: {bool(plan.get('central_story'))} "
        f"approved={bool(plan.get('approved'))} beats={len(plan.get('beats') or [])} | "
        f"Topic: {(project.get('topic') or '')[:80]!r} | Target words: {target} | "
        f"Research chars: {research_chars} | Sources: {len(project.get('sources') or [])} | "
        f"Legacy storytime context: NONE"
    )
    logger.info(msg)
    print(f"[documentary-script] {msg}")
    append_log(str(project["id"]), msg)


def generate_documentary_script(project: dict[str, Any], *, use_llm: bool = True) -> dict[str, Any]:
    """Generate script from approved Story Plan. Does not auto-approve."""
    topic = str(project.get("topic") or "").strip()
    if not topic:
        raise ValueError("Choose a topic before generating a script.")

    if use_llm and not story_plan_is_approved(project):
        raise ValueError(
            "Approve the Story Plan first (Story step). "
            "Do not generate a full script until central story + beats are approved."
        )

    idea = project.get("idea") if isinstance(project.get("idea"), dict) else {}
    notes = str(project.get("research_notes") or "").strip()
    thin = research_is_thin(project)
    tema = build_documentary_tema(project)
    target = int(project.get("target_words") or 2000)
    snap = project.get("creative_profile_snapshot") if isinstance(project.get("creative_profile_snapshot"), dict) else {}
    lang = language_from_profile(snap) if snap else str(project.get("language") or "en")
    creative_context = (
        DOCUMENTARY_INVARIANTS
        + "\n\n"
        + STORY_CRAFT_BIBLE
        + "\n\n"
        + documentary_script_context(snap or None, idea=idea or None)
    )

    log_pre_generation_debug(project, target=target, research_chars=len(notes))

    quality_meta: dict[str, Any] = {}
    if use_llm:
        script, wc, _mins = generar_guion(
            tema,
            target_words=target,
            plantilla=TEMPLATE_ID,
            creative_context=creative_context,
            force_este_eres_tu_opening=False,
        )
        # Heuristic quality; one directed revision if clearly failing.
        review = heuristic_script_quality(script, target_words=target)
        quality_meta = {"heuristic": review, "revised": False}
        needs_rev = (not review.get("pass")) or any(
            "Ending leans" in p or "abrupt" in p.lower() or "filler" in p.lower() or "Repetitive" in p
            for p in (review.get("problems") or [])
        )
        pre_rev = script
        pre_wc = count_words(script)
        if needs_rev:
            append_log(str(project["id"]), "script quality FAIL → one revision")
            plan_block = story_plan_prompt_block(get_story_plan(project))
            revised = revise_script_once(
                script,
                story_plan_block=plan_block,
                research_notes=notes,
                review=review,
                target_words=target,
            )
            rev_wc = count_words(revised)
            # Never keep a revision that collapses the draft (model often "fixes" by shortening into an essay stub).
            if rev_wc >= int(pre_wc * 0.85):
                script = revised
                quality_meta["revised"] = True
                quality_meta["after"] = heuristic_script_quality(script, target_words=target)
            else:
                append_log(str(project["id"]), f"revision discarded (shrunk {pre_wc}→{rev_wc}); keep draft + strip essay tail")
                script = pre_rev
                quality_meta["revised"] = False
                quality_meta["revision_discarded_shrink"] = True
        script = strip_essay_tail(script)
        plan = get_story_plan(project)
        if ending_is_abrupt(script, str(plan.get("ending_state") or "")):
            append_log(str(project["id"]), "script ending abrupt → append landing")
            script = close_script_ending(
                script,
                ending_state=str(plan.get("ending_state") or ""),
                hook=str(plan.get("hook") or ""),
                research_notes=notes,
            )
        wc = count_words(script)
    else:
        script = _mock_script(topic, target, research_notes=notes)
        wc = count_words(script)
        quality_meta = {"heuristic": heuristic_script_quality(script, target_words=target), "revised": False}

    script = strip_metadata_leaks(script)
    ok, reasons = validate_documentary_script(
        script,
        language=lang,
        target_words=target,
        # Prefer a solid shorter true story over padding; soft range is 1800–2200.
        allow_short_if_thin_research=True,
        enforce_editorial_heuristics=False,
    )
    if not ok:
        append_log(str(project["id"]), f"script REJECTED: {'; '.join(reasons)}")
        raise ValueError(
            "Generated script failed Documentary quality checks:\n- "
            + "\n- ".join(reasons)
            + "\n\nFix research/Story Plan and regenerate."
        )

    soft = editorial_warnings(script, target_words=target)
    project["script"] = script
    project["script_approved"] = False
    project["fact_check_status"] = "pending"
    project["ui_step"] = "script"
    project["script_quality"] = quality_meta
    # Soft editorial / research gaps are NOT UI blockers.
    project["script_editorial_notes"] = soft
    project["script_warnings"] = (
        ["Little research provided — script may be shorter than target."] if thin else []
    )
    set_checkpoint(project, "script_ready", True)
    set_checkpoint(project, "flow_pack_ready", False)

    from src.documentary.voice_script_sync import invalidate_voice_for_script_change

    invalidate_voice_for_script_change(project, reason="script regenerated")

    root = project_dir(str(project["id"]))
    (root / "script" / "script.txt").write_text(script, encoding="utf-8")
    (root / "script" / "script_meta.json").write_text(
        json.dumps(
            {
                "word_count": wc,
                "target_words": target,
                "target_range": [1800, 2200],
                "template": TEMPLATE_ID,
                "language": lang,
                "workflow": "documentary",
                "pov": "third_person",
                "factuality": "nonfiction",
                "research_thin": thin,
                "story_plan": True,
                "quality": quality_meta,
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
    script = strip_essay_tail(strip_metadata_leaks((script or "").strip()))
    if not script:
        raise ValueError("Script is empty.")
    snap = project.get("creative_profile_snapshot") if isinstance(project.get("creative_profile_snapshot"), dict) else {}
    lang = language_from_profile(snap) if snap else str(project.get("language") or "en")
    target = int(project.get("target_words") or 2000)
    ok, reasons = validate_documentary_script(
        script,
        language=lang,
        target_words=target,
        allow_short_if_thin_research=True,
        enforce_editorial_heuristics=False,
    )
    if not ok:
        raise ValueError("Edited script failed Documentary checks:\n- " + "\n- ".join(reasons))
    soft = editorial_warnings(script, target_words=target)
    project["script"] = script
    project["script_approved"] = False
    project["fact_check_status"] = "pending"
    project["script_editorial_notes"] = soft
    project["script_warnings"] = []  # no peach banners for soft filler
    set_checkpoint(project, "script_ready", True)
    set_checkpoint(project, "flow_pack_ready", False)
    from src.documentary.voice_script_sync import invalidate_voice_for_script_change

    invalidate_voice_for_script_change(project, reason="script edited")
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
        "In production, replace with a fact-checked English script grounded in research and an approved Story Plan. "
    )
    if research_notes.strip():
        base += "Research notes were provided and must constrain any real generation. "
    words = base.split()
    filler = (
        "Adam Neumann co-founded the company. SoftBank invested. The 2019 IPO filing exposed losses. "
        "The public listing was withdrawn. SoftBank arranged a rescue. Later restructuring followed. "
    ).split()
    while len(words) < max(80, int(target_words * 0.3)):
        words.extend(filler)
    return " ".join(words[: max(80, int(target_words * 0.35))])
