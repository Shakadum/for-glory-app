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

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_NAME', 'dqa0q3qlx'),
    api_key=os.environ.get('CLOUDINARY_KEY', ''),
    api_secret=os.environ.get('CLOUDINARY_SECRET', ''),
    secure=True
)

# ----------------------------------------------------------------------
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
app = FastAPI(title="For Glory Cloud")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get('/health')
def health():
    return {'status': 'ok'}


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
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Faz upload de arquivo para o Cloudinary.
    Retorna a URL segura (https) e metadados básicos.
    """
    try:
        filename = (file.filename or "").lower()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        allowed = {"png","jpg","jpeg","gif","webp","mp4","mov","webm","mp3","wav","ogg","m4a","pdf"}
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido")

        # garante config do Cloudinary (usa env vars)
        try:
            init_cloudinary()
        except Exception as e:
            logger.exception("Cloudinary não configurado")
            raise HTTPException(status_code=500, detail="Cloudinary não configurado") from e

        # lê bytes
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        # upload
        result = cloudinary.uploader.upload(
            data,
            resource_type="auto",
            folder="uploads",
            use_filename=True,
            unique_filename=True,
            overwrite=False,
        )

        return {
            "url": result.get("secure_url") or result.get("url"),
            "public_id": result.get("public_id"),
            "resource_type": result.get("resource_type"),
            "bytes": result.get("bytes"),
            "format": result.get("format"),
            "original_filename": result.get("original_filename"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao fazer upload")
        raise HTTPException(status_code=500, detail="Falha no upload") from e
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
@app.post("/users/me/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Upload to Cloudinary and persist URL
    try:
        init_cloudinary()
        res = cloudinary.uploader.upload(
            await file.read(),
            folder=f"forglory/avatars/{current_user.id}",
            resource_type="image",
        )
        url = res.get("secure_url") or res.get("url")
        if not url:
            raise HTTPException(status_code=500, detail="Cloudinary did not return URL")
        current_user.avatar_url = url
        db.add(current_user)
        db.commit()
        return {"avatar_url": url}
    except Exception as e:
        logger.exception("Avatar upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Avatar upload failed")


@app.get("/users/id/{uid}")
def get_user_public(uid: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    s = format_user_summary(u)
    return {
        "id": u.id,
        "username": u.username,
        "avatar_url": u.avatar_url,
        "cover_url": u.cover_url,
        "bio": u.bio,
        "xp": u.xp,
        "rank": s.get("rank") or compute_rank(u.xp),
        "rank_color": s.get("color") or "#2ecc71",
        "special_emblem": s.get("special_emblem") or "",
    }


# compat: front-end antigo usa /users/basic/{uid}
@app.get("/users/basic/{uid}")
def get_user_basic(uid: int, db: Session = Depends(get_db)):
    return get_user_public(uid, db)

@app.post("/users/me/cover")
async def upload_my_cover(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        init_cloudinary()
        res = cloudinary.uploader.upload(
            await file.read(),
            folder=f"forglory/covers/{current_user.id}",
            resource_type="image",
        )
        url = res.get("secure_url") or res.get("url")
        if not url:
            raise HTTPException(status_code=500, detail="Cloudinary did not return URL")
        current_user.cover_url = url
        db.add(current_user)
        db.commit()
        return {"cover_url": url}
    except Exception as e:
        logger.exception("Cover upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Cover upload failed")


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
async def update_prof_meta(
    request: Request,
    avatar_url: Optional[str] = Form(None),
    cover_url: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Atualiza metadados do perfil.

    Aceita tanto JSON (fetch) quanto form-data (form HTML).
    """
    if avatar_url is None and cover_url is None and bio is None:
        try:
            payload = await request.json()
            avatar_url = payload.get("avatar_url")
            cover_url = payload.get("cover_url")
            bio = payload.get("bio")
        except Exception:
            pass

    if avatar_url:
        current_user.avatar_url = avatar_url
    if cover_url:
        current_user.cover_url = cover_url
    if bio is not None:
        current_user.bio = bio
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
    posts_data = []
    for p in posts:
        cu = (getattr(p, "content_url", None) or getattr(p, "media_url", None) or getattr(p, "url", None) or "").strip()
        cap = getattr(p, "caption", None) or getattr(p, "text", None) or ""
        ts = getattr(p, "timestamp", None) or getattr(p, "created_at", None) or getattr(p, "created", None)
        created = ts.isoformat() if hasattr(ts, "isoformat") and ts else (str(ts) if ts else None)
        posts_data.append({
            "id": p.id,
            "content_url": cu if cu else None,
            "media_type": getattr(p, "media_type", None) or "image",
            "caption": cap if cap else None,
            "created_at": created,
        })
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
    db.add(Post(user_id=current_user.id, content_url=d.content_url, media_type=d.media_type, caption=d.caption, timestamp=datetime.utcnow()))
    current_user.xp += 50
    db.commit()
    return {"status": "ok"}

