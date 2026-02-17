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
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from datetime import datetime
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForGlory")

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
class FriendRequest(BaseModel): user_id: int; friend_id: int

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

# --- HTML FRONTEND CORRIGIDO ---
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
        body { background-color: #0b0c10; color: #e0e0e0; font-family: 'Inter', sans-serif; margin: 0; height: 100dvh; display: flex; flex-direction: column; overflow: hidden; }
        
        #app { display: flex; flex: 1; overflow: hidden; position: relative; }
        
        /* SIDEBAR */
        #sidebar { width: 80px; background: rgba(11, 12, 16, 0.95); border-right: 1px solid var(--glass-border); display: flex; flex-direction: column; align-items: center; padding: 20px 0; z-index: 10; }
        .nav-btn { width: 50px; height: 50px; border-radius: 15px; border: none; background: transparent; color: #666; font-size: 24px; margin-bottom: 20px; cursor: pointer; }
        .nav-btn.active { background: rgba(102, 252, 241, 0.15); color: var(--primary); border: 1px solid var(--glass-border); }
        .my-avatar-mini { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; border: 2px solid var(--glass-border); }

        #content-area { flex: 1; display: flex; flex-direction: column; position: relative; }
        .view { display: none; flex: 1; flex-direction: column; overflow: hidden; }
        .view.active { display: flex; }

        /* MODALS (CORRIGIDO) */
        .modal { position: fixed; inset: 0; background: #000; z-index: 200; display: flex; align-items: center; justify-content: center; }
        
        /* O ERRO ESTAVA AQUI: removido !important */
        .hidden { display: none; } 
        
        .modal-box { background: #111; padding: 30px; border-radius: 20px; border: 1px solid var(--glass-border); width: 90%; max-width: 350px; text-align: center; }
        .inp { width: 100%; padding: 12px; margin: 10px 0; background: #222; border: 1px solid #444; color: white; border-radius: 8px; text-align: center; font-size: 16px; }
        .btn { width: 100%; padding: 12px; margin-top: 10px; background: var(--primary); border: none; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 16px; }
        
        .link-text { color:#888; text-decoration:underline; cursor:pointer; font-size:14px; margin-top:15px; display:inline-block; }

        /* CHAT & FEED ESTILOS BASICOS */
        #chat-list { flex: 1; padding: 20px; overflow-y: auto; }
        .msg-bubble { background: #222; padding: 10px; border-radius: 10px; margin-bottom: 10px; }
        #chat-input-area { padding: 15px; background: #111; display: flex; gap: 10px; }
        #chat-msg { flex: 1; padding: 10px; border-radius: 20px; border: none; background: #333; color: white; }
        
        #feed-container { flex: 1; overflow-y: auto; padding: 10px; }
        .post-card { background: #111; margin-bottom: 15px; border-radius: 10px; overflow: hidden; border: 1px solid #333; }
        .post-media { width: 100%; max-height: 400px; object-fit: contain; background: black; }
        .post-header { padding: 10px; display: flex; align-items: center; gap: 10px; }
        .add-friend-btn { background: var(--primary); border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px; font-weight: bold; }

        @media (max-width: 768px) { #app { flex-direction: column-reverse; } #sidebar { width: 100%; height: 60px; flex-direction: row; justify-content: space-around; } }
    </style>
</head>
<body>

    <div id="modal-login" class="modal">
        <div class="modal-box">
            <h1 style="color:var(--primary); font-family:'Rajdhani'; font-size:2.5em; margin-bottom:20px;">FOR GLORY</h1>
            
            <div id="login-form">
                <input id="l-user" class="inp" placeholder="CODINOME">
                <input id="l-pass" class="inp" type="password" placeholder="SENHA">
                <button onclick="doLogin()" class="btn">ENTRAR</button>
                
                <div style="display:flex; justify-content:space-between; margin-top:15px;">
                    <span class="link-text" onclick="toggleAuth('register')">Criar Conta</span>
                    <span class="link-text" onclick="alert('Funcionalidade em manutenção.')">Esqueci Senha</span>
                </div>
            </div>

            <div id="register-form" class="hidden">
                <input id="r-user" class="inp" placeholder="NOVO CODINOME">
                <input id="r-email" class="inp" placeholder="EMAIL TÁTICO">
                <input id="r-pass" class="inp" type="password" placeholder="SENHA">
                <button onclick="doRegister()" class="btn">CADASTRAR</button>
                <p class="link-text" onclick="toggleAuth('login')">Voltar ao Login</p>
            </div>
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
                <div style="padding:15px; border-bottom:1px solid #333; color:var(--primary); font-family:'Rajdhani'">GERAL</div>
                <div id="chat-list"></div>
                <div id="chat-input-area">
                    <input id="chat-msg" placeholder="Mensagem...">
                    <button onclick="sendMsg()" style="background:var(--primary); border:none; width:40px; height:40px; border-radius:50%">➤</button>
                </div>
            </div>

            <div id="view-feed" class="view">
                <div id="feed-container"></div>
                <button onclick="document.getElementById('file-input').click()" style="position:fixed; bottom:80px; right:20px; width:60px; height:60px; border-radius:50%; background:var(--primary); border:none; font-size:30px; box-shadow:0 0 20px rgba(102,252,241,0.5); cursor:pointer;">+</button>
                <input type="file" id="file-input" style="display:none" onchange="uploadPost()">
            </div>

            <div id="view-profile" class="view" style="padding:20px; text-align:center;">
                <img id="p-avatar" src="" style="width:100px; height:100px; border-radius:50%; border:3px solid var(--primary);">
                <h2 id="p-name" style="color:white; margin-top:10px;">...</h2>
                <button onclick="logout()" style="background:transparent; border:1px solid red; color:red; padding:10px 20px; border-radius:20px; margin-top:20px;">SAIR</button>
            </div>
        </div>
    </div>

    <script>
        var user = null; var ws = null;

        function toggleAuth(mode) {
            if(mode === 'register') {
                document.getElementById('login-form').classList.add('hidden');
                document.getElementById('register-form').classList.remove('hidden');
            } else {
                document.getElementById('login-form').classList.remove('hidden');
                document.getElementById('register-form').classList.add('hidden');
            }
        }

        async function doLogin() {
            let u=document.getElementById('l-user').value, p=document.getElementById('l-pass').value;
            try {
                let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
                if(!r.ok) throw new Error("Erro Login");
                user=await r.json(); startApp();
            } catch(e){ alert(e.message); }
        }

        async function doRegister() {
            let u=document.getElementById('r-user').value, e=document.getElementById('r-email').value, p=document.getElementById('r-pass').value;
            try {
                let r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,email:e,password:p})});
                if(!r.ok) throw new Error("Erro Registro");
                alert("Sucesso! Faça Login."); toggleAuth('login');
            } catch(e){ alert(e.message); }
        }

        function startApp() {
            document.getElementById('modal-login').style.display = 'none';
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

        // FEED
        async function loadFeed() {
            let r=await fetch('/posts?uid='+user.id);
            let posts=await r.json();
            let html='';
            posts.forEach(p => {
                let media=p.media_type==='video'?`<video src="${p.content_url}" controls class="post-media"></video>`:`<img src="${p.content_url}" class="post-media">`;
                html+=`<div class="post-card"><div class="post-header"><span>${p.author_name}</span></div>${media}<div style="padding:10px">${p.caption}</div></div>`;
            });
            document.getElementById('feed-container').innerHTML=html;
        }

        async function uploadPost() {
            let file = document.getElementById('file-input').files[0];
            if(!file) return;
            let cap = prompt("Legenda:");
            let fd = new FormData(); fd.append('file', file); fd.append('user_id', user.id); fd.append('caption', cap || "");
            alert("Enviando... aguarde.");
            let r = await fetch('/upload/post', {method:'POST', body:fd});
            if(r.ok) { alert("Sucesso!"); loadFeed(); }
        }

        // CHAT
        function connectWS() {
            let proto = location.protocol==='https:'?'wss:':'ws:';
            ws = new WebSocket(`${proto}//${location.host}/ws/Geral/${user.id}`);
            ws.onmessage = (e) => {
                let d=JSON.parse(e.data);
                let box=document.getElementById('chat-list');
                box.innerHTML+=`<div class="msg-bubble"><b>${d.username}:</b> ${d.content}</div>`;
            }
        }
        function sendMsg() {
            let inp=document.getElementById('chat-msg');
            if(inp.value){ ws.send(inp.value); inp.value=''; }
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

@app.get("/posts")
async def get_posts(uid: int, db: Session=Depends(get_db)):
    posts = db.query(Post).order_by(Post.timestamp.desc()).all()
    return [{"content_url": p.content_url, "media_type": p.media_type, "caption": p.caption, "author_name": p.author.username} for p in posts]

@app.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int, db: Session=Depends(get_db)):
    await manager.connect(ws,ch)
    try:
        u = db.query(User).filter(User.id == uid).first()
        while True:
            txt=await ws.receive_text()
            await manager.broadcast({"username":u.username, "content":txt}, ch)
    except: manager.disconnect(ws,ch)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
