"""Deterministic agent (no LLM). Runs the whole demo on its own.

Uses the SAME module functions as the LLM tools, so numbers are identical in both modes.
"""
from __future__ import annotations

import re
from fractions import Fraction

import calc
from calc import CalcError
from modules import budget, goals, obligations, proposals
from state import State
from texts import tr

UNITS = {"млрд": 10**9, "миллиард": 10**9, "млн": 10**6, "миллион": 10**6, "тыс": 10**3, "k": 10**3, "к": 10**3,
         "mlrd": 10**9, "milliard": 10**9, "mln": 10**6, "million": 10**6, "ming": 10**3}

GOAL_NAMES = [
    ("машин", "Машина"), ("авто", "Машина"), ("телефон", "Телефон"), ("айфон", "Телефон"),
    ("квартир", "Квартира"), ("дом", "Дом"), ("отпуск", "Отпуск"), ("путешеств", "Путешествие"),
    ("свадьб", "Свадьба"), ("учеб", "Учёба"), ("учёб", "Учёба"), ("контракт", "Учёба"),
    ("ноутбук", "Ноутбук"), ("хадж", "Хадж"), ("умр", "Умра"), ("бизнес", "Бизнес"), ("ремонт", "Ремонт"),
    ("mashin", "Mashina"), ("telefon", "Telefon"), ("uy", "Uy"), ("kvartira", "Kvartira"), ("to'y", "To'y"),
    ("sayohat", "Sayohat"), ("noutbuk", "Noutbuk"), ("o'qish", "O'qish"),
]


def _num(s: str) -> Fraction:
    return Fraction(s.replace(",", "."))


def parse(text: str) -> dict:
    t = text.lower().replace("ё", "е")
    t = re.sub(r"(?<=\d)[  ](?=\d{3}\b)", "", t)  # "50 000 000" -> "50000000"
    out: dict = {}
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", t)
    if m:
        out["rate"] = _num(m.group(1))
        t = t[:m.start()] + " " + t[m.end():]
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(год|года|лет|мес\w*|yil\w*|oy\w*)", t)
    if m:
        n = _num(m.group(1))
        out["months"] = int(n * 12) if m.group(2).startswith(("год", "лет", "yil")) else int(n)
        t = t[:m.start()] + " " + t[m.end():]
    elif "полгода" in t:
        out["months"] = 6
    elif re.search(r"\bза год\b|\bна год\b", t):
        out["months"] = 12
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(млрд|миллиард\w*|млн|миллион\w*|тыс\w*|mlrd|milliard\w*|mln|"
                         r"million\w*|ming\w*|k\b|к\b)?", t):
        unit = m.group(2)
        if unit:
            mult = next(v for k, v in UNITS.items() if unit.startswith(k))
            out["amount"] = int(_num(m.group(1)) * mult)
            break
        val = _num(m.group(1))
        if val >= 1000:
            out["amount"] = int(val)
            break
    for stem, name in GOAL_NAMES:
        if stem in t:
            out["name"] = name
            break
    return out


def intent(text: str) -> str:
    t = text.lower()
    if re.search(r"кредит|рассроч|займ|заем|заём|в долг взять|kredit|nasiya", t):
        return "credit"
    if re.search(r"накоп|копить|отлож|цел|мечт|собрать|yig'|yig‘|jamg'|maqsad|orzu", t):
        return "goal"
    if re.search(r"аренд|долг|обязат|платеж|платёж|оплат|ijara|qarz|majburiyat|to'lov", t):
        return "obligations"
    if re.search(r"сколько|остат|баланс|потрат|хватит|свобод|на жизнь|qancha|balans|sarfla", t):
        return "cashflow"
    return "help"


def reply(s: State, message: str) -> dict:
    kind = intent(message)
    p = parse(message)
    try:
        if kind == "goal":
            return _goal(s, p)
        if kind == "credit":
            return _credit(s, p)
        if kind == "obligations":
            return _obligations(s)
        if kind == "cashflow":
            return _cashflow(s)
    except CalcError as e:
        return {"reply": str(e), "proposals": []}
    return {"reply": tr("f_help"), "proposals": []}


