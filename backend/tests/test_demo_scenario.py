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
    # breakdown for the "salary split" sheet: waterfall order, sums to the salary
    bd = flow["breakdown"]
    assert [(b["type"], b["label"], b["amount"]) for b in bd] == [
        ("obligation", "Аренда квартиры", 1_500_000), ("goal", "Машина", 1_338_750),
        ("goal", "Телефон", 637_500), ("main", "Основная карта", 2_898_750)]
    assert sum(b["amount"] for b in bd) == 6_375_000
    assert [b["target_id"] for b in bd][0] == "obl_rent" and bd[-1]["target_id"] == "main"
    assert bd[1]["priority"] == 1 and bd[1]["percent"] == 21
    assert all(b["progress_after"] >= b["progress_before"] for b in bd if b["type"] != "main")
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
    assert r["delay_days"] == 3 and r["bonus_lost"] == 1_045_500  # next 12 months only
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


def test_step4b_release_needs_pin_then_notice_and_cancel(c):
    g = car(c)
    stop = c.post("/spend", json={"source_id": g["id"], "amount": 100_000, "mcc": "5812", "merchant": "Plov Center"}).json()
    # without the PIN: rejected
    assert c.post(f"/spend/{stop['stop_id']}/resolve", json={"option": "proceed"}).status_code == 401
    # wrong PIN: rejected, attempts left shown
    bad = c.post("/auth/step-up", json={"pin": "0000"})
    assert bad.status_code == 401 and bad.json()["attempts_left"] == 2
    # correct PIN: accepted
    tok = c.post("/auth/step-up", json={"pin": "1234"}).json()["token"]
    ok = c.post(f"/spend/{stop['stop_id']}/resolve", json={"option": "proceed"}, headers={"X-Step-Up": tok})
    assert ok.status_code == 200 and car(c)["saved"] == g["saved"] - 100_000
    n = [p for p in c.get("/agent/inbox").json() if p["kind"] == "security_notice" and p["status"] == "pending"]
    assert len(n) == 1 and "Это были не вы?" in n[0]["text"]
    # "Отменить" within 24 h: money and discipline bonus restored, later steps unchanged
    c.post(f"/agent/proposals/{n[0]['id']}/confirm")
    assert car(c)["saved"] == g["saved"] and car(c)["disciplined"] is True


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


def test_step8_credit_advisor_nothing_applied_without_confirmation(c):
    before = c.get("/state").json()
    r = c.post("/agent/chat", json={"message": "Посоветуй лучший кредит с низким процентом на компьютер 15 млн"}).json()
    adv = r["credit_advice"]
    assert adv and adv["demo_data"] and len(adv["options"]) == 3
    best = adv["best"]
    assert best["product_id"] == "demo_cons_std" and best["months"] == 12 and "best_cost" in best["tags"]
    assert best["total_overpayment"] == 2_345_425 and best["monthly_payment"] == 1_432_952
    assert adv["lowest_payment"]["product_id"] == "demo_cons_long" and adv["lowest_payment"]["months"] == 48
    assert any(d["name"] == "Машина" and d["delay_months"] > 0 for d in best["goal_delays"])
    assert adv["wait_option"]["months_worst"] == 30 and adv["wait_option"]["overpayment_avoided"] == 2_345_425
    assert "Лучший по стоимости" in r["reply"] and "решать вам" in r["reply"].lower()
    after = c.get("/state").json()
    assert after["credit_applications"] == [] and after["main"] == before["main"]  # nothing applied
    # no amount -> one question, nothing else
    q = c.post("/agent/chat", json={"message": "Подбери кредит с низким процентом"}).json()
    assert "На какую сумму" in q["reply"] and not q.get("credit_advice")


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
