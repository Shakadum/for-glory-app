from fastapi import APIRouter, Query, Body
from app.api.core import *

router = APIRouter()

@router.post("/call/ring/dm")
async def ring_dm(d: CallRingDMData, db: Session = Depends(get_db)):
    caller = db.query(User).filter_by(id=d.caller_id).first()
    if caller:
        await manager.send_personal({
            "type": "incoming_call",
            "caller_id": caller.id,
            "caller_name": caller.username,
            "caller_avatar": (caller.avatar_url or "/static/default-avatar.svg"),
            "channel_name": d.channel_name,
            "call_type": "dm",
            "target_id": d.target_id
        }, d.target_id)
    return {"status": "ok"}


@router.post("/call/ring/group")
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
                "caller_avatar": (caller.avatar_url or "/static/default-avatar.svg"),
                "channel_name": d.channel_name,
                "call_type": "group",
                "target_id": d.group_id
            }, m.user_id)
    return {"status": "ok"}




@router.get("/agora/token")
def agora_token(
    channel: str = Query(..., min_length=1),
    uid: str = Query(..., min_length=1),
    user=Depends(get_current_user),
):
    """Return an RTC token when AGORA_APP_CERT is configured.
    If your Agora project requires tokens, you MUST set AGORA_APP_CERT on the backend.
    """
    # Basic auth guard: only allow requesting token for yourself
    if str(user.id) != str(uid):
        raise HTTPException(status_code=403, detail="uid mismatch")

    from app.api.core import settings
    app_id = getattr(settings, "AGORA_APP_ID", None)
    app_cert = getattr(settings, "AGORA_APP_CERT", None)
    expire = int(getattr(settings, "AGORA_TOKEN_EXPIRE", 3600) or 3600)

    if not app_id:
        raise HTTPException(status_code=500, detail="AGORA_APP_ID not configured")

    if not app_cert:
        # Token-less join (works only if your Agora project does not require tokens)
        return {"app_id": app_id, "token": None, "expire_seconds": expire}

    token = build_rtc_token(RtcTokenOptions(app_id=app_id, app_cert=app_cert, channel=channel, uid=str(uid), expire_seconds=expire))
    return {"app_id": app_id, "token": token, "expire_seconds": expire}


@router.get("/agora-config")
def get_agora_config():
    return {"app_id": os.environ.get("AGORA_APP_ID", "")}


@router.post("/call/bg/set")
def set_call_bg(d: SetWallpaperData, db: Session = Depends(get_db)):
    bg = db.query(CallBackground).filter_by(target_type=d.target_type, target_id=d.target_id).first()
    if bg:
        bg.bg_url = d.bg_url
    else:
        db.add(CallBackground(target_type=d.target_type, target_id=d.target_id, bg_url=d.bg_url))
    db.commit()
    return {"status": "ok"}


@router.get("/call/bg/{target_type}/{target_id}")
def get_call_bg(target_type: str, target_id: str, db: Session = Depends(get_db)):
    bg = db.query(CallBackground).filter_by(target_type=target_type, target_id=target_id).first()
    return {"bg_url": bg.bg_url if bg else None}


@router.get("/call/bg/call/{channel_name}")
def get_call_bg_by_channel(channel_name: str, db: Session = Depends(get_db)):
    bg = db.query(CallBackground).filter_by(target_type="call", target_id=channel_name).first()
    return {"bg_url": bg.bg_url if bg else None}


@router.get("/call/bg/channel/{channel_id}")
def get_channel_bg(channel_id: int, db: Session = Depends(get_db)):
    bg = db.query(CallBackground).filter_by(target_type="channel", target_id=str(channel_id)).first()
    return {"bg_url": bg.bg_url if bg else None}

# ----------------------------------------------------------------------
# WEBSOCKET (COM TOKEN)
# ----------------------------------------------------------------------


# ─────────────────────────────────────────────────────────────
#  ACTIVE CALL TRACKER  (in-memory — resets on server restart)
# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
#  ACTIVE CALL TRACKER (in-memory — resets on server restart)
#  - Resolve "call fantasma": TTL + ping
# ─────────────────────────────────────────────────────────────
# channel_name -> {"started_at": float, "users": {user_id: last_seen_ts}}
_active_calls: dict = {}

def _prune_call(channel: str, ttl_seconds: int = 35):
    import time
    info = _active_calls.get(channel)
    if not info:
        return None
    now = time.time()
    users = info.get("users") or {}
    stale = [uid for uid, ts in users.items() if (now - float(ts or 0)) > ttl_seconds]
    for uid in stale:
        users.pop(uid, None)
    if not users:
        _active_calls.pop(channel, None)
        return None
    info["users"] = users
    return info

@router.post("/call/start")
async def call_start(d: dict = Body(...), user=Depends(get_current_user)):
    import time
    ch = str(d.get("channel", "")).strip()
    if not ch:
        raise HTTPException(400, "channel required")
    if ch not in _active_calls:
        _active_calls[ch] = {"started_at": time.time(), "users": {}}
    _active_calls[ch]["users"][user.id] = time.time()
    return {"status": "ok"}

@router.post("/call/ping")
async def call_ping(d: dict = Body(...), user=Depends(get_current_user)):
    """Refresh participation timestamp to avoid ghost calls when tabs suspend/close."""
    import time
    ch = str(d.get("channel", "")).strip()
    if not ch:
        raise HTTPException(400, "channel required")
    if ch not in _active_calls:
        _active_calls[ch] = {"started_at": time.time(), "users": {}}
    _active_calls[ch]["users"][user.id] = time.time()
    return {"status": "ok"}

@router.post("/call/end")
async def call_end(d: dict = Body(...), user=Depends(get_current_user)):
    ch = str(d.get("channel", "")).strip()
    info = _active_calls.get(ch)
    if info:
        users = info.get("users") or {}
        users.pop(user.id, None)
        if not users:
            _active_calls.pop(ch, None)
        else:
            info["users"] = users
    return {"status": "ok"}

@router.get("/call/active")
async def call_active(channel: str, user=Depends(get_current_user)):
    info = _prune_call(channel)
    if not info:
        return {"active": False}
    return {"active": True, "participants": len(info.get("users") or {})}
