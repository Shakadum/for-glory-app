// ═══════════════════════════════════════════════════════════════
// FOR GLORY — app.js  (LOADER)
// Este arquivo é apenas o ponto de entrada.
// Toda a lógica foi modularizada em app/static/js/
//
// Ordem de carregamento (definida no index.html via <script>):
//   1. js/core.js        — globals, i18n, authFetch, WebSocket, goView
//   2. js/misc.js        — formatadores, emoji, sanitize, diagnóstico
//   3. js/auth.js        — login, register, reset de senha
//   4. js/call.js        — Agora RTC, painel de chamada, botão flutuante
//   5. js/feed.js        — posts, likes, comentários, histórico, gravação
//   6. js/inbox.js       — DMs, grupos, status online, typing indicator
//   7. js/communities.js — bases, canais, membros, admin
//   8. js/profile.js     — perfil público/privado, busca, edição
//   9. js/quiz.js        — quizzes, glory, ranking
//  10. js/vip.js         — planos VIP, assinatura, glory multiplier
//  11. transparency.js   — portal da transparência (já existia separado)
//  12. news.js           — notícias (já existia separado)
//  13. app.js            — este arquivo (inicialização mínima)
// ═══════════════════════════════════════════════════════════════

// Nada a fazer aqui — o DOMContentLoaded está em core.js
// Este arquivo existe para compatibilidade com scripts que referenciem app.js

if (typeof window !== 'undefined') {
    window.__appVersion = '2.0.0-modular';
    window.__appModules = [
        'core','misc','auth','call','feed',
        'inbox','communities','profile','quiz','vip'
    ];
    console.log('[ForGlory] App modular v2.0 carregado.');
}
