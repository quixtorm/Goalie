"""Seed data. Exact values from the demo script — do not change without updating tests."""
from datetime import date, datetime

from calc import OTHER, SALARY, TRANSFER
from state import Goal, Obligation, State
from texts import both, msg

START = datetime(2026, 12, 1, 9, 0)

FAMILY = both("Семья", "Oila")
WORK = both("Зарплата", "Ish haqi")
CLIENT = both("Клиент", "Mijoz")

# 12 months of SALARY. The planning window is the last 6 (worst 6 800 000, avg 7 500 000 — the verified demo numbers);
# the earlier months are all >= 6 800 000, so they do not change the worst month either.
SALARIES = [
    ("2025-12-01", 7_000_000), ("2026-01-01", 7_100_000), ("2026-02-01", 6_900_000), ("2026-03-01", 7_300_000),
    ("2026-04-01", 7_500_000), ("2026-05-01", 7_200_000),
    ("2026-06-01", 7_200_000), ("2026-07-01", 6_800_000), ("2026-08-01", 7_600_000), ("2026-09-01", 8_200_000),
    ("2026-10-01", 7_400_000), ("2026-11-01", 7_800_000),
]
# Irregular transfers from family + one client payment: visible in history, EXCLUDED from planning.
OTHER_INFLOWS = [
    ("2026-08-14", 2_000_000, TRANSFER, FAMILY),
    ("2026-10-20", 1_500_000, TRANSFER, FAMILY),
    ("2026-11-27", 450_000, OTHER, CLIENT),
]


def seed() -> State:
    incomes = [{"id": f"inc_s{i}", "date": d, "amount": a, "type": SALARY, "source": WORK, "offer_open": False}
               for i, (d, a) in enumerate(SALARIES)]
    incomes += [{"id": f"inc_o{i}", "date": d, "amount": a, "type": t, "source": src, "offer_open": False}
                for i, (d, a, t, src) in enumerate(OTHER_INFLOWS)]
    s = State(
        clock=START,
        incomes=incomes,
        main_balance=12_000_000,
        next_income_date=date(2026, 12, 1),  # salary is "due today"
    )
    s.goals["goal_phone"] = Goal(
        id="goal_phone", name="Телефон", amount=8_000_000, saved=3_200_000, percent=10,
        disciplined=True, planned_months_left=8, priority=1, names={"ru": "Телефон", "uz": "Telefon"},
    )
    s.obligations["obl_rent"] = Obligation(
        id="obl_rent", name="Аренда квартиры", amount=2_500_000, due_date=date(2026, 12, 7),
        reserved=1_000_000, monthly=True, names={"ru": "Аренда квартиры", "uz": "Kvartira ijarasi"},
    )
    tx = [
        ("2026-11-30", msg("tx_groceries", shop="Korzinka"), -186_000, "5411", None),
        ("2026-11-30", msg("tx_taxi"), -32_000, "4121", None),
        ("2026-11-29", msg("tx_mobile"), -65_000, "4814", None),
        ("2026-11-29", msg("tx_groceries", shop="Makro"), -243_000, "5411", None),
        ("2026-11-28", msg("tx_metro"), -5_000, "4111", None),
        ("2026-11-27", msg("tx_client"), 450_000, None, OTHER),
        ("2026-11-27", msg("tx_groceries", shop="Havas"), -98_000, "5411", None),
        ("2026-11-26", msg("tx_taxi"), -27_000, "4121", None),
        ("2026-11-25", msg("tx_utilities"), -310_000, "4900", None),
        ("2026-11-24", msg("tx_chaikhana"), -84_000, "5812", None),
    ]
    s.transactions = [
        {"id": f"tx_seed{i}", "date": d, "title": t, "amount": a, "source": "main", "mcc": m, "type": ty}
        for i, (d, t, a, m, ty) in enumerate(tx)
    ]
    return s
