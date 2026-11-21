"""All formulas and constants. Pure, typed, deterministic. No LLM, no state.

Numeric rules:
- money is int so'm, percent is int
- intermediate math uses Fraction; ceil is applied to exact rationals
- money results rounded half-up once, at the end (round_money)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction
from math import ceil

from texts import tr

# ---- constants (tunable, nowhere else) ----
MAX_SUBCARDS = 3
MAX_TOTAL_PERCENT = 40
MIN_PERCENT = 1
COOLDOWN_HOURS = 24
BASE_RATE = 12          # annual %
DISCIPLINE_RATE = 22    # annual %
DTI_THRESHOLD = Fraction(40, 100)
DEADLINE_REMINDER_DAYS = 5
INCOME_HISTORY_MONTHS = 6
DAILY_SPEND_BASELINE = 120_000
PAYDAY_INTERVAL_DAYS = 30
MAX_AMOUNT = 1_000_000_000_000
MAX_MONTHS = 120


class CalcError(ValueError):
    """Validation error with a user-facing Russian message."""


# ---- helpers ----
def round_money(x: Fraction | int) -> int:
    """Round half up to whole so'm."""
    x = Fraction(x)
    if x >= 0:
        return int(x + Fraction(1, 2))
    return -int(-x + Fraction(1, 2))


def fmt_uzs(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}{abs(int(amount)):,}".replace(",", " ") + " so'm"


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    # clamp day to month length
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise AssertionError("unreachable")


