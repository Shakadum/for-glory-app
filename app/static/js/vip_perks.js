/**
 * ForGlory — VIP Perks UI
 * Borda de perfil (prata/ouro), cor do nome, painel de seleção
 */

// ── Cache de perks do usuário atual ─────────────────────────────────────────
let __vipPerks = null;

async function loadVipPerks(force = false) {
    if (__vipPerks && !force) return __vipPerks;
    try {
        const r = await authFetch('/my/vip-perks');
        __vipPerks = await r.json();
        // Aplicar borda no avatar do usuário logado
        if (window.__currentUser) applyVipBorder(window.__currentUser.id, __vipPerks.current_border);
        return __vipPerks;
    } catch(e) { return null; }
}

// ── Aplicar borda VIP num elemento de avatar ─────────────────────────────────
/**
 * Envolve um <img> de avatar com o frame VIP.
 * @param {HTMLElement} imgEl  — o elemento <img>
 * @param {string} border      — 'none' | 'prata' | 'ouro'
 * @param {number} size        — tamanho px do avatar (default 48)
 */
function wrapAvatarWithBorder(imgEl, border, size = 48) {
    if (!imgEl || !border || border === 'none') return;

    // Remover borda anterior se já aplicada
    removeVipBorder(imgEl);

    const frameUrl = border === 'ouro'
        ? '/static/vip_border_ouro.png'
        : '/static/vip_border_prata.png';

    const parent = imgEl.parentElement;
    if (!parent) return;

    // Wrapper posicionado
    const wrap = document.createElement('div');
    wrap.className = 'vip-av-wrap';
    wrap.style.cssText =
        `position:relative;` +
        `width:${size}px;height:${size}px;` +
        `flex-shrink:0;display:inline-block;`;

    parent.insertBefore(wrap, imgEl);
    wrap.appendChild(imgEl);

    // Avatar: centralizado, circular, menor que o wrap
    const av = Math.round(size * 0.70);
    imgEl.style.cssText =
        `position:absolute;` +
        `top:50%;left:50%;` +
        `transform:translate(-50%,-50%);` +
        `width:${av}px;height:${av}px;` +
        `border-radius:50%;object-fit:cover;`;

    // Frame ornamentado por cima — PNG com transparência real, sem blend mode
    const frame = document.createElement('img');
    frame.src = frameUrl;
    frame.className = 'vip-border-frame';
    frame.style.cssText =
        `position:absolute;inset:0;` +
        `width:100%;height:100%;` +
        `pointer-events:none;` +
        `object-fit:contain;`;
    wrap.appendChild(frame);

    wrap.dataset.vipBorderWrap = border;
}

function removeVipBorder(imgEl) {
    if (!imgEl) return;
    // Se está dentro de um wrap, tirar o img de volta e remover o wrap
    const wrap = imgEl.closest('.vip-av-wrap');
    if (wrap && wrap.parentElement) {
        imgEl.style.cssText = '';
        wrap.parentElement.insertBefore(imgEl, wrap);
        wrap.remove();
    }
    imgEl.style.outline = '';
    imgEl.style.outlineOffset = '';
    imgEl.style.boxShadow = '';
    delete imgEl.dataset.borderApplied;
}

// ── Aplicar borda VIP globalmente (chat, lista, perfil) ──────────────────────
function applyAllVipBorders() {
    // Será chamado após carregar mensagens e listas
    // Usa dataset para não aplicar duas vezes
    document.querySelectorAll('[data-vip-border]:not([data-border-applied])').forEach(el => {
        if (el.dataset.vipBorder === 'none') return;
        const border = el.dataset.vipBorder;
        const size = parseInt(el.dataset.vipSize || '48');
        el.dataset.borderApplied = '1';
        wrapAvatarWithBorder(el, border, size);
    });
}

// ── Nome colorido ────────────────────────────────────────────────────────────
function applyVipNameColor(el, color) {
    if (!el || !color) return;
    el.style.color = color;
    el.style.textShadow = `0 0 8px ${color}66`;
}

// ── Balão de chat VIP ouro ───────────────────────────────────────────────────
function applyVipBubble(bubbleEl, bubbleType) {
    if (!bubbleEl || !bubbleType || bubbleType === 'none') return;
    if (bubbleType === 'prata') {
        bubbleEl.style.background    = 'linear-gradient(135deg, #1e1e2e 0%, #2d2d3f 40%, #1a1a2a 100%)';
        bubbleEl.style.border        = '1px solid rgba(180,180,220,0.5)';
        bubbleEl.style.boxShadow     = '0 0 10px rgba(160,160,255,0.2), inset 0 1px 0 rgba(255,255,255,0.08)';
        bubbleEl.style.color         = '#dde0ff';
        bubbleEl.style.backdropFilter = 'blur(4px)';
    }
}

