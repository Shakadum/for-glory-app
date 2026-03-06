"""
Diagnostics router: system health checks for admins.
GET /admin/diagnostics — runs all checks and returns structured report.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timezone, timedelta
import logging
import httpx
import asyncio

from app.api.core import get_db, get_current_active_user
from app.models.models import User, PrivateMessage
from app.models.features import (
    Politician, PoliticianTerm, MessageReaction, Quiz, QuizAttempt,
    NewsArticle
)
from app.core.redis import get_redis

logger = logging.getLogger("ForGlory")
router = APIRouter()

def utcnow():
    return datetime.now(timezone.utc)


def check(name: str, status: str, count: int = 0, message: str = "") -> dict:
    return {"name": name, "status": status, "count": count, "message": message}


async def run_all_checks(db: Session) -> list:
    results = []

    # ── 1. Políticos sem foto ────────────────────────────────────────────────
    try:
        n = db.query(func.count(Politician.id)).filter(
            (Politician.photo == None) | (Politician.photo == '')
        ).scalar() or 0
        results.append(check(
            "Políticos sem foto", "warning" if n > 50 else "ok", n,
            f"{n} políticos sem foto" if n else "Todos têm foto"
        ))
    except Exception as e:
        results.append(check("Políticos sem foto", "error", 0, str(e)))

    # ── 2. Mandatos com datas inválidas ─────────────────────────────────────
    try:
        n = db.query(func.count(PoliticianTerm.id)).filter(
            PoliticianTerm.end_date < PoliticianTerm.start_date
        ).scalar() or 0
        results.append(check(
            "Mandatos com datas inválidas", "error" if n else "ok", n,
            f"{n} mandatos com end_date < start_date" if n else "Datas OK"
        ))
    except Exception as e:
        results.append(check("Mandatos com datas inválidas", "error", 0, str(e)))

    # ── 3. Políticos duplicados (mesmo wikidata_id) ──────────────────────────
    try:
        rows = db.execute(text("""
            SELECT wikidata_id, COUNT(*) as c
            FROM politicians
            WHERE wikidata_id IS NOT NULL AND wikidata_id != ''
            GROUP BY wikidata_id HAVING COUNT(*) > 1
        """)).fetchall()
        n = len(rows)
        results.append(check(
            "Duplicatas Wikidata", "error" if n else "ok", n,
            f"{n} wikidata_ids duplicados" if n else "Sem duplicatas"
        ))
    except Exception as e:
        results.append(check("Duplicatas Wikidata", "error", 0, str(e)))

    # ── 4. Políticos sem partido ────────────────────────────────────────────
    try:
        n = db.query(func.count(Politician.id)).filter(
            (Politician.party == None) | (Politician.party == ''),
            Politician.current_position != None,
        ).scalar() or 0
        results.append(check(
            "Políticos sem partido", "warning" if n > 20 else "ok", n,
            f"{n} políticos com cargo mas sem partido" if n else "OK"
        ))
    except Exception as e:
        results.append(check("Políticos sem partido", "error", 0, str(e)))

    # ── 5. Artigos de notícias nas últimas 24h ──────────────────────────────
    try:
        cutoff = utcnow() - timedelta(hours=24)
        n = db.query(func.count(NewsArticle.id)).filter(
            NewsArticle.created_at >= cutoff
        ).scalar() or 0
        results.append(check(
            "Notícias últimas 24h", "warning" if n == 0 else "ok", n,
            f"{n} artigos indexados nas últimas 24h"
        ))
    except Exception as e:
        results.append(check("Notícias últimas 24h", "error", 0, str(e)))

    # ── 6. Redis health ─────────────────────────────────────────────────────
    try:
        r = get_redis()
        if r:
            await r.ping()
            results.append(check("Redis", "ok", 0, "Conectado e respondendo"))
        else:
            results.append(check("Redis", "warning", 0, "Redis não configurado (REDIS_URL ausente)"))
    except Exception as e:
        results.append(check("Redis", "error", 0, f"Falha: {e}"))

    # ── 7. Mensagens privadas nas últimas 24h ────────────────────────────────
    try:
        cutoff = utcnow() - timedelta(hours=24)
        n = db.query(func.count(PrivateMessage.id)).filter(
            PrivateMessage.timestamp >= cutoff
        ).scalar() or 0
        results.append(check("Mensagens DM 24h", "ok", n, f"{n} mensagens nas últimas 24h"))
    except Exception as e:
        results.append(check("Mensagens DM 24h", "error", 0, str(e)))

    # ── 8. Quizzes ativos ───────────────────────────────────────────────────
    try:
        n = db.query(func.count(Quiz.id)).filter(Quiz.is_active == 1).scalar() or 0
        results.append(check(
            "Quizzes ativos", "warning" if n == 0 else "ok", n,
            f"{n} quizzes disponíveis" if n else "Nenhum quiz ativo"
        ))
    except Exception as e:
        results.append(check("Quizzes ativos", "error", 0, str(e)))

    # ── 9. Total de usuários registrados ────────────────────────────────────
    try:
        n = db.query(func.count(User.id)).scalar() or 0
        results.append(check("Usuários totais", "ok", n, f"{n} usuários registrados"))
    except Exception as e:
        results.append(check("Usuários totais", "error", 0, str(e)))

    # ── 10. Total de políticos no banco ─────────────────────────────────────
    try:
        n = db.query(func.count(Politician.id)).scalar() or 0
        results.append(check(
            "Políticos no banco", "warning" if n < 10 else "ok", n,
            f"{n} políticos indexados"
        ))
    except Exception as e:
        results.append(check("Políticos no banco", "error", 0, str(e)))

    return results


@router.get("/admin/diagnostics")
async def run_diagnostics(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if getattr(user, 'role', '') not in ('admin', 'fundador'):
        raise HTTPException(403, "Acesso restrito a administradores")

    checks = await run_all_checks(db)

    overall = "ok"
    for c in checks:
        if c["status"] == "error":
            overall = "error"
            break
        if c["status"] == "warning" and overall != "error":
            overall = "warning"

    return {
        "overall": overall,
        "checks": checks,
        "generated_at": utcnow().isoformat(),
        "total_checks": len(checks),
        "errors": sum(1 for c in checks if c["status"] == "error"),
        "warnings": sum(1 for c in checks if c["status"] == "warning"),
    }


@router.get("/admin/stats")
def admin_stats(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if getattr(user, 'role', '') not in ('admin', 'fundador'):
        raise HTTPException(403, "Acesso restrito")

    cutoff_24h = utcnow() - timedelta(hours=24)
    cutoff_7d  = utcnow() - timedelta(days=7)

    try:
        total_users = db.query(func.count(User.id)).scalar() or 0
        msgs_24h    = db.query(func.count(PrivateMessage.id)).filter(PrivateMessage.timestamp >= cutoff_24h).scalar() or 0
        politicians = db.query(func.count(Politician.id)).scalar() or 0
        articles    = db.query(func.count(NewsArticle.id)).scalar() or 0
        quizzes_done= db.query(func.count(QuizAttempt.id)).filter(QuizAttempt.completed_at >= cutoff_7d).scalar() or 0
        return {
            "users_total": total_users,
            "messages_24h": msgs_24h,
            "politicians_total": politicians,
            "news_articles_total": articles,
            "quiz_attempts_7d": quizzes_done,
        }
    except Exception as e:
        raise HTTPException(500, str(e))
