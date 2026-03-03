// ============================================================
//  FOR GLORY — PORTAL DA TRANSPARÊNCIA
//  Adicione ao final de app/static/transparency.js
// ============================================================

window.__transState = {
    tab:         'search',       // 'search' | 'profile' | 'compare'
    politician:  null,           // politician object atualmente aberto
    compareList: [],             // lista de IDs para comparar (max 4)
    searchResults: [],
    country:     'BR',
};

// ────────────────────────────────────────────────────────────
//  INICIALIZA
// ────────────────────────────────────────────────────────────
async function initTransparency() {
    renderTransparencyView('search');
    // Carrega destaques
    try {
        const r = await authFetch('/transparency/featured');
        if (r.ok) {
            const data = await r.json();
            renderFeatured(data.featured || []);
        }
    } catch (e) {}
}

// ────────────────────────────────────────────────────────────
//  RENDERIZA ESTADO DA VIEW
// ────────────────────────────────────────────────────────────
function renderTransparencyView(tab) {
    window.__transState.tab = tab;
    const container = document.getElementById('trans-content');
    if (!container) return;

    // Update tab buttons
    document.querySelectorAll('.trans-tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.tab === tab);
    });

    if (tab === 'search') renderSearchView(container);
    else if (tab === 'profile') renderProfileView(container);
    else if (tab === 'compare') renderCompareView(container);
}

// ────────────────────────────────────────────────────────────
//  ABA: BUSCA
// ────────────────────────────────────────────────────────────
function renderSearchView(container) {
    container.innerHTML = `
        <div class="trans-search-bar">
            <div class="trans-country-chips" id="trans-country-chips">
                ${['BR','US','FR','DE','GB','AR','PT','MX','JP','CN'].map(cc => `
                    <button class="trans-chip ${window.__transState.country === cc ? 'active' : ''}"
                        onclick="setTransCountry('${cc}')">${cc}</button>
                `).join('')}
            </div>
            <div class="trans-input-row">
                <input id="trans-search-input"
                    class="gs-input" style="flex:1;"
                    placeholder="🔍 Buscar político por nome..."
                    onkeydown="if(event.key==='Enter') doTransSearch()">
                <button class="btn-main" style="margin:0; padding:10px 18px;" onclick="doTransSearch()">Buscar</button>
            </div>
        </div>
        <div id="trans-featured" class="trans-featured-grid"></div>
        <div id="trans-results" class="trans-results-list"></div>
    `;
}

function setTransCountry(cc) {
    window.__transState.country = cc;
    document.querySelectorAll('.trans-chip').forEach(b => b.classList.toggle('active', b.dataset && b.textContent.trim() === cc));
    // Re-render chips
    const chips = document.getElementById('trans-country-chips');
    if (chips) {
        chips.querySelectorAll('.trans-chip').forEach(b => {
            b.classList.toggle('active', b.textContent.trim() === cc);
        });
    }
}

async function doTransSearch() {
    const q = (document.getElementById('trans-search-input')?.value || '').trim();
    if (!q) return;

    const results = document.getElementById('trans-results');
    if (!results) return;
    results.innerHTML = '<div class="news-loading"><div class="news-spinner"></div><span>Buscando...</span></div>';

    try {
        const r = await authFetch(`/transparency/search?q=${encodeURIComponent(q)}&country=${window.__transState.country}`);
        if (!r.ok) throw new Error();
        const data = await r.json();
        renderSearchResults(data.results || []);
    } catch (e) {
        results.innerHTML = '<div class="news-empty">Erro ao buscar. Tente novamente.</div>';
    }
}

function renderSearchResults(list) {
    const el = document.getElementById('trans-results');
    if (!el) return;
    if (!list.length) {
        el.innerHTML = '<div class="news-empty"><div style="font-size:32px;margin-bottom:8px;">🔍</div>Nenhum resultado encontrado.</div>';
        return;
    }
    el.innerHTML = list.map(p => politicianCard(p, 'search')).join('');
}

function renderFeatured(list) {
    const el = document.getElementById('trans-featured');
    if (!el || !list.length) return;
    el.innerHTML = `
        <div class="trans-section-label">⭐ Destaques Globais</div>
        <div class="trans-featured-row">
            ${list.map(p => politicianCard(p, 'featured')).join('')}
        </div>`;
}

