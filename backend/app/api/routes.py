"""
API routes.

Contract: the server owns the total. Every cost-adding path (swap, optional
add-on, guide) runs through the BudgetGuard on the server; the client only
renders what it is given. Money crosses the wire as {amount: str, currency},
never as a JSON number.
"""
from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.money import Money
from app.core.session import Session
from app.data.packagepro import (
    get_components,
    get_package,
    get_packages,
    get_price_explanation,
    get_swap_alternatives,
)
from app.intel.engine import (
    Traveler,
    advise_swap,
    explain_cold_start,
    recommend_guides,
    recommend_packages,
    score_package,
)

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# In-memory session store (SQLite-backed swap-in point later; a 24h demo does
# not need a durable store, and resumability is a design-doc nice-to-have).
# ---------------------------------------------------------------------------

_sessions: dict[str, Session] = {}


def _get(session_id: str) -> Session:
    s = _sessions.get(session_id)
    if s is None:
        raise HTTPException(404, f"no session {session_id}")
    return s


def _money(amount: str | Decimal, currency: str) -> Money:
    try:
        return Money(amount, currency)
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, str(exc))


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------

class IntakeRequest(BaseModel):
    languages: list[str] = Field(default_factory=list)
    budget_band: str = ""
    travel_style: str = ""
    traveller_type: str = ""
    pace: str = ""
    interests: list[str] = Field(default_factory=list)
    budget_cap: str = Field(..., description="Decimal string, e.g. 25000.00")
    currency: str = "INR"


@router.post("/session")
def create_session(req: IntakeRequest):
    """Start a planning session: traveler profile + hard budget cap."""
    session_id = uuid.uuid4().hex[:12]
    s = Session(
        session_id=session_id,
        languages=tuple(req.languages),
        budget_band=req.budget_band,
        travel_style=req.travel_style,
        traveller_type=req.traveller_type,
        pace=req.pace,
        interests=tuple(req.interests),
    )
    cap = _money(req.budget_cap, req.currency)
    s.init_guard(cap)
    cold = explain_cold_start(s.traveler)
    s.say("intake", "reasoning", f"Traveler profile recorded. {cold['evidence']}")
    if cold["cold_start"]:
        s.say("intake", "reasoning",
              "Ranking will use declared preferences only — no inferred history.")
    _sessions[session_id] = s
    return {"session_id": session_id, "cold_start": cold, "state": s.to_state()}


@router.get("/session/{session_id}")
def get_session_state(session_id: str):
    return _get(session_id).to_state()


# ---------------------------------------------------------------------------
# Packages — browse + rank
# ---------------------------------------------------------------------------

@router.get("/packages")
def list_packages(
    languages: str | None = None,
    theme: str | None = None,
    city_id: str | None = None,
    min_days: int | None = None,
    max_days: int | None = None,
    limit: int = 24,
):
    """Browse/filter packages. `languages` is comma-separated BCP-47 (R6)."""
    langs = [l.strip() for l in languages.split(",") if l.strip()] if languages else None
    pkgs = get_packages(
        languages=langs, theme=theme, city_id=city_id,
        min_days=min_days, max_days=max_days, limit=limit,
    )
    return {"count": len(pkgs), "packages": [_pkg(p) for p in pkgs]}


@router.get("/packages/recommend/{session_id}")
def recommend(session_id: str, limit: int = 8):
    """The AI feature: rank packages for THIS traveler, with reasons."""
    s = _get(session_id)
    ranked = recommend_packages(s.traveler, limit=limit)
    cold = explain_cold_start(s.traveler)
    s.say("recommend", "tool_call", "recommend_packages(traveler)")
    return {
        "cold_start": cold,
        "results": [
            {
                "package": _pkg(p),
                "score": scored.to_dict(),
            }
            for p, scored in ranked
        ],
    }


@router.get("/packages/{package_id}")
def package_detail(package_id: str):
    pkg = get_package(package_id)
    if pkg is None:
        raise HTTPException(404, "package not found")
    comps = get_components(package_id)
    return {
        "package": _pkg(pkg),
        "components": [_comp(c) for c in comps],
        "by_day": {
            str(day): [_comp(c) for c in comps if c.day_index == day]
            for day in sorted({c.day_index for c in comps})
        },
    }


# ---------------------------------------------------------------------------
# Choose + customize
# ---------------------------------------------------------------------------

