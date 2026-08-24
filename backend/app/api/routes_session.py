from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.agent.graph import run_phase1, run_phase2_select_flight, run_phase3_select_hotel
from app.config import settings
from app.db.database import load_state, save_state
from app.models import NegotiationChoiceRequest, SelectionRequest, SessionResponse, StartSessionRequest

router = APIRouter(prefix="/session", tags=["session"])


def _to_response(state: dict) -> SessionResponse:
    return SessionResponse(
        session_id=state["session_id"],
        status=state.get("status", "planning"),
        plan_steps=state.get("plan_steps", []),
        trace=state.get("trace", []),
        flight_options=state.get("flight_options", []),
        hotel_options=state.get("hotel_options", []),
        place_options=state.get("place_options", []),
        chosen_flight=state.get("chosen_flight"),
        chosen_hotel=state.get("chosen_hotel"),
        running_total=state.get("running_total", 0),
        budget_cap=state.get("budget_cap", 0),
        budget_decisions=state.get("budget_decisions", []),
        negotiation_options=state.get("negotiation_options", []),
        cart=state.get("cart"),
        clarifying_question=state.get("clarifying_question"),
    )


@router.post("", response_model=SessionResponse)
async def start_session(req: StartSessionRequest) -> SessionResponse:
    """Phase 1: Intake → search flights + places → pause for user to pick a flight."""
    session_id = str(uuid.uuid4())
    initial_state = {
        "session_id": session_id,
        "goal": req.goal,
        "origin": req.origin,
        "destination": req.destination,
        "depart_date": req.depart_date,
        "return_date": req.return_date,
        "travelers": req.travelers,
        "budget_cap": req.budget_cap or settings.DEFAULT_SESSION_SPEND_CAP_USD,
        "currency": req.currency,
    }
    result_state = run_phase1(initial_state)
    await save_state(session_id, result_state)
    return _to_response(result_state)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    state = await load_state(session_id)
    if not state:
        raise HTTPException(404, "Session not found")
    return _to_response(state)


@router.post("/{session_id}/select-flight", response_model=SessionResponse)
async def select_flight(session_id: str, req: SelectionRequest) -> SessionResponse:
    """Phase 2: User picks a flight → budget check → search hotels → pause for hotel pick."""
    state = await load_state(session_id)
    if not state:
        raise HTTPException(404, "Session not found")
    if state.get("status") != "select_flight":
        raise HTTPException(400, "Session is not waiting for a flight selection.")

    result_state = run_phase2_select_flight(state, req.choice_index)
    await save_state(session_id, result_state)
    return _to_response(result_state)


@router.post("/{session_id}/select-hotel", response_model=SessionResponse)
async def select_hotel(session_id: str, req: SelectionRequest) -> SessionResponse:
    """Phase 3: User picks a hotel → budget check → propose cart → pause for confirmation."""
    state = await load_state(session_id)
    if not state:
        raise HTTPException(404, "Session not found")
    if state.get("status") != "select_hotel":
        raise HTTPException(400, "Session is not waiting for a hotel selection.")

    result_state = run_phase3_select_hotel(state, req.choice_index)
    await save_state(session_id, result_state)
    return _to_response(result_state)


@router.post("/{session_id}/negotiate", response_model=SessionResponse)
async def resolve_negotiation(session_id: str, req: NegotiationChoiceRequest) -> SessionResponse:
    """
    Handles budget negotiation — user picks a trade-off when a budget check fails.
    After resolving, re-runs the appropriate phase.
    """
    state = await load_state(session_id)
    if not state:
        raise HTTPException(404, "Session not found")

    if req.choice == "raise_cap":
        if not req.new_cap or req.new_cap <= 0:
            raise HTTPException(422, "new_cap is required and must be > 0 when choice is 'raise_cap'.")
        state["budget_cap"] = req.new_cap
    elif req.choice == "approve_overage":
        last_decision = (state.get("budget_decisions") or [{}])[-1]
        overage = last_decision.get("overage", 0)
        state["budget_cap"] = state.get("running_total", 0) + max(0, overage)
    elif req.choice == "remove_item":
        if state.get("chosen_hotel"):
            state["chosen_hotel"] = None
        elif state.get("chosen_flight"):
            state["chosen_flight"] = None

    state["needs_user_decision"] = False

    # Determine which phase to re-run based on what's been selected
    if state.get("chosen_flight") and not state.get("chosen_hotel"):
        # Flight was chosen, hotel search needs to happen
        # Re-select the same flight with updated budget
        flight_idx = None
        for i, opt in enumerate(state.get("flight_options", [])):
            if opt.get("airline") == state["chosen_flight"].get("airline"):
                flight_idx = i
                break
        if flight_idx is not None:
            state["running_total"] = 0.0  # Reset running total for re-check
            result_state = run_phase2_select_flight(state, flight_idx)
        else:
            state["status"] = "select_flight"
            result_state = state
    elif not state.get("chosen_flight"):
        # Go back to flight selection
        state["status"] = "select_flight"
        result_state = state
    else:
        # Both chosen, re-run hotel selection
        hotel_idx = None
        for i, opt in enumerate(state.get("hotel_options", [])):
            if opt.get("name") == state["chosen_hotel"].get("name"):
                hotel_idx = i
                break
        if hotel_idx is not None:
            # Reset to just flight cost
            state["running_total"] = state["chosen_flight"].get("price_inr", 0)
            result_state = run_phase3_select_hotel(state, hotel_idx)
        else:
            state["status"] = "select_hotel"
            result_state = state

    await save_state(session_id, result_state)
    return _to_response(result_state)


@router.post("/{session_id}/confirm", response_model=SessionResponse)
async def confirm_booking(session_id: str) -> SessionResponse:
    """
    The hard confirmation gate. Booking/payment is mocked —
    wire a real payment processor only behind this endpoint.
    """
    state = await load_state(session_id)
    if not state:
        raise HTTPException(404, "Session not found")
    if state.get("status") != "awaiting_confirmation":
        raise HTTPException(400, "Nothing awaiting confirmation for this session")

    state["status"] = "confirmed"
    state.setdefault("trace", []).append(
        {"node": "confirm_booking", "kind": "decision",
         "content": "User confirmed. Booking mocked (wire real payment provider here)."}
    )
    await save_state(session_id, state)
    return _to_response(state)
