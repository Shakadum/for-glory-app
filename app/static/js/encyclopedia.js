/**
 * ForGlory — Enciclopédia Viva
 * UI: trust score, sugestões, moderação, histórico
 */

/* ── Renderiza o bloco de Trust Score na ficha ─────────────────────────── */
async function loadTrustScore(politicianId, container) {
  try {
    const r = await authFetch(`/transparency/politician/${politicianId}/trust`);
    const d = await r.json();
    const bar = Math.round(d.score || 50);
    const barColor = d.color || '#888';
    container.innerHTML = `
      <div class="trust-block" style="margin:12px 0;padding:12px;background:rgba(0,0,0,0.3);border-radius:10px;border:1px solid #333;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <span style="color:var(--primary);font-weight:bold;font-size:13px;">🔍 Confiabilidade</span>
          <span style="color:${barColor};font-weight:bold;font-size:14px;">${d.label} — ${bar}/100</span>
        </div>
        <div style="width:100%;height:8px;background:#222;border-radius:4px;overflow:hidden;">
          <div style="width:${bar}%;height:100%;background:${barColor};border-radius:4px;transition:width 0.5s;"></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:8px;font-size:11px;color:#888;">
          <span>📎 Fontes: ${d.details?.fontes ?? '-'}</span>
          <span>👥 Comunidade: ${d.details?.comunidade ?? '-'}</span>
          <span>📋 Completude: ${d.details?.completude ?? '-'}</span>
        </div>
        ${d.edits ? `<div style="font-size:11px;color:#666;margin-top:4px;">✅ ${d.edits.aprovadas} edições aprovadas · ❌ ${d.edits.rejeitadas} rejeitadas</div>` : ''}
      </div>`;
  } catch(e) { container.innerHTML = ''; }
}

/* ── Lista sugestões da comunidade ─────────────────────────────────────── */
async function loadEdits(politicianId, container, user) {
  try {
    const r = await fetch(`/transparency/politician/${politicianId}/edits`);
    const d = await r.json();
    const edits = d.edits || [];
    if (!edits.length) {
      container.innerHTML = `<p style="color:#666;font-size:13px;text-align:center;padding:10px;">Nenhuma sugestão ainda. Seja o primeiro!</p>`;
      return;
    }
    container.innerHTML = edits.map(e => {
      const statusBadge = {
        pending: '<span style="color:#f59e0b;font-size:11px;">⏳ Pendente</span>',
        approved: '<span style="color:#22c55e;font-size:11px;">✅ Aprovada</span>',
        rejected: '<span style="color:#ef4444;font-size:11px;">❌ Rejeitada</span>',
      }[e.status] || '';
      const srcHtml = (e.sources || []).map(s =>
        s.url ? `<a href="${escapeHtml(s.url)}" target="_blank" style="color:#66fcf1;font-size:11px;display:inline-flex;align-items:center;gap:3px;">🔗 ${escapeHtml(s.label||s.url)}</a>` : ''
      ).join(' ');
      const newValDisplay = typeof e.new_value === 'object'
        ? JSON.stringify(e.new_value)
        : String(e.new_value);
      return `
        <div style="background:rgba(255,255,255,0.04);border:1px solid #333;border-radius:8px;padding:10px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="color:var(--primary);font-size:12px;font-weight:bold;">${escapeHtml(e.field_label)}</span>
            ${statusBadge}
          </div>
          <div style="color:white;font-size:13px;margin-bottom:4px;">${escapeHtml(newValDisplay)}</div>
          ${e.reason ? `<div style="color:#aaa;font-size:12px;font-style:italic;">"${escapeHtml(e.reason)}"</div>` : ''}
          ${srcHtml ? `<div style="margin-top:6px;">${srcHtml}</div>` : ''}
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
            <span style="color:#555;font-size:11px;">${e.created_at}</span>
            ${e.status === 'pending' ? `
              <div style="display:flex;gap:6px;">
                <button onclick="voteEdit(${e.id},1,this)" style="background:rgba(34,197,94,0.15);border:1px solid #22c55e;color:#22c55e;border-radius:6px;padding:3px 8px;font-size:11px;cursor:pointer;">
                  👍 ${e.votes.ups}
                </button>
                <button onclick="voteEdit(${e.id},-1,this)" style="background:rgba(239,68,68,0.15);border:1px solid #ef4444;color:#ef4444;border-radius:6px;padding:3px 8px;font-size:11px;cursor:pointer;">
                  👎 ${e.votes.downs}
                </button>
              </div>` : `<span style="color:#555;font-size:11px;">👍 ${e.votes.ups} · 👎 ${e.votes.downs}</span>`}
          </div>
          ${e.review_note ? `<div style="color:#888;font-size:11px;margin-top:4px;border-top:1px solid #333;padding-top:4px;">Moderação: ${escapeHtml(e.review_note)}</div>` : ''}
        </div>`;
    }).join('');
  } catch(e) { container.innerHTML = '<p style="color:#666;">Erro ao carregar sugestões.</p>'; }
}

