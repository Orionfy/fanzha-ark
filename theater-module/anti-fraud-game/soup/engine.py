"""反诈海龟汤 · 问答引擎。

会话状态 + 关键词问答匹配 + 侦探评级。纯规则引擎，无外部依赖：
- ask：玩家自由打字提问，按线索关键词匹配回答「是 / 否 / 无关 / 已问过」
- hint：按进度发放方向性提示（计惩罚）
- reveal：揭晓汤底 + 线索复盘 + 侦探评级
"""

import difflib
import re
import string
import unicodedata
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
    hints_used: int = 0


class HintResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    hint: str
    hints_used: int
    remaining: int = 0
    exhausted: bool = False


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
    asked_texts: tuple[str, ...] = ()
    processing: bool = False
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


@dataclass(frozen=True, slots=True)
class SoupBusyError(Exception):
    session_id: str

    def __str__(self) -> str:
        return f"soup session {self.session_id} is busy"

# 否定词表：用于「是不是没有X」类提问的语义反转（长词在前，避免子串截断）
_NEGATION_PATTERN: Final[re.Pattern] = re.compile(r"没有|不是|未曾|并未|没|未")
# 疑问句脚手架：先剥离再扫否定，防止「他是不是转账了」被「不是」误翻转
_QUESTION_SCAFFOLD: Final[re.Pattern] = re.compile(r"是不是|是否|有没有|难道")
_REPEAT_SIMILARITY_THRESHOLD: Final[float] = 0.75


sessions: Final[dict[str, SoupSession]] = {}

# 线索关键词编译缓存：puzzle_id → [(clue_id, ((keyword, 正则), ...))]，只编译一次
_PATTERN_CACHE: Final[dict[str, list[tuple[str, tuple[tuple[str, re.Pattern], ...]]]]] = {}


def _compiled_patterns(puzzle_id: str) -> list[tuple[str, tuple[tuple[str, re.Pattern], ...]]]:
    cached = _PATTERN_CACHE.get(puzzle_id)
    if cached is not None:
        return cached
    puzzle = PUZZLES[puzzle_id]
    compiled = [
        (
            clue["id"],
            tuple(
                (keyword, re.compile(re.escape(keyword)))
                for keyword in sorted(clue["keywords"], key=len, reverse=True)
            ),
        )
        for clue in puzzle["clues"]
    ]
    _PATTERN_CACHE[puzzle_id] = compiled
    return compiled


def _normalize_question(text: str) -> str:
    """归一化问题文本：全角转半角、去空白与标点，供重复提问相似度比对。"""
    normalized = unicodedata.normalize("NFKC", text).lower()
    return "".join(
        ch for ch in normalized
        if not unicodedata.category(ch).startswith(("P", "Z", "S")) and ch not in string.punctuation
    )


def _is_repeat(text: str, asked_texts: tuple[str, ...]) -> bool:
    if not asked_texts:
        return False
    normalized = _normalize_question(text)
    if not normalized:
        return False
    matcher = difflib.SequenceMatcher(autojunk=False)
    matcher.set_seq2(normalized)
    for previous in asked_texts:
        matcher.set_seq1(previous)
        if matcher.quick_ratio() > _REPEAT_SIMILARITY_THRESHOLD and matcher.ratio() > _REPEAT_SIMILARITY_THRESHOLD:
            return True
    return False


def _best_unrevealed_hit(
    text: str,
    patterns: list[tuple[str, tuple[tuple[str, re.Pattern], ...]]],
    revealed_clues: tuple[str, ...],
) -> tuple[str | None, int]:
    """按命中关键词总长度评分取最优未揭示线索，避免泛化词抢先误判。"""
    best_id: str | None = None
    best_score = 0
    for clue_id, keyword_patterns in patterns:
        if clue_id in revealed_clues:
            continue
        score = sum(len(keyword) for keyword, pattern in keyword_patterns if pattern.search(text))
        if score > best_score:
            best_id, best_score = clue_id, score
    return best_id, best_score


def _hit_keyword_start(text: str, keywords: tuple[tuple[str, re.Pattern], ...]) -> int | None:
    for keyword, pattern in keywords:
        match = pattern.search(text)
        if match:
            return match.start()
    return None


def _is_negated(text: str, keyword_start: int) -> bool:
    window = _QUESTION_SCAFFOLD.sub("", text[max(0, keyword_start - 12):keyword_start])
    return bool(_NEGATION_PATTERN.search(window))


def _acquire_session(session_id: str) -> SoupSession:
    session = _get_session(session_id)
    if session.processing:
        raise SoupBusyError(session_id=session_id)
    sessions[session_id] = replace(session, processing=True)
    return session


