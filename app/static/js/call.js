// ═══════════════════════════════════════════════════════════════
// FOR GLORY — CALL — Agora RTC, Call Panel, Botão Flutuante
// Gerado por splitter v2 — extração correta por profundidade de chaves
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */

function initDraggableFloatingCallButton() {
    const btn = document.getElementById('floating-call-btn');
    if (!btn) return;

    // Restore last position
    try {
        const raw = localStorage.getItem('floatingCallBtnPos');
        if (raw) {
            const p = JSON.parse(raw);
            if (p && typeof p.x === 'number' && typeof p.y === 'number') {
                btn.style.left = p.x + 'px';
                btn.style.top = p.y + 'px';
                btn.style.right = 'auto';
                btn.style.bottom = 'auto';
                btn.style.position = 'fixed';
            }
        }
    } catch(e) {}

    btn.style.touchAction = 'none';
    btn.style.userSelect  = 'none';

    // ── Estado ──────────────────────────────────────────────────────
    let dragging  = false;
    let startX = 0, startY = 0;
    let origLeft = 0, origTop = 0;
    let btnW = 0, btnH = 0;
    let curDX = 0, curDY = 0;
    let moved  = 0, rafId = 0;

    // Edge-snap state
    let snapped = false;  // está colado na borda?
    let snapSide = '';    // 'left' | 'right'
    // Quanto de movimento (px) cancela o snap
    const SNAP_PULL_THRESHOLD = 50;
    const SNAP_ZONE = 28;   // px da borda para acionar snap
    const SNAP_DELAY = 120; // ms depois de soltar na borda

    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

    // ── Snap visual ──────────────────────────────────────────────────
    function applySnap(side) {
        snapped  = true;
        snapSide = side;
        btn.classList.add('fcb-snapped', side === 'left' ? 'fcb-snap-left' : 'fcb-snap-right');
        btn.style.transform = 'translate3d(0,0,0)';
    }
    function releaseSnap() {
        snapped  = false;
        snapSide = '';
        btn.classList.remove('fcb-snapped', 'fcb-snap-left', 'fcb-snap-right');
    }
    function checkSnap() {
        const rect = btn.getBoundingClientRect();
        const mid  = rect.left + rect.width / 2;
        if (rect.left <= SNAP_ZONE) {
            btn.style.left = '0px';
            btn.style.top  = origTop + curDY + 'px';
            btn.style.transform = 'translate3d(0,0,0)';
            applySnap('left');
            return true;
        }
        if (rect.right >= window.innerWidth - SNAP_ZONE) {
            btn.style.left = (window.innerWidth - rect.width) + 'px';
            btn.style.top  = origTop + curDY + 'px';
            btn.style.transform = 'translate3d(0,0,0)';
            applySnap('right');
            return true;
        }
        releaseSnap();
        return false;
    }

    // ── Handlers ────────────────────────────────────────────────────
    const onDown = (ev) => {
        if (ev.button !== undefined && ev.button !== 0) return;
        const e = ev.touches ? ev.touches[0] : ev;

        const rect = btn.getBoundingClientRect();
        btn.style.position = 'fixed';
        btn.style.right  = 'auto';
        btn.style.bottom = 'auto';
        btn.style.left   = rect.left + 'px';
        btn.style.top    = rect.top  + 'px';
        btn.style.transform = 'translate3d(0,0,0)';

        // Se estava snapped, re-ancora para posição atual
        if (snapped) releaseSnap();

        origLeft = rect.left;
        origTop  = rect.top;
        btnW     = rect.width;
        btnH     = rect.height;
        startX   = e.clientX;
        startY   = e.clientY;
        curDX = curDY = 0;
        moved     = 0;
        dragging  = true;

        btn.style.willChange = 'transform';
        btn.style.transition = 'none';

        try { ev.pointerId != null && btn.setPointerCapture(ev.pointerId); } catch(_) {}
        ev.preventDefault && ev.preventDefault();
    };

    const onMove = (ev) => {
        if (!dragging) return;
        const e = ev.touches ? ev.touches[0] : ev;

        const maxDX = window.innerWidth  - btnW - 6 - origLeft;
        const minDX = 6 - origLeft;
        const maxDY = window.innerHeight - btnH - 6 - origTop;
        const minDY = 6 - origTop;

        curDX = clamp(e.clientX - startX, minDX, maxDX);
        curDY = clamp(e.clientY - startY, minDY, maxDY);
        moved = Math.max(moved, Math.abs(curDX), Math.abs(curDY));

        if (!rafId) {
            rafId = requestAnimationFrame(() => {
                rafId = 0;
                btn.style.transform = `translate3d(${curDX}px,${curDY}px,0)`;
            });
        }

        ev.preventDefault && ev.preventDefault();
    };

    const onUp = () => {
        if (!dragging) return;
        dragging = false;
        if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }

        const finalLeft = origLeft + curDX;
        const finalTop  = origTop  + curDY;
        btn.style.left      = finalLeft + 'px';
        btn.style.top       = finalTop  + 'px';
        btn.style.transform = 'translate3d(0,0,0)';
        btn.style.willChange = 'auto';

        // Transição suave para snap
        btn.style.transition = 'left 0.25s cubic-bezier(.4,0,.2,1), top 0.25s cubic-bezier(.4,0,.2,1)';
        setTimeout(() => { btn.style.transition = ''; }, 260);

        // Verifica snap após animação
        setTimeout(checkSnap, SNAP_DELAY);

        try {
            localStorage.setItem('floatingCallBtnPos',
                JSON.stringify({ x: finalLeft, y: finalTop }));
        } catch(_) {}

        if (moved > 5) {
            btn.__justDragged = true;
            setTimeout(() => { btn.__justDragged = false; }, 300);
        }
    };

    if (window.PointerEvent) {
        btn.addEventListener('pointerdown',    onDown, { passive: false });
        window.addEventListener('pointermove', onMove, { passive: false });
        window.addEventListener('pointerup',   onUp,  { passive: true });
        window.addEventListener('pointercancel', onUp, { passive: true });
    } else {
        btn.addEventListener('touchstart',    onDown, { passive: false });
        window.addEventListener('touchmove',  onMove, { passive: false });
        window.addEventListener('touchend',   onUp,  { passive: true });
        btn.addEventListener('mousedown',     onDown);
        window.addEventListener('mousemove',  onMove);
        window.addEventListener('mouseup',    onUp);
    }

    // Cancela click se foi drag
    btn.addEventListener('click', (e) => {
        if (btn.__justDragged) { e.preventDefault(); e.stopPropagation(); }
    }, true);
}

