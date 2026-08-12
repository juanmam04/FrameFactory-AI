"""Documentary script generation (English factual business documentary)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.documentary.project import append_log, project_dir, save_project, set_checkpoint
from src.script_generator import count_words, generar_guion


def generate_documentary_script(project: dict[str, Any], *, use_llm: bool = True) -> dict[str, Any]:
    """Generate or refresh script into project workspace. Does not auto-approve."""
    topic = str(project.get("topic") or "").strip()
    if not topic:
        raise ValueError("project.topic required")
    notes = str(project.get("research_notes") or "").strip()
    sources = project.get("sources") or []
    src_txt = "\n".join(f"- {s}" for s in sources) if sources else "- (none listed yet)"

    tema = (
        f"{topic}\n\n"
        f"RESEARCH NOTES (use only these facts; if something is unknown, say so or omit — NEVER invent):\n"
        f"{notes or '(empty — keep claims minimal and clearly general)'}\n\n"
        f"SOURCES:\n{src_txt}"
    )
    target = int(project.get("target_words") or 1500)

    if use_llm:
        script, wc, _mins = generar_guion(
            tema,
            target_words=target,
            plantilla="business_documentary_en",
        )
    else:
        script = _mock_script(topic, target)
        wc = count_words(script)

    project["script"] = script
    project["script_approved"] = False
    project["fact_check_status"] = "pending"
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
        raise ValueError("script empty")
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
        raise ValueError("No script to approve")
    project["script_approved"] = True
    project["fact_check_status"] = "approved"
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
