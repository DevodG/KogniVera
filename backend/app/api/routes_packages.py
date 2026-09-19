"""
Package retrieval and component swapping endpoints.

GET /api/packages
  Search tour packages with filters for city, language, theme, duration, price.

GET /api/packages/{package_id}/components
  List all components for a package.

GET /api/packages/{package_id}/components/{component_id}/alternatives
  List alternatives for a component.

POST /api/packages/{package_id}/swap
  Swap one component for another and recompute cost.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.packagepro import (
    compute_swap_delta,
    get_alternatives,
    get_components,
    get_packages,
    query_one,
)

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("")
async def search_packages(
    city_id: Optional[str] = Query(None),
    languages: Optional[str] = Query(None, description="Comma-separated BCP-47 tags"),
    theme: Optional[str] = Query(None),
    min_days: Optional[int] = Query(None),
    max_days: Optional[int] = Query(None),
    max_price: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
):
    """Search and filter tour packages."""
    lang_list = [l.strip() for l in languages.split(",")] if languages else None
    
    price_val = None
    if max_price:
        try:
            price_val = Decimal(max_price)
        except InvalidOperation:
            raise HTTPException(422, "Invalid max_price")

    packages = get_packages(
        city_id=city_id,
        languages=lang_list,
        theme=theme,
        min_days=min_days,
        max_days=max_days,
        max_price=price_val,
        limit=limit,
    )
    return {"count": len(packages), "packages": packages}


@router.get("/{package_id}/components")
async def list_components(package_id: str):
    """List all components for a package."""
    # Verify package exists
    if not query_one("SELECT 1 FROM tour_packages WHERE package_id = ?", (package_id,)):
        raise HTTPException(404, "Package not found")
        
    return {"components": get_components(package_id)}


@router.get("/{package_id}/components/{component_id}/alternatives")
async def list_alternatives(package_id: str, component_id: str):
    """List valid alternatives for swapping out a component."""
    return {"alternatives": get_alternatives(component_id)}


class SwapRequest(BaseModel):
    from_component_id: str
    to_component_id: str


@router.post("/{package_id}/swap")
async def swap_component(package_id: str, req: SwapRequest):
    """
    Dry-run swap endpoint that computes the new price delta.
    Does not persist the swap to the read-only DB; the frontend uses this
    to update its running total and re-check the budget guard.
    """
    try:
        delta = compute_swap_delta(req.from_component_id, req.to_component_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
        
    # Return the delta as a string to preserve precision
    return {
        "status": "success",
        "delta_inr": str(delta),
        "from_component_id": req.from_component_id,
        "to_component_id": req.to_component_id,
    }