function openCallInvite() {
    document.getElementById('modal-call-invite').classList.remove('hidden');
    document.getElementById('call-invite-username').value = '';
    document.getElementById('call-invite-error').style.display = 'none';
    setTimeout(() => document.getElementById('call-invite-username').focus(), 100);
}

async function sendCallInvite() {
    const username = (document.getElementById('call-invite-username').value || '').trim();
    if (!username) return;
    const errEl = document.getElementById('call-invite-error');
    errEl.style.display = 'none';
    try {
        // Busca o usuário pelo username
        const r = await authFetch(`/user/search?q=${encodeURIComponent(username)}`);
        const data = await r.json();
        const found = Array.isArray(data) ? data[0] : (data.users && data.users[0]);
        if (!found) { errEl.innerText = 'Usuário não encontrado.'; errEl.style.display = 'block'; return; }
        // Envia incoming_call via ring/dm usando o canal atual
        await fetch('/call/ring/dm', {
            method: 'POST',
            headers: {'Content-Type':'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}`},
            body: JSON.stringify({
                caller_id: user.id,
                target_id: found.id,
                channel_name: window.currentAgoraChannel
            })
        });
        showToast(`📞 Convite enviado para ${found.username || found.name}`);
        document.getElementById('modal-call-invite').classList.add('hidden');
    } catch(e) {
        errEl.innerText = 'Falha ao enviar convite.';
        errEl.style.display = 'block';
    }
}

async function joinActiveCall(channel, type) {
    if (rtc.client) return showToast("Você já está em uma call!");
    window.isCaller = false;
    window.pendingCallType = type;
    window.currentAgoraChannel = channel;
    document.getElementById('floating-call-btn').style.display = 'flex';
    showCallPanel();
    await connectToAgora(channel, type);
}

async function initCall(typeParam, targetId) {
    if (rtc.client) return showToast("Você já está em uma call!");
    window.isCaller = true;
    window.callTargetId = targetId;
    window.pendingCallType = typeParam;
    
    let channelName = "";
    if (typeParam === 'dm' || typeParam === '1v1') { 
        channelName = `call_dm_${Math.min(user.id, targetId)}_${Math.max(user.id, targetId)}`; 
        await fetch('/call/ring/dm', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({caller_id:user.id, target_id:targetId, channel_name:channelName})});
    } else if (typeParam === 'group') { 
        channelName = `call_group_${targetId}`; 
        await fetch('/call/ring/group', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({caller_id:user.id, group_id:targetId, channel_name:channelName})});
    } else if (typeParam === 'channel' || typeParam === 'voice') { 
        channelName = `call_channel_${targetId}`; 
        connectToAgora(channelName, typeParam); 
        return;
    } else { return showToast("Alvo inválido."); }
    
    window.currentAgoraChannel = sanitizeChannelName(channelName);
    if(!window.currentAgoraChannel){ showToast("❌ Canal inválido"); return; }
    window.callHasConnected = false;
    
    document.getElementById('call-active-profile').style.display = 'none';
    document.getElementById('call-hud-status').innerText = "CHAMANDO...";
    document.getElementById('floating-call-btn').style.display = 'flex'; 
    showCallPanel();
    
    let bgAction = document.getElementById('call-bg-action');
    bgAction.style.display = 'block';
    
    safePlaySound(window.callingSound); 
}

