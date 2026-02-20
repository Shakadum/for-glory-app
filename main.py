import uvicorn
import json
import hashlib
import random
import os
import logging
import threading
from typing import List
from fastapi import FastAPI, WebSocket, Request, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table, or_, and_, text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
import cloudinary.uploader
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jose import jwt, JWTError
from collections import Counter

# --- CONFIGURAÇÕES GERAIS E CHAVES ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForGlory")

SECRET_KEY = os.environ.get("SECRET_KEY", "sua_chave_secreta_super_segura_123")
AGORA_APP_ID = os.environ.get("AGORA_APP_ID", "") 
ALGORITHM = "HS256"

mail_conf = ConnectionConfig(
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "seu_email@gmail.com"),
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "sua_senha_app"),
    MAIL_FROM = os.environ.get("MAIL_FROM", "seu_email@gmail.com"),
    MAIL_PORT = 465,  
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = False, 
    MAIL_SSL_TLS = True,   
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

cloudinary.config(cloud_name=os.environ.get('CLOUDINARY_NAME'), api_key=os.environ.get('CLOUDINARY_KEY'), api_secret=os.environ.get('CLOUDINARY_SECRET'), secure=True)

# --- BANCO DE DADOS BLINDADO ---
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./for_glory_v6.db")

if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 20}, pool_size=15, max_overflow=30)
else:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_size=30, max_overflow=50, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

friendship = Table('friendships', Base.metadata, Column('user_id', Integer, ForeignKey('users.id'), primary_key=True), Column('friend_id', Integer, ForeignKey('users.id'), primary_key=True))

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    xp = Column(Integer, default=0)
    avatar_url = Column(String, default="https://ui-avatars.com/api/?name=Soldado&background=1f2833&color=66fcf1&bold=true")
    cover_url = Column(String, default="https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY")
    bio = Column(String, default="Recruta do For Glory")
    is_invisible = Column(Integer, default=0) 
    role = Column(String, default="membro") 
    friends = relationship("User", secondary=friendship, primaryjoin=id==friendship.c.user_id, secondaryjoin=id==friendship.c.friend_id, backref="friended_by")

class FriendRequest(Base):
    __tablename__ = "friend_requests"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", foreign_keys=[sender_id])

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content_url = Column(String)
    media_type = Column(String)
    caption = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    author = relationship("User")

class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    author = relationship("User")

class PrivateMessage(Base):
    __tablename__ = "private_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    is_read = Column(Integer, default=0) 
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", foreign_keys=[sender_id])

class ChatGroup(Base):
    __tablename__ = "chat_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("chat_groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

class GroupMessage(Base):
    __tablename__ = "group_messages"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("chat_groups.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", foreign_keys=[sender_id])

class Community(Base):
    __tablename__ = "communities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    avatar_url = Column(String)
    is_private = Column(Integer, default=0) 
    creator_id = Column(Integer, ForeignKey("users.id"))