function applyAllVipBubbles() {
    document.querySelectorAll('[data-vip-bubble]:not([data-bubble-applied])').forEach(el => {
        const t = el.dataset.vipBubble;
        if (t && t !== 'none') {
            applyVipBubble(el, t);
            el.dataset.bubbleApplied = '1';
        }
    });
}

// manter alias para compatibilidade
function applyGoldBubble(bubbleEl) { applyVipBubble(bubbleEl, 'prata'); }

// ── Aplicar balões VIP em todos os .msg-bubble com data-vip-bubble ─────────
function applyAllVipBubbles() {
    document.querySelectorAll('[data-vip-bubble]:not([data-bubble-applied])').forEach(el => {
        const t = el.dataset.vipBubble;
        if (t && t !== 'none') {
            applyVipBubble(el, t);
            el.dataset.bubbleApplied = '1';
        }
    });
}

// ── Painel de seleção de borda (dentro do VIP panel) ─────────────────────────
async function renderVipBorderPanel(container) {
    if (!container) return;
    const perks = await loadVipPerks(true);
    if (!perks) { container.innerHTML = ''; return; }

    const cur = perks.current_border || 'none';

    const borderOption = (id, label, imgUrl, available, reason) => {
        const active = cur === id;
        return `
        <div style="background:rgba(255,255,255,0.04);border:2px solid ${active ? '#ffd93d' : '#222'};
             border-radius:14px;padding:14px;text-align:center;position:relative;
             opacity:${available ? '1' : '0.45'};">
            ${active ? '<div style="position:absolute;top:6px;right:8px;color:#ffd93d;font-size:11px;font-weight:bold;">✓ ATIVA</div>' : ''}
            ${imgUrl
                ? `<img src="${imgUrl}" style="width:90px;height:90px;object-fit:contain;margin:0 auto 8px;display:block;">`
                : `<div style="width:90px;height:90px;border-radius:50%;border:2px dashed #333;margin:0 auto 8px;display:flex;align-items:center;justify-content:center;color:#555;font-size:22px;">👤</div>`}
            <div style="color:white;font-weight:bold;font-size:13px;margin-bottom:4px;">${label}</div>
            ${available
                ? `<button onclick="selectVipBorder('${id}')"
                    style="margin-top:6px;background:${active ? '#ffd93d' : 'rgba(255,211,61,0.15)'};
                    color:${active ? '#0b0c10' : '#ffd93d'};border:1px solid #ffd93d;
                    border-radius:8px;padding:5px 14px;font-size:12px;cursor:pointer;font-family:'Rajdhani';font-weight:700;">
                    ${active ? '✓ Selecionada' : 'Selecionar'}
                  </button>`
                : `<div style="color:#666;font-size:11px;margin-top:6px;">${reason}</div>`}
        </div>`;
    };

    // Cor do nome
    const nameColorHtml = perks.is_vip ? `
        <div style="margin-top:16px;padding:14px;background:rgba(255,255,255,0.04);border-radius:12px;border:1px solid #222;">
            <div style="color:var(--primary);font-size:13px;font-weight:bold;margin-bottom:8px;">✏️ Cor do nome</div>
            <div style="display:flex;align-items:center;gap:10px;">
                <input type="color" id="vip-name-color-picker" value="${perks.name_color || '#66fcf1'}"
                    style="width:40px;height:40px;border:none;background:none;cursor:pointer;border-radius:50%;">
                <input type="text" id="vip-name-color-hex" value="${perks.name_color || '#66fcf1'}"
                    placeholder="#RRGGBB" maxlength="7"
                    style="flex:1;background:#111;color:white;border:1px solid #333;border-radius:8px;padding:7px 10px;font-size:13px;">
                <button onclick="saveVipNameColor()"
                    style="background:rgba(102,252,241,0.15);border:1px solid var(--primary);color:var(--primary);
                    border-radius:8px;padding:7px 14px;font-size:12px;cursor:pointer;font-family:'Rajdhani';font-weight:700;">
                    SALVAR
                </button>
                <button onclick="saveVipNameColor('')"
                    style="background:transparent;border:1px solid #444;color:#666;
                    border-radius:8px;padding:7px 10px;font-size:12px;cursor:pointer;">
                    Padrão
                </button>
            </div>
            <div style="margin-top:8px;font-size:12px;color:#555;">Prévia: 
                <span id="vip-name-preview" style="color:${perks.name_color || '#66fcf1'};font-weight:bold;">
                    ${window.__currentUser?.username || 'Você'}
                </span>
            </div>
        </div>` : '';

    // Progresso ouro (se não desbloqueado)
    const goldProgressHtml = (!perks.gold_unlocked_permanently && perks.is_vip) ? `
        <div style="margin-top:10px;padding:10px;background:rgba(255,211,61,0.05);border:1px solid #ffd93d33;border-radius:10px;font-size:12px;">
            <div style="color:#ffd93d;font-weight:bold;margin-bottom:4px;">🔓 Desbloquear Borda Ouro</div>
            <div style="color:#888;">Faltam <b style="color:white;">${perks.months_to_gold} meses</b> ou assine o plano anual</div>
            <div style="width:100%;height:6px;background:#222;border-radius:3px;margin-top:6px;">
                <div style="width:${Math.min(100, (perks.total_vip_months/12)*100)}%;height:100%;background:#ffd93d;border-radius:3px;"></div>
            </div>
            <div style="color:#555;font-size:11px;margin-top:4px;">${perks.total_vip_months}/12 meses acumulados</div>
        </div>` : '';

    container.innerHTML = `
        <div style="margin-top:12px;">
            <div style="color:var(--primary);font-size:13px;font-weight:bold;margin-bottom:10px;">🖼️ Borda de perfil</div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">
                ${borderOption('none', 'Sem borda', null, true, '')}
                ${borderOption('prata', 'VIP Prata', '/static/vip_border_prata.png', perks.silver_available, 'Requer assinatura VIP')}
                ${borderOption('ouro', 'VIP Ouro', '/static/vip_border_ouro.png', perks.gold_available,
                    perks.gold_unlocked_permanently ? 'Reative a assinatura' : `${perks.months_to_gold} meses restantes`)}
            </div>
            ${goldProgressHtml}
            ${nameColorHtml}
        </div>`;

    // Sync picker ↔ hex input
    const picker = document.getElementById('vip-name-color-picker');
    const hexIn  = document.getElementById('vip-name-color-hex');
    const prev   = document.getElementById('vip-name-preview');
    if (picker) {
        picker.addEventListener('input', () => {
            if (hexIn) hexIn.value = picker.value;
            if (prev)  { prev.style.color = picker.value; }
        });
        if (hexIn) hexIn.addEventListener('input', () => {
            if (/^#[0-9a-fA-F]{6}$/.test(hexIn.value)) {
                picker.value = hexIn.value;
                if (prev) prev.style.color = hexIn.value;
            }
        });
    }
}

