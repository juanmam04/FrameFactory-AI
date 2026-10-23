"""Conversational Studio agent: diagnose any project/engine layer, apply only after approval."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.documentary.project import project_dir, save_project, set_checkpoint
from studio.editorial import STAGE_IDS, _load, current, invalidate_production

router = APIRouter(prefix="/api/projects", tags=["creative-agent"])

REPO_ROOT = Path(__file__).resolve().parents[1]

ENGINE_ALLOWLIST = (
    "src/documentary/formats/check_als/",
    "src/documentary/formats/check_als/visuals.py",
    "src/documentary/formats/check_als/script.py",
    "src/documentary/formats/check_als/story_arch.py",
    "src/documentary/formats/check_als/editorial.py",
    "src/documentary/formats/check_als/profile.py",
    "src/documentary/story_bible.py",
    "src/documentary/visual_plan.py",
    "src/documentary/editorial.py",
    "studio/story_architect.py",
    "studio/editorial_script.py",
)

PROJECT_TARGETS = {
    "brief",
    "structure",
    "bible",
    "visual",
    "production",
    "concepts",
    "packaging",
    "script",
    "story",
    "visual_plan",
    "creative_rule",
    "engine_file",
}

FROZEN_PILOT = "pilot-fase2-basket"


class AgentMessage(BaseModel):
    message: str = Field(min_length=3, max_length=4000)
    project_snapshot: dict[str, Any] | None = None
    creative_rules: list[str] = Field(default_factory=list)


class AgentRevision(BaseModel):
    instruction: str = Field(min_length=4, max_length=3000)
    scope: str = "opening"
    project_snapshot: dict[str, Any] | None = None
    creative_rules: list[str] = Field(default_factory=list)


class RuleApproval(BaseModel):
    rule: str = Field(min_length=8, max_length=700)
    project_snapshot: dict[str, Any] | None = None


class ProposedChange(BaseModel):
    target: str
    summary: str = ""
    preview: str = ""
    instruction: str = ""
    path: str = ""
    content: str | dict[str, Any] | None = None


class AgentApply(BaseModel):
    changes: list[ProposedChange] = Field(min_length=1)
    project_snapshot: dict[str, Any] | None = None
    creative_rules: list[str] = Field(default_factory=list)
    confirm_frozen: bool = False


def _client():
    from openai import OpenAI
    from src.documentary.openai_key import require_openai_api_key

    return OpenAI(api_key=require_openai_api_key("FrameFactory Agente Editorial"))


def _llm(messages: list[dict[str, str]], *, json_mode: bool = False, temperature: float = 0.45) -> str:
    kwargs: dict[str, Any] = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": temperature,
        "messages": messages,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return (_client().chat.completions.create(**kwargs).choices[0].message.content or "").strip()


def _clip(obj: Any, limit: int = 12000) -> Any:
    text = json.dumps(obj, ensure_ascii=False, default=str) if not isinstance(obj, str) else obj
    if len(text) <= limit:
        return obj if not isinstance(obj, str) else text
    if isinstance(obj, str):
        return text[:limit] + "…"
    try:
        return json.loads(text[:limit] + '"}')
    except Exception:
        return {"_truncated": text[:limit]}


def _read_json_file(path: Path) -> Any:
    if not path.is_file() or path.stat().st_size <= 0:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _context(p: dict[str, Any]) -> dict[str, Any]:
    ed = current(p) if p.get("editorial") else current({"editorial": {}})
    stages = ed.get("stages", {})
    chosen: dict[str, Any] = {}
    for key in ("concepts", "packaging"):
        data = stages.get(key, {}).get("data", {})
        chosen[key] = next(
            (x for x in data.get("options", []) if str(x.get("id")) == str(data.get("selected"))),
            {},
        )
    pid = str(p.get("id") or "")
    root = project_dir(pid) if pid else None
    story_bible = None
    visual_plan = None
    if root is not None:
        story_bible = _read_json_file(root / "flow-pack" / "story-bible.json")
        visual_plan = _read_json_file(root / "flow-pack" / "visual-plan.json")
    story_plan = p.get("story_plan") if isinstance(p.get("story_plan"), dict) else {}
    history = p.get("creative_agent_history") if isinstance(p.get("creative_agent_history"), list) else []
    turns = []
    for item in history[-20:]:
        if not isinstance(item, dict):
            continue
        if item.get("feedback"):
            turns.append({"role": "user", "content": str(item.get("feedback") or "")[:2000]})
        if item.get("reply"):
            turns.append({"role": "assistant", "content": str(item.get("reply") or "")[:3000]})
    return {
        "id": pid,
        "title": p.get("title"),
        "topic": p.get("topic"),
        "language": p.get("language"),
        "format": p.get("format") or p.get("format_id"),
        "ui_step": p.get("ui_step"),
        "active_stage": ed.get("active_stage"),
        "checkpoints": p.get("checkpoints") or {},
        "brief": stages.get("brief", {}).get("data", {}),
        "approved_story": chosen.get("concepts"),
        "approved_packaging": chosen.get("packaging"),
        "structure": _clip(stages.get("structure", {}).get("data", {}), 8000),
        "bible": _clip(stages.get("bible", {}).get("data", {}), 8000),
        "visual_identity": _clip(stages.get("visual", {}).get("data", {}), 4000),
        "production": _clip(stages.get("production", {}).get("data", {}), 4000),
        "story_plan": _clip(story_plan, 6000),
        "flow_story_bible": _clip(story_bible, 6000) if story_bible else None,
        "visual_plan": _clip(visual_plan, 6000) if visual_plan else None,
        "script": str(p.get("script") or "")[:28000],
        "script_approved": bool(p.get("script_approved")),
        "existing_rules": p.get("creative_rules") or [],
        "conversation_turns": turns,
        "engine_allowlist": list(ENGINE_ALLOWLIST),
    }


def _history_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for turn in context.get("conversation_turns") or []:
        role = str(turn.get("role") or "")
        content = str(turn.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            out.append({"role": role, "content": content})
    return out[-20:]


def _normalize_proposals(raw: Any) -> list[dict[str, Any]]:
    items = raw if isinstance(raw, list) else []
    out: list[dict[str, Any]] = []
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        target = str(item.get("target") or "").strip()
        if target not in PROJECT_TARGETS:
            continue
        path = str(item.get("path") or "").strip().replace("\\", "/")
        if target == "engine_file" and path and not _engine_path_allowed(path):
            continue
        out.append(
            {
                "target": target,
                "summary": str(item.get("summary") or "")[:500],
                "preview": str(item.get("preview") or "")[:2000],
                "instruction": str(item.get("instruction") or item.get("summary") or "")[:3000],
                "path": path if target == "engine_file" else "",
            }
        )
    return out


def _engine_path_allowed(rel: str) -> bool:
    rel = rel.replace("\\", "/").lstrip("./")
    if ".." in rel.split("/") or rel.startswith("/") or ":" in rel[:3]:
        return False
    if any(part.startswith(".") for part in rel.split("/") if part not in {".", ".."}):
        # allow normal files; block .env
        if any(part.startswith(".env") for part in rel.split("/")):
            return False
    for allowed in ENGINE_ALLOWLIST:
        a = allowed.rstrip("/")
        if allowed.endswith("/"):
            if rel.startswith(a + "/") or rel == a:
                return True
        elif rel == a:
            return True
    return False


@router.post("/{project_id}/agent/chat")
def agent_chat(project_id: str, body: AgentMessage):
    p = _load(project_id, body.project_snapshot)
    rules = list(dict.fromkeys([*(p.get("creative_rules") or []), *body.creative_rules]))[:35]
    context = _context(p)
    context["existing_rules"] = rules
    system = (
        "You are the built-in FrameFactory creative/technical director inside Studio. "
        "Respond in the user's language. "
        "You can discuss ANY layer: premise, story architecture, narrative bible, visual plan, "
        "script, creative rules, or engine prompt/validation code under the allowlist. "
        "First understand the user's problem, explain clearly what is wrong and why, then propose "
        "concrete changes. DO NOT claim you already applied changes. "
        "Treat entertainment POV / Check ALS fiction as designed stories, not documentaries of fact. "
        "If the issue is engine behavior (prompts, tags, validation), propose target=engine_file "
        "with a path from engine_allowlist. Prefer project-layer fixes when possible. "
        "Always return JSON with: "
        "reply (clear explanation + advice), "
        "diagnosis (which layer fails), "
        "proposed_changes (array of {target, summary, preview, instruction, path?}), "
        "proposed_rule (reusable rule or empty), "
        "needs_approval (always true). "
        "Valid targets: brief, structure, bible, visual, production, concepts, packaging, "
        "script, story, visual_plan, creative_rule, engine_file. "
        "Never execute repository writes in this step."
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    messages.extend(_history_messages(context))
    messages.append(
        {
            "role": "user",
            "content": json.dumps(
                {"feedback": body.message, "project": {k: v for k, v in context.items() if k != "conversation_turns"}},
                ensure_ascii=False,
                default=str,
            ),
        }
    )
    try:
        result = json.loads(_llm(messages, json_mode=True))
        proposals = _normalize_proposals(result.get("proposed_changes"))
        # Back-compat: older clients expected suggested_edit for script-only revise.
        suggested_edit = ""
        suggested_scope = "opening"
        for ch in proposals:
            if ch["target"] == "script":
                suggested_edit = ch.get("instruction") or ch.get("summary") or ""
                suggested_scope = "full" if "full" in (ch.get("summary") or "").lower() else "opening"
                break
        if not suggested_edit:
            suggested_edit = str(result.get("suggested_edit") or "")[:3000]
            suggested_scope = (
                result.get("suggested_scope")
                if result.get("suggested_scope") in ("opening", "full")
                else "opening"
            )
            if suggested_edit and not any(c["target"] == "script" for c in proposals):
                proposals.append(
                    {
                        "target": "script",
                        "summary": suggested_edit[:500],
                        "preview": suggested_edit[:2000],
                        "instruction": suggested_edit,
                        "path": "",
                    }
                )
        answer = {
            "reply": str(result.get("reply") or "Revisá los problemas señalados."),
            "diagnosis": str(result.get("diagnosis") or "")[:800],
            "proposed_changes": proposals,
            "proposed_rule": str(result.get("proposed_rule") or "")[:700],
            "suggested_edit": suggested_edit,
            "suggested_scope": suggested_scope,
            "needs_approval": True,
        }
        p.setdefault("creative_agent_history", []).append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "feedback": body.message,
                "reply": answer["reply"],
                "diagnosis": answer["diagnosis"],
                "proposed_changes": proposals,
            }
        )
        p["creative_agent_history"] = p["creative_agent_history"][-30:]
        p["creative_agent_pending"] = {
            "at": datetime.now(timezone.utc).isoformat(),
            "proposed_changes": proposals,
            "proposed_rule": answer["proposed_rule"],
        }
        save_project(p)
        return answer
    except Exception as e:
        raise HTTPException(502, "No se pudo consultar el agente: " + str(e)[:200]) from e


def _invalidate_after_narrative(project: dict[str, Any], *, touch_script: bool) -> None:
    invalidate_production(project)
    if touch_script:
        from src.documentary.voice_script_sync import invalidate_voice_for_script_change

        try:
            invalidate_voice_for_script_change(project, reason="agent applied narrative change")
        except Exception:
            set_checkpoint(project, "voice_ready", False)
            set_checkpoint(project, "render_ready", False)


def _apply_editorial_stage(project: dict[str, Any], stage: str, instruction: str, content: Any) -> str:
    if stage not in STAGE_IDS:
        raise HTTPException(400, f"Etapa editorial inválida: {stage}")
    ed = current(project)
    previous = ed["stages"][stage].get("data") or {}
    if isinstance(content, dict) and content:
        new_data = content
    else:
        raw = _llm(
            [
                {
                    "role": "system",
                    "content": (
                        "You rewrite ONE editorial stage JSON for a FrameFactory project. "
                        "Return ONLY a JSON object for that stage data (no markdown). "
                        "Preserve useful structure; apply the user's instruction precisely."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"stage": stage, "instruction": instruction, "current_data": previous},
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ],
            json_mode=True,
            temperature=0.4,
        )
        new_data = json.loads(raw)
        if not isinstance(new_data, dict):
            raise HTTPException(502, "El modelo no devolvió JSON de etapa válido.")
    index = STAGE_IDS.index(stage)
    ed["stages"][stage]["data"] = new_data
    ed["stages"][stage]["approved"] = False
    ed["stages"][stage]["approved_at"] = None
    for later in STAGE_IDS[index + 1 :]:
        ed["stages"][later]["approved"] = False
        ed["stages"][later]["approved_at"] = None
    ed["active_stage"] = stage
    ed["history"].append(
        {
            "stage": stage,
            "action": "agent_apply",
            "at": datetime.now(timezone.utc).isoformat(),
            "note": instruction[:240],
        }
    )
    project["editorial"] = ed
    _invalidate_after_narrative(project, touch_script=True)
    return f"editorial.stages.{stage}"


def _apply_script(project: dict[str, Any], instruction: str, scope: str = "full") -> str:
    script = str(project.get("script") or "").strip()
    if not script:
        raise HTTPException(409, "Este proyecto todavía no tiene un guion.")
    if project.get("script_approved"):
        project["script_approved"] = False
    scope = scope if scope in ("opening", "full") else "full"
    if scope == "full" and len(script) > 13500:
        scope = "opening"
    cut = min(len(script), 6500)
    if scope == "opening":
        boundary = script.rfind("\n\n", 0, cut)
        if boundary > 1200:
            cut = boundary
    original = script if scope == "full" else script[:cut]
    rest = "" if scope == "full" else script[cut:]
    context = _context(project)
    context.pop("script", None)
    edited = _llm(
        [
            {
                "role": "system",
                "content": (
                    "Rewrite the given fictional POV narrative according to the user's requested edit. "
                    "Return ONLY revised narration, not commentary. Keep perspective and characters. "
                    "Comparable length; smooth transition into any untouched remainder."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_instruction": instruction,
                        "permanent_rules": project.get("creative_rules") or [],
                        "project": context,
                        "text_to_rewrite": original,
                        "next_untouched_text": rest[:700],
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ],
        temperature=0.6,
    )
    if len(edited.split()) < max(60, int(len(original.split()) * 0.45)):
        raise HTTPException(502, "La corrección quedó demasiado corta. Se conservó el guion.")
    from src.documentary.script_service import save_edited_script

    updated = save_edited_script(project, edited + rest)
    if updated is not project:
        project.update(updated)
    return "script"


def _apply_story(project: dict[str, Any], instruction: str, content: Any) -> str:
    current_plan = project.get("story_plan") if isinstance(project.get("story_plan"), dict) else {}
    if isinstance(content, dict) and content:
        new_plan = content
    else:
        raw = _llm(
            [
                {
                    "role": "system",
                    "content": (
                        "Rewrite the project's story_plan JSON according to the instruction. "
                        "Return ONLY a JSON object."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"instruction": instruction, "current_story_plan": current_plan},
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ],
            json_mode=True,
            temperature=0.4,
        )
        new_plan = json.loads(raw)
        if not isinstance(new_plan, dict):
            raise HTTPException(502, "story_plan inválido.")
    project["story_plan"] = new_plan
    project["story_plan_approved"] = False
    set_checkpoint(project, "story_ready", False)
    set_checkpoint(project, "script_ready", False)
    _invalidate_after_narrative(project, touch_script=True)
    return "story_plan"


def _apply_visual_plan(project: dict[str, Any], instruction: str, content: Any) -> str:
    pid = str(project.get("id") or "")
    path = project_dir(pid) / "flow-pack" / "visual-plan.json"
    current_plan = _read_json_file(path) or {}
    if isinstance(content, dict) and content:
        new_plan = content
    else:
        raw = _llm(
            [
                {
                    "role": "system",
                    "content": (
                        "Rewrite visual-plan.json for this episode according to the instruction. "
                        "Return ONLY a JSON object."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"instruction": instruction, "current_visual_plan": current_plan},
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ],
            json_mode=True,
            temperature=0.35,
        )
        new_plan = json.loads(raw)
        if not isinstance(new_plan, dict):
            raise HTTPException(502, "visual_plan inválido.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(new_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    set_checkpoint(project, "flow_pack_ready", False)
    set_checkpoint(project, "images_imported", False)
    return "flow-pack/visual-plan.json"


def _apply_engine_file(rel_path: str, instruction: str, content: str | None) -> str:
    rel = rel_path.replace("\\", "/").lstrip("./")
    if not _engine_path_allowed(rel):
        raise HTTPException(400, f"Path fuera de allowlist: {rel}")
    if rel.startswith("projects/") and FROZEN_PILOT in rel:
        raise HTTPException(403, "El pilot congelado no se modifica por el agente.")
    dest = REPO_ROOT / rel
    if not dest.resolve().is_relative_to(REPO_ROOT.resolve()):
        raise HTTPException(400, "Path inválido.")
    if content is not None and str(content).strip():
        new_text = str(content)
    else:
        if not dest.is_file():
            raise HTTPException(404, f"No existe el archivo del motor: {rel}")
        old = dest.read_text(encoding="utf-8")
        if len(old) > 120_000:
            raise HTTPException(422, "Archivo demasiado grande para patch automático.")
        new_text = _llm(
            [
                {
                    "role": "system",
                    "content": (
                        "You are editing FrameFactory engine source. Apply the instruction with a "
                        "minimal precise change. Return ONLY the full new file contents, no markdown fences."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"path": rel, "instruction": instruction, "current_file": old},
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0.2,
        )
        if new_text.startswith("```"):
            lines = new_text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            new_text = "\n".join(lines)
        if len(new_text.strip()) < max(40, int(len(old) * 0.3)):
            raise HTTPException(502, "El patch del motor quedó demasiado corto; no se escribió.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new_text if new_text.endswith("\n") else new_text + "\n", encoding="utf-8")
    return rel


@router.post("/{project_id}/agent/apply")
def apply_with_agent(project_id: str, body: AgentApply):
    p = _load(project_id, body.project_snapshot)
    if project_id == FROZEN_PILOT and not body.confirm_frozen:
        # Allow script/bible of other projects freely; pilot needs explicit confirm for engine.
        if any(c.target == "engine_file" for c in body.changes):
            raise HTTPException(
                403,
                "pilot-fase2-basket está congelado para cambios de motor. "
                "Pasá confirm_frozen=true solo si lo pediste explícitamente.",
            )
    rules = list(dict.fromkeys([*(p.get("creative_rules") or []), *body.creative_rules]))[:35]
    p["creative_rules"] = rules
    applied: list[dict[str, str]] = []
    notes: list[str] = []
    for change in body.changes:
        target = change.target.strip()
        if target not in PROJECT_TARGETS:
            raise HTTPException(400, f"Target inválido: {target}")
        instruction = (change.instruction or change.summary or "").strip()
        if target == "creative_rule":
            rule = (change.preview or instruction or change.summary).strip()
            if len(rule) < 8:
                raise HTTPException(422, "Regla demasiado corta.")
            existing = p.setdefault("creative_rules", [])
            if rule.casefold() not in [x.casefold() for x in existing]:
                existing.append(rule)
            p["creative_rules"] = existing[-35:]
            applied.append({"target": target, "path": "creative_rules"})
            notes.append("Regla creativa guardada.")
            continue
        if target == "script":
            path = _apply_script(p, instruction or "Mejorá el guion según el diagnóstico.", "full")
            applied.append({"target": target, "path": path})
            notes.append("Guion actualizado. Revisá el paso Guion / auditoría.")
            continue
        if target in STAGE_IDS:
            path = _apply_editorial_stage(p, target, instruction, change.content)
            applied.append({"target": target, "path": path})
            notes.append(f"Etapa {target} actualizada (aprobaciones posteriores reiniciadas).")
            continue
        if target == "story":
            path = _apply_story(p, instruction, change.content)
            applied.append({"target": target, "path": path})
            notes.append("Historia / story_plan actualizada. Regenerá guion si hace falta.")
            continue
        if target == "visual_plan":
            path = _apply_visual_plan(p, instruction, change.content)
            applied.append({"target": target, "path": path})
            notes.append("Plan visual actualizado. Revisá Imágenes / Flow.")
            continue
        if target == "engine_file":
            path = _apply_engine_file(
                change.path,
                instruction,
                change.content if isinstance(change.content, str) else None,
            )
            applied.append({"target": target, "path": path})
            notes.append(f"Motor actualizado: {path}. Probá de nuevo el paso afectado.")
            continue
        raise HTTPException(400, f"Target no implementado: {target}")

    p.setdefault("creative_agent_revisions", []).append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "applied": applied,
            "changes": [c.model_dump() for c in body.changes],
        }
    )
    p["creative_agent_revisions"] = p["creative_agent_revisions"][-8:]
    p["creative_agent_pending"] = {}
    save_project(p)
    verify = " · ".join(notes) if notes else "Cambios aplicados."
    return {
        "applied": True,
        "targets": applied,
        "note": verify,
        "creative_rules": p.get("creative_rules") or [],
    }


@router.post("/{project_id}/agent/revise")
def revise_with_agent(project_id: str, body: AgentRevision):
    p = _load(project_id, body.project_snapshot)
    script = str(p.get("script") or "").strip()
    if not script:
        raise HTTPException(409, "Este proyecto todavía no tiene un guion.")
    if p.get("script_approved"):
        raise HTTPException(409, "El guion está aprobado. Reabrilo antes de modificarlo.")
    scope = body.scope if body.scope in ("opening", "full") else "opening"
    if scope == "full" and len(script) > 13500:
        raise HTTPException(
            422,
            "El guion es demasiado largo para una reescritura completa segura. Elegí corregir el inicio.",
        )
    rules = list(dict.fromkeys([*(p.get("creative_rules") or []), *body.creative_rules]))[:35]
    p["creative_rules"] = rules
    previous = script
    path = _apply_script(p, body.instruction, scope)
    p.setdefault("creative_agent_revisions", []).append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "instruction": body.instruction,
            "scope": scope,
            "previous_script": previous,
            "path": path,
        }
    )
    p["creative_agent_revisions"] = p["creative_agent_revisions"][-4:]
    save_project(p)
    return {
        "applied": True,
        "scope": scope,
        "script": p["script"],
        "note": "Guion actualizado. La aprobación y auditoría se reiniciaron para revisarlo.",
    }


@router.post("/{project_id}/agent/rule")
def approve_creative_rule(project_id: str, body: RuleApproval):
    p = _load(project_id, body.project_snapshot)
    rules = p.setdefault("creative_rules", [])
    rule = body.rule.strip()
    if rule.casefold() not in [x.casefold() for x in rules]:
        rules.append(rule)
    p["creative_rules"] = rules[-35:]
    save_project(p)
    return {"approved": True, "creative_rules": p["creative_rules"]}
