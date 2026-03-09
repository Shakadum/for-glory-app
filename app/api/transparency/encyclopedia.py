"""
For Glory — Enciclopédia Viva
Módulo: lógica de sugestões, moderação, score de confiança e histórico
"""
import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from .models import PoliticianEdit, EditSource, EditVote, PoliticianRevision, PoliticianTrustScore


# ── Campos editáveis e seus labels ───────────────────────────────────────────
EDITABLE_FIELDS = {
    "salary":      {"label": "Salário", "type": "number"},
    "party":       {"label": "Partido", "type": "text"},
    "bio":         {"label": "Biografia", "type": "textarea"},
    "charges":     {"label": "Acusações/Processos", "type": "list"},
    "photo":       {"label": "Foto", "type": "url"},
    "email":       {"label": "E-mail", "type": "text"},
    "assets":      {"label": "Patrimônio declarado", "type": "number"},
    "education":   {"label": "Formação", "type": "text"},
    "mandates":    {"label": "Mandatos/histórico", "type": "list"},
}

SOURCE_KINDS = {
    "official": "🏛️ Oficial",
    "news":     "📰 Notícia",
    "wikipedia":"📚 Wikipedia",
    "other":    "🔗 Outro",
}


# ── Trust Score ───────────────────────────────────────────────────────────────

def _recalc_trust(db: Session, politician_id: str) -> float:
    """Recalcula e salva o trust score de um político."""
    edits = db.query(PoliticianEdit).filter_by(politician_id=politician_id).all()
    approved = [e for e in edits if e.status == "approved"]
    rejected = [e for e in edits if e.status == "rejected"]

    # Source score: média de qualidade de fontes nas edições aprovadas
    total_sources = sum(len(e.sources) for e in approved)
    official_sources = sum(
        sum(1 for s in e.sources if s.kind == "official") for e in approved
    )
    source_score = min(100.0, (official_sources * 30 + total_sources * 10)) if total_sources else 50.0

    # Community score: baseado em avaliações
    from .models import PoliticianRating
    ratings = db.query(PoliticianRating).filter_by(politician_id=politician_id).all()
    if ratings:
        avg = sum(r.score for r in ratings) / len(ratings)
        community_score = (avg / 5.0) * 100
    else:
        community_score = 50.0

    # Data score: edições aprovadas aumentam, rejeitadas diminuem
    data_score = min(100.0, max(0.0, 50.0 + len(approved) * 5 - len(rejected) * 8))

    # Score final ponderado
    score = round(source_score * 0.4 + community_score * 0.3 + data_score * 0.3, 1)

    row = db.query(PoliticianTrustScore).filter_by(politician_id=politician_id).first()
    if row:
        row.score = score
        row.source_score = source_score
        row.community_score = community_score
        row.data_score = data_score
        row.approved_edits = len(approved)
        row.rejected_edits = len(rejected)
        row.total_sources = total_sources
        row.updated_at = datetime.now(timezone.utc)
    else:
        db.add(PoliticianTrustScore(
            politician_id=politician_id,
            score=score, source_score=source_score,
            community_score=community_score, data_score=data_score,
            approved_edits=len(approved), rejected_edits=len(rejected),
            total_sources=total_sources,
        ))
    db.commit()
    return score


def get_trust_score(db: Session, politician_id: str) -> dict:
    row = db.query(PoliticianTrustScore).filter_by(politician_id=politician_id).first()
    if not row:
        return {"score": 50.0, "label": "Dados básicos", "color": "#888", "details": {}}
    score = row.score
    if score >= 80:
        label, color = "Alta confiança", "#22c55e"
    elif score >= 60:
        label, color = "Confiável", "#66fcf1"
    elif score >= 40:
        label, color = "Dados básicos", "#f59e0b"
    else:
        label, color = "Pouco verificado", "#ef4444"
    return {
        "score": score, "label": label, "color": color,
        "details": {
            "fontes": round(row.source_score, 1),
            "comunidade": round(row.community_score, 1),
            "completude": round(row.data_score, 1),
        },
        "edits": {"aprovadas": row.approved_edits, "rejeitadas": row.rejected_edits},
        "total_sources": row.total_sources,
    }


# ── Sugestões ─────────────────────────────────────────────────────────────────

def create_edit_suggestion(
    db: Session,
    politician_id: str,
    user_id: int,
    field: str,
    new_value,
    old_value=None,
    reason: str = "",
    sources: list = None,
) -> PoliticianEdit:
    if field not in EDITABLE_FIELDS:
        raise ValueError(f"Campo '{field}' não é editável")

    edit = PoliticianEdit(
        politician_id=politician_id,
        user_id=user_id,
        field=field,
        old_value=json.dumps(old_value, ensure_ascii=False) if old_value is not None else None,
        new_value=json.dumps(new_value, ensure_ascii=False),
        reason=reason,
        status="pending",
    )
    db.add(edit)
    db.flush()  # gera edit.id

    for src in (sources or []):
        db.add(EditSource(
            edit_id=edit.id,
            url=src.get("url", ""),
            label=src.get("label", ""),
            kind=src.get("kind", "other"),
        ))

    db.commit()
    db.refresh(edit)
    return edit


