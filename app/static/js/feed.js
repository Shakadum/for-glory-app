// ═══════════════════════════════════════════════════════════════
// FOR GLORY — FEED — Posts, Likes, Comentários, Histórico, Gravação
// Gerado por splitter v2 — extração correta por profundidade de chaves
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */

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

async function loadMyHistory(){try{let hist=await fetch(`/user/${user.id}?viewer_id=${user.id}&nocache=${new Date().getTime()}`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } }); let hData=await hist.json(); let grid=document.getElementById('my-posts-grid');if(!grid)return;if((hData.posts||[]).length===0)grid.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_history')}</p>`;(hData.posts||[]).forEach(p=>{grid.innerHTML+=p.media_type==='video'?`<video src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:10px;" controls preload="metadata"></video>`:`<img src="${p.content_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;cursor:pointer;border-radius:10px;" onclick="window.open(this.src)">`;});}catch(e){ console.error(e); }}

async function loadFeed(){
    if(!window.FEED_ENABLED) {
        const cont = document.getElementById('feed-container');
        if(cont) cont.innerHTML = `<div style="text-align:center;color:#888;padding:30px;">Feed desativado.</div>`;
        return;
    }
    try{let r=await fetch(`/posts?uid=${user.id}&limit=50&nocache=${new Date().getTime()}`);if(!r.ok)return;let p=await r.json();let h=JSON.stringify(p.map(x=>x.id+x.likes+x.comments+(x.user_liked?"1":"0")));if(h===lastFeedHash)return;lastFeedHash=h;let openComments=[];let activeInputs={};let focusedInputId=null;if(document.activeElement&&document.activeElement.classList.contains('comment-inp')){focusedInputId=document.activeElement.id;}document.querySelectorAll('.comments-section').forEach(sec=>{if(sec.style.display==='block')openComments.push(sec.id.split('-')[1]);});document.querySelectorAll('.comment-inp').forEach(inp=>{if(inp.value)activeInputs[inp.id]=inp.value;});let ht='';p.forEach(x=>{let m=x.media_type==='video'?`<video src="${x.content_url}" class="post-media" controls playsinline preload="metadata"></video>`:`<img src="${x.content_url}" class="post-media" loading="lazy">`;m=`<div class="post-media-wrapper">${m}</div>`;let delBtn=x.author_id===user.id?`<span onclick="window.deleteTarget={type:'post', id:${x.id}}; document.getElementById('modal-delete').classList.remove('hidden');" style="cursor:pointer;opacity:0.5;font-size:20px;transition:0.2s;" onmouseover="this.style.opacity='1';this.style.color='#ff5555'" onmouseout="this.style.opacity='0.5';this.style.color=''">🗑️</span>`:'';let heartIcon=x.user_liked?"❤️":"🤍";let heartClass=x.user_liked?"liked":"";let rankHtml=formatRankInfo(x.author_rank,x.special_emblem,x.rank_color);ht+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer" onclick="openPublicProfile(${x.author_id})"><div class="av-wrap" style="margin-right:12px;"><img src="${safeAvatarUrl(x.author_avatar, x.author_name)}" onerror="this.src='/static/default-avatar.svg'" class="post-av" style="margin:0;"><div class="status-dot" data-uid="${x.author_id}"></div></div><div class="user-info-box"><b style="color:white;font-size:14px">${x.author_name}</b><div style="margin-top:2px;">${rankHtml}</div></div></div>${delBtn}</div>${m}<div class="post-actions"><button class="action-btn ${heartClass}" onclick="toggleLike(${x.id}, this)"><span class="icon">${heartIcon}</span> <span class="count" style="color:white;font-weight:bold;">${x.likes}</span></button><button class="action-btn" onclick="toggleComments(${x.id})">💬 <span class="count" style="color:white;font-weight:bold;">${x.comments}</span></button></div><div class="post-caption"><b style="color:white;cursor:pointer;" onclick="openPublicProfile(${x.author_id})">${x.author_name}</b> ${(x.caption||"")}</div><div id="comments-${x.id}" class="comments-section"><div id="comment-list-${x.id}"></div><form class="comment-input-area" onsubmit="sendComment(${x.id}); return false;"><button type="button" class="icon-btn" id="btn-mic-comment-${x.id}" onclick="toggleRecord('comment-${x.id}')">🎤</button><input id="comment-inp-${x.id}" class="comment-inp" placeholder="${t('caption_placeholder')}" autocomplete="off"><button type="button" class="icon-btn" onclick="openEmoji('comment-inp-${x.id}')">😀</button><button type="submit" class="btn-send-msg">➤</button></form></div></div>`});document.getElementById('feed-container').innerHTML=ht;openComments.forEach(pid=>{let sec=document.getElementById(`comments-${pid}`);if(sec){sec.style.display='block';loadComments(pid);}});for(let id in activeInputs){let inp=document.getElementById(id);if(inp)inp.value=activeInputs[id];}if(focusedInputId){let inp=document.getElementById(focusedInputId);if(inp){inp.focus({preventScroll:true});let val=inp.value;inp.value='';inp.value=val;}}updateStatusDots();}catch(e){ console.error(e); }}

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

async function uploadToCloudinary(file){
    let formData=new FormData();
    formData.append('file',file);
    let res=await authFetch('/upload',{method:'POST',body:formData});
    let data=await res.json();
    return pickUploadedUrl(data);
}

async function submitPost(){
    let file=document.getElementById('file-upload').files[0];
    let caption=document.getElementById('caption-upload').value.trim();
    if(!file&&!caption)return;
    let btn=document.getElementById('btn-pub');
    btn.disabled=true;btn.innerText='⏳ POSTANDO...';
    try{
        let url=null;
        let mtype='text';
        if(file){
            url=await uploadToCloudinary(file);
            mtype=file.type.startsWith('video')?'video':'image';
        }
        let r=await authFetch('/post',{method:'POST',body:JSON.stringify({caption:caption,content_url:url||'',media_type:mtype})});
        if(r.ok){
            closeUpload();
            loadFeed();
            showToast('✔ Post publicado!');
        }
    }catch(e){ console.error(e); showToast('❌ Erro ao postar.'); }
    finally{ btn.disabled=false;btn.innerText=t('publish'); }
}