function declineCall() { 
    document.getElementById('modal-incoming-call').classList.add('hidden'); 
    stopSounds();
    if (globalWS && globalWS.readyState === WebSocket.OPEN && window.pendingCallerId) {
        globalWS.send(`CALL_SIGNAL:${window.pendingCallerId}:rejected:${window.currentAgoraChannel}`);
    }
}

async function acceptCall() { 
    document.getElementById('modal-incoming-call').classList.add('hidden'); 
    stopSounds();
    window.callHasConnected = false; 
    window.isCaller = false;
    
    if (globalWS && globalWS.readyState === WebSocket.OPEN && window.pendingCallerId) {
        globalWS.send(`CALL_SIGNAL:${window.pendingCallerId}:accepted:${window.currentAgoraChannel}`);
    }
    
    const ch = window.pendingCallChannel || window.currentAgoraChannel;
    await connectToAgora(ch, window.pendingCallType); 
}

async function connectToAgora(channelName, typeParam) {
    window.currentAgoraChannel = sanitizeChannelName(channelName);
    if(!window.currentAgoraChannel){ showToast("❌ Canal inválido"); return; } 
    document.getElementById('call-active-profile').style.display = 'none';
    document.getElementById('call-hud-status').innerText = "CONECTANDO...";
    
    let bgAction = document.getElementById('call-bg-action');
    if (typeParam === 'dm' || typeParam === '1v1' || typeParam === 'group') { bgAction.style.display = 'block'; } 
    else { bgAction.style.display = window.currentCommIsAdmin ? 'block' : 'none'; }
    
    try {
        const safeCh = window.currentAgoraChannel;
        let res = await authFetch(`/agora/token?channel=${encodeURIComponent(safeCh)}&uid=${user.id}`);
        if (!res.ok) {
            console.error('Agora token error:', res.status);
            showToast('⚠️ Sessão expirada ou sem permissão para a call. Faça login novamente.');
            leaveCall();
            return;
        }
        let conf = await res.json();
        if (!conf.app_id || conf.app_id.trim() === "") { showToast("⚠️ ERRO: Central de Rádio Offline (Configure o AGORA_APP_ID no Render)"); leaveCall(); return; }
if (rtc.client) { await rtc.client.leave(); }
        
        try {
            let rBg = await fetch(`/call/bg/call/${encodeURIComponent(window.currentAgoraChannel)}`); let resBg = await rBg.json();
            if(resBg && resBg.bg_url) { document.getElementById('expanded-call-panel').style.backgroundImage = `url('${resBg.bg_url}')`; } 
            else { document.getElementById('expanded-call-panel').style.backgroundImage = 'none'; }
        } catch(e) { console.error(e); }

        rtc.client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
        rtc.remoteUsers = {};
        // Marca como "ainda não conectou com ninguém" (para auto-encerrar quando ficar sozinho)
        window.callHasConnected = false;
        
        rtc.client.on("user-published", async (remoteUser, mediaType) => {
            window.callHasConnected = true; 
            stopSounds();
            await rtc.client.subscribe(remoteUser, mediaType);
            if (mediaType === "audio") { rtc.remoteUsers[remoteUser.uid] = remoteUser; __getRemoteState(remoteUser.uid).remoteUnpub = false; remoteUser.audioTrack.play(); renderCallPanel(rtc, user.id); }
        });
        
        rtc.client.on("user-unpublished", (remoteUser, mediaType) => {
            // Remote stopped publishing audio/video — keep user visible and mark status.
            rtc.remoteUsers[remoteUser.uid] = remoteUser;
            if (mediaType === "audio" || !mediaType) __getRemoteState(remoteUser.uid).remoteUnpub = true;
            renderCallPanel(rtc, user.id);
        });
        rtc.client.on("user-left", (remoteUser) => {
            delete rtc.remoteUsers[remoteUser.uid];
            if (window.__remoteAudioState) delete window.__remoteAudioState[remoteUser.uid];
            renderCallPanel(rtc, user.id);
            const remaining = Object.keys(rtc.remoteUsers).length;
            if (window.callHasConnected) {
                showToast("Um aliado saiu da chamada.");
                // Encerra automaticamente quando ficar sozinho (grupo ou 1v1)
                if (remaining === 0) {
                    setTimeout(() => leaveCall(), 1500); // pequeno delay para o toast aparecer
                }
            }
        });
        
        await rtc.client.join(conf.app_id, window.currentAgoraChannel, conf.token, user.id);
        
        try { rtc.localAudioTrack = await AgoraRTC.createMicrophoneAudioTrack(); } 
        catch(micErr) { alert("⚠️ Sem Microfone! Autorize no navegador para usar o rádio."); leaveCall(); return; }
        
        await rtc.client.publish([rtc.localAudioTrack]);

        // Se ninguém entrar em 30s, encerra por privacidade/UX.
        setTimeout(() => {
            try{
                if(rtc && rtc.client && Object.keys(rtc.remoteUsers || {}).length === 0){
                    showToast("Ninguém entrou na call.");
                    leaveCall();
                }
            }catch(e){}
        }, 30000);
        // Registra call ativa no backend (permite others to join)
        try {
            await authFetch('/call/start', {method:'POST', body: JSON.stringify({channel: window.currentAgoraChannel})});
        } catch(_) {}
        window.__callEndLogged = false;
        if (!window.__callStartedAt) window.__callStartedAt = Date.now();
        if (!window.__callStartLogged) {
          window.__callStartLogged = true;
          const dt = new Date();
          sendSystemDmMessage(`📞 Chamada iniciada em ${dt.toLocaleDateString()} ${dt.toLocaleTimeString()}`);
        }
        try {
            window.callStartedAt = Date.now();
            // (evita duplicar) o sendSystemDmMessage acima já envia o evento de call no chat
        } catch(e) { console.warn('call chat start event failed', e); }

        document.getElementById('floating-call-btn').style.display = 'flex'; showCallPanel();
        
    } catch(e) { console.error("Call Connect Error:", e); showToast("Falha ao conectar na Call."); leaveCall(); }
}

