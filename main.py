import uvicorn
import json
import hashlib
import random
import os
import shutil
import logging
from fastapi import FastAPI, WebSocket, Request, Depends, UploadFile, File, Form
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
    avatar_url = Column(String, default="https://api.dicebear.com/7.x/notionists/svg?seed=Glory")
    cover_url = Column(String, default="https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY") # NOVA CAPA
    bio = Column(String, default="Soldado do For Glory")
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
    # --- FRONTEND ---
html_content = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, interactive-widget=resizes-content">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Rajdhani:wght@600;700&display=swap" rel="stylesheet">
<title>For Glory</title>
<style>
:root{--primary:#66fcf1;--dark-bg:#0b0c10;--glass:rgba(15,20,25,0.95);--border:rgba(102,252,241,0.2)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;scrollbar-width:thin;scrollbar-color:var(--primary) #111}
body{background-color:var(--dark-bg);color:#e0e0e0;font-family:'Inter',sans-serif;margin:0;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
#app{display:flex;flex:1;overflow:hidden;position:relative}
/* SIDEBAR */
#sidebar{width:80px;background:rgba(11,12,16,0.98);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:20px 0;z-index:20}
.nav-btn{width:50px;height:50px;border-radius:15px;border:none;background:transparent;color:#666;font-size:24px;margin-bottom:20px;cursor:pointer;transition:0.2s}
.nav-btn.active{background:rgba(102,252,241,0.1);color:var(--primary);border:1px solid var(--border);box-shadow:0 0 10px rgba(102,252,241,0.1)}
.my-avatar-mini{width:45px;height:45px;border-radius:50%;object-fit:cover;border:2px solid var(--border)}
/* CONTENT */
#content-area{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden}
.view{display:none;flex:1;flex-direction:column;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;height:100%;width:100%;padding-bottom:20px}
.view.active{display:flex}
/* CHAT */
#chat-list{flex:1;overflow-y:auto;padding:15px;display:flex;flex-direction:column;gap:12px}
.msg-row{display:flex;gap:10px;max-width:90%;animation:fadeIn 0.2s ease}
.msg-row.mine{align-self:flex-end;flex-direction:row-reverse}
.msg-row.temp{opacity: 0.6;}
.msg-av{width:32px;height:32px;border-radius:50%;object-fit:cover;cursor:pointer;border:1px solid #333}
.msg-bubble{padding:10px 14px;border-radius:16px;background:#1f1f1f;color:#ddd;word-break:break-word;font-size:15px;line-height:1.4}
.msg-row.mine .msg-bubble{background:linear-gradient(135deg,#2c7a7b,#234e52);color:white;border:1px solid rgba(102,252,241,0.3)}
.chat-img{max-width:100%;border-radius:10px;margin-top:5px;cursor:pointer;border:1px solid rgba(255,255,255,0.1)}
#chat-input-area{background:#111;padding:10px;display:flex;gap:8px;align-items:center;flex-shrink:0;border-top:1px solid #333}
#chat-msg{flex:1;background:#222;border:1px solid #444;border-radius:20px;padding:12px;color:white;outline:none;font-size:16px}
/* FEED */
#feed-container{flex:1;overflow-y:auto;padding:0;padding-bottom:90px}
.post-card{background:rgba(20,20,25,0.6);margin-bottom:8px;border-bottom:1px solid var(--border)}
.post-header{padding:10px 15px;display:flex;align-items:center;justify-content:space-between}
.post-av{width:40px;height:40px;border-radius:50%;margin-right:10px;object-fit:cover;border:1px solid var(--primary)}
.post-media{width:100%;max-height:500px;object-fit:contain;background:black;display:block}
.post-caption{padding:12px;color:#ccc;font-size:14px}
/* PROFILE (HEADER CAPA + FOTO) */
#profile-view,#public-profile-view{padding:0;display:flex;flex-direction:column;align-items:center;text-align:center}
.profile-header-container { position: relative; width: 100%; height: 200px; margin-bottom: 50px; }
.profile-cover { width: 100%; height: 100%; object-fit: cover; opacity: 0.8; mask-image: linear-gradient(to bottom, black 50%, transparent 100%); -webkit-mask-image: linear-gradient(to bottom, black 50%, transparent 100%); }
.profile-pic-lg { position: absolute; bottom: -40px; left: 50%; transform: translateX(-50%); width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 4px solid var(--dark-bg); box-shadow: 0 0 20px var(--primary); cursor: pointer; }

#search-box{width:95%;max-width:320px;background:rgba(255,255,255,0.05);padding:8px;border-radius:12px;margin:15px auto;display:flex;gap:5px;border:1px solid #333}
#search-input{flex:1;background:transparent;border:none;color:white;font-size:16px;outline:none}
.search-res{padding:12px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;background:rgba(0,0,0,0.4);margin-top:5px;border-radius:8px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;width:100%;max-width:500px;margin-top:20px}
.grid-item{width:100%;aspect-ratio:1/1;object-fit:cover;background:#1a1a1a;cursor:pointer}
/* UTILS */
.btn-float{position:fixed;bottom:80px;right:20px;width:55px;height:55px;border-radius:50%;background:var(--primary);border:none;font-size:28px;box-shadow:0 4px 15px rgba(102,252,241,0.4);cursor:pointer;z-index:50;display:flex;align-items:center;justify-content:center;color:#000}
.btn-std{background:rgba(255,255,255,0.1);border:1px solid #444;color:white;padding:10px 20px;border-radius:8px;cursor:pointer;font-size:14px;flex:1;text-align:center;}
.btn-std:hover{background:rgba(102,252,241,0.1);border-color:var(--primary)}
/* MODAL */
.modal{position:fixed;inset:0;background:#0b0c10;z-index:9000;display:flex;align-items:center;justify-content:center}
.modal.transparent-bg{background:rgba(0,0,0,0.85);backdrop-filter:blur(5px);}
.hidden{display:none !important}
.modal-box{background:#111;padding:25px;border-radius:20px;border:1px solid var(--border);width:90%;max-width:350px;text-align:center;box-shadow:0 0 30px rgba(0,0,0,0.8)}
.inp{width:100%;padding:12px;margin:8px 0;background:#222;border:1px solid #444;color:white;border-radius:8px;text-align:center;font-size:16px}
.btn-main{width:100%;padding:12px;margin-top:10px;background:var(--primary);border:none;font-weight:700;border-radius:8px;cursor:pointer;font-size:16px;color:#000}
#toast{visibility:hidden;min-width:200px;background:var(--glass);color:var(--primary);text-align:center;border-radius:50px;padding:12px 24px;position:fixed;z-index:9999;left:50%;top:30px;transform:translateX(-50%);border:1px solid var(--primary);font-weight:600}
#toast.show{visibility:visible;animation:fadeInOut 3s}
/* EMOJI PICKER Z-INDEX */
#emoji-picker{position:absolute;bottom:80px;right:10px;width:90%;max-width:320px;background:var(--glass);border:1px solid var(--border);border-radius:15px;display:none;flex-direction:column;z-index:10001;box-shadow:0 0 25px rgba(0,0,0,0.8)}
.emoji-header{padding:10px 15px;display:flex;justify-content:space-between;border-bottom:1px solid #333;background:rgba(102,252,241,0.05)}
.emoji-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;padding:10px;max-height:220px;overflow-y:auto}
.emoji-btn{font-size:22px;padding:8px;cursor:pointer;border-radius:5px;text-align:center}
.emoji-btn:active{background:var(--primary)}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeInOut{0%{top:0;opacity:0}20%{top:30px;opacity:1}80%{top:30px;opacity:1}100%{top:0;opacity:0}}
@media(max-width:768px){#app{flex-direction:column-reverse}#sidebar{width:100%;height:60px;flex-direction:row;justify-content:space-around;padding:0;border-top:1px solid var(--border);border-right:none}.btn-float{bottom:70px}}
</style>
</head>
<body>
<div id="toast">Notificação</div>

<div id="emoji-picker">
    <div class="emoji-header">
        <span style="color:var(--primary);font-weight:bold;font-family:'Rajdhani'">EMOJIS</span>
        <span onclick="toggleEmoji()" style="color:#ff5555;cursor:pointer;font-weight:bold">✕</span>
    </div>
    <div id="emoji-grid" class="emoji-grid"></div>
</div>

<div id="modal-login" class="modal"><div class="modal-box"><h1 style="color:var(--primary);font-family:'Rajdhani';font-size:32px;margin:0 0 20px 0">FOR GLORY</h1><div id="login-form"><input id="l-user" class="inp" placeholder="CODINOME"><input id="l-pass" class="inp" type="password" placeholder="SENHA"><button onclick="doLogin()" class="btn-main">ENTRAR</button><div style="margin-top:15px;font-size:14px;color:#888"><span onclick="toggleAuth('register')" style="text-decoration:underline;cursor:pointer">Criar Conta</span></div></div><div id="register-form" class="hidden"><input id="r-user" class="inp" placeholder="NOVO USUÁRIO"><input id="r-email" class="inp" placeholder="EMAIL"><input id="r-pass" class="inp" type="password" placeholder="SENHA"><button onclick="doRegister()" class="btn-main">REGISTRAR</button><p onclick="toggleAuth('login')" style="color:#888;text-decoration:underline;cursor:pointer;margin-top:15px">Voltar</p></div></div></div>

<div id="modal-upload" class="modal hidden transparent-bg"><div class="modal-box"><h2 style="color:white">NOVO POST</h2><input type="file" id="file-upload" class="inp" accept="image/*,video/*"><div style="display:flex;gap:5px;align-items:center;margin-bottom:10px"><input type="text" id="caption-upload" class="inp" placeholder="Legenda..." style="margin:0"><button onclick="openEmoji('caption-upload')" style="background:none;border:none;font-size:22px;cursor:pointer">😀</button></div><div id="progress-container" style="display:none;background:#333;height:6px;border-radius:3px;overflow:hidden"><div id="progress-bar" style="width:0%;height:100%;background:var(--primary);transition:width 0.3s"></div></div><div id="progress-text" style="font-size:12px;color:var(--primary);margin-top:5px;display:none">0%</div><button onclick="submitPost()" class="btn-main">PUBLICAR</button><button onclick="closeUpload()" class="btn-std" style="width:100%;margin:10px 0 0 0">CANCELAR</button></div></div>

<div id="modal-profile" class="modal hidden transparent-bg"><div class="modal-box"><h2 style="color:var(--primary)">EDITAR</h2>
<label style="color:#aaa;font-size:12px;display:block;margin-top:10px">Foto de Perfil</label>
<input type="file" id="avatar-upload" class="inp" accept="image/*">
<label style="color:#aaa;font-size:12px;display:block;margin-top:10px">Capa de Fundo (Banner)</label>
<input type="file" id="cover-upload" class="inp" accept="image/*">
<input type="text" id="bio-update" class="inp" placeholder="Bio...">
<button onclick="updateProfile()" class="btn-main">SALVAR</button><button onclick="document.getElementById('modal-profile').classList.add('hidden')" class="btn-std" style="width:100%;margin:10px 0 0 0">CANCELAR</button></div></div>

<div id="app">
    <div id="sidebar"><button class="nav-btn active" onclick="goView('chat')">💬</button><button class="nav-btn" onclick="goView('feed')">🎬</button><button class="nav-btn" onclick="goView('profile')"><img id="nav-avatar" src="" class="my-avatar-mini"></button></div>
    <div id="content-area">
        <div id="view-chat" class="view active"><div style="padding:15px;border-bottom:1px solid #222;color:var(--primary);font-family:'Rajdhani';font-weight:bold;letter-spacing:1px;text-align:center">CANAL GERAL</div><div id="chat-list"></div><div id="chat-input-area"><button onclick="document.getElementById('chat-file').click()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#888;padding:5px">📎</button><input type="file" id="chat-file" class="hidden" onchange="uploadChatImage()"><input id="chat-msg" placeholder="Mensagem..." onkeypress="if(event.key==='Enter')sendMsg()"><button onclick="openEmoji('chat-msg')" style="background:none;border:none;font-size:22px;cursor:pointer;margin-right:5px">😀</button><button onclick="sendMsg()" style="background:var(--primary);border:none;width:40px;height:40px;border-radius:50%;font-weight:bold;display:flex;align-items:center;justify-content:center">➤</button></div></div>
        <div id="view-feed" class="view"><div id="feed-container"></div><button class="btn-float" onclick="document.getElementById('modal-upload').classList.remove('hidden')">+</button></div>
        
        <div id="view-profile" class="view">
            <div class="profile-header-container">
                <img id="p-cover" src="" class="profile-cover">
                <img id="p-avatar" src="" class="profile-pic-lg" onclick="document.getElementById('modal-profile').classList.remove('hidden')">
            </div>
            <div style="display:flex;flex-direction:column;align-items:center;width:100%;text-align:center;margin-top:10px;">
                <h2 id="p-name" style="color:white;font-family:'Rajdhani';width:100%;text-align:center;margin:5px 0;">...</h2>
                <p id="p-bio" style="color:#888;width:100%;text-align:center;margin:0 0 20px 0;font-style:italic">...</p>
            </div>
            <div id="search-box"><input id="search-input" placeholder="Buscar Soldado..."><button onclick="searchUsers()" style="background:none;border:none;color:var(--primary);font-size:18px;cursor:pointer">🔍</button></div>
            <div id="search-results"></div>
            <div style="display:flex;justify-content:center;gap:10px;width:95%;max-width:320px;margin:10px auto;">
                <button onclick="toggleRequests('requests')" class="btn-std">📩 Solicitações</button>
                <button onclick="toggleRequests('friends')" class="btn-std">👥 Amigos</button>
            </div>
            <div id="requests-list" style="display:none;width:95%;max-width:320px;margin:10px auto"></div>
            <div style="display:flex;justify-content:center;width:95%;max-width:320px;margin:30px auto 0 auto;">
                <button onclick="logout()" class="btn-std" style="border-color:#ff5555;color:#ff5555;width:100%;text-align:center;">SAIR DO SISTEMA</button>
            </div>
        </div>

        <div id="view-public-profile" class="view"><button onclick="goView('feed')" style="position:absolute;top:15px;left:15px;z-index:10;background:rgba(0,0,0,0.5);border:1px solid #444;color:white;border-radius:8px;padding:5px 10px;cursor:pointer">⬅ Voltar</button>
            <div class="profile-header-container">
                <img id="pub-cover" src="" class="profile-cover">
                <img id="pub-avatar" src="" class="profile-pic-lg" style="cursor:default;border-color:#888">
            </div>
            <div style="display:flex;flex-direction:column;align-items:center;text-align:center;margin-top:10px">
                <h2 id="pub-name" style="color:white;font-family:'Rajdhani'">...</h2><p id="pub-bio" style="color:#888;margin-bottom:20px">...</p>
                <div id="pub-actions"></div>
                <div id="pub-grid" class="grid"></div>
            </div>
        </div>
    </div>
</div>
<script>
var user=null,ws=null,syncInterval=null,lastFeedHash="",currentEmojiTarget=null;
const EMOJIS = ["😂","🔥","❤️","💀","🎮","🇧🇷","🫡","🤡","😭","😎","🤬","👀","👍","👎","🔫","💣","⚔️","🛡️","🏆","💰","🍕","🍺","👋","🚫","✅","👑","💩","👻","👽","🤖","🤫","🥶","🤯","🥳","🤢","🤕","🤑","🤠","😈","👿","👹","👺","👾"];

window.onload=()=>{
    let g=document.getElementById('emoji-grid');
    EMOJIS.forEach(e=>{let s=document.createElement('div');s.className='emoji-btn';s.innerText=e;s.onclick=()=>addEmoji(e);g.appendChild(s)});
};

function showToast(m){let x=document.getElementById("toast");x.innerText=m;x.className="show";setTimeout(()=>x.className=x.className.replace("show",""),3000)}
function toggleAuth(m){document.getElementById('login-form').classList.toggle('hidden',m==='register');document.getElementById('register-form').classList.toggle('hidden',m!=='register')}
async function doLogin(){try{let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('l-user').value,password:document.getElementById('l-pass').value})});if(!r.ok)throw 1;user=await r.json();startApp()}catch(e){showToast("Erro no Login")}}
async function doRegister(){try{let r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('r-user').value,email:document.getElementById('r-email').value,password:document.getElementById('r-pass').value})});if(!r.ok)throw 1;showToast("Sucesso!");toggleAuth('login')}catch(e){showToast("Erro Registro")}}
function startApp(){document.getElementById('modal-login').classList.add('hidden');updateUI();loadFeed();connectWS();syncInterval=setInterval(()=>{if(document.getElementById('view-feed').classList.contains('active'))loadFeed()},3000)}

// --- UI UPDATE COM CAPA ---
function updateUI(){
    let t = new Date().getTime();
    let url = user.avatar_url + "?t=" + t;
    let cover = (user.cover_url || "https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY") + "?t=" + t;
    
    document.querySelectorAll('.my-avatar-mini, #p-avatar, .msg-row.mine .msg-av').forEach(img => { img.src = url; });
    document.getElementById('p-cover').src = cover;
    document.getElementById('p-name').innerText=user.username;
    document.getElementById('p-bio').innerText=user.bio;
}

function logout(){location.reload()}
function goView(v){document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));document.getElementById('view-'+v).classList.add('active');document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));if(v!=='public-profile')event.currentTarget.classList.add('active')}
async function searchUsers(){let q=document.getElementById('search-input').value;if(!q)return;let r=await fetch('/users/search?q='+q);let res=await r.json();let b=document.getElementById('search-results');b.innerHTML='';res.forEach(u=>{if(u.id!==user.id)b.innerHTML+=`<div class="search-res" onclick="openPublicProfile(${u.id})"><div style="display:flex;align-items:center;gap:10px"><img src="${u.avatar_url}" style="width:30px;height:30px;border-radius:50%"><b>${u.username}</b></div></div>`})}

// --- PUBLIC PROFILE COM CAPA ---
async function openPublicProfile(uid){
    let r=await fetch('/user/'+uid+'?viewer_id='+user.id);
    let d=await r.json();
    let t = new Date().getTime();
    document.getElementById('pub-avatar').src=d.avatar_url+"?t="+t;
    document.getElementById('pub-cover').src=(d.cover_url || "https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY") + "?t=" + t;
    document.getElementById('pub-name').innerText=d.username;
    document.getElementById('pub-bio').innerText=d.bio;
    let ab=document.getElementById('pub-actions');ab.innerHTML='';
    if(d.friend_status==='friends')ab.innerHTML='<span style="color:#0f0">✔ Amigos</span>';
    else if(d.friend_status==='pending_sent')ab.innerHTML='<span style="color:orange">Solicitado</span>';
    else if(d.friend_status==='pending_received')ab.innerHTML=`<button class="btn-std" onclick="handleReq(${d.request_id},'accept')">Aceitar</button>`;
    else ab.innerHTML=`<button class="btn-std" onclick="sendRequest(${uid})" style="border-color:var(--primary)">Adicionar</button>`;
    let g=document.getElementById('pub-grid');g.innerHTML='';d.posts.forEach(p=>{g.innerHTML+=p.media_type==='video'?`<video src="${p.content_url}" class="grid-item" controls preload="none"></video>`:`<img src="${p.content_url}" class="grid-item" loading="lazy">`});
    goView('public-profile')
}

async function sendRequest(tid){if((await fetch('/friend/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_id:tid,sender_id:user.id})})).ok){showToast("Enviado!");openPublicProfile(tid)}}
async function toggleRequests(type){
    let b=document.getElementById('requests-list');
    if(b.style.display==='block' && b.dataset.type === type){b.style.display='none';return}
    b.style.display='block';b.dataset.type = type;b.innerHTML='Carregando...';
    let d=await (await fetch('/friend/requests?uid='+user.id)).json();b.innerHTML='';
    if(type === 'requests') {
        b.innerHTML = '<h4 style="color:#888;margin:5px 0">Recebidas</h4>';
        if(!d.requests.length) b.innerHTML+='<small>Nenhuma.</small>';
        d.requests.forEach(r=>{b.innerHTML+=`<div class="search-res" style="background:rgba(255,255,255,0.05)"><span>${r.username}</span><div><button onclick="handleReq(${r.id},'accept')" style="color:#0f0;background:none;border:none;cursor:pointer">✔</button><button onclick="handleReq(${r.id},'reject')" style="color:red;background:none;border:none;cursor:pointer">✖</button></div></div>`});
    } else {
        b.innerHTML = '<h4 style="color:#888;margin:5px 0">Meus Amigos</h4>';
        if(!d.friends.length) b.innerHTML+='<small>Nenhum.</small>';
        d.friends.forEach(f=>{b.innerHTML+=`<div class="search-res" onclick="openPublicProfile(${f.id})"><img src="${f.avatar_url}" style="width:25px;height:25px;border-radius:50%"> ${f.username}</div>`});
    }
}
async function handleReq(rid,act){if((await fetch('/friend/handle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:rid,action:act})})).ok){showToast("Feito!");toggleRequests('requests')}}

function submitPost(){
    let f=document.getElementById('file-upload').files[0];
    let cap=document.getElementById('caption-upload').value;
    if(!f)return showToast("Arquivo?");
    let blob = URL.createObjectURL(f);
    let m = f.type.startsWith('video') ? `<video src="${blob}" class="post-media" controls></video>` : `<img src="${blob}" class="post-media">`;
    let html = `<div class="post-card" style="opacity:0.7"><div class="post-header"><div style="display:flex;align-items:center"><img src="${user.avatar_url}" class="post-av"><b>${user.username}</b></div><span>Enviando...</span></div>${m}<div class="post-caption"><b>${user.username}</b> ${cap}</div></div>`;
    document.getElementById('feed-container').insertAdjacentHTML('afterbegin', html);
    closeUpload();
    let fd=new FormData();fd.append('file',f);fd.append('user_id',user.id);fd.append('caption',cap);
    let x=new XMLHttpRequest();x.open('POST','/upload/post',true);
    x.onload=()=>{if(x.status===200){showToast("Enviado!");lastFeedHash="";loadFeed()}else showToast("Erro")};x.send(fd);
}

function sendMsg(){
    let i=document.getElementById('chat-msg');
    let txt = i.value.trim();
    if(!txt) return;
    let b=document.getElementById('chat-list');
    let html = `<div class="msg-row mine temp"><img src="${user.avatar_url}" class="msg-av"><div><div class="msg-bubble">${txt}</div></div></div>`;
    b.insertAdjacentHTML('beforeend', html);
    b.scrollTop=b.scrollHeight;
    ws.send(txt);
    i.value='';toggleEmoji(true);
}

async function uploadChatImage(){
    let f=document.getElementById('chat-file').files[0];
    if(!f)return;
    let blob = URL.createObjectURL(f);
    let b=document.getElementById('chat-list');
    let html = `<div class="msg-row mine temp"><img src="${user.avatar_url}" class="msg-av"><div><div class="msg-bubble"><img src="${blob}" class="chat-img"></div></div></div>`;
    b.insertAdjacentHTML('beforeend', html);
    b.scrollTop=b.scrollHeight;
    let fd=new FormData();fd.append('file',f);let r=await fetch('/upload/chat',{method:'POST',body:fd});
    if(r.ok){let d=await r.json();ws.send(d.url)}
}

function connectWS(){
    if(ws)ws.close();
    let p=location.protocol==='https:'?'wss:':'ws:';
    ws=new WebSocket(`${p}//${location.host}/ws/Geral/${user.id}`);
    ws.onmessage=e=>{
        let d=JSON.parse(e.data);
        if(d.user_id === user.id) {
            let temps = document.querySelectorAll('.msg-row.mine.temp');
            if(temps.length > 0) temps[temps.length-1].remove(); 
        }
        let b=document.getElementById('chat-list');
        let m=d.user_id===user.id;
        let c=d.content.includes('/static/')?`<img src="${d.content}" class="chat-img" onclick="window.open(this.src)" loading="lazy">`:d.content;
        let a=`${d.avatar}?t=${new Date().getTime()}`;
        let html = `<div class="msg-row ${m?'mine':''}"><img src="${a}" class="msg-av" onclick="openPublicProfile(${d.user_id})"><div><div style="font-size:11px;color:var(--primary);margin-bottom:2px;cursor:pointer" onclick="openPublicProfile(${d.user_id})">${d.username}</div><div class="msg-bubble">${c}</div></div></div>`;
        b.insertAdjacentHTML('beforeend', html);
        b.scrollTop=b.scrollHeight;
    };
    ws.onclose=()=>setTimeout(connectWS,2000);
}

function closeUpload(){
    document.getElementById('modal-upload').classList.add('hidden');
    document.getElementById('progress-container').style.display='none';
    document.getElementById('progress-bar').style.width='0%';
    document.getElementById('file-upload').value = "";
    toggleEmoji(true);
}
async function deletePost(pid){if(!confirm("Apagar?"))return;if((await fetch('/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,user_id:user.id})})).ok){showToast("Apagado!");lastFeedHash="";loadFeed()}}
async function loadFeed(){try{let r=await fetch('/posts?uid='+user.id+'&limit=50');if(!r.ok)return;let p=await r.json();let h=JSON.stringify(p.map(x=>x.id));if(h===lastFeedHash)return;lastFeedHash=h;let ht='';p.forEach(x=>{let m=x.media_type==='video'?`<video src="${x.content_url}" class="post-media" controls preload="none" playsinline poster="${x.content_url}#t=0.5"></video>`:`<img src="${x.content_url}" class="post-media" loading="lazy">`;let btn=x.author_id===user.id?`<span onclick="deletePost(${x.id})" style="cursor:pointer;font-size:18px">🗑️</span>`:x.is_friend?'<span style="color:#0f0;font-size:12px">✔</span>':`<button onclick="openPublicProfile(${x.author_id})" class="btn-std" style="padding:2px 8px;font-size:11px">ADD</button>`;ht+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer" onclick="openPublicProfile(${x.author_id})"><img src="${x.author_avatar}" class="post-av"><b>${x.author_name}</b></div>${btn}</div>${m}<div class="post-caption"><b>${x.author_name}</b> ${x.caption}</div></div>`});document.getElementById('feed-container').innerHTML=ht}catch(e){}}

// --- ATUALIZAR PERFIL COM CAPA ---
async function updateProfile(){
    let f=document.getElementById('avatar-upload').files[0];
    let c=document.getElementById('cover-upload').files[0];
    let b=document.getElementById('bio-update').value;
    let fd=new FormData();fd.append('user_id',user.id);
    if(f)fd.append('file',f);
    if(c)fd.append('cover',c); // Envia capa
    if(b)fd.append('bio',b);
    let r=await fetch('/profile/update',{method:'POST',body:fd});
    if(r.ok){
        let d=await r.json();
        user.avatar_url=d.avatar_url;
        user.cover_url=d.cover_url;
        user.bio=d.bio;
        updateUI();
        document.getElementById('modal-profile').classList.add('hidden');
        showToast("Atualizado!");
    }
}
function openEmoji(id){currentEmojiTarget=id;document.getElementById('emoji-picker').style.display='flex'}
function toggleEmoji(forceClose){let e=document.getElementById('emoji-picker');if(forceClose===true){e.style.display='none'}else{e.style.display=e.style.display==='flex'?'none':'flex'}}
function addEmoji(e){if(currentEmojiTarget){let i=document.getElementById(currentEmojiTarget);i.value+=e}}
</script>
</body>
</html>
@app.get("/", response_class=HTMLResponse)
async def get(): return HTMLResponse(content=html_content)

# --- API ---
@app.post("/register")
async def reg(d: RegisterData, db: Session=Depends(get_db)):
    if db.query(User).filter(User.username==d.username).first():
        raise HTTPException(400, "User existe")
    db.add(User(username=d.username, email=d.email, password_hash=criptografar(d.password)))
    db.commit()
    return {"status":"ok"}

@app.post("/login")
async def log(d: LoginData, db: Session=Depends(get_db)):
    u = db.query(User).filter(User.username==d.username).first()
    if not u or u.password_hash != criptografar(d.password):
        raise HTTPException(400, "Erro")
    return {"id":u.id, "username":u.username, "avatar_url":u.avatar_url, "cover_url":u.cover_url, "bio":u.bio}

@app.post("/upload/post")
async def upload_post(user_id: int = Form(...), caption: str = Form(""), file: UploadFile = File(...), db: Session=Depends(get_db)):
    filename = f"p_{user_id}_{random.randint(1000,9999)}_{file.filename}"
    with open(f"static/{filename}", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    m_type = "video" if file.content_type.startswith("video") else "image"
    db.add(Post(user_id=user_id, content_url=f"/static/{filename}", media_type=m_type, caption=caption))
    db.commit()
    return {"status":"ok"}

@app.post("/post/delete")
async def delete_post_endpoint(d: DeletePostData, db: Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id == d.post_id).first()
    if not post or post.user_id != d.user_id:
        return {"status": "error"}
    try:
        os.remove(f".{post.content_url}")
    except:
        pass
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
    return [{"id": p.id, "content_url": p.content_url, "media_type": p.media_type, "caption": p.caption, "author_name": p.author.username, "author_avatar": p.author.avatar_url, "author_id": p.author.id, "is_friend": p.author.id in my_friends_ids} for p in posts]

@app.get("/users/search")
async def search_users(q: str, db: Session=Depends(get_db)):
    users = db.query(User).filter(User.username.like(f"%{q}%")).limit(10).all()
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in users]

@app.post("/profile/update")
async def update_prof(user_id: int = Form(...), bio: str = Form(None), file: UploadFile = File(None), cover: UploadFile = File(None), db: Session=Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if file:
        fname = f"a_{user_id}_{random.randint(1000,9999)}_{file.filename}"
        with open(f"static/{fname}", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        u.avatar_url = f"/static/{fname}"
    if cover:
        cname = f"cv_{user_id}_{random.randint(1000,9999)}_{cover.filename}"
        with open(f"static/{cname}", "wb") as buffer:
            shutil.copyfileobj(cover.file, buffer)
        u.cover_url = f"/static/{cname}"
    if bio:
        u.bio = bio
    db.commit()
    return {"avatar_url": u.avatar_url, "cover_url": u.cover_url, "bio": u.bio}

@app.post("/friend/request")
async def send_req(d: dict, db: Session=Depends(get_db)):
    sender_id = d.get('sender_id')
    target_id = d.get('target_id')
    me = db.query(User).filter(User.id == sender_id).first()
    target = db.query(User).filter(User.id == target_id).first()
    if target in me.friends:
        return {"status": "already_friends"}
    existing = db.query(FriendRequest).filter(or_(and_(FriendRequest.sender_id==sender_id, FriendRequest.receiver_id==target_id),and_(FriendRequest.sender_id==target_id, FriendRequest.receiver_id==sender_id))).first()
    if existing:
        return {"status": "pending"}
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
    if not req:
        return {"status": "error"}
    if d.action == 'accept':
        u1 = db.query(User).filter(User.id == req.sender_id).first()
        u2 = db.query(User).filter(User.id == req.receiver_id).first()
        u1.friends.append(u2)
        u2.friends.append(u1)
        db.delete(req)
        db.commit()
    elif d.action == 'reject':
        db.delete(req)
        db.commit()
    return {"status": "ok"}

@app.get("/user/{target_id}")
async def get_user_profile(target_id: int, viewer_id: int, db: Session=Depends(get_db)):
    target = db.query(User).filter(User.id == target_id).first()
    viewer = db.query(User).filter(User.id == viewer_id).first()
    posts = db.query(Post).filter(Post.user_id == target_id).order_by(Post.timestamp.desc()).all()
    posts_data = [{"content_url": p.content_url, "media_type": p.media_type} for p in posts]
    status = "friends" if target in viewer.friends else "none"
    if status == "none":
        sent = db.query(FriendRequest).filter(FriendRequest.sender_id == viewer_id, FriendRequest.receiver_id == target_id).first()
        received = db.query(FriendRequest).filter(FriendRequest.sender_id == target_id, FriendRequest.receiver_id == viewer_id).first()
        if sent:
            status = "pending_sent"
        if received:
            status = "pending_received"
            req_id = received.id
    return {"username": target.username, "avatar_url": target.avatar_url, "cover_url": target.cover_url, "bio": target.bio, "posts": posts_data, "friend_status": status, "request_id": locals().get('req_id')}

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
    uvicorn.run(app, host="0.0.0.0", port=10000)
