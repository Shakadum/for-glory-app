// ═══════════════════════════════════════════════════════════════
// FOR GLORY — MISC — Formatadores, Emoji, Sanitize, Diagnóstico, Typing
// Gerado por splitter v2 — extração correta por profundidade de chaves
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */

function isCallSystemMsg(text) {
    return typeof text === 'string' && (
        text.startsWith('📞 Chamada iniciada') ||
        text.startsWith('📞 Chamada finalizada') ||
        text.startsWith('📞 Call ini')
    );
}

function buildCallEventHtml(msgId, text, timeHtml) {
    // Separa ícone e texto para estilizar melhor
    const clean = text.replace('📞 ', '');
    return `<div id="${msgId}" class="msg-system-event">
        <div class="msg-system-bubble">
            <span class="msg-system-icon">📞</span>
            <span class="msg-system-text">${escapeHtml(clean)}</span>
            ${timeHtml}
        </div>
    </div>`;
}

function sanitizeChannelName(raw){
    if(raw===null || raw===undefined) return null;
    let s = String(raw).trim();
    if(!s) return null;
    const lower = s.toLowerCase();
    if(lower==='null' || lower==='undefined') return null;
    // caracteres permitidos: a-zA-Z0-9 espaço e alguns símbolos. Pra garantir, trocamos o resto por "_"
    s = s.replace(/[^a-zA-Z0-9 !#$%&()+\-:;<=>.?@\[\]^_{}|~ ,]/g, "_");
    // Agora limita em bytes (UTF-8). Como estamos com ASCII, 1 char = 1 byte.
    if(s.length > 60) s = s.slice(0, 60);
    // evita vazio/invalid
    if(!s) return null;
    return s;
}

function initEmojis(){let g=document.getElementById('emoji-grid'); if(!g) return; if(!window.EMOJIS||!Array.isArray(window.EMOJIS)){console.warn('EMOJIS missing'); return;} window.EMOJIS.forEach(e=>{ let s=document.createElement('div'); s.style.cssText="font-size:24px;cursor:pointer;text-align:center;padding:5px;border-radius:5px;transition:0.2s;"; s.innerText=e; s.onclick=()=>{ if(currentEmojiTarget){ let inp=document.getElementById(currentEmojiTarget); inp.value+=e; inp.focus(); } }; s.onmouseover=()=>s.style.background="rgba(102,252,241,0.2)"; s.onmouseout=()=>s.style.background="transparent"; g.appendChild(s); }); }

function closeUpload(){ document.getElementById('modal-upload').classList.add('hidden'); document.getElementById('file-upload').value=''; document.getElementById('caption-upload').value=''; }

function openEmoji(id){ currentEmojiTarget=id; document.getElementById('emoji-picker').style.display='flex'; }

function toggleEmoji(forceClose){ let e=document.getElementById('emoji-picker'); if(forceClose===true) e.style.display='none'; else e.style.display = e.style.display==='flex'?'none':'flex'; }

function updateStatusDots(){ document.querySelectorAll('.status-dot').forEach(dot=>{ let uid=parseInt(dot.getAttribute('data-uid')); if(!uid)return; if(window.onlineUsers.includes(uid)) dot.classList.add('online'); else dot.classList.remove('online'); }); }

async function loadDiagnostics() {
    const panel = document.getElementById('diagnostics-panel');
    const mini  = document.getElementById('diag-mini');
    if (!panel) return;
    panel.style.display = 'block';
    panel.innerHTML = '<div style="color:#4b5563;font-size:12px;text-align:center;padding:16px;">⏳ Executando diagnóstico...</div>';
    try {
        const r = await authFetch('/admin/diagnostics');
        if (r.status === 403) {
            panel.innerHTML = '<div style="color:#6b7280;font-size:12px;text-align:center;padding:16px;">Diagnóstico disponível apenas para administradores.</div>';
            return;
        }
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();

        const overallColor = d.overall==='ok'?'#10b981':d.overall==='warning'?'#f59e0b':'#ef4444';
        const overallIcon  = d.overall==='ok'?'✅':d.overall==='warning'?'⚠️':'❌';

        if (mini) mini.innerHTML = `${overallIcon} ${d.errors} erros · ${d.warnings} avisos · <span style="cursor:pointer;color:#66fcf1;text-decoration:underline;" onclick="loadDiagnostics()">Atualizar →</span>`;

        panel.innerHTML = `
            <div style="background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                    <div style="font-family:'Rajdhani';font-weight:800;font-size:14px;color:${overallColor};">
                        ${overallIcon} Sistema: ${d.overall.toUpperCase()}
                    </div>
                    <div style="font-size:11px;color:#4b5563;">${new Date(d.generated_at).toLocaleTimeString('pt-BR')}</div>
                </div>
                <div style="display:flex;flex-direction:column;gap:8px;">
                    ${(d.checks||[]).map(c => {
                        const color = c.status==='ok'?'#10b981':c.status==='warning'?'#f59e0b':'#ef4444';
                        const icon  = c.status==='ok'?'✅':c.status==='warning'?'⚠️':'❌';
                        return `<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;background:rgba(255,255,255,0.02);border-radius:8px;border:1px solid rgba(255,255,255,0.04);">
                            <span style="font-size:13px;">${icon}</span>
                            <div style="flex:1;">
                                <div style="font-size:12px;color:#e5e7eb;font-weight:600;">${escapeHtml(c.name)}</div>
                                <div style="font-size:11px;color:#6b7280;margin-top:2px;">${escapeHtml(c.message)}</div>
                            </div>
                            ${c.count > 0 ? `<span style="font-family:'Rajdhani';font-weight:700;font-size:13px;color:${color};">${c.count}</span>` : ''}
                        </div>`;
                    }).join('')}
                </div>
            </div>`;
    } catch(e) {
        console.error('loadDiagnostics:', e);
        panel.innerHTML = '<div style="color:#ef4444;font-size:12px;text-align:center;padding:16px;">Erro ao executar diagnóstico.</div>';
    }
}

let __typingTimer = null;

function onDmInputTyping() {
    if (!dmWS || dmWS.readyState !== WebSocket.OPEN) return;
    clearTimeout(__typingTimer);
    dmWS.send(JSON.stringify({type:'typing_start', username: user?.username||''}));
    __typingTimer = setTimeout(() => {
        if (dmWS && dmWS.readyState === WebSocket.OPEN) {
            dmWS.send(JSON.stringify({type:'typing_stop', username: user?.username||''}));
        }
    }, 2000);
}

function showTypingIndicator(username) {
    const list = document.getElementById('dm-list');
    if (!list) return;
    let ind = document.getElementById('typing-indicator');
    if (!ind) {
        list.insertAdjacentHTML('beforeend', `<div id="typing-indicator" style="padding:8px 12px;color:#6b7280;font-size:12px;font-style:italic;">${escapeHtml(username)} está digitando...</div>`);
    } else {
        ind.textContent = `${username} está digitando...`;
    }
    list.scrollTop = list.scrollHeight;
    clearTimeout(window.__typingHideTimer);
    window.__typingHideTimer = setTimeout(() => {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }, 3000);
}
