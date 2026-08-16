"""FrameFactory Documentary Studio — FastAPI (not Streamlit)."""
from __future__ import annotations

import json
import os
import re
import traceback
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
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
from src.documentary.youtube_pack import generate_youtube_pack, save_youtube_pack
from src.documentary.flow_pack import export_flow_pack, load_shot_list
from src.documentary.import_images import (
    delete_all_project_images,
    delete_master_image,
    delete_project_image,
    ensure_master_thumb,
    ensure_still_thumb,
    import_images,
    import_uploaded_images,
    master_file,
    masters_dir,
    normalize_master_id,
    save_master_upload,
    still_file,
    _refresh_after_image_delete,
)
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
    list_projects,
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

STEPS = [
    "topic",
    "research",
    "story",
    "script",
    "flow",
    "images",
    "voice",
    "music",
    "preview",
    "render",
    "subs",
    "publish",
    "done",
]

_PROJECT_RE = re.compile(r"^/api/projects/([^/]+)")


def _reject_heavy_on_vercel() -> None:
    if on_vercel():
        raise HTTPException(
            400,
            "El video final necesita FFmpeg en tu Mac. La voz sí se genera acá. Para el render: npm run dev.",
        )


def _sync_safe(fn) -> None:
    try:
        fn()
    except Exception:
        traceback.print_exc()


_SKIP_SYNC = {
    "/health",
    "/",
    "/sw.js",
    "/api/ping",
    "/api/bootstrap",  # must stay instant — never block Home on Supabase pull
    "/api/ideas",
    "/api/credentials/recheck",
    "/api/sync/status",
    "/api/sync/push",
    "/api/sync/pull",
}


class WorkspaceSyncMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/assets") or path in _SKIP_SYNC:
            return await call_next(request)
        from src.documentary import cloud_sync

        if not cloud_sync.configured():
            return await call_next(request)

        m = _PROJECT_RE.match(path)
        pid = m.group(1) if m else None

        response = await call_next(request)

        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and pid
            and path.startswith("/api/")
        ):
            if (
                path.endswith("/step")
                or "/images/upload" in path
                or "/masters/upload" in path
                or path.endswith("/voice")
                or path.endswith("/render")
                or path.endswith("/render/preview")
                or path.endswith("/render/edit")
                or path.endswith("/render/cancel")
                or path.endswith("/captions")
                or path.endswith("/captions.vtt")
                or "/captions/" in path
                or path.endswith("/youtube")
            ):
                if path.endswith("/step"):
                    _sync_safe(lambda: cloud_sync.push_paths(pid, ["project.json"]))
            elif request.method == "DELETE" and ("/images" in path or "/masters/" in path):
                pass
            else:
                _sync_safe(lambda: cloud_sync.push_project(pid, include_images=False))
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="FrameFactory Studio", docs_url="/api/docs")
    app.add_middleware(WorkspaceSyncMiddleware)
    static_dir = ROOT / "static"
    if static_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(static_dir), check_dir=False), name="assets")

    @app.get("/", response_class=HTMLResponse)
    def index():
        html_path = ROOT / "templates" / "index.html"
        if not html_path.is_file():
            return HTMLResponse(
                f"<pre>Missing {html_path}. Vercel bundle did not include studio/templates.</pre>",
                status_code=500,
            )
        return HTMLResponse(
            html_path.read_text(encoding="utf-8"),
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    @app.get("/sw.js")
    def service_worker():
        path = ROOT / "static" / "sw.js"
        if not path.is_file():
            raise HTTPException(404, "sw.js missing")
        return FileResponse(
            path,
            media_type="application/javascript; charset=utf-8",
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Service-Worker-Allowed": "/",
            },
        )

    @app.get("/assets/studio.css")
    def studio_css():
        """Serve CSS with no-cache so top-bar layout fixes land in production."""
        css_path = ROOT / "static" / "studio.css"
        if not css_path.is_file():
            raise HTTPException(404, "studio.css missing from deploy bundle")
        return FileResponse(
            css_path,
            media_type="text/css; charset=utf-8",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    @app.get("/health")
    def health():
        import os

        return {
            "ok": True,
            "app": "documentary-studio",
            "vercel": on_vercel(),
            "commit": (os.getenv("VERCEL_GIT_COMMIT_SHA") or os.getenv("GIT_COMMIT") or "")[:12],
            "build": "20260816-hq",
        }

    @app.get("/api/ping")
    def ping():
        import os

        return {
            "ok": True,
            "vercel": on_vercel(),
            "commit": (os.getenv("VERCEL_GIT_COMMIT_SHA") or "")[:12],
            "build": "20260816-hq",
        }

    # ── channel / home ──────────────────────────────────────────────
    @app.get("/api/bootstrap")
    def bootstrap():
        try:
            reload_env()
            # Optional fast index sync (project.json only). Never block Home for minutes.
            sync_note = ""
            try:
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    idx = cloud_sync.pull_home_index(timeout_sec=5.0)
                    if not idx.get("ok") and idx.get("error"):
                        sync_note = str(idx.get("error") or "")
            except Exception as sync_exc:
                sync_note = str(sync_exc)[:160]
            sess, profile = _ensure_channel()
            goal = goal_count_from_profile(profile, 100)
            sid = str(sess.get("id") or "")
            listed = list_projects_for_session(sid)
            if not listed:
                listed = list_projects()
                stats = session_stats(None, goal)
            else:
                stats = session_stats(sid, goal)
            projects = [
                _project_card(p)
                for p in sorted(
                    listed,
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
                    "sync_note": sync_note,
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
        except Exception as e:
            traceback.print_exc()
            return {
                "runtime": {"vercel": on_vercel(), "voice_render": False},
                "channel": {"name": "FrameFactory", "session_id": "", "tagline": str(e)},
                "workspace": {
                    "projects_dir": "",
                    "data_dir": "",
                    "synced": False,
                    "supabase": bool((os.getenv("DATABASE_URL") or "").strip()),
                },
                "stats": {"day": 0, "goal": 100, "completed": 0, "in_progress": 0, "remaining": 100},
                "projects": [],
                "credentials": {
                    "openai": {"status": "error", "detail": str(e)},
                    "elevenlabs": {"status": "unchecked", "detail": ""},
                    "ready_research": False,
                    "ready_voice": False,
                },
                "boot_error": traceback.format_exc(),
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
            if not list_projects():
                raise HTTPException(
                    400,
                    "No hay episodios en este servidor para subir. Tocá «Bajar de la nube» primero.",
                )
            return cloud_sync.push_all()
        except HTTPException:
            raise
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
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(lambda: cloud_sync.push_project(str(data.get("id") or "")))
                    _sync_safe(cloud_sync.push_sessions)
            return {"project": _project_full(data)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        try:
            return {"project": _project_full(load_project(project_id))}
        except FileNotFoundError as e:
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(lambda: cloud_sync.pull_project(project_id, light=True))
                    try:
                        return {"project": _project_full(load_project(project_id))}
                    except FileNotFoundError:
                        pass
            raise HTTPException(404, str(e)) from e

    @app.patch("/api/projects/{project_id}/step")
    def set_step(project_id: str, body: StepBody):
        try:
            p = load_project(project_id)
        except FileNotFoundError as e:
            raise HTTPException(404, str(e)) from e
        if body.step not in STEPS:
            raise HTTPException(400, "Invalid step")
        step = body.step
        if step == "images":
            step = "flow"
        if step == "subs":
            step = "render"
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

    @app.get("/api/projects/{project_id}/images/{number}")
    def image_file(project_id: str, number: int):
        root = project_dir(project_id) / "images"
        n = int(number)
        thumb = root / f"{n:03d}.thumb.jpg"
        path = still_file(root, n)
        if path is None and not (thumb.is_file() and thumb.stat().st_size > 0):
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                for name in (
                    f"{n:03d}.jpg",
                    f"{n:03d}.png",
                    f"{n:03d}.webp",
                    f"{n:03d}.jpeg",
                    f"{n:03d}.thumb.jpg",
                ):
                    if cloud_sync.pull_one(project_id, f"images/{name}"):
                        break
                path = still_file(root, n)
        serve = ensure_still_thumb(root, n)
        if serve is None and thumb.is_file() and thumb.stat().st_size > 0:
            serve = thumb
        if serve is not None:
            return FileResponse(
                serve,
                media_type="image/jpeg" if serve.suffix.lower() in {".jpg", ".jpeg"} else None,
                headers={"Cache-Control": "private, max-age=60, must-revalidate"},
            )
        raise HTTPException(404, f"No image {n:03d}")

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
            from src.documentary import cloud_sync

            rels = list(report.get("stored") or [])
            if not rels and force_number is not None:
                found = still_file(project_dir(project_id) / "images", force_number)
                if found is not None:
                    rels = [f"images/{found.name}"]
            if cloud_sync.configured() and rels:
                nums: list[int] = []
                for rel in rels:
                    m = re.search(r"(\d{3})", Path(rel).name)
                    if m:
                        nums.append(int(m.group(1)))
                stale: list[str] = []
                for n in sorted(set(nums)):
                    stale.extend(
                        [
                            f"images/{n:03d}.png",
                            f"images/{n:03d}.webp",
                            f"images/{n:03d}.jpeg",
                        ]
                    )
                if stale:
                    cloud_sync.delete_paths(project_id, stale)
                pushed = cloud_sync.push_paths(project_id, rels)
                if on_vercel() and not pushed.get("uploaded") and not pushed.get("unchanged"):
                    pushed = cloud_sync.push_paths(project_id, rels)
                if on_vercel() and not pushed.get("uploaded") and not pushed.get("unchanged"):
                    raise ValueError("No se pudieron guardar las imágenes en la nube. Probá de nuevo.")
            return {
                "ok": True,
                "report": report,
            }
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.get("/api/projects/{project_id}/masters/{ref_id}")
    def master_image(project_id: str, ref_id: str):
        try:
            eid = normalize_master_id(ref_id)
        except ValueError as e:
            raise HTTPException(400, _err(e)) from e
        found = master_file(project_id, eid)
        thumb = masters_dir(project_id) / f"{eid}.thumb.jpg"
        if found is None and not (thumb.is_file() and thumb.stat().st_size > 0):
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                for name in (f"{eid}.jpg", f"{eid}.png", f"{eid}.webp", f"{eid}.jpeg", f"{eid}.thumb.jpg"):
                    if cloud_sync.pull_one(project_id, f"flow-pack/references/masters/{name}"):
                        break
        serve = ensure_master_thumb(project_id, eid)
        if serve is None and thumb.is_file() and thumb.stat().st_size > 0:
            serve = thumb
        if serve is None:
            raise HTTPException(404, f"No master {eid}")
        return FileResponse(
            serve,
            media_type="image/jpeg" if serve.suffix.lower() in {".jpg", ".jpeg"} else None,
            headers={"Cache-Control": "private, max-age=60, must-revalidate"},
        )

    @app.post("/api/projects/{project_id}/masters/upload")
    async def master_upload(
        project_id: str,
        files: list[UploadFile] = File(...),
        force_id: str | None = Form(default=None),
    ):
        try:
            load_project(project_id)
            if not force_id:
                raise ValueError("Falta la cara (CHAR_001).")
            eid = normalize_master_id(force_id)
            raw = b""
            fname = "upload.jpg"
            for f in files:
                raw = await f.read()
                fname = f.filename or fname
                if raw:
                    break
            if not raw:
                raise ValueError("No files received.")
            report = save_master_upload(project_id, eid, raw, fname)
            from src.documentary import cloud_sync

            rels = list(report.get("stored") or [])
            if cloud_sync.configured() and rels:
                cloud_sync.delete_paths(
                    project_id,
                    [
                        f"flow-pack/references/masters/{eid}.png",
                        f"flow-pack/references/masters/{eid}.webp",
                        f"flow-pack/references/masters/{eid}.jpeg",
                    ],
                )
                pushed = cloud_sync.push_paths(project_id, rels)
                if on_vercel() and not pushed.get("uploaded") and not pushed.get("unchanged"):
                    raise ValueError("No se pudo guardar la cara en la nube. Probá de nuevo.")
            return {"ok": True, "report": report}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.delete("/api/projects/{project_id}/masters/{ref_id}")
    def master_delete(project_id: str, ref_id: str):
        try:
            load_project(project_id)
            eid = normalize_master_id(ref_id)
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                cloud_sync.delete_paths(
                    project_id,
                    [
                        f"flow-pack/references/masters/{eid}{ext}"
                        for ext in (".jpg", ".jpeg", ".png", ".webp")
                    ]
                    + [f"flow-pack/references/masters/{eid}.thumb.jpg"],
                )
            result = delete_master_image(project_id, eid)
            return {"ok": True, "deleted": result}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.delete("/api/projects/{project_id}/images/{number}")
    def images_delete_one(project_id: str, number: int):
        try:
            p = load_project(project_id)
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                n = int(number)
                cloud_sync.delete_paths(
                    project_id,
                    [f"images/{n:03d}{ext}" for ext in (".jpg", ".jpeg", ".png", ".webp")]
                    + [f"images/{n:03d}.thumb.jpg"],
                )
            result = delete_project_image(project_id, number)
            sync = _refresh_after_image_delete(p)
            if on_vercel() and cloud_sync.configured():
                _sync_safe(lambda: cloud_sync.push_paths(project_id, ["project.json"]))
            return {"ok": True, "deleted": result, "sync": sync}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.delete("/api/projects/{project_id}/images")
    def images_delete_all(project_id: str):
        try:
            p = load_project(project_id)
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                cloud_sync.delete_image_blobs(project_id)
            result = delete_all_project_images(project_id)
            sync = _refresh_after_image_delete(p)
            if on_vercel() and cloud_sync.configured():
                _sync_safe(lambda: cloud_sync.push_paths(project_id, ["project.json"]))
            return {"ok": True, "deleted": result, "sync": sync}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.get("/api/music")
    def music_bed():
        from src.documentary.music_bed import documentary_bed_path

        path = documentary_bed_path()
        if not path.is_file() or path.stat().st_size <= 0:
            raise HTTPException(404, "No hay música de fondo")
        return FileResponse(
            path,
            media_type="audio/wav",
            filename="documentary_bed.wav",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/api/projects/{project_id}/audio")
    def audio_file(project_id: str):
        path = project_dir(project_id) / "audio" / "narration.mp3"
        if not path.is_file() or path.stat().st_size <= 0:
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                cloud_sync.pull_one(project_id, "audio/narration.mp3")
        if path.is_file() and path.stat().st_size > 0:
            return FileResponse(path, media_type="audio/mpeg")
        raise HTTPException(404, "No hay narración todavía")

    @app.post("/api/projects/{project_id}/voice")
    def voice_generate(project_id: str):
        try:
            from src.documentary.voice_service import generate_project_voice

            generate_project_voice(load_project(project_id))
            p = load_project(project_id)
            p["ui_step"] = "voice"
            save_project(p)
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(
                        lambda: cloud_sync.push_paths(
                            project_id,
                            [
                                "project.json",
                                "audio/narration.mp3",
                                "audio/narration_script.txt",
                            ],
                        )
                    )
            return {"project": _project_full(p)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.get("/api/projects/{project_id}/video/status")
    def video_status(project_id: str):
        from src.documentary.captions import captioned_video_path
        from src.documentary.pipeline_invalidate import preview_matches_voice
        from src.documentary.voice_script_sync import ensure_voice_binding, voice_matches_script
        from src.video_assembler import mp4_is_complete

        local = project_dir(project_id) / "render" / "final.mp4"
        cap = captioned_video_path(project_id)
        prev = project_dir(project_id) / "render" / "preview.mp4"
        ready = mp4_is_complete(local)
        captions = mp4_is_complete(cap)
        preview = mp4_is_complete(prev)
        # Prefer local project.json. Soft-pull only when missing (Vercel cold start).
        try:
            proj = load_project(project_id)
        except Exception:
            proj = None
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                try:
                    cloud_sync.pull_one(project_id, "project.json", force=False)
                    proj = load_project(project_id)
                except Exception:
                    proj = None
        if proj is not None:
            try:
                proj = ensure_voice_binding(proj)
            except Exception:
                pass
        rec = proj.get("render") if isinstance((proj or {}).get("render"), dict) else {}

        # On Vercel each request is a new FS: pull the preview mp4 if cloud has it.
        if not preview:
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                want = str(rec.get("preview") or "") == "render/preview.mp4" or str(rec.get("stage") or "").startswith(
                    "preview"
                )
                if not want:
                    # Cold instance may lack local project.json meta — check the bucket.
                    try:
                        want = "render/preview.mp4" in set(cloud_sync.list_rel_paths(project_id, "render/"))
                    except Exception:
                        want = False
                if want:
                    try:
                        if not proj:
                            cloud_sync.pull_one(project_id, "project.json", force=False)
                            try:
                                proj = ensure_voice_binding(load_project(project_id))
                                rec = proj.get("render") if isinstance(proj.get("render"), dict) else {}
                            except Exception:
                                pass
                        cloud_sync.pull_one(project_id, "render/preview.mp4", force=False)
                    except Exception:
                        pass
                    preview = mp4_is_complete(prev)

        voice_ok = bool(proj and voice_matches_script(proj))
        preview_ok = bool(preview and proj and preview_matches_voice(proj))
        # Stale preview vs current voice: hide it in the UI, but do NOT delete here.
        # Deletion belongs to wipe_voice_derived() when the narration actually changes.
        if preview and not preview_ok:
            # If meta is missing but file exists and voice is ok, still show (legacy takes).
            if voice_ok and preview and not ((rec.get("preview_meta") or {}).get("audio_sha")):
                preview_ok = True
            else:
                preview = False

        if not ready or not captions:
            from src.documentary import cloud_sync

            if cloud_sync.configured() and voice_ok:
                try:
                    rels = set(cloud_sync.list_rel_paths(project_id, "render/"))
                except Exception:
                    rels = set()
                ready = ready or "render/final.mp4" in rels
                captions = captions or "render/final_captions.mp4" in rels
                if not preview and "render/preview.mp4" in rels:
                    try:
                        cloud_sync.pull_one(project_id, "render/preview.mp4", force=False)
                    except Exception:
                        pass
                    preview = mp4_is_complete(prev)
                    preview_ok = bool(preview and proj and preview_matches_voice(proj))
                    if preview and not preview_ok and voice_ok and not ((rec.get("preview_meta") or {}).get("audio_sha")):
                        preview_ok = True
                    elif preview and not preview_ok:
                        preview = False
        if proj is not None:
            captions = captions or bool((proj.get("captions") or {}).get("burned")) or bool(
                (proj.get("checkpoints") or {}).get("captions_ready")
            )
            if ready and not voice_ok:
                ready = False
        state = str(rec.get("state") or "").strip() or ("done" if ready else "idle")
        message = str(rec.get("message") or "")
        started = str(rec.get("started_at") or "")
        need_continue = bool(rec.get("need_continue"))
        stage_now = str(rec.get("stage") or "")
        # Preview leftovers used to leave state=running forever → step 9 stuck on "Armando…".
        if state == "running" and (
            stage_now == "preview_done" or stage_now.startswith("preview_")
        ):
            state = "idle"
            need_continue = False
            if stage_now == "preview_done":
                message = message or "Prueba lista. Tocá Renderizar episodio para el video completo."
            if proj is not None and str(rec.get("state") or "") == "running":
                try:
                    from src.documentary.project import _utc_now, save_project

                    rec["state"] = "idle"
                    rec["need_continue"] = False
                    rec["kb_done"] = 0
                    rec["kb_total"] = 0
                    rec["percent"] = 0
                    rec["updated_at"] = _utc_now()
                    rec["message"] = (
                        message
                        or "Prueba lista. Tocá Renderizar episodio para el video completo."
                    )
                    proj["render"] = rec
                    save_project(proj)
                    from src.documentary import cloud_sync

                    if cloud_sync.configured():
                        try:
                            cloud_sync.push_paths(project_id, ["project.json"])
                        except Exception:
                            pass
                except Exception:
                    pass
        # Old stuck "Se cortó" errors → resume instead of blocking the UI.
        if state == "error" and "Se cortó" in (message or str(rec.get("error") or "")):
            if not ready:
                state = "running"
                message = "Reanudando render (el servidor corta a los ~5 min)…"
                need_continue = True
        if state == "running":
            try:
                from datetime import datetime, timezone

                stamp = str(rec.get("updated_at") or started or "")
                t0 = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - t0).total_seconds()
                # Vercel lambdas die ~300s. Don't flip to ERROR — tell the UI to resume.
                # Never auto-resume a preview stage.
                if age > 200 and not stage_now.startswith("preview"):
                    state = "running"
                    done = int(rec.get("kb_done") or 0)
                    total = int(rec.get("kb_total") or 0)
                    if done and total:
                        message = f"Reanudando desde foto {done}/{total} (el servidor corta a los ~5 min)…"
                    else:
                        message = "Reanudando render (el servidor corta a los ~5 min)…"
                    need_continue = True
            except Exception:
                pass
        if rec.get("cancelled") and state != "running":
            state = "idle"
            message = message or "Frenaste el render."
        elif ready and state != "running":
            state = "done"
            message = message or "Terminado. Ya lo podés descargar."
        labels = {
            "idle": "Frenado" if rec.get("cancelled") else "No iniciado",
            "running": "En curso",
            "done": "Terminado",
            "error": "Error",
        }
        kb_done = int(rec.get("kb_done") or 0)
        kb_total = int(rec.get("kb_total") or 0)
        percent = rec.get("percent")
        try:
            percent = int(percent) if percent is not None else None
        except Exception:
            percent = None
        if percent is None and kb_total > 0:
            percent = max(0, min(100, int(round(100 * kb_done / kb_total))))
        elapsed = 0
        try:
            from datetime import datetime, timezone

            stamp = str(rec.get("started_at") or "")
            if stamp and state == "running":
                t0 = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                elapsed = max(0, int((datetime.now(timezone.utc) - t0).total_seconds()))
        except Exception:
            elapsed = 0
        return {
            "ready": bool(ready),
            "bytes": local.stat().st_size if local.is_file() else 0,
            "captions": bool(captions),
            "state": state,
            "label": labels.get(state, state),
            "message": message
            or {
                "idle": "Todavía no se armó el video.",
                "running": "Armando el video… unos minutos.",
                "done": "Terminado. Ya lo podés descargar.",
                "error": "Falló el render.",
            }.get(state, ""),
            "error": str(rec.get("error") or "") if state == "error" else "",
            "started_at": started,
            "updated_at": str(rec.get("updated_at") or ""),
            "preview": bool(preview),
            "preview_matches_voice": bool(preview_ok),
            "preview_busy": bool(
                str(rec.get("stage") or "").startswith("preview_")
                and str(rec.get("stage") or "") != "preview_done"
                and not preview
            ),
            "voice_matches_script": bool(voice_ok),
            "edit": rec.get("edit") if isinstance(rec.get("edit"), dict) else {},
            "need_continue": bool(need_continue) and state == "running",
            "kb_done": kb_done,
            "kb_total": kb_total,
            "percent": percent if percent is not None else 0,
            "stage": str(rec.get("stage") or ""),
            "elapsed_sec": elapsed,
            "preview_meta": rec.get("preview_meta") if isinstance(rec.get("preview_meta"), dict) else {},
        }

    @app.api_route("/api/projects/{project_id}/video", methods=["GET", "HEAD"])
    def video_file(project_id: str, request: Request, download: int = 0):
        from src.documentary.media_serve import serve_project_mp4

        return serve_project_mp4(
            request,
            project_id=project_id,
            rel_path="render/final.mp4",
            download=bool(download),
            filename=f"{project_id}.mp4",
            fallback_rel="render/final_captions.mp4",
        )

    @app.post("/api/projects/{project_id}/render")
    def render_video(project_id: str, resume: int = 0):
        from src.documentary.assemble_service import (
            RenderCancelled,
            assemble_and_render,
            render_was_cancelled,
            set_render_state,
        )

        p = load_project(project_id)
        rec = p.get("render") if isinstance(p.get("render"), dict) else {}
        resuming = bool(resume)
        if resuming:
            try:
                from datetime import datetime, timezone

                stamp = str(rec.get("updated_at") or rec.get("started_at") or "")
                t0 = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - t0).total_seconds()
            except Exception:
                age = 9999.0
            # Another lambda/request is still encoding — don't reset and start over.
            if str(rec.get("state") or "") == "running" and age < 240 and not rec.get("need_continue"):
                return {"ok": True, "already": True, "project": _project_full(p)}
            set_render_state(
                p,
                "running",
                message="Reanudando el episodio desde donde quedó.",
                reset_progress=False,
            )
        else:
            set_render_state(p, "running", message="Armando el episodio (zoom, fundidos, música). Unos minutos.")
        if on_vercel():
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                _sync_safe(lambda: cloud_sync.push_paths(project_id, ["project.json"]))
        try:
            assembled = assemble_and_render(load_project(project_id), resume=resuming)
            p = load_project(project_id)
            if assembled is None or bool((p.get("render") or {}).get("need_continue")):
                if on_vercel():
                    from src.documentary import cloud_sync

                    if cloud_sync.configured():
                        _sync_safe(lambda: cloud_sync.push_paths(project_id, ["project.json"]))
                return {"ok": True, "continue": True, "project": _project_full(p)}
            if render_was_cancelled(project_id) or bool((p.get("render") or {}).get("cancelled")):
                return {"ok": True, "cancelled": True, "project": _project_full(p)}
            cap_ok = bool((p.get("captions") or {}).get("burned") or (p.get("checkpoints") or {}).get("captions_ready"))
            q = (p.get("render") or {}).get("height") if isinstance(p.get("render"), dict) else None
            q_label = "4K" if q and int(q) >= 2000 else "Full HD 1080p"
            set_render_state(
                p,
                "done",
                message=(
                    f"Terminado · {q_label} · subtítulos incluidos."
                    if cap_ok
                    else f"Terminado · {q_label}."
                ),
            )
            p["ui_step"] = "render"
            save_project(p)
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(
                        lambda: cloud_sync.push_paths(
                            project_id,
                            [
                                "project.json",
                                "render/final.mp4",
                                "render/final_master.mp4",
                                "render/final_captions.mp4",
                                "render/captions.srt",
                            ],
                        )
                    )
            return {"project": _project_full(p)}
        except RenderCancelled:
            p = load_project(project_id)
            return {"ok": True, "cancelled": True, "project": _project_full(p)}
        except Exception as e:
            try:
                from src.documentary.assemble_service import render_was_cancelled as _was_stop

                if _was_stop(project_id):
                    return {"ok": True, "cancelled": True, "project": _project_full(load_project(project_id))}
            except Exception:
                pass
            try:
                p = load_project(project_id)
                set_render_state(p, "error", error=_err(e))
                if on_vercel():
                    from src.documentary import cloud_sync

                    if cloud_sync.configured():
                        _sync_safe(lambda: cloud_sync.push_paths(project_id, ["project.json"]))
            except Exception:
                pass
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/render/cancel")
    def render_cancel(project_id: str):
        from src.documentary.assemble_service import cancel_render

        p = load_project(project_id)
        cancel_render(p)
        if on_vercel():
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                _sync_safe(
                    lambda: cloud_sync.push_paths(
                        project_id, ["project.json", "render/cancel.flag"]
                    )
                )
        return {"ok": True, "cancelled": True, "project": _project_full(load_project(project_id))}

    @app.put("/api/projects/{project_id}/render/edit")
    def render_edit(project_id: str, body: RenderEditBody):
        from src.documentary.assemble_service import save_edit_settings

        try:
            p = load_project(project_id)
            edit = save_edit_settings(
                p,
                {
                    "seconds_per_image": body.seconds_per_image,
                    "motion": body.motion,
                    "transition": body.transition,
                    "music_volume": body.music_volume,
                    "look": body.look,
                },
            )
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(lambda: cloud_sync.push_paths(project_id, ["project.json"]))
            return {"ok": True, "edit": edit, "project": _project_full(load_project(project_id))}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/render/preview")
    def render_preview(project_id: str):
        from src.documentary.assemble_service import assemble_preview_clip

        try:
            assemble_preview_clip(load_project(project_id))
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    # Push must finish before the client polls status, or the UI never sees the take.
                    try:
                        cloud_sync.push_paths(
                            project_id,
                            [
                                "project.json",
                                "render/preview.mp4",
                                "render/captions.srt",
                                "render/captions_preview.srt",
                            ],
                        )
                    except Exception as sync_err:
                        # Preview file is local-ready; don't fail the request solely on sync.
                        print(f"[preview] cloud push: {sync_err}")
            return {"ok": True, "preview": True, "project": _project_full(load_project(project_id))}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.api_route("/api/projects/{project_id}/video/preview", methods=["GET", "HEAD"])
    def preview_video_file(project_id: str, request: Request):
        from src.documentary.media_serve import serve_project_mp4

        return serve_project_mp4(
            request,
            project_id=project_id,
            rel_path="render/preview.mp4",
            download=False,
            filename=f"{project_id}-preview.mp4",
        )

    @app.api_route("/api/projects/{project_id}/video/captions", methods=["GET", "HEAD"])
    def captioned_video_file(project_id: str, request: Request, download: int = 0):
        from src.documentary.media_serve import serve_project_mp4

        return serve_project_mp4(
            request,
            project_id=project_id,
            rel_path="render/final_captions.mp4",
            download=bool(download),
            filename=f"{project_id}-subs.mp4",
            fallback_rel="render/final.mp4",
        )

    @app.get("/api/projects/{project_id}/captions")
    def captions_get(project_id: str):
        from src.documentary.captions import captions_srt_path, srt_to_cues

        p = load_project(project_id)
        path = captions_srt_path(project_id)
        if not path.is_file() or path.stat().st_size <= 0:
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                cloud_sync.pull_one(project_id, "render/captions.srt")
        srt = path.read_text(encoding="utf-8") if path.is_file() else ""
        burned = bool((p.get("captions") or {}).get("burned"))
        return {"srt": srt, "cues": srt_to_cues(srt), "burned": burned}

    @app.get("/api/projects/{project_id}/captions.vtt")
    def captions_vtt(project_id: str):
        from src.documentary.captions import captions_srt_path, srt_to_vtt

        path = captions_srt_path(project_id)
        if not path.is_file() or path.stat().st_size <= 0:
            from src.documentary import cloud_sync

            if cloud_sync.configured():
                cloud_sync.pull_one(project_id, "render/captions.srt")
        if not path.is_file() or path.stat().st_size <= 0:
            raise HTTPException(404, "No hay subtítulos todavía")
        return Response(
            srt_to_vtt(path.read_text(encoding="utf-8")),
            media_type="text/vtt; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/api/projects/{project_id}/captions")
    def captions_generate(project_id: str):
        try:
            from src.documentary.captions import generate_captions

            data = generate_captions(load_project(project_id), force=True)
            p = load_project(project_id)
            p["ui_step"] = "subs"
            save_project(p)
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(
                        lambda: cloud_sync.push_paths(
                            project_id, ["project.json", "render/captions.srt"]
                        )
                    )
            return {"project": _project_full(p), **data}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.put("/api/projects/{project_id}/captions")
    def captions_save(project_id: str, body: CaptionsBody):
        try:
            from src.documentary.captions import save_captions

            data = save_captions(load_project(project_id), body.srt or "")
            p = load_project(project_id)
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(
                        lambda: cloud_sync.push_paths(
                            project_id, ["project.json", "render/captions.srt"]
                        )
                    )
            return {"project": _project_full(p), **data}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/captions/burn")
    def captions_burn(project_id: str):
        try:
            from src.documentary.captions import burn_captions

            burn_captions(load_project(project_id))
            p = load_project(project_id)
            p["ui_step"] = "subs"
            save_project(p)
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(
                        lambda: cloud_sync.push_paths(
                            project_id,
                            [
                                "project.json",
                                "render/captions.srt",
                                "render/final.mp4",
                                "render/final_captions.mp4",
                            ],
                        )
                    )
            return {"project": _project_full(p)}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.post("/api/projects/{project_id}/youtube")
    def youtube_generate(project_id: str):
        try:
            p = load_project(project_id)
            pack = generate_youtube_pack(p)
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(
                        lambda: cloud_sync.push_paths(
                            project_id, ["project.json", "metadata/youtube.json"]
                        )
                    )
            return {"project": _project_full(load_project(project_id)), "youtube": pack}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    @app.put("/api/projects/{project_id}/youtube")
    def youtube_save(project_id: str, body: YoutubeBody):
        try:
            p = load_project(project_id)
            pack = save_youtube_pack(
                p,
                {
                    "title": body.title,
                    "alt_titles": body.alt_titles,
                    "description": body.description,
                    "thumbnail_text": body.thumbnail_text,
                    "thumbnail_prompt": body.thumbnail_prompt,
                },
            )
            if on_vercel():
                from src.documentary import cloud_sync

                if cloud_sync.configured():
                    _sync_safe(
                        lambda: cloud_sync.push_paths(
                            project_id, ["project.json", "metadata/youtube.json"]
                        )
                    )
            return {"project": _project_full(load_project(project_id)), "youtube": pack}
        except Exception as e:
            raise HTTPException(400, _err(e)) from e

    return app


def _flow_payload(project_id: str, p: dict[str, Any]) -> dict[str, Any]:
    try:
        from src.documentary import cloud_sync

        if cloud_sync.configured():
            cloud_sync.pull_one(project_id, "flow-pack/shot-list.json", force=False)
            cloud_sync.pull_one(project_id, "flow-pack/visual-plan.json", force=False)
    except Exception:
        pass
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


class YoutubeBody(BaseModel):
    title: str = ""
    alt_titles: list[str] = Field(default_factory=list)
    description: str = ""
    thumbnail_text: str = ""
    thumbnail_prompt: str = ""


class CaptionsBody(BaseModel):
    srt: str = ""


class RenderEditBody(BaseModel):
    seconds_per_image: float | None = None
    motion: str | None = None
    transition: str | None = None
    music_volume: float | None = None
    look: str | None = None


def _err(e: BaseException) -> str:
    msg = str(e) or e.__class__.__name__
    if len(msg) > 800:
        msg = msg[:800] + "…"
    return msg


def _youtube_of(p: dict[str, Any]) -> dict[str, Any]:
    y = p.get("youtube") if isinstance(p.get("youtube"), dict) else {}
    if str(y.get("title") or "").strip():
        return y
    pid = str(p.get("id") or "")
    if not pid:
        return y or {}
    path = project_dir(pid) / "metadata" / "youtube.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return y or {}


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
        "voice": _voice_of(p),
        "render": p.get("render") if isinstance(p.get("render"), dict) else {},
        "captions": p.get("captions") or {},
        "youtube": _youtube_of(p),
        "checkpoints": p.get("checkpoints") or {},
        "flow_pack_path": str(project_dir(str(p["id"])) / "flow-pack") if p.get("id") else "",
    }


def _voice_of(p: dict) -> dict:
    from src.documentary.voice_script_sync import ensure_voice_binding, script_hash, voice_matches_script

    try:
        ensure_voice_binding(p)
    except Exception:
        pass
    voice = dict(p.get("voice") or {}) if isinstance(p.get("voice"), dict) else {}
    voice["matches_script"] = voice_matches_script(p)
    voice["current_script_hash"] = script_hash(str(p.get("script") or ""))
    return voice


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


# Named studio_app on purpose: a top-level `app` makes Vercel detect FastAPI
# and swallow /api file functions (ping included).
studio_app = create_app()
