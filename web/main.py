"""
FrameFactory — aplicación web pública y SaaS (FastAPI).

Ejecutar desde la raíz del repo:
  uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from starlette.middleware.sessions import SessionMiddleware

from src.catalog_service import BACKGROUNDS, CHARACTERS, VOICES
from src.config_loader import BASE
from src.saas_creative_profile import merge_profile_disk
from src.saas_platform.billing import (
    grant_tokens,
    plan_for_user_display,
    read_wallet_balance,
    token_cost_per_video,
    user_may_generate,
)
from web.auth_password import hash_password, verify_password
from web.database import Base, SessionLocal, engine, get_db
from web.deps import get_current_user_optional, require_user
from web.models import (
    AdminAuditLog,
    CreativeProfile,
    RenderJob,
    Subscription,
    SubscriptionPlan,
    TokenTransaction,
    TokenWallet,
    User,
    VideoProject,
)
from web.render_worker import enqueue_render_job, sync_job_progress_from_disk
from web.seed import assign_free_plan_to_user, ensure_bootstrap_admin, seed_plans

ROOT = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(ROOT / "templates"))
STATIC = ROOT / "static"
TEMPLATES.env.globals["now_year"] = datetime.now().year


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _admin_redirect(user: User) -> RedirectResponse | None:
    if user.role != "admin":
        return RedirectResponse("/app/dashboard", status_code=302)
    return None


def _require_completed_onboarding(user: User, request: Request) -> RedirectResponse | None:
    path = request.url.path
    if path in ("/app/onboarding", "/app/settings"):
        return None
    if not user.onboarding_completed_at:
        return RedirectResponse("/app/onboarding", status_code=302)
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(BASE / ".env")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_plans(db)
        db.commit()
        ensure_bootstrap_admin(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="FrameFactory", lifespan=lifespan)
    secret = os.getenv("WEB_SESSION_SECRET") or secrets.token_hex(32)
    app.add_middleware(SessionMiddleware, secret_key=secret, same_site="lax", https_only=False)

    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

    @app.get("/")
    def landing(request: Request):
        return TEMPLATES.TemplateResponse("public/landing.html", {"request": request})

    @app.get("/features")
    def features(request: Request):
        return TEMPLATES.TemplateResponse("public/features.html", {"request": request})

    @app.get("/pricing")
    def pricing(request: Request, db: Session = Depends(get_db)):
        plans = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active == True).order_by(SubscriptionPlan.sort_order)).all()
        return TEMPLATES.TemplateResponse("public/pricing.html", {"request": request, "plans": plans})

    @app.get("/faq")
    def faq_page(request: Request):
        return TEMPLATES.TemplateResponse("public/faq.html", {"request": request})

    @app.get("/login")
    def login_get(request: Request, db: Session = Depends(get_db)):
        if get_current_user_optional(request, db):
            return RedirectResponse("/app/dashboard", status_code=302)
        return TEMPLATES.TemplateResponse("auth/login.html", {"request": request, "error": None})

    @app.post("/login")
    def login_post(
        request: Request,
        db: Session = Depends(get_db),
        email: str = Form(...),
        password: str = Form(...),
    ):
        email_n = email.strip().lower()
        user = db.scalars(select(User).where(User.email == email_n)).first()
        if not user or not verify_password(password, user.hashed_password):
            return TEMPLATES.TemplateResponse(
                "auth/login.html",
                {"request": request, "error": "Credenciales inválidas."},
                status_code=401,
            )
        request.session["uid"] = user.id
        return RedirectResponse("/app/dashboard", status_code=302)

    @app.get("/register")
    def register_get(request: Request, db: Session = Depends(get_db)):
        if get_current_user_optional(request, db):
            return RedirectResponse("/app/dashboard", status_code=302)
        return TEMPLATES.TemplateResponse("auth/register.html", {"request": request, "error": None})

    @app.post("/register")
    def register_post(
        request: Request,
        db: Session = Depends(get_db),
        name: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
    ):
        now = _utcnow()
        u = User(
            email=email.strip().lower(),
            name=name.strip()[:255],
            hashed_password=hash_password(password),
            role="user",
            is_active=True,
            onboarding_completed_at=None,
            created_at=now,
            updated_at=now,
        )
        db.add(u)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            return TEMPLATES.TemplateResponse(
                "auth/register.html",
                {"request": request, "error": "Ese email ya está registrado."},
                status_code=400,
            )
        assign_free_plan_to_user(db, u)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return TEMPLATES.TemplateResponse(
                "auth/register.html",
                {"request": request, "error": "Ese email ya está registrado."},
                status_code=400,
            )
        request.session["uid"] = u.id
        return RedirectResponse("/app/onboarding", status_code=302)

    @app.get("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/", status_code=302)

    @app.get("/auth/forgot")
    def forgot_get(request: Request):
        return TEMPLATES.TemplateResponse("auth/forgot.html", {"request": request, "error": None, "reset_link": None})

    @app.post("/auth/forgot")
    def forgot_post(request: Request, db: Session = Depends(get_db), email: str = Form(...)):
        u = db.scalars(select(User).where(User.email == email.strip().lower())).first()
        reset_link = None
        if u:
            tok = secrets.token_urlsafe(48)
            u.password_reset_token = tok
            u.password_reset_expires = _utcnow() + timedelta(hours=1)
            u.updated_at = _utcnow()
            db.commit()
            reset_link = f"/auth/reset?token={tok}"
        return TEMPLATES.TemplateResponse(
            "auth/forgot.html",
            {
                "request": request,
                "error": None if u else "Si el email existe, recibirás instrucciones.",
                "reset_link": reset_link,
            },
        )

    @app.get("/auth/reset")
    def reset_get(request: Request, token: str = ""):
        if not token:
            raise HTTPException(400, "Token faltante")
        return TEMPLATES.TemplateResponse("auth/reset_password.html", {"request": request, "token": token, "error": None})

    @app.post("/auth/reset")
    def reset_post(request: Request, db: Session = Depends(get_db), token: str = Form(...), password: str = Form(...)):
        u = db.scalars(select(User).where(User.password_reset_token == token)).first()
        if not u or not u.password_reset_expires or u.password_reset_expires < _utcnow():
            return TEMPLATES.TemplateResponse(
                "auth/reset_password.html",
                {"request": request, "token": token, "error": "Token inválido o vencido."},
                status_code=400,
            )
        u.hashed_password = hash_password(password)
        u.password_reset_token = None
        u.password_reset_expires = None
        u.updated_at = _utcnow()
        db.commit()
        return RedirectResponse("/login", status_code=302)

    def _ctx_app(request: Request, db: Session, user: User, nav: str, **kw):
        bal = read_wallet_balance(db, user.id) if user.role != "admin" else 0
        fe = request.query_params.get("error")
        fo = request.query_params.get("ok")
        return {
            "request": request,
            "user": user,
            "nav": nav,
            "token_balance": bal,
            "flash_error": fe,
            "flash_ok": fo,
            **kw,
        }

    @app.get("/app/dashboard")
    def app_dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if redir := _require_completed_onboarding(user, request):
            return redir
        if request.session.pop("tour_after_onboarding", None):
            show_tour = True
        else:
            show_tour = bool(request.query_params.get("tour"))
        pc = db.scalar(select(func.count()).select_from(VideoProject).where(VideoProject.user_id == user.id)) or 0
        rc = (
            db.scalar(
                select(func.count()).select_from(VideoProject).where(VideoProject.user_id == user.id, VideoProject.status == "ready")
            )
            or 0
        )
        return TEMPLATES.TemplateResponse(
            "app/dashboard.html",
            _ctx_app(
                request,
                db,
                user,
                "dashboard",
                projects_count=int(pc),
                ready_count=int(rc),
                token_cost=token_cost_per_video(),
                show_tour=show_tour,
            ),
        )

    @app.get("/app/onboarding")
    def onboarding_get(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        return TEMPLATES.TemplateResponse("app/onboarding.html", _ctx_app(request, db, user, "onboarding"))

    @app.post("/app/onboarding")
    def onboarding_post(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(require_user),
        niche: str = Form(...),
        tone: str = Form(...),
        format: str = Form(...),
        notes: str = Form(""),
    ):
        cp = db.scalars(select(CreativeProfile).where(CreativeProfile.user_id == user.id)).first()
        payload = dict(cp.payload) if cp and isinstance(cp.payload, dict) else {}
        payload.update(
            {
                "niche": niche.strip(),
                "tone": tone.strip(),
                "video": {"primary_format": format.strip()},
                "notes_freeform": notes.strip(),
            }
        )
        if not cp:
            cp = CreativeProfile(user_id=user.id, payload=payload, updated_at=_utcnow())
            db.add(cp)
        else:
            cp.payload = payload
            cp.updated_at = _utcnow()
        user.onboarding_completed_at = _utcnow()
        user.updated_at = _utcnow()
        db.commit()
        request.session["tour_after_onboarding"] = True
        return RedirectResponse("/app/dashboard?tour=1", status_code=302)

    @app.get("/app/create")
    def create_get(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if redir := _require_completed_onboarding(user, request):
            return redir
        bal = read_wallet_balance(db, user.id)
        ok, msg = user_may_generate(user, bal)
        return TEMPLATES.TemplateResponse(
            "app/create.html",
            _ctx_app(
                request,
                db,
                user,
                "create",
                characters=CHARACTERS,
                backgrounds=BACKGROUNDS,
                voices=VOICES,
                default_char="cartoon_biz_1",
                default_bg="dark_studio",
                default_voice="male_sharp",
                block_reason=None if ok else msg,
                token_cost=token_cost_per_video(),
            ),
        )

    @app.post("/app/create")
    def create_post(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(require_user),
        topic: str = Form(...),
        character_id: str = Form("cartoon_biz_1"),
        background_id: str = Form("dark_studio"),
        voice_id: str = Form("male_sharp"),
        target_words: int = Form(420),
    ):
        if redir := _require_completed_onboarding(user, request):
            return redir
        user = (
            db.scalars(select(User).where(User.id == user.id).options(joinedload(User.subscription).joinedload(Subscription.plan))).unique().first()
            or user
        )
        bal = read_wallet_balance(db, user.id)
        ok, msg = user_may_generate(user, bal)
        if not ok:
            return TEMPLATES.TemplateResponse(
                "app/create.html",
                _ctx_app(
                    request,
                    db,
                    user,
                    "create",
                    characters=CHARACTERS,
                    backgrounds=BACKGROUNDS,
                    voices=VOICES,
                    default_char=character_id,
                    default_bg=background_id,
                    default_voice=voice_id,
                    block_reason=msg,
                    token_cost=token_cost_per_video(),
                ),
                status_code=400,
            )
        now = _utcnow()
        tw = max(80, min(10000, int(target_words)))
        proj = VideoProject(
            user_id=user.id,
            topic=topic.strip()[:512],
            status="queued",
            character_id=character_id.strip()[:64],
            background_id=background_id.strip()[:64],
            voice_id=voice_id.strip()[:64],
            target_words=tw,
            voice_speed=1.0,
            subtitles_enabled=True,
            subtitle_style="default",
            created_at=now,
            updated_at=now,
        )
        db.add(proj)
        db.flush()
        job = RenderJob(user_id=user.id, project_id=proj.id, state="queued", progress_step="", progress_pct=0.0)
        db.add(job)
        db.commit()
        enqueue_render_job(job.id)
        return RedirectResponse("/app/library?ok=Generación+encolada", status_code=302)

    @app.get("/app/library")
    def library(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if redir := _require_completed_onboarding(user, request):
            return redir
        projects = db.scalars(select(VideoProject).where(VideoProject.user_id == user.id).order_by(VideoProject.created_at.desc())).all()
        rows = []
        for p in projects:
            for j in p.jobs:
                sync_job_progress_from_disk(db, j.id)
            db.refresh(p)
            rows.append(
                {
                    "id": p.id,
                    "topic": p.topic,
                    "status": p.status,
                    "created_at": p.created_at.astimezone().strftime("%Y-%m-%d %H:%M") if p.created_at else "",
                    "video_relpath": p.video_relpath,
                }
            )
        return TEMPLATES.TemplateResponse("app/library.html", _ctx_app(request, db, user, "library", projects=rows))

    @app.get("/app/editor/{project_id:int}")
    def editor(request: Request, project_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if redir := _require_completed_onboarding(user, request):
            return redir
        proj = db.get(VideoProject, project_id)
        if not proj or proj.user_id != user.id:
            raise HTTPException(404)
        for j in proj.jobs:
            sync_job_progress_from_disk(db, j.id)
        db.refresh(proj)
        return TEMPLATES.TemplateResponse("app/editor.html", _ctx_app(request, db, user, "library", project=proj))

    @app.get("/app/media/project/{project_id:int}/video")
    def media_video(project_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        proj = db.get(VideoProject, project_id)
        if not proj:
            raise HTTPException(404)
        if proj.user_id != user.id and user.role != "admin":
            raise HTTPException(403)
        if not proj.video_relpath:
            raise HTTPException(404)
        path = (BASE / proj.video_relpath).resolve()
        try:
            path.relative_to(BASE.resolve())
        except ValueError:
            raise HTTPException(400)
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path, media_type="video/mp4", filename=path.name)

    @app.get("/app/profile")
    def profile_get(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        cp = db.scalars(select(CreativeProfile).where(CreativeProfile.user_id == user.id)).first()
        merged = merge_profile_disk(cp.payload if cp and isinstance(cp.payload, dict) else {})
        profile_json = json.dumps(merged, ensure_ascii=False, indent=2)
        return TEMPLATES.TemplateResponse("app/profile.html", _ctx_app(request, db, user, "profile", profile_json=profile_json))

    @app.post("/app/profile")
    def profile_post(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user), payload: str = Form(...)):
        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise ValueError("JSON debe ser objeto")
        except Exception:
            profile_json = payload
            return TEMPLATES.TemplateResponse(
                "app/profile.html",
                _ctx_app(request, db, user, "profile", profile_json=profile_json),
                status_code=400,
            )
        cp = db.scalars(select(CreativeProfile).where(CreativeProfile.user_id == user.id)).first()
        if not cp:
            cp = CreativeProfile(user_id=user.id, payload=data, updated_at=_utcnow())
            db.add(cp)
        else:
            cp.payload = data
            cp.updated_at = _utcnow()
        db.commit()
        return RedirectResponse("/app/profile?ok=Perfil+guardado", status_code=302)

    @app.get("/app/billing")
    def billing(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if redir := _require_completed_onboarding(user, request):
            return redir
        user = (
            db.scalars(select(User).where(User.id == user.id).options(joinedload(User.subscription).joinedload(Subscription.plan))).unique().first()
            or user
        )
        ps = plan_for_user_display(user)
        sub = user.subscription
        renewal = None
        if sub and sub.current_period_end:
            renewal = sub.current_period_end.astimezone().strftime("%Y-%m-%d")
        return TEMPLATES.TemplateResponse(
            "app/billing.html",
            _ctx_app(
                request,
                db,
                user,
                "billing",
                plan=ps,
                sub=sub,
                renewal=renewal,
            ),
        )

    @app.get("/app/usage")
    def usage(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if redir := _require_completed_onboarding(user, request):
            return redir
        user_full = (
            db.scalars(select(User).where(User.id == user.id).options(joinedload(User.subscription).joinedload(Subscription.plan))).unique().first()
            or user
        )
        txs = db.scalars(select(TokenTransaction).where(TokenTransaction.user_id == user.id).order_by(TokenTransaction.created_at.desc()).limit(80)).all()
        rows = [
            {
                "created_at": t.created_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                "amount": t.amount,
                "balance_after": t.balance_after,
                "reason": t.reason,
                "ref_type": t.ref_type,
                "ref_id": t.ref_id,
            }
            for t in txs
        ]
        allowance = 0
        if user_full.subscription and user_full.subscription.plan:
            allowance = int(user_full.subscription.plan.monthly_token_allowance or 0)
        return TEMPLATES.TemplateResponse(
            "app/usage.html",
            _ctx_app(
                request,
                db,
                user,
                "usage",
                transactions=rows,
                monthly_allowance=allowance,
                token_cost=token_cost_per_video(),
            ),
        )

    @app.get("/app/settings")
    def settings_get(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        return TEMPLATES.TemplateResponse("app/settings.html", _ctx_app(request, db, user, "settings"))

    @app.post("/app/settings")
    def settings_post(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(require_user),
        name: str = Form(""),
        new_password: str = Form(""),
    ):
        user.name = name.strip()[:255]
        user.updated_at = _utcnow()
        if new_password.strip():
            user.hashed_password = hash_password(new_password.strip())
        db.commit()
        return RedirectResponse("/app/settings?ok=Guardado", status_code=302)

    @app.get("/admin")
    def admin_home(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if r := _admin_redirect(user):
            return r
        stats = {
            "users": db.scalar(select(func.count()).select_from(User)) or 0,
            "projects": db.scalar(select(func.count()).select_from(VideoProject)) or 0,
            "jobs_done": db.scalar(select(func.count()).select_from(RenderJob).where(RenderJob.state == "done")) or 0,
            "jobs_failed": db.scalar(select(func.count()).select_from(RenderJob).where(RenderJob.state == "failed")) or 0,
        }
        db_path = str((BASE / "data" / "framefactory.db").resolve())
        return TEMPLATES.TemplateResponse(
            "admin/dashboard.html",
            {"request": request, "nav": "dash", "flash_error": request.query_params.get("error"), "flash_ok": request.query_params.get("ok"), "stats": stats, "db_path": db_path},
        )

    @app.get("/admin/users")
    def admin_users(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if r := _admin_redirect(user):
            return r
        users = db.scalars(select(User).order_by(User.id)).all()
        rows = []
        for u in users:
            bal = read_wallet_balance(db, u.id)
            rows.append({"id": u.id, "email": u.email, "role": u.role, "is_active": u.is_active, "balance": bal})
        return TEMPLATES.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "nav": "users",
                "flash_error": request.query_params.get("error"),
                "flash_ok": request.query_params.get("ok"),
                "users": rows,
            },
        )

    @app.post("/admin/users/{uid:int}/tokens")
    def admin_user_token_adjust(
        uid: int,
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(require_user),
        delta: str = Form("0"),
        reason: str = Form("admin_adjustment"),
    ):
        if r := _admin_redirect(user):
            return r
        target = db.get(User, uid)
        if not target:
            raise HTTPException(404)
        try:
            delta_int = int(str(delta).strip() or "0")
        except ValueError:
            delta_int = 0
        grant_tokens(db, target, delta_int, reason=reason[:120], ref_type="admin", ref_id=str(user.id))
        db.add(AdminAuditLog(admin_user_id=user.id, action="token_adjust", target_user_id=uid, payload_json={"delta": delta, "reason": reason}, created_at=_utcnow()))
        db.commit()
        return RedirectResponse("/admin/users?ok=Ajuste+aplicado", status_code=302)

    @app.post("/admin/users/{uid:int}/role")
    def admin_role(uid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if r := _admin_redirect(user):
            return r
        target = db.get(User, uid)
        if not target or target.id == user.id:
            return RedirectResponse("/admin/users?error=Operación+no+permitida", status_code=302)
        target.role = "user" if target.role == "admin" else "admin"
        target.updated_at = _utcnow()
        db.add(AdminAuditLog(admin_user_id=user.id, action="role_toggle", target_user_id=uid, payload_json={"new_role": target.role}, created_at=_utcnow()))
        db.commit()
        return RedirectResponse("/admin/users?ok=Rol+actualizado", status_code=302)

    @app.get("/admin/projects")
    def admin_projects(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if r := _admin_redirect(user):
            return r
        q = (
            select(VideoProject, User.email)
            .join(User, VideoProject.user_id == User.id)
            .order_by(VideoProject.created_at.desc())
            .limit(200)
        )
        res = db.execute(q).all()
        rows = [{"id": p.id, "owner_email": email, "status": p.status, "topic": p.topic, "video_relpath": p.video_relpath} for p, email in res]
        return TEMPLATES.TemplateResponse(
            "admin/projects.html",
            {"request": request, "nav": "projects", "flash_error": None, "flash_ok": None, "projects": rows},
        )

    @app.get("/admin/plans")
    def admin_plans_get(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if r := _admin_redirect(user):
            return r
        plans = db.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order)).all()
        return TEMPLATES.TemplateResponse(
            "admin/plans.html",
            {"request": request, "nav": "plans", "flash_error": None, "flash_ok": None, "plans": plans},
        )

    @app.post("/admin/plans/{pid:int}")
    def admin_plans_post(
        pid: int,
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(require_user),
        name: str = Form(...),
        monthly_price_cents: int = Form(0),
        monthly_token_allowance: int = Form(0),
        is_active: str = Form(None),
    ):
        if r := _admin_redirect(user):
            return r
        p = db.get(SubscriptionPlan, pid)
        if not p:
            raise HTTPException(404)
        p.name = name.strip()[:128]
        p.monthly_price_cents = max(0, int(monthly_price_cents))
        p.monthly_token_allowance = max(0, int(monthly_token_allowance))
        p.is_active = is_active == "1"
        db.add(AdminAuditLog(admin_user_id=user.id, action="plan_update", target_user_id=None, payload_json={"plan_id": pid}, created_at=_utcnow()))
        db.commit()
        return RedirectResponse("/admin/plans?ok=Plan+actualizado", status_code=302)

    @app.get("/admin/catalog")
    def admin_catalog(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if r := _admin_redirect(user):
            return r
        characters = [{"id": k, "name": v["name"], "uri": v.get("base_image_uri", "")} for k, v in CHARACTERS.items()]
        backgrounds = [{"id": k, "name": v["name"], "uri": v.get("asset_uri", "")} for k, v in BACKGROUNDS.items()]
        voices = [{"id": k, "name": v["name"], "provider": v.get("provider", "")} for k, v in VOICES.items()]
        return TEMPLATES.TemplateResponse(
            "admin/catalog.html",
            {"request": request, "nav": "catalog", "flash_error": None, "flash_ok": None, "characters": characters, "backgrounds": backgrounds, "voices": voices},
        )

    @app.get("/admin/tokens")
    def admin_token_ledger(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
        if r := _admin_redirect(user):
            return r
        q = (
            select(TokenTransaction, User.email)
            .join(User, TokenTransaction.user_id == User.id)
            .order_by(TokenTransaction.created_at.desc())
            .limit(200)
        )
        res = db.execute(q).all()
        rows = [
            {
                "id": t.id,
                "user_email": email,
                "created_at": t.created_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                "amount": t.amount,
                "balance_after": t.balance_after,
                "reason": t.reason,
                "ref_type": t.ref_type,
                "ref_id": t.ref_id,
            }
            for t, email in res
        ]
        return TEMPLATES.TemplateResponse(
            "admin/tokens.html",
            {"request": request, "nav": "tokens", "flash_error": None, "flash_ok": None, "transactions": rows},
        )

    return app


app = create_app()
