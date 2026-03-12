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
    group = ChatGroup(name=d.name, creator_id=current_user.id, avatar_url=getattr(d, 'avatar_url', '') or '')
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
        "msg_vip_border": getattr(m, 'msg_vip_border', None) or 'none',
        "msg_vip_bubble": getattr(m, 'msg_vip_bubble', None) or 'none',
    } for m in msgs]

# ----------------------------------------------------------------------
# ENDPOINTS DE COMUNIDADES
# ----------------------------------------------------------------------



@router.get("/group/{group_id}")
def get_group_info(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # must be member
    is_member = db.query(GroupMember).filter_by(group_id=group_id, user_id=current_user.id).first()
    if not is_member:
        raise HTTPException(403, "Você não faz parte deste grupo")
    g = db.query(ChatGroup).filter_by(id=group_id).first()
    if not g:
        raise HTTPException(404, "Grupo não encontrado")
    members = db.query(User).join(GroupMember, GroupMember.user_id == User.id).filter(GroupMember.group_id == group_id).all()
    return {
        "id": g.id,
        "name": g.name,
        "creator_id": g.creator_id,
        "avatar": (g.avatar_url or ""),
        "members": [format_user_summary(u) for u in members],
    }


class UpdateGroupAvatarData(BaseModel):
    avatar_url: str = ""


@router.post("/group/{group_id}/avatar")
def update_group_avatar(
    group_id: int,
    d: UpdateGroupAvatarData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    g = db.query(ChatGroup).filter_by(id=group_id).first()
    if not g:
        raise HTTPException(404, "Grupo não encontrado")
    # only creator can change (fallback: allow any member if creator_id is null)
    if g.creator_id and g.creator_id != current_user.id:
        raise HTTPException(403, "Somente o criador pode alterar a foto do grupo")
    is_member = db.query(GroupMember).filter_by(group_id=group_id, user_id=current_user.id).first()
    if not is_member:
        raise HTTPException(403, "Você não faz parte deste grupo")
    g.avatar_url = (d.avatar_url or "")
    db.add(g)
    db.commit()
    return {"status": "ok", "avatar": g.avatar_url}


class GroupMemberChangeData(BaseModel):
    user_id: int


@router.post("/group/{group_id}/members/add")
def add_group_member(
    group_id: int,
    d: GroupMemberChangeData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    g = db.query(ChatGroup).filter_by(id=group_id).first()
    if not g:
        raise HTTPException(404, "Grupo não encontrado")
    if g.creator_id and g.creator_id != current_user.id:
        raise HTTPException(403, "Somente o criador pode adicionar membros")
    if not db.query(User).filter_by(id=d.user_id).first():
        raise HTTPException(404, "Usuário não encontrado")
    if db.query(GroupMember).filter_by(group_id=group_id, user_id=d.user_id).first():
        return {"status": "ok"}  # já é membro
    db.add(GroupMember(group_id=group_id, user_id=d.user_id))
    db.commit()
    return {"status": "ok"}


@router.post("/group/{group_id}/members/remove")
def remove_group_member(
    group_id: int,
    d: GroupMemberChangeData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    g = db.query(ChatGroup).filter_by(id=group_id).first()
    if not g:
        raise HTTPException(404, "Grupo não encontrado")
    if g.creator_id and g.creator_id != current_user.id:
        raise HTTPException(403, "Somente o criador pode remover membros")
    gm = db.query(GroupMember).filter_by(group_id=group_id, user_id=d.user_id).first()
    if not gm:
        return {"status": "ok"}
    db.delete(gm)
    db.commit()
    return {"status": "ok"}


@router.post("/group/{group_id}/leave")
def leave_group(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    gm = db.query(GroupMember).filter_by(group_id=group_id, user_id=current_user.id).first()
    if not gm:
        return {"status": "ok"}
    db.delete(gm)
    db.commit()
    return {"status": "ok"}

