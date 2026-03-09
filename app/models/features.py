"""
Models for: Politicians, News, VIP/Plans, Quizzes, Glory Points, Presence, Reactions
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, Float, SmallInteger,
    DateTime, Date, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


# ── PRESENCE ────────────────────────────────────────────────────────────────
class Presence(Base):
    __tablename__ = 'presence'
    user_id      = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    status       = Column(String(20), default='offline')   # online|away|offline|dnd
    last_seen    = Column(DateTime(timezone=True), default=utcnow)
    custom_status = Column(String(128), nullable=True)


# ── MESSAGE REACTIONS ────────────────────────────────────────────────────────
class MessageReaction(Base):
    __tablename__ = 'message_reactions'
    __table_args__ = (
        UniqueConstraint('message_id', 'message_type', 'user_id', 'emoji', name='uq_reaction'),
    )
    id           = Column(Integer, primary_key=True, autoincrement=True)
    message_id   = Column(Integer, nullable=False, index=True)
    message_type = Column(String(20), default='dm')   # dm | group | comm
    user_id      = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    emoji        = Column(String(10), nullable=False)
    created_at   = Column(DateTime(timezone=True), default=utcnow)


# ── POLITICIANS ──────────────────────────────────────────────────────────────
class Politician(Base):
    __tablename__ = 'politicians'
    id               = Column(String(100), primary_key=True)
    wikidata_id      = Column(String(30), nullable=True, index=True)
    name             = Column(String(300), nullable=False, index=True)
    photo            = Column(Text, nullable=True)
    country          = Column(String(5),  nullable=True, index=True)
    state            = Column(String(100), nullable=True, index=True)
    city             = Column(String(150), nullable=True)
    party            = Column(String(150), nullable=True)
    current_position = Column(String(200), nullable=True)
    birth_date       = Column(Date, nullable=True)
    education        = Column(Text, nullable=True)
    profession       = Column(String(200), nullable=True)
    bio              = Column(Text, nullable=True)
    _salary_info     = Column('salary_info', Text, nullable=True)
    _social_links    = Column('social_links', Text, nullable=True)
    source           = Column(String(50), nullable=True)
    photo_verified   = Column(Integer, default=0)
    created_at       = Column(DateTime(timezone=True), default=utcnow)
    updated_at       = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    terms    = relationship('PoliticianTerm',    back_populates='politician', cascade='all, delete-orphan')
    expenses = relationship('PoliticianExpense', back_populates='politician', cascade='all, delete-orphan')
    votes    = relationship('PoliticianVote',    back_populates='politician', cascade='all, delete-orphan')
    # ratings relationship defined in PoliticianRating (models.py) via back_populates

    @property
    def salary_info(self):
        try: return json.loads(self._salary_info) if self._salary_info else {}
        except: return {}

    @salary_info.setter
    def salary_info(self, v):
        self._salary_info = json.dumps(v, ensure_ascii=False) if v else None

    @property
    def social_links(self):
        try: return json.loads(self._social_links) if self._social_links else {}
        except: return {}

    @social_links.setter
    def social_links(self, v):
        self._social_links = json.dumps(v, ensure_ascii=False) if v else None

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'photo': self.photo or '',
            'country': self.country or '', 'state': self.state or '',
            'city': self.city or '', 'party': self.party or '',
            'role': self.current_position or '', 'source': self.source or '',
            'bio': self.bio or '', 'education': self.education or '',
            'salary_info': self.salary_info, 'social_links': self.social_links,
            'wikidata_id': self.wikidata_id or '',
        }


class PoliticianTerm(Base):
    __tablename__ = 'politician_terms'
    id            = Column(Integer, primary_key=True, autoincrement=True)
    politician_id = Column(String(100), ForeignKey('politicians.id', ondelete='CASCADE'), nullable=False, index=True)
    office        = Column(String(200), nullable=True)
    party         = Column(String(150), nullable=True)
    region        = Column(String(100), nullable=True)
    start_date    = Column(Date, nullable=True)
    end_date      = Column(Date, nullable=True)
    votes_count   = Column(Integer, default=0)
    presence_pct  = Column(Float, nullable=True)
    politician    = relationship('Politician', back_populates='terms')


class PoliticianExpense(Base):
    __tablename__ = 'politician_expenses'
    id            = Column(Integer, primary_key=True, autoincrement=True)
    politician_id = Column(String(100), ForeignKey('politicians.id', ondelete='CASCADE'), nullable=False, index=True)
    year          = Column(Integer, nullable=False)
    month         = Column(Integer, nullable=False)
    category      = Column(String(200), nullable=True)
    amount        = Column(Float, nullable=True)
    description   = Column(Text, nullable=True)
    document_url  = Column(Text, nullable=True)
    politician    = relationship('Politician', back_populates='expenses')


class PoliticianVote(Base):
    __tablename__ = 'politician_votes'
    id            = Column(Integer, primary_key=True, autoincrement=True)
    politician_id = Column(String(100), ForeignKey('politicians.id', ondelete='CASCADE'), nullable=False, index=True)
    vote_date     = Column(Date, nullable=True)
    proposition   = Column(String(300), nullable=True)
    position      = Column(String(30), nullable=True)   # sim|nao|abstencao|ausente
    session_url   = Column(Text, nullable=True)
    politician    = relationship('Politician', back_populates='votes')


class PoliticalParty(Base):
    __tablename__ = 'political_parties'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    sigla        = Column(String(30), nullable=False)
    name         = Column(String(200), nullable=True)
    country      = Column(String(5), nullable=True)
    ideology     = Column(String(200), nullable=True)
    founded_year = Column(Integer, nullable=True)
    logo_url     = Column(Text, nullable=True)


# ── NEWS ─────────────────────────────────────────────────────────────────────
class NewsSource(Base):
    __tablename__ = 'news_sources'
    id       = Column(Integer, primary_key=True, autoincrement=True)
    name     = Column(String(200), nullable=False)
    domain   = Column(String(200), nullable=True, unique=True)
    country  = Column(String(5), nullable=True)
    verified = Column(Integer, default=0)
    logo_url = Column(Text, nullable=True)
    articles = relationship('NewsArticle', back_populates='source')


class NewsCategory(Base):
    __tablename__ = 'news_categories'
    id       = Column(Integer, primary_key=True, autoincrement=True)
    slug     = Column(String(50), nullable=False, unique=True)
    label    = Column(String(100), nullable=True)
    color    = Column(String(20), nullable=True)
    articles = relationship('NewsArticle', back_populates='category')


class NewsArticle(Base):
    __tablename__ = 'news_articles'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    source_id       = Column(Integer, ForeignKey('news_sources.id', ondelete='SET NULL'), nullable=True)
    category_id     = Column(Integer, ForeignKey('news_categories.id', ondelete='SET NULL'), nullable=True)
    title           = Column(Text, nullable=False)
    description     = Column(Text, nullable=True)
    url             = Column(Text, nullable=False, unique=True)
    image_url       = Column(Text, nullable=True)
    country_code    = Column(String(5), nullable=True, index=True)
    region_code     = Column(String(15), nullable=True, index=True)
    city            = Column(String(150), nullable=True)
    published_at    = Column(DateTime(timezone=True), nullable=True, index=True)
    relevance_score = Column(Float, default=0.0)
    verified        = Column(Integer, default=0)
    created_at      = Column(DateTime(timezone=True), default=utcnow)
    source          = relationship('NewsSource', back_populates='articles')
    category        = relationship('NewsCategory', back_populates='articles')
    votes           = relationship('NewsVote', back_populates='article', cascade='all, delete-orphan')
    comments        = relationship('NewsComment', back_populates='article', cascade='all, delete-orphan')


class NewsVote(Base):
    __tablename__ = 'news_votes'
    __table_args__ = (UniqueConstraint('article_id', 'user_id', name='uq_news_vote'),)
    id         = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey('news_articles.id', ondelete='CASCADE'), nullable=False)
    user_id    = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    vote       = Column(SmallInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    article    = relationship('NewsArticle', back_populates='votes')


class NewsComment(Base):
    __tablename__ = 'news_comments'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey('news_articles.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    parent_id  = Column(Integer, ForeignKey('news_comments.id', ondelete='CASCADE'), nullable=True)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    article    = relationship('NewsArticle', back_populates='comments')
    replies    = relationship('NewsComment', backref='parent', remote_side=[id])


# ── VIP / PLANS ──────────────────────────────────────────────────────────────
class Plan(Base):
    __tablename__ = 'plans'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    slug             = Column(String(30), nullable=False, unique=True)
    name             = Column(String(100), nullable=False)
    price_monthly    = Column(Float, default=0.0)
    price_yearly     = Column(Float, default=0.0)
    _features        = Column('features', Text, nullable=True)
    glory_multiplier = Column(Float, default=1.0)

    @property
    def features(self):
        try: return json.loads(self._features) if self._features else {}
        except: return {}


class Subscription(Base):
    __tablename__ = 'subscriptions'
    id                   = Column(Integer, primary_key=True, autoincrement=True)
    user_id              = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    plan_id              = Column(Integer, ForeignKey('plans.id', ondelete='SET NULL'), nullable=True)
    status               = Column(String(30), default='active')   # active|cancelled|past_due|trial
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end   = Column(DateTime(timezone=True), nullable=True)
    provider             = Column(String(50), nullable=True)
    external_id          = Column(String(200), nullable=True)
    created_at           = Column(DateTime(timezone=True), default=utcnow)
    plan                 = relationship('Plan')



class VipPerk(Base):
    """Controle de desbloqueio VIP por usuário.
    Separa o estado 'já desbloqueou ouro' (permanente) do 'assinatura ativa'.
    """
    __tablename__ = 'vip_perks'

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    user_id                 = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'),
                                     nullable=False, unique=True, index=True)
    # Meses acumulados com assinatura ativa (para desbloquear ouro nos 12 meses)
    total_vip_months        = Column(Integer, default=0)
    # Flag permanente: ouro já foi desbloqueado alguma vez (não reseta ao cancelar)
    gold_border_unlocked    = Column(Integer, default=0)  # 0|1
    gold_border_unlocked_at = Column(DateTime(timezone=True), nullable=True)
    # Assinatura anual: desbloqueia ouro na hora
    annual_sub_unlocked     = Column(Integer, default=0)  # 0|1
    updated_at              = Column(DateTime(timezone=True), default=utcnow)

class Payment(Base):
    __tablename__ = 'payments'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True)
    amount          = Column(Float, nullable=False)
    currency        = Column(String(5), default='BRL')
    status          = Column(String(30), nullable=True)
    provider        = Column(String(50), nullable=True)
    external_id     = Column(String(200), nullable=True)
    paid_at         = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), default=utcnow)


# ── GLORY SYSTEM ─────────────────────────────────────────────────────────────
class GloryPointsLog(Base):
    __tablename__ = 'glory_points_log'
    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    points      = Column(Integer, nullable=False)
    source      = Column(String(50), nullable=True)
    description = Column(String(200), nullable=True)
    created_at  = Column(DateTime(timezone=True), default=utcnow)


class GloryRank(Base):
    __tablename__ = 'glory_ranks'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    slug       = Column(String(50), nullable=False, unique=True)
    name       = Column(String(100), nullable=False)
    min_points = Column(Integer, nullable=False)
    max_points = Column(Integer, nullable=True)
    color      = Column(String(20), nullable=True)
    badge_icon = Column(String(10), nullable=True)


# ── QUIZZES ──────────────────────────────────────────────────────────────────
class Quiz(Base):
    __tablename__ = 'quizzes'
    id          = Column(Integer, primary_key=True, autoincrement=True)
    title       = Column(String(300), nullable=False)
    category    = Column(String(50), nullable=True)
    difficulty  = Column(String(20), default='medium')
    source_type = Column(String(30), nullable=True)
    source_id   = Column(String(200), nullable=True)
    is_active   = Column(Integer, default=1)
    expires_at  = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), default=utcnow)
    questions   = relationship('QuizQuestion', back_populates='quiz', cascade='all, delete-orphan')
    attempts    = relationship('QuizAttempt',  back_populates='quiz',  cascade='all, delete-orphan')


class QuizQuestion(Base):
    __tablename__ = 'quiz_questions'
    id            = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id       = Column(Integer, ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False, index=True)
    question      = Column(Text, nullable=False)
    _options      = Column('options', Text, nullable=False)
    correct_index = Column(Integer, nullable=False)
    explanation   = Column(Text, nullable=True)
    source_url    = Column(Text, nullable=True)
    points        = Column(Integer, default=10)
    quiz          = relationship('Quiz', back_populates='questions')

    @property
    def options(self):
        try: return json.loads(self._options) if self._options else []
        except: return []

    @options.setter
    def options(self, v):
        self._options = json.dumps(v, ensure_ascii=False)


class QuizAttempt(Base):
    __tablename__ = 'quiz_attempts'
    __table_args__ = (UniqueConstraint('user_id', 'quiz_id', name='uq_quiz_attempt'),)
    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    quiz_id      = Column(Integer, ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False)
    score        = Column(Integer, default=0)
    time_sec     = Column(Integer, nullable=True)
    _answers     = Column('answers', Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), default=utcnow)
    quiz         = relationship('Quiz', back_populates='attempts')

    @property
    def answers(self):
        try: return json.loads(self._answers) if self._answers else []
        except: return []
