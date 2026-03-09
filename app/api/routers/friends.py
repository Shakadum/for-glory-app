from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.post("/friend/request")
@router.post("/friends/request")
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


@router.get("/friend/requests")
@router.get("/friends/requests")
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


@router.post("/friend/handle")
@router.post("/friends/handle")
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


@router.post("/friend/remove")
@router.post("/friends/remove")
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

