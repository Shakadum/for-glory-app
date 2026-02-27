// ===== Emoji data (fallback) =====
const EMOJIS = window.EMOJIS || [
  "😀","😁","😂","🤣","😊","😍","😘","😎","🤔","😅","😭","😡",
  "👍","👎","🙏","💪","🔥","⭐","🎉","❤️","💔","😴","🤯","🥶",
  "😈","🤝","🎮","🏆","⚔️","🛡️","📌","📎","✅","❌","⚠️","💬"
];
window.EMOJIS = EMOJIS;

window.deleteTarget = {type: null, id: null};

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
    const dd = document.querySelector('.lang-dropdown');
    const btn = document.getElementById('lang-btn-current');
    if(!dd || !btn) return;

    btn.addEventListener('click', (e)=>{
        e.preventDefault();
        e.stopPropagation();
        dd.classList.toggle('open');
    });

    // Fecha ao clicar fora
    document.addEventListener('click', (e)=>{
        if(!dd.contains(e.target) && e.target !== btn) dd.classList.remove('open');
    });

    // Fecha com ESC
    document.addEventListener('keydown', (e)=>{
        if(e.key === 'Escape') dd.classList.remove('open');
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    // Tradução da interface
    let flag = window.currentLang === 'pt' ? '🇧🇷 PT' : (window.currentLang === 'es' ? '🇪🇸 ES' : '🇺🇸 EN');
    document.getElementById('lang-btn-current').innerHTML = `🌍 ${flag}`;
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

window.ringtone = new Audio('https://actions.google.com/sounds/v1/alarms/phone_ringing.ogg'); window.ringtone.loop = true;
window.callingSound = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg'); window.callingSound.loop = true;
window.msgSound = new Audio('https://actions.google.com/sounds/v1/water/pop.ogg');

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

function safeAvatarUrl(u) {
    if (!u || typeof u !== 'string') return '/static/default-avatar.svg';
    if (u.startsWith('http://') || u.startsWith('https://')) return u;
    if (u.startsWith('/')) return u;
    return `/${u}`;
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

        rtc.client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" }); rtc.remoteUsers = {};
        
        rtc.client.on("user-published", async (remoteUser, mediaType) => {
            window.callHasConnected = true; 
            stopSounds();
            await rtc.client.subscribe(remoteUser, mediaType);
            if (mediaType === "audio") { rtc.remoteUsers[remoteUser.uid] = remoteUser; remoteUser.audioTrack.play(); renderCallPanel(); }
        });
        
        rtc.client.on("user-unpublished", (remoteUser) => { 
            delete rtc.remoteUsers[remoteUser.uid]; renderCallPanel(); 
            if(Object.keys(rtc.remoteUsers).length === 0 && window.callHasConnected) { showToast("O aliado desligou."); leaveCall(); }
        });
        
        await rtc.client.join(conf.app_id, window.currentAgoraChannel, conf.token, user.id);
        
        try { rtc.localAudioTrack = await AgoraRTC.createMicrophoneAudioTrack(); } 
        catch(micErr) { alert("⚠️ Sem Microfone! Autorize no navegador para usar o rádio."); leaveCall(); return; }
        
        await rtc.client.publish([rtc.localAudioTrack]);
        try {
            window.callStartedAt = Date.now();
            if (window.currentCallType === 'dm' && dmWS && dmWS.readyState === 1) {
                dmWS.send(`📞 Call iniciada • ${new Date(window.callStartedAt).toLocaleString()}`);
            }
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
            body:JSON.stringify({ target_type: 'call', target_id: window.currentAgoraChannel, bg_url: data.secure_url })
        });
        document.getElementById('expanded-call-panel').style.backgroundImage=`url('${data.secure_url}')`;
        showToast("Fundo alterado!");
        if(globalWS && globalWS.readyState === WebSocket.OPEN) {
            globalWS.send("SYNC_BG:" + window.currentAgoraChannel + ":" + data.secure_url);
        }
    } catch(e) { console.error("Upload BG erro:", e); showToast("Erro na imagem."); }
}

async function leaveCall() { 
    stopSounds();
    if (rtc.localAudioTrack) { rtc.localAudioTrack.close(); } 
    if (rtc.client) { await rtc.client.leave(); } 
    
    if (window.isCaller && window.callTargetId && !window.callHasConnected && globalWS) {
        globalWS.send(`CALL_SIGNAL:${window.callTargetId}:cancelled:${window.currentAgoraChannel}`);
    }
    
    rtc.localAudioTrack = null; rtc.client = null; window.callHasConnected = false; window.currentAgoraChannel = null;
    window.isCaller = false; window.callTargetId = null;
    
    clearInterval(callInterval); 
    document.getElementById('expanded-call-panel').style.display = 'none'; 
    document.getElementById('floating-call-btn').style.display = 'none'; 
    let btn = document.getElementById('btn-mute-call'); btn.classList.remove('muted'); btn.innerHTML = '🎤'; isMicMuted = false;
}

