import uvicorn
import json
import os
import logging
import hashlib
from typing import List, Optional
from fastapi import FastAPI, WebSocket, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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
# CONFIGURAÇÕES DE SEGURANÇA
# ----------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "sua_chave_secreta_super_segura_123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # Garante que a senha não ultrapasse 72 bytes (limite do bcrypt)
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password = password_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.password_hash:
        return False

    # Tenta bcrypt apenas se o hash parecer bcrypt
    if user.password_hash.startswith("$2b$"):
        try:
            if verify_password(password, user.password_hash):
                return user
        except Exception:
            pass  # Falha na verificação bcrypt, continua para SHA256

    # Tenta SHA256 (legado)
    if user.password_hash == hashlib.sha256(password.encode()).hexdigest():
        # Atualiza para bcrypt
        user.password_hash = get_password_hash(password)
        db.commit()
        return user

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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForGlory")

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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    # Validações simples
    if file.size > 100 * 1024 * 1024:
        raise HTTPException(400, "Arquivo muito grande (máx 100MB)")
    allowed = ["image/jpeg", "image/png", "image/gif", "video/mp4", "video/webm", "audio/webm", "audio/mpeg"]
    if file.content_type not in allowed:
        raise HTTPException(400, "Tipo de arquivo não permitido")
    try:
        result = cloudinary.uploader.upload(file.file, resource_type="auto")
        return {"secure_url": result["secure_url"]}
    except Exception as e:
        raise HTTPException(500, f"Erro no upload: {e}")

