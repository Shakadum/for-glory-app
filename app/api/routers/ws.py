"""
WebSocket unificado — corrigido e estável.

Fixes:
- Heartbeat ping/pong
- Presença online via Redis com TTL
- accept() SEMPRE primeiro (sem race condition)
- typing_start / typing_stop
- delete_msg broadcast
"""
from fastapi import APIRouter
from app.api.core import *
from app.core.redis import online_add, online_remove

router = APIRouter()


@router.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int):
    # ── 1. Accept PRIMEIRO ───────────────────────────────────────────────────
    await ws.accept()

    # ── 2. Validar token ─────────────────────────────────────────────────────
    token = ws.query_params.get("token")
    try:
        token_payload = verify_token(token)
        token_username = token_payload.get("sub")
    except Exception:
        await ws.send_text(json.dumps({"type": "error", "detail": "Token inválido"}))
        await ws.close(code=1008)
        return

    # ── 3. Validar usuário ───────────────────────────────────────────────────
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == uid).first()
        if not user or user.username != token_username:
            await ws.send_text(json.dumps({"type": "error", "detail": "Acesso negado"}))
            await ws.close(code=1008)
            return

    # ── 4. Registrar + marcar online ─────────────────────────────────────────
    manager.connect_accepted(ws, ch, uid)
    await online_add(uid)

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

            # Ping string legado
            if text_msg == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
                await online_add(uid)
                continue

            # Protocolos legados
            if text_msg.startswith("CALL_SIGNAL:"):
                parts = text_msg.split(":", 3)
                if len(parts) == 4:
                    try:
                        target_uid = int(parts[1])
                    except Exception:
                        continue
                    action = parts[2]
                    channel_name = parts[3]
                    type_map = {"accepted": "call_accepted", "rejected": "call_rejected", "cancelled": "call_cancelled"}
                    if action in type_map:
                        await manager.send_personal({"type": type_map[action], "channel": channel_name}, target_uid)
                continue

            if text_msg.startswith("SYNC_BG:"):
                parts = text_msg.split(":", 2)
                if len(parts) == 3:
                    await manager.broadcast({"type": "sync_bg", "channel": parts[1], "bg_url": parts[2]}, ch)
                continue

            if text_msg.startswith("KICK_CALL:"):
                parts = text_msg.split(":", 1)
                if len(parts) == 2:
                    try:
                        await manager.send_personal({"type": "kick_call", "from": uid}, int(parts[1]))
                    except Exception:
                        pass
                continue

            # Parse JSON
            try:
                data = json.loads(text_msg)
                if not isinstance(data, dict):
                    data = {"type": "msg", "content": str(data)}
            except Exception:
                data = {"type": "msg", "content": text_msg}

            msg_type = (data.get("type") or "msg").strip()

            if msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
                await online_add(uid)
                continue

            # Typing indicators
            if msg_type in ("typing_start", "typing_stop"):
                for conn in list(manager.active.get(ch, [])):
                    if conn is not ws:
                        try:
                            await conn.send_text(json.dumps({
                                "type": msg_type, "user_id": uid,
                                "username": data.get("username", ""),
                            }))
                        except Exception:
                            pass
                continue

            # Call signaling JSON
            if msg_type in {"call_invite", "call_accept", "call_reject", "call_end"}:
                to_uid = data.get("to")
                channel_name = data.get("channel")
                if not to_uid or not channel_name:
                    continue
                try:
                    to_uid = int(to_uid)
                except Exception:
                    continue
                type_map = {"call_invite": "incoming_call", "call_accept": "call_accepted",
                            "call_reject": "call_rejected", "call_end": "call_ended"}
                await manager.send_personal({"type": type_map[msg_type], "from": uid, "channel": channel_name}, to_uid)
                continue

            # Delete message
            if msg_type == "delete_msg":
                msg_id = data.get("msg_id")
                if msg_id:
                    await manager.broadcast({"type": "message_deleted", "msg_id": msg_id}, ch)
                continue

            # Normal message
            content = data.get("content")
            if content is None:
                continue
            content = str(content).strip()
            if not content:
                continue
            if len(content) > 2000:
                await ws.send_text(json.dumps({"type": "error", "detail": "Mensagem muito longa"}))
                continue

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
                    "avatar": u_sum.get("avatar_url") or sender.avatar_url or "",
                    "rank": u_sum.get("rank"),
                    "color": u_sum.get("color"),
                    "special_emblem": u_sum.get("special_emblem"),
                    "content": content,
                    "timestamp": now.isoformat(),
                    "can_delete": True,
                }

                if ch.startswith("dm_"):
                    parts = ch.split("_")
                    if len(parts) == 3:
                        a, b = int(parts[1]), int(parts[2])
                        to_uid = b if uid == a else a
                        pm = PrivateMessage(sender_id=uid, receiver_id=to_uid, content=content, timestamp=now)
                        db.add(pm); db.commit(); db.refresh(pm)
                        payload["id"] = pm.id
                        await manager.broadcast(payload, ch)
                        await manager.send_personal({**payload, "type": "new_dm"}, to_uid)
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

                payload["id"] = int(now.timestamp() * 1000)
                await manager.broadcast(payload, ch)

    except Exception:
        logger.exception("Erro no WebSocket uid=%s ch=%s", uid, ch)
    finally:
        manager.disconnect(ws, ch, uid)
        if not manager.user_ws.get(uid):
            await online_remove(uid)
