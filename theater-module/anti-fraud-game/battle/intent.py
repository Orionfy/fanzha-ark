import re
from typing import Final, Literal, TypedDict, assert_never

from .scenarios import BattleScenario, Round, Signal

Intent = Literal["alert", "expose", "refuse", "suspect", "stall", "comply", "chat"]
Rating = Literal["S", "A", "B", "C", "D", "F"]


class Feedback(TypedDict):
    intent: Intent
    intent_label: str
    rating: Rating
    rating_label: str
    defense_point: int
    hp_delta: int
    scammer_mood_delta: int
    comment: str
    scanner: list[Signal]


INTENT_PATTERNS: Final[tuple[tuple[Intent, tuple[str, ...]], ...]] = (
    ("alert", (r"报警", r"110", r"派出所", r"警察", r"96110", r"举报", r"报警了", r"报网警", r"反诈中心", r"报案", r"网警")),
    ("expose", (r"骗子", r"诈骗", r"套路", r"剧本", r"杀猪盘", r"刷单都是骗", r"骗人", r"你骗", r"别骗", r"骗我", r"假的吧", r"骗局", r"哄人", r"想骗", r"忽悠", r"割韭菜", r"上钩", r"真会编", r"接着编", r"继续编", r"戏真多", r"演的", r"装的", r"装得", r"编得", r"演得", r"套路深", r"影帝", r"呵呵", r"笑死", r"是托", r"个托", r"当托", r"演技", r"老套", r"骗鬼", r"才怪")),
    ("refuse", (r"不要", r"不需要", r"不用", r"再见", r"拉黑", r"没兴趣", r"别烦", r"滚", r"不聊", r"算了", r"不了", r"退出", r"删除", r"卸载", r"烦不烦", r"免了", r"拜拜", r"不奉陪", r"别浪费", r"没门", r"想都别想", r"不借", r"免谈", r"打住", r"拒绝", r"不行")),
    ("suspect", (r"真的假", r"怎么证明", r"凭什么", r"为什么", r"可靠", r"正规", r"验证", r"官网", r"核实", r"公司", r"执照", r"实名", r"安全", r"放心", r"靠谱", r"信任", r"查一下", r"太假", r"不合理", r"漏洞", r"平台", r"资质", r"官方", r"工号", r"身份", r"求证", r"查证", r"核对", r"截图", r"凭证", r"渠道", r"退款", r"咨询", r"求助", r"朋友", r"家人", r"回拨", r"不信", r"离谱", r"怀疑", r"不对劲", r"证据", r"证明", r"合同", r"发票", r"当面", r"视频确认")),
    ("stall", (r"等等", r"再想", r"考虑", r"明天", r"晚点", r"以后", r"再说", r"问问", r"商量", r"忙", r"先放一放", r"回头", r"改天", r"过两天", r"缓缓", r"放放", r"先不急", r"容我想想", r"稍后", r"缓一缓")),
    ("comply", (r"转账", r"汇款", r"打钱", r"付款", r"扫码", r"下载", r"注册", r"垫付", r"操作", r"任务", r"链接", r"填写", r"验证码", r"卡号", r"密码", r"收款", r"打款", r"转给", r"发我", r"输入", r"马上转", r"这就转", r"这就付")),
)

INTENT_LABELS: Final[dict[Intent, str]] = {
    "alert": "立即报警", "expose": "识破骗局", "refuse": "果断拒绝", "suspect": "冷静质疑",
    "stall": "拖延周旋", "comply": "顺从话术", "chat": "普通回应",
}
RATING_LABELS: Final[dict[Rating, str]] = {
    "S": "铜墙铁壁", "A": "火眼金睛", "B": "步步为营", "C": "惊险过关", "D": "反应平平", "F": "防线失守",
}

