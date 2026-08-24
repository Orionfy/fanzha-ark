from fastapi.testclient import TestClient

from api import app
from knowledge.data import QUIZ_BANK, TOPICS
from knowledge.engine import _rating_for

client = TestClient(app)


def test_topics_data_has_ten_complete_entries() -> None:
    # Given / When
    required_keys = {"id", "name", "icon", "tagline", "difficulty", "summary",
                     "tactics", "scripts", "signals", "rules", "case_study", "related_topic_ids"}

    # Then
    assert len(TOPICS) == 10
    for topic_id, topic in TOPICS.items():
        assert set(topic.keys()) == required_keys, topic_id
        assert topic["id"] == topic_id
        assert 4 <= len(topic["tactics"]) <= 6, topic_id
        assert 3 <= len(topic["scripts"]) <= 5, topic_id
        assert 4 <= len(topic["signals"]) <= 6, topic_id
        assert 3 <= len(topic["rules"]) <= 5, topic_id
        assert set(topic["case_study"].keys()) == {"title", "story", "analysis"}, topic_id
        for related_id in topic["related_topic_ids"]:
            assert related_id in TOPICS, (topic_id, related_id)


def test_quiz_bank_covers_every_topic_with_valid_questions() -> None:
    # Given（≥24 题、每主题至少 2 题、选项恰好 4 个）
    counts: dict[str, int] = {}

    # When
    for question in QUIZ_BANK:
        counts[question["topic_id"]] = counts.get(question["topic_id"], 0) + 1

    # Then
    assert len(QUIZ_BANK) >= 24
    assert len({q["qid"] for q in QUIZ_BANK}) == len(QUIZ_BANK)
    assert set(counts.keys()) == set(TOPICS.keys())
    for topic_id, count in counts.items():
        assert count >= 2, topic_id
    for question in QUIZ_BANK:
        assert len(question["options"]) == 4, question["qid"]
        assert 0 <= question["correct_index"] <= 3, question["qid"]
        assert len(question["explanation"]) <= 50, question["qid"]


def test_topics_endpoint_returns_ten_cards() -> None:
    # When
    response = client.get("/api/knowledge/topics")

    # Then
    assert response.status_code == 200
    topics = response.json()["topics"]
    assert len(topics) == 10
    for card in topics:
        for key in ("id", "name", "icon", "tagline", "difficulty", "quiz_count"):
            assert key in card, card
        assert card["quiz_count"] >= 2, card


def test_topic_detail_contains_all_sections() -> None:
    # When
    response = client.get("/api/knowledge/topics/brushing_rebate")
    detail = response.json()

    # Then
    assert response.status_code == 200
    assert detail["name"] == "刷单返利"
    assert 4 <= len(detail["tactics"]) <= 6
    assert 3 <= len(detail["scripts"]) <= 5
    assert 4 <= len(detail["signals"]) <= 6
    assert 3 <= len(detail["rules"]) <= 5
    assert set(detail["case_study"].keys()) == {"title", "story", "analysis"}
    assert all(related in TOPICS for related in detail["related_topic_ids"])


def test_unknown_topic_returns_404() -> None:
    # When
    response = client.get("/api/knowledge/topics/not_a_topic")

    # Then
    assert response.status_code == 404
    assert response.json()["detail"] == "该主题不存在"


def test_quiz_draw_never_leaks_answers() -> None:
    # When
    response = client.get("/api/knowledge/quiz?count=20")
    questions = response.json()["questions"]

    # Then
    assert response.status_code == 200
    assert len(questions) == 20
    for question in questions:
        assert set(question.keys()) == {"qid", "topic_id", "question", "options"}, question
        assert len(question["options"]) == 4
        assert "correct_index" not in question
        assert "explanation" not in question
    assert len({q["qid"] for q in questions}) == len(questions)


def test_quiz_draw_filters_by_topic_and_caps_at_available() -> None:
    # Given（每主题仅 3 题，count 超出时应返回全部可用题）
    topic_id = "prize_tax"

    # When
    response = client.get(f"/api/knowledge/quiz?count=20&topic_id={topic_id}")
    questions = response.json()["questions"]

    # Then
    assert response.status_code == 200
    assert len(questions) == 3
    assert {q["topic_id"] for q in questions} == {topic_id}


