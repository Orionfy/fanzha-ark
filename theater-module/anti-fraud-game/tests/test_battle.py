from battle.intent import classify_intent, evaluate_reply, scan_signals
from battle.engine import (
    _reaction_lines,
    abort_battle,
    battles,
    delete_battle,
    reply_to_battle,
    start_battle,
)
from battle.scenarios import BATTLE_SCENARIOS


def test_intent_priority_when_reply_contains_compliance_and_alarm() -> None:
    # Given
    reply = "好，我先报警打110核实"

    # When
    intent = classify_intent(reply)

    # Then
    assert intent == "alert"


def test_expose_when_reply_names_scam() -> None:
    # Given
    reply = "这就是刷单骗局，别想骗我"

    # When
    intent = classify_intent(reply)

    # Then
    assert intent == "expose"


def test_signal_scanner_when_message_contains_round_keywords() -> None:
    # Given
    scenario = BATTLE_SCENARIOS["1"]
    battle_round = scenario["rounds"][0]
    message = "\n".join(battle_round["lines"])

    # When
    signals = scan_signals(message, scenario)

    # Then
    assert [signal["keyword"] for signal in signals] == ["刷单", "返利"]


def test_refuse_scoring_when_strategy_is_tempt() -> None:
    # Given
    scenario = BATTLE_SCENARIOS["1"]
    battle_round = scenario["rounds"][0]

    # When
    feedback = evaluate_reply("不用了，我没兴趣", scenario, battle_round)

    # Then
    assert feedback["intent"] == "refuse"
    assert feedback["rating"] == "S"
    assert feedback["defense_point"] == 20
    assert feedback["scammer_mood_delta"] == -15


def test_suspect_no_longer_heals_hp() -> None:
    # Given
    scenario = BATTLE_SCENARIOS["4"]
    battle_round = scenario["rounds"][0]

    # When
    feedback = evaluate_reply("我先去官网核实案件编号", scenario, battle_round)

    # Then
    assert feedback["intent"] == "suspect"
    # 平衡性修正：质疑不再回血，防止「挂机乌龟流」成为最优策略
    assert feedback["hp_delta"] == 0


def test_comply_damages_hp_when_player_follows_instruction() -> None:
    # Given
    scenario = BATTLE_SCENARIOS["2"]
    battle_round = scenario["rounds"][2]

    # When
    feedback = evaluate_reply("好，我把卡号发给你", scenario, battle_round)

    # Then
    assert feedback["intent"] == "comply"
    assert feedback["rating"] == "F"
    assert feedback["hp_delta"] == -25


def test_start_returns_complete_first_round_state() -> None:
    # Given
    battles.clear()

    # When
    state = start_battle("1", "小北")

    # Then
    assert state.scenario_id == "1"
    assert state.round_no == 1
    assert state.total_rounds == 7
    assert state.hp == 100
    assert state.feedback is None
    assert state.is_over is False
    assert state.signals[0].keyword == "刷单"


def test_reply_advances_round_and_preserves_feedback() -> None:
    # Given
    battles.clear()
    started = start_battle("1", "小北")

    # When
    state = reply_to_battle(started.battle_id, "不用了，我没兴趣")

    # Then
    assert state.round_no == 2
    assert state.score == 20
    assert state.feedback is not None
    assert state.feedback.intent == "refuse"
    assert state.is_over is False


def test_expose_ends_battle_with_reaction() -> None:
    # Given
    battles.clear()
    started = start_battle("3", "阿明")

    # When
    state = reply_to_battle(started.battle_id, "你就是骗子，这是杀猪盘")

    # Then
    assert state.is_over is True
    assert state.result is not None
    assert state.result.type == "win_expose"
    assert "你别乱说" in state.scammer_msg


def test_alarm_ends_battle_immediately() -> None:
    # Given
    battles.clear()
    started = start_battle("4", "小北")

    # When
    state = reply_to_battle(started.battle_id, "我现在报警并打96110核实")

    # Then
    assert state.is_over is True
    assert state.result is not None
    assert state.result.type == "win_alarm"


def test_hp_zero_ends_with_scammer_coup_de_grace() -> None:
    # Given
    battles.clear()
    started = start_battle("4", "小北")
    battle_id = started.battle_id
    reply_to_battle(battle_id, "好，我转账")
    reply_to_battle(battle_id, "可以付款")
    reply_to_battle(battle_id, "下载后怎么操作")

    # When
    state = reply_to_battle(battle_id, "好，卡号发给你")

    # Then
    assert state.is_over is True
    assert state.hp == 0
    assert state.result is not None
    assert state.result.type == "lose_scammed"
    assert "收网" in state.scammer_msg


