"""
For Glory — Portal da Transparência
Módulo: Modelos SQLAlchemy
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base


class PoliticianRating(Base):
    __tablename__ = "politician_ratings"
    id            = Column(Integer, primary_key=True, index=True)
    politician_id = Column(String(100), index=True)
    user_id       = Column(Integer, index=True)
    score         = Column(Integer)
    comment       = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MayorCache(Base):
    """Cache persistente — 5571 prefeitos. Fontes: TSE 2024 + Wikidata."""
    __tablename__ = "mayor_cache"
    __table_args__ = (UniqueConstraint("uf", "city_norm", name="uq_mc_uf_city"),)
    id         = Column(Integer, primary_key=True)
    uf         = Column(String(2),   index=True)
    city_norm  = Column(String(200), index=True)
    city_name  = Column(String(200))
    data       = Column(Text)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── ENCICLOPÉDIA VIVA ────────────────────────────────────────────────────────

class PoliticianEdit(Base):
    """Sugestão de edição de dados de um político pela comunidade."""
    __tablename__ = "politician_edits"

    id            = Column(Integer, primary_key=True, index=True)
    politician_id = Column(String(100), index=True, nullable=False)
    user_id       = Column(Integer, index=True, nullable=False)

    # Campo editado (ex: "salary", "party", "bio", "charges", "photo")
    field         = Column(String(100), nullable=False)
    # Valor anterior (JSON serializado)
    old_value     = Column(Text, nullable=True)
    # Valor proposto (JSON serializado)
    new_value     = Column(Text, nullable=False)
    # Justificativa do editor
    reason        = Column(Text, nullable=True)

    # Status: pending | approved | rejected
    status        = Column(String(20), default="pending", index=True)
    # Moderador que aprovou/rejeitou
    reviewed_by   = Column(Integer, nullable=True)
    reviewed_at   = Column(DateTime, nullable=True)
    review_note   = Column(Text, nullable=True)

    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    sources       = relationship("EditSource", back_populates="edit", cascade="all, delete-orphan")
    votes         = relationship("EditVote", back_populates="edit", cascade="all, delete-orphan")


class EditSource(Base):
    """Fonte citada para uma sugestão de edição."""
    __tablename__ = "edit_sources"

    id       = Column(Integer, primary_key=True)
    edit_id  = Column(Integer, ForeignKey("politician_edits.id"), nullable=False, index=True)
    url      = Column(Text, nullable=True)
    label    = Column(String(300), nullable=True)   # ex: "Câmara dos Deputados - Ficha"
    kind     = Column(String(50), nullable=True)    # "official" | "news" | "wikipedia" | "other"

    edit     = relationship("PoliticianEdit", back_populates="sources")


class EditVote(Base):
    """Voto da comunidade numa sugestão (upvote/downvote)."""
    __tablename__ = "edit_votes"
    __table_args__ = (UniqueConstraint("edit_id", "user_id", name="uq_ev_edit_user"),)

    id      = Column(Integer, primary_key=True)
    edit_id = Column(Integer, ForeignKey("politician_edits.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False)
    value   = Column(Integer, nullable=False)  # +1 ou -1

    edit    = relationship("PoliticianEdit", back_populates="votes")


class PoliticianRevision(Base):
    """Registro imutável de cada mudança aprovada (histórico de revisões)."""
    __tablename__ = "politician_revisions"

    id            = Column(Integer, primary_key=True)
    politician_id = Column(String(100), index=True, nullable=False)
    edit_id       = Column(Integer, ForeignKey("politician_edits.id"), nullable=True)
    # Snapshot completo dos dados do político naquele momento (JSON)
    snapshot      = Column(Text, nullable=False)
    changed_field = Column(String(100), nullable=True)
    changed_by    = Column(Integer, nullable=True)   # user_id
    approved_by   = Column(Integer, nullable=True)   # moderator user_id
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PoliticianTrustScore(Base):
    """Score de confiança calculado para cada político."""
    __tablename__ = "politician_trust_scores"
    __table_args__ = (UniqueConstraint("politician_id", name="uq_pts_politician"),)

    id            = Column(Integer, primary_key=True)
    politician_id = Column(String(100), index=True, nullable=False)
    # Score 0-100
    score         = Column(Float, default=50.0)
    # Fatores individuais (0-100 cada)
    source_score  = Column(Float, default=50.0)  # qualidade das fontes
    community_score = Column(Float, default=50.0) # avaliação da comunidade
    data_score    = Column(Float, default=50.0)  # completude dos dados
    # Contagens
    approved_edits   = Column(Integer, default=0)
    rejected_edits   = Column(Integer, default=0)
    total_sources    = Column(Integer, default=0)
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
