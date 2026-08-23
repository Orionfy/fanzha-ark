"""反诈海龟汤 · 问答引擎。

会话状态 + 关键词问答匹配 + 侦探评级。纯规则引擎，无外部依赖：
- ask：玩家自由打字提问，按线索关键词匹配回答「是 / 否 / 无关 / 已问过」
- hint：按进度发放方向性提示（计惩罚）
- reveal：揭晓汤底 + 线索复盘 + 侦探评级
"""

import re
from dataclasses import dataclass, field, replace
from typing import Final, Literal
from uuid import uuid4
import time

from pydantic import BaseModel, ConfigDict

from .puzzles import PUZZLES, Puzzle

AnswerType = Literal["yes", "no", "irrelevant", "repeat"]

# 无关问题兜底回答池（轮换使用，避免复读）
IRRELEVANT_REPLIES: Final[tuple[str, ...]] = (
    "这个问题恐怕与案情无关。想想骗局的突破口会在哪里？",
    "嗯……这个方向暂时查不到线索，换个角度再问问看。",
    "主持人翻了下案卷：没有这方面的记录。聚焦可疑的细节吧。",
    "与本案无关哦。提示一下：多问问「对方做了什么」。",
    "查不到相关的线索。想一想：受害者哪个环节交出了什么？",
    "这条线索不在案卷里。试着从钱和信息两个方向入手。",
)

RATING_LABELS: Final[dict[str, str]] = {
    "S": "名侦探", "A": "资深警探", "B": "反诈民警", "C": "见习警员", "D": "热心市民",
}


