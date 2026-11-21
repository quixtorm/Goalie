from datetime import date

from fallback import parse
from mock_data import seed
from modules import obligations, proposals


def pending(s, kind=None):
    return [p for p in s.proposals.values() if p.status == "pending" and (kind is None or p.kind == kind)]


def test_no_proposals_at_seed():
    s = seed()
    proposals.agent_review(s)
    assert pending(s) == []


def test_review_is_idempotent():
    s = seed()
    obligations.create(s, "Долг", 1_000_000, date(2026, 12, 3))
    proposals.agent_review(s)
    proposals.agent_review(s)
    assert len(pending(s, "obligation_topup")) == 1


def test_stale_proposal_resolved_by_salary():
    s = seed()
    s.obligations["obl_rent"].due_date = date(2026, 12, 4)
    proposals.agent_review(s)
    assert len(pending(s, "obligation_topup")) == 1
    proposals.salary(s, 7_500_000)
    assert pending(s, "obligation_topup") == []


def test_confirm_applies_exactly_once():
    s = seed()
    o = obligations.create(s, "Долг", 1_000_000, date(2026, 12, 3))
    proposals.agent_review(s)
    p = pending(s, "obligation_topup")[0]
    proposals.apply(s, p.id)
    try:
        proposals.apply(s, p.id)
        raise AssertionError("second confirm must fail")
    except ValueError:
        pass
    assert s.obligations[o.id].reserved == 1_000_000
    assert s.main_balance == 11_000_000


def test_parser():
    assert parse("Хочу накопить 100 млн за 3 года") == {"amount": 100_000_000, "months": 36}
    assert parse("50 млн на машину за 3 года") == {"amount": 50_000_000, "months": 36, "name": "Машина"}
    p = parse("телефон в кредит 20 млн на 12 месяцев под 28%")
    assert (p["amount"], p["months"], p["rate"]) == (20_000_000, 12, 28)
    assert parse("1,5 млн за полгода")["amount"] == 1_500_000
    assert parse("10 000 000 за 10 месяцев")["amount"] == 10_000_000
