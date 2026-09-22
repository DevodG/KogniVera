"""Language-matched, genuinely-available guide matching."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from ..db.packagepro import PackageProDB, dec, dec_num
from ..models import GuideAvailabilityModel, GuideModel
from . import pricing


def _split_langs(raw: Optional[str]) -> list[str]:
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


def _theme_synonyms(theme: Optional[str]) -> list[str]:
    """Map a package theme onto guide specialisation vocabulary."""
    if not theme:
        return []
    table = {
        "heritage": ["heritage", "religious", "history", "culture", "cultural"],
        "pilgrimage": ["religious", "heritage", "spiritual"],
        "food_trail": ["food", "cuisine", "culinary"],
        "adventure": ["adventure", "trekking", "photography", "wildlife"],
        "wildlife": ["wildlife", "nature", "adventure", "trekking"],
        "wellness": ["wellness", "ayurveda", "yoga"],
        "honeymoon": ["photography", "food", "heritage"],
        "family": ["family", "food", "heritage"],
    }
    return table.get(theme.lower(), [theme.lower()])


def guide_cost_for_trip(
    guide: dict[str, Any], service: str, availability: list[dict[str, Any]]
) -> tuple[Decimal, Decimal]:
    """Cost for the trip using the multiplier of the first available day.

    Returns ``(cost, multiplier)``. ``cost`` is zero when unavailable.
    """
    avail = [a for a in availability if int(a["is_available"]) == 1 and int(a["slots_available"]) > 0]
    if not avail:
        return Decimal("0"), Decimal("1")
    mult = dec_num(avail[0]["price_multiplier"])
    return pricing.guide_cost(guide, service, mult), mult


def match_guides(
    db: PackageProDB,
    city_id: str,
    preferred_languages: list[str],
    theme: Optional[str],
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Return guides for the city with real availability, best fit first."""
    guides = db.guides_by_city(city_id)
    if not guides:
        return []

    avail_map: dict[str, list[dict[str, Any]]] = {}
    for row in db.availability_for_guides(
        [g["guide_id"] for g in guides], start_date, end_date
    ):
        avail_map.setdefault(row["guide_id"], []).append(row)

    wanted = _theme_synonyms(theme)
    scored: list[tuple[int, Any, Any, Any]] = []

    for g in guides:
        langs = _split_langs(g["languages"])
        matched_langs = [l for l in preferred_languages if l in langs]
        avail = avail_map.get(g["guide_id"], [])
        free_days = [a for a in avail if int(a["is_available"]) == 1]
        has_free = bool(free_days)

        score = 0
        if matched_langs:
            score += 100
        if has_free:
            score += 50
        spec = (g["specialisation"] or "").lower()
        sec = (g["secondary_specialisation"] or "").lower()
        if wanted and (spec in wanted or sec in wanted):
            score += 30
        rating = dec_num(g["rating"]) if g.get("rating") not in (None, "") else Decimal("0")
        score += int(rating * 10)
        if int(g["certified"]) == 1:
            score += 5

        scored.append((score, g, avail, matched_langs))

    scored.sort(key=lambda t: (-t[0], t[1]["display_name"], t[1]["guide_id"]))

    out: list[dict[str, Any]] = []
    for score, g, avail, matched_langs in scored:
        free_days = [a for a in avail if int(a["is_available"]) == 1]
        busy_days = [a for a in avail if int(a["is_available"]) == 0]
        cost, mult = guide_cost_for_trip(g, "full_day", avail)
        spec = (g["specialisation"] or "").lower()
        sec = (g["secondary_specialisation"] or "").lower()
        reasons = []
        if matched_langs:
            reasons.append(f"Speaks {', '.join(matched_langs)} (you asked for {', '.join(preferred_languages)})")
        if wanted and (spec in wanted or sec in wanted):
            reasons.append(f"Specialty {g['specialisation']} matches your {theme} theme")
        elif spec:
            reasons.append(f"Specialty: {g['specialisation']}")
        if free_days:
            reasons.append(
                f"Available on {len(free_days)} of {len(avail)} trip days "
                f"(from {free_days[0]['for_date']})"
            )
        else:
            reasons.append("No free day across your trip dates")
        if g.get("rating"):
            reasons.append(f"Rating {g['rating']} from {g['review_count']} reviews")
        if int(g["certified"]) == 1:
            reasons.append("Certified guide")

        out.append(
            {
                "guide": g,
                "languages": langs,
                "available": bool(free_days),
                "available_days": free_days,
                "unavailable_days": busy_days,
                "full_day_cost": cost,
                "half_day_cost": (
                    pricing.guide_cost(g, "half_day", mult) if free_days else Decimal("0")
                ),
                "multiplier": mult,
                "fit_reason": "; ".join(reasons) if reasons else "City match",
                "match_score": score,
            }
        )
    return out


def to_guide_model(entry: dict[str, Any], selected: bool = False,
                   service: Optional[str] = None) -> GuideModel:
    g = entry["guide"]
    cost = entry["full_day_cost"] if (service or "full_day") == "full_day" else entry["half_day_cost"]
    return GuideModel(
        guide_id=g["guide_id"],
        display_name=g["display_name"],
        languages=entry["languages"],
        specialisation=g["specialisation"],
        secondary_specialisation=g.get("secondary_specialisation"),
        years_experience=int(g["years_experience"]),
        rating=f"{dec_num(g['rating']):.1f}" if g.get("rating") not in (None, "") else None,
        review_count=int(g["review_count"]),
        day_rate=f"{dec(g['day_rate']):.2f}",
        half_day_rate=f"{dec(g['half_day_rate']):.2f}",
        currency=g["currency"],
        certified=bool(int(g["certified"])),
        bio=g["bio"],
        city_id=g["city_id"],
        available=entry["available"],
        available_days=[
            GuideAvailabilityModel(
                for_date=a["for_date"],
                is_available=bool(int(a["is_available"])),
                slots_available=int(a["slots_available"]),
                price_multiplier=f"{dec_num(a['price_multiplier']):.2f}",
            )
            for a in entry["available_days"]
        ],
        unavailable_days=[
            GuideAvailabilityModel(
                for_date=a["for_date"],
                is_available=bool(int(a["is_available"])),
                slots_available=int(a["slots_available"]),
                price_multiplier=f"{dec_num(a['price_multiplier']):.2f}",
            )
            for a in entry["unavailable_days"]
        ],
        selected_cost=f"{cost:.2f}" if selected else None,
        selected_multiplier=f"{entry['multiplier']:.2f}" if selected else None,
        selected_service=service if selected else None,
        fit_reason=entry["fit_reason"],
    )
