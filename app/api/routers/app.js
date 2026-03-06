

window.dmSendQueue = window.dmSendQueue || [];
window.dmWSChatKey = window.dmWSChatKey || null;
function sendSystemDmMessage(text) {
  try {
    if (window.dmWS && dmWS.readyState === WebSocket.OPEN) {
      dmWS.send(String(text));
    }
  } catch (e) { console.warn('system dm message failed', e); }
}
// ===== Emoji data (fallback) =====
const EMOJIS = window.EMOJIS || [
  "😀","😁","😂","🤣","😊","😍","😘","😎","🤔","😅","😭","😡",
  "👍","👎","🙏","💪","🔥","⭐","🎉","❤️","💔","😴","🤯","🥶",
  "😈","🤝","🎮","🏆","⚔️","🛡️","📌","📎","✅","❌","⚠️","💬"
];
window.EMOJIS = EMOJIS;

window.deleteTarget = {type: null, id: null};
// ===== Helpers (safety) =====
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
window.showRanksModal = showRanksModal;




// CLOUDINARY - NÃO USADO DIRETAMENTE (UPLOAD VIA BACKEND)
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
// Salva o idioma e recarrega a página (compatível com handlers inline do HTML)
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
    // Modal de login já está visível no HTML por padrão — não precisa fazer nada
});

function showLoginScreen() {
    setLangDropdownVisible(true);
    document.getElementById('app').style.display = 'none';
    document.getElementById('modal-login').classList.remove('hidden');
    toggleAuth('login');
}

var user=null, dmWS=null, commWS=null, globalWS=null, syncInterval=null, lastFeedHash="", currentEmojiTarget=null, currentChatId=null, currentChatType=null;

// ===== Feature toggles =====
// Remoção do FEED (timeline) solicitada: mantemos posts/perfil e outras funções,
// mas desativamos a navegação e o carregamento do feed.
window.FEED_ENABLED = false;
// Prevent race conditions when switching chats quickly (especially on mobile).
// Any async fetch/WS handler must check this token before mutating the DOM.
var currentChatLoadToken = 0;
var activeCommId=null, activeChannelId=null;
window.onlineUsers = []; window.unreadData = {}; window.lastTotalUnread = 0;
let mediaRecorders = {}; let audioChunks = {}; let recordTimers = {}; let recordSeconds = {};

let rtc = { localAudioTrack: null, client: null, remoteUsers: {} };
let callDuration = 0, callInterval = null; 
window.pendingCallChannel = null; window.pendingCallType = null;
window.currentAgoraChannel = null;
window.isCaller = false;
window.callTargetId = null;

// Desbloqueador de Áudio Automático
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


function safeDisplayName(obj) {
    if (!obj) return 'Usuário';
    return (obj.display_name || obj.name || obj.username || obj.user || obj.nickname || '').toString().trim() || 'Usuário';
}
// expõe helpers para handlers que rodam antes (evita "not defined" se algo falhar no parse parcial)
window.safeAvatarUrl = safeAvatarUrl;
window.safeDisplayName = safeDisplayName;


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
    // Não forçar Content-Type quando for FormData (upload de arquivos)
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


// ===== Draggable floating call button (mobile + desktop) =====
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

// ── Convidar para call em andamento ───────────────────────────────────
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

// Entrar em call já em andamento (sem ring)
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

window.callUsersCache = {};
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


// ===== Remote audio controls (mute other + volume 0..200) =====
window.__remoteAudioState = window.__remoteAudioState || {};

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

// Backward compatibility (old name used elsewhere)
function changeRemoteVol(uid, val) { setRemoteVolume(uid, val); }


let isMicMuted = false;
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

// Mostra/esconde botão de convidar conforme tipo da call
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
function isCallSystemMsg(text) {
    return typeof text === 'string' && (
        text.startsWith('📞 Chamada iniciada') ||
        text.startsWith('📞 Chamada finalizada') ||
        text.startsWith('📞 Call ini')
    );
}

// Gera HTML especial para mensagens de sistema (centralizadas, sem avatar)
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


// Sanitiza channel name pro Agora (<=64 bytes e caracteres permitidos)
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

function initEmojis(){let g=document.getElementById('emoji-grid'); if(!g) return; if(!window.EMOJIS||!Array.isArray(window.EMOJIS)){console.warn('EMOJIS missing'); return;} window.EMOJIS.forEach(e=>{ let s=document.createElement('div'); s.style.cssText="font-size:24px;cursor:pointer;text-align:center;padding:5px;border-radius:5px;transition:0.2s;"; s.innerText=e; s.onclick=()=>{ if(currentEmojiTarget){ let inp=document.getElementById(currentEmojiTarget); inp.value+=e; inp.focus(); } }; s.onmouseover=()=>s.style.background="rgba(102,252,241,0.2)"; s.onmouseout=()=>s.style.background="transparent"; g.appendChild(s); }); } initEmojis();
function checkToken(){ const urlParams=new URLSearchParams(window.location.search); const token=urlParams.get('token'); if(token){ toggleAuth('reset'); window.history.replaceState({}, document.title, "/"); window.resetToken=token; } }
function closeUpload(){ document.getElementById('modal-upload').classList.add('hidden'); document.getElementById('file-upload').value=''; document.getElementById('caption-upload').value=''; }
function openEmoji(id){ currentEmojiTarget=id; document.getElementById('emoji-picker').style.display='flex'; }
function toggleEmoji(forceClose){ let e=document.getElementById('emoji-picker'); if(forceClose===true) e.style.display='none'; else e.style.display = e.style.display==='flex'?'none':'flex'; }

document.addEventListener("visibilitychange", ()=>{ 
    if(document.visibilityState==="visible" && user){ 
        fetchUnread();
        fetchOnlineUsers();
        if(window.FEED_ENABLED && document.getElementById('view-feed').classList.contains('active')) loadFeed();
        if(activeChannelId && commWS && commWS.readyState!==WebSocket.OPEN) connectCommWS(activeChannelId);
    }
});

// Garante liberação do microfone ao sair/fechar aba (privacidade)
window.addEventListener('pagehide', ()=>{
    try{ if(rtc && (rtc.client || rtc.localAudioTrack)) leaveCall(); }catch(e){}
});
window.addEventListener('beforeunload', ()=>{
    try{ if(rtc && (rtc.client || rtc.localAudioTrack)) leaveCall(); }catch(e){}
});
async function fetchOnlineUsers(){ if(!user)return; try{ let r=await fetch(`/users/online?nocache=${new Date().getTime()}`); window.onlineUsers=await r.json(); updateStatusDots(); }catch(e){ console.error(e); } }
function updateStatusDots(){ document.querySelectorAll('.status-dot').forEach(dot=>{ let uid=parseInt(dot.getAttribute('data-uid')); if(!uid)return; if(window.onlineUsers.includes(uid)) dot.classList.add('online'); else dot.classList.remove('online'); }); }

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

