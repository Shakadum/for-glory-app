import uvicorn
import json
import hashlib
import smtplib
import random
import os
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# ==============================================================================
# 🚨 PREENCHA AQUI
EMAIL_REMETENTE = "shakadum96@gmail.com"
SENHA_EMAIL_APP = "gjhjtsyapxjhyeop"
# ==============================================================================

if not os.path.exists("static"):
    os.makedirs("static")

# --- BANCO DE DADOS ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./for_glory.db"
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
    bio = Column(String, default="Soldado do For Glory")
    friends = relationship("User", secondary=friendship, primaryjoin=id==friendship.c.user_id, secondaryjoin=id==friendship.c.friend_id, backref="friended_by")

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

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    channel_name = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    sender_id = Column(Integer, ForeignKey("users.id"))
    sender = relationship("User")

Base.metadata.create_all(bind=engine)

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
class FriendRequest(BaseModel): user_id: int; friend_id: int

# --- FUNÇÕES ---
def get_db(): 
    db = SessionLocal()
    try: yield db
    finally: db.close()

def criptografar(s): return hashlib.sha256(s.encode()).hexdigest()

@app.on_event("startup")
def startup():
    db = SessionLocal()
    for n in ["Geral", "Memes", "Off-Topic"]: 
        if not db.query(Channel).filter(Channel.name == n).first(): db.add(Channel(name=n))
    db.commit(); db.close()

