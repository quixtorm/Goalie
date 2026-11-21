"""Obligations module ("Щит"): status, reserve top-ups, payment."""
from __future__ import annotations

from datetime import date

import calc
from calc import CalcError
from state import Obligation, State, new_id
from texts import disp, loc, msg, tr


def status(s: State, o: Obligation) -> calc.ObligationStatus:
    return calc.obligation_status(o.amount, o.reserved, o.due_date, s.today, o.paid)


def view(s: State, o: Obligation) -> dict:
    st = status(s, o)
    return {
        "id": o.id, "name": disp(o), "amount": o.amount, "due_date": o.due_date.isoformat(),
        "reserved": o.reserved, "shortfall": st.shortfall, "due_in_days": st.due_in_days,
        "status": st.status, "paid": o.paid, "monthly": o.monthly,
    }


def get(s: State, obl_id: str) -> Obligation:
    o = s.obligations.get(obl_id)
    if not o:
        raise KeyError(tr("err_obl_not_found"))
    return o


def create(s: State, name: str, amount: int, due_date: date, monthly: bool = False) -> Obligation:
    if amount <= 0 or amount > calc.MAX_AMOUNT:
        raise CalcError(tr("err_amount_positive"))
    if due_date < s.today:
        raise CalcError(tr("err_date_past"))
    o = Obligation(id=new_id("obl"), name=name, amount=amount, due_date=due_date, monthly=monthly)
    s.obligations[o.id] = o
    return o


def topup(s: State, obl_id: str, amount: int) -> int:
    o = get(s, obl_id)
    amount = min(amount, max(0, o.amount - o.reserved), s.main_balance)
    if amount <= 0:
        raise CalcError(tr("err_topup"))
    s.main_balance -= amount
    o.reserved += amount
    s.add_tx(msg("tx_reserve", name=loc(o)), -amount, internal=True)
    return amount


def pay(s: State, obl_id: str) -> dict:
    o = get(s, obl_id)
    if o.paid:
        raise CalcError(tr("err_already_paid"))
    short = max(0, o.amount - o.reserved)
    if short > s.main_balance:
        raise CalcError(tr("err_not_enough", short_sum=short - s.main_balance))
    s.main_balance -= short
    o.reserved = 0
    o.paid = True
    s.add_tx(msg("tx_pay", name=loc(o)), -o.amount, source="shield")
    if o.monthly:
        nxt = Obligation(id=new_id("obl"), name=o.name, names=o.names, amount=o.amount,
                         due_date=calc.add_months(o.due_date, 1), monthly=True)
        s.obligations[nxt.id] = nxt
    return {"paid": o.amount, "from_main": short}