// ────────────────────────────────────────────────────────────
//  CARD DO POLÍTICO
// ────────────────────────────────────────────────────────────
function politicianCard(p, mode = 'search') {
    const inCompare = window.__transState.compareList.includes(p.id);
    const sourceColors = { 'camara': '#66fcf1', 'senado': '#ffd93d', 'wikidata': '#c678dd' };
    const srcColor = sourceColors[p.source] || '#888';

    return `
    <div class="trans-card" onclick="openPolitician(${JSON.stringify(p).replace(/"/g,'&quot;')})">
        <div class="trans-card-left">
            <img src="${escapeHtml(p.photo || '')}" class="trans-card-photo"
                onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(p.name)}&background=1a2030&color=66fcf1&size=80'">
            <div class="trans-card-source" style="color:${srcColor}">${(p.source||'').toUpperCase()}</div>
        </div>
        <div class="trans-card-info">
            <div class="trans-card-name">${escapeHtml(p.name)}</div>
            <div class="trans-card-role">${escapeHtml(p.role || '')}</div>
            <div class="trans-card-meta">
                ${p.party ? `<span class="trans-meta-chip">${escapeHtml(p.party)}</span>` : ''}
                ${p.state ? `<span class="trans-meta-chip">${escapeHtml(p.state)}</span>` : ''}
                ${p.country ? `<span class="trans-meta-chip">🌍 ${escapeHtml(p.country)}</span>` : ''}
            </div>
        </div>
        <div class="trans-card-actions">
            <button class="trans-compare-btn ${inCompare ? 'active' : ''}"
                onclick="event.stopPropagation(); toggleCompare(${JSON.stringify(p).replace(/"/g,'&quot;')})"
                title="${inCompare ? 'Remover do comparativo' : 'Adicionar ao comparativo'}">
                ${inCompare ? '✓' : '+'}
            </button>
        </div>
    </div>`;
}

// ────────────────────────────────────────────────────────────
//  ABA: PERFIL DO POLÍTICO
// ────────────────────────────────────────────────────────────
async function openPolitician(p) {
    window.__transState.politician = p;
    const container = document.getElementById('trans-content');
    if (!container) return;

    // Switch to profile tab
    document.querySelectorAll('.trans-tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.tab === 'profile');
    });
    window.__transState.tab = 'profile';

    container.innerHTML = '<div class="news-loading" style="margin-top:60px;"><div class="news-spinner"></div><span>Carregando ficha...</span></div>';

    try {
        const r = await authFetch(`/transparency/politician/${p.id}`);
        if (!r.ok) throw new Error();
        const details = await r.json();
        renderProfile(p, details, container);
    } catch (e) {
        container.innerHTML = `<div class="news-empty">Erro ao carregar dados. <button class="glass-btn" onclick="renderTransparencyView('search')">← Voltar</button></div>`;
    }
}

