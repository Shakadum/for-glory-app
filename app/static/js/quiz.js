// ═══════════════════════════════════════════════════════════════
// FOR GLORY — QUIZ — Quizzes, Glory, Ranking
// Gerado por splitter v2 — extração correta por profundidade de chaves
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */

async function loadQuizPanel() {
    await loadGloryHeader();
    // Renderizar abas de quiz
    const qContainer = document.getElementById('quiz-list');
    if (qContainer) {
        qContainer.insertAdjacentHTML('beforebegin', `
            <div style="display:flex;gap:8px;margin-bottom:14px;border-bottom:1px solid #1e293b;padding-bottom:10px;">
                <button id="qtab-daily" onclick="switchQuizTab('daily')"
                    style="background:#66fcf1;color:#0b0c10;border:none;border-radius:8px;padding:7px 14px;font-family:'Rajdhani';font-weight:700;font-size:12px;cursor:pointer;letter-spacing:0.5px;">
                    🔥 DIÁRIOS (30)
                </button>
                <button id="qtab-all" onclick="switchQuizTab('all')"
                    style="background:rgba(255,255,255,0.06);color:#9ca3af;border:1px solid #1e293b;border-radius:8px;padding:7px 14px;font-family:'Rajdhani';font-weight:700;font-size:12px;cursor:pointer;letter-spacing:0.5px;">
                    📚 TODOS
                </button>
            </div>`);
    }
    await loadDailyQuizzes();
    await loadQuizRanking();

async function loadGloryHeader() {
    try {
        const r = await authFetch('/my/plan');
        if (!r.ok) return;
        const d = await r.json();

        const pts = d.glory?.points || 0;
        const rankName  = d.glory?.rank_name  || 'Cidadão Comum';
        const rankIcon  = d.glory?.rank_icon  || '👤';
        const planName  = d.plan?.name || 'Gratuito';
        const multiplier = d.plan?.glory_multiplier || 1;

        const el = (id) => document.getElementById(id);
        if (el('glory-rank-name'))   el('glory-rank-name').innerText   = rankName;
        if (el('glory-points-total')) el('glory-points-total').innerText = pts.toLocaleString('pt-BR');
        if (el('glory-rank-icon'))   el('glory-rank-icon').innerText   = rankIcon;
        if (el('glory-plan-name'))   el('glory-plan-name').innerText   = `${planName}${multiplier > 1 ? ` · ${multiplier}x Glory` : ''}`;

        // Progress bar placeholder (next rank requires points data)
        const bar = el('glory-progress-bar');
        if (bar) bar.style.width = Math.min(((pts % 1000) / 10), 100) + '%';

        // Store for use in other places
        window.__gloryData = d;
    } catch(e) { console.warn('loadGloryHeader:', e); }
}

async function loadQuizzes() {
    const container = document.getElementById('quiz-list');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;color:#4b5563;padding:30px;font-family:DM Sans,sans-serif;font-size:13px;">⏳ Carregando...</div>';
    try {
        const r = await authFetch('/quizzes?limit=20');
        if (!r.ok) { container.innerHTML = '<div style="color:#888;text-align:center;padding:20px;">Sem quizzes disponíveis.</div>'; return; }
        const quizzes = await r.json();
        if (!quizzes.length) {
            container.innerHTML = '<div style="color:#888;text-align:center;padding:30px;font-family:DM Sans,sans-serif;font-size:13px;">Nenhum quiz disponível ainda.<br><span style="font-size:11px;opacity:0.6;">Admins podem criar quizzes via API.</span></div>';
            return;
        }
        const catColors = {news:'#ef4444',politicians:'#3b82f6',constitution:'#8b5cf6',community:'#10b981',general:'#6b7280'};
        container.innerHTML = quizzes.map(q => {
            const col = catColors[q.category] || '#6b7280';
            const done = q.attempted;
            return `<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,${done?'0.04':'0.08'});border-radius:12px;padding:16px;display:flex;align-items:center;gap:14px;opacity:${done?'0.5':'1'};">
                <div style="width:42px;height:42px;border-radius:10px;background:${col}22;border:1px solid ${col}44;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">
                    ${q.category==='news'?'📰':q.category==='politicians'?'🏛️':q.category==='constitution'?'📜':q.category==='community'?'👥':'🧠'}
                </div>
                <div style="flex:1;min-width:0;">
                    <div style="font-family:DM Sans,sans-serif;font-weight:600;font-size:13px;color:#e5e7eb;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(q.title)}</div>
                    <div style="display:flex;gap:8px;align-items:center;margin-top:5px;">
                        <span style="font-size:10px;color:${col};font-family:'Rajdhani';font-weight:700;letter-spacing:0.5px;">${(q.category||'').toUpperCase()}</span>
                        <span style="font-size:10px;color:#4b5563;">·</span>
                        <span style="font-size:10px;color:#4b5563;">${q.question_count} perguntas</span>
                        <span style="font-size:10px;color:#4b5563;">·</span>
                        <span style="font-size:10px;color:#4b5563;">${q.difficulty==='easy'?'Fácil':q.difficulty==='hard'?'Difícil':'Médio'}</span>
                    </div>
                </div>
                <div style="flex-shrink:0;display:flex;align-items:center;gap:6px;">
                    <button class="fav-star-btn" onclick="toggleFavQuiz({id:${q.id},title:${JSON.stringify(q.title)},category:${JSON.stringify(q.category)},difficulty:${JSON.stringify(q.difficulty)}})" title="Favoritar" style="font-size:16px;">⭐</button>
                    ${done
                        ? '<span style="font-size:11px;color:#10b981;">✓ Feito</span>'
                        : `<button onclick="startQuiz(${q.id},'${escapeHtml(q.title)}')" style="background:#66fcf1;color:#0b0c10;border:none;border-radius:8px;padding:8px 14px;font-family:'Rajdhani';font-weight:700;font-size:12px;cursor:pointer;letter-spacing:0.5px;">JOGAR</button>`
                    }
                </div>
            </div>`;
        }).join('');
    } catch(e) { console.error('loadQuizzes:', e); container.innerHTML = '<div style="color:#888;text-align:center;padding:20px;">Erro ao carregar quizzes.</div>'; }
}

async function loadQuizRanking() {
    const el = document.getElementById('quiz-ranking');
    if (!el) return;
    try {
        const r = await fetch('/quizzes/ranking/weekly');
        if (!r.ok) return;
        const ranking = await r.json();
        if (!ranking.length) { el.innerHTML = '<div style="color:#4b5563;text-align:center;padding:20px;font-size:13px;">Nenhuma participação esta semana.</div>'; return; }
        el.innerHTML = ranking.slice(0, 10).map((entry, i) => {
            const medal = i===0?'🥇':i===1?'🥈':i===2?'🥉':`${i+1}.`;
            return `<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid rgba(255,255,255,0.06);">
                <span style="font-size:${i<3?'18':'13'}px;width:24px;text-align:center;flex-shrink:0;">${medal}</span>
                <img src="${safeAvatarUrl(entry.avatar)}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;" onerror="this.src='/static/default-avatar.svg'">
                <span style="flex:1;font-family:DM Sans,sans-serif;font-size:13px;color:#e5e7eb;">${escapeHtml(entry.username)}</span>
                <span style="font-family:'Rajdhani';font-weight:700;font-size:14px;color:#66fcf1;">${(entry.score_week||0).toLocaleString('pt-BR')} pts</span>
            </div>`;
        }).join('');
    } catch(e) { console.warn('loadQuizRanking:', e); }
}

async function startQuiz(quizId, title) {
    try {
        const r = await authFetch(`/quizzes/${quizId}`);
        if (!r.ok) {
            const err = await r.json().catch(()=>({}));
            return showToast(err.detail || 'Erro ao carregar quiz');
        }
        __quizData = await r.json();
        __quizStartTime = Date.now();
        renderQuizModal(__quizData);
    } catch(e) { console.error('startQuiz:', e); showToast('Erro ao iniciar quiz.'); }
}

function renderQuizModal(quiz) {
    const existing = document.getElementById('modal-quiz');
    if (existing) existing.remove();

    let currentQ = 0;
    const answers = new Array(quiz.questions.length).fill(-1);

    function buildHTML() {
        const q = quiz.questions[currentQ];
        const total = quiz.questions.length;
        const progress = ((currentQ + 1) / total * 100).toFixed(0);
        return `
        <div id="modal-quiz" style="position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;">
            <div style="background:#111827;border:1px solid rgba(102,252,241,0.2);border-radius:18px;padding:24px;max-width:500px;width:100%;max-height:90vh;overflow-y:auto;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
                    <div style="font-family:'Rajdhani';font-weight:800;font-size:14px;color:#66fcf1;letter-spacing:1px;">QUIZ · ${currentQ+1}/${total}</div>
                    <button onclick="document.getElementById('modal-quiz').remove()" style="background:transparent;border:none;color:#6b7280;cursor:pointer;font-size:18px;">✕</button>
                </div>
                <div style="background:rgba(102,252,241,0.05);border-radius:20px;height:4px;margin-bottom:20px;overflow:hidden;">
                    <div style="height:100%;background:#66fcf1;border-radius:20px;width:${progress}%;transition:width 0.3s;"></div>
                </div>
                <div style="font-family:DM Sans,sans-serif;font-weight:600;font-size:15px;color:#f3f4f6;line-height:1.5;margin-bottom:20px;">${escapeHtml(q.question)}</div>
                <div id="quiz-options" style="display:flex;flex-direction:column;gap:10px;">
                    ${q.options.map((opt, i) => `
                    <button onclick="selectAnswer(${i})" id="quiz-opt-${i}" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:14px 16px;text-align:left;color:#e5e7eb;font-family:DM Sans,sans-serif;font-size:13px;cursor:pointer;transition:all 0.15s;width:100%;"
                        onmouseover="if(!this.dataset.locked)this.style.borderColor='rgba(102,252,241,0.4)'"
                        onmouseout="if(!this.dataset.locked)this.style.borderColor='rgba(255,255,255,0.1)'">
                        <span style="color:#66fcf1;margin-right:10px;font-weight:700;">${['A','B','C','D'][i]}.</span>${escapeHtml(opt)}
                    </button>`).join('')}
                </div>
                <div id="quiz-explanation" style="display:none;margin-top:16px;padding:14px;background:rgba(102,252,241,0.05);border:1px solid rgba(102,252,241,0.15);border-radius:10px;font-size:12px;color:#9ca3af;line-height:1.5;"></div>
                <div id="quiz-nav" style="margin-top:18px;display:flex;justify-content:flex-end;gap:10px;display:none;">
                    <button id="quiz-next-btn" onclick="nextQuizQuestion()" style="background:#66fcf1;color:#0b0c10;border:none;border-radius:8px;padding:10px 20px;font-family:'Rajdhani';font-weight:700;font-size:13px;cursor:pointer;letter-spacing:0.5px;">
                        ${currentQ < total-1 ? 'PRÓXIMA →' : 'FINALIZAR ✓'}
                    </button>
                </div>
            </div>
        </div>`;
    }

    document.body.insertAdjacentHTML('beforeend', buildHTML());

    window.selectAnswer = function(idx) {
        const q = quiz.questions[currentQ];
        answers[currentQ] = idx;
        // Lock buttons
        document.querySelectorAll('#quiz-options button').forEach((btn, i) => {
            btn.dataset.locked = '1';
            btn.style.cursor = 'default';
            if (i === q.correct_index) {
                btn.style.background = 'rgba(16,185,129,0.15)';
                btn.style.borderColor = '#10b981';
                btn.style.color = '#10b981';
            } else if (i === idx && idx !== q.correct_index) {
                btn.style.background = 'rgba(239,68,68,0.15)';
                btn.style.borderColor = '#ef4444';
                btn.style.color = '#ef4444';
            }
        });
        // Show explanation
        if (q.explanation) {
            const expl = document.getElementById('quiz-explanation');
            if (expl) { expl.style.display = 'block'; expl.innerHTML = `💡 ${escapeHtml(q.explanation)}`; }
        }
        document.getElementById('quiz-nav').style.display = 'flex';
    };

    window.nextQuizQuestion = function() {
        const modal = document.getElementById('modal-quiz');
        if (!modal) return;
        if (currentQ < quiz.questions.length - 1) {
            currentQ++;
            modal.remove();
            document.body.insertAdjacentHTML('beforeend', buildHTML());
            // Re-register handlers after rebuild
            window.selectAnswer = selectAnswer;
            window.nextQuizQuestion = nextQuizQuestion;
        } else {
            // Submit
            submitQuizAnswers(quiz.id, answers);
        }
    };
}

async function submitQuizAnswers(quizId, answers) {
    const timeSec = Math.floor((Date.now() - __quizStartTime) / 1000);
    try {
        const r = await authFetch(`/quizzes/${quizId}/submit`, {
            method: 'POST',
            body: JSON.stringify({ answers, time_sec: timeSec })
        });
        const d = await r.json();
        const modal = document.getElementById('modal-quiz');
        if (modal) modal.remove();

        if (!r.ok) return showToast(d.detail || 'Erro ao enviar respostas.');

        // Show result modal
        document.body.insertAdjacentHTML('beforeend', `
            <div id="modal-quiz-result" style="position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;">
                <div style="background:#111827;border:1px solid rgba(102,252,241,0.2);border-radius:18px;padding:28px;max-width:380px;width:100%;text-align:center;">
                    <div style="font-size:48px;margin-bottom:12px;">${d.correct === d.total ? '🏆' : d.correct >= d.total/2 ? '⭐' : '📚'}</div>
                    <div style="font-family:'Syne';font-weight:800;font-size:20px;color:#f3f4f6;margin-bottom:8px;">
                        ${d.correct}/${d.total} corretas
                    </div>
                    <div style="font-family:DM Sans,sans-serif;font-size:13px;color:#6b7280;margin-bottom:20px;">${timeSec}s · ${d.multiplier > 1 ? `${d.multiplier}x multiplicador VIP` : 'sem multiplicador'}</div>
                    <div style="background:rgba(102,252,241,0.08);border:1px solid rgba(102,252,241,0.2);border-radius:12px;padding:16px;margin-bottom:20px;">
                        <div style="font-family:'Rajdhani';font-weight:800;font-size:28px;color:#66fcf1;">+${d.glory_earned}</div>
                        <div style="font-size:12px;color:#6b7280;">pontos de glória</div>
                        <div style="font-size:11px;color:#4b5563;margin-top:4px;">Total: ${(d.glory_total||0).toLocaleString('pt-BR')} pts</div>
                    </div>
                    <button onclick="document.getElementById('modal-quiz-result').remove(); loadQuizPanel();" style="background:#66fcf1;color:#0b0c10;border:none;border-radius:8px;padding:12px 24px;font-family:'Rajdhani';font-weight:700;font-size:14px;cursor:pointer;letter-spacing:0.5px;width:100%;">
                        CONTINUAR
                    </button>
                </div>
            </div>
        `);
        // Refresh glory header
        loadGloryHeader();
    } catch(e) { console.error('submitQuizAnswers:', e); showToast('Erro ao enviar respostas.'); }
}}