/* ── Votar numa sugestão ───────────────────────────────────────────────── */
async function voteEdit(editId, value, btn) {
  const user = window.__currentUser;
  if (!user) { showToast('Faça login para votar'); return; }
  try {
    const r = await authFetch(`/transparency/edit/${editId}/vote`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ user_id: user.id, value }),
    });
    const d = await r.json();
    if (d.error) { showToast('❌ ' + d.error); return; }
    // Atualizar contadores no botão
    const parent = btn.closest('div');
    const btns = parent.querySelectorAll('button');
    if (btns[0]) btns[0].innerHTML = `👍 ${d.ups}`;
    if (btns[1]) btns[1].innerHTML = `👎 ${d.downs}`;
  } catch(e) { showToast('Erro ao votar'); }
}

/* ── Modal de sugestão ─────────────────────────────────────────────────── */
function openSuggestModal(politicianId, politicianName) {
  const user = window.__currentUser;
  if (!user) { showToast('Faça login para sugerir edições'); return; }

  const fieldsOpts = Object.entries({
    salary:'Salário', party:'Partido', bio:'Biografia', charges:'Acusações/Processos',
    photo:'Foto', email:'E-mail', assets:'Patrimônio', education:'Formação', mandates:'Mandatos'
  }).map(([v,l]) => `<option value="${v}">${l}</option>`).join('');

  document.getElementById('modal-suggest-title').textContent = `Sugerir edição — ${politicianName}`;
  document.getElementById('modal-suggest-body').innerHTML = `
    <div style="display:flex;flex-direction:column;gap:10px;">
      <select id="sg-field" style="background:#111;color:white;border:1px solid #333;border-radius:8px;padding:8px;">
        <option value="">Selecione o campo...</option>${fieldsOpts}
      </select>
      <textarea id="sg-value" placeholder="Novo valor (ex: R$ 39.293,32 ou texto da bio...)"
        style="background:#111;color:white;border:1px solid #333;border-radius:8px;padding:8px;min-height:80px;resize:vertical;"></textarea>
      <textarea id="sg-reason" placeholder="Justificativa (por que esse valor está errado?)"
        style="background:#111;color:white;border:1px solid #333;border-radius:8px;padding:8px;min-height:60px;resize:vertical;"></textarea>
      <div id="sg-sources-list"></div>
      <button onclick="addSuggestSource()" style="background:rgba(102,252,241,0.1);border:1px solid var(--primary);color:var(--primary);border-radius:8px;padding:6px;font-size:12px;cursor:pointer;">
        + Adicionar fonte/referência
      </button>
      <button onclick="submitSuggest('${politicianId}')" style="background:var(--primary);color:#000;border:none;border-radius:8px;padding:10px;font-weight:bold;cursor:pointer;">
        📨 Enviar sugestão
      </button>
    </div>`;
  document.getElementById('modal-suggest').classList.remove('hidden');
}

function addSuggestSource() {
  const list = document.getElementById('sg-sources-list');
  const idx = list.children.length;
  const div = document.createElement('div');
  div.style.cssText = 'display:flex;gap:6px;margin-bottom:6px;';
  div.innerHTML = `
    <input placeholder="URL da fonte" id="sg-src-url-${idx}"
      style="flex:1;background:#111;color:white;border:1px solid #333;border-radius:8px;padding:6px;font-size:12px;">
    <input placeholder="Descrição" id="sg-src-label-${idx}"
      style="width:120px;background:#111;color:white;border:1px solid #333;border-radius:8px;padding:6px;font-size:12px;">
    <select id="sg-src-kind-${idx}" style="background:#111;color:white;border:1px solid #333;border-radius:8px;padding:6px;font-size:12px;">
      <option value="official">🏛️ Oficial</option>
      <option value="news">📰 Notícia</option>
      <option value="wikipedia">📚 Wikipedia</option>
      <option value="other">🔗 Outro</option>
    </select>`;
  list.appendChild(div);
}

async function submitSuggest(politicianId) {
  const user = window.__currentUser;
  const field   = document.getElementById('sg-field')?.value;
  const newVal  = document.getElementById('sg-value')?.value?.trim();
  const reason  = document.getElementById('sg-reason')?.value?.trim();
  if (!field)  { showToast('Selecione o campo'); return; }
  if (!newVal) { showToast('Preencha o novo valor'); return; }

  const srcList = document.getElementById('sg-sources-list');
  const sources = [...srcList.children].map((_, i) => ({
    url:   document.getElementById(`sg-src-url-${i}`)?.value?.trim() || '',
    label: document.getElementById(`sg-src-label-${i}`)?.value?.trim() || '',
    kind:  document.getElementById(`sg-src-kind-${i}`)?.value || 'other',
  })).filter(s => s.url);

  try {
    const r = await authFetch(`/transparency/politician/${politicianId}/suggest`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ user_id: user.id, field, new_value: newVal, reason, sources }),
    });
    const d = await r.json();
    if (d.error) { showToast('❌ ' + d.error); return; }
    document.getElementById('modal-suggest').classList.add('hidden');
    showToast('📨 Sugestão enviada! Aguarda moderação.');
  } catch(e) { showToast('Erro ao enviar'); }
}

