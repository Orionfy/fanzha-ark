"""反诈知识库 · 百科与测验引擎。

纯函数、无会话状态：
- list_topics / get_topic：诈骗类型百科卡片与详情
- draw_quiz：无状态随机抽题（绝不外泄 correct_index / explanation）
- grade_quiz：提交判分 + 正确率评级 + 逐题复盘
"""

import random
from dataclasses import dataclass
from typing import Final

from pydantic import BaseModel, ConfigDict

from .data import QUIZ_BANK, TOPICS, FraudTopic, QuizQuestion

MIN_DRAW_COUNT: Final[int] = 1
MAX_DRAW_COUNT: Final[int] = 20

# 评级阈值：正确率 ≥90 反诈专家 / ≥70 反诈达人 / ≥50 初窥门径 / 其余 防诈新兵
RATING_THRESHOLDS: Final[tuple[tuple[int, str], ...]] = (
    (90, "反诈专家"),
    (70, "反诈达人"),
    (50, "初窥门径"),
)
DEFAULT_RATING: Final[str] = "防诈新兵"


class TopicCard(BaseModel):
    """主题卡片：列表页字段，不含详情内容。"""
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    icon: str
    tagline: str
    difficulty: str
    quiz_count: int


class CaseStudyView(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    story: str
    analysis: str


class TopicDetail(BaseModel):
    """主题详情：完整百科条目（含套路拆解、话术、信号、法则、案例）。"""
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    icon: str
    tagline: str
    difficulty: str
    summary: str
    tactics: list[str]
    scripts: list[str]
    signals: list[str]
    rules: list[str]
    case_study: CaseStudyView
    related_topic_ids: list[str]


class QuizCard(BaseModel):
    """下发到前端的题目视图：绝不包含答案与解析字段。"""
    model_config = ConfigDict(frozen=True)

    qid: str
    topic_id: str
    question: str
    options: list[str]


class AnswerInput(BaseModel):
    """一条提交的作答记录；choice 为 None 表示该题未作答。"""
    model_config = ConfigDict(frozen=True)

    qid: str
    choice: int | None = None


class ReviewItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    qid: str
    question: str
    options: list[str]
    your_choice: int | None
    correct_index: int
    correct: bool
    explanation: str
    topic_id: str


class GradeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    correct_count: int
    accuracy: int
    rating: str
    review: list[ReviewItem]


@dataclass(frozen=True, slots=True)
class TopicNotFoundError(Exception):
    topic_id: str

    def __str__(self) -> str:
        return f"topic {self.topic_id} not found"


@dataclass(frozen=True, slots=True)
class QuizNotFoundError(Exception):
    qid: str

    def __str__(self) -> str:
        return f"quiz {self.qid} not found"


def list_topics() -> list[TopicCard]:
    return [
        TopicCard(
            id=topic["id"], name=topic["name"], icon=topic["icon"],
            tagline=topic["tagline"], difficulty=topic["difficulty"],
            quiz_count=sum(1 for q in QUIZ_BANK if q["topic_id"] == topic["id"]),
        )
        for topic in TOPICS.values()
    ]


def get_topic(topic_id: str) -> TopicDetail:
    topic = _get_topic(topic_id)
    return TopicDetail(
        id=topic["id"], name=topic["name"], icon=topic["icon"],
        tagline=topic["tagline"], difficulty=topic["difficulty"],
        summary=topic["summary"],
        tactics=topic["tactics"], scripts=topic["scripts"],
        signals=topic["signals"], rules=topic["rules"],
        case_study=CaseStudyView(**topic["case_study"]),
        related_topic_ids=topic["related_topic_ids"],
    )


def draw_quiz(count: int = 5, topic_id: str | None = None) -> list[QuizCard]:
    """无状态随机抽题：不重复抽取，题不足时返回全部可用题。"""
    if not MIN_DRAW_COUNT <= count <= MAX_DRAW_COUNT:
        raise ValueError(f"count 必须在 {MIN_DRAW_COUNT}-{MAX_DRAW_COUNT} 之间")
    pool: list[QuizQuestion] = QUIZ_BANK
    if topic_id is not None:
        _get_topic(topic_id)
        pool = [q for q in QUIZ_BANK if q["topic_id"] == topic_id]
    drawn = random.sample(pool, min(count, len(pool)))
    return [
        QuizCard(qid=q["qid"], topic_id=q["topic_id"], question=q["question"], options=q["options"])
        for q in drawn
    ]


def grade_quiz(answers: list[AnswerInput]) -> GradeResult:
    """逐题判定并评级；未知 qid 抛 QuizNotFoundError（由路由映射 400）。"""
    bank_by_qid: Final[dict[str, QuizQuestion]] = {q["qid"]: q for q in QUIZ_BANK}
    review: list[ReviewItem] = []
    correct_count = 0
    for answer in answers:
        question = bank_by_qid.get(answer.qid)
        if question is None:
            raise QuizNotFoundError(qid=answer.qid)
        correct = answer.choice is not None and answer.choice == question["correct_index"]
        if correct:
            correct_count += 1
        review.append(ReviewItem(
            qid=question["qid"], question=question["question"], options=question["options"],
            your_choice=answer.choice, correct_index=question["correct_index"],
            correct=correct, explanation=question["explanation"], topic_id=question["topic_id"],
        ))
    total = len(review)
    accuracy = round(correct_count / total * 100) if total else 0
    return GradeResult(
        total=total, correct_count=correct_count, accuracy=accuracy,
        rating=_rating_for(accuracy), review=review,
    )


def _rating_for(accuracy: int) -> str:
    for threshold, label in RATING_THRESHOLDS:
        if accuracy >= threshold:
            return label
    return DEFAULT_RATING


def _get_topic(topic_id: str) -> FraudTopic:
    try:
        return TOPICS[topic_id]
    except KeyError:
        raise TopicNotFoundError(topic_id=topic_id) from None
