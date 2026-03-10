// ═══════════════════════════════════════════════════════════════
// FOR GLORY — CORE — Globals, i18n, Utils, AuthFetch, WebSocket, Lifecycle
// Gerado por splitter v2 — extração correta por profundidade de chaves
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */


window.dmSendQueue = window.dmSendQueue || [];
window.dmWSChatKey = window.dmWSChatKey || null;
window.deleteTarget = {type: null, id: null};
window.onlineUsers = []; window.unreadData = {}; window.lastTotalUnread = 0;
window.FEED_ENABLED = false;
var user=null, dmWS=null, commWS=null, globalWS=null, syncInterval=null, 
    lastFeedHash="", currentEmojiTarget=null, currentChatId=null, currentChatType=null;
var currentChatLoadToken = 0;
var activeCommId=null, activeChannelId=null;
let mediaRecorders = {}; let audioChunks = {}; let recordTimers = {}; let recordSeconds = {};
let rtc = { localAudioTrack: null, client: null, remoteUsers: {} };
let callDuration = 0, callInterval = null; 
window.pendingCallChannel = null; window.pendingCallType = null;
window.currentAgoraChannel = null;
window.isCaller = false;
window.callTargetId = null;


const EMOJIS = window.EMOJIS || [
  "😀","😁","😂","🤣","😊","😍","😘","😎","🤔","😅","😭","😡",
  "👍","👎","🙏","💪","🔥","⭐","🎉","❤️","💔","😴","🤯","🥶",
  "😈","🤝","🎮","🏆","⚔️","🛡️","📌","📎","✅","❌","⚠️","💬"
];
window.EMOJIS = EMOJIS;

