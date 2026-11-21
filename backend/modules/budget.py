"""Budget module: income basis, cashflow, free money. Thin wrappers over calc.py."""
from __future__ import annotations

import calc
from state import State


def basis(s: State) -> calc.IncomeBasis:
    return calc.income_basis(s.income_history)


def active_goals(s: State):
    return [g for g in s.goals.values() if g.status == "active"]


def goal_percents(s: State, exclude: str | None = None) -> list[int]:
    return [g.percent for g in active_goals(s) if g.id != exclude]


def used_percent(s: State, exclude: str | None = None) -> int:
    return sum(goal_percents(s, exclude))


def monthly_obligations(s: State) -> int:
    return sum(o.amount for o in s.obligations.values() if o.monthly)


def shortfalls_before_payday(s: State) -> int:
    return sum(
        max(0, o.amount - o.reserved)
        for o in s.obligations.values()
        if not o.paid and o.due_date <= s.next_income_date
    )


def cashflow(s: State) -> calc.Cashflow:
    nxt = s.next_income_date if s.next_income_date > s.today else s.today
    return calc.cashflow_check(
        basis(s), monthly_obligations(s), goal_percents(s), s.main_balance,
        shortfalls_before_payday(s), s.today, nxt,
    )


def can_cover_from_main(s: State, amount: int) -> bool:
    cf = cashflow(s)
    return cf.free_to_spend - amount >= cf.needed_until_payday


def cashflow_view(s: State) -> dict:
    cf = cashflow(s)
    return {
        "free_money_monthly": cf.free_money,
        "days_until_next_income": cf.days_until_next_income,
        "needed_until_payday": cf.needed_until_payday,
        "free_to_spend": cf.free_to_spend,
        "cash_gap": cf.cash_gap,
        "main_balance": s.main_balance,
    }
