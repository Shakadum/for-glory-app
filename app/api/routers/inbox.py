from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.get("/notifications")
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


@router.get("/inbox/unread")
def get_unread(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    unread_pms = db.query(PrivateMessage.sender_id).filter(PrivateMessage.receiver_id == uid, PrivateMessage.is_read == 0).all()
    counts = Counter([str(u[0]) for u in unread_pms])
    return {"total": sum(counts.values()), "by_sender": dict(counts)}


@router.get("/inbox")
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


@router.get("/dms/{target_id}")
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
        "can_delete": (datetime.now(timezone.utc) - ts_aware(m.timestamp)).total_seconds() <= 300,
        **format_user_summary(m.sender)
    } for m in msgs]


@router.post("/inbox/read/{sender_id}")
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


@router.post("/message/delete")
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
        if (datetime.now(timezone.utc) - ts_aware(msg.timestamp)).total_seconds() > 300:
            return {"status": "timeout", "msg": "Tempo limite excedido."}
        msg.content = "[DELETED]"
        db.commit()
        return {"status": "ok"}
    return {"status": "error"}

# ----------------------------------------------------------------------
# ENDPOINTS DE GRUPOS
# ----------------------------------------------------------------------

