"""Credit advisor: ranking is code, over the DEMO catalog only."""
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

import calc
import loan_products
import main
from calc import IncomeBasis
from mock_data import seed
from modules import credits, proposals

B = IncomeBasis(6_800_000, Fraction(7_500_000))


def prod(pid, rate, fee=0, lo=1_000_000, hi=50_000_000, mn=6, mx=36, hist=0):
    return {"id": pid, "name": pid, "type": "consumer", "annual_rate": rate, "origination_fee_percent": fee,
            "min_amount": lo, "max_amount": hi, "min_months": mn, "max_months": mx,
            "early_repayment_allowed": True, "min_salary_history_months": hist}


def rank(products, amount=10_000_000, term=None, obligations=2_500_000, percents=(10,), goals=(), hist=12,
         used=10, linked=None, basis=B):
    return calc.rank_credits(amount, term, products, basis, obligations, list(percents), list(goals), hist, used, linked)


def test_best_is_lowest_total_cost_among_safe():
    r = rank([prod("cheap", 18), prod("pricey", 30), prod("zero_fee_mid", 22)], term=24)
    assert r["best"]["product_id"] == "cheap"
    safe_costs = [o["total_cost"] for o in r["options"] if o["safe"]]
    assert r["best"]["total_cost"] == min(safe_costs)
    assert "best_cost" in r["best"]["tags"]


def test_fee_is_included_in_overpayment():
    r = rank([prod("fee", 0, fee=8, mx=6)], amount=6_000_000, term=6)
    o = r["options"][0]
    assert o["interest"] == 0 and o["origination_fee"] == 480_000
    assert o["total_overpayment"] == 480_000 and o["total_cost"] == 6_480_000


def test_ineligible_products_excluded():
    r = rank([prod("ok", 20), prod("too_big", 20, lo=20_000_000), prod("needs_history", 20, hist=24),
              prod("short_only", 20, mn=3, mx=4)], term=12)
    assert {o["product_id"] for o in r["options"]} == {"ok"}
    reasons = {i["product_id"]: i["reason"] for i in r["ineligible"]}
    assert reasons == {"too_big": "amount", "needs_history": "salary_history", "short_only": "term"}


def test_term_limits_without_term():
    r = rank([prod("mid", 20, mn=12, mx=24)], amount=5_000_000, percents=())
    assert sorted(o["months"] for o in r["options"]) == [12, 24] and r["evaluated"] == 2


def test_income_share_above_40_is_risky():
    r = rank([prod("p", 20, mn=6, mx=6)], amount=20_000_000, term=6, obligations=0, percents=())
    o = r["options"][0]
    assert o["income_share_percent"] > 40 and o["risk"] is True and o["safe"] is False


def test_no_safe_option():
    r = rank([prod("p", 26, mx=12)], amount=40_000_000, obligations=2_500_000)
    assert r["best"] is None and "no_safe" in r["warnings"]
    assert r["lowest_risk"] is not None and "lowest_risk" in r["lowest_risk"]["tags"]


def test_lowest_payment_alternative_and_delays():
    goals = [{"id": "g", "name": "Машина", "amount": 50_000_000, "saved": 1_000_000, "percent": 22}]
    r = rank([prod("short", 24, mx=12), prod("long", 22, mn=24, mx=48)], amount=15_000_000, percents=(22,), goals=goals)
    assert r["lowest_payment"]["product_id"] == "long" and r["lowest_payment"]["months"] == 48
    assert r["best"]["total_overpayment"] < r["lowest_payment"]["total_overpayment"]
    assert all(d["delay_months"] >= 1 for d in r["best"]["goal_delays"])


def test_wait_option_for_goal_linked_credit():
    linked = {"name": "Машина", "amount": 50_000_000, "saved": 1_000_000, "percent": 22}
    r = rank([prod("p", 22, hi=100_000_000, mx=48)], amount=40_000_000, linked=linked, obligations=0, percents=())
    w = r["wait_option"]
    assert w["linked_goal"] == "Машина"
    assert w["months_worst"] == calc.months_needed(49_000_000, 22, 6_800_000)
    assert w["overpayment_avoided"] == (r["best"] or r["lowest_risk"])["total_overpayment"]


def test_catalog_is_demo_and_fictional():
    assert loan_products.DEMO_DATA is True and len(loan_products.PRODUCTS) >= 5
    rates = {p["annual_rate"] for p in loan_products.PRODUCTS}
    assert len(rates) >= 5  # meaningfully different


def test_demo_numbers_for_computer_15m():
    s = seed()
    r = credits.advise(s, 15_000_000)
    assert {i["product_id"] for i in r["ineligible"]} == {"demo_auto", "demo_micro"}
    assert r["best"]["product_id"] == "demo_install" and r["best"]["total_overpayment"] == 1_200_000


@pytest.fixture
def c():
    client = TestClient(main.app)
    client.post("/demo/reset")
    return client


def test_advise_endpoint_and_apply_requires_confirmation(c):
    r = c.post("/credits/advise", json={"amount": 15_000_000}).json()
    best = r["best"]
    before = c.get("/state").json()
    no = c.post("/credits/apply", json={"product_id": best["product_id"], "amount": 15_000_000, "months": best["months"]})
    assert no.status_code == 422
    assert c.get("/state").json()["credit_applications"] == []
    ok = c.post("/credits/apply", json={"product_id": best["product_id"], "amount": 15_000_000,
                                        "months": best["months"], "confirm": True}).json()
    assert ok["status"] == "demo_submitted"
    after = c.get("/state").json()
    assert len(after["credit_applications"]) == 1
    assert after["main"]["main_balance"] == before["main"]["main_balance"]  # mock: no money moved


def test_apply_rejects_ineligible(c):
    r = c.post("/credits/apply", json={"product_id": "demo_auto", "amount": 15_000_000, "months": 12, "confirm": True})
    assert r.status_code == 422
    assert c.post("/credits/apply", json={"product_id": "nope", "amount": 1, "months": 1, "confirm": True}).status_code == 404
