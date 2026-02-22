from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from app.db.base import Base

# Many-to-many friendship relation (symmetric via mirrored inserts in services)
friendship = Table(
    'friendships',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('friend_id', Integer, ForeignKey('users.id'), primary_key=True),
)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)

    xp = Column(Integer, default=0)
    avatar_url = Column(
        String,
        default='https://ui-avatars.com/api/?name=Soldado&background=1f2833&color=66fcf1&bold=true',
    )
    cover_url = Column(
        String,
        default='https://placehold.co/600x200/0b0c10/66fcf1?text=FOR+GLORY',
    )
    bio = Column(String, default='Recruta do For Glory')

    is_invisible = Column(Integer, default=0)
    role = Column(String, default='membro')

    friends = relationship(
        'User',
        secondary=friendship,
        primaryjoin=id == friendship.c.user_id,
        secondaryjoin=id == friendship.c.friend_id,
        backref='friended_by',
    )


class FriendRequest(Base):
    __tablename__ = 'friend_requests'

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    receiver_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)

    sender = relationship('User', foreign_keys=[sender_id])


class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    content_url = Column(String)
    media_type = Column(String)
    caption = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    author = relationship('User')


class Like(Base):
    __tablename__ = 'likes'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    post_id = Column(Integer, ForeignKey('posts.id'))


class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    post_id = Column(Integer, ForeignKey('posts.id'))
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    author = relationship('User')


class PrivateMessage(Base):
    __tablename__ = 'private_messages'

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    receiver_id = Column(Integer, ForeignKey('users.id'))
    content = Column(String)
    is_read = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sender = relationship('User', foreign_keys=[sender_id])


class ChatGroup(Base):
    __tablename__ = 'chat_groups'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)


class GroupMember(Base):
    __tablename__ = 'group_members'

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey('chat_groups.id'))
    user_id = Column(Integer, ForeignKey('users.id'))


class GroupMessage(Base):
    __tablename__ = 'group_messages'

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey('chat_groups.id'))
    sender_id = Column(Integer, ForeignKey('users.id'))
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sender = relationship('User', foreign_keys=[sender_id])


class Community(Base):
    __tablename__ = 'communities'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    avatar_url = Column(String)
    banner_url = Column(String, default='')
    is_private = Column(Integer, default=0)
    creator_id = Column(Integer, ForeignKey('users.id'))


class CommunityMember(Base):
    __tablename__ = 'community_members'

    id = Column(Integer, primary_key=True, index=True)
    comm_id = Column(Integer, ForeignKey('communities.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    role = Column(String, default='member')

    user = relationship('User')


class CommunityChannel(Base):
    __tablename__ = 'community_channels'

    id = Column(Integer, primary_key=True, index=True)
    comm_id = Column(Integer, ForeignKey('communities.id'))
    name = Column(String)
    channel_type = Column(String, default='livre')
    banner_url = Column(String, default='')
    is_private = Column(Integer, default=0)


class CommunityMessage(Base):
    __tablename__ = 'community_messages'

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey('community_channels.id'))
    sender_id = Column(Integer, ForeignKey('users.id'))
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sender = relationship('User', foreign_keys=[sender_id])


class CommunityRequest(Base):
    __tablename__ = 'community_requests'

    id = Column(Integer, primary_key=True, index=True)
    comm_id = Column(Integer, ForeignKey('communities.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', foreign_keys=[user_id])


class CallBackground(Base):
    __tablename__ = 'call_backgrounds'

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String, index=True)
    target_id = Column(String, index=True)
    bg_url = Column(String)


class UserConfig(Base):
    __tablename__ = 'user_configs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    target_type = Column(String)
    target_id = Column(String)
    wallpaper_url = Column(String, default='')
