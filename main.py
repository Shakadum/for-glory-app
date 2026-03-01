from dotenv import load_dotenv
load_dotenv()
import uvicorn
import json
import os
import logging
import hashlib
from typing import List, Optional
from fastapi import FastAPI, WebSocket, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table, or_, and_, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session, joinedload
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
import cloudinary.uploader
from jose import jwt, JWTError
from collections import Counter
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import status

# ----------------------------------------------------------------------
# LOGGER (definido cedo para uso nas funções de segurança)
# ----------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForGlory")

# ----------------------------------------------------------------------
# CONFIGURAÇÕES DE SEGURANÇA
# ----------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "sua_chave_secreta_super_segura_123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# ========== FUNÇÃO CORRIGIDA (APENAS UMA) ==========
def get_password_hash(password):
    # Garante que a senha não ultrapasse 72 bytes (limite do bcrypt)
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password = password_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)

# ========== FUNÇÃO DE AUTENTICAÇÃO COM LOGS ==========
def authenticate_user(db: Session, username: str, password: str):
    logger.info(f"🔍 Tentativa de login para usuário: {username}")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.warning(f"❌ Usuário {username} não encontrado")
        return False
    if not user.password_hash:
        logger.warning(f"❌ Usuário {username} com password_hash vazio")
        return False
    logger.info(f"🔑 Hash armazenado: {user.password_hash[:50]}...")
    
    # Tenta bcrypt
    if user.password_hash.startswith("$2b$"):
        try:
            if verify_password(password, user.password_hash):
                logger.info("✅ Senha correta (bcrypt)")
                return user
            else:
                logger.warning("❌ Senha incorreta (bcrypt)")
        except Exception as e:
            logger.error(f"⚠️ Erro ao verificar bcrypt: {e}")
    
    # Tenta SHA256 (legado)
    if user.password_hash == hashlib.sha256(password.encode()).hexdigest():
        logger.info("🔄 Senha correta (SHA256) - atualizando para bcrypt")
        user.password_hash = get_password_hash(password)
        db.commit()
        return user
    
    logger.warning("❌ Nenhum método válido")
    return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

# ----------------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# ----------------------------------------------------------------------

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_NAME', 'dqa0q3qlx'),
    api_key=os.environ.get('CLOUDINARY_KEY', ''),
    api_secret=os.environ.get('CLOUDINARY_SECRET', ''),
    secure=True
)

