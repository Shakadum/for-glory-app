/**
 * ForGlory — Cosméticos VIP
 * Abas: Bordas | Balões | Nome
 * Para adicionar novos itens: só inserir nos catálogos abaixo.
 */

/* global authFetch, showToast, escapeHtml */

// ── Catálogos ─────────────────────────────────────────────────────────────────

const BORDERS_CATALOG = [
    { id:'none',  label:'Sem Borda',  desc:'Visual padrão',            preview:null,                        unlock:'free'       },
    { id:'prata', label:'VIP Prata',  desc:'Assinantes VIP ativos',    preview:'/static/vip_border_prata.jpg', unlock:'vip_active', lockMsg:'Assine o plano VIP para desbloquear' },
    { id:'ouro',  label:'VIP Ouro',   desc:'12 meses VIP ou plano anual', preview:'/static/vip_border_ouro.jpg', unlock:'vip_gold',   lockMsg:null },
];

const BUBBLES_CATALOG = [
    { id:'none',  label:'Padrão',    desc:'Balão padrão do app',         preview:null,                        previewBg:'rgba(255,255,255,0.08)', unlock:'free'       },
    { id:'prata', label:'VIP Prata', desc:'Balão metálico prateado',     preview:'/static/vip_bubble_prata.jpg', previewBg:null,                unlock:'vip_active', lockMsg:'Assine o plano VIP para desbloquear' },
];

const FONTS_CATALOG = [
    { id:'',                  label:'Padrão',   sample:'ForGlory',  css:"'DM Sans', sans-serif",          unlock:'free'       },
    { id:'Rajdhani',          label:'Rajdhani', sample:'ForGlory',  css:"'Rajdhani', sans-serif",          unlock:'vip_active' },
    { id:'Syne',              label:'Syne',     sample:'ForGlory',  css:"'Syne', sans-serif",              unlock:'vip_active' },
    { id:'Orbitron',          label:'Orbitron', sample:'FORGLORY',  css:"'Orbitron', sans-serif",          unlock:'vip_active' },
    { id:'Cinzel Decorative', label:'Cinzel',   sample:'ForGlory',  css:"'Cinzel Decorative', serif",      unlock:'vip_gold'   },
];

// ── Estado ────────────────────────────────────────────────────────────────────
let __cosmPerks = null;

async function loadCosmetics() {
    try {
        const r = await authFetch('/my/vip-perks');
        __cosmPerks = await r.json();
    } catch(e) {
        __cosmPerks = {
            is_vip:false, silver_available:false, gold_available:false,
            gold_unlocked_permanently:false, total_vip_months:0, months_to_gold:12,
            current_border:'none', current_bubble:'none', current_font:null, name_color:null,
        };
    }
    switchCosmeticsTab('borders');
}

// ── Abas ──────────────────────────────────────────────────────────────────────
function switchCosmeticsTab(tab) {
    ['borders','bubbles','nome'].forEach(t => {
        const btn   = document.getElementById('cosm-tab-' + t);
        const panel = document.getElementById('cosm-panel-' + t);
        const on    = t === tab;
        if (btn) {
            btn.style.borderBottom = on ? '2px solid var(--primary,#66fcf1)' : '2px solid transparent';
            btn.style.color        = on ? 'var(--primary,#66fcf1)' : '#555';
            btn.style.fontWeight   = on ? '700' : '500';
        }
        if (panel) panel.style.display = on ? 'block' : 'none';
    });
    if (tab === 'borders') renderGrid('cosm-panel-borders', BORDERS_CATALOG, 'border', __cosmPerks?.current_border || 'none');
    if (tab === 'bubbles') renderGrid('cosm-panel-bubbles', BUBBLES_CATALOG, 'bubble', __cosmPerks?.current_bubble || 'none');
    if (tab === 'nome')    renderNomePanel();
}

// ── Desbloqueio ───────────────────────────────────────────────────────────────
function isUnlocked(item, perks) {
    if (item.unlock === 'free')       return true;
    if (item.unlock === 'vip_active') return !!perks?.silver_available;
    if (item.unlock === 'vip_gold')   return !!perks?.gold_available;
    return false;
}

function getLockMsg(item, perks) {
    if (item.unlock === 'vip_active') return item.lockMsg || 'Requer VIP ativo';
    if (item.unlock === 'vip_gold') {
        if (perks?.gold_unlocked_permanently) return 'Reative a assinatura VIP';
        const left = perks?.months_to_gold ?? 12;
        return 'Faltam ' + left + ' mês' + (left !== 1 ? 'es' : '') + ' VIP ou plano anual';
    }
    return 'Em breve';
}

