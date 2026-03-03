"""add politician_ratings table

Revision ID: a1b2c3d4e5f6
Revises: f3a1b2c4d5e6
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f3a1b2c4d5e6'  # ajuste para o revision mais recente do seu projeto
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'politician_ratings',
        sa.Column('id',            sa.Integer, primary_key=True, index=True),
        sa.Column('politician_id', sa.String(100), nullable=False, index=True),
        sa.Column('user_id',       sa.Integer, nullable=False, index=True),
        sa.Column('score',         sa.Integer, nullable=False),
        sa.Column('comment',       sa.Text, nullable=True),
        sa.Column('created_at',    sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table('politician_ratings')