window.callUsersCache = {};
async function renderCallPanel() {
    let list = document.getElementById('call-users-list'); list.innerHTML = ''; let count = 0;
    let isAdmin = window.currentCommIsAdmin || false;
    let lastUser = null;
    
    for(let uid in rtc.remoteUsers) {
        if (String(uid) === String(user.id)) continue;
        count++; 
        if(!window.callUsersCache[uid]) {
            try {
                let req = await fetch(`/users/basic/${uid}`);
                window.callUsersCache[uid] = await req.json();
            } catch(e) { console.error("Erro fetch user call:", e); window.callUsersCache[uid] = {name: "Aliado", avatar: "https://ui-avatars.com/api/?name=A"}; }
        }
        
        let uData = window.callUsersCache[uid];
        lastUser = uData;
        let kickBtn = isAdmin ? `<button class="call-kick-btn" onclick="kickFromCall(${uid})" title="Expulsar">❌</button>` : '';
        list.innerHTML += `<div class="call-participant-card"><img src="${safeAvatarUrl(uData.avatar, safeDisplayName(uData))}" class="call-avatar"><span class="call-name">${uData.name}</span>${kickBtn}<input type="range" min="0" max="100" value="100" class="vol-slider" oninput="changeRemoteVol(${uid}, this.value)"></div>`;
    }
    
    let profDiv = document.getElementById('call-active-profile');
    let st = document.getElementById('call-hud-status');
    
    if(count > 0 && lastUser) {
        profDiv.style.display = 'block';
        document.getElementById('call-active-avatar').src = lastUser.avatar;
        document.getElementById('call-active-name').innerText = lastUser.name;
        st.innerText = "EM CHAMADA";
        stopSounds();
    } else {
        profDiv.style.display = 'none';
        list.innerHTML = `<p style="color:#888; font-size:12px; text-align:center; margin:0;">Aguardando na escuta...</p>`;
        st.innerText = window.isCaller ? "CHAMANDO..." : "AGUARDANDO...";
    }
}

function changeRemoteVol(uid, val) { if(rtc.remoteUsers[uid] && rtc.remoteUsers[uid].audioTrack) { rtc.remoteUsers[uid].audioTrack.setVolume(parseInt(val)); } }

let isMicMuted = false;
async function toggleMuteCall() { 
    if(rtc.localAudioTrack) { 
        isMicMuted = !isMicMuted;
        await rtc.localAudioTrack.setMuted(isMicMuted); 
        let btn = document.getElementById('btn-mute-call'); 
        if(isMicMuted) { btn.classList.add('muted'); btn.innerHTML = '🔇'; } 
        else { btn.classList.remove('muted'); btn.innerHTML = '🎤'; } 
    } 
}

function toggleCallPanel() { let p = document.getElementById('expanded-call-panel'); p.style.display = (p.style.display === 'flex') ? 'none' : 'flex'; }
function showCallPanel() { document.getElementById('expanded-call-panel').style.display = 'flex'; callDuration = 0; document.getElementById('call-hud-time').innerText = "00:00"; clearInterval(callInterval); callInterval = setInterval(() => { callDuration++; let m = String(Math.floor(callDuration / 60)).padStart(2, '0'); let s = String(callDuration % 60).padStart(2, '0'); document.getElementById('call-hud-time').innerText = `${m}:${s}`; }, 1000); renderCallPanel(); }
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

document.addEventListener("visibilitychange", ()=>{ if(document.visibilityState==="visible" && user){ fetchUnread(); fetchOnlineUsers(); if(document.getElementById('view-feed').classList.contains('active')) loadFeed(); if(activeChannelId && commWS && commWS.readyState!==WebSocket.OPEN) connectCommWS(activeChannelId); } });
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
    } catch(e) { console.error(e); }
}

