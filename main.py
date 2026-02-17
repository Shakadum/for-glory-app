import uvicorn
import json
import hashlib
import smtplib
import random
import os
import shutil
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table, or_, and_
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForGlory")

if not os.path.exists("static"):
    os.makedirs("static")

# --- BANCO DE DADOS ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./for_glory_v2.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Tabela de Amizades
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

# Cria tabelas
try:
    Base.metadata.create_all(bind=engine)
except: pass

# --- WEBSOCKET ---
class ConnectionManager:
    def __init__(self): self.active = {}
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
app = FastAPI(title="For Glory")

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

# --- FUNÇÕES ---
def get_db(): 
    db = SessionLocal()
    try: yield db
    finally: db.close()

def criptografar(s): return hashlib.sha256(s.encode()).hexdigest()

@app.on_event("startup")
def startup():
    try:
        db = SessionLocal()
        for n in ["Geral", "Memes", "Off-Topic"]: 
            if not db.query(Channel).filter(Channel.name == n).first(): db.add(Channel(name=n))
        db.commit(); db.close()
    except: pass

# --- FRONTEND (MOBILE OTIMIZADO + EMOJIS) ---
html_content = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, interactive-widget=resizes-content">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Rajdhani:wght@600;700&display=swap" rel="stylesheet">
<title>For Glory</title>
<style>
:root{--primary:#66fcf1;--dark-bg:#0b0c10;--glass-border:rgba(102,252,241,0.15)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{background-color:#0b0c10;color:#e0e0e0;font-family:'Inter',sans-serif;margin:0;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
#app{display:flex;flex:1;overflow:hidden;position:relative}
#sidebar{width:80px;background:rgba(11,12,16,0.95);border-right:1px solid var(--glass-border);display:flex;flex-direction:column;align-items:center;padding:20px 0;z-index:10}
.nav-btn{width:50px;height:50px;border-radius:15px;border:none;background:transparent;color:#666;font-size:24px;margin-bottom:20px;cursor:pointer}
.nav-btn.active{background:rgba(102,252,241,0.15);color:var(--primary);border:1px solid var(--glass-border)}
.my-avatar-mini{width:42px;height:42px;border-radius:50%;object-fit:cover;border:2px solid var(--glass-border)}
#content-area{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden}
.view{display:none;flex:1;flex-direction:column;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;height:100%;width:100%}
.view.active{display:flex}
#toast{visibility:hidden;min-width:250px;background-color:rgba(31,40,51,0.95);color:var(--primary);text-align:center;border-radius:10px;padding:16px;position:fixed;z-index:9999;left:50%;top:20px;transform:translateX(-50%);border:1px solid var(--primary);font-family:'Rajdhani';font-size:18px;box-shadow:0 0 15px rgba(102,252,241,0.2)}
#toast.show{visibility:visible;-webkit-animation:fadein 0.5s,fadeout 0.5s 2.5s;animation:fadein 0.5s,fadeout 0.5s 2.5s}
@-webkit-keyframes fadein{from{top:0;opacity:0}to{top:20px;opacity:1}}@keyframes fadein{from{top:0;opacity:0}to{top:20px;opacity:1}}
@-webkit-keyframes fadeout{from{top:20px;opacity:1}to{top:0;opacity:0}}@keyframes fadeout{from{top:20px;opacity:1}to{top:0;opacity:0}}
#chat-list{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:15px}
.msg-row{display:flex;gap:10px;max-width:85%}
.msg-row.mine{align-self:flex-end;flex-direction:row-reverse}
.msg-av{width:35px;height:35px;border-radius:50%;object-fit:cover;cursor:pointer;}
.msg-bubble{padding:10px 15px;border-radius:15px;background:#222;color:#ddd;word-break:break-word}
.msg-row.mine .msg-bubble{background:linear-gradient(135deg,#45a29e,#2f807c);color:white}
.chat-img{max-width:100%;border-radius:10px;margin-top:5px;cursor:pointer;border:1px solid rgba(255,255,255,0.2)}
#chat-input-area{background:#111;padding:10px;display:flex;gap:10px;align-items:center;flex-shrink:0;border-top:1px solid #333}
#chat-msg{flex:1;background:#222;border:1px solid #444;border-radius:20px;padding:12px;color:white;outline:none;font-size:16px}
/* EMOJI PICKER */
#emoji-picker{position:absolute;bottom:70px;left:50%;transform:translateX(-50%);width:90%;max-width:300px;background:#111;border:1px solid var(--primary);border-radius:10px;padding:10px;display:none;grid-template-columns:repeat(6,1fr);gap:5px;z-index:999;max-height:200px;overflow-y:auto;}
.emoji-btn{font-size:20px;cursor:pointer;padding:5px;text-align:center;border-radius:5px;}
.emoji-btn:hover{background:rgba(102,252,241,0.2);}
#feed-container{flex:1;overflow-y:auto;padding:0;padding-bottom:80px}
.post-card{background:rgba(11,12,16,0.6);margin-bottom:10px;border-bottom:1px solid var(--glass-border)}
.post-header{padding:10px;display:flex;align-items:center;justify-content:space-between}
.post-av{width:36px;height:36px;border-radius:50%;margin-right:10px;object-fit:cover;border:1px solid var(--primary)}
.post-media{width:100%;max-height:500px;object-fit:contain;background:black;display:block}
.post-caption{padding:10px;color:#ccc;font-size:14px}
.add-friend-btn{background:transparent;border:1px solid var(--primary);color:var(--primary);padding:5px 10px;border-radius:15px;cursor:pointer;font-size:12px}
.delete-btn{background:transparent;border:none;color:#666;font-size:16px;cursor:pointer;}
.delete-btn:hover{color:red;}
#profile-view,#public-profile-view{padding:30px;display:flex;flex-direction:column;align-items:center;text-align:center}
.profile-pic-lg{width:120px;height:120px;border-radius:50%;object-fit:cover;border:4px solid var(--primary);margin:0 auto 15px auto;cursor:pointer}
#p-name,#p-bio,#pub-name,#pub-bio{width:100%;text-align:center}
#search-box{width:90%;max-width:280px;background:rgba(255,255,255,0.1);padding:10px;border-radius:10px;margin:10px auto 20px auto;display:flex;gap:5px}
#search-input{flex:1;background:#000;border:1px solid #444;padding:8px;color:white;border-radius:5px}
#search-results{width:100%;max-width:280px;margin:0 auto 20px auto}
.search-res{padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;background:rgba(0,0,0,0.3);margin-top:5px;border-radius:5px}
.profile-btn{display:block;background:rgba(255,255,255,0.1);border:1px solid #444;color:white;padding:10px 0;width:180px;border-radius:10px;cursor:pointer;margin:10px auto;transition:0.2s}
.request-btn{background:var(--primary);color:black;border:none;font-weight:bold;width:auto;padding:10px 20px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;width:100%;max-width:400px;margin-top:20px}
.grid-item{width:100%;aspect-ratio:1/1;object-fit:cover;background:#222}
.req-row{background:rgba(100,255,100,0.1);padding:10px;margin:5px auto;width:100%;max-width:280px;border-radius:5px;display:flex;justify-content:space-between;align-items:center}
.btn-sm{padding:5px 10px;border-radius:5px;border:none;cursor:pointer;font-size:12px;margin-left:5px}
.modal{position:fixed;inset:0;background:#000;z-index:200;display:flex;align-items:center;justify-content:center}
.hidden{display:none}
.modal-box{background:#111;padding:30px;border-radius:20px;border:1px solid var(--glass-border);width:90%;max-width:350px;text-align:center}
.inp{width:100%;padding:12px;margin:10px 0;background:#222;border:1px solid #444;color:white;border-radius:8px;text-align:center;font-size:16px}
.btn{width:100%;padding:12px;margin-top:10px;background:var(--primary);border:none;font-weight:bold;border-radius:8px;cursor:pointer;font-size:16px}
#progress-container{width:100%;background:#333;height:10px;border-radius:5px;margin-top:15px;display:none;overflow:hidden}
#progress-bar{width:0%;height:100%;background:#0f0;transition:width 0.2s}
#progress-text{color:#0f0;font-size:12px;margin-top:5px;display:none}
@media(max-width:768px){#app{flex-direction:column-reverse}#sidebar{width:100%;height:60px;flex-direction:row;justify-content:space-around}}
</style>
</head>
<body>
<div id="toast">Notificação</div>
<div id="emoji-picker"></div>

<div id="modal-login" class="modal"><div class="modal-box"><h1 style="color:var(--primary);font-family:'Rajdhani'">FOR GLORY</h1><div id="login-form"><input id="l-user" class="inp" placeholder="CODINOME"><input id="l-pass" class="inp" type="password" placeholder="SENHA"><button onclick="doLogin()" class="btn">ENTRAR</button><div style="display:flex;justify-content:space-between;margin-top:15px;"><span onclick="toggleAuth('register')" style="color:#888;text-decoration:underline;cursor:pointer;">Criar Conta</span></div></div><div id="register-form" class="hidden"><input id="r-user" class="inp" placeholder="NOVO USUÁRIO"><input id="r-email" class="inp" placeholder="EMAIL"><input id="r-pass" class="inp" type="password" placeholder="SENHA"><button onclick="doRegister()" class="btn">REGISTRAR</button><p onclick="toggleAuth('login')" style="color:#888;text-decoration:underline;cursor:pointer;margin-top:10px;">Voltar</p></div></div></div>
<div id="modal-upload" class="modal hidden" style="background:rgba(0,0,0,0.9);"><div class="modal-box"><h2 style="color:white">NOVO POST</h2><input type="file" id="file-upload" class="inp" accept="image/*,video/*">
<div style="display:flex;gap:5px;align-items:center;"><input type="text" id="caption-upload" class="inp" placeholder="Legenda..."><button onclick="toggleEmoji('caption-upload')" style="background:none;border:none;font-size:20px;cursor:pointer;">😀</button></div>
<div id="progress-container"><div id="progress-bar"></div></div><div id="progress-text">Carregando... 0%</div><button onclick="submitPost()" class="btn">PUBLICAR</button><button onclick="closeUpload()" class="btn" style="background:#333;color:white">CANCELAR</button></div></div>
<div id="modal-profile" class="modal hidden" style="background:rgba(0,0,0,0.9);"><div class="modal-box"><h2 style="color:var(--primary);font-family:'Rajdhani'">EDITAR PERFIL</h2><input type="file" id="avatar-upload" class="inp" accept="image/*"><input type="text" id="bio-update" class="inp" placeholder="Bio..."><button onclick="updateProfile()" class="btn">SALVAR</button><button onclick="document.getElementById('modal-profile').classList.add('hidden')" class="btn" style="background:#333;color:white">CANCELAR</button></div></div>
<div id="app">
<div id="sidebar"><button class="nav-btn active" onclick="goView('chat')">💬</button><button class="nav-btn" onclick="goView('feed')">🎬</button><button class="nav-btn" onclick="goView('profile')"><img id="nav-avatar" src="" class="my-avatar-mini" onerror="this.src='https://via.placeholder.com/40'"></button></div>
<div id="content-area">
<div id="view-chat" class="view active"><div style="padding:15px;border-bottom:1px solid #333;color:var(--primary);font-family:'Rajdhani'">GERAL</div><div id="chat-list"></div><div id="chat-input-area"><button onclick="document.getElementById('chat-file').click()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#888;padding:10px;">📎</button><input type="file" id="chat-file" class="hidden" onchange="uploadChatImage()"><input id="chat-msg" placeholder="Mensagem..." onkeypress="if(event.key==='Enter')sendMsg()"><button onclick="toggleEmoji('chat-msg')" style="background:none;border:none;font-size:24px;cursor:pointer;margin-right:5px;">😀</button><button onclick="sendMsg()" style="background:var(--primary);border:none;width:45px;height:45px;border-radius:50%;font-weight:bold;">➤</button></div></div>
<div id="view-feed" class="view"><div id="feed-container"></div><button onclick="document.getElementById('modal-upload').classList.remove('hidden')" style="position:fixed;bottom:80px;right:20px;width:60px;height:60px;border-radius:50%;background:var(--primary);border:none;font-size:30px;box-shadow:0 0 20px rgba(102,252,241,0.5);cursor:pointer;">+</button></div>
<div id="view-profile" class="view"><img id="p-avatar" src="" class="profile-pic-lg" onclick="document.getElementById('modal-profile').classList.remove('hidden')"><h2 id="p-name" style="color:white;font-family:'Rajdhani'">...</h2><p id="p-bio" style="color:#888;margin-bottom:20px">...</p><div id="search-box"><input id="search-input" placeholder="Buscar Soldado..."><button onclick="searchUsers()" style="background:var(--primary);border:none;padding:8px;border-radius:5px;cursor:pointer;">🔍</button></div><div id="search-results"></div><button onclick="toggleRequests()" class="profile-btn">Solicitações & Amigos</button><div id="requests-list" style="display:none;width:100%;max-width:280px;margin:0 auto;"></div><div style="margin-top:20px;"><button onclick="logout()" class="profile-btn" style="border:1px solid red;color:red;background:transparent">SAIR</button></div><div id="my-posts-grid" class="grid"></div></div>
<div id="view-public-profile" class="view"><button onclick="goView('feed')" style="position:absolute;top:10px;left:10px;background:none;border:none;color:white;font-size:20px;">⬅ Voltar</button><div style="padding-top:40px;width:100%;display:flex;flex-direction:column;align-items:center;"><img id="pub-avatar" src="" class="profile-pic-lg" style="cursor:default;border-color:#888;"><h2 id="pub-name" style="color:white;font-family:'Rajdhani'">...</h2><p id="pub-bio" style="color:#888;margin-bottom:20px">...</p><div id="pub-actions"></div><div id="pub-grid" class="grid"></div></div></div>
</div></div>
<script>
var user=null;var ws=null;var syncInterval=null;var lastFeedHash="";
// EMOJI LIST
const EMOJIS = ["😂","🔥","❤️","💀","🎮","🇧🇷","🫡","🤡","😭","😎","🤬","👀","👍","👎","🔫","💣","⚔️","🛡️","🏆","💰","🍕","🍺","👋","🚫","✅","👑","💩","👻","👽","🤖"];
var currentEmojiInput = null;

function showToast(msg){var x=document.getElementById("toast");x.innerText=msg;x.className="show";setTimeout(function(){x.className=x.className.replace("show","")},3000)}
function toggleAuth(mode){document.getElementById('login-form').classList.toggle('hidden',mode==='register');document.getElementById('register-form').classList.toggle('hidden',mode!=='register')}
async function doLogin(){let u=document.getElementById('l-user').value,p=document.getElementById('l-pass').value;try{let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});if(!r.ok)throw new Error("Erro Login");user=await r.json();startApp()}catch(e){showToast("Falha no Login!")}}
async function doRegister(){let u=document.getElementById('r-user').value,e=document.getElementById('r-email').value,p=document.getElementById('r-pass').value;try{let r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,email:e,password:p})});if(!r.ok)throw new Error("Erro Registro");showToast("Sucesso! Faça Login.");toggleAuth('login')}catch(e){showToast("Erro no Registro")}}
function startApp(){document.getElementById('modal-login').classList.add('hidden');updateProfileUI();loadFeed();connectWS();loadMyPosts();
// Init Emoji
let picker = document.getElementById('emoji-picker');
EMOJIS.forEach(e => { let s = document.createElement('span'); s.className='emoji-btn'; s.innerText=e; s.onclick=()=>addEmoji(e); picker.appendChild(s); });
syncInterval=setInterval(()=>{if(document.getElementById('view-feed').classList.contains('active')){loadFeed()}},3000)}
function updateProfileUI(){let ts=new Date().getTime();document.getElementById('p-avatar').src=user.avatar_url+"?t="+ts;document.getElementById('nav-avatar').src=user.avatar_url+"?t="+ts;document.getElementById('p-name').innerText=user.username;document.getElementById('p-bio').innerText=user.bio}
function logout(){location.reload()}
function goView(v){document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));document.getElementById('view-'+v).classList.add('active');document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));if(v==='public-profile')return}
async function searchUsers(){let q=document.getElementById('search-input').value;if(!q)return;let r=await fetch('/users/search?q='+q);let res=await r.json();let box=document.getElementById('search-results');box.innerHTML='';res.forEach(u=>{if(u.id!==user.id){box.innerHTML+=`<div class="search-res" onclick="openPublicProfile(${u.id})"><div style="display:flex;align-items:center;gap:10px;cursor:pointer;"><img src="${u.avatar_url}" style="width:30px;height:30px;border-radius:50%"><span style="color:white;font-weight:bold;">${u.username}</span></div></div>`}})}
async function openPublicProfile(uid){let r=await fetch('/user/'+uid+'?viewer_id='+user.id);let data=await r.json();document.getElementById('pub-avatar').src=data.avatar_url;document.getElementById('pub-name').innerText=data.username;document.getElementById('pub-bio').innerText=data.bio;let actionBox=document.getElementById('pub-actions');actionBox.innerHTML='';if(data.friend_status==='friends'){actionBox.innerHTML='<span style="color:#0f0">✔ Amigos</span>'}else if(data.friend_status==='pending_sent'){actionBox.innerHTML='<span style="color:orange">⌛ Solicitação Enviada</span>'}else if(data.friend_status==='pending_received'){actionBox.innerHTML=`<button class="profile-btn request-btn" onclick="handleReq(${data.request_id}, 'accept')">Aceitar Solicitação</button>`}else{actionBox.innerHTML=`<button class="profile-btn request-btn" onclick="sendRequest(${uid})">Enviar Solicitação de Amizade</button>`}let grid=document.getElementById('pub-grid');grid.innerHTML='';data.posts.forEach(p=>{let content=p.media_type==='video'?`<video src="${p.content_url}" class="grid-item" controls preload="metadata" playsinline></video>`:`<img src="${p.content_url}" class="grid-item">`;grid.innerHTML+=content});goView('public-profile')}
async function sendRequest(targetId){let r=await fetch('/friend/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_id:targetId,sender_id:user.id})});if(r.ok){showToast("Solicitação enviada!");openPublicProfile(targetId)}}
async function toggleRequests(){let box=document.getElementById('requests-list');if(box.style.display==='block'){box.style.display='none';return}box.style.display='block';box.innerHTML='Carregando...';let r=await fetch('/friend/requests?uid='+user.id);let data=await r.json();box.innerHTML='<h4 style="margin:10px 0;color:#888">Solicitações Pendentes</h4>';if(data.requests.length===0)box.innerHTML+='<p style="font-size:12px">Nenhuma solicitação.</p>';data.requests.forEach(req=>{box.innerHTML+=`<div class="req-row"><span>${req.username}</span><div><button class="btn-sm" style="background:#0f0;color:black" onclick="handleReq(${req.id}, 'accept')">V</button><button class="btn-sm" style="background:red;color:white" onclick="handleReq(${req.id}, 'reject')">X</button></div></div>`});box.innerHTML+='<h4 style="margin:10px 0;color:#888;border-top:1px solid #333;paddingTop:10px;">Meus Amigos</h4>';data.friends.forEach(f=>{box.innerHTML+=`<div class="search-res" onclick="openPublicProfile(${f.id})"><img src="${f.avatar_url}" style="width:30px;height:30px;border-radius:50%"><span>${f.username}</span></div>`})}
async function handleReq(rid,action){let r=await fetch('/friend/handle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:rid,action:action})});if(r.ok){showToast("Feito!");toggleRequests()}}
function submitPost(){let file=document.getElementById('file-upload').files[0];let cap=document.getElementById('caption-upload').value;if(!file)return showToast("Selecione um arquivo!");if(file.size>100*1024*1024)return showToast("Arquivo > 100MB!");let fd=new FormData();fd.append('file',file);fd.append('user_id',user.id);fd.append('caption',cap);let xhr=new XMLHttpRequest();xhr.open('POST','/upload/post',true);xhr.upload.onprogress=function(e){if(e.lengthComputable){let percent=(e.loaded/e.total)*100;document.getElementById('progress-container').style.display='block';document.getElementById('progress-text').style.display='block';document.getElementById('progress-bar').style.width=percent+'%';document.getElementById('progress-text').innerText=`Enviando... ${Math.round(percent)}%`}};xhr.onload=function(){if(xhr.status===200){showToast("Postado!");closeUpload();lastFeedHash="";loadFeed()}else{showToast("Erro envio")}};xhr.send(fd)}
function closeUpload(){document.getElementById('modal-upload').classList.add('hidden');document.getElementById('progress-container').style.display='none';document.getElementById('progress-text').style.display='none';document.getElementById('progress-bar').style.width='0%'}
async function deletePost(pid){if(!confirm("Apagar post?"))return;let r=await fetch('/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,user_id:user.id})});if(r.ok){showToast("Apagado!");lastFeedHash="";loadFeed()}}
function connectWS(){if(ws)ws.close();let proto=location.protocol==='https:'?'wss:':'ws:';ws=new WebSocket(`${proto}//${location.host}/ws/Geral/${user.id}`);ws.onmessage=(e)=>{let d=JSON.parse(e.data);let box=document.getElementById('chat-list');let isMine=d.username===user.username;let cls=isMine?'mine':'other';let content=d.content.includes('/static/')?`<img src="${d.content}" class="chat-img" onclick="window.open(this.src)">`:d.content;let avatarUrl=`${d.avatar}?t=${new Date().getTime()}`;
box.innerHTML+=`<div class="msg-row ${cls}"><img src="${avatarUrl}" class="msg-av" onclick="openPublicProfile(${d.user_id})"><div><span class="msg-user" style="font-size:0.7em;color:var(--primary);font-weight:bold;display:block;margin-bottom:4px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username}</span><div class="msg-bubble">${content}</div></div></div>`;box.scrollTop=box.scrollHeight};ws.onclose=()=>setTimeout(connectWS,1000)}
function sendMsg(){let inp=document.getElementById('chat-msg');if(inp.value.trim()){ws.send(inp.value);inp.value=''}}
async function uploadChatImage(){let file=document.getElementById('chat-file').files[0];if(!file)return;showToast("Enviando imagem...");let fd=new FormData();fd.append('file',file);let r=await fetch('/upload/chat',{method:'POST',body:fd});if(r.ok){let data=await r.json();ws.send(data.url)}}
async function loadFeed(){try{let r=await fetch('/posts?uid='+user.id);if(!r.ok)return;let posts=await r.json();let currentHash=JSON.stringify(posts.map(p=>p.id));if(currentHash===lastFeedHash)return;lastFeedHash=currentHash;let html='';posts.forEach(p=>{let media=p.media_type==='video'?`<video src="${p.content_url}" controls class="post-media" preload="metadata" playsinline></video>`:`<img src="${p.content_url}" class="post-media">`;let actionBtn=(p.author_id===user.id)?`<button class="delete-btn" onclick="deletePost(${p.id})">🗑️</button>`:(p.is_friend?'<span style="color:#0f0;font-size:12px">✔ Amigo</span>':`<button class="add-friend-btn" onclick="openPublicProfile(${p.author_id})">ADD</button>`);html+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer;" onclick="openPublicProfile(${p.author_id})"><img src="${p.author_avatar}?t=${new Date().getTime()}" class="post-av"><span class="post-user">${p.author_name}</span></div>${actionBtn}</div>${media}<div class="post-caption"><b>${p.author_name}</b> ${p.caption}</div></div>`});document.getElementById('feed-container').innerHTML=html}catch(e){}}
async function updateProfile(){let file=document.getElementById('avatar-upload').files[0];let bio=document.getElementById('bio-update').value;let fd=new FormData();fd.append('user_id',user.id);if(file)fd.append('file',file);if(bio)fd.append('bio',bio);let r=await fetch('/profile/update',{method:'POST',body:fd});if(r.ok){let d=await r.json();user.avatar_url=d.avatar_url;user.bio=d.bio;updateProfileUI();document.querySelectorAll('.msg-row.mine .msg-av').forEach(img=>{img.src=d.avatar_url+"?t="+new Date().getTime()});document.getElementById('modal-profile').classList.add('hidden');showToast("Perfil Atualizado!")}}
// EMOJI LOGIC
function toggleEmoji(targetId){currentEmojiInput=targetId;let p=document.getElementById('emoji-picker');p.style.display=p.style.display==='grid'?'none':'grid'}
function addEmoji(e){if(currentEmojiInput){let inp=document.getElementById(currentEmojiInput);inp.value+=e;document.getElementById('emoji-picker').style.display='none'}}
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get(): return HTMLResponse(content=html_content)

# --- ENDPOINTS ---
@app.post("/register")
async def reg(d: RegisterData, db: Session=Depends(get_db)):
    if db.query(User).filter(User.username==d.username).first(): raise HTTPException(400, "User existe")
    db.add(User(username=d.username, email=d.email, password_hash=criptografar(d.password))); db.commit()
    return {"status":"ok"}

@app.post("/login")
async def log(d: LoginData, db: Session=Depends(get_db)):
    u=db.query(User).filter(User.username==d.username).first()
    if not u or u.password_hash!=criptografar(d.password): raise HTTPException(400, "Erro")
    return {"id":u.id, "username":u.username, "avatar_url":u.avatar_url, "bio":u.bio}

@app.post("/upload/post")
async def upload_post(user_id: int = Form(...), caption: str = Form(""), file: UploadFile = File(...), db: Session=Depends(get_db)):
    filename = f"post_{user_id}_{random.randint(1000,9999)}_{file.filename}"
    with open(f"static/{filename}", "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    m_type = "video" if file.content_type.startswith("video") else "image"
    db.add(Post(user_id=user_id, content_url=f"/static/{filename}", media_type=m_type, caption=caption)); db.commit()
    return {"status":"ok"}

@app.post("/post/delete")
async def delete_post_endpoint(d: DeletePostData, db: Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id == d.post_id).first()
    if not post or post.user_id != d.user_id: return {"status": "error"}
    try: os.remove(f".{post.content_url}")
    except: pass
    db.delete(post); db.commit()
    return {"status": "ok"}

@app.post("/upload/chat")
async def upload_chat(file: UploadFile = File(...)):
    filename = f"chat_{random.randint(10000,99999)}_{file.filename}"
    with open(f"static/{filename}", "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    return {"url": f"/static/{filename}"}

@app.get("/posts")
async def get_posts(uid: int, db: Session=Depends(get_db)):
    posts = db.query(Post).order_by(Post.timestamp.desc()).all()
    me = db.query(User).filter(User.id == uid).first()
    my_friends_ids = [f.id for f in me.friends] if me else []
    return [{
        "id": p.id,
        "content_url": p.content_url, 
        "media_type": p.media_type, 
        "caption": p.caption, 
        "author_name": p.author.username, 
        "author_avatar": p.author.avatar_url, 
        "author_id": p.author.id,
        "is_friend": p.author.id in my_friends_ids
    } for p in posts]

@app.get("/users/search")
async def search_users(q: str, db: Session=Depends(get_db)):
    users = db.query(User).filter(User.username.like(f"%{q}%")).limit(5).all()
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in users]

@app.post("/profile/update")
async def update_prof(user_id: int = Form(...), bio: str = Form(None), file: UploadFile = File(None), db: Session=Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if file:
        fname = f"av_{user_id}_{random.randint(1000,9999)}_{file.filename}"
        with open(f"static/{fname}", "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        u.avatar_url = f"/static/{fname}"
    if bio: u.bio = bio
    db.commit()
    return {"avatar_url": u.avatar_url, "bio": u.bio}

@app.post("/friend/request")
async def send_req(d: dict, db: Session=Depends(get_db)):
    sender_id = d.get('sender_id')
    target_id = d.get('target_id')
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
        u1, u2 = db.query(User).filter(User.id == req.sender_id).first(), db.query(User).filter(User.id == req.receiver_id).first()
        u1.friends.append(u2); u2.friends.append(u1)
        db.delete(req); db.commit()
    elif d.action == 'reject': db.delete(req); db.commit()
    return {"status": "ok"}

@app.get("/user/{target_id}")
async def get_user_profile(target_id: int, viewer_id: int, db: Session=Depends(get_db)):
    target, viewer = db.query(User).filter(User.id == target_id).first(), db.query(User).filter(User.id == viewer_id).first()
    posts = db.query(Post).filter(Post.user_id == target_id).order_by(Post.timestamp.desc()).all()
    posts_data = [{"content_url": p.content_url, "media_type": p.media_type} for p in posts]
    status = "friends" if target in viewer.friends else "none"
    if status == "none":
        sent = db.query(FriendRequest).filter(FriendRequest.sender_id == viewer_id, FriendRequest.receiver_id == target_id).first()
        received = db.query(FriendRequest).filter(FriendRequest.sender_id == target_id, FriendRequest.receiver_id == viewer_id).first()
        if sent: status = "pending_sent"
        if received: status = "pending_received"; req_id = received.id
    return {"username": target.username, "avatar_url": target.avatar_url, "bio": target.bio, "posts": posts_data, "friend_status": status, "request_id": locals().get('req_id')}

@app.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int, db: Session=Depends(get_db)):
    await manager.connect(ws,ch)
    try:
        while True:
            txt=await ws.receive_text()
            u_fresh = db.query(User).filter(User.id == uid).first()
            await manager.broadcast({"user_id": u_fresh.id, "username":u_fresh.username, "avatar":u_fresh.avatar_url, "content":txt}, ch)
    except: manager.disconnect(ws,ch)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