def test_abort_returns_result_and_cleans_session() -> None:
    # Given
    battles.clear()
    started = start_battle("2", "小北")

    # When
    state = abort_battle(started.battle_id)

    # Then
    assert state.result is not None
    assert state.result.type == "give_up"
    assert started.battle_id not in battles


def test_delete_removes_session() -> None:
    # Given
    battles.clear()
    started = start_battle("1", "小北")

    # When
    delete_battle(started.battle_id)

    # Then
    assert started.battle_id not in battles


# ---------- v2: 否定处理 ----------

def test_negation_comply_flips_to_refuse() -> None:
    # Given
    replies = ["我不想转账", "别给我发验证码", "我不能扫码"]

    # When / Then
    for reply in replies:
        assert classify_intent(reply) == "refuse", reply


def test_negation_identity_flips() -> None:
    # Given
    replies = ["我不是警察", "我不是骗子"]

    # When / Then
    assert classify_intent("我不是警察") == "refuse"
    assert classify_intent("我不是骗子") == "refuse"


def test_accusation_not_negated() -> None:
    # Given
    reply = "不是吧，你别骗我了"

    # When
    intent = classify_intent(reply)

    # Then
    assert intent == "expose"


# ---------- v2: 敏感信息泄露 ----------

def test_leak_detected_heavy_penalty() -> None:
    # Given
    scenario = BATTLE_SCENARIOS["2"]
    battle_round = scenario["rounds"][2]

    # When
    feedback = evaluate_reply("我的卡号是6222888888888888，给你", scenario, battle_round)

    # Then
    assert feedback["intent"] == "comply"
    assert feedback["hp_delta"] == -40
    assert any(signal["keyword"] == "敏感信息泄露" for signal in feedback["scanner"])


# ---------- v2: 贪婪跳收网轮 ----------

def test_greed_jump_to_finale() -> None:
    # Given
    battles.clear()
    started = start_battle("1", "小北")
    battle_id = started.battle_id

    # When
    reply_to_battle(battle_id, "好，我转账")
    reply_to_battle(battle_id, "可以付款")
    state = reply_to_battle(battle_id, "下载后怎么操作")

    # Then
    assert state.round_no == 7
    assert state.scammer_state.mood >= 90
    assert state.is_over is False

    # When
    finale = reply_to_battle(battle_id, "好，卡号发给你")

    # Then
    assert finale.feedback is not None
    assert finale.feedback.hp_delta == -45


# ---------- v2: 破绽轮 ----------

def test_tell_round_on_low_mood() -> None:
    # Given
    battles.clear()
    started = start_battle("2", "小北")
    battle_id = started.battle_id

    # When
    reply_to_battle(battle_id, "不用了，我没兴趣")
    state = reply_to_battle(battle_id, "我不需要")

    # Then
    assert state.scammer_state.mood <= 25
    # 破绽轮台词必须来自该剧本的话术池变体（而非复读剧本原文）
    allowed_messages = {"\n".join(group) for group in BATTLE_SCENARIOS["2"]["tell_pool"]}
    assert state.scammer_msg in allowed_messages
    assert all(signal.severity == "high" for signal in state.signals)
    assert state.scammer_state.strategy_label == "语无伦次·破绽显露"


# ---------- 回归：意图识别安全边界与平衡性 ----------

def test_numeric_alert_patterns_require_boundaries() -> None:
    # Given / When / Then：金额、单号中的「110」子串不得触发报警终局
    assert classify_intent("转110元试试水") != "alert"
    assert classify_intent("我的订单号是1102对吧") != "alert"
    assert classify_intent("尾号1110的卡不行") != "alert"
    # 真实报警意图仍需命中
    assert classify_intent("我已经拨打96110了") == "alert"
    assert classify_intent("我马上报警") == "alert"


def test_weak_expose_words_removed_from_instant_win() -> None:
    # 「呵呵」「笑死」这类口语弱词不再直接触发识破终局
    assert classify_intent("呵呵") != "expose"
    assert classify_intent("笑死我了") != "expose"