const T = {
    'pt': {
        'login_title': 'FOR GLORY', 'login': 'ENTRAR', 'create_acc': 'Criar Conta', 'forgot': 'Esqueci Senha',
        'codename': 'CODINOME', 'password': 'SENHA', 'new_user': 'NOVO USUÁRIO', 'email_real': 'EMAIL (Real)', 'enlist': 'ALISTAR-SE', 'back': 'Voltar',
        'recover': 'RECUPERAR ACESSO', 'reg_email': 'SEU EMAIL CADASTRADO', 'send_link': 'ENVIAR LINK', 'new_pass_title': 'NOVA SENHA', 'new_pass': 'NOVA SENHA', 'save_pass': 'SALVAR SENHA',
        'confirm_action': 'CONFIRMAR AÇÃO', 'confirm_del': 'Tem certeza que deseja apagar isto?', 'delete': 'APAGAR', 'cancel': 'CANCELAR',
        'new_base': 'NOVA BASE OFICIAL', 'base_name': 'Nome da Base', 'base_desc': 'Descrição da Base', 'pub_base': '🌍 Pública', 'priv_base': '🔒 Privada', 'establish': 'ESTABELECER',
        'new_channel': 'NOVO CANAL', 'channel_name': 'Nome do Canal', 'ch_free': '💬 Livre', 'ch_text': '📝 Só Texto', 'ch_media': '🎬 Só Mídia', 'voice_channel': '🎙️ Canal de Voz', 'ch_pub': '🌍 Público', 'ch_priv': '🔒 Privado (Só Admins)', 'create_channel': 'CRIAR CANAL',
        'new_squad': 'NOVO ESQUADRÃO', 'group_name': 'Nome do Grupo', 'select_allies': 'Selecione os aliados:', 'create': 'CRIAR',
        'new_post': 'NOVO POST', 'caption_placeholder': 'Legenda...', 'publish': 'PUBLICAR (+50 XP)',
        'edit_profile': 'EDITAR PERFIL', 'bio_placeholder': 'Escreva sua Bio...', 'save': 'SALVAR',
        'edit_base': 'EDIT BASE', 'base_avatar': 'Novo Avatar', 'base_banner': 'Novo Banner',
        'stealth_on': '🕵️ MODO FURTIVO: ATIVADO', 'stealth_off': '🟢 MODO FURTIVO: DESATIVADO', 'search_soldier': 'Buscar Soldado...', 'requests': '📩 Solicitações', 'friends': '👥 Amigos', 'disconnect': 'DESCONECTAR',
        'private_msgs': 'MENSAGENS PRIVADAS', 'group_x1': '+ GRUPO X1', 'my_bases': '🛡️ MINHAS BASES', 'create_base': '+ CRIAR BASE',
        'explore_bases': '🌐 EXPLORAR BASES', 'search_base': 'Buscar Base...', 'my_history': '🕒 MEU HISTÓRICO',
        'msg_placeholder': 'Mensagem secreta...', 'base_msg_placeholder': 'Mensagem para a base...',
        'at': 'às', 'deleted_msg': '🚫 Apagada', 'audio_proc': 'Processando...',
        'recording': '🔴 Gravando...', 'click_to_send': '(Clique p/ enviar)',
        'empty_box': 'Sua caixa está vazia. Recrute aliados!', 'direct_msg': 'Mensagem Direta', 'squad': '👥 Esquadrão',
        'no_bases': 'Você ainda não tem bases.', 'no_bases_found': 'Nenhuma base encontrada.', 'no_history': 'Nenhuma missão registrada no Feed.',
        'request_join': '🔒 SOLICITAR', 'enter': '🌍 ENTRAR', 'ally': '✔ Aliado', 'sent': 'Enviado', 'accept_ally': 'Aceitar Aliado', 'recruit_ally': 'Recrutar Aliado',
        'creator': '👑 CRIADOR', 'admin': '🛡️ ADMIN', 'member': 'MEMBRO', 'promote': 'Promover', 'demote': 'Rebaixar', 'kick': 'Expulsar',
        'base_members': 'Membros da Base', 'entry_requests': 'Solicitações de Entrada', 'destroy_base': 'DESTRUIR BASE',
        'media_only': 'Canal restrito para mídia 📎', 'in_call': 'EM CHAMADA', 'join_call': 'ENTRAR NA CALL', 'incoming_call': 'CHAMADA RECEBIDA',
        'progression': 'PROGRESSO MILITAR (XP)', 'medals': '🏆 SALA DE TROFÉUS', 'base_banner_opt': 'Banner da Base (Opcional):', 'ch_banner_opt': 'Banner do Canal (Opcional):',
        'no_trophies': 'Soldado sem troféus'
    },
    'en': {
        'login_title': 'FOR GLORY', 'login': 'LOGIN', 'create_acc': 'Create Account', 'forgot': 'Forgot Password',
        'codename': 'CODENAME', 'password': 'PASSWORD', 'new_user': 'NEW USER', 'email_real': 'EMAIL (Real)', 'enlist': 'ENLIST', 'back': 'Back',
        'recover': 'RECOVER ACCESS', 'reg_email': 'REGISTERED EMAIL', 'send_link': 'SEND LINK', 'new_pass_title': 'NEW PASSWORD', 'new_pass': 'NEW PASSWORD', 'save_pass': 'SAVE PASSWORD',
        'confirm_action': 'CONFIRM ACTION', 'confirm_del': 'Are you sure you want to delete this?', 'delete': 'DELETE', 'cancel': 'CANCEL',
        'new_base': 'NEW OFFICIAL BASE', 'base_name': 'Base Name', 'base_desc': 'Description', 'pub_base': '🌍 Public', 'priv_base': '🔒 Private', 'establish': 'ESTABLISH',
        'new_channel': 'NEW CHANNEL', 'channel_name': 'Channel Name', 'ch_free': '💬 Free', 'ch_text': '📝 Text Only', 'ch_media': '🎬 Media Only', 'voice_channel': '🎙️ Voice Channel', 'ch_pub': '🌍 Public', 'ch_priv': '🔒 Private', 'create_channel': 'CREATE CHANNEL',
        'new_squad': 'NEW SQUAD', 'group_name': 'Group Name', 'select_allies': 'Select allies:', 'create': 'CREATE',
        'new_post': 'NEW POST', 'caption_placeholder': 'Caption...', 'publish': 'PUBLISH (+50 XP)',
        'edit_profile': 'EDIT PROFILE', 'bio_placeholder': 'Write your Bio...', 'save': 'SAVE',
        'edit_base': 'EDIT BASE', 'base_avatar': 'New Avatar', 'base_banner': 'New Banner',
        'stealth_on': '🕵️ STEALTH MODE: ON', 'stealth_off': '🟢 STEALTH MODE: OFF', 'search_soldier': 'Search Soldier...', 'requests': '📩 Requests', 'friends': '👥 Friends', 'disconnect': 'LOGOUT',
        'private_msgs': 'PRIVATE MESSAGES', 'group_x1': '+ DM SQUAD', 'my_bases': '🛡️ MY BASES', 'create_base': '+ CREATE BASE',
        'explore_bases': '🌐 EXPLORE BASES', 'search_base': 'Search Base...', 'my_history': '🕒 MY HISTORY',
        'msg_placeholder': 'Secret message...', 'base_msg_placeholder': 'Message to base...',
        'at': 'at', 'deleted_msg': '🚫 Deleted', 'audio_proc': 'Processing...',
        'recording': '🔴 Recording...', 'click_to_send': '(Click to send)',
        'empty_box': 'Your inbox is empty. Recruit allies!', 'direct_msg': 'Direct Message', 'squad': '👥 Squad',
        'no_bases': 'You have no bases yet.', 'no_bases_found': 'No bases found.', 'no_history': 'No missions recorded.',
        'request_join': '🔒 REQUEST', 'enter': '🌍 ENTER', 'ally': '✔ Ally', 'sent': 'Sent', 'accept_ally': 'Accept Ally', 'recruit_ally': 'Recruit Ally',
        'creator': '👑 CREATOR', 'admin': '🛡️ ADMIN', 'member': 'MEMBER', 'promote': 'Promote', 'demote': 'Demote', 'kick': 'Kick',
        'base_members': 'Members', 'entry_requests': 'Requests', 'destroy_base': 'DESTROY BASE',
        'media_only': 'Media restricted channel 📎', 'in_call': 'IN CALL', 'join_call': 'JOIN CALL', 'incoming_call': 'INCOMING CALL',
        'progression': 'PROGRESSION (XP)', 'medals': '🏆 MEDALS', 'base_banner_opt': 'Base Banner (Optional):', 'ch_banner_opt': 'Channel Banner (Optional):',
        'no_trophies': 'Soldier without trophies'
    },
    'es': {
        'login_title': 'FOR GLORY', 'login': 'ENTRAR', 'create_acc': 'Crear Cuenta', 'forgot': 'Olvidé la Contraseña',
        'codename': 'NOMBRE EN CLAVE', 'password': 'CONTRASEÑA', 'new_user': 'NUEVO USUARIO', 'email_real': 'CORREO', 'enlist': 'ALISTARSE', 'back': 'Volver',
        'recover': 'RECUPERAR ACCESO', 'reg_email': 'CORREO REGISTRADO', 'send_link': 'ENVIAR ENLACE', 'new_pass_title': 'NUEVA CONTRASEÑA', 'new_pass': 'NUEVA CONTRASEÑA', 'save_pass': 'GUARDAR CONTRASEÑA',
        'confirm_action': 'CONFIRMAR ACCIÓN', 'confirm_del': '¿Seguro que quieres borrar esto?', 'delete': 'BORRAR', 'cancel': 'CANCELAR',
        'new_base': 'NUEVA BASE OFICIAL', 'base_name': 'Nombre de la Base', 'base_desc': 'Descripción', 'pub_base': '🌍 Pública', 'priv_base': '🔒 Privada', 'establish': 'ESTABLECER',
        'new_channel': 'NUEVO CANAL', 'channel_name': 'Nombre del Canal', 'ch_free': '💬 Libre', 'ch_text': '📝 Solo Texto', 'ch_media': '🎬 Solo Medios', 'voice_channel': '🎙️ Canal de Voz', 'ch_pub': '🌍 Público', 'ch_priv': '🔒 Privado', 'create_channel': 'CREAR CANAL',
        'new_squad': 'NUEVO ESCUADRÓN', 'group_name': 'Nombre del Grupo', 'select_allies': 'Selecciona aliados:', 'create': 'CREAR',
        'new_post': 'NUEVO POST', 'caption_placeholder': 'Leyenda...', 'publish': 'PUBLICAR (+50 XP)',
        'edit_profile': 'EDITAR PERFIL', 'bio_placeholder': 'Escribe tu Bio...', 'save': 'GUARDAR',
        'edit_base': 'EDITAR BASE', 'base_avatar': 'Nuevo Avatar', 'base_banner': 'Nuevo Banner',
        'stealth_on': '🕵️ MODO FURTIVO: ON', 'stealth_off': '🟢 MODO FURTIVO: OFF', 'search_soldier': 'Buscar Soldado...', 'requests': '📩 Solicitudes', 'friends': '👥 Amigos', 'disconnect': 'DESCONECTAR',
        'private_msgs': 'MENSAJES PRIVADOS', 'group_x1': '+ ESCUADRÓN DM', 'my_bases': '🛡️ MIS BASES', 'create_base': '+ CREAR BASE',
        'explore_bases': '🌐 EXPLORAR BASES', 'search_base': 'Buscar Base...', 'my_history': '🕒 MI HISTORIAL',
        'msg_placeholder': 'Mensaje secreto...', 'base_msg_placeholder': 'Mensaje para la base...',
        'at': 'a las', 'deleted_msg': '🚫 Borrado', 'audio_proc': 'Procesando...',
        'recording': '🔴 Grabando...', 'click_to_send': '(Click mic enviar)',
        'empty_box': 'Tu buzón está vacío. ¡Recluta aliados!', 'direct_msg': 'Mensaje Directo', 'squad': '👥 Escuadrón',
        'no_bases': 'Aún no tienes bases.', 'no_bases_found': 'No se encontraron bases.', 'no_history': 'No hay misiones.',
        'request_join': '🔒 SOLICITAR', 'enter': '🌍 ENTRAR', 'ally': '✔ Aliado', 'sent': 'Enviado', 'accept_ally': 'Aceptar Aliado', 'recruit_ally': 'Reclutar Aliado',
        'creator': '👑 CREADOR', 'admin': '🛡️ ADMIN', 'member': 'MIEMBRO', 'promote': 'Promover', 'demote': 'Degradar', 'kick': 'Expulsar',
        'base_members': 'Miembros de la Base', 'entry_requests': 'Solicitudes de Entrada', 'destroy_base': 'DESTRUIR BASE',
        'media_only': 'Canal restringido a medios 📎', 'in_call': 'EN LLAMADA', 'join_call': 'ENTRAR A LA CALL', 'incoming_call': 'LLAMADA ENTRANTE',
        'progression': 'PROGRESO MILITAR (XP)', 'medals': '🏆 SALA DE TROFEOS', 'base_banner_opt': 'Banner de Base (Opcional):', 'ch_banner_opt': 'Banner del Canal (Opcional):',
        'no_trophies': 'Soldado sin trofeos'
    }
};