def _release_session(session_id: str) -> None:
    session = sessions.get(session_id)
    if session is not None:
        sessions[session_id] = replace(session, processing=False)


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
    _acquire_session(session_id)
    try:
        session = _get_session(session_id)
        if session.is_over:
            raise SoupFinishedError(session_id=session_id)
        puzzle = PUZZLES[session.puzzle_id]
        text = text.strip()
        patterns = _compiled_patterns(session.puzzle_id)
        clue_by_id = {c["id"]: c for c in puzzle["clues"]}

        def _record(updated: SoupSession) -> SoupSession:
            with_text = replace(
                updated,
                asked_texts=(*updated.asked_texts, _normalize_question(text)),
            )
            sessions[session_id] = with_text
            return with_text

        # 1) 未揭示线索按命中总长度评分取最优（泛化词不再抢先误判）
        best_id, best_score = _best_unrevealed_hit(text, patterns, session.revealed_clues)
        if best_id is not None and best_score > 0:
            clue = clue_by_id[best_id]
            keywords = dict(patterns)[best_id]
            keyword_start = _hit_keyword_start(text, keywords)
            answer: AnswerType = clue["answer"]
            if keyword_start is not None and _is_negated(text, keyword_start):
                answer = "no" if answer == "yes" else "yes"
            updated = _record(replace(
                session,
                revealed_clues=(*session.revealed_clues, best_id),
                ask_count=session.ask_count + 1,
                last_active=time.time(),
            ))
            return AskResult(
                answer=answer,
                reply=clue["answer_text"],
                clue=ClueView(id=clue["id"], answer=clue["answer"], answer_text=clue["answer_text"]),
                revealed_count=len(updated.revealed_clues),
                total_clues=len(puzzle["clues"]),
                ask_count=updated.ask_count,
                hints_used=session.hints_used,
            )

        # 2) 与历史提问高度相似 → 已问过
        if _is_repeat(text, session.asked_texts):
            updated = _record(replace(
                session,
                ask_count=session.ask_count + 1,
                last_active=time.time(),
            ))
            return AskResult(
                answer="repeat",
                reply="这个问题你已经问过啦——换一种问法也是一样的答案，去挖新的方向吧。",
                revealed_count=len(session.revealed_clues),
                total_clues=len(puzzle["clues"]),
                ask_count=updated.ask_count,
                hints_used=session.hints_used,
            )

        # 3) 命中已揭示线索的关键词 → 提示已在案卷中
        for clue_id, keyword_patterns in patterns:
            if clue_id in session.revealed_clues and any(p.search(text) for _, p in keyword_patterns):
                clue = clue_by_id[clue_id]
                updated = _record(replace(
                    session,
                    ask_count=session.ask_count + 1,
                    last_active=time.time(),
                ))
                prefix = "是的" if clue["answer"] == "yes" else "不是"
                return AskResult(
                    answer="repeat",
                    reply=f"这个问题你已经问过啦——{prefix}。这条线索已在你的案卷里，去挖新的方向吧。",
                    revealed_count=len(session.revealed_clues),
                    total_clues=len(puzzle["clues"]),
                    ask_count=updated.ask_count,
                    hints_used=session.hints_used,
                )

        # 4) 无关问题：轮换兜底回答
        cursor = session.irrelevant_cursor % len(IRRELEVANT_REPLIES)
        updated = _record(replace(
            session,
            ask_count=session.ask_count + 1,
            irrelevant_cursor=session.irrelevant_cursor + 1,
            last_active=time.time(),
        ))
        return AskResult(
            answer="irrelevant",
            reply=IRRELEVANT_REPLIES[cursor],
            revealed_count=len(session.revealed_clues),
            total_clues=len(puzzle["clues"]),
            ask_count=updated.ask_count,
            hints_used=session.hints_used,
        )
    finally:
        _release_session(session_id)


def get_hint(session_id: str) -> HintResult:
    _acquire_session(session_id)
    try:
        session = _get_session(session_id)
        if session.is_over:
            raise SoupFinishedError(session_id=session_id)
        puzzle = PUZZLES[session.puzzle_id]
        hints = puzzle["hints"]
        # 提示按已用次数发放；用尽后仅播报进度，不再计数、不再扣评级
        if session.hints_used < len(hints):
            updated = replace(session, hints_used=session.hints_used + 1, last_active=time.time())
            sessions[session_id] = updated
            return HintResult(
                hint=hints[session.hints_used],
                hints_used=updated.hints_used,
                remaining=len(hints) - updated.hints_used,
            )
        revealed = len(session.revealed_clues)
        total = len(puzzle["clues"])
        hint = f"所有提示都已发完。目前你已揭示 {revealed}/{total} 条线索，试试从「钱」「信息」「验证」三个方向提问。"
        updated = replace(session, last_active=time.time())
        sessions[session_id] = updated
        return HintResult(
            hint=hint,
            hints_used=updated.hints_used,
            remaining=0,
            exhausted=True,
        )
    finally:
        _release_session(session_id)


def reveal_answer(session_id: str) -> SoupState:
    _acquire_session(session_id)
    try:
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
    finally:
        _release_session(session_id)


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
