"""
Shared state that flows through every node of the LangGraph state machine.
Everything the frontend needs to render (plan steps, cost ledger, trace,
decision log, cart) lives here so a single `GET /session/{id}` can return
the whole picture.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class PlanStep(TypedDict, total=False):
    id: str
    title: str
    status: str  # "pending" | "in_progress" | "done" | "failed" | "skipped"


class TraceEvent(TypedDict, total=False):
    node: str
    kind: str  # "reasoning" | "tool_call" | "tool_result" | "decision"
    content: str


class AgentState(TypedDict, total=False):
    # ---- input ----
    session_id: str
    goal: str                     # raw natural-language goal from the user
    origin: str
    destination: str
    depart_date: str
    return_date: str
    travelers: int
    budget_cap: float
    currency: str

    # ---- working memory ----
    plan_steps: list[PlanStep]
    trace: list[TraceEvent]
    flight_options: list[dict[str, Any]]
    hotel_options: list[dict[str, Any]]
    place_options: list[dict[str, Any]]
    chosen_flight: Optional[dict[str, Any]]
    chosen_hotel: Optional[dict[str, Any]]
    running_total: float

    # ---- guardrail ----
    budget_decisions: list[dict[str, Any]]
    needs_user_decision: bool
    negotiation_options: list[str]

    # ---- output ----
    cart: Optional[dict[str, Any]]
    status: str  # "planning" | "select_flight" | "select_hotel" | "awaiting_confirmation" | "confirmed" | "failed" | "needs_input"
    clarifying_question: Optional[str]