let sysLang = navigator.language ? navigator.language.substring(0,2) : 'en';
let validLangs = ['pt', 'en', 'es'];
window.currentLang = 'en';
try {
    let savedLang = localStorage.getItem('lang');
    if (validLangs.includes(savedLang)) { window.currentLang = savedLang; } 
    else { window.currentLang = validLangs.includes(sysLang) ? sysLang : 'en'; localStorage.setItem('lang', window.currentLang); }
} catch(e) { window.currentLang = validLangs.includes(sysLang) ? sysLang : 'en'; }


function t(key) { let dict = T[window.currentLang]; if (!dict) dict = T['en']; return dict[key] || key; }

function changeLanguage(lang) {
    try { localStorage.setItem('lang', lang); } catch (e) {}
    location.reload();
}

function setLangDropdownVisible(visible){
    const dd = document.querySelector('.lang-dropdown');
    if(!dd) return;
    dd.style.display = visible ? 'block' : 'none';
    if(!visible) dd.classList.remove('open');
}

function initLangDropdown(){
    // Inicializa o dropdown do login (dentro do modal)
    const dd = document.getElementById('lang-dropdown-login');
    const btn = document.getElementById('lang-btn-login');
    if(dd && btn) {
        btn.addEventListener('click', (e)=>{
            e.preventDefault();
            e.stopPropagation();
            dd.classList.toggle('open');
        });
        document.addEventListener('click', (e)=>{
            if(!dd.contains(e.target) && e.target !== btn) dd.classList.remove('open');
        });
        document.addEventListener('keydown', (e)=>{
            if(e.key === 'Escape') dd.classList.remove('open');
        });
    }
}

