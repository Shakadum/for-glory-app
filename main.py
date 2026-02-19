import uvicorn
import json
import hashlib
import random
import os
import logging
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

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForGlory")

# --- SEGURANÇA E E-MAIL ---
SECRET_KEY = os.environ.get("SECRET_KEY", "sua_chave_secreta_super_segura_123")
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

# --- CLOUDINARY ---
cloudinary.config( 
  cloud_name = os.environ.get('CLOUDINARY_NAME'), 
  api_key = os.environ.get('CLOUDINARY_KEY'), 
  api_secret = os.environ.get('CLOUDINARY_SECRET'),
  secure = True
)

# --- BANCO DE DADOS (BLINDADO) ---
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./for_glory_v3.db")

if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False, "timeout": 15},
        pool_size=10, 
        max_overflow=20
    )
else:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

friendship = Table(
    'friendships', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('friend_id', Integer, ForeignKey('users.id'), primary_key=True)
)

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
    friends = relationship("User", secondary=friendship, primaryjoin=id==friendship.c.user_id, secondaryjoin=id==friendship.c.friend_id, backref="friended_by")

class FriendRequest(Base):
    __tablename__ = "friend_requests"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.now)
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content_url = Column(String)
    media_type = Column(String)
    caption = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
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
    timestamp = Column(DateTime, default=datetime.now)
    author = relationship("User")

class PrivateMessage(Base):
    __tablename__ = "private_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    is_read = Column(Integer, default=0) 
    timestamp = Column(DateTime, default=datetime.now)
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

class ChatGroup(Base):
    __tablename__ = "chat_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("chat_groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")

