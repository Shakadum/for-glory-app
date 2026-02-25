from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.post("/upload")
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

@router.post("/post/create_from_url")
def create_post_url(
    d: CreatePostData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db.add(Post(user_id=current_user.id, content_url=d.content_url, media_type=d.media_type, caption=d.caption, timestamp=datetime.now(timezone.utc)))
    current_user.xp += 50
    db.commit()
    return {"status": "ok"}

# ----------------------------------------------------------------------
# FRONTEND COMPAT: the UI calls POST /post with the same payload used by
# /post/create_from_url. Without this alias the browser gets 404 and it looks
# like "não publica".

@router.post("/post")
def create_post_alias(
    d: CreatePostData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return create_post_url(d=d, current_user=current_user, db=db)


@router.post("/post/like")
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


@router.post("/post/comment")
def add_comment(
    d: CommentData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db.add(Comment(user_id=current_user.id, post_id=d.post_id, text=d.text))
    db.commit()
    return {"status": "ok"}


@router.post("/post/delete")
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


@router.get("/post/{post_id}/comments")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).filter_by(post_id=post_id).order_by(Comment.timestamp.asc()).all()
    return [{"id": c.id, "text": c.text, "author_name": c.author.username, "author_avatar": c.author.avatar_url, "author_id": c.author.id, **format_user_summary(c.author)} for c in comments]


@router.get("/posts")
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

