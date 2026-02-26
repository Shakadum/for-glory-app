from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.get("/users/me")
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

@router.post("/users/me/avatar")
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



@router.get("/users/id/{uid}")
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

@router.get("/users/basic/{uid}")
def get_user_basic(uid: int, db: Session = Depends(get_db)):
    return get_user_public(uid, db)


@router.post("/users/me/cover")
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



@router.get("/users/online")
async def get_online_users(db: Session = Depends(get_db)):
    active_uids = await online_list() or list(manager.user_ws.keys())
    if not active_uids:
        return []
    visible_users = db.query(User.id).filter(User.id.in_(active_uids), User.is_invisible == 0).all()
    return [u[0] for u in visible_users]


@router.get("/users/search")
def search_users(q: str, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.username.ilike(f"%{q}%")).limit(10).all()
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in users]


@router.post("/profile/stealth")
def toggle_stealth(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    current_user.is_invisible = 1 if current_user.is_invisible == 0 else 0
    db.commit()
    return {"is_invisible": current_user.is_invisible}


@router.post("/profile/update_meta")
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


@router.get("/user/{target_id}")
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

