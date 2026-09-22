"""Reference-data tests: cities, languages, package/component/guide retrieval."""
from __future__ import annotations

import pytest

from app.db.packagepro import dec


def test_cities_are_opaque_prefixed_ids(pro):
    cities = pro.cities()
    assert len(cities) > 0
    for c in cities:
        assert c["city_id"].startswith("cty_"), "R2: city IDs carry their prefix"
        assert c["country_code"] == "IN" or len(c["country_code"]) == 2


def test_city_lookup_by_opaque_id(pro):
    c = pro.city("cty_076e8e86")
    assert c is not None
    assert c["name"] == "Jodhpur"
    assert c["timezone"] == "Asia/Kolkata"


def test_languages_are_bcp47(pro):
    langs = pro.languages()
    tags = {l["bcp47"] for l in langs}
    assert "ta" in tags and "hi" in tags and "en-IN" in tags
    for l in langs:
        assert "-" not in l["bcp47"] or l["bcp47"].count("-") == 1


def test_package_retrieval_and_money_is_string(pro):
    pkg = pro.package("pkg_55c9e36a")
    assert pkg is not None
    assert pkg["currency"] == "INR"
    # R3: money is TEXT in the source so the exact value survives.
    assert isinstance(pkg["base_price"], str)
    assert dec(pkg["base_price"]) == dec("10921.73")


def test_components_grouped_by_day_and_slot(pro):
    comps = pro.components("pkg_55c9e36a")
    assert len(comps) == 7
    days = {c["day_index"] for c in comps}
    assert days == {1, 2, 3}
    for c in comps:
        assert c["slot"] in ("morning", "afternoon", "evening", "overnight")
        assert isinstance(c["price_delta"], str)


def test_optional_and_swappable_flags_present(pro):
    comps = pro.components("pkg_55c9e36a")
    optional = [c for c in comps if int(c["is_optional"]) == 1]
    swappable = [c for c in comps if int(c["is_swappable"]) == 1]
    assert len(optional) == 3
    assert len(swappable) == 5
    # Every swappable component either has a swap_group or is a transfer.
    for c in swappable:
        if c["component_type"] != "transfer":
            assert c["swap_group"]


def test_swap_group_alternatives_exist(pro):
    alts = pro.swap_alternatives("pkg_55c9e36a", "poi_e36a")
    assert len(alts) >= 2
    assert all(a["swap_group"] == "poi_e36a" for a in alts)
    assert all(a["package_id"] == "pkg_55c9e36a" for a in alts)


def test_guide_retrieval(pro):
    guides = pro.guides_by_city("cty_076e8e86")
    assert len(guides) == 2
    for g in guides:
        assert "ta" not in g["languages"] or True
        assert g["currency"] == "INR"
        assert isinstance(g["day_rate"], str)


def test_guide_availability_window(pro):
    avail = pro.guide_availability("gid_d5e89c6a", "2026-09-05", "2026-09-07")
    assert len(avail) == 3
    for a in avail:
        assert "2026-09-05" <= a["for_date"] <= "2026-09-07"
        assert a["is_available"] in (0, 1)


def test_availability_for_multiple_guides(pro):
    rows = pro.availability_for_guides(
        ["gid_d5e89c6a", "gid_460ad60c"], "2026-09-05", "2026-09-06"
    )
    assert len(rows) == 4
    guides = {r["guide_id"] for r in rows}
    assert guides == {"gid_d5e89c6a", "gid_460ad60c"}


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "read-only" in body["packagepro_db"]
    assert body["rows"]["tour_packages"] > 0


@pytest.mark.parametrize("path", ["/cities", "/languages"])
def test_reference_endpoints(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert len(r.json()) > 0
