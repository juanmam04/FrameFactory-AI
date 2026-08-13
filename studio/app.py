"""FrameFactory Documentary Studio — FastAPI (not Streamlit)."""
from __future__ import annotations

import os
import re
import traceback
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from src.config_loader import BASE

load_dotenv(BASE / ".env")
load_dotenv(BASE / ".env.local", override=True)
load_dotenv(BASE / "env.local", override=True)

from src.documentary.runtime import configure_workspace, on_vercel  # noqa: E402

configure_workspace()

from src.documentary.channel import (  # noqa: E402
    business_documentary_profile,
    channel_display_name,
    duration_range_from_profile,
    goal_count_from_profile,
    is_documentary_profile,
    language_from_profile,
    profile_snapshot,
    target_words_from_profile,
)
from src.documentary.credentials import credential_report
from src.documentary.flow_pack import export_flow_pack, load_shot_list
from src.documentary.import_images import import_images, import_uploaded_images
from src.documentary.visual_plan import (
    format_single_prompt,
    load_visual_plan,
    plan_to_markdown as visual_plan_to_markdown,
    sync_ready_from_disk,
    update_visual_description,
)
from src.documentary.ideas import generate_story_ideas
from src.documentary.openai_key import reload_env
from src.documentary.project import (
    PROJECTS_ROOT,
    create_project,
    derive_progress,
    list_projects_for_session,
    load_project,
    project_dir,
    save_project,
    session_stats,
)
from src.documentary.research_service import generate_research_brief
from src.documentary.script_service import approve_script, generate_documentary_script, save_edited_script
from src.documentary.story_plan import (
    approve_story_plan,
    generate_story_plan,
    get_story_plan,
    plan_to_markdown,
    save_story_plan,
)
from src.documentary.voice_service import generate_project_voice
from src.documentary.assemble_service import assemble_and_render
from src.saas_creative_profile import merge_profile_disk
from src.saas_sessions import (
    OUTPUT_DIR,
    add_session,
    ensure_store,
    get_session,
    load_store,
    persist_session,
    persist_session_summary,
    set_active_session,
)

ROOT = Path(__file__).resolve().parent

STEPS = ["topic", "research", "story", "script", "flow", "images", "voice", "render", "done"]

_PROJECT_RE = re.compile(r"^/api/projects/([^/]+)")


def _reject_heavy_on_vercel() -> None:
    if on_vercel():
        raise HTTPException(
            400,
            "Voice and render need FFmpeg on your Mac. Run `npm run dev` locally, then Push to Supabase.",
        )


def _sync_safe(fn) -> None:
    try:
        fn()
    except Exception:
        traceback.print_exc()


class WorkspaceSyncMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/assets") or path in {"/health", "/"}:
            return await call_next(request)
        from src.documentary import cloud_sync

        if not cloud_sync.configured():
            return await call_next(request)

        m = _PROJECT_RE.match(path)
        pid = m.group(1) if m else None
        if on_vercel() and request.method in {"GET", "HEAD"}:
            if pid:
                _sync_safe(lambda: cloud_sync.pull_project(pid))
                _sync_safe(cloud_sync.pull_sessions)
            elif path.startswith("/api/"):
                _sync_safe(cloud_sync.pull_all)

        response = await call_next(request)

        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and path.startswith("/api/")
            and path not in {"/api/sync/push", "/api/sync/pull"}
        ):
            if pid:
                _sync_safe(lambda: cloud_sync.push_project(pid))
                _sync_safe(cloud_sync.push_sessions)
            else:
                _sync_safe(cloud_sync.push_all)
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="FrameFactory Studio", docs_url="/api/docs")
    app.add_middleware(WorkspaceSyncMiddleware)
    app.mount("/assets", StaticFiles(directory=str(ROOT / "static")), name="assets")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse((ROOT / "templates" / "index.html").read_text(encoding="utf-8"))

    @app.get("/health")
    def health():
        return {"ok": True, "app": "documentary-studio", "vercel": on_vercel()}

    # ── channel / home ──────────────────────────────────────────────
    @app.get("/api/bootstrap")
    def bootstrap():
        reload_env()
        sess, profile = _ensure_channel()
        goal = goal_count_from_profile(profile, 100)
        stats = session_stats(str(sess.get("id") or ""), goal)
        projects = [
            _project_card(p)
            for p in sorted(
                list_projects_for_session(str(sess.get("id") or "")),
                key=lambda x: int(x.get("episode_number") or 0),
            )
        ]
        creds = credential_report(live=False)
        return {
            "runtime": {
                "vercel": on_vercel(),
                "voice_render": not on_vercel(),
            },
            "channel": {
                "name": channel_display_name(profile, str(sess.get("title") or "")),
                "session_id": sess.get("id"),
                "tagline": (profile.get("channel") or {}).get("tagline")
                or "Fascinating true stories about companies.",
            },
            "workspace": {
                "projects_dir": str(PROJECTS_ROOT),
                "data_dir": str(OUTPUT_DIR),
                "synced": bool(
                    (
                        os.getenv("DATABASE_URL")
                        or os.getenv("FRAMEFACTORY_WORKSPACE")
                        or os.getenv("FRAMEFACTORY_PROJECTS_DIR")
                        or ""
                    ).strip()
                ),
                "supabase": bool((os.getenv("DATABASE_URL") or "").strip()),
            },
            "stats": stats,
            "projects": projects,
            "credentials": {
                "openai": {"status": creds["openai"].status, "detail": creds["openai"].detail},
                "elevenlabs": {
                    "status": creds["elevenlabs"].status,
                    "detail": creds["elevenlabs"].detail,
                },
                "ready_research": creds["ready_research"],
                "ready_voice": creds["ready_voice"],
            },
        }

    @app.post("/api/credentials/recheck")
    def recheck_credentials():
        reload_env()
        creds = credential_report(live=True)
        return {
            "openai": {"status": creds["openai"].status, "detail": creds["openai"].detail},
            "elevenlabs": {"status": creds["elevenlabs"].status, "detail": creds["elevenlabs"].detail},
            "ready_research": creds["ready_research"],
            "ready_voice": creds["ready_voice"],
        }

    @app.get("/api/sync/status")
    def sync_status():
        from src.documentary import cloud_sync

        return cloud_sync.status()

    @app.post("/api/sync/push")
    def sync_push():
        from src.documentary import cloud_sync

        if not cloud_sync.configured():
            raise HTTPException(400, "Falta DATABASE_URL en .env.local (Supabase)")
        try:
            return cloud_sync.push_all()
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/sync/pull")
    def sync_pull():
        from src.documentary import cloud_sync

        if not cloud_sync.configured():
            raise HTTPException(400, "Falta DATABASE_URL en .env.local (Supabase)")
        try:
            return cloud_sync.pull_all()
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    # ── ideas ───────────────────────────────────────────────────────
    @app.post("/api/ideas")
    def ideas(body: IdeasBody | None = None):
        body = body or IdeasBody()
        sess, profile = _ensure_channel()
        prior = list_projects_for_session(str(sess.get("id") or ""))
        try:
            items = generate_story_ideas(
                profile,
                prior_videos=prior,
                memory_summary=str(sess.get("memory_summary") or ""),
                count=int(body.count or 5),
                use_llm=True,
            )
            return {"ideas": items}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects")
    def new_project(body: NewProjectBody):
        sess, profile = _ensure_channel()
        idea = body.idea or {
            "title_concept": body.title or body.topic,
            "story": body.topic,
            "hook": "",
            "why_it_works": "User topic",
            "content_pillar": "",
            "visual_potential": "Medium",
            "research_risk": "Medium",
            "primary_entity": (body.topic or "")[:80],
        }
        topic = str(idea.get("story") or idea.get("title_concept") or body.topic or "").strip()
        title = str(idea.get("title_concept") or body.title or topic).strip()
        if not topic:
            raise HTTPException(400, "Topic required")
        try:
            data = create_project(
                topic,
                title=title,
                target_words=target_words_from_profile(profile, 2000),
                session_id=str(sess.get("id") or ""),
                creative_profile=profile_snapshot(profile),
                idea=idea,
                language=language_from_profile(profile),
                target_duration_min=duration_range_from_profile(profile),
            )
            return {"project": _project_full(data)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        try:
            return {"project": _project_full(load_project(project_id))}
        except FileNotFoundError as e:
            raise HTTPException(404, str(e)) from e

    @app.patch("/api/projects/{project_id}/step")
    def set_step(project_id: str, body: StepBody):
        p = load_project(project_id)
        if body.step not in STEPS:
            raise HTTPException(400, "Invalid step")
        step = body.step
        # Cannot jump to Script without an approved Story Plan
        if step == "script" and not (p.get("story_plan_approved") or (p.get("story_plan") or {}).get("approved")):
            step = "story"
        p["ui_step"] = step
        save_project(p)
        return {"project": _project_full(p)}

    # ── research ────────────────────────────────────────────────────
    @app.post("/api/projects/{project_id}/research/generate")
    def research_generate(project_id: str):
        try:
            p = generate_research_brief(load_project(project_id), use_llm=True)
            return {"project": _project_full(p)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.put("/api/projects/{project_id}/research")
    def research_save(project_id: str, body: ResearchBody):
        p = load_project(project_id)
        p["research_notes"] = body.notes or ""
        p["sources"] = [s.strip() for s in (body.sources or []) if str(s).strip()]
        p["research_skipped"] = bool(body.skipped)
        p["ui_step"] = "story"
        root = project_dir(project_id)
        (root / "script" / "research_notes.md").write_text(
            f"# Research — {p.get('title')}\n\n{p['research_notes']}\n\n## Sources\n"
            + "\n".join(f"- {s}" for s in p["sources"]),
            encoding="utf-8",
        )
        save_project(p)
        return {"project": _project_full(p)}

    @app.post("/api/projects/{project_id}/story/generate")
    def story_generate(project_id: str):
        try:
            p = generate_story_plan(load_project(project_id), use_llm=True)
            return {"project": _project_full(p), "markdown": plan_to_markdown(get_story_plan(p))}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.put("/api/projects/{project_id}/story")
    def story_save(project_id: str, body: StoryPlanBody):
        try:
            p = save_story_plan(load_project(project_id), body.plan or {})
            return {"project": _project_full(p), "markdown": plan_to_markdown(get_story_plan(p))}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/story/approve")
    def story_approve(project_id: str):
        try:
            p = approve_story_plan(load_project(project_id))
            return {"project": _project_full(p)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    # ── script ──────────────────────────────────────────────────────
    @app.post("/api/projects/{project_id}/script/generate")
    def script_generate(project_id: str):
        try:
            p = generate_documentary_script(load_project(project_id), use_llm=True)
            return {"project": _project_full(p)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.put("/api/projects/{project_id}/script")
    def script_save(project_id: str, body: ScriptBody):
        try:
            p = save_edited_script(load_project(project_id), body.script or "")
            return {"project": _project_full(p)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/script/approve")
    def script_approve(project_id: str):
        try:
            p = approve_script(load_project(project_id))
            # auto flow pack like Streamlit path often does
            try:
                export_flow_pack(p, use_llm=True, rebuild_visuals=True)
                p = load_project(project_id)
            except Exception:
                pass
            p["ui_step"] = "flow"
            save_project(p)
            return {"project": _project_full(p)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    # ── flow / images / voice / render ──────────────────────────────
    @app.post("/api/projects/{project_id}/flow")
    def flow_build(project_id: str):
        try:
            export_flow_pack(load_project(project_id), use_llm=True, rebuild_visuals=True)
            p = load_project(project_id)
            p["ui_step"] = "flow"
            save_project(p)
            return _flow_payload(project_id, p)
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.get("/api/projects/{project_id}/flow")
    def flow_get(project_id: str):
        try:
            return _flow_payload(project_id, load_project(project_id))
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.get("/api/projects/{project_id}/visual-plan")
    def visual_plan_get(project_id: str):
        try:
            plan = load_visual_plan(project_id)
            sync = sync_ready_from_disk(project_id)
            plan = load_visual_plan(project_id)
            return {
                "plan": plan,
                "markdown": visual_plan_to_markdown(plan),
                "sync": sync,
                "project": _project_full(load_project(project_id)),
            }
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.put("/api/projects/{project_id}/visuals/{number}")
    def visual_edit(project_id: str, number: int, body: VisualEditBody):
        try:
            plan = update_visual_description(project_id, number, body.description or "")
            return {"plan": plan, "markdown": visual_plan_to_markdown(plan)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.get("/api/projects/{project_id}/visuals/{number}/prompt")
    def visual_single_prompt(project_id: str, number: int):
        try:
            plan = load_visual_plan(project_id)
            bible = plan.get("visual_bible") or {}
            masters = plan.get("master_references") or []
            for v in plan.get("visuals") or []:
                if int(v.get("number") or 0) == int(number):
                    return {
                        "number": number,
                        "visual_type": v.get("visual_type"),
                        "prompt": format_single_prompt(v, bible, masters)
                        if v.get("visual_type") == "FLOW_REENACTMENT"
                        else (v.get("acquisition_note") or ""),
                        "visual": v,
                    }
            raise HTTPException(404, f"Visual {number:03d} not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/images/import")
    def images_import(project_id: str, body: ImportBody):
        try:
            p = load_project(project_id)
            source = (body.source_dir or "").strip() or str(project_dir(project_id) / "flow-import")
            report = import_images(p, source)
            sync_ready_from_disk(project_id)
            return {"report": report, "project": _project_full(load_project(project_id)), "sync": sync_ready_from_disk(project_id)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/images/upload")
    async def images_upload(
        project_id: str,
        files: list[UploadFile] = File(...),
        force_number: int | None = Form(default=None),
    ):
        """Upload one or many stills from the browser. Name them 001.png (or force_number for one file)."""
        try:
            p = load_project(project_id)
            payload: list[tuple[str, bytes]] = []
            for f in files:
                raw = await f.read()
                if not raw:
                    continue
                payload.append((f.filename or "upload.png", raw))
            if not payload:
                raise ValueError("No files received.")
            report = import_uploaded_images(
                p,
                payload,
                force_number=force_number,
            )
            sync = sync_ready_from_disk(project_id)
            return {
                "report": report,
                "sync": sync,
                "project": _project_full(load_project(project_id)),
            }
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/voice")
    def voice_generate(project_id: str):
        _reject_heavy_on_vercel()
        try:
            generate_project_voice(load_project(project_id))
            p = load_project(project_id)
            p["ui_step"] = "render"
            save_project(p)
            return {"project": _project_full(p)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/render")
    def render_video(project_id: str):
        _reject_heavy_on_vercel()
        try:
            assemble_and_render(load_project(project_id))
            p = load_project(project_id)
            p["ui_step"] = "done"
            save_project(p)
            return {"project": _project_full(p)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    return app


def _flow_payload(project_id: str, p: dict[str, Any]) -> dict[str, Any]:
    shots = load_shot_list(project_id)
    plan = None
    md = ""
    try:
        sync_ready_from_disk(project_id)
        plan = load_visual_plan(project_id)
        md = visual_plan_to_markdown(plan)
        shots = load_shot_list(project_id)
    except Exception:
        pass
    return {
        "shots": shots,
        "visual_plan": plan,
        "visual_plan_markdown": md,
        "project": _project_full(p if p.get("id") else load_project(project_id)),
    }


class IdeasBody(BaseModel):
    count: int = 5


class NewProjectBody(BaseModel):
    topic: str = ""
    title: str = ""
    idea: dict[str, Any] | None = None


class StepBody(BaseModel):
    step: str


class ResearchBody(BaseModel):
    notes: str = ""
    sources: list[str] = Field(default_factory=list)
    skipped: bool = False


class StoryPlanBody(BaseModel):
    plan: dict[str, Any] = Field(default_factory=dict)


class ScriptBody(BaseModel):
    script: str = ""


class VisualEditBody(BaseModel):
    description: str = ""


class ImportBody(BaseModel):
    source_dir: str = ""


def _err(e: BaseException) -> str:
    msg = str(e) or e.__class__.__name__
    if len(msg) > 800:
        msg = msg[:800] + "…"
    return msg


def _project_card(p: dict[str, Any]) -> dict[str, Any]:
    cps = p.get("checkpoints") or {}
    return {
        "id": p.get("id"),
        "title": p.get("title") or p.get("topic"),
        "episode_number": int(p.get("episode_number") or 0),
        "status": "complete" if cps.get("render_ready") else "in_progress",
        "ui_step": p.get("ui_step") or "research",
    }


def _project_full(p: dict[str, Any]) -> dict[str, Any]:
    prog = derive_progress(p)
    plan = get_story_plan(p)
    return {
        "id": p.get("id"),
        "title": p.get("title"),
        "topic": p.get("topic"),
        "episode_number": int(p.get("episode_number") or 0),
        "ui_step": p.get("ui_step") or prog.get("current") or "research",
        "progress": prog,
        "idea": p.get("idea") or {},
        "research_notes": p.get("research_notes") or "",
        "sources": p.get("sources") or [],
        "research_ai_generated": bool(p.get("research_ai_generated")),
        "story_plan": plan,
        "story_plan_approved": bool(p.get("story_plan_approved") or plan.get("approved")),
        "story_plan_markdown": plan_to_markdown(plan) if plan.get("central_story") else "",
        "script": p.get("script") or "",
        "script_approved": bool(p.get("script_approved")),
        "script_warnings": p.get("script_warnings") or [],
        "script_quality": p.get("script_quality") or {},
        "target_words": p.get("target_words") or 2000,
        "voice": p.get("voice") or {},
        "checkpoints": p.get("checkpoints") or {},
        "flow_pack_path": str(project_dir(str(p["id"])) / "flow-pack") if p.get("id") else "",
    }


def _ensure_channel() -> tuple[dict[str, Any], dict[str, Any]]:
    store = ensure_store()
    for s in store.get("sessions") or []:
        if not isinstance(s, dict):
            continue
        title = str(s.get("title") or "")
        prof = merge_profile_disk(s.get("creative_profile"))
        ch_name = str((prof.get("channel") or {}).get("name") or "")
        if "100 Days — Business Documentaries" in title or "100 Days — Business Documentaries" in ch_name:
            fresh = business_documentary_profile()
            ch = prof.get("channel") if isinstance(prof.get("channel"), dict) else {}
            fresh_ch = fresh.get("channel") if isinstance(fresh.get("channel"), dict) else {}
            stale_words = int(ch.get("target_words") or 0) != int(fresh_ch.get("target_words") or 2000)
            stale_dur = list(ch.get("target_duration_min") or []) != list(fresh_ch.get("target_duration_min") or [11, 15])
            stale_tag = ch.get("tagline") != fresh_ch.get("tagline")
            if stale_words or stale_dur or stale_tag or not is_documentary_profile(prof):
                # Keep session id/messages; refresh editorial defaults (2000 words / 11–15 min)
                s["creative_profile"] = fresh
                persist_session(store, str(s["id"]), list(s.get("messages") or []), fresh)
                prof = fresh
            set_active_session(store, str(s["id"]))
            return s, merge_profile_disk(s.get("creative_profile"))

    profile = business_documentary_profile()
    opening = "100 Days — Business Documentaries channel ready."
    store, sid = add_session(store, "100 Days — Business Documentaries", profile)
    messages = [
        {"role": "assistant", "content": opening},
    ]
    persist_session(store, sid, messages, profile)
    persist_session_summary(
        store,
        sid,
        "Channel: 100 Days Business Documentaries. EN, ~11–15 min / ~2000 words, story-first.",
    )
    set_active_session(store, sid)
    sess = get_session(load_store(), sid) or {"id": sid, "title": "100 Days — Business Documentaries"}
    return sess, profile


app = create_app()