function toggleFavQuiz(item) {
    const data = JSON.parse(localStorage.getItem('fg_favorites') || '{}');
    const list = data.quizzes || [];
    const exists = list.find(x => x.id === item.id);
    if (exists) {
        data.quizzes = list.filter(x => x.id !== item.id);
        if (typeof showToast === 'function') showToast('Removido dos favoritos');
    } else {
        data.quizzes = [item, ...list].slice(0, 50);
        if (typeof showToast === 'function') showToast('⭐ Quiz favoritado!');
    }
    localStorage.setItem('fg_favorites', JSON.stringify(data));
}

// ── Abas de quiz ─────────────────────────────────────────────────────────────
function switchQuizTab(tab) {
    document.getElementById('qtab-daily').style.background = tab==='daily' ? '#66fcf1' : 'rgba(255,255,255,0.06)';
    document.getElementById('qtab-daily').style.color = tab==='daily' ? '#0b0c10' : '#9ca3af';
    document.getElementById('qtab-all').style.background = tab==='all' ? '#66fcf1' : 'rgba(255,255,255,0.06)';
    document.getElementById('qtab-all').style.color = tab==='all' ? '#0b0c10' : '#9ca3af';
    if (tab==='daily') loadDailyQuizzes(); else loadQuizzes();
}

