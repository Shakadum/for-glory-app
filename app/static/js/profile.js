// ═══════════════════════════════════════════════════════════════
// FOR GLORY — PROFILE — Perfil Público/Privado, Busca, Edição
// Extraído de app.js — não editar este arquivo manualmente.
// Editar os blocos originais e rodar o splitter novamente.
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */
'use strict';

async function openPublicProfile(uid){
    try{
        // Usa a rota do backend que existe: /user/{target_id}?viewer_id={user_id}
        let r = await authFetch(`/user/${uid}?viewer_id=${user.id}&nocache=${new Date().getTime()}`);
        if(!r.ok) return;
        let d = await r.json();

        document.getElementById('pub-avatar').src = d.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(d.username||'U')}&background=111&color=66fcf1`;
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

// [uploadToCloudinary movida para módulo canônico]
