"""Recommendation tests: eligibility filters, language filtering, ranking."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.db.packagepro import dec
from app.services import recommender
from app.services.recommender import (
    SCORE_DURATION,
    SCORE_LANGUAGE,
    SCORE_THEME,
    SCORE_WITHIN_BUDGET,
    filter_eligible,
    rank,
)
from tests.conftest import JODHPUR, PONDICHERRY


def test_jodhpur_recommendation_returns_eligible_package(solver):
    view = solver.plan(dict(JODHPUR))
    assert view["status"] == "recommended"
    assert len(view["recommendations"]) >= 1
    top = view["recommendations"][0]
    rec = top.model_dump() if hasattr(top, "model_dump") else top
    assert rec["package_id"] == "pkg_55c9e36a"
    assert rec["city_name"] == "Jodhpur"
    assert rec["included_total"] == "17645.89"
    assert rec["within_budget"] is True
    assert rec["languages_offered"] == ["hi", "en-IN"]


def test_language_filter_excludes_packages_without_the_language(pro):
    packages = pro.packages_by_city(JODHPUR["city_id"])
    # Jodhpur's only package offers hi,en-IN — Tamil-only request must reject it.
    eligible, rejected = filter_eligible(
        packages,
        JODHPUR["city_id"],
        ["ta"],
        3,
        2,
        Decimal("50000"),
        "INR",
        None,
        db=pro,
        return_rejected=True,
    )
    assert eligible == []
    assert "no preferred language offered" in rejected[0][1]


def test_currency_filter_rejects_non_inr(pro):
    # There are non-INR packages in the data; they must never be eligible.
    packages = pro.packages_by_city("cty_f288c6a0")
    eligible, _ = filter_eligible(
        packages, "cty_f288c6a0", ["ta", "en-IN"], 6, 2, Decimal("99999"),
        "USD", None, db=pro, return_rejected=True,
    )
    assert eligible == []


def test_group_size_filter(pro):
    packages = pro.packages_by_city(PONDICHERRY["city_id"])
    eligible, rejected = filter_eligible(
        packages, PONDICHERRY["city_id"], ["ta"], 6, 10, Decimal("99999"),
        "INR", None, db=pro, return_rejected=True,
    )
    assert eligible == []
    assert "group size outside range" in rejected[0][1]


def test_duration_filter(pro):
    packages = pro.packages_by_city(JODHPUR["city_id"])
    eligible, rejected = filter_eligible(
        packages, JODHPUR["city_id"], ["hi"], 10, 2, Decimal("99999"),
        "INR", None, db=pro, return_rejected=True,
    )
    assert eligible == []


def test_city_filter_is_enforced(pro):
    packages = pro.packages_by_city("cty_0b92e2e7")  # New Delhi
    eligible, rejected = filter_eligible(
        packages, "cty_076e8e86", ["hi"], 3, 2, Decimal("99999"),
        "INR", None, db=pro, return_rejected=True,
    )
    assert eligible == []


def test_ranking_scores_use_published_weights(pro):
    packages = pro.packages_by_city(JODHPUR["city_id"])
    eligible = filter_eligible(
        packages, JODHPUR["city_id"], ["hi", "en-IN"], 3, 2, Decimal("20000"),
        "INR", "heritage", db=pro,
    )
    scored = rank(eligible, ["hi", "en-IN"], 3, "heritage", Decimal("20000"))
    pkg, score, reasons = scored[0]
    assert score == SCORE_LANGUAGE + SCORE_DURATION + SCORE_THEME + SCORE_WITHIN_BUDGET
    assert score == 100
    assert any("Language match" in r for r in reasons)
    assert any("Duration match" in r for r in reasons)
    assert any("Theme match" in r for r in reasons)
    assert any("Within budget" in r for r in reasons)


def test_ranking_is_deterministic(pro):
    args = (["hi", "en-IN"], 3, "heritage", Decimal("20000"))
    packages = pro.packages_by_city(JODHPUR["city_id"])
    eligible = filter_eligible(
        packages, JODHPUR["city_id"], ["hi", "en-IN"], 3, 2, Decimal("20000"),
        "INR", "heritage", db=pro,
    )
    a = [p["package_id"] for p, _, _ in rank(eligible, *args)]
    b = [p["package_id"] for p, _, _ in rank(list(reversed(eligible)), *args)]
    assert a == b


def test_missing_language_costs_the_language_points(pro):
    packages = pro.packages_by_city(JODHPUR["city_id"])
    eligible = filter_eligible(
        packages, JODHPUR["city_id"], ["en-IN"], 3, 2, Decimal("20000"),
        "INR", None, db=pro,
    )
    scored = rank(eligible, ["en-IN"], 3, None, Decimal("20000"))
    _, score, _ = scored[0]
    assert score == SCORE_LANGUAGE + SCORE_DURATION + SCORE_WITHIN_BUDGET
    assert score == 80


def test_tamil_heritage_flow_finds_pondicherry(solver):
    view = solver.plan(dict(PONDICHERRY))
    assert len(view["recommendations"]) == 1
    top = view["recommendations"][0]
    rec = top.model_dump() if hasattr(top, "model_dump") else top
    assert rec["package_id"] == "pkg_e2cdfb87"
    assert rec["languages_offered"] == ["ta", "en-IN"]
    assert rec["theme"] == "heritage"
    assert rec["duration_days"] == 6


def test_recommend_trace_events_are_user_safe(solver):
    view = solver.plan(dict(JODHPUR))
    for ev in view["trace"]:
        assert {
            "step", "action", "status", "source", "input_summary",
            "result_summary", "user_safe_reason",
        } <= set(ev.keys())
        assert ev["source"].startswith(("PackagePro.", "Waypoint "))
        assert "chain" not in ev["user_safe_reason"].lower()


def test_plan_steps_are_published_before_querying(solver):
    view = solver.plan(dict(JODHPUR))
    assert view["plan_steps"] == [
        "Find packages that match your city, dates, language, group size, and budget.",
        "Explain the best eligible options.",
        "Let you customize itinerary components and choose a guide.",
        "Check your budget after every change.",
        "Never book anything until you approve.",
    ]
    # The plan trace must be the first event, before any package query.
    assert view["trace"][0]["action"] == "plan"
    assert view["trace"][0]["status"] == "complete"


def test_no_eligible_package_returns_empty_recommendations(solver):
    request = dict(JODHPUR)
    request["preferred_languages"] = ["ta"]  # Jodhpur offers hi,en-IN only
    view = solver.plan(request)
    assert view["recommendations"] == []
    assert any("Searching" in e["result_summary"] for e in view["trace"])


def test_recommend_endpoint_persists_session(client):
    r = client.post("/planner/recommend", json=JODHPUR)
    assert r.status_code == 200
    body = r.json()
    sid = body["session_id"]
    assert body["request"]["city_id"] == JODHPUR["city_id"]
    got = client.get(f"/sessions/{sid}")
    assert got.status_code == 200
    assert got.json()["session_id"] == sid


def test_recommend_rejects_missing_city(client):
    bad = dict(JODHPUR)
    bad["city_id"] = "cty_does_not_exist"
    r = client.post("/planner/recommend", json=bad)
    assert r.status_code == 200
    assert r.json()["recommendations"] == []


def test_recommend_rejects_invalid_money(client):
    bad = dict(JODHPUR)
    bad["budget"] = {"amount": "not-a-number", "currency": "INR"}
    r = client.post("/planner/recommend", json=bad)
    assert r.status_code == 422
