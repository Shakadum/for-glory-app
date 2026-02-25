import uvicorn
import json
import os
import logging
import hashlib
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, UploadFile, File, Form
from starlette.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.db.session import get_db, engine, SessionLocal
from app.db.base import Base
from app.models.models import (
    User, FriendRequest, Post, Like, Comment, PrivateMessage,
    ChatGroup, GroupMember, GroupMessage,
    Community, CommunityMember, CommunityChannel, CommunityMessage, CommunityRequest,
    CallBackground, UserConfig, friendship
)
from app.services.cloudinary import init_cloudinary
try:
    import cloudinary  # type: ignore
    import cloudinary.uploader  # type: ignore
except Exception:  # pragma: no cover
    cloudinary = None
from jose import jwt, JWTError
from collections import Counter
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import status

# ----------------------------------------------------------------------
# LOGGER (definido cedo para uso nas funções de segurança)
# ----------------------------------------------------------------------
logger = logging.getLogger("ForGlory")

# ----------------------------------------------------------------------
# CONFIGURAÇÕES DE SEGURANÇA
# ----------------------------------------------------------------------
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

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
    """Gera hash bcrypt.

    bcrypt tem limite de 72 bytes: truncar silenciosamente cria risco real
    (senhas diferentes viram a mesma hash). Então aqui a gente bloqueia.
    """
    if isinstance(password, str):
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            raise HTTPException(status_code=400, detail="Senha muito longa (máx. 72 bytes).")
    return pwd_context.hash(password)

# ========== FUNÇÃO DE AUTENTICAÇÃO COM LOGS ==========
def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.password_hash:
        logger.warning(f"❌ Usuário {username} não encontrado ou sem hash")
        return False

    # Verifica com passlib (bcrypt)
    try:
        if verify_password(password, user.password_hash):
            logger.info("✅ Senha correta")
            return user
        logger.warning("❌ Senha incorreta")
        return False
    except Exception:
        logger.exception("Erro ao verificar senha")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
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

def _require_env_any(*names: str) -> str:
    """Return the first env var found among names, else raise."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    raise RuntimeError(
        "Variável de ambiente obrigatória não definida. Informe uma destas: "
        + ", ".join(names)
    )

# Cloudinary pode vir como URL única (mais comum) ou separado em variáveis.
cloudinary_url = os.environ.get("CLOUDINARY_URL")
if cloudinary_url:
    cloudinary.config(cloudinary_url=cloudinary_url, secure=True)
else:
    cloudinary.config(
        cloud_name=_require_env_any("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_NAME"),
        api_key=_require_env_any("CLOUDINARY_API_KEY", "CLOUDINARY_KEY"),
        api_secret=_require_env_any("CLOUDINARY_API_SECRET", "CLOUDINARY_SECRET"),
        secure=True,
    )

# ----------------------------
#------------------------------------------
# BANCO DE DADOS (NEON / POSTGRESQL)
# ----------------------------------------------------------------------

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
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="For Glory Cloud")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        # active[chan] -> list[WebSocket]
        self.active: dict[str, list[WebSocket]] = {}
        # user_ws[uid] -> set[WebSocket] (um usuário pode ter WS global + DM + comm aberto)
        self.user_ws: dict[int, set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, chan: str, uid: int):
        await ws.accept()
        self.active.setdefault(chan, []).append(ws)
        self.user_ws.setdefault(uid, set()).add(ws)

    def disconnect(self, ws: WebSocket, chan: str, uid: int):
        try:
            if chan in self.active and ws in self.active[chan]:
                self.active[chan].remove(ws)
        except Exception:
            pass
        try:
            if uid in self.user_ws and ws in self.user_ws[uid]:
                self.user_ws[uid].remove(ws)
                if not self.user_ws[uid]:
                    del self.user_ws[uid]
        except Exception:
            pass

    async def broadcast(self, msg: dict, chan: str):
        # envia para todos no canal
        payload = json.dumps(msg)
        for conn in list(self.active.get(chan, [])):
            try:
                await conn.send_text(payload)
            except Exception:
                pass

    async def send_personal(self, msg: dict, uid: int):
        # envia para todos sockets desse usuário (global + dm + comm)
        conns = list(self.user_ws.get(uid, set()))
        if not conns:
            return
        payload = json.dumps(msg)
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                pass

manager = ConnectionManager()


def get_utc_iso(dt):
    return dt.isoformat() + "Z" if dt else ""

def create_reset_token(email: str):
    return jwt.encode({"sub": email, "exp": datetime.now(timezone.utc) + timedelta(minutes=30), "type": "reset"}, SECRET_KEY, algorithm=ALGORITHM)

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

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))



# ----------------------------------------------------------------------
# ROTA PRINCIPAL (FRONTEND)
# ----------------------------------------------------------------------
