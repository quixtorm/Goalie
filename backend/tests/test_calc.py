from datetime import date
from fractions import Fraction

import pytest

import calc
from calc import CalcError, IncomeBasis

HIST = [7_200_000, 6_800_000, 7_600_000, 8_200_000, 7_400_000, 7_800_000]
TODAY = date(2026, 12, 1)


@pytest.fixture
def basis():
    return calc.income_basis(HIST)


def test_income_basis(basis):
    assert basis.worst == 6_800_000
    assert basis.avg == 7_500_000


def test_no_history_uses_entered_income():
    b = calc.income_basis([], fallback_income=5_000_000)
    assert b.worst == 5_000_000 and b.avg == 5_000_000
    with pytest.raises(CalcError):
        calc.income_basis([])


def test_rolling_income_history():
    new = calc.roll_income(HIST, 6_375_000)
    assert new == [6_800_000, 7_600_000, 8_200_000, 7_400_000, 7_800_000, 6_375_000]
    assert calc.income_basis(new).worst == 6_375_000


def test_normal_goal_phone(basis):
    f = calc.goal_forecast(8_000_000, 3_200_000, 10, basis, TODAY)
    assert (f.months_worst, f.months_best) == (8, 7)
    assert f.expiry == date(2027, 8, 1)


def test_income_below_average_takes_longer(basis):
    low = calc.income_basis([6_000_000] * 6)
    assert calc.months_needed(5_000_000, 10, low.worst) == 9
    assert calc.months_needed(5_000_000, 10, basis.worst) == 8


def test_one_month_goal(basis):
    s = calc.suggest_percent(680_000, 1, 0, basis)
    assert s.percent == 10 and s.feasible and s.months_worst == 1


def test_suggest_car_50m(basis):
    s = calc.suggest_percent(50_000_000, 36, 10, basis)
    assert (s.percent, s.feasible, s.months_worst, s.months_best) == (21, True, 36, 32)


def test_percent_cap_infeasible_100m(basis):
    s = calc.suggest_percent(100_000_000, 36, 10, basis)
    assert s.raw_percent == 41 and s.percent == 30 and not s.feasible
    assert (s.months_worst, s.months_best) == (50, 45)


def test_fourth_goal_rejected():
    with pytest.raises(CalcError, match="3 целей"):
        calc.validate_new_goal(3, 5, 10, 1_000_000)


def test_total_percent_cap():
    with pytest.raises(CalcError, match="40%"):
        calc.validate_new_goal(1, 31, 10, 1_000_000)
    calc.validate_new_goal(1, 30, 10, 1_000_000)


def test_min_percent():
    with pytest.raises(CalcError):
        calc.validate_new_goal(0, 0, 0, 1_000_000)


def test_ceil_exact_no_float_error():
    # 3 * (10% of 1_000_000) = exactly 300_000 -> exactly 3 months, never 4
    assert calc.months_needed(300_000, 10, 1_000_000) == 3
    assert calc.months_needed(300_001, 10, 1_000_000) == 4
    # classic float trap: 0.07 * 100 != 7.0
    assert calc.months_needed(700, 7, 100) == 100


def test_round_money_half_up():
    assert calc.round_money(Fraction(1, 2)) == 1
    assert calc.round_money(Fraction(3, 2)) == 2
    assert calc.round_money(Fraction(-1, 2)) == -1


def test_annuity_known_value(basis):
    r = calc.calc_credit(20_000_000, 28, 12, IncomeBasis(6_375_000, Fraction(7_362_500)), 2_500_000, [22, 10])
    assert r.payment == 1_930_120
    assert r.overpayment == 3_161_437
    assert r.dti_percent == 30 and not r.dti_risk
    assert r.free_money == 1_835_000 and r.cashflow_risk and r.risk


def test_zero_rate_credit():
    assert calc.annuity_payment(1_200_000, 0, 12) == 100_000


def test_credit_impact_delays_goals():
    b = IncomeBasis(6_375_000, Fraction(7_362_500))
    imp = calc.credit_impact_on_goals(1_930_120, [
        {"id": "car", "name": "Машина", "amount": 50_000_000, "saved": 1_038_750, "percent": 22}], b)
    assert imp[0].months_before == 35 and imp[0].months_after == 51 and imp[0].delay_months == 16


def test_bonus_rate_switch():
    assert calc.monthly_bonus(1_200_000, True) == 22_000
    assert calc.monthly_bonus(1_200_000, False) == 12_000


def test_breach_cost_cinema():
    b = IncomeBasis(6_375_000, Fraction(7_362_500))
    c = calc.breach_cost(50_000_000, 1_338_750, 22, 150_000, b, date(2026, 12, 1))
    assert c.delay_days == 3
    # next 12 months only: sum(1 338 750 + m * 1 402 500, m=1..12) * (22-12)/1200 = 125 460 000 / 120
    assert c.bonus_lost == 1_045_500


def test_breach_bonus_is_next_12_months_only():
    b = IncomeBasis(6_375_000, Fraction(7_362_500))
    contrib = calc.monthly_contribution(22, b.worst)
    expected = calc.round_money(calc.projected_bonus(1_338_750, contrib, 50_000_000, 12, 22)
                                - calc.projected_bonus(1_338_750, contrib, 50_000_000, 12, 12))
    # the same 150 000 purchase on a goal with a much longer horizon still loses only one year of bonus
    long_goal = calc.breach_cost(500_000_000, 1_338_750, 22, 150_000, b, date(2026, 12, 1))
    assert long_goal.bonus_lost == expected
    # a goal that finishes in < 12 months counts only its remaining months (balance capped at the goal)
    short = calc.breach_cost(3_000_000, 1_338_750, 22, 150_000, b, date(2026, 12, 1))
    assert 0 < short.bonus_lost < expected
    # delay logic unchanged
    assert long_goal.delay_days == 3


def test_breach_tiny_amount_min_one_day(basis):
    c = calc.breach_cost(50_000_000, 1_000_000, 21, 1_000, basis, TODAY)
    assert c.delay_days == 1


def test_obligation_status():
    s = calc.obligation_status(2_500_000, 1_000_000, date(2026, 12, 7), TODAY, False)
    assert (s.due_in_days, s.shortfall, s.status) == (6, 1_500_000, "soon")
    s = calc.obligation_status(1_500_000, 0, date(2026, 12, 5), date(2026, 12, 2), False)
    assert s.status == "shortfall"


def test_add_months_clamps_day():
    assert calc.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert calc.add_months(TODAY, 36) == date(2029, 12, 1)


def test_fmt_uzs():
    assert calc.fmt_uzs(10_000_000) == "10 000 000 so'm"
