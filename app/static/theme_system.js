// ════════════════════════════════════════════════════════
//  FOR GLORY — SISTEMA DE TEMAS VIP
//  Adicionar em: /app/static/theme_system.js
//  Incluir no index.html: <script src="/static/theme_system.js" defer></script>
// ════════════════════════════════════════════════════════

(function() {
    const THEMES = {
        default:  { name: 'Padrão',              icon: '⚡', css: null },
        medieval: { name: 'Fantasia Medieval',   icon: '⚔️', css: '/static/theme_medieval.css' },
        // Futuros temas:
        // cyberpunk: { name: 'Cyberpunk',        icon: '🤖', css: '/static/theme_cyberpunk.css' },
        // nature:    { name: 'Natureza Viva',    icon: '🌿', css: '/static/theme_nature.css' },
        // noir:      { name: 'Noir Urbano',      icon: '🕵️', css: '/static/theme_noir.css' },
    };

    const STORAGE_KEY = 'fg_active_theme';
    let _activeTheme = 'default';

    // ── Aplica tema ──────────────────────────────────────
    window.applyTheme = async function(themeId) {
        if (!THEMES[themeId]) return;

        const prev = _activeTheme;
        _activeTheme = themeId;

        // Remove tema anterior
        document.documentElement.removeAttribute('data-theme');
        document.querySelectorAll('[data-theme-css]').forEach(el => el.remove());

        if (themeId !== 'default') {
            const theme = THEMES[themeId];

            // Carrega CSS se não estiver em cache
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = theme.css;
            link.setAttribute('data-theme-css', themeId);
            document.head.appendChild(link);

            await new Promise(resolve => { link.onload = resolve; link.onerror = resolve; });
            document.documentElement.setAttribute('data-theme', themeId);
        }

        localStorage.setItem(STORAGE_KEY, themeId);

        if (typeof showToast === 'function') {
            showToast(`${THEMES[themeId].icon} Tema "${THEMES[themeId].name}" ativado!`);
        }
    };

    // ── Restaura tema salvo ──────────────────────────────
    window.restoreSavedTheme = function() {
        const saved = localStorage.getItem(STORAGE_KEY) || 'default';
        if (saved !== 'default') applyTheme(saved);
    };

    // ── Lista temas disponíveis para UI ─────────────────
    window.getAvailableThemes = function() {
        return Object.entries(THEMES).map(([id, t]) => ({ id, ...t }));
    };

    // ── Restaura ao carregar ─────────────────────────────
    document.addEventListener('DOMContentLoaded', restoreSavedTheme);
})();
