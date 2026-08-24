from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    goal: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    depart_date: Optional[str] = None
    return_date: Optional[str] = None
    travelers: int = 1
    budget_cap: Optional[float] = None
    currency: str = "INR"


class SelectionRequest(BaseModel):
    """User picks a flight or hotel by index from the options list."""
    choice_index: int


class NegotiationChoiceRequest(BaseModel):
    """User's response to a budget-negotiation prompt."""
    choice: str
    new_cap: Optional[float] = None  # required if choice == "raise_cap"


class SessionResponse(BaseModel):
    session_id: str
    status: str
    plan_steps: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    flight_options: list[dict[str, Any]] = []
    hotel_options: list[dict[str, Any]] = []
    place_options: list[dict[str, Any]] = []
    chosen_flight: Optional[dict[str, Any]] = None
    chosen_hotel: Optional[dict[str, Any]] = None
    running_total: float = 0
    budget_cap: float = 0
    budget_decisions: list[dict[str, Any]] = []
    negotiation_options: list[str] = []
    cart: Optional[dict[str, Any]] = None
    clarifying_question: Optional[str] = None
