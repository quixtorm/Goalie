"""DEMO loan catalog («демо-данные»). All products, names and rates are FICTIONAL — not real banks, not real offers.
The agent may only recommend products returned by calc.rank_credits over this list.
Rates differ on purpose so the trade-offs (rate vs fee vs term vs monthly payment) are visible.
"""
from texts import both

DEMO_DATA = True

PRODUCTS: list[dict] = [
    {"id": "demo_cons_std", "names": both("Потребительский Стандарт", "Iste'mol Standart", "Consumer Standard"), "type": "consumer",
     "annual_rate": 26, "origination_fee_percent": 1, "min_amount": 1_000_000, "max_amount": 50_000_000,
     "min_months": 6, "max_months": 36, "early_repayment_allowed": True, "min_salary_history_months": 6,
     "notes": both("Обычный кредит на любые цели, короткие и средние сроки.",
                   "Har qanday maqsad uchun oddiy kredit, qisqa va o'rta muddat.",
                   "A regular loan for any purpose, short and medium terms.")},
    {"id": "demo_cons_long", "names": both("Потребительский Выгодный (долгий срок)", "Iste'mol Foydali (uzoq muddat)", "Consumer Saver (long term)"),
     "type": "consumer", "annual_rate": 22, "origination_fee_percent": 2, "min_amount": 5_000_000,
     "max_amount": 100_000_000, "min_months": 24, "max_months": 60, "early_repayment_allowed": True,
     "min_salary_history_months": 12,
     "notes": both("Ставка ниже, но только на долгий срок — платёж меньше, переплата больше.",
                   "Stavka pastroq, lekin faqat uzoq muddatga — to'lov kichik, ortiqcha to'lov ko'p.",
                   "A lower rate, but only for long terms: a smaller payment, a bigger overpayment.")},
    {"id": "demo_auto", "names": both("Авто кредит", "Avto kredit", "Car loan"), "type": "auto",
     "annual_rate": 19, "origination_fee_percent": 1.5, "min_amount": 20_000_000, "max_amount": 300_000_000,
     "min_months": 12, "max_months": 60, "early_repayment_allowed": True, "min_salary_history_months": 6,
     "notes": both("Для покупки автомобиля, от 20 млн.", "Avtomobil xaridi uchun, 20 mln dan.", "For buying a car, from 20 million.")},
    {"id": "demo_install", "names": both("Рассрочка 0% на 6 мес (комиссия)", "Muddatli to'lov 0% 6 oyga (komissiya)", "0% installments for 6 months (fee)"),
     "type": "installment", "annual_rate": 0, "origination_fee_percent": 8, "min_amount": 1_000_000,
     "max_amount": 20_000_000, "min_months": 3, "max_months": 6, "early_repayment_allowed": False,
     "min_salary_history_months": 3,
     "notes": both("Процентов нет, но разовая комиссия 8% и большой ежемесячный платёж.",
                   "Foiz yo'q, lekin bir martalik 8% komissiya va katta oylik to'lov.",
                   "No interest, but a one-time 8% fee and a large monthly payment.")},
    {"id": "demo_micro", "names": both("Микрозайм", "Mikroqarz", "Microloan"), "type": "microloan",
     "annual_rate": 48, "origination_fee_percent": 0, "min_amount": 500_000, "max_amount": 10_000_000,
     "min_months": 3, "max_months": 12, "early_repayment_allowed": True, "min_salary_history_months": 0,
     "notes": both("Быстро и без истории зарплаты, но очень дорого.", "Tez va maosh tarixisiz, lekin juda qimmat.", "Fast and with no salary history, but very expensive.")},
    {"id": "demo_express", "names": both("Потребительский Экспресс", "Iste'mol Ekspress", "Consumer Express"), "type": "consumer",
     "annual_rate": 30, "origination_fee_percent": 0, "min_amount": 1_000_000, "max_amount": 30_000_000,
     "min_months": 6, "max_months": 24, "early_repayment_allowed": True, "min_salary_history_months": 3,
     "notes": both("Без комиссии, но ставка выше.", "Komissiyasiz, lekin stavka yuqori.", "No fee, but a higher rate.")},
]

BY_ID = {p["id"]: p for p in PRODUCTS}
