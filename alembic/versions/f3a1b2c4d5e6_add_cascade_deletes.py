"""add cascade deletes

Revision ID: f3a1b2c4d5e6
Revises: 822fae71bc5a
Create Date: 2026-02-25 00:00:00.000000

NOTE: PostgreSQL suporta ALTER TABLE ... ADD/DROP CONSTRAINT para mudar
comportamento de ON DELETE. Aqui recriamos as constraints que precisam de CASCADE.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = "f3a1b2c4d5e6"
down_revision = "822fae71bc5a"
branch_labels = None
depends_on = None

# Mapeamento: (tabela, coluna, fk_name_antiga, referencia, acao)
CASCADE_CHANGES = [
    # friendships
    ("friendships", "user_id",   "friendships_user_id_fkey",   "users.id"),
    ("friendships", "friend_id", "friendships_friend_id_fkey", "users.id"),
    # friend_requests
    ("friend_requests", "sender_id",   "friend_requests_sender_id_fkey",   "users.id"),
    ("friend_requests", "receiver_id", "friend_requests_receiver_id_fkey", "users.id"),
    # posts
    ("posts", "user_id", "posts_user_id_fkey", "users.id"),
    # likes
    ("likes", "user_id", "likes_user_id_fkey", "users.id"),
    ("likes", "post_id", "likes_post_id_fkey", "posts.id"),
    # comments
    ("comments", "user_id", "comments_user_id_fkey", "users.id"),
    ("comments", "post_id", "comments_post_id_fkey", "posts.id"),
    # private_messages
    ("private_messages", "sender_id",   "private_messages_sender_id_fkey",   "users.id"),
    ("private_messages", "receiver_id", "private_messages_receiver_id_fkey", "users.id"),
    # group_members
    ("group_members", "group_id", "group_members_group_id_fkey", "chat_groups.id"),
    ("group_members", "user_id",  "group_members_user_id_fkey",  "users.id"),
    # group_messages
    ("group_messages", "group_id",   "group_messages_group_id_fkey",   "chat_groups.id"),
    ("group_messages", "sender_id",  "group_messages_sender_id_fkey",  "users.id"),
    # community_members
    ("community_members", "comm_id",  "community_members_comm_id_fkey",  "communities.id"),
    ("community_members", "user_id",  "community_members_user_id_fkey",  "users.id"),
    # community_channels
    ("community_channels", "comm_id", "community_channels_comm_id_fkey", "communities.id"),
    # community_messages
    ("community_messages", "channel_id", "community_messages_channel_id_fkey", "community_channels.id"),
    ("community_messages", "sender_id",  "community_messages_sender_id_fkey",  "users.id"),
    # community_requests
    ("community_requests", "comm_id",  "community_requests_comm_id_fkey",  "communities.id"),
    ("community_requests", "user_id",  "community_requests_user_id_fkey",  "users.id"),
    # user_configs
    ("user_configs", "user_id", "user_configs_user_id_fkey", "users.id"),
]


def upgrade() -> None:
    for table, col, fk_name, ref in CASCADE_CHANGES:
        ref_table, ref_col = ref.split(".")
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.create_foreign_key(
            fk_name, table, ref_table, [col], [ref_col], ondelete="CASCADE"
        )

    # creator_id vira SET NULL (comunidade sobrevive à exclusão do criador)
    op.drop_constraint("communities_creator_id_fkey", "communities", type_="foreignkey")
    op.alter_column("communities", "creator_id", nullable=True)
    op.create_foreign_key(
        "communities_creator_id_fkey", "communities", "users",
        ["creator_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    # Reverte tudo para FK simples sem CASCADE
    for table, col, fk_name, ref in CASCADE_CHANGES:
        ref_table, ref_col = ref.split(".")
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.create_foreign_key(fk_name, table, ref_table, [col], [ref_col])

    op.drop_constraint("communities_creator_id_fkey", "communities", type_="foreignkey")
    op.create_foreign_key(
        "communities_creator_id_fkey", "communities", "users", ["creator_id"], ["id"]
    )
