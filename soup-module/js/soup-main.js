/* ============================================================
 * soup-main.js - 反诈海龟汤主逻辑
 * 视图切换（谜题列表 / 解谜 / 汤底揭晓）+ 问答流渲染 + 线索进度
 * ============================================================ */

(function () {
    'use strict';

    // ------------------ 状态 ------------------
    let puzzlesCache = [];
    let currentSession = null;      // 后端返回的会话数据（含 session_id）
    let isAsking = false;           // 防重复提交

    // ------------------ DOM ------------------
    const dom = {};

    function cacheDom() {
        dom.puzzleGrid = document.getElementById('puzzleGrid');
        dom.navExitBtn = document.getElementById('navExitBtn');
        dom.qaBody = document.getElementById('qaBody');
        dom.askInput = document.getElementById('askInput');
        dom.askSendBtn = document.getElementById('askSendBtn');
        dom.hintBtn = document.getElementById('hintBtn');
        dom.revealBtn = document.getElementById('revealBtn');
        dom.surfaceCard = document.getElementById('surfaceCard');
        dom.surfaceTitle = document.getElementById('surfaceTitle');
        dom.surfaceText = document.getElementById('surfaceText');
        dom.surfaceToggle = document.getElementById('surfaceToggle');
        dom.clueNum = document.getElementById('clueNum');
        dom.clueTotal = document.getElementById('clueTotal');
        dom.clueFill = document.getElementById('clueFill');
        dom.askCountEl = document.getElementById('askCount');
        dom.hintCountEl = document.getElementById('hintCount');
        dom.resultCard = document.getElementById('resultCard');
        dom.connFailOverlay = document.getElementById('connFailOverlay');
        dom.retryConnBtn = document.getElementById('retryConnBtn');
        dom.toast = document.getElementById('toast');
    }

    function bindEvents() {
        dom.navExitBtn.addEventListener('click', handleExit);
        dom.askSendBtn.addEventListener('click', handleAsk);
        dom.askInput.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.isComposing) handleAsk();
        });
        dom.hintBtn.addEventListener('click', handleHint);
        dom.revealBtn.addEventListener('click', handleReveal);
        dom.surfaceToggle.addEventListener('click', () => {
            const collapsed = dom.surfaceText.classList.toggle('collapsed');
            dom.surfaceToggle.innerHTML = collapsed
                ? '<i class="bi bi-chevron-down"></i> 展开汤面'
                : '<i class="bi bi-chevron-up"></i> 收起汤面';
        });
        dom.retryConnBtn.addEventListener('click', handleRetryConn);
    }

    // ------------------ 视图切换 ------------------
    // 主页滚动位置记忆：离开列表页时记录，返回时恢复原浏览位置（不再强制跳回顶部）
    let homeScrollY = 0;

    function switchView(name) {
        const homeView = document.getElementById('view-home');
        // 离开 home 视图前记录当前滚动位置
        if (homeView && homeView.classList.contains('active')) {
            homeScrollY = window.scrollY;
        }
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${name}`).classList.add('active');
        // 导航栏按钮：仅解谜视图显示退出
        dom.navExitBtn.classList.toggle('d-none', name !== 'game');
        if (name === 'home' && homeScrollY > 0) {
            // 恢复离开列表页时的滚动位置（rAF 等视图 display 生效后再恢复，避免被布局修正覆盖）
            requestAnimationFrame(() => window.scrollTo({ top: homeScrollY, behavior: 'auto' }));
        } else {
            // 其他视图：滚动到顶
            window.scrollTo({ top: 0, behavior: 'auto' });
        }
    }

    // ------------------ 谜题列表 ------------------
    async function loadPuzzles() {
        try {
            const puzzles = await SoupAPI.getPuzzles();
            puzzlesCache = puzzles;
            renderPuzzleGrid(puzzles);
        } catch (err) {
            if (err.isConnectionError && err.isConnectionError()) {
                showConnFail();
            } else if (err.status === 404) {
                // 后端已连接但版本过旧：运行中的后端是海龟汤上线前的旧进程（uvicorn 不会热加载新代码）
                dom.puzzleGrid.innerHTML = `
                    <div class="col-12 text-center py-5">
                        <i class="bi bi-arrow-repeat" style="font-size:2.5rem;color:#d97706;"></i>
                        <p class="mt-3" style="font-weight:700;color:#b45309;">后端服务版本过旧，未加载海龟汤模块</p>
                        <p class="text-muted" style="font-size:0.9rem;">请重启后端服务：在运行 uvicorn 的终端按 Ctrl+C 停止，<br>再重新执行启动命令后刷新本页</p>
                    </div>`;
            } else {
                dom.puzzleGrid.innerHTML = `
                    <div class="col-12 text-center py-5">
                        <i class="bi bi-exclamation-triangle" style="font-size:2.5rem;color:#ef4444;"></i>
                        <p class="mt-3 text-danger">${escapeHtml(err.message)}</p>
                    </div>`;
            }
        }
    }

    function renderPuzzleGrid(puzzles) {
        if (!puzzles || puzzles.length === 0) {
            dom.puzzleGrid.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-inbox" style="font-size:2.5rem;color:var(--gray-400,#94a3b8);"></i>
                    <p class="mt-3 text-muted">暂无可用谜题</p>
                </div>`;
            return;
        }

        dom.puzzleGrid.innerHTML = puzzles.map((p, idx) => {
            const stagger = (idx % 4) + 1;
            const tags = (p.tags || []).map(t => `<span class="puzzle-tag">${escapeHtml(t)}</span>`).join('');
            return `
                <div class="col-md-6 col-lg-4 animate-in stagger-${stagger}">
                    <div class="puzzle-card" data-id="${p.id}">
                        <div class="puzzle-card-cover">
                            <img src="${p.cover}" alt="${escapeHtml(p.name)}" loading="lazy"
                                 onerror="this.style.display='none';">
                            <div class="puzzle-card-cover-overlay"></div>
                            <span class="puzzle-difficulty">难度 ${p.difficulty}</span>
                        </div>
                        <div class="puzzle-card-body">
                            <div class="puzzle-icon"><i class="bi ${p.icon}"></i></div>
                            <h3>${escapeHtml(p.name)}</h3>
                            <p class="puzzle-desc">${escapeHtml(p.description)}</p>
                            <div class="puzzle-tags">${tags}</div>
                            <button class="puzzle-enter-btn">
                                <i class="bi bi-search"></i> 开始推理
                            </button>
                        </div>
                    </div>
                </div>`;
        }).join('');

        // 触发入场动画
        requestAnimationFrame(() => {
            dom.puzzleGrid.querySelectorAll('.animate-in').forEach(el => el.classList.add('visible'));
        });

        // 绑定点击
        dom.puzzleGrid.querySelectorAll('.puzzle-card').forEach(card => {
            card.addEventListener('click', () => {
                const pid = card.dataset.id;
                const p = puzzlesCache.find(x => x.id === pid);
                if (p) selectPuzzle(p);
            });
        });
    }

    // ------------------ 解谜流程 ------------------
    async function selectPuzzle(puzzle) {
        try {
            const state = await SoupAPI.startPuzzle(puzzle.id);
            currentSession = state;
            enterGameView(state);
        } catch (err) {
            if (err.isConnectionError && err.isConnectionError()) {
                showConnFail();
            } else if (err.status === 404) {
                // 后端已连接但版本过旧（无 /api/soup 路由）
                showToast('后端版本过旧，未加载海龟汤模块，请重启后端服务');
            } else {
                showToast(err.message);
            }
        }
    }

    function enterGameView(state) {
        // 汤面
        dom.surfaceTitle.innerHTML = `<i class="bi bi-file-earmark-text"></i> 汤面 · ${escapeHtml(state.puzzle_name)}`;
        dom.surfaceText.innerHTML = state.soup_surface
            .map(p => `<p>${escapeHtml(p)}</p>`).join('');
        dom.surfaceText.classList.remove('collapsed');
        dom.surfaceToggle.innerHTML = '<i class="bi bi-chevron-up"></i> 收起汤面';

        // 清空问答区 + 开场白
        dom.qaBody.innerHTML = '';
        appendHostBubble(
            '我是本案主持人。你可以向我提出任何“是/否”问题，我会如实回答。',
            'hint', '侦探事务所'
        );

        // 线索进度与按钮复位
        updateProgress(state);
        setToolsEnabled(true);
        dom.askInput.value = '';
        dom.askInput.disabled = false;

        switchView('game');
        setTimeout(() => dom.askInput.focus(), 100);
    }

    async function handleAsk() {
        if (!currentSession || isAsking) return;
        const text = dom.askInput.value.trim();
        if (!text) { showToast('请输入你的问题'); return; }

        isAsking = true;
        dom.askSendBtn.disabled = true;
        dom.askInput.value = '';

        // 立即渲染玩家问题
        appendPlayerBubble(text);

        try {
            const result = await SoupAPI.askQuestion(currentSession.session_id, text);
            appendHostBubble(result.reply, result.answer, '主持人');
            updateProgress(result);
        } catch (err) {
            if (err.isConnectionError && err.isConnectionError()) {
                showConnFail();
            } else {
                appendHostBubble('（连接出了点问题：' + err.message + '）', 'irrelevant', '系统');
            }
        } finally {
            isAsking = false;
            dom.askSendBtn.disabled = false;
            dom.askInput.focus();
        }
    }

    async function handleHint() {
        if (!currentSession || isAsking) return;
        isAsking = true;
        dom.hintBtn.disabled = true;
        try {
            const result = await SoupAPI.getHint(currentSession.session_id);
            appendHostBubble('💡 提示：' + result.hint, 'hint', '侦探事务所');
            if (dom.hintCountEl) dom.hintCountEl.textContent = result.hints_used;
            showToast('已发放提示（会影响最终评级）');
        } catch (err) {
            if (err.isConnectionError && err.isConnectionError()) {
                showConnFail();
            } else {
                showToast(err.message);
            }
        } finally {
            isAsking = false;
            dom.hintBtn.disabled = false;
            dom.askInput.focus();
        }
    }

    async function handleReveal() {
        if (!currentSession) return;
        if (!confirm('确定要揭晓汤底吗？揭晓后将无法继续提问本局。')) return;

        try {
            const finalState = await SoupAPI.revealAnswer(currentSession.session_id);
            renderResult(finalState);
            switchView('result');
        } catch (err) {
            if (err.isConnectionError && err.isConnectionError()) {
                showConnFail();
            } else {
                showToast(err.message);
            }
        }
    }

    function handleExit() {
        if (!confirm('确定要退出当前解谜吗？进度将不会保存。')) return;
        // 先切视图给即时反馈，后端会话清理放后台执行，不阻塞 UI
        if (currentSession) {
            SoupAPI.exitSession(currentSession.session_id).catch(() => { /* 静默：退出时不再阻塞用户 */ });
            currentSession = null;
        }
        switchView('home');
        // 谜题列表数据未变化，卡片 DOM 仍在，无需重新拉取重渲染（仅在缓存为空时兜底）
        if (!puzzlesCache.length) loadPuzzles();
    }

    // ------------------ 渲染工具 ------------------
    function updateProgress(data) {
        const revealed = data.revealed_count ?? 0;
        const total = data.total_clues ?? 0;
        const pct = total > 0 ? Math.round((revealed / total) * 100) : 0;
        dom.clueNum.textContent = revealed;
        dom.clueTotal.textContent = total;
        dom.clueFill.style.width = pct + '%';
        if (dom.askCountEl) dom.askCountEl.textContent = data.ask_count ?? 0;
        if (dom.hintCountEl) dom.hintCountEl.textContent = data.hints_used ?? 0;
    }

    function setToolsEnabled(enabled) {
        dom.askSendBtn.disabled = !enabled;
        dom.hintBtn.disabled = !enabled;
        dom.revealBtn.disabled = !enabled;
    }

    const ANSWER_BADGES = {
        yes: '<span class="qa-answer-badge badge-yes"><i class="bi bi-check-lg"></i> 是</span>',
        no: '<span class="qa-answer-badge badge-no"><i class="bi bi-x-lg"></i> 否</span>',
        irrelevant: '<span class="qa-answer-badge badge-irrelevant"><i class="bi bi-slash-circle"></i> 无关</span>',
        repeat: '<span class="qa-answer-badge badge-repeat"><i class="bi bi-arrow-repeat"></i> 已问过</span>',
        hint: '<span class="qa-answer-badge badge-hint"><i class="bi bi-lightbulb"></i> 提示</span>',
    };

    function appendPlayerBubble(text) {
        const row = document.createElement('div');
        row.className = 'qa-row qa-player';
        row.innerHTML = `
            <div class="qa-avatar"><i class="bi bi-person-fill" style="color:#34d399;"></i></div>
            <div class="qa-content">
                <span class="qa-name">你</span>
                <div class="qa-bubble">${escapeHtml(text)}</div>
            </div>`;
        dom.qaBody.appendChild(row);
        scrollToBottom();
    }

    function appendHostBubble(text, answerType, name) {
        const row = document.createElement('div');
        row.className = 'qa-row qa-host' + (answerType === 'hint' ? ' qa-hint-tip' : '');
        const badge = ANSWER_BADGES[answerType] || '';
        row.innerHTML = `
            <div class="qa-avatar">🕵️</div>
            <div class="qa-content">
                <span class="qa-name">${escapeHtml(name || '主持人')}</span>
                <div class="qa-bubble">${escapeHtml(text)}</div>
                ${badge}
            </div>`;
        dom.qaBody.appendChild(row);
        scrollToBottom();
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            dom.qaBody.scrollTop = dom.qaBody.scrollHeight;
        });
    }

    // ------------------ 汤底揭晓 ------------------
    function renderResult(state) {
        const res = state.result;
        if (!res) return;

        const missedHtml = (res.missed_clues || []).length > 0 ? `
            <div class="result-section">
                <h3><i class="bi bi-eyeglasses"></i> 你遗漏的线索</h3>
                <div class="missed-clue-list">
                    ${res.missed_clues.map(c => `
                        <div class="missed-clue-item">
                            <span class="missed-clue-answer ${c.answer}">${c.answer === 'yes' ? '是' : '否'}</span>${escapeHtml(c.answer_text)}
                        </div>`).join('')}
                </div>
            </div>` : '';

        const lessonsHtml = (res.lessons || []).map(l => `
            <div class="lesson-card">
                <div class="lesson-icon"><i class="bi bi-shield-check"></i></div>
                <div>
                    <h4>${escapeHtml(l.point)}</h4>
                    <p>${escapeHtml(l.rule)}</p>
                </div>
            </div>`).join('');

        dom.resultCard.innerHTML = `
            <div class="result-hero">
                <div class="rating-badge rating-${res.rating}">${res.rating}</div>
                <h2>${escapeHtml(state.puzzle_name)} · 汤底揭晓</h2>
                <div class="rating-label">侦探评级：${escapeHtml(res.rating_label)}</div>
                <div class="result-stats">
                    <div class="result-stat"><div class="num">${res.score}</div><div class="label">推理得分</div></div>
                    <div class="result-stat"><div class="num">${res.revealed_count}/${res.total_clues}</div><div class="label">揭示线索</div></div>
                    <div class="result-stat"><div class="num">${res.ask_count}</div><div class="label">提问次数</div></div>
                    <div class="result-stat"><div class="num">${res.hints_used}</div><div class="label">使用提示</div></div>
                </div>
            </div>
            <div class="result-section">
                <h3><i class="bi bi-book-half"></i> 汤底 · 案件还原</h3>
                ${res.soup_bottom.map(p => `<p>${escapeHtml(p)}</p>`).join('')}
            </div>
            ${missedHtml}
            <div class="result-section">
                <h3><i class="bi bi-shield-fill-check"></i> 反诈要点</h3>
                ${lessonsHtml}
            </div>
            <div class="result-actions">
                <button class="btn-play-again" id="playAgainBtn"><i class="bi bi-arrow-repeat"></i> 再来一局</button>
                <a href="soup.html" class="btn-back-list"><i class="bi bi-grid"></i> 返回谜题列表</a>
            </div>`;

        document.getElementById('playAgainBtn').addEventListener('click', () => {
            currentSession = null;
            switchView('home');
            // 谜题列表数据未变化，无需重新拉取重渲染
            if (!puzzlesCache.length) loadPuzzles();
        });
    }

    // ------------------ 通用工具 ------------------
    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function showConnFail() {
        dom.connFailOverlay.classList.remove('d-none');
    }

    async function handleRetryConn() {
        const alive = await SoupAPI.ping();
        if (alive) {
            dom.connFailOverlay.classList.add('d-none');
            loadPuzzles();
        } else {
            showToast('仍未连接到服务器，请确认后端已启动');
        }
    }

    function showToast(message) {
        if (!dom.toast) return;
        const item = document.createElement('div');
        item.className = 'toast-item';
        item.innerHTML = `<i class="bi bi-info-circle"></i> ${escapeHtml(message)}`;
        dom.toast.appendChild(item);
        setTimeout(() => item.remove(), 3200);
    }

    // ------------------ 初始化 ------------------
    function init() {
        cacheDom();
        bindEvents();
        loadPuzzles();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
