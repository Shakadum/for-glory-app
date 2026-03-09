// ═══════════════════════════════════════════════════════════════
// FOR GLORY — VIP — Planos, Assinatura, Glory Multiplier
// Gerado por splitter v2 — extração correta por profundidade de chaves
// ═══════════════════════════════════════════════════════════════
/* global user, authFetch, safeAvatarUrl, showToast, t, goView, escapeHtml */

async function loadVipPanel() {
    await loadGloryHeader();
    await loadVipPlans();
    // Renderizar painel de bordas VIP
    setTimeout(() => {
        const el = document.getElementById('vip-border-panel');
        if (el && typeof renderVipBorderPanel === 'function') renderVipBorderPanel(el);
    }, 200);

async function loadVipPlans() {
    const container = document.getElementById('vip-plans');
    const currentPlanEl = document.getElementById('vip-current-plan');
    if (!container) return;

    try {
        const [plansR, myR] = await Promise.all([
            fetch('/plans'),
            authFetch('/my/plan'),
        ]);
        const plans  = plansR.ok ? await plansR.json() : [];
        const myData = myR.ok   ? await myR.json() : {};
        const currentSlug = myData?.plan?.slug || 'free';

        if (currentPlanEl) {
            const cp = myData?.plan || {};
            const sub = myData?.subscription;
            currentPlanEl.innerHTML = `
                <div style="background:rgba(102,252,241,0.06);border:1px solid rgba(102,252,241,0.15);border-radius:12px;padding:16px;display:flex;align-items:center;gap:14px;">
                    <div style="font-size:24px;">${currentSlug==='free'?'👤':currentSlug==='vip1'?'🥈':currentSlug==='vip2'?'🥇':'💎'}</div>
                    <div style="flex:1;">
                        <div style="font-family:'Rajdhani';font-weight:800;font-size:15px;color:#66fcf1;">Plano atual: ${cp.name || 'Gratuito'}</div>
                        <div style="font-size:12px;color:#6b7280;margin-top:3px;">Multiplicador de Glory: ${(cp.glory_multiplier||1)}x
                        ${sub?.expires ? ` · Renova em ${new Date(sub.expires).toLocaleDateString('pt-BR')}` : ''}
                        </div>
                    </div>
                    ${currentSlug !== 'free' ? '<button onclick="cancelSubscription()" style="background:transparent;border:1px solid #ef4444;color:#ef4444;border-radius:8px;padding:6px 12px;font-size:11px;cursor:pointer;">Cancelar</button>' : ''}
                </div>`;
        }

        const planColors  = {free:'#6b7280', vip1:'#9ca3af', vip2:'#f59e0b', vip3:'#66fcf1'};
        const planIcons   = {free:'👤', vip1:'🥈', vip2:'🥇', vip3:'💎'};
        const planFeats   = {
            free:  ['10 quizzes/dia','Rank básico','Acesso completo ao Portal'],
            vip1:  ['30 quizzes/dia','2x Glory points','Badge prata','Borda personalizada'],
            vip2:  ['100 quizzes/dia','5x Glory points','Badge ouro','Temas exclusivos','Quizzes premium'],
            vip3:  ['Quizzes ilimitados','10x Glory points','Badge diamante','Temas exclusivos','Suporte prioritário','Acesso antecipado'],
        };

        container.innerHTML = plans.map(p => {
            const isCurrent = p.slug === currentSlug;
            const color     = planColors[p.slug] || '#6b7280';
            const icon      = planIcons[p.slug]  || '👤';
            const feats     = planFeats[p.slug]  || [];
            return `
            <div style="background:rgba(255,255,255,0.03);border:1px solid ${isCurrent ? color : 'rgba(255,255,255,0.08)'};border-radius:14px;padding:20px;${isCurrent?`box-shadow:0 0 20px ${color}22;`:''}">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
                    <div style="display:flex;align-items:center;gap:10px;">
                        <span style="font-size:22px;">${icon}</span>
                        <div>
                            <div style="font-family:'Rajdhani';font-weight:800;font-size:16px;color:${color};letter-spacing:0.5px;">${p.name}</div>
                            <div style="font-size:12px;color:#6b7280;">${p.glory_multiplier}x Glory</div>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-family:'Syne';font-weight:800;font-size:18px;color:#f3f4f6;">
                            ${p.price_monthly > 0 ? `R$ ${p.price_monthly.toFixed(2).replace('.',',')}` : 'Grátis'}
                        </div>
                        ${p.price_monthly > 0 ? '<div style="font-size:10px;color:#4b5563;">/mês</div>' : ''}
                    </div>
                </div>
                <ul style="list-style:none;padding:0;margin:0 0 16px 0;display:flex;flex-direction:column;gap:7px;">
                    ${feats.map(f => `<li style="font-size:12px;color:#9ca3af;display:flex;align-items:center;gap:8px;"><span style="color:${color};">✓</span>${f}</li>`).join('')}
                </ul>
                ${isCurrent
                    ? `<div style="text-align:center;padding:10px;background:${color}22;border-radius:8px;font-family:'Rajdhani';font-weight:700;font-size:12px;color:${color};letter-spacing:1px;">PLANO ATUAL</div>`
                    : p.slug === 'free' ? '' : `<button onclick="subscribePlan('${p.slug}')" style="width:100%;background:${color};color:#0b0c10;border:none;border-radius:8px;padding:12px;font-family:'Rajdhani';font-weight:700;font-size:13px;cursor:pointer;letter-spacing:0.5px;">
                        ASSINAR${p.price_monthly > 0 ? ` · R$ ${p.price_monthly.toFixed(2).replace('.',',')}` : ''}
                    </button>`
                }
            </div>`;
        }).join('');
    } catch(e) { console.error('loadVipPlans:', e); }
}

async function subscribePlan(slug) {
    if (!confirm(`Assinar plano ${slug}? (Modo demonstração — sem cobrança real)`)) return;
    try {
        const r = await authFetch('/subscription/create', {
            method: 'POST',
            body: JSON.stringify({ plan_slug: slug, provider: 'manual' })
        });
        const d = await r.json();
        if (r.ok) {
            showToast(`✅ Plano ${slug} ativado!`);
            loadVipPanel();
            loadGloryHeader();
        } else {
            showToast(d.detail || 'Erro ao assinar plano');
        }
    } catch(e) { showToast('Erro ao assinar plano.'); }
}

async function cancelSubscription() {
    if (!confirm('Cancelar assinatura? Você voltará ao plano gratuito.')) return;
    try {
        const r = await authFetch('/subscription/cancel', { method: 'POST' });
        if (r.ok) { showToast('Assinatura cancelada.'); loadVipPanel(); }
    } catch(e) { showToast('Erro ao cancelar.'); }
}
}
