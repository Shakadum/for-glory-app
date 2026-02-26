from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.post("/group/create")
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


@router.get("/group/{group_id}/messages")
def get_group_messages(
    group_id: int,
    db: Session = Depends(get_db)
):
    msgs = db.query(GroupMessage).filter_by(group_id=group_id).order_by(GroupMessage.timestamp.asc()).limit(100).all()
    return [{
        **format_user_summary(m.sender),
        "id": m.id,
        "user_id": m.sender_id,
        "content": m.content,
        "timestamp": get_utc_iso(m.timestamp),
        "avatar": m.sender.avatar_url,
        "username": m.sender.username,
        "can_delete": (datetime.now(timezone.utc) - ts_aware(m.timestamp)).total_seconds() <= 300,
    } for m in msgs]

# ----------------------------------------------------------------------
# ENDPOINTS DE COMUNIDADES
# ----------------------------------------------------------------------

