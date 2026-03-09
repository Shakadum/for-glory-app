"""vip_perks — bordas, cor do nome, meses acumulados

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    # Novos campos no User
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('vip_border',     sa.String(20),  nullable=True, server_default='none'))
        batch.add_column(sa.Column('vip_name_color', sa.String(10),  nullable=True))

    # Tabela VipPerk
    op.create_table(
        'vip_perks',
        sa.Column('id',                      sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id',                 sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('total_vip_months',        sa.Integer(), server_default='0'),
        sa.Column('gold_border_unlocked',    sa.Integer(), server_default='0'),
        sa.Column('gold_border_unlocked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('annual_sub_unlocked',     sa.Integer(), server_default='0'),
        sa.Column('updated_at',              sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_vip_perks_user_id', 'vip_perks', ['user_id'])


def downgrade():
    op.drop_table('vip_perks')
    with op.batch_alter_table('users') as batch:
        batch.drop_column('vip_name_color')
        batch.drop_column('vip_border')