class GroupMessage(Base):
    __tablename__ = "group_messages"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("chat_groups.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    sender = relationship("User", foreign_keys=[sender_id])

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error(f"Erro BD: {e}")

def calcular_patente(xp):
    if xp < 100: return "Recruta 🔰"
    if xp < 500: return "Soldado ⚔️"
    if xp < 1000: return "Cabo 🎖️"
    if xp < 2000: return "3º Sargento 🎗️"
    if xp < 5000: return "Capitão 👑"
    return "Lenda 🐲"

def create_reset_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=30) 
    to_encode = {"sub": email, "exp": expire, "type": "reset"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset": return None
        return payload.get("sub") 
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
            if self.user_connections[uid] <= 0:
                del self.user_connections[uid]

    async def broadcast(self, msg: dict, chan: str):
        for conn in self.active.get(chan, []):
            try: await conn.send_text(json.dumps(msg))
            except: pass

manager = ConnectionManager()
app = FastAPI(title="For Glory Cloud")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
class CreateGroupData(BaseModel): name: str; creator_id: int; member_ids: List[int]
class ReadData(BaseModel): uid: int 

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def criptografar(s): return hashlib.sha256(s.encode()).hexdigest()

@app.on_event("startup")
def startup():
    if "sqlite" in str(engine.url):
        with engine.connect() as conn:
            try: conn.execute(text("PRAGMA journal_mode=WAL;")); conn.commit()
            except: pass
            
    # Executando updates separadamente para não envenenar transações no PostgreSQL
    for query in [
        "ALTER TABLE users ADD COLUMN is_invisible INTEGER DEFAULT 0",
        "ALTER TABLE private_messages ADD COLUMN is_read INTEGER DEFAULT 0"
    ]:
        try:
            with engine.connect() as conn:
                conn.execute(text(query))
                conn.commit()
        except Exception:
            pass # A coluna já existe
        
    db = SessionLocal()
    try:
        if not db.query(Channel).first():
            db.add(Channel(name="Geral"))
            db.commit()
    except: pass
    finally: db.close()

# --- FRONTEND COMPLETO ---
html_content = r"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Rajdhani:wght@600;700&display=swap" rel="stylesheet">
<title>For Glory</title>
<style>
:root{--primary:#66fcf1;--dark-bg:#0b0c10;--card-bg:#1f2833;--glass:rgba(31, 40, 51, 0.7);--border:rgba(102,252,241,0.15)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;scrollbar-width:thin;scrollbar-color:var(--primary) #111}
body{background-color:var(--dark-bg);background-image:radial-gradient(circle at 50% 0%, #1a1d26 0%, #0b0c10 70%);color:#e0e0e0;font-family:'Inter',sans-serif;margin:0;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
#app{display:flex;flex:1;overflow:hidden;position:relative}

#sidebar{width:80px;background:rgba(11,12,16,0.6);backdrop-filter:blur(12px);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:20px 0;z-index:20}
.nav-btn{width:50px;height:50px;border-radius:14px;border:none;background:transparent;color:#888;font-size:24px;margin-bottom:20px;cursor:pointer;transition:0.3s;position:relative;}
.nav-btn.active{background:rgba(102,252,241,0.15);color:var(--primary);border:1px solid var(--border);box-shadow:0 0 15px rgba(102,252,241,0.2);transform:scale(1.05)}
.my-avatar-mini{width:45px;height:45px;border-radius:50%;object-fit:cover;border:2px solid var(--border); background:#111;}
.nav-badge { position:absolute; top:-2px; right:-2px; background:#ff5555; color:white; font-size:11px; font-weight:bold; padding:2px 6px; border-radius:10px; display:none; z-index:10; box-shadow:0 0 5px #ff5555; border:2px solid var(--dark-bg); font-family:'Inter',sans-serif; }
.list-badge { background:#ff5555; color:white; font-size:12px; font-weight:bold; padding:2px 8px; border-radius:12px; display:none; box-shadow:0 0 5px #ff5555; font-family:'Inter',sans-serif; }

#content-area{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden}
.view{display:none;flex:1;flex-direction:column;overflow-y:auto;height:100%;width:100%;padding-bottom:20px}
.view.active{display:flex;animation:fadeIn 0.3s ease-out}

#feed-container{flex:1;overflow-y:auto;padding:20px 0;padding-bottom:100px;display:flex;flex-direction:column;align-items:center; gap:20px;}
.post-card{background:var(--card-bg);width:100%;max-width:480px;border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.05); overflow:hidden; display:flex; flex-direction:column; flex-shrink:0;}
.post-header{padding:12px 15px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.2)}
.post-av{width:42px;height:42px;border-radius:50%;margin-right:12px;object-fit:cover;border:1px solid var(--primary); background:#111;}
.rank-badge{font-size:10px;color:var(--primary);font-weight:bold;text-transform:uppercase;background:rgba(102,252,241,0.1);padding:3px 8px;border-radius:6px;border:1px solid rgba(102,252,241,0.3)}

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
.comment-row { display: flex; gap: 10px; margin-bottom: 12px; font-size: 13px; animation: fadeIn 0.3s; }
.comment-av { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; border: 1px solid #444; cursor:pointer; }
.comment-input-area { display: flex; gap: 8px; margin-top: 15px; align-items: center; }
.comment-inp { flex: 1; background: rgba(255,255,255,0.05); border: 1px solid #444; border-radius: 20px; padding: 10px 15px; color: white; outline: none; font-size: 13px; }
.comment-inp:focus { border-color: var(--primary); }

#chat-list, #dm-list {flex:1;overflow-y:auto;padding:15px;display:flex;flex-direction:column;gap:12px}
.msg-row{display:flex;gap:10px;max-width:85%}
.msg-row.mine{align-self:flex-end;flex-direction:row-reverse}
.msg-av{width:36px;height:36px;border-radius:50%;object-fit:cover; background:#111; cursor:pointer;}
.msg-bubble{padding:10px 16px;border-radius:18px;background:#2b343f;color:#e0e0e0;word-break:break-word;font-size:15px}
.msg-row.mine .msg-bubble{background:linear-gradient(135deg,#1d4e4f,#133638);color:white;border:1px solid rgba(102,252,241,0.2)}
.chat-input-area {background:rgba(11,12,16,0.9);padding:15px;display:flex;gap:10px;align-items:center;border-top:1px solid var(--border)}
.chat-msg {flex:1;background:rgba(255,255,255,0.05);border:1px solid #444;border-radius:24px;padding:12px 20px;color:white;outline:none}

.chat-box-centered { width: 100%; max-width: 600px; height: 85vh; margin: auto; background: var(--card-bg); border-radius: 16px; border: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }

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
.modal-box{background:rgba(20,25,35,0.95);padding:30px;border-radius:24px;border:1px solid var(--border);width:90%;max-width:380px;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,0.8);animation:scaleUp 0.3s}
.inp{width:100%;padding:14px;margin:10px 0;background:rgba(0,0,0,0.3);border:1px solid #444;color:white;border-radius:10px;text-align:center;font-size:16px}
.btn-main{width:100%;padding:14px;margin-top:15px;background:var(--primary);border:none;font-weight:700;border-radius:10px;cursor:pointer;font-size:16px;color:#0b0c10;text-transform:uppercase}
.btn-link{background:none;border:none;color:#888;text-decoration:underline;cursor:pointer;margin-top:15px;font-size:14px}
#toast{visibility:hidden;opacity:0;min-width:200px;background:var(--primary);color:#000;text-align:center;border-radius:50px;padding:12px 24px;position:fixed;z-index:9999;left:50%;top:30px;transform:translateX(-50%);font-weight:bold;transition:0.3s}
#toast.show{visibility:visible;opacity:1}
.hidden{display:none !important}
@keyframes fadeIn{from{opacity:0;transform:scale(0.98)}to{opacity:1;transform:scale(1)}}
@keyframes scaleUp{from{transform:scale(0.8);opacity:0}to{transform:scale(1);opacity:1}}
@media(max-width:768px){#app{flex-direction:column-reverse}#sidebar{width:100%;height:65px;flex-direction:row;justify-content:space-around;padding:0;border-top:1px solid var(--border);border-right:none;background:rgba(11,12,16,0.95)}.btn-float{bottom:80px}}
</style>
</head>
<body>
<div id="toast">Notificação</div>

<div id="emoji-picker" style="position:absolute;bottom:80px;right:10px;width:90%;max-width:320px;background:rgba(20,25,35,0.95);border:1px solid var(--border);border-radius:15px;display:none;flex-direction:column;z-index:10001;box-shadow:0 0 25px rgba(0,0,0,0.8);backdrop-filter:blur(10px)">
    <div style="padding:10px 15px;display:flex;justify-content:space-between;border-bottom:1px solid #333"><span style="color:var(--primary);font-weight:bold;font-family:'Rajdhani'">EMOJIS</span><span onclick="toggleEmoji(true)" style="color:#ff5555;cursor:pointer;font-weight:bold">✕</span></div>
    <div id="emoji-grid" style="display:grid;grid-template-columns:repeat(7,1fr);gap:5px;padding:10px;max-height:220px;overflow-y:auto"></div>
</div>

<div id="modal-login" class="modal">
    <div class="modal-box">
        <h1 style="color:var(--primary);font-family:'Rajdhani';font-size:42px;margin:0 0 10px 0">FOR GLORY</h1>
        <div id="login-form">
            <input id="l-user" class="inp" placeholder="CODINOME">
            <input id="l-pass" class="inp" type="password" placeholder="SENHA" onkeypress="if(event.key==='Enter')doLogin()">
            <button onclick="doLogin()" class="btn-main">ENTRAR</button>
            <div style="margin-top:20px;display:flex;justify-content:space-between">
                <span onclick="toggleAuth('register')" class="btn-link" style="color:white;text-decoration:none;">Criar Conta</span>
                <span onclick="toggleAuth('forgot')" class="btn-link" style="color:var(--primary);text-decoration:none;">Esqueci Senha</span>
            </div>
        </div>
        <div id="register-form" class="hidden">
            <input id="r-user" class="inp" placeholder="NOVO USUÁRIO">
            <input id="r-email" class="inp" placeholder="EMAIL (Real)">
            <input id="r-pass" class="inp" type="password" placeholder="SENHA">
            <button onclick="doRegister()" class="btn-main">ALISTAR-SE</button>
            <p onclick="toggleAuth('login')" class="btn-link">Voltar</p>
        </div>
        <div id="forgot-form" class="hidden">
            <h3 style="color:white">RECUPERAR ACESSO</h3>
            <input id="f-email" class="inp" placeholder="SEU EMAIL CADASTRADO">
            <button onclick="requestReset()" class="btn-main">ENVIAR LINK</button>
            <p onclick="toggleAuth('login')" class="btn-link">Voltar</p>
        </div>
        <div id="reset-form" class="hidden">
            <h3 style="color:var(--primary)">NOVA SENHA</h3>
            <input id="new-pass" class="inp" type="password" placeholder="NOVA SENHA">
            <button onclick="doResetPassword()" class="btn-main">SALVAR SENHA</button>
        </div>
    </div>
</div>

<div id="modal-delete" class="modal hidden">
    <div class="modal-box" style="border-color: rgba(255, 85, 85, 0.3);">
        <h2 style="color:#ff5555; font-family:'Rajdhani'; margin-top:0;">CONFIRMAR BAIXA</h2>
        <p style="color:#ccc; margin: 15px 0; font-size:15px;">Tem certeza que deseja excluir esta missão do registro oficial?</p>
        <div style="display:flex; gap:10px; margin-top:20px;">
            <button id="btn-confirm-delete" class="btn-main" style="background:#ff5555; color:white; margin-top:0;">EXCLUIR</button>
            <button onclick="document.getElementById('modal-delete').classList.add('hidden')" class="btn-main" style="background:transparent; border:1px solid #444; color:#888; margin-top:0;">CANCELAR</button>
        </div>
    </div>
</div>

<div id="modal-create-group" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;">NOVO ESQUADRÃO</h2>
        <input id="new-group-name" class="inp" placeholder="Nome do Grupo">
        <p style="color:#888;font-size:12px;text-align:left;margin-bottom:5px;">Selecione os aliados:</p>
        <div id="group-friends-list" style="max-height:150px; overflow-y:auto; text-align:left; margin-bottom:15px; background:rgba(0,0,0,0.3); padding:10px; border-radius:10px;"></div>
        <div style="display:flex; gap:10px;">
            <button onclick="submitCreateGroup()" class="btn-main" style="margin-top:0;">CRIAR</button>
            <button onclick="document.getElementById('modal-create-group').classList.add('hidden')" class="btn-main" style="background:transparent; border:1px solid #444; color:#888; margin-top:0;">CANCELAR</button>
        </div>
    </div>
</div>

<div id="modal-upload" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:white">NOVO POST</h2>
        <input type="file" id="file-upload" class="inp" accept="image/*,video/*" style="margin-bottom: 5px;">
        <span style="color:#ffaa00; font-size:11px; display:block; text-align:left; padding-left:5px; font-weight:bold;">⚠️ Limite por arquivo: 100MB</span>
        <div style="display:flex;gap:5px;align-items:center;margin-bottom:10px;margin-top:10px">
            <input type="text" id="caption-upload" class="inp" placeholder="Legenda..." style="margin:0">
            <button onclick="openEmoji('caption-upload')" style="background:none;border:none;font-size:24px;cursor:pointer">😀</button>
        </div>
        <div id="upload-progress" style="display:none;background:#333;height:6px;border-radius:3px;margin-top:10px;overflow:hidden"><div id="progress-bar" style="width:0%;height:100%;background:var(--primary);transition:width 0.2s"></div></div>
        <div id="progress-text" style="color:var(--primary);font-size:12px;margin-top:5px;display:none;font-weight:bold">0%</div>
        <button id="btn-pub" onclick="submitPost()" class="btn-main">PUBLICAR (+50 XP)</button>
        <button onclick="closeUpload()" class="btn-link" style="color:#888;display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none">CANCELAR</button>
    </div>
</div>

<div id="modal-profile" class="modal hidden"><div class="modal-box"><h2 style="color:var(--primary)">EDITAR PERFIL</h2><label style="color:#aaa;display:block;margin-top:10px;font-size:12px;">Foto de Perfil</label><input type="file" id="avatar-upload" class="inp" accept="image/*"><span style="color:#ffaa00; font-size:11px; display:block; text-align:left; padding-left:5px; margin-top:-5px; margin-bottom:5px;">⚠️ Limite: 100MB</span><label style="color:#aaa;display:block;margin-top:10px;font-size:12px;">Capa de Fundo</label><input type="file" id="cover-upload" class="inp" accept="image/*"><span style="color:#ffaa00; font-size:11px; display:block; text-align:left; padding-left:5px; margin-top:-5px; margin-bottom:5px;">⚠️ Limite: 100MB</span><input id="bio-update" class="inp" placeholder="Escreva sua Bio..."><button id="btn-save-profile" onclick="updateProfile()" class="btn-main">SALVAR</button><button onclick="document.getElementById('modal-profile').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none">FECHAR</button></div></div>

<div id="app">
    <div id="sidebar">
        <button class="nav-btn" onclick="goView('profile')"><img id="nav-avatar" src="" class="my-avatar-mini" onerror="this.src='https://ui-avatars.com/api/?name=User&background=111&color=66fcf1'"></button>
        <button class="nav-btn" onclick="goView('chat')">💬</button>
        <button class="nav-btn active" onclick="goView('feed')">🎬</button>
        <button class="nav-btn" onclick="goView('inbox')" style="position:relative;">📩<div id="inbox-badge" class="nav-badge"></div></button>
    </div>

    <div id="content-area">
        
        <div id="view-feed" class="view active">
            <div id="feed-container"></div>
            <button class="btn-float" onclick="document.getElementById('modal-upload').classList.remove('hidden')">+</button>
        </div>

        <div id="view-chat" class="view">
            <div style="padding:15px;text-align:center;color:var(--primary);font-family:'Rajdhani';font-weight:bold;background:rgba(0,0,0,0.2);letter-spacing:2px;">CANAL GERAL</div>
            <div id="chat-list"></div>
            <form class="chat-input-area" onsubmit="sendMsg(); return false;">
                <input type="file" id="chat-file" class="hidden" onchange="uploadChatImage()" accept="image/*,video/*">
                <button type="button" onclick="document.getElementById('chat-file').click()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#888">📎</button>
                <input id="chat-msg" class="chat-msg" placeholder="Mensagem..." autocomplete="off">
                <button type="button" onclick="openEmoji('chat-msg')" style="background:none;border:none;font-size:24px;cursor:pointer;margin-right:5px">😀</button>
                <button type="submit" style="background:var(--primary);border:none;min-width:45px;height:45px;border-radius:12px;font-weight:bold;color:#0b0c10;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;">➤</button>
            </form>
        </div>

        <div id="view-inbox" class="view">
            <div style="padding:15px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.2);border-bottom:1px solid rgba(255,255,255,0.05);">
                <div style="color:var(--primary);font-family:'Rajdhani';font-weight:bold;letter-spacing:2px;">MENSAGENS</div>
                <button onclick="openCreateGroupModal()" class="glass-btn" style="padding:8px 12px; margin:0; flex:none;">+ GRUPO</button>
            </div>
            <div id="inbox-list" style="padding:15px; display:flex; flex-direction:column; gap:10px; overflow-y:auto; flex:1;"></div>
        </div>

        <div id="view-dm" class="view" style="justify-content:center; padding:15px; background:rgba(0,0,0,0.5);">
            <div class="chat-box-centered">
                <div style="padding:15px;display:flex;align-items:center;background:rgba(0,0,0,0.4);border-bottom:1px solid rgba(255,255,255,0.05);">
                    <button onclick="goView('inbox')" style="background:none;border:none;color:var(--primary);font-size:18px;cursor:pointer;margin-right:15px;">⬅ Voltar</button>
                    <div id="dm-header-name" style="color:white;font-family:'Rajdhani';font-weight:bold;letter-spacing:1px;font-size:18px;">Chat</div>
                </div>
                <div id="dm-list"></div>
                <form id="dm-input-area" class="chat-input-area" onsubmit="sendDM(); return false;">
                    <input type="file" id="dm-file" class="hidden" onchange="uploadDMImage()" accept="image/*,video/*">
                    <button type="button" onclick="document.getElementById('dm-file').click()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#888">📎</button>
                    <input id="dm-msg" class="chat-msg" placeholder="Mensagem secreta..." autocomplete="off">
                    <button type="button" onclick="openEmoji('dm-msg')" style="background:none;border:none;font-size:24px;cursor:pointer;margin-right:5px">😀</button>
                    <button type="submit" style="background:var(--primary);border:none;min-width:45px;height:45px;border-radius:12px;font-weight:bold;color:#0b0c10;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;">➤</button>
                </form>
            </div>
        </div>

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
                <span id="p-rank" class="rank-badge">...</span>
                <p id="p-bio" style="color:#888;margin:10px 0 20px 0;font-style:italic;">...</p>
            </div>
            <div style="width:90%; max-width:400px; margin:0 auto; text-align:center">
                <button id="btn-stealth" onclick="toggleStealth()" class="glass-btn" style="width:100%; margin-bottom:20px;">MODO FURTIVO</button>

                <div class="search-glass">
                    <input id="search-input" placeholder="Buscar Soldado..." onkeypress="if(event.key==='Enter')searchUsers()">
                    <button type="button" onclick="searchUsers()" style="background:none;border:none;color:var(--primary);font-size:18px;cursor:pointer;">🔍</button>
                    <button type="button" onclick="clearSearch()" style="background:none;border:none;color:#ff5555;font-size:18px;cursor:pointer;padding-left:10px;">✕</button>
                </div>
                <div id="search-results"></div>
                
                <div style="display:flex; gap:10px; margin-top:10px">
                    <button onclick="toggleRequests('requests')" class="glass-btn">📩 Solicitações</button>
                    <button onclick="toggleRequests('friends')" class="glass-btn">👥 Amigos</button>
                </div>
                <div id="requests-list" style="margin-top:15px; background:rgba(0,0,0,0.3); border-radius:10px;"></div>
                
                <button onclick="logout()" class="glass-btn danger-btn">DESCONECTAR DO SISTEMA</button>
            </div>
        </div>

        <div id="view-public-profile" class="view">
            <button onclick="goView('feed')" style="position:absolute;top:20px;left:20px;z-index:10;background:rgba(0,0,0,0.5);color:white;border:1px solid #444;padding:8px 15px;border-radius:8px;backdrop-filter:blur(5px);cursor:pointer;">⬅ Voltar</button>
            <div class="profile-header-container">
                <img id="pub-cover" src="" class="profile-cover" onerror="this.src='https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY'">
                <div class="profile-pic-lg-wrap">
                    <img id="pub-avatar" src="" class="profile-pic-lg" onerror="this.src='https://ui-avatars.com/api/?name=User&background=111&color=66fcf1'">
                    <div id="pub-status-dot" class="status-dot status-dot-lg"></div>
                </div>
            </div>
            <div style="text-align:center;margin-top:20px">
                <h2 id="pub-name" style="color:white;font-family:'Rajdhani';margin:5px 0;">...</h2>
                <span id="pub-rank" class="rank-badge">...</span>
                <p id="pub-bio" style="color:#888;margin:10px 0 20px 0;">...</p>
                <div id="pub-actions" style="margin-bottom:20px; display:flex; justify-content:center; gap:10px;"></div>
                <div id="pub-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:2px;max-width:500px;margin:0 auto;"></div>
            </div>
        </div>
    </div>
</div>

<script>
var user=null, ws=null, dmWS=null, syncInterval=null, lastFeedHash="", currentEmojiTarget=null, currentChatId=null, currentChatType=null;
window.onlineUsers = []; window.unreadData = {}; 

const CLOUD_NAME = "dqa0q3qlx"; 
const UPLOAD_PRESET = "for_glory_preset"; 
const EMOJIS = ["😂","🔥","❤️","💀","🎮","🇧🇷","🫡","🤡","😭","😎","🤬","👀","👍","👎","🔫","💣","⚔️","🛡️","🏆","💰","🍕","🍺","👋","🚫","✅","👑","💩","👻","👽","🤖","🤫","🥶","🤯","🥳","🤢","🤕","🤑","🤠","😈","👿","👹","👺","👾"];

function showToast(m){let x=document.getElementById("toast");x.innerText=m;x.className="show";setTimeout(()=>{x.className=""},3000)}
function toggleAuth(m){['login','register','forgot','reset'].forEach(f=>document.getElementById(f+'-form').classList.add('hidden'));document.getElementById(m+'-form').classList.remove('hidden');}

function initEmojis() {
    let g = document.getElementById('emoji-grid');
    if(!g) return;
    g.innerHTML = '';
    EMOJIS.forEach(e => {
        let s = document.createElement('div');
        s.style.cssText = "font-size:24px;cursor:pointer;text-align:center;padding:5px;border-radius:5px;transition:0.2s;";
        s.innerText = e;
        s.onclick = () => { if(currentEmojiTarget){ let inp = document.getElementById(currentEmojiTarget); inp.value += e; inp.focus(); } };
        s.onmouseover = () => s.style.background = "rgba(102,252,241,0.2)";
        s.onmouseout = () => s.style.background = "transparent";
        g.appendChild(s);
    });
}
initEmojis();

function checkToken() {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    if (token) { toggleAuth('reset'); window.history.replaceState({}, document.title, "/"); window.resetToken = token; }
}
checkToken();

function openEmoji(id){currentEmojiTarget = id; document.getElementById('emoji-picker').style.display='flex';}
function toggleEmoji(forceClose){let e = document.getElementById('emoji-picker'); if(forceClose === true) e.style.display='none'; else e.style.display = e.style.display === 'flex' ? 'none' : 'flex';}

async function fetchOnlineUsers() {
    if(!user) return;
    try { let r = await fetch('/users/online'); window.onlineUsers = await r.json(); updateStatusDots(); } catch(e){}
}
function updateStatusDots() {
    document.querySelectorAll('.status-dot').forEach(dot => {
        let uid = parseInt(dot.getAttribute('data-uid'));
        if(!uid) return;
        if(window.onlineUsers.includes(uid)) dot.classList.add('online'); else dot.classList.remove('online');
    });
}

async function fetchUnread() {
    if(!user) return;
    try {
        let r = await fetch(`/inbox/unread/${user.id}`); let d = await r.json(); window.unreadData = d.by_sender;
        let badge = document.getElementById('inbox-badge');
        if(d.total > 0) { badge.innerText = d.total; badge.style.display = 'block'; } else { badge.style.display = 'none'; }
        if(document.getElementById('view-inbox').classList.contains('active')) {
            document.querySelectorAll('.inbox-item').forEach(item => {
                let sid = parseInt(item.getAttribute('data-id')); let type = item.getAttribute('data-type'); let b = item.querySelector('.list-badge');
                if(type === '1v1' && window.unreadData[sid]) { b.innerText = window.unreadData[sid]; b.style.display = 'block'; } else if(b) { b.style.display = 'none'; }
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
    if(user.is_invisible) { btn.innerText = "🕵️ MODO FURTIVO: ATIVADO"; btn.style.borderColor = "#ffaa00"; btn.style.color = "#ffaa00"; myDot.classList.remove('online'); } 
    else { btn.innerText = "🟢 MODO FURTIVO: DESATIVADO"; btn.style.borderColor = "rgba(102, 252, 241, 0.3)"; btn.style.color = "var(--primary)"; myDot.classList.add('online'); }
}

async function requestReset() { let email = document.getElementById('f-email').value; if(!email) return showToast("Digite seu e-mail!"); try { let r = await fetch('/auth/forgot-password', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email: email}) }); showToast("E-mail enviado! Verifique spam."); toggleAuth('login'); } catch(e) { showToast("Erro"); } }
async function doResetPassword() { let newPass = document.getElementById('new-pass').value; if(!newPass) return showToast("Digite a nova senha!"); try { let r = await fetch('/auth/reset-password', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token: window.resetToken, new_password: newPass}) }); if(r.ok) { showToast("Senha alterada! Faça login."); toggleAuth('login'); } else { showToast("Link expirado."); } } catch(e) { showToast("Erro"); } }
async function doLogin(){try{let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('l-user').value,password:document.getElementById('l-pass').value})});if(!r.ok)throw 1;user=await r.json();startApp()}catch(e){showToast("Erro Login")}}
async function doRegister(){try{let r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('r-user').value,email:document.getElementById('r-email').value,password:document.getElementById('r-pass').value})});if(!r.ok)throw 1;showToast("Registrado!");toggleAuth('login')}catch(e){showToast("Erro Registro")}}

function startApp(){
    document.getElementById('modal-login').classList.add('hidden');
    updateUI(); loadFeed(); connectWS(); fetchOnlineUsers(); fetchUnread();
    syncInterval=setInterval(()=>{
        if(document.getElementById('view-feed').classList.contains('active')) loadFeed();
        fetchOnlineUsers(); fetchUnread(); 
    },4000);
}

function updateUI(){
    if(!user) return;
    let safeAvatar = user.avatar_url;
    if(!safeAvatar || safeAvatar.includes("undefined")) safeAvatar = `https://ui-avatars.com/api/?name=${user.username}&background=1f2833&color=66fcf1&bold=true`;
    document.getElementById('nav-avatar').src = safeAvatar; document.getElementById('p-avatar').src = safeAvatar;
    let pCover = document.getElementById('p-cover'); pCover.src = user.cover_url || "https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY"; pCover.style.display = 'block';
    document.getElementById('p-name').innerText = user.username || "Soldado"; document.getElementById('p-bio').innerText = user.bio || "Na base de operações."; document.getElementById('p-rank').innerText = user.rank || "REC";
    document.querySelectorAll('.my-avatar-mini').forEach(img => img.src = safeAvatar);
    updateStealthUI();
}
function logout(){location.reload()}
function goView(v){
    document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));
    document.getElementById('view-'+v).classList.add('active');
    if(v !== 'public-profile' && v !== 'dm') { document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active')); if(event && event.target) event.target.closest('.nav-btn')?.classList.add('active'); }
    if(v === 'inbox') loadInbox();
}

async function loadFeed(){
    try{
        let r=await fetch(`/posts?uid=${user.id}&limit=50&nocache=${new Date().getTime()}`);
        if(!r.ok)return;
        let p=await r.json();
        let h=JSON.stringify(p.map(x=>x.id + x.likes + x.comments + (x.user_liked?"1":"0"))); 
        if(h===lastFeedHash)return;
        lastFeedHash=h;
        
        let openComments = []; let activeInputs = {}; let focusedInputId = null;
        if (document.activeElement && document.activeElement.classList.contains('comment-inp')) { focusedInputId = document.activeElement.id; }
        document.querySelectorAll('.comments-section').forEach(sec => { if(sec.style.display === 'block') openComments.push(sec.id.split('-')[1]); });
        document.querySelectorAll('.comment-inp').forEach(inp => { if(inp.value) activeInputs[inp.id] = inp.value; });

        let ht='';
        p.forEach(x=>{
            let m=x.media_type==='video'?`<video src="${x.content_url}" class="post-media" controls playsinline preload="metadata"></video>`:`<img src="${x.content_url}" class="post-media" loading="lazy">`;
            m = `<div class="post-media-wrapper">${m}</div>`;
            let delBtn=x.author_id===user.id?`<span onclick="confirmDeletePost(${x.id})" style="cursor:pointer;opacity:0.5;font-size:20px;transition:0.2s;" onmouseover="this.style.opacity='1';this.style.color='#ff5555'" onmouseout="this.style.opacity='0.5';this.style.color=''">🗑️</span>`:'';
            let heartIcon = x.user_liked ? "❤️" : "🤍"; let heartClass = x.user_liked ? "liked" : "";
            
            ht+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer" onclick="openPublicProfile(${x.author_id})"><div class="av-wrap" style="margin-right:12px;"><img src="${x.author_avatar}" class="post-av" style="margin:0;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${x.author_id}"></div></div><div class="user-info-box"><b style="color:white;font-size:14px">${x.author_name}</b><div class="rank-badge">${x.author_rank}</div></div></div>${delBtn}</div>${m}<div class="post-actions"><button class="action-btn ${heartClass}" onclick="toggleLike(${x.id}, this)"><span class="icon">${heartIcon}</span> <span class="count" style="color:white;font-weight:bold;">${x.likes}</span></button><button class="action-btn" onclick="toggleComments(${x.id})">💬 <span class="count" style="color:white;font-weight:bold;">${x.comments}</span></button></div><div class="post-caption"><b style="color:white;cursor:pointer;" onclick="openPublicProfile(${x.author_id})">${x.author_name}</b> ${x.caption}</div><div id="comments-${x.id}" class="comments-section"><div id="comment-list-${x.id}"></div><form class="comment-input-area" onsubmit="sendComment(${x.id}); return false;"><input id="comment-inp-${x.id}" class="comment-inp" placeholder="Comentar..." autocomplete="off"><button type="button" onclick="openEmoji('comment-inp-${x.id}')" style="background:none;border:none;font-size:20px;cursor:pointer;padding:0 5px;">😀</button><button type="submit" style="background:var(--primary);border:none;border-radius:12px;padding:8px 15px;color:black;font-weight:bold;cursor:pointer;">➤</button></form></div></div>`
        });
        document.getElementById('feed-container').innerHTML=ht;
        
        openComments.forEach(pid => { let sec = document.getElementById(`comments-${pid}`); if(sec) { sec.style.display = 'block'; loadComments(pid); } });
        for (let id in activeInputs) { let inp = document.getElementById(id); if (inp) inp.value = activeInputs[id]; }
        if (focusedInputId) { let inp = document.getElementById(focusedInputId); if (inp) { inp.focus({preventScroll: true}); let val = inp.value; inp.value = ''; inp.value = val; } }
        updateStatusDots();
    }catch(e){}
}

let postToDelete = null;
function confirmDeletePost(pid) { postToDelete = pid; document.getElementById('modal-delete').classList.remove('hidden'); }
document.getElementById('btn-confirm-delete').onclick = async () => {
    if(!postToDelete) return; let pid = postToDelete; document.getElementById('modal-delete').classList.add('hidden');
    let r = await fetch('/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,user_id:user.id})});
    if(r.ok) { showToast("Missão excluída."); lastFeedHash=""; loadFeed(); }
};

async function toggleLike(pid, btn) {
    let r = await fetch('/post/like', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({post_id:pid, user_id:user.id})});
    if(r.ok) { let d = await r.json(); let icon = btn.querySelector('.icon'); let count = btn.querySelector('.count'); if(d.liked) { btn.classList.add('liked'); icon.innerText = "❤️"; } else { btn.classList.remove('liked'); icon.innerText = "🤍"; } count.innerText = d.count; lastFeedHash=""; loadFeed(); }
}

async function toggleComments(pid) {
    let sec = document.getElementById(`comments-${pid}`);
    if(sec.style.display === 'block') { sec.style.display = 'none'; } else { sec.style.display = 'block'; loadComments(pid); }
}

async function loadComments(pid) {
    let r = await fetch(`/post/${pid}/comments`);
    let list = document.getElementById(`comment-list-${pid}`);
    if(r.ok) {
        let comments = await r.json();
        if(comments.length === 0){ list.innerHTML = "<p style='color:#888;font-size:12px;text-align:center;'>Nenhum comentário ainda.</p>"; return;}
        list.innerHTML = comments.map(c => `<div class="comment-row"><div class="av-wrap" onclick="openPublicProfile(${c.author_id})"><img src="${c.author_avatar}" class="comment-av" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${c.author_id}" style="width:8px;height:8px;border-width:1px;"></div></div><div><b style="color:var(--primary);cursor:pointer;" onclick="openPublicProfile(${c.author_id})">${c.author_name}</b> <span style="color:#e0e0e0">${c.text}</span></div></div>`).join('');
        updateStatusDots();
    }
}

async function sendComment(pid) {
    let inp = document.getElementById(`comment-inp-${pid}`); let text = inp.value.trim(); if(!text) return;
    let r = await fetch('/post/comment', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({post_id:pid, user_id:user.id, text:text})});
    if(r.ok) { inp.value = ''; toggleEmoji(true); lastFeedHash=""; loadFeed(); }
}

async function loadInbox() {
    let r = await fetch(`/inbox/${user.id}`); let d = await r.json(); let b = document.getElementById('inbox-list'); b.innerHTML = '';
    if(d.groups.length === 0 && d.friends.length === 0) { b.innerHTML = "<p style='text-align:center;color:#888;margin-top:20px;'>Sua caixa está vazia. Recrute aliados!</p>"; return; }
    d.groups.forEach(g => { b.innerHTML += `<div class="inbox-item" data-id="${g.id}" data-type="group" style="display:flex;align-items:center;gap:15px;padding:12px;background:var(--card-bg);border-radius:12px;cursor:pointer;border:1px solid rgba(102,252,241,0.2);" onclick="openChat(${g.id}, '${g.name}', 'group')"><img src="${g.avatar}" style="width:45px;height:45px;border-radius:50%;"><div style="flex:1;"><b style="color:white;font-size:16px;">${g.name}</b><br><span style="font-size:12px;color:var(--primary);">👥 Esquadrão</span></div></div>`; });
    d.friends.forEach(f => {
        let unreadCount = (window.unreadData && window.unreadData[f.id]) ? window.unreadData[f.id] : 0; let badgeDisplay = unreadCount > 0 ? 'block' : 'none';
        b.innerHTML += `<div class="inbox-item" data-id="${f.id}" data-type="1v1" style="display:flex;align-items:center;gap:15px;padding:12px;background:rgba(255,255,255,0.05);border-radius:12px;cursor:pointer;" onclick="openChat(${f.id}, '${f.name}', '1v1')"><div class="av-wrap"><img src="${f.avatar}" style="width:45px;height:45px;border-radius:50%;object-fit:cover;"><div class="status-dot" data-uid="${f.id}"></div></div><div style="flex:1;"><b style="color:white;font-size:16px;">${f.name}</b><br><span style="font-size:12px;color:#888;">Mensagem Direta</span></div><div class="list-badge" style="display:${badgeDisplay}">${unreadCount}</div></div>`;
    });
    updateStatusDots();
}

async function openCreateGroupModal() {
    let r = await fetch(`/inbox/${user.id}`); let d = await r.json(); let list = document.getElementById('group-friends-list');
    if(d.friends.length === 0) { list.innerHTML = "<p style='color:#ff5555;font-size:13px;'>Você precisa de aliados para criar um grupo.</p>"; } 
    else { list.innerHTML = d.friends.map(f => `<label style="display:flex; align-items:center; gap:10px; color:white; margin-bottom:10px; cursor:pointer;"><input type="checkbox" class="grp-friend-cb" value="${f.id}" style="width:18px;height:18px;"><img src="${f.avatar}" style="width:30px;height:30px;border-radius:50%;object-fit:cover;"> ${f.name}</label>`).join(''); }
    document.getElementById('new-group-name').value = ''; document.getElementById('modal-create-group').classList.remove('hidden');
}

async function submitCreateGroup() {
    let name = document.getElementById('new-group-name').value.trim(); if(!name) return showToast("Dê um nome ao grupo!");
    let cbs = document.querySelectorAll('.grp-friend-cb:checked'); let member_ids = Array.from(cbs).map(cb => parseInt(cb.value));
    if(member_ids.length === 0) return showToast("Selecione pelo menos 1 aliado!");
    let r = await fetch('/group/create', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:name, creator_id:user.id, member_ids:member_ids})});
    if(r.ok) { document.getElementById('modal-create-group').classList.add('hidden'); showToast("Esquadrão criado!"); loadInbox(); }
}

async function openChat(id, name, type) {
    currentChatId = id; currentChatType = type;
    document.getElementById('dm-header-name').innerText = type === 'group' ? "Grupo: " + name : "Chat: " + name;
    goView('dm');
    
    if(type === '1v1') { await fetch(`/inbox/read/${id}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({uid:user.id})}); fetchUnread(); }
    
    let list = document.getElementById('dm-list'); list.innerHTML = '';
    let fetchUrl = type === 'group' ? `/group/${id}/messages` : `/dms/${id}?uid=${user.id}`;
    let r = await fetch(fetchUrl);
    if(r.ok) {
        let msgs = await r.json();
        msgs.forEach(d => {
            let m = (d.sender_id === user.id); let c = d.content;
            if(c.startsWith('http') && c.includes('cloudinary')) { if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) { c = `<video src="${c}" style="max-width:100%; border-radius:10px; border:1px solid #444;" controls playsinline></video>`; } else { c = `<img src="${c}" style="max-width:100%; border-radius:10px; cursor:pointer; border:1px solid #444;" onclick="window.open(this.src)">`; } }
            let h = `<div class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.sender_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.sender_id})">${d.username}</div><div class="msg-bubble">${c}</div></div></div>`;
            list.insertAdjacentHTML('beforeend',h);
        });
        list.scrollTop = list.scrollHeight;
    }
    
    if(dmWS) dmWS.close();
    let p = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let ch = type === 'group' ? `group_${id}` : `dm_${Math.min(user.id, id)}_${Math.max(user.id, id)}`;
    dmWS = new WebSocket(`${p}//${location.host}/ws/${ch}/${user.id}`);
    dmWS.onmessage = e => {
        let d = JSON.parse(e.data); let b = document.getElementById('dm-list'); let m = parseInt(d.user_id) === parseInt(user.id); let c = d.content;
        if(c.startsWith('http') && c.includes('cloudinary')) { if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) { c = `<video src="${c}" style="max-width:100%; border-radius:10px; border:1px solid #444;" controls playsinline></video>`; } else { c = `<img src="${c}" style="max-width:100%; border-radius:10px; cursor:pointer; border:1px solid #444;" onclick="window.open(this.src)">`; } }
        let h = `<div class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username}</div><div class="msg-bubble">${c}</div></div></div>`;
        b.insertAdjacentHTML('beforeend',h); b.scrollTop = b.scrollHeight;
        
        if(currentChatType === '1v1' && currentChatId === d.user_id) { fetch(`/inbox/read/${d.user_id}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({uid:user.id})}).then(()=>fetchUnread()); } 
        else { fetchUnread(); }
    };
}

function sendDM() { 
    let i = document.getElementById('dm-msg'); 
    let msg = i.value.trim();
    if(msg && dmWS) { 
        dmWS.send(msg); 
        i.value = ''; toggleEmoji(true); 
    } 
}

async function uploadDMImage(){
    let f=document.getElementById('dm-file').files[0];
    if(!f)return; showToast("Enviando arquivo...");
    try{ let c=await uploadToCloudinary(f); if(dmWS) dmWS.send(c.secure_url); } catch(e){alert("Erro ao enviar: " + e)}
}

async function openPublicProfile(uid){
    let r=await fetch('/user/'+uid+'?viewer_id='+user.id); let d=await r.json();
    document.getElementById('pub-avatar').src=d.avatar_url; let pc=document.getElementById('pub-cover'); pc.src=d.cover_url; pc.style.display='block';
    document.getElementById('pub-name').innerText=d.username; document.getElementById('pub-bio').innerText=d.bio; document.getElementById('pub-rank').innerText=d.rank;
    let ab=document.getElementById('pub-actions'); ab.innerHTML='';
    document.getElementById('pub-status-dot').setAttribute('data-uid', uid); updateStatusDots();
    
    if(d.friend_status==='friends') {
        ab.innerHTML=`<span style="color:#66fcf1; border:1px solid #66fcf1; padding:10px 15px; border-radius:12px; font-weight:bold;">✔ Aliado</span> <button class="glass-btn" style="padding:10px 20px; border-color:var(--primary); font-size:14px; max-width:180px;" onclick="openChat(${uid}, '${d.username}', '1v1')">💬 Mensagem</button>`;
    } else if(d.friend_status==='pending_sent') { ab.innerHTML='<span style="color:orange; border:1px solid orange; padding:10px 15px; border-radius:12px;">Enviado</span>'; } 
    else if(d.friend_status==='pending_received') { ab.innerHTML=`<button class="glass-btn" onclick="handleReq(${d.request_id},'accept')">Aceitar Aliado</button>`; } 
    else { ab.innerHTML=`<button class="glass-btn" onclick="sendRequest(${uid})">Recrutar Aliado</button>`; }
    
    let g=document.getElementById('pub-grid'); g.innerHTML='';
    d.posts.forEach(p=>{g.innerHTML+=p.media_type==='video'?`<video src="${p.content_url}" style="width:100%; aspect-ratio:1/1; object-fit:cover;" controls></video>`:`<img src="${p.content_url}" style="width:100%; aspect-ratio:1/1; object-fit:cover; cursor:pointer;" onclick="window.open(this.src)">`});
    goView('public-profile')
}

async function uploadToCloudinary(file){
    let limiteMB = 100; if(file.size > (limiteMB * 1024 * 1024)) return Promise.reject(`Arquivo excedeu ${limiteMB}MB!`);
    let resType = file.type.startsWith('video') ? 'video' : 'image'; let url = `https://api.cloudinary.com/v1_1/${CLOUD_NAME}/${resType}/upload`;
    let fd=new FormData(); fd.append('file',file); fd.append('upload_preset',UPLOAD_PRESET);
    return new Promise((res,rej)=>{
        let x=new XMLHttpRequest(); x.open('POST', url, true);
        x.upload.onprogress = (e) => { if (e.lengthComputable && document.getElementById('progress-bar')) { let p = Math.round((e.loaded / e.total) * 100); document.getElementById('progress-bar').style.width = p + '%'; document.getElementById('progress-text').innerText = p + '%'; } };
        x.onload=()=>{ if(x.status===200) res(JSON.parse(x.responseText)); else { try { rej(JSON.parse(x.responseText).error.message); } catch(err) { rej("Formato inválido."); } } };
        x.onerror=()=>rej("Conexão caiu."); x.send(fd)
    });
}
async function submitPost(){let f=document.getElementById('file-upload').files[0];let cap=document.getElementById('caption-upload').value;if(!f)return showToast("Selecione um arquivo!");let btn=document.getElementById('btn-pub');btn.innerText="ENVIANDO...";btn.disabled=true;document.getElementById('upload-progress').style.display='block';document.getElementById('progress-text').style.display='block';try{let c = await uploadToCloudinary(f);let fd=new FormData();fd.append('user_id',user.id);fd.append('caption',cap);fd.append('content_url',c.secure_url);fd.append('media_type',c.resource_type);let r=await fetch('/post/create_from_url',{method:'POST',body:fd});if(r.ok){showToast("Sucesso!");user.xp+=50;lastFeedHash="";loadFeed();closeUpload();}}catch(e){alert("Ops! " + e);}finally{btn.innerText="PUBLICAR (+50 XP)";btn.disabled=false;document.getElementById('upload-progress').style.display='none';document.getElementById('progress-text').style.display='none';document.getElementById('progress-bar').style.width='0%';}}
async function updateProfile(){let btn=document.getElementById('btn-save-profile');btn.innerText="ENVIANDO...";btn.disabled=true;try{let f=document.getElementById('avatar-upload').files[0];let c=document.getElementById('cover-upload').files[0];let b=document.getElementById('bio-update').value;let au=null,cu=null;if(f){let r=await uploadToCloudinary(f);au=r.secure_url}if(c){let r=await uploadToCloudinary(c);cu=r.secure_url}let fd=new FormData();fd.append('user_id',user.id);if(au)fd.append('avatar_url',au);if(cu)fd.append('cover_url',cu);if(b)fd.append('bio',b);let r=await fetch('/profile/update_meta',{method:'POST',body:fd});if(r.ok){let d=await r.json();Object.assign(user,d);updateUI();document.getElementById('modal-profile').classList.add('hidden');showToast("Atualizado!")}}catch(e){alert("Ops! " + e)}finally{btn.innerText="SALVAR";btn.disabled=false;}}

// CHAT GERAL E RECEBEDOR DE PING DE NOTIFICAÇÃO
function connectWS(){
    if(ws)ws.close(); let p=location.protocol==='https:'?'wss:':'ws:'; ws=new WebSocket(`${p}//${location.host}/ws/Geral/${user.id}`);
    ws.onmessage=e=>{
        let d=JSON.parse(e.data);
        // Sistema Ultrassônico de Notificação (Se receber um ping de DM, recarrega a bolinha vermelha na hora)
        if(d.type === 'ping') { fetchUnread(); return; }
        
        let b=document.getElementById('chat-list'); let m=parseInt(d.user_id)===parseInt(user.id); let c = d.content;
        if(c.startsWith('http') && c.includes('cloudinary')) { if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) { c = `<video src="${c}" style="max-width:100%; border-radius:10px; border:1px solid #444;" controls playsinline></video>`; } else { c = `<img src="${c}" style="max-width:100%; border-radius:10px; cursor:pointer; border:1px solid #444;" onclick="window.open(this.src)">`; } }
        let h=`<div class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username}</div><div class="msg-bubble">${c}</div></div></div>`;
        b.insertAdjacentHTML('beforeend',h); b.scrollTop=b.scrollHeight
    }
}
function sendMsg(){let i=document.getElementById('chat-msg');if(i.value.trim()){ws.send(i.value.trim());i.value=''; toggleEmoji(true);}}
async function uploadChatImage(){let f=document.getElementById('chat-file').files[0];if(!f)return;showToast("Enviando arquivo...");try{let c=await uploadToCloudinary(f);ws.send(c.secure_url);}catch(e){alert("Erro ao enviar: " + e)}}
function closeUpload(){document.getElementById('modal-upload').classList.add('hidden')}

