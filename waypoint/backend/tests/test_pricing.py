"""Pricing tests — the Decimal rules.

R3: money is a fixed-point 2-place decimal plus an ISO-4217 currency. No float
may ever touch a value we display or compare.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.db.packagepro import dec
from app.services import pricing

JODHPUR_COMPONENTS = [
    {"price_delta": "385.31", "is_optional": 0},
    {"price_delta": "4570.17", "is_optional": 0},
    {"price_delta": "1216.82", "is_optional": 0},
    {"price_delta": "551.86", "is_optional": 0},
    {"price_delta": "593.83", "is_optional": 1},
    {"price_delta": "1479.39", "is_optional": 1},
    {"price_delta": "579.93", "is_optional": 1},
]
JODHPUR_BASE = "10921.73"


def test_dec_rejects_float():
    from app.db.packagepro import PackageProError

    with pytest.raises(PackageProError):
        dec(4.3)


def test_dec_handles_none_and_strings():
    assert dec(None) == Decimal("0")
    assert dec("8500.00") == Decimal("8500.00")
    assert dec(" 8500.00 ") == Decimal("8500.00")


def test_included_total_uses_packagepro_convention():
    total = pricing.included_total(JODHPUR_BASE, JODHPUR_COMPONENTS)
    # base + 385.31 + 4570.17 + 1216.82 + 551.86  (optionals excluded)
    assert total == Decimal("17645.89")
    assert total == dec("10921.73") + dec("385.31") + dec("4570.17") + dec(
        "1216.82"
    ) + dec("551.86")


def test_included_total_from_real_db(pro):
    comps = pro.components("pkg_55c9e36a")
    pkg = pro.package("pkg_55c9e36a")
    total = pricing.included_total(pkg["base_price"], comps)
    assert total == Decimal("17645.89")


def test_included_total_excludes_optionals():
    with_optional = pricing.included_total("1000.00", [
        {"price_delta": "100.00", "is_optional": 0},
        {"price_delta": "50.00", "is_optional": 1},
    ])
    assert with_optional == Decimal("1100.00")


def test_swap_pricing_convention():
    old = {"price_delta": "385.31"}
    new = {"price_delta": "551.86"}
    assert pricing.swap_delta(old, new) == Decimal("166.55")
    # new_total = current - old + new
    assert pricing.apply_swap(Decimal("17645.89"), old, new) == Decimal("17812.44")


def test_swap_can_reduce_price():
    old = {"price_delta": "551.86"}
    new = {"price_delta": "385.31"}
    assert pricing.swap_delta(old, new) == Decimal("-166.55")
    assert pricing.apply_swap(Decimal("17645.89"), old, new) == Decimal("17479.34")


def test_quantize_always_two_places():
    assert pricing.quantize_money(Decimal("100")) == Decimal("100.00")
    assert str(pricing.quantize_money(Decimal("99.999"))) == "100.00"


def test_guide_cost_uses_decimal_multiplier():
    guide = {"day_rate": "2400.00", "half_day_rate": "1440.00"}
    assert pricing.guide_cost(guide, "full_day", 1) == Decimal("2400.00")
    assert pricing.guide_cost(guide, "full_day", "1.25") == Decimal("3000.00")
    assert pricing.guide_cost(guide, "half_day", "1.25") == Decimal("1800.00")
    assert pricing.guide_cost(guide, "full_day", Decimal("1.35")) == Decimal("3240.00")


def test_no_float_creates_displayed_money():
    # The classic float trap: 0.1 + 0.2 != 0.3. Decimal must not reproduce it.
    assert dec("0.10") + dec("0.20") == Decimal("0.30")
    with pytest.raises(Exception):
        dec(0.1)


def test_trip_days_is_inclusive():
    assert pricing.trip_days("2026-09-05", "2026-09-07") == 3
    assert pricing.trip_days("2026-09-05", "2026-09-10") == 6
    assert pricing.trip_days("2026-09-05", "2026-09-05") == 1


def test_trip_days_rejects_inverted_range():
    with pytest.raises(ValueError):
        pricing.trip_days("2026-09-10", "2026-09-05")


def test_remaining_and_overage():
    assert pricing.remaining(Decimal("20000"), Decimal("17645.89")) == Decimal("2354.11")
    assert pricing.overage(Decimal("20000"), Decimal("20850")) == Decimal("850.00")
    assert pricing.overage(Decimal("20000"), Decimal("20000")) is None
    assert pricing.overage(Decimal("20000"), Decimal("10000")) is None
