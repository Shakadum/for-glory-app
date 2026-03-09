"""vip repair — garante colunas vip_border e vip_name_color existem

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

revision = 'g3h4i5j6k7l8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def _add_if_missing(table, column_name, column_def):
    """Tenta adicionar coluna; ignora se já existir."""
    try:
        op.add_column(table, column_def)
    except Exception:
        pass  # Coluna já existe — OK


def upgrade():
    _add_if_missing('users', 'vip_border',
        sa.Column('vip_border', sa.String(20), nullable=True, server_default='none'))
    _add_if_missing('users', 'vip_name_color',
        sa.Column('vip_name_color', sa.String(10), nullable=True))


def downgrade():
    pass  # Não remove em downgrade — repair não reverte