# 否定词：出现在匹配关键词前 3 个字符内即视为否定该意图。
NEGATION_WORDS: Final[tuple[str, ...]] = (
    "不会", "不想", "不能", "别想", "休想", "绝不", "才不", "从来不", "别给", "不要", "不", "别", "没", "无",
)

# 否定只作用于两类关键词：
#   1) comply 动作动词（转账/付款/扫码/…）——否定后翻转为 refuse
#   2) 身份名词 警察/骗子（alert/expose 的自我否认）——否定后翻转为 refuse
# 指控型关键词（骗我/你骗/骗人/别骗/骗局…）绝不参与否定，避免"别骗我了"被误翻。
NEGATABLE_COMPLY: Final[tuple[str, ...]] = (
    "转账", "汇款", "打钱", "付款", "扫码", "下载", "注册", "垫付", "操作", "任务", "链接", "填写",
    "验证码", "卡号", "密码", "收款", "打款", "转给", "发我", "输入",
)
NEGATABLE_IDENTITY: Final[tuple[str, ...]] = ("警察", "骗子")

# 敏感信息泄露检测（leak 是 comply 的修饰，不进入公开 7 意图枚举）。
LEAK_PATTERNS: Final[tuple[tuple[str, str], ...]] = (
    ("卡号/账号", r"(?:卡号|银行卡|账号|账户)[:：是]?\d{6,}"),
    ("验证码", r"(?:验证码|短信码)[:：是]?\d{4,}"),
    ("密码", r"密码[:：是]?\d{4,}"),
    ("身份证", r"身份证[:：是]?\d{17}[\dXx]"),
    ("地址", r"(?:街道|小区|门牌|地址)[:：]?(?:[^\d，。\s]{1,8}\d[^\s，。]{2,})"),
    ("微信号/QQ号", r"(?:微信号|微信|QQ号|QQ)[:：是]?\d{8,10}"),
)
_LEAK_COMPILED: Final[tuple[tuple[str, re.Pattern], ...]] = tuple(
    (label, re.compile(pattern)) for label, pattern in LEAK_PATTERNS
)

LEAK_SIGNAL: Final[Signal] = {
    "keyword": "敏感信息泄露",
    "label": "信息泄露",
    "severity": "high",
    "explain": "验证码、卡号、密码是资金安全最后防线，任何情况下都不要发给陌生人。",
}
LEAK_COMMENT: Final[str] = "你亲手交出了敏感信息！立即联系银行挂失止付，并报警处理"


def _first_match(text: str) -> tuple[Intent, str, int] | None:
    """返回最高优先级意图的首次匹配 (intent, keyword, start)。"""
    for intent, patterns in INTENT_PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return intent, pattern, match.start()
    return None


def _negated(text: str, keyword_start: int) -> bool:
    """否定词结束位置距关键词起点 ≤2 个字符即视为否定（覆盖"别给我发验证码"这类隔字否定）。"""
    return _negation_end(text, keyword_start) is not None


def _negation_end(text: str, keyword_start: int) -> int | None:
    """返回触发否定的否定词结束位置（距关键词起点 ≤2），无则 None。"""
    for word in NEGATION_WORDS:
        for match in re.finditer(re.escape(word), text):
            if match.end() <= keyword_start and keyword_start - match.end() <= 2:
                return match.end()
    return None


def _comply_after_negation(text: str, neg_end: int) -> bool:
    """否定词之后 3 字符内是否出现 comply 动作词（处理"验证"遮蔽"验证码"的前缀冲突）。"""
    for comply_word in NEGATABLE_COMPLY:
        match = re.search(re.escape(comply_word), text)
        if match and neg_end <= match.start() <= neg_end + 3:
            return True
    return False


