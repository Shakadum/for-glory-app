// ═══════════════════════════════════════════════════════════════
// FOR GLORY — AUTH — Login, Register, Reset de Senha
// Extraído de app.js — não editar este arquivo manualmente.
// Editar os blocos originais e rodar o splitter novamente.
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */
'use strict';

function toggleAuth(m){ ['login','register','forgot','reset'].forEach(f=>document.getElementById(f+'-form').classList.add('hidden')); document.getElementById(m+'-form').classList.remove('hidden'); }
async function doLogin() {
    let btn = document.querySelector('#login-form .btn-main');
    let originalText = btn ? btn.innerText : 'ENTRAR';
    if (btn) { btn.disabled = true; btn.innerText = '⏳ ENTRANDO...'; }
    try {
        let username = document.getElementById('l-user').value.trim();
        let password = document.getElementById('l-pass').value;
        if (!username || !password) { showToast('⚠️ Preencha usuário e senha.'); return; }
        let formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        let r = await fetch('/token', { method: 'POST', body: formData });
        if (r.status === 401) { showToast('❌ Usuário ou senha incorretos.'); return; }
        if (!r.ok) { showToast('❌ Erro no servidor. Tente novamente.'); return; }
        let data = await r.json();
        localStorage.setItem('token', data.access_token);
        let me = await fetch('/users/me', { headers: { 'Authorization': `Bearer ${data.access_token}` } });
        if (!me.ok) { showToast('❌ Erro ao carregar perfil.'); return; }
        user = await me.json();
        startApp();
    } catch(e) {
        console.error('Erro no login:', e);
        showToast('❌ Erro de conexão. Verifique sua internet.');
    } finally {
        if (btn) { btn.disabled = false; btn.innerText = originalText; }
    }
}
async function doRegister(){ let btn=document.querySelector('#register-form .btn-main'); let oldText=btn.innerText; btn.innerText="⏳ REGISTRANDO..."; btn.disabled=true; try{ let r=await fetch('/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username: document.getElementById('r-user').value, email: document.getElementById('r-email').value, password: document.getElementById('r-pass').value})}); if(!r.ok) throw new Error("Erro"); showToast("✔ Registrado! Faça login."); toggleAuth('login'); }catch(e){ console.error(e); showToast("❌ Erro no registro."); }finally{ btn.innerText=oldText; btn.disabled=false; } }
function formatMsgTime(iso){ if(!iso) return ""; let d=new Date(iso); return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')} ${t('at')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`; }
function formatRankInfo(rank, special, color){ return `${special ? `<span class="special-badge">${special}</span>` : ''}${rank ? `<span class="rank-badge" style="color:${color}; border-color:${color};">${rank}</span>` : ''}`; }

// Detecta se uma mensagem é evento de sistema (call iniciada/finalizada)

// [toggleStealth movida para módulo canônico]

// [updateStealthUI movida para módulo canônico]

async function requestReset(){let email=document.getElementById('f-email').value;if(!email)return showToast("Erro!");try{let r=await fetch('/auth/forgot-password', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email:email})}); showToast("Enviado!"); toggleAuth('login');}catch(e){console.error(e);showToast("Erro");}}
async function doResetPassword(){let newPass=document.getElementById('new-pass').value;if(!newPass)return showToast("Erro!");try{let r=await fetch('/auth/reset-password', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token:window.resetToken,new_password:newPass})}); if(r.ok){showToast("Alterada!");toggleAuth('login');}else{showToast("Link expirado.");}}catch(e){console.error(e);showToast("Erro");}}

// [renderMedals movida para módulo canônico]