async function selectVipBorder(border) {
    try {
        const r = await authFetch('/my/vip-perks/set-border', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({border}),
        });
        const d = await r.json();
        if (d.error) { showToast('❌ ' + d.error); return; }
        __vipPerks = null;
        showToast(border === 'none' ? 'Borda removida' : `✅ Borda ${border} ativada!`);
        // Re-render panel
        const el = document.getElementById('vip-border-panel');
        if (el) renderVipBorderPanel(el);
    } catch(e) { showToast('Erro ao definir borda'); }
}

async function saveVipNameColor(forceColor) {
    const color = forceColor !== undefined
        ? forceColor
        : (document.getElementById('vip-name-color-hex')?.value?.trim() || '');
    try {
        const r = await authFetch('/my/vip-perks/set-name-color', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({color}),
        });
        const d = await r.json();
        if (d.error) { showToast('❌ ' + d.error); return; }
        __vipPerks = null;
        showToast(color ? `✅ Cor #${color} salva!` : 'Cor redefinida para o padrão');
    } catch(e) { showToast('Erro ao salvar cor'); }
}

window.loadVipPerks         = loadVipPerks;
window.wrapAvatarWithBorder = wrapAvatarWithBorder;
window.removeVipBorder       = removeVipBorder;
window.applyAllVipBorders   = applyAllVipBorders;
window.applyVipNameColor    = applyVipNameColor;
window.applyGoldBubble      = applyGoldBubble;
window.applyVipBubble       = applyVipBubble;
window.applyAllVipBubbles   = applyAllVipBubbles;
window.renderVipBorderPanel = renderVipBorderPanel;
window.selectVipBorder      = selectVipBorder;
window.saveVipNameColor     = saveVipNameColor;