function clearSearch() { document.getElementById('search-input').value = ''; document.getElementById('search-results').innerHTML = ''; }
async function searchUsers(){let q=document.getElementById('search-input').value;if(!q)return;let r=await fetch('/users/search?q='+q);let res=await r.json();let b=document.getElementById('search-results');b.innerHTML='';res.forEach(u=>{if(u.id!==user.id)b.innerHTML+=`<div style="padding:10px;background:rgba(255,255,255,0.05);margin-top:5px;border-radius:8px;display:flex;align-items:center;gap:10px;cursor:pointer" onclick="openPublicProfile(${u.id})"><div class="av-wrap"><img src="${u.avatar_url}" style="width:35px;height:35px;border-radius:50%;object-fit:cover;margin:0;"><div class="status-dot" data-uid="${u.id}"></div></div><span>${u.username}</span></div>`}); updateStatusDots();}
async function toggleRequests(type){let b=document.getElementById('requests-list');if(b.style.display==='block'){b.style.display='none';return}b.style.display='block';let d=await (await fetch('/friend/requests?uid='+user.id)).json();b.innerHTML=type==='requests'?(d.requests.length?d.requests.map(r=>`<div style="padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;">${r.username} <button class="glass-btn" style="padding:5px 10px; flex:none;" onclick="handleReq(${r.id},'accept')">Aceitar</button></div>`).join(''):'<p style="padding:10px;color:#888;">Sem solicitações.</p>'):(d.friends.length?d.friends.map(f=>`<div style="padding:10px;border-bottom:1px solid #333;cursor:pointer;display:flex;align-items:center;gap:10px;" onclick="openPublicProfile(${f.id})"><div class="av-wrap"><img src="${f.avatar}" style="width:30px;height:30px;border-radius:50%;"><div class="status-dot" data-uid="${f.id}" style="width:10px;height:10px;"></div></div>${f.username}</div>`).join(''):'<p style="padding:10px;color:#888;">Sem aliados.</p>'); updateStatusDots();}
async function sendRequest(tid){if((await fetch('/friend/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_id:tid,sender_id:user.id})})).ok){showToast("Convite Enviado!");openPublicProfile(tid)}}
async function handleReq(rid,act){if((await fetch('/friend/handle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:rid,action:act})})).ok){showToast("Processado!");toggleRequests('requests')}}
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
    counts = Counter([u[0] for u in unread_pms])
    return {"total": sum(counts.values()), "by_sender": dict(counts)}

@app.post("/inbox/read/{sender_id}")
async def mark_read(sender_id: int, d: ReadData, db: Session=Depends(get_db)):
    db.query(PrivateMessage).filter(PrivateMessage.sender_id == sender_id, PrivateMessage.receiver_id == d.uid).update({"is_read": 1})
    db.commit()
    return {"status": "ok"}

@app.post("/auth/forgot-password")
async def forgot_password(d: ForgotPasswordData, background_tasks: BackgroundTasks, db: Session=Depends(get_db)):
    user = db.query(User).filter(User.email == d.email).first()
    if not user: return {"status": "ok"}
    token = create_reset_token(user.email)
    reset_link = f"https://for-glory.onrender.com/?token={token}"
    message = MessageSchema(subject="Recuperação de Senha - For Glory", recipients=[d.email], body=f"""<p>Soldado {user.username},</p><p>Recebemos um pedido de resgate para sua conta.</p><p>Clique no link abaixo para redefinir sua senha:</p><a href="{reset_link}" style="background:#66fcf1; color:black; padding:10px 20px; text-decoration:none; border-radius:5px;">REDEFINIR SENHA</a><p>Este link expira em 30 minutos.</p>""", subtype=MessageType.html)
    fm = FastMail(mail_conf)
    background_tasks.add_task(fm.send_message, message)
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
    db.add(User(username=d.username, email=d.email, password_hash=criptografar(d.password), xp=0, is_invisible=0))
    db.commit()
    return {"status":"ok"}

@app.post("/login")
async def log(d: LoginData, db: Session=Depends(get_db)):
    u = db.query(User).filter(User.username==d.username).first()
    if not u or u.password_hash != criptografar(d.password): raise HTTPException(400, "Erro")
    return {"id":u.id, "username":u.username, "avatar_url":u.avatar_url, "cover_url":u.cover_url, "bio":u.bio, "xp": u.xp, "rank": calcular_patente(u.xp), "is_invisible": getattr(u, 'is_invisible', 0)}

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

@app.get("/post/{post_id}/comments")
async def get_comments(post_id: int, db: Session=Depends(get_db)):
    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.timestamp.asc()).all()
    return [{"id": c.id, "text": c.text, "author_name": c.author.username, "author_avatar": c.author.avatar_url, "author_id": c.author.id} for c in comments]

@app.get("/posts")
async def get_posts(uid: int, limit: int = 50, db: Session=Depends(get_db)):
    posts = db.query(Post).order_by(Post.timestamp.desc()).limit(limit).all()
    result = []
    for p in posts:
        like_count = db.query(Like).filter(Like.post_id == p.id).count()
        user_liked = db.query(Like).filter(Like.post_id == p.id, Like.user_id == uid).first() is not None
        comment_count = db.query(Comment).filter(Comment.post_id == p.id).count()
        result.append({"id": p.id, "content_url": p.content_url, "media_type": p.media_type, "caption": p.caption, "author_name": p.author.username, "author_avatar": p.author.avatar_url, "author_rank": calcular_patente(p.author.xp), "author_id": p.author.id, "likes": like_count, "user_liked": user_liked, "comments": comment_count})
    return result

@app.post("/post/delete")
async def delete_post_endpoint(d: DeletePostData, db: Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id == d.post_id).first()
    if not post or post.user_id != d.user_id: return {"status": "error"}
    db.query(Like).filter(Like.post_id == post.id).delete()
    db.query(Comment).filter(Comment.post_id == post.id).delete()
    db.delete(post); db.commit()
    return {"status": "ok"}

@app.post("/profile/update_meta")
async def update_prof_meta(user_id: int = Form(...), bio: str = Form(None), avatar_url: str = Form(None), cover_url: str = Form(None), db: Session=Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if avatar_url: u.avatar_url = avatar_url
    if cover_url: u.cover_url = cover_url
    if bio: u.bio = bio
    db.commit()
    return {"avatar_url": u.avatar_url, "cover_url": u.cover_url, "bio": u.bio, "rank": calcular_patente(u.xp)}

@app.get("/users/search")
async def search_users(q: str, db: Session=Depends(get_db)):
    users = db.query(User).filter(User.username.like(f"%{q}%")).limit(10).all()
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
    return [{"id": m.id, "sender_id": m.sender_id, "content": m.content, "timestamp": m.timestamp.isoformat(), "avatar": m.sender.avatar_url, "username": m.sender.username} for m in msgs]

@app.get("/dms/{target_id}")
async def get_dms(target_id: int, uid: int, db: Session=Depends(get_db)):
    msgs = db.query(PrivateMessage).filter(
        or_(
            and_(PrivateMessage.sender_id == uid, PrivateMessage.receiver_id == target_id),
            and_(PrivateMessage.sender_id == target_id, PrivateMessage.receiver_id == uid)
        )
    ).order_by(PrivateMessage.timestamp.asc()).limit(100).all()
    return [{"id": m.id, "sender_id": m.sender_id, "content": m.content, "timestamp": m.timestamp.isoformat(), "avatar": m.sender.avatar_url, "username": m.sender.username} for m in msgs]

@app.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int):
    await manager.connect(ws, ch, uid)
    try:
        while True:
            txt = await ws.receive_text()
            user_data = None
            
            # ABRE BANCO SÓ PARA SALVAR, FECHA NA HORA
            db = SessionLocal()
            try:
                u_fresh = db.query(User).filter(User.id == uid).first()
                user_data = {"user_id": u_fresh.id, "username": u_fresh.username, "avatar": u_fresh.avatar_url, "content": txt, "type": "msg"}
                
                if ch.startswith("dm_"):
                    parts = ch.split("_")
                    id1, id2 = int(parts[1]), int(parts[2])
                    rec_id = id2 if uid == id1 else id1
                    db.add(PrivateMessage(sender_id=uid, receiver_id=rec_id, content=txt, is_read=0))
                    db.commit()
                elif ch.startswith("group_"):
                    grp_id = int(ch.split("_")[1])
                    db.add(GroupMessage(group_id=grp_id, sender_id=uid, content=txt))
                    db.commit()
            except Exception as e:
                logger.error(f"Erro BD WS Protegido: {e}")
                db.rollback()
                user_data = None # Impede o broadcast se falhou no banco
            finally:
                db.close() 

            if user_data:
                await manager.broadcast(user_data, ch)
                # SISTEMA DE NOTIFICAÇÃO (PING GLOBAL)
                if ch.startswith("dm_"):
                    await manager.broadcast({"type": "ping"}, "Geral")

    except Exception:
        manager.disconnect(ws, ch, uid)

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
    return {"username": target.username, "avatar_url": target.avatar_url, "cover_url": target.cover_url, "bio": target.bio, "rank": calcular_patente(target.xp), "posts": posts_data, "friend_status": status, "request_id": req_id}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
