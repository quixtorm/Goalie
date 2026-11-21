"""Seed data. Exact values from the demo script — do not change without updating tests."""
from datetime import date, datetime

from state import Goal, Obligation, State

START = datetime(2026, 12, 1, 9, 0)


def seed() -> State:
    s = State(
        clock=START,
        income_history=[7_200_000, 6_800_000, 7_600_000, 8_200_000, 7_400_000, 7_800_000],
        main_balance=12_000_000,
        next_income_date=date(2026, 12, 1),  # salary is "due today"
    )
    s.goals["goal_phone"] = Goal(
        id="goal_phone", name="Телефон", amount=8_000_000, saved=3_200_000, percent=10,
        disciplined=True, planned_months_left=8, priority=1,
    )
    s.obligations["obl_rent"] = Obligation(
        id="obl_rent", name="Аренда квартиры", amount=2_500_000, due_date=date(2026, 12, 7),
        reserved=1_000_000, monthly=True,
    )
    tx = [
        ("2026-11-30", "Korzinka — продукты", -186_000, "5411"),
        ("2026-11-30", "Yandex Go", -32_000, "4121"),
        ("2026-11-29", "Uzmobile — связь", -65_000, "4814"),
        ("2026-11-29", "Makro — продукты", -243_000, "5411"),
        ("2026-11-28", "Метро", -5_000, "4111"),
        ("2026-11-27", "Перевод от клиента", 450_000, None),
        ("2026-11-27", "Havas — продукты", -98_000, "5411"),
        ("2026-11-26", "Yandex Go", -27_000, "4121"),
        ("2026-11-25", "Коммунальные услуги", -310_000, "4900"),
        ("2026-11-24", "Чайхана", -84_000, "5812"),
    ]
    s.transactions = [
        {"id": f"tx_seed{i}", "date": d, "title": t, "amount": a, "source": "main", "mcc": m}
        for i, (d, t, a, m) in enumerate(tx)
    ]
    return s