class CommunityMember(Base):
    __tablename__ = "community_members"
    id = Column(Integer, primary_key=True, index=True)
    comm_id = Column(Integer, ForeignKey("communities.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String, default="member") 
    user = relationship("User")

class CommunityChannel(Base):
    __tablename__ = "community_channels"
    id = Column(Integer, primary_key=True, index=True)
    comm_id = Column(Integer, ForeignKey("communities.id"))
    name = Column(String)
    channel_type = Column(String, default="livre") 
    is_private = Column(Integer, default=0) 

class CommunityMessage(Base):
    __tablename__ = "community_messages"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("community_channels.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", foreign_keys=[sender_id])

class CommunityRequest(Base):
    __tablename__ = "community_requests"
    id = Column(Integer, primary_key=True, index=True)
    comm_id = Column(Integer, ForeignKey("communities.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", foreign_keys=[user_id])

try: Base.metadata.create_all(bind=engine)
except Exception as e: logger.error(f"Erro BD: {e}")

# --- SISTEMA DE CARREIRA MILITAR ---
def get_user_badges(xp, user_id, role):
    tiers = [
        (0, "Recruta", 100, "#888888"), (100, "Soldado", 300, "#2ecc71"),
        (300, "Cabo", 600, "#27ae60"), (600, "3º Sargento", 1000, "#3498db"),
        (1000, "2º Sargento", 1500, "#2980b9"), (1500, "1º Sargento", 2500, "#9b59b6"),
        (2500, "Subtenente", 4000, "#8e44ad"), (4000, "Tenente", 6000, "#f1c40f"),
        (6000, "Capitão", 10000, "#f39c12"), (10000, "Major", 15000, "#e67e22"),
        (15000, "Tenente-Coronel", 25000, "#e74c3c"), (25000, "Coronel", 50000, "#c0392b"),
        (50000, "General ⭐", 50000, "#FFD700")
    ]
    rank = tiers[0][1]; color = tiers[0][3]; next_xp = tiers[0][2]; next_rank = tiers[1][1]
    
    for i, t in enumerate(tiers):
        if xp >= t[0]:
            rank = t[1]; color = t[3]; next_xp = t[2]
            next_rank = tiers[i+1][1] if i+1 < len(tiers) else "Nível Máximo"
            
    percent = int((xp / next_xp) * 100) if next_xp > xp else 100
    if percent > 100: percent = 100

    special_emblem = ""
    if user_id == 1 or role == "fundador": special_emblem = "💎 Fundador"
    elif role == "admin": special_emblem = "🛡️ Admin"
    elif role == "vip": special_emblem = "🌟 VIP"

    medals = []
    all_medals = [
        {"icon": "🩸", "name": "1º Sangue", "desc": "Completou a 1ª Missão", "req": 50},
        {"icon": "🥈", "name": "Veterano", "desc": "Alcançou 500 XP", "req": 500},
        {"icon": "🥇", "name": "Elite", "desc": "Alcançou 2.000 XP", "req": 2000},
        {"icon": "🏆", "name": "Estrategista", "desc": "Alcançou 10.000 XP", "req": 10000},
        {"icon": "⭐", "name": "Supremo", "desc": "Tornou-se General", "req": 50000}
    ]
    
    if user_id == 1 or role == "fundador": medals.append({"icon": "💎", "name": "A Gênese", "desc": "Criador da Plataforma", "earned": True, "missing": 0})
    for m in all_medals:
        earned = xp >= m['req']
        missing = m['req'] - xp if not earned else 0
        medals.append({"icon": m['icon'], "name": m['name'], "desc": m['desc'], "earned": earned, "missing": missing})

    return {"rank": rank, "color": color, "next_xp": next_xp, "next_rank": next_rank, "percent": percent, "special_emblem": special_emblem, "medals": medals}

def get_utc_iso(dt): return dt.isoformat() + "Z" if dt else ""
def create_reset_token(email: str): return jwt.encode({"sub": email, "exp": datetime.utcnow() + timedelta(minutes=30), "type": "reset"}, SECRET_KEY, algorithm=ALGORITHM)
def verify_reset_token(token: str):
    try:
        p = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return p.get("sub") if p.get("type") == "reset" else None
    except JWTError: return None

class ConnectionManager:
    def __init__(self):
        self.active = {}
        self.user_connections = {}
    async def connect(self, ws: WebSocket, chan: str, uid: int):
        await ws.accept()
        if chan not in self.active: self.active[chan] = []
        self.active[chan].append(ws)
        self.user_connections[uid] = self.user_connections.get(uid, 0) + 1
    def disconnect(self, ws: WebSocket, chan: str, uid: int):
        if chan in self.active and ws in self.active[chan]: self.active[chan].remove(ws)
        if uid in self.user_connections:
            self.user_connections[uid] -= 1
            if self.user_connections[uid] <= 0: del self.user_connections[uid]
    async def broadcast(self, msg: dict, chan: str):
        for conn in self.active.get(chan, []):
            try: await conn.send_text(json.dumps(msg))
            except: pass

manager = ConnectionManager()

# --- INSTANCIAÇÃO DO APP (MUITO IMPORTANTE FICAR AQUI) ---
app = FastAPI(title="For Glory Cloud")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

class LoginData(BaseModel): username: str; password: str
class RegisterData(BaseModel): username: str; email: str; password: str
class FriendReqData(BaseModel): target_id: int; sender_id: int = 0
class RequestActionData(BaseModel): request_id: int; action: str
class DeletePostData(BaseModel): post_id: int; user_id: int
class ForgotPasswordData(BaseModel): email: EmailStr
class ResetPasswordData(BaseModel): token: str; new_password: str
class CommentData(BaseModel): user_id: int; post_id: int; text: str
class DelCommentData(BaseModel): comment_id: int; user_id: int
class CreateGroupData(BaseModel): name: str; creator_id: int; member_ids: List[int]
class ReadData(BaseModel): uid: int 
class JoinCommData(BaseModel): user_id: int; comm_id: int
class HandleCommReqData(BaseModel): req_id: int; action: str; admin_id: int

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- TÁTICA DE REPARO EM SEGUNDO PLANO (AGORA O APP EXISTE!) ---
@app.on_event("startup")
def startup_db_fix():
    def upgrade_db():
        try:
            if "sqlite" in str(engine.url):
                with engine.connect() as conn:
                    conn.execute(text("PRAGMA journal_mode=WAL;"))
                    conn.commit()
        except Exception: pass
        
        for query in ["ALTER TABLE users ADD COLUMN is_invisible INTEGER DEFAULT 0", "ALTER TABLE private_messages ADD COLUMN is_read INTEGER DEFAULT 0", "ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'membro'"]:
            try:
                with engine.connect() as conn:
                    if "postgres" in str(engine.url): conn.execute(text("SET statement_timeout = '3s'"))
                    conn.execute(text(query))
                    conn.commit()
            except Exception: pass
    threading.Thread(target=upgrade_db).start()

# --- FRONTEND (HTML/CSS/JS) ---
html_content = r"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Rajdhani:wght@600;700&display=swap" rel="stylesheet">
<script async defer src="https://download.agora.io/sdk/release/AgoraRTC_N-4.20.2.js"></script>
<title>For Glory</title>
<style>
:root{--primary:#66fcf1;--dark-bg:#0b0c10;--card-bg:#1f2833;--glass:rgba(31, 40, 51, 0.7);--border:rgba(102,252,241,0.15)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;scrollbar-width:thin;scrollbar-color:var(--primary) #111}
body{background-color:var(--dark-bg);background-image:radial-gradient(circle at 50% 0%, #1a1d26 0%, #0b0c10 70%);color:#e0e0e0;font-family:'Inter',sans-serif;margin:0;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
#app{display:flex;flex:1;overflow:hidden;position:relative}

#sidebar{width:80px;background:rgba(11,12,16,0.6);backdrop-filter:blur(12px);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:20px 0;z-index:100}
.nav-btn{width:50px;height:50px;border-radius:14px;border:none;background:transparent;color:#888;font-size:24px;margin-bottom:15px;cursor:pointer;transition:0.3s;position:relative; flex-shrink:0;}
.nav-btn.active{background:rgba(102,252,241,0.15);color:var(--primary);border:1px solid var(--border);box-shadow:0 0 15px rgba(102,252,241,0.2);transform:scale(1.05)}
.my-avatar-mini{width:45px;height:45px;border-radius:50%;object-fit:cover;border:2px solid var(--border); background:#111;}
.nav-badge { position:absolute; top:-2px; right:-2px; background:#ff5555; color:white; font-size:11px; font-weight:bold; padding:2px 6px; border-radius:10px; display:none; z-index:10; box-shadow:0 0 5px #ff5555; border:2px solid var(--dark-bg); }

#content-area{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden}
.view{display:none;flex:1;flex-direction:column;overflow-y:auto;height:100%;width:100%;padding-bottom:20px}
.view.active{display:flex;animation:fadeIn 0.3s ease-out}

.rank-badge{font-size: 9px; font-weight: bold; text-transform: uppercase; background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 6px; border: 1px solid; display: inline-block; margin-left: 4px; vertical-align: middle; line-height:1;}
.special-badge{font-size: 9px; color: #0b0c10; font-weight: bold; text-transform: uppercase; background: linear-gradient(45deg, #FFD700, #ff8c00); padding: 2px 6px; border-radius: 6px; display: inline-block; margin-left: 4px; vertical-align: middle; box-shadow: 0 0 5px rgba(255,165,0,0.5); line-height:1;}

#call-hud { display:none; position:fixed; bottom:90px; left:50%; transform:translateX(-50%); background:rgba(11,12,16,0.95); border:1px solid #2ecc71; border-radius:20px; padding:12px 20px; z-index:9999; align-items:center; gap:20px; box-shadow:0 10px 30px rgba(46,204,113,0.3); width:90%; max-width:350px; backdrop-filter:blur(10px); animation: scaleUp 0.3s ease-out; }
.call-btn-circle { background:#333; color:white; border:none; border-radius:50%; width:45px; height:45px; font-size:18px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:0.2s; }
.call-btn-circle:hover { transform:scale(1.1); }
.call-btn-circle.muted { background:#ffaa00; color:#000; box-shadow:0 0 10px rgba(255,170,0,0.5); }
.call-btn-hangup { background:#ff5555; color:white; border:none; border-radius:50%; width:45px; height:45px; font-size:22px; cursor:pointer; display:flex; align-items:center; justify-content:center; transform:rotate(135deg); transition:0.2s; box-shadow:0 0 10px rgba(255,85,85,0.5); }
.call-btn-hangup:hover { background:#cc0000; }

#feed-container{flex:1;overflow-y:auto;padding:20px 0;padding-bottom:100px;display:flex;flex-direction:column;align-items:center; gap:20px;}
.post-card{background:var(--card-bg);width:100%;max-width:480px;border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.05); overflow:hidden; display:flex; flex-direction:column; flex-shrink:0;}
.post-header{padding:12px 15px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.2)}
.post-av{width:42px;height:42px;border-radius:50%;margin-right:12px;object-fit:cover;border:1px solid var(--primary); background:#111;}
.post-media-wrapper { width: 100%; background: #030405; display: flex; justify-content: center; align-items: center; border-top: 1px solid rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02); padding: 5px 0;}
.post-media { max-width: 100%; max-height: 65vh; object-fit: contain !important; display: block; }
.post-caption{padding:15px;color:#ccc;font-size:14px;line-height:1.5}

.av-wrap { position: relative; display: inline-block; cursor: pointer; margin:0;}
.status-dot { position: absolute; bottom: 0; right: 0; width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--card-bg); background: #555; transition: 0.3s; z-index: 5; }
.status-dot.online { background: #2ecc71; box-shadow: 0 0 5px #2ecc71; }
.status-dot-lg { width: 20px; height: 20px; border-width: 3px; bottom: 5px; right: 10px; border-color: var(--dark-bg); }

.post-actions { padding: 10px 15px; display: flex; gap: 20px; background:rgba(0,0,0,0.15); border-top: 1px solid rgba(255,255,255,0.02); }
.action-btn { background: none; border: none; color: #888; font-size: 16px; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: 0.2s; font-family:'Inter', sans-serif;}
.action-btn.liked { color: #ff5555; }
.action-btn:hover { color: var(--primary); transform: scale(1.05); }

.comments-section { display: none; padding: 15px; background: rgba(0,0,0,0.3); border-top: 1px solid rgba(255,255,255,0.05); }
.comment-row { display: flex; gap: 10px; margin-bottom: 12px; font-size: 13px; animation: fadeIn 0.3s; align-items:flex-start; }
.comment-av { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; border: 1px solid #444; cursor:pointer; }

.styled-select { appearance: none; background: rgba(255,255,255,0.05) url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%2366fcf1%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E") no-repeat right 15px top 50%; background-size: 12px auto; border: 1px solid #444; border-radius: 12px; color: white; padding: 14px 40px 14px 15px; font-size: 15px; width: 100%; margin-bottom: 10px; cursor: pointer; transition: 0.3s; }
.styled-select:focus { border-color: var(--primary); outline: none; box-shadow: 0 0 10px rgba(102,252,241,0.2); }
.styled-select option { background: var(--dark-bg); color: white; padding: 10px; }

.chat-input-area, .comment-input-area { display: flex; gap: 8px; align-items: center; border-top: 1px solid var(--border); flex-wrap: nowrap; width: 100%; box-sizing: border-box; padding:15px; background:rgba(11,12,16,0.95); flex-shrink:0;}
.chat-msg, .comment-inp { flex: 1; min-width: 0; background: rgba(255,255,255,0.05); border: 1px solid #444; border-radius: 20px; padding: 12px 15px; color: white; outline: none; font-size: 14px; transition:0.3s;}
.chat-msg:focus, .comment-inp:focus { border-color: var(--primary); }
.chat-msg:disabled { opacity:0.8; background:rgba(255,85,85,0.1); cursor:not-allowed; border-color: #ff5555; color: #ff5555; font-weight:bold;}
.btn-send-msg { background: var(--primary); border: none; flex: 0 0 45px !important; width: 45px !important; height: 45px !important; border-radius: 12px; font-weight: bold; color: #0b0c10; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0; margin: 0; }
.icon-btn { background: none; border: none; font-size: 22px; cursor: pointer; color: #888; flex: 0 0 35px; padding: 0; display: flex; align-items: center; justify-content: center; margin: 0; transition:0.2s;}
.icon-btn.recording { color: #ff5555; animation: pulse 1s infinite; transform: scale(1.2); }

#dm-list, #comm-chat-list {flex:1;overflow-y:auto;padding:15px;display:flex;flex-direction:column;gap:12px}
.msg-row{display:flex;gap:10px;max-width:85%; animation: fadeIn 0.2s ease-out;}
.msg-row.mine{align-self:flex-end;flex-direction:row-reverse}
.msg-av{width:36px;height:36px;border-radius:50%;object-fit:cover; background:#111; cursor:pointer;}
.msg-bubble{padding:10px 16px;border-radius:18px;background:#2b343f;color:#e0e0e0;word-break:break-word;font-size:15px; position:relative; min-width:80px;}
.msg-row.mine .msg-bubble{background:linear-gradient(135deg,#1d4e4f,#133638);color:white;border:1px solid rgba(102,252,241,0.2)}
.del-msg-btn { font-size:12px; cursor:pointer; color:#ff5555; opacity:0.6; position:absolute; bottom:-15px; right:5px; transition:0.2s; }
.del-msg-btn:hover { opacity:1; transform:scale(1.2); }
.msg-time { display:block; font-size:10px; color:rgba(255,255,255,0.5); text-align:right; margin-top:4px; font-family:'Inter', sans-serif;}
.msg-deleted { font-style: italic; color: #ffaa00; background: rgba(255,170,0,0.1); padding: 5px 10px; border-radius: 8px; font-size: 13px; display: inline-block; border: 1px dashed rgba(255,170,0,0.5); }

.chat-box-centered { width: 100%; max-width: 600px; height: 85vh; margin: auto; background: var(--card-bg); border-radius: 16px; border: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }

.comm-card { background:rgba(0,0,0,0.4); border:1px solid #444; border-radius:16px; padding:20px 15px; text-align:center; cursor:pointer; transition:0.3s; display:flex; flex-direction:column; align-items:center; box-shadow:0 4px 15px rgba(0,0,0,0.2); position:relative; overflow:hidden;}
.comm-card:hover { border-color:var(--primary); transform:translateY(-5px); box-shadow:0 8px 25px rgba(102,252,241,0.15); }
.comm-avatar { width:70px; height:70px; border-radius:20px; object-fit:cover; margin-bottom:12px; border:2px solid #555; }
.comm-layout { flex-direction:column; height:100%; background:var(--dark-bg); overflow:hidden;}
.comm-topbar { padding: 15px 20px; background: rgba(11,12,16,0.95); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 20px rgba(0,0,0,0.5); z-index: 10; gap:10px; }
#active-comm-name { font-size: 22px; text-transform: uppercase; color: var(--primary); font-family: 'Rajdhani', sans-serif; font-weight: bold; letter-spacing: 2px; flex:1; text-align:center; background: linear-gradient(90deg, transparent, rgba(102,252,241,0.1), transparent); padding: 5px 10px; border-radius: 20px; text-shadow: 0 0 10px rgba(102,252,241,0.3); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}

.comm-channels-bar { padding: 12px 15px; background: #0b0c10; display: flex; gap: 10px; overflow-x: auto; border-bottom: 1px solid rgba(255,255,255,0.05); }
.channel-btn { background: rgba(255,255,255,0.05); border: 1px solid #333; color: #aaa; padding: 8px 18px; border-radius: 20px; cursor: pointer; white-space: nowrap; font-weight: bold; font-family: 'Inter', sans-serif; font-size: 13px; transition: 0.3s; flex-shrink:0; }
.channel-btn:hover { background: rgba(102,252,241,0.1); color: white; }
.channel-btn.active { background: var(--primary); color: #0b0c10; border-color: var(--primary); box-shadow: 0 0 12px rgba(102,252,241,0.4); }

.profile-header-container{position:relative;width:100%;height:220px;margin-bottom:60px}
.profile-cover{width:100%;height:100%;object-fit:cover;opacity:0.9;mask-image:linear-gradient(to bottom,black 60%,transparent 100%); background:#111;}
.profile-pic-lg-wrap { position:absolute; bottom:-50px; left:50%; transform:translateX(-50%); z-index: 10; }
.profile-pic-lg { width:130px; height:130px; border-radius:50%; object-fit:cover; border:4px solid var(--dark-bg); box-shadow:0 0 25px rgba(102,252,241,0.3); cursor:pointer; background:#1f2833; display:block; }

.glass-btn { background: rgba(102, 252, 241, 0.08); border: 1px solid rgba(102, 252, 241, 0.3); color: var(--primary); padding: 12px 20px; border-radius: 12px; cursor: pointer; font-weight: bold; font-family: 'Inter', sans-serif; transition: 0.3s; text-transform: uppercase; font-size: 13px; letter-spacing: 1px; flex: 1; }
.glass-btn:hover { background: rgba(102, 252, 241, 0.15); box-shadow: 0 0 10px rgba(102,252,241,0.2); }
.danger-btn { color: #ff5555; border-color: rgba(255, 85, 85, 0.3); background: rgba(255, 85, 85, 0.08); width: 100%; margin-top: 20px; }
.danger-btn:hover { background: rgba(255, 85, 85, 0.2); box-shadow: 0 0 10px rgba(255,85,85,0.2); }
.search-glass { display: flex; background: rgba(0,0,0,0.4); border: 1px solid #333; border-radius: 15px; padding: 5px 15px; margin-bottom: 20px; width: 100%; align-items:center;}
.search-glass input { background: transparent; border: none; color: white; outline: none; flex: 1; padding: 10px 0; font-size: 15px; }

.btn-float{position:fixed;bottom:90px;right:25px;width:60px;height:60px;border-radius:50%;background:var(--primary);border:none;font-size:32px;box-shadow:0 4px 20px rgba(102,252,241,0.4);cursor:pointer;z-index:50;display:flex;align-items:center;justify-content:center;color:#0b0c10}
.modal{position:fixed;inset:0;background:rgba(0,0,0,0.95);z-index:9000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(15px)}
.modal-box{background:rgba(20,25,35,0.95);padding:30px;border-radius:24px;border:1px solid var(--border);width:90%;max-width:380px;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,0.8);animation:scaleUp 0.3s;max-height:90vh;overflow-y:auto; scrollbar-width:thin;}
.inp{width:100%;padding:14px;margin:10px 0;background:rgba(0,0,0,0.3);border:1px solid #444;color:white;border-radius:10px;text-align:center;font-size:16px}
.btn-main{width:100%;padding:14px;margin-top:15px;background:var(--primary);border:none;font-weight:700;border-radius:10px;cursor:pointer;font-size:16px;color:#0b0c10;text-transform:uppercase}
.btn-link{background:none;border:none;color:#888;text-decoration:underline;cursor:pointer;margin-top:15px;font-size:14px}

#toast{visibility:hidden;opacity:0;min-width:200px;background:var(--primary);color:#0b0c10;text-align:center;border-radius:50px;padding:12px 24px;position:fixed;z-index:9999;left:50%;top:30px;transform:translateX(-50%);font-weight:bold;transition:0.3s; box-shadow: 0 5px 20px rgba(102,252,241,0.5);}
#toast.show{visibility:visible;opacity:1; top:40px;}
.hidden{display:none !important}

@keyframes fadeIn{from{opacity:0;transform:scale(0.98)}to{opacity:1;transform:scale(1)}}
@keyframes scaleUp{from{transform:scale(0.8);opacity:0}to{transform:scale(1);opacity:1}}
@keyframes pulse{0%{opacity:1; transform:scale(1);} 50%{opacity:0.5; transform:scale(1.2);} 100%{opacity:1; transform:scale(1);}}

@media(max-width:768px){
    #app{flex-direction:column-reverse}
    #sidebar{width:100%;height:65px;flex-direction:row;justify-content:flex-start;gap:15px;padding:0 15px;border-top:1px solid var(--border);border-right:none;background:rgba(11,12,16,0.95);overflow-x:auto;overflow-y:hidden; white-space:nowrap; scrollbar-width:none; -webkit-overflow-scrolling:touch;}
    #sidebar::-webkit-scrollbar { display:none; }
    .nav-btn { margin-bottom: 0; margin-top: 7px; flex-shrink: 0;}
    .btn-float{bottom:80px}
    #call-hud { bottom: 85px; width:95%; padding:10px; }
    .glass-btn.btn-call-header { padding:6px 10px; font-size:11px; }
}
</style>
</head>
<body>
<div id="toast">Notificação</div>

<div id="lang-menu" style="position:absolute; top:15px; right:15px; z-index:9999;">
    <select id="lang-selector" onchange="changeLanguage(this.value)" style="background:rgba(0,0,0,0.6); color:white; border:1px solid var(--primary); border-radius:8px; padding:6px; outline:none; cursor:pointer;">
        <option value="pt">🇧🇷 PT</option><option value="en">🇺🇸 EN</option><option value="es">🇪🇸 ES</option>
    </select>
</div>

<div id="emoji-picker" style="position:absolute;bottom:80px;right:10px;width:90%;max-width:320px;background:rgba(20,25,35,0.95);border:1px solid var(--border);border-radius:15px;display:none;flex-direction:column;z-index:10001;box-shadow:0 0 25px rgba(0,0,0,0.8);backdrop-filter:blur(10px)">
    <div style="padding:10px 15px;display:flex;justify-content:space-between;border-bottom:1px solid #333"><span style="color:var(--primary);font-weight:bold;font-family:'Rajdhani'">EMOJIS</span><span onclick="toggleEmoji(true)" style="color:#ff5555;cursor:pointer;font-weight:bold">✕</span></div>
    <div id="emoji-grid" style="display:grid;grid-template-columns:repeat(7,1fr);gap:5px;padding:10px;max-height:220px;overflow-y:auto"></div>
</div>

<div id="call-hud">
    <div style="flex:1;">
        <div style="color:#2ecc71; font-size:12px; font-weight:bold; font-family:'Inter';"><span style="animation:pulse 1s infinite; display:inline-block;">🔴</span> <span id="call-hud-status">EM CHAMADA</span></div>
        <div id="call-hud-time" style="color:white; font-family:'Rajdhani'; font-size:18px;">00:00</div>
    </div>
    <button id="btn-mute-call" class="call-btn-circle" onclick="toggleMuteCall()">🎤</button>
    <button class="call-btn-hangup" onclick="leaveCall()">📞</button>
</div>

<div id="modal-login" class="modal">
    <div class="modal-box">
        <h1 style="color:var(--primary);font-family:'Rajdhani';font-size:42px;margin:0 0 10px 0" data-i18n="login_title">FOR GLORY</h1>
        <div id="login-form">
            <input id="l-user" class="inp" placeholder="CODINOME" data-i18n="codename">
            <input id="l-pass" class="inp" type="password" placeholder="SENHA" data-i18n="password" onkeypress="if(event.key==='Enter')doLogin()">
            <button onclick="doLogin()" class="btn-main" data-i18n="login">ENTRAR</button>
            <div style="margin-top:20px;display:flex;justify-content:space-between">
                <span onclick="toggleAuth('register')" class="btn-link" style="color:white;text-decoration:none;" data-i18n="create_acc">Criar Conta</span>
                <span onclick="toggleAuth('forgot')" class="btn-link" style="color:var(--primary);text-decoration:none;" data-i18n="forgot">Esqueci Senha</span>
            </div>
        </div>
        <div id="register-form" class="hidden">
            <input id="r-user" class="inp" placeholder="NOVO USUÁRIO" data-i18n="new_user">
            <input id="r-email" class="inp" placeholder="EMAIL" data-i18n="email_real">
            <input id="r-pass" class="inp" type="password" placeholder="SENHA" data-i18n="password">
            <button onclick="doRegister()" class="btn-main" data-i18n="enlist">ALISTAR-SE</button>
            <p onclick="toggleAuth('login')" class="btn-link" data-i18n="back">Voltar</p>
        </div>
        <div id="forgot-form" class="hidden">
            <h3 style="color:white" data-i18n="recover">RECUPERAR ACESSO</h3>
            <input id="f-email" class="inp" placeholder="SEU EMAIL" data-i18n="reg_email">
            <button onclick="requestReset()" class="btn-main" data-i18n="send_link">ENVIAR LINK</button>
            <p onclick="toggleAuth('login')" class="btn-link" data-i18n="back">Voltar</p>
        </div>
        <div id="reset-form" class="hidden">
            <h3 style="color:var(--primary)" data-i18n="new_pass_title">NOVA SENHA</h3>
            <input id="new-pass" class="inp" type="password" placeholder="NOVA SENHA" data-i18n="new_pass">
            <button onclick="doResetPassword()" class="btn-main" data-i18n="save_pass">SALVAR SENHA</button>
        </div>
    </div>
</div>

<div id="modal-delete" class="modal hidden"><div class="modal-box" style="border-color: rgba(255, 85, 85, 0.3);"><h2 style="color:#ff5555; font-family:'Rajdhani'; margin-top:0;" data-i18n="confirm_action">CONFIRMAR AÇÃO</h2><p style="color:#ccc; margin: 15px 0; font-size:15px;" data-i18n="confirm_del">Tem certeza que deseja apagar isto?</p><div style="display:flex; gap:10px; margin-top:20px;"><button id="btn-confirm-delete" class="btn-main" style="background:#ff5555; color:white; margin-top:0;" data-i18n="delete">APAGAR</button><button onclick="document.getElementById('modal-delete').classList.add('hidden')" class="btn-main" style="background:transparent; border:1px solid #444; color:#888; margin-top:0;" data-i18n="cancel">CANCELAR</button></div></div></div>

<div id="modal-create-comm" class="modal hidden"><div class="modal-box"><h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;" data-i18n="new_base">NOVA BASE OFICIAL</h2><input type="file" id="comm-avatar-upload" class="inp" accept="image/*" title="Avatar da Base"><input id="new-comm-name" class="inp" placeholder="Nome" data-i18n="base_name"><input id="new-comm-desc" class="inp" placeholder="Desc" data-i18n="base_desc"><select id="new-comm-priv" class="styled-select"><option value="0" data-i18n="pub_base">🌍 Pública</option><option value="1" data-i18n="priv_base">🔒 Privada</option></select><button onclick="submitCreateComm(event)" class="btn-main" data-i18n="establish">ESTABELECER</button><button onclick="document.getElementById('modal-create-comm').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">CANCELAR</button></div></div>

<div id="modal-create-channel" class="modal hidden"><div class="modal-box"><h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;" data-i18n="new_channel">NOVO CANAL</h2><input id="new-ch-name" class="inp" placeholder="Nome" data-i18n="channel_name"><select id="new-ch-type" class="styled-select"><option value="livre" data-i18n="ch_free">💬 Livre</option><option value="text" data-i18n="ch_text">📝 Só Texto</option><option value="media" data-i18n="ch_media">🎬 Só Mídia</option></select><select id="new-ch-priv" class="styled-select"><option value="0" data-i18n="ch_pub">🌍 Público</option><option value="1" data-i18n="ch_priv">🔒 Privado</option></select><button onclick="submitCreateChannel()" class="btn-main" data-i18n="create_channel">CRIAR CANAL</button><button onclick="document.getElementById('modal-create-channel').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">CANCELAR</button></div></div>

<div id="modal-create-group" class="modal hidden"><div class="modal-box"><h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;" data-i18n="new_squad">NOVO ESQUADRÃO</h2><input id="new-group-name" class="inp" placeholder="Grupo" data-i18n="group_name"><p style="color:#888;font-size:12px;text-align:left;margin-bottom:5px;" data-i18n="select_allies">Selecione os aliados:</p><div id="group-friends-list" style="max-height:150px; overflow-y:auto; text-align:left; margin-bottom:15px; background:rgba(0,0,0,0.3); padding:10px; border-radius:10px;"></div><div style="display:flex; gap:10px;"><button onclick="submitCreateGroup()" class="btn-main" style="margin-top:0;" data-i18n="create">CRIAR</button><button onclick="document.getElementById('modal-create-group').classList.add('hidden')" class="btn-main" style="background:transparent; border:1px solid #444; color:#888; margin-top:0;" data-i18n="cancel">CANCELAR</button></div></div></div>

<div id="modal-upload" class="modal hidden"><div class="modal-box"><h2 style="color:white" data-i18n="new_post">NOVO POST</h2><input type="file" id="file-upload" class="inp" accept="image/*,video/*" style="margin-bottom: 5px;"><span style="color:#ffaa00; font-size:11px; display:block; text-align:left; padding-left:5px; font-weight:bold;">⚠️ Max 100MB</span><div style="display:flex;gap:5px;align-items:center;margin-bottom:10px;margin-top:10px"><input type="text" id="caption-upload" class="inp" placeholder="Legenda..." data-i18n="caption_placeholder" style="margin:0"><button type="button" class="icon-btn" onclick="openEmoji('caption-upload')">😀</button></div><div id="upload-progress" style="display:none;background:#333;height:6px;border-radius:3px;margin-top:10px;overflow:hidden"><div id="progress-bar" style="width:0%;height:100%;background:var(--primary);transition:width 0.2s"></div></div><div id="progress-text" style="color:var(--primary);font-size:12px;margin-top:5px;display:none;font-weight:bold">0%</div><button id="btn-pub" onclick="submitPost()" class="btn-main" data-i18n="publish">PUBLICAR (+50 XP)</button><button onclick="closeUpload()" class="btn-link" style="color:#888;display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">CANCELAR</button></div></div>

<div id="modal-profile" class="modal hidden"><div class="modal-box"><h2 style="color:var(--primary)" data-i18n="edit_profile">EDITAR PERFIL</h2><label style="color:#aaa;display:block;margin-top:10px;font-size:12px;">Avatar</label><input type="file" id="avatar-upload" class="inp" accept="image/*"><label style="color:#aaa;display:block;margin-top:10px;font-size:12px;">Cover</label><input type="file" id="cover-upload" class="inp" accept="image/*"><input id="bio-update" class="inp" placeholder="Bio" data-i18n="bio_placeholder"><button id="btn-save-profile" onclick="updateProfile()" class="btn-main" data-i18n="save">SALVAR</button><button onclick="document.getElementById('modal-profile').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">FECHAR</button></div></div>

<div id="modal-ranks" class="modal hidden">
    <div class="modal-box" style="max-height: 80vh; overflow-y: auto;">
        <h2 style="color:var(--primary); font-family:'Rajdhani';">📋 TODAS AS PATENTES</h2>
        <div id="ranks-list" style="display:flex; flex-direction:column; gap:10px; text-align:left; margin-top:15px;"></div>
        <button onclick="document.getElementById('modal-ranks').classList.add('hidden')" class="btn-main" style="margin-top:20px;" data-i18n="cancel">FECHAR</button>
    </div>
</div>

<div id="app">
    <div id="sidebar">
        <button id="nav-profile-btn" class="nav-btn" onclick="goView('profile', this)"><img id="nav-avatar" src="" class="my-avatar-mini" onerror="this.src='https://ui-avatars.com/api/?name=User&background=111&color=66fcf1'"></button>
        <button class="nav-btn" onclick="goView('inbox', this)" style="position:relative;">📩<div id="inbox-badge" class="nav-badge"></div></button>
        <button class="nav-btn" onclick="goView('feed', this)">🎬</button>
        <button class="nav-btn" onclick="goView('mycomms', this)">🛡️</button>
        <button class="nav-btn" onclick="goView('explore', this)">🌐</button>
        <button class="nav-btn" onclick="goView('history', this)">🕒</button>
    </div>
    <div id="content-area">
        <div id="view-profile" class="view">
            <div class="profile-header-container">
                <img id="p-cover" src="" class="profile-cover" onerror="this.src='https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY'">
                <div class="profile-pic-lg-wrap">
                    <img id="p-avatar" src="" class="profile-pic-lg" onclick="document.getElementById('modal-profile').classList.remove('hidden')" onerror="this.src='https://ui-avatars.com/api/?name=User&background=111&color=66fcf1'">
                    <div id="my-status-dot" class="status-dot status-dot-lg online"></div>
                </div>
            </div>
            <div style="text-align:center;margin-top:10px">
                <h2 id="p-name" style="color:white;font-family:'Rajdhani';font-size:28px;margin:5px 0;">...</h2>
                <div id="p-emblems" style="margin-bottom:10px;"></div>
                <p id="p-bio" style="color:#888;margin:10px 0 20px 0;font-style:italic;">...</p>
            </div>
            <div id="p-progression-box"></div>
            <div id="p-medals-box" style="text-align:center;"></div>
            <div style="width:90%; max-width:400px; margin:0 auto; text-align:center; border-top:1px solid #333; padding-top:20px;">
                <button id="btn-stealth" onclick="toggleStealth()" class="glass-btn" style="width:100%; margin-bottom:20px;" data-i18n="stealth_on">MODO FURTIVO</button>
                <div class="search-glass">
                    <input id="search-input" placeholder="Buscar..." data-i18n="search_soldier" onkeypress="if(event.key==='Enter')searchUsers()">
                    <button type="button" onclick="searchUsers()" style="background:none;border:none;color:var(--primary);font-size:18px;cursor:pointer;">🔍</button>
                    <button type="button" onclick="clearSearch()" style="background:none;border:none;color:#ff5555;font-size:18px;cursor:pointer;padding-left:10px;">✕</button>
                </div>
                <div id="search-results"></div>
                <div style="display:flex; gap:10px; margin-top:10px">
                    <button onclick="toggleRequests('requests')" class="glass-btn" data-i18n="requests">📩 Solicitações</button>
                    <button onclick="toggleRequests('friends')" class="glass-btn" data-i18n="friends">👥 Amigos</button>
                </div>
                <div id="requests-list" style="margin-top:15px; background:rgba(0,0,0,0.3); border-radius:10px;"></div>
                <button onclick="logout()" class="glass-btn danger-btn" style="margin-top:40px;" data-i18n="disconnect">DESCONECTAR</button>
            </div>
        </div>
        <div id="view-inbox" class="view">
            <div style="padding:15px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.2);border-bottom:1px solid rgba(255,255,255,0.05);">
                <div style="color:var(--primary);font-family:'Rajdhani';font-weight:bold;letter-spacing:2px;font-size:20px;" data-i18n="private_msgs">MENSAGENS PRIVADAS</div>
                <button onclick="openCreateGroupModal()" class="glass-btn" style="padding:8px 12px; margin:0; flex:none;" data-i18n="group_x1">+ GRUPO X1</button>
            </div>
            <div id="inbox-list" style="padding:15px; display:flex; flex-direction:column; gap:10px; overflow-y:auto; flex:1;"></div>
        </div>
        <div id="view-feed" class="view active">
            <div id="feed-container"></div>
            <button class="btn-float" onclick="document.getElementById('modal-upload').classList.remove('hidden')">+</button>
        </div>
        <div id="view-mycomms" class="view">
            <div style="padding:20px; background:rgba(0,0,0,0.3); border-bottom:1px solid #333; display:flex; justify-content:space-between; align-items:center;">
                <span style="color:white; font-family:'Rajdhani'; font-weight:bold; font-size:24px; letter-spacing:1px;" data-i18n="my_bases">🛡️ MINHAS BASES</span>
                <button class="glass-btn" style="margin:0; flex:none; padding:8px 15px;" onclick="document.getElementById('modal-create-comm').classList.remove('hidden')" data-i18n="create_base">+ CRIAR BASE</button>
            </div>
            <div style="padding:20px; flex:1; overflow-y:auto; text-align:center;">
                <div id="my-comms-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:15px; margin-bottom:40px;"></div>
            </div>
        </div>
        <div id="view-explore" class="view">
            <div style="padding:20px; background:rgba(0,0,0,0.3); border-bottom:1px solid #333; text-align:center;">
                <span style="color:var(--primary); font-family:'Rajdhani'; font-weight:bold; font-size:24px; letter-spacing:1px;" data-i18n="explore_bases">🌐 EXPLORAR BASES</span>
            </div>
            <div style="padding:20px; flex:1; overflow-y:auto; text-align:center;">
                <div class="search-glass" style="max-width:400px; margin:0 auto 20px auto;">
                    <input id="search-comm-input" placeholder="Buscar..." data-i18n="search_base" onkeypress="if(event.key==='Enter')searchComms()">
                    <button type="button" onclick="searchComms()" style="background:none;border:none;color:var(--primary);font-size:18px;cursor:pointer;">🔍</button>
                    <button type="button" onclick="clearCommSearch()" style="background:none;border:none;color:#ff5555;font-size:18px;cursor:pointer;padding-left:10px;">✕</button>
                </div>
                <div id="public-comms-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:15px; margin-bottom:40px;"></div>
            </div>
        </div>
        <div id="view-history" class="view">
            <div style="padding:20px; background:rgba(0,0,0,0.3); border-bottom:1px solid #333; text-align:center;">
                <span style="color:white; font-family:'Rajdhani'; font-weight:bold; font-size:24px; letter-spacing:1px;" data-i18n="my_history">🕒 MEU HISTÓRICO</span>
            </div>
            <div style="padding:20px; flex:1; overflow-y:auto; text-align:center;">
                <div id="my-posts-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:10px; margin:0 auto; max-width:800px;"></div>
            </div>
        </div>
        <div id="view-dm" class="view" style="justify-content:center; padding:15px; background:rgba(0,0,0,0.5);">
            <div class="chat-box-centered">
                <div style="padding:15px;display:flex;align-items:center;background:rgba(0,0,0,0.4);border-bottom:1px solid rgba(255,255,255,0.05); gap:10px;">
                    <button onclick="goView('inbox', document.querySelectorAll('.nav-btn')[1])" style="background:none;border:none;color:var(--primary);font-size:18px;cursor:pointer;">⬅</button>
                    <div id="dm-header-name" style="color:white;font-family:'Rajdhani';font-weight:bold;letter-spacing:1px;font-size:18px;flex:1;">Chat</div>
                    <button onclick="initCall()" class="glass-btn btn-call-header" style="flex:none; padding:8px 15px; border-color:#2ecc71; color:#2ecc71;">📞 CALL</button>
                </div>
                <div id="dm-list"></div>
                <form id="dm-input-area" class="chat-input-area" onsubmit="sendDM(); return false;">
                    <input type="file" id="dm-file" class="hidden" onchange="uploadDMImage()" accept="image/*,video/*,audio/*">
                    <button type="button" class="icon-btn" onclick="document.getElementById('dm-file').click()">📎</button>
                    <button type="button" class="icon-btn" id="btn-mic-dm" onclick="toggleRecord('dm')">🎤</button>
                    <input id="dm-msg" class="chat-msg" placeholder="Mensagem" data-i18n="msg_placeholder" autocomplete="off">
                    <button type="button" class="icon-btn" onclick="openEmoji('dm-msg')">😀</button>
                    <button type="submit" class="btn-send-msg">➤</button>
                </form>
            </div>
        </div>
        <div id="view-comm-dashboard" class="view comm-layout">
            <div class="comm-topbar">
                <button onclick="closeComm()" style="background:none;border:none;color:var(--primary);font-size:24px;cursor:pointer;">⬅</button>
                <div id="active-comm-name">NOME DA BASE</div>
                <button onclick="initCall()" class="glass-btn btn-call-header" style="flex:none; padding:8px 12px; border-color:#2ecc71; color:#2ecc71; margin-right:5px;">📞 CALL</button>
                <button onclick="showCommInfo()" class="glass-btn" style="padding:6px 12px; margin:0; flex:none; background:rgba(255,255,255,0.1); color:white; border-color:#555;">ℹ️</button>
            </div>
            <div class="comm-channels-bar" id="comm-channels-bar"></div>
            <div id="comm-chat-area" style="display:flex; flex-direction:column; flex:1; overflow:hidden;">
                <div id="comm-chat-list" style="flex:1; overflow-y:auto; padding:15px; display:flex; flex-direction:column; gap:12px;"></div>
                <form id="comm-input-form" class="chat-input-area" onsubmit="sendCommMsg(); return false;">
                    <input type="file" id="comm-file" class="hidden" onchange="uploadCommImage()" accept="image/*,video/*,audio/*">
                    <button type="button" id="btn-comm-clip" class="icon-btn" onclick="document.getElementById('comm-file').click()">📎</button>
                    <button type="button" id="btn-comm-mic" class="icon-btn" onclick="toggleRecord('comm')">🎤</button>
                    <input id="comm-msg" class="chat-msg" placeholder="Mensagem" data-i18n="base_msg_placeholder" autocomplete="off">
                    <button type="button" id="btn-comm-emoji" class="icon-btn" onclick="openEmoji('comm-msg')">😀</button>
                    <button type="submit" id="btn-comm-send" class="btn-send-msg">➤</button>
                </form>
            </div>
            <div id="comm-info-area" style="display:none; flex:1; overflow-y:auto; padding:30px; align-items:center; flex-direction:column;">
                <div style="background:var(--card-bg); border:1px solid #444; border-radius:20px; padding:30px; width:100%; max-width:500px; text-align:center; box-shadow:0 10px 30px rgba(0,0,0,0.5);">
                    <img id="c-info-av" src="" style="width:120px;height:120px;border-radius:24px;object-fit:cover;border:3px solid var(--primary);margin-bottom:15px;">
                    <h2 id="c-info-name" style="color:white;margin:0;font-family:'Rajdhani';font-size:32px;">...</h2>
                    <p id="c-info-desc" style="color:#aaa;font-size:15px;margin:10px 0 25px 0;">...</p>
                    <div id="c-info-admin-btn" style="margin-bottom:20px;"></div>
                    <div style="background:rgba(0,0,0,0.4); border-radius:16px; padding:20px; text-align:left;">
                        <h3 style="color:var(--primary); margin-top:0; border-bottom:1px solid #333; padding-bottom:10px;" data-i18n="base_members">Membros</h3>
                        <div id="c-info-members" style="display:flex; flex-direction:column; gap:12px; max-height:300px; overflow-y:auto; padding-right:5px;"></div>
                    </div>
                    <div id="c-info-requests-container" style="display:none; width:100%; margin-top:20px; background:rgba(0,0,0,0.4); border-radius:16px; padding:20px; text-align:left;">
                        <h3 style="color:orange; margin-top:0; border-bottom:1px solid #333; padding-bottom:10px;" data-i18n="entry_requests">Solicitações</h3>
                        <div id="c-info-requests" style="display:flex; flex-direction:column; gap:12px;"></div>
                    </div>
                    <div id="c-info-destroy-btn" style="margin-top:20px;"></div>
                </div>
            </div>
        </div>
        <div id="view-public-profile" class="view">
            <button onclick="goView('feed', document.querySelectorAll('.nav-btn')[2])" style="position:absolute;top:20px;left:20px;z-index:10;background:rgba(0,0,0,0.5);color:white;border:1px solid #444;padding:8px 15px;border-radius:8px;backdrop-filter:blur(5px);cursor:pointer;" data-i18n="back">⬅ Voltar</button>
            <div class="profile-header-container">
                <img id="pub-cover" src="" class="profile-cover" onerror="this.src='https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY'">
                <div class="profile-pic-lg-wrap">
                    <img id="pub-avatar" src="" class="profile-pic-lg" onerror="this.src='https://ui-avatars.com/api/?name=User&background=111&color=66fcf1'">
                    <div id="pub-status-dot" class="status-dot status-dot-lg"></div>
                </div>
            </div>
            <div style="text-align:center;margin-top:20px">
                <h2 id="pub-name" style="color:white;font-family:'Rajdhani';margin:5px 0;">...</h2>
                <div id="pub-emblems" style="margin-bottom:10px;"></div>
                <p id="pub-bio" style="color:#888;margin:10px 0 20px 0;">...</p>
                <div id="pub-medals-box" style="text-align:center;"></div>
                <div id="pub-actions" style="margin-bottom:20px; display:flex; justify-content:center; gap:10px;"></div>
                <div id="pub-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:2px;max-width:500px;margin:0 auto;"></div>
            </div>
        </div>
    </div>
</div>

<script>
const T = {
    'pt': {
        'login_title': 'FOR GLORY', 'login': 'ENTRAR', 'create_acc': 'Criar Conta', 'forgot': 'Esqueci Senha',
        'codename': 'CODINOME', 'password': 'SENHA', 'new_user': 'NOVO USUÁRIO', 'email_real': 'EMAIL (Real)', 'enlist': 'ALISTAR-SE', 'back': 'Voltar',
        'recover': 'RECUPERAR ACESSO', 'reg_email': 'SEU EMAIL CADASTRADO', 'send_link': 'ENVIAR LINK', 'new_pass_title': 'NOVA SENHA', 'new_pass': 'NOVA SENHA', 'save_pass': 'SALVAR SENHA',
        'confirm_action': 'CONFIRMAR AÇÃO', 'confirm_del': 'Tem certeza que deseja apagar isto?', 'delete': 'APAGAR', 'cancel': 'CANCELAR',
        'new_base': 'NOVA BASE OFICIAL', 'base_name': 'Nome da Base', 'base_desc': 'Descrição da Base', 'pub_base': '🌍 Pública', 'priv_base': '🔒 Privada', 'establish': 'ESTABELECER',
        'new_channel': 'NOVO CANAL', 'channel_name': 'Nome (Ex: avisos)', 'ch_free': '💬 Livre', 'ch_text': '📝 Só Texto', 'ch_media': '🎬 Só Mídia', 'ch_pub': '🌍 Público', 'ch_priv': '🔒 Privado (Só Admins)', 'create_channel': 'CRIAR CANAL',
        'new_squad': 'NOVO ESQUADRÃO', 'group_name': 'Nome do Grupo', 'select_allies': 'Selecione os aliados:', 'create': 'CRIAR',
        'new_post': 'NOVO POST', 'caption_placeholder': 'Legenda...', 'publish': 'PUBLICAR (+50 XP)',
        'edit_profile': 'EDITAR PERFIL', 'bio_placeholder': 'Escreva sua Bio...', 'save': 'SALVAR',
        'stealth_on': '🕵️ MODO FURTIVO: ATIVADO', 'stealth_off': '🟢 MODO FURTIVO: DESATIVADO', 'search_soldier': 'Buscar Soldado...', 'requests': '📩 Solicitações', 'friends': '👥 Amigos', 'disconnect': 'DESCONECTAR',
        'private_msgs': 'MENSAGENS PRIVADAS', 'group_x1': '+ GRUPO X1', 'my_bases': '🛡️ MINHAS BASES', 'create_base': '+ CRIAR BASE',
        'explore_bases': '🌐 EXPLORAR BASES', 'search_base': 'Buscar Base...', 'my_history': '🕒 MEU HISTÓRICO',
        'msg_placeholder': 'Mensagem secreta...', 'base_msg_placeholder': 'Mensagem para a base...',
        'at': 'às', 'deleted_msg': '🚫 Mensagem apagada', 'audio_proc': 'Processando...',
        'recording': '🔴 Gravando...', 'click_to_send': '(Clique no mic p/ enviar)',
        'empty_box': 'Sua caixa está vazia. Recrute aliados!', 'direct_msg': 'Mensagem Direta', 'squad': '👥 Esquadrão DM',
        'no_bases': 'Você ainda não tem bases.', 'no_bases_found': 'Nenhuma base encontrada.', 'no_history': 'Nenhuma missão registrada no Feed.',
        'request_join': '🔒 SOLICITAR', 'enter': '🌍 ENTRAR', 'ally': '✔ Aliado', 'sent': 'Enviado', 'accept_ally': 'Aceitar Aliado', 'recruit_ally': 'Recrutar Aliado',
        'creator': '👑 CRIADOR', 'admin': '🛡️ ADMIN', 'member': 'MEMBRO', 'promote': 'Promover',
        'base_members': 'Membros da Base', 'entry_requests': 'Solicitações de Entrada', 'destroy_base': 'DESTRUIR BASE',
        'media_only': 'Canal restrito para mídia 📎', 'new_msg_alert': '🔔 Nova mensagem!',
        'progression': 'PROGRESSO (XP)', 'medals': '🏆 MEDALHAS'
    },
    'en': {
        'login_title': 'FOR GLORY', 'login': 'LOGIN', 'create_acc': 'Create Account', 'forgot': 'Forgot Password',
        'codename': 'CODENAME', 'password': 'PASSWORD', 'new_user': 'NEW USER', 'email_real': 'EMAIL (Real)', 'enlist': 'ENLIST', 'back': 'Back',
        'recover': 'RECOVER ACCESS', 'reg_email': 'REGISTERED EMAIL', 'send_link': 'SEND LINK', 'new_pass_title': 'NEW PASSWORD', 'new_pass': 'NEW PASSWORD', 'save_pass': 'SAVE PASSWORD',
        'confirm_action': 'CONFIRM ACTION', 'confirm_del': 'Are you sure you want to delete this?', 'delete': 'DELETE', 'cancel': 'CANCEL',
        'new_base': 'NEW OFFICIAL BASE', 'base_name': 'Base Name', 'base_desc': 'Base Description', 'pub_base': '🌍 Public', 'priv_base': '🔒 Private', 'establish': 'ESTABLISH',
        'new_channel': 'NEW CHANNEL', 'channel_name': 'Name', 'ch_free': '💬 Free', 'ch_text': '📝 Text Only', 'ch_media': '🎬 Media Only', 'ch_pub': '🌍 Public', 'ch_priv': '🔒 Private', 'create_channel': 'CREATE CHANNEL',
        'new_squad': 'NEW SQUAD', 'group_name': 'Group Name', 'select_allies': 'Select allies:', 'create': 'CREATE',
        'new_post': 'NEW POST', 'caption_placeholder': 'Caption...', 'publish': 'PUBLISH (+50 XP)',
        'edit_profile': 'EDIT PROFILE', 'bio_placeholder': 'Write your Bio...', 'save': 'SAVE',
        'stealth_on': '🕵️ STEALTH MODE: ON', 'stealth_off': '🟢 STEALTH MODE: OFF', 'search_soldier': 'Search Soldier...', 'requests': '📩 Requests', 'friends': '👥 Friends', 'disconnect': 'LOGOUT',
        'private_msgs': 'PRIVATE MESSAGES', 'group_x1': '+ DM SQUAD', 'my_bases': '🛡️ MY BASES', 'create_base': '+ CREATE BASE',
        'explore_bases': '🌐 EXPLORE BASES', 'search_base': 'Search Base...', 'my_history': '🕒 MY HISTORY',
        'msg_placeholder': 'Secret message...', 'base_msg_placeholder': 'Message to base...',
        'at': 'at', 'deleted_msg': '🚫 Message deleted', 'audio_proc': 'Processing...',
        'recording': '🔴 Recording...', 'click_to_send': '(Click mic to send)',
        'empty_box': 'Your inbox is empty. Recruit allies!', 'direct_msg': 'Direct Message', 'squad': '👥 DM Squad',
        'no_bases': 'You have no bases yet.', 'no_bases_found': 'No bases found.', 'no_history': 'No missions recorded in Feed.',
        'request_join': '🔒 REQUEST', 'enter': '🌍 ENTER', 'ally': '✔ Ally', 'sent': 'Sent', 'accept_ally': 'Accept Ally', 'recruit_ally': 'Recruit Ally',
        'creator': '👑 CREATOR', 'admin': '🛡️ ADMIN', 'member': 'MEMBER', 'promote': 'Promote',
        'base_members': 'Base Members', 'entry_requests': 'Entry Requests', 'destroy_base': 'DESTROY BASE',
        'media_only': 'Media restricted channel 📎', 'new_msg_alert': '🔔 New message!',
        'progression': 'PROGRESSION (XP)', 'medals': '🏆 MEDALS'
    },
    'es': {
        'login_title': 'FOR GLORY', 'login': 'ENTRAR', 'create_acc': 'Crear Cuenta', 'forgot': 'Olvidé la Contraseña',
        'codename': 'NOMBRE EN CLAVE', 'password': 'CONTRASEÑA', 'new_user': 'NUEVO USUARIO', 'email_real': 'CORREO (Real)', 'enlist': 'ALISTARSE', 'back': 'Volver',
        'recover': 'RECUPERAR ACCESO', 'reg_email': 'CORREO REGISTRADO', 'send_link': 'ENVIAR ENLACE', 'new_pass_title': 'NUEVA CONTRASEÑA', 'new_pass': 'NUEVA CONTRASEÑA', 'save_pass': 'GUARDAR CONTRASEÑA',
        'confirm_action': 'CONFIRMAR ACCIÓN', 'confirm_del': '¿Seguro que quieres borrar esto?', 'delete': 'BORRAR', 'cancel': 'CANCELAR',
        'new_base': 'NUEVA BASE', 'base_name': 'Nombre de la Base', 'base_desc': 'Descripción', 'pub_base': '🌍 Pública', 'priv_base': '🔒 Privada', 'establish': 'ESTABLECER',
        'new_channel': 'NUEVO CANAL', 'channel_name': 'Nombre', 'ch_free': '💬 Libre', 'ch_text': '📝 Solo Texto', 'ch_media': '🎬 Solo Medios', 'ch_pub': '🌍 Público', 'ch_priv': '🔒 Privado', 'create_channel': 'CREAR CANAL',
        'new_squad': 'NUEVO ESCUADRÓN', 'group_name': 'Nombre del Grupo', 'select_allies': 'Selecciona aliados:', 'create': 'CREAR',
        'new_post': 'NUEVO POST', 'caption_placeholder': 'Leyenda...', 'publish': 'PUBLICAR (+50 XP)',
        'edit_profile': 'EDITAR PERFIL', 'bio_placeholder': 'Escribe tu Bio...', 'save': 'GUARDAR',
        'stealth_on': '🕵️ MODO FURTIVO: ON', 'stealth_off': '🟢 MODO FURTIVO: OFF', 'search_soldier': 'Buscar Soldado...', 'requests': '📩 Solicitudes', 'friends': '👥 Amigos', 'disconnect': 'DESCONECTAR',
        'private_msgs': 'MENSAJES PRIVADOS', 'group_x1': '+ ESCUADRÓN DM', 'my_bases': '🛡️ MIS BASES', 'create_base': '+ CREAR BASE',
        'explore_bases': '🌐 EXPLORAR BASES', 'search_base': 'Buscar Base...', 'my_history': '🕒 MI HISTORIAL',
        'msg_placeholder': 'Mensaje secreto...', 'base_msg_placeholder': 'Mensaje para la base...',
        'at': 'a las', 'deleted_msg': '🚫 Mensaje borrado', 'audio_proc': 'Procesando...',
        'recording': '🔴 Grabando...', 'click_to_send': '(Click mic enviar)',
        'empty_box': 'Tu buzón está vacío. ¡Recluta aliados!', 'direct_msg': 'Mensaje Directo', 'squad': '👥 Escuadrón',
        'no_bases': 'Aún no tienes bases.', 'no_bases_found': 'No se encontraron bases.', 'no_history': 'No hay misiones.',
        'request_join': '🔒 SOLICITAR', 'enter': '🌍 ENTRAR', 'ally': '✔ Aliado', 'sent': 'Enviado', 'accept_ally': 'Aceptar Aliado', 'recruit_ally': 'Reclutar Aliado',
        'creator': '👑 CREADOR', 'admin': '🛡️ ADMIN', 'member': 'MIEMBRO', 'promote': 'Promover',
        'base_members': 'Miembros', 'entry_requests': 'Solicitudes', 'destroy_base': 'DESTRUIR BASE',
        'media_only': 'Canal restringido a medios 📎', 'new_msg_alert': '🔔 ¡Nuevo mensaje!',
        'progression': 'PROGRESO (XP)', 'medals': '🏆 MEDALLAS'
    }
};

let sysLang = navigator.language ? navigator.language.substring(0,2) : 'en';
let validLangs = ['pt', 'en', 'es'];
window.currentLang = 'en';
try {
    let savedLang = localStorage.getItem('lang');
    if (validLangs.includes(savedLang)) { window.currentLang = savedLang; } 
    else { window.currentLang = validLangs.includes(sysLang) ? sysLang : 'en'; localStorage.setItem('lang', window.currentLang); }
} catch(e) { window.currentLang = validLangs.includes(sysLang) ? sysLang : 'en'; }

function t(key) { let dict = T[window.currentLang]; if (!dict) dict = T['en']; return dict[key] || key; }
function changeLanguage(lang) { try { localStorage.setItem('lang', lang); } catch(e){} location.reload(); }

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById('lang-selector').value = window.currentLang;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        let k = el.getAttribute('data-i18n');
        if(el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = t(k);
        else el.innerText = t(k);
    });
});

var user=null, dmWS=null, commWS=null, globalWS=null, syncInterval=null, lastFeedHash="", currentEmojiTarget=null, currentChatId=null, currentChatType=null;
var activeCommId=null, activeChannelId=null;
window.onlineUsers = []; window.unreadData = {}; window.lastTotalUnread = 0;
let mediaRecorders = {}; let audioChunks = {}; let recordTimers = {}; let recordSeconds = {};

let rtc = { localAudioTrack: null, client: null };
let callDuration = 0, callInterval = null;

const CLOUD_NAME = "dqa0q3qlx"; 
const UPLOAD_PRESET = "for_glory_preset"; 
const EMOJIS = ["😂","🔥","❤️","💀","🎮","🇧🇷","🫡","🤡","😭","😎","🤬","👀","👍","👎","🔫","💣","⚔️","🛡️","🏆","💰","🍕","🍺","👋","🚫","✅","👑","💩","👻","👽","🤖","🤫","🥶","🤯","🥳","🤢","🤕","🤑","🤠","😈","👿","👹","👺","👾"];

const RANK_TIERS = [
    { xp: 0, name: "Recruta", color: "#888888" }, { xp: 100, name: "Soldado", color: "#2ecc71" },
    { xp: 300, name: "Cabo", color: "#27ae60" }, { xp: 600, name: "3º Sargento", color: "#3498db" },
    { xp: 1000, name: "2º Sargento", color: "#2980b9" }, { xp: 1500, name: "1º Sargento", color: "#9b59b6" },
    { xp: 2500, name: "Subtenente", color: "#8e44ad" }, { xp: 4000, name: "Tenente", color: "#f1c40f" },
    { xp: 6000, name: "Capitão", color: "#f39c12" }, { xp: 10000, name: "Major", color: "#e67e22" },
    { xp: 15000, name: "Tenente-Coronel", color: "#e74c3c" }, { xp: 25000, name: "Coronel", color: "#c0392b" },
    { xp: 50000, name: "General ⭐", color: "#FFD700" }
];

function showRanksModal() {
    let list = document.getElementById('ranks-list');
    list.innerHTML = RANK_TIERS.map(r => `
        <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.05); padding:10px 15px; border-radius:10px; border-left:4px solid ${r.color};">
            <span style="color:white; font-weight:bold; font-size:15px;">${r.name}</span>
            <span style="color:${r.color}; font-family:'Rajdhani'; font-weight:bold;">${r.xp} XP</span>
        </div>
    `).join('');
    document.getElementById('modal-ranks').classList.remove('hidden');
}

function showToast(m){let x=document.getElementById("toast");x.innerText=m;x.className="show";setTimeout(()=>{x.className=""},3000)}
function toggleAuth(m){['login','register','forgot','reset'].forEach(f=>document.getElementById(f+'-form').classList.add('hidden'));document.getElementById(m+'-form').classList.remove('hidden');}

async function doLogin() {
    let btn = document.querySelector('#login-form .btn-main');
    let oldText = btn.innerText;
    btn.innerText = "⏳ CONECTANDO...";
    btn.disabled = true;
    try {
        let r = await fetch('/login', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: document.getElementById('l-user').value, password: document.getElementById('l-pass').value})
        });
        if (!r.ok) throw new Error("Erro no login");
        user = await r.json();
        startApp();
    } catch(e) { showToast("❌ Codinome/Senha incorretos.");
    } finally { btn.innerText = oldText; btn.disabled = false; }
}

async function doRegister() {
    let btn = document.querySelector('#register-form .btn-main');
    let oldText = btn.innerText;
    btn.innerText = "⏳ REGISTRANDO...";
    btn.disabled = true;
    try {
        let r = await fetch('/register', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: document.getElementById('r-user').value, email: document.getElementById('r-email').value, password: document.getElementById('r-pass').value})
        });
        if (!r.ok) throw new Error("Erro");
        showToast("✔ Registrado! Faça login.");
        toggleAuth('login');
    } catch(e) { showToast("❌ Erro. Usuário ou e-mail já existe.");
    } finally { btn.innerText = oldText; btn.disabled = false; }
}

function formatMsgTime(iso) {
    if(!iso) return "";
    let d = new Date(iso); 
    let dia = String(d.getDate()).padStart(2, '0');
    let mes = String(d.getMonth()+1).padStart(2, '0');
    let h = String(d.getHours()).padStart(2, '0');
    let m = String(d.getMinutes()).padStart(2, '0');
    return `${dia}/${mes} ${t('at')} ${h}:${m}`;
}

function formatRankInfo(rank, special, color) {
    let h = '';
    if(special) h += `<span class="special-badge">${special}</span>`;
    if(rank) h += `<span class="rank-badge" style="color:${color}; border-color:${color};">${rank}</span>`;
    return h;
}

function initEmojis() {
    let g = document.getElementById('emoji-grid'); if(!g) return; g.innerHTML = '';
    EMOJIS.forEach(e => {
        let s = document.createElement('div'); s.style.cssText = "font-size:24px;cursor:pointer;text-align:center;padding:5px;border-radius:5px;transition:0.2s;"; s.innerText = e;
        s.onclick = () => { if(currentEmojiTarget){ let inp = document.getElementById(currentEmojiTarget); inp.value += e; inp.focus(); } };
        s.onmouseover = () => s.style.background = "rgba(102,252,241,0.2)"; s.onmouseout = () => s.style.background = "transparent"; g.appendChild(s);
    });
}
initEmojis();

function checkToken() {
    const urlParams = new URLSearchParams(window.location.search); const token = urlParams.get('token');
    if (token) { toggleAuth('reset'); window.history.replaceState({}, document.title, "/"); window.resetToken = token; }
}
checkToken();

function closeUpload() {
    document.getElementById('modal-upload').classList.add('hidden');
    document.getElementById('file-upload').value = '';
    document.getElementById('caption-upload').value = '';
}

function openEmoji(id){currentEmojiTarget = id; document.getElementById('emoji-picker').style.display='flex';}
function toggleEmoji(forceClose){let e = document.getElementById('emoji-picker'); if(forceClose === true) e.style.display='none'; else e.style.display = e.style.display === 'flex' ? 'none' : 'flex';}

document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && user) {
        fetchUnread(); fetchOnlineUsers();
        if(document.getElementById('view-feed').classList.contains('active')) loadFeed();
        if(activeChannelId && commWS && commWS.readyState !== WebSocket.OPEN) connectCommWS(activeChannelId); 
    }
});

async function fetchOnlineUsers() {
    if(!user) return;
    try { let r = await fetch(`/users/online?nocache=${new Date().getTime()}`); window.onlineUsers = await r.json(); updateStatusDots(); } catch(e){}
}
function updateStatusDots() {
    document.querySelectorAll('.status-dot').forEach(dot => {
        let uid = parseInt(dot.getAttribute('data-uid')); if(!uid) return;
        if(window.onlineUsers.includes(uid)) dot.classList.add('online'); else dot.classList.remove('online');
    });
}

async function fetchUnread() {
    if(!user) return;
    try {
        let r = await fetch(`/inbox/unread/${user.id}?nocache=${new Date().getTime()}`); let d = await r.json(); window.unreadData = d.by_sender || {};
        let badge = document.getElementById('inbox-badge');
        
        if(d.total > 0) { 
            badge.innerText = d.total; 
            badge.style.display = 'block'; 
            badge.style.top = '0px'; 
            badge.style.right = '0px';
        } else { badge.style.display = 'none'; }
        
        if (window.lastTotalUnread !== undefined && d.total > window.lastTotalUnread) { showToast(t('new_msg_alert')); }
        window.lastTotalUnread = d.total;

        if(document.getElementById('view-inbox').classList.contains('active')) {
            document.querySelectorAll('.inbox-item').forEach(item => {
                let sid = item.getAttribute('data-id'); 
                let type = item.getAttribute('data-type'); 
                let b = item.querySelector('.list-badge');
                if(type === '1v1' && window.unreadData[sid]) { 
                    b.innerText = window.unreadData[sid]; b.style.display = 'block'; 
                } else if(b) { b.style.display = 'none'; }
            });
        }
    } catch(e){}
}

async function toggleStealth() {
    let r = await fetch('/profile/stealth', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({uid:user.id})});
    if(r.ok) { let d = await r.json(); user.is_invisible = d.is_invisible; updateStealthUI(); fetchOnlineUsers(); }
}
function updateStealthUI() {
    let btn = document.getElementById('btn-stealth'); let myDot = document.getElementById('my-status-dot');
    if(user.is_invisible) { btn.innerText = t('stealth_on'); btn.style.borderColor = "#ffaa00"; btn.style.color = "#ffaa00"; myDot.classList.remove('online'); } 
    else { btn.innerText = t('stealth_off'); btn.style.borderColor = "rgba(102, 252, 241, 0.3)"; btn.style.color = "var(--primary)"; myDot.classList.add('online'); }
}

async function requestReset() { let email = document.getElementById('f-email').value; if(!email) return showToast("Erro!"); try { let r = await fetch('/auth/forgot-password', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email: email}) }); showToast("Enviado!"); toggleAuth('login'); } catch(e) { showToast("Erro"); } }
async function doResetPassword() { let newPass = document.getElementById('new-pass').value; if(!newPass) return showToast("Erro!"); try { let r = await fetch('/auth/reset-password', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token: window.resetToken, new_password: newPass}) }); if(r.ok) { showToast("Alterada!"); toggleAuth('login'); } else { showToast("Link expirado."); } } catch(e) { showToast("Erro"); } }

function renderMedals(boxId, medalsData) {
    let box = document.getElementById(boxId);
    if(!medalsData || medalsData.length === 0) { box.innerHTML = ''; return; }
    
    let mHtml = medalsData.map(m => {
        let isEarned = m.earned;
        let op = isEarned ? '1' : '0.4';
        let filter = isEarned ? 'drop-shadow(0 0 8px rgba(102,252,241,0.4))' : 'grayscale(100%)';
        let statusText = isEarned ? `<span style="color:#2ecc71;font-size:9px;">✔ Desbloqueado</span>` : `<span style="color:#ff5555;font-size:9px;">🔒 Faltam ${m.missing} XP</span>`;
        
        return `
        <div style="background:rgba(0,0,0,0.5); padding:12px 5px; border-radius:12px; border:1px solid ${isEarned ? 'rgba(102,252,241,0.3)' : '#333'}; width:100px; text-align:center; opacity:${op}; display:flex; flex-direction:column; align-items:center; justify-content:space-between; transition:0.3s;" title="${m.desc}">
            <div style="font-size:32px; filter:${filter}; margin-bottom:5px;">${m.icon}</div>
            <div style="font-size:11px; color:white; font-weight:bold; font-family:'Inter'; line-height:1.2; margin-bottom:4px;">${m.name}</div>
            ${statusText}
        </div>`;
    }).join('');
    
    box.innerHTML = `
        <h3 style="color:var(--primary); font-family:'Rajdhani'; letter-spacing:1px; text-align:center; margin-top:30px; border-bottom:1px solid #333; padding-bottom:10px; display:inline-block;">${t('medals')}</h3>
        <div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-bottom: 30px;">${mHtml}</div>
    `;
}

function updateUI(){
    if(!user) return;
    let safeAvatar = user.avatar_url; if(!safeAvatar || safeAvatar.includes("undefined")) safeAvatar = `https://ui-avatars.com/api/?name=${user.username}&background=1f2833&color=66fcf1&bold=true`;
    document.getElementById('nav-avatar').src = safeAvatar; document.getElementById('p-avatar').src = safeAvatar;
    let pCover = document.getElementById('p-cover'); pCover.src = user.cover_url || "https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY"; pCover.style.display = 'block';
    
    document.getElementById('p-name').innerText = user.username || "Soldado"; 
    document.getElementById('p-bio').innerText = user.bio || "Na base de operações."; 
    document.getElementById('p-emblems').innerHTML = formatRankInfo(user.rank, user.special_emblem, user.color);
    
    let missingXP = user.next_xp - user.xp;
    document.getElementById('p-progression-box').innerHTML = `
        <div style="margin: 20px auto; width: 90%; max-width: 400px; text-align: left; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 12px; border: 1px solid #333;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="color: var(--primary); font-weight: bold; font-size: 14px;">${t('progression')}</span>
                <span style="color: white; font-size: 14px; font-family:'Rajdhani'; font-weight:bold;">${user.xp} / ${user.next_xp} XP</span>
            </div>
            <div style="width: 100%; background: #222; height: 10px; border-radius: 5px; overflow: hidden; box-shadow:inset 0 2px 5px rgba(0,0,0,0.5);">
                <div style="width: ${user.percent}%; height: 100%; background: linear-gradient(90deg, #1d4e4f, var(--primary)); transition: width 0.5s;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:8px; align-items:center;">
                <span style="color: #888; font-size: 11px;">Falta ${missingXP} XP para ${user.next_rank}</span>
                <button class="btn-link" style="margin:0; font-size:11px;" onclick="showRanksModal()">Ver Patentes</button>
            </div>
        </div>
    `;
    
    renderMedals('p-medals-box', user.medals);
    document.querySelectorAll('.my-avatar-mini').forEach(img => img.src = safeAvatar);
    updateStealthUI();
}

function startApp(){
    document.getElementById('modal-login').classList.add('hidden');
    document.getElementById('lang-menu').classList.add('hidden'); 
    updateUI(); fetchOnlineUsers(); fetchUnread(); 
    goView('profile', document.getElementById('nav-profile-btn'));
    
    let p = location.protocol === 'https:' ? 'wss:' : 'ws:';
    globalWS = new WebSocket(`${p}//${location.host}/ws/Geral/${user.id}`);
    globalWS.onmessage = (e) => {
        let d = JSON.parse(e.data);
        if(d.type === 'ping') { fetchUnread(); }
    };
    globalWS.onclose = () => { setTimeout(() => { if(user) startApp(); }, 5000); };

    syncInterval=setInterval(()=>{
        if(document.getElementById('view-feed').classList.contains('active')) loadFeed();
        fetchOnlineUsers(); fetchUnread(); 
    },4000);
}

function logout(){location.reload()}

function goView(v, btnElem){
    document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));
    document.getElementById('view-'+v).classList.add('active');
    
    if(v !== 'public-profile' && v !== 'dm' && v !== 'comm-dashboard') { 
        document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active')); 
        if(btnElem) btnElem.classList.add('active');
        else if(event && event.target && event.target.closest) event.target.closest('.nav-btn')?.classList.add('active'); 
    }
    
    if(v === 'inbox') loadInbox();
    if(v === 'mycomms') loadMyComms();
    if(v === 'explore') loadPublicComms();
    if(v === 'history') loadMyHistory();
    if(v === 'feed') loadFeed();
}

/* =========================================
   SISTEMA DE CALL (AGORA.IO SFU) EM SEGUNDO PLANO
   ========================================= */
async function initCall() {
    if (rtc.client) return showToast("Você já está em uma call!");
    
    let channelName = "";
    if (document.getElementById('view-dm').classList.contains('active')) {
        channelName = `call_${currentChatType}_${currentChatId}`;
    } else if (document.getElementById('view-comm-dashboard').classList.contains('active')) {
        channelName = `call_comm_${activeCommId}`;
    } else {
        return showToast("Entre em um chat para iniciar a Call.");
    }

    showToast("Conectando ao Satélite de Voz...");
    try {
        let res = await fetch('/agora-config');
        let conf = await res.json();
        if (!conf.app_id) return showToast("Erro: APP ID do Rádio não configurado no Servidor.");

        rtc.client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
        
        rtc.client.on("user-published", async (remoteUser, mediaType) => {
            await rtc.client.subscribe(remoteUser, mediaType);
            if (mediaType === "audio") { remoteUser.audioTrack.play(); }
        });

        let uid = await rtc.client.join(conf.app_id, channelName, null, user.id);
        
        rtc.localAudioTrack = await AgoraRTC.createMicrophoneAudioTrack({
            encoderConfig: "high_quality", AEC: true, ANS: true, AGC: false 
        });
        
        await rtc.client.publish([rtc.localAudioTrack]);
        showCallHUD();
    } catch(e) {
        showToast("Erro ao iniciar Call. Verifique o Microfone.");
        leaveCall();
    }
}

function showCallHUD() {
    document.getElementById('call-hud').style.display = 'flex';
    callDuration = 0;
    document.getElementById('call-hud-time').innerText = "00:00";
    callInterval = setInterval(() => {
        callDuration++;
        let m = String(Math.floor(callDuration / 60)).padStart(2, '0');
        let s = String(callDuration % 60).padStart(2, '0');
        document.getElementById('call-hud-time').innerText = `${m}:${s}`;
    }, 1000);
}

async function leaveCall() {
    if (rtc.localAudioTrack) { rtc.localAudioTrack.close(); }
    if (rtc.client) { await rtc.client.leave(); }
    rtc.localAudioTrack = null;
    rtc.client = null;
    
    clearInterval(callInterval);
    document.getElementById('call-hud').style.display = 'none';
    
    let btn = document.getElementById('btn-mute-call');
    btn.classList.remove('muted');
    btn.innerHTML = '🎤';
    showToast("Chamada Encerrada.");
}

function toggleMuteCall() {
    if(rtc.localAudioTrack) {
        let muted = !rtc.localAudioTrack.muted;
        rtc.localAudioTrack.setMuted(muted);
        let btn = document.getElementById('btn-mute-call');
        if(muted) { btn.classList.add('muted'); btn.innerHTML = '🔇'; } 
        else { btn.classList.remove('muted'); btn.innerHTML = '🎤'; }
    }
}

async function toggleRecord(type) {
    let btn = document.getElementById(`btn-mic-${type}`);
    let inpId = type === 'dm' ? 'dm-msg' : (type === 'comm' ? 'comm-msg' : `comment-inp-${type.split('-')[1]}`);
    let inp = document.getElementById(inpId);

    if (mediaRecorders[type] && mediaRecorders[type].state === 'recording') { 
        mediaRecorders[type].stop(); 
        btn.classList.remove('recording'); 
        clearInterval(recordTimers[type]);
        if(inp) { inp.placeholder = t('audio_proc'); inp.disabled = false; }
        return; 
    }
    try {
        let stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: false, sampleRate: 48000 } });
        let options = {};
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) { options = { mimeType: 'audio/webm;codecs=opus', audioBitsPerSecond: 128000 }; }
        
        mediaRecorders[type] = new MediaRecorder(stream, options);
        audioChunks[type] = [];
        mediaRecorders[type].ondataavailable = e => { if(e.data.size > 0) audioChunks[type].push(e.data); };
        mediaRecorders[type].onstop = async () => {
            let blob = new Blob(audioChunks[type], { type: 'audio/webm' });
            let file = new File([blob], "radio.webm", { type: 'audio/webm' });
            try {
                let res = await uploadToCloudinary(file);
                let audioMsg = "[AUDIO]" + res.secure_url;
                if(type === 'dm' && dmWS) { dmWS.send(audioMsg); }
                else if(type === 'comm' && commWS) { commWS.send(audioMsg); }
                else if(type.startsWith('comment-')) {
                    let pid = type.split('-')[1];
                    await fetch('/post/comment', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({post_id:pid, user_id:user.id, text:audioMsg})});
                    lastFeedHash=""; loadFeed();
                }
            } catch(err) { showToast("Erro."); }
            stream.getTracks().forEach(t => t.stop());
            if(inp) { inp.placeholder = ""; } 
        };
        
        mediaRecorders[type].start();
        btn.classList.add('recording');
        
        if(inp) {
            inp.disabled = true;
            recordSeconds[type] = 0;
            inp.placeholder = `${t('recording')} 00:00`;
            recordTimers[type] = setInterval(() => {
                recordSeconds[type]++;
                let mins = String(Math.floor(recordSeconds[type] / 60)).padStart(2, '0');
                let secs = String(recordSeconds[type] % 60).padStart(2, '0');
                inp.placeholder = `${t('recording')} ${mins}:${secs} ${t('click_to_send')}`;
            }, 1000);
        }
    } catch (e) { showToast("Mic Blocked!"); }
}

async function loadMyHistory() {
    let hist = await fetch(`/user/${user.id}?viewer_id=${user.id}&nocache=${new Date().getTime()}`); let hData = await hist.json();
    let grid = document.getElementById('my-posts-grid'); grid.innerHTML = '';
    if(hData.posts.length === 0) grid.innerHTML = `<p style='color:#888;grid-column:1/-1;'>${t('no_history')}</p>`;
    hData.posts.forEach(p => { grid.innerHTML += p.media_type==='video' ? `<video src="${p.content_url}" style="width:100%; aspect-ratio:1/1; object-fit:cover; border-radius:10px;" controls preload="metadata"></video>` : `<img src="${p.content_url}" style="width:100%; aspect-ratio:1/1; object-fit:cover; cursor:pointer; border-radius:10px;" onclick="window.open(this.src)">`; });
}

async function loadFeed(){
    try{
        let r=await fetch(`/posts?uid=${user.id}&limit=50&nocache=${new Date().getTime()}`); if(!r.ok)return; let p=await r.json();
        let h=JSON.stringify(p.map(x=>x.id + x.likes + x.comments + (x.user_liked?"1":"0"))); if(h===lastFeedHash)return; lastFeedHash=h;
        
        let openComments = []; let activeInputs = {}; let focusedInputId = null;
        if (document.activeElement && document.activeElement.classList.contains('comment-inp')) { focusedInputId = document.activeElement.id; }
        document.querySelectorAll('.comments-section').forEach(sec => { if(sec.style.display === 'block') openComments.push(sec.id.split('-')[1]); });
        document.querySelectorAll('.comment-inp').forEach(inp => { if(inp.value) activeInputs[inp.id] = inp.value; });

        let ht='';
        p.forEach(x=>{
            let m=x.media_type==='video'?`<video src="${x.content_url}" class="post-media" controls playsinline preload="metadata"></video>`:`<img src="${x.content_url}" class="post-media" loading="lazy">`;
            m = `<div class="post-media-wrapper">${m}</div>`;
            let delBtn=x.author_id===user.id?`<span onclick="confirmDelete('post', ${x.id})" style="cursor:pointer;opacity:0.5;font-size:20px;transition:0.2s;" onmouseover="this.style.opacity='1';this.style.color='#ff5555'" onmouseout="this.style.opacity='0.5';this.style.color=''">🗑️</span>`:'';
            let heartIcon = x.user_liked ? "❤️" : "🤍"; let heartClass = x.user_liked ? "liked" : "";
            let rankHtml = formatRankInfo(x.author_rank, x.special_emblem, x.rank_color);

            ht+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer" onclick="openPublicProfile(${x.author_id})"><div class="av-wrap" style="margin-right:12px;"><img src="${x.author_avatar}" class="post-av" style="margin:0;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${x.author_id}"></div></div><div class="user-info-box"><b style="color:white;font-size:14px">${x.author_name}</b><div style="margin-top:2px;">${rankHtml}</div></div></div>${delBtn}</div>${m}<div class="post-actions"><button class="action-btn ${heartClass}" onclick="toggleLike(${x.id}, this)"><span class="icon">${heartIcon}</span> <span class="count" style="color:white;font-weight:bold;">${x.likes}</span></button><button class="action-btn" onclick="toggleComments(${x.id})">💬 <span class="count" style="color:white;font-weight:bold;">${x.comments}</span></button></div><div class="post-caption"><b style="color:white;cursor:pointer;" onclick="openPublicProfile(${x.author_id})">${x.author_name}</b> ${x.caption}</div><div id="comments-${x.id}" class="comments-section"><div id="comment-list-${x.id}"></div><form class="comment-input-area" onsubmit="sendComment(${x.id}); return false;"><button type="button" class="icon-btn" id="btn-mic-comment-${x.id}" onclick="toggleRecord('comment-${x.id}')">🎤</button><input id="comment-inp-${x.id}" class="comment-inp" placeholder="${t('caption_placeholder')}" autocomplete="off"><button type="button" class="icon-btn" onclick="openEmoji('comment-inp-${x.id}')">😀</button><button type="submit" class="btn-send-msg">➤</button></form></div></div>`
        });
        document.getElementById('feed-container').innerHTML=ht;
        
        openComments.forEach(pid => { let sec = document.getElementById(`comments-${pid}`); if(sec) { sec.style.display = 'block'; loadComments(pid); } });
        for (let id in activeInputs) { let inp = document.getElementById(id); if (inp) inp.value = activeInputs[id]; }
        if (focusedInputId) { let inp = document.getElementById(focusedInputId); if (inp) { inp.focus({preventScroll: true}); let val = inp.value; inp.value = ''; inp.value = val; } }
        updateStatusDots();
    }catch(e){}
}

function confirmDelete(type, id) { deleteTarget = {type:type, id:id}; document.getElementById('modal-delete').classList.remove('hidden'); }
document.getElementById('btn-confirm-delete').onclick = async () => {
    if(!deleteTarget.id) return; 
    let tp = deleteTarget.type; let id = deleteTarget.id; document.getElementById('modal-delete').classList.add('hidden');
    
    if(tp === 'post') {
        let r = await fetch('/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id,user_id:user.id})});
        if(r.ok) { lastFeedHash=""; loadFeed(); loadMyHistory(); updateProfileState(); } 
    } else if (tp === 'comment') {
        let r = await fetch('/comment/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({comment_id:id,user_id:user.id})});
        if(r.ok) { lastFeedHash=""; loadFeed(); }
    } else if (tp === 'base') {
        let fd = new FormData(); fd.append('user_id', user.id);
        let r = await fetch(`/community/${id}/delete`,{method:'POST', body:fd});
        if(r.ok) { closeComm(); }
    } else if (tp === 'dm_msg' || tp === 'comm_msg' || tp === 'group_msg') {
        let mainType = tp === 'dm_msg' ? 'dm' : (tp === 'comm_msg' ? 'comm' : 'group');
        let r = await fetch('/message/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({msg_id:id, type:mainType, user_id:user.id})});
        let res = await r.json();
        if(res.status === 'ok') {
            let msgBubble = document.getElementById(`${tp}-${id}`).querySelector('.msg-bubble');
            let timeSpan = msgBubble.querySelector('.msg-time');
            let timeStr = timeSpan ? timeSpan.outerHTML : '';
            msgBubble.innerHTML = `<span class="msg-deleted">${t('deleted_msg')}</span>${timeStr}`;
            let btn = document.getElementById(`${tp}-${id}`).querySelector('.del-msg-btn');
            if(btn) btn.remove();
        } else if (res.status === 'timeout') {
            showToast(res.msg);
            let btn = document.getElementById(`${tp}-${id}`).querySelector('.del-msg-btn');
            if(btn) btn.remove();
        }
    }
};

async function updateProfileState() {
    let r = await fetch(`/user/${user.id}?viewer_id=${user.id}&nocache=${new Date().getTime()}`); 
    let d = await r.json();
    Object.assign(user, d);
    updateUI();
}

async function toggleLike(pid, btn) {
    let r = await fetch('/post/like', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({post_id:pid, user_id:user.id})});
    if(r.ok) { let d = await r.json(); let icon = btn.querySelector('.icon'); let count = btn.querySelector('.count'); if(d.liked) { btn.classList.add('liked'); icon.innerText = "❤️"; } else { btn.classList.remove('liked'); icon.innerText = "🤍"; } count.innerText = d.count; lastFeedHash=""; }
}

async function toggleComments(pid) {
    let sec = document.getElementById(`comments-${pid}`);
    if(sec.style.display === 'block') { sec.style.display = 'none'; } else { sec.style.display = 'block'; loadComments(pid); }
}

async function loadComments(pid) {
    let r = await fetch(`/post/${pid}/comments?nocache=${new Date().getTime()}`);
    let list = document.getElementById(`comment-list-${pid}`);
    if(r.ok) {
        let comments = await r.json();
        if(comments.length === 0){ list.innerHTML = `<p style='color:#888;font-size:12px;text-align:center;'>Vazio</p>`; return;}
        list.innerHTML = comments.map(c => {
            let delBtn = (c.author_id === user.id) ? `<span onclick="confirmDelete('comment', ${c.id})" style="color:#ff5555;cursor:pointer;margin-left:auto;font-size:14px;padding:0 5px;">🗑️</span>` : '';
            let txt = c.text;
            if(txt.startsWith('[AUDIO]')) { txt = `<audio controls src="${txt.replace('[AUDIO]','')}" style="max-width:200px; height:35px; outline:none; margin-top:5px;"></audio>`; }
            return `<div class="comment-row" style="align-items:center;"><div class="av-wrap" onclick="openPublicProfile(${c.author_id})"><img src="${c.author_avatar}" class="comment-av" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${c.author_id}" style="width:8px;height:8px;border-width:1px;"></div></div><div style="flex:1;"><b style="color:var(--primary);cursor:pointer;" onclick="openPublicProfile(${c.author_id})">${c.author_name}</b> <span style="display:inline-block; margin-left:5px;">${formatRankInfo(c.author_rank, c.special_emblem, c.color)}</span> <span style="color:#e0e0e0; display:block; margin-top:3px;">${txt}</span></div>${delBtn}</div>`
        }).join('');
        updateStatusDots();
    }
}

async function sendComment(pid) {
    let inp = document.getElementById(`comment-inp-${pid}`); let text = inp.value.trim(); if(!text) return;
    let r = await fetch('/post/comment', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({post_id:pid, user_id:user.id, text:text})});
    if(r.ok) { inp.value = ''; toggleEmoji(true); lastFeedHash=""; loadFeed(); }
}

async function loadInbox() {
    let r = await fetch(`/inbox/${user.id}?nocache=${new Date().getTime()}`); let d = await r.json(); let b = document.getElementById('inbox-list'); b.innerHTML = '';
    if(d.groups.length === 0 && d.friends.length === 0) { b.innerHTML = `<p style='text-align:center;color:#888;margin-top:20px;'>${t('empty_box')}</p>`; return; }
    d.groups.forEach(g => { b.innerHTML += `<div class="inbox-item" data-id="${g.id}" data-type="group" style="display:flex;align-items:center;gap:15px;padding:12px;background:var(--card-bg);border-radius:12px;cursor:pointer;border:1px solid rgba(102,252,241,0.2);" onclick="openChat(${g.id}, '${g.name}', 'group')"><img src="${g.avatar}" style="width:45px;height:45px;border-radius:50%;"><div style="flex:1;"><b style="color:white;font-size:16px;">${g.name}</b><br><span style="font-size:12px;color:var(--primary);">${t('squad')}</span></div></div>`; });
    d.friends.forEach(f => {
        let unreadCount = (window.unreadData && window.unreadData[String(f.id)]) ? window.unreadData[String(f.id)] : 0; 
        let badgeDisplay = unreadCount > 0 ? 'block' : 'none';
        b.innerHTML += `
        <div class="inbox-item" data-id="${f.id}" data-type="1v1" style="display:flex;align-items:center;gap:15px;padding:12px;background:rgba(255,255,255,0.05);border-radius:12px;cursor:pointer;" onclick="openChat(${f.id}, '${f.name}', '1v1')">
            <div class="av-wrap"><img src="${f.avatar}" style="width:45px;height:45px;border-radius:50%;object-fit:cover;"><div class="status-dot" data-uid="${f.id}"></div></div>
            <div style="flex:1;"><b style="color:white;font-size:16px;">${f.name}</b><br><span style="font-size:12px;color:#888;">${t('direct_msg')}</span></div>
            <div class="list-badge" style="display:${badgeDisplay}; background:#ff5555; color:white; font-size:12px; font-weight:bold; padding:4px 10px; border-radius:12px; box-shadow:0 0 8px rgba(255,85,85,0.6);">${unreadCount}</div>
        </div>`;
    });
    updateStatusDots();
}

async function openCreateGroupModal() {
    let r = await fetch(`/inbox/${user.id}?nocache=${new Date().getTime()}`); let d = await r.json(); let list = document.getElementById('group-friends-list');
    if(d.friends.length === 0) { list.innerHTML = `<p style='color:#ff5555;font-size:13px;'>Adicione amigos primeiro.</p>`; } 
    else { list.innerHTML = d.friends.map(f => `<label style="display:flex; align-items:center; gap:10px; color:white; margin-bottom:10px; cursor:pointer;"><input type="checkbox" class="grp-friend-cb" value="${f.id}" style="width:18px;height:18px;"><img src="${f.avatar}" style="width:30px;height:30px;border-radius:50%;object-fit:cover;"> ${f.name}</label>`).join(''); }
    document.getElementById('new-group-name').value = ''; document.getElementById('modal-create-group').classList.remove('hidden');
}

async function submitCreateGroup() {
    let name = document.getElementById('new-group-name').value.trim(); if(!name) return;
    let cbs = document.querySelectorAll('.grp-friend-cb:checked'); let member_ids = Array.from(cbs).map(cb => parseInt(cb.value));
    if(member_ids.length === 0) return;
    let r = await fetch('/group/create', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:name, creator_id:user.id, member_ids:member_ids})});
    if(r.ok) { document.getElementById('modal-create-group').classList.add('hidden'); loadInbox(); }
}

async function fetchChatMessages(id, type) {
    let list = document.getElementById('dm-list');
    let fetchUrl = type === 'group' ? `/group/${id}/messages?nocache=${new Date().getTime()}` : `/dms/${id}?uid=${user.id}&nocache=${new Date().getTime()}`;
    let r = await fetch(fetchUrl);
    if(r.ok) {
        let msgs = await r.json();
        let isAtBottom = (list.scrollHeight - list.scrollTop <= list.clientHeight + 50);
        msgs.forEach(d => {
            let prefix = type === 'group' ? 'group_msg' : 'dm_msg'; let msgId = `${prefix}-${d.id}`;
            if(!document.getElementById(msgId)) {
                let m = (d.user_id === user.id); let c = d.content; let delBtn = '';
                let timeHtml = d.timestamp ? `<span class="msg-time">${formatMsgTime(d.timestamp)}</span>` : '';
                
                if(c === '[DELETED]') { c = `<span class="msg-deleted">${t('deleted_msg')}</span>`; } 
                else {
                    if(c.startsWith('[AUDIO]')) { c = `<audio controls src="${c.replace('[AUDIO]','')}" style="max-width:200px; height:40px; outline:none;"></audio>`; }
                    else if(c.startsWith('http') && c.includes('cloudinary')) { if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) { c = `<video src="${c}" style="max-width:100%; border-radius:10px; border:1px solid #444;" controls playsinline></video>`; } else { c = `<img src="${c}" style="max-width:100%; border-radius:10px; cursor:pointer; border:1px solid #444;" onclick="window.open(this.src)">`; } }
                    delBtn = (m && d.can_delete) ? `<span class="del-msg-btn" onclick="confirmDelete('${prefix}', ${d.id})">🗑️</span>` : '';
                }
                let h = `<div id="${msgId}" class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div><div class="msg-bubble">${c}${timeHtml}${delBtn}</div></div></div>`;
                list.insertAdjacentHTML('beforeend',h);
            }
        });
        if(isAtBottom) list.scrollTop = list.scrollHeight;
    }
}

function connectDmWS(id, name, type) {
    if(dmWS) dmWS.close();
    let p = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let ch = type === 'group' ? `group_${id}` : `dm_${Math.min(user.id, id)}_${Math.max(user.id, id)}`;
    dmWS = new WebSocket(`${p}//${location.host}/ws/${ch}/${user.id}`);
    
    dmWS.onclose = () => { setTimeout(() => { if(currentChatId === id && document.getElementById('view-dm').classList.contains('active')) { fetchChatMessages(id, type); connectDmWS(id, name, type); } }, 2000); };
    dmWS.onmessage = e => {
        let d = JSON.parse(e.data); let b = document.getElementById('dm-list'); let m = parseInt(d.user_id) === parseInt(user.id); let c = d.content;
        if(d.type === 'ping') return;
        let prefix = type === 'group' ? 'group_msg' : 'dm_msg'; let msgId = `${prefix}-${d.id}`;
        if(!document.getElementById(msgId)) {
            let delBtn = ''; let timeHtml = d.timestamp ? `<span class="msg-time">${formatMsgTime(d.timestamp)}</span>` : '';
            if(c === '[DELETED]') { c = `<span class="msg-deleted">${t('deleted_msg')}</span>`; } 
            else {
                if(c.startsWith('[AUDIO]')) { c = `<audio controls src="${c.replace('[AUDIO]','')}" style="max-width:200px; height:40px; outline:none;"></audio>`; }
                else if(c.startsWith('http') && c.includes('cloudinary')) { if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) { c = `<video src="${c}" style="max-width:100%; border-radius:10px; border:1px solid #444;" controls playsinline></video>`; } else { c = `<img src="${c}" style="max-width:100%; border-radius:10px; cursor:pointer; border:1px solid #444;" onclick="window.open(this.src)">`; } }
                delBtn = (m && d.can_delete) ? `<span class="del-msg-btn" onclick="confirmDelete('${prefix}', ${d.id})">🗑️</span>` : '';
            }
            let h = `<div id="${msgId}" class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div><div class="msg-bubble">${c}${timeHtml}${delBtn}</div></div></div>`;
            b.insertAdjacentHTML('beforeend',h); b.scrollTop = b.scrollHeight;
        }
        if(currentChatType === '1v1' && currentChatId === d.user_id) { fetch(`/inbox/read/${d.user_id}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({uid:user.id})}).then(()=>fetchUnread()); } else { fetchUnread(); }
    };
}

async function openChat(id, name, type) {
    let changingChat = (currentChatId !== id || currentChatType !== type);
    currentChatId = id; currentChatType = type;
    document.getElementById('dm-header-name').innerText = name;
    goView('dm');
    if(type === '1v1') { await fetch(`/inbox/read/${id}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({uid:user.id})}); fetchUnread(); }
    if(changingChat) { document.getElementById('dm-list').innerHTML = ''; }
    await fetchChatMessages(id, type);
    if(changingChat || !dmWS || dmWS.readyState !== WebSocket.OPEN) { connectDmWS(id, name, type); }
}

function sendDM() { let i = document.getElementById('dm-msg'); let msg = i.value.trim(); if(msg && dmWS && dmWS.readyState === WebSocket.OPEN) { dmWS.send(msg); i.value = ''; toggleEmoji(true); } }
async function uploadDMImage(){ let f=document.getElementById('dm-file').files[0]; if(!f)return; try{ let c=await uploadToCloudinary(f); if(dmWS) dmWS.send(c.secure_url); } catch(e){alert("Erro: " + e)} }

async function loadMyComms() {
    let r = await fetch(`/communities/list/${user.id}?nocache=${new Date().getTime()}`); let d = await r.json();
    let mList = document.getElementById('my-comms-grid'); mList.innerHTML = '';
    if(d.my_comms.length === 0) mList.innerHTML = `<p style='color:#888;grid-column:1/-1;'>${t('no_bases')}</p>`;
    d.my_comms.forEach(c => { mList.innerHTML += `<div class="comm-card" onclick="openCommunity(${c.id})"><img src="${c.avatar_url}" class="comm-avatar"><b style="color:white;font-size:16px;font-family:'Rajdhani';letter-spacing:1px;">${c.name}</b></div>`; });
}

async function loadPublicComms() {
    let r = await fetch(`/communities/search?uid=${user.id}&nocache=${new Date().getTime()}`); let d = await r.json();
    let pList = document.getElementById('public-comms-grid'); pList.innerHTML = '';
    if(d.length === 0) pList.innerHTML = `<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;
    d.forEach(c => { 
        let btnStr = c.is_private ? `<button class="glass-btn" style="padding:5px 10px; width:100%; border-color:orange; color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>` : `<button class="glass-btn" style="padding:5px 10px; width:100%; border-color:#2ecc71; color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;
        pList.innerHTML += `<div class="comm-card"><img src="${c.avatar_url}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:'Rajdhani';letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`; 
    });
}

function clearCommSearch() { document.getElementById('search-comm-input').value = ''; loadPublicComms(); }
async function searchComms() {
    let q = document.getElementById('search-comm-input').value.trim();
    let r = await fetch(`/communities/search?uid=${user.id}&q=${q}&nocache=${new Date().getTime()}`); let d = await r.json();
    let pList = document.getElementById('public-comms-grid'); pList.innerHTML = '';
    if(d.length === 0) pList.innerHTML = `<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;
    d.forEach(c => { 
        let btnStr = c.is_private ? `<button class="glass-btn" style="padding:5px 10px; width:100%; border-color:orange; color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>` : `<button class="glass-btn" style="padding:5px 10px; width:100%; border-color:#2ecc71; color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;
        pList.innerHTML += `<div class="comm-card"><img src="${c.avatar_url}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:'Rajdhani';letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`; 
    });
}

async function submitCreateComm(e) {
    let n = document.getElementById('new-comm-name').value.trim(); let d = document.getElementById('new-comm-desc').value.trim(); let p = document.getElementById('new-comm-priv').value; let f = document.getElementById('comm-avatar-upload').files[0];
    if(!n) return;
    let btn = e.target; btn.disabled = true;
    try {
        let av = "https://ui-avatars.com/api/?name="+n+"&background=111&color=66fcf1";
        if(f) { let c = await uploadToCloudinary(f); av = c.secure_url; }
        let fd = new FormData(); fd.append('user_id', user.id); fd.append('name', n); fd.append('desc', d); fd.append('is_priv', p); fd.append('avatar_url', av);
        let r = await fetch('/community/create', {method:'POST', body:fd});
        if(r.ok) { document.getElementById('modal-create-comm').classList.add('hidden'); loadMyComms(); goView('mycomms', document.querySelectorAll('.nav-btn')[3]); }
    } catch(e) { } finally { btn.disabled = false; }
}

async function joinCommunity(cid) {
    let r = await fetch('/community/join', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({user_id:user.id, comm_id:cid})});
    if(r.ok) { loadPublicComms(); openCommunity(cid); }
}

async function requestCommJoin(cid) {
    let r = await fetch('/community/request/send', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({user_id:user.id, comm_id:cid})});
    if(r.ok) { let d = await r.json(); }
}

async function openCommunity(cid) {
    activeCommId = cid;
    goView('comm-dashboard'); 
    document.getElementById('comm-info-area').style.display = 'none';
    document.getElementById('comm-chat-area').style.display = 'flex';
    
    let r = await fetch(`/community/${cid}/${user.id}?nocache=${new Date().getTime()}`); let d = await r.json();
    document.getElementById('active-comm-name').innerText = "🛡️ " + d.name;
    document.getElementById('c-info-av').src = d.avatar_url; document.getElementById('c-info-name').innerText = d.name; document.getElementById('c-info-desc').innerText = d.description;
    
    let mHtml = "";
    d.members.forEach(m => { 
        let roleBadge = m.id === d.creator_id ? t('creator') : (m.role === 'admin' ? t('admin') : t('member'));
        let promoteBtn = (d.is_admin && m.id !== d.creator_id && m.role !== 'admin') ? `<button class="glass-btn" style="padding:2px 8px; font-size:10px; flex:none; margin-left:5px;" onclick="promoteMember(${cid}, ${m.id})">${t('promote')}</button>` : '';
        mHtml += `<div style="display:flex;align-items:center;gap:10px;padding:10px;border-bottom:1px solid #333;border-radius:10px;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'"><img src="${m.avatar}" onclick="openPublicProfile(${m.id})" style="width:35px;height:35px;border-radius:50%;object-fit:cover;border:1px solid #555;cursor:pointer;"> <span style="color:white;flex:1;font-weight:bold;cursor:pointer;" onclick="openPublicProfile(${m.id})">${m.name}</span> <span class="ch-badge" style="color:${m.role==='admin'||m.id===d.creator_id?'var(--primary)':'#888'}">${roleBadge}</span>${promoteBtn}</div>`; 
    });
    document.getElementById('c-info-members').innerHTML = mHtml;
    
    let addBtn = document.getElementById('c-info-admin-btn');
    let reqCont = document.getElementById('c-info-requests-container');
    let reqList = document.getElementById('c-info-requests');
    let delCont = document.getElementById('c-info-destroy-btn');
    
    if(d.is_admin) { 
        addBtn.innerHTML = `<button class="glass-btn" style="width:100%; border-color:#2ecc71; color:#2ecc71; font-size:15px; letter-spacing:2px;" onclick="document.getElementById('modal-create-channel').classList.remove('hidden')">+ ${t('create_channel')}</button>`; 
        let reqR = await fetch(`/community/${cid}/requests?uid=${user.id}`); let reqs = await reqR.json();
        if(reqs.length > 0) {
            reqCont.style.display = 'block'; reqList.innerHTML = '';
            reqs.forEach(rq => { reqList.innerHTML += `<div style="display:flex;align-items:center;gap:10px;background:rgba(0,0,0,0.5);padding:10px;border-radius:10px;"><img src="${rq.avatar}" style="width:30px;height:30px;border-radius:50%;"><span style="color:white;flex:1;">${rq.username}</span><button class="glass-btn" style="padding:5px 10px;flex:none;" onclick="handleCommReq(${rq.id}, 'accept')">✔</button><button class="glass-btn" style="padding:5px 10px;flex:none;border-color:#ff5555;color:#ff5555;" onclick="handleCommReq(${rq.id}, 'reject')">✕</button></div>`; });
        } else { reqCont.style.display = 'none'; }
    } else { addBtn.innerHTML=''; reqCont.style.display = 'none'; }

    if(d.creator_id === user.id) { delCont.innerHTML = `<button class="glass-btn danger-btn" onclick="confirmDelete('base', ${cid})">${t('destroy_base')}</button>`; } else { delCont.innerHTML = ''; }

    let cb = document.getElementById('comm-channels-bar'); cb.innerHTML = '';
    if(d.channels.length > 0) {
        d.channels.forEach(ch => { cb.innerHTML += `<button class="channel-btn" onclick="joinChannel(${ch.id}, '${ch.type}', this)">${ch.name}</button>`; });
        joinChannel(d.channels[0].id, d.channels[0].type, cb.children[0]); 
    } else { document.getElementById('comm-chat-list').innerHTML = ""; }
}

async function handleCommReq(rid, act) {
    let r = await fetch('/community/request/handle', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({req_id:rid, action:act, admin_id:user.id})});
    if(r.ok) { openCommunity(activeCommId); }
}

async function promoteMember(cid, tid) {
    let r = await fetch('/community/member/promote', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({comm_id:cid, admin_id:user.id, target_id:tid})});
    if(r.ok) { openCommunity(cid); }
}

function showCommInfo() { document.getElementById('comm-chat-area').style.display='none'; document.getElementById('comm-info-area').style.display='flex'; }
function closeComm() { goView('mycomms', document.querySelectorAll('.nav-btn')[3]); if(commWS) commWS.close(); }

async function submitCreateChannel() {
    let n = document.getElementById('new-ch-name').value.trim(); let t = document.getElementById('new-ch-type').value; let p = document.getElementById('new-ch-priv').value;
    if(!n) return;
    let r = await fetch('/community/channel/create', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({comm_id:activeCommId, user_id:user.id, name:n, type:t, is_private:parseInt(p)})});
    if(r.ok) { document.getElementById('modal-create-channel').classList.add('hidden'); openCommunity(activeCommId); }
}

async function fetchCommMessages(chid) {
    let list = document.getElementById('comm-chat-list');
    let r = await fetch(`/community/channel/${chid}/messages?nocache=${new Date().getTime()}`);
    if(r.ok) {
        let msgs = await r.json();
        let isAtBottom = (list.scrollHeight - list.scrollTop <= list.clientHeight + 50);
        msgs.forEach(d => {
            let prefix = 'comm_msg'; let msgId = `${prefix}-${d.id}`;
            if(!document.getElementById(msgId)) {
                let m = (d.user_id === user.id); let c = d.content; let delBtn = '';
                let timeHtml = d.timestamp ? `<span class="msg-time">${formatMsgTime(d.timestamp)}</span>` : '';
                if(c === '[DELETED]') { c = `<span class="msg-deleted">${t('deleted_msg')}</span>`; } 
                else {
                    if(c.startsWith('[AUDIO]')) { c = `<audio controls src="${c.replace('[AUDIO]','')}" style="max-width:200px; height:40px; outline:none;"></audio>`; }
                    else if(c.startsWith('http') && c.includes('cloudinary')) { if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) { c = `<video src="${c}" style="max-width:100%; border-radius:10px; border:1px solid #444;" controls playsinline></video>`; } else { c = `<img src="${c}" style="max-width:100%; border-radius:10px; cursor:pointer; border:1px solid #444;" onclick="window.open(this.src)">`; } }
                    delBtn = (m && d.can_delete) ? `<span class="del-msg-btn" onclick="confirmDelete('${prefix}', ${d.id})">🗑️</span>` : '';
                }
                let h = `<div id="${msgId}" class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div><div class="msg-bubble">${c}${timeHtml}${delBtn}</div></div></div>`;
                list.insertAdjacentHTML('beforeend', h);
            }
        });
        if(isAtBottom) list.scrollTop = list.scrollHeight;
    }
}

function connectCommWS(chid) {
    if(commWS) commWS.close();
    let p = location.protocol === 'https:' ? 'wss:' : 'ws:';
    commWS = new WebSocket(`${p}//${location.host}/ws/comm_${chid}/${user.id}`);
    commWS.onclose = () => { setTimeout(() => { if(activeChannelId === chid && document.getElementById('comm-chat-area').style.display==='flex') { fetchCommMessages(chid); connectCommWS(chid); } }, 2000); };
    commWS.onmessage = e => {
        let d = JSON.parse(e.data); let b = document.getElementById('comm-chat-list'); let m = parseInt(d.user_id) === parseInt(user.id); let c = d.content;
        if(d.type === 'ping') return;
        let prefix = 'comm_msg'; let msgId = `${prefix}-${d.id}`;
        if(!document.getElementById(msgId)) {
            let delBtn = ''; let timeHtml = d.timestamp ? `<span class="msg-time">${formatMsgTime(d.timestamp)}</span>` : '';
            if(c === '[DELETED]') { c = `<span class="msg-deleted">${t('deleted_msg')}</span>`; } 
            else {
                if(c.startsWith('[AUDIO]')) { c = `<audio controls src="${c.replace('[AUDIO]','')}" style="max-width:200px; height:40px; outline:none;"></audio>`; }
                else if(c.startsWith('http') && c.includes('cloudinary')) { if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) { c = `<video src="${c}" style="max-width:100%; border-radius:10px; border:1px solid #444;" controls playsinline></video>`; } else { c = `<img src="${c}" style="max-width:100%; border-radius:10px; cursor:pointer; border:1px solid #444;" onclick="window.open(this.src)">`; } }
                delBtn = (m && d.can_delete) ? `<span class="del-msg-btn" onclick="confirmDelete('${prefix}', ${d.id})">🗑️</span>` : '';
            }
            let h = `<div id="${msgId}" class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div><div class="msg-bubble">${c}${timeHtml}${delBtn}</div></div></div>`;
            b.insertAdjacentHTML('beforeend',h); b.scrollTop = b.scrollHeight;
        }
    };
}

async function joinChannel(chid, type, btnElem) {
    let changingChannel = (activeChannelId !== chid);
    activeChannelId = chid;
    document.getElementById('comm-info-area').style.display='none'; document.getElementById('comm-chat-area').style.display='flex';
    if(btnElem) { document.querySelectorAll('.channel-btn').forEach(b=>b.classList.remove('active')); btnElem.classList.add('active'); }
    
    let inp = document.getElementById('comm-msg'); let clip = document.getElementById('btn-comm-clip'); let emj = document.getElementById('btn-comm-emoji'); let mic = document.getElementById('btn-comm-mic');
    inp.disabled = false; clip.style.display = 'flex'; emj.style.display = 'flex'; mic.style.display = 'flex';
    if(type === 'media') { inp.disabled = true; inp.placeholder = t('media_only'); emj.style.display = 'none'; mic.style.display = 'none'; } 
    else if(type === 'text') { inp.placeholder = t('base_msg_placeholder'); clip.style.display = 'none'; mic.style.display = 'flex'; }
    else { inp.placeholder = t('base_msg_placeholder'); }

    if(changingChannel) { document.getElementById('comm-chat-list').innerHTML = ''; }
    await fetchCommMessages(chid);
    if(changingChannel || !commWS || commWS.readyState !== WebSocket.OPEN) { connectCommWS(chid); }
}

function sendCommMsg() { let i = document.getElementById('comm-msg'); let msg = i.value.trim(); if(msg && commWS && commWS.readyState === WebSocket.OPEN) { commWS.send(msg); i.value = ''; toggleEmoji(true); } }
async function uploadCommImage(){ let f=document.getElementById('comm-file').files[0]; if(!f)return; try{ let c=await uploadToCloudinary(f); if(commWS) commWS.send(c.secure_url); } catch(e){} }

async function openPublicProfile(uid){
    let r=await fetch(`/user/${uid}?viewer_id=${user.id}&nocache=${new Date().getTime()}`); let d=await r.json();
    document.getElementById('pub-avatar').src=d.avatar_url; let pc=document.getElementById('pub-cover'); pc.src=d.cover_url; pc.style.display='block';
    document.getElementById('pub-name').innerText=d.username; document.getElementById('pub-bio').innerText=d.bio;
    
    document.getElementById('pub-emblems').innerHTML = formatRankInfo(d.rank, d.special_emblem, d.color);
    renderMedals('pub-medals-box', d.medals);

    let ab=document.getElementById('pub-actions'); ab.innerHTML='';
    document.getElementById('pub-status-dot').setAttribute('data-uid', uid); updateStatusDots();
    
    if(d.friend_status==='friends') {
        ab.innerHTML=`<span style="color:#66fcf1; border:1px solid #66fcf1; padding:10px 15px; border-radius:12px; font-weight:bold;">${t('ally')}</span> <button class="glass-btn" style="padding:10px 20px; border-color:var(--primary); font-size:14px; max-width:180px;" onclick="openChat(${uid}, '${d.username}', '1v1')">💬 Mensagem</button>`;
    } else if(d.friend_status==='pending_sent') { ab.innerHTML=`<span style="color:orange; border:1px solid orange; padding:10px 15px; border-radius:12px;">${t('sent')}</span>`; } 
    else if(d.friend_status==='pending_received') { ab.innerHTML=`<button class="glass-btn" onclick="handleReq(${d.request_id},'accept')">${t('accept_ally')}</button>`; } 
    else { ab.innerHTML=`<button class="glass-btn" onclick="sendRequest(${uid})">${t('recruit_ally')}</button>`; }
    
    let g=document.getElementById('pub-grid'); g.innerHTML='';
    d.posts.forEach(p=>{g.innerHTML+=p.media_type==='video'?`<video src="${p.content_url}" style="width:100%; aspect-ratio:1/1; object-fit:cover;" controls></video>`:`<img src="${p.content_url}" style="width:100%; aspect-ratio:1/1; object-fit:cover; cursor:pointer;" onclick="window.open(this.src)">`});
    goView('public-profile')
}

async function uploadToCloudinary(file){
    let limiteMB = 100; if(file.size > (limiteMB * 1024 * 1024)) return Promise.reject();
    let resType = (file.type.startsWith('video') || file.type.startsWith('audio')) ? 'video' : 'image'; 
    let url = `https://api.cloudinary.com/v1_1/${CLOUD_NAME}/${resType}/upload`;
    let fd=new FormData(); fd.append('file',file); fd.append('upload_preset',UPLOAD_PRESET);
    return new Promise((res,rej)=>{
        let x=new XMLHttpRequest(); x.open('POST', url, true);
        x.upload.onprogress = (e) => { if (e.lengthComputable && document.getElementById('progress-bar')) { let p = Math.round((e.loaded / e.total) * 100); document.getElementById('progress-bar').style.width = p + '%'; document.getElementById('progress-text').innerText = p + '%'; } };
        x.onload=()=>{ if(x.status===200) res(JSON.parse(x.responseText)); else { rej(); } };
        x.onerror=()=>rej(); x.send(fd)
    });
}
async function submitPost(){let f=document.getElementById('file-upload').files[0];let cap=document.getElementById('caption-upload').value;if(!f)return;let btn=document.getElementById('btn-pub');btn.disabled=true;document.getElementById('upload-progress').style.display='block';document.getElementById('progress-text').style.display='block';try{let c = await uploadToCloudinary(f);let fd=new FormData();fd.append('user_id',user.id);fd.append('caption',cap);fd.append('content_url',c.secure_url);fd.append('media_type',c.resource_type);let r=await fetch('/post/create_from_url',{method:'POST',body:fd});if(r.ok){lastFeedHash="";loadFeed();closeUpload();loadMyHistory();updateProfileState();}}catch(e){}finally{btn.disabled=false;document.getElementById('upload-progress').style.display='none';document.getElementById('progress-text').style.display='none';document.getElementById('progress-bar').style.width='0%';}}
async function updateProfile(){let btn=document.getElementById('btn-save-profile');btn.disabled=true;try{let f=document.getElementById('avatar-upload').files[0];let c=document.getElementById('cover-upload').files[0];let b=document.getElementById('bio-update').value;let au=null,cu=null;if(f){let r=await uploadToCloudinary(f);au=r.secure_url}if(c){let r=await uploadToCloudinary(c);cu=r.secure_url}let fd=new FormData();fd.append('user_id',user.id);if(au)fd.append('avatar_url',au);if(cu)fd.append('cover_url',cu);if(b)fd.append('bio',b);let r=await fetch('/profile/update_meta',{method:'POST',body:fd});if(r.ok){let d=await r.json();Object.assign(user,d);updateUI();document.getElementById('modal-profile').classList.add('hidden');}}catch(e){}finally{btn.disabled=false;}}

function clearSearch() { document.getElementById('search-input').value = ''; document.getElementById('search-results').innerHTML = ''; }
async function searchUsers(){let q=document.getElementById('search-input').value;if(!q)return;let r=await fetch(`/users/search?q=${q}&nocache=${new Date().getTime()}`);let res=await r.json();let b=document.getElementById('search-results');b.innerHTML='';res.forEach(u=>{if(u.id!==user.id)b.innerHTML+=`<div style="padding:10px;background:rgba(255,255,255,0.05);margin-top:5px;border-radius:8px;display:flex;align-items:center;gap:10px;cursor:pointer" onclick="openPublicProfile(${u.id})"><div class="av-wrap"><img src="${u.avatar_url}" style="width:35px;height:35px;border-radius:50%;object-fit:cover;margin:0;"><div class="status-dot" data-uid="${u.id}"></div></div><span>${u.username}</span></div>`}); updateStatusDots();}
async function toggleRequests(type){let b=document.getElementById('requests-list');if(b.style.display==='block'){b.style.display='none';return}b.style.display='block';let d=await (await fetch(`/friend/requests?uid=${user.id}&nocache=${new Date().getTime()}`)).json();b.innerHTML=type==='requests'?(d.requests.length?d.requests.map(r=>`<div style="padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;">${r.username} <button class="glass-btn" style="padding:5px 10px; flex:none;" onclick="handleReq(${r.id},'accept')">${t('accept_ally')}</button></div>`).join(''):`<p style="padding:10px;color:#888;">Vazio.</p>`):(d.friends.length?d.friends.map(f=>`<div style="padding:10px;border-bottom:1px solid #333;cursor:pointer;display:flex;align-items:center;gap:10px;" onclick="openPublicProfile(${f.id})"><div class="av-wrap"><img src="${f.avatar}" style="width:30px;height:30px;border-radius:50%;"><div class="status-dot" data-uid="${f.id}" style="width:10px;height:10px;"></div></div>${f.username}</div>`).join(''):`<p style="padding:10px;color:#888;">Vazio.</p>`); updateStatusDots();}
async function sendRequest(tid){if((await fetch('/friend/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_id:tid,sender_id:user.id})})).ok){openPublicProfile(tid)}}
async function handleReq(rid,act){if((await fetch('/friend/handle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:rid,action:act})})).ok){toggleRequests('requests')}}
</script>
</body>
</html>
"""

# --- ROTAS DA API ---
@app.get("/", response_class=HTMLResponse)
async def get(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return HTMLResponse(content=html_content)

@app.get("/users/online")
async def get_online_users(db: Session=Depends(get_db)):
    active_uids = list(manager.user_connections.keys())
    if not active_uids: return []
    visible_users = db.query(User.id).filter(User.id.in_(active_uids), User.is_invisible == 0).all()
    return [u[0] for u in visible_users]

@app.post("/profile/stealth")
async def toggle_stealth(d: dict, db: Session=Depends(get_db)):
    uid = d.get("uid")
    u = db.query(User).filter(User.id == uid).first()
    if u:
        u.is_invisible = 1 if u.is_invisible == 0 else 0
        db.commit()
        return {"is_invisible": u.is_invisible}
    return {"status": "error"}

@app.get("/inbox/unread/{uid}")
async def get_unread(uid: int, db: Session=Depends(get_db)):
    unread_pms = db.query(PrivateMessage.sender_id).filter(PrivateMessage.receiver_id == uid, PrivateMessage.is_read == 0).all()
    counts = Counter([str(u[0]) for u in unread_pms])
    return {"total": sum(counts.values()), "by_sender": dict(counts)}

@app.post("/inbox/read/{sender_id}")
async def mark_read(sender_id: int, d: ReadData, db: Session=Depends(get_db)):
    db.query(PrivateMessage).filter(PrivateMessage.sender_id == sender_id, PrivateMessage.receiver_id == d.uid).update({"is_read": 1})
    db.commit()
    return {"status": "ok"}

@app.post("/auth/forgot-password")
async def forgot_password(d: ForgotPasswordData, db: Session=Depends(get_db)):
    user = db.query(User).filter(User.email == d.email).first()
    if not user: return {"status": "ok"} 
    token = create_reset_token(user.email)
    reset_link = f"https://for-glory.onrender.com/?token={token}"
    logger.info("="*60)
    logger.info(f"🚨 CHAVE DE RESGATE GERADA! COPIE O LINK ABAIXO NO NAVEGADOR: 🚨")
    logger.info(f"{reset_link}")
    logger.info("="*60)
    return {"status": "ok"}

@app.post("/auth/reset-password")
async def reset_password(d: ResetPasswordData, db: Session=Depends(get_db)):
    email = verify_reset_token(d.token)
    if not email: raise HTTPException(400, "Token inválido")
    user = db.query(User).filter(User.email == email).first()
    if not user: raise HTTPException(404, "Usuário não encontrado")
    user.password_hash = criptografar(d.new_password)
    db.commit()
    return {"status": "ok"}

@app.post("/register")
async def reg(d: RegisterData, db: Session=Depends(get_db)):
    if db.query(User).filter(User.username==d.username).first(): raise HTTPException(400, "User existe")
    is_first = db.query(User).count() == 0
    role = "fundador" if is_first else "membro"
    db.add(User(username=d.username, email=d.email, password_hash=criptografar(d.password), xp=0, is_invisible=0, role=role))
    db.commit()
    return {"status":"ok"}

@app.post("/login")
async def log(d: LoginData, db: Session=Depends(get_db)):
    u = db.query(User).filter(User.username==d.username).first()
    if not u or u.password_hash != criptografar(d.password): raise HTTPException(400, "Erro")
    b = get_user_badges(u.xp, u.id, getattr(u, 'role', 'membro'))
    return {
        "id":u.id, "username":u.username, "avatar_url":u.avatar_url, "cover_url":u.cover_url, "bio":u.bio, 
        "xp": u.xp, "rank": b['rank'], "color": b['color'], "special_emblem": b['special_emblem'], 
        "percent": b['percent'], "next_xp": b['next_xp'], "next_rank": b['next_rank'], 
        "medals": b['medals'], "is_invisible": getattr(u, 'is_invisible', 0)
    }

@app.post("/post/create_from_url")
async def create_post_url(user_id: int = Form(...), caption: str = Form(""), content_url: str = Form(...), media_type: str = Form(...), db: Session=Depends(get_db)):
    db.add(Post(user_id=user_id, content_url=content_url, media_type=media_type, caption=caption))
    user = db.query(User).filter(User.id == user_id).first()
    if user: user.xp += 50 
    db.commit()
    return {"status":"ok"}

@app.post("/post/like")
async def toggle_like(d: dict, db: Session=Depends(get_db)):
    post_id = d.get('post_id'); user_id = d.get('user_id')
    existing = db.query(Like).filter(Like.post_id==post_id, Like.user_id==user_id).first()
    if existing: db.delete(existing); liked = False
    else: db.add(Like(post_id=post_id, user_id=user_id)); liked = True
    db.commit()
    count = db.query(Like).filter(Like.post_id==post_id).count()
    return {"liked": liked, "count": count}

@app.post("/post/comment")
async def add_comment(d: CommentData, db: Session=Depends(get_db)):
    c = Comment(user_id=d.user_id, post_id=d.post_id, text=d.text)
    db.add(c); db.commit()
    return {"status": "ok"}

@app.post("/comment/delete")
async def del_comment(d: DelCommentData, db: Session=Depends(get_db)):
    c = db.query(Comment).filter(Comment.id == d.comment_id).first()
    if c and c.user_id == d.user_id: db.delete(c); db.commit()
    return {"status": "ok"}

@app.post("/message/delete")
async def delete_msg(d: dict, db: Session=Depends(get_db)):
    msg_id = d.get('msg_id'); msg_type = d.get('type'); uid = d.get('user_id')
    msg = None
    if msg_type == 'dm': msg = db.query(PrivateMessage).get(msg_id)
    elif msg_type == 'comm': msg = db.query(CommunityMessage).get(msg_id)
    elif msg_type == 'group': msg = db.query(GroupMessage).get(msg_id)
    
    if msg and msg.sender_id == uid:
        if (datetime.utcnow() - msg.timestamp).total_seconds() > 300:
            return {"status": "timeout", "msg": "Tempo limite (5min) excedido."}
        msg.content = "[DELETED]"
        db.commit()
        return {"status": "ok"}
    return {"status": "error"}

@app.get("/post/{post_id}/comments")
async def get_comments(post_id: int, db: Session=Depends(get_db)):
    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.timestamp.asc()).all()
    res = []
    for c in comments:
        b = get_user_badges(c.author.xp, c.author.id, getattr(c.author, 'role', 'membro'))
        res.append({"id": c.id, "text": c.text, "author_name": c.author.username, "author_avatar": c.author.avatar_url, "author_id": c.author.id, "author_rank": b['rank'], "color": b['color'], "special_emblem": b['special_emblem']})
    return res

@app.get("/posts")
async def get_posts(uid: int, limit: int = 50, db: Session=Depends(get_db)):
    posts = db.query(Post).order_by(Post.timestamp.desc()).limit(limit).all()
    result = []
    for p in posts:
        like_count = db.query(Like).filter(Like.post_id == p.id).count()
        user_liked = db.query(Like).filter(Like.post_id == p.id, Like.user_id == uid).first() is not None
        comment_count = db.query(Comment).filter(Comment.post_id == p.id).count()
        b = get_user_badges(p.author.xp, p.author.id, getattr(p.author, 'role', 'membro'))
        result.append({"id": p.id, "content_url": p.content_url, "media_type": p.media_type, "caption": p.caption, "author_name": p.author.username, "author_avatar": p.author.avatar_url, "author_rank": b['rank'], "rank_color": b['color'], "special_emblem": b['special_emblem'], "author_id": p.author.id, "likes": like_count, "user_liked": user_liked, "comments": comment_count})
    return result

@app.post("/post/delete")
async def delete_post_endpoint(d: DeletePostData, db: Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id == d.post_id).first()
    if not post or post.user_id != d.user_id: return {"status": "error"}
    db.query(Like).filter(Like.post_id == post.id).delete()
    db.query(Comment).filter(Comment.post_id == post.id).delete()
    db.delete(post)
    user = db.query(User).filter(User.id == d.user_id).first()
    if user and user.xp >= 50: user.xp -= 50
    db.commit()
    return {"status": "ok"}

@app.post("/profile/update_meta")
async def update_prof_meta(user_id: int = Form(...), bio: str = Form(None), avatar_url: str = Form(None), cover_url: str = Form(None), db: Session=Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if avatar_url: u.avatar_url = avatar_url
    if cover_url: u.cover_url = cover_url
    if bio: u.bio = bio
    db.commit()
    return {"status":"ok"}

@app.get("/users/search")
async def search_users(q: str, db: Session=Depends(get_db)):
    users = db.query(User).filter(User.username.ilike(f"%{q}%")).limit(10).all()
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in users]

@app.get("/inbox/{uid}")
async def get_inbox(uid: int, db: Session=Depends(get_db)):
    me = db.query(User).filter(User.id == uid).first()
    friends_data = [{"id": f.id, "name": f.username, "avatar": f.avatar_url} for f in me.friends]
    my_groups = db.query(GroupMember).filter(GroupMember.user_id == uid).all()
    groups_data = []
    for gm in my_groups:
        grp = db.query(ChatGroup).filter(ChatGroup.id == gm.group_id).first()
        if grp: groups_data.append({"id": grp.id, "name": grp.name, "avatar": "https://ui-avatars.com/api/?name=G&background=111&color=66fcf1"})
    return {"friends": friends_data, "groups": groups_data}

@app.get("/dms/{target_id}")
async def get_dms(target_id: int, uid: int, db: Session=Depends(get_db)):
    msgs = db.query(PrivateMessage).filter(or_(and_(PrivateMessage.sender_id == uid, PrivateMessage.receiver_id == target_id),and_(PrivateMessage.sender_id == target_id, PrivateMessage.receiver_id == uid))).order_by(PrivateMessage.timestamp.asc()).limit(100).all()
    res = []
    for m in msgs:
        b = get_user_badges(m.sender.xp, m.sender.id, getattr(m.sender, 'role', 'membro'))
        res.append({"id": m.id, "user_id": m.sender_id, "content": m.content, "timestamp": get_utc_iso(m.timestamp), "avatar": m.sender.avatar_url, "username": m.sender.username, "rank": b['rank'], "color": b['color'], "special_emblem": b['special_emblem'], "can_delete": (datetime.utcnow() - m.timestamp).total_seconds() <= 300})
    return res

@app.post("/community/create")
async def create_comm(user_id: int=Form(...), name: str=Form(...), desc: str=Form(""), is_priv: int=Form(0), avatar_url: str=Form(...), db: Session=Depends(get_db)):
    c = Community(name=name, description=desc, avatar_url=avatar_url, is_private=is_priv, creator_id=user_id)
    db.add(c); db.commit(); db.refresh(c)
    db.add(CommunityMember(comm_id=c.id, user_id=user_id, role="admin"))
    db.add(CommunityChannel(comm_id=c.id, name="geral", channel_type="livre", is_private=0))
    db.commit()
    return {"status": "ok"}

@app.post("/community/{cid}/delete")
async def destroy_comm(cid: int, user_id: int = Form(...), db: Session=Depends(get_db)):
    c = db.query(Community).get(cid)
    if not c or c.creator_id != user_id: return {"status": "error"}
    ch_ids = [ch.id for ch in db.query(CommunityChannel).filter_by(comm_id=cid).all()]
    if ch_ids: db.query(CommunityMessage).filter(CommunityMessage.channel_id.in_(ch_ids)).delete(synchronize_session=False)
    db.query(CommunityChannel).filter_by(comm_id=cid).delete()
    db.query(CommunityMember).filter_by(comm_id=cid).delete()
    db.query(CommunityRequest).filter_by(comm_id=cid).delete()
    db.delete(c); db.commit()
    return {"status": "ok"}

@app.post("/community/member/promote")
async def promote_member(d: dict, db: Session=Depends(get_db)):
    c = db.query(Community).get(d['comm_id'])
    admin = db.query(CommunityMember).filter_by(comm_id=c.id, user_id=d['admin_id']).first()
    if not admin or (admin.role != 'admin' and c.creator_id != admin.user_id): return {"status": "error"}
    target = db.query(CommunityMember).filter_by(comm_id=c.id, user_id=d['target_id']).first()
    if target: target.role = 'admin'; db.commit()
    return {"status": "ok"}

@app.get("/communities/list/{uid}")
async def list_comms(uid: int, db: Session=Depends(get_db)):
    my_memberships = db.query(CommunityMember).filter(CommunityMember.user_id == uid).all()
    my_comm_ids = [m.comm_id for m in my_memberships]
    my_comms = db.query(Community).filter(Community.id.in_(my_comm_ids)).all()
    return {"my_comms": [{"id": c.id, "name": c.name, "avatar_url": c.avatar_url} for c in my_comms]}

@app.get("/communities/search")
async def search_comms(uid: int, q: str = "", db: Session=Depends(get_db)):
    my_memberships = db.query(CommunityMember).filter(CommunityMember.user_id == uid).all()
    my_comm_ids = [m.comm_id for m in my_memberships]
    query = db.query(Community).filter(~Community.id.in_(my_comm_ids))
    if q: query = query.filter(Community.name.ilike(f"%{q}%"))
    comms = query.limit(20).all()
    return [{"id": c.id, "name": c.name, "avatar_url": c.avatar_url, "desc": c.description, "is_private": c.is_private} for c in comms]

@app.post("/community/request/send")
async def send_comm_req(d: JoinCommData, db: Session=Depends(get_db)):
    c = db.query(Community).get(d.comm_id)
    if not c: return {"status": "error"}
    if c.is_private == 0:
        if not db.query(CommunityMember).filter_by(comm_id=c.id, user_id=d.user_id).first():
            db.add(CommunityMember(comm_id=c.id, user_id=d.user_id, role="member")); db.commit()
        return {"status": "joined"}
    else:
        ext = db.query(CommunityRequest).filter_by(comm_id=c.id, user_id=d.user_id).first()
        if not ext: db.add(CommunityRequest(comm_id=c.id, user_id=d.user_id)); db.commit()
        return {"status": "requested"}

@app.get("/community/{cid}/requests")
async def get_comm_reqs(cid: int, uid: int, db: Session=Depends(get_db)):
    role = db.query(CommunityMember).filter_by(comm_id=cid, user_id=uid).first()
    if not role or role.role != "admin": return []
    reqs = db.query(CommunityRequest).filter_by(comm_id=cid).all()
    return [{"id": r.id, "user_id": r.user.id, "username": r.user.username, "avatar": r.user.avatar_url} for r in reqs]

@app.post("/community/request/handle")
async def handle_comm_req(d: HandleCommReqData, db: Session=Depends(get_db)):
    req = db.query(CommunityRequest).filter_by(id=d.req_id).first()
    if not req: return {"status": "error"}
    role = db.query(CommunityMember).filter_by(comm_id=req.comm_id, user_id=d.admin_id).first()
    if not role or role.role != "admin": return {"status": "unauthorized"}
    if d.action == "accept": db.add(CommunityMember(comm_id=req.comm_id, user_id=req.user_id, role="member"))
    db.delete(req); db.commit()
    return {"status": "ok"}

@app.get("/community/{cid}/{uid}")
async def get_comm_details(cid: int, uid: int, db: Session=Depends(get_db)):
    c = db.query(Community).get(cid)
    my_role = db.query(CommunityMember).filter_by(comm_id=cid, user_id=uid).first()
    is_admin = my_role and my_role.role == "admin"
    channels = db.query(CommunityChannel).filter_by(comm_id=cid).all()
    visible_channels = [{"id": ch.id, "name": ch.name, "type": ch.channel_type} for ch in channels if ch.is_private == 0 or is_admin]
    members = db.query(CommunityMember).filter_by(comm_id=cid).all()
    members_data = [{"id": m.user.id, "name": m.user.username, "avatar": m.user.avatar_url, "role": m.role} for m in members]
    return {"name": c.name, "description": c.description, "avatar_url": c.avatar_url, "is_admin": is_admin, "creator_id": c.creator_id, "channels": visible_channels, "members": members_data}

@app.post("/community/channel/create")
async def create_channel(d: dict, db: Session=Depends(get_db)):
    role = db.query(CommunityMember).filter_by(comm_id=d['comm_id'], user_id=d['user_id']).first()
    if not role or role.role != "admin": return {"status": "error"}
    db.add(CommunityChannel(comm_id=d['comm_id'], name=d['name'], channel_type=d['type'], is_private=d['is_private'])); db.commit()
    return {"status": "ok"}

@app.get("/community/channel/{chid}/messages")
async def get_comm_msgs(chid: int, db: Session=Depends(get_db)):
    msgs = db.query(CommunityMessage).filter_by(channel_id=chid).order_by(CommunityMessage.timestamp.asc()).limit(100).all()
    res = []
    for m in msgs:
        b = get_user_badges(m.sender.xp, m.sender.id, getattr(m.sender, 'role', 'membro'))
        res.append({"id": m.id, "user_id": m.sender_id, "content": m.content, "timestamp": get_utc_iso(m.timestamp), "avatar": m.sender.avatar_url, "username": m.sender.username, "rank": b['rank'], "color": b['color'], "special_emblem": b['special_emblem'], "can_delete": (datetime.utcnow() - m.timestamp).total_seconds() <= 300})
    return res

@app.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int):
    await manager.connect(ws, ch, uid)
    try:
        while True:
            txt = await ws.receive_text()
            db = SessionLocal()
            msg_id = None
            now_iso = datetime.utcnow().isoformat() + "Z"
            try:
                u_fresh = db.query(User).filter(User.id == uid).first()
                if ch.startswith("dm_"):
                    parts = ch.split("_")
                    rec_id = int(parts[2]) if uid == int(parts[1]) else int(parts[1])
                    new_msg = PrivateMessage(sender_id=uid, receiver_id=rec_id, content=txt, is_read=0)
                    db.add(new_msg); db.commit(); db.refresh(new_msg)
                    msg_id = new_msg.id
                    now_iso = get_utc_iso(new_msg.timestamp)
                elif ch.startswith("comm_"):
                    chid = int(ch.split("_")[1])
                    new_msg = CommunityMessage(channel_id=chid, sender_id=uid, content=txt)
                    db.add(new_msg); db.commit(); db.refresh(new_msg)
                    msg_id = new_msg.id
                    now_iso = get_utc_iso(new_msg.timestamp)
                elif ch.startswith("group_"):
                    grid = int(ch.split("_")[1])
                    new_msg = GroupMessage(group_id=grid, sender_id=uid, content=txt)
                    db.add(new_msg); db.commit(); db.refresh(new_msg)
                    msg_id = new_msg.id
                    now_iso = get_utc_iso(new_msg.timestamp)
                
                if msg_id:
                    b = get_user_badges(u_fresh.xp, u_fresh.id, getattr(u_fresh, 'role', 'membro'))
                    user_data = {
                        "id": msg_id, "user_id": u_fresh.id, "username": u_fresh.username, 
                        "avatar": u_fresh.avatar_url, "content": txt, "can_delete": True, 
                        "timestamp": now_iso, "rank": b['rank'], "color": b['color'], "special_emblem": b['special_emblem']
                    }
                    await manager.broadcast(user_data, ch)
                    if ch.startswith("dm_") or ch.startswith("group_"): 
                        await manager.broadcast({"type": "ping"}, "Geral")
            except Exception as e: db.rollback()
            finally: db.close()
    except Exception:
        manager.disconnect(ws, ch, uid)

@app.post("/group/create")
async def create_group(d: CreateGroupData, db: Session=Depends(get_db)):
    grp = ChatGroup(name=d.name)
    db.add(grp); db.commit(); db.refresh(grp)
    db.add(GroupMember(group_id=grp.id, user_id=d.creator_id))
    for mid in d.member_ids: db.add(GroupMember(group_id=grp.id, user_id=mid))
    db.commit()
    return {"status": "ok"}

@app.get("/group/{group_id}/messages")
async def get_group_msgs(group_id: int, db: Session=Depends(get_db)):
    msgs = db.query(GroupMessage).filter(GroupMessage.group_id == group_id).order_by(GroupMessage.timestamp.asc()).limit(100).all()
    res = []
    for m in msgs:
        b = get_user_badges(m.sender.xp, m.sender.id, getattr(m.sender, 'role', 'membro'))
        res.append({"id": m.id, "user_id": m.sender_id, "content": m.content, "timestamp": get_utc_iso(m.timestamp), "avatar": m.sender.avatar_url, "username": m.sender.username, "rank": b['rank'], "color": b['color'], "special_emblem": b['special_emblem'], "can_delete": (datetime.utcnow() - m.timestamp).total_seconds() <= 300})
    return res

@app.post("/friend/request")
async def send_req(d: dict, db: Session=Depends(get_db)):
    sender_id = d.get('sender_id'); target_id = d.get('target_id')
    me = db.query(User).filter(User.id == sender_id).first()
    target = db.query(User).filter(User.id == target_id).first()
    if target in me.friends: return {"status": "already_friends"}
    existing = db.query(FriendRequest).filter(or_(and_(FriendRequest.sender_id==sender_id, FriendRequest.receiver_id==target_id),and_(FriendRequest.sender_id==target_id, FriendRequest.receiver_id==sender_id))).first()
    if existing: return {"status": "pending"}
    db.add(FriendRequest(sender_id=sender_id, receiver_id=target_id)); db.commit()
    return {"status": "sent"}

@app.get("/friend/requests")
async def get_reqs(uid: int, db: Session=Depends(get_db)):
    reqs = db.query(FriendRequest).filter(FriendRequest.receiver_id == uid).all()
    requests_data = [{"id": r.id, "username": db.query(User).filter(User.id == r.sender_id).first().username} for r in reqs]
    me = db.query(User).filter(User.id == uid).first()
    friends_data = [{"id": f.id, "username": f.username, "avatar": f.avatar_url} for f in me.friends]
    return {"requests": requests_data, "friends": friends_data}

@app.post("/friend/handle")
async def handle_req(d: RequestActionData, db: Session=Depends(get_db)):
    req = db.query(FriendRequest).filter(FriendRequest.id == d.request_id).first()
    if not req: return {"status": "error"}
    if d.action == 'accept':
        u1 = db.query(User).filter(User.id == req.sender_id).first()
        u2 = db.query(User).filter(User.id == req.receiver_id).first()
        u1.friends.append(u2); u2.friends.append(u1)
    db.delete(req); db.commit()
    return {"status": "ok"}

@app.get("/user/{target_id}")
async def get_user_profile(target_id: int, viewer_id: int, db: Session=Depends(get_db)):
    target = db.query(User).filter(User.id == target_id).first()
    viewer = db.query(User).filter(User.id == viewer_id).first()
    posts = db.query(Post).filter(Post.user_id == target_id).order_by(Post.timestamp.desc()).all()
    posts_data = [{"content_url": p.content_url, "media_type": p.media_type} for p in posts]
    status = "friends" if target in viewer.friends else "none"
    req_id = None
    if status == "none":
        sent = db.query(FriendRequest).filter(FriendRequest.sender_id == viewer_id, FriendRequest.receiver_id == target_id).first()
        received = db.query(FriendRequest).filter(FriendRequest.sender_id == target_id, FriendRequest.receiver_id == viewer_id).first()
        if sent: status = "pending_sent"
        if received: status = "pending_received"; req_id = received.id
        
    b = get_user_badges(target.xp, target.id, getattr(target, 'role', 'membro'))
    return {"username": target.username, "avatar_url": target.avatar_url, "cover_url": target.cover_url, "bio": target.bio, "rank": b['rank'], "color": b['color'], "special_emblem": b['special_emblem'], "medals": b['medals'], "percent": b['percent'], "next_xp": b['next_xp'], "next_rank": b['next_rank'], "posts": posts_data, "friend_status": status, "request_id": req_id}

@app.get("/agora-config")
async def get_agora_config():
    return {"app_id": AGORA_APP_ID}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
