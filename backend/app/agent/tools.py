"""
Tools the agent can call. Every function here has a matching JSON schema in
TOOL_SCHEMAS below, which is what gets passed to the LLM as `tools=`.

Each tool currently returns MOCK data so the whole system runs with zero
external keys. Flip USE_REAL_* to True (and fill the matching keys in .env)
to swap in a real provider — the function signature and return shape stay
identical, so nothing else in the agent needs to change.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from app.config import settings

USE_REAL_FLIGHTS = bool(settings.AMADEUS_CLIENT_ID and settings.AMADEUS_CLIENT_SECRET)
USE_REAL_HOTELS = bool(settings.HOTELBEDS_API_KEY)
USE_REAL_PLACES = bool(settings.GOOGLE_PLACES_API_KEY)


# ---------------------------------------------------------------------------
# Flight search
# ---------------------------------------------------------------------------
def search_flights(origin: str, destination: str, date: str, travelers: int = 1) -> list[dict[str, Any]]:
    if USE_REAL_FLIGHTS:
        return _search_flights_amadeus(origin, destination, date, travelers)
    return _mock_flights(origin, destination, date, travelers)


def _mock_flights(origin: str, destination: str, date: str, travelers: int) -> list[dict[str, Any]]:
    airlines = ["IndiGo", "Air India", "Vistara", "SpiceJet", "Akasa Air"]
    out = []
    for airline in random.sample(airlines, k=3):
        price = random.randint(3500, 9500) * travelers
        out.append(
            {
                "airline": airline,
                "origin": origin,
                "destination": destination,
                "date": date,
                "departure_time": f"{random.randint(5, 21):02d}:{random.choice(['00', '15', '30', '45'])}",
                "duration_minutes": random.randint(70, 180),
                "price_inr": price,
                "travelers": travelers,
                "confidence": round(random.uniform(0.7, 0.98), 2),  # feeds the "confidence badge" UI feature
                "source": "mock",
            }
        )
    return sorted(out, key=lambda f: f["price_inr"])


def _search_flights_amadeus(origin: str, destination: str, date: str, travelers: int) -> list[dict[str, Any]]:
    """
    Real implementation — requires AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET
    in .env (free self-service tier: https://developers.amadeus.com).
    """
    from amadeus import Client  # imported lazily so the package is optional

    amadeus = Client(
        client_id=settings.AMADEUS_CLIENT_ID,
        client_secret=settings.AMADEUS_CLIENT_SECRET,
        hostname="test" if settings.AMADEUS_ENV == "test" else "production",
    )
    resp = amadeus.shopping.flight_offers_search.get(
        originLocationCode=origin,
        destinationLocationCode=destination,
        departureDate=date,
        adults=travelers,
        max=5,
    )
    out = []
    for offer in resp.data:
        price = float(offer["price"]["total"])
        out.append(
            {
                "airline": offer["validatingAirlineCodes"][0],
                "origin": origin,
                "destination": destination,
                "date": date,
                "departure_time": offer["itineraries"][0]["segments"][0]["departure"]["at"],
                "duration_minutes": None,
                "price_inr": price,
                "travelers": travelers,
                "confidence": 0.95,
                "source": "amadeus",
            }
        )
    return out


# ---------------------------------------------------------------------------
# Hotel search
# ---------------------------------------------------------------------------
def search_hotels(city: str, check_in: str, check_out: str, travelers: int = 1) -> list[dict[str, Any]]:
    if USE_REAL_HOTELS:
        try:
            return _search_hotels_hotelbeds(city, check_in, check_out, travelers)
        except NotImplementedError:
            pass  # real integration not wired yet — fall through to mock
    return _mock_hotels(city, check_in, check_out, travelers)


def _mock_hotels(city: str, check_in: str, check_out: str, travelers: int) -> list[dict[str, Any]]:
    names = ["The Riverside Inn", "Palm Grove Resort", "Old Town Boutique Stay", "Sunset Bay Hotel", "Heritage Courtyard"]
    nights = max(
        1,
        (datetime.fromisoformat(check_out) - datetime.fromisoformat(check_in)).days
        if _looks_like_date(check_in) and _looks_like_date(check_out)
        else 3,
    )
    out = []
    for name in random.sample(names, k=3):
        per_night = random.randint(1800, 6500)
        out.append(
            {
                "name": name,
                "city": city,
                "check_in": check_in,
                "check_out": check_out,
                "nights": nights,
                "rating": round(random.uniform(3.6, 4.8), 1),
                "price_per_night_inr": per_night,
                "total_price_inr": per_night * nights,
                "confidence": round(random.uniform(0.7, 0.97), 2),
                "source": "mock",
            }
        )
    return sorted(out, key=lambda h: h["total_price_inr"])


def _looks_like_date(s: str) -> bool:
    try:
        datetime.fromisoformat(s)
        return True
    except Exception:
        return False


def _search_hotels_hotelbeds(city: str, check_in: str, check_out: str, travelers: int) -> list[dict[str, Any]]:
    """
    Real implementation stub — requires HOTELBEDS_API_KEY / HOTELBEDS_API_SECRET
    (https://developer.hotelbeds.com). Hotelbeds auth uses an X-Signature
    header (SHA256 of key+secret+timestamp) — implement in a real deploy.
    """
    raise NotImplementedError("Wire Hotelbeds signed request here; falls back to mock until then.")


# ---------------------------------------------------------------------------
# Nearby places / activities
# ---------------------------------------------------------------------------
def search_nearby_places(city: str, interest: str = "attractions") -> list[dict[str, Any]]:
    if USE_REAL_PLACES:
        try:
            return _search_places_google(city, interest)
        except NotImplementedError:
            pass  # real integration not wired yet — fall through to mock
    sample = [
        {"name": f"{city} Old Fort", "category": "heritage", "avg_cost_inr": 300},
        {"name": f"{city} Night Market", "category": "food", "avg_cost_inr": 800},
        {"name": f"{city} Lakeside Walk", "category": "outdoors", "avg_cost_inr": 0},
        {"name": f"{city} Art Museum", "category": "culture", "avg_cost_inr": 400},
    ]
    return sample


def _search_places_google(city: str, interest: str) -> list[dict[str, Any]]:
    """Real implementation stub — requires GOOGLE_PLACES_API_KEY."""
    raise NotImplementedError("Wire Google Places Text Search API here.")


# ---------------------------------------------------------------------------
# Budget check — the tool the agent MUST call before proposing a cart
# ---------------------------------------------------------------------------
def check_budget(running_total_inr: float, cap_inr: float) -> dict[str, Any]:
    remaining = cap_inr - running_total_inr
    # FIX B7: Return 0.0 (not None) when cap is 0 so the frontend can safely
    # call .toLocaleString() / display the value without a TypeError.
    pct_used = round((running_total_inr / cap_inr) * 100, 1) if cap_inr else 0.0
    return {
        "running_total_inr": running_total_inr,
        "cap_inr": cap_inr,
        "remaining_inr": remaining,
        "pct_used": pct_used,
        "over_budget": remaining < 0,
        "overage_inr": max(0, -remaining),
    }


# ---------------------------------------------------------------------------
# JSON schemas passed to the LLM as `tools=`
# ---------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search flights between two cities on a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "travelers": {"type": "integer", "default": 1},
                },
                "required": ["origin", "destination", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "Search hotels in a city for a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "check_in": {"type": "string", "description": "YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "YYYY-MM-DD"},
                    "travelers": {"type": "integer", "default": 1},
                },
                "required": ["city", "check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_nearby_places",
            "description": "Find nearby attractions/activities in a city, optionally filtered by interest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "interest": {"type": "string", "default": "attractions"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_budget",
            "description": "Check the running trip total against the traveler's spend cap. MUST be called before proposing a final cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "running_total_inr": {"type": "number"},
                    "cap_inr": {"type": "number"},
                },
                "required": ["running_total_inr", "cap_inr"],
            },
        },
    },
]

TOOL_REGISTRY = {
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "search_nearby_places": search_nearby_places,
    "check_budget": check_budget,
}
