"""Guide matching: language, specialty, availability filtering and cost."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services import pricing
from app.services.guides import guide_cost_for_trip, match_guides, to_guide_model
from tests.conftest import JODHPUR, JODHPUR_PACKAGE, PONDICHERRY

JODHPUR_GUIDES = {"gid_d5e89c6a": "Anita Iyer", "gid_460ad60c": "Aarav Patel"}
PONDICHERRY_GUIDES = {"gid_3561d64b": "Arjun Patel", "gid_b37f26b0": "Karthik Tanaka"}


def test_match_guides_returns_city_guides_with_availability(pro):
    entries = match_guides(
        pro, JODHPUR["city_id"], ["hi", "en-IN"], "heritage",
        JODHPUR["start_date"], JODHPUR["end_date"],
    )
    assert len(entries) == 2
    names = {e["guide"]["display_name"] for e in entries}
    assert names == set(JODHPUR_GUIDES.values())
    for e in entries:
        assert e["available"] is True
        assert len(e["available_days"]) + len(e["unavailable_days"]) == 3


def test_guide_availability_is_real_not_asserted(pro):
    entries = match_guides(
        pro, JODHPUR["city_id"], ["hi"], None,
        "2026-09-05", "2026-09-07",
    )
    for e in entries:
        for day in e["available_days"]:
            assert int(day["is_available"]) == 1
            assert int(day["slots_available"]) > 0
        for day in e["unavailable_days"]:
            assert int(day["is_available"]) == 0


def test_language_filter_ranks_tamil_guides_first_for_tamil_request(pro):
    entries = match_guides(
        pro, PONDICHERRY["city_id"], ["ta", "en-IN"], "heritage",
        PONDICHERRY["start_date"], PONDICHERRY["end_date"],
    )
    assert len(entries) == 2
    assert all("ta" in e["languages"] for e in entries)
    top = entries[0]
    assert "ta" in top["languages"]


def test_guides_without_availability_are_marked_unavailable(pro):
    # Construct a date window where a guide has no free day by picking the
    # full availability matrix and finding a busy window.
    avail = pro.guide_availability("gid_3561d64b", "2026-09-01", "2026-09-30")
    busy = [a["for_date"] for a in avail if int(a["is_available"]) == 0]
    if len(busy) >= 2:
        start, end = busy[0], busy[-1]
        entries = match_guides(
            pro, PONDICHERRY["city_id"], ["ta"], None, start, end,
        )
        hit = next(e for e in entries if e["guide"]["guide_id"] == "gid_3561d64b")
        if all(int(a["is_available"]) == 0 for a in pro.guide_availability("gid_3561d64b", start, end)):
            assert hit["available"] is False
            assert hit["full_day_cost"] == Decimal("0")


def test_guide_cost_applies_date_multiplier_with_decimal(pro):
    guide = pro.guide("gid_3561d64b")
    avail = pro.guide_availability("gid_3561d64b", "2026-09-05", "2026-09-06")
    cost, mult = guide_cost_for_trip(guide, "full_day", avail)
    first_free = next(a for a in avail if int(a["is_available"]) == 1)
    expected = pricing.guide_cost(guide, "full_day", first_free["price_multiplier"])
    assert cost == expected
    assert mult == Decimal(str(first_free["price_multiplier"]))


def test_guide_cost_zero_when_unavailable(pro):
    guide = pro.guide("gid_3561d64b")
    cost, _ = guide_cost_for_trip(guide, "full_day", [])
    assert cost == Decimal("0")


def test_guide_selection_persists_multiplier_and_cost(solver):
    # A ₹22,500 cap leaves room for the guide after the package total.
    view = solver.plan({**JODHPUR, "budget": {"amount": "22500.00", "currency": "INR"}})
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    result = solver.select_guide(sid, "gid_d5e89c6a", "full_day")
    s = solver.sessions.get_session(sid)
    pkg_total = Decimal("17645.89")
    # Anita Iyer is first free on 2026-09-06 with a 1.35 date multiplier.
    assert s["selected_guide_id"] == "gid_d5e89c6a"
    assert s["guide_service"] == "full_day"
    assert Decimal(s["guide_multiplier"]) == Decimal("1.35")
    assert Decimal(s["guide_cost"]) == Decimal("3240.00")
    assert Decimal(s["total_amount"]) == pkg_total + Decimal("3240.00")
    assert result["budget"]["decision"] == "approved"
    assert result["budget"]["remaining"] == "1614.11"


def pro_first_free_mult(solver, guide_id) -> str:
    rows = solver.pro.guide_availability(guide_id, JODHPUR["start_date"], JODHPUR["end_date"])
    return next(a["price_multiplier"] for a in rows if int(a["is_available"]) == 1)


def test_guide_selection_blocked_when_over_budget(solver):
    view = solver.plan({**JODHPUR, "budget": {"amount": "17800.00", "currency": "INR"}})
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    result = solver.select_guide(sid, "gid_d5e89c6a", "full_day")
    assert result["budget"]["decision"] == "blocked"
    assert result.get("guide_blocked") is True
    # Nothing must be persisted.
    s = solver.sessions.get_session(sid)
    assert s["selected_guide_id"] is None
    assert s["guide_cost"] is None


def test_unavailable_guide_cannot_be_selected(solver):
    view = solver.plan(dict(JODHPUR))
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    # 2026-09-05 is a fully-booked day for this guide in guide_availability.
    solver.sessions.update_session(sid, start_date="2026-09-05", end_date="2026-09-05")
    with pytest.raises(ValueError, match="not available"):
        solver.select_guide(sid, "gid_d5e89c6a", "full_day")


def test_guide_from_another_city_is_rejected(solver):
    view = solver.plan(dict(JODHPUR))
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    with pytest.raises(ValueError, match="different city"):
        solver.select_guide(sid, "gid_3561d64b", "full_day")


def test_invalid_service_is_rejected(solver):
    view = solver.plan(dict(JODHPUR))
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    with pytest.raises(ValueError, match="service"):
        solver.select_guide(sid, "gid_d5e89c6a", "multi_day")


def test_guides_endpoint_marks_selected_guide(solver, client):
    view = solver.plan({**JODHPUR, "budget": {"amount": "22500.00", "currency": "INR"}})
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    solver.select_guide(sid, "gid_d5e89c6a", "full_day")
    r = client.get(f"/sessions/{sid}/guides")
    assert r.status_code == 200
    guides = r.json()["guides"]
    selected = [g for g in guides if g.get("selected_cost") is not None]
    assert len(selected) == 1
    assert selected[0]["guide_id"] == "gid_d5e89c6a"
    assert selected[0]["selected_cost"] == "3240.00"


def test_guide_model_caries_availability_detail(pro):
    entries = match_guides(
        pro, JODHPUR["city_id"], ["hi", "en-IN"], None,
        JODHPUR["start_date"], JODHPUR["end_date"],
    )
    model = to_guide_model(entries[0])
    assert model.available is True
    assert all(a.is_available for a in model.available_days)
    assert all(not a.is_available for a in model.unavailable_days)
    assert model.fit_reason
