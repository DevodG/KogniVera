from app.agent.budget_guard import BudgetGuard


def test_allows_spending_within_cap():
    guard = BudgetGuard(cap=10000)
    decision = guard.add_cost(4000, "flight")
    assert decision.allowed is True
    assert guard.running_total == 4000


def test_blocks_spending_over_cap_and_offers_negotiation():
    guard = BudgetGuard(cap=10000)
    guard.add_cost(8000, "flight")
    decision = guard.add_cost(5000, "hotel")
    assert decision.allowed is False
    assert decision.overage == 3000
    assert guard.running_total == 8000  # NOT committed — hard stop
    assert len(decision.negotiation_options) == 4


def test_audit_trail_records_every_decision():
    guard = BudgetGuard(cap=5000)
    guard.add_cost(2000, "flight")
    guard.add_cost(4000, "hotel")  # blocked
    trail = guard.audit_trail()
    assert len(trail) == 2
    assert trail[0]["allowed"] is True
    assert trail[1]["allowed"] is False