async function submitCreateComm(e){e.preventDefault();let n=document.getElementById('new-comm-name').value.trim();let d=document.getElementById('new-comm-desc').value.trim();let p=document.getElementById('new-comm-priv').value;let avFile=document.getElementById('comm-avatar-upload').files[0];let banFile=document.getElementById('comm-banner-upload').files[0];if(!n)return showToast("Digite um nome!");let btn=e.target;btn.disabled=true;btn.innerText="CRIANDO...";try{let safeName=encodeURIComponent(n);let av="https://ui-avatars.com/api/?name="+safeName+"&background=111&color=66fcf1";let ban="https://placehold.co/600x200/0b0c10/1f2833?text="+safeName;if(avFile){let formData = new FormData(); formData.append('file', avFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); av = pickUploadedUrl(data) || av; } if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); ban = pickUploadedUrl(data) || ban; } let payload = { name:n, desc:d, is_priv:parseInt(p), avatar_url:av, banner_url:ban }; let r=await authFetch('/community/create', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-create-comm').classList.add('hidden');showToast("Base Criada!");loadMyComms();goView('mycomms');}}catch(err){console.error(err);showToast("Erro.");}finally{btn.disabled=false;btn.innerText=t('establish');}}
async function submitEditComm(){let avFile=document.getElementById('edit-comm-avatar').files[0];let banFile=document.getElementById('edit-comm-banner').files[0];if(!avFile&&!banFile)return showToast("Selecione algo.");let btn=document.getElementById('btn-save-comm');btn.disabled=true;btn.innerText="ENVIANDO...";try{let au=null; let bu=null; if(avFile){let formData = new FormData(); formData.append('file', avFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); au = pickUploadedUrl(data) || au; } if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); bu = pickUploadedUrl(data) || bu; } let payload = { comm_id: activeCommId, avatar_url: au, banner_url: bu }; let r=await authFetch('/community/edit', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-edit-comm').classList.add('hidden');showToast("Base Atualizada!");openCommunity(activeCommId, true);loadMyComms();}}catch(e){console.error(e);showToast("Erro.");}finally{btn.disabled=false;btn.innerText=t('save');}}
async function submitCreateChannel(){let n=document.getElementById('new-ch-name').value.trim();let tType=document.getElementById('new-ch-type').value;let p=document.getElementById('new-ch-priv').value;let banFile=document.getElementById('new-ch-banner').files[0];if(!n)return showToast("Digite o nome.");let btn=document.getElementById('btn-create-ch');btn.disabled=true;btn.innerText="CRIANDO...";try{let safeName=encodeURIComponent(n);let ban="https://placehold.co/600x200/0b0c10/1f2833?text="+safeName;if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); ban = pickUploadedUrl(data) || ban; } let payload = { comm_id: activeCommId, name:n, type:tType, is_private:parseInt(p), banner_url:ban }; let r=await authFetch('/community/channel/create', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-create-channel').classList.add('hidden');showToast("Canal Criado!");openCommunity(activeCommId, true);}}catch(err){console.error(err);}finally{btn.disabled=false;btn.innerText=t('create_channel');}}
async function toggleStealth(){try{let r=await authFetch('/profile/stealth', {method:'POST'}); if(r.ok){let d=await r.json(); user.is_invisible=d.is_invisible; updateStealthUI(); fetchOnlineUsers();}}catch(e){ console.error(e); }}
function updateStealthUI(){let btn=document.getElementById('btn-stealth');let myDot=document.getElementById('my-status-dot');if(user.is_invisible){btn.innerText=t('stealth_on');btn.style.borderColor="#ffaa00";btn.style.color="#ffaa00";myDot.classList.remove('online');}else{btn.innerText=t('stealth_off');btn.style.borderColor="rgba(102, 252, 241, 0.3)";btn.style.color="var(--primary)";myDot.classList.add('online');}}
async function requestReset(){let email=document.getElementById('f-email').value;if(!email)return showToast("Erro!");try{let r=await fetch('/auth/forgot-password', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email:email})}); showToast("Enviado!"); toggleAuth('login');}catch(e){console.error(e);showToast("Erro");}}
async function doResetPassword(){let newPass=document.getElementById('new-pass').value;if(!newPass)return showToast("Erro!");try{let r=await fetch('/auth/reset-password', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token:window.resetToken,new_password:newPass})}); if(r.ok){showToast("Alterada!");toggleAuth('login');}else{showToast("Link expirado.");}}catch(e){console.error(e);showToast("Erro");}}

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
        return `<div style="background:rgba(0,0,0,0.5); padding:12px 5px; border-radius:12px; border:1px solid ${m.earned ? 'rgba(102,252,241,0.3)' : '#333'}; width:100px; text-align:center; opacity:${op}; display:flex; flex-direction:column; align-items:center; justify-content:space-between; transition:0.3s;" title="${m.desc}"><div style="font-size:32px; filter:${filter}; margin-bottom:5px;">${m.icon}</div><div style="font-size:11px; color:white; font-weight:bold; font-family:'Inter'; line-height:1.2; margin-bottom:4px;">${m.name}</div>${statusText}</div>`;
    }).join('');
    box.innerHTML = `<h3 style="color:var(--primary); font-family:"Rajdhani"; letter-spacing:1px; text-align:center; margin-top:30px; border-bottom:1px solid #333; padding-bottom:10px; display:inline-block;">${t('medals')}</h3><div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-bottom: 30px;">${mHtml}</div>`;
}

