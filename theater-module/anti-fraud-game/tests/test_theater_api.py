from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def _start_game(scenario_id: str) -> str:
    response = client.post("/api/game/start", json={
        "name": "测试",
        "gender": "1",
        "identity": "2",
        "scenario_id": scenario_id,
    })
    assert response.status_code == 200
    return response.json()["game_id"]


def _advance(game_id: str, steps: int) -> None:
    for _ in range(steps):
        response = client.post(f"/api/game/{game_id}/advance")
        assert response.status_code == 200


def test_alert_rejected_on_node_without_allow_alert() -> None:
    # Given（票务场景：节点 2 为 choice 且未开启 allow_alert）
    game_id = _start_game("3")
    _advance(game_id, steps=2)

    # When
    response = client.post(f"/api/game/{game_id}/choice", json={"choice": "报警"})

    # Then
    assert response.status_code == 400
    assert response.json()["detail"] == "当前节点不支持报警"


def test_alert_allowed_node_still_jumps_to_alert_node() -> None:
    # Given（AI 换脸场景：节点 1-1 开启 allow_alert，alert_node=police_alert）
    game_id = _start_game("8")
    _advance(game_id, steps=1)                                        # 0 → 0-1
    client.post(f"/api/game/{game_id}/choice", json={"choice": "1"})  # → 1
    _advance(game_id, steps=1)                                        # 1 → 1-1

    # When
    response = client.post(f"/api/game/{game_id}/choice", json={"choice": "报警"})

    # Then
    assert response.status_code == 200
    assert response.json()["node_id"] == "police_alert"


def test_normal_choice_unaffected_by_alert_guard() -> None:
    # Given（同上票务场景节点 2）
    game_id = _start_game("3")
    _advance(game_id, steps=2)

    # When / Then（数字选项不受报警校验影响）
    response = client.post(f"/api/game/{game_id}/choice", json={"choice": "4"})
    assert response.status_code == 200
    assert response.json()["node_id"] == "24"


def run_theater_api_tests() -> None:
    test_alert_rejected_on_node_without_allow_alert()
    test_alert_allowed_node_still_jumps_to_alert_node()
    test_normal_choice_unaffected_by_alert_guard()
    print("theater api tests ok (3 passed)")


if __name__ == "__main__":
    run_theater_api_tests()