async function loadInbox(){
    try {
        await fetchUnread();
        let r = await fetch('/inbox?nocache=' + new Date().getTime(), { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        let d = await r.json();
        let b = document.getElementById('inbox-list'); b.innerHTML = '';
        if((d.groups || []).length === 0 && (d.friends || []).length === 0) { b.innerHTML = `<p style='text-align:center;color:#888;margin-top:20px;'>${t('empty_box')}</p>`; return; }
        (d.groups || []).forEach(g => { b.innerHTML += `<div class="inbox-item" data-id="${g.id}" data-type="group" style="display:flex;align-items:center;gap:15px;padding:12px;background:var(--card-bg);border-radius:12px;cursor:pointer;border:1px solid rgba(102,252,241,0.2);" onclick="openChat(${g.id}, '${g.name}', 'group')"><img src="${g.avatar}" style="width:45px;height:45px;border-radius:50%;"><div style="flex:1;"><b style="color:white;font-size:16px;">${g.name}</b><br><span style="font-size:12px;color:var(--primary);">${t('squad')}</span></div></div>`; });
        (d.friends || []).forEach(f => {
            let unreadCount = (window.unreadData && window.unreadData[String(f.id)]) ? window.unreadData[String(f.id)] : 0; let badgeDisplay = unreadCount > 0 ? 'block' : 'none';
            b.innerHTML += `<div class="inbox-item" data-id="${f.id}" data-type="1v1" style="display:flex;align-items:center;gap:15px;padding:12px;background:rgba(255,255,255,0.05);border-radius:12px;cursor:pointer;" onclick="openChat(${f.id}, '${f.name}', '1v1')"><div class="av-wrap"><img src="${f.avatar}" style="width:45px;height:45px;border-radius:50%;object-fit:cover;"><div class="status-dot" data-uid="${f.id}"></div></div><div style="flex:1;"><b style="color:white;font-size:16px;">${f.name}</b><br><span style="font-size:12px;color:#888;">${t('direct_msg')}</span></div><div class="list-badge" style="display:${badgeDisplay}; background:#ff5555; color:white; font-size:12px; font-weight:bold; padding:4px 10px; border-radius:12px; box-shadow:0 0 8px rgba(255,85,85,0.6);">${unreadCount}</div></div>`;
        });
        updateStatusDots();
    } catch(e) { console.error(e); }
}

async function openCreateGroupModal(){ try{ let r=await authFetch(`/inbox?nocache=${new Date().getTime()}`); let d=await r.json(); let list=document.getElementById('group-friends-list'); if((d.friends||[]).length===0){list.innerHTML=`<p style='color:#ff5555;font-size:13px;'>Adicione amigos primeiro.</p>`;}else{list.innerHTML=d.friends.map(f=>`<label style="display:flex;align-items:center;gap:10px;color:white;margin-bottom:10px;cursor:pointer;"><input type="checkbox" class="grp-friend-cb" value="${f.id}" style="width:18px;height:18px;"><img src="${f.avatar}" style="width:30px;height:30px;border-radius:50%;object-fit:cover;"> ${f.name}</label>`).join('');} document.getElementById('new-group-name').value=''; document.getElementById('modal-create-group').classList.remove('hidden'); }catch(e){ console.error(e); } }
async function submitCreateGroup(){ let name=document.getElementById('new-group-name').value.trim(); if(!name)return; let cbs=document.querySelectorAll('.grp-friend-cb:checked'); let member_ids=Array.from(cbs).map(cb=>parseInt(cb.value)); if(member_ids.length===0)return; try{ let r=await fetch('/group/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,creator_id:user.id,member_ids:member_ids})}); if(r.ok){document.getElementById('modal-create-group').classList.add('hidden');loadInbox();} }catch(e){ console.error(e); } }
async function toggleRequests(type){ let b=document.getElementById('requests-list'); if(b.style.display==='block'){b.style.display='none';return;} b.style.display='block'; try{ let r=await authFetch(`/friend/requests?nocache=${new Date().getTime()}`); let d=await r.json(); if(type==='requests'){b.innerHTML=(d.requests||[]).length?d.requests.map(r=>`<div style="padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;">${r.username} <button class="glass-btn" style="padding:5px 10px;flex:none;" onclick="handleReq(${r.id},'accept')">${t('accept_ally')}</button></div>`).join(''):`<p style="padding:10px;color:#888;">Vazio.</p>`;}else{b.innerHTML=(d.friends||[]).length?d.friends.map(f=>`<div style="padding:10px;border-bottom:1px solid #333;cursor:pointer;display:flex;align-items:center;gap:10px;" onclick="openPublicProfile(${f.id})"><div class="av-wrap"><img src="${f.avatar}" style="width:30px;height:30px;border-radius:50%;"><div class="status-dot" data-uid="${f.id}" style="width:10px;height:10px;"></div></div>${f.username}</div>`).join(''):`<p style="padding:10px;color:#888;">Vazio.</p>`;} updateStatusDots(); }catch(e){ console.error(e); } }
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

async function submitCreateComm(e){e.preventDefault();let n=document.getElementById('new-comm-name').value.trim();let d=document.getElementById('new-comm-desc').value.trim();let p=document.getElementById('new-comm-priv').value;let avFile=document.getElementById('comm-avatar-upload').files[0];let banFile=document.getElementById('comm-banner-upload').files[0];if(!n)return showToast("Digite um nome!");let btn=e.target;btn.disabled=true;btn.innerText="CRIANDO...";try{let safeName=encodeURIComponent(n);let av="https://ui-avatars.com/api/?name="+safeName+"&background=111&color=66fcf1";let ban="https://placehold.co/600x200/0b0c10/1f2833?text="+safeName;if(avFile){let formData = new FormData(); formData.append('file', avFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); av = data.secure_url; } if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); ban = data.secure_url; } let payload = { name:n, desc:d, is_priv:parseInt(p), avatar_url:av, banner_url:ban }; let r=await authFetch('/community/create', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-create-comm').classList.add('hidden');showToast("Base Criada!");loadMyComms();goView('mycomms');}}catch(err){console.error(err);showToast("Erro.");}finally{btn.disabled=false;btn.innerText=t('establish');}}
async function submitEditComm(){let avFile=document.getElementById('edit-comm-avatar').files[0];let banFile=document.getElementById('edit-comm-banner').files[0];if(!avFile&&!banFile)return showToast("Selecione algo.");let btn=document.getElementById('btn-save-comm');btn.disabled=true;btn.innerText="ENVIANDO...";try{let au=null; let bu=null; if(avFile){let formData = new FormData(); formData.append('file', avFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); au = data.secure_url; } if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); bu = data.secure_url; } let payload = { comm_id: activeCommId, avatar_url: au, banner_url: bu }; let r=await authFetch('/community/edit', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-edit-comm').classList.add('hidden');showToast("Base Atualizada!");openCommunity(activeCommId, true);loadMyComms();}}catch(e){console.error(e);showToast("Erro.");}finally{btn.disabled=false;btn.innerText=t('save');}}
async function submitCreateChannel(){let n=document.getElementById('new-ch-name').value.trim();let tType=document.getElementById('new-ch-type').value;let p=document.getElementById('new-ch-priv').value;let banFile=document.getElementById('new-ch-banner').files[0];if(!n)return showToast("Digite o nome.");let btn=document.getElementById('btn-create-ch');btn.disabled=true;btn.innerText="CRIANDO...";try{let safeName=encodeURIComponent(n);let ban="https://placehold.co/600x200/0b0c10/1f2833?text="+safeName;if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); ban = data.secure_url; } let payload = { comm_id: activeCommId, name:n, type:tType, is_private:parseInt(p), banner_url:ban }; let r=await authFetch('/community/channel/create', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-create-channel').classList.add('hidden');showToast("Canal Criado!");openCommunity(activeCommId, true);}}catch(err){console.error(err);}finally{btn.disabled=false;btn.innerText=t('create_channel');}}
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
    document.getElementById('p-progression-box').innerHTML = `<div style="margin: 20px auto; width: 90%; max-width: 400px; text-align: left; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 12px; border: 1px solid #333;"><div style="display: flex; justify-content: space-between; margin-bottom: 5px;"><span style="color: var(--primary); font-weight: bold; font-size: 14px;">${t('progression')}</span><span style="color: white; font-size: 14px; font-family:'Rajdhani'; font-weight:bold;">${user.xp} / ${user.next_xp} XP</span></div><div style="width: 100%; background: #222; height: 10px; border-radius: 5px; overflow: hidden; box-shadow:inset 0 2px 5px rgba(0,0,0,0.5);"><div style="width: ${user.percent}%; height: 100%; background: linear-gradient(90deg, #1d4e4f, var(--primary)); transition: width 0.5s;"></div></div><div style="display:flex; justify-content:space-between; margin-top:8px; align-items:center;"><span style="color: #888; font-size: 11px;">Falta ${missingXP} XP para ${user.next_rank}</span><button class="btn-link" style="margin:0; font-size:11px;" onclick="showRanksModal()">Ver Patentes</button></div></div>`;
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
        setTimeout(() => { if(user) connectGlobalWS(); }, 4000); 
    };
}
connectGlobalWS();

if(!window._globalPingInterval){
    window._globalPingInterval = setInterval(()=>{ 
        if(globalWS && globalWS.readyState === WebSocket.OPEN) { globalWS.send("ping"); } 
    }, 20000);
}
    syncInterval=setInterval(()=>{ if(document.getElementById('view-feed').classList.contains('active')) loadFeed(); fetchOnlineUsers(); },4000);
}

function logout(){ localStorage.removeItem('token'); user = null; if(syncInterval) clearInterval(syncInterval); if(globalWS) globalWS.close(); showLoginScreen(); }
function goView(v, btnElem){
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
                let audioMsg="[AUDIO]"+data.secure_url; 
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
async function loadFeed(){try{let r=await fetch(`/posts?uid=${user.id}&limit=50&nocache=${new Date().getTime()}`);if(!r.ok)return;let p=await r.json();let h=JSON.stringify(p.map(x=>x.id+x.likes+x.comments+(x.user_liked?"1":"0")));if(h===lastFeedHash)return;lastFeedHash=h;let openComments=[];let activeInputs={};let focusedInputId=null;if(document.activeElement&&document.activeElement.classList.contains('comment-inp')){focusedInputId=document.activeElement.id;}document.querySelectorAll('.comments-section').forEach(sec=>{if(sec.style.display==='block')openComments.push(sec.id.split('-')[1]);});document.querySelectorAll('.comment-inp').forEach(inp=>{if(inp.value)activeInputs[inp.id]=inp.value;});let ht='';p.forEach(x=>{let m=x.media_type==='video'?`<video src="${x.content_url}" class="post-media" controls playsinline preload="metadata"></video>`:`<img src="${x.content_url}" class="post-media" loading="lazy">`;m=`<div class="post-media-wrapper">${m}</div>`;let delBtn=x.author_id===user.id?`<span onclick="window.deleteTarget={type:'post', id:${x.id}}; document.getElementById('modal-delete').classList.remove('hidden');" style="cursor:pointer;opacity:0.5;font-size:20px;transition:0.2s;" onmouseover="this.style.opacity='1';this.style.color='#ff5555'" onmouseout="this.style.opacity='0.5';this.style.color=''">🗑️</span>`:'';let heartIcon=x.user_liked?"❤️":"🤍";let heartClass=x.user_liked?"liked":"";let rankHtml=formatRankInfo(x.author_rank,x.special_emblem,x.rank_color);ht+=`<div class="post-card"><div class="post-header"><div style="display:flex;align-items:center;cursor:pointer" onclick="openPublicProfile(${x.author_id})"><div class="av-wrap" style="margin-right:12px;"><img src="${x.author_avatar}" class="post-av" style="margin:0;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${x.author_id}"></div></div><div class="user-info-box"><b style="color:white;font-size:14px">${x.author_name}</b><div style="margin-top:2px;">${rankHtml}</div></div></div>${delBtn}</div>${m}<div class="post-actions"><button class="action-btn ${heartClass}" onclick="toggleLike(${x.id}, this)"><span class="icon">${heartIcon}</span> <span class="count" style="color:white;font-weight:bold;">${x.likes}</span></button><button class="action-btn" onclick="toggleComments(${x.id})">💬 <span class="count" style="color:white;font-weight:bold;">${x.comments}</span></button></div><div class="post-caption"><b style="color:white;cursor:pointer;" onclick="openPublicProfile(${x.author_id})">${x.author_name}</b> ${(x.caption||"")}</div><div id="comments-${x.id}" class="comments-section"><div id="comment-list-${x.id}"></div><form class="comment-input-area" onsubmit="sendComment(${x.id}); return false;"><button type="button" class="icon-btn" id="btn-mic-comment-${x.id}" onclick="toggleRecord('comment-${x.id}')">🎤</button><input id="comment-inp-${x.id}" class="comment-inp" placeholder="${t('caption_placeholder')}" autocomplete="off"><button type="button" class="icon-btn" onclick="openEmoji('comment-inp-${x.id}')">😀</button><button type="submit" class="btn-send-msg">➤</button></form></div></div>`});document.getElementById('feed-container').innerHTML=ht;openComments.forEach(pid=>{let sec=document.getElementById(`comments-${pid}`);if(sec){sec.style.display='block';loadComments(pid);}});for(let id in activeInputs){let inp=document.getElementById(id);if(inp)inp.value=activeInputs[id];}if(focusedInputId){let inp=document.getElementById(focusedInputId);if(inp){inp.focus({preventScroll:true});let val=inp.value;inp.value='';inp.value=val;}}updateStatusDots();}catch(e){ console.error(e); }}

document.getElementById('btn-confirm-delete').onclick=async()=>{if(!window.deleteTarget || !window.deleteTarget.id)return;let tp=window.deleteTarget.type;let id=window.deleteTarget.id;document.getElementById('modal-delete').classList.add('hidden');try{if(tp==='post'){let r=await authFetch('/post/delete', {method:'POST', body:JSON.stringify({post_id:id})}); if(r.ok){try{ bumpCommentCount(pid, 1); }catch(e){};
                    await loadComments(pid);loadMyHistory();updateProfileState();}}else if(tp==='comment'){let r=await authFetch('/comment/delete', {method:'POST', body:JSON.stringify({comment_id:id})}); if(r.ok){try{ bumpCommentCount(pid, 1); }catch(e){};
                    await loadComments(pid);}}else if(tp==='base'){let r=await authFetch(`/community/${id}/delete`, {method:'POST'}); if(r.ok){closeComm();loadMyComms();}}else if(tp==='channel'){let r=await authFetch(`/community/channel/${id}/delete`, {method:'POST'}); if(r.ok){document.getElementById('modal-edit-channel').classList.add('hidden');openCommunity(activeCommId, true);}}else if(tp==='dm_msg'||tp==='comm_msg'||tp==='group_msg'){let mainType=tp==='dm_msg'?'dm':(tp==='comm_msg'?'comm':'group');let r=await authFetch('/message/delete', {method:'POST', body:JSON.stringify({msg_id:id,type:mainType})}); let res=await r.json(); if(res.status==='ok'){try{ if(mainType==='dm' && typeof dmWS!=='undefined' && dmWS && dmWS.readyState===1){ dmWS.send(JSON.stringify({type:'message_deleted', msg_id:id})); } }catch(e){} let msgBubble=document.getElementById(`${tp}-${id}`).querySelector('.msg-bubble');let timeSpan=msgBubble.querySelector('.msg-time');let timeStr=timeSpan?timeSpan.outerHTML:'';msgBubble.innerHTML=`<span class="msg-deleted">${t('deleted_msg')}</span>${timeStr}`;let btn=document.getElementById(`${tp}-${id}`).querySelector('.del-msg-btn');if(btn)btn.remove();}}}catch(e){ console.error(e); }};

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

async function loadComments(pid){try{let r=await fetch(`/post/${pid}/comments?nocache=${new Date().getTime()}`);let list=document.getElementById(`comment-list-${pid}`);if(r.ok){let comments=await r.json();if((comments||[]).length===0){list.innerHTML=`<p style='color:#888;font-size:12px;text-align:center;'>Vazio</p>`;return;}list.innerHTML=comments.map(c=>{let delBtn=(c.author_id===user.id)?`<span onclick="window.deleteTarget={type:'comment', id:${c.id}}; document.getElementById('modal-delete').classList.remove('hidden');" style="color:#ff5555;cursor:pointer;margin-left:auto;font-size:14px;padding:0 5px;">🗑️</span>`:'';let txt=c.text;if(txt.startsWith('[AUDIO]')){txt=`<audio controls src="${txt.replace('[AUDIO]','')}" style="max-width:200px;height:35px;outline:none;margin-top:5px;"></audio>`;}return `<div class="comment-row" style="align-items:center;"><div class="av-wrap" onclick="openPublicProfile(${c.author_id})"><img src="${c.author_avatar}" class="comment-av" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${c.author_id}" style="width:8px;height:8px;border-width:1px;"></div></div><div style="flex:1;"><b style="color:var(--primary);cursor:pointer;" onclick="openPublicProfile(${c.author_id})">${c.author_name}</b> <span style="display:inline-block;margin-left:5px;">${formatRankInfo(c.author_rank,c.special_emblem,c.color)}</span> <span style="color:#e0e0e0;display:block;margin-top:3px;">${txt}</span></div>${delBtn}</div>`}).join('');updateStatusDots();}}catch(e){ console.error(e); }}
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
async function fetchChatMessages(id, type) {
    let list = document.getElementById('dm-list');
    let url = type === 'group' ? `/group/${id}/messages?nocache=${new Date().getTime()}` : `/dms/${id}?uid=${user.id}&nocache=${new Date().getTime()}`;
    try {
        let r = await authFetch(url);
        if (r.ok) {
            let msgs = await r.json();
            let isAtBottom = (list.scrollHeight - list.scrollTop <= list.clientHeight + 50);
            (msgs || []).forEach(d => {
                let prefix = type === 'group' ? 'group_msg' : 'dm_msg';
                let msgId = `${prefix}-${d.id}`;
                if (!document.getElementById(msgId)) {
                    let m = (d.user_id === user.id);
                    let c = (d && d.content !== undefined && d.content !== null) ? String(d.content) : '';
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
                    let h = `<div id="${msgId}" class="msg-row ${m ? 'mine' : ''}">
                        <img src="${safeAvatarUrl(d.avatar, safeDisplayName(d))}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'">
                        <div>
                            <div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${escapeHtml(safeDisplayName(d))} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div>
                            <div class="msg-bubble">${c}${timeHtml}${delBtn}</div>
                        </div>
                    </div>`;
                    list.insertAdjacentHTML('beforeend', h);
                }
            });
            if (isAtBottom) list.scrollTop = list.scrollHeight;
        }
    } catch (e) { console.error(e); }
}

async function openChat(id, name, type) {
    let changingChat = (currentChatId !== id || currentChatType !== type);
    currentChatId = id;
    currentChatType = type;
    document.getElementById('dm-header-name').innerText = name;
    goView('dm');
    if (type === '1v1') {
        await fetch(`/inbox/read/${id}`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` }, body: JSON.stringify({ uid: user.id }) });
        fetchUnread();
    }
    if (changingChat) {
        document.getElementById('dm-list').innerHTML = '';
    }
    await fetchChatMessages(id, type);
    if (changingChat || !dmWS || dmWS.readyState !== WebSocket.OPEN) {
        connectDmWS(id, name, type);
    }
}

function connectDmWS(id, name, type) {
    if (dmWS) dmWS.close();
    let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let token = localStorage.getItem('token');
    let ch = type === 'group' ? `group_${id}` : `dm_${Math.min(user.id, id)}_${Math.max(user.id, id)}`;
    dmWS = new WebSocket(`${protocol}//${location.host}/ws/${ch}/${user.id}?token=${token}`);
    dmWS.onclose = () => {
        setTimeout(() => {
            if (currentChatId === id && document.getElementById('view-dm').classList.contains('active')) {
                fetchChatMessages(id, type);
                connectDmWS(id, name, type);
            }
        }, 2000);
    };
    dmWS.onmessage = (e) => {
        let d = JSON.parse(e.data);
        let b = document.getElementById('dm-list');
        let m = parseInt(d.user_id) === parseInt(user.id);
        let c = (d && d.content !== undefined && d.content !== null) ? String(d.content) : '';
        if (d.type === 'ping' || d.type === 'pong') return;
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
            let h = `<div id="${msgId}" class="msg-row ${m ? 'mine' : ''}">
                <img src="${safeAvatarUrl(d.avatar, safeDisplayName(d))}" class="msg-av" onclick="openPublicProfile(${d.user_id})" style="cursor:pointer;" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'">
                <div>
                    <div style="font-size:11px;color:#888;margin-bottom:2px;cursor:pointer;" onclick="openPublicProfile(${d.user_id})">${escapeHtml(safeDisplayName(d))} ${formatRankInfo(d.rank, d.special_emblem, d.color)}</div>
                    <div class="msg-bubble">${c}${timeHtml}${delBtn}</div>
                </div>
            </div>`;
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

function sendDM(){let i=document.getElementById('dm-msg');let msg=i.value.trim();if(msg&&dmWS&&dmWS.readyState===WebSocket.OPEN){dmWS.send(msg);i.value='';toggleEmoji(true);}}
async function uploadDMImage(){let f=document.getElementById('dm-file').files[0];if(!f)return;try{let formData = new FormData(); formData.append('file', f); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); if(dmWS) dmWS.send(data.secure_url); }catch(e){ console.error(e); }}
async function loadMyComms(){try{let r=await authFetch(`/communities/list?nocache=${new Date().getTime()}`); let d=await r.json(); let mList=document.getElementById('my-comms-grid');mList.innerHTML='';if((d.my_comms||[]).length===0)mList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases')}</p>`;(d.my_comms||[]).forEach(c=>{mList.innerHTML+=`<div class="comm-card" data-id="${c.id}" onclick="openCommunity(${c.id})"><img src="${c.avatar_url}" class="comm-avatar"><div class="req-dot" style="display:none;position:absolute;top:-5px;right:-5px;background:#ff5555;color:white;font-size:10px;padding:3px 8px;border-radius:12px;font-weight:bold;box-shadow:0 0 10px #ff5555;border:2px solid var(--dark-bg);z-index:10;">NOVO</div><b style="color:white;font-size:16px;font-family:'Rajdhani';letter-spacing:1px;">${c.name}</b></div>`;});fetchUnread();}catch(e){ console.error(e); }}
async function loadPublicComms(){try{let r=await authFetch(`/communities/search?nocache=${new Date().getTime()}`); let d=await r.json(); let pList=document.getElementById('public-comms-grid');pList.innerHTML='';if((d||[]).length===0)pList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;(d||[]).forEach(c=>{let btnStr=c.is_private?`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:orange;color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>`:`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:#2ecc71;color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;pList.innerHTML+=`<div class="comm-card"><img src="${c.avatar_url}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:'Rajdhani';letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`;});}catch(e){ console.error(e); }}
function clearCommSearch(){document.getElementById('search-comm-input').value='';loadPublicComms();}
async function searchComms(){try{let q=document.getElementById('search-comm-input').value.trim();let r=await authFetch(`/communities/search?q=${q}&nocache=${new Date().getTime()}`); let d=await r.json(); let pList=document.getElementById('public-comms-grid');pList.innerHTML='';if((d||[]).length===0)pList.innerHTML=`<p style='color:#888;grid-column:1/-1;'>${t('no_bases_found')}</p>`;(d||[]).forEach(c=>{let btnStr=c.is_private?`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:orange;color:orange;" onclick="requestCommJoin(${c.id})">${t('request_join')}</button>`:`<button class="glass-btn" style="padding:5px 10px;width:100%;border-color:#2ecc71;color:#2ecc71;" onclick="joinCommunity(${c.id})">${t('enter')}</button>`;pList.innerHTML+=`<div class="comm-card"><img src="${c.avatar_url}" class="comm-avatar"><b style="color:white;font-size:15px;font-family:'Rajdhani';letter-spacing:1px;margin-bottom:5px;">${c.name}</b>${btnStr}</div>`;});}catch(e){ console.error(e); }}
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
            mHtml+=`<div style="display:flex;align-items:center;gap:10px;padding:10px;border-bottom:1px solid #333;border-radius:10px;transition:0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'"><img src="${m.avatar}" onclick="openPublicProfile(${m.id})" style="width:35px;height:35px;border-radius:50%;object-fit:cover;border:1px solid #555;cursor:pointer;"> <span style="color:white;flex:1;font-weight:bold;cursor:pointer;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" onclick="openPublicProfile(${m.id})">${m.name}</span> <span class="ch-badge" style="color:${m.role==='admin'||m.id===d.creator_id?'var(--primary)':'#888'}">${roleBadge}</span>${actions}</div>`;
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
                <img src="${rq.avatar}" style="width:30px;height:30px;border-radius:50%;object-fit:cover;">
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
async function submitEditChannel(){let n=document.getElementById('edit-ch-name').value.trim();let tType=document.getElementById('edit-ch-type').value;let p=document.getElementById('edit-ch-priv').value;let banFile=document.getElementById('edit-ch-banner').files[0];if(!n)return;let btn=document.getElementById('btn-edit-ch');btn.disabled=true;btn.innerText="SALVANDO...";try{let bu=null; if(banFile){let formData = new FormData(); formData.append('file', banFile); let res = await authFetch('/upload', { method: 'POST', body: formData, headers: {} }); let data = await res.json(); bu = data.secure_url; } let payload={channel_id:window.currentEditChannelId, name:n, type:tType, is_private:parseInt(p), banner_url:bu}; let r=await authFetch('/community/channel/edit', {method:'POST', body:JSON.stringify(payload)}); if(r.ok){document.getElementById('modal-edit-channel').classList.add('hidden');openCommunity(activeCommId, true);}}catch(e){ console.error(e); }finally{btn.disabled=false;btn.innerText=t('save');}}

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
        await authFetch(`/community/channel/${activeChannelId}/send`,{method:'POST',body:JSON.stringify({content:data.secure_url})});
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
        document.getElementById('pub-rank').innerHTML = formatRankInfo(d.rank, d.special_emblem, d.rank_color);
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
    return data.secure_url;
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
        res.innerHTML=d.map(u=>`<div class="friend-row" onclick="openPublicProfile(${u.id})" style="cursor:pointer;"><div class="av-wrap"><img src="${u.avatar_url}" class="friend-av" onerror="this.src='https://ui-avatars.com/api/?name=U&background=111&color=66fcf1'"><div class="status-dot" data-uid="${u.id}"></div></div><div style="flex:1"><b style="color:white;">${u.username}</b></div><button class="glass-btn" style="padding:5px 12px;margin:0;" onclick="event.stopPropagation();sendFriendReq(${u.id})">${t('add_friend')}</button></div>`).join('');
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