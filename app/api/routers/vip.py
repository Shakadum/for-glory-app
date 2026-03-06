"""
VIP / Subscriptions / Glory Points router
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from typing import Optional
import json
import logging

from app.api.core import get_db, get_current_active_user
from app.models.models import User
from app.models.features import Plan, Subscription, Payment, GloryPointsLog, GloryRank, Quiz, QuizQuestion, QuizAttempt

logger = logging.getLogger("ForGlory")
router = APIRouter()

def utcnow():
    return datetime.now(timezone.utc)


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_user_glory_rank(points: int, db: Session):
    ranks = db.query(GloryRank).order_by(GloryRank.min_points.desc()).all()
    for r in ranks:
        if points >= r.min_points:
            return r
    return ranks[-1] if ranks else None


def add_glory(user_id: int, points: int, source: str, desc: str, db: Session):
    """Add glory points to user and log it. Returns new total."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return 0
    current = getattr(user, 'glory_points', 0) or 0
    user.glory_points = current + points
    db.add(GloryPointsLog(user_id=user_id, points=points, source=source, description=desc))
    db.commit()
    return user.glory_points


def get_plan_for_user(user: User, db: Session) -> Plan:
    sub = db.query(Subscription).filter_by(user_id=user.id, status='active').first()
    if sub and sub.plan:
        return sub.plan
    free = db.query(Plan).filter_by(slug='free').first()
    return free


# ── Plans ────────────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).order_by(Plan.price_monthly).all()
    return [
        {
            "id": p.id, "slug": p.slug, "name": p.name,
            "price_monthly": p.price_monthly,
            "price_yearly": p.price_yearly,
            "features": p.features,
            "glory_multiplier": p.glory_multiplier,
        }
        for p in plans
    ]


@router.get("/my/plan")
def my_plan(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    plan = get_plan_for_user(user, db)
    sub  = db.query(Subscription).filter_by(user_id=user.id, status='active').first()
    glory = getattr(user, 'glory_points', 0) or 0
    rank  = get_user_glory_rank(glory, db)
    return {
        "plan": {
            "slug": plan.slug if plan else 'free',
            "name": plan.name if plan else 'Gratuito',
            "features": plan.features if plan else {},
            "glory_multiplier": plan.glory_multiplier if plan else 1.0,
        },
        "subscription": {
            "status": sub.status if sub else None,
            "expires": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
        } if sub else None,
        "glory": {
            "points": glory,
            "rank_slug": rank.slug if rank else 'cidadao',
            "rank_name": rank.name if rank else 'Cidadão Comum',
            "rank_color": rank.color if rank else '#6B7280',
            "rank_icon": rank.badge_icon if rank else '👤',
            "next_rank": None,
        },
    }


# ── Glory Points ──────────────────────────────────────────────────────────────

@router.get("/glory/ranks")
def glory_ranks(db: Session = Depends(get_db)):
    ranks = db.query(GloryRank).order_by(GloryRank.min_points).all()
    return [{"slug": r.slug, "name": r.name, "min_points": r.min_points,
             "color": r.color, "icon": r.badge_icon} for r in ranks]


@router.get("/glory/leaderboard")
def glory_leaderboard(db: Session = Depends(get_db)):
    users = db.query(User).filter(
        User.glory_points > 0
    ).order_by(User.glory_points.desc()).limit(50).all()
    result = []
    for i, u in enumerate(users, 1):
        gp = getattr(u, 'glory_points', 0) or 0
        rank = get_user_glory_rank(gp, db)
        result.append({
            "position": i,
            "user_id": u.id,
            "username": u.username,
            "avatar": u.avatar_url or '',
            "glory_points": gp,
            "rank_name": rank.name if rank else 'Cidadão',
            "rank_icon": rank.badge_icon if rank else '👤',
            "rank_color": rank.color if rank else '#6B7280',
        })
    return result


@router.get("/glory/history")
def glory_history(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    logs = db.query(GloryPointsLog)\
             .filter_by(user_id=user.id)\
             .order_by(GloryPointsLog.created_at.desc())\
             .limit(50).all()
    return [
        {
            "points": l.points, "source": l.source,
            "description": l.description,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


# ── Subscriptions (Manual/Webhook) ───────────────────────────────────────────

class SubscribeData(BaseModel):
    plan_slug: str
    provider: Optional[str] = "manual"
    external_id: Optional[str] = None


@router.post("/subscription/create")
def create_subscription(
    d: SubscribeData,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Creates a subscription manually (for testing/admin).
    In production: integrate MercadoPago / Stripe webhook here.
    """
    plan = db.query(Plan).filter_by(slug=d.plan_slug).first()
    if not plan:
        raise HTTPException(404, "Plano não encontrado")

    # Cancel any existing active subscription
    existing = db.query(Subscription).filter_by(user_id=user.id, status='active').first()
    if existing:
        existing.status = 'cancelled'
        db.add(existing)

    now = utcnow()
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status='active',
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        provider=d.provider,
        external_id=d.external_id,
        created_at=now,
    )
    db.add(sub)

    # Update user plan field
    user.plan = plan.slug
    db.add(user)
    db.commit()

    return {"status": "ok", "plan": plan.slug, "expires": sub.current_period_end.isoformat()}


@router.post("/subscription/cancel")
def cancel_subscription(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    sub = db.query(Subscription).filter_by(user_id=user.id, status='active').first()
    if sub:
        sub.status = 'cancelled'
        user.plan = 'free'
        db.add(sub)
        db.add(user)
        db.commit()
    return {"status": "ok"}


@router.post("/webhook/payment")
async def payment_webhook(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Generic payment webhook handler.
    In production: verify HMAC signature from MercadoPago/Stripe before processing.
    """
    event_type = payload.get("type") or payload.get("action")
    logger.info(f"Payment webhook: {event_type}")

    # MercadoPago: payment.updated or payment.created
    if event_type in ("payment.updated", "payment.created", "approved"):
        ext_id = str(payload.get("data", {}).get("id") or payload.get("id", ""))
        sub = db.query(Subscription).filter_by(external_id=ext_id).first()
        if sub:
            sub.status = "active"
            sub.current_period_end = utcnow() + timedelta(days=30)
            user = db.query(User).filter_by(id=sub.user_id).first()
            if user and sub.plan:
                user.plan = sub.plan.slug
                db.add(user)
            db.add(sub)
            db.commit()

    return {"status": "ok"}
