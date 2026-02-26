from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.websocket("/ws/{ch}/{uid}")
async def ws_end(ws: WebSocket, ch: str, uid: int):
    """WebSocket por canal + usuário.

    IMPORTANTE: accept() sempre vem PRIMEIRO.
    Fechar sem accept() resulta em 403 no cliente (Starlette/FastAPI).

    Protocolos suportados:
      - JSON estruturado: {"type": "msg", "content": "..."}
      - Strings legadas: CALL_SIGNAL:uid:action:channel | SYNC_BG:channel:url | KICK_CALL:uid
    """
    # ── 1. Aceitar ANTES de qualquer validação ───────────────────────────────
    await ws.accept()

    # ── 2. Validar token ────────────────────────────────────────────────────
    token = ws.query_params.get("token")
    try:
        token_payload = verify_token(token)
        token_username = token_payload.get("sub")
    except Exception:
        await ws.send_text(json.dumps({"type": "error", "detail": "Token inválido"}))
        await ws.close(code=1008)
        return

    # ── 3. Validar usuário e conferir que uid da URL bate com o token ────────
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == uid).first()
        if not user or user.username != token_username:
            await ws.send_text(json.dumps({"type": "error", "detail": "Acesso negado"}))
            await ws.close(code=1008)
            return

    # ── 4. Registrar conexão (já aceita) ─────────────────────────────────────
    manager.connect_accepted(ws, ch, uid)

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

            # ── Protocolos legados (string pura) ────────────────────────────
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
                    await manager.broadcast({"type": "sync_bg", "channel": parts[1], "bg_url": parts[2]}, ch)
                continue

            if text_msg.startswith("KICK_CALL:"):
                parts = text_msg.split(":", 1)
                if len(parts) == 2:
                    try:
                        target_uid = int(parts[1])
                        await manager.send_personal({"type": "kick_call", "from": uid}, target_uid)
                    except Exception:
                        pass
                continue

            # ── JSON estruturado ou string pura ─────────────────────────────
            try:
                data = json.loads(text_msg)
                if not isinstance(data, dict):
                    data = {"type": "msg", "content": str(data)}
            except Exception:
                data = {"type": "msg", "content": text_msg}

            msg_type = (data.get("type") or "msg").strip()

            if msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
                continue

            # ── Sinalização de chamada ───────────────────────────────────────
            if msg_type in {"call_invite", "call_accept", "call_reject", "call_end"}:
                to_uid = data.get("to")
                channel_name = data.get("channel")
                if not to_uid or not channel_name:
                    continue
                try:
                    to_uid = int(to_uid)
                except Exception:
                    continue
                type_map = {
                    "call_invite": "incoming_call",
                    "call_accept": "call_accepted",
                    "call_reject": "call_rejected",
                    "call_end":    "call_ended",
                }
                await manager.send_personal({"type": type_map[msg_type], "from": uid, "channel": channel_name}, to_uid)
                continue

            # ── Mensagem normal ──────────────────────────────────────────────
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
                    "avatar": u_sum.get("avatar_url") or sender.avatar_url,
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
                        # notifica o destinatário em qualquer canal que ele esteja
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

                # fallback (canal global / status)
                payload["id"] = int(now.timestamp() * 1000)
                await manager.broadcast(payload, ch)

    except Exception:
        logger.exception("Erro no WebSocket uid=%s ch=%s", uid, ch)
    finally:
        manager.disconnect(ws, ch, uid)
