"""Deterministic package recommendation.

The LLM is not required for ranking. Eligibility is a set of hard filters
against real PackagePro rows; ranking is a fixed, published score. A model,
when a key is supplied later, may only *summarise* reasons from these
grounded facts.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from ..db.packagepro import PackageProDB, dec
from ..models import RecommendationModel
from . import pricing

SCORE_LANGUAGE = 40
SCORE_DURATION = 25
SCORE_THEME = 20
SCORE_WITHIN_BUDGET = 15


def _split_langs(raw: Optional[str]) -> list[str]:
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


class EligibilityError(ValueError):
    pass


def filter_eligible(
    packages: list[dict[str, Any]],
    city_id: str,
    preferred_languages: list[str],
    trip_days: int,
    travelers: int,
    budget: Decimal,
    currency: str,
    theme: Optional[str],
    db: Optional[PackageProDB] = None,
    return_rejected: bool = False,
):
    """Apply the hard eligibility filters. Returns (eligible, rejected)."""
    eligible: list[dict[str, Any]] = []
    rejected: list[tuple[dict[str, Any], str]] = []

    for p in packages:
        if p["city_id"] != city_id:
            rejected.append((p, "city mismatch")); continue
        if p["currency"] != currency:
            rejected.append((p, f"currency {p['currency']} is not {currency}")); continue
        if p["status"] != "active":
            rejected.append((p, "package not active")); continue
        langs = _split_langs(p["languages_offered"])
        if not any(lang in langs for lang in preferred_languages):
            rejected.append((p, "no preferred language offered")); continue
        if not (int(p["min_group_size"]) <= travelers <= int(p["max_group_size"])):
            rejected.append((p, "group size outside range")); continue
        if int(p["duration_days"]) != trip_days:
            rejected.append((p, f"duration {p['duration_days']}d != {trip_days}d")); continue

        comps = db.components(p["package_id"]) if db else []
        total = pricing.included_total(p["base_price"], comps)
        p["_included_total"] = total
        p["_languages"] = langs
        eligible.append(p)

    if return_rejected:
        return eligible, rejected
    return eligible


def score_package(
    p: dict[str, Any],
    preferred_languages: list[str],
    trip_days: int,
    theme: Optional[str],
    budget: Decimal,
) -> tuple[int, list[str]]:
    """Deterministic score with the published weights."""
    score = 0
    reasons: list[str] = []

    langs = p.get("_languages") or _split_langs(p["languages_offered"])
    matched = [lang for lang in preferred_languages if lang in langs]
    if matched:
        score += SCORE_LANGUAGE
        reasons.append(
            f"Language match: offers {', '.join(matched)} (+{SCORE_LANGUAGE})"
        )

    if int(p["duration_days"]) == trip_days:
        score += SCORE_DURATION
        reasons.append(
            f"Duration match: {p['duration_days']} days fits your dates "
            f"(+{SCORE_DURATION})"
        )

    if theme and p["theme"] == theme:
        score += SCORE_THEME
        reasons.append(f"Theme match: {p['theme']} (+{SCORE_THEME})")

    total = p.get("_included_total")
    if total is None:
        total = dec(p["base_price"])
    if total <= budget:
        score += SCORE_WITHIN_BUDGET
        reasons.append(
            f"Within budget at {total} {p['currency']} (+{SCORE_WITHIN_BUDGET})"
        )

    if not reasons:
        reasons.append("Meets your hard constraints; no bonus signals matched.")
    return score, reasons


def rank(eligible: list[dict[str, Any]], *score_args) -> list[dict[str, Any]]:
    """Deterministic sort: score desc, then price asc, then package_id asc."""
    scored = []
    for p in eligible:
        score, reasons = score_package(p, *score_args)
        scored.append((p, score, reasons))
    scored.sort(
        key=lambda t: (
            -t[1],
            t[0].get("_included_total") or dec(t[0]["base_price"]),
            t[0]["package_id"],
        )
    )
    return scored


def recommend(db: PackageProDB, request: dict[str, Any], limit: int = 3
              ) -> tuple[list[RecommendationModel], list[dict[str, Any]], list[tuple[Any, str]]]:
    city_id = request["city_id"]
    langs = list(request["preferred_languages"])
    days = pricing.trip_days(request["start_date"], request["end_date"])
    budget = dec(request["budget"]["amount"])
    currency = str(request["budget"]["currency"])
    theme = request.get("theme") or None

    packages = db.packages_by_city(city_id)
    eligible, rejected = filter_eligible(
        packages, city_id, langs, days, int(request["travelers"]),
        budget, currency, theme, db=db, return_rejected=True,
    )
    scored = rank(eligible, langs, days, theme, budget)

    city = db.city(city_id)
    city_name = city["name"] if city else city_id

    out: list[RecommendationModel] = []
    for i, (p, score, reasons) in enumerate(scored[:limit], start=1):
        total = p.get("_included_total")
        if total is None:
            total = pricing.included_total(p["base_price"], db.components(p["package_id"]))
        out.append(
            RecommendationModel(
                rank=i,
                package_id=p["package_id"],
                city_id=p["city_id"],
                city_name=city_name,
                name=p["name"],
                theme=p["theme"],
                tier=p["tier"],
                duration_days=int(p["duration_days"]),
                duration_nights=int(p["duration_nights"]),
                base_price=f"{dec(p['base_price']):.2f}",
                currency=p["currency"],
                included_total=f"{total:.2f}",
                min_group_size=int(p["min_group_size"]),
                max_group_size=int(p["max_group_size"]),
                languages_offered=_split_langs(p["languages_offered"]),
                inclusions=p["inclusions"],
                exclusions=p["exclusions"],
                description=p["description"],
                match_score=score,
                match_reasons=reasons,
                within_budget=total <= budget,
            )
        )
    return out, rejected, scored