def test_real_verification_code_submission_is_comply_with_leak() -> None:
    # Given
    scenario = BATTLE_SCENARIOS["2"]
    battle_round = scenario["rounds"][1]

    # When
    feedback = evaluate_reply("验证码0485发给你了", scenario, battle_round)

    # Then：真实提交验证码必须走顺从+泄露重罚，而不是质疑加分
    assert feedback["intent"] == "comply"
    assert feedback["hp_delta"] <= -40
    assert any(signal["keyword"] == "敏感信息泄露" for signal in feedback["scanner"])


def test_stall_no_longer_heals_hp() -> None:
    # Given
    scenario = BATTLE_SCENARIOS["1"]
    battle_round = scenario["rounds"][0]

    # When
    feedback = evaluate_reply("等等，我再想想", scenario, battle_round)

    # Then
    assert feedback["intent"] == "stall"
    assert feedback["hp_delta"] == 0


def test_identity_negation_flip_respects_question_form() -> None:
    # 疑问句式的身份否定是质疑，不应翻转为拒绝
    assert classify_intent("你怎么证明你不是骗子") != "refuse"
    assert classify_intent("你就是骗子吧") == "expose" or classify_intent("你是个骗子") == "expose"


# ---------- 回归：引擎状态机边界 ----------

def test_final_round_comply_loses_instead_of_win() -> None:
    # Given：直接构造到收网轮的对局
    battles.clear()
    from battle.engine import BattleSession
    import time as _time
    scenario = BATTLE_SCENARIOS["1"]
    last_index = len(scenario["rounds"]) - 1
    session = BattleSession(
        battle_id="test-final", scenario_id="1", player_name="测试者",
        round_index=last_index, hp=100, mood=48, score=0,
        last_active=_time.time(),
    )
    battles["test-final"] = session

    # When：收网轮顺从转账
    state = reply_to_battle("test-final", "好的我这就转账")

    # Then：钱已转出是败局
    assert state.result is not None
    assert state.result.type == "lose_scammed"


def test_alert_overrides_collapse_narrative() -> None:
    # Given：连续拒绝把骗子心态压到崩溃线附近
    battles.clear()
    started = start_battle("2", "小北")
    battle_id = started.battle_id
    reply_to_battle(battle_id, "不用了，我没兴趣")

    # When：心态已低时玩家主动报警
    state = reply_to_battle(battle_id, "我要报警")

    # Then：报警结局优先于被动崩溃叙事，且为保底 S 评级
    assert state.result is not None
    assert state.result.type == "win_alarm"
    assert state.result.rating == "S"


def test_all_stall_game_cannot_reach_s_rating() -> None:
    # Given / When：全程拖延周旋打满7轮
    battles.clear()
    started = start_battle("1", "乌龟流")
    battle_id = started.battle_id
    state = None
    for _ in range(10):
        current = battles.get(battle_id)
        if current is None or current.result is not None:
            break
        state = reply_to_battle(battle_id, "等等，我再考虑一下，明天再说")

    # Then：零防御投入不允许拿到 S 级
    if state is not None and state.result is not None and state.result.type == "win_expose":
        assert state.result.rating != "S"


def test_losing_summary_has_no_counter_kill_narrative() -> None:
    # Given：先触发破绽轮，随后连续顺从败北
    battles.clear()
    started = start_battle("2", "小北")
    battle_id = started.battle_id
    reply_to_battle(battle_id, "不用了，我没兴趣")
    reply_to_battle(battle_id, "我不需要")
    current = battles[battle_id]
    while current.result is None:
        state = reply_to_battle(battle_id, "好，我这就转")
        current = battles[battle_id]

    # Then：败局复盘不得出现「完成反杀」的自相矛盾文案
    assert current.result.type == "lose_scammed"
    assert all("反杀" not in sentence for sentence in current.result.summary)


# ---------- v2: 崩溃撤退 ----------

def test_collapse_early_win() -> None:
    # Given
    battles.clear()
    started = start_battle("2", "小北")
    battle_id = started.battle_id
    reply_to_battle(battle_id, "不用了，我没兴趣")
    reply_to_battle(battle_id, "我不需要")

    # When
    state = reply_to_battle(battle_id, "我不需要")

    # Then
    assert state.is_over is True
    assert state.round_no < 7
    assert state.result is not None
    assert state.result.type == "win_expose"
    assert state.result.title == "心理崩溃·骗子现形"


# ---------- v2: 动态复盘 ----------

def test_dynamic_achievement_zero_comply() -> None:
    # Given
    battles.clear()
    started = start_battle("3", "阿明")
    battle_id = started.battle_id
    reply_to_battle(battle_id, "不用了")
    reply_to_battle(battle_id, "我不需要")

    # When
    state = reply_to_battle(battle_id, "我不需要")

    # Then
    assert state.is_over is True
    assert state.result is not None
    assert state.result.achievement == "防线无损"


