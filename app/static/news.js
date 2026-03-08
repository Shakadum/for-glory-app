// ============================================================
//  FOR GLORY — NAVEGADOR DE NOTÍCIAS GEOLOCALIZADAS
//  Adicione ao final de app/static/app.js
// ============================================================

window.__newsLevel = 'city';
window.__newsLocation = null;
window.__newsCache = {};

// ── Inicializa o feed de notícias ───────────────────────────
async function initNews() {
    const view = document.getElementById('view-news');
    if (!view) return;

    // Detecta localização e mostra no header
    try {
        const r = await authFetch('/news/location');
        if (r.ok) {
            window.__newsLocation = await r.json();
            updateNewsLocationBadge();
        }
    } catch (e) {}

    // Carrega o nível padrão
    loadNews('city');
}

function updateNewsLocationBadge() {
    const loc = window.__newsLocation;
    if (!loc) return;
    const el = document.getElementById('news-location-badge');
    if (el) el.textContent = `📍 ${loc.city}, ${loc.state}`;
}

// ── Botões de zoom (cidade / estado / mundo) ────────────────
function switchNewsLevel(level) {
    window.__newsLevel = level;
    document.querySelectorAll('.news-zoom-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.level === level);
    });
    loadNews(level);
}

// ── Busca e renderiza notícias ───────────────────────────────
async function loadNews(level) {
    window.__newsLevel = level;
    const container = document.getElementById('news-cards-container');
    const statusEl  = document.getElementById('news-status');
    if (!container) return;

    // Spinner
    container.innerHTML = `
        <div class="news-loading">
            <div class="news-spinner"></div>
            <span>Buscando notícias…</span>
        </div>`;

    // Cache de 5 min por nível
    const cacheKey = level + (window.__newsCustomCity || '');
    const cached   = window.__newsCache[cacheKey];
    if (cached && Date.now() - cached.ts < 5 * 60 * 1000) {
        renderNewsCards(cached.data);
        return;
    }

    try {
        const qs  = new URLSearchParams({ level });
        if (window.__newsCustomCity) qs.set('custom_city', window.__newsCustomCity);

        const r = await authFetch(`/news?${qs}`);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const data = await r.json();

        if (!data.api_configured) {
            container.innerHTML = `
                <div class="news-empty">
                    <div style="font-size:40px; margin-bottom:12px;">🔑</div>
                    <div style="font-family:'Rajdhani'; font-size:18px; color:var(--primary); margin-bottom:8px;">API não configurada</div>
                    <div style="color:#888; font-size:13px; line-height:1.6;">
                        Adicione <code style="background:#111; padding:2px 6px; border-radius:4px; color:var(--primary);">GNEWS_API_KEY</code> 
                        ao <code style="background:#111; padding:2px 6px; border-radius:4px; color:var(--primary);">.env</code> do servidor.<br>
                        Chave gratuita em <a href="https://gnews.io" target="_blank" style="color:var(--primary);">gnews.io</a> (100 req/dia).
                    </div>
                </div>`;
            return;
        }

        // Atualiza localização exibida
        if (data.location) {
            window.__newsLocation = { ...window.__newsLocation, ...data.location };
            updateNewsLocationBadge();
        }

        window.__newsCache[cacheKey] = { data, ts: Date.now() };
        renderNewsCards(data);

    } catch (e) {
        container.innerHTML = `
            <div class="news-empty">
                <div style="font-size:40px; margin-bottom:12px;">📡</div>
                <div style="color:#888;">Erro ao carregar notícias. Tente novamente.</div>
                <button onclick="loadNews('${level}')" class="glass-btn" style="margin-top:16px; padding:8px 20px;">↺ Tentar novamente</button>
            </div>`;
    }
}

// ── Renderiza os cards ───────────────────────────────────────
function renderNewsCards(data) {
    const container = document.getElementById('news-cards-container');
    if (!container) return;

    const articles = data.articles || [];
    if (articles.length === 0) {
        container.innerHTML = `
            <div class="news-empty">
                <div style="font-size:40px; margin-bottom:12px;">📭</div>
                <div style="color:#888;">Nenhuma notícia encontrada para esta região.</div>
            </div>`;
        return;
    }

    // Destaque (primeiro artigo com imagem)
    const featured  = articles.find(a => a.image) || articles[0];
    const remaining = articles.filter(a => a !== featured);

    const categoryColors = {
        'cidade':     '#66fcf1',
        'estado':     '#45b7d1',
        'nacional':   '#4ecdc4',
        'geopolítica':'#ff6b6b',
        'economia':   '#ffd93d',
        'tecnologia': '#c678dd',
        'mundo':      '#ff9f43',
    };

    const catColor = c => categoryColors[c] || '#888';

    const featuredHtml = `
        <a href="${escapeHtml(featured.url)}" target="_blank" rel="noopener" class="news-card-featured">
            ${featured.image ? `<img src="${escapeHtml(featured.image)}" class="news-card-featured-img" onerror="this.style.display='none'">` : ''}
            <div class="news-card-featured-overlay">
                <span class="news-cat-badge" style="background:${catColor(featured.category)}20; color:${catColor(featured.category)}; border-color:${catColor(featured.category)}40;">${featured.category.toUpperCase()}</span>
                <div class="news-card-featured-title">${escapeHtml(featured.title)}</div>
                <div class="news-card-featured-meta">
                    <span>${escapeHtml(featured.source)}</span>
                    <span>·</span>
                    <span>${escapeHtml(featured.published_at)}</span>
                </div>
            </div>
        </a>`;

    const cardsHtml = remaining.map(a => `
        <a href="${escapeHtml(a.url)}" target="_blank" rel="noopener" class="news-card">
            ${a.image ? `<img src="${escapeHtml(a.image)}" class="news-card-img" onerror="this.style.display='none'">` : ''}
            <div class="news-card-body">
                <span class="news-cat-badge" style="background:${catColor(a.category)}20; color:${catColor(a.category)}; border-color:${catColor(a.category)}40;">${a.category.toUpperCase()}</span>
                <div class="news-card-title">${escapeHtml(a.title)}</div>
                ${a.description ? `<div class="news-card-desc">${escapeHtml(a.description.slice(0, 100))}…</div>` : ''}
                <div class="news-card-meta">
                    <span>${escapeHtml(a.source)}</span>
                    <span>·</span>
                    <span>${escapeHtml(a.published_at)}</span>
                </div>
            </div>
        </a>`).join('');

    container.innerHTML = featuredHtml + `<div class="news-grid">${cardsHtml}</div>`;
}

// ── Viagem de mapa: ver notícias de outra cidade ─────────────
function openNewsTravel() {
    const modal = document.getElementById('modal-news-travel');
    if (modal) {
        modal.classList.remove('hidden');
        document.getElementById('news-travel-input').focus();
    }
}

function applyNewsTravel() {
    const val = (document.getElementById('news-travel-input').value || '').trim();
    window.__newsCustomCity = val || null;
    document.getElementById('modal-news-travel').classList.add('hidden');

    const badge = document.getElementById('news-location-badge');
    if (badge) badge.textContent = val ? `📍 ${val} (manual)` : `📍 ${window.__newsLocation?.city || ''}`;

    // Limpa cache do nível atual
    delete window.__newsCache['city' + (val || '')];
    loadNews('city');
}

// ── goView hook: patch app.js's goView to also init news ───
// (called once after app.js loads)
document.addEventListener('DOMContentLoaded', () => {
    const _orig = window.goView;
    if (typeof _orig === 'function') {
        window.goView = function(v, btn) {
            _orig(v, btn);
            if (v === 'news') initNews();
        };
    }
});
