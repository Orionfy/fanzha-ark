const BattleAPI = (function () {
    const BASE_URL = 'http://127.0.0.1:8000';
    const TIMEOUT_MS = 10000;

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
                } catch (_) {}
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

        isConnectionError() {
            return this.status === -1 || this.status === 0;
        }
    }

    return {
        APIError,

        async getScenarios() {
            const data = await request('/api/battle/scenarios');
            return data.scenarios || [];
        },

        async startBattle(scenarioId, playerName) {
            return await request('/api/battle/start', {
                method: 'POST',
                body: JSON.stringify({ scenario_id: scenarioId, player_name: playerName })
            });
        },

        async reply(battleId, text) {
            return await request(`/api/battle/${battleId}/reply`, {
                method: 'POST',
                body: JSON.stringify({ text })
            });
        },

        async abort(battleId) {
            return await request(`/api/battle/${battleId}/abort`, { method: 'POST' });
        },

        async cleanup(battleId) {
            try {
                await request(`/api/battle/${battleId}`, { method: 'DELETE' });
            } catch (_) {}
        },

        async ping() {
            try {
                await request('/api/battle/scenarios');
                return true;
            } catch (_) {
                return false;
            }
        }
    };
})();