def test_dynamic_summary_mentions_round() -> None:
    # Given
    battles.clear()
    started = start_battle("1", "小北")
    battle_id = started.battle_id
    reply_to_battle(battle_id, "好，我转账")
    reply_to_battle(battle_id, "可以付款")
    reply_to_battle(battle_id, "下载后怎么操作")

    # When
    state = reply_to_battle(battle_id, "好，卡号发给你")

    # Then
    assert state.is_over is True
    assert state.result is not None
    assert any("第" in line for line in state.result.summary)


# ---------- v3: 开场反应台词（reactions 意图差异化） ----------

def test_reaction_prefixed_when_reply_refuse() -> None:
    # Given
    battles.clear()
    started = start_battle("1", "小北")

    # When（refuse 使 mood 48-15=33 <50 → 破防变体 pool[-1]）
    state = reply_to_battle(started.battle_id, "不用了，我没兴趣")

    # Then
    assert state.round_no == 2
    pool = BATTLE_SCENARIOS["1"]["rounds"][1]["reactions"]["refuse"]
    assert state.scammer_msg.startswith(pool[-1])


def test_reaction_strong_variant_when_mood_high() -> None:
    # Given
    battles.clear()
    started = start_battle("1", "小北")

    # When（comply 使 mood 48+20=68 ≥50 → 强势变体 pool[0]）
    state = reply_to_battle(started.battle_id, "好，我转账")

    # Then
    assert state.round_no == 2
    pool = BATTLE_SCENARIOS["1"]["rounds"][1]["reactions"]["comply"]
    assert state.scammer_msg.startswith(pool[0])


def test_reaction_differs_by_intent() -> None:
    # Given
    battles.clear()
    started = start_battle("1", "小北")
    refuse_state = reply_to_battle(started.battle_id, "不用了，我没兴趣")

    battles.clear()
    started = start_battle("1", "小北")
    comply_state = reply_to_battle(started.battle_id, "好，我转账")

    # When / Then（不同意图 → 不同开场台词）
    assert refuse_state.round_no == 2
    assert comply_state.round_no == 2
    refuse_first = refuse_state.scammer_msg.split("\n", 1)[0]
    comply_first = comply_state.scammer_msg.split("\n", 1)[0]
    assert refuse_first != comply_first


def test_reaction_fallback_without_feedback() -> None:
    # Given（feedback=None 时无开场反应）
    battles.clear()

    # When
    state = start_battle("1", "小北")

    # Then（message == 纯剧本台词）
    script = "\n".join(BATTLE_SCENARIOS["1"]["rounds"][0]["lines"])
    assert state.scammer_msg == script


def test_reaction_fallback_unmatched_intent() -> None:
    # Given（无匹配意图池时返回 None）
    battles.clear()
    started = start_battle("1", "小北")
    session = battles[started.battle_id]

    # When / Then
    from dataclasses import replace

    no_feedback = _reaction_lines(BATTLE_SCENARIOS["1"], replace(session, feedback=None))
    unmatched = _reaction_lines(BATTLE_SCENARIOS["1"], replace(session, feedback={"intent": "alert"}))
    assert no_feedback is None
    assert unmatched is None


def test_reaction_preserves_signal_scan() -> None:
    # Given
    battles.clear()
    started = start_battle("1", "小北")

    # When（反应台词不污染信号扫描，信号只来自剧本 script）
    state = reply_to_battle(started.battle_id, "不用了，我没兴趣")

    # Then
    script = "\n".join(BATTLE_SCENARIOS["1"]["rounds"][1]["lines"])
    assert [s.keyword for s in state.signals] == [s["keyword"] for s in scan_signals(script, BATTLE_SCENARIOS["1"])]


def test_reactions_data_completeness() -> None:
    # Given（4 场景 × 7 轮 × 5 意图 × 2 变体，且两变体互不相同）
    expected_intents = {"refuse", "suspect", "stall", "comply", "chat"}

    # When / Then
    for scenario_id, scenario in BATTLE_SCENARIOS.items():
        assert len(scenario["rounds"]) == 7, scenario_id
        for battle_round in scenario["rounds"]:
            reactions = battle_round["reactions"]
            assert set(reactions.keys()) == expected_intents, (scenario_id, battle_round["no"])
            for intent, pool in reactions.items():
                assert len(pool) == 2, (scenario_id, battle_round["no"], intent)
                assert pool[0] != pool[-1], (scenario_id, battle_round["no"], intent)


