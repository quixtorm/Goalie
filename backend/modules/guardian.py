"""Anti-Impulse Guardian. Category comes ONLY from MCC (mcc.classify)."""
from __future__ import annotations

from datetime import timedelta

import calc
import mcc as mcc_mod
from calc import CalcError
from mcc import Category
from modules import budget, goals, obligations
from state import State, Stop, new_id


def _source(s: State, source_id: str):
    if source_id in s.goals:
        g = s.goals[source_id]
        if g.status != "active" and g.status != "completed":
            raise CalcError("Эта цель сейчас недоступна")
        return "goal", g
    if source_id in s.obligations:
        return "obligation", s.obligations[source_id]
    raise KeyError("Источник не найден")


def _available(kind: str, src) -> int:
    return src.saved if kind == "goal" else src.reserved


def spend(s: State, source_id: str, amount: int, mcc: str, merchant: str, note: str = "") -> dict:
    kind, src = _source(s, source_id)
    if amount <= 0:
        raise CalcError("Сумма должна быть больше нуля")
    if amount > _available(kind, src):
        raise CalcError(f"В «{src.name}» только {calc.fmt_uzs(_available(kind, src))}")
    cat = mcc_mod.classify(mcc)  # note/merchant deliberately ignored
    label = mcc_mod.label(mcc)

    if cat == Category.EMERGENCY:
        _withdraw(s, kind, src, amount, f"{label}: {merchant}", mcc, penalty=False)
        out = {"outcome": "released", "category": cat.value, "source_name": src.name, "amount": amount,
               "merchant": merchant, "label": label}
        if kind == "goal":
            f = goals.forecast(s, src)
            out.update(months_worst=f.months_worst, expiry=f.expiry.isoformat(), rate=calc.rate_for(src.disciplined),
                       saved=src.saved)
        return out

    if cat == Category.OBLIGATION and kind == "obligation":
        _withdraw(s, kind, src, amount, f"{label}: {merchant}", mcc, penalty=False)
        return {"outcome": "released", "category": cat.value, "source_name": src.name, "amount": amount,
                "merchant": merchant, "label": label}

    # IMPULSE / UNKNOWN (and obligation-type MCC paid from a goal) -> stop
    stop = Stop(id=new_id("stop"), source_id=source_id, source_kind=kind, amount=amount, mcc=mcc,
                merchant=merchant, note=note, category=cat.value)
    numbers = {"amount": amount, "merchant": merchant, "label": label, "source_name": src.name,
               "can_cover_from_main": budget.can_cover_from_main(s, amount), "main_balance": s.main_balance}
    if kind == "goal":
        bc = calc.breach_cost(src.amount, src.saved, src.percent, amount, budget.basis(s), s.today)
        numbers.update(delay_days=bc.delay_days, bonus_lost=bc.bonus_lost if src.disciplined else 0,
                       new_months_worst=bc.new_months_worst, new_expiry=bc.new_expiry.isoformat(),
                       disciplined=src.disciplined)
        outcome = "stopped"
    else:
        st = obligations.status(s, src)
        numbers.update(due_date=src.due_date.isoformat(), due_in_days=st.due_in_days,
                       shortfall_after=max(0, src.amount - (src.reserved - amount)))
        outcome = "stopped_obligation"
    stop.numbers = numbers
    s.stops[stop.id] = stop
    return {"outcome": outcome, "category": cat.value, "stop_id": stop.id, **numbers,
            "options": options_for(stop)}


def options_for(stop: Stop) -> list[dict]:
    opts = []
    if stop.numbers.get("can_cover_from_main"):
        opts.append({"key": "cover_from_main", "label": "Оплатить с основной карты"})
    if stop.status == "open" and stop.source_kind == "goal":
        opts.append({"key": "cooling", "label": "Подождать до завтра"})
    if stop.status == "cooling":
        opts.insert(0, {"key": "decline", "label": "Уже не нужно"})
    opts.append({"key": "proceed", "label": "Всё равно потратить", "needs_confirm": stop.source_kind == "obligation"})
    if stop.status == "open":
        opts.append({"key": "decline", "label": "Отказаться"})
    return opts


def _withdraw(s: State, kind: str, src, amount: int, title: str, mcc: str, penalty: bool) -> None:
    if kind == "goal":
        src.saved -= amount
        if penalty:
            src.disciplined = False
        s.add_tx(title, -amount, source=src.id, mcc=mcc)
    else:
        src.reserved -= amount
        s.add_tx(title, -amount, source=src.id, mcc=mcc)


def resolve(s: State, stop_id: str, option: str, confirm: bool = False) -> dict:
    stop = s.stops.get(stop_id)
    if not stop:
        raise KeyError("Покупка не найдена")
    if stop.status == "resolved":
        raise CalcError("Уже решено")
    valid = {o["key"] for o in options_for(stop)}
    # re-check main card at resolve time
    if option == "cover_from_main" and not budget.can_cover_from_main(s, stop.amount):
        raise CalcError("На основной карте не хватит денег до зарплаты")
    if option not in valid and option != "cover_from_main":
        raise CalcError("Этот вариант сейчас недоступен")
    kind, src = _source(s, stop.source_id)

    if option == "cover_from_main":
        s.main_balance -= stop.amount
        s.add_tx(f"{stop.numbers['label']}: {stop.merchant}", -stop.amount, mcc=stop.mcc)
        msg = f"Оплачено с основной карты. «{src.name}» не тронута."
    elif option == "cooling":
        stop.status = "cooling"
        stop.ready_at = s.clock + timedelta(hours=calc.COOLDOWN_HOURS)
        return {"status": "cooling", "ready_at": stop.ready_at.isoformat(),
                "message": "Хорошо, вернёмся к этому завтра. Если желание останется — решим вместе."}
    elif option == "proceed":
        if kind == "obligation" and not confirm:
            raise CalcError("Нужно подтверждение: это деньги на обязательный платёж")
        if stop.amount > _available(kind, src):
            raise CalcError("Денег уже недостаточно")
        _withdraw(s, kind, src, stop.amount, f"{stop.numbers['label']}: {stop.merchant}", stop.mcc, penalty=True)
        msg = (f"Потрачено из «{src.name}». Бонус теперь {calc.BASE_RATE}% годовых."
               if kind == "goal" else f"Потрачено из резерва «{src.name}».")
    else:  # decline
        msg = "Покупка отменена. Деньги остались на месте."
    stop.status, stop.resolution = "resolved", option
    return {"status": "resolved", "resolution": option, "message": msg}


def release_cooling(s: State) -> list[Stop]:
    return [st for st in s.stops.values() if st.status == "cooling" and st.ready_at and s.clock >= st.ready_at]
