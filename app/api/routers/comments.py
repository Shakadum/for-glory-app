from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.post("/comment/delete")
def delete_comment_legacy(
    d: DelCommentData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    c = db.query(Comment).filter(Comment.id == d.comment_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    if c.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para apagar este comentário")
    post_id = c.post_id
    db.delete(c)
    db.commit()
    count = db.query(Comment).filter(Comment.post_id == post_id).count()
    return {"status": "ok", "post_id": post_id, "comment_count": count}

@router.delete("/comments/{comment_id}")
def delete_comment_rest(
    comment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    c = db.query(Comment).filter(Comment.id == comment_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    if c.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para apagar este comentário")
    post_id = c.post_id
    db.delete(c)
    db.commit()
    count = db.query(Comment).filter(Comment.post_id == post_id).count()
    return {"status": "ok", "post_id": post_id, "comment_count": count}
