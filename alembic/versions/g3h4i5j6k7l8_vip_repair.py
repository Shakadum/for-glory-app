"""vip repair — garante colunas vip_border e vip_name_color existem

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'g3h4i5j6k7l8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.scalar() > 0


def upgrade():
    if not _column_exists('users', 'vip_border'):
        op.add_column('users', sa.Column('vip_border', sa.String(20),
                                          nullable=True, server_default='none'))
    if not _column_exists('users', 'vip_name_color'):
        op.add_column('users', sa.Column('vip_name_color', sa.String(10),
                                          nullable=True))


def downgrade():
    pass
