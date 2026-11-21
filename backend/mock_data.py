"""Seed data. Exact values from the demo script — do not change without updating tests."""
from datetime import date, datetime

from state import Goal, Obligation, State
from texts import msg

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
        disciplined=True, planned_months_left=8, priority=1, names={"ru": "Телефон", "uz": "Telefon"},
    )
    s.obligations["obl_rent"] = Obligation(
        id="obl_rent", name="Аренда квартиры", amount=2_500_000, due_date=date(2026, 12, 7),
        reserved=1_000_000, monthly=True, names={"ru": "Аренда квартиры", "uz": "Kvartira ijarasi"},
    )
    tx = [
        ("2026-11-30", msg("tx_groceries", shop="Korzinka"), -186_000, "5411"),
        ("2026-11-30", msg("tx_taxi"), -32_000, "4121"),
        ("2026-11-29", msg("tx_mobile"), -65_000, "4814"),
        ("2026-11-29", msg("tx_groceries", shop="Makro"), -243_000, "5411"),
        ("2026-11-28", msg("tx_metro"), -5_000, "4111"),
        ("2026-11-27", msg("tx_client"), 450_000, None),
        ("2026-11-27", msg("tx_groceries", shop="Havas"), -98_000, "5411"),
        ("2026-11-26", msg("tx_taxi"), -27_000, "4121"),
        ("2026-11-25", msg("tx_utilities"), -310_000, "4900"),
        ("2026-11-24", msg("tx_chaikhana"), -84_000, "5812"),
    ]
    s.transactions = [
        {"id": f"tx_seed{i}", "date": d, "title": t, "amount": a, "source": "main", "mcc": m}
        for i, (d, t, a, m) in enumerate(tx)
    ]
    return s
