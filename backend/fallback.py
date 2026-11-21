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
from textfmt import LOCK_WARNING, days, fmt_date, fmt_uzs, months

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
    return {"reply": ("Я помогаю с деньгами: копить на цель, проверить кредит, следить за обязательными "
                      "платежами и подсказать, сколько можно потратить. Например: «Хочу накопить 50 млн на "
                      "машину за 3 года»."), "proposals": []}


def _goal(s: State, p: dict) -> dict:
    if "amount" not in p:
        return {"reply": "Сколько хотите накопить? Например: «50 млн на машину за 3 года».", "proposals": []}
    if "months" not in p:
        return {"reply": f"За какой срок хотите накопить {fmt_uzs(p['amount'])}? Например: «за 3 года».",
                "proposals": []}
    name = p.get("name", "Новая цель")
    sg = goals.suggest(s, p["amount"], p["months"])
    pct = sg["percent"]
    if sg["feasible"]:
        head = (f"Чтобы накопить {fmt_uzs(p['amount'])} на «{name}» за {months(p['months'])}, "
                f"откладывайте {pct}% дохода — это {fmt_uzs(sg['contribution_worst'])} в месяц.")
    else:
        head = (f"За {months(p['months'])} не получится: нужно {sg['raw_percent']}% дохода, "
                f"а свободно максимум {sg['cap_percent']}% (уже {sg['used_percent']}% идёт на другие цели). "
                f"При {pct}% цель займёт {months(sg['months_worst'])}.")
    body = (f"\n\n• Лучший случай: {months(sg['months_best'])}\n• Худший случай: {months(sg['months_worst'])}"
            f"\n• Срок цели: до {fmt_date(sg['expiry'])}\n\n{LOCK_WARNING}\n\nСоздать цель?")
    prop = proposals.propose_goal(s, name, p["amount"], pct)
    return {"reply": head + body, "proposals": [proposals.view(prop)], "data": sg}


def _credit(s: State, p: dict) -> dict:
    missing = [w for k, w in (("amount", "сумму"), ("months", "срок"), ("rate", "процентную ставку")) if k not in p]
    if missing:
        return {"reply": f"Чтобы посчитать кредит, назовите {', '.join(missing)}. "
                         f"Например: «20 млн на 12 месяцев под 28%».", "proposals": []}
    b = budget.basis(s)
    r = calc.calc_credit(p["amount"], p["rate"], p["months"], b, budget.monthly_obligations(s),
                         budget.goal_percents(s))
    impact = goals.credit_impact(s, r.payment)
    lines = [f"Платёж — {fmt_uzs(r.payment)} в месяц, переплата {fmt_uzs(r.overpayment)}."]
    lines.append(f"\n• Это {r.dti_percent}% вашего самого низкого дохода (безопасно — до 40%).")
    if r.cashflow_risk:
        lines.append(f"• ⚠ После обязательных платежей и целей остаётся {fmt_uzs(r.free_money)} в месяц — "
                     f"платёж больше этой суммы.")
    elif r.dti_risk:
        lines.append("• ⚠ Платёж больше 40% дохода — это высокий риск.")
    else:
        lines.append(f"• После платежа останется {fmt_uzs(r.free_money - r.payment)} свободных денег в месяц.")
    for i in impact:
        if i["months_after"] is None:
            lines.append(f"• «{i['name']}»: при таком платеже копить не получится.")
        elif i["delay_months"]:
            lines.append(f"• «{i['name']}»: {i['months_before']} → {i['months_after']} мес. "
                         f"(+{months(i['delay_months'])})")
    lines.append("\nВарианты: 1) взять меньшую сумму или на дольше; 2) сначала накопить часть; "
                 "3) отказаться от покупки. Конкретные банки я не советую. Что посчитать дальше?")
    return {"reply": "\n".join(lines), "proposals": [],
            "data": {**r.__dict__, "impact": impact}}


def _obligations(s: State) -> dict:
    items = [obligations.view(s, o) for o in s.obligations.values() if not o.paid]
    if not items:
        return {"reply": "Обязательных платежей пока нет.", "proposals": []}
    lines = ["Ваши обязательные платежи:"]
    for o in sorted(items, key=lambda x: x["due_date"]):
        mark = "✓ хватает" if o["shortfall"] == 0 else f"⚠ не хватает {fmt_uzs(o['shortfall'])}"
        lines.append(f"• {o['name']}: {fmt_uzs(o['amount'])}, через {days(o['due_in_days'])} — {mark}")
    pend = [proposals.view(p) for p in s.proposals.values()
            if p.kind == "obligation_topup" and p.status == "pending"]
    if pend:
        lines.append("\nЯ подготовил предложение, как закрыть нехватку.")
    return {"reply": "\n".join(lines), "proposals": pend}


def _cashflow(s: State) -> dict:
    cf = budget.cashflow_view(s)
    txt = (f"На основной карте {fmt_uzs(cf['main_balance'])}. Можно спокойно тратить {fmt_uzs(cf['free_to_spend'])}."
           f"\n\n• До зарплаты {days(cf['days_until_next_income'])}, на жизнь нужно примерно "
           f"{fmt_uzs(cf['needed_until_payday'])}.")
    if cf["cash_gap"]:
        txt += "\n• ⚠ До зарплаты может не хватить — посмотрите предложения во входящих."
    return {"reply": txt, "proposals": [], "data": cf}
