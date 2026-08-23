/* ============================================================
 * api.js - 反诈海龟汤后端 API 封装
 * 提供与 FastAPI 后端 /api/soup/* 交互的所有方法
 * ============================================================ */

const SoupAPI = (function () {
    // 后端基础地址（FastAPI 默认端口 8000）
    const BASE_URL = 'http://127.0.0.1:8000';

    // 请求超时（毫秒）
    const TIMEOUT_MS = 10000;

    /**
     * 统一 fetch 封装：处理超时、错误、JSON 解析
     */
    async function request(path, options = {}) {
        const url = BASE_URL + path;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

        try {
            const resp = await fetch(url, {
                ...options,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    ...(options.headers || {})
                }
            });
            clearTimeout(timer);

            if (!resp.ok) {
                let detail = `HTTP ${resp.status}`;
                try {
                    const errBody = await resp.json();
                    detail = errBody.detail || detail;
                } catch (_) { /* ignore */ }
                throw new APIError(detail, resp.status);
            }

            if (resp.status === 204) return null;
            return await resp.json();
        } catch (err) {
            clearTimeout(timer);
            if (err instanceof APIError) throw err;
            if (err.name === 'AbortError') {
                throw new APIError('请求超时，请检查后端服务是否正常运行', 0);
            }
            if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
                throw new APIError('无法连接游戏服务器', -1);
            }
            throw new APIError(err.message || '网络请求失败', -2);
        }
    }

    class APIError extends Error {
        constructor(message, status) {
            super(message);
            this.name = 'APIError';
            this.status = status;
        }

        /** 是否连接失败（后端未启动） */
        isConnectionError() {
            return this.status === -1 || this.status === 0;
        }
    }

    // ------------------ 对外接口 ------------------

    return {
        APIError,

        /** 获取所有谜题（不含汤底剧透） */
        async getPuzzles() {
            const data = await request('/api/soup/puzzles');
            return data.puzzles || [];
        },

        /** 开始解谜：返回汤面 + 线索进度 */
        async startPuzzle(puzzleId) {
            return await request('/api/soup/start', {
                method: 'POST',
                body: JSON.stringify({ puzzle_id: puzzleId })
            });
        },

        /** 提交一个问题 */
        async askQuestion(sessionId, text) {
            return await request(`/api/soup/${sessionId}/ask`, {
                method: 'POST',
                body: JSON.stringify({ text })
            });
        },

        /** 获取方向性提示 */
        async getHint(sessionId) {
            return await request(`/api/soup/${sessionId}/hint`, {
                method: 'POST'
            });
        },

        /** 揭晓汤底（含评级与复盘） */
        async revealAnswer(sessionId) {
            return await request(`/api/soup/${sessionId}/reveal`, {
                method: 'POST'
            });
        },

        /** 退出解谜 */
        async exitSession(sessionId) {
            try {
                await request(`/api/soup/${sessionId}`, { method: 'DELETE' });
            } catch (_) { /* 静默处理：退出时不再阻塞用户 */ }
        },

        /** 健康检查（用于连接失败重试） */
        async ping() {
            try {
                await request('/api/soup/puzzles');
                return true;
            } catch (_) {
                return false;
            }
        }
    };
})();
