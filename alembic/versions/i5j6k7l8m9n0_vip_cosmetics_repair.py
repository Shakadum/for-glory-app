"""vip cosmetics repair — garante colunas vip_bubble e vip_name_font

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'i5j6k7l8m9n0'
down_revision = 'h4i5j6k7l8m9'
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
    if not _column_exists('users', 'vip_bubble'):
        op.add_column('users', sa.Column('vip_bubble', sa.String(20),
                                           nullable=True, server_default='none'))
    if not _column_exists('users', 'vip_name_font'):
        op.add_column('users', sa.Column('vip_name_font', sa.String(50), nullable=True))
    # Garantir também as colunas anteriores por segurança
    if not _column_exists('users', 'vip_border'):
        op.add_column('users', sa.Column('vip_border', sa.String(20),
                                           nullable=True, server_default='none'))
    if not _column_exists('users', 'vip_name_color'):
        op.add_column('users', sa.Column('vip_name_color', sa.String(10), nullable=True))


def downgrade():
    pass
