/* ============================================================
 * chat-renderer.js - 聊天 UI 渲染引擎
 * 解析场景文本行，识别角色（骗子/民警/用户/旁白/系统/图片），
 * 渲染仿微信气泡 + 打字机效果 + "正在输入"动画
 * ============================================================ */

const ChatRenderer = (function () {

    // 当前场景图片目录（用于拼接图片路径）
    let currentImageDir = '';

    // 角色检测正则
    const RE_SCAMMER = /^(👩‍💼|对方|骗子|客服|雯雯|淘乐购|蜜聊|黄牛|代购|卖家|陌生人|对方发话|对方说|对方继续)/;
    const RE_POLICE = /^(👮|民警|警察|警官|公安|110|反诈中心)/;
    const RE_USER = /^(你[:：]|你说|你回复|你回答|你选择|你发|你按|你的|你打开|你点|你接|你挂|你看|你想|你意识|你决定)/;
    const RE_NARRATOR = /^[（(]/;  // 中文/英文括号开头
    const RE_SYSTEM = /^(【系统|【短信|【来电|【微信|【视频|【电话|【消息|【通知|【蜜聊|【淘乐购|📞|📱|━━)/;
    const RE_IMAGE = /^\[图片\]/;
    const RE_DIVIDER = /^[━─═]{6,}/;

    /**
     * 识别一行文本的角色
     * @param {string} line
     * @returns {{role:string, text:string}}
     */
    function detectRole(line) {
        const text = line.trim();
        if (!text) return { role: 'empty', text: '' };

        if (RE_DIVIDER.test(text)) return { role: 'divider', text };
        if (RE_IMAGE.test(text)) return { role: 'image', text: text.replace(/^\[图片\]\s*/, '') };
        if (RE_SYSTEM.test(text)) return { role: 'system', text };
        if (RE_NARRATOR.test(text)) return { role: 'narrator', text };
        if (RE_POLICE.test(text)) return { role: 'police', text };
        if (RE_SCAMMER.test(text)) return { role: 'scammer', text };
        if (RE_USER.test(text)) return { role: 'user', text };

        // 默认：根据上下文判定为骗子（场景中骗子台词最多）
        return { role: 'scammer', text };
    }

    /**
     * 创建一条聊天消息 DOM（不含打字机效果，用于一次性渲染）
     * @param {{role:string, text:string}} info
     * @returns {HTMLElement}
     */
    function createMessageEl(info) {
        const row = document.createElement('div');
        row.className = `chat-row row-${info.role}`;

        // 旁白/系统/分隔线/图片：特殊渲染
        if (info.role === 'narrator') {
            const bubble = document.createElement('div');
            bubble.className = 'bubble bubble-narrator';
            bubble.textContent = info.text;
            row.appendChild(bubble);
            return row;
        }
        if (info.role === 'system') {
            const bubble = document.createElement('div');
            bubble.className = 'bubble bubble-system';
            bubble.textContent = info.text;
            row.appendChild(bubble);
            return row;
        }
        if (info.role === 'divider') {
            const div = document.createElement('div');
            div.className = 'bubble-divider';
            div.textContent = info.text;
            row.appendChild(div);
            return row;
        }
        if (info.role === 'image') {
            row.className = 'chat-row row-image';
            const card = document.createElement('div');
            card.className = 'bubble-image';

            // 拼接图片路径：theater-module/images/<image_dir>/<filename>
            //（theater.html 位于根目录，资源路径以 theater-module/ 开头）
            const filename = info.text.trim();
            const imgPath = `theater-module/images/${currentImageDir || 'unknown'}/${filename}`;

            // 先渲染真实图片，onerror 时回退到占位卡片；
            // 加载完成添加 loaded 淡入，点击图片可就地放大/还原
            card.innerHTML = `
                <img class="img-real" src="${escapeHtml(imgPath)}" alt="${escapeHtml(filename)}"
                     loading="lazy"
                     onload="this.classList.add('loaded')"
                     onclick="this.classList.toggle('zoomed')"
                     onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="img-fallback" style="display:none;">
                    <div class="img-icon"><i class="bi bi-image"></i></div>
                    <div class="img-info">
                        <div class="img-name">${escapeHtml(filename)}</div>
                        <div class="img-hint">图片占位 · 实际场景中为骗术素材</div>
                    </div>
                </div>`;
            row.appendChild(card);
            return row;
        }
        if (info.role === 'empty') {
            row.style.margin = '0';
            row.style.height = '4px';
            return row;
        }

        // 三类对话角色：骗子/民警/用户
        const avatar = document.createElement('div');
        avatar.className = `avatar avatar-${info.role}`;
        const iconMap = { scammer: '👩\u200d💼', police: '👮', user: '🧑' };
        avatar.textContent = iconMap[info.role] || '💬';

        const bubble = document.createElement('div');
        bubble.className = `bubble bubble-${info.role}`;
        bubble.textContent = info.text;

        // 用户消息：头像在右
        if (info.role === 'user') {
            row.appendChild(bubble);
            row.appendChild(avatar);
        } else {
            row.appendChild(avatar);
            row.appendChild(bubble);
        }
        return row;
    }

    /**
     * HTML 转义
     */
    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    /**
     * 在容器中追加一条消息（带气泡进入动画）
     */
    function appendMessage(chatBody, info) {
        const el = createMessageEl(info);
        chatBody.appendChild(el);
        scrollToBottom(chatBody);
        return el;
    }

    /**
     * 创建"正在输入"指示器
     */
    function showTypingIndicator(chatBody, role = 'scammer') {
        hideTypingIndicator(chatBody);
        const row = document.createElement('div');
        row.className = `chat-row row-${role} typing-row`;
        row.id = '__typing_indicator__';

        if (role !== 'user') {
            const avatar = document.createElement('div');
            avatar.className = `avatar avatar-${role}`;
            avatar.textContent = role === 'police' ? '👮' : '👩\u200d💼';
            row.appendChild(avatar);
        }

        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.innerHTML = `
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>`;
        row.appendChild(indicator);

        if (role === 'user') {
            // 用户消息时，头像在右
            const avatar = document.createElement('div');
            avatar.className = 'avatar avatar-user';
            avatar.textContent = '🧑';
            row.appendChild(avatar);
            // 调整顺序：indicator 在前，avatar 在后
            row.insertBefore(indicator, avatar);
        }

        chatBody.appendChild(row);
        scrollToBottom(chatBody);
    }

    function hideTypingIndicator(chatBody) {
        const existing = chatBody.querySelector('#__typing_indicator__');
        if (existing) existing.remove();
    }

    /**
     * 打字机效果渲染一条消息
     * @param {HTMLElement} chatBody
     * @param {{role:string, text:string}} info
     * @param {number} speed - 每字毫秒（默认 35ms）
     * @param {function|null} shouldAbort - 中止判断回调（返回 true 时立即停止打字，用于退出/重开游戏时取消旧渲染）
     * @returns {Promise<void>}
     */
    function typewriterAppend(chatBody, info, speed = 35, shouldAbort = null) {
        return new Promise(resolve => {
            // 旁白/系统/分隔线/图片/空行：直接追加，不打字机
            if (['narrator', 'system', 'divider', 'image', 'empty'].includes(info.role)) {
                if (shouldAbort && shouldAbort()) { resolve(); return; }
                appendMessage(chatBody, info);
                // 短暂延迟，让用户看到
                setTimeout(resolve, info.role === 'divider' ? 200 : 400);
                return;
            }

            // 三类对话角色：打字机
            const row = createMessageEl(info);
            const bubble = row.querySelector('.bubble');
            if (!bubble) { appendMessage(chatBody, info); resolve(); return; }

            // 清空文字，准备打字
            const fullText = info.text;
            bubble.textContent = '';
            chatBody.appendChild(row);
            scrollToBottom(chatBody);

            // 添加光标
            const cursor = document.createElement('span');
            cursor.className = 'typing-cursor';
            bubble.appendChild(cursor);

            let i = 0;
            const tick = () => {
                // 会话已切换（退出/重开）：立即停止打字并清理光标
                if (shouldAbort && shouldAbort()) {
                    cursor.remove();
                    resolve();
                    return;
                }
                if (i >= fullText.length) {
                    cursor.remove();
                    resolve();
                    return;
                }
                // 一次推进 1 个字符（中文按 Unicode 码点处理）
                const ch = fullText[i++];
                bubble.insertBefore(document.createTextNode(ch), cursor);
                if (i % 3 === 0) scrollToBottom(chatBody);
                setTimeout(tick, speed);
            };
            tick();
        });
    }

    /**
     * 滚动到底部
     */
    function scrollToBottom(chatBody) {
        requestAnimationFrame(() => {
            chatBody.scrollTop = chatBody.scrollHeight;
        });
    }

    /**
     * 清空聊天区
     */
    function clear(chatBody) {
        chatBody.innerHTML = '';
    }

    /**
     * 设置当前场景图片目录（用于拼接图片路径）
     * @param {string} imageDir
     */
    function setImageDir(imageDir) {
        currentImageDir = imageDir || '';
    }

    return {
        detectRole,
        createMessageEl,
        appendMessage,
        typewriterAppend,
        showTypingIndicator,
        hideTypingIndicator,
        scrollToBottom,
        clear,
        setImageDir
    };
})();
