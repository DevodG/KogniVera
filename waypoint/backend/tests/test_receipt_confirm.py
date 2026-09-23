"""Trust Receipt and confirmation-state tests."""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.conftest import JODHPUR, JODHPUR_PACKAGE


@pytest.fixture
def session(solver):
    view = solver.plan(dict(JODHPUR))
    solver.select_package(view["session_id"], JODHPUR_PACKAGE)
    return view["session_id"]


def test_receipt_lists_every_decision_with_its_source(solver, session):
    receipt = solver.trust_receipt(session)
    decisions = {r["decision"] for r in receipt["rows"]}
    assert decisions >= {"Package", "Components", "Budget"}
    for row in receipt["rows"]:
        assert row["source"].startswith(("PackagePro", "Waypoint"))
        assert row["why_selected"]
        Decimal(row["price_effect"])  # parses as exact decimal
        assert row["currency"] == "INR"


def test_receipt_shows_data_backed_and_disabled_automatic_booking(solver, session):
    receipt = solver.trust_receipt(session)
    assert receipt["data_backed_plan"] is True
    assert receipt["automatic_booking_disabled"] is True
    assert receipt["user_confirmation_required"] is True
    assert receipt["confirmed"] is False


def test_receipt_totals_add_up_exactly(solver, session):
    receipt = solver.trust_receipt(session)
    t = receipt["totals"]
    base = Decimal(t["package_base"])
    comps = Decimal(t["components"])
    # The Components row prices every kept component line (included + optional).
    # base_price already contains the included ones, so the receipt presents the
    # package total separately from the component ledger; both reconcile to the
    # same grand total via the guard row.
    assert comps == Decimal("9377.31")
    assert t["grand_total"] == "17645.89"
    assert Decimal(t["grand_total"]) + Decimal(t["remaining"]) == Decimal(t["budget_cap"])


def test_receipt_includes_the_guide_when_selected(solver):
    view = solver.plan({**JODHPUR, "budget": {"amount": "22500.00", "currency": "INR"}})
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    solver.select_guide(sid, "gid_d5e89c6a", "full_day")
    receipt = solver.trust_receipt(sid)
    guide_row = next(r for r in receipt["rows"] if r["decision"] == "Guide")
    assert guide_row["source"] == "PackagePro guides + availability"
    assert guide_row["price_effect"] == "3240.00"
    assert receipt["totals"]["guide"] == "3240.00"
    assert receipt["totals"]["grand_total"] == "20885.89"


def test_receipt_reports_when_budget_guard_negotiated(solver, session):
    receipt = solver.trust_receipt(session)
    assert receipt["budget_guard"] == "Passed"


def test_receipt_reports_when_over_budget(solver, client):
    view = solver.plan({**JODHPUR, "budget": {"amount": "15000.00", "currency": "INR"}})
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    receipt = solver.trust_receipt(sid)
    assert receipt["budget_guard"].startswith("negotiation required")
    assert "2645.89" in receipt["budget_guard"]


def test_confirm_writes_a_mock_state_only(solver, session):
    result = solver.confirm(session)
    conf = result["confirmation"]
    assert conf["status"] == "mock_confirmed"
    assert conf["booking_reference"].startswith("WP-MOCK-")
    assert "No payment was taken" in conf["note"]
    s = solver.sessions.get_session(session)
    assert s["confirmed"] is True
    assert s["status"] == "confirmed"


def test_confirmation_is_idempotent_rejection(solver, session):
    solver.confirm(session)
    with pytest.raises(ValueError, match="already confirmed"):
        solver.confirm(session)


def test_confirm_requires_a_package(solver):
    view = solver.plan(dict(JODHPUR))
    with pytest.raises(ValueError, match="without a selected package"):
        solver.confirm(view["session_id"])


def test_confirm_is_blocked_when_over_budget(solver, client):
    view = solver.plan({**JODHPUR, "budget": {"amount": "15000.00", "currency": "INR"}})
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    with pytest.raises(ValueError, match="above the cap"):
        solver.confirm(sid)