function escapeHtml(input) {
    const s = String(input ?? "");
    return s.replace(/[&<>"']/g, (ch) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }[ch]));
}
window.escapeHtml = escapeHtml;


function safeDisplayName(u) {
    const name =
        (u && (u.username || u.name || u.display_name || u.nickname || u.user)) ||
        "";
    const trimmed = String(name).trim();
    return trimmed ? trimmed : "Usuário";
}




// Picks the best URL field returned by /upload.
// Backend returns {url: "...", ...}. Older code expected secure_url.
function pickUploadedUrl(data) {
  try {
    const cand = (data && (data.secure_url || data.url || data.secureUrl || data.secureURL || data.location)) || "";
    const s = String(cand || "").trim();
    if (!s || s === "undefined" || s === "null") return null;
    if (s.startsWith("http://") || s.startsWith("https://")) return s;
    return s;
  } catch (e) {
    return null;
  }
}

function safeDisplayName(u) {
    const name =
        (u && (u.username || u.name || u.display_name || u.nickname || u.user)) ||
        "";
    const trimmed = String(name).trim();
    return trimmed ? trimmed : "Usuário";
}

function pickUploadedUrl(data) {
  try {
    const cand = (data && (data.secure_url || data.url || data.secureUrl || data.secureURL || data.location)) || "";
    const s = String(cand || "").trim();
    if (!s || s === "undefined" || s === "null") return null;
    if (s.startsWith("http://") || s.startsWith("https://")) return s;
    return s;
  } catch (e) {
    return null;
  }
}

function normalizeUserBasic(u, fallbackUid = null) {
    const id = (u && (u.id ?? u.uid)) ?? fallbackUid;
    const name = safeDisplayName(u);
    const avatar = safeAvatarUrl(u && (u.avatar_url || u.avatar || u.photo_url || u.photo || u.picture || u.profile_pic));
    return { id, name, avatar };
}

const __userBasicCache = window.__userBasicCache || (window.__userBasicCache = {});

async function getUserBasic(uid) {
    if (!uid && uid !== 0) return normalizeUserBasic({}, uid);
    if (__userBasicCache[uid]) return __userBasicCache[uid];
    try {
        const r = await fetch(`/users/basic/${uid}`);
        if (r.ok) {
            const data = await r.json();
            __userBasicCache[uid] = normalizeUserBasic(data, uid);
            return __userBasicCache[uid];
        }
    } catch (e) {}
    __userBasicCache[uid] = normalizeUserBasic({ username: `Usuário ${uid}` }, uid);
    return __userBasicCache[uid];
}

function showRanksModal() {
    const modal =
        document.getElementById('ranks-modal') ||
        document.getElementById('rank-modal') ||
        document.getElementById('modal-ranks');
    if (modal) {
        modal.style.display = 'block';
        modal.classList.add('open');
        return;
    }
    alert('Ranks: em breve.');
}


document.body.addEventListener('click', () => {
    if(window.ringtone && window.ringtone.state === 'suspended') window.ringtone.resume();
}, { once: true });
window.ringtone = new Audio('/static/sounds/ringtone.wav'); window.ringtone.loop = true;
window.callingSound = new Audio('/static/sounds/calling.wav'); window.callingSound.loop = true;
window.msgSound = new Audio('/static/sounds/message.wav');


function safePlaySound(snd) {
    try { let p = snd.play(); if (p !== undefined) { p.catch(e => console.log("Áudio bloqueado", e)); } } catch(err){}
}

function stopSounds() {
    try {
        if (window.callingSound) { window.callingSound.pause(); window.callingSound.currentTime = 0; }
    } catch (e) {}
    try {
        if (window.ringtone) { window.ringtone.pause(); window.ringtone.currentTime = 0; }
    } catch (e) {}
}

function buildDmCallChannel(a, b) {
    const x = Number(a), y = Number(b);
    const low = Math.min(x, y), high = Math.max(x, y);
    return `dm_${low}_${high}`;
}

function safeAvatarUrl(url, fallbackName){
  try{
    const s = (url === undefined || url === null) ? "" : String(url).trim();
    if(!s || s === "undefined" || s === "null"){
      return "/static/default-avatar.svg";
    }
    if (s.startsWith("http://") || s.startsWith("https://") || s.startsWith("data:")) return s;
    if (s.startsWith("/")) return s;
    return "/" + s;
  }catch(e){
    return "/static/default-avatar.svg";
  }
}

window.safeAvatarUrl = safeAvatarUrl;
window.safeDisplayName = safeDisplayName;
window.escapeHtml = escapeHtml;
window.showRanksModal = showRanksModal;

async function authFetch(url, options = {}) {
    const token = localStorage.getItem('token');
    if (token) {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (Date.now() >= payload.exp * 1000) {
                localStorage.removeItem('token');
                showToast('⚠️ Sessão expirada. Faça login novamente.');
                goView('auth');
                return new Response(null, { status: 401 });
            }
        } catch(e) {}
    }
    if (!token) {
        document.getElementById('modal-login').classList.remove('hidden');
        throw new Error('No token');
    }
    const isFormData = options.body instanceof FormData;
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        ...(isFormData ? {} : { 'Content-Type': 'application/json' })
    };
    const res = await fetch(url, options);
    if (res.status === 401) {
        localStorage.removeItem('token');
        user = null;
        showToast('⚠️ Sessão expirada. Faça login novamente.');
        showLoginScreen();
        throw new Error('Unauthorized');
    }
    return res;
}

