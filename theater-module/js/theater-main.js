/* ============================================================
 * theater-main.js - 入口编排
 * 视图切换、表单校验、场景卡绑定、结局渲染、错误遮罩
 * ============================================================ */

(function () {
    // ------------------ DOM 引用 ------------------
    const dom = {
        // 视图
        views: {
            home: document.getElementById('view-home'),
            setup: document.getElementById('view-setup'),
            game: document.getElementById('view-game'),
            ending: document.getElementById('view-ending')
        },
        // 导航
        navRestartBtn: document.getElementById('navRestartBtn'),
        // 首页
        scenarioGrid: document.getElementById('scenarioGrid'),
        statScenariosNum: document.getElementById('statScenarios'),
        // 角色设定
        setupScenarioIcon: document.getElementById('setupScenarioIcon'),
        setupScenarioName: document.getElementById('setupScenarioName'),
        setupScenarioDesc: document.getElementById('setupScenarioDesc'),
        setupScenarioTags: document.getElementById('setupScenarioTags'),
        inputName: document.getElementById('inputName'),
        nameFeedback: document.getElementById('nameFeedback'),
        setupBackBtn: document.getElementById('setupBackBtn'),
        startGameBtn: document.getElementById('startGameBtn'),
        // 游戏
        gameScenarioName: document.getElementById('gameScenarioName'),
        chatBody: document.getElementById('chatBody'),
        choiceBar: document.getElementById('choiceBar'),
        alertBtn: document.getElementById('alertBtn'),
        exitGameBtn: document.getElementById('exitGameBtn'),
        autoHint: document.getElementById('autoHint'),
        // 结局
        endingCard: document.getElementById('endingCard'),
        // 错误遮罩
        connFailOverlay: document.getElementById('connFailOverlay'),
        retryConnBtn: document.getElementById('retryConnBtn'),
        // Toast
        toast: document.getElementById('toast')
    };

    // 当前选中的场景
    let currentScenario = null;
    // 缓存场景列表
    let scenariosCache = [];

    // 结局分类中文标签
    const ENDING_LABELS = {
        bad: '糟糕结局',
        tragic: '悲剧结局',
        normal: '普通结局',
        perfect: '完美结局',
        hidden: '隐藏结局',
        special: '特殊结局',
        accident: '意外结局',
        redemption: '救赎结局'
    };

    // 结局图标
    const ENDING_ICONS = {
        bad: 'bi-emoji-frown',
        tragic: 'bi-emoji-dizzy',
        normal: 'bi-emoji-neutral',
        perfect: 'bi-emoji-star-eyes',
        hidden: 'bi-gem',
        special: 'bi-award',
        accident: 'bi-emoji-surprised',
        redemption: 'bi-shield-check'
    };

    // ------------------ 初始化 ------------------
    document.addEventListener('DOMContentLoaded', init);

    async function init() {
        bindEvents();
        startStarCanvas();
        GameState.init({
            chatBody: dom.chatBody,
            choiceBar: dom.choiceBar,
            alertBtn: dom.alertBtn,
            autoHint: dom.autoHint,
            gameScenarioName: dom.gameScenarioName
        });

        // 注册 GameState 回调
        GameState.onEnding = renderEnding;
        GameState.onError = (err) => showToast(err.message, 'error');
        GameState.onConnectionLost = () => showConnFail();

        // 加载场景列表
        await loadScenarios();
    }

    function bindEvents() {
        dom.setupBackBtn.addEventListener('click', () => switchView('home'));
        dom.startGameBtn.addEventListener('click', handleStartGame);
        dom.alertBtn.addEventListener('click', handleAlert);
        dom.exitGameBtn.addEventListener('click', handleExitGame);
        dom.navRestartBtn.addEventListener('click', () => {
            if (confirm('确定要退出当前游戏，重新选择场景吗？')) {
                handleExitGame();
            }
        });
        dom.retryConnBtn.addEventListener('click', handleRetryConn);
        dom.inputName.addEventListener('input', validateName);
    }

    // ------------------ 场景加载 ------------------
    async function loadScenarios() {
        try {
            const scenarios = await TheaterAPI.getScenarios();
            scenariosCache = scenarios;
            renderScenarioGrid(scenarios);
            // 宣传数字以实际接口返回为准（避免静态文案失实）
            if (dom.statScenariosNum) {
                dom.statScenariosNum.textContent = String(scenarios.length);
            }
        } catch (err) {
            if (err.isConnectionError && err.isConnectionError()) {
                showConnFail();
            } else {
                dom.scenarioGrid.innerHTML = `
                    <div class="col-12 text-center py-5">
                        <i class="bi bi-exclamation-triangle" style="font-size:2.5rem;color:var(--danger-color);"></i>
                        <p class="mt-3 text-danger">${escapeHtml(err.message)}</p>
                    </div>`;
            }
        }
    }

    function renderScenarioGrid(scenarios) {
        if (!scenarios || scenarios.length === 0) {
            dom.scenarioGrid.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-inbox" style="font-size:2.5rem;color:var(--gray-400);"></i>
                    <p class="mt-3 text-muted">暂无可用场景</p>
                </div>`;
            return;
        }

        dom.scenarioGrid.innerHTML = scenarios.map((s, idx) => {
            const stagger = (idx % 4) + 1;
            const tags = (s.tags || []).map(t => `<span class="scenario-tag">${escapeHtml(t)}</span>`).join('');
            return `
                <div class="col-md-6 col-lg-3 animate-in stagger-${stagger}">
                    <div class="scenario-card theme-${escapeHtml(String(s.theme || '').replace('fc-theme-', ''))}" data-id="${escapeHtml(s.id)}">
                        <div class="scenario-card-cover">
                            <img src="${escapeHtml(s.cover)}" alt="${escapeHtml(s.name)}" loading="lazy"
                                 onerror="this.style.display='none';this.parentElement.style.background='linear-gradient(135deg,var(--card-primary),var(--card-secondary))';">
                            <div class="scenario-card-cover-overlay">
                                <span class="scenario-difficulty">难度 ${escapeHtml(s.difficulty)}</span>
                            </div>
                        </div>
                        <div class="scenario-card-body">
                            <div class="scenario-icon"><i class="bi ${escapeHtml(s.icon)}"></i></div>
                            <h3>${escapeHtml(s.name)}</h3>
                            <p class="scenario-desc">${escapeHtml(s.description)}</p>
                            <div class="scenario-tags">${tags}</div>
                            <button class="scenario-enter-btn">
                                <i class="bi bi-play-fill"></i> 进入剧场
                            </button>
                        </div>
                    </div>
                </div>`;
        }).join('');

        // 触发动画
        requestAnimationFrame(() => {
            dom.scenarioGrid.querySelectorAll('.animate-in').forEach(el => el.classList.add('visible'));
        });

        // 绑定点击
        dom.scenarioGrid.querySelectorAll('.scenario-card').forEach(card => {
            card.addEventListener('click', () => {
                const sid = card.dataset.id;
                const s = scenariosCache.find(x => x.id === sid);
                if (s) {
                    selectScenario(s);
                }
            });
        });
    }

    function selectScenario(scenario) {
        currentScenario = scenario;
        // 填充角色设定视图
        dom.setupScenarioIcon.innerHTML = `<i class="bi ${escapeHtml(scenario.icon)}"></i>`;
        dom.setupScenarioName.textContent = scenario.name;
        dom.setupScenarioDesc.textContent = scenario.description;
        dom.setupScenarioTags.innerHTML = (scenario.tags || [])
            .map(t => `<span class="scenario-tag">${escapeHtml(t)}</span>`).join('');
        // 重置表单
        dom.inputName.value = '';
        dom.inputName.classList.remove('is-invalid');
        dom.nameFeedback.textContent = '';
        // 默认选第一个
        document.querySelector('input[name="gender"][value="1"]').checked = true;
        document.querySelector('input[name="identity"][value="1"]').checked = true;

        switchView('setup');
    }

    // ------------------ 表单校验 ------------------
    function validateName() {
        const val = dom.inputName.value.trim();
        // 2-4 位汉字
        const re = /^[\u4e00-\u9fa5]{2,4}$/;
        if (!val) {
            dom.inputName.classList.remove('is-invalid');
            dom.nameFeedback.textContent = '';
            return false;
        }
        if (!re.test(val)) {
            dom.inputName.classList.add('is-invalid');
            dom.nameFeedback.textContent = '姓名必须是 2-4 位汉字';
            return false;
        }
        dom.inputName.classList.remove('is-invalid');
        dom.nameFeedback.textContent = '';
        return true;
    }

    // ------------------ 启动游戏 ------------------
    async function handleStartGame() {
        if (!currentScenario) {
            showToast('请先选择场景', 'warning');
            return;
        }
        if (!validateName()) {
            if (!dom.inputName.value.trim()) {
                dom.inputName.classList.add('is-invalid');
                dom.nameFeedback.textContent = '请输入姓名';
            }
            return;
        }
        const userInfo = {
            name: dom.inputName.value.trim(),
            gender: document.querySelector('input[name="gender"]:checked').value,
            identity: document.querySelector('input[name="identity"]:checked').value,
            scenario_id: currentScenario.id
        };

        dom.startGameBtn.disabled = true;
        dom.startGameBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 加载中...';

        try {
            switchView('game');
            document.body.classList.add('in-game');
            dom.navRestartBtn.classList.remove('d-none');
            await GameState.start(userInfo, currentScenario.name);
        } catch (err) {
            switchView('setup');
            document.body.classList.remove('in-game');
            dom.navRestartBtn.classList.add('d-none');
            if (err.isConnectionError && err.isConnectionError()) {
                showConnFail();
            } else {
                showToast(err.message, 'error');
            }
        } finally {
            dom.startGameBtn.disabled = false;
            dom.startGameBtn.innerHTML = '<i class="bi bi-play-fill"></i> 开始剧情';
        }
    }

    // ------------------ 报警 ------------------
    async function handleAlert() {
        if (!confirm('确定要报警吗？报警后警方将介入处理。')) return;
        // 不在此处隐藏按钮：请求失败时由 GameState.submitAlert 按
        // currentNode.allow_alert 恢复显隐，成功则由新节点渲染接管
        showToast('正在拨号报警...', 'success');
        await GameState.submitAlert();
    }

    // ------------------ 退出游戏 ------------------
    function handleExitGame() {
        // 先切视图给即时反馈，后端会话清理放后台执行，不阻塞 UI
        GameState.exit().catch(() => { /* 静默：退出时不再阻塞用户 */ });
        document.body.classList.remove('in-game');
        dom.navRestartBtn.classList.add('d-none');
        switchView('home');
    }

    // ------------------ 结局渲染 ------------------
    function renderEnding(ending) {
        const cat = ending.category || 'normal';
        const label = ENDING_LABELS[cat] || '结局';
        const icon = ENDING_ICONS[cat] || 'bi-flag';

        const paragraphs = (ending.paragraphs || [])
            .map(p => `<p class="ending-paragraph">${escapeHtml(p)}</p>`)
            .join('');

        dom.endingCard.className = `ending-card cat-${cat} animate-in visible`;
        dom.endingCard.innerHTML = `
            <div class="ending-header">
                <div class="ending-icon"><i class="bi ${icon}"></i></div>
                <span class="ending-category-badge">${label}</span>
                <h2 class="ending-title">${escapeHtml(ending.title || '剧情结束')}</h2>
            </div>
            <div class="ending-body">
                ${paragraphs}
                ${ending.achievement ? `
                <div class="ending-achievement">
                    <div class="achievement-icon"><i class="bi bi-trophy-fill"></i></div>
                    <div class="achievement-label">解锁成就</div>
                    <div class="achievement-name">${escapeHtml(ending.achievement)}</div>
                </div>` : ''}
            </div>
            <div class="ending-actions">
                <button class="ending-btn ending-btn-replay" id="endingReplayBtn">
                    <i class="bi bi-arrow-repeat"></i> 再次挑战
                </button>
                <a href="index.html#training" class="ending-btn ending-btn-home">
                    <i class="bi bi-house"></i> 返回首页
                </a>
            </div>`;

        document.body.classList.remove('in-game');
        dom.navRestartBtn.classList.add('d-none');
        switchView('ending');

        // 绑定"再次挑战"
        document.getElementById('endingReplayBtn').addEventListener('click', () => {
            switchView('home');
        });
    }

    // ------------------ 视图切换 ------------------
    // 主页滚动位置记忆：离开列表页时记录，返回时恢复原浏览位置（不再强制跳回顶部）
    let homeScrollY = 0;

    function switchView(name) {
        // 离开 home 视图前记录当前滚动位置
        if (dom.views.home && dom.views.home.classList.contains('active')) {
            homeScrollY = window.scrollY;
        }
        Object.values(dom.views).forEach(v => v.classList.remove('active'));
        const target = dom.views[name];
        if (target) {
            target.classList.add('active');
            // 重新触发 animate-in
            target.querySelectorAll('.animate-in').forEach(el => {
                el.classList.remove('visible');
                requestAnimationFrame(() => el.classList.add('visible'));
            });
            if (name === 'home' && homeScrollY > 0) {
                // 恢复离开列表页时的滚动位置（rAF 等视图 display 生效后再恢复，避免被布局修正覆盖）
                requestAnimationFrame(() => window.scrollTo({ top: homeScrollY, behavior: 'auto' }));
            } else {
                // 其他视图：瞬时滚动到顶（切换瞬间已有大量入场动画，平滑滚动会逐帧强制 layout 造成卡顿）
                window.scrollTo({ top: 0, behavior: 'auto' });
            }
        }

        // 非游戏视图下移除 in-game 类
        if (name !== 'game') {
            document.body.classList.remove('in-game');
        } else {
            document.body.classList.add('in-game');
        }

        // 仅在游戏视图显示"重选场景"按钮
        if (name === 'home' || name === 'setup') {
            dom.navRestartBtn.classList.add('d-none');
        } else if (name === 'game') {
            dom.navRestartBtn.classList.remove('d-none');
        }
    }

    // ------------------ 连接失败遮罩 ------------------
    function showConnFail() {
        dom.connFailOverlay.classList.remove('d-none');
    }

    function hideConnFail() {
        dom.connFailOverlay.classList.add('d-none');
    }

    async function handleRetryConn() {
        dom.retryConnBtn.disabled = true;
        dom.retryConnBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 重试中...';
        const ok = await TheaterAPI.ping();
        dom.retryConnBtn.disabled = false;
        dom.retryConnBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 重试连接';
        if (!ok) {
            showToast('仍无法连接，请确认后端已启动', 'error');
            return;
        }
        hideConnFail();
        showToast('连接成功', 'success');

        // 存活会话优先续接当前节点，而不是强制回首页丢弃进度
        const st = GameState.state;
        if (st.gameId && !st.isEnded) {
            try {
                const node = await TheaterAPI.getNode(st.gameId);
                switchView('game');
                await GameState.resume(node);
                return;
            } catch (_) {
                // 会话已失效（如后端重启丢失内存会话）：清理残留状态后回首页
                await GameState.exit().catch(() => {});
            }
        }
        await loadScenarios();
        switchView('home');
    }

    // ------------------ Toast ------------------
    function showToast(message, type = 'info') {
        const item = document.createElement('div');
        item.className = `toast-item toast-${type}`;
        item.textContent = message;
        dom.toast.appendChild(item);
        setTimeout(() => {
            item.classList.add('toast-out');
            setTimeout(() => item.remove(), 300);
        }, 3000);
    }

    // ------------------ HTML 转义 ------------------
    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    // ------------------ 星空 Canvas ------------------
    function startStarCanvas() {
        const canvas = document.getElementById('starCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let stars = [];
        let animId = null;

        let starsResizeTimer = null;

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }

        function initStars() {
            const count = Math.floor((canvas.width * canvas.height) / 12000);
            stars = [];
            for (let i = 0; i < count; i++) {
                stars.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height,
                    r: Math.random() * 1.2 + 0.3,
                    a: Math.random() * 0.6 + 0.2,
                    twinkleSpeed: Math.random() * 0.02 + 0.005,
                    twinkleDir: Math.random() > 0.5 ? 1 : -1
                });
            }
        }

        // 节流：星星闪烁极慢，20fps 与 60fps 肉眼无差别，可省约 2/3 的绘制开销
        const FRAME_INTERVAL = 50; // ms（约 20fps）
        let lastDrawTime = 0;

        function draw(now) {
            animId = requestAnimationFrame(draw);
            if (now - lastDrawTime < FRAME_INTERVAL) return;
            lastDrawTime = now;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            for (const s of stars) {
                s.a += s.twinkleSpeed * s.twinkleDir;
                if (s.a > 0.9 || s.a < 0.15) s.twinkleDir *= -1;
                ctx.beginPath();
                ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(200, 220, 255, ${s.a})`;
                ctx.fill();
            }
        }

        resize();
        initStars();
        // 窗口缩放防抖：200ms 停止后再重建星空，避免拖拽期间高频重算
        window.addEventListener('resize', () => {
            clearTimeout(starsResizeTimer);
            starsResizeTimer = setTimeout(() => {
                resize();
                initStars();
            }, 200);
        });
        animId = requestAnimationFrame(draw);
    }

})();