// ── Quizzes diários por IA ────────────────────────────────────────────────────
const CAT_ICONS = {
    política_local:'🏛️', noticias_locais:'📰', geopolitica:'🌍',
    noticias_globais:'🌐', historia:'📜', geografia:'🗺️',
};
const CAT_LABELS = {
    política_local:'Política Local', noticias_locais:'Notícias do Dia',
    geopolitica:'Geopolítica', noticias_globais:'Mundo', historia:'História', geografia:'Geografia',
};
const CAT_COLORS = {
    política_local:'#3b82f6', noticias_locais:'#ef4444', geopolitica:'#ff6b6b',
    noticias_globais:'#ff9f43', historia:'#8b5cf6', geografia:'#10b981',
};

async function loadDailyQuizzes() {
    const container = document.getElementById('quiz-list');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;color:#4b5563;padding:30px;font-size:13px;">⏳ Carregando quizzes do dia...</div>';

    // Detectar país do usuário (usa o contexto de geolocalização da transparência se disponível)
    const country = window.__userCountry || 'BR';

    try {
        // Checar se já foram gerados
        const statusR = await fetch(`/quizzes/daily/status?country=${country}`);
        const status = await statusR.json();

        if (!status.ready) {
            container.innerHTML = `
                <div style="text-align:center;padding:30px;">
                    <div style="font-size:36px;margin-bottom:12px;">⚙️</div>
                    <div style="color:#9ca3af;font-size:14px;margin-bottom:16px;">Gerando quizzes do dia...</div>
                    <div style="color:#4b5563;font-size:12px;margin-bottom:20px;">Isso leva ~30 segundos na primeira vez do dia</div>
                    <button onclick="triggerAndLoadDaily('${country}')"
                        style="background:#66fcf1;color:#0b0c10;border:none;border-radius:8px;padding:10px 20px;font-family:'Rajdhani';font-weight:700;font-size:13px;cursor:pointer;">
                        ▶ GERAR AGORA
                    </button>
                </div>`;
            return;
        }

        const r = await authFetch(`/quizzes/daily?country=${country}`);
        const data = await r.json();
        const quizzes = data.quizzes || [];

        if (!quizzes.length) {
            container.innerHTML = '<div style="color:#888;text-align:center;padding:30px;">Nenhum quiz gerado ainda hoje.</div>';
            return;
        }

        // Agrupar por categoria
        const byCategory = {};
        for (const q of quizzes) {
            if (!byCategory[q.category]) byCategory[q.category] = [];
            byCategory[q.category].push(q);
        }

        const catOrder = ['política_local','noticias_locais','geopolitica','noticias_globais','historia','geografia'];
        let html = `<div style="color:#4b5563;font-size:11px;margin-bottom:12px;text-align:right;">🗓️ ${new Date().toLocaleDateString('pt-BR')} · ${quizzes.length} quizzes</div>`;

        for (const cat of catOrder) {
            const items = byCategory[cat] || [];
            if (!items.length) continue;
            const color = CAT_COLORS[cat] || '#888';
            const icon = CAT_ICONS[cat] || '🧠';
            const label = CAT_LABELS[cat] || cat;

            html += `<div style="margin-bottom:6px;">
                <div style="display:flex;align-items:center;gap:8px;padding:8px 0 6px;border-bottom:1px solid #1a1a2e;">
                    <span style="font-size:16px;">${icon}</span>
                    <span style="color:${color};font-family:'Rajdhani';font-weight:700;font-size:13px;letter-spacing:0.5px;">${label.toUpperCase()}</span>
                    <span style="color:#374151;font-size:11px;">${items.length} quizzes</span>
                </div>
            </div>`;

            html += items.map(q => {
                const diff = q.difficulty==='easy'?'Fácil':q.difficulty==='hard'?'Difícil':'Médio';
                const diffColor = q.difficulty==='easy'?'#10b981':q.difficulty==='hard'?'#ef4444':'#f59e0b';
                return `<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-left:3px solid ${color};border-radius:10px;padding:12px 14px;display:flex;align-items:center;gap:12px;margin-bottom:6px;">
                    <div style="flex:1;min-width:0;">
                        <div style="font-size:13px;color:#e5e7eb;font-family:'DM Sans';font-weight:600;line-height:1.3;">${escapeHtml(q.title)}</div>
                        <div style="display:flex;gap:8px;align-items:center;margin-top:5px;">
                            <span style="font-size:10px;color:${diffColor};font-family:'Rajdhani';font-weight:700;">${diff}</span>
                            <span style="font-size:10px;color:#374151;">·</span>
                            <span style="font-size:10px;color:#374151;">${q.question_count} perguntas</span>
                            ${q.expires_at ? `<span style="font-size:10px;color:#374151;">· até ${q.expires_at}</span>` : ''}
                        </div>
                    </div>
                    <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
                        <button class="fav-star-btn" onclick="toggleFavQuiz({id:${q.id},title:${JSON.stringify(q.title)},category:${JSON.stringify(q.category)},difficulty:${JSON.stringify(q.difficulty)}})" title="Favoritar">⭐</button>
                        <button onclick="startQuiz(${q.id},'${escapeHtml(q.title)}')"
                            style="background:#66fcf1;color:#0b0c10;border:none;border-radius:8px;padding:7px 12px;font-family:'Rajdhani';font-weight:700;font-size:12px;cursor:pointer;letter-spacing:0.5px;white-space:nowrap;">
                            JOGAR
                        </button>
                    </div>
                </div>`;
            }).join('');
        }

        container.innerHTML = html;
    } catch(e) {
        console.error('loadDailyQuizzes:', e);
        container.innerHTML = '<div style="color:#888;text-align:center;padding:20px;">Erro ao carregar quizzes do dia.</div>';
    }
}

async function triggerAndLoadDaily(country) {
    const container = document.getElementById('quiz-list');
    if (container) container.innerHTML = '<div style="text-align:center;color:#4b5563;padding:30px;font-size:13px;">⚙️ Gerando 30 quizzes... aguarde ~30s</div>';
    try {
        await authFetch('/quizzes/generate-daily', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({country}),
        });
        await loadDailyQuizzes();
    } catch(e) {
        if (container) container.innerHTML = '<div style="color:#888;text-align:center;padding:20px;">Erro ao gerar quizzes.</div>';
    }
}
