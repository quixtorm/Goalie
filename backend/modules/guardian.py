"""Anti-Impulse Guardian. Category comes ONLY from MCC (mcc.classify)."""
from __future__ import annotations

from datetime import timedelta

import calc
import mcc as mcc_mod
from calc import CalcError
from mcc import Category
from modules import budget, goals, obligations
from state import State, Stop, new_id
from texts import disp, msg, tr


def _source(s: State, source_id: str):
    if source_id in s.goals:
        g = s.goals[source_id]
        if g.status != "active" and g.status != "completed":
            raise CalcError(tr("err_goal_unavailable"))
        return "goal", g
    if source_id in s.obligations:
        return "obligation", s.obligations[source_id]
    raise KeyError(tr("err_source_not_found"))


def _available(kind: str, src) -> int:
    return src.saved if kind == "goal" else src.reserved


def _purchase_title(mcc: str, merchant: str) -> dict:
    return msg("tx_purchase", label=mcc_mod.labels(mcc), merchant=merchant)


def spend(s: State, source_id: str, amount: int, mcc: str, merchant: str, note: str = "") -> dict:
    kind, src = _source(s, source_id)
    if amount <= 0:
        raise CalcError(tr("err_amount_positive"))
    if amount > _available(kind, src):
        raise CalcError(tr("err_only_in", name=disp(src), avail_sum=_available(kind, src)))
    cat = mcc_mod.classify(mcc)  # note/merchant deliberately ignored
    label = mcc_mod.label(mcc)

    if cat == Category.EMERGENCY:
        _withdraw(s, kind, src, amount, _purchase_title(mcc, merchant), mcc, penalty=False)
        out = {"outcome": "released", "category": cat.value, "source_name": disp(src), "amount": amount,
               "merchant": merchant, "label": label}
        if kind == "goal":
            f = goals.forecast(s, src)
            out.update(months_worst=f.months_worst, expiry=f.expiry.isoformat(), rate=calc.rate_for(src.disciplined),
                       saved=src.saved)
        return out

    if cat == Category.OBLIGATION and kind == "obligation":
        _withdraw(s, kind, src, amount, _purchase_title(mcc, merchant), mcc, penalty=False)
        return {"outcome": "released", "category": cat.value, "source_name": disp(src), "amount": amount,
                "merchant": merchant, "label": label}

    # IMPULSE / UNKNOWN (and obligation-type MCC paid from a goal) -> stop
    stop = Stop(id=new_id("stop"), source_id=source_id, source_kind=kind, amount=amount, mcc=mcc,
                merchant=merchant, note=note, category=cat.value)
    numbers = {"amount": amount, "merchant": merchant,
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
    return {"outcome": outcome, "category": cat.value, "stop_id": stop.id, **stop_view(s, stop)}


def stop_view(s: State, stop: Stop) -> dict:
    """Stop numbers + labels in the current language."""
    _, src = _source(s, stop.source_id)
    return {**stop.numbers, "label": mcc_mod.label(stop.mcc), "source_name": disp(src), "status": stop.status,
            "options": options_for(stop)}


_LABEL = {"cover_from_main": "g_cover", "cooling": "g_cool", "proceed": "g_proceed"}


def options_for(stop: Stop, stored: bool = False) -> list[dict]:
    """stored=True returns msg() labels (for proposals rendered later); otherwise text in the current language."""
    lab = (lambda k: msg(k)) if stored else (lambda k: tr(k))
    opts = []
    if stop.numbers.get("can_cover_from_main"):
        opts.append({"key": "cover_from_main", "label": lab("g_cover")})
    if stop.status == "open" and stop.source_kind == "goal":
        opts.append({"key": "cooling", "label": lab("g_cool")})
    if stop.status == "cooling":
        opts.insert(0, {"key": "decline", "label": lab("g_no_need")})
    opts.append({"key": "proceed", "label": lab("g_proceed"), "needs_confirm": stop.source_kind == "obligation"})
    if stop.status == "open":
        opts.append({"key": "decline", "label": lab("g_decline")})
    return opts


def _withdraw(s: State, kind: str, src, amount: int, title, mcc: str, penalty: bool) -> None:
    if kind == "goal":
        src.saved -= amount
        if penalty:
            src.disciplined = False
    else:
        src.reserved -= amount
    s.add_tx(title, -amount, source=src.id, mcc=mcc)


def resolve(s: State, stop_id: str, option: str, confirm: bool = False) -> dict:
    stop = s.stops.get(stop_id)
    if not stop:
        raise KeyError(tr("err_purchase_not_found"))
    if stop.status == "resolved":
        raise CalcError(tr("err_already_resolved"))
    valid = {o["key"] for o in options_for(stop)}
    # re-check main card at resolve time
    if option == "cover_from_main" and not budget.can_cover_from_main(s, stop.amount):
        raise CalcError(tr("err_main_not_enough"))
    if option not in valid and option != "cover_from_main":
        raise CalcError(tr("err_option_unavailable"))
    kind, src = _source(s, stop.source_id)

    if option == "cover_from_main":
        s.main_balance -= stop.amount
        s.add_tx(_purchase_title(stop.mcc, stop.merchant), -stop.amount, mcc=stop.mcc)
        text = tr("gm_covered", name=disp(src))
    elif option == "cooling":
        stop.status = "cooling"
        stop.ready_at = s.clock + timedelta(hours=calc.COOLDOWN_HOURS)
        return {"status": "cooling", "ready_at": stop.ready_at.isoformat(), "message": tr("gm_cooling")}
    elif option == "proceed":
        if kind == "obligation" and not confirm:
            raise CalcError(tr("err_need_confirm_obl"))
        if stop.amount > _available(kind, src):
            raise CalcError(tr("err_money_insufficient"))
        _withdraw(s, kind, src, stop.amount, _purchase_title(stop.mcc, stop.merchant), stop.mcc, penalty=True)
        text = (tr("gm_spent_goal", name=disp(src), rate=calc.BASE_RATE) if kind == "goal"
                else tr("gm_spent_obl", name=disp(src)))
    else:  # decline
        text = tr("gm_declined")
    stop.status, stop.resolution = "resolved", option
    return {"status": "resolved", "resolution": option, "message": text}


def release_cooling(s: State) -> list[Stop]:
    return [st for st in s.stops.values() if st.status == "cooling" and st.ready_at and s.clock >= st.ready_at]