function sendSystemDmMessage(text) {
  try {
    if (window.dmWS && dmWS.readyState === WebSocket.OPEN) {
      dmWS.send(String(text));
    }
  } catch (e) { console.warn('system dm message failed', e); }
}

function showLoginScreen() {
    setLangDropdownVisible(true);
    document.getElementById('app').style.display = 'none';
    document.getElementById('modal-login').classList.remove('hidden');
    toggleAuth('login');
}

document.addEventListener("DOMContentLoaded", async () => {
    initDraggableFloatingCallButton();
    // Tradução da interface
    let flag = window.currentLang === 'pt' ? '🇧🇷 PT' : (window.currentLang === 'es' ? '🇪🇸 ES' : '🇺🇸 EN');
    let langBtnLogin = document.getElementById('lang-btn-login');
    if(langBtnLogin) langBtnLogin.innerHTML = `🌍 ${flag}`;
    initLangDropdown();
    document.querySelectorAll('[data-i18n]').forEach(el => {
        let k = el.getAttribute('data-i18n');
        if(el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = t(k);
        else el.innerText = t(k);
    });

    // Checar token na URL (reset de senha)
    checkToken();

    // Tentar auto-login com token salvo
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
        try {
            const payload = JSON.parse(atob(savedToken.split('.')[1]));
            if (Date.now() < payload.exp * 1000) {
                const me = await fetch('/users/me', { headers: { 'Authorization': `Bearer ${savedToken}` } });
                if (me.ok) {
                    user = await me.json();
                    startApp();
                    return;
                }
            }
        } catch(e) {}
        localStorage.removeItem('token');
    }
});