async function uploadCallBg(inputElem){
    if(!inputElem.files || !inputElem.files[0]) return;
    if(!window.currentAgoraChannel) { showToast("Aguarde conectar na call."); return; }
    showToast("Aplicando fundo tático...");
    try{
        let formData = new FormData();
        formData.append('file', inputElem.files[0]);
        let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); // sem Content-Type
        let data = await res.json();
        await authFetch('/call/bg/set', {
            method:'POST',
            body:JSON.stringify({ target_type: 'call', target_id: window.currentAgoraChannel, bg_url: (pickUploadedUrl(data) || '') })
        });
        const bgUrl = pickUploadedUrl(data);
        if(!bgUrl){ showToast('Erro na imagem.'); return; }
        document.getElementById('expanded-call-panel').style.backgroundImage=`url('${bgUrl}')`;
        showToast("Fundo alterado!");
        if(globalWS && globalWS.readyState === WebSocket.OPEN) {
            globalWS.send("SYNC_BG:" + window.currentAgoraChannel + ":" + bgUrl);
        }
    } catch(e) { console.error("Upload BG erro:", e); showToast("Erro na imagem."); }
}

function leaveCall() {
    // ── 1. Fecha a UI imediatamente — sem await, sem bloqueio ──────────
    clearInterval(callInterval);

    // Evita qualquer reconexão automática (ex: visibilitychange) enquanto está saindo.
    window.currentAgoraChannel = null;
    window.pendingCallFrom = null;
    window.pendingCallType = null;

    try { document.getElementById('expanded-call-panel').style.display = 'none'; } catch(_) {}
    try { document.getElementById('floating-call-btn').style.display = 'none'; } catch(_) {}
    try {
        const muteBtn = document.getElementById('btn-mute-call');
        if (muteBtn) {
            muteBtn.classList.remove('muted');
            muteBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`;
        }
    } catch(_) {}
    isMicMuted = false;

    // ── 2. Captura estado antes de limpar ──────────────────────────────
    const wasCaller    = window.isCaller;
    const targetId     = window.callTargetId;
    const channel      = window.currentAgoraChannel;
    const wasConnected = window.callHasConnected;
    const startedAt    = window.__callStartedAt;

    // ── 3. Captura referências Agora antes de limpar ──────────────────────
    const _audioTrack = rtc.localAudioTrack;
    const _client     = rtc.client;
    stopSounds();
    _stopCallKeepAlive();
    rtc.localAudioTrack = null;
    rtc.client          = null;
    window.callHasConnected    = false;
    window.currentAgoraChannel = null;
    window.isCaller            = false;
    window.callTargetId        = null;
    window.__callStartLogged   = false;
    window.__callStartedAt     = null;
    window.__leavingCall       = false;

    // ── 4. Limpeza pesada em background (não bloqueia UI) ──────────────
    (async () => {
        // Duração no chat
        try {
            if (startedAt && !window.__callEndLogged) {
                window.__callEndLogged = true;
                const sec = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
                const mm = String(Math.floor(sec / 60)).padStart(2, '0');
                const ss = String(sec % 60).padStart(2, '0');
                sendSystemDmMessage(`📞 Chamada finalizada (duração ${mm}:${ss})`);
            }
        } catch(_) {}

        // Sinal de cancelamento
        try {
            if (wasCaller && targetId && !wasConnected && globalWS && globalWS.readyState === WebSocket.OPEN)
                globalWS.send(`CALL_SIGNAL:${targetId}:cancelled:${channel}`);
        } catch(_) {}

        // Sai do canal Agora — com timeout de 4s para não travar
        try {
            if (_audioTrack) _audioTrack.close();
        } catch(_) {}
        try {
            if (_client) await Promise.race([
                _client.leave(),
                new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 4000))
            ]);
        } catch(_) {}

        // Backend
        try {
            if (channel)
                await authFetch('/call/end', { method: 'POST', body: JSON.stringify({ channel }) });
        } catch(_) {}
    })();
}

async function renderCallPanel(rtc, localUid) {
    try {
        const panel = document.getElementById('expanded-call-panel');
        if (!panel) return;

        const usersList = document.getElementById('call-users-list');
        const activeProfile = document.getElementById('call-active-profile');

        const statusText = document.getElementById('call-status');
        const timeText = document.getElementById('call-time');
        const nameText = document.getElementById('call-active-name');
        const avatarImg = document.getElementById('call-active-avatar');

        // Build participant list (local + remote)
        const remoteUids = Object.keys(rtc?.remoteUsers || {}).map(k => Number(k)).filter(n => !Number.isNaN(n));
        const allUids = Array.from(new Set([localUid, ...remoteUids]));

        const basics = [];
        for (const uid of allUids) basics.push(await getUserBasic(uid));

        // UI: list
        if (usersList) {
            usersList.innerHTML = '';
            // remote control state
            window.__remoteAudioState = window.__remoteAudioState || {};

            basics.forEach(b => {
                const uid = Number(b.id);
                const isLocal = (uid === Number(localUid));
                const st = window.__remoteAudioState[uid] || (window.__remoteAudioState[uid] = { muted:false, volume:100, remoteUnpub:false, prevVolume:100 });

                const item = document.createElement('div');
                item.className = 'call-user-row';

                const muted = !!st.muted || !!st.remoteUnpub;
                const vol = Math.max(0, Math.min(200, parseInt(st.volume ?? 100)));

                item.innerHTML = `
                    <div class="cu-avatar-wrap">
                        <img src="${escapeHtml(safeAvatarUrl(b.avatar))}" class="cu-avatar" alt="">
                        ${muted ? `<span class="cu-muted-dot"></span>` : ``}
                    </div>

                    <div class="cu-info">
                        <div class="cu-name">${escapeHtml(b.name)}</div>
                        <div class="cu-sub">${isLocal ? 'Você' : (muted ? 'Mutado' : 'Ativo')}</div>
                    </div>

                    ${isLocal ? `` : `
                    <div class="cu-vol-inline">
                        <input class="cu-slider" type="range" min="0" max="200" value="${vol}" data-action="remote-volume" data-uid="${uid}">
                        <span class="cu-vol-pct" data-action="vol-label">${vol}%</span>
                    </div>

                    <button class="cu-mute-btn ${st.muted ? 'is-muted' : ''}" data-action="toggle-remote-mute" data-uid="${uid}" title="${st.muted ? 'Desmutar' : 'Mutar'}">
                        ${st.muted ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>` : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>`}
                    </button>
                    `}
                `;

                // wire events (only for remote)
                if (!isLocal) {
                    const muteBtn = item.querySelector('[data-action="toggle-remote-mute"]');
                    const slider  = item.querySelector('[data-action="remote-volume"]');
                    const label   = item.querySelector('[data-action="vol-label"]');

                    const updateSliderTrack = (slider, v) => {
                        const pct = Math.round((v / 200) * 100);
                        slider.style.background = `linear-gradient(to right, var(--primary) ${pct}%, rgba(255,255,255,0.15) ${pct}%)`;
                    };

                    if (muteBtn) {
                        muteBtn.addEventListener('click', async () => {
                            await toggleRemoteMute(uid);
                            renderCallPanel(rtc, localUid);
                        });
                    }
                    if (slider) {
                        updateSliderTrack(slider, parseInt(slider.value));
                        slider.addEventListener('input', () => {
                            const v = parseInt(slider.value);
                            st.volume = v;
                            if (label) label.textContent = `${v}%`;
                            updateSliderTrack(slider, v);
                            setRemoteVolume(uid, v);
                        });
                    }
                }

                usersList.appendChild(item);
            });
        }

        // Pick "active" = first remote (if exists), otherwise local
        let activeUid = remoteUids.length ? remoteUids[0] : localUid;
        const activeBasic = await getUserBasic(activeUid);

        if (avatarImg) avatarImg.src = safeAvatarUrl(activeBasic?.avatar);
        if (nameText) nameText.textContent = (activeBasic?.name || 'Usuário');

        // Status + timer
        if (statusText) statusText.textContent = 'EM CHAMADA';
        const startedAt = window.__callStartedAt || Date.now();
        window.__callStartedAt = startedAt;
        if (timeText) {
            const sec = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
            const mm = String(Math.floor(sec / 60)).padStart(2, '0');
            const ss = String(sec % 60).padStart(2, '0');
            timeText.textContent = `${mm}:${ss}`;
        }

        // If group call, show "X participantes" as subtitle
        const subtitle = document.getElementById('call-subtitle');
        if (subtitle) {
            if (allUids.length > 2) subtitle.textContent = `${allUids.length} participantes`;
            else subtitle.textContent = '';
        }

        // Ensure panel visible (some flows rely on this)
        panel.style.display = 'flex';
    } catch (e) {
        console.warn("renderCallPanel failed:", e);
    }
}

function __getRemoteState(uid) {
    uid = Number(uid);
    if (!window.__remoteAudioState[uid]) window.__remoteAudioState[uid] = { muted:false, volume:100, remoteUnpub:false, prevVolume:100 };
    return window.__remoteAudioState[uid];
}

function setRemoteVolume(uid, volumePct) {
    uid = Number(uid);
    const st = __getRemoteState(uid);
    const v = Math.max(0, Math.min(200, parseInt(volumePct)));
    st.volume = v;

    const user = rtc?.remoteUsers?.[uid];
    const track = user?.audioTrack;
    if (!track || !track.setVolume) return;

    // Agora Web SDK volume is typically 0..100; for >100 we clamp but keep UI at 200.
    const sdkVol = Math.max(0, Math.min(100, v));
    try { track.setVolume(sdkVol); } catch(e){ console.warn("setRemoteVolume failed", e); }
}

async function toggleRemoteMute(uid) {
    uid = Number(uid);
    const st = __getRemoteState(uid);

    if (!st.muted) {
        st.prevVolume = (st.volume ?? 100);
        st.muted = true;
        setRemoteVolume(uid, 0);
    } else {
        st.muted = false;
        setRemoteVolume(uid, st.prevVolume ?? 100);
    }
}

function changeRemoteVol(uid, val) { setRemoteVolume(uid, val); }

async function toggleMuteCall() { 
    if(rtc.localAudioTrack) { 
        isMicMuted = !isMicMuted;
        await rtc.localAudioTrack.setMuted(isMicMuted); 
        let btn = document.getElementById('btn-mute-call'); 
        if(isMicMuted) { btn.classList.add('muted'); btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="1" y1="1" x2="23" y2="23"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`; } 
        else { btn.classList.remove('muted'); btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`; } 
    } 
}

function toggleCallPanel() { let p = document.getElementById('expanded-call-panel'); p.style.display = (p.style.display === 'flex') ? 'none' : 'flex'; }

function updateCallInviteBtn() {
    const btn = document.querySelector('.cp-ctrl-invite');
    if (!btn) return;
    const isGroup = (window.pendingCallType === 'group' || window.pendingCallType === 'channel');
    btn.style.display = isGroup ? 'flex' : 'none';
}

function showCallPanel() { document.getElementById('expanded-call-panel').style.display = 'flex'; updateCallInviteBtn(); callDuration = 0; document.getElementById('call-hud-time').innerText = "00:00"; clearInterval(callInterval); callInterval = setInterval(() => { callDuration++; let m = String(Math.floor(callDuration / 60)).padStart(2, '0'); let s = String(callDuration % 60).padStart(2, '0'); document.getElementById('call-hud-time').innerText = `${m}:${s}`; }, 1000); renderCallPanel(rtc, user.id); }

function kickFromCall(targetUid) { if(confirm("Expulsar soldado da ligação?")) { if(globalWS && globalWS.readyState === WebSocket.OPEN) { globalWS.send("KICK_CALL:" + targetUid); } } }

function showToast(m){ let x=document.getElementById("toast"); x.innerText=m; x.className="show"; setTimeout(()=>{x.className=""},5000); }

function toggleAuth(m){ ['login','register','forgot','reset'].forEach(f=>document.getElementById(f+'-form').classList.add('hidden')); document.getElementById(m+'-form').classList.remove('hidden'); }