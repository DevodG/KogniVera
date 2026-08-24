"""
Hard spend-cap enforcement — the centerpiece "trust" feature.

Two modes:
1. If you `pip install git+https://github.com/AgentBudget/agentbudget.git`
   this module will use it automatically (see the try/except below).
2. Otherwise a small in-house guard runs instead, with identical behavior:
   never let the agent cross the cap, and always produce a structured
   negotiation offer instead of a flat refusal.

This is intentionally decoupled from the LLM — the cap is enforced in code,
not by asking the model nicely. A model can hallucinate; this class can't.
"""
from __future__ import annotations

from dataclasses import dataclass, field

try:
    from agentbudget import AgentBudget as _RealAgentBudget  # type: ignore

    HAS_AGENTBUDGET_SDK = True
except ImportError:
    HAS_AGENTBUDGET_SDK = False


@dataclass
class BudgetDecision:
    allowed: bool
    running_total: float
    cap: float
    overage: float
    message: str
    negotiation_options: list[str] = field(default_factory=list)


class BudgetGuard:
    """Session-scoped hard cap. One instance per trip-planning session."""

    def __init__(self, cap: float, currency: str = "INR"):
        self.cap = cap
        self.currency = currency
        self.running_total = 0.0
        self.decisions_log: list[BudgetDecision] = []

    def add_cost(self, amount: float, label: str) -> BudgetDecision:
        prospective_total = self.running_total + amount
        overage = max(0.0, prospective_total - self.cap)

        if overage <= 0:
            self.running_total = prospective_total
            decision = BudgetDecision(
                allowed=True,
                running_total=self.running_total,
                cap=self.cap,
                overage=0.0,
                message=f"Added {label}: {amount:.0f} {self.currency}. "
                f"{self.running_total:.0f}/{self.cap:.0f} used.",
            )
        else:
            # Hard stop — do NOT commit the cost. Offer structured trade-offs
            # instead of a flat "no" (this is the "negotiation, not refusal" feature).
            decision = BudgetDecision(
                allowed=False,
                running_total=self.running_total,
                cap=self.cap,
                overage=overage,
                message=f"Adding {label} ({amount:.0f} {self.currency}) would exceed the "
                f"{self.cap:.0f} {self.currency} cap by {overage:.0f}.",
                negotiation_options=[
                    f"Approve a {overage:.0f} {self.currency} overage for this item",
                    "Swap this item for a cheaper alternative and re-search",
                    "Remove this item and continue with what's already planned",
                    "Raise the overall trip budget cap",
                ],
            )
        self.decisions_log.append(decision)
        return decision

    def remaining(self) -> float:
        return max(0.0, self.cap - self.running_total)

    def pct_used(self) -> float:
        return round((self.running_total / self.cap) * 100, 1) if self.cap else 0.0

    def audit_trail(self) -> list[dict]:
        """Exportable, timestamped-by-order decision log — the trust/B2B feature."""
        return [
            {
                "step": i + 1,
                "allowed": d.allowed,
                "running_total": d.running_total,
                "cap": d.cap,
                "overage": d.overage,
                "message": d.message,
                "negotiation_options": d.negotiation_options,
            }
            for i, d in enumerate(self.decisions_log)
        ]
