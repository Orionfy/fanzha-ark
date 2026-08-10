(function () {
    const STRATEGY_MAP = {
        tempt: { emoji: '🍬', label: '诱惑' },
        authority: { emoji: '🎩', label: '权威' },
        emotional: { emoji: '💞', label: '情感' },
        threat: { emoji: '🔪', label: '恐吓' }
    };

    const RATING_MAP = {
        S: { label: '铜墙铁壁', className: 'rating-S' },
        A: { label: '稳健防守', className: 'rating-A' },
        B: { label: '保持警惕', className: 'rating-B' },
        C: { label: '防线松动', className: 'rating-C' },
        D: { label: '风险较高', className: 'rating-D' },
        F: { label: '防线失守', className: 'rating-F' }
    };

    const RESULT_TYPE_MAP = {
        win_expose: { emoji: '🔎', title: '拆穿骗子' },
        win_alarm: { emoji: '🚨', title: '报警完胜' },
        lose_scammed: { emoji: '⚠️', title: '骗局得逞' },
        give_up: { emoji: '⏸️', title: '中途退出' }
    };

    const dom = {
        views: {
            home: document.getElementById('view-home'),
            setup: document.getElementById('view-setup'),
            battle: document.getElementById('view-battle'),
            result: document.getElementById('view-result')
        },
        navRestartBtn: document.getElementById('navRestartBtn'),
        scriptGrid: document.getElementById('scriptGrid'),
        setupScenarioIcon: document.getElementById('setupScenarioIcon'),
        setupScenarioName: document.getElementById('setupScenarioName'),
        setupScenarioDesc: document.getElementById('setupScenarioDesc'),
        setupScenarioMeta: document.getElementById('setupScenarioMeta'),
        inputName: document.getElementById('inputName'),
        nameFeedback: document.getElementById('nameFeedback'),
        setupBackBtn: document.getElementById('setupBackBtn'),
        startBattleBtn: document.getElementById('startBattleBtn'),
        scammerAvatar: document.getElementById('scammerAvatar'),
        scammerName: document.getElementById('scammerName'),
        scammerTitle: document.getElementById('scammerTitle'),
        scammerSignature: document.getElementById('scammerSignature'),
        strategyChip: document.getElementById('strategyChip'),
        hpValue: document.getElementById('hpValue'),
        hpFill: document.getElementById('hpFill'),
        scoreValue: document.getElementById('scoreValue'),
        ratingChip: document.getElementById('ratingChip'),
        roundValue: document.getElementById('roundValue'),
        totalRounds: document.getElementById('totalRounds'),
        moodIcon: document.getElementById('moodIcon'),
        moodValue: document.getElementById('moodValue'),
        moodFill: document.getElementById('moodFill'),
        chatBody: document.getElementById('chatBody'),
        signalPreview: document.getElementById('signalPreview'),
        replyInput: document.getElementById('replyInput'),
        sendReplyBtn: document.getElementById('sendReplyBtn'),
        charCount: document.getElementById('charCount'),
        resultCard: document.getElementById('resultCard'),
        connFailOverlay: document.getElementById('connFailOverlay'),
        retryConnBtn: document.getElementById('retryConnBtn'),
        toast: document.getElementById('toast')
    };

    let scenariosCache = [];
    let currentScenario = null;
    let battleState = null;
    let lastScammerBubble = null;
    let isBusy = false;

    document.addEventListener('DOMContentLoaded', init);

    async function init() {
        bindEvents();
        startStarCanvas();
        await loadScenarios();
    }

    function bindEvents() {
        dom.setupBackBtn.addEventListener('click', () => switchView('home'));
        dom.startBattleBtn.addEventListener('click', handleStartBattle);
        dom.sendReplyBtn.addEventListener('click', handleSendReply);
        dom.navRestartBtn.addEventListener('click', handleAbortBattle);
        dom.retryConnBtn.addEventListener('click', handleRetryConnection);
        dom.inputName.addEventListener('input', validateName);
        dom.replyInput.addEventListener('input', () => {
            dom.charCount.textContent = `${dom.replyInput.value.length}/500`;
        });
        dom.replyInput.addEventListener('keydown', event => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                handleSendReply();
            }
        });
    }

    async function loadScenarios() {
        try {
            const scenarios = await BattleAPI.getScenarios();
            scenariosCache = scenarios;
            renderScriptGrid(scenarios);
        } catch (error) {
            handleApiError(error, true);
        }
    }

    function renderScriptGrid(scenarios) {
        if (!scenarios.length) {
            dom.scriptGrid.innerHTML = '<div class="col-12 loading-state"><i class="bi bi-inbox" aria-hidden="true"></i><p>暂无可用实战剧本</p></div>';
            return;
        }

        dom.scriptGrid.innerHTML = scenarios.map((scenario, index) => {
            const icon = safeIcon(scenario.icon);
            const tags = (scenario.tags || []).map(tag => `<span class="script-tag">${escapeHtml(tag)}</span>`).join('');
            const tips = Array.isArray(scenario.tips) ? scenario.tips.join(' · ') : (scenario.tips || '留意对方索要的个人信息与资金操作');
            const cover = escapeHtml(scenario.cover || '');
            return `
                <div class="col-md-6 col-lg-3 animate-in stagger-${(index % 4) + 1}">
                    <article class="script-card" data-id="${escapeHtml(scenario.id)}" tabindex="0" aria-label="进入${escapeHtml(scenario.name)}实战">
                        <div class="script-cover">
                            <img src="${cover}" alt="${escapeHtml(scenario.name)}" width="640" height="360" loading="lazy">
                            <div class="script-cover-overlay">
                                <span class="difficulty-badge"><i class="bi bi-speedometer2" aria-hidden="true"></i> ${escapeHtml(scenario.difficulty || '未知')}</span>
                                <span class="rounds-badge">${escapeHtml(scenario.rounds || 0)} 回合</span>
                            </div>
                        </div>
                        <div class="script-card-body">
                            <div class="script-title-row"><div class="script-icon"><i class="bi ${icon}" aria-hidden="true"></i></div><h3>${escapeHtml(scenario.name)}</h3></div>
                            <p class="script-desc">${escapeHtml(scenario.description)}</p>
                            <div class="script-meta"><span class="fraud-tag">${escapeHtml(scenario.fraud_type || '诈骗话术')}</span>${tags}</div>
                            <div class="script-tips" title="${escapeHtml(tips)}"><i class="bi bi-lightbulb-fill" aria-hidden="true"></i><span>${escapeHtml(tips)}</span></div>
                            <button class="script-enter-btn" type="button"><i class="bi bi-chat-dots-fill" aria-hidden="true"></i> 进入实战</button>
                        </div>
                    </article>
                </div>`;
        }).join('');

        dom.scriptGrid.querySelectorAll('.script-cover img').forEach(image => {
            image.addEventListener('error', () => {
                image.hidden = true;
            });
        });

        requestAnimationFrame(() => {
            dom.scriptGrid.querySelectorAll('.animate-in').forEach(element => element.classList.add('visible'));
        });

        dom.scriptGrid.querySelectorAll('.script-card').forEach(card => {
            const choose = () => selectScenario(card.dataset.id);
            card.addEventListener('click', choose);
            card.addEventListener('keydown', event => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    choose();
                }
            });
        });
    }

    function selectScenario(scenarioId) {
        const scenario = scenariosCache.find(item => String(item.id) === String(scenarioId));
        if (!scenario) return;
        currentScenario = scenario;
        dom.setupScenarioIcon.innerHTML = `<i class="bi ${safeIcon(scenario.icon)}" aria-hidden="true"></i>`;
        dom.setupScenarioName.textContent = scenario.name || '未命名剧本';
        dom.setupScenarioDesc.textContent = scenario.description || '';
        const metadata = [scenario.fraud_type, scenario.difficulty, `${scenario.rounds || 0} 回合`, ...(scenario.tags || [])];
        dom.setupScenarioMeta.innerHTML = metadata.filter(Boolean).map(item => `<span class="script-tag">${escapeHtml(item)}</span>`).join('');
        dom.inputName.value = '';
        clearNameError();
        switchView('setup');
        requestAnimationFrame(() => dom.inputName.focus());
    }

    function validateName() {
        const name = dom.inputName.value.trim();
        if (name.length >= 1 && name.length <= 10) {
            clearNameError();
            return true;
        }
        if (!name) {
            setNameError('请输入你的昵称');
        } else {
            setNameError('昵称需为 1-10 个字符');
        }
        return false;
    }

    function setNameError(message) {
        dom.inputName.classList.add('is-invalid');
        dom.inputName.setAttribute('aria-invalid', 'true');
        dom.nameFeedback.textContent = message;
    }

    function clearNameError() {
        dom.inputName.classList.remove('is-invalid');
        dom.inputName.removeAttribute('aria-invalid');
        dom.nameFeedback.textContent = '';
    }

    async function handleStartBattle() {
        if (!currentScenario || !validateName() || isBusy) return;
        setStartBusy(true);
        try {
            battleState = await BattleAPI.startBattle(String(currentScenario.id), dom.inputName.value.trim());
            resetBattleSurface();
            switchView('battle');
            renderScammerProfile(battleState);
            updateHud(battleState, false);
            renderSignalPreview(battleState.signals);
            appendNarration(`对战开始：你正在与【${battleState.scammer?.name || '未知对手'}】对话…`);
            setComposerEnabled(false);
            await renderScammerTurn(battleState.scammer_msg, battleState.scammer);
            setComposerEnabled(true);
            dom.replyInput.focus();
        } catch (error) {
            handleApiError(error);
        } finally {
            setStartBusy(false);
        }
    }

    function resetBattleSurface() {
        dom.chatBody.innerHTML = '';
        dom.replyInput.value = '';
        dom.charCount.textContent = '0/500';
        lastScammerBubble = null;
    }

    async function handleSendReply() {
        const text = dom.replyInput.value.trim();
        if (!battleState || battleState.is_over || isBusy) return;
        if (!text) {
            showToast('先写下你的回复再发送', 'warning');
            dom.replyInput.focus();
            return;
        }

        const analyzedBubble = lastScammerBubble;
        appendPlayerMessage(text);
        dom.replyInput.value = '';
        dom.charCount.textContent = '0/500';
        setComposerEnabled(false);
        isBusy = true;

        try {
            const nextState = await BattleAPI.reply(battleState.battle_id, text);
            battleState = nextState;
            renderScammerProfile(nextState);
            updateHud(nextState, true);
            renderSignalPreview(nextState.signals);

            if (nextState.scammer_msg) {
                await renderScammerTurn(nextState.scammer_msg, nextState.scammer);
            }

            if (nextState.feedback) {
                await revealFeedback(nextState.feedback, analyzedBubble);
            }

            if (nextState.is_over && nextState.result) {
                await delay(850);
                renderResult(nextState.result);
                return;
            }

            setComposerEnabled(true);
            dom.replyInput.focus();
        } catch (error) {
            handleApiError(error);
            setComposerEnabled(true);
        } finally {
            isBusy = false;
        }
    }

    async function renderScammerTurn(message, scammer) {
        const typingRow = showTypingIndicator();
        await delay(prefersReducedMotion() ? 50 : 520);
        typingRow.remove();
        const lines = String(message || '').split('\n').filter(line => line.trim());
        for (const line of lines) {
            const bubble = appendScammerMessage('', scammer);
            await typeText(bubble.querySelector('.message-text'), line);
            lastScammerBubble = bubble;
            scrollChatToBottom();
            await delay(prefersReducedMotion() ? 0 : 160);
        }
    }

    function appendScammerMessage(text, scammer) {
        const row = document.createElement('div');
        row.className = 'chat-row row-scammer';
        row.innerHTML = `
            <div class="chat-avatar" aria-hidden="true">${escapeHtml(scammer?.avatar || '')}</div>
            <div class="chat-bubble bubble-scammer"><span class="message-text">${escapeHtml(text)}</span><span class="scanline" aria-hidden="true"></span></div>`;
        dom.chatBody.appendChild(row);
        scrollChatToBottom();
        return row.querySelector('.bubble-scammer');
    }

    function appendPlayerMessage(text) {
        const row = document.createElement('div');
        row.className = 'chat-row row-player';
        row.innerHTML = `<div class="chat-bubble bubble-player">${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;
        dom.chatBody.appendChild(row);
        scrollChatToBottom();
    }

    function appendNarration(text) {
        const row = document.createElement('div');
        row.className = 'chat-row row-narration';
        row.innerHTML = `<div class="chat-bubble bubble-narration"><i class="bi bi-broadcast" aria-hidden="true"></i> ${escapeHtml(text)}</div>`;
        dom.chatBody.appendChild(row);
    }

    function showTypingIndicator() {
        const row = document.createElement('div');
        row.className = 'chat-row row-scammer typing-row';
        row.innerHTML = `
            <div class="chat-avatar" aria-hidden="true">${escapeHtml(battleState?.scammer?.avatar || '')}</div>
            <div class="typing-indicator"><span class="typing-label">对方正在输入…</span><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>`;
        dom.chatBody.appendChild(row);
        scrollChatToBottom();
        return row;
    }

    async function typeText(target, text) {
        const characters = Array.from(String(text));
        if (prefersReducedMotion()) {
            target.textContent = text;
            return;
        }
        const cursor = document.createElement('span');
        cursor.className = 'typing-cursor';
        target.appendChild(cursor);
        for (const character of characters) {
            cursor.before(document.createTextNode(character));
            await delay(25 + Math.random() * 15);
        }
        cursor.remove();
    }

    async function revealFeedback(feedback, analyzedBubble) {
        const scanner = feedback.scanner || [];
        if (analyzedBubble) {
            analyzedBubble.classList.add('scanning');
            await delay(prefersReducedMotion() ? 30 : 900);
            analyzedBubble.classList.remove('scanning');
            highlightSignals(analyzedBubble, scanner);
        }

        const rating = normalizeRating(feedback.rating);
        const ratingMeta = RATING_MAP[rating];
        const defensePoint = Number(feedback.defense_point || 0);
        const panel = document.createElement('section');
        panel.className = 'feedback-panel';
        panel.setAttribute('aria-label', '本轮防御反馈');
        panel.innerHTML = `
            <div class="feedback-head">
                <span class="feedback-label"><i class="bi bi-cpu" aria-hidden="true"></i> 实时防御判定</span>
                <span class="intent-chip">意图识别 · ${escapeHtml(feedback.intent_label || feedback.intent || '未识别')}</span>
                <span class="feedback-rating ${ratingMeta.className}">${rating} · ${escapeHtml(feedback.rating_label || ratingMeta.label)}</span>
                <span class="point-chip ${defensePoint >= 0 ? 'positive' : 'negative'}">${defensePoint >= 0 ? '+' : ''}${escapeHtml(defensePoint)} 防御分</span>
            </div>
            ${feedback.comment ? `<p class="feedback-comment">${escapeHtml(feedback.comment)}</p>` : ''}
            <div class="scanner-section">
                <div class="scanner-title"><i class="bi bi-search" aria-hidden="true"></i> 诈骗信号扫描</div>
                <div class="signal-list">${renderSignalCards(scanner)}</div>
            </div>`;
        dom.chatBody.appendChild(panel);
        panel.querySelectorAll('.signal-card').forEach((card, index) => {
            card.style.animationDelay = `${index * 80}ms`;
        });
        panel.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'end' });
    }

    function renderSignalCards(signals) {
        if (!signals.length) return '<p class="scanner-empty">本轮未扫描到明确关键词，仍需结合上下文判断。</p>';
        return signals.map(signal => {
            const severity = normalizeSeverity(signal.severity);
            const severityLabel = severity === 'high' ? '高危' : severity === 'mid' ? '可疑' : '提示';
            return `
                <article class="signal-card">
                    <span class="signal-keyword">${escapeHtml(signal.keyword || signal.label || '可疑信号')}</span>
                    <span class="severity-badge severity-${severity}">${severityLabel}</span>
                    <span class="signal-explain">${escapeHtml(signal.explain || signal.label || '')}</span>
                </article>`;
        }).join('');
    }

    function highlightSignals(bubble, signals) {
        const textElement = bubble.querySelector('.message-text');
        if (!textElement) return;
        let safeText = escapeHtml(textElement.textContent || '');
        const keywords = signals.map(signal => String(signal.keyword || '')).filter(Boolean).sort((a, b) => b.length - a.length);
        keywords.forEach(keyword => {
            const safeKeyword = escapeHtml(keyword);
            safeText = safeText.split(safeKeyword).join(`<mark>${safeKeyword}</mark>`);
        });
        textElement.innerHTML = safeText;
    }

    function renderScammerProfile(state) {
        const scammer = state.scammer || {};
        const strategy = STRATEGY_MAP[state.scammer_state?.strategy] || { emoji: '🛡️', label: '试探' };
        dom.scammerAvatar.textContent = scammer.avatar || '';
        dom.scammerName.textContent = scammer.name || '未知对手';
        dom.scammerTitle.textContent = scammer.title || '身份待核验';
        dom.scammerSignature.textContent = scammer.signature || '对方没有留下签名';
        dom.strategyChip.innerHTML = `<i class="bi bi-shield-exclamation" aria-hidden="true"></i><span>当前策略：${escapeHtml(strategy.emoji)} ${escapeHtml(strategy.label)} · ${escapeHtml(state.scammer_state?.strategy_label || '')}</span>`;
    }

    function updateHud(state, animateScore) {
        const hp = clamp(Number(state.hp || 0), 0, Number(state.max_hp || 100));
        const maxHp = Math.max(Number(state.max_hp || 100), 1);
        const mood = clamp(Number(state.scammer_state?.mood || 0), 0, 100);
        const score = Number(state.score || 0);
        const rating = normalizeRating(state.feedback?.rating || ratingFromScore(score));
        dom.hpValue.textContent = `${hp}/${maxHp}`;
        dom.hpFill.style.transform = `scaleX(${hp / maxHp})`;
        dom.hpFill.classList.toggle('hp-mid', hp / maxHp <= 0.6 && hp / maxHp > 0.3);
        dom.hpFill.classList.toggle('hp-low', hp / maxHp <= 0.3);
        dom.moodValue.textContent = String(mood);
        dom.moodFill.style.transform = `scaleX(${mood / 100})`;
        dom.moodFill.classList.toggle('mood-soft', mood <= 45);
        dom.moodIcon.className = `bi ${mood <= 45 ? 'bi-shield-slash-fill' : 'bi-heart-pulse-fill'}`;
        dom.roundValue.textContent = String(state.round_no || 1);
        dom.totalRounds.textContent = String(state.total_rounds || 1);
        dom.ratingChip.className = `rating-chip ${RATING_MAP[rating].className}`;
        dom.ratingChip.textContent = rating;
        if (animateScore) countScoreTo(score); else dom.scoreValue.textContent = String(score);
    }

    function renderSignalPreview(signals) {
        if (!signals || !signals.length) {
            dom.signalPreview.classList.add('d-none');
            dom.signalPreview.innerHTML = '';
            return;
        }
        dom.signalPreview.classList.remove('d-none');
        dom.signalPreview.innerHTML = signals.map(signal => `<button class="signal-preview-chip" type="button" title="${escapeHtml(signal.explain || signal.label || '')}"><i class="bi bi-exclamation-diamond" aria-hidden="true"></i> ${escapeHtml(signal.keyword || signal.label || '可疑信号')}</button>`).join('');
        dom.signalPreview.querySelectorAll('button').forEach(button => {
            button.addEventListener('click', () => {
                if (!lastScammerBubble) return;
                lastScammerBubble.classList.remove('scanning');
                requestAnimationFrame(() => lastScammerBubble.classList.add('scanning'));
                lastScammerBubble.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'center' });
            });
        });
    }

    function countScoreTo(target) {
        const start = Number(dom.scoreValue.textContent) || 0;
        const difference = target - start;
        if (prefersReducedMotion() || difference === 0) {
            dom.scoreValue.textContent = String(target);
            return;
        }
        const startedAt = performance.now();
        const tick = now => {
            const progress = Math.min((now - startedAt) / 450, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            dom.scoreValue.textContent = String(Math.round(start + difference * eased));
            if (progress < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    }

    async function handleAbortBattle() {
        if (!battleState || battleState.is_over || isBusy) return;
        if (!window.confirm('确定结束当前对战并生成中途退出报告吗？')) return;
        isBusy = true;
        setComposerEnabled(false);
        try {
            const state = await BattleAPI.abort(battleState.battle_id);
            battleState = state;
            if (state.result) renderResult(state.result);
            else switchView('home');
        } catch (error) {
            handleApiError(error);
        } finally {
            isBusy = false;
        }
    }

    function renderResult(result) {
        const type = RESULT_TYPE_MAP[result.type] || { emoji: '📋', title: result.title || '对战结束' };
        const rating = normalizeRating(result.rating);
        const ratingMeta = RATING_MAP[rating];
        const summaries = (result.summary || []).map(item => `<li><i class="bi bi-check-circle-fill" aria-hidden="true"></i><span>${escapeHtml(item)}</span></li>`).join('');
        const lessons = (result.lessons || []).map(lesson => `
            <article class="lesson-card">
                <div class="lesson-point"><i class="bi bi-info-circle-fill" aria-hidden="true"></i>${escapeHtml(lesson.point)}</div>
                <p class="lesson-rule">${escapeHtml(lesson.rule)}</p>
            </article>`).join('');

        dom.resultCard.className = `result-card result-${safeResultType(result.type)} animate-in visible`;
        dom.resultCard.innerHTML = `
            <div class="result-banner">${escapeHtml(type.emoji)} ${escapeHtml(result.title || type.title)}</div>
            <div class="result-hero">
                <div class="result-rating">${rating}</div>
                <h2 id="resultTitle" class="result-title">${escapeHtml(type.title)}</h2>
                <div class="result-label">${escapeHtml(result.rating_label || ratingMeta.label)}</div>
                <p class="result-score">总分 <strong>${escapeHtml(result.score || 0)}</strong></p>
            </div>
            <div class="result-body">
                <section class="report-section">
                    <h3 class="report-heading"><i class="bi bi-clipboard2-check-fill" aria-hidden="true"></i> 本局复盘</h3>
                    <ul class="summary-list">${summaries || '<li><i class="bi bi-check-circle-fill" aria-hidden="true"></i><span>本局对话已完成分析。</span></li>'}</ul>
                </section>
                <section class="report-section">
                    <h3 class="report-heading"><i class="bi bi-journal-bookmark-fill" aria-hidden="true"></i> 防骗法则</h3>
                    <div class="lessons-grid">${lessons || '<article class="lesson-card"><div class="lesson-point"><i class="bi bi-info-circle-fill" aria-hidden="true"></i>保持核验</div><p class="lesson-rule">涉及资金与身份信息时，通过官方渠道独立核实。</p></article>'}</div>
                </section>
                ${result.achievement ? `<section class="report-section achievement-block"><div class="achievement-icon"><i class="bi bi-trophy-fill" aria-hidden="true"></i></div><div><small>解锁成就</small><strong>${escapeHtml(result.achievement)}</strong></div></section>` : ''}
            </div>
            <div class="result-actions">
                <button id="resultReplayBtn" class="result-btn result-btn-primary" type="button"><i class="bi bi-arrow-repeat" aria-hidden="true"></i> 再来一局</button>
                <button id="resultChangeBtn" class="result-btn result-btn-secondary" type="button"><i class="bi bi-grid" aria-hidden="true"></i> 换个剧本</button>
                <a href="index.html#training" class="result-btn result-btn-secondary"><i class="bi bi-house" aria-hidden="true"></i> 返回首页</a>
            </div>`;
        switchView('result');
        dom.resultCard.querySelector('#resultReplayBtn').addEventListener('click', async () => {
            await cleanupBattle();
            selectScenario(currentScenario?.id);
        });
        dom.resultCard.querySelector('#resultChangeBtn').addEventListener('click', async () => {
            await cleanupBattle();
            currentScenario = null;
            switchView('home');
        });
    }

    async function cleanupBattle() {
        if (battleState?.battle_id) await BattleAPI.cleanup(battleState.battle_id);
        battleState = null;
    }

    function switchView(name) {
        Object.values(dom.views).forEach(view => view.classList.remove('active'));
        const target = dom.views[name];
        if (!target) return;
        target.classList.add('active');
        target.querySelectorAll('.animate-in').forEach(element => {
            element.classList.remove('visible');
            requestAnimationFrame(() => element.classList.add('visible'));
        });
        document.body.classList.toggle('in-battle', name === 'battle');
        dom.navRestartBtn.classList.toggle('d-none', name !== 'battle');
        window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
    }

    function setComposerEnabled(enabled) {
        dom.replyInput.disabled = !enabled;
        dom.sendReplyBtn.disabled = !enabled;
        dom.replyInput.placeholder = enabled ? '输入你的真实回复…' : '正在分析对话…';
    }

    function setStartBusy(busy) {
        isBusy = busy;
        dom.startBattleBtn.disabled = busy;
        dom.startBattleBtn.innerHTML = busy
            ? '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> 正在接入…'
            : '<i class="bi bi-lightning-charge-fill" aria-hidden="true"></i> 开始对战';
    }

    function handleApiError(error, loadingScenarios = false) {
        if (error?.isConnectionError?.()) {
            showConnectionFailure();
            return;
        }
        const message = error?.message || '请求失败，请稍后重试';
        if (loadingScenarios) {
            dom.scriptGrid.innerHTML = `<div class="col-12 loading-state"><i class="bi bi-exclamation-triangle" aria-hidden="true"></i><p>${escapeHtml(message)}</p></div>`;
        } else {
            showToast(message, 'error');
        }
    }

    function showConnectionFailure() {
        dom.connFailOverlay.classList.remove('d-none');
        dom.retryConnBtn.focus();
    }

    async function handleRetryConnection() {
        dom.retryConnBtn.disabled = true;
        dom.retryConnBtn.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> 重试中…';
        const connected = await BattleAPI.ping();
        dom.retryConnBtn.disabled = false;
        dom.retryConnBtn.innerHTML = '<i class="bi bi-arrow-clockwise" aria-hidden="true"></i> 重试连接';
        if (!connected) {
            showToast('仍无法连接，请确认后端已启动', 'error');
            return;
        }
        dom.connFailOverlay.classList.add('d-none');
        await loadScenarios();
        switchView('home');
        showToast('游戏服务器已连接', 'success');
    }

    function showToast(message, type = 'info') {
        const item = document.createElement('div');
        item.className = `toast-item toast-${safeToastType(type)}`;
        item.textContent = String(message);
        dom.toast.appendChild(item);
        setTimeout(() => {
            item.classList.add('toast-out');
            setTimeout(() => item.remove(), 320);
        }, 3000);
    }

    function scrollChatToBottom() {
        requestAnimationFrame(() => {
            dom.chatBody.scrollTop = dom.chatBody.scrollHeight;
        });
    }

    function normalizeRating(rating) {
        const value = String(rating || 'D').toUpperCase();
        return RATING_MAP[value] ? value : 'D';
    }

    function ratingFromScore(score) {
        if (score >= 90) return 'S';
        if (score >= 75) return 'A';
        if (score >= 60) return 'B';
        if (score >= 40) return 'C';
        if (score >= 20) return 'D';
        return 'F';
    }

    function normalizeSeverity(severity) {
        const value = String(severity || 'low').toLowerCase();
        if (value === 'high') return 'high';
        if (value === 'mid' || value === 'medium') return 'mid';
        return 'low';
    }

    function safeIcon(icon) {
        const value = String(icon || 'bi-chat-square-text');
        return /^bi-[a-z0-9-]+$/i.test(value) ? value : 'bi-chat-square-text';
    }

    function safeResultType(type) {
        const value = String(type || 'give_up');
        return RESULT_TYPE_MAP[value] ? value : 'give_up';
    }

    function safeToastType(type) {
        return ['info', 'error', 'success', 'warning'].includes(type) ? type : 'info';
    }

    function clamp(value, minimum, maximum) {
        return Math.min(Math.max(value, minimum), maximum);
    }

    function prefersReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    function delay(milliseconds) {
        return new Promise(resolve => setTimeout(resolve, milliseconds));
    }

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, character => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[character]));
    }

    function startStarCanvas() {
        const canvas = document.getElementById('starCanvas');
        if (!canvas) return;
        const context = canvas.getContext('2d');
        let stars = [];
        let animationId = null;

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            initializeStars();
        }

        function initializeStars() {
            const count = Math.floor((canvas.width * canvas.height) / 12000);
            stars = [];
            for (let index = 0; index < count; index += 1) {
                stars.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height,
                    radius: Math.random() * 1.2 + 0.3,
                    alpha: Math.random() * 0.6 + 0.2,
                    twinkleSpeed: Math.random() * 0.02 + 0.005,
                    twinkleDirection: Math.random() > 0.5 ? 1 : -1
                });
            }
        }

        function draw() {
            context.clearRect(0, 0, canvas.width, canvas.height);
            for (const star of stars) {
                star.alpha += star.twinkleSpeed * star.twinkleDirection;
                if (star.alpha > 0.9 || star.alpha < 0.15) star.twinkleDirection *= -1;
                context.beginPath();
                context.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
                context.fillStyle = `rgba(200, 220, 255, ${star.alpha})`;
                context.fill();
            }
            animationId = requestAnimationFrame(draw);
        }

        resize();
        window.addEventListener('resize', resize);
        draw();
    }
})();
