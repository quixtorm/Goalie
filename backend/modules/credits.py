"""Credit advisor module: wraps calc.rank_credits over the DEMO catalog, and records mock applications."""
from __future__ import annotations

import calc
import loan_products
from calc import CalcError
from modules import budget, goals
from state import State, new_id
from texts import disp, render, tr


def _products() -> list[dict]:
    return [{**p, "name": render(p["names"]), "note": render(p["notes"])} for p in loan_products.PRODUCTS]


def advise(s: State, amount: int, term_months: int | None = None, goal_id: str | None = None) -> dict:
    linked = None
    if goal_id:
        g = goals.get(s, goal_id)
        linked = {"name": disp(g), "amount": g.amount, "saved": g.saved, "percent": g.percent}
    goal_inputs = [{"id": g.id, "name": disp(g), "amount": g.amount, "saved": g.saved, "percent": g.percent}
                   for g in budget.active_goals(s)]
    salary_months = len(calc.salary_amounts(s.incomes))
    res = calc.rank_credits(amount, term_months, _products(), budget.basis(s), budget.monthly_obligations(s),
                            budget.goal_percents(s), goal_inputs, salary_months, budget.used_percent(s), linked)
    res["goal_id"] = goal_id
    return res


def apply(s: State, product_id: str, amount: int, months: int, confirm: bool) -> dict:
    """MOCK application: needs explicit confirmation, re-checks eligibility, records it. Moves no money."""
    if not confirm:
        raise CalcError(tr("err_need_confirm"))
    if product_id not in loan_products.BY_ID:
        raise KeyError(tr("err_credit_not_eligible"))
    res = advise(s, amount, months)
    p = next((o for o in res["options"] + [res["best"], res["lowest_payment"], res["fastest"], res["lowest_risk"]]
              if o and o["product_id"] == product_id and o["months"] == months), None)
    if p is None:
        # not in the shown top list: re-rank this product alone
        only = calc.rank_credits(amount, months, [x for x in _products() if x["id"] == product_id], budget.basis(s),
                                 budget.monthly_obligations(s), budget.goal_percents(s), [],
                                 len(calc.salary_amounts(s.incomes)), budget.used_percent(s))
        p = only["options"][0] if only["options"] else None
    if p is None:
        raise CalcError(tr("err_credit_not_eligible"))
    app = {"id": new_id("app"), "date": s.today.isoformat(), "product_id": product_id, "amount": amount,
           "months": months, "monthly_payment": p["monthly_payment"], "total_overpayment": p["total_overpayment"],
           "status": "demo_submitted"}
    s.credit_applications.append(app)
    return {**app, "name": p["name"],
            "message": tr("credit_applied", name=p["name"], amount_sum=amount, n_months=months)}


def applications_view(s: State) -> list[dict]:
    return [{**a, "name": render(loan_products.BY_ID[a["product_id"]]["names"])} for a in s.credit_applications]
