from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .engine import (
    BattleFinishedError,
    BattleNotFoundError,
    BattleState,
    ScenarioNotFoundError,
    abort_battle,
    delete_battle,
    list_scenarios,
    reply_to_battle,
    start_battle,
)


class StartRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario_id: str
    player_name: str = Field(min_length=1, max_length=10)


class ReplyRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1, max_length=500)


class ScenarioSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    description: str
    icon: str
    theme: str
    tags: list[str]
    difficulty: str
    cover: str
    rounds: int
    fraud_type: str
    tips: list[str]


class ScenarioListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenarios: list[ScenarioSummary]


class MessageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str


router = APIRouter(prefix="/api/battle", tags=["话术实战营"])


@router.get("/scenarios", response_model=ScenarioListResponse)
async def get_battle_scenarios() -> ScenarioListResponse:
    summaries = [
        ScenarioSummary(
            id=scenario["id"], name=scenario["name"], description=scenario["description"],
            icon=scenario["icon"], theme=scenario["theme"], tags=scenario["tags"],
            difficulty=scenario["difficulty"], cover=scenario["cover"], rounds=len(scenario["rounds"]),
            fraud_type=scenario["fraud_type"], tips=scenario["tips"],
        )
        for scenario in list_scenarios()
    ]
    return ScenarioListResponse(scenarios=summaries)


@router.post("/start", response_model=BattleState)
async def start(request: StartRequest) -> BattleState:
    try:
        return start_battle(request.scenario_id, request.player_name)
    except ScenarioNotFoundError as error:
        raise HTTPException(status_code=400, detail="对战场景不存在") from error


@router.post("/{battle_id}/reply", response_model=BattleState)
async def reply(battle_id: str, request: ReplyRequest) -> BattleState:
    try:
        return reply_to_battle(battle_id, request.text)
    except BattleNotFoundError as error:
        raise HTTPException(status_code=404, detail="对战不存在") from error
    except BattleFinishedError as error:
        raise HTTPException(status_code=400, detail="对战已经结束") from error


@router.post("/{battle_id}/abort", response_model=BattleState)
async def abort(battle_id: str) -> BattleState:
    try:
        return abort_battle(battle_id)
    except BattleNotFoundError as error:
        raise HTTPException(status_code=404, detail="对战不存在") from error


@router.delete("/{battle_id}", response_model=MessageResponse)
async def remove(battle_id: str) -> MessageResponse:
    try:
        delete_battle(battle_id)
    except BattleNotFoundError as error:
        raise HTTPException(status_code=404, detail="对战不存在") from error
    return MessageResponse(message="对战已结束")