# ----------------------------------------------------------------------
# BANCO DE DADOS (NEON / POSTGRESQL)
# ----------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./for_glory_v7.db"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
else:
    engine = create_engine(DATABASE_URL, pool_size=15, max_overflow=30, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

friendship = Table('friendships', Base.metadata,
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
    cover_url = Column(String, default="https://placehold.co/600x200/0b0c10/66fcf1?text=FOR+GLORY")
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
    banner_url = Column(String, default="")
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
    banner_url = Column(String, default="")
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

class CallBackground(Base):
    __tablename__ = "call_backgrounds"
    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String, index=True)
    target_id = Column(String, index=True)
    bg_url = Column(String)

class UserConfig(Base):
    __tablename__ = "user_configs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    target_type = Column(String)
    target_id = Column(String)
    wallpaper_url = Column(String, default="")

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error(f"Erro inicial BD: {e}")

# ----------------------------------------------------------------------
# MODELOS PYDANTIC (CORRIGIDOS)
# ----------------------------------------------------------------------
class LoginData(BaseModel):
    username: str
    password: str

class RegisterData(BaseModel):
    username: str
    email: str
    password: str

class ForgotPasswordData(BaseModel):
    email: str

class ResetPasswordData(BaseModel):
    token: str
    new_password: str

class ReadData(BaseModel):
    uid: int

class CreatePostData(BaseModel):
    caption: str
    content_url: str
    media_type: str

class ToggleLikeData(BaseModel):
    post_id: int

class DeletePostData(BaseModel):
    post_id: int

class CommentData(BaseModel):
    post_id: int
    text: str

class DelCommentData(BaseModel):
    comment_id: int

class DeleteMsgData(BaseModel):
    msg_id: int
    type: str

class FriendReqData(BaseModel):
    target_id: int

class UnfriendData(BaseModel):
    friend_id: int

class RequestActionData(BaseModel):
    request_id: int
    action: str

class CreateGroupData(BaseModel):
    name: str
    creator_id: int
    member_ids: List[int]

class CreateCommData(BaseModel):
    name: str
    desc: str
    is_priv: int
    avatar_url: str
    banner_url: str

class EditCommData(BaseModel):
    comm_id: int
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None

class JoinCommData(BaseModel):
    comm_id: int

class HandleCommReqData(BaseModel):
    req_id: int
    action: str

class CommMemberActionData(BaseModel):
    comm_id: int
    target_id: int

class CreateChannelData(BaseModel):
    comm_id: int
    name: str
    type: str
    is_private: int
    banner_url: Optional[str] = None

class EditChannelData(BaseModel):
    channel_id: int
    name: str
    type: str
    is_private: int
    banner_url: Optional[str] = None

class CallRingDMData(BaseModel):
    caller_id: int
    target_id: int
    channel_name: str

class CallRingGroupData(BaseModel):
    caller_id: int
    group_id: int
    channel_name: str

class SetWallpaperData(BaseModel):
    user_id: Optional[int] = None
    target_type: str
    target_id: str
    bg_url: Optional[str] = None

class UpdateProfileData(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None

# ----------------------------------------------------------------------
# APP E MANAGERS
# ----------------------------------------------------------------------
app = FastAPI(title="For Glory Cloud")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class ConnectionManager:
    def __init__(self):
        self.active = {}
        self.user_ws = {}
    async def connect(self, ws: WebSocket, chan: str, uid: int):
        await ws.accept()
        if chan not in self.active:
            self.active[chan] = []
        self.active[chan].append(ws)
        if chan == "Geral":
            self.user_ws[uid] = ws
    def disconnect(self, ws: WebSocket, chan: str, uid: int):
        if chan in self.active and ws in self.active[chan]:
            self.active[chan].remove(ws)
        if chan == "Geral" and uid in self.user_ws:
            del self.user_ws[uid]
    async def broadcast(self, msg: dict, chan: str):
        for conn in self.active.get(chan, []):
            try:
                await conn.send_text(json.dumps(msg))
            except:
                pass
    async def send_personal(self, msg: dict, uid: int):
        ws = self.user_ws.get(uid)
        if ws:
            try:
                await ws.send_text(json.dumps(msg))
            except:
                pass

manager = ConnectionManager()


def get_utc_iso(dt):
    return dt.isoformat() + "Z" if dt else ""

def create_reset_token(email: str):
    return jwt.encode({"sub": email, "exp": datetime.utcnow() + timedelta(minutes=30), "type": "reset"}, SECRET_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str):
    try:
        p = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return p.get("sub") if p.get("type") == "reset" else None
    except JWTError:
        return None

def get_user_badges(xp, user_id, role):
    tiers = [
        (0, "Recruta", 100, "#888888"),
        (100, "Soldado", 300, "#2ecc71"),
        (300, "Cabo", 600, "#27ae60"),
        (600, "3º Sargento", 1000, "#3498db"),
        (1000, "2º Sargento", 1500, "#2980b9"),
        (1500, "1º Sargento", 2500, "#9b59b6"),
        (2500, "Subtenente", 4000, "#8e44ad"),
        (4000, "Tenente", 6000, "#f1c40f"),
        (6000, "Capitão", 10000, "#f39c12"),
        (10000, "Major", 15000, "#e67e22"),
        (15000, "Tenente-Coronel", 25000, "#e74c3c"),
        (25000, "Coronel", 50000, "#c0392b"),
        (50000, "General ⭐", 50000, "#FFD700")
    ]
    rank = tiers[0][1]
    color = tiers[0][3]
    next_xp = tiers[0][2]
    next_rank = tiers[1][1]
    for i, t in enumerate(tiers):
        if xp >= t[0]:
            rank = t[1]
            color = t[3]
            next_xp = t[2]
            next_rank = tiers[i+1][1] if i+1 < len(tiers) else "Nível Máximo"
    percent = int((xp / next_xp) * 100) if next_xp > xp else 100
    if percent > 100:
        percent = 100
    special_emblem = "💎 Fundador" if user_id == 1 or role == "fundador" else ("🛡️ Admin" if role == "admin" else ("🌟 VIP" if role == "vip" else ""))
    medals = []
    all_medals = [
        {"icon": "🩸", "name": "1º Sangue", "desc": "Completou a 1ª Missão", "req": 50},
        {"icon": "🥈", "name": "Veterano", "desc": "Alcançou 500 XP", "req": 500},
        {"icon": "🥇", "name": "Elite", "desc": "Alcançou 2.000 XP", "req": 2000},
        {"icon": "🏆", "name": "Estrategista", "desc": "Alcançou 10.000 XP", "req": 10000},
        {"icon": "⭐", "name": "Supremo", "desc": "Tornou-se General", "req": 50000}
    ]
    if user_id == 1 or role == "fundador":
        medals.append({"icon": "💎", "name": "A Gênese", "desc": "Criador da Plataforma", "earned": True, "missing": 0})
    for m in all_medals:
        earned = xp >= m['req']
        missing = m['req'] - xp if not earned else 0
        medals.append({"icon": m['icon'], "name": m['name'], "desc": m['desc'], "earned": earned, "missing": missing})
    return {
        "rank": rank,
        "color": color,
        "next_xp": next_xp,
        "next_rank": next_rank,
        "percent": percent,
        "special_emblem": special_emblem,
        "medals": medals
    }

def format_user_summary(user: User):
    if not user:
        return {"id": 0, "username": "Desconhecido", "avatar_url": "https://ui-avatars.com/api/?name=?", "rank": "Recruta", "color": "#888", "special_emblem": ""}
    b = get_user_badges(user.xp, user.id, getattr(user, 'role', 'membro'))
    return {
        "id": user.id,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "rank": b['rank'],
        "color": b['color'],
        "special_emblem": b['special_emblem']
    }

# ----------------------------------------------------------------------
# ENDPOINTS DE UPLOAD (VIA BACKEND)
# ----------------------------------------------------------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload de imagem/vídeo para o Cloudinary.

    Aceita apenas tipos MIME comuns de imagem e vídeo. Retorna URL pública.
    """
    allowed_mime_types = [
        "image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif",
        "video/mp4", "video/webm", "video/quicktime",
    ]

    if file.content_type not in allowed_mime_types:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido.")

    # Envia para Cloudinary (resource_type='auto' suporta imagem/vídeo)
    result = cloudinary.uploader.upload(file.file, resource_type="auto")
    return {"url": result.get("secure_url")}

# ----------------------------------------------------------------------
# ENDPOINTS DE AUTENTICAÇÃO E USUÁRIO

# ----------------------------------------------------------------------
@app.post("/register")
def register(d: RegisterData, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=d.username).first():
        raise HTTPException(400, "Username already exists")
    hashed = get_password_hash(d.password)
    logger.info(f"Hash gerado para {d.username}: {hashed[:50]}...")
    db.add(User(
        username=d.username,
        email=d.email,
        password_hash=hashed,
        xp=0,
        is_invisible=0,
        role="fundador" if db.query(User).count() == 0 else "membro"
    ))
    db.commit()
    return {"status": "ok"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Rota de fallback para compatibilidade (caso algum cliente use /login)
@app.post("/login")
async def login_legacy(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return await login_for_access_token(form_data, db)

@app.post("/auth/forgot-password")
def forgot_password(d: ForgotPasswordData, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=d.email).first()
    if user:
        token = create_reset_token(user.email)
        logger.info(f"RESGATE: https://for-glory.onrender.com/?token={token}")
    return {"status": "ok"}

@app.post("/auth/reset-password")
def reset_password(d: ResetPasswordData, db: Session = Depends(get_db)):
    email = verify_reset_token(d.token)
    if not email:
        raise HTTPException(400, "Token inválido ou expirado")
    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    new_hash = get_password_hash(d.new_password)
    logger.info(f"Novo hash gerado para {email}")
    user.password_hash = new_hash
    db.commit()
    return {"status": "ok"}

@app.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    b = get_user_badges(current_user.xp, current_user.id, getattr(current_user, 'role', 'membro'))
    return {
        "id": current_user.id,
        "username": current_user.username,
        "avatar_url": current_user.avatar_url,
        "cover_url": current_user.cover_url,
        "bio": current_user.bio,
        "xp": current_user.xp,
        "rank": b['rank'],
        "color": b['color'],
        "special_emblem": b['special_emblem'],
        "percent": b['percent'],
        "next_xp": b['next_xp'],
        "next_rank": b['next_rank'],
        "medals": b['medals'],
        "is_invisible": getattr(current_user, 'is_invisible', 0)
    }

@app.get("/users/online")
def get_online_users(db: Session = Depends(get_db)):
    active_uids = list(manager.user_ws.keys())
    if not active_uids:
        return []
    visible_users = db.query(User.id).filter(User.id.in_(active_uids), User.is_invisible == 0).all()
    return [u[0] for u in visible_users]

@app.get("/users/search")
def search_users(q: str, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.username.ilike(f"%{q}%")).limit(10).all()
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in users]

@app.post("/profile/stealth")
def toggle_stealth(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    current_user.is_invisible = 1 if current_user.is_invisible == 0 else 0
    db.commit()
    return {"is_invisible": current_user.is_invisible}

@app.post("/profile/update_meta")
def update_prof_meta(
    d: UpdateProfileData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if d.avatar_url:
        current_user.avatar_url = d.avatar_url
    if d.cover_url:
        current_user.cover_url = d.cover_url
    if d.bio:
        current_user.bio = d.bio
    db.commit()
    return {"status": "ok"}

@app.get("/user/{target_id}")
async def get_user_profile(
    target_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    target = db.query(User).filter_by(id=target_id).first()
    viewer = current_user
    if not target or not viewer:
        return {"username": "Desconhecido", "avatar_url": "https://ui-avatars.com/api/?name=?", "cover_url": "", "bio": "Perdido em combate.", "rank": "Recruta", "color": "#888", "special_emblem": "", "medals": [], "percent": 0, "next_xp": 100, "next_rank": "Soldado", "posts": [], "friend_status": "none", "request_id": None}
    posts = db.query(Post).filter_by(user_id=target_id).order_by(Post.timestamp.desc()).all()
    posts_data = [{"content_url": p.content_url, "media_type": p.media_type} for p in posts]
    status = "friends" if target in viewer.friends else "none"
    req_id = None
    if status == "none":
        sent = db.query(FriendRequest).filter_by(sender_id=viewer.id, receiver_id=target_id).first()
        received = db.query(FriendRequest).filter_by(sender_id=target_id, receiver_id=viewer.id).first()
        if sent:
            status = "pending_sent"
        if received:
            status = "pending_received"
            req_id = received.id
    return {"username": target.username, "avatar_url": target.avatar_url, "cover_url": target.cover_url, "bio": target.bio, "posts": posts_data, "friend_status": status, "request_id": req_id, **format_user_summary(target)}

# ----------------------------------------------------------------------
# ENDPOINTS DE POSTS
# ----------------------------------------------------------------------
@app.post("/post/create_from_url")
def create_post_url(
    d: CreatePostData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db.add(Post(user_id=current_user.id, content_url=d.content_url, media_type=d.media_type, caption=(d.caption or "")))
    current_user.xp += 50
    db.commit()
    return {"status": "ok"}

@app.post("/post/like")
def toggle_like(
    d: ToggleLikeData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    existing = db.query(Like).filter_by(post_id=d.post_id, user_id=current_user.id).first()
    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(Like(post_id=d.post_id, user_id=current_user.id))
        liked = True
    db.commit()
    return {"liked": liked, "count": db.query(Like).filter_by(post_id=d.post_id).count()}

@app.post("/post/comment")
def add_comment(
    d: CommentData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db.add(Comment(user_id=current_user.id, post_id=d.post_id, text=d.text))
    db.commit()
    return {"status": "ok"}

@app.post("/comment/delete")
def del_comment(
    d: DelCommentData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    c = db.query(Comment).filter_by(id=d.comment_id).first()
    if c and c.user_id == current_user.id:
        db.delete(c)
        db.commit()
    return {"status": "ok"}

@app.post("/post/delete")
def delete_post_endpoint(
    d: DeletePostData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter_by(id=d.post_id).first()
    if not post or post.user_id != current_user.id:
        return {"status": "error"}
    db.query(Like).filter_by(post_id=post.id).delete()
    db.query(Comment).filter_by(post_id=post.id).delete()
    db.delete(post)
    if current_user.xp >= 50:
        current_user.xp -= 50
    db.commit()
    return {"status": "ok"}

@app.get("/post/{post_id}/comments")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).filter_by(post_id=post_id).order_by(Comment.timestamp.asc()).all()
    return [{"id": c.id, "text": c.text, "author_name": c.author.username, "author_avatar": c.author.avatar_url, "author_id": c.author.id, **format_user_summary(c.author)} for c in comments]

@app.get("/posts")
def get_posts(uid: int, limit: int = 50, db: Session = Depends(get_db)):
    posts = db.query(Post).options(joinedload(Post.author)).order_by(Post.timestamp.desc()).limit(limit).all()
    post_ids = [p.id for p in posts]
    likes_bulk = db.query(Like.post_id, Like.user_id).filter(Like.post_id.in_(post_ids)).all() if post_ids else []
    comments_count = db.query(Comment.post_id, func.count(Comment.id)).filter(Comment.post_id.in_(post_ids)).group_by(Comment.post_id).all() if post_ids else []
    comments_dict = dict(comments_count)
    result = []
    for p in posts:
        post_likes = [l for l in likes_bulk if l[0] == p.id]
        u_sum = format_user_summary(p.author)
        result.append({
            "id": p.id,
            "content_url": p.content_url,
            "media_type": p.media_type,
            "caption": p.caption,
            "author_name": u_sum["username"],
            "author_avatar": u_sum["avatar_url"],
            "author_rank": u_sum["rank"],
            "rank_color": u_sum["color"],
            "special_emblem": u_sum["special_emblem"],
            "author_id": p.author_id,
            "likes": len(post_likes),
            "user_liked": any(l[1] == uid for l in post_likes),
            "comments": comments_dict.get(p.id, 0)
        })
    return result

# ----------------------------------------------------------------------
# ENDPOINTS DE AMIZADE
# ----------------------------------------------------------------------
@app.post("/friend/request")
def send_req(
    d: FriendReqData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    me = current_user
    target = db.query(User).filter_by(id=d.target_id).first()
    if not target:
        return {"status": "error"}
    if target in me.friends:
        return {"status": "already_friends"}
    existing = db.query(FriendRequest).filter(
        or_(
            and_(FriendRequest.sender_id == me.id, FriendRequest.receiver_id == d.target_id),
            and_(FriendRequest.sender_id == d.target_id, FriendRequest.receiver_id == me.id)
        )
    ).first()
    if existing:
        return {"status": "pending"}
    db.add(FriendRequest(sender_id=me.id, receiver_id=d.target_id))
    db.commit()
    return {"status": "sent"}

@app.get("/friend/requests")
def get_reqs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    reqs = db.query(FriendRequest).filter_by(receiver_id=uid).all()
    requests_data = [{"id": r.id, "username": db.query(User).filter_by(id=r.sender_id).first().username} for r in reqs]
    me = db.query(User).filter_by(id=uid).first()
    friends_data = [{"id": f.id, "username": f.username, "avatar": f.avatar_url} for f in me.friends] if me else []
    return {"requests": requests_data, "friends": friends_data}

@app.post("/friend/handle")
def handle_req(
    d: RequestActionData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    req = db.query(FriendRequest).filter_by(id=d.request_id).first()
    if not req or req.receiver_id != current_user.id:
        return {"status": "error"}
    if d.action == 'accept':
        u1 = db.query(User).filter_by(id=req.sender_id).first()
        u2 = db.query(User).filter_by(id=req.receiver_id).first()
        u1.friends.append(u2)
        u2.friends.append(u1)
    db.delete(req)
    db.commit()
    return {"status": "ok"}

@app.post("/friend/remove")
def remove_friend(
    d: UnfriendData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    me = current_user
    other = db.query(User).filter_by(id=d.friend_id).first()
    if not other:
        raise HTTPException(404, "Usuário não encontrado")
    if other in me.friends:
        me.friends.remove(other)
    if me in other.friends:
        other.friends.remove(me)
    db.query(FriendRequest).filter(
        or_(
            and_(FriendRequest.sender_id == me.id, FriendRequest.receiver_id == d.friend_id),
            and_(FriendRequest.sender_id == d.friend_id, FriendRequest.receiver_id == me.id)
        )
    ).delete(synchronize_session=False)
    db.commit()
    return {"status": "ok"}

# ----------------------------------------------------------------------
# ENDPOINTS DE MENSAGENS E INBOX
# ----------------------------------------------------------------------
@app.get("/notifications")
def get_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    unread_pms = db.query(PrivateMessage.sender_id).filter(PrivateMessage.receiver_id == uid, PrivateMessage.is_read == 0).all()
    pm_counts = Counter([str(u[0]) for u in unread_pms])
    total_dms = sum(pm_counts.values())

    my_comms = db.query(Community).filter(Community.creator_id == uid).all()
    my_admin_roles = db.query(CommunityMember).filter_by(user_id=uid, role="admin").all()
    admin_comm_ids = set([c.id for c in my_comms] + [r.comm_id for r in my_admin_roles])

    req_counts = {}
    if admin_comm_ids:
        pending_reqs = db.query(CommunityRequest.comm_id).filter(CommunityRequest.comm_id.in_(list(admin_comm_ids))).all()
        req_counts = Counter([str(r[0]) for r in pending_reqs])

    friend_reqs_count = db.query(FriendRequest).filter_by(receiver_id=uid).count()

    return {
        "dms": {"total": total_dms, "by_sender": dict(pm_counts)},
        "comms": {"total": sum(req_counts.values()), "by_comm": dict(req_counts)},
        "friend_reqs": friend_reqs_count
    }

@app.get("/inbox/unread")
def get_unread(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    unread_pms = db.query(PrivateMessage.sender_id).filter(PrivateMessage.receiver_id == uid, PrivateMessage.is_read == 0).all()
    counts = Counter([str(u[0]) for u in unread_pms])
    return {"total": sum(counts.values()), "by_sender": dict(counts)}

@app.get("/inbox")
def get_inbox(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    me = db.query(User).filter_by(id=uid).first()
    friends_data = [{"id": f.id, "name": f.username, "avatar": f.avatar_url} for f in me.friends] if me else []
    my_groups = db.query(GroupMember).filter_by(user_id=uid).all()
    groups_data = []
    for gm in my_groups:
        group = db.query(ChatGroup).filter_by(id=gm.group_id).first()
        if group:
            groups_data.append({"id": group.id, "name": group.name, "avatar": "https://ui-avatars.com/api/?name=G&background=111&color=66fcf1"})
    return {"friends": friends_data, "groups": groups_data}

@app.get("/dms/{target_id}")
def get_dms(
    target_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    msgs = db.query(PrivateMessage).filter(
        or_(
            and_(PrivateMessage.sender_id == uid, PrivateMessage.receiver_id == target_id),
            and_(PrivateMessage.sender_id == target_id, PrivateMessage.receiver_id == uid)
        )
    ).order_by(PrivateMessage.timestamp.asc()).limit(100).all()
    return [{
        "id": m.id,
        "user_id": m.sender_id,
        "content": m.content,
        "timestamp": get_utc_iso(m.timestamp),
        "avatar": m.sender.avatar_url,
        "username": m.sender.username,
        "can_delete": (datetime.utcnow() - m.timestamp).total_seconds() <= 300,
        **format_user_summary(m.sender)
    } for m in msgs]

@app.post("/inbox/read/{sender_id}")
def mark_read(
    sender_id: int,
    d: ReadData,
    db: Session = Depends(get_db)
):
    db.query(PrivateMessage).filter(
        PrivateMessage.sender_id == sender_id,
        PrivateMessage.receiver_id == d.uid
    ).update({"is_read": 1})
    db.commit()
    return {"status": "ok"}

@app.post("/message/delete")
async def delete_msg(
    d: DeleteMsgData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    msg = None
    if d.type == 'dm':
        msg = db.query(PrivateMessage).filter_by(id=d.msg_id).first()
    elif d.type == 'comm':
        msg = db.query(CommunityMessage).filter_by(id=d.msg_id).first()
    elif d.type == 'group':
        msg = db.query(GroupMessage).filter_by(id=d.msg_id).first()

    if msg and msg.sender_id == current_user.id:
        if (datetime.utcnow() - msg.timestamp).total_seconds() > 300:
            return {"status": "timeout", "msg": "Tempo limite excedido."}
        msg.content = "[DELETED]"
        db.commit()

# Notifica todos conectados para apagar no outro cliente também
try:
    await manager.broadcast_json("Geral", {
        "type": "message_deleted",
        "msg_id": int(d.msg_id),
        "scope": d.type,
        "by": current_user.id,
    })
except Exception as e:
    logger.warning(f"broadcast message_deleted failed: {e}")

        return {"status": "ok"}
    return {"status": "error"}

# ----------------------------------------------------------------------
# ENDPOINTS DE GRUPOS
# ----------------------------------------------------------------------
@app.post("/group/create")
def create_group(
    d: CreateGroupData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if d.creator_id != current_user.id:
        raise HTTPException(403, "Você só pode criar grupos como você mesmo")
    group = ChatGroup(name=d.name)
    db.add(group)
    db.commit()
    db.refresh(group)
    # Adiciona o criador
    db.add(GroupMember(group_id=group.id, user_id=current_user.id))
    for mid in d.member_ids:
        if mid != current_user.id:
            db.add(GroupMember(group_id=group.id, user_id=mid))
    db.commit()
    return {"status": "ok"}

@app.get("/group/{group_id}/messages")
def get_group_messages(
    group_id: int,
    db: Session = Depends(get_db)
):
    msgs = db.query(GroupMessage).filter_by(group_id=group_id).order_by(GroupMessage.timestamp.asc()).limit(100).all()
    return [{
        "id": m.id,
        "user_id": m.sender_id,
        "content": m.content,
        "timestamp": get_utc_iso(m.timestamp),
        "avatar": m.sender.avatar_url,
        "username": m.sender.username,
        "can_delete": (datetime.utcnow() - m.timestamp).total_seconds() <= 300,
        **format_user_summary(m.sender)
    } for m in msgs]

# ----------------------------------------------------------------------
# ENDPOINTS DE COMUNIDADES
# ----------------------------------------------------------------------
@app.post("/community/create")
def create_comm(
    d: CreateCommData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    c = Community(
        name=d.name,
        description=d.desc,
        avatar_url=d.avatar_url,
        banner_url=d.banner_url,
        is_private=d.is_priv,
        creator_id=current_user.id
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    db.add(CommunityMember(comm_id=c.id, user_id=current_user.id, role="admin"))
    db.add(CommunityChannel(comm_id=c.id, name="geral", channel_type="livre", is_private=0, banner_url=d.banner_url))
    db.commit()
    return {"status": "ok"}

@app.post("/community/join")
def join_comm(
    d: JoinCommData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    c = db.query(Community).filter_by(id=d.comm_id).first()
    if not c or c.is_private:
        return {"status": "error"}
    if not db.query(CommunityMember).filter_by(comm_id=c.id, user_id=current_user.id).first():
        db.add(CommunityMember(comm_id=c.id, user_id=current_user.id, role="member"))
        db.commit()
    return {"status": "ok"}

@app.post("/community/{cid}/leave")
def leave_community(
    cid: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    member = db.query(CommunityMember).filter_by(comm_id=cid, user_id=current_user.id).first()
    if member:
        comm = db.query(Community).filter_by(id=cid).first()
        if member.role == 'admin' and comm and comm.creator_id == current_user.id:
            return {"status": "error", "msg": "O criador não pode sair sem deletar a base."}
        db.delete(member)
        db.commit()
    return {"status": "ok"}

@app.post("/community/edit")
def edit_comm(
    d: EditCommData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    c = db.query(Community).filter_by(id=d.comm_id).first()
    if not c or c.creator_id != current_user.id:
        return {"status": "error"}
    if d.avatar_url:
        c.avatar_url = d.avatar_url
    if d.banner_url:
        c.banner_url = d.banner_url
        geral_ch = db.query(CommunityChannel).filter_by(comm_id=c.id, name="geral").first()
        if geral_ch:
            geral_ch.banner_url = d.banner_url
    db.commit()
    return {"status": "ok"}

@app.post("/community/{cid}/delete")
def destroy_comm(
    cid: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    c = db.query(Community).filter_by(id=cid).first()
    if not c or c.creator_id != current_user.id:
        return {"status": "error"}
    ch_ids = [ch.id for ch in db.query(CommunityChannel).filter_by(comm_id=cid).all()]
    if ch_ids:
        db.query(CommunityMessage).filter(CommunityMessage.channel_id.in_(ch_ids)).delete(synchronize_session=False)
    db.query(CommunityChannel).filter_by(comm_id=cid).delete()
    db.query(CommunityMember).filter_by(comm_id=cid).delete()
    db.query(CommunityRequest).filter_by(comm_id=cid).delete()
    db.delete(c)
    db.commit()
    return {"status": "ok"}

@app.post("/community/member/promote")
def promote_member(
    d: CommMemberActionData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    c = db.query(Community).filter_by(id=d.comm_id).first()
    if not c:
        return {"status": "error"}
    admin = db.query(CommunityMember).filter_by(comm_id=c.id, user_id=current_user.id).first()
    if not admin or (admin.role != 'admin' and c.creator_id != current_user.id):
        return {"status": "error"}
    target = db.query(CommunityMember).filter_by(comm_id=c.id, user_id=d.target_id).first()
    if target:
        target.role = 'admin'
        db.commit()
    return {"status": "ok"}

@app.post("/community/member/demote")
def demote_member(
    d: CommMemberActionData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    c = db.query(Community).filter_by(id=d.comm_id).first()
    if not c or c.creator_id != current_user.id:
        return {"status": "error"}
    target = db.query(CommunityMember).filter_by(comm_id=c.id, user_id=d.target_id).first()
    if target and target.role == 'admin':
        target.role = 'member'
        db.commit()
    return {"status": "ok"}

@app.post("/community/member/kick")
def kick_member(
    d: CommMemberActionData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    c = db.query(Community).filter_by(id=d.comm_id).first()
    if not c:
        return {"status": "error"}
    admin = db.query(CommunityMember).filter_by(comm_id=c.id, user_id=current_user.id).first()
    if not admin or (admin.role != 'admin' and c.creator_id != current_user.id):
        return {"status": "error"}
    target = db.query(CommunityMember).filter_by(comm_id=c.id, user_id=d.target_id).first()
    if not target or target.user_id == c.creator_id or (target.role == 'admin' and c.creator_id != current_user.id):
        return {"status": "error"}
    db.delete(target)
    db.commit()
    return {"status": "ok"}

@app.get("/communities/list")
def list_comms(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    my_comm_ids = [m.comm_id for m in db.query(CommunityMember).filter_by(user_id=uid).all()]
    return {"my_comms": [{"id": c.id, "name": c.name, "avatar_url": c.avatar_url} for c in db.query(Community).filter(Community.id.in_(my_comm_ids)).all()]}

@app.get("/communities/search")
def search_comms(
    current_user: User = Depends(get_current_active_user),
    q: str = "",
    db: Session = Depends(get_db)
):
    uid = current_user.id
    my_comm_ids = [m.comm_id for m in db.query(CommunityMember).filter_by(user_id=uid).all()]
    query = db.query(Community).filter(~Community.id.in_(my_comm_ids))
    if q:
        query = query.filter(Community.name.ilike(f"%{q}%"))
    return [{"id": c.id, "name": c.name, "avatar_url": c.avatar_url, "desc": c.description, "is_private": c.is_private} for c in query.limit(20).all()]

@app.post("/community/request/send")
def send_comm_req(
    d: JoinCommData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    c = db.query(Community).filter_by(id=d.comm_id).first()
    if not c:
        return {"status": "error"}
    if c.is_private == 0:
        if not db.query(CommunityMember).filter_by(comm_id=c.id, user_id=current_user.id).first():
            db.add(CommunityMember(comm_id=c.id, user_id=current_user.id, role="member"))
            db.commit()
        return {"status": "joined"}
    else:
        if not db.query(CommunityRequest).filter_by(comm_id=c.id, user_id=current_user.id).first():
            db.add(CommunityRequest(comm_id=c.id, user_id=current_user.id))
            db.commit()
        return {"status": "requested"}

@app.get("/community/{cid}/requests")
def get_comm_reqs(
    cid: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    role = db.query(CommunityMember).filter_by(comm_id=cid, user_id=uid).first()
    c = db.query(Community).filter_by(id=cid).first()
    if (not role or role.role != "admin") and (c and c.creator_id != uid):
        return []
    return [{"id": r.id, "user_id": r.user.id, "username": r.user.username, "avatar": r.user.avatar_url} for r in db.query(CommunityRequest).filter_by(comm_id=cid).all()]

@app.post("/community/request/handle")
def handle_comm_req(
    d: HandleCommReqData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    req = db.query(CommunityRequest).filter_by(id=d.req_id).first()
    if not req:
        return {"status": "error"}
    role = db.query(CommunityMember).filter_by(comm_id=req.comm_id, user_id=current_user.id).first()
    c = db.query(Community).filter_by(id=req.comm_id).first()
    if (not role or role.role != "admin") and (c and c.creator_id != current_user.id):
        return {"status": "unauthorized"}
    if d.action == "accept":
        if not db.query(CommunityMember).filter_by(comm_id=req.comm_id, user_id=req.user_id).first():
            db.add(CommunityMember(comm_id=req.comm_id, user_id=req.user_id, role="member"))
    db.delete(req)
    db.commit()
    return {"status": "ok"}

@app.get("/community/{cid}")
def get_comm_details(
    cid: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    c = db.query(Community).filter_by(id=cid).first()
    my_role = db.query(CommunityMember).filter_by(comm_id=cid, user_id=uid).first()
    is_admin = my_role and my_role.role == "admin"
    channels = db.query(CommunityChannel).filter_by(comm_id=cid).all()
    visible_channels = [
        {"id": ch.id, "name": ch.name, "type": ch.channel_type, "banner_url": ch.banner_url, "is_private": ch.is_private}
        for ch in channels if ch.is_private == 0 or is_admin or (c and c.creator_id == uid)
    ]
    members = db.query(CommunityMember).filter_by(comm_id=cid).all()
    members_data = [{"id": m.user.id, "name": m.user.username, "avatar": m.user.avatar_url, "role": m.role} for m in members]
    return {
        "name": c.name if c else "?",
        "description": c.description if c else "",
        "avatar_url": c.avatar_url if c else "",
        "banner_url": c.banner_url if c else "",
        "is_admin": is_admin,
        "creator_id": c.creator_id if c else 0,
        "channels": visible_channels,
        "members": members_data
    }

@app.post("/community/channel/create")
def create_channel(
    d: CreateChannelData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    role = db.query(CommunityMember).filter_by(comm_id=d.comm_id, user_id=current_user.id).first()
    c = db.query(Community).filter_by(id=d.comm_id).first()
    if (not role or role.role != "admin") and (c and c.creator_id != current_user.id):
        return {"status": "error"}
    db.add(CommunityChannel(
        comm_id=d.comm_id,
        name=d.name,
        channel_type=d.type,
        is_private=d.is_private,
        banner_url=d.banner_url
    ))
    db.commit()
    return {"status": "ok"}

@app.post("/community/channel/edit")
def edit_channel(
    d: EditChannelData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    ch = db.query(CommunityChannel).filter_by(id=d.channel_id).first()
    if not ch:
        return {"status": "error"}
    role = db.query(CommunityMember).filter_by(comm_id=ch.comm_id, user_id=current_user.id).first()
    c = db.query(Community).filter_by(id=ch.comm_id).first()
    if (not role or role.role != "admin") and (c and c.creator_id != current_user.id):
        return {"status": "error"}
    ch.name = d.name
    ch.channel_type = d.type
    ch.is_private = d.is_private
    if d.banner_url:
        ch.banner_url = d.banner_url
    db.commit()
    return {"status": "ok"}

@app.post("/community/channel/{chid}/delete")
def destroy_channel(
    chid: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    ch = db.query(CommunityChannel).filter_by(id=chid).first()
    if not ch:
        return {"status": "error"}
    role = db.query(CommunityMember).filter_by(comm_id=ch.comm_id, user_id=current_user.id).first()
    c = db.query(Community).filter_by(id=ch.comm_id).first()
    if (not role or role.role != "admin") and (c and c.creator_id != current_user.id):
        return {"status": "error"}
    db.query(CommunityMessage).filter_by(channel_id=chid).delete()
    db.delete(ch)
    db.commit()
    return {"status": "ok"}

@app.get("/community/channel/{chid}/messages")
def get_comm_msgs(chid: int, db: Session = Depends(get_db)):
    msgs = db.query(CommunityMessage).filter_by(channel_id=chid).order_by(CommunityMessage.timestamp.asc()).limit(100).all()
    return [{
        "id": m.id,
        "user_id": m.sender_id,
        "content": m.content,
        "timestamp": get_utc_iso(m.timestamp),
        "avatar": m.sender.avatar_url,
        "username": m.sender.username,
        "can_delete": (datetime.utcnow() - m.timestamp).total_seconds() <= 300,
        **format_user_summary(m.sender)
    } for m in msgs]

# ----------------------------------------------------------------------
# ENDPOINTS DE CHAMADAS (AGORA)
# ----------------------------------------------------------------------
@app.post("/call/ring/dm")
async def ring_dm(d: CallRingDMData, db: Session = Depends(get_db)):
    caller = db.query(User).filter_by(id=d.caller_id).first()
    if caller:
        await manager.send_personal({
            "type": "incoming_call",
            "caller_id": caller.id,
            "caller_name": caller.username,
            "caller_avatar": caller.avatar_url,
            "channel_name": d.channel_name,
            "call_type": "dm",
            "target_id": d.target_id
        }, d.target_id)
    return {"status": "ok"}

@app.post("/call/ring/group")
async def ring_group(d: CallRingGroupData, db: Session = Depends(get_db)):
    caller = db.query(User).filter_by(id=d.caller_id).first()
    group = db.query(ChatGroup).filter_by(id=d.group_id).first()
    if not caller or not group:
        return {"status": "error"}
    for m in db.query(GroupMember).filter_by(group_id=d.group_id).all():
        if m.user_id != d.caller_id:
            await manager.send_personal({
                "type": "incoming_call",
                "caller_id": caller.id,
                "caller_name": f"{caller.username} (Grp: {group.name})",
                "caller_avatar": caller.avatar_url,
                "channel_name": d.channel_name,
                "call_type": "group",
                "target_id": d.group_id
            }, m.user_id)
    return {"status": "ok"}

@app.get("/agora-config")
def get_agora_config():
    return {"app_id": os.environ.get("AGORA_APP_ID", "")}


@app.get("/agora/token")
def get_agora_token(channel: str, uid: int = 0, current_user: User = Depends(get_current_active_user)):
    """Gera token RTC da Agora (necessário quando App Certificate está ligado)."""
    app_id = os.environ.get("AGORA_APP_ID", "")
    app_cert = os.environ.get("AGORA_APP_CERTIFICATE", "")
    if not app_id or not app_cert:
        raise HTTPException(status_code=500, detail="AGORA_APP_ID/AGORA_APP_CERTIFICATE não configurados")
    try:
        from agora_token_builder import RtcTokenBuilder
    except Exception as e:
        raise HTTPException(status_code=500, detail="Dependência agora-token-builder não instalada") from e
    channel_name = channel
    uid_int = int(uid) if uid else int(current_user.id)
    # role: 1 = publisher, 2 = subscriber (conforme token builder)
    role = 1
    expire = int(
    os.getenv("AGORA_TOKEN_EXPIRE_SECONDS")
    or os.getenv("AGORA_TOKEN_EXPIRE")
    or "3600"
)
    current_ts = int(datetime.now(timezone.utc).timestamp())
privilege_expired_ts = current_ts + expire

token = RtcTokenBuilder.buildTokenWithUid(
    app_id,
    app_cert,
    channel_name,
    uid_int,
    role,
    privilege_expired_ts
)

return {
    "app_id": app_id,
    "token": token,
    "uid": uid_int,
    "expires_in": expire
}

@app.post("/call/bg/set")
def set_call_bg(d: SetWallpaperData, db: Session = Depends(get_db)):
    bg = db.query(CallBackground).filter_by(target_type=d.target_type, target_id=d.target_id).first()
    if bg:
        bg.bg_url = d.bg_url
    else:
        db.add(CallBackground(target_type=d.target_type, target_id=d.target_id, bg_url=d.bg_url))
    db.commit()
    return {"status": "ok"}

@app.get("/call/bg/{target_type}/{target_id}")
def get_call_bg(target_type: str, target_id: str, db: Session = Depends(get_db)):
    bg = db.query(CallBackground).filter_by(target_type=target_type, target_id=target_id).first()
    return {"bg_url": bg.bg_url if bg else None}

@app.get("/call/bg/call/{channel_name}")
def get_call_bg_by_channel(channel_name: str, db: Session = Depends(get_db)):
    bg = db.query(CallBackground).filter_by(target_type="call", target_id=channel_name).first()
    return {"bg_url": bg.bg_url if bg else None}

@app.get("/call/bg/channel/{channel_id}")
def get_channel_bg(channel_id: int, db: Session = Depends(get_db)):
    bg = db.query(CallBackground).filter_by(target_type="channel", target_id=str(channel_id)).first()
    return {"bg_url": bg.bg_url if bg else None}

# ----------------------------------------------------------------------
# WEBSOCKET (COM TOKEN)
# ----------------------------------------------------------------------
def handle_dm_message(db: Session, ch: str, uid: int, txt: str):
    parts = ch.split("_")
    rec_id = int(parts[2]) if uid == int(parts[1]) else int(parts[1])
    new_msg = PrivateMessage(sender_id=uid, receiver_id=rec_id, content=txt, is_read=0)
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg, rec_id

def handle_comm_message(db: Session, ch: str, uid: int, txt: str):
    chid = int(ch.split("_")[1])
    new_msg = CommunityMessage(channel_id=chid, sender_id=uid, content=txt)
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg, None

def handle_group_message(db: Session, ch: str, uid: int, txt: str):
    grid = int(ch.split("_")[1])
    new_msg = GroupMessage(group_id=grid, sender_id=uid, content=txt)
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg, None

@app.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int):
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=1008, reason="Missing token")
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            await ws.close(code=1008, reason="Invalid token")
            return
        db = SessionLocal()
        user = db.query(User).filter(User.username == username).first()
        if not user or user.id != uid:
            await ws.close(code=1008, reason="User mismatch")
            return
    except JWTError:
        await ws.close(code=1008, reason="Invalid token")
        return
    finally:
        db.close()

    await manager.connect(ws, ch, uid)

    try:
        while True:
            txt = await ws.receive_text()

            if txt == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
                continue

            db = SessionLocal()
            try:
                u_fresh = db.query(User).filter_by(id=uid).first()
                if not u_fresh:
                    continue

                new_msg = None
                target_dm_id = None

                if ch.startswith("dm_"):
                    new_msg, target_dm_id = handle_dm_message(db, ch, uid, txt)
                    if target_dm_id:
                        await manager.send_personal({"type": "new_dm", "sender_id": u_fresh.id, "sender_name": u_fresh.username}, target_dm_id)
                elif ch.startswith("comm_"):
                    new_msg, _ = handle_comm_message(db, ch, uid, txt)
                elif ch.startswith("group_"):
                    new_msg, _ = handle_group_message(db, ch, uid, txt)

                if new_msg:
                    b = get_user_badges(u_fresh.xp, u_fresh.id, getattr(u_fresh, 'role', 'membro'))
                    user_data = {
                        "id": new_msg.id,
                        "user_id": u_fresh.id,
                        "username": u_fresh.username,
                        "avatar": u_fresh.avatar_url,
                        "content": txt,
                        "can_delete": True,
                        "timestamp": get_utc_iso(new_msg.timestamp),
                        "rank": b['rank'],
                        "color": b['color'],
                        "special_emblem": b['special_emblem']
                    }
                    await manager.broadcast(user_data, ch)
                    if ch.startswith("dm_") or ch.startswith("group_"):
                        await manager.broadcast({"type": "ping"}, "Geral")
            except Exception as e:
                db.rollback()
                logger.error(f"Erro WS: {e}")
            finally:
                db.close()
    except Exception:
        manager.disconnect(ws, ch, uid)

# ----------------------------------------------------------------------
# FRONTEND (CORRIGIDO)
# ----------------------------------------------------------------------
html_content = ""  # moved to app/templates/index.html + app/static


# ----------------------------------------------------------------------
# ROTA PRINCIPAL (FRONTEND)
# ----------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