function renderProfile(p, d, container) {
    const rating = d.community_rating || {};
    const avgRating = rating.average;
    const stars = (score) => '★'.repeat(score) + '☆'.repeat(5 - score);

    const expenseRows = (d.expenses || []).map(e =>
        `<div class="trans-row">
            <span style="flex:1;color:#c5c6c7;">${escapeHtml(e.description || '')}</span>
            <span style="color:#ffd93d;font-weight:600;">R$ ${Number(e.value||0).toLocaleString('pt-BR', {minimumFractionDigits:2})}</span>
            <span style="color:#6b7280;font-size:11px;margin-left:8px;">${escapeHtml(e.date||'')}</span>
        </div>`
    ).join('') || '<div style="color:#6b7280;font-size:13px;padding:8px 0;">Dados não disponíveis</div>';

    const voteRows = (d.votes || []).map(v =>
        `<div class="trans-row">
            <span style="flex:1;color:#c5c6c7;font-size:12px;">${escapeHtml(v.description || '')}</span>
            ${v.vote ? `<span class="trans-meta-chip" style="background:rgba(102,252,241,0.1);color:#66fcf1;">${escapeHtml(v.vote)}</span>` : ''}
            <span style="color:#6b7280;font-size:11px;">${escapeHtml(v.date||'')}</span>
        </div>`
    ).join('') || '<div style="color:#6b7280;font-size:13px;padding:8px 0;">Sem votações registradas</div>';

    const comments = (rating.comments || []).map(c =>
        `<div class="trans-comment">
            <div class="trans-comment-stars">${stars(c.score)}</div>
            <div style="color:#c5c6c7;font-size:12px;">${escapeHtml(c.comment || '')}</div>
            <div style="color:#4b5563;font-size:11px;">${c.date}</div>
        </div>`
    ).join('');

    container.innerHTML = `
        <div class="trans-profile-wrap">
            <!-- Back button -->
            <button class="trans-back-btn" onclick="renderTransparencyView('search')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                Voltar à busca
            </button>

            <!-- Hero -->
            <div class="trans-profile-hero">
                <img src="${escapeHtml(p.photo || d.photo || '')}" class="trans-profile-photo"
                    onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(p.name)}&background=1a2030&color=66fcf1&size=120'">
                <div class="trans-profile-hero-info">
                    <div class="trans-profile-name">${escapeHtml(p.name)}</div>
                    <div class="trans-profile-role">${escapeHtml(d.role || p.role || '')}</div>
                    <div class="trans-card-meta" style="margin-top:6px;">
                        ${(d.party||p.party) ? `<span class="trans-meta-chip">${escapeHtml(d.party||p.party)}</span>` : ''}
                        ${(d.state||p.state) ? `<span class="trans-meta-chip">${escapeHtml(d.state||p.state)}</span>` : ''}
                        ${(d.country||p.country) ? `<span class="trans-meta-chip">🌍 ${escapeHtml(d.country||p.country)}</span>` : ''}
                    </div>
                    ${avgRating ? `
                    <div class="trans-rating-display">
                        <span class="trans-stars-big">${'★'.repeat(Math.round(avgRating))}${'☆'.repeat(5-Math.round(avgRating))}</span>
                        <span style="color:#ffd93d;font-weight:700;">${avgRating}</span>
                        <span style="color:#6b7280;font-size:12px;">(${rating.count} avaliações)</span>
                    </div>` : ''}
                </div>
                <button class="trans-compare-btn-lg ${window.__transState.compareList.includes(p.id) ? 'active' : ''}"
                    onclick="toggleCompare(${JSON.stringify(p).replace(/"/g,'&quot;')})">
                    ${window.__transState.compareList.includes(p.id) ? '✓ No comparativo' : '+ Comparar'}
                </button>
            </div>

            <!-- Bio -->
            ${d.bio ? `<div class="trans-section"><div class="trans-section-label">📖 Biografia</div><p style="color:#9ca3af;font-size:13px;line-height:1.7;margin:0;">${escapeHtml(d.bio)}</p></div>` : ''}

            <!-- Dados pessoais -->
            <div class="trans-section">
                <div class="trans-section-label">📋 Dados</div>
                <div class="trans-data-grid">
                    ${d.full_name ? `<div class="trans-data-item"><span class="trans-data-label">Nome completo</span><span class="trans-data-value">${escapeHtml(d.full_name)}</span></div>` : ''}
                    ${d.birth_date ? `<div class="trans-data-item"><span class="trans-data-label">Nascimento</span><span class="trans-data-value">${escapeHtml(d.birth_date)}</span></div>` : ''}
                    ${d.birth_place ? `<div class="trans-data-item"><span class="trans-data-label">Naturalidade</span><span class="trans-data-value">${escapeHtml(d.birth_place)}</span></div>` : ''}
                    ${d.education ? `<div class="trans-data-item"><span class="trans-data-label">Formação</span><span class="trans-data-value">${escapeHtml(d.education)}</span></div>` : ''}
                    ${d.occupation ? `<div class="trans-data-item"><span class="trans-data-label">Profissão</span><span class="trans-data-value">${escapeHtml(d.occupation)}</span></div>` : ''}
                    ${d.email ? `<div class="trans-data-item"><span class="trans-data-label">E-mail</span><span class="trans-data-value">${escapeHtml(d.email)}</span></div>` : ''}
                </div>
            </div>

            <!-- Aviso legal -->
            <div class="trans-legal-notice">
                ⚖️ <strong>Aviso legal:</strong> Informações obtidas de fontes públicas oficiais (APIs da Câmara, Senado, Wikidata e Portal da Transparência). Processos e dados financeiros são de domínio público conforme a Lei de Acesso à Informação (Lei 12.527/2011).
            </div>

            <!-- Despesas -->
            <div class="trans-section">
                <div class="trans-section-label">💰 Últimas Despesas Declaradas</div>
                ${expenseRows}
                ${p.source === 'camara' ? `<a href="https://www.camara.leg.br/deputados/${p.api_id}" target="_blank" class="trans-source-link">Ver tudo na Câmara ↗</a>` : ''}
            </div>

            <!-- Votações -->
            <div class="trans-section">
                <div class="trans-section-label">🗳️ Votações Recentes</div>
                ${voteRows}
            </div>

            <!-- Avaliar -->
            <div class="trans-section">
                <div class="trans-section-label">⭐ Avaliação da Comunidade</div>
                <div class="trans-rating-widget" id="trans-rating-widget">
                    <div style="color:#9ca3af;font-size:13px;margin-bottom:10px;">Como você avalia a atuação deste político?</div>
                    <div class="trans-stars-input" id="trans-stars-${p.id}">
                        ${[1,2,3,4,5].map(n => `<span class="trans-star" data-val="${n}" onclick="setRatingStar('${escapeHtml(p.id)}',${n})">☆</span>`).join('')}
                    </div>
                    <textarea id="trans-rating-comment" placeholder="Deixe um comentário (opcional)..."
                        style="width:100%;box-sizing:border-box;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:8px;color:#c5c6c7;padding:10px;font-family:'DM Sans';font-size:13px;resize:none;height:70px;margin-top:10px;outline:none;"></textarea>
                    <button class="btn-main" style="margin-top:8px;padding:8px 20px;"
                        onclick="submitRating('${escapeHtml(p.id)}')">Enviar Avaliação</button>
                </div>
                ${comments ? `<div class="trans-comments-list">${comments}</div>` : ''}
            </div>
        </div>`;

    // Rating interaction
    window.__transCurrentRating = 0;
}

