"""encyclopedia viva — edits, votes, revisions, trust scores

Revision ID: e1f2a3b4c5d6
Revises: a1b2c3d4e5f6
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f2a3b4c5d6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'politician_edits',
        sa.Column('id',            sa.Integer(),     primary_key=True),
        sa.Column('politician_id', sa.String(100),   nullable=False, index=True),
        sa.Column('user_id',       sa.Integer(),     nullable=False, index=True),
        sa.Column('field',         sa.String(100),   nullable=False),
        sa.Column('old_value',     sa.Text(),        nullable=True),
        sa.Column('new_value',     sa.Text(),        nullable=False),
        sa.Column('reason',        sa.Text(),        nullable=True),
        sa.Column('status',        sa.String(20),    server_default='pending'),
        sa.Column('reviewed_by',   sa.Integer(),     nullable=True),
        sa.Column('reviewed_at',   sa.DateTime(),    nullable=True),
        sa.Column('review_note',   sa.Text(),        nullable=True),
        sa.Column('created_at',    sa.DateTime(),    server_default=sa.func.now()),
        sa.Column('updated_at',    sa.DateTime(),    server_default=sa.func.now()),
    )
    op.create_index('ix_pe_status', 'politician_edits', ['status'])

    op.create_table(
        'edit_sources',
        sa.Column('id',      sa.Integer(), primary_key=True),
        sa.Column('edit_id', sa.Integer(), sa.ForeignKey('politician_edits.id'), nullable=False, index=True),
        sa.Column('url',     sa.Text(),    nullable=True),
        sa.Column('label',   sa.String(300), nullable=True),
        sa.Column('kind',    sa.String(50),  nullable=True),
    )

    op.create_table(
        'edit_votes',
        sa.Column('id',      sa.Integer(), primary_key=True),
        sa.Column('edit_id', sa.Integer(), sa.ForeignKey('politician_edits.id'), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('value',   sa.Integer(), nullable=False),
        sa.UniqueConstraint('edit_id', 'user_id', name='uq_ev_edit_user'),
    )

    op.create_table(
        'politician_revisions',
        sa.Column('id',            sa.Integer(),    primary_key=True),
        sa.Column('politician_id', sa.String(100),  nullable=False, index=True),
        sa.Column('edit_id',       sa.Integer(),    sa.ForeignKey('politician_edits.id'), nullable=True),
        sa.Column('snapshot',      sa.Text(),       nullable=False),
        sa.Column('changed_field', sa.String(100),  nullable=True),
        sa.Column('changed_by',    sa.Integer(),    nullable=True),
        sa.Column('approved_by',   sa.Integer(),    nullable=True),
        sa.Column('created_at',    sa.DateTime(),   server_default=sa.func.now()),
    )

    op.create_table(
        'politician_trust_scores',
        sa.Column('id',               sa.Integer(),  primary_key=True),
        sa.Column('politician_id',    sa.String(100), nullable=False, index=True),
        sa.Column('score',            sa.Float(),    server_default='50'),
        sa.Column('source_score',     sa.Float(),    server_default='50'),
        sa.Column('community_score',  sa.Float(),    server_default='50'),
        sa.Column('data_score',       sa.Float(),    server_default='50'),
        sa.Column('approved_edits',   sa.Integer(),  server_default='0'),
        sa.Column('rejected_edits',   sa.Integer(),  server_default='0'),
        sa.Column('total_sources',    sa.Integer(),  server_default='0'),
        sa.Column('updated_at',       sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('politician_id', name='uq_pts_politician'),
    )


def downgrade():
    op.drop_table('politician_trust_scores')
    op.drop_table('politician_revisions')
    op.drop_table('edit_votes')
    op.drop_table('edit_sources')
    op.drop_table('politician_edits')
