/* ============================================================
 * api.js - 闯关剧场后端 API 封装
 * 提供与 FastAPI 后端交互的所有方法
 * ============================================================ */

const TheaterAPI = (function () {
    // 后端基础地址（FastAPI 默认端口 8000）
    const BASE_URL = 'http://127.0.0.1:8000';

    // 请求超时（毫秒）
    const TIMEOUT_MS = 10000;

    /**
     * 统一 fetch 封装：处理超时、错误、JSON 解析
     * @param {string} path - 接口路径
     * @param {object} options - fetch 配置
     * @returns {Promise<any>}
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

            // 处理 204 No Content
            if (resp.status === 204) return null;
            return await resp.json();
        } catch (err) {
            clearTimeout(timer);
            if (err instanceof APIError) throw err;
            if (err.name === 'AbortError') {
                throw new APIError('请求超时，请检查后端服务是否正常运行', 0);
            }
            // 网络错误（后端未启动）
            if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
                throw new APIError('无法连接游戏服务器', -1);
            }
            throw new APIError(err.message || '网络请求失败', -2);
        }
    }

    /**
     * 自定义错误类
     */
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

        /** 获取所有可选场景 */
        async getScenarios() {
            const data = await request('/api/scenarios');
            return data.scenarios || [];
        },

        /**
         * 开始游戏
         * @param {{name:string, gender:string, identity:string, scenario_id:string}} userInfo
         */
        async startGame(userInfo) {
            return await request('/api/game/start', {
                method: 'POST',
                body: JSON.stringify(userInfo)
            });
        },

        /** 获取当前节点（只读） */
        async getNode(gameId) {
            return await request(`/api/game/${gameId}/node`);
        },

        /** 推进 auto 节点到 next */
        async advanceNode(gameId) {
            return await request(`/api/game/${gameId}/advance`, {
                method: 'POST'
            });
        },

        /**
         * 提交选择（choice 节点）
         * @param {string} gameId
         * @param {string} choice - 选项数字或 "报警"
         */
        async makeChoice(gameId, choice) {
            return await request(`/api/game/${gameId}/choice`, {
                method: 'POST',
                body: JSON.stringify({ choice })
            });
        },

        /** 结束游戏 */
        async endGame(gameId) {
            try {
                await request(`/api/game/${gameId}`, { method: 'DELETE' });
            } catch (_) { /* 静默处理：游戏结束时不再阻塞用户 */ }
        },

        /** 健康检查（用于连接失败重试） */
        async ping() {
            try {
                await request('/api/scenarios');
                return true;
            } catch (_) {
                return false;
            }
        }
    };
})();
