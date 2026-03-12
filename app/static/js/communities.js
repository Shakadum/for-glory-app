// ═══════════════════════════════════════════════════════════════
// FOR GLORY — COMMUNITIES — Bases, Canais, Membros, Admin
// Gerado por splitter v2 — extração correta por profundidade de chaves
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */

async function submitCreateComm(e){e.preventDefault();let n=document.getElementById('new-comm-name').value.trim();let d=document.getElementById('new-comm-desc').value.trim();let p=document.getElementById('new-comm-priv').value;let avFile=document.getElementById('comm-avatar-upload').files[0];let banFile=document.getElementById('comm-banner-upload').files[0];if(!n)return showToast("Digite um nome!");let btn=e.target;btn.disabled=true;btn.innerText="CRIANDO...";try{let safeName=encodeURIComponent(n);let av="https://ui-avatars.com/api/?name="+safeName+"&background=111&color=66fcf1";let ban="https://placehold.co/600x200/0b0c10/1f2833?text="+safeName;if(avFile){let formData = new FormData(); formData.append('file', avFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); av = pickUploadedUrl(data) || av; } if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); ban = pickUploadedUrl(data) || ban; } let payload = { name:n, desc:d, is_priv:parseInt(p), avatar_url:av, banner_url:ban }; let r=await authFetch('/community/create', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-create-comm').classList.add('hidden');showToast("Base Criada!");loadMyComms();goView('mycomms');}}catch(err){console.error(err);showToast("Erro.");}finally{btn.disabled=false;btn.innerText=t('establish');}}

async function submitEditComm(){let avFile=document.getElementById('edit-comm-avatar').files[0];let banFile=document.getElementById('edit-comm-banner').files[0];if(!avFile&&!banFile)return showToast("Selecione algo.");let btn=document.getElementById('btn-save-comm');btn.disabled=true;btn.innerText="ENVIANDO...";try{let au=null; let bu=null; if(avFile){let formData = new FormData(); formData.append('file', avFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); au = pickUploadedUrl(data) || au; } if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); bu = pickUploadedUrl(data) || bu; } let payload = { comm_id: activeCommId, avatar_url: au, banner_url: bu }; let r=await authFetch('/community/edit', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-edit-comm').classList.add('hidden');showToast("Base Atualizada!");openCommunity(activeCommId, true);loadMyComms();}}catch(e){console.error(e);showToast("Erro.");}finally{btn.disabled=false;btn.innerText=t('save');}}

async function submitCreateChannel(){let n=document.getElementById('new-ch-name').value.trim();let tType=document.getElementById('new-ch-type').value;let p=document.getElementById('new-ch-priv').value;let banFile=document.getElementById('new-ch-banner').files[0];if(!n)return showToast("Digite o nome.");let btn=document.getElementById('btn-create-ch');btn.disabled=true;btn.innerText="CRIANDO...";try{let safeName=encodeURIComponent(n);let ban="https://placehold.co/600x200/0b0c10/1f2833?text="+safeName;if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); ban = pickUploadedUrl(data) || ban; } let payload = { comm_id: activeCommId, name:n, type:tType, is_private:parseInt(p), banner_url:ban }; let r=await authFetch('/community/channel/create', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-create-channel').classList.add('hidden');showToast("Canal Criado!");openCommunity(activeCommId, true);}}catch(err){console.error(err);}finally{btn.disabled=false;btn.innerText=t('create_channel');}}

async function loadMyComms(){try{let r=await authFetch(`/communities/list?nocache=${new Date().getTime()}`); let d=await r.json(); let mList=document.getElementById('my-comms-grid');mList.innerHTML='';if((d.my_comms||[]).length===0)mList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases')}</p>`;(d.my_comms||[]).forEach(c=>{mList.innerHTML+=`<div class="comm-card" data-id="${c.id}" onclick="openCommunity(${c.id})"><img src="${safeAvatarUrl(c.avatar_url)}" class="comm-avatar"><div class="req-dot" style="display:none;position:absolute;top:-5px;right:-5px;background:#ff5555;color:white;font-size:10px;padding:3px 8px;border-radius:12px;font-weight:bold;box-shadow:0 0 10px #ff5555;border:2px solid var(--dark-bg);z-index:10;">NOVO</div><b style="color:white;font-size:16px;font-family:'Rajdhani';letter-spacing:1px;">${c.name}</b></div>`;});fetchUnread();}catch(e){ console.error(e); }}

async function loadPublicComms(){try{let r=await authFetch(`/communities/search?nocache=${new Date().getTime()}`); let d=await r.json(); let pList=document.getElementById('public-comms-grid');pList.innerHTML='';if((d||[]).length===0)pList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;(d||[]).forEach(c=>{let btnStr=c.is_private?`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:orange;color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>`:`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:#2ecc71;color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;pList.innerHTML+=`<div class="comm-card"><img src="${safeAvatarUrl(c.avatar_url)}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:'Rajdhani';letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`;});}catch(e){ console.error(e); }}

function clearCommSearch(){document.getElementById('search-comm-input').value='';loadPublicComms();}

async function searchComms(){try{let q=document.getElementById('search-comm-input').value.trim();let r=await authFetch(`/communities/search?q=${q}&nocache=${new Date().getTime()}`); let d=await r.json(); let pList=document.getElementById('public-comms-grid');pList.innerHTML='';if((d||[]).length===0)pList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;(d||[]).forEach(c=>{let btnStr=c.is_private?`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:orange;color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>`:`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:#2ecc71;color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;pList.innerHTML+=`<div class="comm-card"><img src="${safeAvatarUrl(c.avatar_url)}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:'Rajdhani';letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`;});}catch(e){ console.error(e); }}

async function joinCommunity(cid){try{let r=await authFetch('/community/join', {method:'POST', body:JSON.stringify({comm_id:cid})}); if(r.ok){showToast("Entrou na Base com sucesso!");loadPublicComms();openCommunity(cid);}else{showToast("Erro.");}}catch(e){ console.error(e); }}

async function requestCommJoin(cid){try{let r=await authFetch('/community/request/send', {method:'POST', body:JSON.stringify({comm_id:cid})}); if(r.ok){showToast("Enviado.");}}catch(e){ console.error(e); }}

async function leaveCommunity(cid){if(confirm("Desertar desta base?")){try{let r=await authFetch(`/community/${cid}/leave`, {method:'POST'}); let res=await r.json(); if(res.status==='ok'){closeComm();loadMyComms();}else{showToast(res.msg);}}catch(e){ console.error(e); }}}

async function openCommunity(cid, keepInfoOpen=false){
    activeCommId=cid;goView('comm-dashboard');
    let infoArea = document.getElementById('comm-info-area');
    let chatArea = document.getElementById('comm-chat-area');
    let isInfoOpen = infoArea.style.display === 'flex';
    if(!keepInfoOpen && !isInfoOpen) { infoArea.style.display='none'; chatArea.style.display='flex'; }
    
    try{
        let r=await authFetch(`/community/${cid}?nocache=${new Date().getTime()}`);
        let d=await r.json();
        let headerBg=d.banner_url?`url('${d.banner_url}')`:'none';
        document.getElementById('comm-header').style.backgroundImage=headerBg;document.getElementById('c-info-av').src=d.avatar_url;
        document.getElementById('c-info-banner').style.backgroundImage=headerBg;document.getElementById('c-info-name').innerText=d.name;document.getElementById('c-info-desc').innerText=d.description;
        window.currentCommIsAdmin=d.is_admin||d.creator_id===user.id;
        let mHtml="";
        (d.members||[]).forEach(m=>{
            let roleBadge=m.id===d.creator_id?t('creator'):(m.role==='admin'?t('admin'):t('member'));
            let actions='<div class="admin-action-wrap">';
            if((d.is_admin||d.creator_id===user.id)&&m.id!==d.creator_id&&(d.creator_id===user.id||m.role!=='admin')){actions+=`<button title="${t('kick')}" class="admin-action-btn danger" onclick="kickMember(${cid}, ${m.id})">❌</button>`;}
            actions+='</div>';
            mHtml+=`<div style="display:flex;align-items:center;gap:10px;padding:10px;border-bottom:1px solid #333;border-radius:10px;transition:0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'"><img src="${safeAvatarUrl(m.avatar, m.name)}" onclick="openPublicProfile(${m.id})" style="width:35px;height:35px;border-radius:50%;object-fit:cover;border:1px solid #555;cursor:pointer;" onerror="this.src='/static/default-avatar.svg'"> <span style="color:white;flex:1;font-weight:bold;cursor:pointer;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" onclick="openPublicProfile(${m.id})">${m.name}</span> <span class="ch-badge" style="color:${m.role==='admin'||m.id===d.creator_id?'var(--primary)':'#888'}">${roleBadge}</span>${actions}</div>`;
        });
        document.getElementById('c-info-members').innerHTML=mHtml;
        let addBtn=document.getElementById('c-info-admin-btn');let reqCont=document.getElementById('c-info-requests-container');let reqList=document.getElementById('c-info-requests');let delCont=document.getElementById('c-info-destroy-btn');
        if(d.creator_id===user.id){delCont.innerHTML=`<button class="glass-btn" style="width:100%;margin-bottom:10px;color:#2ecc71;border-color:#2ecc71;" onclick="document.getElementById('modal-edit-comm').classList.remove('hidden')">✏️ EDITAR BASE</button><button class="glass-btn danger-btn" onclick="window.deleteTarget={type:'base', id:${cid}}; document.getElementById('modal-delete').classList.remove('hidden');">${t('destroy_base')}</button>`;}else{delCont.innerHTML=`<button class="glass-btn danger-btn" onclick="leaveCommunity(${cid})">🚪 SAIR DA BASE</button>`;}
        if(d.is_admin||d.creator_id===user.id){
            addBtn.innerHTML=`<button class="glass-btn" style="width:100%;border-color:#('hidden')">✏️ EDITAR BASE</button><button class="glass-btn danger-btn" onclick="window.deleteTarget={type:'base', id:${cid}}; document.getElementById('modal-delete').classList.remove('hidden');">${t('destroy_base')}</button>`;}else{delCont.innerHTML=`<button class="glass-btn danger-btn" onclick="leaveCommunity(${cid})">🚪 SAIR DA BASE</button>`;}
        if(d.is_admin||d.creator_id===user.id){
            addBtn.innerHTML=`<button class="glass-btn" style="width:100%;border-color:#2ecc71;color:#2ecc71;font-size2ecc71;color:#2ecc71;font-size:15px;letter-spacing:2px;" onclick="document.getElementById('modal-create-channel').classList.remove('hidden')">+ ${t('create_channel')}</button>`;
            let reqR=await authFetch(`/community/${cid}/requests?nocache=${new Date().getTime()}`);
            let reqs=await reqR.json();
            if((reqs||[]).length>0){
    reqCont.style.display='block';
    reqList.innerHTML='';
    reqs.forEach(rq=>{
        reqList.innerHTML += `
            <div style="display:flex;align-items:center;gap:10px;background:rgba(0,0,0,0.5);padding:10px;border-radius:10px;margin-bottom:8px;">
                <img src="${safeAvatarUrl(rq.avatar, rq.username)}" style="width:30px;height:30px;border-radius:50%;object-fit:cover;" onerror="this.src='/static/default-avatar.svg'">
                <span style="color:white;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${rq.username}</span>
                <button class="glass-btn" style="padding:5px 10px;flex:none;" onclick="handleCommReq(${rq.id}, 'accept')">✔</button>
                <button class="glass-btn" style="padding:5px 10px;flex:none;border-color:#ff5555;color:#ff5555;" onclick="handleCommReq(${rq.id}, 'reject')">✕</button>
            </div>
        `;
    });
}else{
    reqCont.style.display='none';
}
        }else{addBtn.innerHTML='';reqCont.style.display='none';}
        let cb=document.getElementById('comm-channels-bar');cb.innerHTML='';
        if((d.channels||[]).length>0){
            let sortedChannels=d.channels.sort((a,b)=>{if(a.name.toLowerCase()==='geral')return -1;if(b.name.toLowerCase()==='geral')return 1;return 0;});
            sortedChannels.forEach(ch=>{
                let bgStyle=ch.banner_url?`background-image:linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url('${ch.banner_url}');border:none;`:'';let icon=ch.type==='voice'?'🎙️ ':'';
                let editBtn=(d.is_admin||d.creator_id===user.id)?`<span style="margin-left:5px;font-size:11px;cursor:pointer;opacity:0.7;" onclick="event.stopPropagation(); openEditChannelModal(${ch.id}, '${ch.name}', '${ch.type}', ${ch.is_private})">⚙️</span>`:'';
                cb.innerHTML+=`<button class="channel-btn" style="${bgStyle}" onclick="joinChannel(${ch.id}, '${ch.type}', this)">${icon}${ch.name} ${editBtn}</button>`;
            });
            if(!keepInfoOpen && !isInfoOpen) { joinChannel(sortedChannels[0].id,sortedChannels[0].type,cb.children[0]); }
        }else{document.getElementById('comm-chat-list').innerHTML="";}
    }catch(e){ console.error(e); }
}

async function promoteMember(cid,tid){try{let payload={comm_id:cid,target_id:tid};let r=await authFetch('/community/promote',{method:'POST',body:JSON.stringify(payload)});if(r.ok){showToast('Promovido!');openCommunity(cid,true);}}catch(e){console.error(e);}}

async function demoteMember(cid,tid){try{let payload={comm_id:cid,target_id:tid};let r=await authFetch('/community/member/demote', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){await openCommunity(cid, true);}}catch(e){ console.error(e); }}

async function kickMember(cid,tid){if(confirm("Tem certeza que dese?")){try{let payload={comm_id:cid,target_id:tid};let r=await authFetch('/community/member/kick', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){await openCommunity(cid, true);}}catch(e){ console.error(e); }}}

function showCommInfo(){document.getElementById('comm-chat-area').style.display='none';document.getElementById('comm-info-area').style.display='flex';}

function closeComm(){goView('mycomms',document.querySelectorAll('.nav-btn')[3]);if(commWS)commWS.close();}

function openEditChannelModal(id,name,type,priv){window.currentEditChannelId=id;document.getElementById('edit-ch-name').value=name;document.getElementById('edit-ch-type').value=type;document.getElementById('edit-ch-priv').value=priv;document.getElementById('modal-edit-channel').classList.remove('hidden');}

async function submitEditChannel(){let n=document.getElementById('edit-ch-name').value.trim();let tType=document.getElementById('edit-ch-type').value;let p=document.getElementById('edit-ch-priv').value;let banFile=document.getElementById('edit-ch-banner').files[0];if(!n)return;let btn=document.getElementById('btn-edit-ch');btn.disabled=true;btn.innerText="SALVANDO...";try{let bu=null; if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); bu = pickUploadedUrl(data) || bu; } let payload={channel_id:window.currentEditChannelId, name:n, type:tType, is_private:parseInt(p), banner_url:bu}; let r=await authFetch('/community/channel/edit', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-edit-channel').classList.add('hidden');openCommunity(activeCommId, true);}}catch(e){ console.error(e); }finally{btn.disabled=false;btn.innerText=t('save');}}

async function fetchCommMessages(chid){
    let list=document.getElementById('comm-chat-list');
    try{
        let r=await fetch(`/community/channel/${chid}/messages?nocache=${new Date().getTime()}`);
        if(r.ok){
            let msgs=await r.json();
            let isAtBottom=(list.scrollHeight-list.scrollTop<=list.clientHeight+50);
            (msgs||[]).forEach(d=>{
                let prefix='comm_msg';
                let msgId=`${prefix}-${d.id}`;
                if(!document.getElementById(msgId)){
                    let m=(d.user_id===user.id);
                    let c=d.content;
                    let delBtn='';
                    let timeHtml=d.timestamp?`<span class="msg-time">${formatMsgTime(d.timestamp)}</span>`:'';
                    if(c==='[DELETED]'){
                        c=`<span class="msg-deleted">${t('deleted_msg')}</span>`;
                    }else{
                        if(c.startsWith('[AUDIO]')){
                            c=`<audio controls src="${c.replace('[AUDIO]','')}" style="max-width:200px;height:40px;outline:none;"></audio>`;
                        }else if(c.startsWith('http')&&c.includes('cloudinary')){
                            if(c.match(/\.(mp4|webm|mov|ogg|mkv)$/i)||c.includes('/video/upload/')){
                                c=`<video src="${c}" style="max-width:100%;border-radius:10px;border:1px solid #444;" controls playsinline></video>`;
                            }else{
                                c=`<img src="${c}" style="max-width:100%;border-radius:10px;cursor:pointer;border:1px solid #444;" onclick="window.open(this.src)">`;
                            }
                        }
                        delBtn=(m&&d.can_delete)?`<span class="del-msg-btn" onclick="window.deleteTarget={type:'${prefix}', id:${d.id}}; document.getElementById('modal-delete').classList.remove('hidden');">🗑️</span>`:'';
                    }
                    let h=`<div id="${msgId}" class="msg-row ${m?'mine':''}"><img src="${safeAvatarUrl(d.avatar, safeDisplayName(d))}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'" data-vip-border="${d.vip_border||'none'}" data-vip-size="40"><div style="min-width:0;flex:1;"><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})"><span style="${(d.vip_name_color?'color:'+d.vip_name_color+';text-shadow:0 0 8px '+d.vip_name_color+'66;':'')}${d.vip_name_font?'font-family:'+d.vip_name_font+',sans-serif;':''}">${escapeHtml(safeDisplayName(d))}</span> ${formatRankInfo(d.rank,d.special_emblem,d.color)}</div><div class="msg-bubble" ${d.vip_bubble && d.vip_bubble!=='none' ? `data-vip-bubble="${d.vip_bubble}"` : ''}>${c}${timeHtml}${delBtn}</div></div></div>`;
                    list.insertAdjacentHTML('beforeend',h);
                }
            });
            if(isAtBottom)list.scrollTop=list.scrollHeight;
            if(typeof applyAllVipBorders==='function') applyAllVipBorders();
            if(typeof applyAllVipBubbles==='function') applyAllVipBubbles();
        }
    }catch(e){ console.error(e); }
}

function connectCommWS(chid){
    if(commWS) { try{ commWS.close(); }catch(e){} }
    let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let token = localStorage.getItem('token');
    // Usa o mesmo endpoint genérico /ws/{ch}/{uid}
    let ch = `comm_${chid}`;
    commWS = new WebSocket(`${protocol}//${location.host}/ws/${ch}/${user.id}?token=${token}`);
    commWS.onmessage = () => { 
        // Atualiza o chat do canal ativo
        if(activeChannelId === chid) fetchCommMessages(chid); 
    };
    commWS.onclose = () => { 
        setTimeout(() => { if(user && activeChannelId === chid) connectCommWS(chid); }, 3000);
    };
}

async function joinChannel(chid, chtype, btn){
    activeChannelId=chid;
    document.querySelectorAll('.channel-btn').forEach(b=>b.classList.remove('active'));
    if(btn) btn.classList.add('active');
    document.getElementById('comm-chat-list').innerHTML='';
    if(chtype==='voice'){
        document.getElementById('comm-chat-area').style.display='none';
        document.getElementById('comm-voice-area').style.display='flex';
        connectCommWS(chid);
    } else {
        document.getElementById('comm-voice-area').style.display='none';
        document.getElementById('comm-chat-area').style.display='flex';
        await fetchCommMessages(chid);
        connectCommWS(chid);
        let list=document.getElementById('comm-chat-list');
        list.scrollTop=list.scrollHeight;
    }
}

async function sendCommMsg(){
    let inp = document.getElementById('comm-msg');
    let msg = (inp ? inp.value.trim() : '');
    if(!msg || !activeChannelId) return;
    inp.value = '';
    try{
        if(commWS && commWS.readyState === WebSocket.OPEN){
            commWS.send(msg);
        } else {
            // fallback: tenta reconectar e enviar via HTTP
            await authFetch(`/community/channel/${activeChannelId}/send`, {method:'POST', body: JSON.stringify({content: msg})});
        }
    }catch(e){ console.error(e); showToast("Erro ao enviar."); }
}

async function uploadCommImage(){
    let f=document.getElementById('comm-file').files[0];
    if(!f)return;
    try{
        let formData=new FormData();
        formData.append('file',f);
        let res=await authFetch('/upload',{method:'POST',body:formData});
        let data=await res.json();
        await authFetch(`/community/channel/${activeChannelId}/send`,{method:'POST',body:JSON.stringify({content:(pickUploadedUrl(data) || '')})});
    }catch(e){ console.error(e); }
}