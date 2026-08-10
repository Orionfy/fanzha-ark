/* ============================================================
 * game-state.js - 游戏状态机
 * 维护当前 gameId/scenarioId，根据节点类型（auto/choice/ending）
 * 分发渲染：auto→打字机播完自动推进；choice→渲染选项；ending→跳结局
 * ============================================================ */

const GameState = (function () {

    const state = {
        gameId: null,
        scenarioId: null,
        scenarioName: '',
        currentNode: null,
        isEnded: false
    };

    // 推进深度计数：允许 auto→auto 链嵌套推进，并防外部并发重复推进
    let advanceDepth = 0;

    // DOM 引用（init 时绑定）
    let dom = {};

    /** 配置项（可覆盖） */
    const config = {
        autoNextDelay: 800,        // auto 节点播完后等待多久再 advance
        typingSpeed: 30,           // 打字机每字毫秒
        typingDelayBefore: 600,    // 出现"正在输入"到开始打字的时间
        roleForAuto: 'scammer'     // auto 节点默认角色（实际每行会重新识别）
    };

    /**
     * 初始化：绑定 DOM
     */
    function init(elements) {
        dom = elements;
    }

    /**
     * 启动游戏
     * @param {{name:string, gender:string, identity:string, scenario_id:string}} userInfo
     * @param {string} scenarioName
     */
    async function start(userInfo, scenarioName) {
        state.scenarioId = userInfo.scenario_id;
        state.scenarioName = scenarioName;
        state.isEnded = false;
        advanceDepth = 0;

        const data = await TheaterAPI.startGame(userInfo);
        state.gameId = data.game_id;
        dom.gameScenarioName.textContent = data.scenario_name || scenarioName;

        ChatRenderer.clear(dom.chatBody);
        await renderNode(data);
    }

    /**
     * 渲染一个节点
     */
    async function renderNode(node) {
        state.currentNode = node;

        // 设置图片目录（供 ChatRenderer 拼接图片路径；回退到 scenario_id）
        if (node.image_dir) {
            ChatRenderer.setImageDir(node.image_dir);
        } else if (node.scenario_id) {
            ChatRenderer.setImageDir(node.scenario_id);
        }

        // 结局节点：交给上层处理
        if (node.type === 'ending' || node.is_ending) {
            state.isEnded = true;
            handleEnding(node);
            return;
        }

        // 报警按钮显隐
        if (node.allow_alert) {
            dom.alertBtn.classList.remove('d-none');
        } else {
            dom.alertBtn.classList.add('d-none');
        }

        // 隐藏选项区
        dom.choiceBar.classList.add('d-none');
        dom.choiceBar.innerHTML = '';

        // 内容渲染：逐行打字机
        const lines = node.content || [];
        for (const line of lines) {
            const info = ChatRenderer.detectRole(line);

            // 对话角色（骗子/民警/用户）先显示"正在输入"
            if (['scammer', 'police', 'user'].includes(info.role)) {
                ChatRenderer.showTypingIndicator(dom.chatBody, info.role);
                await sleep(config.typingDelayBefore);
                ChatRenderer.hideTypingIndicator(dom.chatBody);
            }

            await ChatRenderer.typewriterAppend(dom.chatBody, info, config.typingSpeed);
        }

        // 根据节点类型分发
        if (node.type === 'auto' && node.next) {
            // auto 节点：显示"剧情推进中"，等待后自动 advance
            dom.autoHint.classList.remove('d-none');
            await sleep(config.autoNextDelay);
            dom.autoHint.classList.add('d-none');
            if (!state.isEnded) {
                await advance();
            }
        } else if (node.type === 'choice') {
            // choice 节点：渲染选项
            const choices = node.choices || [];
            if (choices.length === 0) {
                handleApiError(new Error('剧情数据异常：当前节点没有选项'));
                return;
            }
            renderChoices(choices);
        }
    }

    /**
     * 渲染选项按钮
     */
    function renderChoices(choices) {
        dom.choiceBar.innerHTML = '';
        choices.forEach(c => {
            const btn = document.createElement('button');
            btn.className = 'choice-btn';
            btn.textContent = c.text;
            btn.dataset.target = c.target;
            btn.addEventListener('click', () => {
                // 禁用所有选项，防止重复点击
                dom.choiceBar.querySelectorAll('.choice-btn').forEach(b => b.disabled = true);
                submitChoice(c.id);
            });
            dom.choiceBar.appendChild(btn);
        });
        dom.choiceBar.classList.remove('d-none');
    }

    /**
     * 提交数字选择
     */
    async function submitChoice(choiceId) {
        if (!state.gameId || state.isEnded) return;
        try {
            dom.choiceBar.classList.add('d-none');
            const node = await TheaterAPI.makeChoice(state.gameId, choiceId);
            await renderNode(node);
        } catch (err) {
            handleApiError(err);
            // 重新显示选项让用户再选
            dom.choiceBar.classList.remove('d-none');
            dom.choiceBar.querySelectorAll('.choice-btn').forEach(b => b.disabled = false);
        }
    }

    /**
     * 提交报警
     */
    async function submitAlert() {
        if (!state.gameId || state.isEnded) return;
        // 显示用户"报警"消息
        ChatRenderer.appendMessage(dom.chatBody, { role: 'user', text: '我要报警！' });
        try {
            const node = await TheaterAPI.makeChoice(state.gameId, '报警');
            await renderNode(node);
        } catch (err) {
            handleApiError(err);
        }
    }

    /**
     * 推进 auto 节点
     * 通过深度计数支持连续 auto→auto 链（每个 auto 节点渲染完即推进到 next，
     * 嵌套调用不会被拦截），同时防止外部并发重复推进。
     */
    async function advance() {
        if (!state.gameId || state.isEnded) return;
        advanceDepth++;
        try {
            const node = await TheaterAPI.advanceNode(state.gameId);
            await renderNode(node);
        } catch (err) {
            // 某些节点不支持 advance（choice 节点），静默处理
            if (!err.message.includes('不支持自动推进')) {
                handleApiError(err);
            }
        } finally {
            advanceDepth--;
        }
    }

    /**
     * 处理结局：调用上层回调
     */
    function handleEnding(node) {
        dom.alertBtn.classList.add('d-none');
        dom.choiceBar.classList.add('d-none');
        dom.autoHint.classList.add('d-none');
        if (typeof state.onEnding === 'function') {
            state.onEnding(node.ending || {
                title: '剧情结束',
                category: 'normal',
                paragraphs: node.content || [],
                achievement: '完成体验'
            });
        }
    }

    /**
     * 统一错误处理
     */
    function handleApiError(err) {
        if (err.isConnectionError && err.isConnectionError()) {
            if (typeof state.onConnectionLost === 'function') {
                state.onConnectionLost(err);
                return;
            }
        }
        if (typeof state.onError === 'function') {
            state.onError(err);
        } else {
            console.error('[GameState]', err);
        }
    }

    /**
     * 退出游戏：调用后端 DELETE
     */
    async function exit() {
        if (state.gameId) {
            await TheaterAPI.endGame(state.gameId);
        }
        state.gameId = null;
        state.isEnded = false;
        state.currentNode = null;
    }

    function sleep(ms) {
        return new Promise(r => setTimeout(r, ms));
    }

    return {
        init,
        start,
        submitChoice,
        submitAlert,
        exit,
        state,
        config,
        set onEnding(fn) { state.onEnding = fn; },
        set onError(fn) { state.onError = fn; },
        set onConnectionLost(fn) { state.onConnectionLost = fn; }
    };
})();
