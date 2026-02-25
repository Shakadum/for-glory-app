from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.post("/community/create")
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


@router.post("/community/join")
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


@router.post("/community/{cid}/leave")
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


@router.post("/community/edit")
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


@router.post("/community/{cid}/delete")
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


@router.post("/community/member/promote")
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


@router.post("/community/member/demote")
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


@router.post("/community/member/kick")
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


@router.get("/communities/list")
def list_comms(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    uid = current_user.id
    my_comm_ids = [m.comm_id for m in db.query(CommunityMember).filter_by(user_id=uid).all()]
    return {"my_comms": [{"id": c.id, "name": c.name, "avatar_url": c.avatar_url} for c in db.query(Community).filter(Community.id.in_(my_comm_ids)).all()]}


@router.get("/communities/search")
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


@router.post("/community/request/send")
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


@router.get("/community/{cid}/requests")
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


@router.post("/community/request/handle")
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


@router.get("/community/{cid}")
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


@router.post("/community/channel/create")
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


@router.post("/community/channel/edit")
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


@router.post("/community/channel/{chid}/delete")
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


@router.get("/community/channel/{chid}/messages")
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

