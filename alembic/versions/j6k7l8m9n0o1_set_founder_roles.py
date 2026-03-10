"""set founder roles — Comando, Shakadum, Shay

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = 'j6k7l8m9n0o1'
down_revision = 'i5j6k7l8m9n0'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "UPDATE users SET role = 'fundador' "
        "WHERE username IN ('Comando', 'Shakadum', 'Shay')"
    ))


def downgrade():
    op.execute(sa.text(
        "UPDATE users SET role = 'membro' "
        "WHERE username IN ('Comando', 'Shakadum', 'Shay')"
    ))
