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

    // 会话令牌：start/exit 时递增；旧的渲染循环（打字机/auto 推进）检测到令牌变化即中止
    let renderToken = 0;

    // 提交互斥标志：选项/报警/推进任一进行中时阻止新的提交
    //（链式 auto 推进属于同一操作的延续，由 renderNode 在链式调用前先释放）
    let busy = false;

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
        renderToken++;  // 使旧的渲染循环（如有）失效
        const token = renderToken;
        state.scenarioId = userInfo.scenario_id;
        state.scenarioName = scenarioName;
        state.isEnded = false;
        busy = false;

        const data = await TheaterAPI.startGame(userInfo);
        if (token !== renderToken) return;  // 等待期间发生了退出/重开，旧响应不得污染新会话
        state.gameId = data.game_id;
        dom.gameScenarioName.textContent = data.scenario_name || scenarioName;

        ChatRenderer.clear(dom.chatBody);
        await renderNode(data);
    }

    /**
     * 渲染一个节点
     */
    async function renderNode(node) {
        const token = renderToken;  // 捕获当前会话令牌
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

        // 报警按钮显隐；打字期间禁用，播完按节点配置恢复
        syncAlertBtn();
        dom.alertBtn.disabled = true;

        // 隐藏选项区
        dom.choiceBar.classList.add('d-none');
        dom.choiceBar.innerHTML = '';

        // 内容渲染：逐行打字机
        const lines = node.content || [];
        for (const line of lines) {
            // 会话已切换（退出/重开）：立即中止本轮渲染
            if (token !== renderToken) return;

            const info = ChatRenderer.detectRole(line);

            // 对话角色（骗子/民警/用户）先显示"正在输入"
            if (['scammer', 'police', 'user'].includes(info.role)) {
                ChatRenderer.showTypingIndicator(dom.chatBody, info.role);
                await sleep(config.typingDelayBefore);
                if (token !== renderToken) {
                    ChatRenderer.hideTypingIndicator(dom.chatBody);
                    return;
                }
                ChatRenderer.hideTypingIndicator(dom.chatBody);
            }

            await ChatRenderer.typewriterAppend(
                dom.chatBody, info, config.typingSpeed,
                () => token !== renderToken
            );
        }

        // 会话已切换：不再分发后续节点逻辑
        if (token !== renderToken) return;

        // 播完恢复报警按钮可用
        dom.alertBtn.disabled = false;

        // 根据节点类型分发
        if (node.type === 'auto' && node.next) {
            // auto 节点：显示"剧情推进中"，等待后自动 advance
            dom.autoHint.classList.remove('d-none');
            await sleep(config.autoNextDelay);
            dom.autoHint.classList.add('d-none');
            if (!state.isEnded && token === renderToken) {
                busy = false;  // 链式推进是同一操作的延续，先释放再由 advance 重新持有
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
     * 按当前节点配置同步报警按钮显隐
     */
    function syncAlertBtn() {
        const allow = !!(state.currentNode && state.currentNode.allow_alert && !state.isEnded);
        dom.alertBtn.classList.toggle('d-none', !allow);
    }

    /**
     * 提交数字选择
     */
    async function submitChoice(choiceId) {
        if (!state.gameId || state.isEnded || busy) return;
        busy = true;
        const token = renderToken;  // 捕获会话令牌，await 后校验防旧响应污染新会话
        const gid = state.gameId;
        try {
            dom.choiceBar.classList.add('d-none');
            const node = await TheaterAPI.makeChoice(gid, choiceId);
            if (token !== renderToken || state.gameId !== gid) return;
            await renderNode(node);
        } catch (err) {
            // 会话已切换：旧选项条属于已结束的会话，放弃恢复
            if (token !== renderToken || state.gameId !== gid) return;
            handleApiError(err);
            // 重新显示选项让用户再选
            dom.choiceBar.classList.remove('d-none');
            dom.choiceBar.querySelectorAll('.choice-btn').forEach(b => b.disabled = false);
        } finally {
            if (token === renderToken) busy = false;
        }
    }

    /**
     * 提交报警
     */
    async function submitAlert() {
        if (!state.gameId || state.isEnded || busy) return;
        busy = true;
        const token = renderToken;
        const gid = state.gameId;
        // 乐观气泡：先展示"报警"，请求失败时回滚移除
        const optimisticEl = ChatRenderer.appendMessage(dom.chatBody, { role: 'user', text: '我要报警！' });
        try {
            const node = await TheaterAPI.makeChoice(gid, '报警');
            if (token !== renderToken || state.gameId !== gid) return;
            await renderNode(node);
        } catch (err) {
            optimisticEl.remove();
            if (token !== renderToken || state.gameId !== gid) return;
            handleApiError(err);
            syncAlertBtn();  // 按 currentNode.allow_alert 恢复按钮显隐
        } finally {
            if (token === renderToken) busy = false;
        }
    }

    /**
     * 推进 auto 节点
     * 通过深度计数支持连续 auto→auto 链（每个 auto 节点渲染完即推进到 next，
     * 嵌套调用不会被拦截），同时防止外部并发重复推进。
     */
    async function advance() {
        if (!state.gameId || state.isEnded || busy) return;
        busy = true;
        const token = renderToken;
        const gid = state.gameId;
        try {
            const node = await TheaterAPI.advanceNode(gid);
            if (token !== renderToken || state.gameId !== gid) return;
            await renderNode(node);
        } catch (err) {
            // 会话已切换或某些节点不支持 advance（choice 节点），静默处理
            if (token !== renderToken || state.gameId !== gid) return;
            if (!err.message.includes('不支持自动推进')) {
                handleApiError(err);
            }
        } finally {
            if (token === renderToken) busy = false;
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
     * 退出游戏：调用后端 DELETE（状态同步重置，请求后台进行不阻塞 UI）
     */
    async function exit() {
        renderToken++;  // 中止仍在进行的打字机与 auto 推进循环
        busy = false;
        const gameId = state.gameId;   // 捕获旧会话 ID
        state.gameId = null;           // 同步重置，避免"退出后立即重开"被旧请求的延续覆盖
        state.isEnded = false;
        state.currentNode = null;
        if (gameId) {
            await TheaterAPI.endGame(gameId);
        }
    }

    /**
     * 连接恢复后续接渲染当前节点：
     * 后端会话仍存活时由重试逻辑调用，避免强制回首页丢弃进度。
     * 以新令牌整体重渲染，中止可能残留的旧打字/推进循环。
     */
    async function resume(node) {
        renderToken++;
        busy = false;
        state.isEnded = false;
        ChatRenderer.clear(dom.chatBody);
        await renderNode(node);
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
        resume,
        state,
        config,
        set onEnding(fn) { state.onEnding = fn; },
        set onError(fn) { state.onError = fn; },
        set onConnectionLost(fn) { state.onConnectionLost = fn; }
    };
})();
