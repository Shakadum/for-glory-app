"""
For Glory — Portal da Transparência
Módulo: Modelos SQLAlchemy
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint
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
    """Cache persistente — 5571 prefeitos. Fontes: TSE 2024 + Wikidata.
    TTL 90 dias (prefeitos mudam só a cada 4 anos)."""
    __tablename__ = "mayor_cache"
    __table_args__ = (UniqueConstraint("uf", "city_norm", name="uq_mc_uf_city"),)
    id         = Column(Integer, primary_key=True)
    uf         = Column(String(2),   index=True)
    city_norm  = Column(String(200), index=True)
    city_name  = Column(String(200))
    data       = Column(Text)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
