"""
Guide matching endpoint.

GET /api/guides/match
  Query params:
    city_id         — filter to a specific city
    languages       — comma-separated BCP-47 tags (e.g. hi,en-IN)
    specialisation  — e.g. food, history, trekking, wildlife
    max_day_rate    — maximum day rate in rupees (Decimal)
    from_date       — YYYY-MM-DD (start of availability window)
    to_date         — YYYY-MM-DD (end of availability window, default +30 days)
    limit           — max results (default 10, max 50)

GET /api/guides/{guide_id}
  Returns a single guide's full profile.

GET /api/guides/cities
  Returns all active cities (for dropdowns).

GET /api/guides/languages
  Returns all supported BCP-47 language tags.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.packagepro import get_cities, get_languages, get_matching_guides, query_one

router = APIRouter(prefix="/guides", tags=["guides"])


# ---------------------------------------------------------------------------
# Guide matching
# ---------------------------------------------------------------------------

@router.get("/match")
async def match_guides(
    city_id: Optional[str] = Query(None, description="Filter by city ID (e.g. cty_c07454f1)"),
    languages: Optional[str] = Query(None, description="Comma-separated BCP-47 tags, e.g. hi,en-IN"),
    specialisation: Optional[str] = Query(None, description="Primary or secondary specialisation"),
    max_day_rate: Optional[str] = Query(None, description="Max day rate (Decimal string, in guide's currency)"),
    from_date: Optional[str] = Query(None, description="Availability window start YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="Availability window end YYYY-MM-DD"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Find tour guides matching language, specialisation, budget and availability.
    All money comparisons use Decimal — never float.
    """
    # Parse languages list
    lang_list: list[str] | None = None
    if languages:
        lang_list = [l.strip() for l in languages.split(",") if l.strip()]

    # Parse max day rate as Decimal
    max_rate: Decimal | None = None
    if max_day_rate:
        try:
            max_rate = Decimal(max_day_rate)
        except InvalidOperation:
            raise HTTPException(422, f"Invalid max_day_rate value: {max_day_rate!r}")

    # Default availability window: today → +30 days
    if from_date is None:
        from_date = date.today().isoformat()
    if to_date is None:
        to_date = (date.today() + timedelta(days=30)).isoformat()

    guides = get_matching_guides(
        languages=lang_list,
        specialisation=specialisation,
        max_day_rate=max_rate,
        city_id=city_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )

    return {
        "count": len(guides),
        "from_date": from_date,
        "to_date": to_date,
        "guides": guides,
    }


# ---------------------------------------------------------------------------
# Single guide
# ---------------------------------------------------------------------------

@router.get("/{guide_id}")
async def get_guide(guide_id: str):
    """Return the full profile for a single guide."""
    row = query_one(
        """
        SELECT g.*, c.city_name
        FROM tour_guides g
        LEFT JOIN cities c ON c.city_id = g.city_id
        WHERE g.guide_id = ?
        """,
        (guide_id,),
    )
    if not row:
        raise HTTPException(404, f"Guide {guide_id!r} not found")
    return row


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

@router.get("/ref/cities")
async def list_cities(country_iso2: str = Query("IN")):
    """Return active cities for populating dropdowns."""
    return get_cities(country_iso2=country_iso2)


@router.get("/ref/languages")
async def list_languages():
    """Return all BCP-47 language tags supported by the PackagePro dataset."""
    return get_languages()
