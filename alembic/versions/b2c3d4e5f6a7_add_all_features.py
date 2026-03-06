"""add all features: politicians db, news db, vip, quizzes, reactions, presence

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # ── USER EXTENSIONS ─────────────────────────────────────────────────────
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('glory_points', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('plan', sa.String(20), nullable=True, server_default='free'))
        batch_op.add_column(sa.Column('rank_slug', sa.String(50), nullable=True, server_default='recruta'))

    # ── PRESENCE ────────────────────────────────────────────────────────────
    op.create_table('presence',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='offline'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('custom_status', sa.String(128), nullable=True),
    )

    # ── MESSAGE REACTIONS ────────────────────────────────────────────────────
    op.create_table('message_reactions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('message_id', sa.Integer(), nullable=False, index=True),
        sa.Column('message_type', sa.String(20), nullable=False, server_default='dm'),  # dm | group | comm
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('emoji', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('message_id', 'message_type', 'user_id', 'emoji', name='uq_reaction'),
    )

    # ── POLITICIANS ──────────────────────────────────────────────────────────
    op.create_table('politicians',
        sa.Column('id', sa.String(100), primary_key=True),          # wd-Q12345 or tse-12345
        sa.Column('wikidata_id', sa.String(30), nullable=True, index=True),
        sa.Column('name', sa.String(300), nullable=False, index=True),
        sa.Column('photo', sa.Text(), nullable=True),
        sa.Column('country', sa.String(5), nullable=True, index=True),
        sa.Column('state', sa.String(100), nullable=True, index=True),
        sa.Column('city', sa.String(150), nullable=True),
        sa.Column('party', sa.String(150), nullable=True),
        sa.Column('current_position', sa.String(200), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('education', sa.Text(), nullable=True),
        sa.Column('profession', sa.String(200), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('salary_info', sa.Text(), nullable=True),          # JSON string
        sa.Column('social_links', sa.Text(), nullable=True),         # JSON string
        sa.Column('source', sa.String(50), nullable=True),           # camara|senado|wikidata|tse|manual
        sa.Column('photo_verified', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── POLITICIAN TERMS ────────────────────────────────────────────────────
    op.create_table('politician_terms',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('politician_id', sa.String(100), sa.ForeignKey('politicians.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('office', sa.String(200), nullable=True),
        sa.Column('party', sa.String(150), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('votes_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('presence_pct', sa.Float(), nullable=True),
    )

    # ── POLITICIAN EXPENSES ──────────────────────────────────────────────────
    op.create_table('politician_expenses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('politician_id', sa.String(100), sa.ForeignKey('politicians.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(200), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('document_url', sa.Text(), nullable=True),
    )

    # ── POLITICIAN VOTES ─────────────────────────────────────────────────────
    op.create_table('politician_votes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('politician_id', sa.String(100), sa.ForeignKey('politicians.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('vote_date', sa.Date(), nullable=True),
        sa.Column('proposition', sa.String(300), nullable=True),
        sa.Column('position', sa.String(30), nullable=True),   # sim|nao|abstencao|ausente
        sa.Column('session_url', sa.Text(), nullable=True),
    )

    # ── POLITICAL PARTIES ────────────────────────────────────────────────────
    op.create_table('political_parties',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sigla', sa.String(30), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('country', sa.String(5), nullable=True),
        sa.Column('ideology', sa.String(200), nullable=True),
        sa.Column('founded_year', sa.Integer(), nullable=True),
        sa.Column('logo_url', sa.Text(), nullable=True),
    )

    # ── NEWS SOURCES ─────────────────────────────────────────────────────────
    op.create_table('news_sources',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('domain', sa.String(200), nullable=True, unique=True),
        sa.Column('country', sa.String(5), nullable=True),
        sa.Column('verified', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('logo_url', sa.Text(), nullable=True),
    )

    # ── NEWS CATEGORIES ──────────────────────────────────────────────────────
    op.create_table('news_categories',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('slug', sa.String(50), nullable=False, unique=True),
        sa.Column('label', sa.String(100), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
    )

    # ── NEWS ARTICLES ────────────────────────────────────────────────────────
    op.create_table('news_articles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('news_sources.id', ondelete='SET NULL'), nullable=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('news_categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=False, unique=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('country_code', sa.String(5), nullable=True, index=True),
        sa.Column('region_code', sa.String(15), nullable=True, index=True),
        sa.Column('city', sa.String(150), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('relevance_score', sa.Float(), nullable=True, server_default='0'),
        sa.Column('verified', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── NEWS VOTES ───────────────────────────────────────────────────────────
    op.create_table('news_votes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('news_articles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vote', sa.SmallInteger(), nullable=False),   # +1 ou -1
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('article_id', 'user_id', name='uq_news_vote'),
    )

    # ── NEWS COMMENTS ────────────────────────────────────────────────────────
    op.create_table('news_comments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('news_articles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('news_comments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── VIP PLANS ────────────────────────────────────────────────────────────
    op.create_table('plans',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('slug', sa.String(30), nullable=False, unique=True),  # free|vip1|vip2|vip3
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('price_monthly', sa.Float(), nullable=True, server_default='0'),
        sa.Column('price_yearly', sa.Float(), nullable=True, server_default='0'),
        sa.Column('features', sa.Text(), nullable=True),   # JSON
        sa.Column('glory_multiplier', sa.Float(), nullable=True, server_default='1'),
    )

    # ── SUBSCRIPTIONS ────────────────────────────────────────────────────────
    op.create_table('subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('plans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(30), nullable=True, server_default='active'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),       # stripe|mercadopago|manual
        sa.Column('external_id', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── PAYMENTS ─────────────────────────────────────────────────────────────
    op.create_table('payments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', sa.Integer(), sa.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(5), nullable=True, server_default='BRL'),
        sa.Column('status', sa.String(30), nullable=True),  # pending|paid|failed|refunded
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('external_id', sa.String(200), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── GLORY POINTS LOG ─────────────────────────────────────────────────────
    op.create_table('glory_points_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(50), nullable=True),   # quiz|post|login|streak
        sa.Column('description', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── RANKS ────────────────────────────────────────────────────────────────
    op.create_table('glory_ranks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('slug', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('min_points', sa.Integer(), nullable=False),
        sa.Column('max_points', sa.Integer(), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('badge_icon', sa.String(10), nullable=True),
    )

    # ── QUIZZES ──────────────────────────────────────────────────────────────
    op.create_table('quizzes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),  # news|politicians|constitution|community
        sa.Column('difficulty', sa.String(20), nullable=True, server_default='medium'),
        sa.Column('source_type', sa.String(30), nullable=True),
        sa.Column('source_id', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── QUIZ QUESTIONS ───────────────────────────────────────────────────────
    op.create_table('quiz_questions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('quiz_id', sa.Integer(), sa.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('options', sa.Text(), nullable=False),       # JSON array of 4 strings
        sa.Column('correct_index', sa.Integer(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True, server_default='10'),
    )

    # ── QUIZ ATTEMPTS ────────────────────────────────────────────────────────
    op.create_table('quiz_attempts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('quiz_id', sa.Integer(), sa.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('time_sec', sa.Integer(), nullable=True),
        sa.Column('answers', sa.Text(), nullable=True),        # JSON: [0, 2, 1, 3, ...]
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('user_id', 'quiz_id', name='uq_quiz_attempt'),
    )

    # ── SEED: glory ranks ─────────────────────────────────────────────────────
    glory_ranks_table = sa.table('glory_ranks',
        sa.column('slug', sa.String),
        sa.column('name', sa.String),
        sa.column('min_points', sa.Integer),
        sa.column('max_points', sa.Integer),
        sa.column('color', sa.String),
        sa.column('badge_icon', sa.String),
    )
    op.bulk_insert(glory_ranks_table, [
        {'slug': 'cidadao',     'name': 'Cidadão Comum',      'min_points': 0,     'max_points': 499,   'color': '#6B7280', 'badge_icon': '👤'},
        {'slug': 'consciente',  'name': 'Consciente',          'min_points': 500,   'max_points': 1999,  'color': '#10B981', 'badge_icon': '🌱'},
        {'slug': 'fiscal',      'name': 'Fiscal',              'min_points': 2000,  'max_points': 4999,  'color': '#3B82F6', 'badge_icon': '🔍'},
        {'slug': 'guardiao',    'name': 'Guardião',            'min_points': 5000,  'max_points': 14999, 'color': '#8B5CF6', 'badge_icon': '🛡️'},
        {'slug': 'sentinela',   'name': 'Sentinela',           'min_points': 15000, 'max_points': 49999, 'color': '#F59E0B', 'badge_icon': '⚔️'},
        {'slug': 'voz',         'name': 'Voz da República',    'min_points': 50000, 'max_points': None,  'color': '#66FCF1', 'badge_icon': '🎙️'},
    ])

    # ── SEED: vip plans ────────────────────────────────────────────────────────
    plans_table = sa.table('plans',
        sa.column('slug', sa.String),
        sa.column('name', sa.String),
        sa.column('price_monthly', sa.Float),
        sa.column('price_yearly', sa.Float),
        sa.column('glory_multiplier', sa.Float),
        sa.column('features', sa.String),
    )
    op.bulk_insert(plans_table, [
        {'slug': 'free', 'name': 'Gratuito',     'price_monthly': 0,     'price_yearly': 0,      'glory_multiplier': 1.0,  'features': '{"quiz_daily":10,"badge":null}'},
        {'slug': 'vip1', 'name': 'Cidadão VIP',  'price_monthly': 9.90,  'price_yearly': 99.00,  'glory_multiplier': 2.0,  'features': '{"quiz_daily":30,"badge":"prata","border":true}'},
        {'slug': 'vip2', 'name': 'Guardião',     'price_monthly': 24.90, 'price_yearly': 249.00, 'glory_multiplier': 5.0,  'features': '{"quiz_daily":100,"badge":"ouro","border":true,"themes":true}'},
        {'slug': 'vip3', 'name': 'Sentinela',    'price_monthly': 49.90, 'price_yearly': 499.00, 'glory_multiplier': 10.0, 'features': '{"quiz_daily":999,"badge":"diamante","border":true,"themes":true,"support":true}'},
    ])

    # ── SEED: news categories ──────────────────────────────────────────────────
    news_cats_table = sa.table('news_categories',
        sa.column('slug', sa.String),
        sa.column('label', sa.String),
        sa.column('color', sa.String),
    )
    op.bulk_insert(news_cats_table, [
        {'slug': 'politics', 'label': 'Política',    'color': '#EF4444'},
        {'slug': 'economy',  'label': 'Economia',    'color': '#F59E0B'},
        {'slug': 'world',    'label': 'Mundo',       'color': '#3B82F6'},
        {'slug': 'tech',     'label': 'Tecnologia',  'color': '#8B5CF6'},
        {'slug': 'society',  'label': 'Sociedade',   'color': '#10B981'},
        {'slug': 'sports',   'label': 'Esportes',    'color': '#F97316'},
        {'slug': 'health',   'label': 'Saúde',       'color': '#06B6D4'},
    ])

def downgrade():
    op.drop_table('quiz_attempts')
    op.drop_table('quiz_questions')
    op.drop_table('quizzes')
    op.drop_table('glory_ranks')
    op.drop_table('glory_points_log')
    op.drop_table('payments')
    op.drop_table('subscriptions')
    op.drop_table('plans')
    op.drop_table('news_comments')
    op.drop_table('news_votes')
    op.drop_table('news_articles')
    op.drop_table('news_categories')
    op.drop_table('news_sources')
    op.drop_table('political_parties')
    op.drop_table('politician_votes')
    op.drop_table('politician_expenses')
    op.drop_table('politician_terms')
    op.drop_table('politicians')
    op.drop_table('message_reactions')
    op.drop_table('presence')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('rank_slug')
        batch_op.drop_column('plan')
        batch_op.drop_column('glory_points')
