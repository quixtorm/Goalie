"""Only SALARY drives the plan. Transfers from family never change it; they only trigger an optional proposal."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

import calc
import main
from mock_data import seed
from modules import budget, goals, proposals

TODAY = date(2026, 12, 1)


def rec(d, amount, t):
    return {"id": d + t, "date": d, "amount": amount, "type": t, "source": "x"}


SAL = [rec(f"2026-{m:02d}-01", a, calc.SALARY)
       for m, a in zip(range(6, 12), [7_200_000, 6_800_000, 7_600_000, 8_200_000, 7_400_000, 7_800_000])]


def test_seed_basis_unchanged_and_salary_only():
    s = seed()
    assert calc.worst_monthly_income(s.incomes) == 6_800_000
    assert calc.avg_monthly_income(s.incomes) == 7_500_000
    assert calc.worst_annual_income(s.incomes) == 81_600_000
    by = calc.income_by_type(s.incomes, TODAY)["by_type"]
    assert by["SALARY"]["count"] == 12 and by["TRANSFER"] == {"total": 3_500_000, "count": 2}
    assert by["OTHER"] == {"total": 450_000, "count": 1}


def test_large_transfer_does_not_change_income_plan_or_expiry():
    with_transfer = SAL + [rec("2026-11-15", 50_000_000, calc.TRANSFER), rec("2026-11-20", 9_000_000, calc.OTHER)]
    a, b = calc.basis_from_records(SAL), calc.basis_from_records(with_transfer)
    assert (a.worst, a.avg) == (b.worst, b.avg)
    assert calc.suggest_percent(50_000_000, 36, 10, a) == calc.suggest_percent(50_000_000, 36, 10, b)
    fa, fb = calc.goal_forecast(50_000_000, 0, 21, a, TODAY), calc.goal_forecast(50_000_000, 0, 21, b, TODAY)
    assert fa.expiry == fb.expiry


def test_lower_salary_does_change_the_plan():
    lower = SAL + [rec("2026-12-01", 6_375_000, calc.SALARY)]
    b = calc.basis_from_records(lower)
    assert b.worst == 6_375_000
    assert calc.goal_forecast(48_661_250, 0, 21, b, TODAY).months_worst == 37  # was 36 at the old worst


def test_transfer_suggestion_formula():
    assert calc.transfer_save_suggestion(2_000_000, 10, 4_800_000, 12_000_000) == 200_000
    assert calc.transfer_save_suggestion(2_000_000, 10, 50_000, 12_000_000) == 50_000   # capped by goal
    assert calc.transfer_save_suggestion(2_000_000, 10, 4_800_000, 0) == 0             # capped by main card


def snapshot(s):
    return {g.id: (g.saved, g.percent, goals.view(s, g)["expiry"], goals.view(s, g)["months_worst"])
            for g in s.goals.values()}


def test_transfer_in_leaves_goals_and_plan_untouched_and_offers_proposal():
    s = seed()
    before_goals, before_basis = snapshot(s), budget.basis(s)
    main0 = s.main_balance
    proposals.transfer_in(s, 2_000_000, "Семья")
    assert snapshot(s) == before_goals
    assert budget.basis(s) == before_basis
    assert s.main_balance == main0 + 2_000_000
    props = [p for p in s.proposals.values() if p.kind == "transfer_save" and p.status == "pending"]
    assert len(props) == 1 and props[0].numbers["suggested"] == 200_000


def test_confirm_moves_exactly_the_suggestion():
    s = seed()
    proposals.transfer_in(s, 2_000_000, "Семья")
    p = next(p for p in s.proposals.values() if p.kind == "transfer_save")
    main1, saved1 = s.main_balance, s.goals["goal_phone"].saved
    proposals.apply(s, p.id)
    assert s.goals["goal_phone"].saved == saved1 + 200_000
    assert s.main_balance == main1 - 200_000
    assert s.goals["goal_phone"].percent == 10  # plan unchanged
    proposals.agent_review(s)
    assert not [p for p in s.proposals.values() if p.kind == "transfer_save" and p.status == "pending"]


def test_reject_leaves_everything_unchanged():
    s = seed()
    proposals.transfer_in(s, 2_000_000, "Семья")
    p = next(p for p in s.proposals.values() if p.kind == "transfer_save")
    before, main1 = snapshot(s), s.main_balance
    proposals.reject(s, p.id)
    proposals.agent_review(s)
    assert snapshot(s) == before and s.main_balance == main1
    assert not [p for p in s.proposals.values() if p.kind == "transfer_save" and p.status == "pending"]


def test_api_transfer_and_income_view():
    c = TestClient(main.app)
    c.post("/demo/reset")
    st0 = c.get("/state").json()
    r = c.post("/demo/transfer-in", json={"amount": 2_000_000, "source": "Семья"})
    assert r.status_code == 200 and r.json()["type"] == "TRANSFER"
    st = c.get("/state").json()
    assert st["income"]["worst"] == st0["income"]["worst"] and st["income"]["worst_annual"] == 81_600_000
    assert [g["expiry"] for g in st["goals"]] == [g["expiry"] for g in st0["goals"]]
    assert st["transactions"][0]["type"] == "TRANSFER"
    assert st["today_summary"]["income_by_type"]["TRANSFER"] == 2_000_000
    assert c.post("/demo/transfer-in", json={"amount": 0, "source": "x"}).status_code == 422
    assert c.post("/demo/transfer-in", json={"amount": 10, "source": ""}).status_code == 422


def test_fallback_explains_why_transfers_are_not_counted():
    c = TestClient(main.app)
    c.post("/demo/reset")
    r = c.post("/agent/chat", json={"message": "Почему переводы от семьи не учитываются в плане?"}).json()
    assert r["source"] == "fallback"
    assert "только по зарплате" in r["reply"] and "6 800 000" in r["reply"] and "3 500 000" in r["reply"]