function setRatingStar(politicianId, val) {
    window.__transCurrentRating = val;
    const stars = document.querySelectorAll(`#trans-stars-${CSS.escape(politicianId)} .trans-star`);
    stars.forEach((s, i) => {
        s.textContent = i < val ? '★' : '☆';
        s.style.color = i < val ? '#ffd93d' : '#4b5563';
    });
}

async function submitRating(politicianId) {
    if (!window.__transCurrentRating) {
        showToast('Selecione uma nota de 1 a 5!');
        return;
    }
    const comment = (document.getElementById('trans-rating-comment')?.value || '').trim();
    try {
        const r = await authFetch('/transparency/rate', {
            method: 'POST',
            body: JSON.stringify({
                politician_id: politicianId,
                user_id: user.id,
                score: window.__transCurrentRating,
                comment,
            })
        });
        if (r.ok) {
            showToast('✅ Avaliação enviada!');
            document.getElementById('trans-rating-widget').innerHTML =
                `<div style="color:#66fcf1;font-family:'Rajdhani';font-size:16px;">✓ Avaliação registrada. Obrigado por fiscalizar!</div>`;
        }
    } catch (e) {
        showToast('Erro ao enviar avaliação.');
    }
}

// ────────────────────────────────────────────────────────────
//  ABA: COMPARATIVO
// ────────────────────────────────────────────────────────────
function toggleCompare(p) {
    const list = window.__transState.compareList;
    const pList = window.__transState.comparePoliticians || (window.__transState.comparePoliticians = []);
    const idx = list.indexOf(p.id);

    if (idx >= 0) {
        list.splice(idx, 1);
        pList.splice(idx, 1);
    } else {
        if (list.length >= 4) {
            showToast('Máximo de 4 políticos no comparativo.');
            return;
        }
        list.push(p.id);
        pList.push(p);
    }

    // Update compare badge
    const badge = document.getElementById('trans-compare-badge');
    if (badge) {
        badge.textContent = list.length || '';
        badge.style.display = list.length ? 'flex' : 'none';
    }

    showToast(idx >= 0 ? '✗ Removido do comparativo' : `✓ ${p.name} adicionado ao comparativo`);
}