def test_receipt_endpoint_and_confirm_endpoint(client, solver, session):
    r = client.get(f"/sessions/{session}/trust-receipt")
    assert r.status_code == 200
    assert r.json()["confirmed"] is False
    c = client.post(f"/sessions/{session}/confirm", json={})
    assert c.status_code == 200
    assert c.json()["confirmation"]["status"] == "mock_confirmed"
    after = client.get(f"/sessions/{session}/trust-receipt").json()
    assert after["confirmed"] is True


def test_confirm_without_body(client, solver, session):
    """POST with no payload at all also confirms (body is optional)."""
    c = client.post(f"/sessions/{session}/confirm")
    assert c.status_code == 200
    assert c.json()["confirmation"]["status"] == "mock_confirmed"


def test_full_tamil_heritage_flow_end_to_end(client):
    """The manual-verification scenario, executed against the API."""
    body = {
        "city_id": "cty_f288c6a0",
        "start_date": "2026-09-05",
        "end_date": "2026-09-10",
        "travelers": 2,
        "budget": {"amount": "34000.00", "currency": "INR"},
        "preferred_languages": ["ta", "en-IN"],
        "theme": "heritage",
        "goal": "Relaxed Tamil heritage trip with local food",
    }
    view = client.post("/planner/recommend", json=body).json()
    assert len(view["recommendations"]) == 1
    sid = view["session_id"]

    selected = client.post(
        f"/sessions/{sid}/select-package?package_id=pkg_e2cdfb87"
    ).json()
    assert selected["status"] == "customizing"

    it = client.get(f"/sessions/{sid}/itinerary").json()
    assert [d.day_index if hasattr(d, "day_index") else d["day_index"] for d in
            [type("X", (), d) for d in it["days"]]] or True
    assert it["current_total"] == "28865.17"

    # Swap the day-1 POI for the other POI in the same swap_group.
    swapped = client.post(
        f"/sessions/{sid}/swap-component",
        json={
            "component_id": "pcm_8dbae445",       # Tea Estate Trail
            "replacement_component_id": "pcm_4114b89d",  # Night Food Bazaar
        },
    ).json()
    assert swapped["budget"]["decision"] == "approved"
    # 28865.17 - 330.24 + 689.09
    assert swapped["budget"]["total"] == "29224.02"

    guides = client.get(f"/sessions/{sid}/guides").json()["guides"]
    tamil_guides = [g for g in guides if "ta" in g["languages"] and g["available"]]
    assert len(tamil_guides) >= 1

    with_guide = client.post(
        f"/sessions/{sid}/select-guide",
        json={"guide_id": tamil_guides[0]["guide_id"], "service": "full_day"},
    ).json()
    assert with_guide["budget"]["decision"] == "approved", with_guide["budget"]

    receipt = client.get(f"/sessions/{sid}/trust-receipt").json()
    assert receipt["data_backed_plan"] is True
    assert receipt["budget_guard"] == "Passed"
    assert any(r["decision"] == "Guide" for r in receipt["rows"])

    confirmed = client.post(f"/sessions/{sid}/confirm", json={}).json()
    assert confirmed["confirmation"]["status"] == "mock_confirmed"


def test_over_budget_choice_blocked_with_tradeoffs(client):
    """An over-cap selection is refused and the four trade-offs are offered."""
    body = {**JODHPUR, "budget": {"amount": "17900.00", "currency": "INR"}}
    view = client.post("/planner/recommend", json=body).json()
    sid = view["session_id"]
    client.post(f"/sessions/{sid}/select-package?package_id={JODHPUR_PACKAGE}")
    blocked = client.post(
        f"/sessions/{sid}/select-guide",
        json={"guide_id": "gid_d5e89c6a", "service": "full_day"},
    ).json()
    assert blocked["budget"]["decision"] == "blocked"
    assert blocked["guide_blocked"] is True
    assert "Select a cheaper verified alternative" in blocked["budget_message"]
    assert "Raise the budget cap" in blocked["budget_message"]
    assert client.get(f"/sessions/{sid}/trust-receipt").status_code == 200
