"""反诈知识库 · API 路由（/api/knowledge/*）。"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from .engine import (
    AnswerInput,
    GradeResult,
    TopicCard,
    TopicDetail,
    TopicNotFoundError,
    QuizNotFoundError,
    draw_quiz,
    get_topic,
    grade_quiz,
    list_topics,
)


class TopicListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    topics: list


class QuizListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    questions: list


class SubmitRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    answers: list[AnswerInput] = Field(min_length=1)


router = APIRouter(prefix="/api/knowledge", tags=["反诈知识库"])


@router.get("/topics", response_model=TopicListResponse)
async def get_topics() -> TopicListResponse:
    """诈骗类型百科列表（卡片级字段，供知识库首页使用）"""
    return TopicListResponse(topics=[topic.model_dump() for topic in list_topics()])


@router.get("/topics/{topic_id}", response_model=TopicDetail)
async def get_topic_detail(topic_id: str) -> TopicDetail:
    """主题详情：套路拆解 + 典型话术 + 识别信号 + 防骗法则 + 案例复盘"""
    try:
        return get_topic(topic_id)
    except TopicNotFoundError as error:
        raise HTTPException(status_code=404, detail="该主题不存在") from error


@router.get("/quiz", response_model=QuizListResponse)
async def get_quiz(
    count: int = Query(default=5, ge=1, le=20),
    topic_id: str | None = Query(default=None),
) -> QuizListResponse:
    """随机抽取测验题（不含答案与解析字段）"""
    try:
        questions = draw_quiz(count=count, topic_id=topic_id)
    except TopicNotFoundError as error:
        raise HTTPException(status_code=404, detail="该主题不存在") from error
    return QuizListResponse(questions=[question.model_dump() for question in questions])


@router.post("/quiz/submit", response_model=GradeResult)
async def submit_quiz(request: SubmitRequest) -> GradeResult:
    """提交答案判分：正确率评级 + 逐题复盘"""
    try:
        return grade_quiz(request.answers)
    except QuizNotFoundError as error:
        raise HTTPException(status_code=400, detail=f"题目不存在: {error.qid}") from error
