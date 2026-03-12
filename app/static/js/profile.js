// ═══════════════════════════════════════════════════════════════
// FOR GLORY — PROFILE — Perfil Público/Privado, Busca, Edição, Stealth
// Gerado por splitter v2 — extração correta por profundidade de chaves
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */

async function openPublicProfile(uid){
    try{
        // Usa a rota do backend que existe: /user/{target_id}?viewer_id={user_id}
        let r = await authFetch(`/user/${uid}?viewer_id=${user.id}&nocache=${new Date().getTime()}`);
        if(!r.ok) return;
        let d = await r.json();

        document.getElementById('pub-avatar').src = d.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(d.username||'U')}&background=111&color=66fcf1`;
        if (typeof applyProfilePageBorder === 'function') applyProfilePageBorder('pub-avatar', d.vip_border || 'none');
        document.getElementById('pub-cover').src = d.cover_url || "https://placehold.co/600x200/0b0c10/66fcf1?text=FOR+GLORY";
        document.getElementById('pub-name').innerText = d.username || '';
        document.getElementById('pub-bio').innerText = d.bio || '';
        document.getElementById('pub-emblems').innerHTML = formatRankInfo(d.rank, d.special_emblem, d.rank_color);
        renderMedals('pub-medals-box', d.medals || [], true);

        // grid de posts
        let grid = document.getElementById('pub-grid');
        grid.innerHTML = '';
        (d.posts || []).forEach(p => {
            grid.innerHTML += (p.media_type === 'video')
                ? `<video src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:10px;" controls playsinline preload="metadata"></video>`
                : `<img src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;cursor:pointer;border-radius:10px;" onclick="window.open(this.src)">`;
        });

        // ações
        let actionsDiv = document.getElementById('pub-actions');
        if(uid === user.id){
            actionsDiv.innerHTML = '';
        } else {
            let fs = d.friend_status || 'none';
            let reqId = d.request_id;
            let btns = [];
            if(fs === 'friends'){
                btns.push(`<button class="btn-main" style="margin-top:0;background:transparent;border:1px solid #ff5555;color:#ff5555;" onclick="unfriend(${uid})">💔 Desfazer amizade</button>`);
                btns.push(`<button class="btn-main" style="margin-top:0;" onclick="openChat(${uid}, '${(d.username||'DM').replace(/'/g, "\\'")}', '1v1')">💬 DM</button>`);
            } else if(fs === 'pending_received' && reqId){
                btns.push(`<button class="btn-main" style="margin-top:0;" onclick="handleReq(${reqId}, 'accept')">✔ Aceitar</button>`);
                btns.push(`<button class="btn-main" style="margin-top:0;background:transparent;border:1px solid #ff5555;color:#ff5555;" onclick="handleReq(${reqId}, 'reject')">✕ Recusar</button>`);
            } else if(fs === 'pending_sent'){
                btns.push(`<button class="btn-main" style="margin-top:0;opacity:0.7;" disabled>📩 Solicitação enviada</button>`);
            } else {
                btns.push(`<button class="btn-main" style="margin-top:0;" onclick="sendRequest(${uid})">➕ Recrutar aliado</button>`);
                btns.push(`<button class="btn-main" style="margin-top:0;background:transparent;border:1px solid var(--primary);" onclick="openChat(${uid}, '${(d.username||'DM').replace(/'/g, "\\'")}', '1v1')">💬 DM</button>`);
            }
            actionsDiv.innerHTML = btns.join('');
        }

        goView('public-profile');
    }catch(e){ console.error(e); }
}

async function updateProfile(){
    let btn=document.getElementById('btn-save-profile');
    btn.disabled=true;
    try{
        let f=document.getElementById('avatar-upload').files[0];
        let c=document.getElementById('cover-upload').files[0];
        let b=document.getElementById('bio-update').value;
        let au=null,cu=null;
        if(f) au=await uploadToCloudinary(f);
        if(c) cu=await uploadToCloudinary(c);
        let payload={avatar_url:au,cover_url:cu,bio:b};
        let r=await authFetch('/profile/update_meta',{method:'POST',body:JSON.stringify(payload)});
        if(r.ok){updateProfileState();document.getElementById('modal-profile').classList.add('hidden');}
    }catch(e){ console.error(e); }
    finally{ btn.disabled=false; }
}

function clearSearch(){
    document.getElementById('search-input').value='';
    document.getElementById('search-results').innerHTML='';
}

async function searchUsers(){
    let q=document.getElementById('search-input').value.trim();
    if(!q)return;
    try{
        let r=await authFetch(`/users/search?q=${encodeURIComponent(q)}`);
        let d=await r.json();
        let res=document.getElementById('search-results');
        if(!d||d.length===0){res.innerHTML=`<p style='color:#888;text-align:center;margin-top:10px;'>${t('no_results')}</p>`;return;}
        res.innerHTML=d.map(u=>`<div class="friend-row" onclick="openPublicProfile(${u.id})" style="cursor:pointer;"><div class="av-wrap"><img src="${safeAvatarUrl(u.avatar_url)}" class="friend-av" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${u.id}"></div></div><div style="flex:1"><b style="color:white;">${u.username}</b></div><button class="glass-btn" style="padding:5px 12px;margin:0;" onclick="event.stopPropagation();sendRequest(${u.id})">${t('add_friend')}</button></div>`).join('');
        updateStatusDots();
    }catch(e){ console.error(e); }


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
}

async function toggleStealth(){try{let r=await authFetch('/profile/stealth', {method:'POST'}); if(r.ok){let d=await r.json(); user.is_invisible=d.is_invisible; updateStealthUI(); fetchOnlineUsers();}}catch(e){ console.error(e); }}

function updateStealthUI(){let btn=document.getElementById('btn-stealth');let myDot=document.getElementById('my-status-dot');if(user.is_invisible){btn.innerText=t('stealth_on');btn.style.borderColor="#ffaa00";btn.style.color="#ffaa00";myDot.classList.remove('online');}else{btn.innerText=t('stealth_off');btn.style.borderColor="rgba(102, 252, 241, 0.3)";btn.style.color="var(--primary)";myDot.classList.add('online');}}