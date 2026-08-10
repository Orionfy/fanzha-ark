from dataclasses import dataclass, replace
from typing import Final, Literal, assert_never
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from .intent import Feedback, Intent, evaluate_reply, scan_signals
from .scenarios import BATTLE_SCENARIOS, BattleScenario, Signal

ResultType = Literal["win_expose", "win_alarm", "lose_scammed", "give_up"]

# 初始心态：48 保证 3 连 comply 才触发贪婪跳收网轮（48+40=88<90，48+60=100≥90），
# 同时首轮 alert(-40) 后心态 8>5 不会误触发崩溃，2 次 refuse 后 18≤25 触发破绽轮。
INITIAL_MOOD: Final[int] = 48
COLLAPSE_THRESHOLD: Final[int] = 5
TELL_THRESHOLD: Final[int] = 25
GREED_THRESHOLD: Final[int] = 90

GREED_COMMENT: Final[str] = "骗子认定你已完全上钩，直接亮出最后一张牌——收网。"
COLLAPSE_MSG: Final[str] = "你、你等着……这单我不接了！\n对方手忙脚乱地挂断，头像很快变成了灰色。"
ALARM_MSG: Final[str] = "你、你别乱来，我只是按流程通知！\n电话那头突然挂断，96110与民警已介入处置。\n骗子的恐吓在警灯亮起时彻底失效。"
EXPOSE_MSG: Final[str] = "你别乱说，什么诈骗？不做就算了！\n对方嘴硬了一句，随即撤回消息并仓皇下线。"
LOSE_MSG: Final[str] = "【收网】验证已完成，款项正在处理，请勿联系银行。\n随后对方删除好友，所谓平台余额再也无法提现。"

# 破绽轮无信号时合成的信号（按场景）。
TELL_SYNTHESIZED: Final[dict[str, Signal]] = {
    "1": {"keyword": "群主后台", "label": "破绽暴露", "severity": "high", "explain": "骗子情急之下把'冤大头'说漏嘴，暴露了刷单骗局的真实意图。"},
    "2": {"keyword": "理赔流程", "label": "破绽暴露", "severity": "high", "explain": "对方慌乱中自相矛盾，正规客服绝不会如此语无伦次。"},
    "3": {"keyword": "投资平台", "label": "破绽暴露", "severity": "high", "explain": "骗子破防时把'表哥的平台'说了出来，情感包装彻底崩塌。"},
    "4": {"keyword": "安全账户", "label": "破绽暴露", "severity": "high", "explain": "冒牌'警察'急得漏出了真实目的——就是要你转账。"},
}


class SignalView(BaseModel):
    model_config = ConfigDict(frozen=True)

    keyword: str
    label: str
    severity: Literal["high", "mid"]
    explain: str


