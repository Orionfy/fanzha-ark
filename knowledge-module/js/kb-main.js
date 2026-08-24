/* ============================================================
 * kb-main.js - 反诈知识库主逻辑
 * 视图切换（知识列表 / 主题详情 / 自测设置 / 答题 / 结果）
 * 搜索过滤 + 分类筛选 + 纯前端答题流 + API 判分
 * ============================================================ */

(function () {
    'use strict';

    // ------------------ 常量 ------------------
    const GROUP_ALL = 'all';
    const GROUP_HOT = 'hot';
    const GROUP_NEW = 'new';
    // 新型手段关键词：AI 换脸拟声 / 裸聊敲诈 / 杀猪盘等新形态骗局
    const NEW_TOPIC_PATTERN = /(AI|换脸|拟声|裸聊|杀猪盘)/;

    const RATING_CLASS_MAP = {
        '反诈专家': 'rating-expert',
        '反诈达人': 'rating-master',
        '初窥门径': 'rating-apprentice',
        '防诈新兵': 'rating-rookie'
    };

    const OPTION_LETTERS = ['A', 'B', 'C', 'D'];

    // ------------------ 状态 ------------------
    let topicsCache = [];
    let filters = { query: '', group: GROUP_ALL };
    let quizConfig = { count: 5, topicId: '' };
    let quizQuestions = [];
    let quizAnswers = [];
    let quizIndex = 0;
    let isAnswering = false;   // 选项点击后的过渡期，禁重复点击
    let isBusy = false;        // 网络请求期间禁重复提交
    let answerTimer = null;        // chooseOption 的过渡定时器句柄
    let quizFlowToken = 0;         // 答题流程令牌：退出/重开自测时使在途定时器与判分失效
    let searchDebounceTimer = null; // 搜索框防抖句柄

    // ------------------ DOM ------------------
    const dom = {};

    function cacheDom() {
        dom.views = {
            home: document.getElementById('view-home'),
            detail: document.getElementById('view-detail'),
            quizSetup: document.getElementById('view-quiz-setup'),
            quizPlay: document.getElementById('view-quiz-play'),
            quizResult: document.getElementById('view-quiz-result')
        };
        dom.navExitBtn = document.getElementById('navExitBtn');
        dom.statTopicCount = document.getElementById('statTopicCount');
        dom.searchInput = document.getElementById('searchInput');
        dom.chipRow = document.getElementById('chipRow');
        dom.topicGrid = document.getElementById('topicGrid');
        dom.quizCtaBtn = document.getElementById('quizCtaBtn');
        dom.detailBody = document.getElementById('detailBody');
        dom.countChips = document.getElementById('countChips');
        dom.topicSelect = document.getElementById('topicSelect');
        dom.quizStartBtn = document.getElementById('quizStartBtn');
        dom.quizProgressLabel = document.getElementById('quizProgressLabel');
        dom.quizProgressFill = document.getElementById('quizProgressFill');
        dom.quizStage = document.getElementById('quizStage');
        dom.quizResultCard = document.getElementById('quizResultCard');
        dom.connFailOverlay = document.getElementById('connFailOverlay');
        dom.retryConnBtn = document.getElementById('retryConnBtn');
        dom.toast = document.getElementById('toast');
    }

    function bindEvents() {
        dom.navExitBtn.addEventListener('click', handleExitQuiz);
        dom.searchInput.addEventListener('input', () => {
            filters.query = dom.searchInput.value;
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(renderTopicGrid, 180);
        });
        dom.chipRow.addEventListener('click', event => {
            const chip = event.target.closest('.filter-chip');
            if (!chip) return;
            filters.group = chip.dataset.group || GROUP_ALL;
            dom.chipRow.querySelectorAll('.filter-chip').forEach(el => {
                el.classList.toggle('active', el === chip);
            });
            renderTopicGrid();
        });
        dom.topicGrid.addEventListener('click', event => {
            const resetBtn = event.target.closest('#resetFilterBtn');
            if (resetBtn) {
                filters.query = '';
                dom.searchInput.value = '';
                filters.group = GROUP_ALL;
                dom.chipRow.querySelectorAll('.filter-chip').forEach(el => {
                    el.classList.toggle('active', el.dataset.group === GROUP_ALL);
                });
                renderTopicGrid();
                return;
            }
            const card = event.target.closest('.topic-card');
            if (card) openTopic(card.dataset.id);
        });
        dom.quizCtaBtn.addEventListener('click', () => switchView('quizSetup'));
        dom.detailBody.addEventListener('click', event => {
            const backBtn = event.target.closest('#detailBackBtn');
            if (backBtn) { switchView('home'); return; }
            const caseToggle = event.target.closest('.case-toggle');
            if (caseToggle) {
                const panel = caseToggle.closest('.case-panel');
                const open = panel.classList.toggle('open');
                caseToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
                return;
            }
            const related = event.target.closest('[data-related-id]');
            if (related) openTopic(related.dataset.relatedId);
        });
        dom.countChips.addEventListener('click', event => {
            const chip = event.target.closest('.count-chip');
            if (!chip) return;
            quizConfig.count = Number(chip.dataset.count) || 5;
            dom.countChips.querySelectorAll('.count-chip').forEach(el => {
                el.classList.toggle('active', el === chip);
            });
        });
        dom.quizStartBtn.addEventListener('click', startQuiz);
        dom.quizStage.addEventListener('click', event => {
            const retry = event.target.closest('#retrySubmitBtn');
            if (retry) { finishQuiz(); return; }
            const option = event.target.closest('.quiz-option');
            if (option) chooseOption(Number(option.dataset.choice));
        });
        dom.retryConnBtn.addEventListener('click', handleRetryConn);
    }

    // ------------------ 视图切换 ------------------
    // 主页滚动位置记忆：离开列表页时记录，返回时恢复原浏览位置
    let homeScrollY = 0;

    function switchView(name) {
        if (dom.views.home && dom.views.home.classList.contains('active')) {
            homeScrollY = window.scrollY;
        }
        Object.values(dom.views).forEach(view => view.classList.remove('active'));
        const target = dom.views[name];
        if (!target) return;
        target.classList.add('active');
        target.querySelectorAll('.animate-in').forEach(element => {
            element.classList.remove('visible');
            requestAnimationFrame(() => element.classList.add('visible'));
        });
        // 导航栏按钮：仅答题视图显示退出自测
        dom.navExitBtn.classList.toggle('d-none', name !== 'quizPlay');
        if (name === 'home' && homeScrollY > 0) {
            requestAnimationFrame(() => window.scrollTo({ top: homeScrollY, behavior: 'auto' }));
        } else {
            window.scrollTo({ top: 0, behavior: 'auto' });
        }
    }

    // ------------------ 知识列表 ------------------
    async function loadTopics() {
        try {
            topicsCache = await KnowledgeAPI.getTopics();
            if (dom.statTopicCount) dom.statTopicCount.textContent = String(topicsCache.length || 10);
            populateTopicSelect();
            renderTopicGrid();
        } catch (err) {
            handleApiError(err, true);
        }
    }

    function populateTopicSelect() {
        dom.topicSelect.innerHTML = '<option value="">全部主题（混合出题）</option>' +
            topicsCache.map(t =>
                `<option value="${escapeHtml(String(t.id))}">${escapeHtml(t.name)}</option>`
            ).join('');
    }

    function resolveGroup(topic) {
        if (topic.group) return String(topic.group);
        return NEW_TOPIC_PATTERN.test(String(topic.name || '')) ? GROUP_NEW : GROUP_HOT;
    }

    function applyFilters() {
        const query = filters.query.trim().toLowerCase();
        return topicsCache.filter(topic => {
            if (filters.group !== GROUP_ALL && resolveGroup(topic) !== filters.group) return false;
            if (!query) return true;
            return [topic.name, topic.tagline, topic.summary]
                .some(field => String(field || '').toLowerCase().includes(query));
        });
    }

    function renderTopicGrid() {
        const list = applyFilters();

        if (!topicsCache.length) return; // 加载失败/未加载时保留原占位或错误态

        if (!list.length) {
            dom.topicGrid.innerHTML = `
                <div class="col-12 empty-state">
                    <i class="bi bi-search" aria-hidden="true"></i>
                    <p>没有找到与「${escapeHtml(filters.query.trim())}」相关的知识主题</p>
                    <button class="empty-reset-btn" id="resetFilterBtn" type="button">
                        <i class="bi bi-x-circle"></i> 清除筛选条件
                    </button>
                </div>`;
            return;
        }

        dom.topicGrid.innerHTML = list.map((topic, idx) => `
            <div class="col-md-6 col-lg-4 animate-in stagger-${(idx % 4) + 1}">
                <article class="topic-card" data-id="${escapeHtml(String(topic.id))}" tabindex="0"
                         role="button" aria-label="查看${escapeHtml(topic.name)}详解">
                    <div class="topic-icon"><i class="bi ${safeIcon(topic.icon)}" aria-hidden="true"></i></div>
                    <div class="topic-info">
                        <h3>${escapeHtml(topic.name)}</h3>
                        <p class="topic-tagline">${escapeHtml(topic.tagline || '')}</p>
                        ${renderStars(topic.difficulty)}
                    </div>
                    <i class="bi bi-chevron-right topic-arrow" aria-hidden="true"></i>
                </article>
            </div>`).join('');

        requestAnimationFrame(() => {
            dom.topicGrid.querySelectorAll('.animate-in').forEach(el => el.classList.add('visible'));
        });

        dom.topicGrid.querySelectorAll('.topic-card').forEach(card => {
            card.addEventListener('keydown', event => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    openTopic(card.dataset.id);
                }
            });
        });
    }

    /** 难度展示：数字按 5 星渲染；含 ★/☆ 的字符串直接展示 */
    function renderStars(difficulty) {
        if (typeof difficulty === 'number' && Number.isFinite(difficulty)) {
            const level = Math.min(Math.max(Math.round(difficulty), 1), 5);
            let html = '';
            for (let i = 1; i <= 5; i++) {
                html += `<i class="bi ${i <= level ? 'bi-star-fill' : 'bi-star'}" aria-hidden="true"></i>`;
            }
            return `<span class="stars" aria-label="难度 ${level} / 5">${html}</span>`;
        }
        const text = String(difficulty ?? '').trim();
        if (!text) return '';
        if (text.includes('★') || text.includes('☆')) {
            return `<span class="stars-text">${escapeHtml(text)}</span>`;
        }
        const parsed = parseInt(text, 10);
        if (!Number.isNaN(parsed)) return renderStars(parsed);
        return `<span class="stars-text">${escapeHtml(text)}</span>`;
    }

    // ------------------ 主题详情 ------------------
    async function openTopic(topicId) {
        if (topicId === undefined || topicId === null || topicId === '') return;
        dom.detailBody.innerHTML = `
            <div class="detail-loading">
                <div class="spinner-border" role="status"><span class="visually-hidden">加载中</span></div>
                <p class="mt-3">正在调取档案...</p>
            </div>`;
        switchView('detail');
        try {
            const topic = await KnowledgeAPI.getTopic(topicId);
            renderDetail(topic);
        } catch (err) {
            // 连接错误同样先渲染带出口的错误态（返回知识库 / 重新加载），
            // 再叠加断连遮罩；重连成功关闭遮罩后用户有页内出口
            const isConnFail = Boolean(err?.isConnectionError?.());
            dom.detailBody.innerHTML = `
                <button class="detail-back-btn" id="detailBackBtn" type="button">
                    <i class="bi bi-arrow-left" aria-hidden="true"></i> 返回知识库
                </button>
                <div class="detail-error">
                    <i class="bi bi-exclamation-triangle" aria-hidden="true"></i>
                    <p>${escapeHtml(err?.message || '档案调取失败，请稍后重试')}</p>
                    <button class="btn-secondary-pill" id="detailRetryBtn" type="button">
                        <i class="bi bi-arrow-clockwise" aria-hidden="true"></i> 重新加载
                    </button>
                </div>`;
            const retryBtn = document.getElementById('detailRetryBtn');
            if (retryBtn) retryBtn.addEventListener('click', () => openTopic(topicId));
            if (isConnFail) showConnFail();
        }
    }

    /** 兼容 tactics 元素为字符串或 {title/description} 对象的情况 */
    function stepText(step) {
        if (typeof step === 'string') return step;
        if (step && typeof step === 'object') {
            const title = step.title || step.name || '';
            const body = step.description || step.text || step.content || step.desc || '';
            if (title && body) return `${title}：${body}`;
            return title || body;
        }
        return String(step ?? '');
    }

    function renderDetail(topic) {
        const related = (topic.related_topic_ids || [])
            .map(id => topicsCache.find(t => String(t.id) === String(id)))
            .filter(Boolean);

        const tactics = (Array.isArray(topic.tactics) ? topic.tactics : []).map(stepText);
        const scripts = Array.isArray(topic.scripts) ? topic.scripts.map(stepText) : [];
        const signals = Array.isArray(topic.signals) ? topic.signals.map(stepText) : [];
        const rules = Array.isArray(topic.rules) ? topic.rules.map(stepText) : [];
        const caseStudy = topic.case_study || {};

        dom.detailBody.innerHTML = `
            <button class="detail-back-btn" id="detailBackBtn" type="button">
                <i class="bi bi-arrow-left" aria-hidden="true"></i> 返回知识库
            </button>

            <header class="detail-header animate-in visible">
                <div class="detail-header-icon"><i class="bi ${safeIcon(topic.icon)}" aria-hidden="true"></i></div>
                <div class="detail-header-info">
                    <h2>${escapeHtml(topic.name)}</h2>
                    ${renderStars(topic.difficulty)}
                    <p class="detail-tagline">${escapeHtml(topic.tagline || '')}</p>
                </div>
            </header>

            ${topic.summary ? `<p class="detail-summary animate-in visible">${escapeHtml(topic.summary)}</p>` : ''}

            ${tactics.length ? `
            <section class="detail-section animate-in visible">
                <h3 class="detail-heading"><i class="bi bi-diagram-3" aria-hidden="true"></i> 套路拆解</h3>
                <ol class="kb-timeline">
                    ${tactics.map((step, i) => `
                        <li class="timeline-step">
                            <span class="step-no">${i + 1}</span>
                            <div class="step-text">${escapeHtml(step)}</div>
                        </li>`).join('')}
                </ol>
            </section>` : ''}

            ${scripts.length ? `
            <section class="detail-section animate-in visible">
                <h3 class="detail-heading"><i class="bi bi-chat-quote" aria-hidden="true"></i> 典型话术</h3>
                ${scripts.map(script => `
                    <blockquote class="script-quote">
                        <i class="bi bi-quote quote-mark" aria-hidden="true"></i>
                        <span>${escapeHtml(script)}</span>
                    </blockquote>`).join('')}
            </section>` : ''}

            ${signals.length ? `
            <section class="detail-section animate-in visible">
                <h3 class="detail-heading"><i class="bi bi-shield-exclamation" aria-hidden="true"></i> 识别信号</h3>
                <ul class="signal-checklist">
                    ${signals.map(signal => `
                        <li class="signal-item">
                            <i class="bi bi-check2-square" aria-hidden="true"></i>
                            <span>${escapeHtml(signal)}</span>
                        </li>`).join('')}
                </ul>
            </section>` : ''}

            ${rules.length ? `
            <section class="detail-section animate-in visible">
                <h3 class="detail-heading"><i class="bi bi-journal-check" aria-hidden="true"></i> 防骗法则</h3>
                <div class="rule-grid">
                    ${rules.map((rule, i) => `
                        <div class="rule-card">
                            <div class="rule-no">法则 ${String(i + 1).padStart(2, '0')}</div>
                            <p>${escapeHtml(rule)}</p>
                        </div>`).join('')}
                </div>
            </section>` : ''}

            ${(caseStudy.story || caseStudy.analysis) ? `
            <section class="detail-section animate-in visible">
                <h3 class="detail-heading"><i class="bi bi-file-earmark-text" aria-hidden="true"></i> 真实案例剖析</h3>
                <div class="case-panel">
                    <button class="case-toggle" type="button" aria-expanded="false">
                        <span class="case-toggle-label">
                            <i class="bi bi-book" aria-hidden="true"></i>
                            ${escapeHtml(caseStudy.title || '展开案例')}
                        </span>
                        <i class="bi bi-chevron-down" aria-hidden="true"></i>
                    </button>
                    <div class="case-body">
                        ${caseStudy.story ? `<p class="case-story">${escapeHtml(caseStudy.story)}</p>` : ''}
                        ${caseStudy.analysis ? `
                        <div class="case-analysis">
                            <div class="case-analysis-label">
                                <i class="bi bi-lightbulb" aria-hidden="true"></i> 案例分析
                            </div>
                            <p>${escapeHtml(caseStudy.analysis)}</p>
                        </div>` : ''}
                    </div>
                </div>
            </section>` : ''}

            ${related.length ? `
            <section class="detail-section animate-in visible">
                <h3 class="detail-heading"><i class="bi bi-collection" aria-hidden="true"></i> 相关推荐</h3>
                <div class="related-grid">
                    ${related.map(t => `
                        <button class="related-card" type="button" data-related-id="${escapeHtml(String(t.id))}">
                            <i class="bi ${safeIcon(t.icon)}" aria-hidden="true"></i>
                            <span>${escapeHtml(t.name)}</span>
                            <i class="bi bi-arrow-right related-go" aria-hidden="true"></i>
                        </button>`).join('')}
                </div>
            </section>` : ''}
        `;
    }

    // ------------------ 自测：开始 ------------------
    async function startQuiz() {
        if (isBusy) return;
        quizFlowToken += 1; // 使旧流程的在途定时器 / 判分回调失效
        quizConfig.topicId = dom.topicSelect.value || '';
        setStartBusy(true);
        try {
            quizQuestions = await KnowledgeAPI.getQuiz(quizConfig.count, quizConfig.topicId);
            if (!quizQuestions.length) {
                showToast('未获取到题目，请稍后再试', 'warning');
                return;
            }
            quizAnswers = [];
            quizIndex = 0;
            renderQuizQuestion();
            switchView('quizPlay');
        } catch (err) {
            handleApiError(err);
        } finally {
            setStartBusy(false);
        }
    }

    function setStartBusy(busy) {
        isBusy = busy;
        dom.quizStartBtn.disabled = busy;
        dom.quizStartBtn.innerHTML = busy
            ? '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> 正在出题…'
            : '<i class="bi bi-play-fill" aria-hidden="true"></i> 开始挑战';
    }

    // ------------------ 自测：答题（纯前端流转） ------------------
    function renderQuizQuestion() {
        const question = quizQuestions[quizIndex];
        const total = quizQuestions.length;
        dom.quizProgressLabel.innerHTML =
            `第 <strong>${quizIndex + 1}</strong> / ${total} 题`;
        dom.quizProgressFill.style.width = `${((quizIndex + 1) / total) * 100}%`;

        const topic = topicsCache.find(t => String(t.id) === String(question.topic_id));
        dom.quizStage.innerHTML = `
            <div class="quiz-question-card animate-in visible">
                ${topic ? `
                <div class="quiz-topic-tag">
                    <i class="bi ${safeIcon(topic.icon)}" aria-hidden="true"></i> ${escapeHtml(topic.name)}
                </div>` : ''}
                <h2 class="quiz-question">${escapeHtml(question.question)}</h2>
                <div class="quiz-options">
                    ${(question.options || []).map((opt, i) => `
                        <button class="quiz-option" type="button" data-choice="${i}">
                            <span class="option-letter">${OPTION_LETTERS[i] || i + 1}</span>
                            <span class="option-text">${escapeHtml(opt)}</span>
                        </button>`).join('')}
                </div>
            </div>`;
    }

    function chooseOption(choiceIndex) {
        if (isAnswering) return;
        const question = quizQuestions[quizIndex];
        if (!question) return;

        isAnswering = true;
        quizAnswers.push({ qid: question.qid, choice: choiceIndex });

        // 高亮所选选项并锁定全部选项，短暂停留后进入下一题
        dom.quizStage.querySelectorAll('.quiz-option').forEach(btn => {
            btn.disabled = true;
        });
        const picked = dom.quizStage.querySelector(`.quiz-option[data-choice="${choiceIndex}"]`);
        if (picked) picked.classList.add('selected');

        const myToken = quizFlowToken;
        answerTimer = setTimeout(() => {
            if (myToken !== quizFlowToken) return; // 流程已被退出/重开，放弃本次流转
            isAnswering = false;
            quizIndex += 1;
            if (quizIndex < quizQuestions.length) {
                renderQuizQuestion();
            } else {
                finishQuiz();
            }
        }, prefersReducedMotion() ? 60 : 360);
    }

    // ------------------ 自测：交卷判分 ------------------
    async function finishQuiz() {
        if (!quizAnswers.length) return;
        const myToken = quizFlowToken;
        dom.quizProgressLabel.textContent = '正在判分…';
        dom.quizStage.innerHTML = `
            <div class="quiz-submitting">
                <div class="spinner-border" role="status"><span class="visually-hidden">判分中</span></div>
                <p>正在生成你的防诈成绩单…</p>
            </div>`;
        try {
            const result = await KnowledgeAPI.submitQuiz(quizAnswers);
            if (myToken !== quizFlowToken) return; // 判分期间流程已被退出/重开，放弃渲染
            renderQuizResult(result);
            switchView('quizResult');
        } catch (err) {
            if (err?.isConnectionError?.()) showConnFail();
            dom.quizStage.innerHTML = `
                <div class="quiz-submit-error">
                    <i class="bi bi-exclamation-triangle" aria-hidden="true"></i>
                    <p>${escapeHtml(err?.message || '判分失败，请稍后重试')}</p>
                    <button class="btn-retry-submit" id="retrySubmitBtn" type="button">
                        <i class="bi bi-arrow-clockwise" aria-hidden="true"></i> 重试交卷
                    </button>
                </div>`;
        }
    }

    function normalizeAccuracy(value) {
        const num = Number(value);
        if (!Number.isFinite(num)) return 0;
        const pct = num <= 1 ? num * 100 : num;
        return Math.min(Math.max(Math.round(pct), 0), 100);
    }

    function renderQuizResult(result) {
        const total = Number(result.total ?? quizAnswers.length);
        const correctCount = Number(result.correct_count ?? 0);
        const accuracyPct = normalizeAccuracy(result.accuracy);
        const ratingText = String(result.rating || '防诈新兵');
        const ratingClass = RATING_CLASS_MAP[ratingText] || 'rating-rookie';

        const RING_RADIUS = 52;
        const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

        const reviewHtml = (result.review || []).map(item => {
            const isCorrect = Boolean(item.correct);
            const yourChoice = Number(item.your_choice);
            const correctIndex = Number(item.correct_index);
            const topic = topicsCache.find(t => String(t.id) === String(item.topic_id));
            const optionsHtml = (item.options || []).map((opt, i) => {
                const classes = ['review-option'];
                if (i === correctIndex) classes.push('correct');
                if (i === yourChoice && !isCorrect) classes.push('wrong');
                let marker = '';
                if (i === yourChoice) marker = '<span class="review-marker yours">你的答案</span>';
                else if (i === correctIndex) marker = '<span class="review-marker correct-tag">正确答案</span>';
                return `
                    <li class="${classes.join(' ')}">
                        <span class="option-letter">${OPTION_LETTERS[i] || i + 1}</span>
                        <span class="option-text">${escapeHtml(opt)}</span>
                        ${marker}
                    </li>`;
            }).join('');
            return `
                <article class="review-item ${isCorrect ? 'right' : 'wrong'}">
                    <div class="review-head">
                        <span class="review-verdict ${isCorrect ? 'ok' : 'bad'}">
                            <i class="bi ${isCorrect ? 'bi-check-circle-fill' : 'bi-x-circle-fill'}" aria-hidden="true"></i>
                            ${isCorrect ? '回答正确' : '回答错误'}
                        </span>
                        ${topic ? `<span class="review-topic">${escapeHtml(topic.name)}</span>` : ''}
                    </div>
                    <h4>${escapeHtml(item.question)}</h4>
                    <ul class="review-options">${optionsHtml}</ul>
                    ${item.explanation ? `
                    <div class="review-explain">
                        <i class="bi bi-lightbulb" aria-hidden="true"></i>
                        <span>${escapeHtml(item.explanation)}</span>
                    </div>` : ''}
                </article>`;
        }).join('');

        dom.quizResultCard.innerHTML = `
            <div class="result-hero">
                <div class="quiz-rating-badge ${ratingClass}">${escapeHtml(ratingText)}</div>
                <div class="accuracy-ring-wrap">
                    <svg class="accuracy-ring" viewBox="0 0 120 120" aria-hidden="true">
                        <defs>
                            <linearGradient id="kbRingGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#059669"/>
                                <stop offset="100%" stop-color="#34d399"/>
                            </linearGradient>
                        </defs>
                        <circle class="ring-bg" cx="60" cy="60" r="${RING_RADIUS}"></circle>
                        <circle class="ring-fill" cx="60" cy="60" r="${RING_RADIUS}"
                                stroke-dasharray="${RING_CIRCUMFERENCE.toFixed(1)}"
                                stroke-dashoffset="${RING_CIRCUMFERENCE.toFixed(1)}"></circle>
                    </svg>
                    <div class="accuracy-text">
                        <strong>${accuracyPct}%</strong>
                        <span>正确率</span>
                    </div>
                </div>
                <div class="result-stats">
                    <div class="result-stat"><div class="num">${total}</div><div class="label">题目总数</div></div>
                    <div class="result-stat"><div class="num">${correctCount}</div><div class="label">答对</div></div>
                    <div class="result-stat"><div class="num">${Math.max(total - correctCount, 0)}</div><div class="label">答错</div></div>
                </div>
            </div>
            <div class="result-review">
                <h3><i class="bi bi-list-check" aria-hidden="true"></i> 逐题回顾</h3>
                ${reviewHtml || '<p style="color:var(--gray-400);font-size:0.9rem;">暂无回顾数据</p>'}
            </div>
            <div class="result-actions">
                <button class="btn-primary-pill" id="quizAgainBtn" type="button">
                    <i class="bi bi-arrow-repeat" aria-hidden="true"></i> 再来一组
                </button>
                <button class="btn-secondary-pill" id="quizHomeBtn" type="button">
                    <i class="bi bi-journal-bookmark" aria-hidden="true"></i> 回知识库
                </button>
            </div>`;

        document.getElementById('quizAgainBtn').addEventListener('click', () => {
            resetQuizState();
            switchView('quizSetup');
        });
        document.getElementById('quizHomeBtn').addEventListener('click', () => {
            resetQuizState();
            switchView('home');
        });

        // 正确率环形动画：先强制提交一次布局（初始 dashoffset），
        // 再写入目标值以触发过渡；后台标签页 rAF 被节流时同样生效
        const ring = dom.quizResultCard.querySelector('.ring-fill');
        if (ring) {
            const targetOffset = RING_CIRCUMFERENCE * (1 - accuracyPct / 100);
            void dom.quizResultCard.offsetWidth;
            ring.style.strokeDashoffset = String(targetOffset.toFixed(1));
        }
    }

    function resetQuizState() {
        quizFlowToken += 1; // 作废在途的答题定时器与判分回调
        if (answerTimer) {
            clearTimeout(answerTimer);
            answerTimer = null;
        }
        quizQuestions = [];
        quizAnswers = [];
        quizIndex = 0;
        isAnswering = false;
        dom.quizStage.innerHTML = '';
        dom.quizProgressFill.style.width = '0%';
        dom.quizProgressLabel.textContent = '';
    }

    function handleExitQuiz() {
        if (!window.confirm('确定要退出本次自测吗？当前答题进度将不会保存。')) return;
        resetQuizState();
        switchView('home');
    }

    // ------------------ 错误处理 & 通用工具 ------------------
    function handleApiError(error, loadingTopics = false) {
        if (error?.isConnectionError?.()) {
            showConnFail();
            return;
        }
        if (error?.status === 404 && loadingTopics) {
            // 后端已连接但版本过旧：运行中的后端进程未加载知识库模块
            dom.topicGrid.innerHTML = `
                <div class="col-12 empty-state">
                    <i class="bi bi-arrow-repeat" aria-hidden="true"></i>
                    <p style="color:#fbbf24;font-weight:700;">后端服务版本过旧，未加载知识库模块</p>
                    <p style="font-size:0.88rem;">请重启后端服务：在运行 uvicorn 的终端按 Ctrl+C 停止，<br>再重新执行启动命令后刷新本页</p>
                </div>`;
            return;
        }
        const message = error?.message || '请求失败，请稍后重试';
        if (loadingTopics) {
            dom.topicGrid.innerHTML = `
                <div class="col-12 empty-state">
                    <i class="bi bi-exclamation-triangle" aria-hidden="true"></i>
                    <p>${escapeHtml(message)}</p>
                    <button class="empty-reset-btn" id="reloadTopicsBtn" type="button">
                        <i class="bi bi-arrow-clockwise"></i> 重新加载
                    </button>
                </div>`;
            const reloadBtn = document.getElementById('reloadTopicsBtn');
            if (reloadBtn) reloadBtn.addEventListener('click', loadTopics);
        } else {
            showToast(message, 'error');
        }
    }

    function showConnFail() {
        dom.connFailOverlay.classList.remove('d-none');
    }

    async function handleRetryConn() {
        dom.retryConnBtn.disabled = true;
        dom.retryConnBtn.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> 重试中…';
        const alive = await KnowledgeAPI.ping();
        dom.retryConnBtn.disabled = false;
        dom.retryConnBtn.innerHTML = '<i class="bi bi-arrow-clockwise" aria-hidden="true"></i> 重试连接';
        if (!alive) {
            showToast('仍无法连接服务，请确认后端已启动', 'error');
            return;
        }
        dom.connFailOverlay.classList.add('d-none');
        await loadTopics();
        showToast('服务已连接', 'success');
    }

    function showToast(message, type = 'info') {
        if (!dom.toast) return;
        const safeType = ['info', 'error', 'success', 'warning'].includes(type) ? type : 'info';
        const icons = {
            info: 'bi-info-circle',
            error: 'bi-x-octagon',
            success: 'bi-check-circle',
            warning: 'bi-exclamation-triangle'
        };
        const item = document.createElement('div');
        item.className = `toast-item toast-${safeType}`;
        item.innerHTML = `<i class="bi ${icons[safeType]}" aria-hidden="true"></i> ${escapeHtml(message)}`;
        dom.toast.appendChild(item);
        setTimeout(() => item.remove(), 3200);
    }

    function safeIcon(icon) {
        const value = String(icon || 'bi-journal-bookmark-fill');
        return /^bi-[a-z0-9-]+$/i.test(value) ? value : 'bi-journal-bookmark-fill';
    }

    function prefersReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    function escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ------------------ 初始化 ------------------
    function init() {
        cacheDom();
        bindEvents();
        loadTopics();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
