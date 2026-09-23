"""Waypoint API routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from ..agent.solver import Solver
from ..db.packagepro import PackageProDB
from ..db.session import SessionDB
from ..models import (
    CityModel,
    ConfirmRequest,
    HealthModel,
    LanguageModel,
    NegotiateRequest,
    PlannerRequest,
    SelectGuideRequest,
    SwapRequest,
)

router = APIRouter()


def _pro() -> PackageProDB:
    from ..main import get_pro

    return get_pro()


def _sessions() -> SessionDB:
    from ..main import get_sessions

    return get_sessions()


def _solver() -> Solver:
    return Solver(_pro(), _sessions())


@router.get("/health", response_model=HealthModel)
def health() -> HealthModel:
    pro = _pro()
    return HealthModel(
        status="ok",
        packagepro_db="connected (read-only)",
        packagepro_path=pro.path,
        session_db=_sessions().path,
        rows=pro.table_counts(),
        ai_key_configured=False,
    )


@router.get("/cities", response_model=list[CityModel])
def cities(limit: int = 200) -> list[CityModel]:
    rows = _pro().cities(limit=limit)
    return [CityModel(**r) for r in rows]


@router.get("/languages", response_model=list[LanguageModel])
def languages() -> list[LanguageModel]:
    rows = _pro().languages()
    return [
        LanguageModel(
            bcp47=r["bcp47"],
            english_name=r["english_name"],
            native_name=r["native_name"],
            script=r["script"],
        )
        for r in rows
    ]


@router.get("/city-packages/{city_id}")
def city_packages(city_id: str) -> list[dict[str, Any]]:
    """Available packages for a city — durations, themes, price ranges.

    The frontend uses this to hint valid date ranges and budget when the
    user selects a destination.
    """
    pro = _pro()
    packages = pro.packages_by_city(city_id)
    out = []
    for p in packages:
        from ..services import pricing as _pricing
        comps = pro.components(p["package_id"])
        total = _pricing.included_total(p["base_price"], comps)
        out.append({
            "package_id": p["package_id"],
            "name": p["name"],
            "theme": p["theme"],
            "tier": p["tier"],
            "duration_days": int(p["duration_days"]),
            "base_price": str(p["base_price"]),
            "included_total": f"{total:.2f}",
            "currency": p["currency"],
            "min_group_size": int(p["min_group_size"]),
            "max_group_size": int(p["max_group_size"]),
            "languages_offered": [t.strip() for t in (p["languages_offered"] or "").split(",") if t.strip()],
        })
    return out


@router.post("/planner/recommend")
def recommend(request: PlannerRequest) -> dict[str, Any]:
    solver = _solver()
    try:
        return solver.plan(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/sessions/{session_id}/select-package")
def select_package(session_id: str, package_id: str) -> dict[str, Any]:
    solver = _solver()
    try:
        return solver.select_package(session_id, package_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    s = _sessions().get_session(session_id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return _solver()._session_view(session_id)


@router.get("/sessions/{session_id}/itinerary")
def get_itinerary(session_id: str) -> dict[str, Any]:
    from ..services.itinerary import ItineraryService

    try:
        it = ItineraryService(_pro(), _sessions(), session_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return it.itinerary().model_dump()


@router.post("/sessions/{session_id}/swap-component")
def swap_component(session_id: str, request: SwapRequest) -> dict[str, Any]:
    solver = _solver()
    try:
        return solver.swap(session_id, request.component_id, request.replacement_component_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/sessions/{session_id}/select-guide")
def select_guide(session_id: str, request: SelectGuideRequest) -> dict[str, Any]:
    solver = _solver()
    try:
        return solver.select_guide(session_id, request.guide_id, request.service)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/sessions/{session_id}/negotiate")
def negotiate(session_id: str, request: NegotiateRequest) -> dict[str, Any]:
    solver = _solver()
    try:
        return solver.negotiate(
            session_id,
            request.option,
            new_budget=request.new_budget.amount if request.new_budget else None,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/sessions/{session_id}/trust-receipt")
def trust_receipt(session_id: str) -> dict[str, Any]:
    solver = _solver()
    try:
        return solver.trust_receipt(session_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/sessions/{session_id}/confirm")
def confirm(session_id: str, request: ConfirmRequest) -> dict[str, Any]:
    solver = _solver()
    try:
        return solver.confirm(session_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/sessions/{session_id}/guides")
def session_guides(session_id: str) -> dict[str, Any]:
    """Guides matched to this session's city, language, theme and dates."""
    from ..services.guides import match_guides, to_guide_model

    s = _sessions().get_session(session_id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    entries = match_guides(
        _pro(),
        s["city_id"],
        s["request"]["preferred_languages"],
        s.get("theme"),
        s["start_date"],
        s["end_date"],
    )
    return {
        "session_id": session_id,
        "guides": [
            to_guide_model(e, selected=(e["guide"]["guide_id"] == s.get("selected_guide_id"))).model_dump()
            for e in entries
        ],
    }
