"""
The agent's brain — now as a set of composable phases instead of a single
monolithic state machine.

New interactive flow (user-driven selection):

  Phase 1:  intake → plan → search_flights + search_places → PAUSE (select_flight)
  Phase 2:  user picks flight → budget_check → search_hotels → PAUSE (select_hotel)
  Phase 3:  user picks hotel → budget_check → propose_cart → PAUSE (awaiting_confirmation)
  Phase 4:  user confirms → done

This is MUCH faster than the old LLM-pick flow because the user drives
selection — no waiting for an LLM round-trip just to pick the cheapest flight.

Every node still appends to `trace` (for the live "agent thinking" feed in the
UI) and every budget decision is logged in `budget_decisions`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from app.agent.budget_guard import BudgetGuard
from app.agent.state import AgentState
from app.agent.tools import search_flights, search_hotels, search_nearby_places


def _trace(state: dict, node: str, kind: str, content: str) -> None:
    if "trace" not in state:
        state["trace"] = []
    state["trace"].append({"node": node, "kind": kind, "content": content})


def _plan_step(state: dict, step_id: str, title: str, status: str) -> None:
    steps = state.setdefault("plan_steps", [])
    for s in steps:
        if s["id"] == step_id:
            s["status"] = status
            return
    steps.append({"id": step_id, "title": title, "status": status})


# ---------------------------------------------------------------------------
# Phase 1: Intake → Search flights + places → Pause for user selection
# ---------------------------------------------------------------------------
def run_phase1(state: dict) -> dict:
    """
    Called on initial session start. Validates input, searches flights and
    nearby places, then pauses with status='select_flight' so the user
    can pick a flight from the options.
    """
    # -- Intake validation --
    required = ["origin", "destination", "depart_date", "budget_cap"]
    missing = [f for f in required if not state.get(f)]
    if missing:
        state["status"] = "needs_input"
        state["clarifying_question"] = (
            f"Before I plan anything, I need: {', '.join(missing)}. Could you share those?"
        )
        _trace(state, "intake", "decision", f"Missing fields: {missing}")
        return state

    state["currency"] = state.get("currency") or "INR"
    state["travelers"] = state.get("travelers") or 1
    state["trace"] = []
    state["plan_steps"] = []
    state["budget_decisions"] = []
    state["running_total"] = 0.0
    state["status"] = "planning"
    _trace(state, "intake", "reasoning", "All required fields present. Building plan.")

    # -- Build visible plan --
    plan = [
        ("search_flights", "Search flights"),
        ("select_flight", "You pick a flight"),
        ("budget_check_1", "Check budget after flight"),
        ("search_hotels", "Search hotels"),
        ("select_hotel", "You pick a hotel"),
        ("budget_check_2", "Check budget after hotel"),
        ("propose_cart", "Review and confirm your trip"),
    ]
    for step_id, title in plan:
        _plan_step(state, step_id, title, "pending")
    _trace(state, "plan", "reasoning", "Plan created. You'll pick every item — nothing is auto-booked.")

    # -- Search flights --
    _plan_step(state, "search_flights", "Search flights", "in_progress")
    options = search_flights(
        state["origin"], state["destination"], state["depart_date"], state["travelers"]
    )
    state["flight_options"] = options
    _trace(state, "search_flights", "tool_call",
           f"search_flights({state['origin']} → {state['destination']}, {state['depart_date']})")
    cheapest = options[0]["price_inr"] if options else "n/a"
    _trace(state, "search_flights", "tool_result",
           f"{len(options)} options found, cheapest ₹{cheapest}")
    _plan_step(state, "search_flights", "Search flights", "done")

    # -- Search nearby places (show alongside flights for context) --
    places = search_nearby_places(state["destination"])
    state["place_options"] = places
    _trace(state, "search_places", "tool_call",
           f"search_nearby_places({state['destination']})")
    _trace(state, "search_places", "tool_result",
           f"{len(places)} attractions/activities found")

    # -- Pause for user to pick a flight --
    _plan_step(state, "select_flight", "You pick a flight", "in_progress")
    state["status"] = "select_flight"
    _trace(state, "select_flight", "decision",
           "Flights ready — pick the one you like. Budget guard is watching.")
    return state


# ---------------------------------------------------------------------------
# Phase 2: User selected a flight → budget check → search hotels → pause
# ---------------------------------------------------------------------------
def run_phase2_select_flight(state: dict, choice_index: int) -> dict:
    """
    Called when the user picks a flight. Runs budget check, searches hotels,
    then pauses with status='select_hotel'.
    """
    options = state.get("flight_options") or []
    if not options:
        state["status"] = "failed"
        _trace(state, "select_flight", "decision", "No flight options available.")
        return state

    # Clamp index
    idx = max(0, min(choice_index, len(options) - 1))
    chosen = options[idx]
    state["chosen_flight"] = {
        **chosen,
        "agent_reasoning": "Selected by you.",
        "agent_confidence": 1.0,
    }
    _plan_step(state, "select_flight", "You pick a flight", "done")
    _trace(state, "select_flight", "decision",
           f"You picked {chosen['airline']} for ₹{chosen['price_inr']}.")

    # -- Budget check for flight --
    amount = chosen.get("price_inr", 0)
    _plan_step(state, "budget_check_1", "Check budget after flight", "in_progress")
    guard = BudgetGuard(cap=state["budget_cap"], currency=state.get("currency", "INR"))
    guard.running_total = state.get("running_total", 0.0)
    decision = guard.add_cost(amount, f"Flight ({chosen['airline']})")
    state["running_total"] = guard.running_total
    state.setdefault("budget_decisions", []).append({
        "allowed": decision.allowed,
        "running_total": decision.running_total,
        "cap": decision.cap,
        "overage": decision.overage,
        "message": decision.message,
        "negotiation_options": decision.negotiation_options,
    })
    _trace(state, "budget_check", "decision", decision.message)

    if not decision.allowed:
        state["status"] = "needs_input"
        state["needs_user_decision"] = True
        state["negotiation_options"] = decision.negotiation_options
        _plan_step(state, "budget_check_1", "Check budget after flight", "failed")
        return state

    state["needs_user_decision"] = False
    _plan_step(state, "budget_check_1", "Check budget after flight", "done")

    # -- Search hotels --
    _plan_step(state, "search_hotels", "Search hotels", "in_progress")
    raw_return = state.get("return_date")
    if raw_return:
        return_date = raw_return
    else:
        try:
            return_date = (
                datetime.fromisoformat(state["depart_date"]) + timedelta(days=3)
            ).strftime("%Y-%m-%d")
        except Exception:
            return_date = state["depart_date"]

    hotel_options = search_hotels(
        state["destination"], state["depart_date"], return_date, state["travelers"]
    )
    state["hotel_options"] = hotel_options
    _trace(state, "search_hotels", "tool_call",
           f"search_hotels({state['destination']}, {state['depart_date']} → {return_date})")
    _trace(state, "search_hotels", "tool_result",
           f"{len(hotel_options)} options found")
    _plan_step(state, "search_hotels", "Search hotels", "done")

    # -- Pause for user to pick a hotel --
    _plan_step(state, "select_hotel", "You pick a hotel", "in_progress")
    state["status"] = "select_hotel"
    _trace(state, "select_hotel", "decision",
           "Hotels ready — pick one that fits your vibe and budget.")
    return state


# ---------------------------------------------------------------------------
# Phase 3: User selected a hotel → budget check → propose cart
# ---------------------------------------------------------------------------
def run_phase3_select_hotel(state: dict, choice_index: int) -> dict:
    """
    Called when the user picks a hotel. Runs budget check, assembles cart,
    pauses with status='awaiting_confirmation'.
    """
    options = state.get("hotel_options") or []
    if not options:
        state["status"] = "failed"
        _trace(state, "select_hotel", "decision", "No hotel options available.")
        return state

    idx = max(0, min(choice_index, len(options) - 1))
    chosen = options[idx]
    state["chosen_hotel"] = {
        **chosen,
        "agent_reasoning": "Selected by you.",
        "agent_confidence": 1.0,
    }
    _plan_step(state, "select_hotel", "You pick a hotel", "done")
    _trace(state, "select_hotel", "decision",
           f"You picked {chosen['name']} for ₹{chosen['total_price_inr']}.")

    # -- Budget check for hotel --
    amount = chosen.get("total_price_inr", 0)
    _plan_step(state, "budget_check_2", "Check budget after hotel", "in_progress")
    guard = BudgetGuard(cap=state["budget_cap"], currency=state.get("currency", "INR"))
    guard.running_total = state.get("running_total", 0.0)
    decision = guard.add_cost(amount, f"Hotel ({chosen['name']})")
    state["running_total"] = guard.running_total
    state.setdefault("budget_decisions", []).append({
        "allowed": decision.allowed,
        "running_total": decision.running_total,
        "cap": decision.cap,
        "overage": decision.overage,
        "message": decision.message,
        "negotiation_options": decision.negotiation_options,
    })
    _trace(state, "budget_check", "decision", decision.message)

    if not decision.allowed:
        state["status"] = "needs_input"
        state["needs_user_decision"] = True
        state["negotiation_options"] = decision.negotiation_options
        _plan_step(state, "budget_check_2", "Check budget after hotel", "failed")
        return state

    state["needs_user_decision"] = False
    _plan_step(state, "budget_check_2", "Check budget after hotel", "done")

    # -- Propose cart --
    _plan_step(state, "propose_cart", "Review and confirm your trip", "in_progress")
    state["cart"] = {
        "flight": state.get("chosen_flight"),
        "hotel": state.get("chosen_hotel"),
        "total_inr": state.get("running_total"),
        "budget_cap_inr": state.get("budget_cap"),
        "remaining_inr": state.get("budget_cap", 0) - state.get("running_total", 0),
    }
    state["status"] = "awaiting_confirmation"
    _trace(state, "propose_cart", "decision",
           "Cart assembled. Review your selections and confirm when ready.")
    _plan_step(state, "propose_cart", "Review and confirm your trip", "done")
    return state
