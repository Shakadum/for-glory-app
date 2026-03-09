"""
News articles DB router: votes, comments, article list from DB.
Works alongside the existing GNews proxy in news.py.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from typing import Optional
import logging

from app.api.core import get_db, get_current_active_user
from app.models.models import User
from app.models.features import (
    NewsArticle, NewsSource, NewsCategory, NewsVote, NewsComment
)

logger = logging.getLogger("ForGlory")
router = APIRouter()

def utcnow():
    return datetime.now(timezone.utc)


# ── Article list (from DB, ranked by relevance) ───────────────────────────────

@router.get("/news/articles")
def list_articles(
    country: Optional[str] = None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(30, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(NewsArticle)
    if country:
        query = query.filter(NewsArticle.country_code == country.upper())
    if region:
        query = query.filter(NewsArticle.region_code == region.upper())
    if category:
        cat = db.query(NewsCategory).filter_by(slug=category).first()
        if cat:
            query = query.filter(NewsArticle.category_id == cat.id)
    if q:
        query = query.filter(
            or_(
                NewsArticle.title.ilike(f'%{q}%'),
                NewsArticle.description.ilike(f'%{q}%'),
            )
        )
    articles = query.order_by(
        NewsArticle.relevance_score.desc(),
        NewsArticle.published_at.desc()
    ).offset(offset).limit(limit).all()

    return [_format_article(a, db) for a in articles]


@router.get("/news/articles/{article_id}")
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
):
    a = db.query(NewsArticle).filter_by(id=article_id).first()
    if not a:
        raise HTTPException(404, "Artigo não encontrado")
    return _format_article(a, db, include_comments=True)


# ── Votes ─────────────────────────────────────────────────────────────────────

class VoteData(BaseModel):
    article_id: int
    vote: int   # +1 or -1


@router.post("/news/vote")
def vote_article(
    d: VoteData,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if d.vote not in (1, -1):
        raise HTTPException(400, "Vote deve ser +1 ou -1")

    article = db.query(NewsArticle).filter_by(id=d.article_id).first()
    if not article:
        raise HTTPException(404, "Artigo não encontrado")

    existing = db.query(NewsVote).filter_by(article_id=d.article_id, user_id=user.id).first()
    if existing:
        if existing.vote == d.vote:
            db.delete(existing)
            db.commit()
            return {"status": "removed"}
        existing.vote = d.vote
        db.add(existing)
    else:
        db.add(NewsVote(article_id=d.article_id, user_id=user.id, vote=d.vote, created_at=utcnow()))

    db.commit()
    _update_relevance(article, db)
    return {"status": "ok"}


# ── Comments ──────────────────────────────────────────────────────────────────

class CommentData(BaseModel):
    article_id: int
    content: str
    parent_id: Optional[int] = None


@router.post("/news/comment")
def add_comment(
    d: CommentData,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not d.content.strip():
        raise HTTPException(400, "Comentário vazio")
    if len(d.content) > 1000:
        raise HTTPException(400, "Comentário muito longo (máx. 1000 chars)")

    article = db.query(NewsArticle).filter_by(id=d.article_id).first()
    if not article:
        raise HTTPException(404, "Artigo não encontrado")

    comment = NewsComment(
        article_id=d.article_id,
        user_id=user.id,
        parent_id=d.parent_id,
        content=d.content.strip(),
        created_at=utcnow(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {"status": "ok", "id": comment.id}


@router.get("/news/comments/{article_id}")
def get_comments(
    article_id: int,
    db: Session = Depends(get_db),
):
    comments = db.query(NewsComment)\
                 .filter_by(article_id=article_id, parent_id=None)\
                 .order_by(NewsComment.created_at.asc())\
                 .limit(100).all()
    return [_format_comment(c, db) for c in comments]


# ── Sources ───────────────────────────────────────────────────────────────────

@router.get("/news/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(NewsSource).order_by(NewsSource.name).all()
    return [{"id": s.id, "name": s.name, "domain": s.domain,
             "verified": bool(s.verified), "country": s.country} for s in sources]


@router.get("/news/categories")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(NewsCategory).all()
    return [{"slug": c.slug, "label": c.label, "color": c.color} for c in cats]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_article(a: NewsArticle, db: Session, include_comments=False) -> dict:
    upvotes   = db.query(func.count(NewsVote.id)).filter_by(article_id=a.id, vote=1).scalar() or 0
    downvotes = db.query(func.count(NewsVote.id)).filter_by(article_id=a.id, vote=-1).scalar() or 0
    comment_count = db.query(func.count(NewsComment.id)).filter_by(article_id=a.id).scalar() or 0

    result = {
        "id": a.id,
        "title": a.title,
        "description": a.description or '',
        "url": a.url,
        "image_url": a.image_url or '',
        "country_code": a.country_code or '',
        "region_code": a.region_code or '',
        "city": a.city or '',
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "relevance_score": a.relevance_score or 0,
        "verified": bool(a.verified),
        "upvotes": upvotes,
        "downvotes": downvotes,
        "comment_count": comment_count,
        "source": {
            "name": a.source.name if a.source else '',
            "verified": bool(a.source.verified) if a.source else False,
        } if a.source else None,
        "category": {
            "slug": a.category.slug if a.category else '',
            "label": a.category.label if a.category else '',
            "color": a.category.color if a.category else '',
        } if a.category else None,
    }
    if include_comments:
        comments = db.query(NewsComment)\
                     .filter_by(article_id=a.id, parent_id=None)\
                     .order_by(NewsComment.created_at)\
                     .limit(50).all()
        result['comments'] = [_format_comment(c, db) for c in comments]
    return result


def _format_comment(c: NewsComment, db: Session) -> dict:
    user = db.query(User).filter_by(id=c.user_id).first()
    replies = db.query(NewsComment).filter_by(parent_id=c.id)\
                .order_by(NewsComment.created_at).limit(20).all()
    return {
        "id": c.id,
        "content": c.content,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "user": {
            "id": user.id if user else 0,
            "username": user.username if user else 'Usuário',
            "avatar": user.avatar_url if user else '',
        },
        "replies": [_format_comment(r, db) for r in replies],
    }


def _update_relevance(article: NewsArticle, db: Session):
    """Recalculate relevance score after a vote."""
    upvotes   = db.query(func.count(NewsVote.id)).filter_by(article_id=article.id, vote=1).scalar() or 0
    downvotes = db.query(func.count(NewsVote.id)).filter_by(article_id=article.id, vote=-1).scalar() or 0
    # Simple Wilson score approximation
    article.relevance_score = float(upvotes - downvotes)
    db.add(article)
    db.commit()
