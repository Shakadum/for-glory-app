from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int):
    """WebSocket por canal + usuário (single instance).

    Aceita JSON estruturado OU string pura (compat com front antigo).
    Também aceita protocolos legados por prefixo:
      - CALL_SIGNAL:{targetUid}:{accepted|rejected|cancelled}:{channel}
      - SYNC_BG:{channel}:{bg_url}
      - KICK_CALL:{targetUid}
    """
    # valida token
    try:
        token = ws.query_params.get("token")
        _ = verify_token(token)
    except Exception:
        await ws.close(code=1008)
        return

    # valida usuário
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            await ws.close(code=1008)
            return

    await manager.connect(ws, ch, uid)

    try:
        while True:
            try:
                text_msg = await ws.receive_text()
            except WebSocketDisconnect:
                break
            except RuntimeError:
                break

            text_msg = (text_msg or "").strip()
            if not text_msg:
                continue

            # ------------------ Protocolos legados (strings) ------------------
            if text_msg.startswith("CALL_SIGNAL:"):
                parts = text_msg.split(":", 3)
                if len(parts) == 4:
                    try:
                        target_uid = int(parts[1])
                    except Exception:
                        continue
                    action = parts[2]
                    channel_name = parts[3]
                    if action == "accepted":
                        await manager.send_personal({"type": "call_accepted", "channel": channel_name}, target_uid)
                    elif action == "rejected":
                        await manager.send_personal({"type": "call_rejected", "channel": channel_name}, target_uid)
                    elif action == "cancelled":
                        await manager.send_personal({"type": "call_cancelled", "channel": channel_name}, target_uid)
                continue

            if text_msg.startswith("SYNC_BG:"):
                parts = text_msg.split(":", 2)
                if len(parts) == 3:
                    channel_name = parts[1]
                    bg_url = parts[2]
                    await manager.broadcast({"type": "sync_bg", "channel": channel_name, "bg_url": bg_url}, ch)
                continue

            if text_msg.startswith("KICK_CALL:"):
                parts = text_msg.split(":", 1)
                if len(parts) == 2:
                    try:
                        target_uid = int(parts[1])
                    except Exception:
                        continue
                    await manager.send_personal({"type": "kick_call", "from": uid}, target_uid)
                continue

            # ------------------ JSON estruturado OU string pura ------------------
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

            # ------------------ sinalização de call (novo) ------------------
            if msg_type in {"call_invite", "call_accept", "call_reject", "call_end"}:
                to_uid = data.get("to")
                channel_name = data.get("channel")
                if not to_uid or not channel_name:
                    continue
                try:
                    to_uid = int(to_uid)
                except Exception:
                    continue

                if msg_type == "call_invite":
                    await manager.send_personal({"type": "incoming_call", "from": uid, "channel": channel_name}, to_uid)
                elif msg_type == "call_accept":
                    await manager.send_personal({"type": "call_accepted", "from": uid, "channel": channel_name}, to_uid)
                elif msg_type == "call_reject":
                    await manager.send_personal({"type": "call_rejected", "from": uid, "channel": channel_name}, to_uid)
                elif msg_type == "call_end":
                    await manager.send_personal({"type": "call_ended", "from": uid, "channel": channel_name}, to_uid)
                continue

            # ------------------ mensagem normal ------------------
            content = data.get("content")
            if content is None:
                continue
            if not isinstance(content, str):
                content = str(content)
            content = content.strip()
            if not content:
                continue
            if len(content) > 2000:
                await ws.send_text(json.dumps({"type": "error", "detail": "Mensagem muito longa"}))
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
                    parts = ch.split("_")
                    if len(parts) == 3:
                        a = int(parts[1]); b = int(parts[2])
                        to_uid = b if uid == a else a
                        pm = PrivateMessage(sender_id=uid, receiver_id=to_uid, content=content, timestamp=now)
                        db.add(pm); db.commit(); db.refresh(pm)
                        payload["id"] = pm.id
                        await manager.broadcast(payload, ch)
                        await manager.send_personal(payload, to_uid)
                        continue

                if ch.startswith("group_"):
                    parts = ch.split("_")
                    if len(parts) == 2:
                        gid = int(parts[1])
                        gm = GroupMessage(group_id=gid, sender_id=uid, content=content, timestamp=now)
                        db.add(gm); db.commit(); db.refresh(gm)
                        payload["id"] = gm.id
                        await manager.broadcast(payload, ch)
                        continue

                if ch.startswith("comm_"):
                    parts = ch.split("_")
                    if len(parts) == 2:
                        channel_id = int(parts[1])
                        cm = CommunityMessage(channel_id=channel_id, sender_id=uid, content=content, timestamp=now)
                        db.add(cm); db.commit(); db.refresh(cm)
                        payload["id"] = cm.id
                        await manager.broadcast(payload, ch)
                        continue

                # fallback
                payload["id"] = int(now.timestamp() * 1000)
                await manager.broadcast(payload, ch)

    except Exception:
        logger.exception("Erro no WebSocket")
    finally:
        manager.disconnect(ws, ch, uid)