class ScammerView(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    avatar: str
    title: str
    signature: str


class ScammerStateView(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: Literal["tempt", "authority", "emotional", "threat"]
    strategy_label: str
    mood: int


class FeedbackView(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent: Intent
    intent_label: str
    rating: Literal["S", "A", "B", "C", "D", "F"]
    rating_label: str
    defense_point: int
    hp_delta: int
    scammer_mood_delta: int
    comment: str
    scanner: list[SignalView]


class LessonView(BaseModel):
    model_config = ConfigDict(frozen=True)

    point: str
    rule: str


class ResultView(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: ResultType
    title: str
    rating: Literal["S", "A", "B", "C"]
    rating_label: str
    score: int
    summary: list[str]
    lessons: list[LessonView]
    achievement: str


class BattleState(BaseModel):
    model_config = ConfigDict(frozen=True)

    battle_id: str
    scenario_id: str
    scenario_name: str
    fraud_type: str
    cover: str
    round_no: int
    total_rounds: int
    round_phase: str
    round_title: str
    scammer: ScammerView
    scammer_msg: str
    signals: list[SignalView]
    scammer_state: ScammerStateView
    hp: int
    max_hp: int
    score: int
    feedback: FeedbackView | None
    is_over: bool
    result: ResultView | None
    image_dir: str


@dataclass(frozen=True, slots=True)
class LogEntry:
    round_no: int
    intent: str
    rating: str
    hp_delta: int
    score_delta: int
    mood_after: int
    signals_hit: list[str]


@dataclass(frozen=True, slots=True)
class BattleSession:
    battle_id: str
    scenario_id: str
    player_name: str
    round_index: int = 0
    hp: int = 100
    score: int = 0
    mood: int = INITIAL_MOOD
    feedback: Feedback | None = None
    result: ResultView | None = None
    final_message: str | None = None
    log: tuple[LogEntry, ...] = ()
    told: bool = False
    told_round_no: int | None = None
    min_hp: int = 100
    recovered: bool = False


@dataclass(frozen=True, slots=True)
class BattleNotFoundError(Exception):
    battle_id: str

    def __str__(self) -> str:
        return f"battle {self.battle_id} not found"


@dataclass(frozen=True, slots=True)
class ScenarioNotFoundError(Exception):
    scenario_id: str

    def __str__(self) -> str:
        return f"scenario {self.scenario_id} not found"


@dataclass(frozen=True, slots=True)
class BattleFinishedError(Exception):
    battle_id: str

    def __str__(self) -> str:
        return f"battle {self.battle_id} already finished"


battles: Final[dict[str, BattleSession]] = {}
STRATEGY_LABELS: Final = {
    "tempt": "甜蜜诱惑", "authority": "权威施压", "emotional": "情感操控", "threat": "恐吓逼迫",
}
TELL_STRATEGY_LABEL: Final[str] = "语无伦次·破绽显露"


def list_scenarios() -> list[BattleScenario]:
    return list(BATTLE_SCENARIOS.values())


def start_battle(scenario_id: str, player_name: str) -> BattleState:
    if scenario_id not in BATTLE_SCENARIOS:
        raise ScenarioNotFoundError(scenario_id=scenario_id)
    session = BattleSession(battle_id=str(uuid4()), scenario_id=scenario_id, player_name=player_name)
    battles[session.battle_id] = session
    return _build_state(session)


def reply_to_battle(battle_id: str, text: str) -> BattleState:
    session = _get_session(battle_id)
    if session.result is not None:
        raise BattleFinishedError(battle_id=battle_id)
    scenario = BATTLE_SCENARIOS[session.scenario_id]
    battle_round = scenario["rounds"][session.round_index]
    feedback = evaluate_reply(
        text, scenario, battle_round,
        tell=session.told,
        greed=session.round_index == scenario["finale_round"],
    )
    hp = min(100, max(0, session.hp + feedback["hp_delta"]))
    mood = min(100, max(0, session.mood + feedback["scammer_mood_delta"]))
    score = session.score + feedback["defense_point"]
    log_entry = LogEntry(
        round_no=battle_round["no"],
        intent=feedback["intent"],
        rating=feedback["rating"],
        hp_delta=feedback["hp_delta"],
        score_delta=feedback["defense_point"],
        mood_after=mood,
        signals_hit=[signal["keyword"] for signal in feedback["scanner"]],
    )
    updated = replace(
        session,
        hp=hp, mood=mood, score=score, min_hp=min(session.min_hp, hp),
        feedback=feedback, log=(*session.log, log_entry), told=False,
    )

    intent = feedback["intent"]
    if mood <= COLLAPSE_THRESHOLD:
        result = _result_for("win_expose", scenario, updated, collapse=True)
        updated = replace(updated, result=result, final_message=COLLAPSE_MSG)
    else:
        match intent:
            case "alert":
                result = _result_for("win_alarm", scenario, updated)
                updated = replace(updated, result=result, final_message=ALARM_MSG)
            case "expose":
                result = _result_for("win_expose", scenario, updated)
                updated = replace(updated, result=result, final_message=EXPOSE_MSG)
            case "refuse" | "suspect" | "stall" | "comply" | "chat":
                if hp <= 0:
                    result = _result_for("lose_scammed", scenario, updated)
                    updated = replace(updated, result=result, final_message=LOSE_MSG)
                elif session.round_index >= len(scenario["rounds"]) - 1:
                    result = _result_for("win_expose", scenario, updated)
                    updated = replace(updated, result=result)
                else:
                    new_round = session.round_index + 1
                    jump = False
                    if mood >= GREED_THRESHOLD and session.round_index < scenario["finale_round"]:
                        new_round = scenario["finale_round"]
                        jump = True
                    told = False
                    told_round_no = session.told_round_no
                    if mood <= TELL_THRESHOLD and session.told_round_no is None:
                        told = True
                        told_round_no = scenario["rounds"][new_round]["no"]
                    if jump:
                        feedback = {**feedback, "comment": GREED_COMMENT}
                    updated = replace(
                        updated, round_index=new_round, told=told,
                        told_round_no=told_round_no, feedback=feedback,
                    )

    battles[battle_id] = updated
    return _build_state(updated)


def abort_battle(battle_id: str) -> BattleState:
    session = _get_session(battle_id)
    scenario = BATTLE_SCENARIOS[session.scenario_id]
    result = _result_for("give_up", scenario, session)
    state = _build_state(replace(session, result=result))
    del battles[battle_id]
    return state


def delete_battle(battle_id: str) -> None:
    _get_session(battle_id)
    del battles[battle_id]


def _get_session(battle_id: str) -> BattleSession:
    try:
        return battles[battle_id]
    except KeyError:
        raise BattleNotFoundError(battle_id=battle_id) from None


def _tell_state(scenario: BattleScenario, session: BattleSession) -> tuple[str, list[Signal], str, str]:
    battle_round = scenario["rounds"][session.round_index]
    tell_pool = scenario["tell_pool"]
    message = "\n".join(tell_pool[session.round_index % len(tell_pool)])
    if battle_round["signals"]:
        signals = [{**signal, "severity": "high"} for signal in battle_round["signals"]]
    else:
        signals = [dict(TELL_SYNTHESIZED[scenario["id"]])]
    return message, signals, "threat", TELL_STRATEGY_LABEL


def _reaction_lines(scenario: BattleScenario, session: BattleSession) -> str | None:
    """根据玩家上一轮意图与骗子当前心态，生成开场即时回应（无匹配时返回 None）。"""
    feedback = session.feedback
    if feedback is None:
        return None
    pool = scenario["rounds"][session.round_index].get("reactions", {}).get(feedback["intent"])
    if not pool:
        return None
    return pool[0] if session.mood >= 50 else pool[-1]


def _build_state(session: BattleSession) -> BattleState:
    scenario = BATTLE_SCENARIOS[session.scenario_id]
    if session.final_message:
        message = session.final_message
        signals: list[Signal] = []
        strategy: Literal["tempt", "authority", "emotional", "threat"] = "threat"
        strategy_label = STRATEGY_LABELS["threat"]
    elif session.told:
        message, signals, strategy, strategy_label = _tell_state(scenario, session)
    else:
        battle_round = scenario["rounds"][session.round_index]
        script = "\n".join(battle_round["lines"])
        reaction = _reaction_lines(scenario, session)
        message = f"{reaction}\n{script}" if reaction else script
        signals = scan_signals(script, scenario)
        strategy = battle_round["strategy"]
        strategy_label = STRATEGY_LABELS[strategy]
    round_no = scenario["rounds"][session.round_index]["no"]
    phase, title = scenario["round_meta"].get(round_no, ("", ""))
    return BattleState(
        battle_id=session.battle_id, scenario_id=session.scenario_id, scenario_name=scenario["name"],
        fraud_type=scenario["fraud_type"], cover=scenario["cover"], round_no=round_no,
        total_rounds=len(scenario["rounds"]), round_phase=phase, round_title=title,
        scammer=ScammerView.model_validate(scenario["scammer"]),
        scammer_msg=message, signals=[SignalView.model_validate(signal) for signal in signals],
        scammer_state=ScammerStateView(strategy=strategy, strategy_label=strategy_label, mood=session.mood),
        hp=session.hp, max_hp=100, score=session.score,
        feedback=FeedbackView.model_validate(session.feedback) if session.feedback else None,
        is_over=session.result is not None, result=session.result, image_dir="",
    )


def _signal_explain(scenario: BattleScenario, round_no: int, keyword: str) -> str:
    for signal in scenario["rounds"][round_no - 1]["signals"]:
        if signal["keyword"] == keyword:
            return signal["explain"]
    return ""


def _dynamic_lessons(scenario: BattleScenario, session: BattleSession) -> list[LessonView]:
    lessons: list[LessonView] = []
    for entry in session.log:
        if entry.signals_hit and entry.intent in ("comply", "chat", "stall"):
            keyword = entry.signals_hit[0]
            rule = _signal_explain(scenario, entry.round_no, keyword)
            if not rule:
                continue
            lessons.append(LessonView(point=f"第{entry.round_no}轮'{keyword}'信号", rule=rule))
            if len(lessons) >= 3:
                break
    if not lessons:
        lessons = [
            LessonView(point=f"遇到{scenario['fraud_type']}", rule=scenario["tips"][0]),
            LessonView(point="对方要求转账或提供敏感信息", rule=scenario["tips"][1]),
        ]
    for tip in scenario["tips"]:
        if len(lessons) >= 5:
            break
        if not any(lesson.rule == tip for lesson in lessons):
            lessons.append(LessonView(point="反诈提醒", rule=tip))
    return lessons[:5]


def _dynamic_summary(
    result_type: ResultType, scenario: BattleScenario, session: BattleSession, collapse: bool = False,
) -> list[str]:
    sentences: list[str] = []
    comply_rounds = [entry for entry in session.log if entry.intent == "comply"]
    if not comply_rounds:
        sentences.append("全程零顺从，骗子始终找不到收割机会。")
    else:
        for entry in comply_rounds[:2]:
            keyword = entry.signals_hit[0] if entry.signals_hit else "话术"
            sentences.append(
                f"第{entry.round_no}轮你顺从了'{keyword}'话术，损失{abs(entry.hp_delta)}点防御力，这正是骗子得寸进尺的关键。"
            )
        if len(comply_rounds) > 2:
            sentences.append(f"你先后{len(comply_rounds)}次顺从，骗子步步加码，损失像滚雪球一样扩大。")
    if session.told_round_no is not None:
        sentences.append(f"第{session.told_round_no}轮骗子心态崩溃、破绽百出，你抓住机会完成反杀。")
    if result_type == "win_alarm":
        sentences.append("及时报警让骗局止步，也切断了骗子继续作案的可能。")
    elif result_type == "win_expose":
        if collapse:
            sentences.append("骗子心理防线彻底崩塌、仓皇逃窜，你的防守直接击穿了整套话术。")
        else:
            sentences.append("你识破了整盘骗局，骗子的一切话术在你面前失效。")
    elif result_type == "lose_scammed":
        sentences.append("骗子完成收割后立刻消失，所谓收益永远无法提现。")
    else:
        sentences.append("你及时抽身，没有让损失继续扩大。")
    if len(sentences) < 3:
        sentences.append("现实中遇到同类话术，应第一时间挂断并通过官方渠道核实。")
        sentences.append("遭遇诈骗请保留证据，拨打110或96110求助。")
    return sentences[:5]


def _dynamic_achievement(result_type: ResultType, session: BattleSession) -> str:
    comply_count = sum(1 for entry in session.log if entry.intent == "comply")
    if result_type == "lose_scammed":
        return "深刻一课"
    if result_type in ("win_expose", "win_alarm"):
        if comply_count == 0:
            return "防线无损"
        if session.log and session.log[-1].round_no <= 3:
            return "快准狠"
        if comply_count >= 2:
            return "亡羊补牢"
        if session.min_hp < 40 and session.hp > 70:
            return "绝地反击"
        if result_type == "win_alarm":
            return "正义执行"
    return ""


def _result_for(
    result_type: ResultType, scenario: BattleScenario, session: BattleSession, *, collapse: bool = False,
) -> ResultView:
    score = session.score
    hp = session.hp
    lessons = _dynamic_lessons(scenario, session)
    achievement = _dynamic_achievement(result_type, session)
    summary = _dynamic_summary(result_type, scenario, session, collapse=collapse)
    match result_type:
        case "win_alarm":
            title, rating, label = "警灯亮起·联动反诈", "S", "反诈卫士"
        case "win_expose":
            if score >= 180 or hp >= 70:
                rating, label = "S", "反诈卫士"
            elif score >= 100 or hp >= 50:
                rating, label = "A", "识诈达人"
            elif score >= 60 or hp >= 30:
                rating, label = "B", "谨慎行者"
            else:
                rating, label = "C", "反诈学员"
            if collapse:
                title = "心理崩溃·骗子现形"
            elif rating == "S":
                title = "铜墙铁壁·完美防御"
            elif rating == "A":
                title = "火眼金睛·识局脱身"
            elif rating == "B":
                title = "步步为营·守住底线"
            else:
                title = "惊险过关·险胜脱身"
        case "lose_scammed":
            title, rating, label = "防线失守·骗局收网", "C", "待加强"
        case "give_up":
            title, rating, label = "主动撤离·及时止损", "C", "止损意识"
        case unreachable:
            assert_never(unreachable)
    if not achievement:
        achievement = {
            "win_alarm": "反诈先锋",
            "win_expose": "反诈先锋" if rating == "S" else "清醒守门员" if rating == "A" else "止损能手" if rating == "B" else "绝处逢生",
            "lose_scammed": "深刻一课",
            "give_up": "安全撤退",
        }[result_type]
    return ResultView(
        type=result_type, title=title, rating=rating, rating_label=label, score=score,
        summary=summary, lessons=lessons, achievement=achievement,
    )