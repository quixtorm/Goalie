"""Goals module: forecasts, creation, use, early close, credit impact."""
from __future__ import annotations

from datetime import timedelta

import calc
from calc import CalcError
from modules import budget
from state import Goal, State, new_id


def forecast(s: State, g: Goal) -> calc.GoalForecast:
    return calc.goal_forecast(g.amount, g.saved, g.percent, budget.basis(s), s.today)


def view(s: State, g: Goal) -> dict:
    f = forecast(s, g)
    return {
        "id": g.id, "name": g.name, "amount": g.amount, "saved": g.saved, "percent": g.percent,
        "priority": g.priority,
        "progress": min(100, round(g.saved * 100 / g.amount)) if g.amount else 0,
        "remaining": f.remaining, "months_worst": f.months_worst, "months_best": f.months_best,
        "expiry": f.expiry.isoformat(), "contribution_worst": f.contribution_worst,
        "contribution_avg": f.contribution_avg, "disciplined": g.disciplined,
        "rate": calc.rate_for(g.disciplined), "accrued_bonus": g.accrued_bonus,
        "status": g.status, "can_use": g.saved >= g.amount and g.status in ("active", "completed"),
        "planned_months_left": g.planned_months_left,
        "close_ready_at": g.close_ready_at.isoformat() if g.close_ready_at else None,
    }


def preview(s: State, amount: int, percent: int, saved: int = 0, exclude: str | None = None) -> dict:
    count = len([g for g in budget.active_goals(s) if g.id != exclude])
    calc.validate_new_goal(count, percent, budget.used_percent(s, exclude), amount)
    f = calc.goal_forecast(amount, saved, percent, budget.basis(s), s.today)
    return {
        "amount": amount, "percent": percent, "months_worst": f.months_worst, "months_best": f.months_best,
        "expiry": f.expiry.isoformat(), "contribution_worst": f.contribution_worst,
        "contribution_avg": f.contribution_avg,
    }


def suggest(s: State, amount: int, months: int, exclude: str | None = None) -> dict:
    sp = calc.suggest_percent(amount, months, budget.used_percent(s, exclude), budget.basis(s))
    b = budget.basis(s)
    out = {
        "amount": amount, "target_months": months, "percent": sp.percent, "feasible": sp.feasible,
        "raw_percent": sp.raw_percent, "cap_percent": sp.cap, "months_worst": sp.months_worst,
        "months_best": sp.months_best,
        "expiry": calc.add_months(s.today, sp.months_worst).isoformat(),
        "contribution_worst": calc.round_money(calc.monthly_contribution(sp.percent, b.worst)),
        "used_percent": budget.used_percent(s, exclude),
    }
    return out


def create(s: State, name: str, amount: int, percent: int) -> Goal:
    calc.validate_new_goal(len(budget.active_goals(s)), percent, budget.used_percent(s), amount)
    mw = calc.months_needed(amount, percent, budget.basis(s).worst)
    g = Goal(id=new_id("goal"), name=name, amount=amount, saved=0, percent=percent, planned_months_left=mw,
             priority=len(budget.active_goals(s)) + 1)
    s.goals[g.id] = g
    budget.renumber(s)
    return g


def reorder(s: State, ids: list[str]) -> list[Goal]:
    """ids = active goal ids from highest to lowest priority. Must list each active goal exactly once."""
    active = {g.id for g in budget.active_goals(s)}
    if len(ids) != len(set(ids)) or set(ids) != active:
        raise CalcError("Список целей не совпадает с активными целями")
    for i, gid in enumerate(ids, start=1):
        s.goals[gid].priority = i
    return budget.active_goals(s)


def set_percent(s: State, goal_id: str, percent: int) -> Goal:
    g = get(s, goal_id)
    if percent < calc.MIN_PERCENT or budget.used_percent(s, g.id) + percent > calc.MAX_TOTAL_PERCENT:
        raise CalcError(f"Сумма процентов по целям не может быть больше {calc.MAX_TOTAL_PERCENT}%")
    g.percent = percent
    g.planned_months_left = forecast(s, g).months_worst
    return g


def get(s: State, goal_id: str) -> Goal:
    g = s.goals.get(goal_id)
    if not g:
        raise KeyError("Цель не найдена")
    return g


def use(s: State, goal_id: str) -> dict:
    g = get(s, goal_id)
    if g.status not in ("active", "completed") or g.saved < g.amount:
        raise CalcError("Цель ещё не накоплена")
    payout = g.saved + g.accrued_bonus
    s.main_balance += payout
    s.add_tx(f"Цель «{g.name}» достигнута (с бонусом {calc.fmt_uzs(g.accrued_bonus)})", payout)
    g.saved, g.status = 0, "used"
    budget.renumber(s)
    return {"payout": payout, "bonus": g.accrued_bonus}


def start_close(s: State, goal_id: str) -> dict:
    g = get(s, goal_id)
    if g.status != "active":
        raise CalcError("Эту цель нельзя закрыть")
    g.status = "closing"
    g.close_ready_at = s.clock + timedelta(hours=calc.COOLDOWN_HOURS)
    lost = g.accrued_bonus
    budget.renumber(s)
    return {"returns": g.saved, "bonus_lost": lost, "ready_at": g.close_ready_at.isoformat()}


def finish_closures(s: State) -> None:
    for g in s.goals.values():
        if g.status == "closing" and g.close_ready_at and s.clock >= g.close_ready_at:
            s.main_balance += g.saved
            s.add_tx(f"Цель «{g.name}» закрыта, деньги вернулись", g.saved)
            g.saved, g.accrued_bonus, g.status = 0, 0, "closed"
    budget.renumber(s)


def credit_impact(s: State, payment: int) -> list[dict]:
    goals = [{"id": g.id, "name": g.name, "amount": g.amount, "saved": g.saved, "percent": g.percent}
             for g in budget.active_goals(s)]
    return [i.__dict__ for i in calc.credit_impact_on_goals(payment, goals, budget.basis(s))]