async function renderCompareView(container) {
    const list = window.__transState.compareList;
    const pList = window.__transState.comparePoliticians || [];

    if (list.length < 2) {
        container.innerHTML = `
            <div class="news-empty" style="padding:60px 20px;">
                <div style="font-size:40px;margin-bottom:16px;">⚖️</div>
                <div style="font-family:'Rajdhani';font-size:18px;color:var(--primary);margin-bottom:8px;">Comparativo de Políticos</div>
                <div style="color:#6b7280;font-size:13px;line-height:1.6;">
                    Adicione pelo menos 2 políticos ao comparativo usando o botão <strong style="color:#c5c6c7;">+</strong> nos cards de busca.
                </div>
                <button class="glass-btn" style="margin-top:20px;" onclick="renderTransparencyView('search')">← Buscar Políticos</button>
            </div>`;
        return;
    }

    container.innerHTML = '<div class="news-loading"><div class="news-spinner"></div><span>Carregando comparativo...</span></div>';

    try {
        const r = await authFetch(`/transparency/compare?ids=${list.join(',')}`);
        if (!r.ok) throw new Error();
        const data = await r.json();

        const politicians = data.politicians || [];
        if (!politicians.length) throw new Error();

        // Build comparison table
        const fields = [
            { key: 'party', label: 'Partido' },
            { key: 'state', label: 'Estado/UF' },
            { key: 'country', label: 'País' },
            { key: 'education', label: 'Formação' },
            { key: 'occupation', label: 'Profissão anterior' },
            { key: 'birth_date', label: 'Nascimento' },
        ];

        const headers = politicians.map((p, i) => {
            const orig = pList[i] || {};
            return `
                <th class="trans-cmp-header">
                    <img src="${escapeHtml(orig.photo || '')}" class="trans-cmp-photo"
                        onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(orig.name||'?')}&background=1a2030&color=66fcf1&size=60'">
                    <div class="trans-cmp-name">${escapeHtml(orig.name || p.id)}</div>
                    <div class="trans-cmp-role">${escapeHtml(orig.role || '')}</div>
                </th>`;
        }).join('');

        const rows = fields.map(f => {
            const cells = politicians.map(p =>
                `<td class="trans-cmp-cell">${escapeHtml(p[f.key] || '—')}</td>`
            ).join('');
            return `<tr><td class="trans-cmp-label">${f.label}</td>${cells}</tr>`;
        }).join('');

        // Expenses row
        const expCells = politicians.map(p => {
            const total = (p.expenses || []).reduce((s, e) => s + (e.value || 0), 0);
            return `<td class="trans-cmp-cell" style="color:#ffd93d;">R$ ${total.toLocaleString('pt-BR', {minimumFractionDigits:2})}</td>`;
        }).join('');

        container.innerHTML = `
            <div class="trans-profile-wrap">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                    <div style="font-family:'Rajdhani';font-size:18px;color:var(--primary);font-weight:700;">⚖️ Comparativo</div>
                    <button class="trans-back-btn" onclick="renderTransparencyView('search')">← Voltar</button>
                </div>
                <div style="overflow-x:auto;">
                    <table class="trans-compare-table">
                        <thead><tr><th class="trans-cmp-label">Campo</th>${headers}</tr></thead>
                        <tbody>
                            ${rows}
                            <tr><td class="trans-cmp-label">💰 Total despesas (recente)</td>${expCells}</tr>
                        </tbody>
                    </table>
                </div>
                <button class="glass-btn" style="margin-top:16px;" onclick="window.__transState.compareList=[]; window.__transState.comparePoliticians=[]; renderTransparencyView('search');">
                    ✕ Limpar comparativo
                </button>
            </div>`;
    } catch (e) {
        container.innerHTML = `<div class="news-empty">Erro ao carregar comparativo. <button class="glass-btn" onclick="renderTransparencyView('search')">← Voltar</button></div>`;
    }
}

// ────────────────────────────────────────────────────────────
//  HOOK: inicializa quando view-news é aberta
// ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const _newsOrig = window.goView;
    if (typeof _newsOrig === 'function') {
        window.goView = function(v, btn) {
            _newsOrig(v, btn);
            if (v === 'news') {
                // Initialize both tabs on first open
                const activeMainTab = document.querySelector('.news-main-tab.active');
                if (activeMainTab) {
                    const t = activeMainTab.dataset.main;
                    if (t === 'news') initNews();
                    else if (t === 'transparency') initTransparency();
                }
            }
        };
    }
});