def vote_on_edit(db: Session, edit_id: int, user_id: int, value: int) -> dict:
    """value: +1 (apoia) ou -1 (contesta)."""
    if value not in (1, -1):
        raise ValueError("value deve ser +1 ou -1")
    existing = db.query(EditVote).filter_by(edit_id=edit_id, user_id=user_id).first()
    if existing:
        existing.value = value
    else:
        db.add(EditVote(edit_id=edit_id, user_id=user_id, value=value))
    db.commit()
    total = db.query(EditVote).filter_by(edit_id=edit_id).all()
    ups   = sum(1 for v in total if v.value == 1)
    downs = sum(1 for v in total if v.value == -1)
    return {"ups": ups, "downs": downs, "user_vote": value}


def moderate_edit(
    db: Session,
    edit_id: int,
    moderator_id: int,
    approve: bool,
    note: str = "",
) -> PoliticianEdit:
    edit = db.query(PoliticianEdit).filter_by(id=edit_id).first()
    if not edit:
        raise ValueError("Edição não encontrada")
    if edit.status != "pending":
        raise ValueError("Edição já foi revisada")

    edit.status = "approved" if approve else "rejected"
    edit.reviewed_by = moderator_id
    edit.reviewed_at = datetime.now(timezone.utc)
    edit.review_note = note

    if approve:
        # Criar revisão imutável
        revision = PoliticianRevision(
            politician_id=edit.politician_id,
            edit_id=edit.id,
            snapshot="{}",   # será preenchido pela rota com dados completos
            changed_field=edit.field,
            changed_by=edit.user_id,
            approved_by=moderator_id,
        )
        db.add(revision)

    db.commit()
    db.refresh(edit)
    _recalc_trust(db, edit.politician_id)
    return edit


def get_edits_for_politician(db: Session, politician_id: str, status: str = None) -> list:
    q = db.query(PoliticianEdit).filter_by(politician_id=politician_id)
    if status:
        q = q.filter_by(status=status)
    edits = q.order_by(PoliticianEdit.created_at.desc()).all()
    result = []
    for e in edits:
        ups   = sum(1 for v in e.votes if v.value == 1)
        downs = sum(1 for v in e.votes if v.value == -1)
        result.append({
            "id": e.id,
            "field": e.field,
            "field_label": EDITABLE_FIELDS.get(e.field, {}).get("label", e.field),
            "old_value": json.loads(e.old_value) if e.old_value else None,
            "new_value": json.loads(e.new_value),
            "reason": e.reason,
            "status": e.status,
            "review_note": e.review_note,
            "created_at": e.created_at.strftime("%d/%m/%Y %H:%M") if e.created_at else "",
            "sources": [{"url": s.url, "label": s.label, "kind": s.kind} for s in e.sources],
            "votes": {"ups": ups, "downs": downs},
        })
    return result


def get_revision_history(db: Session, politician_id: str) -> list:
    revs = (
        db.query(PoliticianRevision)
        .filter_by(politician_id=politician_id)
        .order_by(PoliticianRevision.created_at.desc())
        .limit(50)
        .all()
    )
    return [{
        "id": r.id,
        "field": r.changed_field,
        "field_label": EDITABLE_FIELDS.get(r.changed_field or "", {}).get("label", r.changed_field or ""),
        "changed_by": r.changed_by,
        "approved_by": r.approved_by,
        "created_at": r.created_at.strftime("%d/%m/%Y %H:%M") if r.created_at else "",
    } for r in revs]


def get_pending_edits(db: Session, limit: int = 50) -> list:
    """Para painel de moderação — lista todas as sugestões pendentes."""
    edits = (
        db.query(PoliticianEdit)
        .filter_by(status="pending")
        .order_by(PoliticianEdit.created_at.asc())
        .limit(limit)
        .all()
    )
    result = []
    for e in edits:
        ups = sum(1 for v in e.votes if v.value == 1)
        downs = sum(1 for v in e.votes if v.value == -1)
        result.append({
            "id": e.id,
            "politician_id": e.politician_id,
            "field": e.field,
            "field_label": EDITABLE_FIELDS.get(e.field, {}).get("label", e.field),
            "new_value": json.loads(e.new_value),
            "old_value": json.loads(e.old_value) if e.old_value else None,
            "reason": e.reason,
            "user_id": e.user_id,
            "created_at": e.created_at.strftime("%d/%m/%Y %H:%M") if e.created_at else "",
            "sources": [{"url": s.url, "label": s.label, "kind": s.kind} for s in e.sources],
            "votes": {"ups": ups, "downs": downs},
        })
    return result
