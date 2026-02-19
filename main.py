import uvicorn
import json
import hashlib
import random
import os
import logging
from fastapi import FastAPI, WebSocket, Request, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table, or_, and_
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
import cloudinary.uploader
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jose import jwt, JWTError

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

# --- BANCO DE DADOS ---
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./for_glory_v2.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
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
    # NOVO AVATAR PADRÃO (Nunca falha)
    avatar_url = Column(String, default="https://ui-avatars.com/api/?name=Soldado&background=1f2833&color=66fcf1&bold=true")
    cover_url = Column(String, default="https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY")
    bio = Column(String, default="Recruta do For Glory")
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

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error(f"Erro BD: {e}")
    # --- LÓGICA DE PATENTES ---
def calcular_patente(xp):
    if xp < 100: return "Recruta 🔰"
    if xp < 500: return "Soldado ⚔️"
    if xp < 1000: return "Cabo 🎖️"
    if xp < 2000: return "3º Sargento 🎗️"
    if xp < 5000: return "Capitão 👑"
    return "Lenda 🐲"

# --- UTILITÁRIOS DE SENHA ---
def create_reset_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=30) 
    to_encode = {"sub": email, "exp": expire, "type": "reset"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset": return None
        return payload.get("sub") 
    except JWTError:
        return None

# --- WEBSOCKET ---
class ConnectionManager:
    def __init__(self):
        self.active = {}
    async def connect(self, ws: WebSocket, chan: str):
        await ws.accept()
        if chan not in self.active: self.active[chan] = []
        self.active[chan].append(ws)
    def disconnect(self, ws: WebSocket, chan: str):
        if chan in self.active and ws in self.active[chan]: self.active[chan].remove(ws)
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

# --- MODELOS ---
class LoginData(BaseModel): username: str; password: str
class RegisterData(BaseModel): username: str; email: str; password: str
class FriendReqData(BaseModel): target_id: int; sender_id: int = 0
class RequestActionData(BaseModel): request_id: int; action: str
class DeletePostData(BaseModel): post_id: int; user_id: int
class ForgotPasswordData(BaseModel): email: EmailStr
class ResetPasswordData(BaseModel): token: str; new_password: str

# --- DEPENDÊNCIAS ---
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def criptografar(s):
    return hashlib.sha256(s.encode()).hexdigest()

@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        if not db.query(Channel).first():
            db.add(Channel(name="Geral"))
            db.commit()
    except: pass
    db.close()
# --- FRONTEND COMPLETO ---
html_content = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Rajdhani:wght@600;700&display=swap" rel="stylesheet">
<title>For Glory</title>
<style>
:root{--primary:#66fcf1;--dark-bg:#0b0c10;--card-bg:#1f2833;--glass:rgba(31, 40, 51, 0.7);--border:rgba(102,252,241,0.15)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;scrollbar-width:thin;scrollbar-color:var(--primary) #111}
body{background-color:var(--dark-bg);background-image:radial-gradient(circle at 50% 0%, #1a1d26 0%, #0b0c10 70%);color:#e0e0e0;font-family:'Inter',sans-serif;margin:0;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
#app{display:flex;flex:1;overflow:hidden;position:relative}
#sidebar{width:80px;background:rgba(11,12,16,0.6);backdrop-filter:blur(12px);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:20px 0;z-index:20}
.nav-btn{width:50px;height:50px;border-radius:14px;border:none;background:transparent;color:#888;font-size:24px;margin-bottom:20px;cursor:pointer;transition:0.3s}
.nav-btn.active{background:rgba(102,252,241,0.15);color:var(--primary);border:1px solid var(--border);box-shadow:0 0 15px rgba(102,252,241,0.2);transform:scale(1.05)}
.my-avatar-mini{width:45px;height:45px;border-radius:50%;object-fit:cover;border:2px solid var(--border); background:#111;}

#content-area{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden}
.view{display:none;flex:1;flex-direction:column;overflow-y:auto;height:100%;width:100%;padding-bottom:20px}
.view.active{display:flex;animation:fadeIn 0.3s ease-out}

/* POSTS FEED */
#feed-container{flex:1;overflow-y:auto;padding:20px 0;padding-bottom:100px;display:flex;flex-direction:column;align-items:center}
.post-card{background:var(--card-bg);width:100%;max-width:480px;margin-bottom:20px;border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.05)}
.post-header{padding:12px 15px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.2)}
.post-av{width:42px;height:42px;border-radius:50%;margin-right:12px;object-fit:cover;border:1px solid var(--primary); background:#111;}
.rank-badge{font-size:10px;color:var(--primary);font-weight:bold;text-transform:uppercase;background:rgba(102,252,241,0.1);padding:3px 8px;border-radius:6px;border:1px solid rgba(102,252,241,0.3)}
.post-media{width:100%;max-height:600px;object-fit:contain;background:#000;display:block}
.post-caption{padding:15px;color:#ccc;font-size:14px;line-height:1.5}

/* CHAT */
#chat-list{flex:1;overflow-y:auto;padding:15px;display:flex;flex-direction:column;gap:12px}
.msg-row{display:flex;gap:10px;max-width:85%}
.msg-row.mine{align-self:flex-end;flex-direction:row-reverse}
.msg-av{width:36px;height:36px;border-radius:50%;object-fit:cover; background:#111;}
.msg-bubble{padding:10px 16px;border-radius:18px;background:#2b343f;color:#e0e0e0;word-break:break-word;font-size:15px}
.msg-row.mine .msg-bubble{background:linear-gradient(135deg,#1d4e4f,#133638);color:white;border:1px solid rgba(102,252,241,0.2)}
#chat-input-area{background:rgba(11,12,16,0.9);padding:15px;display:flex;gap:10px;align-items:center;border-top:1px solid var(--border)}
#chat-msg{flex:1;background:rgba(255,255,255,0.05);border:1px solid #444;border-radius:24px;padding:12px 20px;color:white;outline:none}

/* PERFIL E BOTÕES NOVOS */
.profile-header-container{position:relative;width:100%;height:220px;margin-bottom:60px}
.profile-cover{width:100%;height:100%;object-fit:cover;opacity:0.9;mask-image:linear-gradient(to bottom,black 60%,transparent 100%); background:#111;}
.profile-pic-lg{position:absolute;bottom:-50px;left:50%;transform:translateX(-50%);width:130px;height:130px;border-radius:50%;object-fit:cover;border:4px solid var(--dark-bg);box-shadow:0 0 25px rgba(102,252,241,0.3);cursor:pointer; background:#1f2833;}

.glass-btn {
    background: rgba(102, 252, 241, 0.08); border: 1px solid rgba(102, 252, 241, 0.3); color: var(--primary);
    padding: 12px 20px; border-radius: 12px; cursor: pointer; font-weight: bold; font-family: 'Inter', sans-serif;
    transition: 0.3s; text-transform: uppercase; font-size: 13px; letter-spacing: 1px; flex: 1;
}
.glass-btn:hover { background: rgba(102, 252, 241, 0.15); box-shadow: 0 0 10px rgba(102,252,241,0.2); }
.danger-btn { color: #ff5555; border-color: rgba(255, 85, 85, 0.3); background: rgba(255, 85, 85, 0.08); width: 100%; margin-top: 20px; }
.danger-btn:hover { background: rgba(255, 85, 85, 0.2); box-shadow: 0 0 10px rgba(255,85,85,0.2); }
.search-glass {
    display: flex; background: rgba(0,0,0,0.4); border: 1px solid #333;
    border-radius: 15px; padding: 5px 15px; margin-bottom: 20px; width: 100%;
}
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
            <input id="l-pass" class="inp" type="password" placeholder="SENHA">
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
            <p style="color:#888;font-size:12px">Enviaremos um link de resgate para seu e-mail.</p>
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

<div id="modal-upload" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:white">NOVO POST</h2>
        <input type="file" id="file-upload" class="inp" accept="image/*,video/*">
        <div style="display:flex;gap:5px;align-items:center;margin-bottom:10px;margin-top:10px">
            <input type="text" id="caption-upload" class="inp" placeholder="Legenda..." style="margin:0">
            <button onclick="openEmoji('caption-upload')" style="background:none;border:none;font-size:24px;cursor:pointer">😀</button>
        </div>
        
        <div id="upload-progress" style="display:none;background:#333;height:6px;border-radius:3px;margin-top:10px;overflow:hidden">
            <div id="progress-bar" style="width:0%;height:100%;background:var(--primary);transition:width 0.2s"></div>
        </div>
        <div id="progress-text" style="color:var(--primary);font-size:12px;margin-top:5px;display:none;font-weight:bold">0%</div>
        
        <button id="btn-pub" onclick="submitPost()" class="btn-main">PUBLICAR (+50 XP)</button>
        <button onclick="closeUpload()" class="btn-link" style="color:#888;display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none">CANCELAR</button>
    </div>
</div>

<div id="modal-profile" class="modal hidden"><div class="modal-box"><h2 style="color:var(--primary)">EDITAR PERFIL</h2><label style="color:#aaa;display:block;margin-top:10px;font-size:12px;">Foto de Perfil</label><input type="file" id="avatar-upload" class="inp" accept="image/*"><label style="color:#aaa;display:block;margin-top:10px;font-size:12px;">Capa de Fundo</label><input type="file" id="cover-upload" class="inp" accept="image/*"><input id="bio-update" class="inp" placeholder="Escreva sua Bio..."><button id="btn-save-profile" onclick="updateProfile()" class="btn-main">SALVAR</button><button onclick="document.getElementById('modal-profile').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none">FECHAR</button></div></div>

<div id="app">
    <div id="sidebar">
        <button class="nav-btn active" onclick="goView('chat')">💬</button>
        <button class="nav-btn" onclick="goView('feed')">🎬</button>
        <button class="nav-btn" onclick="goView('profile')"><img id="nav-avatar" src="" class="my-avatar-mini" onerror="this.src='https://ui-avatars.com/api/?name=User&background=111&color=66fcf1'"></button>
    </div>

    <div id="content-area">
        <div id="view-chat" class="view active">
            <div style="padding:15px;text-align:center;color:var(--primary);font-family:'Rajdhani';font-weight:bold;background:rgba(0,0,0,0.2);letter-spacing:2px;">CANAL GERAL</div>
            <div id="chat-list"></div>
            <div id="chat-input-area">
                <input type="file" id="chat-file" class="hidden" onchange="uploadChatImage()" accept="image/*,video/*">
                <button onclick="document.getElementById('chat-file').click()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#888">📎</button>
                <input id="chat-msg" placeholder="Mensagem..." onkeypress="if(event.key==='Enter')sendMsg()">
                <button onclick="openEmoji('chat-msg')" style="background:none;border:none;font-size:24px;cursor:pointer;margin-right:5px">😀</button>
                <button onclick="sendMsg()" style="background:var(--primary);border:none;width:45px;height:45px;border-radius:12px;font-weight:bold;color:#0b0c10;">➤</button>
            </div>
        </div>

        <div id="view-feed" class="view">
            <div id="feed-container"></div>
            <button class="btn-float" onclick="document.getElementById('modal-upload').classList.remove('hidden')">+</button>
        </div>

        <div id="view-profile" class="view">
            <div class="profile-header-container">
                <img id="p-cover" src="" class="profile-cover" onerror="this.src='https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY'">
                <img id="p-avatar" src="" class="profile-pic-lg" onclick="document.getElementById('modal-profile').classList.remove('hidden')" onerror="this.src='https://ui-avatars.com/api/?name=User&background=111&color=66fcf1'">
            </div>
            <div style="text-align:center;margin-top:10px">
                <h2 id="p-name" style="color:white;font-family:'Rajdhani';font-size:28px;margin:5px 0;">...</h2>
                <span id="p-rank" class="rank-badge">...</span>
                <p id="p-bio" style="color:#888;margin:10px 0 20px 0;font-style:italic;">...</p>
            </div>
            <div style="width:90%; max-width:400px; margin:0 auto; text-align:center">
                
                <div class="search-glass">
                    <input id="search-input" placeholder="Buscar Soldado...">
                    <button onclick="searchUsers()" style="background:none;border:none;color:var(--primary);font-size:18px;cursor:pointer;">🔍</button>
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
                <img id="pub-avatar" src="" class="profile-pic-lg" onerror="this.src='https://ui-avatars.com/api/?name=User&background=111&color=66fcf1'">
            </div>
            <div style="text-align:center;margin-top:20px">
                <h2 id="pub-name" style="color:white;font-family:'Rajdhani';margin:5px 0;">...</h2>
                <span id="pub-rank" class="rank-badge">...</span>
                <p id="pub-bio" style="color:#888;margin:10px 0 20px 0;">...</p>
                <div id="pub-actions" style="margin-bottom:20px;"></div>
                <div id="pub-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:2px;max-width:500px;margin:0 auto;"></div>
            </div>
        </div>
    </div>
</div>

<script>
var user=null,ws=null,syncInterval=null,lastFeedHash="",currentEmojiTarget=null;
const CLOUD_NAME = "dqa0q3qlx"; 
const UPLOAD_PRESET = "for_glory_preset"; 

// ARRAY DE EMOJIS
const EMOJIS = ["😂","🔥","❤️","💀","🎮","🇧🇷","🫡","🤡","😭","😎","🤬","👀","👍","👎","🔫","💣","⚔️","🛡️","🏆","💰","🍕","🍺","👋","🚫","✅","👑","💩","👻","👽","🤖","🤫","🥶","🤯","🥳","🤢","🤕","🤑","🤠","😈","👿","👹","👺","👾"];

function showToast(m){let x=document.getElementById("toast");x.innerText=m;x.className="show";setTimeout(()=>{x.className=""},3000)}
function toggleAuth(m){['login','register','forgot','reset'].forEach(f=>document.getElementById(f+'-form').classList.add('hidden'));document.getElementById(m+'-form').classList.remove('hidden');}

// 1. INJEÇÃO IMEDIATA E BLINDADA DE EMOJIS (Sem depender de window.onload)
function initEmojis() {
    let g = document.getElementById('emoji-grid');
    if(!g) return;
    g.innerHTML = '';
    EMOJIS.forEach(e => {
        let s = document.createElement('div');
        s.style.cssText = "font-size:24px;cursor:pointer;text-align:center;padding:5px;border-radius:5px;transition:0.2s;";
        s.innerText = e;
        s.onclick = () => {
            if(currentEmojiTarget){
                let inp = document.getElementById(currentEmojiTarget);
                inp.value += e;
                inp.focus();
            }
        };
        s.onmouseover = () => s.style.background = "rgba(102,252,241,0.2)";
        s.onmouseout = () => s.style.background = "transparent";
        g.appendChild(s);
    });
}
initEmojis(); // Chama a função na mesma hora!

// 2. VERIFICADOR DE TOKEN IMEDIATO
function checkToken() {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    if (token) {
        toggleAuth('reset');
        window.history.replaceState({}, document.title, "/");
        window.resetToken = token;
    }
}
checkToken();

function openEmoji(id){
    currentEmojiTarget = id;
    document.getElementById('emoji-picker').style.display='flex';
}

function toggleEmoji(forceClose){
    let e = document.getElementById('emoji-picker');
    if(forceClose === true) e.style.display='none';
    else e.style.display = e.style.display === 'flex' ? 'none' : 'flex';
}

// RESTO DO SISTEMA DE LOGIN E RECUPERAÇÃO
async function requestReset() {
    let email = document.getElementById('f-email').value;
    if(!email) return showToast("Digite seu e-mail!");
    try {
        let r = await fetch('/auth/forgot-password', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({email: email})
        });
        showToast("E-mail enviado! Verifique sua caixa (e spam).");
        toggleAuth('login');
    } catch(e) { showToast("Erro de conexão"); }
}
async function doResetPassword() {
    let newPass = document.getElementById('new-pass').value;
    if(!newPass) return showToast("Digite a nova senha!");
    try {
        let r = await fetch('/auth/reset-password', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({token: window.resetToken, new_password: newPass})
        });
        if(r.ok) { showToast("Senha alterada! Faça login."); toggleAuth('login'); } 
        else { showToast("Link expirado ou inválido."); }
    } catch(e) { showToast("Erro"); }
}

async function doLogin(){try{let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('l-user').value,password:document.getElementById('l-pass').value})});if(!r.ok)throw 1;user=await r.json();startApp()}catch(e){showToast("Erro Login")}}
async function doRegister(){try{let r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('r-user').value,email:document.getElementById('r-email').value,password:document.getElementById('r-pass').value})});if(!r.ok)throw 1;showToast("Registrado!");toggleAuth('login')}catch(e){showToast("Erro Registro")}}

function startApp(){document.getElementById('modal-login').classList.add('hidden');updateUI();loadFeed();connectWS();syncInterval=setInterval(()=>{if(document.getElementById('view-feed').classList.contains('active'))loadFeed()},4000)}

function updateUI(){
    if(!user) return;
    let safeAvatar = user.avatar_url;
    if(!safeAvatar || safeAvatar.includes("undefined")) {
        safeAvatar = `https://ui-avatars.com/api/?name=${user.username}&background=1f2833&color=66fcf1&bold=true`;
    }
    document.getElementById('nav-avatar').src = safeAvatar;
    document.getElementById('p-avatar').src = safeAvatar;
    let pCover = document.getElementById('p-cover');
    pCover.src = user.cover_url || "https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY";
    pCover.style.display = 'block';
    document.getElementById('p-name').innerText = user.username || "Soldado";
    document.getElementById('p-bio').innerText = user.bio || "Na base de operações.";
    document.getElementById('p-rank').innerText = user.rank || "REC";
    document.querySelectorAll('.my-avatar-mini').forEach(img => img.src = safeAvatar);
}

function logout(){location.reload()}
function goView(v){document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));document.getElementById('view-'+v).classList.add('active');document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));if(v!=='public-profile')event.target.closest('.nav-btn').classList.add('active')}

