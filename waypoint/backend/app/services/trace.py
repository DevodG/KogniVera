"""Structured, user-safe transparency events.

Rule 8: no hidden chain-of-thought is ever exposed. Transparency here means
*what the agent did, against which data, and why* — a structured audit trail
written in plain, reviewable facts.
"""
from __future__ import annotations

from typing import Any, Optional

_STEP = {
    "plan": 1,
    "recommend": 2,
    "match_guides": 3,
    "swap": 4,
    "budget": 5,
    "receipt": 6,
    "confirm": 7,
    "select_package": 2,
    "select_guide": 3,
    "negotiate": 5,
}

SOURCE = {
    "packages": "PackagePro.tour_packages",
    "components": "PackagePro.package_components",
    "guides": "PackagePro.tour_guides + guide_availability",
    "cities": "PackagePro.cities",
    "languages": "PackagePro.languages",
    "guard": "Waypoint Budget Guard",
    "session": "Waypoint session store",
}


def build(action: str, status: str, source: str, input_summary: str,
          result_summary: str, user_safe_reason: str,
          step: Optional[int] = None) -> dict[str, Any]:
    return {
        "step": int(step if step is not None else _STEP.get(action, 0)),
        "action": action,
        "status": status,
        "source": source,
        "input_summary": input_summary,
        "result_summary": result_summary,
        "user_safe_reason": user_safe_reason,
    }


def searching_packages(request: dict[str, Any]) -> dict[str, Any]:
    langs = ", ".join(request["preferred_languages"])
    return build(
        "recommend", "running", SOURCE["packages"],
        f"{request['city_id']}, {request['travelers']} travellers, "
        f"{request['start_date']} to {request['end_date']}, "
        f"budget {request['budget']['amount']} {request['budget']['currency']}",
        f"Searching real PackagePro packages for your constraints.",
        f"Filtering by city, language ({langs}), group size, duration and budget.",
    )


def found_packages(n: int, request: dict[str, Any], top_name: Optional[str]) -> dict[str, Any]:
    langs = ", ".join(request["preferred_languages"])
    days = None
    return build(
        "recommend", "complete", SOURCE["packages"],
        f"{request['city_id']}, {langs}, {request['start_date']} to {request['end_date']}",
        f"Found {n} eligible packages matching {langs}."
        + (f" Best match: {top_name}." if top_name else ""),
        "Ranked deterministically: language +40, duration +25, theme +20, within budget +15.",
    )


def package_selected(package: dict[str, Any], total: str, currency: str) -> dict[str, Any]:
    return build(
        "select_package", "complete", SOURCE["packages"],
        f"package_id {package['package_id']}",
        f"Selected by you: {package['name']} saved at {total} {currency}; no booking made.",
        "User decision recorded in the session store; nothing was booked.",
    )


def itinerary_loaded(package: dict[str, Any], n_components: int, total: str) -> dict[str, Any]:
    return build(
        "swap", "complete", SOURCE["components"],
        f"package_id {package['package_id']}",
        f"Itinerary loaded: {n_components} components across "
        f"{package['duration_days']} days. Running total {total} {package['currency']}.",
        "Components grouped by day and slot; optional and swappable items are labelled.",
    )


def swap_applied(old_title: str, new_title: str, delta: str, currency: str,
                 total: str, remaining: str) -> dict[str, Any]:
    d = _d(delta)
    if d > 0:
        phrase = f"adds {d} {currency}"
    elif d < 0:
        phrase = f"saves {abs(d)} {currency}"
    else:
        phrase = f"costs {d} {currency}"
    return build(
        "swap", "complete", SOURCE["components"],
        f"swap {old_title} -> {new_title}",
        f"Swap checked: {new_title} {phrase}. "
        f"New total {total} {currency}; {remaining} {currency} remains.",
        "Replacement comes from the same package, swap_group, day and slot.",
    )


def swap_blocked(reason: str) -> dict[str, Any]:
    return build(
        "swap", "blocked", SOURCE["components"], "swap request", reason,
        "Only components in the same package, swap_group, day_index and slot may be exchanged.",
    )


def guide_match(city_name: str, n_available: int, n_total: int, langs: str,
                start: str, end: str) -> dict[str, Any]:
    return build(
        "match_guides", "complete", SOURCE["guides"],
        f"{city_name}, {langs}, {start} to {end}",
        f"Guide check: {n_available} of {n_total} matching guides are available "
        f"across your trip dates.",
        "Filtered by language, specialty, rating and real date availability.",
    )


def guide_selected(guide: dict[str, Any], cost: str, multiplier: str,
                   currency: str, total: str) -> dict[str, Any]:
    return build(
        "select_guide", "complete", SOURCE["guides"],
        f"guide_id {guide['guide_id']}",
        f"Guide {guide['display_name']} added at {cost} {currency} "
        f"(rate x {multiplier} date multiplier). New total {total} {currency}.",
        "Date multiplier applied with Decimal; cost added server-side.",
    )


def guide_unavailable(guide: dict[str, Any]) -> dict[str, Any]:
    return build(
        "match_guides", "blocked", SOURCE["guides"],
        f"guide_id {guide['guide_id']}",
        f"{guide['display_name']} is not available on your trip dates.",
        "guide_availability shows no free slot; the guide cannot be selected.",
    )


def budget_approved(remaining: str, currency: str) -> dict[str, Any]:
    return build(
        "budget", "complete", SOURCE["guard"], "proposed change",
        f"Budget Guard approved: {remaining} {currency} remains.",
        "Server-side check against the cap you set; the browser is not trusted for totals.",
    )


def budget_blocked(overage: str, cap: str, currency: str) -> dict[str, Any]:
    return build(
        "budget", "blocked", SOURCE["guard"], "proposed change",
        f"Budget Guard blocked this choice: it would exceed your {cap} {currency} "
        f"cap by {overage} {currency}.",
        "The cap is code-enforced; the change was not applied.",
    )


def negotiation_applied(option: str, total: str, remaining: str, currency: str) -> dict[str, Any]:
    return build(
        "negotiate", "complete", SOURCE["guard"], f"negotiation option {option}",
        f"Negotiation applied ({option}). Total {total} {currency}; "
        f"{remaining} {currency} remains.",
        "The user chose how to resolve the overage; the decision is in the audit log.",
    )


def receipt_ready(total: str, currency: str, guard: str) -> dict[str, Any]:
    return build(
        "receipt", "complete", SOURCE["session"], f"session total {total} {currency}",
        f"Trust Receipt built. Budget Guard: {guard}.",
        "Every line shows its data source and exact price effect.",
    )


def confirmed(reference: str, total: str, currency: str) -> dict[str, Any]:
    return build(
        "confirm", "complete", SOURCE["session"], f"reference {reference}",
        f"Mock confirmation {reference} recorded at {total} {currency}. "
        f"No payment was taken and nothing was really booked.",
        "Confirmation is a state change in the session store only.",
    )


# ---------------------------------------------------------------------------
# tiny helpers
# ---------------------------------------------------------------------------


def _d(s: str) -> Decimal:
    from decimal import Decimal

    return Decimal(str(s).replace(",", ""))
