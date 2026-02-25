from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int):
    """WebSocket por canal + usuário.

    Importante: com múltiplas instâncias, você precisa de um 'backplane' (Redis/pubsub)
    para broadcast entre instâncias. Este handler funciona para 1 instância.
    """
    # valida token (query ?token=...)
    # Em WebSocket, o FastAPI NÃO injeta query params como argumento da função.
    # Então precisamos ler manualmente de ws.query_params.
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=1008)
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            await ws.close(code=1008)
            return

        # `sub` may be username (older tokens) or numeric user id (newer tokens)
        token_uid = None
        token_username = None
        try:
            token_uid = int(sub)
        except (TypeError, ValueError):
            token_username = str(sub)

        if token_uid is not None:
            if token_uid != int(uid):
                await ws.close(code=1008)
                return
        else:
            with SessionLocal() as db:
                u = db.query(User).filter(User.username == token_username).first()
                if not u or u.id != int(uid):
                    await ws.close(code=1008)
                    return
    except Exception:
        await ws.close(code=1008)
        return

    # valida usuário no DB
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == uid).first()
            if not user:
                await ws.close(code=1008)
                return

        # conecta (faz accept dentro do manager)
        # ConnectionManager.connect espera (ws, chan, uid)
        await manager.connect(ws, ch, uid)

        while True:
            msg = await ws.receive()
            text_msg = (msg.get("text") or "").strip()
            if not text_msg:
                # ignora pings/frames vazios
                continue

            # Aceita JSON estruturado *ou* string pura (compat com front antigo)
            try:
                data = json.loads(text_msg)
                if not isinstance(data, dict):
                    data = {"type": "msg", "content": str(data)}
            except Exception:
                data = {"type": "msg", "content": text_msg}

            msg_type = (data.get("type") or "msg").strip()
            if msg_type == "ping":
                await manager.broadcast({"type": "pong"}, ch)
                continue

            content = data.get("content")

            # validações
            if content is None:
                continue

            if not isinstance(content, str):
                content = str(content)

            content = content.strip()
            if not content:
                continue

            if len(content) > 2000:
                await ws.send_json({"type": "error", "detail": "Mensagem muito longa"})
                continue

            # Persistência + payload compatível com o front
            with SessionLocal() as db:
                sender = db.query(User).filter(User.id == uid).first()
                if not sender:
                    continue
                u_sum = format_user_summary(sender)

                now = datetime.now(timezone.utc)

                payload = {
                    "type": "msg",
                    "user_id": uid,
                    "username": u_sum.get("username") or sender.username,
                    "avatar": u_sum.get("avatar_url") or sender.avatar_url,
                    "rank": u_sum.get("rank"),
                    "color": u_sum.get("color"),
                    "special_emblem": u_sum.get("special_emblem"),
                    "content": content,
                    "timestamp": now.isoformat(),
                    "can_delete": True,
                }

                # Roteamento por prefixo do canal (dm_, group_, comm_)
                if ch.startswith("dm_"):
                    # dm_{min}_{max}
                    parts = ch.split("_")
                    if len(parts) == 3:
                        a = int(parts[1]); b = int(parts[2])
                        to_uid = b if uid == a else a
                        pm = PrivateMessage(sender_id=uid, receiver_id=to_uid, content=content, timestamp=now)
                        db.add(pm); db.commit(); db.refresh(pm)
                        payload["id"] = pm.id
                        # broadcast para quem estiver com o DM aberto
                        await manager.broadcast(payload, ch)
                        # entrega direta (garante DM mesmo se o destinatário não estiver no canal dm_)
                        await manager.send_personal(payload, to_uid)
                        continue

                if ch.startswith("group_"):
                    # group_{id}
                    parts = ch.split("_")
                    if len(parts) == 2:
                        gid = int(parts[1])
                        gm = GroupMessage(group_id=gid, sender_id=uid, content=content, timestamp=now)
                        db.add(gm); db.commit(); db.refresh(gm)
                        payload["id"] = gm.id
                        await manager.broadcast(payload, ch)
                        continue

                if ch.startswith("comm_"):
                    # comm_{channelId}
                    parts = ch.split("_")
                    if len(parts) == 2:
                        channel_id = int(parts[1])
                        cm = CommunityMessage(channel_id=channel_id, sender_id=uid, content=content, timestamp=now)
                        db.add(cm); db.commit(); db.refresh(cm)
                        payload["id"] = cm.id
                        await manager.broadcast(payload, ch)
                        continue

                # fallback: broadcast simples
                payload["id"] = int(now.timestamp() * 1000)
                await manager.broadcast(payload, ch)

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Erro no WebSocket")
    finally:
        manager.disconnect(ws, ch, uid)