async function openPublicProfile(uid){let r=await fetch('/user/'+uid+'?viewer_id='+user.id);let d=await r.json();document.getElementById('pub-avatar').src=d.avatar_url;let pc=document.getElementById('pub-cover');pc.src=d.cover_url;pc.style.display='block';document.getElementById('pub-name').innerText=d.username;document.getElementById('pub-bio').innerText=d.bio;document.getElementById('pub-rank').innerText=d.rank;let ab=document.getElementById('pub-actions');ab.innerHTML='';if(d.friend_status==='friends')ab.innerHTML='<span style="color:#66fcf1; border:1px solid #66fcf1; padding:5px 10px; border-radius:8px;">✔ Aliado</span>';else if(d.friend_status==='pending_sent')ab.innerHTML='<span style="color:orange">Enviado</span>';else if(d.friend_status==='pending_received')ab.innerHTML=`<button class="glass-btn" onclick="handleReq(${d.request_id},'accept')">Aceitar Aliado</button>`;else ab.innerHTML=`<button class="glass-btn" onclick="sendRequest(${uid})">Recrutar Aliado</button>`;let g=document.getElementById('pub-grid');g.innerHTML='';d.posts.forEach(p=>{g.innerHTML+=p.media_type==='video'?`<video src="${p.content_url}" style="width:100%; aspect-ratio:1/1; object-fit:cover;" controls></video>`:`<img src="${p.content_url}" style="width:100%; aspect-ratio:1/1; object-fit:cover; cursor:pointer;" onclick="window.open(this.src)">`});goView('public-profile')}