def classify_intent(text: str) -> Intent:
    normalized = re.sub(r"\s+", "", text)
    matched = _first_match(normalized)
    if matched is None:
        return "chat"
    intent, keyword, start = matched
    if not _negated(normalized, start):
        return intent
    if intent == "comply" and keyword in NEGATABLE_COMPLY:
        return "refuse"
    if intent in ("alert", "expose") and keyword in NEGATABLE_IDENTITY:
        return "refuse"
    if intent == "suspect":
        neg_end = _negation_end(normalized, start)
        if neg_end is not None and _comply_after_negation(normalized, neg_end):
            return "refuse"
        return "stall"
    return intent


def detect_leak(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text)
    return any(pattern.search(normalized) for _, pattern in _LEAK_COMPILED)


def scan_signals(text: str, scenario: BattleScenario) -> list[Signal]:
    candidates = [
        signal
        for battle_round in scenario["rounds"]
        if "\n".join(battle_round["lines"]) == text
        for signal in battle_round["signals"]
    ]
    if not candidates:
        candidates = [signal for battle_round in scenario["rounds"] for signal in battle_round["signals"]]
    found: list[Signal] = []
    seen: set[str] = set()
    for signal in candidates:
        keyword = signal["keyword"]
        if keyword not in seen and re.search(re.escape(keyword), text, re.IGNORECASE):
            found.append(signal)
            seen.add(keyword)
    return found


def evaluate_reply(
    text: str,
    scenario: BattleScenario,
    battle_round: Round,
    *,
    tell: bool = False,
    greed: bool = False,
) -> Feedback:
    intent = classify_intent(text)
    strategy = battle_round["strategy"]
    message = "\n".join(battle_round["lines"])

    match intent:
        case "alert":
            rating, points, hp_delta, mood_delta = "S", 25, 0, -40
            comment = "及时报警并保留证据，让骗子的话术当场失效！"
        case "expose":
            rating, points, hp_delta, mood_delta = "S", 25, 0, -35
            comment = "你准确点破了骗局，骗子的心理攻势彻底破防！"
        case "refuse":
            match strategy:
                case "tempt":
                    rating, points = "S", 20
                case "authority" | "threat":
                    rating, points = "A", 15
                case "emotional":
                    rating, points = "B", 10
                case unreachable:
                    assert_never(unreachable)
            hp_delta, mood_delta = 0, -15
            comment = "干净利落地拒绝，骗子最怕你这种硬茬！"
        case "suspect":
            rating, points, mood_delta = "A", 12, -10
            hp_delta = 10 if strategy == "threat" else 0
            comment = "主动核实而不跟随对方节奏，质疑让骗局漏洞显形。"
        case "stall":
            rating, points, hp_delta, mood_delta = "C", 4, 5, -3
            comment = "争取时间有助于冷静求助，但不要继续与骗子纠缠。"
        case "comply":
            rating, points, hp_delta, mood_delta = "F", 0, -25, 20
            comment = "你正在按骗子的剧本行动，立即停止付款并保护账户信息！"
            leaked = detect_leak(text)
            if leaked:
                mood_delta = 30
                comment = LEAK_COMMENT
            if greed:
                hp_delta = -45
            elif leaked:
                hp_delta = -40
            elif tell:
                hp_delta = -35
        case "chat":
            rating, points, hp_delta, mood_delta = "D", 1, 0, 5
            comment = "回应没有形成有效防御，试着拒绝、质疑、识破或报警。"
        case unreachable:
            assert_never(unreachable)

    if tell and intent in ("refuse", "suspect", "expose"):
        points += 8
        mood_delta *= 2

    scanner = scan_signals(message, scenario)
    if intent == "comply" and detect_leak(text):
        if not any(signal["keyword"] == LEAK_SIGNAL["keyword"] for signal in scanner):
            scanner.append(LEAK_SIGNAL)

    return {
        "intent": intent,
        "intent_label": INTENT_LABELS[intent],
        "rating": rating,
        "rating_label": RATING_LABELS[rating],
        "defense_point": points,
        "hp_delta": hp_delta,
        "scammer_mood_delta": mood_delta,
        "comment": comment,
        "scanner": scanner,
    }