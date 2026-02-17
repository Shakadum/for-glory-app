import uvicorn
import json
import hashlib
import random
import os
import shutil
import logging
from fastapi import FastAPI, WebSocket, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from datetime import datetime
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# --- LOGGING PARA RENDER (Debug) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForGlory")

# --- CONFIGURAÇÃO DE DIRETÓRIOS ---
if not os.path.exists("static"):
    os.makedirs("static")

# --- BANCO DE DADOS (AJUSTADO PARA NUVEM) ---
# Usamos /tmp/ no Render para evitar erros de permissão em alguns casos,
# mas saiba que no plano grátis o banco reseta se o servidor desligar.
SQLALCHEMY_DATABASE_URL = "sqlite:///./for_glory.db" 

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- TABELAS ---
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

# Tenta criar as tabelas e avisa se falhar
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Banco de dados iniciado com sucesso.")
except Exception as e:
    logger.error(f"Erro fatal ao criar banco: {e}")

# --- WEBSOCKET MANAGER ---
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

# Permite acesso de qualquer lugar (Vital para o Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# --- MODELOS DE DADOS ---
class LoginData(BaseModel): username: str; password: str
class RegisterData(BaseModel): username: str; email: str; password: str
class FriendRequest(BaseModel): user_id: int; friend_id: int

# --- FUNÇÕES AUXILIARES ---
def get_db(): 
    db = SessionLocal()
    try: yield db
    finally: db.close()

def criptografar(s): return hashlib.sha256(s.encode()).hexdigest()

@app.on_event("startup")
def startup():
    # Garante canais padrão
    try:
        db = SessionLocal()
        for n in ["Geral", "Memes", "Off-Topic"]: 
            if not db.query(Channel).filter(Channel.name == n).first(): db.add(Channel(name=n))
        db.commit(); db.close()
    except: pass

# --- HTML (FRONTEND) ---
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

        /* MODALS */
        .modal { position: fixed; inset: 0; background: #000; z-index: 200; display: flex; align-items: center; justify-content: center; }
        .hidden { display: none !important; }
        .modal-box { background: #111; padding: 30px; border-radius: 20px; border: 1px solid var(--glass-border); width: 90%; max-width: 350px; text-align: center; }
        .inp { width: 100%; padding: 12px; margin: 10px 0; background: #222; border: 1px solid #444; color: white; border-radius: 8px; text-align: center; font-size: 16px; }
        .btn { width: 100%; padding: 12px; margin-top: 10px; background: var(--primary); border: none; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 16px; }

        @media (max-width: 768px) { #app { flex-direction: column-reverse; } #sidebar { width: 100%; height: 60px; flex-direction: row; justify-content: space-around; } }
    </style>
</head>
<body>

    <div id="modal-login" class="modal">
        <div class="modal-box">
            <h1 style="color:var(--primary); font-family:'Rajdhani'">FOR GLORY</h1>
            <div id="login-form">
                <input id="l-user" class="inp" placeholder="USUÁRIO">
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

    <div id="app">
        <div id="sidebar">
            <button class="nav-btn active" onclick="alert('Faça Login primeiro!')">🔒</button>
        </div>
        <div id="content-area" style="display:flex; align-items:center; justify-content:center;">
            <h2 style="color:#333;">Sistema Bloqueado</h2>
        </div>
    </div>

    <script>
        var user = null;

        function toggleAuth(m) {
            document.getElementById('login-form').style.display = m==='login'?'block':'none';
            document.getElementById('register-form').style.display = m==='register'?'block':'none';
        }

        async function doLogin() {
            let u=document.getElementById('l-user').value;
            let p=document.getElementById('l-pass').value;
            if(!u || !p) return alert("Preencha tudo!");
            
            try {
                let r = await fetch('/login', {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({username:u, password:p})
                });
                
                if(!r.ok) {
                    let err = await r.json();
                    throw new Error(err.detail || "Erro desconhecido");
                }
                user = await r.json();
                alert("Bem-vindo, " + user.username + "!");
                location.reload(); // Recarrega para entrar (simplificado)
            } catch(e) {
                alert("ERRO NO LOGIN: " + e.message);
            }
        }

        async function doRegister() {
            let u=document.getElementById('r-user').value;
            let e=document.getElementById('r-email').value;
            let p=document.getElementById('r-pass').value;
            if(!u || !e || !p) return alert("Preencha tudo!");

            try {
                let r = await fetch('/register', {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({username:u, email:e, password:p})
                });

                if(!r.ok) {
                    let err = await r.text(); // Pega texto puro caso não seja JSON
                    throw new Error(err || "Erro ao conectar no servidor");
                }
                alert("Conta criada! Agora faça login.");
                toggleAuth('login');
            } catch(e) {
                alert("ERRO NO REGISTRO: " + e.message);
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get(): return HTMLResponse(content=html_content)

# --- ENDPOINTS CRÍTICOS COM LOGS ---
@app.post("/register")
async def reg(d: RegisterData, db: Session=Depends(get_db)):
    try:
        # Verifica se user existe
        if db.query(User).filter(User.username==d.username).first():
            raise HTTPException(400, "Este nome de usuário já existe.")
        
        # Cria novo user
        new_user = User(
            username=d.username, 
            email=d.email, 
            password_hash=criptografar(d.password)
        )
        db.add(new_user)
        db.commit()
        logger.info(f"Usuário criado: {d.username}")
        return {"status":"ok"}
    except Exception as e:
        logger.error(f"Erro no registro: {e}")
        # Retorna o erro exato para o frontend mostrar no alerta
        raise HTTPException(500, detail=str(e))

@app.post("/login")
async def log(d: LoginData, db: Session=Depends(get_db)):
    u=db.query(User).filter(User.username==d.username).first()
    if not u or u.password_hash!=criptografar(d.password):
        raise HTTPException(400, "Usuário ou senha incorretos")
    return {"id":u.id, "username":u.username, "avatar_url":u.avatar_url, "bio":u.bio}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
