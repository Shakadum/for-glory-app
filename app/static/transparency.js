// ============================================================
//  FOR GLORY — PORTAL DA TRANSPARÊNCIA v4
// ============================================================
window.__transState = {
    tab:'search', politician:null, compareList:[], comparePoliticians:[],
    country:'BR', currentRating:0, localData:null,
};

// ── INIT ─────────────────────────────────────────────────────
async function initTransparency() {
    renderTransparencyView('search');
    loadLocalPanel();
}

// ── TABS ──────────────────────────────────────────────────────
function renderTransparencyView(tab) {
    window.__transState.tab = tab;
    document.querySelectorAll('.trans-tab-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.tab === tab));
    const container = document.getElementById('trans-content');
    if (!container) return;
    if (tab === 'search')       renderSearchView(container);
    else if (tab === 'profile') { if(window.__transState.politician) openPolitician(window.__transState.politician); else renderSearchView(container); }
    else if (tab === 'compare') renderCompareView(container);
}

// ── SEARCH VIEW ───────────────────────────────────────────────
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
        <div id="trans-results" class="trans-results-list"></div>
        <div id="trans-local-panel"></div>`;

    // Re-inject cached local data if available
    if (window.__transState.localData) {
        renderLocalPanelData(window.__transState.localData);
    } else {
        document.getElementById('trans-local-panel').innerHTML =
            '<div class="news-loading" style="margin:24px auto;"><div class="news-spinner"></div><span>Carregando seus representantes...</span></div>';
    }
}

function setTransCountry(cc) {
    window.__transState.country = cc;
    document.querySelectorAll('.trans-chip').forEach(b =>
        b.classList.toggle('active', b.textContent.trim()===cc));
}

async function doTransSearch() {
    const q = (document.getElementById('trans-search-input')?.value||'').trim();
    if (!q) return;
    const results = document.getElementById('trans-results');
    if (!results) return;
    results.innerHTML = '<div class="news-loading"><div class="news-spinner"></div><span>Buscando políticos...</span></div>';
    document.getElementById('trans-local-panel').style.display = 'none';
    try {
        const r = await authFetch(`/transparency/search?q=${encodeURIComponent(q)}&country=${window.__transState.country}`);
        if (!r.ok) throw new Error();
        const data = await r.json();
        const list = data.results||[];
        if (!list.length) {
            results.innerHTML = '<div class="news-empty"><div style="font-size:32px;margin-bottom:8px;">🔍</div>Nenhum político encontrado.</div>';
        } else {
            results.innerHTML = `
                <div class="trans-results-header">
                    <span style="color:#66fcf1;font-family:\'Rajdhani\';font-weight:700;">${list.length} resultado${list.length!==1?'s':''} para "${escapeHtml(q)}"</span>
                    <button class="glass-btn" style="padding:4px 10px;font-size:11px;" onclick="clearTransSearch()">✕ Limpar</button>
                </div>
                ${list.map(p=>politicianCard(p)).join('')}`;
        }
    } catch(e) {
        results.innerHTML = '<div class="news-empty">Erro ao buscar. Tente novamente.</div>';
    }
}

function clearTransSearch() {
    const results = document.getElementById('trans-results');
    const panel   = document.getElementById('trans-local-panel');
    if (results) results.innerHTML = '';
    if (panel)   panel.style.display = '';
    const inp = document.getElementById('trans-search-input');
    if (inp) inp.value = '';
}

// ── LOCAL PANEL LOADER ────────────────────────────────────────
async function loadLocalPanel() {
    try {
        const r = await authFetch('/transparency/local');
        if (!r.ok) throw new Error();
        const data = await r.json();
        window.__transState.localData = data;
        renderLocalPanelData(data);
    } catch(e) {
        const el = document.getElementById('trans-local-panel');
        if (el) el.innerHTML = '<div class="news-empty" style="padding:20px 0;">Não foi possível carregar representantes locais.</div>';
    }
}

function renderLocalPanelData(data) {
    const el = document.getElementById('trans-local-panel');
    if (!el) return;

    const loc = data.location || {};
    const sections = data.sections || [];

    const allUFs = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SE','SP','TO'];
    const ufNames = {AC:'Acre',AL:'Alagoas',AP:'Amapá',AM:'Amazonas',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MT:'Mato Grosso',MS:'Mato Grosso do Sul',MG:'Minas Gerais',PA:'Pará',PB:'Paraíba',PR:'Paraná',PE:'Pernambuco',PI:'Piauí',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RS:'Rio Grande do Sul',RO:'Rondônia',RR:'Roraima',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};
    const detectedCity = loc.city||'';
    const detectedState = loc.state_full||loc.state||'';

    el.innerHTML = `
        <!-- LOCATION BANNER -->
        <div class="trans-location-banner">
            <div class="trans-location-icon">📍</div>
            <div style="flex:1;min-width:0;">
                <div class="trans-location-title">Seus Representantes</div>
                <div class="trans-location-sub" id="trans-loc-display">
                    📌 ${escapeHtml(detectedState||loc.uf||'')} · ${escapeHtml(loc.country||'Brasil')}
                    ${detectedCity ? `<span style="color:#4b5563;font-size:10px;margin-left:6px;">IP aponta para ${escapeHtml(detectedCity)} — ajuste se estiver errado</span>` : ''}
                </div>
                <!-- Override row -->
                <div class="trans-loc-override" id="trans-loc-override" style="display:none;margin-top:8px;gap:6px;flex-wrap:wrap;">
                    <span style="color:#9ca3af;font-size:11px;align-self:center;">Selecionar estado:</span>
                    <select id="trans-uf-select" class="gs-input" style="padding:4px 8px;font-size:12px;width:auto;flex:0;">
                        ${allUFs.map(u => `<option value="${u}" ${u===loc.uf?'selected':''}>${u} — ${ufNames[u]||u}</option>`).join('')}
                    </select>
                    <button class="btn-main" style="margin:0;padding:5px 14px;font-size:12px;" onclick="applyUFOverride()">Aplicar</button>
                    <button class="glass-btn" style="padding:5px 10px;font-size:11px;" onclick="document.getElementById('trans-loc-override').style.display='none'">✕</button>
                </div>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0;margin-left:8px;">
                <button class="glass-btn" style="padding:5px 10px;font-size:11px;"
                    onclick="toggleLocOverride()" title="Corrigir estado">✏️ Corrigir</button>
                <button class="glass-btn" style="padding:5px 10px;font-size:11px;"
                    onclick="loadLocalPanel()" title="Atualizar">↺</button>
            </div>
        </div>

        <!-- SECTIONS -->
        ${sections.map(s => renderSection(s)).join('')}
    `;
}

function renderSection(s) {
    const pols = s.politicians || [];
    if (!pols.length) return '';
    
    const isBig  = s.id === 'executivo';
    const is3col = s.id === 'deputados' || s.id === 'stf';

    return `
        <div class="trans-local-section">
            <div class="trans-local-section-header" style="border-left-color:${s.color};">
                <div>
                    <div class="trans-local-section-title" style="color:${s.color};">${s.title}</div>
                    <div class="trans-local-section-sub">${escapeHtml(s.subtitle||'')}</div>
                </div>
                <div class="trans-local-count" style="background:${s.color}20;color:${s.color};">${pols.length}</div>
            </div>
            <div class="${isBig ? 'trans-exec-row' : is3col ? 'trans-grid-3col' : 'trans-grid-wrap'}">
                ${pols.map(p => isBig ? renderExecCard(p, s.color) : renderMiniCard(p, s.color)).join('')}
            </div>
        </div>`;
}

// Big card for president/vp
function renderExecCard(p, color) {
    const inCmp = window.__transState.compareList.includes(p.id);
    const pJson = JSON.stringify(p).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');
    return `
        <div class="trans-exec-card" onclick='openPolitician(${pJson})'
            style="--accent:${color};">
            <div class="trans-exec-photo-wrap">
                <img src="${escapeHtml(p.photo||'')}" class="trans-exec-photo"
                    onerror="this.onerror=null;this.src='https://ui-avatars.com/api/?name='+encodeURIComponent((p.name||'?').split(' ').slice(-2).join('+'))+'&background=131820&color='+('${color}'.replace('#',''))+'&bold=true&size=160'">
                <div class="trans-exec-overlay"></div>
                ${p.highlight ? '<div class="trans-exec-badge">👑 Presidente</div>' : ''}
            </div>
            <div class="trans-exec-info">
                <div class="trans-exec-name">${escapeHtml(p.name||'')}</div>
                <div class="trans-exec-role">${escapeHtml(p.role||'')}</div>
                ${p.party ? `<span class="trans-exec-party" style="background:${color}18;border-color:${color}40;color:${color};">${escapeHtml(p.party)}</span>` : ''}
                <div class="trans-exec-actions">
                    <button class="trans-exec-btn" onclick="event.stopPropagation();openPolitician(${pJson})">Ver Ficha</button>
                    <button class="trans-cmp-sm ${inCmp?'active':''}"
                        onclick="event.stopPropagation();toggleCompare(${pJson})"
                        title="Adicionar ao comparativo">${inCmp?'✓':'+Compare'}</button>
                </div>
            </div>
        </div>`;
}

// Compact card for deputies/senators/ministers
function renderMiniCard(p, color) {
    const inCmp = window.__transState.compareList.includes(p.id);
    const pJson = JSON.stringify(p).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');
    return `
        <div class="trans-mini-card" onclick='openPolitician(${pJson})'
            style="--accent:${color};">
            <img src="${escapeHtml(p.photo||'')}" class="trans-mini-photo"
                onerror="this.onerror=null;this.src='https://ui-avatars.com/api/?name='+encodeURIComponent((p.name||'?').split(' ').slice(-2).join('+'))+'&background=131820&color='+('${color}'.replace('#',''))+'&bold=true&size=80'">
            <div class="trans-mini-info">
                <div class="trans-mini-name">${escapeHtml(p.name||'')}</div>
                ${p.party ? `<span class="trans-mini-party" style="color:${color};">${escapeHtml(p.party)}</span>` : ''}
                ${p.state ? `<span class="trans-mini-state">${escapeHtml(p.state)}</span>` : ''}
            </div>
            <button class="trans-mini-cmp ${inCmp?'active':''}"
                style="color:${inCmp?color:'#4b5563'};border-color:${inCmp?color:'rgba(255,255,255,0.1)'};"
                onclick="event.stopPropagation();toggleCompare(${pJson})">${inCmp?'✓':'+'}</button>
        </div>`;
}

// ── POLITICIAN CARD (search results) ─────────────────────────
function politicianCard(p) {
    const inCmp = window.__transState.compareList.includes(p.id);
    const srcColor = {camara:'#66fcf1',senado:'#ffd93d',wikidata:'#c678dd'}[p.source]||'#888';
    const pJson = JSON.stringify(p).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');
    return `
    <div class="trans-card" onclick='openPolitician(${pJson})'>
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
            <button class="trans-compare-btn ${inCmp?'active':''}"
                onclick="event.stopPropagation();toggleCompare(${pJson})"
                title="${inCmp?'Remover':'Adicionar ao comparativo'}">${inCmp?'✓':'+'}</button>
        </div>
    </div>`;
}

// ── PROFILE ───────────────────────────────────────────────────
async function openPolitician(p) {
    window.__transState.politician = p;
    document.querySelectorAll('.trans-tab-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.tab==='profile'));
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

function _stars(n,max=5){n=Math.round(n||0);return '<span style="color:#ffd93d;letter-spacing:2px;">'+'★'.repeat(n)+'☆'.repeat(max-n)+'</span>';}
function _fmt_brl(v){return 'R$ '+Number(v||0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});}
function _fmt_date(s){if(!s)return '';try{return new Date(s+'T00:00:00').toLocaleDateString('pt-BR');}catch{return s;}}

function renderProfile(p, d, container) {
    const r=d.community_rating||{}, sal=d.salary_info, inCmp=window.__transState.compareList.includes(p.id);
    const pJson=JSON.stringify(p).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');

    const bioHtml = d.bio ? `<div class="trans-section"><div class="trans-section-label">📖 Biografia</div><p style="color:#9ca3af;font-size:13px;line-height:1.75;margin:0;">${escapeHtml(d.bio)}</p>${d.wiki_link?`<a href="${escapeHtml(d.wiki_link)}" target="_blank" class="trans-source-link">Leia mais na Wikipedia ↗</a>`:''}</div>` : '';

    const fields=[['Nome completo',d.full_name||p.name],['Nascimento',_fmt_date(d.birth_date)],['Local',d.birth_place],['País',d.country||p.country],['Partido(s)',(d.all_parties||[d.party||p.party]).filter(Boolean).join(' • ')],['Formação',(d.all_education||[d.education]).filter(Boolean).join(' • ')],['Profissão anterior',d.occupation],['E-mail',d.email],].filter(([,v])=>v);
    const dadosHtml = fields.length ? `<div class="trans-section"><div class="trans-section-label">📋 Dados Pessoais</div><div class="trans-data-grid">${fields.map(([k,v])=>`<div class="trans-data-item"><span class="trans-data-label">${k}</span><span class="trans-data-value">${v}</span></div>`).join('')}</div></div>` : '';

    const allRoles=d.all_roles||(d.role?[d.role]:[]);
    const cargosHtml=allRoles.length?`<div class="trans-section"><div class="trans-section-label">🏛️ Cargos Exercidos</div>${allRoles.map(r2=>`<div class="trans-row"><span style="color:#c5c6c7;font-size:13px;">• ${escapeHtml(r2)}</span></div>`).join('')}</div>` : '';

    const salHtml=sal?`<div class="trans-section"><div class="trans-section-label">💰 Salário e Benefícios</div><div class="trans-salary-hero"><div class="trans-salary-value">${_fmt_brl(sal.subsidio_mensal)}<span style="font-size:12px;color:#9ca3af;font-weight:400;">/mês</span></div><div class="trans-salary-desc">${escapeHtml(sal.subsidio_desc)}</div></div>${(sal.beneficios||[]).map(b=>`<div class="trans-benefit-row"><div style="flex:1;"><div style="color:#c5c6c7;font-size:13px;font-weight:600;">${escapeHtml(b.nome)}</div><div style="color:#6b7280;font-size:11px;margin-top:2px;">${escapeHtml(b.descricao)}</div></div><div style="color:#ffd93d;font-size:12px;font-weight:700;white-space:nowrap;margin-left:12px;">${escapeHtml(b.valor)}</div></div>`).join('')}<div class="trans-benefit-waiver">ℹ️ ${escapeHtml(sal.beneficios_abdicados_info||'')}</div><a href="${escapeHtml(sal.fonte||'')}" target="_blank" class="trans-source-link">Fonte: Portal da Transparência ↗</a></div>` : '';

    const expenses=d.expenses||[], totalDesp=expenses.reduce((s,e)=>s+(e.value||0),0);
    const despHtml=`<div class="trans-section"><div class="trans-section-label" style="display:flex;justify-content:space-between;""><span>🧾 Despesas Declaradas</span>${totalDesp?`<span style="color:#ffd93d;font-size:12px;">${_fmt_brl(totalDesp)}</span>`:''}</div>${expenses.length?expenses.map(e=>`<div class="trans-row"><div style="flex:1;min-width:0;"><div style="color:#c5c6c7;font-size:12px;font-weight:600;">${escapeHtml(e.description||'')}</div><div style="color:#6b7280;font-size:11px;">${escapeHtml(e.provider||'')}</div></div><div style="text-align:right;flex-shrink:0;margin-left:8px;"><div style="color:#ffd93d;font-weight:700;font-size:12px;">${_fmt_brl(e.value)}</div><div style="color:#4b5563;font-size:10px;">${escapeHtml(e.date||'')}</div></div></div>`).join(''):'<div style="color:#6b7280;font-size:13px;padding:8px 0;">Sem despesas registradas para este cargo.</div>'}</div>`;

    const votes=d.votes||[];
    const vIcon=v=>{const vv=(v||'').toLowerCase();if(vv==='sim'||vv==='yes')return '<span style="color:#2ecc71;font-weight:600;">✅ Sim</span>';if(vv==='não'||vv==='nao'||vv==='no')return '<span style="color:#ff5555;font-weight:600;">❌ Não</span>';if(vv.includes('abst'))return '<span style="color:#ffd93d;font-weight:600;">⬜ Abstenção</span>';if(vv==='obstrução'||vv.includes('obstru'))return '<span style="color:#c678dd;font-weight:600;">🚫 Obstrução</span>';return v?`<span style="color:#9ca3af;">${escapeHtml(v)}</span>`:''};
    // Executivo: mostra ações em vez de votações
    const execActions = d.executive_actions || [];
    const votHtml = execActions.length ? `
        <div class="trans-section">
            <div class="trans-section-label">📜 Ações do Executivo Federal</div>
            <div style="color:#6b7280;font-size:11px;margin-bottom:10px;">Medidas Provisórias, Projetos de Lei e Mensagens ao Congresso enviadas pelo Executivo</div>
            ${execActions.map(a=>`
                <div class="trans-row" style="align-items:flex-start;gap:10px;">
                    <div style="flex-shrink:0;">
                        <span class="trans-meta-chip" style="background:rgba(255,211,61,0.1);border-color:rgba(255,211,61,0.3);color:#ffd93d;font-weight:700;">${escapeHtml(a.sigla||'')}</span>
                    </div>
                    <div style="flex:1;min-width:0;">
                        <div style="color:#9ca3af;font-size:10px;font-weight:600;letter-spacing:0.5px;">${escapeHtml(a.type||'')}</div>
                        <div style="color:#c5c6c7;font-size:12px;line-height:1.5;margin-top:2px;">${escapeHtml((a.description||'').substring(0,200))}</div>
                        <div style="color:#4b5563;font-size:10px;margin-top:2px;">${escapeHtml(a.numero||'')} · ${escapeHtml(a.date||'')}</div>
                    </div>
                </div>`).join('')}
            ${d.actions_source ? `<div style="margin-top:8px;"><a href="https://dadosabertos.camara.leg.br" target="_blank" class="trans-source-link">Fonte: ${escapeHtml(d.actions_source)} ↗</a></div>` : ''}
        </div>` :
        `<div class="trans-section"><div class="trans-section-label">🗳️ Votações Recentes</div>${votes.length?votes.map(v=>`<div class="trans-row" style="align-items:flex-start;gap:10px;"><div style="flex:1;min-width:0;"><div style="color:#c5c6c7;font-size:12px;line-height:1.5;">${escapeHtml(v.description||'Votação sem descrição registrada')}</div><div style="color:#4b5563;font-size:10px;margin-top:2px;">${escapeHtml(v.date||'')}</div></div><div style="flex-shrink:0;font-size:12px;">${vIcon(v.vote)}</div></div>`).join(''):'<div style="color:#6b7280;font-size:13px;padding:8px 0;">Sem votações registradas. Isso pode ocorrer para cargos do Executivo (Presidente, Governadores) e do Judiciário (STF), que não votam no Congresso Nacional.</div>'}</div>`;

    const charges=d.charges||[];
    const chargesHtml=`<div class="trans-section"><div class="trans-section-label">⚖️ Casos na Justiça</div><div class="trans-legal-notice">⚠️ Dados de fontes públicas oficiais. Processos em andamento não implicam condenação (Lei 12.527/2011).</div>${charges.length?charges.map(c=>`<div class="trans-row"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ff6b6b" stroke-width="2" style="flex-shrink:0;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg><span style="color:#fca5a5;font-size:13px;">${escapeHtml(c)}</span></div>`).join(''):'<div style="color:#6b7280;font-size:13px;padding:8px 0;">Nenhum processo criminal registrado em fontes públicas consultadas.</div>'}</div>`;

    const avgR=r.average;
    const ratingHtml=`<div class="trans-section"><div class="trans-section-label">⭐ Avaliação da Comunidade</div>${avgR?`<div class="trans-rating-summary"><div class="trans-rating-big-score">${avgR}</div><div>${_stars(avgR)}<div style="color:#6b7280;font-size:12px;margin-top:4px;">${r.count} avaliação${r.count!==1?'ões':''}</div></div></div>`:'<div style="color:#6b7280;font-size:13px;margin-bottom:12px;">Seja o primeiro a avaliar!</div>'}<div class="trans-rating-widget" id="trans-rating-widget-${p.id}"><div style="color:#9ca3af;font-size:12px;margin-bottom:10px;">Sua avaliação:</div><div class="trans-stars-input" id="trans-stars-${p.id}">${[1,2,3,4,5].map(n=>`<span class="trans-star" data-val="${n}" onmouseover="hoverRatingStar('${escapeHtml(p.id)}',${n})" onmouseout="unhoverRatingStar('${escapeHtml(p.id)}')" onclick="setRatingStar('${escapeHtml(p.id)}',${n})">☆</span>`).join('')}</div><textarea id="trans-rating-comment-${p.id}" placeholder="Comentário público sobre a atuação deste político (opcional)..." style="width:100%;box-sizing:border-box;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:8px;color:#c5c6c7;padding:10px;font-family:\'DM Sans\';font-size:13px;resize:none;height:80px;margin-top:10px;outline:none;"></textarea><button class="btn-main" style="margin-top:8px;padding:8px 20px;" onclick="submitRating('${escapeHtml(p.id)}')">📤 Enviar Avaliação</button></div>${(r.comments||[]).length?`<div class="trans-section-label" style="margin-top:16px;font-size:11px;">AVALIAÇÕES RECENTES</div><div class="trans-comments-list">${r.comments.map(c=>`<div class="trans-comment"><div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">${_stars(c.score)}<span style="color:#4b5563;font-size:11px;">${escapeHtml(c.date)}</span></div>${c.comment?`<div style="color:#9ca3af;font-size:12px;margin-top:4px;">"${escapeHtml(c.comment)}"</div>`:''}</div>`).join('')}</div>`:''}</div>`;

    container.innerHTML=`<div class="trans-profile-wrap">
        <button class="trans-back-btn" onclick="renderTransparencyView('search')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg> Voltar
        </button>
        <div class="trans-profile-hero">
            <img src="${escapeHtml(d.photo||p.photo||'')}" class="trans-profile-photo"
                onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(p.name||'?')}&background=1a2030&color=66fcf1&size=120'">
            <div class="trans-profile-hero-info" style="flex:1;min-width:0;">
                <div class="trans-profile-name">${escapeHtml(d.full_name||p.name||'')}</div>
                <div class="trans-profile-role">${escapeHtml(d.role||p.role||d.description||'')}</div>
                <div class="trans-card-meta" style="margin-top:6px;flex-wrap:wrap;">
                    ${((d.all_parties&&d.all_parties.length?d.all_parties:[d.party||p.party]).filter(Boolean)).map(pt=>`<span class="trans-meta-chip">${escapeHtml(pt)}</span>`).join('')}
                    ${(d.state||p.state)?`<span class="trans-meta-chip">${escapeHtml(d.state||p.state)}</span>`:''}
                    ${(d.country||p.country)?`<span class="trans-meta-chip">🌍 ${escapeHtml(d.country||p.country)}</span>`:''}
                </div>
                ${avgR?`<div style="margin-top:8px;display:flex;align-items:center;gap:8px;">${_stars(avgR)}<span style="color:#ffd93d;font-weight:700;">${avgR}</span><span style="color:#6b7280;font-size:12px;">(${r.count})</span></div>`:''}
            </div>
            <button class="trans-compare-btn-lg ${inCmp?'active':''}" onclick="toggleCompare(${pJson})">${inCmp?'✓ No comparativo':'+ Comparar'}</button>
        </div>
        ${bioHtml}${dadosHtml}${cargosHtml}${salHtml}${despHtml}${votHtml}${chargesHtml}${ratingHtml}
    </div>`;
    window.__transState.currentRating = 0;
}

