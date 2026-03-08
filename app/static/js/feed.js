// ═══════════════════════════════════════════════════════════════
// FOR GLORY — FEED — Posts, Likes, Comentários, Histórico, Gravação
// Extraído de app.js — não editar este arquivo manualmente.
// Editar os blocos originais e rodar o splitter novamente.
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */
'use strict';

}

async function toggleRecord(type) { 
    let btn=document.getElementById(`btn-mic-${type}`); 
    let inpId=type==='dm'?'dm-msg':(type==='comm'?'comm-msg':`comment-inp-${type.split('-')[1]}`); 
    let inp=document.getElementById(inpId); 
    
    if(mediaRecorders[type]&&mediaRecorders[type].state==='recording'){
        mediaRecorders[type].stop();
        btn.classList.remove('recording');
        clearInterval(recordTimers[type]);
        if(inp){inp.placeholder=t('audio_proc');inp.disabled=true;}
        return;
    } 
    try{ 
        let stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:false,sampleRate:48000}});
        let options={};
        if(MediaRecorder.isTypeSupported('audio/webm;codecs=opus')){options={mimeType:'audio/webm;codecs=opus',audioBitsPerSecond:128000};} 
        mediaRecorders[type]=new MediaRecorder(stream,options);
        audioChunks[type]=[];
        mediaRecorders[type].ondataavailable=e=>{if(e.data.size>0)audioChunks[type].push(e.data);}; 
        
        mediaRecorders[type].onstop=async()=>{ 
            let blob=new Blob(audioChunks[type],{type:'audio/webm'});
            let file=new File([blob],"radio.webm",{type:'audio/webm'}); 
            try{ 
                let formData = new FormData(); formData.append('file', file);
                let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} });
                let data = await res.json();
                const url = pickUploadedUrl(data);
                if(!url){ throw new Error("upload_sem_url"); }
                let audioMsg="[AUDIO]"+url; 
                if(type==='dm'&&dmWS){dmWS.send(audioMsg);}
                else if(type==='comm'&&commWS){commWS.send(audioMsg);}
                else if(type.startsWith('comment-')){ 
                    let pid=type.split('-')[1];
                    await authFetch('/post/comment', { method:'POST', body:JSON.stringify({post_id:pid,text:audioMsg}) });
                    try{ bumpCommentCount(pid, 1); }catch(e){};
                    await loadComments(pid);
                } 
            }catch(err){ console.error(err); showToast("Falha ao enviar áudio."); } 
            stream.getTracks().forEach(t=>t.stop());
            if(inp){ inp.disabled=false; inp.placeholder= t(type==='comm'?'base_msg_placeholder':'msg_placeholder'); } 
        }; 
        
        mediaRecorders[type].start();
        btn.classList.add('recording'); 
        if(inp){
            inp.disabled=true;recordSeconds[type]=0;inp.placeholder=`${t('recording')} 00:00`;
            recordTimers[type]=setInterval(()=>{
                recordSeconds[type]++;
                let mins=String(Math.floor(recordSeconds[type]/60)).padStart(2,'0');
                let secs=String(recordSeconds[type]%60).padStart(2,'0');
                inp.placeholder=`${t('recording')} ${mins}:${secs} ${t('click_to_send')}`;
            },1000);
        } 
    }catch(e){ console.error(e); showToast("Sem Microfone!");} 
}

