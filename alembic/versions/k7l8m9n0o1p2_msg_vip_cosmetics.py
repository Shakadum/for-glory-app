"""msg_vip_cosmetics — save border/bubble per message

Revision ID: k7l8m9n0o1p2
Revises: j6k7l8m9n0o1
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'k7l8m9n0o1p2'
down_revision = 'j6k7l8m9n0o1'
branch_labels = None
depends_on = None

TABLES = [
    ('private_messages',    'msg_vip_border'),
    ('private_messages',    'msg_vip_bubble'),
    ('group_messages',      'msg_vip_border'),
    ('group_messages',      'msg_vip_bubble'),
    ('community_messages',  'msg_vip_border'),
    ('community_messages',  'msg_vip_bubble'),
]

def upgrade():
    conn = op.get_bind()
    for table, col in TABLES:
        exists = conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ), {'t': table, 'c': col}).fetchone()
        if not exists:
            conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN {col} VARCHAR(20) DEFAULT 'none'"
            ))

def downgrade():
    conn = op.get_bind()
    for table, col in TABLES:
        exists = conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ), {'t': table, 'c': col}).fetchone()
        if exists:
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {col}"))
