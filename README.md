# fanzha-ark 反诈训练营 · 闯关剧场

沉浸式反诈教育互动游戏，通过模拟真实诈骗对话场景，帮助用户识别骗术、提升防骗能力。

## 项目结构

```
fanzha-ark/
├── index.html                      # 主入口页面（反诈训练营）
├── theater.html                    # 闯关剧场页面
└── theater-module/                 # 剧场模块
    ├── anti-fraud-game/            # 反诈游戏后端（FastAPI）
    │   ├── api.py                  # API 入口
    │   ├── core/                   # 游戏核心逻辑
    │   ├── scenarios/              # 7 个诈骗场景节点数据
    │   └── endings/                # 各场景结局数据
    ├── images/                     # 场景图片资源（按场景分目录）
    ├── css/                        # 前端样式
    └── js/                         # 前端逻辑（聊天渲染、状态机）
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