// ── Grade de cards ────────────────────────────────────────────────────────────
function renderGrid(containerId, catalog, type, currentId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;padding:4px 0 8px;">' +
        catalog.map(item => renderCard(item, __cosmPerks, currentId, type)).join('') +
        '</div>';
}

function renderCard(item, perks, currentId, type) {
    const unlocked = isUnlocked(item, perks);
    const active   = currentId === item.id;
    const lockMsg  = unlocked ? '' : getLockMsg(item, perks);

    // Barra de progresso ouro
    let progress = '';
    if (!unlocked && item.unlock === 'vip_gold' && perks) {
        const pct = Math.min(100, ((perks.total_vip_months || 0) / 12) * 100);
        progress = '<div style="margin-top:6px;">' +
            '<div style="width:100%;height:4px;background:#1a1a1a;border-radius:2px;overflow:hidden;">' +
            '<div style="width:' + pct + '%;height:100%;background:#ffd93d;border-radius:2px;"></div></div>' +
            '<div style="color:#555;font-size:10px;margin-top:2px;text-align:center;">' +
            (perks.total_vip_months || 0) + '/12 meses acumulados</div></div>';
    }

    // Preview
    let preview;
    if (type === 'border') {
        preview = '<div style="position:relative;width:72px;height:72px;margin:0 auto 10px;">' +
            '<div style="width:46px;height:46px;border-radius:50%;background:#111;border:2px solid #2a2a2a;' +
            'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);' +
            'display:flex;align-items:center;justify-content:center;font-size:16px;">' +
            (unlocked ? '👤' : '🔒') + '</div>' +
            (item.preview ? '<img src="' + item.preview + '" style="position:absolute;inset:0;width:100%;height:100%;' +
            'object-fit:contain;pointer-events:none;' + (!unlocked ? 'filter:grayscale(1) opacity(0.3);' : '') + '">' : '') +
            '</div>';
    } else {
        preview = '<div style="margin:0 auto 10px;padding:0 4px;">' +
            '<div style="border-radius:12px 12px 12px 0;padding:7px 11px;font-size:11px;color:white;' +
            (item.preview
                ? 'background-image:url(\'' + item.preview + '\');background-size:cover;background-position:center;text-shadow:0 1px 3px rgba(0,0,0,0.9);'
                : 'background:' + (item.previewBg || 'rgba(255,255,255,0.08)') + ';border:1px solid #2a2a2a;') +
            (!unlocked ? 'filter:grayscale(1) opacity(0.35);' : '') + '">' +
            'Olá! Prévia 👋</div></div>';
    }

    const borderCol = active ? '#ffd93d' : (unlocked ? '#2a2a3e' : '#1a1a1e');
    const bgCol     = active ? 'rgba(255,211,61,0.06)' : 'rgba(255,255,255,0.02)';

    let action;
    if (active) {
        action = '<div style="font-size:10px;color:#ffd93d;font-family:\'Rajdhani\';font-weight:700;">✓ Em uso</div>';
    } else if (unlocked) {
        action = '<button onclick="event.stopPropagation();selectCosmetic(\'' + type + '\',\'' + item.id + '\')" ' +
            'style="width:100%;padding:5px;background:rgba(102,252,241,0.08);border:1px solid rgba(102,252,241,0.3);' +
            'color:var(--primary,#66fcf1);border-radius:7px;font-size:11px;cursor:pointer;' +
            'font-family:\'Rajdhani\';font-weight:700;">USAR</button>';
    } else {
        action = '<div style="background:rgba(0,0,0,0.25);border-radius:7px;padding:5px 6px;' +
            'font-size:10px;color:#444;line-height:1.4;">🔒 ' + lockMsg + '</div>' + progress;
    }

    return '<div onclick="' + (unlocked && !active ? 'selectCosmetic(\'' + type + '\',\'' + item.id + '\')' : '') + '" ' +
        'style="border:2px solid ' + borderCol + ';background:' + bgCol + ';border-radius:14px;padding:12px;' +
        'text-align:center;position:relative;cursor:' + (unlocked && !active ? 'pointer' : 'default') + ';' +
        'transition:border-color 0.2s;">' +
        (active ? '<div style="position:absolute;top:7px;right:7px;background:#ffd93d;color:#0b0c10;' +
            'border-radius:5px;padding:1px 7px;font-size:9px;font-family:\'Rajdhani\';font-weight:800;">✓ ATIVA</div>' : '') +
        (!unlocked ? '<div style="position:absolute;top:7px;left:7px;font-size:13px;">🔒</div>' : '') +
        preview +
        '<div style="color:' + (unlocked ? 'white' : '#444') + ';font-weight:700;font-size:12px;margin-bottom:2px;font-family:\'Rajdhani\';">' + item.label + '</div>' +
        '<div style="color:' + (unlocked ? '#6b7280' : '#2a2a2a') + ';font-size:10px;margin-bottom:8px;">' + item.desc + '</div>' +
        action + '</div>';
}