# --- FRONTEND (COM SISTEMA DE DIAGNÓSTICO) ---
html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Rajdhani:wght@600;700&display=swap" rel="stylesheet">
    <title>For Glory</title>
    <style>
        :root { --primary: #66fcf1; --dark-bg: #0b0c10; --glass-border: rgba(102, 252, 241, 0.15); }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background-color: #0b0c10 !important; background-image: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); color: #e0e0e0; font-family: 'Inter', sans-serif; margin: 0; height: 100dvh; display: flex; flex-direction: column; overflow: hidden; }
        
        #app { display: flex; flex: 1; overflow: hidden; position: relative; }
        
        /* SIDEBAR */
        #sidebar { width: 80px; background: rgba(11, 12, 16, 0.95); border-right: 1px solid var(--glass-border); display: flex; flex-direction: column; align-items: center; padding: 20px 0; z-index: 10; }
        .nav-btn { width: 50px; height: 50px; border-radius: 15px; border: none; background: transparent; color: #666; font-size: 24px; margin-bottom: 20px; cursor: pointer; }
        .nav-btn.active { background: rgba(102, 252, 241, 0.15); color: var(--primary); border: 1px solid var(--glass-border); box-shadow: 0 0 10px rgba(102, 252, 241, 0.2); }
        .my-avatar-mini { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; border: 2px solid var(--glass-border); }

        #content-area { flex: 1; display: flex; flex-direction: column; position: relative; }
        .view { display: none; flex: 1; flex-direction: column; overflow: hidden; }
        .view.active { display: flex; }

        /* CHAT */
        #chat-header { height: 60px; background: rgba(11,12,16,0.9); border-bottom: 1px solid var(--glass-border); display: flex; align-items: center; padding: 0 20px; font-family: 'Rajdhani'; color: var(--primary); font-size: 1.2em; }
        #chat-list { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
        .msg-row { display: flex; gap: 10px; max-width: 85%; }
        .msg-row.mine { align-self: flex-end; flex-direction: row-reverse; }
        .msg-av { width: 35px; height: 35px; border-radius: 50%; object-fit: cover; }
        .msg-bubble { padding: 10px 15px; border-radius: 15px; background: #222; color: #ddd; word-break: break-word; }
        .msg-row.mine .msg-bubble { background: linear-gradient(135deg, #45a29e, #2f807c); color: white; }
        
        #chat-input-area { background: #111; padding: 15px; display: flex; gap: 10px; align-items: center; }
        #chat-msg { flex: 1; background: #222; border: 1px solid #444; border-radius: 20px; padding: 10px; color: white; outline: none; }
        .chat-img { max-width: 100%; border-radius: 10px; margin-top: 5px; cursor: pointer; }

        /* FEED & SEARCH */
        #feed-container { flex: 1; overflow-y: auto; padding: 0; }
        .post-card { background: rgba(11, 12, 16, 0.6); margin-bottom: 10px; border-bottom: 1px solid var(--glass-border); }
        .post-header { padding: 10px; display: flex; align-items: center; justify-content: space-between; }
        .post-av { width: 32px; height: 32px; border-radius: 50%; margin-right: 10px; }
        .post-media { width: 100%; max-height: 500px; object-fit: contain; background: black; display: block; }
        .post-caption { padding: 10px; color: #ccc; font-size: 14px; }
        
        #search-area { padding: 15px; background: rgba(255,255,255,0.05); margin: 10px; border-radius: 10px; }
        #search-input { width: 70%; padding: 8px; background: #000; border: 1px solid #444; color: white; border-radius: 5px; }
        .search-res { margin-top: 10px; padding: 10px; background: rgba(0,0,0,0.5); border-radius: 5px; display: flex; justify-content: space-between; }
        .add-friend-btn { background: var(--primary); border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-weight: bold; }

        /* MODALS */
        .modal { position: fixed; inset: 0; background: #000; z-index: 200; display: flex; align-items: center; justify-content: center; }
        .hidden { display: none !important; }
        .modal-box { background: #111; padding: 30px; border-radius: 20px; border: 1px solid var(--glass-border); width: 90%; max-width: 350px; text-align: center; }
        .inp { width: 100%; padding: 12px; margin: 10px 0; background: #222; border: 1px solid #444; color: white; border-radius: 8px; text-align: center; font-size: 16px; }
        .btn { width: 100%; padding: 12px; margin-top: 10px; background: var(--primary); border: none; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 16px; }

        /* DEBUG CONSOLE */
        #debug-console { position: fixed; top: 0; left: 0; width: 100%; background: rgba(100,0,0,0.9); color: white; padding: 20px; z-index: 9999; display: none; font-family: monospace; }

        @media (max-width: 768px) { #app { flex-direction: column-reverse; } #sidebar { width: 100%; height: 60px; flex-direction: row; justify-content: space-around; } }
    </style>
</head>
<body>

    <div id="debug-console"></div>

    <div id="modal-login" class="modal">
        <div class="modal-box">
            <h1 style="color:var(--primary); font-family:'Rajdhani'">FOR GLORY</h1>
            <div id="login-form">
                <input id="l-user" class="inp" placeholder="CODINOME">
                <input id="l-pass" class="inp" type="password" placeholder="SENHA">
                <button onclick="doLogin()" class="btn">ENTRAR</button>
                <p onclick="toggleAuth('register')" style="color:#888; text-decoration:underline; cursor:pointer; margin-top:10px;">Criar Conta</p>
            </div>
            <div id="register-form" class="hidden">
                <input id="r-user" class="inp" placeholder="NOVO USUÁRIO">
                <input id="r-email" class="inp" placeholder="EMAIL">
                <input id="r-pass" class="inp" type="password" placeholder="SENHA">
                <button onclick="doRegister()" class="btn">REGISTRAR</button>
                <p onclick="toggleAuth('login')" style="color:#888; text-decoration:underline; cursor:pointer; margin-top:10px;">Voltar</p>
            </div>
        </div>
    </div>

    <div id="modal-upload" class="modal hidden" style="background:rgba(0,0,0,0.9);">
        <div class="modal-box">
            <h2 style="color:white">NOVO POST</h2>
            <input type="file" id="file-upload" class="inp">
            <input type="text" id="caption-upload" class="inp" placeholder="Legenda...">
            <div id="progress-text" style="color:#0f0; display:none">Enviando...</div>
            <button onclick="submitPost()" class="btn">PUBLICAR</button>
            <button onclick="document.getElementById('modal-upload').classList.add('hidden')" class="btn" style="background:#333; color:white">CANCELAR</button>
        </div>
    </div>

    <div id="app">
        <div id="sidebar">
            <button class="nav-btn active" onclick="goView('chat')">💬</button>
            <button class="nav-btn" onclick="goView('feed')">🎬</button>
            <button class="nav-btn" onclick="goView('profile')">👤</button>
        </div>

        <div id="content-area">
            <div id="view-chat" class="view active">
                <div id="chat-header">GERAL</div>
                <div id="chat-list"></div>
                <div id="chat-input-area">
                    <button onclick="document.getElementById('chat-file').click()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#888;">📎</button>
                    <input type="file" id="chat-file" class="hidden" onchange="uploadChatImage()">
                    <input id="chat-msg" placeholder="Mensagem...">
                    <button onclick="sendMsg()" style="background:var(--primary); border:none; width:40px; height:40px; border-radius:50%; font-weight:bold;">➤</button>
                </div>
            </div>

            <div id="view-feed" class="view">
                <div id="feed-container"></div>
                <button onclick="document.getElementById('modal-upload').classList.remove('hidden')" style="position:fixed; bottom:80px; right:20px; width:60px; height:60px; border-radius:50%; background:var(--primary); border:none; font-size:30px; box-shadow:0 0 20px rgba(102,252,241,0.5);">+</button>
            </div>

            <div id="view-profile" class="view" style="padding:20px; text-align:center; overflow-y:auto;">
                <img id="p-avatar" src="" style="width:100px; height:100px; border-radius:50%; border:3px solid var(--primary);">
                <h2 id="p-name" style="color:white; font-family:'Rajdhani'">...</h2>
                
                <div id="search-area">
                    <input id="search-input" placeholder="Buscar Amigo...">
                    <button onclick="searchUsers()" style="background:var(--primary); border:none; padding:8px; border-radius:5px; margin-left:5px;">🔍</button>
                    <div id="search-results"></div>
                </div>
                
                <button onclick="logout()" style="background:transparent; border:1px solid red; color:red; padding:10px 20px; border-radius:20px; margin-top:20px;">SAIR</button>
            </div>
        </div>
    </div>

    <script>
        // --- SISTEMA DE DIAGNÓSTICO (CAIXA PRETA) ---
        window.onerror = function(msg, url, line) {
            let box = document.getElementById('debug-console');
            box.style.display = 'block';
            box.innerHTML += "ERRO CRÍTICO: " + msg + "<br>";
            return false;
        };

        const API_HEADERS = {'ngrok-skip-browser-warning': 'true'};
        var user = null; var ws = null;

        function logError(msg) {
            let box = document.getElementById('debug-console');
            box.style.display = 'block';
            box.innerHTML += "AVISO: " + msg + "<br>";
            setTimeout(() => box.style.display='none', 5000);
        }

        // --- AUTH ---
        function toggleAuth(m) {
            document.getElementById('login-form').style.display = m==='login'?'block':'none';
            document.getElementById('register-form').style.display = m==='register'?'block':'none';
        }
        async function doLogin() {
            let u=document.getElementById('l-user').value, p=document.getElementById('l-pass').value;
            try {
                let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json', ...API_HEADERS},body:JSON.stringify({username:u,password:p})});
                if(!r.ok) throw new Error("Login Falhou");
                user=await r.json(); startApp();
            } catch(e){ logError(e.message); }
        }
        async function doRegister() {
            let u=document.getElementById('r-user').value, e=document.getElementById('r-email').value, p=document.getElementById('r-pass').value;
            try {
                let r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json', ...API_HEADERS},body:JSON.stringify({username:u,email:e,password:p})});
                if(!r.ok) throw new Error("Registro Falhou");
                alert("Sucesso! Faça Login."); toggleAuth('login');
            } catch(e){ logError(e.message); }
        }
        function startApp() {
            document.getElementById('modal-login').classList.add('hidden');
            document.getElementById('p-avatar').src = user.avatar_url;
            document.getElementById('p-name').innerText = user.username;
            loadFeed(); connectWS();
        }
        function logout() { location.reload(); }

        function goView(v) {
            document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));
            document.getElementById('view-'+v).classList.add('active');
            document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
            event.currentTarget.classList.add('active');
        }

        // --- BUSCA ---
        async function searchUsers() {
            let q = document.getElementById('search-input').value;
            if(!q) return;
            try {
                let r = await fetch('/users/search?q=' + q, {headers: API_HEADERS});
                let res = await r.json();
                let box = document.getElementById('search-results');
                box.innerHTML = '';
                if(res.length === 0) box.innerHTML = '<p style="color:#666">Ninguém.</p>';
                res.forEach(u => {
                    if(u.id !== user.id) {
                        box.innerHTML += `<div class="search-res">
                            <span style="color:white">${u.username}</span>
                            <button class="add-friend-btn" onclick="addFriend(${u.id})">ADD</button>
                        </div>`;
                    }
                });
            } catch(e) { logError("Erro Busca"); }
        }

        async function addFriend(fid) {
            try {
                let r = await fetch('/friend/add', {
                    method:'POST',
                    headers:{'Content-Type':'application/json', ...API_HEADERS},
                    body:JSON.stringify({user_id: user.id, friend_id: fid})
                });
                if(r.ok) { alert("Amigo adicionado!"); loadFeed(); }
            } catch(e) { logError("Erro Add Amigo"); }
        }

        // --- CHAT ---
        function connectWS() {
            if(ws) ws.close();
            let proto = location.protocol==='https:'?'wss:':'ws:';
            ws = new WebSocket(`${proto}//${location.host}/ws/Geral/${user.id}`);
            ws.onmessage = (e) => {
                try {
                    let d=JSON.parse(e.data);
                    let box=document.getElementById('chat-list');
                    let isMine=d.username===user.username;
                    let cls=isMine?'mine':'other';
                    let content = d.content.includes('/static/') ? `<img src="${d.content}" class="chat-img">` : d.content;
                    box.innerHTML+=`<div class="msg-row ${cls}"><img src="${d.avatar}" class="msg-av"><div><span class="msg-user">${d.username}</span><div class="msg-bubble">${content}</div></div></div>`;
                    box.scrollTop=box.scrollHeight;
                } catch(err) { console.log(err); }
            }
        }
        function sendMsg() {
            let inp=document.getElementById('chat-msg');
            if(inp.value.trim()){ ws.send(inp.value); inp.value=''; }
        }
        async function uploadChatImage() {
            let file = document.getElementById('chat-file').files[0];
            if(!file) return;
            let fd = new FormData(); fd.append('file', file);
            let r = await fetch('/upload/chat', {method:'POST', body:fd});
            if(r.ok) { let data = await r.json(); ws.send(data.url); }
        }

        // --- FEED ---
        async function loadFeed() {
            try {
                let r=await fetch('/posts?uid='+user.id, {headers: API_HEADERS}); 
                if(!r.ok) return;
                let posts=await r.json();
                let html='';
                posts.forEach(p => {
                    let media=p.media_type==='video'?`<video src="${p.content_url}" controls class="post-media"></video>`:`<img src="${p.content_url}" class="post-media">`;
                    let btn = (p.author_id !== user.id && !p.is_friend) ? `<button class="add-friend-btn" onclick="addFriend(${p.author_id})">ADD</button>` : '';
                    if(p.is_friend) btn = '<span style="color:#0f0; font-size:12px">✔ Amigo</span>';
                    
                    html+=`<div class="post-card">
                        <div class="post-header">
                            <div style="display:flex;align-items:center"><img src="${p.author_avatar}" class="post-av"><span class="post-user">${p.author_name}</span></div>
                            ${btn}
                        </div>
                        ${media}
                        <div class="post-caption"><b>${p.author_name}</b> ${p.caption}</div>
                    </div>`;
                });
                document.getElementById('feed-container').innerHTML=html;
            } catch(e) { logError("Erro Feed"); }
        }

        function submitPost() {
            let file = document.getElementById('file-upload').files[0];
            let cap = document.getElementById('caption-upload').value;
            if(!file) return alert("Selecione um arquivo!");
            let fd = new FormData(); fd.append('file', file); fd.append('user_id', user.id); fd.append('caption', cap);
            
            document.getElementById('progress-text').style.display = 'block';
            
            fetch('/upload/post', {method:'POST', body:fd}).then(r => {
                if(r.ok) { alert("Postado!"); document.getElementById('modal-upload').classList.add('hidden'); loadFeed(); }
                else { alert("Erro envio"); }
                document.getElementById('progress-text').style.display = 'none';
            });
        }
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

@app.post("/friend/add")
async def add_friend(r: FriendRequest, db: Session=Depends(get_db)):
    u = db.query(User).filter(User.id == r.user_id).first()
    f = db.query(User).filter(User.id == r.friend_id).first()
    if u and f and f not in u.friends:
        u.friends.append(f)
        f.friends.append(u)
        db.commit()
    return {"status": "ok"}

@app.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int, db: Session=Depends(get_db)):
    await manager.connect(ws,ch)
    try:
        while True:
            txt=await ws.receive_text()
            u_fresh = db.query(User).filter(User.id == uid).first()
            await manager.broadcast({"username":u_fresh.username, "avatar":u_fresh.avatar_url, "content":txt}, ch)
    except: manager.disconnect(ws,ch)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)