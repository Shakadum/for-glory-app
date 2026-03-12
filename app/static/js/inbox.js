// ═══════════════════════════════════════════════════════════════
// FOR GLORY — INBOX — DMs, Grupos, Status Online, Unread
// Gerado por splitter v2 — extração correta por profundidade de chaves
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */

async function fetchOnlineUsers(){ if(!user)return; try{ let r=await fetch(`/users/online?nocache=${new Date().getTime()}`); window.onlineUsers=await r.json(); updateStatusDots(); }catch(e){ console.error(e); } }

async function fetchUnread(){
    if(!user) return;
    try {
        let r = await fetch(`/notifications?nocache=${new Date().getTime()}`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        let d = await r.json(); 
        window.unreadData = d.dms.by_sender || {};
        let badgeInbox = document.getElementById('inbox-badge');
        if(d.dms.total > 0) { badgeInbox.innerText = d.dms.total; badgeInbox.style.display = 'block'; } else { badgeInbox.style.display = 'none'; }
        
        let badgeBases = document.getElementById('bases-badge');
        if(d.comms.total > 0) { badgeBases.innerText = d.comms.total; badgeBases.style.display = 'block'; } else { badgeBases.style.display = 'none'; }
        
        let badgeProfile = document.getElementById('profile-badge');
        if(d.friend_reqs > 0) { badgeProfile.innerText = d.friend_reqs; badgeProfile.style.display = 'block'; } else { badgeProfile.style.display = 'none'; }

        window.lastTotalUnread = d.dms.total;
        if(document.getElementById('view-inbox').classList.contains('active')) {
            document.querySelectorAll('.inbox-item').forEach(item => { let sid = item.getAttribute('data-id'); let type = item.getAttribute('data-type'); let b = item.querySelector('.list-badge'); if(type === '1v1' && window.unreadData[sid]) { b.innerText = window.unreadData[sid]; b.style.display = 'block'; } else if(b) { b.style.display = 'none'; } });
        }
        if(document.getElementById('view-mycomms').classList.contains('active')) {
            document.querySelectorAll('.comm-card').forEach(card => { let cid = card.getAttribute('data-id'); let dot = card.querySelector('.req-dot'); if(d.comms.by_comm[cid]) { if(dot) dot.style.display='block'; } else { if(dot) dot.style.display='none'; } });
        }
    } catch(e) { console.error(e);
        const badgeInbox = document.getElementById('inbox-badge');
        const badgeBases = document.getElementById('bases-badge');
        const badgeProfile = document.getElementById('profile-badge');
        if (badgeInbox) badgeInbox.style.display = 'none';
        if (badgeBases) badgeBases.style.display = 'none';
        if (badgeProfile) badgeProfile.style.display = 'none';
        window.unreadData = {};
        window.lastTotalUnread = 0;
    }
}

async function loadInbox(){
    try {
        await fetchUnread();
        let r = await fetch('/inbox?nocache=' + new Date().getTime(), { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        let d = await r.json();
        let b = document.getElementById('inbox-list'); b.innerHTML = '';
        if((d.groups || []).length === 0 && (d.friends || []).length === 0) { b.innerHTML = `<p style='text-align:center;color:#888;margin-top:20px;'>${t('empty_box')}</p>`; return; }
        (d.groups || []).forEach(g => {
            const previews = (g.member_previews || []).slice(0, 4);
            const extraCount = (g.member_count || 0) - previews.length;
            const avatarsHtml = previews.map((m, i) =>
                `<img class="squad-av-preview" src="${safeAvatarUrl(m.avatar)}" style="z-index:${previews.length - i}" onerror="this.src='/static/default-avatar.svg'">`
            ).join('') + (extraCount > 0 ? `<span class="squad-av-extra">+${extraCount}</span>` : '');

            b.innerHTML += `
            <div class="inbox-item squad-card" data-id="${g.id}" data-type="group" onclick="openChat(${g.id}, '${g.name.replace(/'/g, "\\'")}', 'group', '${g.avatar}')">
                <div class="squad-card-left">
                    <div class="squad-avatar-wrap">
                        <img class="squad-avatar" src="${safeAvatarUrl(g.avatar)}" onerror="this.src='/static/default-avatar.svg'">
                        <span class="squad-icon-badge">
                            <svg width="9" height="9" viewBox="0 0 24 24" fill="currentColor"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                        </span>
                    </div>
                    <div class="squad-info">
                        <div class="squad-name">${escapeHtml(g.name)}</div>
                        <div class="squad-meta">
                            <div class="squad-av-stack">${avatarsHtml}</div>
                            <span class="squad-count">${g.member_count || 0} membros</span>
                        </div>
                    </div>
                </div>
                <svg class="squad-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
            </div>`;
        });
        (d.friends || []).forEach(f => {
            let unreadCount = (window.unreadData && window.unreadData[String(f.id)]) ? window.unreadData[String(f.id)] : 0; let badgeDisplay = unreadCount > 0 ? 'block' : 'none';
            b.innerHTML += `<div class="inbox-item" data-id="${f.id}" data-type="1v1" style="display:flex;align-items:center;gap:15px;padding:12px;background:rgba(255,255,255,0.05);border-radius:12px;cursor:pointer;" onclick="openChat(${f.id}, '${f.name}', '1v1', '${safeAvatarUrl(f.avatar, f.name)}')"><div class="av-wrap"><img src="${safeAvatarUrl(f.avatar, f.name)}" style="width:45px;height:45px;border-radius:50%;object-fit:cover;" onerror="this.src='/static/default-avatar.svg'"><div class="status-dot" data-uid="${f.id}"></div></div><div style="flex:1;"><b style="color:white;font-size:16px;">${f.name}</b><br><span style="font-size:12px;color:#888;">${t('direct_msg')}</span></div><div class="list-badge" style="display:${badgeDisplay}; background:#ff5555; color:white; font-size:12px; font-weight:bold; padding:4px 10px; border-radius:12px; box-shadow:0 0 8px rgba(255,85,85,0.6);">${unreadCount}</div></div>`;
        });
        updateStatusDots();
    } catch(e) { console.error(e); }
}

async function openCreateGroupModal(){ try{ let r=await authFetch(`/inbox?nocache=${new Date().getTime()}`); let d=await r.json(); let list=document.getElementById('group-friends-list'); if((d.friends||[]).length===0){list.innerHTML=`<p style='color:#ff5555;font-size:13px;'>Adicione amigos primeiro.</p>`;}else{list.innerHTML=d.friends.map(f=>`<label style="display:flex;align-items:center;gap:10px;color:white;margin-bottom:10px;cursor:pointer;"><input type="checkbox" class="grp-friend-cb" value="${f.id}" style="width:18px;height:18px;"><img src="${safeAvatarUrl(f.avatar, f.name)}" style="width:30px;height:30px;border-radius:50%;object-fit:cover;" onerror="this.src='/static/default-avatar.svg'"> ${f.name}</label>`).join('');} document.getElementById('new-group-name').value=''; document.getElementById('modal-create-group').classList.remove('hidden'); }catch(e){ console.error(e); } }

async function submitCreateGroup(){
  let name = document.getElementById('new-group-name').value.trim();
  if(!name) return;

  let cbs = document.querySelectorAll('.grp-friend-cb:checked');
  let member_ids = Array.from(cbs).map(cb => parseInt(cb.value));
  if(member_ids.length === 0) return;

  try{
    let r = await authFetch('/group/create', {
      method:'POST',
      body: JSON.stringify({ name:name, creator_id:user.id, member_ids:member_ids })
    });
    if(r.ok){
      document.getElementById('modal-create-group').classList.add('hidden');
      loadInbox();
    } else {
      console.error('POST /group/create failed', r.status);
      showToast('Erro ao criar grupo.');
    }
  }catch(e){
    console.error(e);
    showToast('Erro ao criar grupo.');
  }
}

async function toggleRequests(type){ let b=document.getElementById('requests-list'); if(b.style.display==='block'){b.style.display='none';return;} b.style.display='block'; try{ let r=await authFetch(`/friend/requests?nocache=${new Date().getTime()}`); let d=await r.json(); if(type==='requests'){b.innerHTML=(d.requests||[]).length?d.requests.map(r=>`<div style="padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;">${r.username} <button class="glass-btn" style="padding:5px 10px;flex:none;" onclick="handleReq(${r.id},'accept')">${t('accept_ally')}</button></div>`).join(''):`<p style="padding:10px;color:#888;">Vazio.</p>`;}else{b.innerHTML=(d.friends||[]).length?d.friends.map(f=>`<div style="padding:10px;border-bottom:1px solid #333;cursor:pointer;display:flex;align-items:center;gap:10px;" onclick="openPublicProfile(${f.id})"><div class="av-wrap"><img src="${safeAvatarUrl(f.avatar, f.username)}" style="width:30px;height:30px;border-radius:50%;" onerror="this.src='/static/default-avatar.svg'"><div class="status-dot" data-uid="${f.id}" style="width:10px;height:10px;"></div></div>${f.username}</div>`).join(''):`<p style="padding:10px;color:#888;">Vazio.</p>`;} updateStatusDots(); }catch(e){ console.error(e); } }

async function sendRequest(tid){try{let r=await authFetch('/friend/request',{method:'POST',body:JSON.stringify({target_id:tid})});if(r.ok){openPublicProfile(tid);}}catch(e){ console.error(e); }}

async function handleReq(rid,act){try{let r=await authFetch('/friend/handle',{method:'POST',body:JSON.stringify({request_id:rid,action:act})});if(r.ok){toggleRequests('requests');fetchUnread();}}catch(e){ console.error(e); }}

async function handleCommReq(rid,act){try{let r=await authFetch('/community/request/handle',{method:'POST',body:JSON.stringify({req_id:rid,action:act})});if(r.ok){showToast("Membro atualizado!");fetchUnread();await openCommunity(activeCommId, true);}}catch(e){ console.error(e); }}

async function unfriend(fid) {
    if(confirm("Desfazer amizade com este soldado?")) {
        try {
            let r = await authFetch('/friend/remove', {method:'POST', body:JSON.stringify({friend_id: fid})});
            if(r.ok) { showToast("Amizade desfeita."); openPublicProfile(fid); loadInbox(); fetchUnread(); }
        } catch(e) { console.error(e); }
    }
}

async function fetchChatMessages(id, type, loadToken) {
    let list = document.getElementById('dm-list');
    let url = type === 'group' ? `/group/${id}/messages?nocache=${new Date().getTime()}` : `/dms/${id}?uid=${user.id}&nocache=${new Date().getTime()}`;
    try {
        let r = await authFetch(url);
        if (r.ok) {
            // If user switched chats while this request was in-flight, ignore the result.
            if (loadToken !== undefined && loadToken !== currentChatLoadToken) return;
            let msgs = await r.json();
            let isAtBottom = (list.scrollHeight - list.scrollTop <= list.clientHeight + 50);
            (msgs || []).forEach(d => {
                let prefix = type === 'group' ? 'group_msg' : 'dm_msg';
                let msgId = `${prefix}-${d.id}`;
                if (!document.getElementById(msgId)) {
                    let m = (d.user_id === user.id);
                    let c = (d && d.content !== undefined && d.content !== null) ? String(d.content) : '';
        if(c && (c.toLowerCase()==='undefined' || c.toLowerCase()==='null')) c='';
                    if(c && (c.toLowerCase()==='undefined' || c.toLowerCase()==='null')) c='';
                    let delBtn = '';
                    let timeHtml = d.timestamp ? `<span class="msg-time">${formatMsgTime(d.timestamp)}</span>` : '';
                    if (c === '[DELETED]') {
                        c = `<span class="msg-deleted">${t('deleted_msg')}</span>`;
                    } else {
                        if (c.startsWith('[AUDIO]')) {
                            c = `<audio controls src="${c.replace('[AUDIO]', '')}" style="max-width:200px;height:40px;outline:none;"></audio>`;
                        } else if (c.startsWith('http') && c.includes('cloudinary')) {
                            if (c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) {
                                c = `<video src="${c}" style="max-width:100%;border-radius:10px;border:1px solid #444;" controls playsinline></video>`;
                            } else {
                                c = `<img src="${c}" style="max-width:100%;border-radius:10px;cursor:pointer;border:1px solid #444;" onclick="window.open(this.src)">`;
                            }
                        }
                        delBtn = (m && d.can_delete) ? `<span class="del-msg-btn" onclick="window.deleteTarget={type:'${prefix}', id:${d.id}}; document.getElementById('modal-delete').classList.remove('hidden');">🗑️</span>` : '';
                    }
                    let h;
                    if(isCallSystemMsg(d.content || '')) {
                        h = buildCallEventHtml(msgId, d.content || '', timeHtml);
                    } else {
                        h = `<div id="${msgId}" class="msg-row ${m ? 'mine' : ''}">
                        <img src="${safeAvatarUrl(d.avatar, safeDisplayName(d))}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'" data-vip-border="${d.vip_border||'none'}" data-vip-size="40">
                        <div>
                            <div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})"><span style="${(d.vip_name_color ? 'color:'+d.vip_name_color+';text-shadow:0 0 8px '+d.vip_name_color+'66;' : '')}${d.vip_name_font ? 'font-family:\''+d.vip_name_font+'\',sans-serif;' : ''}">${escapeHtml(safeDisplayName(d))}</span> ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div>
                            <div class="msg-bubble" ${!m && d.vip_bubble && d.vip_bubble!=='none' ? `data-vip-bubble="${d.vip_bubble}"` : ''}>${c}${timeHtml}${delBtn}</div>
                        </div>
                    </div>`;
                    }
                    list.insertAdjacentHTML('beforeend', h);
                }
            });
            if (isAtBottom) list.scrollTop = list.scrollHeight;
            if(typeof applyAllVipBorders==="function") setTimeout(applyAllVipBorders, 50);
            if(typeof applyAllVipBubbles==="function") setTimeout(applyAllVipBubbles, 60);
        }
    } catch (e) { console.error(e); }
}

async function openChat(id, name, type, avatar) {
    let changingChat = (currentChatId !== id || currentChatType !== type);
    currentChatId = id;
    currentChatType = type;
    // New token for this chat session (prevents DM/group mixing from async races)
    const loadToken = ++currentChatLoadToken;

    // Populate header
    document.getElementById('dm-header-name').innerText = name;

    // Sub-label by type
    const sub = document.getElementById('dm-header-sub');
    if (sub) sub.innerText = type === 'group' ? 'Grupo' : 'Mensagem Direta';

    // Group settings button
    const gear = document.getElementById('group-settings-btn');
    if (gear) {
        if (type === 'group') {
            gear.style.display = 'inline-flex';
            gear.dataset.groupId = String(id);
        } else {
            gear.style.display = 'none';
            gear.dataset.groupId = '';
        }
    }


    // Avatar
    const av = document.getElementById('dm-header-avatar');
    if (av) {
        av.src = avatar ? safeAvatarUrl(avatar) : '/static/default-avatar.svg';
        av.onerror = () => { av.src = '/static/default-avatar.svg'; };
    }

    // Status dot — só para 1v1
    const dot = document.getElementById('dm-header-status-dot');
    if (dot) {
        if (type === '1v1') {
            dot.setAttribute('data-uid', id);
            dot.style.display = 'block';
            updateStatusDots();
        } else {
            dot.style.display = 'none';
        }
    }

    // Show/hide call button
    const callBtn = document.getElementById('dm-call-btn');
    if (callBtn) callBtn.style.display = 'flex';

    // Verifica se há call ativa no canal e mostra badge "ENTRAR"
    try {
        const expectedCh = (type === 'group')
            ? sanitizeChannelName(`call_group_${id}`)
            : sanitizeChannelName(`call_dm_${Math.min(user.id, id)}_${Math.max(user.id, id)}`);
        const r = await authFetch(`/call/active?channel=${encodeURIComponent(expectedCh)}`);
        if (r.ok) {
            const info = await r.json();
            const sub = document.getElementById('dm-header-sub');
            if (sub) {
                if (info.active && !rtc.client) {
                    sub.innerHTML = `<span class="join-call-badge" onclick="joinActiveCall('${expectedCh}','${type}')">
                        <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.41 2 2 0 0 1 3.6 1.21h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.81a16 16 0 0 0 6.29 6.29l.96-.96a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                        CALL ATIVA · ${info.participants} ${info.participants===1?'pessoa':'pessoas'} · ENTRAR
                    </span>`;
                } else {
                    sub.innerText = type === 'group' ? 'Grupo' : 'Mensagem Direta';
                }
            }
        }
    } catch(_) {}

    goView('dm');
    if (type === '1v1') {
        await fetch(`/inbox/read/${id}`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` }, body: JSON.stringify({ uid: user.id }) });
        fetchUnread();
    }
    document.getElementById('dm-list').innerHTML = '';
    await fetchChatMessages(id, type, loadToken);
    if (changingChat || !dmWS || dmWS.readyState !== WebSocket.OPEN) {
        connectDmWS(id, name, type, loadToken);
    }
}

function connectDmWS(id, name, type, loadToken) {
    if (dmWS) dmWS.close();
    let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let token = localStorage.getItem('token');
    let ch = type === 'group' ? `group_${id}` : `dm_${Math.min(user.id, id)}_${Math.max(user.id, id)}`;
    dmWS = new WebSocket(`${protocol}//${location.host}/ws/${ch}/${user.id}?token=${token}`);
    dmWS.onopen = () => {
        try {
            // Flush legacy in-memory queue
            while (window.dmSendQueue && window.dmSendQueue.length && dmWS.readyState === WebSocket.OPEN) {
                dmWS.send(window.dmSendQueue.shift());
            }
            // Flush IndexedDB offline queue via FGOffline
            if (window.FGOffline) {
                window.FGOffline.flushOutboundQueue((content, channel) => {
                    if (channel === ch && dmWS.readyState === WebSocket.OPEN) {
                        dmWS.send(content);
                    }
                });
            }
        } catch (e) { console.error('flush dmSendQueue failed', e); }
    };
    dmWS.onclose = () => {
        setTimeout(() => {
            // If user switched chats, don't reconnect/fetch the old chat.
            if (loadToken !== currentChatLoadToken) return;
            if (currentChatId === id && currentChatType === type && document.getElementById('view-dm').classList.contains('active')) {
                // no fetchChatMessages on close; avoid races/badges
                connectDmWS(id, name, type, loadToken);
            }
        }, Math.min(1200 * Math.pow(1.5, window._dmWsRetry = (window._dmWsRetry||0) + 1), 16000));
    };
    dmWS.onmessage = (e) => {
        let d = JSON.parse(e.data);

        // Não misturar mensagens de outra conversa (mobile alterna rápido e pode chegar msg de chat antigo)
        // If user switched chats, never render into the current DOM
        if (loadToken !== currentChatLoadToken || currentChatId !== id || currentChatType !== type) {
            // Só atualiza contadores (sem renderizar no chat aberto)
            try { fetchUnread(); } catch(_) {}
            return;
        }
        let b = document.getElementById('dm-list');
        let m = parseInt(d.user_id) === parseInt(user.id);
        let c = (d && d.content !== undefined && d.content !== null) ? String(d.content) : '';
        if(c && (c.toLowerCase()==='undefined' || c.toLowerCase()==='null')) c='';
                    if(c && (c.toLowerCase()==='undefined' || c.toLowerCase()==='null')) c='';
        if (d.type === 'ping' || d.type === 'pong') return;

        // Evita aparecer "Usuário"/mensagens vazias quando chegam eventos de controle (call_accepted, sync_bg, etc.)
        // Esses eventos não são mensagens de chat e não devem ser renderizados na lista.
        if (d.type && d.type !== 'msg' && d.type !== 'new_dm' && d.type !== 'message_deleted') {
            if (d.type === 'error') { console.warn('WS error:', d.detail || d); }
            if (d.type === 'typing_start') { if (typeof showTypingIndicator === 'function') showTypingIndicator(d.username || 'Alguém'); }
            if (d.type === 'typing_stop') { const ti = document.getElementById('typing-indicator'); if(ti) ti.remove(); }
            return;
        }
        if (d.type === 'message_deleted' && (d.msg_id || d.id)) {
            const delId = String(d.msg_id || d.id);
            const el = document.getElementById(`dm_msg-${delId}`) || document.getElementById(`group_msg-${delId}`);
            if (el) {
                const bubble = el.querySelector('.msg-bubble');
                if (bubble) {
                    const timeSpan = bubble.querySelector('.msg-time');
                    const timeHtml = timeSpan ? timeSpan.outerHTML : '';
                    bubble.innerHTML = `<span class="msg-deleted">${t('deleted_msg')}</span>${timeHtml}`;
                    const btn = el.querySelector('.del-msg-btn');
                    if (btn) btn.remove();
                }
            }
            return;
        }
        if (c.startsWith('[CALL_BG]')) { return; }
        let prefix = type === 'group' ? 'group_msg' : 'dm_msg';
        let msgId = `${prefix}-${d.id}`;
        if (!document.getElementById(msgId)) {
            let delBtn = '';
            let timeHtml = d.timestamp ? `<span class="msg-time">${formatMsgTime(d.timestamp)}</span>` : '';
            if (c === '[DELETED]') {
                c = `<span class="msg-deleted">${t('deleted_msg')}</span>`;
            } else {
                if (c.startsWith('[AUDIO]')) {
                    c = `<audio controls src="${c.replace('[AUDIO]', '')}" style="max-width:200px;height:40px;outline:none;"></audio>`;
                } else if (c.startsWith('http') && c.includes('cloudinary')) {
                    if (c.match(/\.(mp4|webm|mov|ogg|mkv)$/i) || c.includes('/video/upload/')) {
                        c = `<video src="${c}" style="max-width:100%;border-radius:10px;border:1px solid #444;" controls playsinline></video>`;
                    } else {
                        c = `<img src="${c}" style="max-width:100%;border-radius:10px;cursor:pointer;border:1px solid #444;" onclick="window.open(this.src)">`;
                    }
                }
                delBtn = (m && d.can_delete) ? `<span class="del-msg-btn" onclick="window.deleteTarget={type:'${prefix}', id:${d.id}}; document.getElementById('modal-delete').classList.remove('hidden');">🗑️</span>` : '';
            }
            let h;
            if(isCallSystemMsg(d.content || '')) {
                h = buildCallEventHtml(msgId, d.content || '', timeHtml);
            } else {
                h = `<div id="${msgId}" class="msg-row ${m ? 'mine' : ''}">
                <img src="${safeAvatarUrl(d.avatar, safeDisplayName(d))}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'" data-vip-border="${d.vip_border||'none'}" data-vip-size="40">
                <div>
                    <div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})"><span style="${(d.vip_name_color?'color:'+d.vip_name_color+';text-shadow:0 0 8px '+d.vip_name_color+'66;':'')}${d.vip_name_font?'font-family:'+d.vip_name_font+',sans-serif;':''}">${escapeHtml(safeDisplayName(d))}</span> ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div>
                    <div class="msg-bubble" ${!m && d.vip_bubble && d.vip_bubble!=='none' ? `data-vip-bubble="${d.vip_bubble}"` : ''}>${c}${timeHtml}${delBtn}</div>
                </div>
            </div>`;
            }
            b.insertAdjacentHTML('beforeend', h);
            b.scrollTop = b.scrollHeight;
            if(typeof applyAllVipBorders==='function') setTimeout(applyAllVipBorders, 50);
            if(typeof applyAllVipBubbles==='function') setTimeout(applyAllVipBubbles, 60);
        }
        let isDmActive = document.getElementById('view-dm').classList.contains('active');
        if (isDmActive && currentChatType === '1v1' && currentChatId === d.user_id) {
            fetch(`/inbox/read/${d.user_id}`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` }, body: JSON.stringify({ uid: user.id }) }).then(() => fetchUnread());
        } else {
            fetchUnread();
        }
    };
}

function sendDM(){
  let i = document.getElementById('dm-msg');
  let msg = i.value.trim();
  if(!msg) return;

  // clear input immediately for better UX
  i.value = '';
  toggleEmoji(true);

  if(dmWS && dmWS.readyState === WebSocket.OPEN){
    dmWS.send(msg);
  } else {
    // Queue in IndexedDB for offline persistence
    if (window.FGOffline) {
      const ch = currentChatType === 'group'
        ? `group_${currentChatId}`
        : `dm_${Math.min(user.id, currentChatId)}_${Math.max(user.id, currentChatId)}`;
      window.FGOffline.enqueueOutbound(ch, msg);
    } else {
      window.dmSendQueue = window.dmSendQueue || [];
      window.dmSendQueue.push(msg);
    }
    try { dmWS && dmWS.close(); } catch(e) {}
    if (window.currentChatId && window.currentChatType) {
      connectDmWS(currentChatId, window.currentChatName || '', currentChatType, window.currentChatLoadToken);
    }
  }
}

async function uploadDMImage(){
  let f = document.getElementById('dm-file').files[0];
  if(!f) return;
  try{
    let formData = new FormData();
    formData.append('file', f);
    let res = await authFetch('/upload', { method:'POST', body: formData, headers:{} });
    let data = await res.json();
    const url = (typeof pickUploadedUrl === 'function' ? pickUploadedUrl(data) : null) || data.secure_url || data.url;
    if(!url){ showToast("Erro no upload da imagem."); return; }

    if(dmWS && dmWS.readyState === WebSocket.OPEN){
      dmWS.send(url);
    } else {
      window.dmSendQueue = window.dmSendQueue || [];
      window.dmSendQueue.push(url);
      try { dmWS && dmWS.close(); } catch(e) {}
      if (window.currentChatId && window.currentChatType) {
        connectDmWS(currentChatId, window.currentChatName || '', currentChatType, window.currentChatLoadToken);
      }
    }
  }catch(e){
    console.error(e);
    showToast("Erro no upload da imagem.");
  }
}

function applyRemoteDelete(msgNumericId){
    const candidates = [
        `dm_msg-${msgNumericId}`,
        `comm_msg-${msgNumericId}`,
        `geral_msg-${msgNumericId}`,
        `msg-${msgNumericId}`,
    ];
    for(const id of candidates){
        const el = document.getElementById(id);
        if(!el) continue;
        // marca visualmente como apagada
        const bubble = el.querySelector('.msg-bubble');
        if(bubble){
            bubble.innerHTML = '<span style="color:#888;font-style:italic;">[mensagem apagada]</span>';
        } else {
            el.innerHTML = '<span style="color:#888;font-style:italic;">[mensagem apagada]</span>';
        }
        // remove botão de delete se existir
        el.querySelectorAll('.del-msg-btn').forEach(b=>b.remove());
    }
}

function openGroupSettings(){
    try{
        if (currentChatType !== 'group' || !currentChatId) return;
        const modal = document.getElementById('modal-group-settings');
        if (!modal) return;
        document.getElementById('group-settings-error').style.display = 'none';
        modal.classList.remove('hidden');
        loadGroupSettings();
    }catch(e){ console.error(e); }
}

function closeGroupSettings(){
    const modal = document.getElementById('modal-group-settings');
    if (modal) modal.classList.add('hidden');
}

function gsError(msg){
    const el = document.getElementById('group-settings-error');
    if (!el) return;
    el.innerText = msg || 'Falha.';
    el.style.display = 'block';
}

async function loadGroupSettings(){
    try{
        const gid = currentChatId;
        const res  = await authFetch(`/group/${gid}`);          // retorna Response
        const data = await res.json();                           // parseia para objeto
        if (!data) return;
        const nameEl = document.getElementById('group-settings-name');
        const metaEl = document.getElementById('group-settings-meta');
        const avEl   = document.getElementById('group-settings-avatar');
        if (nameEl) nameEl.innerText = data.name || 'Grupo';
        const members = Array.isArray(data.members) ? data.members : [];
        if (metaEl) metaEl.innerText = `${members.length} membro${members.length !== 1 ? 's' : ''}`;
        if (avEl) avEl.src = (data.avatar || data.avatar_url)
            ? safeAvatarUrl(data.avatar || data.avatar_url)
            : '/static/default-avatar.svg';
        renderGroupMembers(members, data.creator_id);
    }catch(e){
        console.error(e);
        gsError('Não foi possível carregar dados do grupo.');
    }
}

function renderGroupMembers(members, creatorId){
    const list = document.getElementById('group-members-list');
    if (!list) return;
    list.innerHTML = '';
    members.forEach(m => {
        const row = document.createElement('div');
        row.className = 'group-member-row';
        const left = document.createElement('div');
        left.className = 'group-member-left';

        const av = document.createElement('img');
        av.className = 'group-member-avatar';
        av.src = safeAvatarUrl(m.avatar_url || m.avatar) || '/static/default-avatar.svg';
        av.onerror = ()=>{ av.src = '/static/default-avatar.svg'; };

        const nm = document.createElement('div');
        nm.className = 'group-member-name';
        nm.innerText = m.username || m.name || `ID ${m.id}`;

        left.appendChild(av);
        left.appendChild(nm);

        const actions = document.createElement('div');
        actions.className = 'group-member-actions';

        // Não mostra REMOVER para si mesmo nem se não for criador
        const isMe = (m.id === user.id);
        const isCreator = (user.id === creatorId);
        if (!isMe) {
            const btnRemove = document.createElement('button');
            btnRemove.className = 'gm-remove-btn';
            btnRemove.title = 'Remover membro';
            btnRemove.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
            if (!isCreator) btnRemove.style.display = 'none'; // só criador remove
            btnRemove.onclick = ()=> removeGroupMember(m.id);
            actions.appendChild(btnRemove);
        } else {
            const youBadge = document.createElement('span');
            youBadge.className = 'gm-you-badge';
            youBadge.innerText = 'Você';
            actions.appendChild(youBadge);
        }

        row.appendChild(left);
        row.appendChild(actions);
        list.appendChild(row);
    });
}

async function addGroupMember(){
    try{
        const inp = document.getElementById('group-add-username');
        const username = (inp && inp.value || '').trim();
        if (!username) return gsError('Informe o usuário para adicionar.');
        document.getElementById('group-settings-error').style.display = 'none';
        await authFetch(`/group/${currentChatId}/members/add`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ username })
        });
        if (inp) inp.value = '';
        await loadGroupSettings();
        await refreshInbox();
    }catch(e){
        console.error(e);
        gsError('Não foi possível adicionar. Verifique o nome do usuário ou permissões.');
    }
}

async function removeGroupMember(user_id){
    try{
        document.getElementById('group-settings-error').style.display = 'none';
        await authFetch(`/group/${currentChatId}/members/remove`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ user_id })
        });
        await loadGroupSettings();
        await refreshInbox();
    }catch(e){
        console.error(e);
        gsError('Não foi possível remover. Você pode não ter permissão.');
    }
}

async function leaveGroup(){
    try{
        document.getElementById('group-settings-error').style.display = 'none';
        await authFetch(`/group/${currentChatId}/leave`, { method: 'POST' });
        closeGroupSettings();
        // Volta pra inbox
        document.getElementById('dm-chat-area').classList.add('hidden');
        await refreshInbox();
    }catch(e){
        console.error(e);
        gsError('Não foi possível sair do grupo.');
    }
}

async function changeGroupAvatar(){
    try{
        // Use existing upload modal flow if present; fallback to file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.onchange = async () => {
            const f = fileInput.files && fileInput.files[0];
            if (!f) return;
            const fd = new FormData();
            fd.append('file', f);
            const res = await fetch('/upload', { method:'POST', body: fd });
            const data = await res.json().catch(()=> ({}));
            const url = pickUploadedUrl(data);
            if (!url) return gsError('Upload falhou.');
            await authFetch(`/group/${currentChatId}/avatar`, {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ avatar_url: url })
            });
            await loadGroupSettings();
            await refreshInbox();
            // update header avatar if you have one specific to groups
        };
        fileInput.click();
    }catch(e){
        console.error(e);
        gsError('Não foi possível trocar a foto do grupo.');
    }
}