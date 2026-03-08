// Safe modular facade for the existing app.js globals.
// This is a first-step refactor that does not change runtime behavior.
(function () {
  window.FGCore = Object.freeze({
    authFetch: (...args) => window.authFetch(...args),
    showToast: (...args) => window.showToast(...args),
    formatMsgTime: (...args) => window.formatMsgTime(...args),
    formatRankInfo: (...args) => window.formatRankInfo(...args),
    sanitizeChannelName: (...args) => window.sanitizeChannelName(...args),
    renderMedals: (...args) => window.renderMedals(...args),
    updateUI: (...args) => window.updateUI(...args),
    goView: (...args) => window.goView(...args),
  });
})();
