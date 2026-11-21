"""Proactive agent: agent_review() creates proposals; apply() executes them ONLY after confirmation.

(The prompt places agent_review in agent.py; it lives here so the LLM file stays small. agent.py re-exports it.)
"""
from __future__ import annotations

from datetime import timedelta

import calc
from calc import CalcError
from modules import budget, goals, guardian, obligations
from state import Proposal, State, new_id


def _days_word(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "дня"
    return "дней"


def _add(s: State, kind: str, key: str, title: str, text: str, options: list[dict], numbers: dict,
         origin: str = "agent") -> Proposal:
    for p in s.proposals.values():
        if p.condition_key == key and p.status == "pending":
            return p
    p = Proposal(id=new_id("prop"), kind=kind, title=title, text=text, options=options,
                 condition_key=key, numbers=numbers, origin=origin, created_at=s.clock)
    s.proposals[p.id] = p
    return p


def agent_review(s: State) -> None:
    """Idempotent. Creates missing proposals, resolves stale ones."""
    valid: set[str] = set()
    b = budget.basis(s)

    # 1. goal drift
    for g in budget.active_goals(s):
        f = goals.forecast(s, g)
        if f.remaining <= 0 or g.planned_months_left <= 0:
            continue
        shift = f.months_worst - g.planned_months_left
        if shift >= 1:
            sp = calc.suggest_percent(f.remaining, g.planned_months_left, budget.used_percent(s, g.id), b)
            if sp.percent == g.percent:
                continue
            key = f"drift:{g.id}:{f.months_worst}:{g.planned_months_left}"
            valid.add(key)
            if sp.feasible:
                text = (f"Доход стал ниже, и цель «{g.name}» сдвинулась на {shift} мес. "
                        f"Если откладывать {sp.percent}% вместо {g.percent}%, успеете в срок.")
            else:
                text = (f"Цель «{g.name}» сдвинулась на {shift} мес. Максимум, что можно отложить, — {sp.percent}%: "
                        f"тогда цель займёт {sp.months_worst} мес.")
            _add(s, "goal_percent", key, f"Цель «{g.name}» отстаёт", text,
                 [{"key": "apply", "label": f"Поставить {sp.percent}%",
                   "action": {"type": "set_percent", "params": {"goal_id": g.id, "percent": sp.percent}}}],
                 {"goal_id": g.id, "old_percent": g.percent, "new_percent": sp.percent,
                  "months_now": f.months_worst, "months_planned": g.planned_months_left,
                  "months_after": sp.months_worst, "months_best_after": sp.months_best,
                  "expiry_after": calc.add_months(s.today, sp.months_worst).isoformat(),
                  "contribution_after": calc.round_money(calc.monthly_contribution(sp.percent, b.worst))})

    # 2. obligation shortfall near due date
    for o in s.obligations.values():
        st = obligations.status(s, o)
        if o.paid or st.shortfall <= 0 or st.due_in_days > calc.DEADLINE_REMINDER_DAYS or st.due_in_days < 0:
            continue
        key = f"topup:{o.id}:{st.shortfall}"
        valid.add(key)
        amount = min(st.shortfall, s.main_balance)
        when = f"через {st.due_in_days} {_days_word(st.due_in_days)}" if st.due_in_days else "сегодня"
        text = f"Платёж «{o.name}» {when}. Не хватает {calc.fmt_uzs(st.shortfall)}."
        if amount < st.shortfall:
            text += f" С основной карты можно перевести только {calc.fmt_uzs(amount)}."
        _add(s, "obligation_topup", key, f"«{o.name}»: не хватает денег", text,
             [{"key": "apply", "label": f"Перевести {calc.fmt_uzs(amount)}",
               "action": {"type": "topup", "params": {"obligation_id": o.id, "amount": amount}}}],
             {"obligation_id": o.id, "shortfall": st.shortfall, "amount": amount, "due_in_days": st.due_in_days,
              "due_date": o.due_date.isoformat(), "main_balance": s.main_balance})

    # 3. cash gap
    cf = budget.cashflow(s)
    if cf.cash_gap and budget.active_goals(s):
        g = max(budget.active_goals(s), key=lambda x: goals.forecast(s, x).months_worst)
        new_pct = max(calc.MIN_PERCENT, g.percent - 5)
        if new_pct < g.percent:
            key = f"cashgap:{g.id}:{cf.free_to_spend}"
            valid.add(key)
            _add(s, "cash_gap", key, "До зарплаты может не хватить",
                 f"На жизнь до зарплаты нужно около {calc.fmt_uzs(cf.needed_until_payday)}, "
                 f"а свободно {calc.fmt_uzs(cf.free_to_spend)}. Можно временно уменьшить «{g.name}» "
                 f"с {g.percent}% до {new_pct}%.",
                 [{"key": "apply", "label": f"Уменьшить до {new_pct}%",
                   "action": {"type": "set_percent", "params": {"goal_id": g.id, "percent": new_pct}}}],
                 {"goal_id": g.id, "free_to_spend": cf.free_to_spend, "needed": cf.needed_until_payday})

    # 4. cooling-off finished
    for st in guardian.release_cooling(s):
        key = f"cool:{st.id}"
        valid.add(key)
        st.numbers["can_cover_from_main"] = budget.can_cover_from_main(s, st.amount)
        opts = [{"key": o["key"], "label": o["label"],
                 "action": {"type": "resolve_stop", "params": {"stop_id": st.id, "option": o["key"]}}}
                for o in guardian.options_for(st)]
        _add(s, "cooling_ready", key, "Прошли сутки",
             f"Покупка «{st.merchant}» на {calc.fmt_uzs(st.amount)} всё ещё нужна?", opts,
             {"stop_id": st.id, "amount": st.amount, "merchant": st.merchant})

    # resolve stale agent proposals
    for p in s.proposals.values():
        if p.origin == "agent" and p.status == "pending" and p.condition_key not in valid:
            p.status = "resolved"


def propose_goal(s: State, name: str, amount: int, percent: int) -> Proposal:
    pv = goals.preview(s, amount, percent)
    return _add(s, "create_goal", f"chat:{new_id('g')}", f"Новая цель «{name}»",
                f"Откладывать {percent}% дохода на «{name}» ({calc.fmt_uzs(amount)}).",
                [{"key": "apply", "label": "Создать цель",
                  "action": {"type": "create_goal", "params": {"name": name, "amount": amount, "percent": percent}}}],
                {"name": name, **pv}, origin="chat")


def propose_obligation(s: State, name: str, amount: int, due_date: str) -> Proposal:
    return _add(s, "create_obligation", f"chat:{new_id('o')}", f"Новый платёж «{name}»",
                f"Добавить обязательный платёж {calc.fmt_uzs(amount)} до {due_date}.",
                [{"key": "apply", "label": "Добавить платёж",
                  "action": {"type": "create_obligation",
                             "params": {"name": name, "amount": amount, "due_date": due_date}}}],
                {"name": name, "amount": amount, "due_date": due_date}, origin="chat")


def apply(s: State, proposal_id: str, option_key: str | None = None) -> dict:
    p = s.proposals.get(proposal_id)
    if not p:
        raise KeyError("Предложение не найдено")
    if p.status != "pending":
        raise CalcError("Это предложение уже обработано")
    opt = next((o for o in p.options if o["key"] == option_key), None) if option_key else p.options[0]
    if not opt:
        raise CalcError("Нет такого варианта")
    a = opt["action"]
    t, prm = a["type"], a["params"]
    if t == "set_percent":
        g = goals.set_percent(s, prm["goal_id"], prm["percent"])
        result = f"Готово: «{g.name}» — {g.percent}% дохода."
    elif t == "topup":
        moved = obligations.topup(s, prm["obligation_id"], prm["amount"])
        result = f"Переведено {calc.fmt_uzs(moved)} в резерв."
    elif t == "resolve_stop":
        result = guardian.resolve(s, prm["stop_id"], prm["option"], confirm=True)["message"]
    elif t == "create_goal":
        g = goals.create(s, prm["name"], prm["amount"], prm["percent"])
        result = f"Цель «{g.name}» создана."
    elif t == "create_obligation":
        from datetime import date
        o = obligations.create(s, prm["name"], prm["amount"], date.fromisoformat(prm["due_date"]))
        result = f"Платёж «{o.name}» добавлен."
    else:
        raise CalcError("Неизвестное действие")
    p.status, p.result = "confirmed", result
    agent_review(s)
    return {"status": "confirmed", "message": result}


def reject(s: State, proposal_id: str) -> dict:
    p = s.proposals.get(proposal_id)
    if not p:
        raise KeyError("Предложение не найдено")
    if p.status != "pending":
        raise CalcError("Это предложение уже обработано")
    p.status = "rejected"
    return {"status": "rejected"}


def view(p: Proposal) -> dict:
    return {"id": p.id, "kind": p.kind, "title": p.title, "text": p.text, "status": p.status,
            "origin": p.origin, "numbers": p.numbers, "result": p.result,
            "options": [{"key": o["key"], "label": o["label"]} for o in p.options],
            "created_at": p.created_at.isoformat() if p.created_at else None}


# ---- demo events ----
def salary(s: State, amount: int) -> dict:
    if amount <= 0 or amount > calc.MAX_AMOUNT:
        raise CalcError("Сумма зарплаты должна быть больше нуля")
    s.income_history = calc.roll_income(s.income_history, amount)
    # bonus for the past month, before new contributions
    for g in budget.active_goals(s):
        g.accrued_bonus += calc.monthly_bonus(g.saved, g.disciplined)
    left = amount
    flow = {"obligations": [], "goals": [], "main": 0}
    for o in sorted((o for o in s.obligations.values() if not o.paid), key=lambda x: x.due_date):
        put = min(max(0, o.amount - o.reserved), left)
        if put:
            o.reserved += put
            left -= put
            flow["obligations"].append({"id": o.id, "name": o.name, "amount": put})
    for g in budget.active_goals(s):
        put = min(calc.round_money(calc.monthly_contribution(g.percent, amount)), g.amount - g.saved, left)
        if put > 0:
            g.saved += put
            left -= put
            flow["goals"].append({"id": g.id, "name": g.name, "amount": put})
        g.planned_months_left = max(0, g.planned_months_left - 1)
        if g.saved >= g.amount:
            g.status = "completed"
    s.main_balance += left
    flow["main"] = left
    s.add_tx("Зарплата", amount)
    s.next_income_date = s.today + timedelta(days=calc.PAYDAY_INTERVAL_DAYS)
    agent_review(s)
    return flow


def skip_time(s: State, hours: int) -> None:
    s.clock += timedelta(hours=hours)
    goals.finish_closures(s)
    agent_review(s)