def ceil_frac(x: Fraction) -> int:
    return -((-x.numerator) // x.denominator)


# ---- income ----
@dataclass(frozen=True)
class IncomeBasis:
    worst: int
    avg: Fraction


def income_basis(history: list[int], fallback_income: int | None = None) -> IncomeBasis:
    recent = history[-INCOME_HISTORY_MONTHS:]
    if not recent:
        if not fallback_income or fallback_income <= 0:
            raise CalcError(tr("err_income_needed"))
        return IncomeBasis(fallback_income, Fraction(fallback_income))
    return IncomeBasis(min(recent), Fraction(sum(recent), len(recent)))


def roll_income(history: list[int], salary: int) -> list[int]:
    return (history + [salary])[-INCOME_HISTORY_MONTHS:]


# ---- income types: ONLY salary counts for planning ----
SALARY, TRANSFER, OTHER = "SALARY", "TRANSFER", "OTHER"
INCOME_TYPES = (SALARY, TRANSFER, OTHER)
ANNUAL_WINDOW_MONTHS = 12


def salary_amounts(records: list[dict]) -> list[int]:
    """Salary amounts in date order. Transfers from family and other inflows are excluded on purpose:
    they are irregular, so a plan built on them could break."""
    return [r["amount"] for r in sorted(records, key=lambda r: r["date"]) if r["type"] == SALARY]


def basis_from_records(records: list[dict], fallback_income: int | None = None) -> IncomeBasis:
    """worst/avg MONTHLY income over the last INCOME_HISTORY_MONTHS salaries (salary only)."""
    return income_basis(salary_amounts(records), fallback_income)


def worst_monthly_income(records: list[dict]) -> int:
    return basis_from_records(records).worst


def avg_monthly_income(records: list[dict]) -> int:
    return round_money(basis_from_records(records).avg)


def worst_annual_income(records: list[dict]) -> int:
    """Conservative yearly salary we plan on: worst month x 12 (salary only)."""
    return worst_monthly_income(records) * 12


def income_by_type(records: list[dict], today: date, months: int = ANNUAL_WINDOW_MONTHS) -> dict:
    """Totals and counts per income type for the last `months` months (for display / the agent)."""
    since = add_months(today, -months).isoformat()
    out = {t: {"total": 0, "count": 0} for t in INCOME_TYPES}
    for r in records:
        if r["date"] >= since and r["type"] in out:  # window includes its first day
            out[r["type"]]["total"] += r["amount"]
            out[r["type"]]["count"] += 1
    return {"months": months, "planning_basis": SALARY, "by_type": out}


def transfer_save_suggestion(transfer: int, goal_percent: int, goal_remaining: int, main_balance: int) -> int:
    """Optional extra saving from a transfer: the goal's own percent of the transfer,
    capped by what the goal still needs and by what is on the main card."""
    if transfer <= 0 or goal_remaining <= 0:
        return 0
    return max(0, min(round_money(Fraction(transfer * goal_percent, 100)), goal_remaining, main_balance))


# ---- goals ----
def monthly_contribution(percent: int, income: Fraction | int) -> Fraction:
    return Fraction(percent, 100) * Fraction(income)


def months_needed(remaining: int, percent: int, income: Fraction | int) -> int:
    if remaining <= 0:
        return 0
    contrib = monthly_contribution(percent, income)
    if contrib <= 0:
        raise CalcError(tr("err_income_positive"))
    return ceil_frac(Fraction(remaining) / contrib)


@dataclass(frozen=True)
class GoalForecast:
    remaining: int
    months_worst: int
    months_best: int
    expiry: date
    contribution_worst: int
    contribution_avg: int


def goal_forecast(goal_amount: int, saved: int, percent: int, basis: IncomeBasis, today: date) -> GoalForecast:
    remaining = max(0, goal_amount - saved)
    mw = months_needed(remaining, percent, basis.worst)
    mb = months_needed(remaining, percent, basis.avg)
    return GoalForecast(
        remaining=remaining,
        months_worst=mw,
        months_best=mb,
        expiry=add_months(today, mw),
        contribution_worst=round_money(monthly_contribution(percent, basis.worst)),
        contribution_avg=round_money(monthly_contribution(percent, basis.avg)),
    )


@dataclass(frozen=True)
class PercentSuggestion:
    percent: int
    raw_percent: int
    feasible: bool
    months_worst: int
    months_best: int
    cap: int


def suggest_percent(remaining: int, target_months: int, used_percent: int, basis: IncomeBasis) -> PercentSuggestion:
    if target_months < 1 or target_months > MAX_MONTHS:
        raise CalcError(tr("err_term", max=MAX_MONTHS))
    cap = MAX_TOTAL_PERCENT - used_percent
    if cap < MIN_PERCENT:
        raise CalcError(tr("err_total_pct", max=MAX_TOTAL_PERCENT))
    raw = ceil_frac(Fraction(remaining) / (target_months * basis.worst) * 100) if remaining > 0 else MIN_PERCENT
    pct = min(max(raw, MIN_PERCENT), cap)
    return PercentSuggestion(
        percent=pct,
        raw_percent=raw,
        feasible=raw <= cap,
        months_worst=months_needed(remaining, pct, basis.worst),
        months_best=months_needed(remaining, pct, basis.avg),
        cap=cap,
    )


def validate_new_goal(existing_count: int, percent: int, used_percent: int, amount: int) -> None:
    if existing_count >= MAX_SUBCARDS:
        raise CalcError(tr("err_max_goals", max=MAX_SUBCARDS))
    if amount <= 0 or amount > MAX_AMOUNT:
        raise CalcError(tr("err_goal_amount"))
    if percent < MIN_PERCENT:
        raise CalcError(tr("err_min_pct", min=MIN_PERCENT))
    if used_percent + percent > MAX_TOTAL_PERCENT:
        raise CalcError(tr("err_total_pct", max=MAX_TOTAL_PERCENT))


# ---- bonus ----
def rate_for(disciplined: bool) -> int:
    return DISCIPLINE_RATE if disciplined else BASE_RATE


def monthly_bonus(saved: int, disciplined: bool) -> int:
    return round_money(Fraction(saved) * Fraction(rate_for(disciplined), 1200))


def projected_bonus(saved: int, contribution: Fraction, goal_amount: int, months: int, rate: int) -> Fraction:
    total, bal = Fraction(0), Fraction(saved)
    for _ in range(months):
        bal = min(bal + contribution, Fraction(goal_amount))
        total += bal * Fraction(rate, 1200)
    return total


@dataclass(frozen=True)
class BreachCost:
    delay_days: int
    bonus_lost: int
    new_months_worst: int
    new_expiry: date


def breach_cost(goal_amount: int, saved: int, percent: int, amount: int, basis: IncomeBasis, today: date) -> BreachCost:
    contrib = monthly_contribution(percent, basis.worst)
    delay = round_money(Fraction(amount) / contrib * 30) if amount > 0 else 0
    if amount > 0:
        delay = max(1, delay)
    remaining = max(0, goal_amount - saved)
    mw = months_needed(remaining, percent, basis.worst)
    lost = projected_bonus(saved, contrib, goal_amount, mw, DISCIPLINE_RATE) - projected_bonus(
        saved, contrib, goal_amount, mw, BASE_RATE
    )
    new_mw = months_needed(remaining + amount, percent, basis.worst)
    return BreachCost(delay, round_money(lost), new_mw, add_months(today, new_mw))


# ---- credit ----
@dataclass(frozen=True)
class CreditResult:
    payment: int
    overpayment: int
    dti_percent: int
    dti_risk: bool
    free_money: int
    cashflow_risk: bool
    risk: bool


def annuity_payment(amount: int, annual_rate: Fraction | int, months: int) -> Fraction:
    if months < 1 or months > MAX_MONTHS:
        raise CalcError(tr("err_term", max=MAX_MONTHS))
    if amount <= 0 or amount > MAX_AMOUNT:
        raise CalcError(tr("err_credit_amount"))
    r = Fraction(annual_rate) / 1200
    if r == 0:
        return Fraction(amount, months)
    if r < 0:
        raise CalcError(tr("err_rate_negative"))
    return Fraction(amount) * r / (1 - 1 / (1 + r) ** months)


def free_money(basis: IncomeBasis, monthly_obligations: int, goal_percents: list[int]) -> Fraction:
    return Fraction(basis.worst) - monthly_obligations - sum(monthly_contribution(p, basis.worst) for p in goal_percents)


def calc_credit(amount: int, annual_rate: Fraction | int, months: int, basis: IncomeBasis,
                monthly_obligations: int, goal_percents: list[int]) -> CreditResult:
    pay = annuity_payment(amount, annual_rate, months)
    dti = pay / basis.worst
    free = free_money(basis, monthly_obligations, goal_percents)
    dti_risk = dti > DTI_THRESHOLD
    cash_risk = pay > free
    return CreditResult(
        payment=round_money(pay),
        overpayment=round_money(pay * months - amount),
        dti_percent=round_money(dti * 100),
        dti_risk=dti_risk,
        free_money=round_money(free),
        cashflow_risk=cash_risk,
        risk=dti_risk or cash_risk,
    )


@dataclass(frozen=True)
class GoalImpact:
    goal_id: str
    name: str
    months_before: int
    months_after: int | None  # None = never reachable
    delay_months: int | None


def credit_impact_on_goals(payment: int, goals: list[dict], basis: IncomeBasis) -> list[GoalImpact]:
    """goals: dicts with id, name, amount, saved, percent."""
    eff = basis.worst - payment
    out = []
    for g in goals:
        remaining = max(0, g["amount"] - g["saved"])
        before = months_needed(remaining, g["percent"], basis.worst)
        if eff <= 0:
            out.append(GoalImpact(g["id"], g["name"], before, None, None))
            continue
        after = months_needed(remaining, g["percent"], eff)
        out.append(GoalImpact(g["id"], g["name"], before, after, after - before))
    return out


# ---- cashflow / obligations ----
@dataclass(frozen=True)
class Cashflow:
    free_money: int
    days_until_next_income: int
    needed_until_payday: int
    free_to_spend: int
    cash_gap: bool


def cashflow_check(basis: IncomeBasis, monthly_obligations: int, goal_percents: list[int], main_balance: int,
                   shortfalls_before_payday: int, today: date, next_income: date) -> Cashflow:
    days = max(0, (next_income - today).days)
    needed = DAILY_SPEND_BASELINE * days
    fts = main_balance - shortfalls_before_payday
    return Cashflow(
        free_money=round_money(free_money(basis, monthly_obligations, goal_percents)),
        days_until_next_income=days,
        needed_until_payday=needed,
        free_to_spend=fts,
        cash_gap=fts < needed,
    )


@dataclass(frozen=True)
class ObligationStatus:
    reserved: int
    due_in_days: int
    shortfall: int
    status: str  # ok | soon | shortfall | overdue | paid


def obligation_status(amount: int, reserved: int, due: date, today: date, paid: bool) -> ObligationStatus:
    due_in = (due - today).days
    short = max(0, amount - reserved)
    if paid:
        st = "paid"
    elif due_in < 0:
        st = "overdue"
    elif short > 0 and due_in <= DEADLINE_REMINDER_DAYS:
        st = "shortfall"
    elif short > 0:
        st = "soon"
    else:
        st = "ok"
    return ObligationStatus(reserved, due_in, short, st)
