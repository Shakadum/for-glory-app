import uvicorn
import json
import hashlib
import random
import os
import shutil
import logging
from fastapi import FastAPI, WebSocket, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table, or_, and_
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from datetime import datetime
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# --- CONFIGURAÇÃO ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForGlory")

if not os.path.exists("static"):
    os.makedirs("static")

# --- BANCO DE DADOS ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./for_glory_v2.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
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
    avatar_url = Column(String, default="https://api.dicebear.com/7.x/notionists/svg?seed=Glory")
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
except:
    pass
    # --- LÓGICA DE PATENTES ---
def calcular_patente(xp):
    if xp < 100: return "Recruta 🔰"
    if xp < 500: return "Soldado ⚔️"
    if xp < 1000: return "Cabo 🎖️"
    if xp < 2000: return "3º Sargento 🎗️"
    if xp < 5000: return "Capitão 👑"
    return "Lenda 🐲"

# --- WEBSOCKET ---
class ConnectionManager:
    def __init__(self):
        self.active = {}
    async def connect(self, ws: WebSocket, chan: str):
        await ws.accept()
        if chan not in self.active:
            self.active[chan] = []
        self.active[chan].append(ws)
    def disconnect(self, ws: WebSocket, chan: str):
        if chan in self.active and ws in self.active[chan]:
            self.active[chan].remove(ws)
    async def broadcast(self, msg: dict, chan: str):
        for conn in self.active.get(chan, []):
            try:
                await conn.send_text(json.dumps(msg))
            except:
                pass

manager = ConnectionManager()
app = FastAPI(title="For Glory Optimized")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- MODELOS ---
class LoginData(BaseModel): username: str; password: str
class RegisterData(BaseModel): username: str; email: str; password: str
class FriendReqData(BaseModel): target_id: int; sender_id: int = 0
class RequestActionData(BaseModel): request_id: int; action: str
class DeletePostData(BaseModel): post_id: int; user_id: int

# --- DEPENDÊNCIAS ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def criptografar(s):
    return hashlib.sha256(s.encode()).hexdigest()

@app.on_event("startup")
def startup():
    db = SessionLocal()
    if not db.query(Channel).first():
        db.add(Channel(name="Geral"))
        db.commit()
    db.close()
    # --- FRONTEND COMPLETO ---
