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


def test_suspect_recovers_hp_when_strategy_is_threat() -> None:
    # Given
    scenario = BATTLE_SCENARIOS["4"]
    battle_round = scenario["rounds"][0]

    # When
    feedback = evaluate_reply("我先去官网核实案件编号", scenario, battle_round)

    # Then
    assert feedback["intent"] == "suspect"
    assert feedback["hp_delta"] == 10


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
    assert "理赔流程" in state.scammer_msg
    assert all(signal.severity == "high" for signal in state.signals)
    assert state.scammer_state.strategy_label == "语无伦次·破绽显露"


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
    test_suspect_recovers_hp_when_strategy_is_threat()
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