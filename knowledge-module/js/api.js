/* ============================================================
 * api.js - 反诈知识库后端 API 封装
 * 提供与 FastAPI 后端 /api/knowledge/* 交互的所有方法
 * ============================================================ */

const KnowledgeAPI = (function () {
    // 后端基础地址（FastAPI 默认端口 8000）
    const BASE_URL = 'http://127.0.0.1:8000';

    // 请求超时（毫秒）
    const TIMEOUT_MS = 10000;

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
                throw new APIError('无法连接服务，请确认后端已启动', -1);
            }
            throw new APIError(err.message || '网络请求失败', -2);
        }
    }

    // ------------------ 对外接口 ------------------

    return {
        APIError,

        /** 获取全部知识主题列表 */
        async getTopics() {
            const data = await request('/api/knowledge/topics');
            return data.topics || [];
        },

        /** 获取单个主题详情（套路/话术/信号/法则/案例/相关推荐） */
        async getTopic(topicId) {
            return await request(`/api/knowledge/topics/${encodeURIComponent(String(topicId))}`);
        },

        /** 拉取一组自测题（不含答案，count: 5/10，topicId 可选） */
        async getQuiz(count, topicId) {
            const params = new URLSearchParams({ count: String(count) });
            if (topicId) params.set('topic_id', String(topicId));
            const data = await request(`/api/knowledge/quiz?${params.toString()}`);
            return data.questions || [];
        },

        /** 交卷判分：answers: [{qid, choice}] → 总分/正确率/称号/逐题回顾 */
        async submitQuiz(answers) {
            return await request('/api/knowledge/quiz/submit', {
                method: 'POST',
                body: JSON.stringify({ answers })
            });
        },

        /** 健康检查（用于连接失败重试） */
        async ping() {
            try {
                await request('/api/knowledge/topics');
                return true;
            } catch (_) {
                return false;
            }
        }
    };
})();
