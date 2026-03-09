"""
Message reactions: add, remove, list reactions for DM/Group/Community messages.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional
import logging

from app.api.core import get_db, get_current_active_user
from app.models.models import User
from app.models.features import MessageReaction

logger = logging.getLogger("ForGlory")
router = APIRouter()

def utcnow():
    return datetime.now(timezone.utc)


class ReactionData(BaseModel):
    message_id: int
    message_type: str   # dm | group | comm
    emoji: str


@router.post("/reactions/add")
def add_reaction(
    d: ReactionData,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Validate emoji length
    if len(d.emoji.encode('utf-8')) > 20:
        raise HTTPException(400, "Emoji inválido")

    # Check if already reacted with same emoji
    existing = db.query(MessageReaction).filter_by(
        message_id=d.message_id,
        message_type=d.message_type,
        user_id=user.id,
        emoji=d.emoji,
    ).first()

    if existing:
        # Toggle off
        db.delete(existing)
        db.commit()
        return {"status": "removed"}

    # Add reaction
    reaction = MessageReaction(
        message_id=d.message_id,
        message_type=d.message_type,
        user_id=user.id,
        emoji=d.emoji,
        created_at=utcnow(),
    )
    db.add(reaction)
    db.commit()
    return {"status": "added"}


@router.get("/reactions/{message_type}/{message_id}")
def get_reactions(
    message_type: str,
    message_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_active_user),
):
    """Return grouped reactions with count and whether current user reacted."""
    rows = db.query(
        MessageReaction.emoji,
        func.count(MessageReaction.id).label('count'),
    ).filter_by(
        message_id=message_id,
        message_type=message_type,
    ).group_by(MessageReaction.emoji).all()

    # Which emojis the current user used
    my_reactions = set()
    if user:
        my = db.query(MessageReaction.emoji).filter_by(
            message_id=message_id,
            message_type=message_type,
            user_id=user.id,
        ).all()
        my_reactions = {r.emoji for r in my}

    return [
        {
            "emoji": row.emoji,
            "count": row.count,
            "reacted": row.emoji in my_reactions,
        }
        for row in rows
    ]


@router.delete("/reactions/remove")
def remove_reaction(
    d: ReactionData,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    reaction = db.query(MessageReaction).filter_by(
        message_id=d.message_id,
        message_type=d.message_type,
        user_id=user.id,
        emoji=d.emoji,
    ).first()
    if reaction:
        db.delete(reaction)
        db.commit()
    return {"status": "ok"}