async function loadFeed(){try{let r=await fetch('/posts?uid='+user.id+'&limit=50');if(!r.ok)return;let p=await r.json();let h=JSON.stringify(p.map(x=>x.id));if(h===lastFeedHash)return;lastFeedHash=h;let ht='';p.forEach(x=>{let m=x.media_type==='video'?`<video src="${x.content_url}" class="post-media" controls playsinline></video>`:`<img src="${x.content_url}" class="post-media" loading="lazy">`;let delBtn=x.author_id===user.id?`<span onclick="deletePost(${x.id})" style="cursor:pointer;opacity:0.5;font-size:20px;">🗑️</span>`:'';ht+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer" onclick="openPublicProfile(${x.author_id})"><img src="${x.author_avatar}" class="post-av"><div class="user-info-box"><b style="color:white;font-size:14px">${x.author_name}</b><div class="rank-badge">${x.author_rank}</div></div></div>${delBtn}</div>${m}<div class="post-caption"><b style="color:white">${x.author_name}</b> ${x.caption}</div></div>`});document.getElementById('feed-container').innerHTML=ht;}catch(e){}}

// UPLOADS INTELIGENTES COM PROTEÇÃO DE TAMANHO E TIPO
async function uploadToCloudinary(file){
    let limiteMB = 50; 
    if(file.size > (limiteMB * 1024 * 1024)) {
        return Promise.reject(`Arquivo muito pesado! O limite grátis é de ${limiteMB}MB.`);
    }

    let resType = file.type.startsWith('video') ? 'video' : 'image';
    let url = `https://api.cloudinary.com/v1_1/${CLOUD_NAME}/${resType}/upload`;

    let fd=new FormData();
    fd.append('file',file);
    fd.append('upload_preset',UPLOAD_PRESET);
    
    return new Promise((res,rej)=>{
        let x=new XMLHttpRequest();
        x.open('POST', url, true);
        x.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                let percent = Math.round((e.loaded / e.total) * 100);
                if(document.getElementById('progress-bar')) {
                    document.getElementById('progress-bar').style.width = percent + '%';
                    document.getElementById('progress-text').innerText = percent + '%';
                }
            }
        };
        x.onload=()=>{
            if(x.status===200) res(JSON.parse(x.responseText));
            else {
                try { rej(JSON.parse(x.responseText).error.message); } 
                catch(err) { rej("A nuvem recusou o arquivo (formato inválido)."); }
            }
        };
        x.onerror=()=>rej("Conexão caiu ou limite estourado na nuvem.");
        x.send(fd)
    });
}

async function submitPost(){
    let f=document.getElementById('file-upload').files[0];
    let cap=document.getElementById('caption-upload').value;
    if(!f)return showToast("Arquivo?");
    
    let btn=document.getElementById('btn-pub');
    btn.innerText="ENVIANDO..."; 
    btn.disabled=true;
    
    document.getElementById('upload-progress').style.display='block';
    document.getElementById('progress-text').style.display='block';

    try{
        let c = await uploadToCloudinary(f);
        let fd=new FormData();
        fd.append('user_id',user.id);
        fd.append('caption',cap);
        fd.append('content_url',c.secure_url);
        fd.append('media_type',c.resource_type);
        
        let r=await fetch('/post/create_from_url',{method:'POST',body:fd});
        if(r.ok){
            showToast("Sucesso!");
            user.xp+=50;
            lastFeedHash="";
            loadFeed();
            closeUpload();
        }
    }catch(e){
        alert("Ops! Falha na Missão: " + e); 
    }finally{
        btn.innerText="PUBLICAR (+50 XP)";
        btn.disabled=false;
        document.getElementById('upload-progress').style.display='none';
        document.getElementById('progress-text').style.display='none';
        document.getElementById('progress-bar').style.width='0%';
    }
}

async function updateProfile(){let btn=document.getElementById('btn-save-profile');btn.innerText="ENVIANDO...";btn.disabled=true;try{let f=document.getElementById('avatar-upload').files[0];let c=document.getElementById('cover-upload').files[0];let b=document.getElementById('bio-update').value;let au=null,cu=null;if(f){let r=await uploadToCloudinary(f);au=r.secure_url}if(c){let r=await uploadToCloudinary(c);cu=r.secure_url}let fd=new FormData();fd.append('user_id',user.id);if(au)fd.append('avatar_url',au);if(cu)fd.append('cover_url',cu);if(b)fd.append('bio',b);let r=await fetch('/profile/update_meta',{method:'POST',body:fd});if(r.ok){let d=await r.json();Object.assign(user,d);updateUI();document.getElementById('modal-profile').classList.add('hidden');showToast("Atualizado!")}}catch(e){alert("Erro: " + e)}finally{btn.innerText="SALVAR";btn.disabled=false;}}

// CHAT INTELIGENTE 
function connectWS(){
    if(ws)ws.close();
    let p=location.protocol==='https:'?'wss:':'ws:';
    ws=new WebSocket(`${p}//${location.host}/ws/Geral/${user.id}`);
    ws.onmessage=e=>{
        let d=JSON.parse(e.data);
        let b=document.getElementById('chat-list');
        let m=parseInt(d.user_id)===parseInt(user.id);
        
        let c = d.content;
        
        if(c.startsWith('http') && c.includes('cloudinary')) {
            if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) {
                c = `<video src="${c}" style="max-width:100%; border-radius:10px; border:1px solid #444;" controls playsinline></video>`;
            } else {
                c = `<img src="${c}" style="max-width:100%; border-radius:10px; cursor:pointer; border:1px solid #444;" onclick="window.open(this.src)">`;
            }
        }
        
        let h=`<div class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;">${d.username}</div><div class="msg-bubble">${c}</div></div></div>`;
        b.insertAdjacentHTML('beforeend',h);
        b.scrollTop=b.scrollHeight
    }
}

function sendMsg(){let i=document.getElementById('chat-msg');if(i.value.trim()){ws.send(i.value.trim());i.value=''; toggleEmoji(true);}}
async function uploadChatImage(){let f=document.getElementById('chat-file').files[0];if(!f)return;showToast("Enviando arquivo...");try{let c=await uploadToCloudinary(f);ws.send(c.secure_url);}catch(e){alert("Erro ao enviar: " + e)}}
function closeUpload(){document.getElementById('modal-upload').classList.add('hidden')}
async function searchUsers(){let q=document.getElementById('search-input').value;if(!q)return;let r=await fetch('/users/search?q='+q);let res=await r.json();let b=document.getElementById('search-results');b.innerHTML='';res.forEach(u=>{if(u.id!==user.id)b.innerHTML+=`<div style="padding:10px;background:rgba(255,255,255,0.05);margin-top:5px;border-radius:8px;display:flex;align-items:center;gap:10px;cursor:pointer" onclick="openPublicProfile(${u.id})"><img src="${u.avatar_url}" style="width:35px;height:35px;border-radius:50%;object-fit:cover;"><span>${u.username}</span></div>`})}
async function toggleRequests(type){let b=document.getElementById('requests-list');if(b.style.display==='block'){b.style.display='none';return}b.style.display='block';let d=await (await fetch('/friend/requests?uid='+user.id)).json();b.innerHTML=type==='requests'?(d.requests.length?d.requests.map(r=>`<div style="padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;">${r.username} <button class="glass-btn" style="padding:5px 10px; flex:none;" onclick="handleReq(${r.id},'accept')">Aceitar</button></div>`).join(''):'<p style="padding:10px;color:#888;">Sem solicitações.</p>'):(d.friends.length?d.friends.map(f=>`<div style="padding:10px;border-bottom:1px solid #333;cursor:pointer;" onclick="openPublicProfile(${f.id})">${f.username}</div>`).join(''):'<p style="padding:10px;color:#888;">Sem aliados.</p>')}
async function sendRequest(tid){if((await fetch('/friend/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_id:tid,sender_id:user.id})})).ok){showToast("Convite Enviado!");openPublicProfile(tid)}}
async function handleReq(rid,act){if((await fetch('/friend/handle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:rid,action:act})})).ok){showToast("Processado!");toggleRequests('requests')}}
async function deletePost(pid){if(confirm("Confirmar baixa?"))if((await fetch('/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,user_id:user.id})})).ok){lastFeedHash="";loadFeed()}}
</script>
</body>
</html>
"""
@app.get("/", response_class=HTMLResponse)
async def get(): return HTMLResponse(content=html_content)
    # --- API ENDPOINTS ---
@app.post("/auth/forgot-password")
async def forgot_password(d: ForgotPasswordData, background_tasks: BackgroundTasks, db: Session=Depends(get_db)):
    user = db.query(User).filter(User.email == d.email).first()
    if not user:
        return {"status": "ok"}
    
    token = create_reset_token(user.email)
    reset_link = f"https://for-glory.onrender.com/?token={token}"
    
    message = MessageSchema(
        subject="Recuperação de Senha - For Glory",
        recipients=[d.email],
        body=f"""
        <p>Soldado {user.username},</p>
        <p>Recebemos um pedido de resgate para sua conta.</p>
        <p>Clique no link abaixo para redefinir sua senha:</p>
        <a href="{reset_link}" style="background:#66fcf1; color:black; padding:10px 20px; text-decoration:none; border-radius:5px;">REDEFINIR SENHA</a>
        <p>Este link expira em 30 minutos.</p>
        """,
        subtype=MessageType.html
    )
    
    fm = FastMail(mail_conf)
    background_tasks.add_task(fm.send_message, message)
    return {"status": "ok"}

@app.post("/auth/reset-password")
async def reset_password(d: ResetPasswordData, db: Session=Depends(get_db)):
    email = verify_reset_token(d.token)
    if not email:
        raise HTTPException(400, "Token inválido ou expirado")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    
    user.password_hash = criptografar(d.new_password)
    db.commit()
    return {"status": "ok"}

@app.post("/register")
async def reg(d: RegisterData, db: Session=Depends(get_db)):
    if db.query(User).filter(User.username==d.username).first():
        raise HTTPException(400, "User existe")
    db.add(User(username=d.username, email=d.email, password_hash=criptografar(d.password), xp=0))
    db.commit()
    return {"status":"ok"}

@app.post("/login")
async def log(d: LoginData, db: Session=Depends(get_db)):
    u = db.query(User).filter(User.username==d.username).first()
    if not u or u.password_hash != criptografar(d.password):
        raise HTTPException(400, "Erro")
    patente = calcular_patente(u.xp)
    return {"id":u.id, "username":u.username, "avatar_url":u.avatar_url, "cover_url":u.cover_url, "bio":u.bio, "xp": u.xp, "rank": patente}

@app.post("/post/create_from_url")
async def create_post_url(user_id: int = Form(...), caption: str = Form(""), content_url: str = Form(...), media_type: str = Form(...), db: Session=Depends(get_db)):
    db.add(Post(user_id=user_id, content_url=content_url, media_type=media_type, caption=caption))
    user = db.query(User).filter(User.id == user_id).first()
    if user: user.xp += 50 
    db.commit()
    return {"status":"ok"}

@app.post("/profile/update_meta")
async def update_prof_meta(user_id: int = Form(...), bio: str = Form(None), avatar_url: str = Form(None), cover_url: str = Form(None), db: Session=Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if avatar_url: u.avatar_url = avatar_url
    if cover_url: u.cover_url = cover_url
    if bio: u.bio = bio
    db.commit()
    return {"avatar_url": u.avatar_url, "cover_url": u.cover_url, "bio": u.bio, "rank": calcular_patente(u.xp)}

@app.get("/posts")
async def get_posts(uid: int, limit: int = 50, db: Session=Depends(get_db)):
    posts = db.query(Post).order_by(Post.timestamp.desc()).limit(limit).all()
    return [{"id": p.id, "content_url": p.content_url, "media_type": p.media_type, "caption": p.caption, "author_name": p.author.username, "author_avatar": p.author.avatar_url, "author_rank": calcular_patente(p.author.xp), "author_id": p.author.id} for p in posts]

@app.get("/users/search")
async def search_users(q: str, db: Session=Depends(get_db)):
    users = db.query(User).filter(User.username.like(f"%{q}%")).limit(10).all()
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in users]

@app.post("/upload/chat")
async def upload_chat(file: UploadFile = File(...)):
    return {"url": ""}

@app.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int, db: Session=Depends(get_db)):
    await manager.connect(ws, ch)
    try:
        while True:
            txt = await ws.receive_text()
            u_fresh = db.query(User).filter(User.id == uid).first()
            await manager.broadcast({"user_id": u_fresh.id, "username": u_fresh.username, "avatar": u_fresh.avatar_url, "content": txt}, ch)
    except:
        manager.disconnect(ws, ch)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)



