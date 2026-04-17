from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from web.database import get_db
from web.models import Subscription, SubscriptionPlan, TokenWallet, User


def get_current_user_optional(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    uid = request.session.get("uid")
    if not uid:
        return None
    try:
        iuid = int(uid)
    except (TypeError, ValueError):
        return None
    stmt = (
        select(User)
        .where(User.id == iuid)
        .options(
            joinedload(User.subscription).joinedload(Subscription.plan),
            joinedload(User.wallet),
        )
    )
    return db.scalars(stmt).unique().first()


def require_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    u = get_current_user_optional(request, db)
    if not u:
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
    return u


def require_admin(user: Annotated[User, Depends(require_user)]) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Se requiere rol administrador.")
    return user


def wallet_balance(user: User, db: Session) -> int:
    w = db.scalars(select(TokenWallet).where(TokenWallet.user_id == user.id)).first()
    if not w:
        return 0
    return int(w.balance or 0)