function renderMedals(boxId, medalsData, isPublic = false) {
    let box = document.getElementById(boxId); 
    if(!medalsData) { box.innerHTML = ''; return; }
    let medalsToShow = isPublic ? medalsData.filter(m => m.earned) : medalsData;
    if (isPublic && medalsToShow.length === 0) {
        box.innerHTML = `<div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:12px; border:1px dashed #444; color:#888; font-style:italic;">🎖️ ${t('no_trophies')}</div>`;
        return;
    }
    if(!isPublic && medalsToShow.length === 0) { box.innerHTML = ''; return; }
    let mHtml = medalsToShow.map(m => {
        let op = m.earned ? '1' : '0.4'; let filter = m.earned ? 'drop-shadow(0 0 8px rgba(102,252,241,0.4))' : 'grayscale(100%)';
        let statusText = m.earned ? `<span style="color:#2ecc71;font-size:9px;">✔ Desbloqueado</span>` : `<span style="color:#ff5555;font-size:9px;">🔒 Faltam ${m.missing} XP</span>`;
        return `<div class="medal-card" style="background:rgba(0,0,0,0.5); padding:12px 5px; border-radius:12px; border:1px solid ${m.earned ? 'rgba(102,252,241,0.3)' : '#333'}; width:100px; text-align:center; opacity:${op}; display:flex; flex-direction:column; align-items:center; justify-content:space-between; transition:0.3s;" title="${m.desc}"><div style="font-size:32px; filter:${filter}; margin-bottom:5px;">${m.icon}</div><div style="font-size:11px; color:white; font-weight:bold; font-family:'Inter'; line-height:1.2; margin-bottom:4px;">${m.name}</div>${statusText}</div>`;
    }).join('');
    box.innerHTML = `<h3 style="color:var(--primary); font-family:'Rajdhani'; letter-spacing:1px; text-align:center; margin-top:30px; border-bottom:1px solid #333; padding-bottom:10px; display:inline-block;">${t('medals')}</h3><div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-bottom: 30px;">${mHtml}</div>`;
}

function updateUI(){
    if(!user) return;
    let safeAvatar = user.avatar_url; if(!safeAvatar || safeAvatar.includes("undefined")) safeAvatar = `https://ui-avatars.com/api/?name=${user.username}&background=1f2833&color=66fcf1&bold=true`;
    document.getElementById('nav-avatar').src = safeAvatar; document.getElementById('p-avatar').src = safeAvatar;
    let pCover = document.getElementById('p-cover'); pCover.src = user.cover_url || "https://placehold.co/600x200/0b0c10/66fcf1?text=FOR+GLORY"; pCover.style.display = 'block';
    document.getElementById('p-name').innerText = user.username || "Soldado"; document.getElementById('p-bio').innerText = user.bio || "Na base de operações."; 
    document.getElementById('p-emblems').innerHTML = formatRankInfo(user.rank, user.special_emblem, user.color);
    let missingXP = user.next_xp - user.xp;
    document.getElementById('p-progression-box').innerHTML = `<div class="xp-box" style="margin: 20px auto; width: 90%; max-width: 400px; text-align: left; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 12px; border: 1px solid #333;"><div style="display: flex; justify-content: space-between; margin-bottom: 5px;"><span style="color: var(--primary); font-weight: bold; font-size: 14px;">${t('progression')}</span><span style="color: white; font-size: 14px; font-family:'Rajdhani'; font-weight:bold;">${user.xp} / ${user.next_xp} XP</span></div><div class="xp-track" style="width: 100%; background: #222; height: 10px; border-radius: 5px; overflow: hidden; box-shadow:inset 0 2px 5px rgba(0,0,0,0.5);"><div class="xp-fill" style="width: ${user.percent}%; height: 100%; background: linear-gradient(90deg, #1d4e4f, var(--primary)); transition: width 0.5s;"></div></div><div style="display:flex; justify-content:space-between; margin-top:8px; align-items:center;"><span class="xp-label" style="color: #888; font-size: 11px;">Falta ${missingXP} XP para ${user.next_rank}</span><button class="btn-link" style="margin:0; font-size:11px;" onclick="showRanksModal()">Ver Patentes</button></div></div>`;
    renderMedals('p-medals-box', user.medals, false); document.querySelectorAll('.my-avatar-mini').forEach(img => img.src = safeAvatar); updateStealthUI();
}