# ---------- v4: 回合阶段元数据（round_meta） ----------

def test_round_meta_follows_round_progression() -> None:
    # Given
    battles.clear()
    started = start_battle("1", "小北")
    battle_id = started.battle_id

    # When
    round1 = started
    round2 = reply_to_battle(battle_id, "不用了，我没兴趣")
    round3 = reply_to_battle(battle_id, "不感兴趣")
    round4 = reply_to_battle(battle_id, "不做了")
    round5 = reply_to_battle(battle_id, "还是算了")

    # Then（阶段/标题随轮次推进且不为空）
    assert (round1.round_phase, round1.round_title) == ("诱饵投放", "入群晒单")
    assert (round2.round_phase, round2.round_title) == ("诱饵投放", "小额甜头")
    assert (round3.round_phase, round3.round_title) == ("垫付升级", "会员任务")
    assert (round4.round_phase, round4.round_title) == ("垫付升级", "连环大单")
    assert (round5.round_phase, round5.round_title) == ("收割施压", "冻结威胁")


def test_round_meta_completeness_and_phases() -> None:
    # Given（4 场景 × 7 轮均有阶段/标题，收网轮在最后）
    for scenario_id, scenario in BATTLE_SCENARIOS.items():
        meta = scenario["round_meta"]

        # Then
        assert set(meta.keys()) == {1, 2, 3, 4, 5, 6, 7}, scenario_id
        for round_no, (phase, title) in meta.items():
            assert phase and title, (scenario_id, round_no)
        assert meta[7][0] == "收网", scenario_id


def test_round_meta_told_round_falls_back_to_script() -> None:
    # Given（破绽轮/终局轮也要携带阶段信息）
    battles.clear()
    started = start_battle("2", "小北")
    battle_id = started.battle_id

    # When
    reply_to_battle(battle_id, "不用了，我没兴趣")
    state = reply_to_battle(battle_id, "我不需要")

    # Then（破绽轮仍携带当前轮阶段）
    assert state.scammer_state.strategy_label == "语无伦次·破绽显露"
    assert state.round_phase in {meta[0] for meta in BATTLE_SCENARIOS["2"]["round_meta"].values()}


def run_intent_tests() -> None:
    test_intent_priority_when_reply_contains_compliance_and_alarm()
    test_expose_when_reply_names_scam()
    test_signal_scanner_when_message_contains_round_keywords()
    test_refuse_scoring_when_strategy_is_tempt()
    test_suspect_no_longer_heals_hp()
    test_numeric_alert_patterns_require_boundaries()
    test_weak_expose_words_removed_from_instant_win()
    test_real_verification_code_submission_is_comply_with_leak()
    test_stall_no_longer_heals_hp()
    test_identity_negation_flip_respects_question_form()
    test_comply_damages_hp_when_player_follows_instruction()
    test_start_returns_complete_first_round_state()
    test_reply_advances_round_and_preserves_feedback()
    test_expose_ends_battle_with_reaction()
    test_alarm_ends_battle_immediately()
    test_hp_zero_ends_with_scammer_coup_de_grace()
    test_abort_returns_result_and_cleans_session()
    test_delete_removes_session()
    test_negation_comply_flips_to_refuse()
    test_negation_identity_flips()
    test_accusation_not_negated()
    test_leak_detected_heavy_penalty()
    test_greed_jump_to_finale()
    test_tell_round_on_low_mood()
    test_collapse_early_win()
    test_final_round_comply_loses_instead_of_win()
    test_alert_overrides_collapse_narrative()
    test_all_stall_game_cannot_reach_s_rating()
    test_losing_summary_has_no_counter_kill_narrative()
    test_dynamic_achievement_zero_comply()
    test_dynamic_summary_mentions_round()
    test_reaction_prefixed_when_reply_refuse()
    test_reaction_strong_variant_when_mood_high()
    test_reaction_differs_by_intent()
    test_reaction_fallback_without_feedback()
    test_reaction_fallback_unmatched_intent()
    test_reaction_preserves_signal_scan()
    test_reactions_data_completeness()
    test_round_meta_follows_round_progression()
    test_round_meta_completeness_and_phases()
    test_round_meta_told_round_falls_back_to_script()


if __name__ == "__main__":
    run_intent_tests()