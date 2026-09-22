"""
Package repricing — the core PS-04 requirement, in Decimal.

Formula (from the data guide and starter query 3):
    total = base_price + SUM(price_delta for each kept component)

`price_delta` is SIGNED and may be negative. Repricing happens in Money (R3);
a float here produces a total 0.01 off and impossible to explain to a judge.

A "kept" component is one that is not optional. Optional components are
charged only if the traveller adds them. Swapping replaces one component with
another in the same swap_group; the price effect is the delta of the new line
minus the delta of the old line.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.money import Money


@dataclass(frozen=True)
class Component:
    """A single package_components row, with money already lifted to Money."""

    component_id: str
    package_id: str
    component_type: str
    entity_type: str | None
    entity_id: str | None
    day_index: int
    slot: str
    title: str
    quantity: int
    price_delta: Money
    is_optional: bool
    is_swappable: bool
    swap_group: str | None

    @property
    def key(self) -> str:
        return self.component_id


@dataclass(frozen=True)
class Package:
    """A tour_packages row."""

    package_id: str
    city_id: str
    name: str
    theme: str
    tier: str
    duration_days: int
    duration_nights: int
    base_price: Money
    min_group_size: int
    max_group_size: int
    difficulty: str
    languages_offered: list[str]
    inclusions: str
    exclusions: str
    description: str


@dataclass
class RepriceBreakdown:
    """The auditable answer to 'why does this cost what it costs'."""

    base_price: Money
    included_delta: Money
    optional_added: Money
    total: Money
    line_items: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "base_price": self.base_price.to_dict(),
            "included_delta": self.included_delta.to_dict(),
            "optional_added": self.optional_added.to_dict(),
            "total": self.total.to_dict(),
            "line_items": self.line_items,
        }


def reprice(
    package: Package,
    components: list[Component],
    selected_optional: set[str] | None = None,
    swaps: dict[str, str] | None = None,
) -> RepriceBreakdown:
    """
    Compute the live price of a customized package.

    Args:
        package: the base package.
        components: all its components.
        selected_optional: ids of OPTIONAL components the traveller added.
        swaps: mapping of original component_id -> replacement component_id.
               Both lines must share a swap_group (validated by the caller).

    Returns:
        An exact Decimal breakdown the UI can render and the budget guard can
        enforce against. Never a float at any point.
    """
    selected_optional = selected_optional or set()
    swaps = {} if swaps is None else swaps

    # Resolve the effective component set: apply swaps.
    by_id = {c.component_id: c for c in components}
    effective: list[Component] = []
    for comp in components:
        replacement_id = swaps.get(comp.component_id)
        if replacement_id is not None:
            replacement = by_id.get(replacement_id)
            if replacement is None:
                raise KeyError(f"swap target {replacement_id} not in package {package.package_id}")
            effective.append(replacement)
        else:
            effective.append(comp)

    currency = package.base_price.currency
    included = Money.zero(currency)
    optional_total = Money.zero(currency)
    line_items: list[dict] = []

    for comp in effective:
        if not comp.is_optional:
            included = included + comp.price_delta
            line_items.append(
                {
                    "component_id": comp.component_id,
                    "title": comp.title,
                    "day_index": comp.day_index,
                    "slot": comp.slot,
                    "kind": "included",
                    "delta": comp.price_delta.to_dict(),
                    "swapped_from": _origin(comp.component_id, swaps),
                }
            )
        elif comp.component_id in selected_optional:
            optional_total = optional_total + comp.price_delta
            line_items.append(
                {
                    "component_id": comp.component_id,
                    "title": comp.title,
                    "day_index": comp.day_index,
                    "slot": comp.slot,
                    "kind": "optional",
                    "delta": comp.price_delta.to_dict(),
                    "swapped_from": _origin(comp.component_id, swaps),
                }
            )

    total = package.base_price + included + optional_total
    return RepriceBreakdown(
        base_price=package.base_price,
        included_delta=included,
        optional_added=optional_total,
        total=total,
        line_items=line_items,
    )


def _origin(component_id: str, swaps: dict[str, str]) -> str | None:
    """If this component is a swap replacement, report what it replaced."""
    for original, replacement in swaps.items():
        if replacement == component_id:
            return original
    return None


def swap_delta(from_comp: Component, to_comp: Component) -> Money:
    """Net price change of swapping one line for another. Signed."""
    return to_comp.price_delta - from_comp.price_delta


def validate_swap(from_comp: Component, to_comp: Component) -> None:
    """A swap is only legal within the same package and swap_group."""
    if from_comp.package_id != to_comp.package_id:
        raise ValueError(
            f"cannot swap across packages: {from_comp.package_id} vs {to_comp.package_id}"
        )
    if not from_comp.is_swappable or not to_comp.is_swappable:
        raise ValueError("both components must be swappable")
    if not from_comp.swap_group or from_comp.swap_group != to_comp.swap_group:
        raise ValueError(
            f"components must share a swap_group: "
            f"{from_comp.swap_group!r} vs {to_comp.swap_group!r}"
        )
    if from_comp.component_id == to_comp.component_id:
        raise ValueError("cannot swap a component with itself")