function startApp(){
    document.getElementById('modal-login').classList.add('hidden'); document.getElementById('app').style.display = 'flex'; 
    updateUI(); fetchOnlineUsers(); fetchUnread(); goView('profile', document.getElementById('nav-profile-btn'));
    
    let p = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let token = localStorage.getItem('token');
    // --- WebSocket global (notificações / chamadas) ---
function connectGlobalWS(){
    try{ if(globalWS) globalWS.close(); }catch(e){}
    let p = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let token = localStorage.getItem('token');
    globalWS = new WebSocket(`${p}//${location.host}/ws/Geral/${user.id}?token=${token}`);

    globalWS.onmessage = (e) => {
        let d = JSON.parse(e.data);
        if(d.type === 'pong') return; 
        if(d.type === 'ping') { fetchUnread(); }

        if(d.type === 'sync_bg' && window.currentAgoraChannel === d.channel) {
            document.getElementById('expanded-call-panel').style.backgroundImage = `url('${d.bg_url}')`;
        }

        if(d.type === 'new_dm') {
            let isDmActive = document.getElementById('view-dm').classList.contains('active');
            if(isDmActive && currentChatType === '1v1' && currentChatId === d.sender_id) {} 
            else { safePlaySound(window.msgSound); fetchUnread(); }
        }

        if(d.type === 'kick_call' && d.target_id === user.id) {
            showToast("Você foi removido da chamada."); leaveCall();
        }

        if(d.type === 'call_accepted') {
            stopSounds();
            window.currentAgoraChannel = sanitizeChannelName(d.channel || window.pendingCallChannel);
            connectToAgora(window.currentAgoraChannel, window.pendingCallType);
        }

        if(d.type === 'call_rejected') {
            showToast("❌ Chamada recusada.");
            leaveCall();
        }

        if(d.type === 'call_cancelled') {
            showToast("⚠️ A chamada foi cancelada.");
            document.getElementById('modal-incoming-call').classList.add('hidden'); 
            stopSounds();
        }
        if(d.type === 'message_deleted') {
            applyRemoteDelete(d.msg_id);
        }


        if(d.type === 'incoming_call') {
            window.pendingCallerId = d.caller_id;
            document.getElementById('incoming-call-name').innerText = d.caller_name || 'Usuário';
            document.getElementById('incoming-call-av').src = safeAvatarUrl(d.caller_avatar, d.caller_name);

            // Canal: nunca pode ser null (Agora exige nome válido <= 64 bytes)
            let ch = d.channel_name;
            if(!ch && d.call_type === 'dm') ch = buildDmCallChannel(user.id, d.caller_id);
            if(!ch) ch = `call_${Date.now()}_${d.caller_id}_${user.id}`;
            window.pendingCallChannel = sanitizeChannelName(ch);
            window.currentAgoraChannel = window.pendingCallChannel;
            window.pendingCallType = d.call_type;

            document.getElementById('modal-incoming-call').classList.remove('hidden');
            safePlaySound(window.ringtone);
        }
    };

    globalWS.onclose = () => { 
        // reconecta só o websocket, sem reiniciar app (evita loops e múltiplos intervals)
        setTimeout(() => { if(user) connectGlobalWS();
// ── Reconexão ao voltar do segundo plano ──────────────────────────────
document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState !== 'hidden' && rtc.client && window.currentAgoraChannel) {
        try {
            // Verifica se o audio track ainda está publicado
            if (rtc.localAudioTrack && rtc.localAudioTrack.enabled === false) {
                await rtc.localAudioTrack.setEnabled(true);
            }
            // Se o cliente desconectou, tenta reconectar
            const state = rtc.client.connectionState;
            if (state === 'DISCONNECTED' || state === 'DISCONNECTING') {
                showToast('🔄 Reconectando call...');
                await connectToAgora(window.currentAgoraChannel, window.pendingCallType);
            }
        } catch(e) { console.warn('visibilitychange reconnect:', e); }
    }
});

// Mantém AudioContext ativo no mobile (evita suspensão pelo browser)
let _keepAliveInterval = null;
function _startCallKeepAlive() {
    if (_keepAliveInterval) return;
    _keepAliveInterval = setInterval(() => {
        try {
            if (rtc.client && AgoraRTC) {
                // Agora SDK mantém conexão — apenas verificamos estado
                const s = rtc.client.connectionState;
                if (s !== 'CONNECTED' && s !== 'CONNECTING' && window.currentAgoraChannel) {
                    console.warn('Keep-alive: state =', s);
                }
            }
        } catch(_) {}
    }, 8000);
}
function _stopCallKeepAlive() {
    if (_keepAliveInterval) { clearInterval(_keepAliveInterval); _keepAliveInterval = null; }
}

 }, 4000); 
    };
}
connectGlobalWS();

if(!window._globalPingInterval){
    window._globalPingInterval = setInterval(()=>{ 
        if(globalWS && globalWS.readyState === WebSocket.OPEN) { globalWS.send("ping"); } 
    }, 20000);
}
    syncInterval=setInterval(()=>{ 
        if(window.FEED_ENABLED && document.getElementById('view-feed').classList.contains('active')) loadFeed();
        fetchOnlineUsers();
    },4000);
}