// ── Painel Nome ───────────────────────────────────────────────────────────────
function renderNomePanel() {
    const el = document.getElementById('cosm-panel-nome');
    if (!el) return;
    const perks    = __cosmPerks;
    const isVip    = !!perks?.is_vip;
    const curFont  = perks?.current_font || '';
    const curColor = perks?.name_color || '#66fcf1';

    const fontCards = FONTS_CATALOG.map(function(font) {
        const unlocked = isUnlocked(font, perks);
        const active   = curFont === font.id;
        const lockMsg  = unlocked ? '' : getLockMsg(font, perks);

        let btn;
        if (active) {
            btn = '<span style="font-size:9px;font-family:\'Rajdhani\';font-weight:800;color:#ffd93d;' +
                'background:rgba(255,211,61,0.15);border-radius:5px;padding:2px 7px;flex-shrink:0;">✓ ATIVA</span>';
        } else if (unlocked) {
            btn = '<button onclick="event.stopPropagation();selectFont(\'' + font.id + '\')" ' +
                'style="background:rgba(102,252,241,0.08);border:1px solid rgba(102,252,241,0.3);' +
                'color:var(--primary,#66fcf1);border-radius:7px;padding:4px 10px;font-size:10px;' +
                'cursor:pointer;font-family:\'Rajdhani\';font-weight:700;flex-shrink:0;">USAR</button>';
        } else {
            btn = '<span style="font-size:10px;color:#333;flex-shrink:0;">🔒</span>';
        }

        return '<div onclick="' + (unlocked ? 'selectFont(\'' + font.id + '\')' : '') + '" ' +
            'style="display:flex;align-items:center;gap:12px;padding:10px 12px;' +
            'border:2px solid ' + (active ? '#ffd93d' : (unlocked ? '#2a2a3e' : '#1a1a1e')) + ';' +
            'background:' + (active ? 'rgba(255,211,61,0.05)' : 'rgba(255,255,255,0.02)') + ';' +
            'border-radius:11px;cursor:' + (unlocked && !active ? 'pointer' : 'default') + ';' +
            'transition:border-color 0.2s;">' +
            '<div style="flex:1;min-width:0;">' +
            '<div style="font-family:' + font.css + ';font-size:15px;color:' + (unlocked ? curColor : '#2a2a2a') + ';' +
            'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + font.sample + '</div>' +
            '<div style="font-size:10px;color:' + (unlocked ? '#555' : '#2a2a2a') + ';margin-top:1px;">' +
            font.label + (!unlocked ? ' · ' + lockMsg : '') + '</div></div>' +
            btn + '</div>';
    }).join('');

    const colorSection = isVip
        ? '<div style="margin-top:16px;padding:13px;background:rgba(255,255,255,0.03);' +
          'border:1px solid #1e1e2e;border-radius:12px;">' +
          '<div style="font-family:\'Rajdhani\';font-weight:800;font-size:13px;color:#c5c6c7;' +
          'letter-spacing:.5px;margin-bottom:10px;">🎨 COR DO NOME</div>' +
          '<div style="display:flex;align-items:center;gap:8px;">' +
          '<input type="color" id="cosm-color-pick" value="' + curColor + '" ' +
          'style="width:38px;height:38px;border:none;background:none;cursor:pointer;border-radius:50%;padding:0;flex-shrink:0;">' +
          '<input type="text" id="cosm-color-hex" value="' + curColor + '" maxlength="7" placeholder="#RRGGBB" ' +
          'style="flex:1;background:#111;color:white;border:1px solid #2a2a2a;border-radius:8px;padding:8px 10px;font-size:13px;">' +
          '<button onclick="saveNameColor()" style="background:rgba(102,252,241,0.1);border:1px solid rgba(102,252,241,0.35);' +
          'color:var(--primary,#66fcf1);border-radius:8px;padding:8px 14px;font-size:11px;cursor:pointer;' +
          'font-family:\'Rajdhani\';font-weight:700;flex-shrink:0;">SALVAR</button>' +
          '<button onclick="saveNameColor(\'\')" title="Resetar" style="background:transparent;border:1px solid #222;' +
          'color:#444;border-radius:8px;padding:8px 10px;font-size:13px;cursor:pointer;flex-shrink:0;">↺</button></div>' +
          '<div style="margin-top:10px;padding:8px 10px;background:#0b0c10;border-radius:8px;font-size:12px;color:#555;">' +
          'Prévia: <span id="cosm-name-prev" style="font-weight:600;color:' + curColor + ';' +
          'text-shadow:0 0 8px ' + curColor + '55;margin-left:6px;">' +
          (window.__currentUser?.username || 'Você') + '</span></div></div>'
        : '<div style="margin-top:16px;padding:12px;background:rgba(255,211,61,0.04);' +
          'border:1px solid rgba(255,211,61,0.12);border-radius:12px;text-align:center;">' +
          '<div style="font-size:12px;color:#555;">🎨 Cor do nome — disponível para assinantes VIP ⭐</div></div>';

    el.innerHTML = '<div style="padding:4px 0 12px;">' +
        '<div style="font-family:\'Rajdhani\';font-weight:800;font-size:13px;color:#c5c6c7;' +
        'letter-spacing:.5px;margin-bottom:10px;">✍️ FONTE DO NOME</div>' +
        '<div style="display:flex;flex-direction:column;gap:8px;">' + fontCards + '</div>' +
        colorSection + '</div>';

    // Sync picker ↔ hex ↔ preview
    const pick = document.getElementById('cosm-color-pick');
    const hex  = document.getElementById('cosm-color-hex');
    const prev = document.getElementById('cosm-name-prev');
    if (pick && hex && prev) {
        pick.addEventListener('input', function() {
            hex.value = pick.value;
            prev.style.color = pick.value;
            prev.style.textShadow = '0 0 8px ' + pick.value + '55';
        });
        hex.addEventListener('input', function() {
            if (/^#[0-9a-fA-F]{6}$/.test(hex.value)) {
                pick.value = hex.value;
                prev.style.color = hex.value;
                prev.style.textShadow = '0 0 8px ' + hex.value + '55';
            }
        });
    }
}