function updateUI(){
    if(!user) return;
    let safeAvatar = user.avatar_url; if(!safeAvatar || safeAvatar.includes("undefined")) safeAvatar = `https://ui-avatars.com/api/?name=${user.username}&background=1f2833&color=66fcf1&bold=true`;
    document.getElementById('nav-avatar').src = safeAvatar; document.getElementById('p-avatar').src = safeAvatar;
    let pCover = document.getElementById('p-cover'); pCover.src = user.cover_url || "https://placehold.co/600x200/0b0c10/66fcf1?text=FOR+GLORY"; pCover.style.display = 'block';
    document.getElementById('p-name').innerText = user.username || "Soldado"; document.getElementById('p-bio').innerText = user.bio || "Na base de operações."; 
    document.getElementById('p-emblems').innerHTML = formatRankInfo(user.rank, user.special_emblem, user.color);
    let missingXP = user.next_xp - user.xp;
    document.getElementById('p-progression-box').innerHTML = `<div style="margin: 20px auto; width: 90%; max-width: 400px; text-align: left; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 12px; border: 1px solid #333;"><div style="display: flex; justify-content: space-between; margin-bottom: 5px;"><span style="color: var(--primary); font-weight: bold; font-size: 14px;">${t('progression')}</span><span style="color: white; font-size: 14px; font-family:"Rajdhani"; font-weight:bold;">${user.xp} / ${user.next_xp} XP</span></div><div style="width: 100%; background: #222; height: 10px; border-radius: 5px; overflow: hidden; box-shadow:inset 0 2px 5px rgba(0,0,0,0.5);"><div style="width: ${user.percent}%; height: 100%; background: linear-gradient(90deg, #1d4e4f, var(--primary)); transition: width 0.5s;"></div></div><div style="display:flex; justify-content:space-between; margin-top:8px; align-items:center;"><span style="color: #888; font-size: 11px;">Falta ${missingXP} XP para ${user.next_rank}</span><button class="btn-link" style="margin:0; font-size:11px;" onclick="showRanksModal()">Ver Patentes</button></div></div>`;
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
    if(!window.FEED_ENABLED) {
        const cont = document.getElementById('feed-container');
        if(cont) cont.innerHTML = `<div style="text-align:center;color:#888;padding:30px;">Feed desativado.</div>`;
        return;
    }
    try{let r=await fetch(`/posts?uid=${user.id}&limit=50&nocache=${new Date().getTime()}`);if(!r.ok)return;let p=await r.json();let h=JSON.stringify(p.map(x=>x.id+x.likes+x.comments+(x.user_liked?"1":"0")));if(h===lastFeedHash)return;lastFeedHash=h;let openComments=[];let activeInputs={};let focusedInputId=null;if(document.activeElement&&document.activeElement.classList.contains('comment-inp')){focusedInputId=document.activeElement.id;}document.querySelectorAll('.comments-section').forEach(sec=>{if(sec.style.display==='block')openComments.push(sec.id.split('-')[1]);});document.querySelectorAll('.comment-inp').forEach(inp=>{if(inp.value)activeInputs[inp.id]=inp.value;});let ht='';p.forEach(x=>{let m=x.media_type==='video'?`<video src="${x.content_url}" class="post-media" controls playsinline preload="metadata"></video>`:`<img src="${x.content_url}" class="post-media" loading="lazy">`;m=`<div class="post-media-wrapper">${m}</div>`;let delBtn=x.author_id===user.id?`<span onclick="window.deleteTarget={type:'post', id:${x.id}}; document.getElementById('modal-delete').classList.remove('hidden');" style="cursor:pointer;opacity:0.5;font-size:20px;transition:0.2s;" onmouseover="this.style.opacity='1';this.style.color='#ff5555'" onmouseout="this.style.opacity='0.5';this.style.color=''">🗑️</span>`:'';let heartIcon=x.user_liked?"❤️":"🤍";let heartClass=x.user_liked?"liked":"";let rankHtml=formatRankInfo(x.author_rank,x.special_emblem,x.rank_color);ht+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer" onclick="openPublicProfile(${x.author_id})"><div class="av-wrap" style="margin-right:12px;"><img src="${safeAvatarUrl(x.author_avatar, x.author_name)}" onerror="this.src='/static/default-avatar.svg'" class="post-av" style="margin:0;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${x.author_id}"></div></div><div class="user-info-box"><b style="color:white;font-size:14px">${x.author_name}</b><div style="margin-top:2px;">${rankHtml}</div></div></div>${delBtn}</div>${m}<div class="post-actions"><button class="action-btn ${heartClass}" onclick="toggleLike(${x.id}, this)"><span class="icon">${heartIcon}</span> <span class="count" style="color:white;font-weight:bold;">${x.likes}</span></button><button class="action-btn" onclick="toggleComments(${x.id})">💬 <span class="count" style="color:white;font-weight:bold;">${x.comments}</span></button></div><div class="post-caption"><b style="color:white;cursor:pointer;" onclick="openPublicProfile(${x.author_id})">${x.author_name}</b> ${(x.caption||"")}</div><div id="comments-${x.id}" class="comments-section"><div id="comment-list-${x.id}"></div><form class="comment-input-area" onsubmit="sendComment(${x.id}); return false;"><button type="button" class="icon-btn" id="btn-mic-comment-${x.id}" onclick="toggleRecord('comment-${x.id}')">🎤</button><input id="comment-inp-${x.id}" class="comment-inp" placeholder="${t('caption_placeholder')}" autocomplete="off"><button type="button" class="icon-btn" onclick="openEmoji('comment-inp-${x.id}')">😀</button><button type="submit" class="btn-send-msg">➤</button></form></div></div>`});document.getElementById('feed-container').innerHTML=ht;openComments.forEach(pid=>{let sec=document.getElementById(`comments-${pid}`);if(sec){sec.style.display='block';loadComments(pid);}});for(let id in activeInputs){let inp=document.getElementById(id);if(inp)inp.value=activeInputs[id];}if(focusedInputId){let inp=document.getElementById(focusedInputId);if(inp){inp.focus({preventScroll:true});let val=inp.value;inp.value='';inp.value=val;}}updateStatusDots();}catch(e){ console.error(e); }}

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

async function loadComments(pid){try{let r=await fetch(`/post/${pid}/comments?nocache=${new Date().getTime()}`);let list=document.getElementById(`comment-list-${pid}`);if(r.ok){let comments=await r.json();if((comments||[]).length===0){list.innerHTML=`<p style='color:#888;font-size:12px;text-align:center;'>Vazio</p>`;return;}list.innerHTML=comments.map(c=>{let delBtn=(c.author_id===user.id)?`<span onclick="window.deleteTarget={type:'comment', id:${c.id}}; document.getElementById('modal-delete').classList.remove('hidden');" style="color:#ff5555;cursor:pointer;margin-left:auto;font-size:14px;padding:0 5px;">🗑️</span>`:'';let txt=c.text;if(txt.startsWith('[AUDIO]')){txt=`<audio controls src="${txt.replace('[AUDIO]','')}" style="max-width:200px;height:35px;outline:none;margin-top:5px;"></audio>`;}return `<div class="comment-row" style="align-items:center;"><div class="av-wrap" onclick="openPublicProfile(${c.author_id})"><img src="${safeAvatarUrl(c.author_avatar, c.author_name)}" onerror="this.src='/static/default-avatar.svg'" class="comment-av" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${c.author_id}" style="width:8px;height:8px;border-width:1px;"></div></div><div style="flex:1;"><b style="color:var(--primary);cursor:pointer;" onclick="openPublicProfile(${c.author_id})">${c.author_name}</b> <span style="display:inline-block;margin-left:5px;">${formatRankInfo(c.author_rank,c.special_emblem,c.color)}</span> <span style="color:#e0e0e0;display:block;margin-top:3px;">${txt}</span></div>${delBtn}</div>`}).join('');updateStatusDots();}}catch(e){ console.error(e); }}
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
                        <img src="${safeAvatarUrl(d.avatar, safeDisplayName(d))}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'">
                        <div>
                            <div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${escapeHtml(safeDisplayName(d))} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div>
                            <div class="msg-bubble">${c}${timeHtml}${delBtn}</div>
                        </div>
                    </div>`;
                    }
                    list.insertAdjacentHTML('beforeend', h);
                }
            });
            if (isAtBottom) list.scrollTop = list.scrollHeight;
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
                <img src="${safeAvatarUrl(d.avatar, safeDisplayName(d))}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'">
                <div>
                    <div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${escapeHtml(safeDisplayName(d))} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div>
                    <div class="msg-bubble">${c}${timeHtml}${delBtn}</div>
                </div>
            </div>`;
            }
            b.insertAdjacentHTML('beforeend', h);
            b.scrollTop = b.scrollHeight;
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
async function loadMyComms(){try{let r=await authFetch(`/communities/list?nocache=${new Date().getTime()}`); let d=await r.json(); let mList=document.getElementById('my-comms-grid');mList.innerHTML='';if((d.my_comms||[]).length===0)mList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases')}</p>`;(d.my_comms||[]).forEach(c=>{mList.innerHTML+=`<div class="comm-card" data-id="${c.id}" onclick="openCommunity(${c.id})"><img src="${safeAvatarUrl(c.avatar_url)}" class="comm-avatar"><div class="req-dot" style="display:none;position:absolute;top:-5px;right:-5px;background:#ff5555;color:white;font-size:10px;padding:3px 8px;border-radius:12px;font-weight:bold;box-shadow:0 0 10px #ff5555;border:2px solid var(--dark-bg);z-index:10;">NOVO</div><b style="color:white;font-size:16px;font-family:"Rajdhani";letter-spacing:1px;">${c.name}</b></div>`;});fetchUnread();}catch(e){ console.error(e); }}
async function loadPublicComms(){try{let r=await authFetch(`/communities/search?nocache=${new Date().getTime()}`); let d=await r.json(); let pList=document.getElementById('public-comms-grid');pList.innerHTML='';if((d||[]).length===0)pList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;(d||[]).forEach(c=>{let btnStr=c.is_private?`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:orange;color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>`:`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:#2ecc71;color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;pList.innerHTML+=`<div class="comm-card"><img src="${safeAvatarUrl(c.avatar_url)}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:"Rajdhani";letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`;});}catch(e){ console.error(e); }}
function clearCommSearch(){document.getElementById('search-comm-input').value='';loadPublicComms();}
async function searchComms(){try{let q=document.getElementById('search-comm-input').value.trim();let r=await authFetch(`/communities/search?q=${q}&nocache=${new Date().getTime()}`); let d=await r.json(); let pList=document.getElementById('public-comms-grid');pList.innerHTML='';if((d||[]).length===0)pList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;(d||[]).forEach(c=>{let btnStr=c.is_private?`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:orange;color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>`:`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:#2ecc71;color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;pList.innerHTML+=`<div class="comm-card"><img src="${safeAvatarUrl(c.avatar_url)}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:"Rajdhani";letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`;});}catch(e){ console.error(e); }}
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

async function promoteMember(cid,tid){try{let payload={comm_id:cid,target_id:tid};let r=await authFetch('/community/member/promote', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){await openCommunity(cid, true);}}catch(e){ console.error(e); }}
async function demoteMember(cid,tid){try{let payload={comm_id:cid,target_id:tid};let r=await authFetch('/community/member/demote', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){await openCommunity(cid, true);}}catch(e){ console.error(e); }}
async function kickMember(cid,tid){if(confirm("Tem certeza que dese?")){try{let payload={comm_id:cid,target_id:tid};let r=await authFetch('/community/member/kick', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){await openCommunity(cid, true);}}catch(e){ console.error(e); }}}
function showCommInfo(){document.getElementById('comm-chat-area').style.display='none';document.getElementById('comm-info-area').style.display='flex';}
function closeComm(){goView('mycomms',document.querySelectorAll('.nav-btn')[3]);if(commWS)commWS.close();}

window.currentEditChannelId=null;
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
                    let h=`<div id="${msgId}" class="msg-row ${m?'mine':''}"><img src="${safeAvatarUrl(d.avatar, safeDisplayName(d))}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div><div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${escapeHtml(safeDisplayName(d))} ${formatRankInfo(d.rank,d.special_emblem,d.color)}</div><div class="msg-bubble">${c}${timeHtml}${delBtn}</div></div></div>`;
                    list.insertAdjacentHTML('beforeend',h);
                }
            });
            if(isAtBottom)list.scrollTop=list.scrollHeight;
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

// ===================== Group Settings Modal =====================
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


// ═══════════════════════════════════════════════════════════════
//  QUIZ & GLORY PANEL
// ═══════════════════════════════════════════════════════════════

async function loadQuizPanel() {
    await loadGloryHeader();
    await loadQuizzes();
    await loadQuizRanking();
}

async function loadGloryHeader() {
    try {
        const r = await authFetch('/my/plan');
        if (!r.ok) return;
        const d = await r.json();

        const pts = d.glory?.points || 0;
        const rankName  = d.glory?.rank_name  || 'Cidadão Comum';
        const rankIcon  = d.glory?.rank_icon  || '👤';
        const planName  = d.plan?.name || 'Gratuito';
        const multiplier = d.plan?.glory_multiplier || 1;

        const el = (id) => document.getElementById(id);
        if (el('glory-rank-name'))   el('glory-rank-name').innerText   = rankName;
        if (el('glory-points-total')) el('glory-points-total').innerText = pts.toLocaleString('pt-BR');
        if (el('glory-rank-icon'))   el('glory-rank-icon').innerText   = rankIcon;
        if (el('glory-plan-name'))   el('glory-plan-name').innerText   = `${planName}${multiplier > 1 ? ` · ${multiplier}x Glory` : ''}`;

        // Progress bar placeholder (next rank requires points data)
        const bar = el('glory-progress-bar');
        if (bar) bar.style.width = Math.min(((pts % 1000) / 10), 100) + '%';

        // Store for use in other places
        window.__gloryData = d;
    } catch(e) { console.warn('loadGloryHeader:', e); }
}

async function loadQuizzes() {
    const container = document.getElementById('quiz-list');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;color:#4b5563;padding:30px;font-family:DM Sans,sans-serif;font-size:13px;">⏳ Carregando...</div>';
    try {
        const r = await authFetch('/quizzes?limit=20');
        if (!r.ok) { container.innerHTML = '<div style="color:#888;text-align:center;padding:20px;">Sem quizzes disponíveis.</div>'; return; }
        const quizzes = await r.json();
        if (!quizzes.length) {
            container.innerHTML = '<div style="color:#888;text-align:center;padding:30px;font-family:"DM Sans";font-size:13px;">Nenhum quiz disponível ainda.<br><span style="font-size:11px;opacity:0.6;">Admins podem criar quizzes via API.</span></div>';
            return;
        }
        const catColors = {news:'#ef4444',politicians:'#3b82f6',constitution:'#8b5cf6',community:'#10b981',general:'#6b7280'};
        container.innerHTML = quizzes.map(q => {
            const col = catColors[q.category] || '#6b7280';
            const done = q.attempted;
            return `<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,${done?'0.04':'0.08'});border-radius:12px;padding:16px;display:flex;align-items:center;gap:14px;opacity:${done?'0.5':'1'};">
                <div style="width:42px;height:42px;border-radius:10px;background:${col}22;border:1px solid ${col}44;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">
                    ${q.category==='news'?'📰':q.category==='politicians'?'🏛️':q.category==='constitution'?'📜':q.category==='community'?'👥':'🧠'}
                </div>
                <div style="flex:1;min-width:0;">
                    <div style="font-family:"DM Sans";font-weight:600;font-size:13px;color:#e5e7eb;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(q.title)}</div>
                    <div style="display:flex;gap:8px;align-items:center;margin-top:5px;">
                        <span style="font-size:10px;color:${col};font-family:"Rajdhani";font-weight:700;letter-spacing:0.5px;">${(q.category||'').toUpperCase()}</span>
                        <span style="font-size:10px;color:#4b5563;">·</span>
                        <span style="font-size:10px;color:#4b5563;">${q.question_count} perguntas</span>
                        <span style="font-size:10px;color:#4b5563;">·</span>
                        <span style="font-size:10px;color:#4b5563;">${q.difficulty==='easy'?'Fácil':q.difficulty==='hard'?'Difícil':'Médio'}</span>
                    </div>
                </div>
                <div style="flex-shrink:0;">
                    ${done
                        ? '<span style="font-size:11px;color:#10b981;">✓ Feito</span>'
                        : `<button onclick="startQuiz(${q.id},'${escapeHtml(q.title)}')" style="background:#66fcf1;color:#0b0c10;border:none;border-radius:8px;padding:8px 14px;font-family:"Rajdhani";font-weight:700;font-size:12px;cursor:pointer;letter-spacing:0.5px;">JOGAR</button>`
                    }
                </div>
            </div>`;
        }).join('');
    } catch(e) { console.error('loadQuizzes:', e); container.innerHTML = '<div style="color:#888;text-align:center;padding:20px;">Erro ao carregar quizzes.</div>'; }
}

async function loadQuizRanking() {
    const el = document.getElementById('quiz-ranking');
    if (!el) return;
    try {
        const r = await fetch('/quizzes/ranking/weekly');
        if (!r.ok) return;
        const ranking = await r.json();
        if (!ranking.length) { el.innerHTML = '<div style="color:#4b5563;text-align:center;padding:20px;font-size:13px;">Nenhuma participação esta semana.</div>'; return; }
        el.innerHTML = ranking.slice(0, 10).map((entry, i) => {
            const medal = i===0?'🥇':i===1?'🥈':i===2?'🥉':`${i+1}.`;
            return `<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid rgba(255,255,255,0.06);">
                <span style="font-size:${i<3?'18':'13'}px;width:24px;text-align:center;flex-shrink:0;">${medal}</span>
                <img src="${safeAvatarUrl(entry.avatar)}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;" onerror="this.src='/static/default-avatar.svg'">
                <span style="flex:1;font-family:"DM Sans";font-size:13px;color:#e5e7eb;">${escapeHtml(entry.username)}</span>
                <span style="font-family:"Rajdhani";font-weight:700;font-size:14px;color:#66fcf1;">${(entry.score_week||0).toLocaleString('pt-BR')} pts</span>
            </div>`;
        }).join('');
    } catch(e) { console.warn('loadQuizRanking:', e); }
}

// Quiz modal
let __quizData = null;
let __quizStartTime = null;

async function startQuiz(quizId, title) {
    try {
        const r = await authFetch(`/quizzes/${quizId}`);
        if (!r.ok) {
            const err = await r.json().catch(()=>({}));
            return showToast(err.detail || 'Erro ao carregar quiz');
        }
        __quizData = await r.json();
        __quizStartTime = Date.now();
        renderQuizModal(__quizData);
    } catch(e) { console.error('startQuiz:', e); showToast('Erro ao iniciar quiz.'); }
}

function renderQuizModal(quiz) {
    const existing = document.getElementById('modal-quiz');
    if (existing) existing.remove();

    let currentQ = 0;
    const answers = new Array(quiz.questions.length).fill(-1);

    function buildHTML() {
        const q = quiz.questions[currentQ];
        const total = quiz.questions.length;
        const progress = ((currentQ + 1) / total * 100).toFixed(0);
        return `
        <div id="modal-quiz" style="position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;">
            <div style="background:#111827;border:1px solid rgba(102,252,241,0.2);border-radius:18px;padding:24px;max-width:500px;width:100%;max-height:90vh;overflow-y:auto;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
                    <div style="font-family:"Rajdhani";font-weight:800;font-size:14px;color:#66fcf1;letter-spacing:1px;">QUIZ · ${currentQ+1}/${total}</div>
                    <button onclick="document.getElementById('modal-quiz').remove()" style="background:transparent;border:none;color:#6b7280;cursor:pointer;font-size:18px;">✕</button>
                </div>
                <div style="background:rgba(102,252,241,0.05);border-radius:20px;height:4px;margin-bottom:20px;overflow:hidden;">
                    <div style="height:100%;background:#66fcf1;border-radius:20px;width:${progress}%;transition:width 0.3s;"></div>
                </div>
                <div style="font-family:"DM Sans";font-weight:600;font-size:15px;color:#f3f4f6;line-height:1.5;margin-bottom:20px;">${escapeHtml(q.question)}</div>
                <div id="quiz-options" style="display:flex;flex-direction:column;gap:10px;">
                    ${q.options.map((opt, i) => `
                    <button onclick="selectAnswer(${i})" id="quiz-opt-${i}" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:14px 16px;text-align:left;color:#e5e7eb;font-family:"DM Sans";font-size:13px;cursor:pointer;transition:all 0.15s;width:100%;"
                        onmouseover="if(!this.dataset.locked)this.style.borderColor='rgba(102,252,241,0.4)'"
                        onmouseout="if(!this.dataset.locked)this.style.borderColor='rgba(255,255,255,0.1)'">
                        <span style="color:#66fcf1;margin-right:10px;font-weight:700;">${['A','B','C','D'][i]}.</span>${escapeHtml(opt)}
                    </button>`).join('')}
                </div>
                <div id="quiz-explanation" style="display:none;margin-top:16px;padding:14px;background:rgba(102,252,241,0.05);border:1px solid rgba(102,252,241,0.15);border-radius:10px;font-size:12px;color:#9ca3af;line-height:1.5;"></div>
                <div id="quiz-nav" style="margin-top:18px;display:flex;justify-content:flex-end;gap:10px;display:none;">
                    <button id="quiz-next-btn" onclick="nextQuizQuestion()" style="background:#66fcf1;color:#0b0c10;border:none;border-radius:8px;padding:10px 20px;font-family:"Rajdhani";font-weight:700;font-size:13px;cursor:pointer;letter-spacing:0.5px;">
                        ${currentQ < total-1 ? 'PRÓXIMA →' : 'FINALIZAR ✓'}
                    </button>
                </div>
            </div>
        </div>`;
    }

    document.body.insertAdjacentHTML('beforeend', buildHTML());

    window.selectAnswer = function(idx) {
        const q = quiz.questions[currentQ];
        answers[currentQ] = idx;
        // Lock buttons
        document.querySelectorAll('#quiz-options button').forEach((btn, i) => {
            btn.dataset.locked = '1';
            btn.style.cursor = 'default';
            if (i === q.correct_index) {
                btn.style.background = 'rgba(16,185,129,0.15)';
                btn.style.borderColor = '#10b981';
                btn.style.color = '#10b981';
            } else if (i === idx && idx !== q.correct_index) {
                btn.style.background = 'rgba(239,68,68,0.15)';
                btn.style.borderColor = '#ef4444';
                btn.style.color = '#ef4444';
            }
        });
        // Show explanation
        if (q.explanation) {
            const expl = document.getElementById('quiz-explanation');
            if (expl) { expl.style.display = 'block'; expl.innerHTML = `💡 ${escapeHtml(q.explanation)}`; }
        }
        document.getElementById('quiz-nav').style.display = 'flex';
    };

    window.nextQuizQuestion = function() {
        const modal = document.getElementById('modal-quiz');
        if (!modal) return;
        if (currentQ < quiz.questions.length - 1) {
            currentQ++;
            modal.remove();
            document.body.insertAdjacentHTML('beforeend', buildHTML());
            // Re-register handlers after rebuild
            window.selectAnswer = selectAnswer;
            window.nextQuizQuestion = nextQuizQuestion;
        } else {
            // Submit
            submitQuizAnswers(quiz.id, answers);
        }
    };
}

async function submitQuizAnswers(quizId, answers) {
    const timeSec = Math.floor((Date.now() - __quizStartTime) / 1000);
    try {
        const r = await authFetch(`/quizzes/${quizId}/submit`, {
            method: 'POST',
            body: JSON.stringify({ answers, time_sec: timeSec })
        });
        const d = await r.json();
        const modal = document.getElementById('modal-quiz');
        if (modal) modal.remove();

        if (!r.ok) return showToast(d.detail || 'Erro ao enviar respostas.');

        // Show result modal
        document.body.insertAdjacentHTML('beforeend', `
            <div id="modal-quiz-result" style="position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;">
                <div style="background:#111827;border:1px solid rgba(102,252,241,0.2);border-radius:18px;padding:28px;max-width:380px;width:100%;text-align:center;">
                    <div style="font-size:48px;margin-bottom:12px;">${d.correct === d.total ? '🏆' : d.correct >= d.total/2 ? '⭐' : '📚'}</div>
                    <div style="font-family:"Syne";font-weight:800;font-size:20px;color:#f3f4f6;margin-bottom:8px;">
                        ${d.correct}/${d.total} corretas
                    </div>
                    <div style="font-family:"DM Sans";font-size:13px;color:#6b7280;margin-bottom:20px;">${timeSec}s · ${d.multiplier > 1 ? `${d.multiplier}x multiplicador VIP` : 'sem multiplicador'}</div>
                    <div style="background:rgba(102,252,241,0.08);border:1px solid rgba(102,252,241,0.2);border-radius:12px;padding:16px;margin-bottom:20px;">
                        <div style="font-family:"Rajdhani";font-weight:800;font-size:28px;color:#66fcf1;">+${d.glory_earned}</div>
                        <div style="font-size:12px;color:#6b7280;">pontos de glória</div>
                        <div style="font-size:11px;color:#4b5563;margin-top:4px;">Total: ${(d.glory_total||0).toLocaleString('pt-BR')} pts</div>
                    </div>
                    <button onclick="document.getElementById('modal-quiz-result').remove(); loadQuizPanel();" style="background:#66fcf1;color:#0b0c10;border:none;border-radius:8px;padding:12px 24px;font-family:"Rajdhani";font-weight:700;font-size:14px;cursor:pointer;letter-spacing:0.5px;width:100%;">
                        CONTINUAR
                    </button>
                </div>
            </div>
        `);
        // Refresh glory header
        loadGloryHeader();
    } catch(e) { console.error('submitQuizAnswers:', e); showToast('Erro ao enviar respostas.'); }
}

// ═══════════════════════════════════════════════════════════════
//  VIP PANEL
// ═══════════════════════════════════════════════════════════════

async function loadVipPanel() {
    await loadGloryHeader(); // shares glory data
    await loadVipPlans();
}

async function loadVipPlans() {
    const container = document.getElementById('vip-plans');
    const currentPlanEl = document.getElementById('vip-current-plan');
    if (!container) return;

    try {
        const [plansR, myR] = await Promise.all([
            fetch('/plans'),
            authFetch('/my/plan'),
        ]);
        const plans  = plansR.ok ? await plansR.json() : [];
        const myData = myR.ok   ? await myR.json() : {};
        const currentSlug = myData?.plan?.slug || 'free';

        if (currentPlanEl) {
            const cp = myData?.plan || {};
            const sub = myData?.subscription;
            currentPlanEl.innerHTML = `
                <div style="background:rgba(102,252,241,0.06);border:1px solid rgba(102,252,241,0.15);border-radius:12px;padding:16px;display:flex;align-items:center;gap:14px;">
                    <div style="font-size:24px;">${currentSlug==='free'?'👤':currentSlug==='vip1'?'🥈':currentSlug==='vip2'?'🥇':'💎'}</div>
                    <div style="flex:1;">
                        <div style="font-family:"Rajdhani";font-weight:800;font-size:15px;color:#66fcf1;">Plano atual: ${cp.name || 'Gratuito'}</div>
                        <div style="font-size:12px;color:#6b7280;margin-top:3px;">Multiplicador de Glory: ${(cp.glory_multiplier||1)}x
                        ${sub?.expires ? ` · Renova em ${new Date(sub.expires).toLocaleDateString('pt-BR')}` : ''}
                        </div>
                    </div>
                    ${currentSlug !== 'free' ? '<button onclick="cancelSubscription()" style="background:transparent;border:1px solid #ef4444;color:#ef4444;border-radius:8px;padding:6px 12px;font-size:11px;cursor:pointer;">Cancelar</button>' : ''}
                </div>`;
        }

        const planColors  = {free:'#6b7280', vip1:'#9ca3af', vip2:'#f59e0b', vip3:'#66fcf1'};
        const planIcons   = {free:'👤', vip1:'🥈', vip2:'🥇', vip3:'💎'};
        const planFeats   = {
            free:  ['10 quizzes/dia','Rank básico','Acesso completo ao Portal'],
            vip1:  ['30 quizzes/dia','2x Glory points','Badge prata','Borda personalizada'],
            vip2:  ['100 quizzes/dia','5x Glory points','Badge ouro','Temas exclusivos','Quizzes premium'],
            vip3:  ['Quizzes ilimitados','10x Glory points','Badge diamante','Temas exclusivos','Suporte prioritário','Acesso antecipado'],
        };

        container.innerHTML = plans.map(p => {
            const isCurrent = p.slug === currentSlug;
            const color     = planColors[p.slug] || '#6b7280';
            const icon      = planIcons[p.slug]  || '👤';
            const feats     = planFeats[p.slug]  || [];
            return `
            <div style="background:rgba(255,255,255,0.03);border:1px solid ${isCurrent ? color : 'rgba(255,255,255,0.08)'};border-radius:14px;padding:20px;${isCurrent?`box-shadow:0 0 20px ${color}22;`:''}">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
                    <div style="display:flex;align-items:center;gap:10px;">
                        <span style="font-size:22px;">${icon}</span>
                        <div>
                            <div style="font-family:"Rajdhani";font-weight:800;font-size:16px;color:${color};letter-spacing:0.5px;">${p.name}</div>
                            <div style="font-size:12px;color:#6b7280;">${p.glory_multiplier}x Glory</div>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-family:"Syne";font-weight:800;font-size:18px;color:#f3f4f6;">
                            ${p.price_monthly > 0 ? `R$ ${p.price_monthly.toFixed(2).replace('.',',')}` : 'Grátis'}
                        </div>
                        ${p.price_monthly > 0 ? '<div style="font-size:10px;color:#4b5563;">/mês</div>' : ''}
                    </div>
                </div>
                <ul style="list-style:none;padding:0;margin:0 0 16px 0;display:flex;flex-direction:column;gap:7px;">
                    ${feats.map(f => `<li style="font-size:12px;color:#9ca3af;display:flex;align-items:center;gap:8px;"><span style="color:${color};">✓</span>${f}</li>`).join('')}
                </ul>
                ${isCurrent
                    ? `<div style="text-align:center;padding:10px;background:${color}22;border-radius:8px;font-family:"Rajdhani";font-weight:700;font-size:12px;color:${color};letter-spacing:1px;">PLANO ATUAL</div>`
                    : p.slug === 'free' ? '' : `<button onclick="subscribePlan('${p.slug}')" style="width:100%;background:${color};color:#0b0c10;border:none;border-radius:8px;padding:12px;font-family:"Rajdhani";font-weight:700;font-size:13px;cursor:pointer;letter-spacing:0.5px;">
                        ASSINAR${p.price_monthly > 0 ? ` · R$ ${p.price_monthly.toFixed(2).replace('.',',')}` : ''}
                    </button>`
                }
            </div>`;
        }).join('');
    } catch(e) { console.error('loadVipPlans:', e); }
}

async function subscribePlan(slug) {
    if (!confirm(`Assinar plano ${slug}? (Modo demonstração — sem cobrança real)`)) return;
    try {
        const r = await authFetch('/subscription/create', {
            method: 'POST',
            body: JSON.stringify({ plan_slug: slug, provider: 'manual' })
        });
        const d = await r.json();
        if (r.ok) {
            showToast(`✅ Plano ${slug} ativado!`);
            loadVipPanel();
            loadGloryHeader();
        } else {
            showToast(d.detail || 'Erro ao assinar plano');
        }
    } catch(e) { showToast('Erro ao assinar plano.'); }
}

async function cancelSubscription() {
    if (!confirm('Cancelar assinatura? Você voltará ao plano gratuito.')) return;
    try {
        const r = await authFetch('/subscription/cancel', { method: 'POST' });
        if (r.ok) { showToast('Assinatura cancelada.'); loadVipPanel(); }
    } catch(e) { showToast('Erro ao cancelar.'); }
}

// ═══════════════════════════════════════════════════════════════
//  DIAGNOSTICS (Admin)
// ═══════════════════════════════════════════════════════════════

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
                    <div style="font-family:"Rajdhani";font-weight:800;font-size:14px;color:${overallColor};">
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
                            ${c.count > 0 ? `<span style="font-family:"Rajdhani";font-weight:700;font-size:13px;color:${color};">${c.count}</span>` : ''}
                        </div>`;
                    }).join('')}
                </div>
            </div>`;
    } catch(e) {
        console.error('loadDiagnostics:', e);
        panel.innerHTML = '<div style="color:#ef4444;font-size:12px;text-align:center;padding:16px;">Erro ao executar diagnóstico.</div>';
    }
}

// ═══════════════════════════════════════════════════════════════
//  TYPING INDICATORS
// ═══════════════════════════════════════════════════════════════

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
window.onDmInputTyping = onDmInputTyping;

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
window.showTypingIndicator = showTypingIndicator;
// ═══════════════════════════════════════════════════════════════
//  VIP UPGRADE MODAL
// ═══════════════════════════════════════════════════════════════

const VIP_PLANS = [
  { slug:'free',  name:'Gratuito',     icon:'👤', color:'#6b7280', colorRgb:'107,114,128', mult:'1x', monthly:0,    yearly:0,
    bubble:{bg:'rgba(255,255,255,0.06)',border:'rgba(255,255,255,0.1)',radius:'12px'},
    font:'Rajdhani', nameColor:'#e5e7eb', borderGlow:'transparent' },
  { slug:'vip1',  name:'Cidadão VIP',  icon:'🥈', color:'#9ca3af', colorRgb:'156,163,175', mult:'2x', monthly:9.90, yearly:99,
    bubble:{bg:'rgba(156,163,175,0.12)',border:'rgba(156,163,175,0.25)',radius:'14px'},
    font:'DM Sans', nameColor:'#d1d5db', borderGlow:'#9ca3af' },
  { slug:'vip2',  name:'Guardião',     icon:'🥇', color:'#f59e0b', colorRgb:'245,158,11',  mult:'5x', monthly:24.90,yearly:249,
    bubble:{bg:'rgba(245,158,11,0.1)',border:'rgba(245,158,11,0.3)',radius:'16px'},
    font:'Syne', nameColor:'#fbbf24', borderGlow:'#f59e0b' },
  { slug:'vip3',  name:'Sentinela',    icon:'💎', color:'#66fcf1', colorRgb:'102,252,241', mult:'10x',monthly:49.90,yearly:499,
    bubble:{bg:'rgba(102,252,241,0.1)',border:'rgba(102,252,241,0.35)',radius:'18px 18px 4px 18px'},
    font:'Rajdhani', nameColor:'#66fcf1', borderGlow:'#66fcf1' },
];

let __vipBilling  = 'monthly';
let __vipSelected = 'vip1';
let __vipCurrent  = 'free';

async function openVipModal() {
  // Load current plan
  try {
    const r = await authFetch('/my/plan');
    if (r.ok) { const d = await r.json(); __vipCurrent = d?.plan?.slug || 'free'; }
  } catch(e) {}

  // If user is on free plan default selection to vip1, else pick next tier
  const idx = VIP_PLANS.findIndex(p => p.slug === __vipCurrent);
  __vipSelected = VIP_PLANS[Math.min(idx + 1, VIP_PLANS.length - 1)].slug;

  renderVipCards();
  updateVipPreview();
  document.getElementById('modal-vip').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeVipModal() {
  document.getElementById('modal-vip').classList.remove('open');
  document.body.style.overflow = '';
}

function setVipBilling(mode) {
  __vipBilling = mode;
  document.getElementById('vip-btn-monthly').classList.toggle('on', mode === 'monthly');
  document.getElementById('vip-btn-yearly').classList.toggle('on',  mode === 'yearly');
  renderVipCards();
  updateVipCta();
}

function renderVipCards() {
  const container = document.getElementById('vip-modal-cards');
  if (!container) return;
  container.innerHTML = VIP_PLANS.map(p => {
    const price = __vipBilling === 'yearly' ? (p.yearly / 12) : p.monthly;
    const priceStr = price === 0 ? 'Grátis' : `R$ ${price.toFixed(2).replace('.',',')}`;
    const periodStr = price === 0 ? '' : `<small>/${__vipBilling === 'yearly' ? 'mês*' : 'mês'}</small>`;
    const isSel = __vipSelected === p.slug;
    const isCurr = __vipCurrent === p.slug;
    return `<div class="vip-pcard ${isSel ? 'sel' : ''} ${isCurr ? 'vip-pcard-curr' : ''}"
        style="--vc:${p.color}; --vcr:${p.colorRgb};"
        onclick="selectVipPlan('${p.slug}')">
        <div class="vip-pcard-icon">${p.icon}</div>
        <div class="vip-pcard-name">${p.name}</div>
        <div class="vip-pcard-price">${priceStr}${periodStr}</div>
        <div class="vip-pcard-mult">${p.mult} Glory</div>
    </div>`;
  }).join('');
}

function selectVipPlan(slug) {
  __vipSelected = slug;
  renderVipCards();
  updateVipPreview();
  updateVipCta();
}

function updateVipPreview() {
  const plan = VIP_PLANS.find(p => p.slug === __vipSelected) || VIP_PLANS[0];
  const nameEl   = document.getElementById('vmp-name');
  const avEl     = document.getElementById('vmp-av');
  const bubbleEl = document.getElementById('vmp-bubble');

  if (nameEl) {
    nameEl.style.fontFamily  = `'${plan.font}', sans-serif`;
    nameEl.style.color       = plan.nameColor;
  }
  if (avEl) {
    avEl.style.boxShadow = plan.borderGlow !== 'transparent'
      ? `0 0 0 3px ${plan.borderGlow}, 0 0 12px ${plan.borderGlow}55`
      : 'none';
  }
  if (bubbleEl) {
    bubbleEl.style.background   = plan.bubble.bg;
    bubbleEl.style.borderColor  = plan.bubble.border;
    bubbleEl.style.borderRadius = plan.bubble.radius;
  }
  updateVipCta();
}

function updateVipCta() {
  const plan   = VIP_PLANS.find(p => p.slug === __vipSelected) || VIP_PLANS[0];
  const ctaBtn = document.getElementById('vip-modal-cta');
  const ctaNote = document.getElementById('vip-modal-note');
  if (!ctaBtn) return;

  const isCurrent = __vipSelected === __vipCurrent;
  const isFree    = plan.slug === 'free';

  if (isCurrent) {
    ctaBtn.disabled = true;
    ctaBtn.textContent = 'PLANO ATUAL';
    if (ctaNote) ctaNote.textContent = 'Você já está neste plano';
  } else if (isFree) {
    ctaBtn.disabled = false;
    ctaBtn.textContent = 'FAZER DOWNGRADE (GRÁTIS)';
    if (ctaNote) ctaNote.textContent = 'Você perderá os benefícios VIP';
  } else {
    const price = __vipBilling === 'yearly' ? plan.yearly : plan.monthly;
    const label = __vipBilling === 'yearly'
      ? `ASSINAR ANUAL — R$ ${price.toFixed(2).replace('.',',')}` 
      : `ASSINAR MENSAL — R$ ${price.toFixed(2).replace('.',',')}`;
    ctaBtn.disabled = false;
    ctaBtn.textContent = label;
    ctaBtn.style.setProperty('--vc',  plan.color);
    ctaBtn.style.setProperty('--vc2', '#8b5cf6');
    if (ctaNote) ctaNote.textContent = 'Pagamento seguro · Cancele quando quiser';
  }
}

async function vipModalSubscribe() {
  const plan = VIP_PLANS.find(p => p.slug === __vipSelected);
  if (!plan || plan.slug === __vipCurrent) return;
  if (plan.slug === 'free') {
    if (!confirm('Cancelar assinatura e voltar para o plano Gratuito?')) return;
    const r = await authFetch('/subscription/cancel', { method:'POST' });
    if (r.ok) { showToast('Assinatura cancelada.'); closeVipModal(); __vipCurrent = 'free'; }
    return;
  }
  // Demo mode — no real payment yet
  const price  = __vipBilling === 'yearly' ? plan.yearly : plan.monthly;
  const period = __vipBilling === 'yearly' ? 'anual' : 'mensal';
  if (!confirm(`Assinar ${plan.name} (${period}) por R$ ${price.toFixed(2).replace('.',',')}?\n\n⚠️ Modo demonstração — sem cobrança real.`)) return;
  try {
    const r = await authFetch('/subscription/create', {
      method:'POST',
      body: JSON.stringify({ plan_slug: plan.slug, provider:'manual', billing: __vipBilling })
    });
    const d = await r.json();
    if (r.ok) {
      showToast(`✅ ${plan.icon} Plano ${plan.name} ativado!`);
      __vipCurrent = plan.slug;
      renderVipCards();
      updateVipCta();
      // Hide the upgrade banner if user is now VIP
      if (plan.slug !== 'free') {
        const banner = document.getElementById('vip-profile-banner');
        if (banner) banner.style.display = 'none';
      }
    } else {
      showToast(d.detail || 'Erro ao assinar plano.');
    }
  } catch(e) { showToast('Erro ao processar assinatura.'); }
}

// Auto-hide banner if already VIP on load
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(async () => {
    try {
      const r = await authFetch('/my/plan');
      if (!r.ok) return;
      const d = await r.json();
      if (d?.plan?.slug && d.plan.slug !== 'free') {
        const banner = document.getElementById('vip-profile-banner');
        if (banner) banner.style.display = 'none';
      }
    } catch(e) {}
  }, 2000);
});
