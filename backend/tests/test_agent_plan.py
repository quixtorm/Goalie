"""The user never chooses a percent: /subcards/plan and /subcards compute it on the server and ignore any client percent."""
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def c():
    client = TestClient(main.app)
    client.post("/demo/reset")
    return client


def test_plan_with_term_matches_verified_numbers(c):
    p = c.post("/subcards/plan", json={"name": "Машина", "goal_amount": 50_000_000, "term_months": 36}).json()
    assert (p["percent"], p["months_worst"], p["months_best"], p["expiry"]) == (21, 36, 32, "2029-12-01")
    assert p["contribution_worst"] == 1_428_000 and p["mode"] == "term" and p["explanation"]


def test_plan_without_term_agent_picks(c):
    p = c.post("/subcards/plan", json={"name": "Отпуск", "goal_amount": 5_000_000}).json()
    # ~24 months at the worst salary: ceil(5 000 000 / (24 * 6 800 000) * 100) = 4%
    assert p["percent"] == 4 and p["mode"] == "auto" and p["months_worst"] <= 24


def test_plan_capped_when_too_big(c):
    p = c.post("/subcards/plan", json={"name": "Машина", "goal_amount": 100_000_000, "term_months": 36}).json()
    assert p["percent"] == 30 and p["mode"] == "term_capped" and p["feasible"] is False


def test_client_percent_is_ignored_on_plan_and_create(c):
    p = c.post("/subcards/plan", json={"name": "Машина", "goal_amount": 50_000_000, "term_months": 36,
                                       "percent": 40}).json()
    assert p["percent"] == 21
    g = c.post("/subcards", json={"name": "Машина", "goal_amount": 50_000_000, "term_months": 36, "percent": 1}).json()
    assert g["percent"] == 21  # server value, not the client's 1


def test_create_equals_plan(c):
    p = c.post("/subcards/plan", json={"name": "Отпуск", "goal_amount": 5_000_000}).json()
    g = c.post("/subcards", json={"name": "Отпуск", "goal_amount": 5_000_000}).json()
    assert (g["percent"], g["expiry"]) == (p["percent"], p["expiry"])


def test_plan_validation(c):
    assert c.post("/subcards/plan", json={"name": "X", "goal_amount": 0}).status_code == 422
    assert c.post("/subcards/plan", json={"name": "X", "goal_amount": 10, "term_months": 0}).status_code == 422
    assert c.post("/subcards/plan", json={"name": "", "goal_amount": 10}).status_code == 422
