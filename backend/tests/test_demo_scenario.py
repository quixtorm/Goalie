"""The 3-minute demo, end to end through the HTTP API, fallback agent (no API key).
Expected numbers were pre-computed with exact arithmetic (see PROMPT_v2.md)."""
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(scope="module")
def c():
    client = TestClient(main.app)
    assert client.post("/demo/reset").status_code == 200
    return client


def inbox(c, kind):
    return [p for p in c.get("/agent/inbox").json() if p["kind"] == kind and p["status"] == "pending"]


def car(c):
    return next(g for g in c.get("/state").json()["goals"] if g["name"] == "Машина")


def test_step1_create_car_goal_via_chat(c):
    r = c.post("/agent/chat", json={"message": "Хочу накопить 50 млн на машину за 3 года"}).json()
    assert r["source"] == "fallback"
    assert r["data"]["percent"] == 21
    assert (r["data"]["months_worst"], r["data"]["months_best"]) == (36, 32)
    assert r["data"]["expiry"] == "2029-12-01"
    assert "защищены от импульсных трат" in r["reply"]
    assert len(r["proposals"]) == 1
    r2 = c.post("/agent/chat", json={"message": "да"}).json()
    assert "создана" in r2["reply"]
    g = car(c)
    assert g["percent"] == 21 and g["planned_months_left"] == 36 and g["priority"] == 2


def test_step1b_reorder_car_first(c):
    r = c.post("/subcards/reorder", json={"ids": [car(c)["id"], "goal_phone"]})
    assert r.status_code == 200
    names = [g["name"] for g in c.get("/state").json()["goals"]]
    assert names == ["Машина", "Телефон"] and car(c)["priority"] == 1


def test_step2_salary_drop_and_new_percent(c):
    flow = c.post("/demo/salary", json={"amount": 6_375_000}).json()
    assert flow["obligations"] == [{"id": "obl_rent", "name": "Аренда квартиры", "amount": 1_500_000}]
    amounts = {g["name"]: g["amount"] for g in flow["goals"]}
    assert amounts == {"Телефон": 637_500, "Машина": 1_338_750}
    assert [g["name"] for g in flow["goals"]] == ["Машина", "Телефон"]  # priority order
    assert flow["shortfalls"] == []
    assert flow["main"] == 2_898_750
    st = c.get("/state").json()
    assert st["main"]["main_balance"] == 14_898_750
    assert st["income"]["worst"] == 6_375_000
    g = car(c)
    assert g["months_worst"] == 37 and g["planned_months_left"] == 35
    props = inbox(c, "goal_percent")
    assert len(props) == 1 and props[0]["numbers"]["new_percent"] == 22
    c.post(f"/agent/proposals/{props[0]['id']}/confirm")
    g = car(c)
    assert (g["percent"], g["months_worst"], g["months_best"], g["expiry"]) == (22, 35, 31, "2029-11-01")
    assert c.get("/state").json()["used_percent"] == 32


def test_step3_cinema_stopped_cooling_then_decline(c):
    g = car(c)
    r = c.post("/spend", json={"source_id": g["id"], "amount": 150_000, "mcc": "7832",
                               "merchant": "Magic Cinema"}).json()
    assert r["outcome"] == "stopped"
    assert r["delay_days"] == 3 and r["bonus_lost"] == 7_750_042
    assert r["can_cover_from_main"] is True
    assert car(c)["saved"] == 1_338_750
    c.post(f"/spend/{r['stop_id']}/resolve", json={"option": "cooling"})
    c.post("/demo/skip-time", json={"hours": 24})
    props = inbox(c, "cooling_ready")
    assert len(props) == 1
    res = c.post(f"/agent/proposals/{props[0]['id']}/confirm", json={"option": "decline"}).json()
    assert res["status"] == "confirmed"
    assert car(c)["saved"] == 1_338_750 and car(c)["disciplined"] is True


def test_step4_pharmacy_released(c):
    g = car(c)
    r = c.post("/spend", json={"source_id": g["id"], "amount": 300_000, "mcc": "5912",
                               "merchant": "Dori-Darmon"}).json()
    assert r["outcome"] == "released"
    g = car(c)
    assert g["saved"] == 1_038_750 and g["disciplined"] and g["rate"] == 22 and g["months_worst"] == 35


def test_step5_credit(c):
    r = c.post("/agent/chat", json={"message": "Хочу телефон в кредит за 20 млн на 12 месяцев под 28%"}).json()
    d = r["data"]
    assert (d["payment"], d["overpayment"], d["dti_percent"]) == (1_930_120, 3_161_437, 30)
    assert d["dti_risk"] is False and d["cashflow_risk"] is True and d["free_money"] == 1_835_000
    imp = next(i for i in d["impact"] if i["name"] == "Машина")
    assert (imp["months_before"], imp["months_after"], imp["delay_months"]) == (35, 51, 16)
    assert r["proposals"] == []  # credit never creates anything


def test_step6_new_debt_topup(c):
    before = c.get("/state").json()["main"]["main_balance"]
    c.post("/obligations", json={"name": "Долг брату", "amount": 1_500_000, "due_date": "2026-12-05"})
    props = inbox(c, "obligation_topup")
    assert len(props) == 1 and props[0]["numbers"]["amount"] == 1_500_000
    c.post(f"/agent/proposals/{props[0]['id']}/confirm")
    st = c.get("/state").json()
    assert st["main"]["main_balance"] == before - 1_500_000
    debt = next(o for o in st["obligations"] if o["name"] == "Долг брату")
    assert debt["reserved"] == 1_500_000 and debt["status"] == "ok"


def test_step7_family_transfer_does_not_change_the_plan(c):
    before = car(c)
    r = c.post("/demo/transfer-in", json={"amount": 2_000_000, "source": "Семья"})
    assert r.status_code == 200
    after = car(c)
    # plan untouched: same percent, deadline, months, saved
    for k in ("percent", "expiry", "months_worst", "months_best", "saved", "priority"):
        assert after[k] == before[k], k
    props = inbox(c, "transfer_save")
    assert len(props) == 1
    p = props[0]
    assert p["numbers"]["goal_id"] == before["id"] and p["numbers"]["suggested"] == 440_000  # 22% of 2 000 000
    c.post(f"/agent/proposals/{p['id']}/confirm")
    g = car(c)
    assert g["saved"] == before["saved"] + 440_000 and g["progress"] >= before["progress"]
    assert g["percent"] == 22 and g["expiry"] == before["expiry"]