html_content = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, interactive-widget=resizes-content">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Rajdhani:wght@600;700&display=swap" rel="stylesheet">
<title>For Glory</title>
<style>
:root{--primary:#66fcf1;--dark-bg:#0b0c10;--card-bg:#1f2833;--glass:rgba(31, 40, 51, 0.7);--border:rgba(102,252,241,0.15)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;scrollbar-width:thin;scrollbar-color:var(--primary) #111}
body{background-color:var(--dark-bg);background-image:radial-gradient(circle at 50% 0%, #1a1d26 0%, #0b0c10 70%);color:#e0e0e0;font-family:'Inter',sans-serif;margin:0;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
#app{display:flex;flex:1;overflow:hidden;position:relative}
#sidebar{width:80px;background:rgba(11,12,16,0.6);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:20px 0;z-index:20}
.nav-btn{width:50px;height:50px;border-radius:14px;border:none;background:transparent;color:#888;font-size:24px;margin-bottom:20px;cursor:pointer;transition:0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)}
.nav-btn.active{background:rgba(102,252,241,0.15);color:var(--primary);border:1px solid var(--border);box-shadow:0 0 15px rgba(102,252,241,0.2);transform:scale(1.05)}
.my-avatar-mini{width:45px;height:45px;border-radius:50%;object-fit:cover;border:2px solid var(--border);transition:0.3s}
#content-area{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden}
.view{display:none;flex:1;flex-direction:column;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;height:100%;width:100%;padding-bottom:20px}
.view.active{display:flex;animation:fadeInView 0.3s ease-out}
#feed-container{flex:1;overflow-y:auto;padding:20px 0;padding-bottom:100px;display:flex;flex-direction:column;align-items:center}
.post-card{background:var(--card-bg);width:100%;max-width:480px;margin-bottom:20px;border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.05);overflow:hidden;transition:transform 0.2s}
.post-header{padding:12px 15px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.2)}
.post-av{width:42px;height:42px;border-radius:50%;margin-right:12px;object-fit:cover;border:1px solid var(--primary)}
.user-info-box{display:flex;flex-direction:column;justify-content:center}
.rank-badge{font-size:10px;color:var(--primary);font-weight:bold;text-transform:uppercase;letter-spacing:1px;background:rgba(102,252,241,0.1);padding:2px 6px;border-radius:4px;width:fit-content;margin-top:2px}
.post-media{width:100%;max-height:600px;object-fit:contain;background:#000;display:block}
.post-caption{padding:15px;color:#ccc;font-size:14px;line-height:1.5}
#chat-list{flex:1;overflow-y:auto;padding:15px;display:flex;flex-direction:column;gap:12px}
.msg-row{display:flex;gap:10px;max-width:85%;animation:slideIn 0.2s ease}
.msg-row.mine{align-self:flex-end;flex-direction:row-reverse}
.msg-av{width:36px;height:36px;border-radius:50%;object-fit:cover;cursor:pointer;box-shadow:0 2px 5px rgba(0,0,0,0.5)}
.msg-bubble{padding:10px 16px;border-radius:18px;background:#2b343f;color:#e0e0e0;word-break:break-word;font-size:15px;line-height:1.4;box-shadow:0 2px 5px rgba(0,0,0,0.2)}
.msg-row.mine .msg-bubble{background:linear-gradient(135deg,#1d4e4f,#133638);color:white;border:1px solid rgba(102,252,241,0.2);border-bottom-right-radius:4px}
.msg-row:not(.mine) .msg-bubble{border-top-left-radius:4px}
#chat-input-area{background:rgba(11,12,16,0.9);backdrop-filter:blur(10px);padding:15px;display:flex;gap:10px;align-items:center;flex-shrink:0;border-top:1px solid var(--border)}
#chat-msg{flex:1;background:rgba(255,255,255,0.05);border:1px solid #444;border-radius:24px;padding:12px 20px;color:white;outline:none;font-size:16px;transition:0.2s}
#chat-msg:focus{border-color:var(--primary);background:rgba(0,0,0,0.3)}
.profile-header-container{position:relative;width:100%;height:220px;margin-bottom:60px}
.profile-cover{width:100%;height:100%;object-fit:cover;opacity:0.9;mask-image:linear-gradient(to bottom,black 60%,transparent 100%);-webkit-mask-image:linear-gradient(to bottom,black 60%,transparent 100%)}
.profile-pic-lg{position:absolute;bottom:-50px;left:50%;transform:translateX(-50%);width:130px;height:130px;border-radius:50%;object-fit:cover;border:4px solid var(--dark-bg);box-shadow:0 0 25px rgba(102,252,241,0.3);cursor:pointer;z-index:2}
.btn-float{position:fixed;bottom:90px;right:25px;width:60px;height:60px;border-radius:50%;background:var(--primary);border:none;font-size:32px;box-shadow:0 4px 20px rgba(102,252,241,0.4);cursor:pointer;z-index:50;display:flex;align-items:center;justify-content:center;color:#0b0c10;transition:transform 0.2s}
.btn-float:active{transform:scale(0.9)}

/* MODAL ESCURO (Blackout) E PROGRESSO */
.modal{position:fixed;inset:0;background:rgba(0,0,0,0.95);z-index:9000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(15px)}
.modal-box{background:rgba(20,25,35,0.95);padding:30px;border-radius:24px;border:1px solid var(--border);width:90%;max-width:380px;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,0.8);animation:scaleUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)}
.inp{width:100%;padding:14px;margin:10px 0;background:rgba(0,0,0,0.3);border:1px solid #444;color:white;border-radius:10px;text-align:center;font-size:16px}
.inp:focus{border-color:var(--primary);outline:none}
.btn-main{width:100%;padding:14px;margin-top:15px;background:var(--primary);border:none;font-weight:700;border-radius:10px;cursor:pointer;font-size:16px;color:#0b0c10;text-transform:uppercase;letter-spacing:1px;transition:0.2s}
.btn-main:hover{box-shadow:0 0 15px rgba(102,252,241,0.4)}
.btn-main:disabled{opacity:0.5;cursor:not-allowed}
.progress-wrapper{width:100%;background:#333;height:10px;border-radius:5px;margin-top:10px;overflow:hidden;display:none}
.progress-fill{height:100%;background:var(--primary);width:0%;transition:width 0.2s}
.hidden{display:none !important}
#toast{visibility:hidden;opacity:0;min-width:200px;background:var(--primary);color:#000;text-align:center;border-radius:50px;padding:12px 24px;position:fixed;z-index:9999;left:50%;top:30px;transform:translateX(-50%);font-weight:bold;box-shadow:0 5px 15px rgba(102,252,241,0.4);transition:opacity 0.3s, visibility 0.3s}
#toast.show{visibility:visible;opacity:1}

@keyframes fadeInView{from{opacity:0;transform:scale(0.98)}to{opacity:1;transform:scale(1)}}
@keyframes scaleUp{from{transform:scale(0.8);opacity:0}to{transform:scale(1);opacity:1}}
@keyframes slideIn{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:translateX(0)}}
@media(max-width:768px){#app{flex-direction:column-reverse}#sidebar{width:100%;height:65px;flex-direction:row;justify-content:space-around;padding:0;border-top:1px solid var(--border);border-right:none;background:rgba(11,12,16,0.95)}.btn-float{bottom:80px}#feed-container{padding-top:10px}.post-card{border-radius:0;border:none;margin-bottom:10px}}
</style>
</head>
<body>
<div id="toast">Notificação</div>
<div id="emoji-picker" style="position:absolute;bottom:80px;right:10px;width:90%;max-width:320px;background:rgba(20,25,35,0.95);border:1px solid var(--border);border-radius:15px;display:none;flex-direction:column;z-index:10001;box-shadow:0 0 25px rgba(0,0,0,0.8);backdrop-filter:blur(10px)">
    <div style="padding:10px 15px;display:flex;justify-content:space-between;border-bottom:1px solid #333"><span style="color:var(--primary);font-weight:bold;font-family:'Rajdhani'">EMOJIS</span><span onclick="toggleEmoji()" style="color:#ff5555;cursor:pointer;font-weight:bold">✕</span></div>
    <div id="emoji-grid" style="display:grid;grid-template-columns:repeat(7,1fr);gap:5px;padding:10px;max-height:220px;overflow-y:auto"></div>
</div>

<div id="modal-login" class="modal"><div class="modal-box"><h1 style="color:var(--primary);font-family:'Rajdhani';font-size:42px;margin:0 0 10px 0;text-shadow:0 0 10px rgba(102,252,241,0.3)">FOR GLORY</h1><p style="color:#888;margin-bottom:20px;font-size:14px">A COMUNIDADE DE ELITE</p><div id="login-form"><input id="l-user" class="inp" placeholder="CODINOME"><input id="l-pass" class="inp" type="password" placeholder="SENHA"><button onclick="doLogin()" class="btn-main">ENTRAR</button><div style="margin-top:20px;font-size:14px;color:#888"><span onclick="toggleAuth('register')" style="text-decoration:underline;cursor:pointer;color:white">Criar Conta</span></div></div><div id="register-form" class="hidden"><input id="r-user" class="inp" placeholder="NOVO USUÁRIO"><input id="r-email" class="inp" placeholder="EMAIL"><input id="r-pass" class="inp" type="password" placeholder="SENHA"><button onclick="doRegister()" class="btn-main">ALISTAR-SE</button><p onclick="toggleAuth('login')" style="color:#888;text-decoration:underline;cursor:pointer;margin-top:20px">Voltar</p></div></div></div>

<div id="modal-upload" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:white;font-family:'Rajdhani'">NOVO ARQUIVO</h2>
        <input type="file" id="file-upload" class="inp" accept="image/*,video/*" style="text-align:left">
        <div style="display:flex;gap:5px;align-items:center;margin-bottom:10px">
            <input type="text" id="caption-upload" class="inp" placeholder="Legenda da Missão..." style="margin:0;text-align:left">
            <button onclick="openEmoji('caption-upload')" style="background:none;border:none;font-size:22px;cursor:pointer">😀</button>
        </div>
        <div id="upload-progress" class="progress-wrapper"><div id="progress-bar" class="progress-fill"></div></div>
        <div id="progress-text" style="color:var(--primary);font-size:12px;margin-top:5px;display:none">0%</div>
        <button onclick="submitPost()" class="btn-main">PUBLICAR (+50 XP)</button>
        <button onclick="closeUpload()" style="width:100%;padding:12px;margin-top:10px;background:transparent;border:1px solid #444;color:#888;border-radius:10px;cursor:pointer">CANCELAR</button>
    </div>
</div>

<div id="modal-profile" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:var(--primary)">DADOS DO SOLDADO</h2>
        <label style="color:#aaa;font-size:12px;display:block;margin-top:10px">Foto de Perfil</label>
        <input type="file" id="avatar-upload" class="inp" accept="image/*">
        <label style="color:#aaa;font-size:12px;display:block;margin-top:10px">Capa de Fundo</label>
        <input type="file" id="cover-upload" class="inp" accept="image/*">
        <input type="text" id="bio-update" class="inp" placeholder="Bio...">
        <button id="btn-save-profile" onclick="updateProfile()" class="btn-main">SALVAR ALTERAÇÕES</button>
        <button onclick="document.getElementById('modal-profile').classList.add('hidden')" style="width:100%;padding:12px;margin-top:10px;background:transparent;border:1px solid #444;color:#888;border-radius:10px;cursor:pointer">FECHAR</button>
    </div>
</div>

<div id="app"><div id="sidebar"><button class="nav-btn active" onclick="goView('chat')">💬</button><button class="nav-btn" onclick="goView('feed')">🎬</button><button class="nav-btn" onclick="goView('profile')"><img id="nav-avatar" src="" class="my-avatar-mini"></button></div>
<div id="content-area">
<div id="view-chat" class="view active"><div style="padding:15px;border-bottom:1px solid rgba(255,255,255,0.05);color:var(--primary);font-family:'Rajdhani';font-weight:bold;letter-spacing:2px;text-align:center;background:rgba(0,0,0,0.2)">CANAL GERAL</div><div id="chat-list"></div><div id="chat-input-area"><button onclick="document.getElementById('chat-file').click()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#888;padding:5px">📎</button><input type="file" id="chat-file" class="hidden" onchange="uploadChatImage()"><input id="chat-msg" placeholder="Enviar mensagem..." onkeypress="if(event.key==='Enter')sendMsg()"><button onclick="openEmoji('chat-msg')" style="background:none;border:none;font-size:22px;cursor:pointer;margin-right:5px">😀</button><button onclick="sendMsg()" style="background:var(--primary);border:none;width:45px;height:45px;border-radius:12px;font-weight:bold;display:flex;align-items:center;justify-content:center;color:#0b0c10;box-shadow:0 0 10px rgba(102,252,241,0.3)">➤</button></div></div>
<div id="view-feed" class="view"><div id="feed-container"></div><button class="btn-float" onclick="document.getElementById('modal-upload').classList.remove('hidden')">+</button></div>
<div id="view-profile" class="view"><div class="profile-header-container"><img id="p-cover" src="" class="profile-cover" onerror="this.style.display='none'" onload="this.style.display='block'"><img id="p-avatar" src="" class="profile-pic-lg" onclick="document.getElementById('modal-profile').classList.remove('hidden')"></div><div style="display:flex;flex-direction:column;align-items:center;width:100%;text-align:center;margin-top:20px;"><h2 id="p-name" style="color:white;font-family:'Rajdhani';margin:5px 0;font-size:28px">...</h2><div id="p-rank" style="background:rgba(102,252,241,0.15);color:var(--primary);padding:4px 12px;border-radius:20px;font-weight:bold;font-size:12px;margin-bottom:10px;border:1px solid rgba(102,252,241,0.3)">REC</div><p id="p-bio" style="color:#888;width:80%;margin:0 0 20px 0;font-style:italic">...</p></div><div style="width:90%;max-width:400px;margin:0 auto"><div style="display:flex;background:rgba(255,255,255,0.05);border-radius:12px;padding:5px;margin-bottom:20px"><input id="search-input" placeholder="Buscar Soldado..." style="flex:1;background:transparent;border:none;color:white;padding:10px;outline:none"><button onclick="searchUsers()" style="background:none;border:none;color:var(--primary);font-size:18px;cursor:pointer;padding:0 15px">🔍</button></div><div id="search-results"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px"><button onclick="toggleRequests('requests')" style="padding:12px;background:rgba(255,255,255,0.05);border:1px solid #333;color:white;border-radius:8px;cursor:pointer">📩 Solicitações</button><button onclick="toggleRequests('friends')" style="padding:12px;background:rgba(255,255,255,0.05);border:1px solid #333;color:white;border-radius:8px;cursor:pointer">👥 Pelotão</button></div><div id="requests-list" style="display:none;margin-top:15px;background:rgba(0,0,0,0.3);padding:10px;border-radius:10px"></div><button onclick="logout()" style="width:100%;margin-top:40px;padding:15px;background:transparent;border:1px solid #ff5555;color:#ff5555;border-radius:10px;cursor:pointer;font-weight:bold">DESCONECTAR</button></div></div>
<div id="view-public-profile" class="view"><button onclick="goView('feed')" style="position:absolute;top:20px;left:20px;z-index:10;background:rgba(0,0,0,0.6);backdrop-filter:blur(5px);border:1px solid #444;color:white;border-radius:8px;padding:8px 15px;cursor:pointer">⬅ Voltar</button><div class="profile-header-container"><img id="pub-cover" src="" class="profile-cover" onerror="this.style.display='none'" onload="this.style.display='block'"><img id="pub-avatar" src="" class="profile-pic-lg" style="cursor:default;border-color:#888"></div><div style="display:flex;flex-direction:column;align-items:center;text-align:center;margin-top:20px"><h2 id="pub-name" style="color:white;font-family:'Rajdhani';margin-bottom:5px">...</h2><span id="pub-rank" style="color:var(--primary);font-size:12px;font-weight:bold;margin-bottom:10px;text-transform:uppercase">...</span><p id="pub-bio" style="color:#888;margin-bottom:20px;width:80%">...</p><div id="pub-actions" style="margin-bottom:20px"></div><div id="pub-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:2px;width:100%;max-width:500px"></div></div></div></div></div>
<script>
var user=null,ws=null,syncInterval=null,lastFeedHash="",currentEmojiTarget=null;
const EMOJIS = ["😂","🔥","❤️","💀","🎮","🇧🇷","🫡","🤡","😭","😎","🤬","👀","👍","👎","🔫","💣","⚔️","🛡️","🏆","💰","🍕","🍺","👋","🚫","✅","👑","💩","👻","👽","🤖","🤫","🥶","🤯","🥳","🤢","🤕","🤑","🤠","😈","👿","👹","👺","👾"];

function showToast(m){
    let x = document.getElementById("toast");
    x.innerText = m;
    x.className = "show";
    setTimeout(function(){ x.className = x.className.replace("show", ""); }, 3000);
}

function toggleAuth(m){document.getElementById('login-form').classList.toggle('hidden',m==='register');document.getElementById('register-form').classList.toggle('hidden',m!=='register')}
async function doLogin(){try{let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('l-user').value,password:document.getElementById('l-pass').value})});if(!r.ok)throw 1;user=await r.json();startApp()}catch(e){showToast("Credenciais Inválidas")}}
async function doRegister(){try{let r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('r-user').value,email:document.getElementById('r-email').value,password:document.getElementById('r-pass').value})});if(!r.ok)throw 1;showToast("Recruta Registrado!");toggleAuth('login')}catch(e){showToast("Erro ao Registrar")}}
function startApp(){document.getElementById('modal-login').classList.add('hidden');updateUI();loadFeed();connectWS();syncInterval=setInterval(()=>{if(document.getElementById('view-feed').classList.contains('active'))loadFeed()},4000)}

function updateUI(){
    if(!user) return;
    let t=new Date().getTime();
    
    // ATUALIZAÇÃO FORÇADA E AGRESSIVA DAS IMAGENS
    let elements = document.getElementsByTagName('img');
    let baseAvatar = user.avatar_url.split("?")[0];
    
    for(let i=0; i<elements.length; i++){
        let img = elements[i];
        // Se a imagem for o avatar do usuário, atualiza a source
        if(img.src.includes(baseAvatar) || img.classList.contains('my-avatar-mini') || img.id === 'p-avatar'){
            img.src = baseAvatar + "?t=" + t;
        }
    }

    document.getElementById('nav-avatar').src = user.avatar_url + "?t=" + t;
    
    // Tratamento da capa: Se for vazia ou placeholder padrão, não precisa esconder, só atualizar
    let cv = user.cover_url || "https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY";
    let pCover = document.getElementById('p-cover');
    pCover.src = cv + "?t=" + t;
    pCover.style.display = 'block'; // Tenta mostrar

    document.getElementById('p-name').innerText=user.username;
    document.getElementById('p-bio').innerText=user.bio;
    document.getElementById('p-rank').innerText=user.rank;
}

function logout(){location.reload()}
function goView(v){document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));document.getElementById('view-'+v).classList.add('active');document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));if(v!=='public-profile'){document.querySelector(`.nav-btn[onclick="goView('${v}')"]`).classList.add('active')}}
async function openPublicProfile(uid){let r=await fetch('/user/'+uid+'?viewer_id='+user.id);let d=await r.json();let t=new Date().getTime();document.getElementById('pub-avatar').src=d.avatar_url+"?t="+t;let pc=document.getElementById('pub-cover');pc.src=d.cover_url+"?t="+t;pc.style.display='block';document.getElementById('pub-name').innerText=d.username;document.getElementById('pub-bio').innerText=d.bio;document.getElementById('pub-rank').innerText=d.rank;let ab=document.getElementById('pub-actions');ab.innerHTML='';if(d.friend_status==='friends')ab.innerHTML='<span style="color:#66fcf1;font-weight:bold;border:1px solid #66fcf1;padding:5px 10px;border-radius:8px">✔ Aliado</span>';else if(d.friend_status==='pending_sent')ab.innerHTML='<span style="color:orange">Convite Enviado</span>';else if(d.friend_status==='pending_received')ab.innerHTML=`<button class="btn-main" style="margin:0;padding:8px 20px" onclick="handleReq(${d.request_id},'accept')">Aceitar Aliado</button>`;else ab.innerHTML=`<button class="btn-main" style="margin:0;padding:8px 20px;background:transparent;border:1px solid var(--primary);color:var(--primary)" onclick="sendRequest(${uid})">Recrutar Aliado</button>`;let g=document.getElementById('pub-grid');g.innerHTML='';d.posts.forEach(p=>{g.innerHTML+=p.media_type==='video'?`<video src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;background:#111" controls></video>`:`<img src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;cursor:pointer">`});goView('public-profile')}
async function loadFeed(){try{let r=await fetch('/posts?uid='+user.id+'&limit=50');if(!r.ok)return;let p=await r.json();let h=JSON.stringify(p.map(x=>x.id));if(h===lastFeedHash)return;lastFeedHash=h;let ht='';p.forEach(x=>{let m=x.media_type==='video'?`<video src="${x.content_url}" class="post-media" controls playsinline></video>`:`<img src="${x.content_url}" class="post-media" loading="lazy">`;let delBtn=x.author_id===user.id?`<span onclick="deletePost(${x.id})" style="cursor:pointer;opacity:0.5">🗑️</span>`:'';ht+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer" onclick="openPublicProfile(${x.author_id})"><img src="${x.author_avatar}" class="post-av"><div class="user-info-box"><b style="color:white;font-size:14px">${x.author_name}</b><div class="rank-badge">${x.author_rank}</div></div></div>${delBtn}</div>${m}<div class="post-caption"><b style="color:white">${x.author_name}</b> ${x.caption}</div></div>`});document.getElementById('feed-container').innerHTML=ht;}catch(e){}}

function submitPost(){
    let f=document.getElementById('file-upload').files[0];
    let cap=document.getElementById('caption-upload').value;
    if(!f)return showToast("Selecione um arquivo!");
    
    // UI Progresso
    document.getElementById('upload-progress').style.display='block';
    let pBar = document.getElementById('progress-bar');
    let pText = document.getElementById('progress-text');
    pText.style.display='block';

    let fd=new FormData();fd.append('file',f);fd.append('user_id',user.id);fd.append('caption',cap);
    let xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload/post', true);
    
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            let percent = Math.round((e.loaded / e.total) * 100);
            pBar.style.width = percent + '%';
            pText.innerText = percent + '%';
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            showToast("Publicado! +50 XP");
            user.xp+=50; lastFeedHash=""; loadFeed(); closeUpload();
            fetch('/login',{method:'POST',body:JSON.stringify({username:user.username,password:''})}).then(r=>r.json()).then(u=>{user=u;updateUI()});
        } else {
            showToast("Falha no envio");
        }
        document.getElementById('upload-progress').style.display='none';
        pText.style.display='none';
        pBar.style.width='0%';
    };
    xhr.send(fd);
}

function connectWS(){
    if(ws)ws.close();
    let p=location.protocol==='https:'?'wss:':'ws:';
    ws=new WebSocket(`${p}//${location.host}/ws/Geral/${user.id}`);
    ws.onmessage=e=>{
        let d=JSON.parse(e.data);
        let b=document.getElementById('chat-list');
        
        // CORREÇÃO CRÍTICA DO LADO DA MENSAGEM
        // Força comparação de Inteiros para não ter erro
        let currentUserId = parseInt(user.id);
        let msgUserId = parseInt(d.user_id);
        let m = (msgUserId === currentUserId);
        
        let c=d.content.includes('/static/')?`<img src="${d.content}" style="max-width:200px;border-radius:10px">`:d.content;
        let html=`<div class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})"><div><div style="font-size:11px;color:#888;margin-bottom:2px">${d.username}</div><div class="msg-bubble">${c}</div></div></div>`;
        b.insertAdjacentHTML('beforeend',html);
        b.scrollTop=b.scrollHeight;
    };
}

function sendMsg(){
    let i=document.getElementById('chat-msg');
    if(i.value.trim()){
        ws.send(i.value.trim());
        i.value='';
        toggleEmoji(true);
    }
}

async function uploadChatImage(){let f=document.getElementById('chat-file').files[0];let fd=new FormData();fd.append('file',f);let r=await fetch('/upload/chat',{method:'POST',body:fd});if(r.ok){let d=await r.json();ws.send(d.url)}}
async function searchUsers(){let q=document.getElementById('search-input').value;if(!q)return;let r=await fetch('/users/search?q='+q);let res=await r.json();let b=document.getElementById('search-results');b.innerHTML='';res.forEach(u=>{if(u.id!==user.id)b.innerHTML+=`<div style="padding:10px;border-bottom:1px solid #333;display:flex;align-items:center;gap:10px;cursor:pointer" onclick="openPublicProfile(${u.id})"><img src="${u.avatar_url}" style="width:30px;height:30px;border-radius:50%"><span>${u.username}</span></div>`})}
async function toggleRequests(type){let b=document.getElementById('requests-list');if(b.style.display==='block'){b.style.display='none';return}b.style.display='block';let d=await (await fetch('/friend/requests?uid='+user.id)).json();b.innerHTML=type==='requests'?(d.requests.length?d.requests.map(r=>`<div>${r.username} <button onclick="handleReq(${r.id},'accept')">✅</button></div>`).join(''):'Sem convites'):(d.friends.length?d.friends.map(f=>`<div onclick="openPublicProfile(${f.id})">${f.username}</div>`).join(''):'Sem aliados')}
async function sendRequest(tid){if((await fetch('/friend/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_id:tid,sender_id:user.id})})).ok){showToast("Convite Enviado!");openPublicProfile(tid)}}
async function handleReq(rid,act){if((await fetch('/friend/handle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:rid,action:act})})).ok){showToast("Processado!");toggleRequests('requests')}}
async function deletePost(pid){if(confirm("Confirmar baixa?"))if((await fetch('/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,user_id:user.id})})).ok){lastFeedHash="";loadFeed()}}

async function updateProfile(){
    let btn = document.getElementById('btn-save-profile');
    btn.innerText = "PROCESSANDO...";
    btn.disabled = true;

    try {
        let fd=new FormData();
        fd.append('user_id', user.id);
        
        let f=document.getElementById('avatar-upload').files[0];
        let c=document.getElementById('cover-upload').files[0];
        let b=document.getElementById('bio-update').value;
        
        if(f) fd.append('file',f);
        if(c) fd.append('cover',c);
        if(b) fd.append('bio',b);

        let r=await fetch('/profile/update',{method:'POST',body:fd});
        
        if(r.ok){
            let d=await r.json();
            Object.assign(user,d);
            updateUI(); // Chama a atualização agressiva
            document.getElementById('modal-profile').classList.add('hidden');
            showToast("Perfil Atualizado!");
        } else {
            alert("Erro no servidor: " + r.status);
        }
    } catch(e) {
        alert("Erro na conexão: " + e);
    } finally {
        btn.innerText = "SALVAR ALTERAÇÕES";
        btn.disabled = false;
    }
}

function closeUpload(){document.getElementById('modal-upload').classList.add('hidden');document.getElementById('file-upload').value="";document.getElementById('caption-upload').value="";document.getElementById('progress-bar').style.width='0%';}
function openEmoji(id){currentEmojiTarget=id;document.getElementById('emoji-picker').style.display='flex'}

function toggleEmoji(forceClose){
    let e=document.getElementById('emoji-picker');
    if(forceClose===true) e.style.display='none';
    else e.style.display=e.style.display==='flex'?'none':'flex';
}

window.onload=()=>{
    let g=document.getElementById('emoji-grid');
    EMOJIS.forEach(e=>{
        let s=document.createElement('div');
        s.style.cssText="font-size:24px;cursor:pointer;text-align:center;padding:5px;";
        s.innerText=e;
        s.onclick=()=>{
            if(currentEmojiTarget){
                let inp = document.getElementById(currentEmojiTarget);
                inp.value+=e;
                inp.focus();
            }
        };
        g.appendChild(s)
    })
};
</script>
<style>@keyframes fadeInOut{0%{top:0;opacity:0}20%{top:30px;opacity:1}80%{top:30px;opacity:1}100%{top:0;opacity:0}}</style>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get(): return HTMLResponse(content=html_content)
    # --- API ENDPOINTS ---
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
    if not u:
         if d.password == "" and d.username: pass 
         else: raise HTTPException(400, "Erro")
    elif u.password_hash != criptografar(d.password):
        raise HTTPException(400, "Erro")
    patente = calcular_patente(u.xp)
    return {"id":u.id, "username":u.username, "avatar_url":u.avatar_url, "cover_url":u.cover_url, "bio":u.bio, "xp": u.xp, "rank": patente}

@app.post("/upload/post")
async def upload_post(user_id: int = Form(...), caption: str = Form(""), file: UploadFile = File(...), db: Session=Depends(get_db)):
    filename = f"p_{user_id}_{random.randint(1000,9999)}_{file.filename}"
    with open(f"static/{filename}", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    m_type = "video" if file.content_type.startswith("video") else "image"
    db.add(Post(user_id=user_id, content_url=f"/static/{filename}", media_type=m_type, caption=caption))
    user = db.query(User).filter(User.id == user_id).first()
    if user: user.xp += 50 
    db.commit()
    return {"status":"ok"}

@app.post("/post/delete")
async def delete_post_endpoint(d: DeletePostData, db: Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id == d.post_id).first()
    if not post or post.user_id != d.user_id:
        return {"status": "error"}
    try: os.remove(f".{post.content_url}")
    except: pass
    db.delete(post)
    db.commit()
    return {"status": "ok"}

@app.post("/upload/chat")
async def upload_chat(file: UploadFile = File(...)):
    filename = f"c_{random.randint(10000,99999)}_{file.filename}"
    with open(f"static/{filename}", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"url": f"/static/{filename}"}

@app.get("/posts")
async def get_posts(uid: int, limit: int = 50, db: Session=Depends(get_db)):
    posts = db.query(Post).order_by(Post.timestamp.desc()).limit(limit).all()
    me = db.query(User).filter(User.id == uid).first()
    my_friends_ids = [f.id for f in me.friends] if me else []
    result = []
    for p in posts:
        rank_author = calcular_patente(p.author.xp)
        result.append({"id": p.id, "content_url": p.content_url, "media_type": p.media_type, "caption": p.caption, "author_name": p.author.username, "author_avatar": p.author.avatar_url, "author_rank": rank_author, "author_id": p.author.id, "is_friend": p.author.id in my_friends_ids})
    return result

@app.get("/users/search")
async def search_users(q: str, db: Session=Depends(get_db)):
    users = db.query(User).filter(User.username.like(f"%{q}%")).limit(10).all()
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in users]

@app.post("/profile/update")
async def update_prof(user_id: int = Form(...), bio: str = Form(None), file: UploadFile = File(None), cover: UploadFile = File(None), db: Session=Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if file and file.filename:
        fname = f"a_{user_id}_{random.randint(1000,9999)}_{file.filename}"
        with open(f"static/{fname}", "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        u.avatar_url = f"/static/{fname}"
    if cover and cover.filename:
        cname = f"cv_{user_id}_{random.randint(1000,9999)}_{cover.filename}"
        with open(f"static/{cname}", "wb") as buffer: shutil.copyfileobj(cover.file, buffer)
        u.cover_url = f"/static/{cname}"
    if bio: u.bio = bio
    db.commit()
    return {"avatar_url": u.avatar_url, "cover_url": u.cover_url, "bio": u.bio, "rank": calcular_patente(u.xp)}

@app.post("/friend/request")
async def send_req(d: dict, db: Session=Depends(get_db)):
    sender_id = d.get('sender_id')
    target_id = d.get('target_id')
    me = db.query(User).filter(User.id == sender_id).first()
    target = db.query(User).filter(User.id == target_id).first()
    if target in me.friends: return {"status": "already_friends"}
    existing = db.query(FriendRequest).filter(or_(and_(FriendRequest.sender_id==sender_id, FriendRequest.receiver_id==target_id),and_(FriendRequest.sender_id==target_id, FriendRequest.receiver_id==sender_id))).first()
    if existing: return {"status": "pending"}
    db.add(FriendRequest(sender_id=sender_id, receiver_id=target_id))
    db.commit()
    return {"status": "sent"}

@app.get("/friend/requests")
async def get_reqs(uid: int, db: Session=Depends(get_db)):
    reqs = db.query(FriendRequest).filter(FriendRequest.receiver_id == uid).all()
    requests_data = []
    for r in reqs:
        sender = db.query(User).filter(User.id == r.sender_id).first()
        requests_data.append({"id": r.id, "username": sender.username, "avatar": sender.avatar_url})
    me = db.query(User).filter(User.id == uid).first()
    friends_data = [{"id": f.id, "username": f.username, "avatar_url": f.avatar_url} for f in me.friends]
    return {"requests": requests_data, "friends": friends_data}

@app.post("/friend/handle")
async def handle_req(d: RequestActionData, db: Session=Depends(get_db)):
    req = db.query(FriendRequest).filter(FriendRequest.id == d.request_id).first()
    if not req: return {"status": "error"}
    if d.action == 'accept':
        u1 = db.query(User).filter(User.id == req.sender_id).first()
        u2 = db.query(User).filter(User.id == req.receiver_id).first()
        u1.friends.append(u2)
        u2.friends.append(u1)
        db.delete(req); db.commit()
    elif d.action == 'reject':
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
