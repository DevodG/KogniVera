"""Decimal pricing for Waypoint.

PackagePro pricing convention:

    included_total = package.base_price
                   + sum(price_delta for included, non-optional components)

Swap pricing convention:

    new_total = current_total - old_component.price_delta
              + replacement_component.price_delta

All arithmetic uses ``Decimal``. Quantisation to two places happens exactly
once per display/comparison boundary, never mid-calculation.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from ..db.packagepro import dec
from ..models import quantize_money

CENT = Decimal("0.01")


def included_total(base_price: Any, components: list[dict[str, Any]]) -> Decimal:
    """base_price + every included, non-optional component delta."""
    total = dec(base_price)
    for c in components:
        if not int(c["is_optional"]) and _is_kept(c):
            total += dec(c["price_delta"])
    return quantize_money(total)


def _is_kept(component: dict[str, Any]) -> bool:
    """A component contributes to the price when it is not optional."""
    return int(component["is_optional"]) == 0


def component_delta(component: dict[str, Any]) -> Decimal:
    return dec(component["price_delta"])


def swap_delta(old_component: dict[str, Any], new_component: dict[str, Any]) -> Decimal:
    """Signed price change of a swap: new delta minus old delta."""
    return dec(new_component["price_delta"]) - dec(old_component["price_delta"])


def apply_swap(current_total: Decimal, old_component: dict[str, Any],
               new_component: dict[str, Any]) -> Decimal:
    return quantize_money(
        current_total - dec(old_component["price_delta"]) + dec(new_component["price_delta"])
    )


def guide_cost(guide: dict[str, Any], service: str,
               multiplier: Any = 1) -> Decimal:
    """Guide service cost with the date multiplier applied, in Decimal.

    ``multiplier`` comes from ``guide_availability.price_multiplier`` and is
    stored NUMERIC(4,2) — it is cast through ``Decimal(str())``.
    """
    rate_key = "day_rate" if service == "full_day" else "half_day_rate"
    if rate_key not in guide:
        raise KeyError(f"guide row is missing {rate_key}")
    base = dec(guide[rate_key])
    from ..db.packagepro import dec_num as _dec_num
    mult = _dec_num(multiplier)
    return quantize_money(base * mult)


def trip_days(start_date: str, end_date: str) -> int:
    """Inclusive day span. Dates are ISO-8601 calendar dates (R4)."""
    from datetime import date

    s = date.fromisoformat(start_date)
    e = date.fromisoformat(end_date)
    if e < s:
        raise ValueError("end_date must not be before start_date")
    return (e - s).days + 1


def remaining(cap: Decimal, total: Decimal) -> Decimal:
    return quantize_money(cap - total)


def overage(cap: Decimal, total: Decimal) -> Optional[Decimal]:
    diff = total - cap
    if diff > Decimal("0"):
        return quantize_money(diff)
    return None
