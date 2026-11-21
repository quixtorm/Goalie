import pytest
from fastapi.testclient import TestClient

import main
from calc import CalcError
from fallback import parse
from mock_data import seed
from modules import budget, goals, proposals


def prios(s):
    return [(g.name, g.priority) for g in budget.active_goals(s)]


def test_default_priority_is_creation_order():
    s = seed()
    goals.create(s, "Машина", 50_000_000, 21)
    goals.create(s, "Отпуск", 5_000_000, 5)
    assert prios(s) == [("Телефон", 1), ("Машина", 2), ("Отпуск", 3)]


def test_reorder():
    s = seed()
    car = goals.create(s, "Машина", 50_000_000, 21)
    goals.reorder(s, [car.id, "goal_phone"])
    assert prios(s) == [("Машина", 1), ("Телефон", 2)]


def test_reorder_rejects_bad_lists():
    s = seed()
    car = goals.create(s, "Машина", 50_000_000, 21)
    for bad in ([car.id], [car.id, car.id], [car.id, "goal_phone", "nope"]):
        with pytest.raises(CalcError):
            goals.reorder(s, bad)


def test_waterfall_funds_in_priority_order_and_reports_shortfall():
    s = seed()
    car = goals.create(s, "Машина", 50_000_000, 21)
    goals.reorder(s, [car.id, "goal_phone"])  # car first
    # salary 2_000_000: rent takes 1_500_000, 500_000 left.
    # car wants 21% = 420_000 (fully funded), phone wants 10% = 200_000 but only 80_000 left
    flow = proposals.salary(s, 2_000_000)
    assert [(g["name"], g["amount"]) for g in flow["goals"]] == [("Машина", 420_000), ("Телефон", 80_000)]
    assert flow["shortfalls"] == [{"id": "goal_phone", "name": "Телефон", "priority": 2, "wanted": 200_000,
                                   "funded": 80_000, "shortfall": 120_000}]
    assert flow["main"] == 0
    assert s.last_salary["shortfalls"][0]["shortfall"] == 120_000


def test_same_salary_other_order_funds_phone_first():
    s = seed()
    goals.create(s, "Машина", 50_000_000, 21)  # phone stays #1
    flow = proposals.salary(s, 2_000_000)
    assert [(g["name"], g["amount"]) for g in flow["goals"]] == [("Телефон", 200_000), ("Машина", 300_000)]
    assert flow["shortfalls"][0]["name"] == "Машина" and flow["shortfalls"][0]["shortfall"] == 120_000


def test_renumber_after_close_and_completion():
    s = seed()
    car = goals.create(s, "Машина", 50_000_000, 21)
    trip = goals.create(s, "Отпуск", 5_000_000, 5)
    goals.start_close(s, "goal_phone")
    assert prios(s) == [("Машина", 1), ("Отпуск", 2)]
    assert s.goals["goal_phone"].priority == 0
    # complete "Отпуск" with one salary
    s.goals[trip.id].saved = 4_900_000
    proposals.salary(s, 7_500_000)
    assert s.goals[trip.id].status == "completed" and s.goals[trip.id].priority == 0
    assert prios(s) == [("Машина", 1)]
    assert car.priority == 1


def test_reorder_endpoint_and_state():
    c = TestClient(main.app)
    c.post("/demo/reset")
    car = c.post("/subcards", json={"name": "Машина", "amount": 50_000_000, "percent": 21}).json()
    assert car["priority"] == 2
    r = c.post("/subcards/reorder", json={"ids": [car["id"], "goal_phone"]})
    assert r.status_code == 200 and [g["priority"] for g in r.json()] == [1, 2]
    st = c.get("/state").json()
    assert [g["name"] for g in st["goals"]] == ["Машина", "Телефон"]
    assert c.post("/subcards/reorder", json={"ids": ["goal_phone"]}).status_code == 422


def test_uzbek_parsing():
    p = parse("Mashina uchun 50 mln 3 yilda yig'moqchiman")
    assert p == {"amount": 50_000_000, "months": 36, "name": "Mashina"}
    p = parse("Telefon kredit 20 mln 12 oyga 28%")
    assert (p["amount"], p["months"], p["rate"]) == (20_000_000, 12, 28)
