// ============================================================
//  FOR GLORY — PORTAL DA TRANSPARÊNCIA v3
// ============================================================

window.__transState = {
    tab: 'search', politician: null, compareList: [], comparePoliticians: [],
    searchResults: [], country: 'BR', currentRating: 0,
};

// ── INIT ─────────────────────────────────────────────────────
async function initTransparency() {
    renderTransparencyView('search');
    try {
        const r = await authFetch('/transparency/featured');
        if (r.ok) { const d = await r.json(); renderFeatured(d.featured || []); }
    } catch(e) {}
}

// ── TABS ──────────────────────────────────────────────────────
function renderTransparencyView(tab) {
    window.__transState.tab = tab;
    document.querySelectorAll('.trans-tab-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.tab === tab));
    const container = document.getElementById('trans-content');
    if (!container) return;
    if (tab === 'search')   renderSearchView(container);
    else if (tab === 'profile') {
        if (window.__transState.politician) openPolitician(window.__transState.politician);
        else renderSearchView(container);
    }
    else if (tab === 'compare') renderCompareView(container);
}

// ── BUSCA ─────────────────────────────────────────────────────
function renderSearchView(container) {
    container.innerHTML = `
        <div class="trans-search-bar">
            <div class="trans-country-chips">
                ${['BR','US','FR','DE','GB','AR','PT','MX','JP','CN','RU','IT','ES'].map(cc =>
                    `<button class="trans-chip ${window.__transState.country===cc?'active':''}"
                        onclick="setTransCountry('${cc}')">${cc}</button>`).join('')}
            </div>
            <div class="trans-input-row">
                <input id="trans-search-input" class="gs-input" style="flex:1;"
                    placeholder="🔍 Buscar político por nome..."
                    onkeydown="if(event.key==='Enter')doTransSearch()">
                <button class="btn-main" style="margin:0;padding:10px 18px;" onclick="doTransSearch()">Buscar</button>
            </div>
        </div>
        <div id="trans-featured" class="trans-featured-grid"></div>
        <div id="trans-results" class="trans-results-list"></div>`;
}

function setTransCountry(cc) {
    window.__transState.country = cc;
    document.querySelectorAll('.trans-chip').forEach(b =>
        b.classList.toggle('active', b.textContent.trim() === cc));
}

async function doTransSearch() {
    const q = (document.getElementById('trans-search-input')?.value||'').trim();
    if (!q) return;
    const results = document.getElementById('trans-results');
    if (!results) return;
    results.innerHTML = '<div class="news-loading"><div class="news-spinner"></div><span>Buscando políticos...</span></div>';
    try {
        const r = await authFetch(`/transparency/search?q=${encodeURIComponent(q)}&country=${window.__transState.country}`);
        if (!r.ok) throw new Error();
        const data = await r.json();
        const list = data.results || [];
        if (!list.length) {
            results.innerHTML = '<div class="news-empty"><div style="font-size:32px;margin-bottom:8px;">🔍</div>Nenhum político encontrado com este nome.</div>';
            return;
        }
        results.innerHTML = list.map(p => politicianCard(p)).join('');
    } catch(e) {
        results.innerHTML = '<div class="news-empty">Erro ao buscar. Tente novamente.</div>';
    }
}

function renderFeatured(list) {
    const el = document.getElementById('trans-featured');
    if (!el || !list.length) return;
    el.innerHTML = `
        <div class="trans-section-label" style="margin-bottom:10px;">⭐ Destaques Globais</div>
        <div class="trans-featured-row">${list.map(p => politicianCard(p, true)).join('')}</div>`;
}

// ── CARD ──────────────────────────────────────────────────────
function politicianCard(p, compact=false) {
    const inCompare = window.__transState.compareList.includes(p.id);
    const srcColor  = {camara:'#66fcf1',senado:'#ffd93d',wikidata:'#c678dd'}[p.source]||'#888';
    const pSafe     = escapeHtml(JSON.stringify(p));
    return `
    <div class="trans-card ${compact?'trans-card-compact':''}"
        onclick='openPolitician(${JSON.stringify(p).replace(/</g,"\\u003c").replace(/>/g,"\\u003e").replace(/&/g,"\\u0026")})'>
        <div class="trans-card-left">
            <img src="${escapeHtml(p.photo||'')}" class="trans-card-photo"
                onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(p.name||'?')}&background=1a2030&color=66fcf1&size=80'">
            <div class="trans-card-source" style="color:${srcColor}">${(p.source||'').toUpperCase()}</div>
        </div>
        <div class="trans-card-info">
            <div class="trans-card-name">${escapeHtml(p.name||'')}</div>
            <div class="trans-card-role">${escapeHtml(p.role||'')}</div>
            <div class="trans-card-meta">
                ${p.party?`<span class="trans-meta-chip">${escapeHtml(p.party)}</span>`:''}
                ${p.state?`<span class="trans-meta-chip">${escapeHtml(p.state)}</span>`:''}
                ${p.country?`<span class="trans-meta-chip">🌍 ${escapeHtml(p.country)}</span>`:''}
            </div>
        </div>
        <div class="trans-card-actions">
            <button class="trans-compare-btn ${inCompare?'active':''}"
                onclick="event.stopPropagation();toggleCompare(${JSON.stringify(p).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026')})"
                title="${inCompare?'Remover':'Adicionar ao comparativo'}">${inCompare?'✓':'+'}</button>
        </div>
    </div>`;
}

// ── PERFIL ────────────────────────────────────────────────────
async function openPolitician(p) {
    window.__transState.politician = p;
    document.querySelectorAll('.trans-tab-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.tab === 'profile'));
    window.__transState.tab = 'profile';
    const container = document.getElementById('trans-content');
    if (!container) return;
    container.innerHTML = '<div class="news-loading" style="margin-top:60px;"><div class="news-spinner"></div><span>Carregando ficha completa...</span></div>';
    try {
        const r = await authFetch(`/transparency/politician/${p.id}`);
        if (!r.ok) throw new Error();
        const d = await r.json();
        renderProfile(p, d, container);
    } catch(e) {
        container.innerHTML = `<div class="news-empty">Erro ao carregar. <button class="glass-btn" onclick="renderTransparencyView('search')">← Voltar</button></div>`;
    }
}

function _stars(n, max=5) {
    n = Math.round(n||0);
    return '<span style="color:#ffd93d;letter-spacing:2px;">'+'★'.repeat(n)+'☆'.repeat(max-n)+'</span>';
}
function _fmt_brl(v) {
    return 'R$ ' + Number(v||0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});
}
function _fmt_date(s) {
    if (!s) return '';
    try { return new Date(s+'T00:00:00').toLocaleDateString('pt-BR'); } catch{ return s; }
}

function renderProfile(p, d, container) {
    const r     = d.community_rating || {};
    const sal   = d.salary_info;
    const inCmp = window.__transState.compareList.includes(p.id);

    // ── Bio
    const bioHtml = d.bio ? `
        <div class="trans-section">
            <div class="trans-section-label">📖 Biografia</div>
            <p style="color:#9ca3af;font-size:13px;line-height:1.75;margin:0;">${escapeHtml(d.bio)}</p>
            ${d.wiki_link?`<a href="${escapeHtml(d.wiki_link)}" target="_blank" class="trans-source-link">Leia mais na Wikipedia ↗</a>`:''}
        </div>` : '';

    // ── Dados pessoais
    const fields = [
        ['Nome completo', d.full_name||p.name],
        ['Nascimento', _fmt_date(d.birth_date)],
        ['Local de nascimento', d.birth_place],
        ['País', d.country||p.country],
        ['Partido(s)', (d.all_parties||[d.party||p.party]).filter(Boolean).join(' • ')],
        ['Formação', (d.all_education||[d.education]).filter(Boolean).join(' • ')],
        ['Profissão anterior', d.occupation],
        ['E-mail', d.email],
        ['Site oficial', d.website ? `<a href="${escapeHtml(d.website)}" target="_blank" style="color:#66fcf1;">${escapeHtml(d.website)}</a>` : ''],
    ].filter(([,v]) => v);

    const dadosHtml = fields.length ? `
        <div class="trans-section">
            <div class="trans-section-label">📋 Dados Pessoais</div>
            <div class="trans-data-grid">${fields.map(([k,v]) =>
                `<div class="trans-data-item">
                    <span class="trans-data-label">${k}</span>
                    <span class="trans-data-value">${v}</span>
                </div>`).join('')}
            </div>
        </div>` : '';

    // ── Cargos
    const allRoles = d.all_roles || (d.role ? [d.role] : []);
    const cargosHtml = allRoles.length ? `
        <div class="trans-section">
            <div class="trans-section-label">🏛️ Cargos Exercidos</div>
            ${allRoles.map(r2 => `<div class="trans-row"><span style="color:#c5c6c7;font-size:13px;">• ${escapeHtml(r2)}</span></div>`).join('')}
        </div>` : '';

    // ── Salário e Benefícios
    const salarioHtml = sal ? `
        <div class="trans-section">
            <div class="trans-section-label">💰 Salário e Benefícios (${escapeHtml(sal.cargo)})</div>
            <div class="trans-salary-hero">
                <div class="trans-salary-value">${_fmt_brl(sal.subsidio_mensal)}<span style="font-size:12px;color:#9ca3af;font-weight:400;">/mês</span></div>
                <div class="trans-salary-desc">${escapeHtml(sal.subsidio_desc)}</div>
            </div>
            <div class="trans-section-label" style="margin:12px 0 8px;font-size:11px;">BENEFÍCIOS INCLUÍDOS</div>
            ${(sal.beneficios||[]).map(b2 => `
                <div class="trans-benefit-row">
                    <div style="flex:1;">
                        <div style="color:#c5c6c7;font-size:13px;font-weight:600;">${escapeHtml(b2.nome)}</div>
                        <div style="color:#6b7280;font-size:11px;margin-top:2px;">${escapeHtml(b2.descricao)}</div>
                    </div>
                    <div style="color:#ffd93d;font-size:12px;font-weight:700;white-space:nowrap;margin-left:12px;">${escapeHtml(b2.valor)}</div>
                </div>`).join('')}
            <div class="trans-benefit-waiver">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                ${escapeHtml(sal.beneficios_abdicados_info||'')}
            </div>
            <a href="${escapeHtml(sal.fonte||'')}" target="_blank" class="trans-source-link">Fonte oficial: Portal da Transparência ↗</a>
        </div>` : '';

    // ── Despesas
    const expenses = d.expenses || [];
    const totalDesp = expenses.reduce((s,e)=>s+(e.value||0),0);
    const despesasHtml = `
        <div class="trans-section">
            <div class="trans-section-label" style="display:flex;justify-content:space-between;align-items:center;">
                <span>🧾 Últimas Despesas Declaradas</span>
                ${totalDesp?`<span style="color:#ffd93d;font-size:12px;">Total: ${_fmt_brl(totalDesp)}</span>`:''}
            </div>
            ${expenses.length ? expenses.map(e => `
                <div class="trans-row">
                    <div style="flex:1;min-width:0;">
                        <div style="color:#c5c6c7;font-size:12px;font-weight:600;">${escapeHtml(e.description||'')}</div>
                        <div style="color:#6b7280;font-size:11px;">${escapeHtml(e.provider||'')}</div>
                    </div>
                    <div style="text-align:right;flex-shrink:0;margin-left:8px;">
                        <div style="color:#ffd93d;font-weight:700;font-size:12px;">${_fmt_brl(e.value)}</div>
                        <div style="color:#4b5563;font-size:10px;">${escapeHtml(e.date||'')}</div>
                    </div>
                </div>`).join('')
            : '<div style="color:#6b7280;font-size:13px;padding:8px 0;">Sem despesas registradas ou fonte não disponível para este cargo.</div>'}
        </div>`;

    // ── Votações
    const votes = d.votes || [];
    const voteIcon = v => {
        const vv = (v||'').toLowerCase();
        if (vv === 'sim' || vv === 'yes') return '<span style="color:#2ecc71;">✅ Sim</span>';
        if (vv === 'não' || vv === 'no' || vv === 'nao') return '<span style="color:#ff5555;">❌ Não</span>';
        if (vv === 'abstenção' || vv === 'abstencao' || vv === 'abstain') return '<span style="color:#ffd93d;">⬜ Abstenção</span>';
        if (v) return `<span style="color:#9ca3af;">${escapeHtml(v)}</span>`;
        return '';
    };
    const votacoesHtml = `
        <div class="trans-section">
            <div class="trans-section-label">🗳️ Votações Recentes</div>
            ${votes.length ? votes.map(v => `
                <div class="trans-row" style="align-items:flex-start;gap:10px;">
                    <div style="flex:1;min-width:0;">
                        <div style="color:#c5c6c7;font-size:12px;line-height:1.5;">${escapeHtml(v.description||'Votação sem descrição')}</div>
                        <div style="color:#4b5563;font-size:10px;margin-top:2px;">${escapeHtml(v.date||'')}</div>
                    </div>
                    <div style="flex-shrink:0;font-size:12px;">${voteIcon(v.vote)}</div>
                </div>`).join('')
            : '<div style="color:#6b7280;font-size:13px;padding:8px 0;">Sem votações registradas ou não disponível para este cargo.</div>'}
        </div>`;

    // ── Casos na Justiça
    const charges = d.charges || [];
    const chargesHtml = `
        <div class="trans-section">
            <div class="trans-section-label">⚖️ Casos na Justiça</div>
            <div class="trans-legal-notice">
                ⚠️ <strong>Aviso legal:</strong> Dados obtidos de fontes públicas (Wikidata, Wikipedia, registros judiciais públicos). 
                Registros de processos em andamento não implicam condenação. Inocência presumida até julgamento final. 
                Conforme Lei 12.527/2011 (Lei de Acesso à Informação).
            </div>
            ${charges.length ? `
                <div style="margin-bottom:8px;">
                    ${charges.map(c => `
                        <div class="trans-row">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ff6b6b" stroke-width="2" style="flex-shrink:0;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                            <span style="color:#fca5a5;font-size:13px;">${escapeHtml(c)}</span>
                        </div>`).join('')}
                </div>` : ''}
            ${d.bio && (d.bio.toLowerCase().includes('process') || d.bio.toLowerCase().includes('acus') || d.bio.toLowerCase().includes('condenad') || d.bio.toLowerCase().includes('preso') || d.bio.toLowerCase().includes('corrupç')) ?
                `<div style="color:#9ca3af;font-size:12px;line-height:1.6;padding:8px;background:rgba(255,107,107,0.06);border-radius:8px;border-left:3px solid rgba(255,107,107,0.3);">
                    ℹ️ Informações sobre processos jurídicos podem constar na biografia (Wikipedia) acima.
                </div>` :
                charges.length === 0 ? '<div style="color:#6b7280;font-size:13px;padding:8px 0;">Nenhum processo criminal registrado em fontes públicas consultadas.</div>' : ''}
        </div>`;

    // ── Avaliação da Comunidade
    const avgRating = r.average;
    const ratingHtml = `
        <div class="trans-section" id="trans-rating-section">
            <div class="trans-section-label">⭐ Avaliação da Comunidade</div>
            ${avgRating ? `
                <div class="trans-rating-summary">
                    <div class="trans-rating-big-score">${avgRating}</div>
                    <div>
                        <div>${_stars(avgRating)}</div>
                        <div style="color:#6b7280;font-size:12px;margin-top:4px;">${r.count} avaliação${r.count!==1?'ões':''}</div>
                    </div>
                </div>` : '<div style="color:#6b7280;font-size:13px;margin-bottom:12px;">Seja o primeiro a avaliar!</div>'}

            <div class="trans-rating-widget" id="trans-rating-widget-${p.id}">
                <div style="color:#9ca3af;font-size:12px;margin-bottom:10px;">Sua avaliação:</div>
                <div class="trans-stars-input" id="trans-stars-${p.id}">
                    ${[1,2,3,4,5].map(n =>
                        `<span class="trans-star" data-val="${n}"
                            onmouseover="hoverRatingStar('${escapeHtml(p.id)}',${n})"
                            onmouseout="unhoverRatingStar('${escapeHtml(p.id)}')"
                            onclick="setRatingStar('${escapeHtml(p.id)}',${n})">☆</span>`
                    ).join('')}
                </div>
                <textarea id="trans-rating-comment-${p.id}"
                    placeholder="Deixe um comentário público sobre a atuação deste político (opcional)..."
                    style="width:100%;box-sizing:border-box;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:8px;color:#c5c6c7;padding:10px;font-family:'DM Sans';font-size:13px;resize:none;height:80px;margin-top:10px;outline:none;"></textarea>
                <button class="btn-main" style="margin-top:8px;padding:8px 20px;"
                    onclick="submitRating('${escapeHtml(p.id)}')">📤 Enviar Avaliação</button>
            </div>

            ${(r.comments||[]).length ? `
                <div class="trans-section-label" style="margin-top:16px;font-size:11px;">AVALIAÇÕES RECENTES</div>
                <div class="trans-comments-list">
                    ${r.comments.map(c => `
                        <div class="trans-comment">
                            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                                ${_stars(c.score)}
                                <span style="color:#4b5563;font-size:11px;">${escapeHtml(c.date)}</span>
                            </div>
                            ${c.comment?`<div style="color:#9ca3af;font-size:12px;margin-top:4px;">"${escapeHtml(c.comment)}"</div>`:''}
                        </div>`).join('')}
                </div>` : ''}
        </div>`;

    container.innerHTML = `
        <div class="trans-profile-wrap">
            <button class="trans-back-btn" onclick="renderTransparencyView('search')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                Voltar à busca
            </button>
            <!-- HERO -->
            <div class="trans-profile-hero">
                <img src="${escapeHtml(d.photo||p.photo||'')}" class="trans-profile-photo"
                    onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(p.name||'?')}&background=1a2030&color=66fcf1&size=120'">
                <div class="trans-profile-hero-info" style="flex:1;min-width:0;">
                    <div class="trans-profile-name">${escapeHtml(d.full_name||p.name||'')}</div>
                    <div class="trans-profile-role">${escapeHtml(d.role||p.role||d.description||'')}</div>
                    <div class="trans-card-meta" style="margin-top:6px;flex-wrap:wrap;">
                        ${((d.all_parties&&d.all_parties.length?d.all_parties:[d.party||p.party]).filter(Boolean)).map(pt=>
                            `<span class="trans-meta-chip">${escapeHtml(pt)}</span>`).join('')}
                        ${(d.state||p.state)?`<span class="trans-meta-chip">${escapeHtml(d.state||p.state)}</span>`:''}
                        ${(d.country||p.country)?`<span class="trans-meta-chip">🌍 ${escapeHtml(d.country||p.country)}</span>`:''}
                    </div>
                    ${avgRating?`<div style="margin-top:8px;display:flex;align-items:center;gap:8px;">
                        ${_stars(avgRating)}<span style="color:#ffd93d;font-weight:700;font-size:14px;">${avgRating}</span>
                        <span style="color:#6b7280;font-size:12px;">(${r.count})</span></div>`:''}
                </div>
                <button class="trans-compare-btn-lg ${inCmp?'active':''}"
                    onclick="toggleCompare(${JSON.stringify(p).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026')})">
                    ${inCmp?'✓ No comparativo':'+ Comparar'}
                </button>
            </div>
            ${bioHtml}${dadosHtml}${cargosHtml}${salarioHtml}${despesasHtml}${votacoesHtml}${chargesHtml}${ratingHtml}
        </div>`;

    window.__transState.currentRating = 0;
}

// ── AVALIAÇÃO ─────────────────────────────────────────────────
function hoverRatingStar(pid, val) {
    if (window.__transState.currentRating > 0) return;
    const stars = document.querySelectorAll(`#trans-stars-${CSS.escape(pid)} .trans-star`);
    stars.forEach((s,i) => { s.textContent = i<val?'★':'☆'; s.style.color = i<val?'#ffd93d':'#4b5563'; });
}
function unhoverRatingStar(pid) {
    const cur = window.__transState.currentRating;
    const stars = document.querySelectorAll(`#trans-stars-${CSS.escape(pid)} .trans-star`);
    stars.forEach((s,i) => { s.textContent = i<cur?'★':'☆'; s.style.color = i<cur?'#ffd93d':'#4b5563'; });
}
function setRatingStar(pid, val) {
    window.__transState.currentRating = val;
    const stars = document.querySelectorAll(`#trans-stars-${CSS.escape(pid)} .trans-star`);
    stars.forEach((s,i) => { s.textContent = i<val?'★':'☆'; s.style.color = i<val?'#ffd93d':'#4b5563'; });
}
async function submitRating(pid) {
    const score = window.__transState.currentRating;
    if (!score) { showToast('⭐ Selecione uma nota de 1 a 5!'); return; }
    const comment = (document.getElementById(`trans-rating-comment-${pid}`)?.value||'').trim();
    try {
        const r = await authFetch('/transparency/rate', {
            method: 'POST',
            body: JSON.stringify({ politician_id: pid, user_id: user.id, score, comment })
        });
        if (!r.ok) throw new Error();
        const data = await r.json();
        if (data.error) { showToast('Erro: ' + data.error); return; }
        showToast('✅ Avaliação enviada! Obrigado por fiscalizar.');
        const widget = document.getElementById(`trans-rating-widget-${pid}`);
        if (widget) widget.innerHTML = `
            <div style="background:rgba(102,252,241,0.08);border:1px solid rgba(102,252,241,0.2);border-radius:10px;padding:14px;text-align:center;">
                <div>${_stars(score)}</div>
                <div style="color:#66fcf1;font-family:'Rajdhani';font-size:16px;margin-top:6px;">Avaliação registrada!</div>
                <div style="color:#6b7280;font-size:12px;margin-top:4px;">Média atual: ${data.new_average} ⭐ (${data.count} avaliações)</div>
            </div>`;
    } catch(e) { showToast('Erro ao enviar avaliação.'); }
}

// ── COMPARATIVO ───────────────────────────────────────────────
function toggleCompare(p) {
    const list = window.__transState.compareList;
    const pList = window.__transState.comparePoliticians;
    const idx = list.indexOf(p.id);
    if (idx >= 0) { list.splice(idx,1); pList.splice(idx,1); }
    else {
        if (list.length >= 4) { showToast('Máximo de 4 políticos no comparativo.'); return; }
        list.push(p.id); pList.push(p);
    }
    const badge = document.getElementById('trans-compare-badge');
    const count = document.getElementById('trans-compare-count');
    if (badge) { badge.textContent = list.length||''; badge.style.display = list.length?'flex':'none'; }
    if (count) { count.textContent = list.length||''; count.style.display = list.length?'inline':'none'; }
    showToast(idx>=0 ? `✗ ${p.name} removido` : `✓ ${p.name} adicionado`);
}

async function renderCompareView(container) {
    const list = window.__transState.compareList;
    const pList = window.__transState.comparePoliticians;
    if (list.length < 2) {
        container.innerHTML = `<div class="news-empty" style="padding:60px 20px;">
            <div style="font-size:40px;margin-bottom:16px;">⚖️</div>
            <div style="font-family:'Rajdhani';font-size:18px;color:var(--primary);margin-bottom:8px;">Comparativo de Políticos</div>
            <div style="color:#6b7280;font-size:13px;">Adicione ao menos 2 políticos com o botão <strong style="color:#c5c6c7;">+</strong>.</div>
            <button class="glass-btn" style="margin-top:20px;" onclick="renderTransparencyView('search')">← Buscar</button></div>`;
        return;
    }
    container.innerHTML = '<div class="news-loading"><div class="news-spinner"></div><span>Carregando comparativo...</span></div>';
    try {
        const r = await authFetch(`/transparency/compare?ids=${list.join(',')}`);
        if (!r.ok) throw new Error();
        const data = await r.json();
        const pols = data.politicians||[];
        if (!pols.length) throw new Error();

        const fields = [
            ['Cargo',           d => (d.all_roles&&d.all_roles[0])||d.role||'—'],
            ['Partido',         d => (d.all_parties&&d.all_parties[0])||d.party||'—'],
            ['País',            d => d.country||'—'],
            ['Formação',        d => d.education||'—'],
            ['Profissão anterior',d=>d.occupation||'—'],
            ['Nascimento',      d => _fmt_date(d.birth_date)||'—'],
            ['Subsídio mensal', d => d.salary_info?_fmt_brl(d.salary_info.subsidio_mensal):'—'],
            ['Total despesas',  d => { const t=(d.expenses||[]).reduce((s,e)=>s+(e.value||0),0); return t?_fmt_brl(t):'—'; }],
            ['Votações registradas', d => d.votes&&d.votes.length ? d.votes.length+'': '—'],
        ];

        const headers = pols.map((pol,i) => {
            const orig = pList[i]||{};
            return `<th class="trans-cmp-header">
                <img src="${escapeHtml(orig.photo||pol.photo||'')}" class="trans-cmp-photo"
                    onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(orig.name||'?')}&background=1a2030&color=66fcf1&size=60'">
                <div class="trans-cmp-name">${escapeHtml(orig.name||pol.full_name||pol.id)}</div>
                <div class="trans-cmp-role">${escapeHtml(orig.role||pol.role||'')}</div>
            </th>`;
        }).join('');

        const rows = fields.map(([label, fn]) =>
            `<tr><td class="trans-cmp-label">${label}</td>${pols.map(pol =>
                `<td class="trans-cmp-cell">${escapeHtml(fn(pol))}</td>`).join('')}</tr>`
        ).join('');

        container.innerHTML = `<div class="trans-profile-wrap">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                <div style="font-family:'Rajdhani';font-size:18px;color:var(--primary);font-weight:700;">⚖️ Comparativo</div>
                <button class="trans-back-btn" onclick="renderTransparencyView('search')">← Voltar</button>
            </div>
            <div style="overflow-x:auto;">
                <table class="trans-compare-table">
                    <thead><tr><th class="trans-cmp-label">Campo</th>${headers}</tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
            <button class="glass-btn" style="margin-top:16px;"
                onclick="window.__transState.compareList=[];window.__transState.comparePoliticians=[];renderTransparencyView('search');">
                ✕ Limpar comparativo</button>
        </div>`;
    } catch(e) {
        container.innerHTML = `<div class="news-empty">Erro ao carregar comparativo. <button class="glass-btn" onclick="renderTransparencyView('search')">← Voltar</button></div>`;
    }
}

// ── HOOK goView ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const _orig = window.goView;
    if (typeof _orig === 'function') {
        window.goView = function(v, btn) {
            _orig(v, btn);
            if (v === 'news') {
                const activeTab = document.querySelector('.news-main-tab.active');
                if (activeTab?.dataset?.main === 'transparency') initTransparency();
                else initNews();
            }
        };
    }
});