@router.post("/session/{session_id}/choose/{package_id}")
def choose_package(session_id: str, package_id: str):
    s = _get(session_id)
    try:
        breakdown = s.choose_package(package_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    return {
        "applied": True,
        "breakdown": breakdown.to_dict(),
        "state": s.to_state(),
    }


class SwapRequest(BaseModel):
    from_component_id: str
    to_component_id: str


@router.post("/session/{session_id}/swap")
def swap_component(session_id: str, req: SwapRequest):
    """
    The core PS-04 operation. Server-authoritative: the guard decides, the
    total moves only if the cap allows, and negotiation options come back
    when it doesn't.
    """
    s = _get(session_id)
    try:
        result = s.swap(req.from_component_id, req.to_component_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {**result, "state": s.to_state()}


@router.post("/session/{session_id}/unswap/{component_id}")
def revert_swap(session_id: str, component_id: str):
    s = _get(session_id)
    try:
        result = s.unswap(component_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    return {**result, "state": s.to_state()}


@router.post("/session/{session_id}/optional/{component_id}")
def add_optional(session_id: str, component_id: str):
    s = _get(session_id)
    try:
        result = s.add_optional(component_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {**result, "state": s.to_state()}


@router.delete("/session/{session_id}/optional/{component_id}")
def remove_optional(session_id: str, component_id: str):
    s = _get(session_id)
    try:
        result = s.remove_optional(component_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {**result, "state": s.to_state()}


# ---------------------------------------------------------------------------
# Swap advice — the AI on the customize screen
# ---------------------------------------------------------------------------

@router.get("/session/{session_id}/swap-advice/{component_id}")
def swap_advice(session_id: str, component_id: str, limit: int = 5):
    """Rank the alternatives for a component with per-signal reasoning."""
    s = _get(session_id)
    remaining = s.guard.remaining() if s.guard else Money("0", "INR")
    ranked = advise_swap(component_id, s.traveler, remaining, limit=limit)
    return {
        "component_id": component_id,
        "alternatives": [
            {"component": _comp(c), "score": scored.to_dict()}
            for c, scored in ranked
        ],
    }


# ---------------------------------------------------------------------------
# Guides — match + availability
# ---------------------------------------------------------------------------

@router.get("/guides")
def list_guides(
    languages: str | None = None,
    specialisation: str | None = None,
    city_id: str | None = None,
    on_date: str | None = None,
    limit: int = 12,
):
    """Filter guides; `on_date` gates on real availability."""
    langs = [l.strip() for l in languages.split(",") if l.strip()] if languages else None
    from app.data.packagepro import get_guides, guides_available_on

    pool = (
        guides_available_on(langs, specialisation, on_date, city_id=city_id, limit=limit)
        if on_date
        else get_guides(languages=langs, specialisation=specialisation, city_id=city_id, limit=limit)
    )
    return {"count": len(pool), "guides": [_guide(g) for g in pool]}


@router.get("/guides/recommend/{session_id}")
def recommend_guides_route(session_id: str, on_date: str | None = None, limit: int = 6):
    s = _get(session_id)
    ranked = recommend_guides(s.traveler, on_date=on_date, limit=limit)
    s.say("guide", "tool_call", f"recommend_guides(on_date={on_date})")
    return {
        "results": [
            {"guide": _guide(g), "score": scored.to_dict()}
            for g, scored in ranked
        ],
    }


@router.post("/session/{session_id}/guide/{guide_id}")
def attach_guide(session_id: str, guide_id: str, on_date: str | None = None):
    """Attach a guide at its real (peak-adjusted) day rate, guarded."""
    from app.data.packagepro import guides_available_on, get_guides

    s = _get(session_id)
    pool = (
        guides_available_on(list(s.languages) or None, None, on_date, limit=60)
        if on_date
        else get_guides(languages=list(s.languages) or None, limit=60)
    )
    match = next((g for g in pool if g["guide_id"] == guide_id), None)
    if match is None:
        raise HTTPException(404, f"guide {guide_id} not available on {on_date}")
    result = s.choose_guide(match)
    return {**result, "state": s.to_state()}


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------

@router.get("/explain/{entity_id}")
def explain_price(entity_id: str, on_date: str | None = None):
    """Why does this cost what it costs? Real factors from price_history."""
    pe = get_price_explanation(entity_id, on_date=on_date)
    if pe is None:
        return {
            "entity_id": entity_id,
            "available": False,
            "note": "no price_history rows for this entity",
        }
    return {
        "entity_id": entity_id,
        "entity_type": pe["entity_type"],
        "effective_date": pe["effective_date"],
        "available": True,
        "price": pe["price"].to_dict(),
        "baseline_price": pe["baseline_price"].to_dict(),
        "factors": {
            "demand_index": str(pe["demand_index"]),
            "occupancy_pct": str(pe["occupancy_pct"]),
            "lead_time_factor": str(pe["lead_time_factor"]),
            "seasonality_factor": str(pe["seasonality_factor"]),
            "event_factor": str(pe["event_factor"]),
            "competitor_factor": str(pe["competitor_factor"]),
            "bound_clamped": pe["bound_clamped"],
        },
        "explanation": pe["explanation"],
    }


# ---------------------------------------------------------------------------
# Serialisers — Money always as a {amount, currency} pair (R3)
# ---------------------------------------------------------------------------

def _pkg(p) -> dict:
    return {
        "package_id": p.package_id,
        "city_id": p.city_id,
        "name": p.name,
        "theme": p.theme,
        "tier": p.tier,
        "duration_days": p.duration_days,
        "duration_nights": p.duration_nights,
        "base_price": p.base_price.to_dict(),
        "difficulty": p.difficulty,
        "languages_offered": p.languages_offered,
        "description": p.description,
    }


def _comp(c) -> dict:
    return {
        "component_id": c.component_id,
        "component_type": c.component_type,
        "entity_type": c.entity_type,
        "entity_id": c.entity_id,
        "day_index": c.day_index,
        "slot": c.slot,
        "title": c.title,
        "quantity": c.quantity,
        "price_delta": c.price_delta.to_dict(),
        "is_optional": c.is_optional,
        "is_swappable": c.is_swappable,
        "swap_group": c.swap_group,
    }


def _guide(g: dict) -> dict:
    rate = g.get("peak_day_rate") or g.get("day_rate")
    return {
        "guide_id": g["guide_id"],
        "display_name": g["display_name"],
        "languages": g.get("languages", []),
        "specialisation": g.get("specialisation"),
        "secondary_specialisation": g.get("secondary_specialisation"),
        "years_experience": g.get("years_experience"),
        "rating": str(g["rating"]) if g.get("rating") is not None else None,
        "review_count": g.get("review_count"),
        "day_rate": rate.to_dict() if rate is not None else None,
        "currency": g.get("currency"),
        "certified": g.get("certified"),
        "bio": g.get("bio"),
        "on_date": g.get("on_date"),
    }
