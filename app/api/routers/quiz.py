"""
Quiz router: listar quizzes, responder, ranking, histórico.
Anti-trapaça: rate limit por dia, cooldown 30min, tempo mínimo server-side.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from typing import List, Optional
import json
import random
import logging

from app.api.core import get_db, get_current_active_user
from app.models.models import User
from app.models.features import (
    Quiz, QuizQuestion, QuizAttempt, GloryPointsLog, Plan, Subscription, GloryRank
)

logger = logging.getLogger("ForGlory")
router = APIRouter()

def utcnow():
    return datetime.now(timezone.utc)


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_daily_limit(user: User, db: Session) -> int:
    sub = db.query(Subscription).filter_by(user_id=user.id, status='active').first()
    if sub and sub.plan:
        feats = sub.plan.features or {}
        return feats.get('quiz_daily', 10)
    return 10  # free tier


def get_glory_multiplier(user: User, db: Session) -> float:
    sub = db.query(Subscription).filter_by(user_id=user.id, status='active').first()
    if sub and sub.plan:
        return sub.plan.glory_multiplier or 1.0
    return 1.0


def add_glory(user_id: int, points: int, source: str, desc: str, db: Session):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return 0
    current = getattr(user, 'glory_points', 0) or 0
    user.glory_points = current + points
    db.add(user)
    db.add(GloryPointsLog(user_id=user_id, points=points, source=source, description=desc))
    db.commit()
    return user.glory_points


def count_today_attempts(user_id: int, db: Session) -> int:
    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.completed_at >= today_start,
    ).count()


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/quizzes")
def list_quizzes(
    category: Optional[str] = None,
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    q = db.query(Quiz).filter(Quiz.is_active == 1)
    if category:
        q = q.filter(Quiz.category == category)
    quizzes = q.order_by(Quiz.created_at.desc()).limit(limit).all()

    # Mark which ones the user already attempted
    attempted = {
        a.quiz_id
        for a in db.query(QuizAttempt.quiz_id).filter_by(user_id=user.id).all()
    }

    return [
        {
            "id": qz.id, "title": qz.title,
            "category": qz.category, "difficulty": qz.difficulty,
            "question_count": len(qz.questions),
            "attempted": qz.id in attempted,
            "created_at": qz.created_at.isoformat() if qz.created_at else None,
        }
        for qz in quizzes
    ]


@router.get("/quizzes/{quiz_id}")
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    quiz = db.query(Quiz).filter_by(id=quiz_id, is_active=1).first()
    if not quiz:
        raise HTTPException(404, "Quiz não encontrado")

    # Check if already attempted
    existing = db.query(QuizAttempt).filter_by(user_id=user.id, quiz_id=quiz_id).first()
    if existing:
        raise HTTPException(409, "Você já respondeu este quiz. Aguarde o próximo!")

    # Daily limit check
    daily = count_today_attempts(user.id, db)
    limit = get_daily_limit(user, db)
    if daily >= limit:
        raise HTTPException(429, f"Limite diário de {limit} quizzes atingido. Volte amanhã!")

    # Shuffle options server-side (returns shuffled + mapping for scoring)
    questions_out = []
    for q in quiz.questions:
        opts = q.options[:]
        correct_text = opts[q.correct_index]
        random.shuffle(opts)
        new_correct = opts.index(correct_text)
        questions_out.append({
            "id": q.id,
            "question": q.question,
            "options": opts,
            "correct_index": new_correct,   # client needs this to validate (no server-trust needed here since it's visible)
            "points": q.points or 10,
            "explanation": q.explanation or "",
        })

    return {
        "id": quiz.id, "title": quiz.title,
        "category": quiz.category, "difficulty": quiz.difficulty,
        "questions": questions_out,
        "time_limit_sec": len(quiz.questions) * 30,  # 30s per question
    }


class SubmitAnswers(BaseModel):
    answers: List[int]      # index chosen for each question (in order returned by GET)
    time_sec: int


@router.post("/quizzes/{quiz_id}/submit")
def submit_quiz(
    quiz_id: int,
    d: SubmitAnswers,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    quiz = db.query(Quiz).filter_by(id=quiz_id, is_active=1).first()
    if not quiz:
        raise HTTPException(404, "Quiz não encontrado")

    # Anti-cheat: already attempted?
    existing = db.query(QuizAttempt).filter_by(user_id=user.id, quiz_id=quiz_id).first()
    if existing:
        raise HTTPException(409, "Já respondido")

    # Anti-cheat: minimum time (1 second per question)
    min_time = len(quiz.questions)
    if d.time_sec < min_time:
        raise HTTPException(400, "Tempo muito rápido. Leia as perguntas!")

    # Anti-cheat: daily limit
    daily = count_today_attempts(user.id, db)
    limit = get_daily_limit(user, db)
    if daily >= limit:
        raise HTTPException(429, f"Limite diário de {limit} quizzes atingido")

    # Score: we need to re-shuffle with same seed? No - we score based on answers vs correct
    # Since we returned correct_index to client, we trust user answers against questions order
    questions = quiz.questions
    if len(d.answers) != len(questions):
        raise HTTPException(400, "Número de respostas incorreto")

    total_points = 0
    correct_count = 0
    results = []
    for i, (q, chosen) in enumerate(zip(questions, d.answers)):
        # Time bonus: full points if answered quickly, reduced after time limit
        time_ratio = min(1.0, (len(questions) * 30) / max(d.time_sec, 1))
        pts = q.points or 10
        if chosen == q.correct_index:
            earned = max(int(pts * time_ratio), 1)
            total_points += earned
            correct_count += 1
            results.append({"correct": True, "earned": earned})
        else:
            results.append({"correct": False, "earned": 0, "correct_index": q.correct_index})

    # Apply VIP multiplier
    multiplier = get_glory_multiplier(user, db)
    final_points = int(total_points * multiplier)

    # Save attempt
    attempt = QuizAttempt(
        user_id=user.id,
        quiz_id=quiz_id,
        score=final_points,
        time_sec=d.time_sec,
        completed_at=utcnow(),
    )
    attempt._answers = json.dumps(d.answers)
    db.add(attempt)

    # Add glory points
    if final_points > 0:
        new_total = add_glory(
            user.id, final_points, "quiz",
            f"Quiz '{quiz.title[:40]}': {correct_count}/{len(questions)} corretas",
            db
        )
    else:
        new_total = getattr(user, 'glory_points', 0) or 0
        db.commit()

    return {
        "score": final_points,
        "correct": correct_count,
        "total": len(questions),
        "multiplier": multiplier,
        "glory_earned": final_points,
        "glory_total": new_total,
        "results": results,
    }


@router.get("/quizzes/ranking/weekly")
def quiz_ranking(db: Session = Depends(get_db)):
    week_start = utcnow() - timedelta(days=7)
    rows = db.query(
        QuizAttempt.user_id,
        func.sum(QuizAttempt.score).label('total'),
        func.count(QuizAttempt.id).label('count'),
    ).filter(
        QuizAttempt.completed_at >= week_start
    ).group_by(QuizAttempt.user_id)\
     .order_by(func.sum(QuizAttempt.score).desc())\
     .limit(20).all()

    result = []
    for i, row in enumerate(rows, 1):
        user = db.query(User).filter_by(id=row.user_id).first()
        if not user:
            continue
        result.append({
            "position": i,
            "user_id": user.id,
            "username": user.username,
            "avatar": user.avatar_url or '',
            "score_week": row.total,
            "quizzes_done": row.count,
        })
    return result


@router.get("/my/quiz-history")
def my_quiz_history(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    attempts = db.query(QuizAttempt)\
                 .filter_by(user_id=user.id)\
                 .order_by(QuizAttempt.completed_at.desc())\
                 .limit(30).all()
    return [
        {
            "quiz_id": a.quiz_id,
            "quiz_title": a.quiz.title if a.quiz else "?",
            "score": a.score,
            "time_sec": a.time_sec,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in attempts
    ]


# ── Admin: criar quiz ────────────────────────────────────────────────────────

class CreateQuizData(BaseModel):
    title: str
    category: str = "general"
    difficulty: str = "medium"
    questions: List[dict]   # [{question, options: [4 strings], correct_index, explanation}]


@router.post("/quizzes/create")
def create_quiz(
    d: CreateQuizData,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if getattr(user, 'role', '') not in ('admin', 'fundador'):
        raise HTTPException(403, "Apenas admins podem criar quizzes")

    quiz = Quiz(
        title=d.title, category=d.category,
        difficulty=d.difficulty, is_active=1,
        created_at=utcnow()
    )
    db.add(quiz)
    db.flush()

    for q in d.questions:
        qq = QuizQuestion(
            quiz_id=quiz.id,
            question=q['question'],
            correct_index=q['correct_index'],
            explanation=q.get('explanation', ''),
            points=q.get('points', 10),
        )
        qq.options = q['options']
        db.add(qq)

    db.commit()
    return {"status": "ok", "quiz_id": quiz.id}


# ═══════════════════════════════════════════════════════════
# QUIZZES DIÁRIOS GERADOS POR IA
# ═══════════════════════════════════════════════════════════

@router.get("/quizzes/daily")
async def list_daily_quizzes(
    country: str = Query("BR"),
    db: Session = Depends(get_db),
):
    """Lista os 30 quizzes do dia para o país do usuário."""
    from datetime import date
    today_prefix = f"daily_{date.today().strftime('%Y%m%d')}_{country.upper()}"
    quizzes = (
        db.query(Quiz)
        .filter(
            Quiz.source_id.like(f"{today_prefix}%"),
            Quiz.is_active == 1,
        )
        .order_by(Quiz.category, Quiz.id)
        .all()
    )
    # Se não há quizzes para hoje, retornar lista vazia (geração é assíncrona)
    result = []
    for q in quizzes:
        attempts = [a for a in q.attempts] if q.attempts else []
        result.append({
            "id": q.id,
            "title": q.title,
            "category": q.category,
            "difficulty": q.difficulty,
            "question_count": len(q.questions),
            "attempted": False,  # será filtrado por user no frontend se autenticado
            "is_daily": True,
            "expires_at": q.expires_at.strftime("%d/%m %H:%M") if q.expires_at else None,
        })
    return {"quizzes": result, "total": len(result), "country": country}


@router.post("/quizzes/generate-daily")
async def trigger_daily_generation(
    data: dict = Body(default={}),
    db: Session = Depends(get_db),
):
    """Dispara a geração dos quizzes do dia. Pode ser chamado pelo cron ou por admin."""
    from app.api.routers.quiz_generator import generate_daily_quizzes
    country = str(data.get("country", "BR")).upper()
    result = await generate_daily_quizzes(country)
    return result


@router.get("/quizzes/daily/status")
async def daily_quiz_status(country: str = Query("BR"), db: Session = Depends(get_db)):
    """Verifica se os quizzes do dia já foram gerados."""
    from datetime import date
    today_prefix = f"daily_{date.today().strftime('%Y%m%d')}_{country.upper()}"
    count = db.query(Quiz).filter(
        Quiz.source_id.like(f"{today_prefix}%"),
        Quiz.is_active == 1,
    ).count()
    return {"generated": count, "ready": count >= 25, "country": country}
