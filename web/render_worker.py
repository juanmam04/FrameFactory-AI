"""Ejecución de renders en hilo de fondo (motor existente `run_saas_mvp`)."""
from __future__ import annotations

import json
import os
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.config_loader import BASE
from src.pipeline import run_saas_mvp
from src.saas_creative_profile import merge_profile_disk
from src.saas_platform.billing import deduct_tokens_after_success, read_wallet_balance, user_may_generate
from web.database import SessionLocal
from web.models import CreativeProfile, RenderJob, VideoProject


def _read_progress(progress_path: Path) -> tuple[str, float]:
    if not progress_path.exists():
        return "", 0.0
    try:
        raw = json.loads(progress_path.read_text(encoding="utf-8"))
        return str(raw.get("step") or ""), float(raw.get("pct") or 0.0)
    except Exception:
        return "", 0.0


def _run_job_inner(job_id: int) -> None:
    load_dotenv(BASE / ".env")
    db: Session = SessionLocal()
    progress_path: Path | None = None
    try:
        job = db.get(RenderJob, job_id)
        if not job:
            return
        project = db.get(VideoProject, job.project_id)
        if not project:
            return
        from web.models import User

        user = db.scalars(
            select(User)
            .where(User.id == job.user_id)
            .options(joinedload(User.subscription))
        ).unique().first()
        if not user:
            return

        bal = read_wallet_balance(db, user.id)
        allowed, deny_msg = user_may_generate(user, bal)
        if not allowed:
            job.state = "failed"
            job.error = deny_msg[:2000]
            job.finished_at = datetime.now(timezone.utc)
            project.status = "failed"
            project.error_message = deny_msg
            db.commit()
            return

        ws = f"job_{job_id}"
        progress_path = (BASE / "output" / ws / "_progress.json").resolve()
        progress_path.parent.mkdir(parents=True, exist_ok=True)

        job.state = "running"
        job.started_at = datetime.now(timezone.utc)
        job.progress_step = "Inicio"
        job.progress_pct = 0.0
        project.status = "rendering"
        db.commit()

        cp_row = db.scalars(select(CreativeProfile).where(CreativeProfile.user_id == user.id)).first()
        profile_payload = (cp_row.payload if cp_row and isinstance(cp_row.payload, dict) else {}) or {}
        creative_profile = merge_profile_disk(profile_payload)

        gpv = os.getenv("GAMEPLAY_BACKGROUND_VIDEO", "").strip()
        gp_arg: Path | None = None
        if gpv:
            gp_try = Path(gpv).expanduser().resolve()
            if gp_try.is_file():
                gp_arg = gp_try

        final = run_saas_mvp(
            project.topic,
            progress_path=progress_path,
            creative_profile=creative_profile,
            session_context=None,
            target_words=int(project.target_words or 420),
            voice_speed=float(project.voice_speed or 1.0),
            subtitles_enabled=bool(project.subtitles_enabled),
            subtitle_style_key=str(project.subtitle_style or "default"),
            character_id=str(project.character_id or None),
            background_id=str(project.background_id or None),
            voice_id=str(project.voice_id or None),
            workspace_subdir=ws,
            gameplay_video_path=gp_arg,
            video_aspect=(os.getenv("GAMEPLAY_VIDEO_ASPECT", "16:9").strip() or "16:9"),
        )

        rel = final.resolve().relative_to(BASE.resolve())
        project.video_relpath = rel.as_posix()
        project.status = "ready"
        project.error_message = None
        job.state = "done"
        job.finished_at = datetime.now(timezone.utc)
        step, pct = _read_progress(progress_path)
        job.progress_step = step or "Listo"
        job.progress_pct = pct or 100.0
        db.commit()

        ok, _ = deduct_tokens_after_success(
            db,
            user,
            reason="video_generation",
            project_id=project.id,
            job_id=job.id,
        )
        if not ok:
            job.error = (job.error or "") + " | token_deduction_failed"
        db.commit()
    except Exception as e:
        try:
            job = db.get(RenderJob, job_id)
            project = db.get(VideoProject, job.project_id) if job else None
            if job:
                job.state = "failed"
                job.error = str(e)[:2000]
                job.finished_at = datetime.now(timezone.utc)
                step, pct = _read_progress(progress_path) if progress_path else ("", 0.0)
                job.progress_step = step
                job.progress_pct = pct
            if project:
                project.status = "failed"
                project.error_message = traceback.format_exc()[-4000:]
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def enqueue_render_job(job_id: int) -> None:
    t = threading.Thread(target=_run_job_inner, args=(job_id,), daemon=True)
    t.start()


def sync_job_progress_from_disk(db: Session, job_id: int) -> None:
    """Actualiza progreso en DB leyendo el JSON del pipeline (para polling UI)."""
    job = db.get(RenderJob, job_id)
    if not job or job.state not in ("queued", "running"):
        return
    ws = f"job_{job_id}"
    p = (BASE / "output" / ws / "_progress.json").resolve()
    step, pct = _read_progress(p)
    if step or pct:
        job.progress_step = step
        job.progress_pct = pct
        db.commit()