class ClueView(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    answer: str
    answer_text: str


class PuzzleSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    description: str
    icon: str
    theme: str
    tags: list[str]
    difficulty: str
    cover: str
    fraud_type: str
    total_clues: int
    tips: list[str]


class AskResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: AnswerType
    reply: str
    clue: ClueView | None = None
    revealed_count: int
    total_clues: int
    ask_count: int


class HintResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    hint: str
    hints_used: int


class LessonView(BaseModel):
    model_config = ConfigDict(frozen=True)

    point: str
    rule: str


class ClueRecap(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    answer_text: str


class RevealResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    soup_bottom: list[str]
    rating: str
    rating_label: str
    score: int
    revealed_count: int
    total_clues: int
    ask_count: int
    hints_used: int
    missed_clues: list[ClueRecap]
    lessons: list[LessonView]


class SoupState(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    puzzle_id: str
    puzzle_name: str
    fraud_type: str
    cover: str
    soup_surface: list[str]
    revealed_count: int
    total_clues: int
    ask_count: int
    hints_used: int
    is_over: bool
    result: RevealResult | None = None


@dataclass(frozen=True, slots=True)
class SoupSession:
    session_id: str
    puzzle_id: str
    revealed_clues: tuple[str, ...] = ()
    ask_count: int = 0
    hints_used: int = 0
    irrelevant_cursor: int = 0
    is_over: bool = False
    result: RevealResult | None = None
    last_active: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class SoupNotFoundError(Exception):
    session_id: str

    def __str__(self) -> str:
        return f"soup session {self.session_id} not found"


@dataclass(frozen=True, slots=True)
class PuzzleNotFoundError(Exception):
    puzzle_id: str

    def __str__(self) -> str:
        return f"puzzle {self.puzzle_id} not found"


@dataclass(frozen=True, slots=True)
class SoupFinishedError(Exception):
    session_id: str

    def __str__(self) -> str:
        return f"soup session {self.session_id} already finished"


sessions: Final[dict[str, SoupSession]] = {}

# 线索关键词正则缓存：puzzle_id → [(clue_id, 合并正则)]，只编译一次
_PATTERN_CACHE: Final[dict[str, list[tuple[str, re.Pattern]]]] = {}


def _compiled_patterns(puzzle_id: str) -> list[tuple[str, re.Pattern]]:
    cached = _PATTERN_CACHE.get(puzzle_id)
    if cached is not None:
        return cached
    puzzle = PUZZLES[puzzle_id]
    compiled = [
        (clue["id"], re.compile("|".join(re.escape(k) for k in clue["keywords"])))
        for clue in puzzle["clues"]
    ]
    _PATTERN_CACHE[puzzle_id] = compiled
    return compiled


def list_puzzles() -> list[PuzzleSummary]:
    return [
        PuzzleSummary(
            id=p["id"], name=p["name"], description=p["description"],
            icon=p["icon"], theme=p["theme"], tags=p["tags"],
            difficulty=p["difficulty"], cover=p["cover"], fraud_type=p["fraud_type"],
            total_clues=len(p["clues"]), tips=p["tips"],
        )
        for p in PUZZLES.values()
    ]


def start_session(puzzle_id: str) -> SoupState:
    if puzzle_id not in PUZZLES:
        raise PuzzleNotFoundError(puzzle_id=puzzle_id)
    session = SoupSession(session_id=str(uuid4()), puzzle_id=puzzle_id)
    sessions[session.session_id] = session
    return _build_state(session)


def ask_question(session_id: str, text: str) -> AskResult:
    session = _get_session(session_id)
    if session.is_over:
        raise SoupFinishedError(session_id=session_id)
    puzzle = PUZZLES[session.puzzle_id]
    text = text.strip()
    patterns = _compiled_patterns(session.puzzle_id)
    clue_by_id = {c["id"]: c for c in puzzle["clues"]}

    # 1) 先匹配未揭示线索（新线索命中）
    for clue_id, pattern in patterns:
        if clue_id in session.revealed_clues:
            continue
        if pattern.search(text):
            clue = clue_by_id[clue_id]
            updated = replace(
                session,
                revealed_clues=(*session.revealed_clues, clue_id),
                ask_count=session.ask_count + 1,
                last_active=time.time(),
            )
            sessions[session_id] = updated
            return AskResult(
                answer=clue["answer"],
                reply=clue["answer_text"],
                clue=ClueView(id=clue["id"], answer=clue["answer"], answer_text=clue["answer_text"]),
                revealed_count=len(updated.revealed_clues),
                total_clues=len(puzzle["clues"]),
                ask_count=updated.ask_count,
            )

    # 2) 已揭示线索重复提问
    for clue_id, pattern in patterns:
        if clue_id in session.revealed_clues and pattern.search(text):
            clue = clue_by_id[clue_id]
            updated = replace(session, ask_count=session.ask_count + 1, last_active=time.time())
            sessions[session_id] = updated
            prefix = "是的" if clue["answer"] == "yes" else "不是"
            return AskResult(
                answer="repeat",
                reply=f"这个问题你已经问过啦——{prefix}。这条线索已在你的案卷里，去挖新的方向吧。",
                revealed_count=len(session.revealed_clues),
                total_clues=len(puzzle["clues"]),
                ask_count=updated.ask_count,
            )

    # 3) 无关问题：轮换兜底回答
    cursor = session.irrelevant_cursor % len(IRRELEVANT_REPLIES)
    updated = replace(
        session,
        ask_count=session.ask_count + 1,
        irrelevant_cursor=session.irrelevant_cursor + 1,
        last_active=time.time(),
    )
    sessions[session_id] = updated
    return AskResult(
        answer="irrelevant",
        reply=IRRELEVANT_REPLIES[cursor],
        revealed_count=len(session.revealed_clues),
        total_clues=len(puzzle["clues"]),
        ask_count=updated.ask_count,
    )


def get_hint(session_id: str) -> HintResult:
    session = _get_session(session_id)
    if session.is_over:
        raise SoupFinishedError(session_id=session_id)
    puzzle = PUZZLES[session.puzzle_id]
    hints = puzzle["hints"]
    # 提示按已用次数发放；用尽后提示当前进度百分比
    if session.hints_used < len(hints):
        hint = hints[session.hints_used]
    else:
        revealed = len(session.revealed_clues)
        total = len(puzzle["clues"])
        hint = f"所有提示都已发完。目前你已揭示 {revealed}/{total} 条线索，试试从「钱」「信息」「验证」三个方向提问。"
    updated = replace(session, hints_used=session.hints_used + 1, last_active=time.time())
    sessions[session_id] = updated
    return HintResult(hint=hint, hints_used=updated.hints_used)


def reveal_answer(session_id: str) -> SoupState:
    session = _get_session(session_id)
    if session.is_over:
        raise SoupFinishedError(session_id=session_id)
    puzzle = PUZZLES[session.puzzle_id]
    total = len(puzzle["clues"])
    revealed = len(session.revealed_clues)
    ask_count = session.ask_count
    hints_used = session.hints_used

    # 侦探评级：线索揭示率（主） + 提问效率 - 提示惩罚
    ratio = revealed / total if total else 0.0
    efficiency = (revealed / ask_count) if ask_count else 0.0
    score_raw = ratio * 0.7 + min(efficiency, 1.0) * 0.3 - hints_used * 0.05
    score = round(max(0.0, score_raw) * 100)
    if score >= 85:
        rating = "S"
    elif score >= 70:
        rating = "A"
    elif score >= 50:
        rating = "B"
    elif score >= 30:
        rating = "C"
    else:
        rating = "D"

    missed = [
        ClueRecap(answer=c["answer"], answer_text=c["answer_text"])
        for c in puzzle["clues"] if c["id"] not in session.revealed_clues
    ]
    result = RevealResult(
        soup_bottom=puzzle["soup_bottom"],
        rating=rating,
        rating_label=RATING_LABELS[rating],
        score=score,
        revealed_count=revealed,
        total_clues=total,
        ask_count=ask_count,
        hints_used=hints_used,
        missed_clues=missed,
        lessons=[LessonView(point=l["point"], rule=l["rule"]) for l in puzzle["lessons"]],
    )
    updated = replace(session, is_over=True, result=result, last_active=time.time())
    sessions[session_id] = updated
    return _build_state(updated)


def delete_session(session_id: str) -> None:
    _get_session(session_id)
    del sessions[session_id]


def cleanup_expired_soup_sessions(now: float, ttl_seconds: int) -> int:
    """回收超过 ttl 不活跃的解谜会话，返回清理数量（由 api.py 后台任务周期调用）。"""
    expired = [
        sid for sid, s in sessions.items()
        if now - s.last_active > ttl_seconds
    ]
    for sid in expired:
        del sessions[sid]
    return len(expired)


def _get_session(session_id: str) -> SoupSession:
    try:
        return sessions[session_id]
    except KeyError:
        raise SoupNotFoundError(session_id=session_id) from None


def _build_state(session: SoupSession) -> SoupState:
    puzzle = PUZZLES[session.puzzle_id]
    return SoupState(
        session_id=session.session_id,
        puzzle_id=puzzle["id"],
        puzzle_name=puzzle["name"],
        fraud_type=puzzle["fraud_type"],
        cover=puzzle["cover"],
        soup_surface=puzzle["soup_surface"],
        revealed_count=len(session.revealed_clues),
        total_clues=len(puzzle["clues"]),
        ask_count=session.ask_count,
        hints_used=session.hints_used,
        is_over=session.is_over,
        result=session.result,
    )