def _goal(s: State, p: dict) -> dict:
    if "amount" not in p:
        return {"reply": tr("f_ask_amount"), "proposals": []}
    if "months" not in p:
        return {"reply": tr("f_ask_term", amount_sum=p["amount"]), "proposals": []}
    name = p.get("name") or tr("f_new_goal")
    sg = goals.suggest(s, p["amount"], p["months"])
    pct = sg["percent"]
    if sg["feasible"]:
        head = tr("f_goal_ok", amount_sum=p["amount"], name=name, term_months=p["months"], pct=pct,
                  contrib_sum=sg["contribution_worst"])
    else:
        head = tr("f_goal_cap", term_months=p["months"], raw=sg["raw_percent"], cap=sg["cap_percent"],
                  used=sg["used_percent"], pct=pct, worst_months=sg["months_worst"])
    body = tr("f_goal_body", best_months=sg["months_best"], worst_months=sg["months_worst"],
              expiry_date=sg["expiry"], lock=tr("lock"))
    prop = proposals.propose_goal(s, name, p["amount"], pct)
    return {"reply": head + body, "proposals": [proposals.view(prop)], "data": sg}


def _credit(s: State, p: dict) -> dict:
    missing = [tr(w) for k, w in (("amount", "w_amount"), ("months", "w_term"), ("rate", "w_rate")) if k not in p]
    if missing:
        return {"reply": tr("f_credit_missing", missing=", ".join(missing)), "proposals": []}
    b = budget.basis(s)
    r = calc.calc_credit(p["amount"], p["rate"], p["months"], b, budget.monthly_obligations(s),
                         budget.goal_percents(s))
    impact = goals.credit_impact(s, r.payment)
    lines = [tr("f_credit_head", pay_sum=r.payment, over_sum=r.overpayment), tr("f_credit_dti", dti=r.dti_percent)]
    if r.cashflow_risk:
        lines.append(tr("f_credit_cash", free_sum=r.free_money))
    elif r.dti_risk:
        lines.append(tr("f_credit_dti_risk"))
    else:
        lines.append(tr("f_credit_left", left_sum=r.free_money - r.payment))
    for i in impact:
        if i["months_after"] is None:
            lines.append(tr("f_credit_never", name=i["name"]))
        elif i["delay_months"]:
            lines.append(tr("f_credit_delay", name=i["name"], before=i["months_before"], after=i["months_after"],
                            delay_months=i["delay_months"]))
    lines.append(tr("f_credit_options"))
    return {"reply": "\n".join(lines), "proposals": [], "data": {**r.__dict__, "impact": impact}}


def _obligations(s: State) -> dict:
    items = [obligations.view(s, o) for o in s.obligations.values() if not o.paid]
    if not items:
        return {"reply": tr("f_obl_none"), "proposals": []}
    lines = [tr("f_obl_head")]
    for o in sorted(items, key=lambda x: x["due_date"]):
        mark = tr("f_obl_ok") if o["shortfall"] == 0 else tr("f_obl_short", short_sum=o["shortfall"])
        when = tr("when_in", n_days=o["due_in_days"]) if o["due_in_days"] else tr("when_today")
        lines.append(tr("f_obl_line", name=o["name"], amount_sum=o["amount"], when=when, mark=mark))
    pend = [proposals.view(p) for p in s.proposals.values()
            if p.kind == "obligation_topup" and p.status == "pending"]
    if pend:
        lines.append(tr("f_obl_prop"))
    return {"reply": "\n".join(lines), "proposals": pend}


def _cashflow(s: State) -> dict:
    cf = budget.cashflow_view(s)
    txt = tr("f_cash", main_sum=cf["main_balance"], free_sum=cf["free_to_spend"], n_days=cf["days_until_next_income"],
             need_sum=cf["needed_until_payday"])
    if cf["cash_gap"]:
        txt += tr("f_cash_gap")
    return {"reply": txt, "proposals": [], "data": cf}
