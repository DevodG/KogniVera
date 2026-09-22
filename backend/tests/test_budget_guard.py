"""
Tests for the BudgetGuard — the trust centerpiece.

The invariant that matters above all: the running total can NEVER exceed the
cap. An over-cap attempt must commit nothing and must return negotiation
options instead of a flat refusal. The previous build got this wrong twice
(float money, and a frontend that bypassed the guard entirely).
"""
from decimal import Decimal

import pytest

from app.core.budget_guard import BudgetGuard
from app.core.money import Money


@pytest.fixture
def guard():
    return BudgetGuard(Money("10000.00", "INR"))


class TestGuardConstruction:
    def test_requires_money_cap(self):
        with pytest.raises(TypeError):
            BudgetGuard(10000.0)  # float — R3

    def test_starts_at_zero(self, guard):
        assert guard.running_total.is_zero()
        assert guard.remaining().amount == Decimal("10000.00")

    def test_empty_audit_trail(self, guard):
        assert guard.audit_trail() == []


class TestWithinCap:
    def test_allows_and_commits(self, guard):
        d = guard.add_cost(Money("4000", "INR"), "flight")
        assert d.allowed is True
        assert guard.running_total.amount == Decimal("4000.00")

    def test_exact_cap_is_allowed(self, guard):
        d = guard.add_cost(Money("10000", "INR"), "exactly the cap")
        assert d.allowed is True
        assert guard.running_total.amount == Decimal("10000.00")

    def test_pct_used(self, guard):
        guard.add_cost(Money("2500", "INR"), "x")
        assert guard.pct_used() == Decimal("25.0")

    def test_pct_used_zero_cap(self):
        g = BudgetGuard(Money("0", "INR"))
        assert g.pct_used() == Decimal("0")

    def test_decisions_are_numbered(self, guard):
        guard.add_cost(Money("100", "INR"), "a")
        guard.add_cost(Money("200", "INR"), "b")
        steps = [d["step"] for d in guard.audit_trail()]
        assert steps == [1, 2]


class TestOverCap:
    """These are the tests that defend the trust thesis."""

    def test_blocks_and_commits_nothing(self, guard):
        guard.add_cost(Money("6000", "INR"), "flight")
        d = guard.add_cost(Money("5000", "INR"), "hotel")
        assert d.allowed is False
        # THE invariant: total unchanged after a refusal.
        assert guard.running_total.amount == Decimal("6000.00")

    def test_returns_four_negotiation_options(self, guard):
        d = guard.add_cost(Money("12000", "INR"), "hotel")
        assert d.allowed is False
        assert d.negotiation is not None
        assert len(d.negotiation.as_list()) == 4

    def test_overage_is_exact(self, guard):
        d = guard.add_cost(Money("12500", "INR"), "hotel")
        assert d.overage.amount == Decimal("2500.00")

    def test_blocked_decision_has_no_overage(self, guard):
        d = guard.add_cost(Money("1000", "INR"), "ok")
        assert d.overage.is_zero()

    def test_would_exceed_does_not_commit(self, guard):
        assert guard.would_exceed(Money("20000", "INR")) is True
        assert guard.running_total.is_zero()

    def test_would_exceed_false(self, guard):
        assert guard.would_exceed(Money("500", "INR")) is False

    def test_currency_mismatch_rejected(self, guard):
        with pytest.raises(ValueError):
            guard.add_cost(Money("100", "USD"), "foreign")

    def test_non_money_rejected(self, guard):
        with pytest.raises(TypeError):
            guard.add_cost(1000.0, "float")  # R3


class TestRemoveAndRaise:
    def test_remove_cost(self, guard):
        guard.add_cost(Money("6000", "INR"), "flight")
        guard.remove_cost(Money("1000", "INR"), "flight partial refund")
        assert guard.running_total.amount == Decimal("5000.00")

    def test_raise_cap(self, guard):
        guard.add_cost(Money("9000", "INR"), "flight")
        guard.raise_cap(Money("20000", "INR"))
        assert guard.cap.amount == Decimal("20000.00")
        # Now the previously-blocked item fits.
        d = guard.add_cost(Money("5000", "INR"), "hotel")
        assert d.allowed is True

    def test_raise_cap_is_logged(self, guard):
        guard.raise_cap(Money("20000", "INR"))
        assert guard.audit_trail()[-1]["label"] == "raise_cap"

    def test_raise_cap_rejects_other_currency(self, guard):
        with pytest.raises(ValueError):
            guard.raise_cap(Money("100", "USD"))


class TestAuditTrail:
    def test_exportable_structure(self, guard):
        guard.add_cost(Money("4000", "INR"), "flight")
        guard.add_cost(Money("8000", "INR"), "too much")
        trail = guard.audit_trail()
        assert len(trail) == 2
        assert trail[0]["allowed"] is True
        assert trail[1]["allowed"] is False
        assert "message" in trail[1]
        assert trail[1]["negotiation"] == [] or len(trail[1]["negotiation"]) == 4

    def test_money_in_trail_is_serialised_as_string(self, guard):
        guard.add_cost(Money("4000", "INR"), "flight")
        entry = guard.audit_trail()[0]
        assert isinstance(entry["running_total"]["amount"], str)
        assert entry["running_total"]["currency"] == "INR"