/* ── Histórico de revisões ─────────────────────────────────────────────── */
async function loadHistory(politicianId, container) {
  try {
    const r = await fetch(`/transparency/politician/${politicianId}/history`);
    const d = await r.json();
    const hist = d.history || [];
    if (!hist.length) {
      container.innerHTML = `<p style="color:#666;font-size:13px;text-align:center;">Nenhuma revisão ainda.</p>`;
      return;
    }
    container.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead><tr style="color:#888;border-bottom:1px solid #333;">
        <th style="text-align:left;padding:4px 8px;">Campo</th>
        <th style="text-align:left;padding:4px 8px;">Data</th>
        <th style="text-align:left;padding:4px 8px;">Por</th>
      </tr></thead><tbody>
      ${hist.map(h => `<tr style="border-bottom:1px solid #1a1a1a;">
        <td style="padding:4px 8px;color:var(--primary);">${escapeHtml(h.field_label||h.field||'—')}</td>
        <td style="padding:4px 8px;color:#888;">${h.created_at}</td>
        <td style="padding:4px 8px;color:#666;">usuário #${h.changed_by||'?'}</td>
      </tr>`).join('')}
      </tbody></table>`;
  } catch(e) { container.innerHTML = ''; }
}

/* ── Painel de Moderação (só staff) ────────────────────────────────────── */
async function loadModerationQueue(user) {
  if (!user?.is_staff) return;
  const panel = document.getElementById('mod-queue-panel');
  if (!panel) return;
  try {
    const r = await authFetch(`/transparency/moderation/queue?moderator_id=${user.id}`);
    const d = await r.json();
    const queue = d.queue || [];
    panel.innerHTML = queue.length
      ? `<h4 style="color:var(--primary);margin:0 0 10px;">⚖️ Fila de moderação (${queue.length})</h4>` +
        queue.map(e => `
          <div style="background:rgba(255,255,255,0.04);border:1px solid #444;border-radius:8px;padding:10px;margin-bottom:8px;">
            <div style="color:#aaa;font-size:11px;margin-bottom:4px;">
              Político: <b style="color:white;">${e.politician_id}</b> · Campo: <b style="color:var(--primary);">${escapeHtml(e.field_label)}</b>
            </div>
            <div style="color:white;font-size:13px;margin-bottom:4px;">${escapeHtml(String(e.new_value))}</div>
            ${e.reason ? `<div style="color:#888;font-size:12px;font-style:italic;">"${escapeHtml(e.reason)}"</div>` : ''}
            ${(e.sources||[]).map(s => s.url ? `<a href="${s.url}" target="_blank" style="color:#66fcf1;font-size:11px;">🔗 ${escapeHtml(s.label||s.url)}</a>` : '').join(' ')}
            <div style="display:flex;gap:8px;margin-top:8px;">
              <button onclick="moderateEdit(${e.id},true,${user.id})" style="flex:1;background:rgba(34,197,94,0.2);border:1px solid #22c55e;color:#22c55e;border-radius:6px;padding:6px;cursor:pointer;font-size:12px;">✅ Aprovar</button>
              <button onclick="moderateEdit(${e.id},false,${user.id})" style="flex:1;background:rgba(239,68,68,0.2);border:1px solid #ef4444;color:#ef4444;border-radius:6px;padding:6px;cursor:pointer;font-size:12px;">❌ Rejeitar</button>
            </div>
            <input id="mod-note-${e.id}" placeholder="Nota (opcional)" style="width:100%;background:#111;color:white;border:1px solid #333;border-radius:6px;padding:5px;font-size:11px;margin-top:6px;box-sizing:border-box;">
          </div>`).join('')
      : '<p style="color:#666;font-size:13px;text-align:center;">Nenhuma sugestão pendente 🎉</p>';
  } catch(e) { if(panel) panel.innerHTML = ''; }
}

async function moderateEdit(editId, approve, modId) {
  const note = document.getElementById(`mod-note-${editId}`)?.value?.trim() || '';
  try {
    const r = await authFetch(`/transparency/edit/${editId}/moderate`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ moderator_id: modId, approve, note }),
    });
    const d = await r.json();
    if (d.error) { showToast('❌ ' + d.error); return; }
    showToast(d.message || 'OK');
    loadModerationQueue(window.__currentUser);
  } catch(e) { showToast('Erro ao moderar'); }
}

window.loadTrustScore   = loadTrustScore;
window.loadEdits        = loadEdits;
window.loadHistory      = loadHistory;
window.openSuggestModal = openSuggestModal;
window.voteEdit         = voteEdit;
window.addSuggestSource = addSuggestSource;
window.submitSuggest    = submitSuggest;
window.loadModerationQueue = loadModerationQueue;
window.moderateEdit     = moderateEdit;
