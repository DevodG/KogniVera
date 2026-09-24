"""Budget Guard tests: under/over cap, negotiation options, audit log."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.budget import BudgetGuard
from app.services import pricing
from tests.conftest import JODHPUR, JODHPUR_PACKAGE


@pytest.fixture
def session(solver):
    view = solver.plan(dict(JODHPUR))
    solver.select_package(view["session_id"], JODHPUR_PACKAGE)
    return view["session_id"]


def guard(solver, session_id) -> BudgetGuard:
    return BudgetGuard(solver.sessions, session_id)


def test_under_budget_is_approved(solver, session):
    result = guard(solver, session).decide(Decimal("17645.89"))
    assert result["decision"] == "approved"
    assert result["remaining"] == "2354.11"
    assert result["overage"] is None
    assert result["negotiation_options"] == []


def test_exactly_at_cap_is_approved(solver, session):
    result = guard(solver, session).decide(Decimal("20000.00"))
    assert result["decision"] == "approved"
    assert result["remaining"] == "0.00"


def test_over_budget_is_blocked(solver, session):
    result = guard(solver, session).decide(Decimal("20850.00"))
    assert result["decision"] == "blocked"
    assert result["overage"] == "850.00"
    assert result["negotiation_options"] == [
        "select_cheaper_alternative",
        "remove_optional_component",
        "raise_budget_cap",
        "approve_overage",
    ]


def test_blocked_message_lists_the_four_choices(solver, session):
    result = guard(solver, session).decide(Decimal("20850.00"))
    msg = guard(solver, session).message(result)
    assert "₹20,000.00" in msg
    assert "₹850.00" in msg
    assert "Select a cheaper verified alternative" in msg
    assert "Remove an optional component" in msg
    assert "Raise the budget cap" in msg
    assert "Explicitly approve this exact overage" in msg


def test_every_decision_is_written_to_the_audit_log(solver, session):
    g = guard(solver, session)
    g.decide(Decimal("17645.89"))
    g.decide(Decimal("20850.00"))
    audit = solver.sessions.audit(session)
    budget_entries = [a for a in audit if a["action"].startswith("budget:change")]
    assert len(budget_entries) == 2
    assert budget_entries[0]["decision"] == "approved"
    assert budget_entries[1]["decision"] == "blocked"
    assert budget_entries[1]["amount"] == "850.00"


def test_raise_budget_cap_option(solver, session):
    result = guard(solver, session).negotiate(
        solver.sessions.get_session(session),
        "raise_budget_cap",
        Decimal("25000.00"),
    )
    assert result["decision"] == "approved"
    assert solver.sessions.get_session(session)["budget_amount"] == "25000.00"


def test_raise_budget_cap_must_be_higher(solver, session):
    with pytest.raises(ValueError, match="must be higher"):
        guard(solver, session).negotiate(
            solver.sessions.get_session(session),
            "raise_budget_cap",
            Decimal("15000.00"),
        )


def test_unknown_negotiation_option(solver, session):
    with pytest.raises(ValueError, match="unknown negotiation option"):
        guard(solver, session).negotiate(
            solver.sessions.get_session(session), "do_magic"
        )


def test_negotiate_endpoint_records_and_reprices(client, solver, session):
    r = client.post(
        f"/sessions/{session}/negotiate",
        json={
            "option": "raise_budget_cap",
            "new_budget": {"amount": "25000.00", "currency": "INR"},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["budget"]["cap"] == "25000.00"
    assert body["budget"]["decision"] == "approved"
    assert any(e["action"] == "negotiate" for e in body["trace"])


def test_negotiate_endpoint_validates_option(client, session):
    r = client.post(
        f"/sessions/{session}/negotiate",
        json={"option": "not_an_option"},
    )
    assert r.status_code == 422


def test_budget_is_read_from_the_server_not_the_client(solver, session):
    # The persisted cap is the only source of truth.
    assert guard(solver, session)._cap() == Decimal("20000.00")
    assert guard(solver, session)._currency() == "INR"


def test_over_budget_guide_then_negotiate_then_confirm(solver, client):
    view = solver.plan(dict(JODHPUR))
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    blocked = solver.select_guide(sid, "gid_460ad60c", "full_day")
    assert blocked["budget"]["decision"] == "blocked"
    assert solver.sessions.get_session(sid)["selected_guide_id"] is None

    raised = solver.negotiate(sid, "raise_budget_cap", "25000.00")
    assert raised["budget"]["decision"] == "approved"

    ok = solver.select_guide(sid, "gid_460ad60c", "full_day")
    assert ok["budget"]["decision"] == "approved"

    receipt = solver.trust_receipt(sid)
    assert receipt["budget_guard"] == "Passed"
    assert solver.confirm(sid)["confirmation"]["status"] == "mock_confirmed"
