"""
Reglas de negocio: planes, tokens y generación.

Los administradores (role == 'admin') están exentos en **toda** la lógica aquí:
no se comprueba saldo, no se descuentan tokens y no se aplica bloqueo por facturación.
Esto debe usarse desde el backend antes/después de cada render; la UI solo refleja el estado.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from web.models import User


def read_wallet_balance(db: "Session", user_id: int) -> int:
    from sqlalchemy import select

    from web.models import TokenWallet

    w = db.scalars(select(TokenWallet).where(TokenWallet.user_id == user_id)).first()
    if not w:
        return 0
    return int(w.balance or 0)


def token_cost_per_video() -> int:
    raw = (os.getenv("SAAS_TOKEN_COST_PER_VIDEO") or "500").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 500


def user_is_admin(user: Any) -> bool:
    return getattr(user, "role", None) == "admin"


def user_may_generate(user: Any, wallet_balance: int | None) -> tuple[bool, str]:
    """
    Devuelve (permitido, mensaje_error_para_ui).
    Admin: siempre (True, "").
    """
    if user_is_admin(user):
        return True, ""
    if not getattr(user, "is_active", True):
        return False, "Tu cuenta está desactivada."
    sub = getattr(user, "subscription", None)
    if sub is None:
        return False, "No hay suscripción activa asignada a tu cuenta."
    if getattr(sub, "status", "") == "past_due":
        return False, "Hay un problema con tu suscripción. Revisá facturación."
    bal = int(wallet_balance or 0)
    cost = token_cost_per_video()
    if bal < cost:
        return False, f"Saldo insuficiente. Necesitás al menos {cost} tokens (tenés {bal})."
    return True, ""


def deduct_tokens_after_success(
    db: "Session",
    user: "User",
    *,
    amount: int | None = None,
    reason: str = "video_generation",
    project_id: int | None = None,
    job_id: int | None = None,
) -> tuple[bool, str]:
    """
    Descuenta tokens tras un render exitoso. Admin: no-op exitoso.
    """
    if user_is_admin(user):
        return True, "admin_exempt"

    cost = int(amount) if amount is not None else token_cost_per_video()
    from sqlalchemy import select

    from web.models import TokenTransaction, TokenWallet

    wallet = db.scalars(select(TokenWallet).where(TokenWallet.user_id == user.id)).first()
    if not wallet:
        return False, "wallet_missing"

    if int(wallet.balance) < cost:
        return False, "insufficient_balance"

    wallet.balance = int(wallet.balance) - cost
    wallet.updated_at = datetime.now(timezone.utc)
    tx = TokenTransaction(
        user_id=user.id,
        amount=-cost,
        balance_after=int(wallet.balance),
        reason=reason,
        ref_type="render_job" if job_id else "video_project",
        ref_id=str(job_id or project_id or ""),
        created_at=datetime.now(timezone.utc),
    )
    db.add(tx)
    db.flush()
    return True, "ok"


def grant_tokens(
    db: "Session",
    user: "User",
    amount: int,
    *,
    reason: str,
    ref_type: str = "admin_adjustment",
    ref_id: str = "",
) -> int:
    """Suma tokens (ajuste admin, bienvenida, etc.). Admin también puede recibir bonos; no rompe reglas."""
    from sqlalchemy import select

    from web.models import TokenTransaction, TokenWallet

    wallet = db.scalars(select(TokenWallet).where(TokenWallet.user_id == user.id)).first()
    if not wallet:
        wallet = TokenWallet(user_id=user.id, balance=0, updated_at=datetime.now(timezone.utc))
        db.add(wallet)
        db.flush()

    wallet.balance = int(wallet.balance) + int(amount)
    wallet.updated_at = datetime.now(timezone.utc)
    tx = TokenTransaction(
        user_id=user.id,
        amount=int(amount),
        balance_after=int(wallet.balance),
        reason=reason,
        ref_type=ref_type,
        ref_id=ref_id or "",
        created_at=datetime.now(timezone.utc),
    )
    db.add(tx)
    db.flush()
    return int(wallet.balance)


@dataclass
class PlanSnapshot:
    slug: str
    name: str
    monthly_price_cents: int
    monthly_token_allowance: int


def plan_for_user_display(user: Any) -> PlanSnapshot | None:
    """Lectura ligera para plantillas; el plan real viene de la relación subscription."""
    sub = getattr(user, "subscription", None)
    if not sub or not getattr(sub, "plan", None):
        return None
    p = sub.plan
    return PlanSnapshot(
        slug=str(p.slug),
        name=str(p.name),
        monthly_price_cents=int(p.monthly_price_cents or 0),
        monthly_token_allowance=int(p.monthly_token_allowance or 0),
    )
