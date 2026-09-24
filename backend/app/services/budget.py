"""The Budget Guard.

The server owns the budget check. The browser is never trusted for totals:
every proposed change is re-priced from PackagePro rows on the server and
compared against the persisted cap.

Decisions: ``approved`` | ``blocked`` | ``negotiation_required``.
Every decision is written to the audit log.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from ..db.session import SessionDB
from ..models import BUDGET_NEGOTIATION_OPTIONS, format_money, money_str, quantize_money
from . import pricing


class BudgetGuard:
    def __init__(self, session_db: SessionDB, session_id: str) -> None:
        self.db = session_db
        self.session_id = session_id

    # ------------------------------------------------------------------

    def decide(self, proposed_total: Decimal, cap: Optional[Decimal] = None,
               currency: Optional[str] = None, action: str = "change",
               detail: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        cap = cap if cap is not None else self._cap()
        currency = currency or self._currency()
        total = quantize_money(proposed_total)
        rem = pricing.remaining(cap, total)
        over = pricing.overage(cap, total)

        if over is None:
            decision = "approved"
            options: list[str] = []
        else:
            decision = "blocked"
            options = list(BUDGET_NEGOTIATION_OPTIONS)

        self.db.add_audit(
            self.session_id, f"budget:{action}", "budget_guard",
            detail or {"proposed_total": money_str(total)},
            decision=decision,
            amount=money_str(total) if decision == "approved" else money_str(over),
            currency=currency,
        )
        return {
            "decision": decision,
            "cap": money_str(cap),
            "currency": currency,
            "total": money_str(total),
            "remaining": money_str(rem),
            "overage": money_str(over) if over is not None else None,
            "negotiation_options": options,
        }

    def message(self, result: dict[str, Any]) -> str:
        """Human-readable decision, formatted with the currency symbol."""
        if result["decision"] == "approved":
            return (
                "Budget Guard approved: "
                + format_money(Decimal(result["remaining"]), result["currency"])
                + " remains."
            )
        cap = format_money(Decimal(result["cap"]), result["currency"])
        over = format_money(Decimal(result["overage"] or "0.00"), result["currency"])
        return (
            f"This choice would exceed your {cap} cap by {over}.\n\n"
            "Choose one:\n"
            "1. Select a cheaper verified alternative.\n"
            "2. Remove an optional component.\n"
            "3. Raise the budget cap.\n"
            "4. Explicitly approve this exact overage."
        )

    # ------------------------------------------------------------------
    # Negotiation
    # ------------------------------------------------------------------

    def negotiate(self, session: dict[str, Any], option: str,
                  new_budget: Optional[Decimal] = None,
                  cheaper_total: Optional[Decimal] = None) -> dict[str, Any]:
        if option not in BUDGET_NEGOTIATION_OPTIONS:
            raise ValueError(f"unknown negotiation option: {option}")

        cap = self._cap()
        currency = self._currency()

        if option == "raise_budget_cap":
            if new_budget is None:
                raise ValueError("raise_budget_cap requires a new budget")
            if new_budget <= cap:
                raise ValueError("new budget cap must be higher than the current cap")
            self.db.update_session(
                self.session_id,
                budget_amount=money_str(new_budget),
            )
            self.db.add_audit(
                self.session_id, "budget:raise_budget_cap", "user",
                {"old_cap": money_str(cap), "new_cap": money_str(new_budget)},
                decision="approved", amount=money_str(new_budget), currency=currency,
            )
            total = Decimal(session["total_amount"]) if session.get("total_amount") else Decimal("0")
            return self.decide(total, cap=new_budget, currency=currency,
                               action="raise_budget_cap",
                               detail={"new_cap": money_str(new_budget)})

        if option == "approve_overage":
            total = (
                Decimal(session["total_amount"])
                if session.get("total_amount")
                else Decimal("0")
            )
            self.db.add_audit(
                self.session_id, "budget:approve_overage", "user",
                {"approved_total": money_str(total), "cap": money_str(cap)},
                decision="approved", amount=money_str(total), currency=currency,
            )
            return {
                "decision": "approved",
                "cap": money_str(cap),
                "currency": currency,
                "total": money_str(total),
                "remaining": money_str(pricing.remaining(cap, total)),
                "overage": money_str(pricing.overage(cap, total) or Decimal("0")),
                "negotiation_options": [],
            }

        # select_cheaper_alternative / remove_optional_component are resolved by
        # the caller re-pricing; the guard records the intent.
        total = cheaper_total if cheaper_total is not None else (
            Decimal(session["total_amount"])
            if session.get("total_amount")
            else Decimal("0")
        )
        self.db.add_audit(
            self.session_id, f"budget:{option}", "user",
            {"intended_total": money_str(total)},
            decision="approved", amount=money_str(total), currency=currency,
        )
        return self.decide(total, action=option,
                           detail={"option": option, "total": money_str(total)})

    # ------------------------------------------------------------------

    def _cap(self) -> Decimal:
        return Decimal(self.db.get_session(self.session_id)["budget_amount"])

    def _currency(self) -> str:
        return str(self.db.get_session(self.session_id)["budget_currency"])