// ── Ações ─────────────────────────────────────────────────────────────────────
async function selectCosmetic(type, id) {
    const ep   = type === 'border' ? '/my/vip-perks/set-border' : '/my/vip-perks/set-bubble';
    const body = type === 'border' ? { border: id } : { bubble: id };
    try {
        const r = await authFetch(ep, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
        const d = await r.json();
        if (d.error) { showToast('❌ ' + d.error); return; }
        __cosmPerks = null;
        showToast(id === 'none' ? '✅ Visual padrão restaurado' : '✅ ' + id.charAt(0).toUpperCase() + id.slice(1) + ' ativado!');
        await loadCosmetics();
        switchCosmeticsTab(type === 'border' ? 'borders' : 'bubbles');
    } catch(e) { showToast('Erro ao salvar'); }
}

async function selectFont(fontId) {
    try {
        const r = await authFetch('/my/vip-perks/set-font', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ font: fontId }) });
        const d = await r.json();
        if (d.error) { showToast('❌ ' + d.error); return; }
        if (__cosmPerks) __cosmPerks.current_font = fontId;
        showToast('✅ Fonte atualizada!');
        renderNomePanel();
    } catch(e) { showToast('Erro ao salvar fonte'); }
}

async function saveNameColor(forceColor) {
    const color = forceColor !== undefined ? forceColor : (document.getElementById('cosm-color-hex')?.value?.trim() || '');
    try {
        const r = await authFetch('/my/vip-perks/set-name-color', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ color }) });
        const d = await r.json();
        if (d.error) { showToast('❌ ' + d.error); return; }
        if (__cosmPerks) __cosmPerks.name_color = color || null;
        showToast(color ? '✅ Cor salva!' : 'Cor resetada para o padrão');
        renderNomePanel();
    } catch(e) { showToast('Erro ao salvar cor'); }
}

window.loadCosmetics      = loadCosmetics;
window.switchCosmeticsTab = switchCosmeticsTab;
window.selectCosmetic     = selectCosmetic;
window.selectFont         = selectFont;
window.saveNameColor      = saveNameColor;
