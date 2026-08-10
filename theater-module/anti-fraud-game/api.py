from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from scenarios import scenarios
import uuid

app = FastAPI(title="反诈骗游戏API", description="提供反诈骗游戏的API接口")

# CORS：允许前端（Live Server / 静态站点）跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 游戏状态存储（内存）
games = {}

# 性别 / 身份 中文映射
GENDER_MAP = {"1": "男", "2": "女", "3": "其他"}
IDENTITY_MAP = {
    "1": "大学生", "2": "上班族", "3": "自由职业者",
    "4": "退休人员", "5": "企业主"
}


def replace_placeholders(text, user_info):
    """替换占位符 {name}/{surname}/{gender}/{identity}"""
    name = user_info.get("name", "")
    gender = GENDER_MAP.get(user_info.get("gender"), "")
    identity = IDENTITY_MAP.get(user_info.get("identity"), "")
    return (text.replace("{name}", name)
                .replace("{surname}", name[0] if name else "")
                .replace("{gender}", gender)
                .replace("{identity}", identity))


# ------------------ 数据模型 ------------------
class UserInfo(BaseModel):
    name: str
    gender: str
    identity: str
    scenario_id: str = "1"


class Choice(BaseModel):
    choice: str


class GameState(BaseModel):
    game_id: str
    node_id: str
    content: list
    type: str
    choices: list = []
    allow_alert: bool = False
    next: Optional[str] = None
    scenario_id: str = ""
    scenario_name: str = ""
    image_dir: str = ""
    is_ending: bool = False
    ending: Optional[dict] = None


def build_node_response(game_id):
    """构建当前节点的响应数据"""
    game_state = games[game_id]
    scenario_id = game_state["scenario_id"]
    scenario_meta = scenarios[scenario_id]
    scenario = scenario_meta["scenario"]
    current_node = game_state["current_node"]
    node = scenario.get(current_node)

    if not node:
        raise HTTPException(status_code=404, detail=f"节点不存在: {current_node}")

    user_info = game_state["user_info"]

    # 处理内容（替换占位符）
    content = []
    if "content" in node:
        for line in node["content"]:
            content.append(replace_placeholders(line, user_info))

    # 处理选项
    choices = []
    if "choices" in node:
        for i, (text, target) in enumerate(node["choices"], 1):
            choices.append({
                "id": str(i),
                "text": replace_placeholders(text, user_info),
                "target": target
            })

    # 结局节点：返回结构化结局数据
    ending_info = None
    is_ending = False
    if node["type"] == "ending":
        is_ending = True
        ending_id = node.get("ending_id")
        if ending_id:
            ending_info = scenario_meta["endings"].get(ending_id)

    return GameState(
        game_id=game_id,
        node_id=current_node,
        content=content,
        type=node["type"],
        choices=choices,
        allow_alert=node.get("allow_alert", False),
        next=node.get("next"),
        scenario_id=scenario_id,
        scenario_name=scenario_meta["name"],
        image_dir=scenario_meta.get("image_dir", ""),
        is_ending=is_ending,
        ending=ending_info
    )


# ------------------ 接口 ------------------
@app.get("/api/scenarios")
async def get_scenarios():
    """获取所有可选场景（不含剧透，供前端场景选择页使用）"""
    return {
        "scenarios": [
            {
                "id": sid,
                "name": s["name"],
                "description": s["description"],
                "icon": s["icon"],
                "theme": s["theme"],
                "tags": s["tags"],
                "difficulty": s["difficulty"],
                "cover": s.get("cover")
            }
            for sid, s in scenarios.items()
        ]
    }


@app.post("/api/game/start", response_model=GameState)
async def start_game(user_info: UserInfo):
    """开始游戏：提交用户信息 + 场景选择，返回初始节点"""
    if not user_info.name or len(user_info.name) < 2 or len(user_info.name) > 4:
        raise HTTPException(status_code=400, detail="姓名必须是2-4个汉字")
    if user_info.gender not in ["1", "2", "3"]:
        raise HTTPException(status_code=400, detail="性别选择无效")
    if user_info.identity not in ["1", "2", "3", "4", "5"]:
        raise HTTPException(status_code=400, detail="身份选择无效")
    if user_info.scenario_id not in scenarios:
        raise HTTPException(status_code=400, detail="场景选择无效")

    game_id = str(uuid.uuid4())
    games[game_id] = {
        "game_id": game_id,
        "current_node": "0",
        "scenario_id": user_info.scenario_id,
        "user_info": user_info.dict()
    }
    return build_node_response(game_id)


@app.get("/api/game/{game_id}/node", response_model=GameState)
async def get_node(game_id: str):
    """获取当前游戏节点（只读，不推进）"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="游戏不存在")
    return build_node_response(game_id)


@app.post("/api/game/{game_id}/advance", response_model=GameState)
async def advance_node(game_id: str):
    """推进 auto 节点到 next，返回新节点"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="游戏不存在")
    game_state = games[game_id]
    scenario = scenarios[game_state["scenario_id"]]["scenario"]
    node = scenario.get(game_state["current_node"])
    if not node or node["type"] != "auto" or "next" not in node:
        raise HTTPException(status_code=400, detail="当前节点不支持自动推进")
    game_state["current_node"] = node["next"]
    return build_node_response(game_id)


@app.post("/api/game/{game_id}/choice", response_model=GameState)
async def make_choice(game_id: str, choice: Choice):
    """提交选择（choice 节点）：选项数字或"报警" """
    if game_id not in games:
        raise HTTPException(status_code=404, detail="游戏不存在")
    game_state = games[game_id]
    scenario_meta = scenarios[game_state["scenario_id"]]
    scenario = scenario_meta["scenario"]
    node = scenario.get(game_state["current_node"])

    if not node or node["type"] != "choice":
        raise HTTPException(status_code=400, detail="当前节点不支持选择")

    selected = choice.choice
    if selected == "报警":
        alert_node = scenario_meta.get("alert_node")
        if not alert_node:
            raise HTTPException(status_code=400, detail="当前场景不支持报警")
        game_state["current_node"] = alert_node
    else:
        try:
            idx = int(selected) - 1
            if 0 <= idx < len(node["choices"]):
                game_state["current_node"] = node["choices"][idx][1]
            else:
                raise HTTPException(status_code=400, detail="选择无效")
        except ValueError:
            raise HTTPException(status_code=400, detail="选择必须是数字")

    return build_node_response(game_id)


@app.get("/api/games")
async def get_games():
    """获取所有游戏状态"""
    return {
        "games": [{
            "game_id": gid,
            "current_node": gs["current_node"],
            "scenario_id": gs["scenario_id"]
        } for gid, gs in games.items()]
    }


@app.delete("/api/game/{game_id}")
async def end_game(game_id: str):
    """结束游戏"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="游戏不存在")
    del games[game_id]
    return {"message": "游戏已结束"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