// ── RATING ────────────────────────────────────────────────────
function hoverRatingStar(pid,val){if(window.__transState.currentRating>0)return;document.querySelectorAll(`#trans-stars-${CSS.escape(pid)} .trans-star`).forEach((s,i)=>{s.textContent=i<val?'★':'☆';s.style.color=i<val?'#ffd93d':'#4b5563';});}
function unhoverRatingStar(pid){const c=window.__transState.currentRating;document.querySelectorAll(`#trans-stars-${CSS.escape(pid)} .trans-star`).forEach((s,i)=>{s.textContent=i<c?'★':'☆';s.style.color=i<c?'#ffd93d':'#4b5563';});}
function setRatingStar(pid,val){window.__transState.currentRating=val;document.querySelectorAll(`#trans-stars-${CSS.escape(pid)} .trans-star`).forEach((s,i)=>{s.textContent=i<val?'★':'☆';s.style.color=i<val?'#ffd93d':'#4b5563';});}
async function submitRating(pid){
    const score=window.__transState.currentRating;
    if(!score){showToast('⭐ Selecione uma nota de 1 a 5!');return;}
    const comment=(document.getElementById(`trans-rating-comment-${pid}`)?.value||'').trim();
    try{
        const r=await authFetch('/transparency/rate',{method:'POST',body:JSON.stringify({politician_id:pid,user_id:user.id,score,comment})});
        if(!r.ok)throw new Error();
        const data=await r.json();
        if(data.error){showToast('Erro: '+data.error);return;}
        showToast('✅ Avaliação enviada! Obrigado por fiscalizar.');
        const w=document.getElementById(`trans-rating-widget-${pid}`);
        if(w)w.innerHTML=`<div style="background:rgba(102,252,241,0.08);border:1px solid rgba(102,252,241,0.2);border-radius:10px;padding:14px;text-align:center;"><div>${_stars(score)}</div><div style="color:#66fcf1;font-family:'Rajdhani';font-size:16px;margin-top:6px;">Avaliação registrada!</div><div style="color:#6b7280;font-size:12px;margin-top:4px;">Média atual: ${data.new_average} ⭐ (${data.count} avaliações)</div></div>`;
    }catch(e){showToast('Erro ao enviar avaliação.');}
}