function connectGlobalWS(){
    try{ if(globalWS) globalWS.close(); }catch(e){}
    let p = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let token = localStorage.getItem('token');
    globalWS = new WebSocket(`${p}//${location.host}/ws/Geral/${user.id}?token=${token}`);

    globalWS.onmessage = (e) => {
        let d = JSON.parse(e.data);
        if(d.type === 'pong') return; 
        if(d.type === 'ping') { fetchUnread(); }

        if(d.type === 'sync_bg' && window.currentAgoraChannel === d.channel) {
            document.getElementById('expanded-call-panel').style.backgroundImage = `url('${d.bg_url}')`;
        }

        if(d.type === 'new_dm') {
            let isDmActive = document.getElementById('view-dm').classList.contains('active');
            if(isDmActive && currentChatType === '1v1' && currentChatId === d.sender_id) {} 
            else { safePlaySound(window.msgSound); fetchUnread(); }
        }

        if(d.type === 'kick_call' && d.target_id === user.id) {
            showToast("Você foi removido da chamada."); leaveCall();
        }

        if(d.type === 'call_accepted') {
            stopSounds();
            window.currentAgoraChannel = sanitizeChannelName(d.channel || window.pendingCallChannel);
            connectToAgora(window.currentAgoraChannel, window.pendingCallType);
        }

        if(d.type === 'call_rejected') {
            showToast("❌ Chamada recusada.");
            leaveCall();
        }

        if(d.type === 'call_cancelled') {
            showToast("⚠️ A chamada foi cancelada.");
            document.getElementById('modal-incoming-call').classList.add('hidden'); 
            stopSounds();
        }
        if(d.type === 'message_deleted') {
            applyRemoteDelete(d.msg_id);
        }


        if(d.type === 'incoming_call') {
            window.pendingCallerId = d.caller_id;
            document.getElementById('incoming-call-name').innerText = d.caller_name || 'Usuário';
            document.getElementById('incoming-call-av').src = safeAvatarUrl(d.caller_avatar, d.caller_name);

            // Canal: nunca pode ser null (Agora exige nome válido <= 64 bytes)
            let ch = d.channel_name;
            if(!ch && d.call_type === 'dm') ch = buildDmCallChannel(user.id, d.caller_id);
            if(!ch) ch = `call_${Date.now()}_${d.caller_id}_${user.id}`;
            window.pendingCallChannel = sanitizeChannelName(ch);
            window.currentAgoraChannel = window.pendingCallChannel;
            window.pendingCallType = d.call_type;

            document.getElementById('modal-incoming-call').classList.remove('hidden');
            safePlaySound(window.ringtone);
        }
    };

    globalWS.onclose = () => { 
        // reconecta só o websocket, sem reiniciar app (evita loops e múltiplos intervals)
        setTimeout(() => { if(user) connectGlobalWS();
// ── Reconexão ao voltar do segundo plano ──────────────────────────────
// [visibilitychange duplicado removido]


// Mantém AudioContext ativo no mobile (evita suspensão pelo browser)
let _keepAliveInterval = null;
function _startCallKeepAlive() {
    if (_keepAliveInterval) return;
    _keepAliveInterval = setInterval(() => {
        try {
            if (rtc.client && AgoraRTC) {
                // Agora SDK mantém conexão — apenas verificamos estado
                const s = rtc.client.connectionState;
                if (s !== 'CONNECTED' && s !== 'CONNECTING' && window.currentAgoraChannel) {
                    console.warn('Keep-alive: state =', s);
                }
            }
        } catch(_) {}
    }, 8000);
}
function _stopCallKeepAlive() {
    if (_keepAliveInterval) { clearInterval(_keepAliveInterval); _keepAliveInterval = null; }
}

 }, 4000); 
    };
}

function _startCallKeepAlive() {
    if (_keepAliveInterval) return;
    _keepAliveInterval = setInterval(() => {
        try {
            if (rtc.client && AgoraRTC) {
                // Agora SDK mantém conexão — apenas verificamos estado
                const s = rtc.client.connectionState;
                if (s !== 'CONNECTED' && s !== 'CONNECTING' && window.currentAgoraChannel) {
                    console.warn('Keep-alive: state =', s);
                }
            }
        } catch(_) {}
    }, 8000);
}

function _stopCallKeepAlive() {
    if (_keepAliveInterval) { clearInterval(_keepAliveInterval); _keepAliveInterval = null; }
}

function logout(){ localStorage.removeItem('token'); user = null; if(syncInterval) clearInterval(syncInterval); if(globalWS) globalWS.close(); showLoginScreen(); }

function goView(v, btnElem){
    // Feed removido: redireciona qualquer tentativa para a caixa de entrada.
    if(v === 'feed' && !window.FEED_ENABLED){
        v = 'inbox';
    }
    document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));
    document.getElementById('view-'+v).classList.add('active');
    if(v !== 'public-profile' && v !== 'dm' && v !== 'comm-dashboard') { document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active')); if(btnElem) btnElem.classList.add('active'); else if(event && event.target && event.target.closest) event.target.closest('.nav-btn')?.classList.add('active'); }
    if(v === 'inbox') loadInbox(); if(v === 'mycomms') loadMyComms(); if(v === 'explore') loadPublicComms(); if(v === 'history') loadMyHistory(); if(v === 'feed') loadFeed();
    if(v === 'vip-panel' && typeof loadVipPanel === 'function') loadVipPanel();
}