async function loadMyHistory(){try{let hist=await fetch(`/user/${user.id}?viewer_id=${user.id}&nocache=${new Date().getTime()}`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } }); let hData=await hist.json(); let grid=document.getElementById('my-posts-grid');grid.innerHTML='';if((hData.posts||[]).length===0)grid.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_history')}</p>`;(hData.posts||[]).forEach(p=>{grid.innerHTML+=p.media_type==='video'?`<video src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:10px;" controls preload="metadata"></video>`:`<img src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;cursor:pointer;border-radius:10px;" onclick="window.open(this.src)">`;});}catch(e){ console.error(e); }}
async function loadFeed(){

// [2ª cópia de loadMyHistory removida — era duplicata do app.js original]

// [2ª cópia de loadFeed removida — era duplicata do app.js original]


document.getElementById('btn-confirm-delete').onclick=async()=>{if(!window.deleteTarget || !window.deleteTarget.id)return;let tp=window.deleteTarget.type;let id=window.deleteTarget.id;document.getElementById('modal-delete').classList.add('hidden');try{if(tp==='post'){let r=await authFetch('/post/delete', {method:'POST', body:JSON.stringify({post_id:id})}); if(r.ok){lastFeedHash=''; loadFeed(); loadMyHistory(); updateProfileState();}}else if(tp==='comment'){let r=await authFetch('/comment/delete', {method:'POST', body:JSON.stringify({comment_id:id})}); if(r.ok){lastFeedHash=''; loadFeed();}}else if(tp==='base'){let r=await authFetch(`/community/${id}/delete`, {method:'POST'}); if(r.ok){closeComm();loadMyComms();}}else if(tp==='channel'){let r=await authFetch(`/community/channel/${id}/delete`, {method:'POST'}); if(r.ok){document.getElementById('modal-edit-channel').classList.add('hidden');openCommunity(activeCommId, true);}}else if(tp==='dm_msg'||tp==='comm_msg'||tp==='group_msg'){let mainType=tp==='dm_msg'?'dm':(tp==='comm_msg'?'comm':'group');let r=await authFetch('/message/delete', {method:'POST', body:JSON.stringify({msg_id:id,type:mainType})}); let res=await r.json(); if(res.status==='ok'){try{ if(mainType==='dm' && typeof dmWS!=='undefined' && dmWS && dmWS.readyState===1){ dmWS.send(JSON.stringify({type:'message_deleted', msg_id:id})); } }catch(e){} let msgBubble=document.getElementById(`${tp}-${id}`).querySelector('.msg-bubble');let timeSpan=msgBubble.querySelector('.msg-time');let timeStr=timeSpan?timeSpan.outerHTML:'';msgBubble.innerHTML=`<span class="msg-deleted">${t('deleted_msg')}</span>${timeStr}`;let btn=document.getElementById(`${tp}-${id}`).querySelector('.del-msg-btn');if(btn)btn.remove();}}}catch(e){ console.error(e); }};

async function updateProfileState() { try { let r = await authFetch(`/user/${user.id}?viewer_id=${user.id}&nocache=${new Date().getTime()}`); let d = await r.json(); Object.assign(user, d); updateUI(); } catch(e) { console.error(e); } }
async function toggleLike(pid, btn) {
    try {
        let r = await authFetch('/post/like', {
            method: 'POST',
            body: JSON.stringify({ post_id: pid })
        });
        if (r.ok) {
            let d = await r.json();
            let icon = btn.querySelector('.icon');
            let count = btn.querySelector('.count');
            if (d.liked) {
                btn.classList.add('liked');
                icon.innerText = "❤️";
            } else {
                btn.classList.remove('liked');
                icon.innerText = "🤍";
            }
            count.innerText = d.count;
            lastFeedHash = "";
        }
    } catch (e) { console.error(e); }
}
async function toggleComments(pid){let sec=document.getElementById(`comments-${pid}`);if(sec.style.display==='block'){sec.style.display='none';}else{sec.style.display='block';loadComments(pid);}}

function bumpCommentCount(pid, delta=1){
    try{
        const btn = document.querySelector(`button[onclick="toggleComments(${pid})"]`);
        if(!btn) return;
        const span = btn.querySelector('.count');
        if(!span) return;
        const n = parseInt(span.innerText || span.textContent || "0", 10) || 0;
        span.innerText = String(n + delta);
    }catch(e){}
}

async function loadComments(pid){try{let r=await fetch(`/post/${pid}/comments?nocache=${new Date().getTime()}`);let list=document.getElementById(`comment-list-${pid}`);if(r.ok){let comments=await r.json();if((comments||[]).length===0){list.innerHTML=`<p style='color:#888;font-size:12px;text-align:center;'>Vazio</p>`;return;}list.innerHTML=comments.map(c=>{let delBtn=(c.author_id===user.id)?`<span onclick="window.deleteTarget={type:'comment', id:${c.id}}; document.getElementById('modal-delete').classList.remove('hidden');" style="color:#ff5555;cursor:pointer;margin-left:auto;font-size:14px;padding:0 5px;">🗑️</span>`:'';let txt=c.text;if(txt.startsWith('[AUDIO]')){txt=`<audio controls src="${txt.replace('[AUDIO]','')}" style="max-width:200px;height:35px;outline:none;margin-top:5px;"></audio>`;}return `<div class="comment-row" style="align-items:center;"><div class="av-wrap" onclick="openPublicProfile(${c.author_id})"><img src="${safeAvatarUrl(c.author_avatar, c.author_name)}" onerror="this.src='/static/default-avatar.svg'" class="comment-av"><div class="status-dot" data-uid="${c.author_id}" style="width:8px;height:8px;border-width:1px;"></div></div><div style="flex:1;"><b style="color:var(--primary);cursor:pointer;" onclick="openPublicProfile(${c.author_id})">${c.author_name}</b> <span style="display:inline-block;margin-left:5px;">${formatRankInfo(c.author_rank,c.special_emblem,c.color)}</span> <span style="color:#e0e0e0;display:block;margin-top:3px;">${txt}</span></div>${delBtn}</div>`}).join('');updateStatusDots();}}catch(e){ console.error(e); }}
async function sendComment(pid) {
    try {
        let inp = document.getElementById(`comment-inp-${pid}`);
        let text = inp.value.trim();
        if (!text) return;
        let r = await authFetch('/post/comment', {
            method: 'POST',
            body: JSON.stringify({ post_id: pid, text: text })
        });
        if (r.ok) {
            inp.value = '';
            toggleEmoji(true);
            try{ bumpCommentCount(pid, 1); }catch(e){};
                    await loadComments(pid);
        }
    } catch (e) { console.error(e); }
}
// [fetchChatMessages movida para módulo canônico]