def test_quiz_draw_rejects_invalid_count() -> None:
    # When / Then（FastAPI Query 校验自动 422）
    assert client.get("/api/knowledge/quiz?count=0").status_code == 422
    assert client.get("/api/knowledge/quiz?count=21").status_code == 422


def test_quiz_draw_unknown_topic_returns_404() -> None:
    # When
    response = client.get("/api/knowledge/quiz?topic_id=not_a_topic")

    # Then
    assert response.status_code == 404
    assert response.json()["detail"] == "该主题不存在"


def test_submit_grades_known_answer_mix() -> None:
    # Given（前 10 题中 9 对 1 错 → accuracy 90 → 反诈专家）
    sampled = QUIZ_BANK[:10]
    answers = [
        {"qid": q["qid"], "choice": q["correct_index"]} for q in sampled[:9]
    ]
    wrong = sampled[9]
    answers.append({"qid": wrong["qid"], "choice": (wrong["correct_index"] + 1) % 4})

    # When
    response = client.post("/api/knowledge/quiz/submit", json={"answers": answers})
    result = response.json()

    # Then
    assert response.status_code == 200
    assert result["total"] == 10
    assert result["correct_count"] == 9
    assert result["accuracy"] == 90
    assert result["rating"] == "反诈专家"
    assert len(result["review"]) == 10
    graded_wrong = next(item for item in result["review"] if item["qid"] == wrong["qid"])
    assert graded_wrong["correct"] is False
    assert graded_wrong["your_choice"] == (wrong["correct_index"] + 1) % 4
    assert graded_wrong["correct_index"] == wrong["correct_index"]
    assert graded_wrong["explanation"] == wrong["explanation"]
    graded_right = result["review"][0]
    assert graded_right["correct"] is True


def test_submit_treats_missing_choice_as_unanswered() -> None:
    # Given（choice 缺省表示未答，判错但不报错）
    question = QUIZ_BANK[0]

    # When
    response = client.post("/api/knowledge/quiz/submit", json={"answers": [{"qid": question["qid"]}]})
    result = response.json()

    # Then
    assert response.status_code == 200
    assert result["total"] == 1
    assert result["correct_count"] == 0
    review = result["review"][0]
    assert review["your_choice"] is None
    assert review["correct"] is False


def test_submit_unknown_qid_maps_to_400() -> None:
    # Given
    payload = {"answers": [{"qid": "q_ghost_99", "choice": 1}]}

    # When
    response = client.post("/api/knowledge/quiz/submit", json=payload)

    # Then
    assert response.status_code == 400
    assert "q_ghost_99" in response.json()["detail"]


def test_submit_rejects_empty_and_malformed_body() -> None:
    # When / Then（请求体校验失败 FastAPI 自动 422）
    assert client.post("/api/knowledge/quiz/submit", json={"answers": []}).status_code == 422
    assert client.post("/api/knowledge/quiz/submit", json={"answers": [{"choice": 1}]}).status_code == 422


def test_rating_boundaries() -> None:
    # Given / When / Then（≥90 专家 / ≥70 达人 / ≥50 门径 / 其余 新兵）
    assert _rating_for(100) == "反诈专家"
    assert _rating_for(90) == "反诈专家"
    assert _rating_for(89) == "反诈达人"
    assert _rating_for(70) == "反诈达人"
    assert _rating_for(69) == "初窥门径"
    assert _rating_for(50) == "初窥门径"
    assert _rating_for(49) == "防诈新兵"
    assert _rating_for(0) == "防诈新兵"


def run_knowledge_tests() -> None:
    test_topics_data_has_ten_complete_entries()
    test_quiz_bank_covers_every_topic_with_valid_questions()
    test_topics_endpoint_returns_ten_cards()
    test_topic_detail_contains_all_sections()
    test_unknown_topic_returns_404()
    test_quiz_draw_never_leaks_answers()
    test_quiz_draw_filters_by_topic_and_caps_at_available()
    test_quiz_draw_rejects_invalid_count()
    test_quiz_draw_unknown_topic_returns_404()
    test_submit_grades_known_answer_mix()
    test_submit_treats_missing_choice_as_unanswered()
    test_submit_unknown_qid_maps_to_400()
    test_submit_rejects_empty_and_malformed_body()
    test_rating_boundaries()


if __name__ == "__main__":
    run_knowledge_tests()
