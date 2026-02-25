from fastapi import APIRouter, Request
from app.api.core import *

router = APIRouter()

@router.post("/comment/delete")
async def delete_comment_legacy(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Endpoint legado usado pelo front antigo.

    Aceita JSON ou form-data e tolera chaves diferentes (comment_id, id, commentId).
    """
    try:
        data = await request.json()
        if not isinstance(data, dict):
            data = {}
    except Exception:
        try:
            form = await request.form()
            data = dict(form)
        except Exception:
            data = {}

    raw_id = (
        data.get("comment_id")
        or data.get("commentId")
        or data.get("id")
        or data.get("comment")
    )
    if raw_id is None:
        raise HTTPException(status_code=400, detail="comment_id missing")
    try:
        comment_id = int(raw_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid comment_id")

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