// ── COMPARE ───────────────────────────────────────────────────
function toggleCompare(p){
    const list=window.__transState.compareList,pList=window.__transState.comparePoliticians;
    const idx=list.indexOf(p.id);
    if(idx>=0){list.splice(idx,1);pList.splice(idx,1);}
    else{if(list.length>=4){showToast('Máximo 4 políticos.');return;}list.push(p.id);pList.push(p);}
    ['trans-compare-badge','trans-compare-count'].forEach(id=>{const b=document.getElementById(id);if(b){b.textContent=list.length||'';b.style.display=list.length?'flex':'none';}});
    showToast(idx>=0?`✗ ${p.name} removido`:`✓ ${p.name} adicionado`);
}

async function renderCompareView(container){
    const list=window.__transState.compareList,pList=window.__transState.comparePoliticians;
    if(list.length<2){container.innerHTML=`<div class="news-empty" style="padding:60px 20px;"><div style="font-size:40px;margin-bottom:16px;">⚖️</div><div style="font-family:'Rajdhani';font-size:18px;color:var(--primary);margin-bottom:8px;">Comparativo de Políticos</div><div style="color:#6b7280;font-size:13px;">Adicione ao menos 2 políticos com o botão <strong style="color:#c5c6c7;">+</strong>.</div><button class="glass-btn" style="margin-top:20px;" onclick="renderTransparencyView('search')">← Buscar</button></div>`;return;}
    container.innerHTML='<div class="news-loading"><div class="news-spinner"></div><span>Carregando comparativo...</span></div>';
    try{
        const r=await authFetch(`/transparency/compare?ids=${list.join(',')}`);
        if(!r.ok)throw new Error();
        const data=await r.json(); const pols=data.politicians||[];
        if(!pols.length)throw new Error();
        const fields=[['Cargo',d=>(d.all_roles&&d.all_roles[0])||d.role||'—'],['Partido',d=>(d.all_parties&&d.all_parties[0])||d.party||'—'],['País',d=>d.country||'—'],['Formação',d=>d.education||'—'],['Profissão ant.',d=>d.occupation||'—'],['Nascimento',d=>_fmt_date(d.birth_date)||'—'],['Subsídio/mês',d=>d.salary_info?_fmt_brl(d.salary_info.subsidio_mensal):'—'],['Total despesas',d=>{const t=(d.expenses||[]).reduce((s,e)=>s+(e.value||0),0);return t?_fmt_brl(t):'—';}],['Votações',d=>d.votes&&d.votes.length?d.votes.length+'':'—']];
        const headers=pols.map((pol,i)=>{const o=pList[i]||{};return `<th class="trans-cmp-header"><img src="${escapeHtml(o.photo||pol.photo||'')}" class="trans-cmp-photo" onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(o.name||'?')}&background=1a2030&color=66fcf1&size=60'"><div class="trans-cmp-name">${escapeHtml(o.name||pol.full_name||pol.id)}</div><div class="trans-cmp-role">${escapeHtml(o.role||pol.role||'')}</div></th>`;}).join('');
        const rows=fields.map(([label,fn])=>`<tr><td class="trans-cmp-label">${label}</td>${pols.map(pol=>`<td class="trans-cmp-cell">${escapeHtml(fn(pol))}</td>`).join('')}</tr>`).join('');
        container.innerHTML=`<div class="trans-profile-wrap"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;"><div style="font-family:'Rajdhani';font-size:18px;color:var(--primary);font-weight:700;">⚖️ Comparativo</div><button class="trans-back-btn" onclick="renderTransparencyView('search')">← Voltar</button></div><div style="overflow-x:auto;"><table class="trans-compare-table"><thead><tr><th class="trans-cmp-label">Campo</th>${headers}</tr></thead><tbody>${rows}</tbody></table></div><button class="glass-btn" style="margin-top:16px;" onclick="window.__transState.compareList=[];window.__transState.comparePoliticians=[];renderTransparencyView('search');">✕ Limpar comparativo</button></div>`;
    }catch(e){container.innerHTML=`<div class="news-empty">Erro. <button class="glass-btn" onclick="renderTransparencyView('search')">← Voltar</button></div>`;}
}

// ── LOCATION OVERRIDE ─────────────────────────────────────────
function toggleLocOverride() {
    const el = document.getElementById('trans-loc-override');
    if (el) el.style.display = el.style.display === 'none' ? 'flex' : 'none';
}
async function applyUFOverride() {
    const uf = document.getElementById('trans-uf-select')?.value;
    if (!uf) return;
    const el = document.getElementById('trans-local-panel');
    if (el) el.innerHTML = '<div class="news-loading" style="margin:24px auto;"><div class="news-spinner"></div><span>Carregando representantes de '+uf+'...</span></div>';
    try {
        const r = await authFetch(`/transparency/local?uf_override=${uf}`);
        if (!r.ok) throw new Error();
        const data = await r.json();
        window.__transState.localData = data;
        renderLocalPanelData(data);
    } catch(e) {
        showToast('Erro ao carregar representantes.');
    }
}

// ── HOOK ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded',()=>{
    const _orig=window.goView;
    if(typeof _orig==='function'){
        window.goView=function(v,btn){
            _orig(v,btn);
            if(v==='news'){const t=document.querySelector('.news-main-tab.active');if(t?.dataset?.main==='transparency')initTransparency();else initNews();}
        };
    }
});
