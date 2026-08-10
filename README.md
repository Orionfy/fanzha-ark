# fanzha-ark 反诈训练营 · 闯关剧场 & 话术实战营

沉浸式反诈教育互动游戏，通过模拟真实诈骗对话场景，帮助用户识别骗术、提升防骗能力。

> **闯关剧场**：选择驱动，模拟真实诈骗对话，每个选择影响结局。
> **话术实战营**：自由对话攻防（开创性玩法）——没有预设选项，玩家真正打字回复虚拟骗子，系统实时识别回复意图、扫描诈骗信号、评定防御力，在话术心理战中练出反诈本能。

## 项目结构

```
fanzha-ark/
├── index.html                      # 主入口页面（反诈训练营）
├── theater.html                    # 闯关剧场页面
├── battle.html                     # 话术实战营页面（自由对话攻防）
├── theater-module/                 # 闯关剧场模块
│   ├── anti-fraud-game/            # 反诈游戏后端（FastAPI）
│   │   ├── api.py                  # API 入口（含 /api/battle/* 路由）
│   │   ├── core/                   # 游戏核心逻辑（CLI）
│   │   ├── scenarios/              # 7 个诈骗场景节点数据
│   │   ├── endings/                # 各场景结局数据
│   │   └── battle/                 # 话术实战营后端
│   │       ├── scenarios.py        # 4 个对战剧本（刷单/客服/杀猪盘/公检法）
│   │       ├── intent.py           # 意图识别 + 信号扫描 + 防御力评分引擎
│   │       ├── engine.py           # 对战状态机（HP/心态/评级/结局）
│   │       └── router.py           # /api/battle/* 路由
│   ├── images/                     # 场景图片资源（按场景分目录）
│   ├── css/                        # 前端样式
│   └── js/                         # 前端逻辑（聊天渲染、状态机）
└── battle-module/                  # 话术实战营前端
    ├── css/battle.css              # 深色星空 + 紫罗兰战斗主题
    └── js/                         # api.js + battle-main.js（战斗状态机）
```

## 后端依赖（Conda 环境）

后端基于 Python + FastAPI，已在以下版本验证通过：

### Python 版本
- **Python 3.14.3**

### 核心依赖包

| 包名            | 版本     | 说明                          |
| --------------- | -------- | ----------------------------- |
| fastapi         | 0.141.1  | Web 框架                      |
| uvicorn         | 0.52.0   | ASGI 服务器                   |
| pydantic        | 2.13.4   | 数据校验                      |
| starlette       | 1.3.1    | ASGI 工具集（fastapi 依赖）   |
| h11             | 0.16.0   | HTTP/1.1 协议（uvicorn 依赖） |
| anyio           | 4.14.2   | 异步兼容层                    |
| click           | 8.4.2    | 命令行工具（uvicorn 依赖）    |
| typing-extensions | 4.16.0 | 类型扩展（pydantic 依赖）     |
| annotated-types | 0.8.0    | 注解类型（pydantic 依赖）     |
| pydantic-core   | 2.46.4   | pydantic 核心引擎             |
| idna            | 3.18     | 域名解析                      |

> 表格中 `fastapi`、`uvicorn`、`pydantic` 为直接依赖，其余为传递依赖（安装直接依赖时自动装入）。

## 环境安装

### 方式一：使用 Conda 创建独立环境（推荐）

```bash
# 进入后端目录
cd theater-module/anti-fraud-game

# 创建 conda 环境（指定目录，便于项目管理）
conda create --prefix .conda python=3.14 -y

# 激活环境
conda activate ./.conda

# 安装核心依赖
pip install fastapi==0.141.1 uvicorn==0.52.0 pydantic==2.13.4
```

### 方式二：使用系统 Python / venv

```bash
cd theater-module/anti-fraud-game

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 安装依赖
pip install fastapi==0.141.1 uvicorn==0.52.0 pydantic==2.13.4
```

## 启动项目

### 1. 启动后端 API 服务

```bash
cd theater-module/anti-fraud-game
conda activate ./.conda           # 或 source venv/bin/activate
python -m uvicorn api:app --port 8000
```

后端启动后访问 http://127.0.0.1:8000/api/scenarios 可查看场景列表。

### 2. 启动前端静态服务

在项目根目录另开一个终端：

```bash
python3 -m http.server 5500
```

浏览器访问 http://127.0.0.1:5500/theater.html 即可进入闯关剧场。

## 场景列表

| ID | 场景名称         | 难度   |
| -- | ---------------- | ------ |
| 1  | 理赔诈骗         | ★★☆    |
| 2  | 裸聊敲诈诈骗     | ★★★    |
| 3  | 票务诈骗         | ★★☆    |
| 4  | 假冒商品诈骗     | ★★☆    |
| 5  | 杀猪盘诈骗       | ★★★    |
| 6  | 刷单返利诈骗     | ★★☆    |
| 7  | 冒充公检法诈骗   | ★★★    |

> 闯关剧场后端接口：`/api/scenarios`、`/api/game/*`（场景节点图 + 结局数据驱动）

## 话术实战营剧本

| ID | 剧本名称       | 骗子策略 | 难度   |
| -- | -------------- | -------- | ------ |
| 1  | 刷单返利话术   | 甜蜜诱惑 | ★★☆    |
| 2  | 冒充客服退款话术 | 权威施压 | ★★☆    |
| 3  | 网恋杀猪盘话术 | 情感操控 | ★★★    |
| 4  | 冒充公检法话术 | 恐吓逼迫 | ★★★    |

> 话术实战营接口：`/api/battle/scenarios`、`/api/battle/start`、`/api/battle/{id}/reply`、`/api/battle/{id}/abort`、`DELETE /api/battle/{id}`（与闯关剧场共用同一后端进程）

## 话术实战营 · 心理战机制（v2）

v2 引擎为每局对战引入**骗子心态（mood 0-100）**状态机——骗子的情绪随你的回复实时升降，并联动多种心理战行为，让攻防有真实节奏：

| 机制 | 触发条件 | 表现 |
| ---- | -------- | ---- |
| **贪婪跳转** | 骗子 mood ≥ 90（连续顺从） | 骗子认定你已上钩，跳过中间话术**直接收网**（终局话术），此轮顺从伤害加重至 -45 |
| **破绽轮** | 骗子 mood ≤ 25（被连续拒绝/质疑） | 骗子**语无伦次·破绽显露**，兜底话术从话术池轮换（不再复读），信号升级为高威胁并合成场景化破绽信号；此轮识破类回复额外 +8 分、心态伤害翻倍 |
| **崩溃轮** | 骗子 mood ≤ 5 | 骗子心理崩溃主动挂断，你**提前获胜**（win_expose，无血条代价） |
| **否定识别** | comply 动作词（转账/汇款/打钱/扫码/验证码…）前出现否定词（不/别/没/不会/休想…） | 意图**翻转为 refuse**，"我不转账""别给我发验证码"不再误判为顺从 |
| **敏感信息泄露检测** | 回复中带出卡号/验证码/密码/身份证/住址/微信号 | 判定为泄露（leak）：**重罚 -40 防御力**，附加"敏感信息泄露"高危信号 |
| **动态复盘** | 对局结束 | 每轮 `LogEntry` 日志驱动**动态复盘**：summary/lessons 引用你的真实回合表现，成就随战绩动态评定（如零顺从得"快准狠"） |

> 场景数据新增 `tell_pool`（每场景 5+ 条破绽话术变体）与 `finale_round`（收网轮）字段，由 `battle/scenarios.py` 提供；评分逻辑见 `battle/intent.py`，状态机见 `battle/engine.py`。