# ----------------------------------------------------------------------
# ENDPOINTS DE AUTENTICAÇÃO E USUÁRIO
# ----------------------------------------------------------------------
@app.post("/register")
def register(d: RegisterData, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=d.username).first():
        raise HTTPException(400, "Username already exists")
    hashed = get_password_hash(d.password)
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
        # Por enquanto, apenas loga o link (futuramente enviar e-mail)
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
    # Log para debug (pode ser removido depois)
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
    db.add(Post(user_id=current_user.id, content_url=d.content_url, media_type=d.media_type, caption=d.caption))
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
def delete_msg(
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
html_content = r"""<!DOCTYPE html>
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

.lang-dropdown { position:absolute; top:15px; right:15px; z-index:9999; }
.lang-btn { background:rgba(11,12,16,0.6); color:white; border:1px solid var(--primary); padding:8px 15px; border-radius:20px; cursor:pointer; font-weight:bold; font-family:'Rajdhani'; backdrop-filter:blur(5px); display:flex; align-items:center; gap:5px; transition:0.3s; }
.lang-btn:hover { background:rgba(102,252,241,0.2); box-shadow:0 0 15px rgba(102,252,241,0.3); }
.lang-content { display:none; position:absolute; top:100%; right:0; background:rgba(20,25,35,0.95); border:1px solid var(--border); border-radius:12px; overflow:hidden; margin-top:8px; flex-direction:column; min-width:120px; box-shadow:0 10px 20px rgba(0,0,0,0.5); backdrop-filter:blur(10px); }
.lang-dropdown:hover .lang-content { display:flex; animation:fadeIn 0.2s; }
.lang-item { padding:10px 15px; color:white; cursor:pointer; font-size:14px; font-weight:bold; transition:0.2s; text-align:left; border-bottom:1px solid #333; }
.lang-item:last-child { border:none; }
.lang-item:hover { background:var(--primary); color:#0b0c10; }

#sidebar{width:80px;background:rgba(11,12,16,0.6);backdrop-filter:blur(12px);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:20px 0;z-index:100}
.nav-btn{width:50px;height:50px;border-radius:14px;border:none;background:transparent;color:#888;font-size:24px;margin-bottom:15px;cursor:pointer;transition:0.3s;position:relative; flex-shrink:0;}
.nav-btn.active{background:rgba(102,252,241,0.15);color:var(--primary);border:1px solid var(--border);box-shadow:0 0 15px rgba(102,252,241,0.2);transform:scale(1.05)}
.my-avatar-mini{width:45px;height:45px;border-radius:50%;object-fit:cover;border:2px solid var(--border); background:#111;}
.nav-badge { position:absolute; top:-2px; right:-2px; background:#ff5555; color:white; font-size:11px; font-weight:bold; padding:2px 6px; border-radius:10px; display:none; z-index:10; box-shadow:0 0 5px #ff5555; border:2px solid var(--dark-bg); }

#content-area{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden}
.view{display:none;flex:1;flex-direction:column;overflow-y:auto;height:100%;width:100%;padding-bottom:20px}
.view.active{display:flex;animation:fadeIn 0.3s ease-out}

.rank-badge{font-size: 9px; font-weight: bold; text-transform: uppercase; background: rgba(0,0,0,0.6); padding: 2px 6px; border-radius: 6px; border: 1px solid; display: inline-block; margin-left: 4px; vertical-align: middle; line-height:1;}
.special-badge{font-size: 9px; color: #0b0c10; font-weight: bold; text-transform: uppercase; background: linear-gradient(45deg, #FFD700, #ff8c00); padding: 2px 6px; border-radius: 6px; display: inline-block; margin-left: 4px; vertical-align: middle; box-shadow: 0 0 5px rgba(255,165,0,0.5); line-height:1;}

#floating-call-btn { position:fixed; bottom:40px; right:40px; width:70px; height:70px; border-radius:50%; background: linear-gradient(135deg, #1f2833, #0b0c10); color:var(--primary); font-size:35px; cursor:pointer; display:none; z-index:9998; align-items:center; justify-content:center; box-shadow: 0 0 20px rgba(102,252,241,0.5), inset 0 0 10px rgba(102,252,241,0.2); border: 2px solid var(--primary); animation: radar-glow 2s infinite; transition: 0.3s transform; }
#floating-call-btn:hover { transform:scale(1.1); box-shadow: 0 0 30px rgba(102,252,241,0.8); }
@keyframes radar-glow { 0% { box-shadow: 0 0 0 0 rgba(102,252,241,0.6); } 70% { box-shadow: 0 0 0 25px rgba(102,252,241,0); } 100% { box-shadow: 0 0 0 0 rgba(102,252,241,0); } }

#expanded-call-panel { display:none; position:fixed; bottom:125px; right:40px; width:320px; background-color: rgba(15, 20, 25, 0.95); background-size: cover; background-position: center; border:1px solid var(--primary); border-radius:20px; z-index:9999; padding:20px; flex-direction:column; box-shadow:0 20px 60px rgba(0,0,0,0.9), 0 0 20px rgba(102,252,241,0.2); animation:scaleUp 0.3s ease-out; overflow:hidden;}
#expanded-call-panel::before { content: ''; position: absolute; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(10px); z-index: 0; }
#expanded-call-panel > * { position: relative; z-index: 1; }

.call-participant-card { display:flex; align-items:center; gap:12px; margin-bottom:10px; background:rgba(255,255,255,0.05); padding:10px 15px; border-radius:12px; border:1px solid rgba(255,255,255,0.1); backdrop-filter:blur(5px); transition:0.3s;}
.call-participant-card:hover { background:rgba(255,255,255,0.1); border-color:var(--primary); }
.call-avatar { width:40px; height:40px; border-radius:50%; border:2px solid var(--primary); object-fit:cover; }
.call-name { flex:1; color:white; font-weight:bold; font-size:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.call-kick-btn { background:rgba(255,85,85,0.1); border:1px solid rgba(255,85,85,0.4); color:#ff5555; padding:6px; border-radius:8px; cursor:pointer; transition:0.2s; display:flex; align-items:center; justify-content:center; }

.vol-slider { width: 70px; accent-color: var(--primary); height:4px; background:#333; border-radius:2px; outline:none; cursor:pointer;}
.call-btn-circle { background:#1f2833; color:white; border:1px solid #444; border-radius:50%; width:45px; height:45px; font-size:18px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:0.2s; }
.call-btn-circle:hover { transform:scale(1.1); border-color:var(--primary); color:var(--primary); box-shadow:0 0 15px rgba(102,252,241,0.3); }
.call-btn-circle.muted { background:rgba(255,85,85,0.1); color:#ff5555; border-color:#ff5555; box-shadow:0 0 15px rgba(255,85,85,0.4); }
.call-btn-hangup { background:linear-gradient(135deg, #ff5555, #cc0000); color:white; border:none; border-radius:30px; width:100%; padding:14px; font-size:15px; font-family:'Rajdhani'; font-weight:bold; letter-spacing:1px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:0.2s; box-shadow:0 8px 20px rgba(255,85,85,0.4); margin-top:10px; text-transform:uppercase;}

.admin-action-wrap { display:flex; gap:5px; margin-left:auto; flex-shrink:0; }
.admin-action-btn { background:rgba(255,255,255,0.1); border:1px solid #555; color:white; padding:4px 8px; border-radius:8px; cursor:pointer; transition:0.2s; font-size:12px; }
.admin-action-btn:hover { transform:scale(1.1); box-shadow:0 0 10px rgba(255,255,255,0.2); }
.admin-action-btn.danger { color:#ff5555; border-color:rgba(255,85,85,0.5); }
.admin-action-btn.success { color:#2ecc71; border-color:rgba(46,204,113,0.5); }

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

.chat-input-area, .comment-input-area { display: flex; gap: 8px; align-items: center; border-top: 1px solid var(--border); flex-wrap: nowrap; width: 100%; box-sizing: border-box; padding:15px; background:rgba(11,12,16,0.95); flex-shrink:0;}
.chat-msg, .comment-inp { flex: 1; min-width: 0; background: rgba(255,255,255,0.05); border: 1px solid #444; border-radius: 20px; padding: 12px 15px; color: white; outline: none; font-size: 14px; transition:0.3s;}
.chat-msg:focus, .comment-inp:focus { border-color: var(--primary); }
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
.msg-time { display:block; font-size:10px; color:rgba(255,255,255,0.5); text-align:right; margin-top:4px; font-family:'Inter', sans-serif;}
.msg-deleted { font-style: italic; color: #ffaa00; background: rgba(255,170,0,0.1); padding: 5px 10px; border-radius: 8px; font-size: 13px; display: inline-block; border: 1px dashed rgba(255,170,0,0.5); }

.chat-box-centered { width: 100%; max-width: 600px; height: 85vh; margin: auto; background: var(--card-bg); border-radius: 16px; border: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }
.comm-card { background:rgba(0,0,0,0.4); border:1px solid #444; border-radius:16px; padding:20px 15px; text-align:center; cursor:pointer; transition:0.3s; display:flex; flex-direction:column; align-items:center; box-shadow:0 4px 15px rgba(0,0,0,0.2); position:relative; overflow:hidden;}
.comm-card:hover { border-color:var(--primary); transform:translateY(-5px); }
.comm-avatar { width:70px; height:70px; border-radius:20px; object-fit:cover; margin-bottom:12px; border:2px solid #555; position:relative; z-index:2; }
.comm-layout { flex-direction:column; height:100%; background:var(--dark-bg); overflow:hidden;}

.comm-topbar { padding: 15px 20px; background: rgba(11,12,16,0.95); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 20px rgba(0,0,0,0.5); z-index: 10; gap:10px; position:relative; background-size: cover; background-position: center; }
.comm-topbar::after { content: ''; position: absolute; inset: 0; background: rgba(0,0,0,0.7); z-index: 1; }
.comm-topbar > * { position: relative; z-index: 2; }
#active-comm-name { font-size: 22px; text-transform: uppercase; color: var(--primary); font-family: 'Rajdhani', sans-serif; font-weight: bold; letter-spacing: 2px; flex:1; text-align:center; padding: 5px 10px; text-shadow: 0 0 10px rgba(102,252,241,0.3), 0 2px 5px rgba(0,0,0,1); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}

.comm-channels-bar { padding: 12px 15px; background: #0b0c10; display: flex; gap: 10px; overflow-x: auto; border-bottom: 1px solid rgba(255,255,255,0.05); }
.channel-btn { background: rgba(255,255,255,0.05); border: 1px solid #333; color: #fff; padding: 8px 18px; border-radius: 20px; cursor: pointer; white-space: nowrap; font-weight: bold; font-family: 'Inter', sans-serif; font-size: 13px; transition: 0.3s; flex-shrink:0; background-size: cover; background-position: center; position: relative; overflow:hidden; display:flex; align-items:center; gap:5px;}
.channel-btn.active { border-color: var(--primary); box-shadow: 0 0 12px rgba(102,252,241,0.6); transform:scale(1.05); color:var(--primary); }

/* CORREÇÃO DO PERFIL RESPONSIVO */
.profile-header-container{position:relative;width:100%;height:180px;margin-bottom:70px}
.profile-cover{width:100%;height:100%;object-fit:cover;opacity:0.9;mask-image:linear-gradient(to bottom,black 60%,transparent 100%); background:#111;}
.profile-pic-lg-wrap { position:absolute; bottom:-60px; left:50%; transform:translateX(-50%); z-index: 10; width:120px; height:120px;}
.profile-pic-lg { width:100%; height:100%; border-radius:50%; object-fit:cover; border:4px solid var(--dark-bg); box-shadow:0 0 20px rgba(102,252,241,0.3); cursor:pointer; background:#1f2833; display:block; }

.glass-btn { background: rgba(102, 252, 241, 0.08); border: 1px solid rgba(102, 252, 241, 0.3); color: var(--primary); padding: 12px 20px; border-radius: 12px; cursor: pointer; font-weight: bold; font-family: 'Inter', sans-serif; transition: 0.3s; text-transform: uppercase; font-size: 13px; letter-spacing: 1px; flex: 1; text-align:center;}
.glass-btn:hover { background: rgba(102, 252, 241, 0.15); box-shadow: 0 0 10px rgba(102,252,241,0.2); }
.danger-btn { color: #ff5555 !important; border-color: rgba(255, 85, 85, 0.3) !important; background: rgba(255, 85, 85, 0.08) !important; margin-top: 20px; width: 100%; }

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
    #floating-call-btn { bottom: 80px; right: 20px; width:60px; height:60px; font-size:30px; }
    #expanded-call-panel { bottom: 150px; right: 20px; width: 90%; max-width: 320px; }
    .profile-header-container { height: 140px; margin-bottom: 50px; }
    .profile-pic-lg-wrap { width: 100px; height: 100px; bottom: -50px; }
}
</style>
</head>
<body>
<div id="toast">Notificação</div>

<div id="modal-incoming-call" class="modal hidden">
    <div class="modal-box" style="border-color: #2ecc71;">
        <h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;" data-i18n="incoming_call">CHAMADA RECEBIDA</h2>
        <img id="incoming-call-av" src="" style="width:80px;height:80px;border-radius:50%;border:3px solid #2ecc71; margin:10px auto; display:block; object-fit:cover;">
        <h3 id="incoming-call-name" style="color:white; margin:10px 0;">...</h3>
        <p style="color:#aaa; font-size:14px; margin-bottom:20px;">está chamando...</p>
        <div style="display:flex; gap:10px;">
            <button onclick="acceptCall()" class="btn-main" style="background:#2ecc71; color:white; margin-top:0;">ACEITAR</button>
            <button onclick="declineCall()" class="btn-main" style="background:#ff5555; color:white; margin-top:0;">RECUSAR</button>
        </div>
    </div>
</div>

<div class="lang-dropdown">
    <div class="lang-btn" id="lang-btn-current">🌍 Idioma</div>
    <div class="lang-content">
        <div class="lang-item" onclick="changeLanguage('pt')">🇧🇷 Português</div>
        <div class="lang-item" onclick="changeLanguage('en')">🇺🇸 English</div>
        <div class="lang-item" onclick="changeLanguage('es')">🇪🇸 Español</div>
    </div>
</div>

<div id="emoji-picker" style="position:absolute;bottom:80px;right:10px;width:90%;max-width:320px;background:rgba(20,25,35,0.95);border:1px solid var(--border);border-radius:15px;display:none;flex-direction:column;z-index:10001;box-shadow:0 0 25px rgba(0,0,0,0.8);backdrop-filter:blur(10px)">
    <div style="padding:10px 15px;display:flex;justify-content:space-between;border-bottom:1px solid #333">
        <span style="color:var(--primary);font-weight:bold;font-family:'Rajdhani'">EMOJIS</span>
        <span onclick="toggleEmoji(true)" style="color:#ff5555;cursor:pointer;font-weight:bold">✕</span>
    </div>
    <div id="emoji-grid" style="display:grid;grid-template-columns:repeat(7,1fr);gap:5px;padding:10px;max-height:220px;overflow-y:auto"></div>
</div>

<div id="floating-call-btn" onclick="toggleCallPanel()">📞</div>
<div id="expanded-call-panel">
    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.2); padding-bottom:15px; margin-bottom:15px;">
        <span style="color:#2ecc71; font-weight:bold; font-family:'Inter'; text-shadow:0 0 5px #2ecc71;">
            <span id="call-hud-status-icon" style="animation:pulse 1s infinite; display:inline-block;">🔴</span> 
            <span id="call-hud-status">AGUARDANDO...</span>
        </span>
        <span id="call-hud-time" style="color:white; font-family:'Rajdhani'; font-size:22px; font-weight:bold; text-shadow:0 0 10px rgba(255,255,255,0.5);">00:00</span>
    </div>
    
    <div id="call-active-profile" style="text-align:center; margin-bottom:15px; display:none;">
        <img id="call-active-avatar" src="" style="width:80px; height:80px; border-radius:50%; border:2px solid var(--primary); object-fit:cover; margin:0 auto; display:block; box-shadow:0 0 15px rgba(102,252,241,0.5);">
        <div id="call-active-name" style="color:white; font-weight:bold; margin-top:10px; font-size:18px; font-family:'Rajdhani'; letter-spacing:1px;"></div>
    </div>

    <div id="call-users-list" style="max-height:150px; overflow-y:auto; margin-bottom:15px; padding-right:5px;"></div>
    
    <div id="call-bg-action" style="text-align:center; margin-bottom:15px; display:none;">
        <input type="file" id="call-bg-file" style="display:none;" accept="image/*" onchange="uploadCallBg(this)">
        <button class="glass-btn" style="padding:8px 15px; font-size:11px; width:100%;" onclick="document.getElementById('call-bg-file').click()">🖼️ TROCAR FUNDO DA CALL</button>
    </div>

    <div style="display:flex; gap:15px; justify-content:center;">
        <button id="btn-mute-call" class="call-btn-circle" onclick="toggleMuteCall()" title="Mutar Microfone">🎤</button>
        <button class="call-btn-circle" onclick="toggleCallPanel()" title="Minimizar">🔽</button>
    </div>
    <button class="call-btn-hangup" onclick="leaveCall()" title="Desligar">📞 CANCELAR</button>
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

<div id="modal-delete" class="modal hidden">
    <div class="modal-box" style="border-color: rgba(255, 85, 85, 0.3);">
        <h2 style="color:#ff5555; font-family:'Rajdhani'; margin-top:0;" data-i18n="confirm_action">CONFIRMAR AÇÃO</h2>
        <p style="color:#ccc; margin: 15px 0; font-size:15px;" data-i18n="confirm_del">Tem certeza que deseja apagar isto?</p>
        <div style="display:flex; gap:10px; margin-top:20px;">
            <button id="btn-confirm-delete" class="btn-main" style="background:#ff5555; color:white; margin-top:0;" data-i18n="delete">APAGAR</button>
            <button onclick="document.getElementById('modal-delete').classList.add('hidden')" class="btn-main" style="background:transparent; border:1px solid #444; color:#888; margin-top:0;" data-i18n="cancel">CANCELAR</button>
        </div>
    </div>
</div>

<div id="modal-create-comm" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;" data-i18n="new_base">NOVA BASE OFICIAL</h2>
        <input type="file" id="comm-avatar-upload" class="inp" accept="image/*" title="Avatar da Base">
        <p style="color:#aaa;font-size:11px;text-align:left;margin:0 0 5px 5px;" data-i18n="base_banner_opt">Banner da Base (Opcional):</p>
        <input type="file" id="comm-banner-upload" class="inp" accept="image/*" title="Banner da Base">
        <input id="new-comm-name" class="inp" placeholder="Nome" data-i18n="base_name">
        <input id="new-comm-desc" class="inp" placeholder="Desc" data-i18n="base_desc">
        <select id="new-comm-priv" class="styled-select">
            <option value="0" data-i18n="pub_base">🌍 Pública</option>
            <option value="1" data-i18n="priv_base">🔒 Privada</option>
        </select>
        <button onclick="submitCreateComm(event)" class="btn-main" data-i18n="establish">ESTABELECER</button>
        <button onclick="document.getElementById('modal-create-comm').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">CANCELAR</button>
    </div>
</div>

<div id="modal-edit-comm" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;" data-i18n="edit_base">EDITAR BASE</h2>
        <label style="color:#aaa;display:block;margin-top:10px;font-size:12px;" data-i18n="base_avatar">Novo Avatar</label>
        <input type="file" id="edit-comm-avatar" class="inp" accept="image/*">
        <label style="color:#aaa;display:block;margin-top:10px;font-size:12px;" data-i18n="base_banner">Novo Banner</label>
        <input type="file" id="edit-comm-banner" class="inp" accept="image/*">
        <button id="btn-save-comm" onclick="submitEditComm()" class="btn-main" data-i18n="save">SALVAR</button>
        <button onclick="document.getElementById('modal-edit-comm').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">CANCELAR</button>
    </div>
</div>

<div id="modal-create-channel" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;" data-i18n="new_channel">NOVO CANAL</h2>
        <input id="new-ch-name" class="inp" placeholder="Nome" data-i18n="channel_name">
        <p style="color:#aaa;font-size:11px;text-align:left;margin:0 0 5px 5px;" data-i18n="ch_banner_opt">Banner do Canal:</p>
        <input type="file" id="new-ch-banner" class="inp" accept="image/*" title="Banner do Canal">
        <select id="new-ch-type" class="styled-select">
            <option value="livre" data-i18n="ch_free">💬 Livre</option>
            <option value="text" data-i18n="ch_text">📝 Só Texto</option>
            <option value="media" data-i18n="ch_media">🎬 Só Mídia</option>
            <option value="voice" data-i18n="voice_channel">🎙️ Canal de Voz</option>
        </select>
        <select id="new-ch-priv" class="styled-select">
            <option value="0" data-i18n="ch_pub">🌍 Público</option>
            <option value="1" data-i18n="ch_priv">🔒 Privado</option>
        </select>
        <button id="btn-create-ch" onclick="submitCreateChannel()" class="btn-main" data-i18n="create_channel">CRIAR CANAL</button>
        <button onclick="document.getElementById('modal-create-channel').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">CANCELAR</button>
    </div>
</div>

<div id="modal-edit-channel" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;">EDITAR CANAL</h2>
        <input id="edit-ch-name" class="inp" placeholder="Novo Nome">
        <p style="color:#aaa;font-size:11px;text-align:left;margin:0 0 5px 5px;">Novo Banner:</p>
        <input type="file" id="edit-ch-banner" class="inp" accept="image/*">
        <select id="edit-ch-type" class="styled-select">
            <option value="livre">💬 Livre</option><option value="text">📝 Só Texto</option>
            <option value="media">🎬 Só Mídia</option><option value="voice">🎙️ Canal de Voz</option>
        </select>
        <select id="edit-ch-priv" class="styled-select">
            <option value="0">🌍 Público</option><option value="1">🔒 Privado</option>
        </select>
        <button id="btn-edit-ch" onclick="submitEditChannel()" class="btn-main" data-i18n="save">SALVAR</button>
        <button onclick="window.deleteTarget={type:'channel', id:window.currentEditChannelId}; document.getElementById('modal-delete').classList.remove('hidden');" class="btn-main" style="background:#ff5555; color:white; margin-top:10px;">DELETAR CANAL</button>
        <button onclick="document.getElementById('modal-edit-channel').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">CANCELAR</button>
    </div>
</div>

<div id="modal-create-group" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:var(--primary); font-family:'Rajdhani'; margin-top:0;" data-i18n="new_squad">NOVO ESQUADRÃO</h2>
        <input id="new-group-name" class="inp" placeholder="Grupo" data-i18n="group_name">
        <p style="color:#888;font-size:12px;text-align:left;margin-bottom:5px;" data-i18n="select_allies">Selecione os aliados:</p>
        <div id="group-friends-list" style="max-height:150px; overflow-y:auto; text-align:left; margin-bottom:15px; background:rgba(0,0,0,0.3); padding:10px; border-radius:10px;"></div>
        <div style="display:flex; gap:10px;">
            <button onclick="submitCreateGroup()" class="btn-main" style="margin-top:0;" data-i18n="create">CRIAR</button>
            <button onclick="document.getElementById('modal-create-group').classList.add('hidden')" class="btn-main" style="background:transparent; border:1px solid #444; color:#888; margin-top:0;" data-i18n="cancel">CANCELAR</button>
        </div>
    </div>
</div>

<div id="modal-upload" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:white" data-i18n="new_post">NOVO POST</h2>
        <input type="file" id="file-upload" class="inp" accept="image/*,video/*" style="margin-bottom: 5px;">
        <span style="color:#ffaa00; font-size:11px; display:block; text-align:left; padding-left:5px; font-weight:bold;">⚠️ Max 100MB</span>
        <div style="display:flex;gap:5px;align-items:center;margin-bottom:10px;margin-top:10px">
            <input type="text" id="caption-upload" class="inp" placeholder="Legenda..." data-i18n="caption_placeholder" style="margin:0">
            <button type="button" class="icon-btn" onclick="openEmoji('caption-upload')">😀</button>
        </div>
        <div id="upload-progress" style="display:none;background:#333;height:6px;border-radius:3px;margin-top:10px;overflow:hidden">
            <div id="progress-bar" style="width:0%;height:100%;background:var(--primary);transition:width 0.2s"></div>
        </div>
        <div id="progress-text" style="color:var(--primary);font-size:12px;margin-top:5px;display:none;font-weight:bold">0%</div>
        <button id="btn-pub" onclick="submitPost()" class="btn-main" data-i18n="publish">PUBLICAR (+50 XP)</button>
        <button onclick="closeUpload()" class="btn-link" style="color:#888;display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">CANCELAR</button>
    </div>
</div>

<div id="modal-profile" class="modal hidden">
    <div class="modal-box">
        <h2 style="color:var(--primary)" data-i18n="edit_profile">EDITAR PERFIL</h2>
        <label style="color:#aaa;display:block;margin-top:10px;font-size:12px;">Avatar</label>
        <input type="file" id="avatar-upload" class="inp" accept="image/*">
        <label style="color:#aaa;display:block;margin-top:10px;font-size:12px;">Cover</label>
        <input type="file" id="cover-upload" class="inp" accept="image/*">
        <input id="bio-update" class="inp" placeholder="Bio" data-i18n="bio_placeholder">
        <button id="btn-save-profile" onclick="updateProfile()" class="btn-main" data-i18n="save">SALVAR</button>
        <button onclick="document.getElementById('modal-profile').classList.add('hidden')" class="btn-link" style="display:block;width:100%;border:1px solid #444;border-radius:10px;padding:12px;text-decoration:none" data-i18n="cancel">FECHAR</button>
    </div>
</div>

<div id="app">
    <div id="sidebar">
        <button id="nav-profile-btn" class="nav-btn" onclick="goView('profile', this)" style="position:relative;">
            <img id="nav-avatar" src="" class="my-avatar-mini" onerror="this.src='https://ui-avatars.com/api/?name=User&background=111&color=66fcf1'">
            <div id="profile-badge" class="nav-badge"></div>
        </button>
        <button class="nav-btn" onclick="goView('inbox', this)" style="position:relative;">📩<div id="inbox-badge" class="nav-badge"></div></button>
        <button class="nav-btn" onclick="goView('feed', this)">🎬</button>
        <button class="nav-btn" onclick="goView('mycomms', this)" style="position:relative;">🛡️<div id="bases-badge" class="nav-badge"></div></button>
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
                    <button onclick="initCall(currentChatType, currentChatId)" class="glass-btn btn-call-header" style="flex:none; padding:8px 15px; border-color:#2ecc71; color:#2ecc71;">📞 CALL</button>
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
            <div class="comm-topbar" id="comm-header">
                <button onclick="closeComm()" style="background:rgba(0,0,0,0.5); border:1px solid #444; border-radius:8px; padding:5px 10px; color:white; font-size:18px; cursor:pointer;">⬅</button>
                <div id="active-comm-name">NOME DA BASE</div>
                <button onclick="showCommInfo()" class="glass-btn" style="padding:6px 12px; margin:0; flex:none; background:rgba(255,255,255,0.1); color:white; border-color:#555;">ℹ️ INFO</button>
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
            
            <div id="comm-info-area" style="display:none; flex:1; overflow-y:auto; padding-bottom:30px; align-items:flex-start; justify-content:center; flex-direction:row; background: var(--dark-bg);">
                <div style="background:var(--card-bg); border:1px solid var(--border); border-radius:16px; width:100%; max-width:600px; margin-top:20px; overflow:hidden; box-shadow:0 15px 35px rgba(0,0,0,0.5);">
                    <div id="c-info-banner" style="width:100%; height:160px; background-size:cover; background-position:center; position:relative; background-color:#111; border-bottom:1px solid #333;">
                        <div style="position:absolute; bottom:-40px; left:25px;">
                            <img id="c-info-av" src="" style="width:100px; height:100px; border-radius:24px; object-fit:cover; border:4px solid var(--card-bg); background:#0b0c10; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
                        </div>
                    </div>
                    <div style="padding: 50px 25px 25px 25px;">
                        <h2 id="c-info-name" style="color:white; margin:0; font-family:'Rajdhani'; font-size:32px; letter-spacing:1px; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">...</h2>
                        <p id="c-info-desc" style="color:#aaa; font-size:14px; margin:10px 0 25px 0; line-height:1.5;">...</p>
                        
                        <div id="c-info-admin-btn" style="margin-bottom:20px; display:flex; flex-direction:column; gap:10px;"></div>
                        
                        <div style="background:rgba(0,0,0,0.3); border-radius:12px; padding:20px; text-align:left; border:1px solid rgba(255,255,255,0.05);">
                            <h3 style="color:var(--primary); margin:0 0 15px 0; border-bottom:1px solid rgba(102,252,241,0.2); padding-bottom:8px; font-size:16px; font-family:'Rajdhani'; letter-spacing:1px; text-transform:uppercase;" data-i18n="base_members">Membros da Base</h3>
                            <div id="c-info-members" style="display:flex; flex-direction:column; gap:8px; max-height:300px; overflow-y:auto; padding-right:5px;"></div>
                        </div>
                        
                        <div id="c-info-requests-container" style="display:none; width:100%; margin-top:20px; background:rgba(0,0,0,0.3); border-radius:12px; padding:20px; text-align:left; border:1px solid rgba(255,165,0,0.2);">
                            <h3 style="color:orange; margin:0 0 15px 0; border-bottom:1px solid rgba(255,165,0,0.2); padding-bottom:8px; font-size:16px; font-family:'Rajdhani'; letter-spacing:1px; text-transform:uppercase;" data-i18n="entry_requests">Solicitações de Entrada</h3>
                            <div id="c-info-requests" style="display:flex; flex-direction:column; gap:8px;"></div>
                        </div>
                        
                        <div id="c-info-destroy-btn" style="margin-top:25px; display:flex; flex-direction:column; gap:10px;"></div>
                    </div>
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
                <div id="pub-actions" style="margin-bottom:20px; display:flex; justify-content:center; flex-wrap:wrap; align-items:center; gap:10px;"></div>
                <div id="pub-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:2px;max-width:500px;margin:0 auto;"></div>
            </div>
        </div>
    </div>
</div>

<script>
window.deleteTarget = {type: null, id: null};

// CLOUDINARY - NÃO USADO DIRETAMENTE (UPLOAD VIA BACKEND)
const T = {
    'pt': {
        'login_title': 'FOR GLORY', 'login': 'ENTRAR', 'create_acc': 'Criar Conta', 'forgot': 'Esqueci Senha',
        'codename': 'CODINOME', 'password': 'SENHA', 'new_user': 'NOVO USUÁRIO', 'email_real': 'EMAIL (Real)', 'enlist': 'ALISTAR-SE', 'back': 'Voltar',
        'recover': 'RECUPERAR ACESSO', 'reg_email': 'SEU EMAIL CADASTRADO', 'send_link': 'ENVIAR LINK', 'new_pass_title': 'NOVA SENHA', 'new_pass': 'NOVA SENHA', 'save_pass': 'SALVAR SENHA',
        'confirm_action': 'CONFIRMAR AÇÃO', 'confirm_del': 'Tem certeza que deseja apagar isto?', 'delete': 'APAGAR', 'cancel': 'CANCELAR',
        'new_base': 'NOVA BASE OFICIAL', 'base_name': 'Nome da Base', 'base_desc': 'Descrição da Base', 'pub_base': '🌍 Pública', 'priv_base': '🔒 Privada', 'establish': 'ESTABELECER',
        'new_channel': 'NOVO CANAL', 'channel_name': 'Nome do Canal', 'ch_free': '💬 Livre', 'ch_text': '📝 Só Texto', 'ch_media': '🎬 Só Mídia', 'voice_channel': '🎙️ Canal de Voz', 'ch_pub': '🌍 Público', 'ch_priv': '🔒 Privado (Só Admins)', 'create_channel': 'CRIAR CANAL',
        'new_squad': 'NOVO ESQUADRÃO', 'group_name': 'Nome do Grupo', 'select_allies': 'Selecione os aliados:', 'create': 'CRIAR',
        'new_post': 'NOVO POST', 'caption_placeholder': 'Legenda...', 'publish': 'PUBLICAR (+50 XP)',
        'edit_profile': 'EDITAR PERFIL', 'bio_placeholder': 'Escreva sua Bio...', 'save': 'SALVAR',
        'edit_base': 'EDIT BASE', 'base_avatar': 'Novo Avatar', 'base_banner': 'Novo Banner',
        'stealth_on': '🕵️ MODO FURTIVO: ATIVADO', 'stealth_off': '🟢 MODO FURTIVO: DESATIVADO', 'search_soldier': 'Buscar Soldado...', 'requests': '📩 Solicitações', 'friends': '👥 Amigos', 'disconnect': 'DESCONECTAR',
        'private_msgs': 'MENSAGENS PRIVADAS', 'group_x1': '+ GRUPO X1', 'my_bases': '🛡️ MINHAS BASES', 'create_base': '+ CRIAR BASE',
        'explore_bases': '🌐 EXPLORAR BASES', 'search_base': 'Buscar Base...', 'my_history': '🕒 MEU HISTÓRICO',
        'msg_placeholder': 'Mensagem secreta...', 'base_msg_placeholder': 'Mensagem para a base...',
        'at': 'às', 'deleted_msg': '🚫 Apagada', 'audio_proc': 'Processando...',
        'recording': '🔴 Gravando...', 'click_to_send': '(Clique p/ enviar)',
        'empty_box': 'Sua caixa está vazia. Recrute aliados!', 'direct_msg': 'Mensagem Direta', 'squad': '👥 Esquadrão',
        'no_bases': 'Você ainda não tem bases.', 'no_bases_found': 'Nenhuma base encontrada.', 'no_history': 'Nenhuma missão registrada no Feed.',
        'request_join': '🔒 SOLICITAR', 'enter': '🌍 ENTRAR', 'ally': '✔ Aliado', 'sent': 'Enviado', 'accept_ally': 'Aceitar Aliado', 'recruit_ally': 'Recrutar Aliado',
        'creator': '👑 CRIADOR', 'admin': '🛡️ ADMIN', 'member': 'MEMBRO', 'promote': 'Promover', 'demote': 'Rebaixar', 'kick': 'Expulsar',
        'base_members': 'Membros da Base', 'entry_requests': 'Solicitações de Entrada', 'destroy_base': 'DESTRUIR BASE',
        'media_only': 'Canal restrito para mídia 📎', 'in_call': 'EM CHAMADA', 'join_call': 'ENTRAR NA CALL', 'incoming_call': 'CHAMADA RECEBIDA',
        'progression': 'PROGRESSO MILITAR (XP)', 'medals': '🏆 SALA DE TROFÉUS', 'base_banner_opt': 'Banner da Base (Opcional):', 'ch_banner_opt': 'Banner do Canal (Opcional):',
        'no_trophies': 'Soldado sem troféus'
    },
    'en': {
        'login_title': 'FOR GLORY', 'login': 'LOGIN', 'create_acc': 'Create Account', 'forgot': 'Forgot Password',
        'codename': 'CODENAME', 'password': 'PASSWORD', 'new_user': 'NEW USER', 'email_real': 'EMAIL (Real)', 'enlist': 'ENLIST', 'back': 'Back',
        'recover': 'RECOVER ACCESS', 'reg_email': 'REGISTERED EMAIL', 'send_link': 'SEND LINK', 'new_pass_title': 'NEW PASSWORD', 'new_pass': 'NEW PASSWORD', 'save_pass': 'SAVE PASSWORD',
        'confirm_action': 'CONFIRM ACTION', 'confirm_del': 'Are you sure you want to delete this?', 'delete': 'DELETE', 'cancel': 'CANCEL',
        'new_base': 'NEW OFFICIAL BASE', 'base_name': 'Base Name', 'base_desc': 'Description', 'pub_base': '🌍 Public', 'priv_base': '🔒 Private', 'establish': 'ESTABLISH',
        'new_channel': 'NEW CHANNEL', 'channel_name': 'Channel Name', 'ch_free': '💬 Free', 'ch_text': '📝 Text Only', 'ch_media': '🎬 Media Only', 'voice_channel': '🎙️ Voice Channel', 'ch_pub': '🌍 Public', 'ch_priv': '🔒 Private', 'create_channel': 'CREATE CHANNEL',
        'new_squad': 'NEW SQUAD', 'group_name': 'Group Name', 'select_allies': 'Select allies:', 'create': 'CREATE',
        'new_post': 'NEW POST', 'caption_placeholder': 'Caption...', 'publish': 'PUBLISH (+50 XP)',
        'edit_profile': 'EDIT PROFILE', 'bio_placeholder': 'Write your Bio...', 'save': 'SAVE',
        'edit_base': 'EDIT BASE', 'base_avatar': 'New Avatar', 'base_banner': 'New Banner',
        'stealth_on': '🕵️ STEALTH MODE: ON', 'stealth_off': '🟢 STEALTH MODE: OFF', 'search_soldier': 'Search Soldier...', 'requests': '📩 Requests', 'friends': '👥 Friends', 'disconnect': 'LOGOUT',
        'private_msgs': 'PRIVATE MESSAGES', 'group_x1': '+ DM SQUAD', 'my_bases': '🛡️ MY BASES', 'create_base': '+ CREATE BASE',
        'explore_bases': '🌐 EXPLORE BASES', 'search_base': 'Search Base...', 'my_history': '🕒 MY HISTORY',
        'msg_placeholder': 'Secret message...', 'base_msg_placeholder': 'Message to base...',
        'at': 'at', 'deleted_msg': '🚫 Deleted', 'audio_proc': 'Processing...',
        'recording': '🔴 Recording...', 'click_to_send': '(Click to send)',
        'empty_box': 'Your inbox is empty. Recruit allies!', 'direct_msg': 'Direct Message', 'squad': '👥 Squad',
        'no_bases': 'You have no bases yet.', 'no_bases_found': 'No bases found.', 'no_history': 'No missions recorded.',
        'request_join': '🔒 REQUEST', 'enter': '🌍 ENTER', 'ally': '✔ Ally', 'sent': 'Sent', 'accept_ally': 'Accept Ally', 'recruit_ally': 'Recruit Ally',
        'creator': '👑 CREATOR', 'admin': '🛡️ ADMIN', 'member': 'MEMBER', 'promote': 'Promote', 'demote': 'Demote', 'kick': 'Kick',
        'base_members': 'Members', 'entry_requests': 'Requests', 'destroy_base': 'DESTROY BASE',
        'media_only': 'Media restricted channel 📎', 'in_call': 'IN CALL', 'join_call': 'JOIN CALL', 'incoming_call': 'INCOMING CALL',
        'progression': 'PROGRESSION (XP)', 'medals': '🏆 MEDALS', 'base_banner_opt': 'Base Banner (Optional):', 'ch_banner_opt': 'Channel Banner (Optional):',
        'no_trophies': 'Soldier without trophies'
    },
    'es': {
        'login_title': 'FOR GLORY', 'login': 'ENTRAR', 'create_acc': 'Crear Cuenta', 'forgot': 'Olvidé la Contraseña',
        'codename': 'NOMBRE EN CLAVE', 'password': 'CONTRASEÑA', 'new_user': 'NUEVO USUARIO', 'email_real': 'CORREO', 'enlist': 'ALISTARSE', 'back': 'Volver',
        'recover': 'RECUPERAR ACCESO', 'reg_email': 'CORREO REGISTRADO', 'send_link': 'ENVIAR ENLACE', 'new_pass_title': 'NUEVA CONTRASEÑA', 'new_pass': 'NUEVA CONTRASEÑA', 'save_pass': 'GUARDAR CONTRASEÑA',
        'confirm_action': 'CONFIRMAR ACCIÓN', 'confirm_del': '¿Seguro que quieres borrar esto?', 'delete': 'BORRAR', 'cancel': 'CANCELAR',
        'new_base': 'NUEVA BASE OFICIAL', 'base_name': 'Nombre de la Base', 'base_desc': 'Descripción', 'pub_base': '🌍 Pública', 'priv_base': '🔒 Privada', 'establish': 'ESTABLECER',
        'new_channel': 'NUEVO CANAL', 'channel_name': 'Nombre del Canal', 'ch_free': '💬 Libre', 'ch_text': '📝 Solo Texto', 'ch_media': '🎬 Solo Medios', 'voice_channel': '🎙️ Canal de Voz', 'ch_pub': '🌍 Público', 'ch_priv': '🔒 Privado', 'create_channel': 'CREAR CANAL',
        'new_squad': 'NUEVO ESCUADRÓN', 'group_name': 'Nombre del Grupo', 'select_allies': 'Selecciona aliados:', 'create': 'CREAR',
        'new_post': 'NUEVO POST', 'caption_placeholder': 'Leyenda...', 'publish': 'PUBLICAR (+50 XP)',
        'edit_profile': 'EDITAR PERFIL', 'bio_placeholder': 'Escribe tu Bio...', 'save': 'GUARDAR',
        'edit_base': 'EDITAR BASE', 'base_avatar': 'Nuevo Avatar', 'base_banner': 'Nuevo Banner',
        'stealth_on': '🕵️ MODO FURTIVO: ON', 'stealth_off': '🟢 MODO FURTIVO: OFF', 'search_soldier': 'Buscar Soldado...', 'requests': '📩 Solicitudes', 'friends': '👥 Amigos', 'disconnect': 'DESCONECTAR',
        'private_msgs': 'MENSAJES PRIVADOS', 'group_x1': '+ ESCUADRÓN DM', 'my_bases': '🛡️ MIS BASES', 'create_base': '+ CREAR BASE',
        'explore_bases': '🌐 EXPLORAR BASES', 'search_base': 'Buscar Base...', 'my_history': '🕒 MI HISTORIAL',
        'msg_placeholder': 'Mensaje secreto...', 'base_msg_placeholder': 'Mensaje para la base...',
        'at': 'a las', 'deleted_msg': '🚫 Borrado', 'audio_proc': 'Procesando...',
        'recording': '🔴 Grabando...', 'click_to_send': '(Click mic enviar)',
        'empty_box': 'Tu buzón está vacío. ¡Recluta aliados!', 'direct_msg': 'Mensaje Directo', 'squad': '👥 Escuadrón',
        'no_bases': 'Aún no tienes bases.', 'no_bases_found': 'No se encontraron bases.', 'no_history': 'No hay misiones.',
        'request_join': '🔒 SOLICITAR', 'enter': '🌍 ENTRAR', 'ally': '✔ Aliado', 'sent': 'Enviado', 'accept_ally': 'Aceptar Aliado', 'recruit_ally': 'Reclutar Aliado',
        'creator': '👑 CREADOR', 'admin': '🛡️ ADMIN', 'member': 'MIEMBRO', 'promote': 'Promover', 'demote': 'Degradar', 'kick': 'Expulsar',
        'base_members': 'Miembros de la Base', 'entry_requests': 'Solicitudes de Entrada', 'destroy_base': 'DESTRUIR BASE',
        'media_only': 'Canal restringido a medios 📎', 'in_call': 'EN LLAMADA', 'join_call': 'ENTRAR A LA CALL', 'incoming_call': 'LLAMADA ENTRANTE',
        'progression': 'PROGRESO MILITAR (XP)', 'medals': '🏆 SALA DE TROFEOS', 'base_banner_opt': 'Banner de Base (Opcional):', 'ch_banner_opt': 'Banner del Canal (Opcional):',
        'no_trophies': 'Soldado sin trofeos'
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
    let flag = window.currentLang === 'pt' ? '🇧🇷 PT' : (window.currentLang === 'es' ? '🇪🇸 ES' : '🇺🇸 EN');
    document.getElementById('lang-btn-current').innerHTML = `🌍 ${flag}`;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        let k = el.getAttribute('data-i18n');
        if(el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = t(k);
        else el.innerText = t(k);
    });
    checkToken(); // Garante que o token seja capturado ao carregar a página
});

var user=null, dmWS=null, commWS=null, globalWS=null, syncInterval=null, lastFeedHash="", currentEmojiTarget=null, currentChatId=null, currentChatType=null;
var activeCommId=null, activeChannelId=null;
window.onlineUsers = []; window.unreadData = {}; window.lastTotalUnread = 0;
let mediaRecorders = {}; let audioChunks = {}; let recordTimers = {}; let recordSeconds = {};

let rtc = { localAudioTrack: null, client: null, remoteUsers: {} };
let callDuration = 0, callInterval = null; 
window.pendingCallChannel = null; window.pendingCallType = null;
window.currentAgoraChannel = null;
window.isCaller = false;
window.callTargetId = null;

// Desbloqueador de Áudio Automático
document.body.addEventListener('click', () => {
    if(window.ringtone && window.ringtone.state === 'suspended') window.ringtone.resume();
}, { once: true });

window.ringtone = new Audio('https://actions.google.com/sounds/v1/alarms/phone_ringing.ogg'); window.ringtone.loop = true;
window.callingSound = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg'); window.callingSound.loop = true;
window.msgSound = new Audio('https://actions.google.com/sounds/v1/water/pop.ogg');

function safePlaySound(snd) {
    try { let p = snd.play(); if (p !== undefined) { p.catch(e => console.log("Áudio bloqueado", e)); } } catch(err){}
}
function stopSounds() {
    if(window.callingSound) { window.callingSound.pause(); window.callingSound.currentTime = 0; }
    if(window.ringtone) { window.ringtone.pause(); window.ringtone.currentTime = 0; }
}

async function authFetch(url, options = {}) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.reload();
        throw new Error('No token');
    }
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
    const res = await fetch(url, options);
    if (res.status === 401) {
        localStorage.removeItem('token');
        window.location.reload();
        throw new Error('Unauthorized');
    }
    return res;
}

async function initCall(typeParam, targetId) {
    if (rtc.client) return showToast("Você já está em uma call!");
    window.isCaller = true;
    window.callTargetId = targetId;
    window.pendingCallType = typeParam;
    
    let channelName = "";
    if (typeParam === 'dm' || typeParam === '1v1') { 
        channelName = `call_dm_${Math.min(user.id, targetId)}_${Math.max(user.id, targetId)}`; 
        await fetch('/call/ring/dm', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({caller_id:user.id, target_id:targetId, channel_name:channelName})});
    } else if (typeParam === 'group') { 
        channelName = `call_group_${targetId}`; 
        await fetch('/call/ring/group', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({caller_id:user.id, group_id:targetId, channel_name:channelName})});
    } else if (typeParam === 'channel' || typeParam === 'voice') { 
        channelName = `call_channel_${targetId}`; 
        connectToAgora(channelName, typeParam); 
        return;
    } else { return showToast("Alvo inválido."); }
    
    window.currentAgoraChannel = channelName;
    window.callHasConnected = false;
    
    document.getElementById('call-active-profile').style.display = 'none';
    document.getElementById('call-hud-status').innerText = "CHAMANDO...";
    document.getElementById('floating-call-btn').style.display = 'flex'; 
    showCallPanel();
    
    let bgAction = document.getElementById('call-bg-action');
    bgAction.style.display = 'block';
    
    safePlaySound(window.callingSound); 
}

function declineCall() { 
    document.getElementById('modal-incoming-call').classList.add('hidden'); 
    stopSounds();
    if (globalWS && globalWS.readyState === WebSocket.OPEN && window.pendingCallerId) {
        globalWS.send(`CALL_SIGNAL:${window.pendingCallerId}:rejected:${window.currentAgoraChannel}`);
    }
}

async function acceptCall() { 
    document.getElementById('modal-incoming-call').classList.add('hidden'); 
    stopSounds();
    window.callHasConnected = false; 
    window.isCaller = false;
    
    if (globalWS && globalWS.readyState === WebSocket.OPEN && window.pendingCallerId) {
        globalWS.send(`CALL_SIGNAL:${window.pendingCallerId}:accepted:${window.currentAgoraChannel}`);
    }
    
    await connectToAgora(window.currentAgoraChannel, window.pendingCallType); 
}

async function connectToAgora(channelName, typeParam) {
    window.currentAgoraChannel = channelName; 
    document.getElementById('call-active-profile').style.display = 'none';
    document.getElementById('call-hud-status').innerText = "CONECTANDO...";
    
    let bgAction = document.getElementById('call-bg-action');
    if (typeParam === 'dm' || typeParam === '1v1' || typeParam === 'group') { bgAction.style.display = 'block'; } 
    else { bgAction.style.display = window.currentCommIsAdmin ? 'block' : 'none'; }
    
    try {
        let res = await fetch('/agora-config'); let conf = await res.json();
        if (!conf.app_id || conf.app_id.trim() === "") { showToast("⚠️ ERRO: Central de Rádio Offline (Configure o AGORA_APP_ID no Render)"); leaveCall(); return; }
        if (rtc.client) { await rtc.client.leave(); }
        
        try {
            let rBg = await fetch(`/call/bg/call/${channelName}`); let resBg = await rBg.json();
            if(resBg && resBg.bg_url) { document.getElementById('expanded-call-panel').style.backgroundImage = `url('${resBg.bg_url}')`; } 
            else { document.getElementById('expanded-call-panel').style.backgroundImage = 'none'; }
        } catch(e) { console.error(e); }

        rtc.client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" }); rtc.remoteUsers = {};
        
        rtc.client.on("user-published", async (remoteUser, mediaType) => {
            window.callHasConnected = true; 
            stopSounds();
            await rtc.client.subscribe(remoteUser, mediaType);
            if (mediaType === "audio") { rtc.remoteUsers[remoteUser.uid] = remoteUser; remoteUser.audioTrack.play(); renderCallPanel(); }
        });
        
        rtc.client.on("user-unpublished", (remoteUser) => { 
            delete rtc.remoteUsers[remoteUser.uid]; renderCallPanel(); 
            if(Object.keys(rtc.remoteUsers).length === 0 && window.callHasConnected) { showToast("O aliado desligou."); leaveCall(); }
        });
        
        await rtc.client.join(conf.app_id, channelName, null, user.id);
        
        try { rtc.localAudioTrack = await AgoraRTC.createMicrophoneAudioTrack(); } 
        catch(micErr) { alert("⚠️ Sem Microfone! Autorize no navegador para usar o rádio."); leaveCall(); return; }
        
        await rtc.client.publish([rtc.localAudioTrack]);
        document.getElementById('floating-call-btn').style.display = 'flex'; showCallPanel();
        
    } catch(e) { console.error("Call Connect Error:", e); showToast("Falha ao conectar na Call."); leaveCall(); }
}

async function uploadCallBg(inputElem){
    if(!inputElem.files || !inputElem.files[0]) return;
    if(!window.currentAgoraChannel) { showToast("Aguarde conectar na call."); return; }
    showToast("Aplicando fundo tático...");
    try{
        let formData = new FormData();
        formData.append('file', inputElem.files[0]);
        let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); // sem Content-Type
        let data = await res.json();
        await authFetch('/call/bg/set', {
            method:'POST',
            body:JSON.stringify({ target_type: 'call', target_id: window.currentAgoraChannel, bg_url: data.secure_url })
        });
        document.getElementById('expanded-call-panel').style.backgroundImage=`url('${data.secure_url}')`;
        showToast("Fundo alterado!");
        if(globalWS && globalWS.readyState === WebSocket.OPEN) {
            globalWS.send("SYNC_BG:" + window.currentAgoraChannel + ":" + data.secure_url);
        }
    } catch(e) { console.error("Upload BG erro:", e); showToast("Erro na imagem."); }
}

async function leaveCall() { 
    stopSounds();
    if (rtc.localAudioTrack) { rtc.localAudioTrack.close(); } 
    if (rtc.client) { await rtc.client.leave(); } 
    
    if (window.isCaller && window.callTargetId && !window.callHasConnected && globalWS) {
        globalWS.send(`CALL_SIGNAL:${window.callTargetId}:cancelled:${window.currentAgoraChannel}`);
    }
    
    rtc.localAudioTrack = null; rtc.client = null; window.callHasConnected = false; window.currentAgoraChannel = null;
    window.isCaller = false; window.callTargetId = null;
    
    clearInterval(callInterval); 
    document.getElementById('expanded-call-panel').style.display = 'none'; 
    document.getElementById('floating-call-btn').style.display = 'none'; 
    let btn = document.getElementById('btn-mute-call'); btn.classList.remove('muted'); btn.innerHTML = '🎤'; isMicMuted = false;
}

window.callUsersCache = {};
async function renderCallPanel() {
    let list = document.getElementById('call-users-list'); list.innerHTML = ''; let count = 0;
    let isAdmin = window.currentCommIsAdmin || false;
    let lastUser = null;
    
    for(let uid in rtc.remoteUsers) {
        if (String(uid) === String(user.id)) continue;
        count++; 
        if(!window.callUsersCache[uid]) {
            try {
                let req = await fetch(`/users/basic/${uid}`);
                window.callUsersCache[uid] = await req.json();
            } catch(e) { console.error("Erro fetch user call:", e); window.callUsersCache[uid] = {name: "Aliado", avatar: "https://ui-avatars.com/api/?name=A"}; }
        }
        
        let uData = window.callUsersCache[uid];
        lastUser = uData;
        let kickBtn = isAdmin ? `<button class="call-kick-btn" onclick="kickFromCall(${uid})" title="Expulsar">❌</button>` : '';
        list.innerHTML += `<div class="call-participant-card"><img src="${uData.avatar}" class="call-avatar"><span class="call-name">${uData.name}</span>${kickBtn}<input type="range" min="0" max="100" value="100" class="vol-slider" oninput="changeRemoteVol(${uid}, this.value)"></div>`;
    }
    
    let profDiv = document.getElementById('call-active-profile');
    let st = document.getElementById('call-hud-status');
    
    if(count > 0 && lastUser) {
        profDiv.style.display = 'block';
        document.getElementById('call-active-avatar').src = lastUser.avatar;
        document.getElementById('call-active-name').innerText = lastUser.name;
        st.innerText = "EM CHAMADA";
        stopSounds();
    } else {
        profDiv.style.display = 'none';
        list.innerHTML = `<p style="color:#888; font-size:12px; text-align:center; margin:0;">Aguardando na escuta...</p>`;
        st.innerText = window.isCaller ? "CHAMANDO..." : "AGUARDANDO...";
    }
}

function changeRemoteVol(uid, val) { if(rtc.remoteUsers[uid] && rtc.remoteUsers[uid].audioTrack) { rtc.remoteUsers[uid].audioTrack.setVolume(parseInt(val)); } }

let isMicMuted = false;
async function toggleMuteCall() { 
    if(rtc.localAudioTrack) { 
        isMicMuted = !isMicMuted;
        await rtc.localAudioTrack.setMuted(isMicMuted); 
        let btn = document.getElementById('btn-mute-call'); 
        if(isMicMuted) { btn.classList.add('muted'); btn.innerHTML = '🔇'; } 
        else { btn.classList.remove('muted'); btn.innerHTML = '🎤'; } 
    } 
}

function toggleCallPanel() { let p = document.getElementById('expanded-call-panel'); p.style.display = (p.style.display === 'flex') ? 'none' : 'flex'; }
function showCallPanel() { document.getElementById('expanded-call-panel').style.display = 'flex'; callDuration = 0; document.getElementById('call-hud-time').innerText = "00:00"; clearInterval(callInterval); callInterval = setInterval(() => { callDuration++; let m = String(Math.floor(callDuration / 60)).padStart(2, '0'); let s = String(callDuration % 60).padStart(2, '0'); document.getElementById('call-hud-time').innerText = `${m}:${s}`; }, 1000); renderCallPanel(); }
function kickFromCall(targetUid) { if(confirm("Expulsar soldado da ligação?")) { if(globalWS && globalWS.readyState === WebSocket.OPEN) { globalWS.send("KICK_CALL:" + targetUid); } } }

function showToast(m){ let x=document.getElementById("toast"); x.innerText=m; x.className="show"; setTimeout(()=>{x.className=""},5000); }
function toggleAuth(m){ ['login','register','forgot','reset'].forEach(f=>document.getElementById(f+'-form').classList.add('hidden')); document.getElementById(m+'-form').classList.remove('hidden'); }
async function doLogin() {
    alert('função doLogin executada');
    let formData = new FormData();
    formData.append('username', document.getElementById('l-user').value);
    formData.append('password', document.getElementById('l-pass').value);
    let r = await fetch('/token', { method: 'POST', body: formData });
    if (!r.ok) { showToast("Erro"); return; }
    let data = await r.json();
    localStorage.setItem('token', data.access_token);
    let me = await fetch('/users/me', { headers: { 'Authorization': `Bearer ${data.access_token}` } });
    user = await me.json();
    startApp();
}
async function doRegister(){ let btn=document.querySelector('#register-form .btn-main'); let oldText=btn.innerText; btn.innerText="⏳ REGISTRANDO..."; btn.disabled=true; try{ let r=await fetch('/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username: document.getElementById('r-user').value, email: document.getElementById('r-email').value, password: document.getElementById('r-pass').value})}); if(!r.ok) throw new Error("Erro"); showToast("✔ Registrado! Faça login."); toggleAuth('login'); }catch(e){ console.error(e); showToast("❌ Erro no registro."); }finally{ btn.innerText=oldText; btn.disabled=false; } }
function formatMsgTime(iso){ if(!iso) return ""; let d=new Date(iso); return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')} ${t('at')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`; }
function formatRankInfo(rank, special, color){ return `${special ? `<span class="special-badge">${special}</span>` : ''}${rank ? `<span class="rank-badge" style="color:${color}; border-color:${color};">${rank}</span>` : ''}`; }
function initEmojis(){ let g=document.getElementById('emoji-grid'); if(!g)return; EMOJIS.forEach(e=>{ let s=document.createElement('div'); s.style.cssText="font-size:24px;cursor:pointer;text-align:center;padding:5px;border-radius:5px;transition:0.2s;"; s.innerText=e; s.onclick=()=>{ if(currentEmojiTarget){ let inp=document.getElementById(currentEmojiTarget); inp.value+=e; inp.focus(); } }; s.onmouseover=()=>s.style.background="rgba(102,252,241,0.2)"; s.onmouseout=()=>s.style.background="transparent"; g.appendChild(s); }); } initEmojis();
function checkToken(){ const urlParams=new URLSearchParams(window.location.search); const token=urlParams.get('token'); if(token){ toggleAuth('reset'); window.history.replaceState({}, document.title, "/"); window.resetToken=token; } }
function closeUpload(){ document.getElementById('modal-upload').classList.add('hidden'); document.getElementById('file-upload').value=''; document.getElementById('caption-upload').value=''; }
function openEmoji(id){ currentEmojiTarget=id; document.getElementById('emoji-picker').style.display='flex'; }
function toggleEmoji(forceClose){ let e=document.getElementById('emoji-picker'); if(forceClose===true) e.style.display='none'; else e.style.display = e.style.display==='flex'?'none':'flex'; }

document.addEventListener("visibilitychange", ()=>{ if(document.visibilityState==="visible" && user){ fetchUnread(); fetchOnlineUsers(); if(document.getElementById('view-feed').classList.contains('active')) loadFeed(); if(activeChannelId && commWS && commWS.readyState!==WebSocket.OPEN) connectCommWS(activeChannelId); } });
async function fetchOnlineUsers(){ if(!user)return; try{ let r=await fetch(`/users/online?nocache=${new Date().getTime()}`); window.onlineUsers=await r.json(); updateStatusDots(); }catch(e){ console.error(e); } }
function updateStatusDots(){ document.querySelectorAll('.status-dot').forEach(dot=>{ let uid=parseInt(dot.getAttribute('data-uid')); if(!uid)return; if(window.onlineUsers.includes(uid)) dot.classList.add('online'); else dot.classList.remove('online'); }); }

async function fetchUnread(){
    if(!user) return;
    try {
        let r = await fetch(`/notifications?nocache=${new Date().getTime()}`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        let d = await r.json(); 
        window.unreadData = d.dms.by_sender || {};
        let badgeInbox = document.getElementById('inbox-badge');
        if(d.dms.total > 0) { badgeInbox.innerText = d.dms.total; badgeInbox.style.display = 'block'; } else { badgeInbox.style.display = 'none'; }
        
        let badgeBases = document.getElementById('bases-badge');
        if(d.comms.total > 0) { badgeBases.innerText = d.comms.total; badgeBases.style.display = 'block'; } else { badgeBases.style.display = 'none'; }
        
        let badgeProfile = document.getElementById('profile-badge');
        if(d.friend_reqs > 0) { badgeProfile.innerText = d.friend_reqs; badgeProfile.style.display = 'block'; } else { badgeProfile.style.display = 'none'; }

        window.lastTotalUnread = d.dms.total;
        if(document.getElementById('view-inbox').classList.contains('active')) {
            document.querySelectorAll('.inbox-item').forEach(item => { let sid = item.getAttribute('data-id'); let type = item.getAttribute('data-type'); let b = item.querySelector('.list-badge'); if(type === '1v1' && window.unreadData[sid]) { b.innerText = window.unreadData[sid]; b.style.display = 'block'; } else if(b) { b.style.display = 'none'; } });
        }
        if(document.getElementById('view-mycomms').classList.contains('active')) {
            document.querySelectorAll('.comm-card').forEach(card => { let cid = card.getAttribute('data-id'); let dot = card.querySelector('.req-dot'); if(d.comms.by_comm[cid]) { if(dot) dot.style.display='block'; } else { if(dot) dot.style.display='none'; } });
        }
    } catch(e) { console.error(e); }
}

async function loadInbox(){
    try {
        await fetchUnread();
        let r = await fetch('/inbox?nocache=' + new Date().getTime(), { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        let d = await r.json();
        let b = document.getElementById('inbox-list'); b.innerHTML = '';
        if((d.groups || []).length === 0 && (d.friends || []).length === 0) { b.innerHTML = `<p style='text-align:center;color:#888;margin-top:20px;'>${t('empty_box')}</p>`; return; }
        (d.groups || []).forEach(g => { b.innerHTML += `<div class="inbox-item" data-id="${g.id}" data-type="group" style="display:flex;align-items:center;gap:15px;padding:12px;background:var(--card-bg);border-radius:12px;cursor:pointer;border:1px solid rgba(102,252,241,0.2);" onclick="openChat(${g.id}, '${g.name}', 'group')"><img src="${g.avatar}" style="width:45px;height:45px;border-radius:50%;"><div style="flex:1;"><b style="color:white;font-size:16px;">${g.name}</b><br><span style="font-size:12px;color:var(--primary);">${t('squad')}</span></div></div>`; });
        (d.friends || []).forEach(f => {
            let unreadCount = (window.unreadData && window.unreadData[String(f.id)]) ? window.unreadData[String(f.id)] : 0; let badgeDisplay = unreadCount > 0 ? 'block' : 'none';
            b.innerHTML += `<div class="inbox-item" data-id="${f.id}" data-type="1v1" style="display:flex;align-items:center;gap:15px;padding:12px;background:rgba(255,255,255,0.05);border-radius:12px;cursor:pointer;" onclick="openChat(${f.id}, '${f.name}', '1v1')"><div class="av-wrap"><img src="${f.avatar}" style="width:45px;height:45px;border-radius:50%;object-fit:cover;"><div class="status-dot" data-uid="${f.id}"></div></div><div style="flex:1;"><b style="color:white;font-size:16px;">${f.name}</b><br><span style="font-size:12px;color:#888;">${t('direct_msg')}</span></div><div class="list-badge" style="display:${badgeDisplay}; background:#ff5555; color:white; font-size:12px; font-weight:bold; padding:4px 10px; border-radius:12px; box-shadow:0 0 8px rgba(255,85,85,0.6);">${unreadCount}</div></div>`;
        });
        updateStatusDots();
    } catch(e) { console.error(e); }
}

async function openCreateGroupModal(){ try{ let r=await authFetch(`/inbox?nocache=${new Date().getTime()}`); let d=await r.json(); let list=document.getElementById('group-friends-list'); if((d.friends||[]).length===0){list.innerHTML=`<p style='color:#ff5555;font-size:13px;'>Adicione amigos primeiro.</p>`;}else{list.innerHTML=d.friends.map(f=>`<label style="display:flex;align-items:center;gap:10px;color:white;margin-bottom:10px;cursor:pointer;"><input type="checkbox" class="grp-friend-cb" value="${f.id}" style="width:18px;height:18px;"><img src="${f.avatar}" style="width:30px;height:30px;border-radius:50%;object-fit:cover;"> ${f.name}</label>`).join('');} document.getElementById('new-group-name').value=''; document.getElementById('modal-create-group').classList.remove('hidden'); }catch(e){ console.error(e); } }
async function submitCreateGroup(){ let name=document.getElementById('new-group-name').value.trim(); if(!name)return; let cbs=document.querySelectorAll('.grp-friend-cb:checked'); let member_ids=Array.from(cbs).map(cb=>parseInt(cb.value)); if(member_ids.length===0)return; try{ let r=await fetch('/group/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,creator_id:user.id,member_ids:member_ids})}); if(r.ok){document.getElementById('modal-create-group').classList.add('hidden');loadInbox();} }catch(e){ console.error(e); } }
async function toggleRequests(type){ let b=document.getElementById('requests-list'); if(b.style.display==='block'){b.style.display='none';return;} b.style.display='block'; try{ let r=await authFetch(`/friend/requests?nocache=${new Date().getTime()}`); let d=await r.json(); if(type==='requests'){b.innerHTML=(d.requests||[]).length?d.requests.map(r=>`<div style="padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;">${r.username} <button class="glass-btn" style="padding:5px 10px;flex:none;" onclick="handleReq(${r.id},'accept')">${t('accept_ally')}</button></div>`).join(''):`<p style="padding:10px;color:#888;">Vazio.</p>`;}else{b.innerHTML=(d.friends||[]).length?d.friends.map(f=>`<div style="padding:10px;border-bottom:1px solid #333;cursor:pointer;display:flex;align-items:center;gap:10px;" onclick="openPublicProfile(${f.id})"><div class="av-wrap"><img src="${f.avatar}" style="width:30px;height:30px;border-radius:50%;"><div class="status-dot" data-uid="${f.id}" style="width:10px;height:10px;"></div></div>${f.username}</div>`).join(''):`<p style="padding:10px;color:#888;">Vazio.</p>`;} updateStatusDots(); }catch(e){ console.error(e); } }
async function sendRequest(tid){try{let r=await authFetch('/friend/request',{method:'POST',body:JSON.stringify({target_id:tid})});if(r.ok){openPublicProfile(tid);}}catch(e){ console.error(e); }}
async function handleReq(rid,act){try{let r=await authFetch('/friend/handle',{method:'POST',body:JSON.stringify({request_id:rid,action:act})});if(r.ok){toggleRequests('requests');fetchUnread();}}catch(e){ console.error(e); }}
async function handleCommReq(rid,act){try{let r=await authFetch('/community/request/handle',{method:'POST',body:JSON.stringify({req_id:rid,action:act})});if(r.ok){showToast("Membro atualizado!");fetchUnread();await openCommunity(activeCommId, true);}}catch(e){ console.error(e); }}

async function unfriend(fid) {
    if(confirm("Desfazer amizade com este soldado?")) {
        try {
            let r = await authFetch('/friend/remove', {method:'POST', body:JSON.stringify({friend_id: fid})});
            if(r.ok) { showToast("Amizade desfeita."); openPublicProfile(fid); loadInbox(); fetchUnread(); }
        } catch(e) { console.error(e); }
    }
}

async function submitCreateComm(e){e.preventDefault();let n=document.getElementById('new-comm-name').value.trim();let d=document.getElementById('new-comm-desc').value.trim();let p=document.getElementById('new-comm-priv').value;let avFile=document.getElementById('comm-avatar-upload').files[0];let banFile=document.getElementById('comm-banner-upload').files[0];if(!n)return showToast("Digite um nome!");let btn=e.target;btn.disabled=true;btn.innerText="CRIANDO...";try{let safeName=encodeURIComponent(n);let av="https://ui-avatars.com/api/?name="+safeName+"&background=111&color=66fcf1";let ban="https://via.placeholder.com/600x200/0b0c10/1f2833?text="+safeName;if(avFile){let formData = new FormData(); formData.append('file', avFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); av = data.secure_url; } if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); ban = data.secure_url; } let payload = { name:n, desc:d, is_priv:parseInt(p), avatar_url:av, banner_url:ban }; let r=await authFetch('/community/create', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-create-comm').classList.add('hidden');showToast("Base Criada!");loadMyComms();goView('mycomms');}}catch(err){console.error(err);showToast("Erro.");}finally{btn.disabled=false;btn.innerText=t('establish');}}
async function submitEditComm(){let avFile=document.getElementById('edit-comm-avatar').files[0];let banFile=document.getElementById('edit-comm-banner').files[0];if(!avFile&&!banFile)return showToast("Selecione algo.");let btn=document.getElementById('btn-save-comm');btn.disabled=true;btn.innerText="ENVIANDO...";try{let au=null; let bu=null; if(avFile){let formData = new FormData(); formData.append('file', avFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); au = data.secure_url; } if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); bu = data.secure_url; } let payload = { comm_id: activeCommId, avatar_url: au, banner_url: bu }; let r=await authFetch('/community/edit', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-edit-comm').classList.add('hidden');showToast("Base Atualizada!");openCommunity(activeCommId, true);loadMyComms();}}catch(e){console.error(e);showToast("Erro.");}finally{btn.disabled=false;btn.innerText=t('save');}}
async function submitCreateChannel(){let n=document.getElementById('new-ch-name').value.trim();let tType=document.getElementById('new-ch-type').value;let p=document.getElementById('new-ch-priv').value;let banFile=document.getElementById('new-ch-banner').files[0];if(!n)return showToast("Digite o nome.");let btn=document.getElementById('btn-create-ch');btn.disabled=true;btn.innerText="CRIANDO...";try{let safeName=encodeURIComponent(n);let ban="https://via.placeholder.com/600x200/0b0c10/1f2833?text="+safeName;if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); ban = data.secure_url; } let payload = { comm_id: activeCommId, name:n, type:tType, is_private:parseInt(p), banner_url:ban }; let r=await authFetch('/community/channel/create', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-create-channel').classList.add('hidden');showToast("Canal Criado!");openCommunity(activeCommId, true);}}catch(err){console.error(err);}finally{btn.disabled=false;btn.innerText=t('create_channel');}}
async function toggleStealth(){try{let r=await authFetch('/profile/stealth', {method:'POST'}); if(r.ok){let d=await r.json(); user.is_invisible=d.is_invisible; updateStealthUI(); fetchOnlineUsers();}}catch(e){ console.error(e); }}
function updateStealthUI(){let btn=document.getElementById('btn-stealth');let myDot=document.getElementById('my-status-dot');if(user.is_invisible){btn.innerText=t('stealth_on');btn.style.borderColor="#ffaa00";btn.style.color="#ffaa00";myDot.classList.remove('online');}else{btn.innerText=t('stealth_off');btn.style.borderColor="rgba(102, 252, 241, 0.3)";btn.style.color="var(--primary)";myDot.classList.add('online');}}
async function requestReset(){let email=document.getElementById('f-email').value;if(!email)return showToast("Erro!");try{let r=await fetch('/auth/forgot-password', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email:email})}); showToast("Enviado!"); toggleAuth('login');}catch(e){console.error(e);showToast("Erro");}}
async function doResetPassword(){let newPass=document.getElementById('new-pass').value;if(!newPass)return showToast("Erro!");try{let r=await fetch('/auth/reset-password', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token:window.resetToken,new_password:newPass})}); if(r.ok){showToast("Alterada!");toggleAuth('login');}else{showToast("Link expirado.");}}catch(e){console.error(e);showToast("Erro");}}

function renderMedals(boxId, medalsData, isPublic = false) {
    let box = document.getElementById(boxId); 
    if(!medalsData) { box.innerHTML = ''; return; }
    let medalsToShow = isPublic ? medalsData.filter(m => m.earned) : medalsData;
    if (isPublic && medalsToShow.length === 0) {
        box.innerHTML = `<div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:12px; border:1px dashed #444; color:#888; font-style:italic;">🎖️ ${t('no_trophies')}</div>`;
        return;
    }
    if(!isPublic && medalsToShow.length === 0) { box.innerHTML = ''; return; }
    let mHtml = medalsToShow.map(m => {
        let op = m.earned ? '1' : '0.4'; let filter = m.earned ? 'drop-shadow(0 0 8px rgba(102,252,241,0.4))' : 'grayscale(100%)';
        let statusText = m.earned ? `<span style="color:#2ecc71;font-size:9px;">✔ Desbloqueado</span>` : `<span style="color:#ff5555;font-size:9px;">🔒 Faltam ${m.missing} XP</span>`;
        return `<div style="background:rgba(0,0,0,0.5); padding:12px 5px; border-radius:12px; border:1px solid ${m.earned ? 'rgba(102,252,241,0.3)' : '#333'}; width:100px; text-align:center; opacity:${op}; display:flex; flex-direction:column; align-items:center; justify-content:space-between; transition:0.3s;" title="${m.desc}"><div style="font-size:32px; filter:${filter}; margin-bottom:5px;">${m.icon}</div><div style="font-size:11px; color:white; font-weight:bold; font-family:'Inter'; line-height:1.2; margin-bottom:4px;">${m.name}</div>${statusText}</div>`;
    }).join('');
    box.innerHTML = `<h3 style="color:var(--primary); font-family:'Rajdhani'; letter-spacing:1px; text-align:center; margin-top:30px; border-bottom:1px solid #333; padding-bottom:10px; display:inline-block;">${t('medals')}</h3><div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-bottom: 30px;">${mHtml}</div>`;
}

function updateUI(){
    if(!user) return;
    let safeAvatar = user.avatar_url; if(!safeAvatar || safeAvatar.includes("undefined")) safeAvatar = `https://ui-avatars.com/api/?name=${user.username}&background=1f2833&color=66fcf1&bold=true`;
    document.getElementById('nav-avatar').src = safeAvatar; document.getElementById('p-avatar').src = safeAvatar;
    let pCover = document.getElementById('p-cover'); pCover.src = user.cover_url || "https://via.placeholder.com/600x200/0b0c10/66fcf1?text=FOR+GLORY"; pCover.style.display = 'block';
    document.getElementById('p-name').innerText = user.username || "Soldado"; document.getElementById('p-bio').innerText = user.bio || "Na base de operações."; 
    document.getElementById('p-emblems').innerHTML = formatRankInfo(user.rank, user.special_emblem, user.color);
    let missingXP = user.next_xp - user.xp;
    document.getElementById('p-progression-box').innerHTML = `<div style="margin: 20px auto; width: 90%; max-width: 400px; text-align: left; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 12px; border: 1px solid #333;"><div style="display: flex; justify-content: space-between; margin-bottom: 5px;"><span style="color: var(--primary); font-weight: bold; font-size: 14px;">${t('progression')}</span><span style="color: white; font-size: 14px; font-family:'Rajdhani'; font-weight:bold;">${user.xp} / ${user.next_xp} XP</span></div><div style="width: 100%; background: #222; height: 10px; border-radius: 5px; overflow: hidden; box-shadow:inset 0 2px 5px rgba(0,0,0,0.5);"><div style="width: ${user.percent}%; height: 100%; background: linear-gradient(90deg, #1d4e4f, var(--primary)); transition: width 0.5s;"></div></div><div style="display:flex; justify-content:space-between; margin-top:8px; align-items:center;"><span style="color: #888; font-size: 11px;">Falta ${missingXP} XP para ${user.next_rank}</span><button class="btn-link" style="margin:0; font-size:11px;" onclick="showRanksModal()">Ver Patentes</button></div></div>`;
    renderMedals('p-medals-box', user.medals, false); document.querySelectorAll('.my-avatar-mini').forEach(img => img.src = safeAvatar); updateStealthUI();
}

function startApp(){
    document.getElementById('modal-login').classList.add('hidden'); document.querySelector('.lang-dropdown').classList.add('hidden'); 
    updateUI(); fetchOnlineUsers(); fetchUnread(); goView('profile', document.getElementById('nav-profile-btn'));
    
    let p = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let token = localStorage.getItem('token');
    globalWS = new WebSocket(`${p}//${location.host}/ws/Geral/${user.id}?token=${token}`);
    globalWS.onmessage = (e) => {
        let d = JSON.parse(e.data);
        if(d.type === 'pong') return; 
        if(d.type === 'ping') { fetchUnread(); }

        if(d.type === 'sync_bg' && window.currentAgoraChannel === d.channel) {
            document.getElementById('expanded-call-panel').style.backgroundImage = `url('${d.bg_url}')`;
        }

        if(d.type === 'new_dm') {
            let isDmActive = document.getElementById('view-dm').classList.contains('active');
            if(isDmActive && currentChatType === '1v1' && currentChatId === d.sender_id) {} 
            else { safePlaySound(window.msgSound); fetchUnread(); }
        }
        
        if(d.type === 'kick_call' && d.target_id === user.id) {
            showToast("Você foi removido da chamada."); leaveCall();
        }
        
        if(d.type === 'call_accepted') {
            stopSounds();
            connectToAgora(d.channel, window.pendingCallType);
        }

        if(d.type === 'call_rejected') {
            showToast("❌ Chamada recusada.");
            leaveCall();
        }

        if(d.type === 'call_cancelled') {
            showToast("⚠️ A chamada foi cancelada.");
            document.getElementById('modal-incoming-call').classList.add('hidden'); 
            stopSounds();
        }
        
        if(d.type === 'incoming_call') {
            window.pendingCallerId = d.caller_id;
            document.getElementById('incoming-call-name').innerText = d.caller_name;
            document.getElementById('incoming-call-av').src = d.caller_avatar;
            window.pendingCallChannel = d.channel_name; window.pendingCallType = d.call_type;
            document.getElementById('modal-incoming-call').classList.remove('hidden');
            safePlaySound(window.ringtone);
        }
    };
    globalWS.onclose = () => { setTimeout(() => { if(user) startApp(); }, 5000); };
    setInterval(()=>{ if(globalWS && globalWS.readyState === WebSocket.OPEN) { globalWS.send("ping"); } }, 20000);
    syncInterval=setInterval(()=>{ if(document.getElementById('view-feed').classList.contains('active')) loadFeed(); fetchOnlineUsers(); },4000);
}

function logout(){location.reload()}
function goView(v, btnElem){
    document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));
    document.getElementById('view-'+v).classList.add('active');
    if(v !== 'public-profile' && v !== 'dm' && v !== 'comm-dashboard') { document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active')); if(btnElem) btnElem.classList.add('active'); else if(event && event.target && event.target.closest) event.target.closest('.nav-btn')?.classList.add('active'); }
    if(v === 'inbox') loadInbox(); if(v === 'mycomms') loadMyComms(); if(v === 'explore') loadPublicComms(); if(v === 'history') loadMyHistory(); if(v === 'feed') loadFeed();
}

async function toggleRecord(type) { 
    let btn=document.getElementById(`btn-mic-${type}`); 
    let inpId=type==='dm'?'dm-msg':(type==='comm'?'comm-msg':`comment-inp-${type.split('-')[1]}`); 
    let inp=document.getElementById(inpId); 
    
    if(mediaRecorders[type]&&mediaRecorders[type].state==='recording'){
        mediaRecorders[type].stop();
        btn.classList.remove('recording');
        clearInterval(recordTimers[type]);
        if(inp){inp.placeholder=t('audio_proc');inp.disabled=true;}
        return;
    } 
    try{ 
        let stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:false,sampleRate:48000}});
        let options={};
        if(MediaRecorder.isTypeSupported('audio/webm;codecs=opus')){options={mimeType:'audio/webm;codecs=opus',audioBitsPerSecond:128000};} 
        mediaRecorders[type]=new MediaRecorder(stream,options);
        audioChunks[type]=[];
        mediaRecorders[type].ondataavailable=e=>{if(e.data.size>0)audioChunks[type].push(e.data);}; 
        
        mediaRecorders[type].onstop=async()=>{ 
            let blob=new Blob(audioChunks[type],{type:'audio/webm'});
            let file=new File([blob],"radio.webm",{type:'audio/webm'}); 
            try{ 
                let formData = new FormData(); formData.append('file', file);
                let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} });
                let data = await res.json();
                let audioMsg="[AUDIO]"+data.secure_url; 
                if(type==='dm'&&dmWS){dmWS.send(audioMsg);}
                else if(type==='comm'&&commWS){commWS.send(audioMsg);}
                else if(type.startsWith('comment-')){ 
                    let pid=type.split('-')[1];
                    await authFetch('/post/comment', { method:'POST', body:JSON.stringify({post_id:pid,text:audioMsg}) });
                    lastFeedHash="";loadFeed();
                } 
            }catch(err){ console.error(err); showToast("Falha ao enviar áudio."); } 
            stream.getTracks().forEach(t=>t.stop());
            if(inp){ inp.disabled=false; inp.placeholder= t(type==='comm'?'base_msg_placeholder':'msg_placeholder'); } 
        }; 
        
        mediaRecorders[type].start();
        btn.classList.add('recording'); 
        if(inp){
            inp.disabled=true;recordSeconds[type]=0;inp.placeholder=`${t('recording')} 00:00`;
            recordTimers[type]=setInterval(()=>{
                recordSeconds[type]++;
                let mins=String(Math.floor(recordSeconds[type]/60)).padStart(2,'0');
                let secs=String(recordSeconds[type]%60).padStart(2,'0');
                inp.placeholder=`${t('recording')} ${mins}:${secs} ${t('click_to_send')}`;
            },1000);
        } 
    }catch(e){ console.error(e); showToast("Sem Microfone!");} 
}

async function loadMyHistory(){try{let hist=await fetch(`/user/${user.id}?viewer_id=${user.id}&nocache=${new Date().getTime()}`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } }); let hData=await hist.json(); let grid=document.getElementById('my-posts-grid');grid.innerHTML='';if((hData.posts||[]).length===0)grid.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_history')}</p>`;(hData.posts||[]).forEach(p=>{grid.innerHTML+=p.media_type==='video'?`<video src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:10px;" controls preload="metadata"></video>`:`<img src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;cursor:pointer;border-radius:10px;" onclick="window.open(this.src)">`;});}catch(e){ console.error(e); }}
async function loadFeed(){try{let r=await fetch(`/posts?uid=${user.id}&limit=50&nocache=${new Date().getTime()}`);if(!r.ok)return;let p=await r.json();let h=JSON.stringify(p.map(x=>x.id+x.likes+x.comments+(x.user_liked?"1":"0")));if(h===lastFeedHash)return;lastFeedHash=h;let openComments=[];let activeInputs={};let focusedInputId=null;if(document.activeElement&&document.activeElement.classList.contains('comment-inp')){focusedInputId=document.activeElement.id;}document.querySelectorAll('.comments-section').forEach(sec=>{if(sec.style.display==='block')openComments.push(sec.id.split('-')[1]);});document.querySelectorAll('.comment-inp').forEach(inp=>{if(inp.value)activeInputs[inp.id]=inp.value;});let ht='';p.forEach(x=>{let m=x.media_type==='video'?`<video src="${x.content_url}" class="post-media" controls playsinline preload="metadata"></video>`:`<img src="${x.content_url}" class="post-media" loading="lazy">`;m=`<div class="post-media-wrapper">${m}</div>`;let delBtn=x.author_id===user.id?`<span onclick="window.deleteTarget={type:'post', id:${x.id}}; document.getElementById('modal-delete').classList.remove('hidden');" style="cursor:pointer;opacity:0.5;font-size:20px;transition:0.2s;" onmouseover="this.style.opacity='1';this.style.color='#ff5555'" onmouseout="this.style.opacity='0.5';this.style.color=''">🗑️</span>`:'';let heartIcon=x.user_liked?"❤️":"🤍";let heartClass=x.user_liked?"liked":"";let rankHtml=formatRankInfo(x.author_rank,x.special_emblem,x.rank_color);ht+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer" onclick="openPublicProfile(${x.author_id})"><div class="av-wrap" style="margin-right:12px;"><img src="${x.author_avatar}" class="post-av" style="margin:0;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${x.author_id}"></div></div><div class="user-info-box"><b style="color:white;font-size:14px">${x.author_name}</b><div style="margin-top:2px;">${rankHtml}</div></div></div>${delBtn}</div>${m}<div class="post-actions"><button class="action-btn ${heartClass}" onclick="toggleLike(${x.id}, this)"><span class="icon">${heartIcon}</span> <span class="count" style="color:white;font-weight:bold;">${x.likes}</span></button><button class="action-btn" onclick="toggleComments(${x.id})">💬 <span class="count" style="color:white;font-weight:bold;">${x.comments}</span></button></div><div class="post-caption"><b style="color:white;cursor:pointer;" onclick="openPublicProfile(${x.author_id})">${x.author_name}</b> ${x.caption}</div><div id="comments-${x.id}" class="comments-section"><div id="comment-list-${x.id}"></div><form class="comment-input-area" onsubmit="sendComment(${x.id}); return false;"><button type="button" class="icon-btn" id="btn-mic-comment-${x.id}" onclick="toggleRecord('comment-${x.id}')">🎤</button><input id="comment-inp-${x.id}" class="comment-inp" placeholder="${t('caption_placeholder')}" autocomplete="off"><button type="button" class="icon-btn" onclick="openEmoji('comment-inp-${x.id}')">😀</button><button type="submit" class="btn-send-msg">➤</button></form></div></div>`});document.getElementById('feed-container').innerHTML=ht;openComments.forEach(pid=>{let sec=document.getElementById(`comments-${pid}`);if(sec){sec.style.display='block';loadComments(pid);}});for(let id in activeInputs){let inp=document.getElementById(id);if(inp)inp.value=activeInputs[id];}if(focusedInputId){let inp=document.getElementById(focusedInputId);if(inp){inp.focus({preventScroll:true});let val=inp.value;inp.value='';inp.value=val;}}updateStatusDots();}catch(e){ console.error(e); }}

document.getElementById('btn-confirm-delete').onclick=async()=>{if(!window.deleteTarget || !window.deleteTarget.id)return;let tp=window.deleteTarget.type;let id=window.deleteTarget.id;document.getElementById('modal-delete').classList.add('hidden');try{if(tp==='post'){let r=await authFetch('/post/delete', {method:'POST', body:JSON.stringify({post_id:id})}); if(r.ok){lastFeedHash="";loadFeed();loadMyHistory();updateProfileState();}}else if(tp==='comment'){let r=await authFetch('/comment/delete', {method:'POST', body:JSON.stringify({comment_id:id})}); if(r.ok){lastFeedHash="";loadFeed();}}else if(tp==='base'){let r=await authFetch(`/community/${id}/delete`, {method:'POST'}); if(r.ok){closeComm();loadMyComms();}}else if(tp==='channel'){let r=await authFetch(`/community/channel/${id}/delete`, {method:'POST'}); if(r.ok){document.getElementById('modal-edit-channel').classList.add('hidden');openCommunity(activeCommId, true);}}else if(tp==='dm_msg'||tp==='comm_msg'||tp==='group_msg'){let mainType=tp==='dm_msg'?'dm':(tp==='comm_msg'?'comm':'group');let r=await authFetch('/message/delete', {method:'POST', body:JSON.stringify({msg_id:id,type:mainType})}); let res=await r.json(); if(res.status==='ok'){let msgBubble=document.getElementById(`${tp}-${id}`).querySelector('.msg-bubble');let timeSpan=msgBubble.querySelector('.msg-time');let timeStr=timeSpan?timeSpan.outerHTML:'';msgBubble.innerHTML=`<span class="msg-deleted">${t('deleted_msg')}</span>${timeStr}`;let btn=document.getElementById(`${tp}-${id}`).querySelector('.del-msg-btn');if(btn)btn.remove();}}}catch(e){ console.error(e); }};

async function updateProfileState() { try { let r = await authFetch(`/user/${user.id}?viewer_id=${user.id}&nocache=${new Date().getTime()}`); let d = await r.json(); Object.assign(user, d); updateUI(); } catch(e) { console.error(e); } }
async function toggleLike(pid, btn) {
    try {
        let r = await authFetch('/post/like', {
            method: 'POST',
            body: JSON.stringify({ post_id: pid })
        });
        if (r.ok) {
            let d = await r.json();
            let icon = btn.querySelector('.icon');
            let count = btn.querySelector('.count');
            if (d.liked) {
                btn.classList.add('liked');
                icon.innerText = "❤️";
            } else {
                btn.classList.remove('liked');
                icon.innerText = "🤍";
            }
            count.innerText = d.count;
            lastFeedHash = "";
        }
    } catch (e) { console.error(e); }
}
async function toggleComments(pid){let sec=document.getElementById(`comments-${pid}`);if(sec.style.display==='block'){sec.style.display='none';}else{sec.style.display='block';loadComments(pid);}}
async function loadComments(pid){try{let r=await fetch(`/post/${pid}/comments?nocache=${new Date().getTime()}`);let list=document.getElementById(`comment-list-${pid}`);if(r.ok){let comments=await r.json();if((comments||[]).length===0){list.innerHTML=`<p style='color:#888;font-size:12px;text-align:center;'>Vazio</p>`;return;}list.innerHTML=comments.map(c=>{let delBtn=(c.author_id===user.id)?`<span onclick="window.deleteTarget={type:'comment', id:${c.id}}; document.getElementById('modal-delete').classList.remove('hidden');" style="color:#ff5555;cursor:pointer;margin-left:auto;font-size:14px;padding:0 5px;">🗑️</span>`:'';let txt=c.text;if(txt.startsWith('[AUDIO]')){txt=`<audio controls src="${txt.replace('[AUDIO]','')}" style="max-width:200px;height:35px;outline:none;margin-top:5px;"></audio>`;}return `<div class="comment-row" style="align-items:center;"><div class="av-wrap" onclick="openPublicProfile(${c.author_id})"><img src="${c.author_avatar}" class="comment-av" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${c.author_id}" style="width:8px;height:8px;border-width:1px;"></div></div><div style="flex:1;"><b style="color:var(--primary);cursor:pointer;" onclick="openPublicProfile(${c.author_id})">${c.author_name}</b> <span style="display:inline-block;margin-left:5px;">${formatRankInfo(c.author_rank,c.special_emblem,c.color)}</span> <span style="color:#e0e0e0;display:block;margin-top:3px;">${txt}</span></div>${delBtn}</div>`}).join('');updateStatusDots();}}catch(e){ console.error(e); }}
async function sendComment(pid) {
    try {
        let inp = document.getElementById(`comment-inp-${pid}`);
        let text = inp.value.trim();
        if (!text) return;
        let r = await authFetch('/post/comment', {
            method: 'POST',
            body: JSON.stringify({ post_id: pid, text: text })
        });
        if (r.ok) {
            inp.value = '';
            toggleEmoji(true);
            lastFeedHash = "";
            loadFeed();
        }
    } catch (e) { console.error(e); }
}
async function fetchChatMessages(id, type) {
    let list = document.getElementById('dm-list');
    let url = type === 'group' ? `/group/${id}/messages?nocache=${new Date().getTime()}` : `/dms/${id}?uid=${user.id}&nocache=${new Date().getTime()}`;
    try {
        let r = await authFetch(url);
        if (r.ok) {
            let msgs = await r.json();
            let isAtBottom = (list.scrollHeight - list.scrollTop <= list.clientHeight + 50);
            (msgs || []).forEach(d => {
                let prefix = type === 'group' ? 'group_msg' : 'dm_msg';
                let msgId = `${prefix}-${d.id}`;
                if (!document.getElementById(msgId)) {
                    let m = (d.user_id === user.id);
                    let c = d.content;
                    let delBtn = '';
                    let timeHtml = d.timestamp ? `<span class="msg-time">${formatMsgTime(d.timestamp)}</span>` : '';
                    if (c === '[DELETED]') {
                        c = `<span class="msg-deleted">${t('deleted_msg')}</span>`;
                    } else {
                        if (c.startsWith('[AUDIO]')) {
                            c = `<audio controls src="${c.replace('[AUDIO]', '')}" style="max-width:200px;height:40px;outline:none;"></audio>`;
                        } else if (c.startsWith('http') && c.includes('cloudinary')) {
                            if (c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) {
                                c = `<video src="${c}" style="max-width:100%;border-radius:10px;border:1px solid #444;" controls playsinline></video>`;
                            } else {
                                c = `<img src="${c}" style="max-width:100%;border-radius:10px;cursor:pointer;border:1px solid #444;" onclick="window.open(this.src)">`;
                            }
                        }
                        delBtn = (m && d.can_delete) ? `<span class="del-msg-btn" onclick="window.deleteTarget={type:'${prefix}', id:${d.id}}; document.getElementById('modal-delete').classList.remove('hidden');">🗑️</span>` : '';
                    }
                    let h = `<div id="${msgId}" class="msg-row ${m ? 'mine' : ''}">
                        <img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'">
                        <div>
                            <div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div>
                            <div class="msg-bubble">${c}${timeHtml}${delBtn}</div>
                        </div>
                    </div>`;
                    list.insertAdjacentHTML('beforeend', h);
                }
            });
            if (isAtBottom) list.scrollTop = list.scrollHeight;
        }
    } catch (e) { console.error(e); }
}

async function openChat(id, name, type) {
    let changingChat = (currentChatId !== id || currentChatType !== type);
    currentChatId = id;
    currentChatType = type;
    document.getElementById('dm-header-name').innerText = name;
    goView('dm');
    if (type === '1v1') {
        await fetch(`/inbox/read/${id}`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` }, body: JSON.stringify({ uid: user.id }) });
        fetchUnread();
    }
    if (changingChat) {
        document.getElementById('dm-list').innerHTML = '';
    }
    await fetchChatMessages(id, type);
    if (changingChat || !dmWS || dmWS.readyState !== WebSocket.OPEN) {
        connectDmWS(id, name, type);
    }
}

function connectDmWS(id, name, type) {
    if (dmWS) dmWS.close();
    let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let token = localStorage.getItem('token');
    let ch = type === 'group' ? `group_${id}` : `dm_${Math.min(user.id, id)}_${Math.max(user.id, id)}`;
    dmWS = new WebSocket(`${protocol}//${location.host}/ws/${ch}/${user.id}?token=${token}`);
    dmWS.onclose = () => {
        setTimeout(() => {
            if (currentChatId === id && document.getElementById('view-dm').classList.contains('active')) {
                fetchChatMessages(id, type);
                connectDmWS(id, name, type);
            }
        }, 2000);
    };
    dmWS.onmessage = (e) => {
        let d = JSON.parse(e.data);
        let b = document.getElementById('dm-list');
        let m = parseInt(d.user_id) === parseInt(user.id);
        let c = d.content;
        if (d.type === 'ping' || d.type === 'pong') return;
        if (c.startsWith('[CALL_BG]')) { return; }
        let prefix = type === 'group' ? 'group_msg' : 'dm_msg';
        let msgId = `${prefix}-${d.id}`;
        if (!document.getElementById(msgId)) {
            let delBtn = '';
            let timeHtml = d.timestamp ? `<span class="msg-time">${formatMsgTime(d.timestamp)}</span>` : '';
            if (c === '[DELETED]') {
                c = `<span class="msg-deleted">${t('deleted_msg')}</span>`;
            } else {
                if (c.startsWith('[AUDIO]')) {
                    c = `<audio controls src="${c.replace('[AUDIO]', '')}" style="max-width:200px;height:40px;outline:none;"></audio>`;
                } else if (c.startsWith('http') && c.includes('cloudinary')) {
                    if (c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) {
                        c = `<video src="${c}" style="max-width:100%;border-radius:10px;border:1px solid #444;" controls playsinline></video>`;
                    } else {
                        c = `<img src="${c}" style="max-width:100%;border-radius:10px;cursor:pointer;border:1px solid #444;" onclick="window.open(this.src)">`;
                    }
                }
                delBtn = (m && d.can_delete) ? `<span class="del-msg-btn" onclick="window.deleteTarget={type:'${prefix}', id:${d.id}}; document.getElementById('modal-delete').classList.remove('hidden');">🗑️</span>` : '';
            }
            let h = `<div id="${msgId}" class="msg-row ${m ? 'mine' : ''}">
                <img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'">
                <div>
                    <div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div>
                    <div class="msg-bubble">${c}${timeHtml}${delBtn}</div>
                </div>
            </div>`;
            b.insertAdjacentHTML('beforeend', h);
            b.scrollTop = b.scrollHeight;
        }
        let isDmActive = document.getElementById('view-dm').classList.contains('active');
        if (isDmActive && currentChatType === '1v1' && currentChatId === d.user_id) {
            fetch(`/inbox/read/${d.user_id}`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` }, body: JSON.stringify({ uid: user.id }) }).then(() => fetchUnread());
        } else {
            fetchUnread();
        }
    };
}

function sendDM(){let i=document.getElementById('dm-msg');let msg=i.value.trim();if(msg&&dmWS&&dmWS.readyState===WebSocket.OPEN){dmWS.send(msg);i.value='';toggleEmoji(true);}}
async function uploadDMImage(){let f=document.getElementById('dm-file').files[0];if(!f)return;try{let formData = new FormData(); formData.append('file', f); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); if(dmWS) dmWS.send(data.secure_url); }catch(e){ console.error(e); }}
async function loadMyComms(){try{let r=await authFetch(`/communities/list?nocache=${new Date().getTime()}`); let d=await r.json(); let mList=document.getElementById('my-comms-grid');mList.innerHTML='';if((d.my_comms||[]).length===0)mList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases')}</p>`;(d.my_comms||[]).forEach(c=>{mList.innerHTML+=`<div class="comm-card" data-id="${c.id}" onclick="openCommunity(${c.id})"><img src="${c.avatar_url}" class="comm-avatar"><div class="req-dot" style="display:none;position:absolute;top:-5px;right:-5px;background:#ff5555;color:white;font-size:10px;padding:3px 8px;border-radius:12px;font-weight:bold;box-shadow:0 0 10px #ff5555;border:2px solid var(--dark-bg);z-index:10;">NOVO</div><b style="color:white;font-size:16px;font-family:'Rajdhani';letter-spacing:1px;">${c.name}</b></div>`;});fetchUnread();}catch(e){ console.error(e); }}
async function loadPublicComms(){try{let r=await authFetch(`/communities/search?nocache=${new Date().getTime()}`); let d=await r.json(); let pList=document.getElementById('public-comms-grid');pList.innerHTML='';if((d||[]).length===0)pList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;(d||[]).forEach(c=>{let btnStr=c.is_private?`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:orange;color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>`:`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:#2ecc71;color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;pList.innerHTML+=`<div class="comm-card"><img src="${c.avatar_url}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:'Rajdhani';letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`;});}catch(e){ console.error(e); }}
function clearCommSearch(){document.getElementById('search-comm-input').value='';loadPublicComms();}
async function searchComms(){try{let q=document.getElementById('search-comm-input').value.trim();let r=await authFetch(`/communities/search?q=${q}&nocache=${new Date().getTime()}`); let d=await r.json(); let pList=document.getElementById('public-comms-grid');pList.innerHTML='';if((d||[]).length===0)pList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;(d||[]).forEach(c=>{let btnStr=c.is_private?`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:orange;color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>`:`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:#2ecc71;color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;pList.innerHTML+=`<div class="comm-card"><img src="${c.avatar_url}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:'Rajdhani';letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`;});}catch(e){ console.error(e); }}
async function joinCommunity(cid){try{let r=await authFetch('/community/join', {method:'POST', body:JSON.stringify({comm_id:cid})}); if(r.ok){showToast("Entrou na Base com sucesso!");loadPublicComms();openCommunity(cid);}else{showToast("Erro.");}}catch(e){ console.error(e); }}
async function requestCommJoin(cid){try{let r=await authFetch('/community/request/send', {method:'POST', body:JSON.stringify({comm_id:cid})}); if(r.ok){showToast("Enviado.");}}catch(e){ console.error(e); }}
async function leaveCommunity(cid){if(confirm("Desertar desta base?")){try{let r=await authFetch(`/community/${cid}/leave`, {method:'POST'}); let res=await r.json(); if(res.status==='ok'){closeComm();loadMyComms();}else{showToast(res.msg);}}catch(e){ console.error(e); }}}

async function openCommunity(cid, keepInfoOpen=false){
    activeCommId=cid;goView('comm-dashboard');
    let infoArea = document.getElementById('comm-info-area');
    let chatArea = document.getElementById('comm-chat-area');
    let isInfoOpen = infoArea.style.display === 'flex';
    if(!keepInfoOpen && !isInfoOpen) { infoArea.style.display='none'; chatArea.style.display='flex'; }
    
    try{
        let r=await authFetch(`/community/${cid}?nocache=${new Date().getTime()}`);
        let d=await r.json();
        document.getElementById('active-comm-name').innerText=d.name;let headerBg=d.banner_url?`url('${d.banner_url}')`:'none';
        document.getElementById('comm-header').style.backgroundImage=headerBg;document.getElementById('c-info-av').src=d.avatar_url;
        document.getElementById('c-info-banner').style.backgroundImage=headerBg;document.getElementById('c-info-name').innerText=d.name;document.getElementById('c-info-desc').innerText=d.description;
        window.currentCommIsAdmin=d.is_admin||d.creator_id===user.id;
        let mHtml="";
        (d.members||[]).forEach(m=>{
            let roleBadge=m.id===d.creator_id?t('creator'):(m.role==='admin'?t('admin'):t('member'));
            let actions='<div class="admin-action-wrap">';
            if(d.is_admin&&m.id!==d.creator_id&&m.role!=='admin'){actions+=`<button title="${t('promote')}" class="admin-action-btn success" onclick="promoteMember(${cid}, ${m.id})">🔼</button>`;}
            if(d.creator_id===user.id&&m.id!==d.creator_id&&m.role==='admin'){actions+=`<button title="${t('demote')}" class="admin-action-btn danger" onclick="demoteMember(${cid}, ${m.id})">🔽</button>`;}
            if((d.is_admin||d.creator_id===user.id)&&m.id!==d.creator_id&&(d.creator_id===user.id||m.role!=='admin')){actions+=`<button title="${t('kick')}" class="admin-action-btn danger" onclick="kickMember(${cid}, ${m.id})">❌</button>`;}
            actions+='</div>';
            mHtml+=`<div style="display:flex;align-items:center;gap:10px;padding:10px;border-bottom:1px solid #333;border-radius:10px;transition:0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'"><img src="${m.avatar}" onclick="openPublicProfile(${m.id})" style="width:35px;height:35px;border-radius:50%;object-fit:cover;border:1px solid #555;cursor:pointer;"> <span style="color:white;flex:1;font-weight:bold;cursor:pointer;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" onclick="openPublicProfile(${m.id})">${m.name}</span> <span class="ch-badge" style="color:${m.role==='admin'||m.id===d.creator_id?'var(--primary)':'#888'}">${roleBadge}</span>${actions}</div>`;
        });
        document.getElementById('c-info-members').innerHTML=mHtml;
        let addBtn=document.getElementById('c-info-admin-btn');let reqCont=document.getElementById('c-info-requests-container');let reqList=document.getElementById('c-info-requests');let delCont=document.getElementById('c-info-destroy-btn');
        if(d.creator_id===user.id){delCont.innerHTML=`<button class="glass-btn" style="width:100%;margin-bottom:10px;color:#2ecc71;border-color:#2ecc71;" onclick="document.getElementById('modal-edit-comm').classList.remove('hidden')">✏️ EDITAR BASE</button><button class="glass-btn danger-btn" onclick="window.deleteTarget={type:'base', id:${cid}}; document.getElementById('modal-delete').classList.remove('hidden');">${t('destroy_base')}</button>`;}else{delCont.innerHTML=`<button class="glass-btn danger-btn" onclick="leaveCommunity(${cid})">🚪 SAIR DA BASE</button>`;}
        if(d.is_admin||d.creator_id===user.id){
            addBtn.innerHTML=`<button class="glass-btn" style="width:100%;border-color:#2ecc71;color:#2ecc71;font-size:15px;letter-spacing:2px;" onclick="document.getElementById('modal-create-channel').classList.remove('hidden')">+ ${t('create_channel')}</button>`;
            let reqR=await authFetch(`/community/${cid}/requests?nocache=${new Date().getTime()}`);
            let reqs=await reqR.json();
            if((reqs||[]).length>0){reqCont.style.display='block';reqList.innerHTML='';reqs.forEach(rq=>{reqList.innerHTML+=`<div style="display:flex;align-items:center;gap:10px;background:rgba(0,0,0,0.5);padding:10px;border-radius:10px;"><img src="${rq.avatar}" style="width:30px;height:30px;border-radius:50%;"><span style="color:white;flex:1;">${rq.username}</span><button class="glass-btn" style="padding:5px 10px;flex:none;" onclick="handleCommReq(${rq.id}, 'accept')">✔</button><button class="glass-btn" style="padding:5px 10px;flex:none;border-color:#ff5555;color:#ff5555;" onclick="handleCommReq(${rq.id}, 'reject')">✕</button></div>`;});}else{reqCont.style.display='none';}
        }else{addBtn.innerHTML='';reqCont.style.display='none';}
        let cb=document.getElementById('comm-channels-bar');cb.innerHTML='';
        if((d.channels||[]).length>0){
            let sortedChannels=d.channels.sort((a,b)=>{if(a.name.toLowerCase()==='geral')return -1;if(b.name.toLowerCase()==='geral')return 1;return 0;});
            sortedChannels.forEach(ch=>{
                let bgStyle=ch.banner_url?`background-image:linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url('${ch.banner_url}');border:none;`:'';let icon=ch.type==='voice'?'🎙️ ':'';
                let editBtn=(d.is_admin||d.creator_id===user.id)?`<span style="margin-left:5px;font-size:11px;cursor:pointer;opacity:0.7;" onclick="event.stopPropagation(); openEditChannelModal(${ch.id}, '${ch.name}', '${ch.type}', ${ch.is_private})">⚙️</span>`:'';
                cb.innerHTML+=`<button class="channel-btn" style="${bgStyle}" onclick="joinChannel(${ch.id}, '${ch.type}', this)">${icon}${ch.name} ${editBtn}</button>`;
            });
            if(!keepInfoOpen && !isInfoOpen) { joinChannel(sortedChannels[0].id,sortedChannels[0].type,cb.children[0]); }
        }else{document.getElementById('comm-chat-list').innerHTML="";}
    }catch(e){ console.error(e); }
}

async function promoteMember(cid,tid){try{let payload={comm_id:cid,target_id:tid};let r=await authFetch('/community/member/promote', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){await openCommunity(cid, true);}}catch(e){ console.error(e); }}
async function demoteMember(cid,tid){try{let payload={comm_id:cid,target_id:tid};let r=await authFetch('/community/member/demote', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){await openCommunity(cid, true);}}catch(e){ console.error(e); }}
async function kickMember(cid,tid){if(confirm("Tem certeza que deseja expulsar?")){try{let payload={comm_id:cid,target_id:tid};let r=await authFetch('/community/member/kick', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){await openCommunity(cid, true);}}catch(e){ console.error(e); }}}
function showCommInfo(){document.getElementById('comm-chat-area').style.display='none';document.getElementById('comm-info-area').style.display='flex';}
function closeComm(){goView('mycomms',document.querySelectorAll('.nav-btn')[3]);if(commWS)commWS.close();}

window.currentEditChannelId=null;
function openEditChannelModal(id,name,type,priv){window.currentEditChannelId=id;document.getElementById('edit-ch-name').value=name;document.getElementById('edit-ch-type').value=type;document.getElementById('edit-ch-priv').value=priv;document.getElementById('modal-edit-channel').classList.remove('hidden');}
async function submitEditChannel(){let n=document.getElementById('edit-ch-name').value.trim();let tType=document.getElementById('edit-ch-type').value;let p=document.getElementById('edit-ch-priv').value;let banFile=document.getElementById('edit-ch-banner').files[0];if(!n)return;let btn=document.getElementById('btn-edit-ch');btn.disabled=true;btn.innerText="SALVANDO...";try{let bu=null; if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); bu = data.secure_url; } let payload={channel_id:window.currentEditChannelId, name:n, type:tType, is_private:parseInt(p), banner_url:bu}; let r=await authFetch('/community/channel/edit', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-edit-channel').classList.add('hidden');openCommunity(activeCommId, true);}}catch(e){ console.error(e); }finally{btn.disabled=false;btn.innerText=t('save');}}

async function fetchCommMessages(chid){let list=document.getElementById('comm-chat-list');try{let r=await fetch(`/community/channel/${chid}/messages?nocache=${new Date().getTime()}`);if(r.ok){let msgs=await r.json();let isAtBottom=(list.scrollHeight-list.scrollTop<=list.clientHeight+50);(msgs||[]).forEach(d=>{let prefix='comm_msg';let msgId=`${prefix}-${d.id}`;if(!document.getElementById(msgId)){let m=(d.user_id===user.id);let c=d.content;let delBtn='';let timeHtml=d.timestamp?`<span class="msg-time">${formatMsgTime(d.timestamp)}</span>`:'';if(c==='[DELETED]'){c=`<span class="msg-deleted">${t('deleted_msg')}</span>`;}else{if(c.startsWith('[AUDIO]')){c=`<audio controls src="${c.replace('[AUDIO]','')}" style="max-width:200px;height:40px;outline:none;"></audio>`;}else if(c.startsWith('http')&&c.includes('cloudinary')){if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i)||c.includes('/video/upload/')){c=`<video src="${c}" style="max-width:100%;border-radius:10px;border:1px solid #444;" controls playsinline></video>`;}else{c=`<img src="${c}" style="max-width:100%;border-radius:10px;cursor:pointer;border:1px solid #444;" onclick="window.open(this.src)">`;}}delBtn=(m&&d.can_delete)?`<span class="del-msg-btn" onclick="window.deleteTarget={type:'${prefix}', id:${d.id}}; document.getElementById('modal-delete').classList.remove('hidden');">🗑️</span>`:'';}let h=`<div id="${msgId}" class="msg-row ${m?'mine':''}"><img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username} ${formatRankInfo(d.rank,d.special_emblem,d.color)}</div><div class="msg-bubble">${c}${timeHtml}${delBtn}</div></div></div>`;list.insertAdjacentHTML('beforeend',h);}});if(isAtBottom)list.scrollTop=list.scrollHeight;}}catch(e){ console.error(e); }}

function connectCommWS(chid) {
    if (commWS) commWS.close();
    let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let token = localStorage.getItem('token');
    commWS = new WebSocket(`${protocol}//${location.host}/ws/comm_${chid}/${user.id}?token=${token}`);
    commWS.onclose = () => {
        setTimeout(() => {
            if (activeChannelId === chid && document.getElementById('comm-chat-area').style.display === 'flex' && window.currentCommType !== 'voice') {
                fetchCommMessages(chid);
                connectCommWS(chid);
            }
        }, 2000);
    };
    commWS.onmessage = (e) => {
        let d = JSON.parse(e.data);
        let b = document.getElementById('comm-chat-list');
        let m = parseInt(d.user_id) === parseInt(user.id);
        let c = d.content;
        if (d.type === 'ping' || d.type === 'pong') return;
        if (c.startsWith('[CALL_BG]')) { return; }
        let prefix = 'comm_msg';
        let msgId = `${prefix}-${d.id}`;
        if (!document.getElementById(msgId)) {
            let delBtn = '';
            let timeHtml = d.timestamp ? `<span class="msg-time">${formatMsgTime(d.timestamp)}</span>` : '';
            if (c === '[DELETED]') {
                c = `<span class="msg-deleted">${t('deleted_msg')}</span>`;
            } else {
                if (c.startsWith('[AUDIO]')) {
                    c = `<audio controls src="${c.replace('[AUDIO]', '')}" style="max-width:200px;height:40px;outline:none;"></audio>`;
                } else if (c.startsWith('http') && c.includes('cloudinary')) {
                    if (c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) {
                        c = `<video src="${c}" style="max-width:100%;border-radius:10px;border:1px solid #444;" controls playsinline></video>`;
                    } else {
                        c = `<img src="${c}" style="max-width:100%;border-radius:10px;cursor:pointer;border:1px solid #444;" onclick="window.open(this.src)">`;
                    }
                }
                delBtn = (m && d.can_delete) ? `<span class="del-msg-btn" onclick="window.deleteTarget={type:'${prefix}', id:${d.id}}; document.getElementById('modal-delete').classList.remove('hidden');">🗑️</span>` : '';
            }
            let h = `<div id="${msgId}" class="msg-row ${m ? 'mine' : ''}">
                <img src="${d.avatar}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'">
                <div>
                    <div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${d.username} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div>
                    <div class="msg-bubble">${c}${timeHtml}${delBtn}</div>
                </div>
            </div>`;
            b.insertAdjacentHTML('beforeend', h);
            b.scrollTop = b.scrollHeight;
        }
    };
}

async function joinChannel(chid, type, btnElem) {
    let changingChannel = (activeChannelId !== chid);
    activeChannelId = chid;
    window.currentCommType = type;
    document.getElementById('comm-info-area').style.display = 'none';
    document.getElementById('comm-chat-area').style.display = 'flex';
    if (btnElem) {
        document.querySelectorAll('.channel-btn').forEach(b => b.classList.remove('active'));
        btnElem.classList.add('active');
    }
    let inpForm = document.getElementById('comm-input-form');
    let inp = document.getElementById('comm-msg');
    let clip = document.getElementById('btn-comm-clip');
    let emj = document.getElementById('btn-comm-emoji');
    let mic = document.getElementById('btn-comm-mic');
    inp.disabled = false;
    clip.style.display = 'flex';
    emj.style.display = 'flex';
    mic.style.display = 'flex';
    inpForm.style.display = 'flex';
    let cp = document.getElementById('expanded-call-panel');
    cp.style.backgroundImage = 'none';
    document.getElementById('call-bg-action').style.display = 'none';
    if (changingChannel && commWS) {
        commWS.close();
        commWS = null;
    }
    if (type === 'voice') {
        inpForm.style.display = 'none';
        document.getElementById('comm-chat-list').innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;text-align:center;"><div style="font-size:50px;margin-bottom:20px;text-shadow:0 0 20px var(--primary);">🎙️</div><h3 style="color:white;font-family:'Rajdhani';font-size:28px;margin:0;">CANAL DE VOZ</h3><p style="color:#aaa;font-size:14px;max-width:250px;">O áudio está rodando em segundo plano. Você pode minimizar o aplicativo ou ir para outras abas.</p><button onclick="initCall('channel', ${chid})" class="btn-main" style="width:auto;padding:15px 40px;font-size:18px;box-shadow:0 10px 20px rgba(102,252,241,0.3);border-radius:30px;">${t('join_call')}</button></div>`;
        if (window.currentCommIsAdmin) {
            document.getElementById('call-bg-action').style.display = 'block';
        }
        try {
            let r = await fetch(`/call/bg/channel/${chid}`);
            let res = await r.json();
            if (res.bg_url) {
                cp.style.backgroundImage = `url('${res.bg_url}')`;
            }
        } catch (e) { console.error(e); }
    } else {
        if (type === 'media') {
            inp.disabled = true;
            inp.placeholder = t('media_only');
            emj.style.display = 'none';
            mic.style.display = 'none';
        } else if (type === 'text') {
            inp.placeholder = t('base_msg_placeholder');
            clip.style.display = 'none';
            mic.style.display = 'flex';
        } else {
            inp.placeholder = t('base_msg_placeholder');
        }
        if (changingChannel) {
            document.getElementById('comm-chat-list').innerHTML = '';
        }
        await fetchCommMessages(chid);
        if (!commWS || commWS.readyState !== WebSocket.OPEN) {
            connectCommWS(chid);
        }
    }
}
function sendCommMsg(){let i=document.getElementById('comm-msg');let msg=i.value.trim();if(msg&&commWS&&commWS.readyState===WebSocket.OPEN){commWS.send(msg);i.value='';toggleEmoji(true);}}
async function uploadCommImage(){let f=document.getElementById('comm-file').files[0];if(!f)return;try{let formData = new FormData(); formData.append('file', f); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); if(commWS) commWS.send(data.secure_url); }catch(e){ console.error(e); }}

async function openPublicProfile(uid){try{let r=await authFetch(`/user/${uid}?viewer_id=${user.id}&nocache=${new Date().getTime()}`); let d=await r.json(); document.getElementById('pub-avatar').src=d.avatar_url;let pc=document.getElementById('pub-cover');pc.src=d.cover_url;pc.style.display='block';document.getElementById('pub-name').innerText=d.username;document.getElementById('pub-bio').innerText=d.bio;document.getElementById('pub-emblems').innerHTML=formatRankInfo(d.rank,d.special_emblem,d.color);renderMedals('pub-medals-box',d.medals,true);let ab=document.getElementById('pub-actions');ab.innerHTML='';document.getElementById('pub-status-dot').setAttribute('data-uid',uid);updateStatusDots();if(d.friend_status==='friends'){ab.innerHTML=`<div style="display:flex; justify-content:center; align-items:center; gap:10px; width:100%;"><span style="color:#66fcf1;border:1px solid #66fcf1;padding:8px 12px;border-radius:12px;font-weight:bold;font-size:12px;">${t('ally')}</span> <button class="glass-btn" style="padding:8px 15px; border-color:var(--primary); font-size:12px; max-width:120px; margin:0;" onclick="openChat(${uid}, '${d.username}', '1v1')">💬 Mensagem</button></div><div style="width:100%; margin-top:15px; text-align:center;"><button class="glass-btn danger-btn" style="padding:8px 15px; font-size:12px; width:auto; display:inline-block; margin:0;" onclick="unfriend(${uid})">❌ Desfazer Amizade</button></div>`;}else if(d.friend_status==='pending_sent'){ab.innerHTML=`<span style="color:orange;border:1px solid orange;padding:10px 15px;border-radius:12px;">${t('sent')}</span>`;}else if(d.friend_status==='pending_received'){ab.innerHTML=`<button class="glass-btn" onclick="handleReq(${d.request_id},'accept')">${t('accept_ally')}</button>`;}else{ab.innerHTML=`<button class="glass-btn" style="padding:10px 20px; font-size:13px; max-width:200px; display:block; margin: 0 auto;" onclick="sendRequest(${uid})">${t('recruit_ally')}</button>`;}let g=document.getElementById('pub-grid');g.innerHTML='';(d.posts||[]).forEach(p=>{g.innerHTML+=p.media_type==='video'?`<video src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;" controls></video>`:`<img src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;cursor:pointer;" onclick="window.open(this.src)">`});goView('public-profile')}catch(e){ console.error(e); }}

async function uploadToCloudinary(file){
    // Não usado mais – substituído por upload via backend
    return Promise.reject("Use /upload");
}

async function submitPost(){let f=document.getElementById('file-upload').files[0];let cap=document.getElementById('caption-upload').value;if(!f)return;let btn=document.getElementById('btn-pub');btn.disabled=true;document.getElementById('upload-progress').style.display='block';document.getElementById('progress-text').style.display='block';try{let formData = new FormData(); formData.append('file', f); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); let payload={ caption: cap, content_url: data.secure_url, media_type: data.resource_type }; let r=await authFetch('/post/create_from_url', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){lastFeedHash="";loadFeed();closeUpload();loadMyHistory();updateProfileState();}}catch(e){ console.error(e); }finally{btn.disabled=false;document.getElementById('upload-progress').style.display='none';document.getElementById('progress-text').style.display='none';document.getElementById('progress-bar').style.width='0%';}}
async function updateProfile(){let btn=document.getElementById('btn-save-profile');btn.disabled=true;try{let f=document.getElementById('avatar-upload').files[0];let c=document.getElementById('cover-upload').files[0];let b=document.getElementById('bio-update').value;let au=null,cu=null;if(f){let formData = new FormData(); formData.append('file', f); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); au = data.secure_url; } if(c){let formData = new FormData(); formData.append('file', c); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); cu = data.secure_url; } let payload={ avatar_url: au, cover_url: cu, bio: b }; let r=await authFetch('/profile/update_meta', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){updateProfileState();document.getElementById('modal-profile').classList.add('hidden');}}catch(e){ console.error(e); }finally{btn.disabled=false;}}
function clearSearch(){document.getElementById('search-input').value='';document.getElementById('search-results').innerHTML='';}
async function searchUsers(){let q=document.getElementById('search-input').value;if(!q)return;try{let r=await fetch(`/users/search?q=${q}&nocache=${new Date().getTime()}`);let res=await r.json();let b=document.getElementById('search-results');b.innerHTML='';(res||[]).forEach(u=>{if(u.id!==user.id)b.innerHTML+=`<div style="padding:10px;background:rgba(255,255,255,0.05);margin-top:5px;border-radius:8px;display:flex;align-items:center;gap:10px;cursor:pointer" onclick="openPublicProfile(${u.id})"><div class="av-wrap"><img src="${u.avatar_url}" style="width:35px;height:35px;border-radius:50%;object-fit:cover;margin:0;"><div class="status-dot" data-uid="${u.id}"></div></div><span>${u.username}</span></div>`});updateStatusDots();}catch(e){ console.error(e); }}
</script>
</body>
</html>
"""

# ----------------------------------------------------------------------
# ROTA PRINCIPAL (FRONTEND)
# ----------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def get():
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