# ----------------------------------------------------------------------
# FRONTEND COMPAT: the UI calls POST /post with the same payload used by
# /post/create_from_url. Without this alias the browser gets 404 and it looks
# like "não publica".
@app.post("/post")
def create_post_alias(
    d: CreatePostData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return create_post_url(d=d, current_user=current_user, db=db)

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
def get_posts(uid: Optional[int] = None, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Retorna feed de posts.

    Observação: o schema real do banco (Post) usa os campos:
      - media_url / media_type / text / created_at / user_id

    O front antigo esperava `content_url` e `caption`, então fazemos o mapeamento.
    Também evitamos 500 por campos inexistentes.
    """

    try:
        posts_q = db.query(Post).options(joinedload(Post.author))
        if uid is not None:
            posts_q = posts_q.filter(Post.user_id == uid)
        posts = (
            posts_q
            .order_by(Post.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        post_ids = [p.id for p in posts]
        likes_bulk = (
            db.query(Like.post_id, Like.user_id)
            .filter(Like.post_id.in_(post_ids))
            .all()
            if post_ids
            else []
        )
        comments_count = (
            db.query(Comment.post_id, func.count(Comment.id))
            .filter(Comment.post_id.in_(post_ids))
            .group_by(Comment.post_id)
            .all()
            if post_ids
            else []
        )
        comments_dict = dict(comments_count)

        result = []
        for p in posts:
            post_likes = [l for l in likes_bulk if l[0] == p.id]
            author = getattr(p, "author", None)
            u_sum = format_user_summary(author) if author else {
                "username": "?",
                "avatar_url": None,
                "rank": "",
                "color": "#888",
                "special_emblem": None,
            }

            result.append(
                {
                    "id": p.id,
                        # Compat: nosso model/tabela usa posts.content_url, posts.caption, posts.timestamp.
                        # Algumas versões antigas do front esperavam media_url/text/created_at.
                        "content_url": (getattr(p, "content_url", None) or getattr(p, "media_url", None) or "").strip() if isinstance((getattr(p, "content_url", None) or getattr(p, "media_url", None) or ""), str) else (getattr(p, "content_url", None) or getattr(p, "media_url", None) or ""),
                        "media_type": getattr(p, "media_type", None),
                        "caption": getattr(p, "caption", None) or getattr(p, "text", None),
                        "created_at": (
                            getattr(p, "timestamp", None).isoformat()
                            if getattr(p, "timestamp", None)
                            else (p.created_at.isoformat() if getattr(p, "created_at", None) else None)
                        ),
                    "author_name": u_sum["username"],
                    "author_avatar": u_sum["avatar_url"],
                    "author_rank": u_sum["rank"],
                    "rank_color": u_sum["color"],
                    "special_emblem": u_sum["special_emblem"],
                    "author_id": getattr(p, "user_id", None),
                    "likes": len(post_likes),
                    "user_liked": any(l[1] == uid for l in post_likes),
                    "comments": comments_dict.get(p.id, 0),
                }
            )

        return result
    except Exception as e:
        logger.exception(f"❌ Erro em /posts (uid={uid}): {e}")
        return []

# ----------------------------------------------------------------------
# ENDPOINTS DE AMIZADE
# ----------------------------------------------------------------------
@app.post("/friend/request")
@app.post("/friends/request")
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
@app.get("/friends/requests")
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
@app.post("/friends/handle")
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
@app.post("/friends/remove")
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
    """WebSocket por canal + usuário.

    Importante: com múltiplas instâncias, você precisa de um 'backplane' (Redis/pubsub)
    para broadcast entre instâncias. Este handler funciona para 1 instância.
    """
    # valida token (query ?token=...)
    # Em WebSocket, o FastAPI NÃO injeta query params como argumento da função.
    # Então precisamos ler manualmente de ws.query_params.
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=1008)
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            await ws.close(code=1008)
            return

        # `sub` may be username (older tokens) or numeric user id (newer tokens)
        token_uid = None
        token_username = None
        try:
            token_uid = int(sub)
        except (TypeError, ValueError):
            token_username = str(sub)

        if token_uid is not None:
            if token_uid != int(uid):
                await ws.close(code=1008)
                return
        else:
            with SessionLocal() as db:
                u = db.query(User).filter(User.username == token_username).first()
                if not u or u.id != int(uid):
                    await ws.close(code=1008)
                    return
    except Exception:
        await ws.close(code=1008)
        return

    # valida usuário no DB
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == uid).first()
            if not user:
                await ws.close(code=1008)
                return

        # conecta (faz accept dentro do manager)
        # ConnectionManager.connect espera (ws, chan, uid)
        await manager.connect(ws, ch, uid)

        while True:
            msg = await ws.receive()
            text_msg = (msg.get("text") or "").strip()
            if not text_msg:
                # ignora pings/frames vazios
                continue

            # Aceita JSON estruturado *ou* string pura (compat com front antigo)
            try:
                data = json.loads(text_msg)
                if not isinstance(data, dict):
                    data = {"type": "msg", "content": str(data)}
            except Exception:
                data = {"type": "msg", "content": text_msg}

            msg_type = (data.get("type") or "msg").strip()
            if msg_type == "ping":
                await manager.broadcast({"type": "pong"}, ch)
                continue

            content = (data.get("content") or "").strip()
            if not content:
                continue

            # Persistência + payload compatível com o front
            with SessionLocal() as db:
                sender = db.query(User).filter(User.id == uid).first()
                if not sender:
                    continue
                u_sum = format_user_summary(sender)

                now = datetime.now(timezone.utc)

                payload = {
                    "type": "msg",
                    "user_id": uid,
                    "username": u_sum.get("username") or sender.username,
                    "avatar": u_sum.get("avatar_url") or sender.avatar_url,
                    "rank": u_sum.get("rank"),
                    "color": u_sum.get("color"),
                    "special_emblem": u_sum.get("special_emblem"),
                    "content": content,
                    "timestamp": now.isoformat(),
                    "can_delete": True,
                }

                # Roteamento por prefixo do canal (dm_, group_, comm_)
                if ch.startswith("dm_"):
                    # dm_{min}_{max}
                    parts = ch.split("_")
                    if len(parts) == 3:
                        a = int(parts[1]); b = int(parts[2])
                        to_uid = b if uid == a else a
                        pm = PrivateMessage(sender_id=uid, receiver_id=to_uid, content=content, timestamp=now)
                        db.add(pm); db.commit(); db.refresh(pm)
                        payload["id"] = pm.id
                        await manager.broadcast(payload, ch)
                        # também notifica no WS "Geral" do destinatário (badge/unread)
                        await manager.send_personal({"type": "dm_notify", "from_uid": uid}, to_uid)
                        continue

                if ch.startswith("group_"):
                    # group_{id}
                    parts = ch.split("_")
                    if len(parts) == 2:
                        gid = int(parts[1])
                        gm = GroupMessage(group_id=gid, sender_id=uid, content=content, timestamp=now)
                        db.add(gm); db.commit(); db.refresh(gm)
                        payload["id"] = gm.id
                        await manager.broadcast(payload, ch)
                        continue

                if ch.startswith("comm_"):
                    # comm_{channelId}
                    parts = ch.split("_")
                    if len(parts) == 2:
                        channel_id = int(parts[1])
                        cm = CommunityMessage(channel_id=channel_id, sender_id=uid, content=content, timestamp=now)
                        db.add(cm); db.commit(); db.refresh(cm)
                        payload["id"] = cm.id
                        await manager.broadcast(payload, ch)
                        continue

                # fallback: broadcast simples
                payload["id"] = int(now.timestamp() * 1000)
                await manager.broadcast(payload, ch)

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Erro no WebSocket")
    finally:
        manager.disconnect(ws, ch, uid)
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))



# ----------------------------------------------------------------------
# ROTA PRINCIPAL (FRONTEND)
# ----------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    # Mantemos server-side template pronto (mesmo que hoje não injete variáveis)
    # Isso facilita futuras configs por ambiente, feature flags, etc.
    return templates.TemplateResponse("index.html", {"request": request})

