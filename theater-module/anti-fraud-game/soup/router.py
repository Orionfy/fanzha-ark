"""反诈海龟汤 · API 路由（/api/soup/*）。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .engine import (
    PuzzleNotFoundError,
    SoupBusyError,
    SoupFinishedError,
    SoupNotFoundError,
    delete_session,
    get_hint,
    list_puzzles,
    ask_question,
    reveal_answer,
    start_session,
)


class StartRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    puzzle_id: str


class AskRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1, max_length=200)


class PuzzleListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    puzzles: list


class MessageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str


router = APIRouter(prefix="/api/soup", tags=["反诈海龟汤"])


@router.get("/puzzles", response_model=PuzzleListResponse)
async def get_puzzles() -> PuzzleListResponse:
    """谜题列表（不含汤底与线索剧透，供谜题选择页使用）"""
    return PuzzleListResponse(puzzles=[p.model_dump() for p in list_puzzles()])


@router.post("/start")
async def start(request: StartRequest):
    """开始解谜：返回汤面 + 线索进度"""
    try:
        return start_session(request.puzzle_id)
    except PuzzleNotFoundError as error:
        raise HTTPException(status_code=400, detail="谜题不存在") from error


@router.post("/{session_id}/ask")
async def ask(session_id: str, request: AskRequest):
    """提交一个问题，主持人回答「是 / 否 / 无关 / 已问过」"""
    try:
        return ask_question(session_id, request.text)
    except SoupNotFoundError as error:
        raise HTTPException(status_code=404, detail="解谜会话不存在") from error
    except SoupFinishedError as error:
        raise HTTPException(status_code=400, detail="本局已揭晓汤底，请重新开始") from error
    except SoupBusyError as error:
        raise HTTPException(status_code=409, detail="请求处理中，请稍候再试") from error


@router.post("/{session_id}/hint")
async def hint(session_id: str):
    """获取方向性提示（影响最终评级）"""
    try:
        return get_hint(session_id)
    except SoupNotFoundError as error:
        raise HTTPException(status_code=404, detail="解谜会话不存在") from error
    except SoupFinishedError as error:
        raise HTTPException(status_code=400, detail="本局已揭晓汤底，请重新开始") from error
    except SoupBusyError as error:
        raise HTTPException(status_code=409, detail="请求处理中，请稍候再试") from error


@router.post("/{session_id}/reveal")
async def reveal(session_id: str):
    """揭晓汤底：完整还原 + 线索复盘 + 侦探评级"""
    try:
        return reveal_answer(session_id)
    except SoupNotFoundError as error:
        raise HTTPException(status_code=404, detail="解谜会话不存在") from error
    except SoupFinishedError as error:
        raise HTTPException(status_code=400, detail="本局已揭晓汤底，请重新开始") from error
    except SoupBusyError as error:
        raise HTTPException(status_code=409, detail="请求处理中，请稍候再试") from error


@router.delete("/{session_id}", response_model=MessageResponse)
async def remove(session_id: str) -> MessageResponse:
    """退出解谜，清理会话"""
    try:
        delete_session(session_id)
    except SoupNotFoundError as error:
        raise HTTPException(status_code=404, detail="解谜会话不存在") from error
    return MessageResponse(message="解谜已结束")
