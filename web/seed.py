from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from web.auth_password import hash_password
from web.models import (
    CreativeProfile,
    Subscription,
    SubscriptionPlan,
    TokenTransaction,
    TokenWallet,
    User,
)


def seed_plans(db: Session) -> None:
    if db.scalars(select(SubscriptionPlan).limit(1)).first():
        return
    rows = [
        SubscriptionPlan(
            slug="free",
            name="Free",
            monthly_price_cents=0,
            monthly_token_allowance=2500,
            max_generations_per_month=4,
            is_active=True,
            sort_order=0,
        ),
        SubscriptionPlan(
            slug="creator",
            name="Creator",
            monthly_price_cents=2900,
            monthly_token_allowance=8000,
            max_generations_per_month=None,
            is_active=True,
            sort_order=1,
        ),
        SubscriptionPlan(
            slug="studio",
            name="Studio",
            monthly_price_cents=9900,
            monthly_token_allowance=40000,
            max_generations_per_month=None,
            is_active=True,
            sort_order=2,
        ),
    ]
    for r in rows:
        db.add(r)
    db.flush()


def _default_period_end() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=30)


def ensure_bootstrap_admin(db: Session) -> None:
    """Crea el primer admin desde env si la tabla de usuarios está vacía."""
    email = (os.getenv("ADMIN_BOOTSTRAP_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD") or ""
    if not email or not password:
        return
    if db.scalars(select(User.id).limit(1)).first() is not None:
        return
    seed_plans(db)
    plan = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.slug == "studio")).first()
    if not plan:
        plan = db.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order)).first()
    if not plan:
        return
    now = datetime.now(timezone.utc)
    u = User(
        email=email,
        name="Administrator",
        hashed_password=hash_password(password),
        role="admin",
        is_active=True,
        onboarding_completed_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(u)
    db.flush()
    db.add(
        Subscription(
            user_id=u.id,
            plan_id=plan.id,
            status="active",
            current_period_end=_default_period_end(),
            created_at=now,
        )
    )
    db.add(TokenWallet(user_id=u.id, balance=0, updated_at=now))
    db.add(CreativeProfile(user_id=u.id, payload={}, updated_at=now))
    db.commit()


def assign_free_plan_to_user(db: Session, user: User) -> None:
    seed_plans(db)
    free = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.slug == "free")).first()
    if not free:
        raise RuntimeError("Plan 'free' no encontrado tras seed_plans.")
    now = datetime.now(timezone.utc)
    allowance = int(free.monthly_token_allowance or 0)
    db.add(
        Subscription(
            user_id=user.id,
            plan_id=free.id,
            status="active",
            current_period_end=_default_period_end(),
            created_at=now,
        )
    )
    db.add(TokenWallet(user_id=user.id, balance=allowance, updated_at=now))
    db.add(
        TokenTransaction(
            user_id=user.id,
            amount=allowance,
            balance_after=allowance,
            reason="signup_grant",
            ref_type="plan",
            ref_id="free",
            created_at=now,
        )
    )
    db.add(CreativeProfile(user_id=user.id, payload={}, updated_at=now))
