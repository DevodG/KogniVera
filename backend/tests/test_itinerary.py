"""Itinerary and swap tests: valid swaps, invalid swaps, live repricing."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.db.packagepro import dec
from app.services.itinerary import ItineraryService, SwapError
from tests.conftest import JODHPUR, JODHPUR_PACKAGE

HOT_SPRINGS = "pcm_64113615"      # day 1 afternoon POI, 385.31, poi_e36a
JAZZ_CELLAR = "pcm_b589c0bc"      # day 2 morning POI, 551.86, poi_e36a
HOTEL = "pcm_10fd434a"            # day 1 morning hotel, 4570.17, hotel_e36a
MEAL = "pcm_f31bcb15"             # day 3 afternoon meal, 593.83, not swappable
GUIDE_COMPONENT = "pcm_089e2e2b"  # day 3 overnight guide, swappable, guide_e36a
TRANSFER = "pcm_f906e597"         # day 2 afternoon transfer, no swap group
PONDICHERRY_COMPONENT = "pcm_84039e0d"  # belongs to another package


@pytest.fixture
def session(solver):
    view = solver.plan(dict(JODHPUR))
    solver.select_package(view["session_id"], JODHPUR_PACKAGE)
    return view["session_id"]


def itinerary(solver, session_id) -> ItineraryService:
    return ItineraryService(solver.pro, solver.sessions, session_id)


def test_itinerary_groups_by_day(solver, session):
    it = itinerary(solver, session).itinerary()
    assert [d.day_index for d in it.days] == [1, 2, 3]
    titles = [c.title for d in it.days for c in d.components]
    assert "Hot Springs" in titles
    assert it.current_total == "17645.89"


def test_components_label_included_optional_and_swappable(solver, session):
    it = itinerary(solver, session).itinerary()
    flat = [c for d in it.days for c in d.components]
    optional = [c for c in flat if c.is_optional]
    included = [c for c in flat if not c.is_optional]
    assert len(optional) == 3
    assert all(c.is_swappable is False or c.component_type == "guide" for c in optional)
    assert all(c.is_swappable for c in included)
    assert it.included_total == "17645.89"


def test_swap_alternatives_are_same_package_and_swap_group(solver, session):
    svc = itinerary(solver, session)
    alts = svc.swap_alternatives(HOT_SPRINGS)
    assert len(alts) == 1
    assert alts[0]["component_id"] == JAZZ_CELLAR
    assert alts[0]["package_id"] == JODHPUR_PACKAGE
    assert alts[0]["swap_group"] == "poi_e36a"


def test_valid_swap_reprices_exactly(solver, session):
    svc = itinerary(solver, session)
    before = svc.package_total()
    applied = svc.apply_swap(HOT_SPRINGS, JAZZ_CELLAR)
    assert applied["delta"] == "166.55"
    assert applied["total"] == "17812.44"
    svc = itinerary(solver, session)
    # 17645.89 - 385.31 + 551.86
    assert svc.package_total() == Decimal("17812.44")
    assert before + Decimal("166.55") == svc.package_total()


def test_swap_persisted_in_session(solver, session):
    svc = itinerary(solver, session)
    svc.apply_swap(HOT_SPRINGS, JAZZ_CELLAR)
    persisted = solver.sessions.get_session(session)["component_overrides_map"]
    assert persisted == {HOT_SPRINGS: JAZZ_CELLAR}


def test_swap_response_contains_budget_and_trace(solver, session):
    view = solver.swap(session, HOT_SPRINGS, JAZZ_CELLAR)
    assert view["budget"]["decision"] == "approved"
    assert view["budget"]["total"] == "17812.44"
    assert view["budget"]["remaining"] == "2187.56"
    summaries = [e["result_summary"] for e in view["trace"]]
    assert any("Swap checked" in s for s in summaries)
    assert any("Budget Guard approved" in s for s in summaries)


def test_swap_back_restores_the_original_price(solver, session):
    solver.swap(session, HOT_SPRINGS, JAZZ_CELLAR)
    view = solver.swap(session, JAZZ_CELLAR, HOT_SPRINGS)
    assert view["budget"]["total"] == "17645.89"


def test_invalid_swap_same_component(solver, session):
    with pytest.raises(SwapError):
        solver.swap(session, HOT_SPRINGS, HOT_SPRINGS)


def test_invalid_swap_different_swap_group(solver, session):
    with pytest.raises(SwapError, match="swap_group"):
        solver.swap(session, HOTEL, JAZZ_CELLAR)


def test_invalid_swap_non_swappable_component(solver, session):
    with pytest.raises(SwapError, match="not swappable"):
        solver.swap(session, MEAL, JAZZ_CELLAR)


def test_invalid_swap_cross_package(solver, session):
    with pytest.raises(SwapError, match="same package"):
        solver.swap(session, HOTEL, PONDICHERRY_COMPONENT)


def test_invalid_swap_component_not_in_session_package(solver, session):
    with pytest.raises(SwapError, match="does not belong"):
        solver.swap(session, PONDICHERRY_COMPONENT, JAZZ_CELLAR)


def test_invalid_swap_wrong_component_type(solver, session):
    # The guide component is swappable and in its own swap group, so the only
    # legal replacement is another guide row; swapping it for a POI must fail.
    svc = itinerary(solver, session)
    with pytest.raises(SwapError):
        svc.validate_swap(GUIDE_COMPONENT, JAZZ_CELLAR)


def test_optional_component_removed_and_restored(solver, session):
    svc = itinerary(solver, session)
    # Removing an optional component is a no-op for the price under the
    # PackagePro convention (only included components are priced), but the
    # removal is persisted and the component disappears from the itinerary.
    removed = svc.remove_optional(MEAL)
    assert removed["delta"] == "-593.83"
    svc = itinerary(solver, session)
    comps = {c["component_id"] for c in svc.effective_components()}
    assert MEAL not in comps
    assert svc.current_total() == Decimal("17645.89")
    restored = svc.restore_optional(MEAL)
    assert restored["delta"] == "593.83"
    svc = itinerary(solver, session)
    assert MEAL in {c["component_id"] for c in svc.effective_components()}


def test_only_optional_components_can_be_removed(solver, session):
    svc = itinerary(solver, session)
    with pytest.raises(SwapError, match="not optional"):
        svc.remove_optional(HOTEL)


def test_itinerary_endpoint_returns_refreshed_totals(solver, client, session):
    r = client.get(f"/sessions/{session}/itinerary")
    assert r.status_code == 200
    body = r.json()
    assert body["current_total"] == "17645.89"
    assert body["budget"]["remaining"] == "2354.11"
    assert body["swaps"] == []


def test_swap_endpoint_blocks_over_budget(solver, client):
    view = solver.plan({**JODHPUR, "budget": {"amount": "17700.00", "currency": "INR"}})
    sid = view["session_id"]
    solver.select_package(sid, JODHPUR_PACKAGE)
    r = client.post(
        f"/sessions/{sid}/swap-component",
        json={"component_id": HOT_SPRINGS, "replacement_component_id": JAZZ_CELLAR},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["budget"]["decision"] == "blocked"
    assert body["budget"]["overage"] == "112.44"
    assert body.get("swap_blocked") is True
    # The swap must NOT have been applied.
    persisted = solver.sessions.get_session(sid)["component_overrides_map"]
    assert persisted == {}


def test_itinerary_requires_a_selected_package(solver, client):
    view = solver.plan(dict(JODHPUR))
    r = client.get(f"/sessions/{view['session_id']}/itinerary")
    assert r.status_code == 400


def test_select_package_from_another_city_is_rejected(solver):
    view = solver.plan(dict(JODHPUR))
    with pytest.raises(ValueError, match="different city"):
        solver.select_package(view["session_id"], "pkg_e2cdfb87")


def test_unknown_session_returns_404(client):
    assert client.get("/sessions/wp_missing").status_code == 404
    assert client.get("/sessions/wp_missing/itinerary").status_code == 404
