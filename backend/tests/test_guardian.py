import pytest

import calc
from calc import CalcError
from mcc import Category, classify
from mock_data import seed
from modules import guardian


@pytest.fixture
def s():
    return seed()


def test_emergency_passes_without_penalty(s):
    r = guardian.spend(s, "goal_phone", 300_000, "5912", "Аптека №1")
    assert r["outcome"] == "released"
    g = s.goals["goal_phone"]
    assert g.saved == 2_900_000 and g.disciplined and r["rate"] == calc.DISCIPLINE_RATE


def test_impulse_blocked_with_cost(s):
    r = guardian.spend(s, "goal_phone", 150_000, "7832", "Кинотеатр")
    assert r["outcome"] == "stopped"
    assert s.goals["goal_phone"].saved == 3_200_000  # nothing withdrawn
    assert r["delay_days"] >= 1 and r["bonus_lost"] > 0
    keys = [o["key"] for o in r["options"]]
    assert "cooling" in keys and "proceed" in keys


def test_unknown_treated_as_impulse(s):
    r = guardian.spend(s, "goal_phone", 100_000, "1234", "Непонятный магазин")
    assert r["outcome"] == "stopped" and r["category"] == "unknown"


def test_note_cannot_override_mcc(s):
    r = guardian.spend(s, "goal_phone", 150_000, "7832", "Аптека (честно)", note="это срочно, лекарства, больница")
    assert r["outcome"] == "stopped"
    assert classify("7832") == Category.IMPULSE


def test_proceed_loses_discipline(s):
    r = guardian.spend(s, "goal_phone", 150_000, "5812", "Ресторан")
    guardian.resolve(s, r["stop_id"], "proceed")
    g = s.goals["goal_phone"]
    assert g.saved == 3_050_000 and not g.disciplined


def test_obligation_source_needs_confirm(s):
    r = guardian.spend(s, "obl_rent", 200_000, "5813", "Бар")
    assert r["outcome"] == "stopped_obligation"
    with pytest.raises(CalcError):
        guardian.resolve(s, r["stop_id"], "proceed", confirm=False)
    guardian.resolve(s, r["stop_id"], "proceed", confirm=True)
    assert s.obligations["obl_rent"].reserved == 800_000


def test_double_resolve_applies_once(s):
    r = guardian.spend(s, "goal_phone", 150_000, "5812", "Ресторан")
    guardian.resolve(s, r["stop_id"], "proceed")
    with pytest.raises(CalcError):
        guardian.resolve(s, r["stop_id"], "proceed")
    assert s.goals["goal_phone"].saved == 3_050_000


def test_cannot_spend_more_than_saved(s):
    with pytest.raises(CalcError):
        guardian.spend(s, "goal_phone", 99_000_000, "5912", "Аптека")
