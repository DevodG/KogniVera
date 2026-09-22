"""The transparent agent plan.

Waypoint's "agent" is a deterministic planner that publishes exactly what it
is going to do before it touches the data, then records a user-safe trace of
what it found. When no AI key is configured the plan is fully rule-driven,
which is the MVP contract: the product works with no external key.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .. import config
from ..db.packagepro import PackageProDB, dec
from ..db.session import SessionDB
from decimal import Decimal

from ..models import money_str
from ..services import pricing, trace
from ..services.budget import BudgetGuard
from ..services.itinerary import ItineraryService, SwapError
from ..services.recommender import recommend

PLAN_STEPS = [
    "Find packages that match your city, dates, language, group size, and budget.",
    "Explain the best eligible options.",
    "Let you customize itinerary components and choose a guide.",
    "Check your budget after every change.",
    "Never book anything until you approve.",
]


def new_session_id() -> str:
    return f"wp_{uuid.uuid4().hex[:16]}"


class Solver:
    def __init__(self, pro: PackageProDB, sessions: SessionDB) -> None:
        self.pro = pro
        self.sessions = sessions

    # ------------------------------------------------------------------

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        session_id = new_session_id()
        self.sessions.create_session(session_id, request, list(PLAN_STEPS))
        self.sessions.add_trace(session_id, trace.build(
            "plan", "complete", trace.SOURCE["packages"],
            f"{request['city_id']}, {request['start_date']} to {request['end_date']}",
            "Plan published before any data is queried: "
            + " | ".join(PLAN_STEPS),
            "The traveller sees the full plan first; nothing runs in the dark.",
            step=1,
        ))
        recs, rejected, _ = self._recommend(session_id, request)
        self.sessions.update_session(session_id, status="recommended")
        return self._session_view(session_id, recommendations=recs)

    def _recommend(self, session_id: str, request: dict[str, Any]):
        self.sessions.add_trace(session_id, trace.searching_packages(request))
        recs, rejected, scored = recommend(self.pro, request)
        top = recs[0].name if recs else None
        self.sessions.add_trace(
            session_id,
            trace.found_packages(len(scored), request, top),
        )
        self.sessions.add_audit(
            session_id, "recommend", "agent",
            {
                "eligible": len(scored),
                "rejected": [
                    {"package_id": p.get("package_id"), "reason": r}
                    for p, r in rejected
                ],
                "shown": [r.package_id for r in recs],
            },
            decision="approved" if recs else "no_match",
        )
        return recs, rejected, scored

    def _session_view(self, session_id: str,
                      recommendations: Optional[list[Any]] = None) -> dict[str, Any]:
        s = self.sessions.get_session(session_id)
        view = {
            "session_id": session_id,
            "status": s["status"],
            "request": s["request"],
            "plan_steps": s["plan_steps"],
            "recommendations": recommendations or [],
            "selected_package_id": s.get("selected_package_id"),
            "selected_guide_id": s.get("selected_guide_id"),
            "budget": None,
            "trace": self.sessions.trace(session_id),
            "audit": self.sessions.audit(session_id),
            "confirmed": bool(s.get("confirmed")),
            "confirmation": s.get("confirmation"),
        }
        if s.get("total_amount"):
            _cap = Decimal(s["budget_amount"])
            _total = Decimal(s["total_amount"])
            cap = pricing.remaining(_cap, _total)
            view["budget"] = {
                "cap": s["budget_amount"],
                "currency": s["budget_currency"],
                "total": s["total_amount"],
                "remaining": str(cap),
                "decision": "approved" if cap >= 0 else "blocked",
                "overage": None if cap >= 0 else str(-cap),
                "negotiation_options": [] if cap >= 0 else [
                    "select_cheaper_alternative", "remove_optional_component",
                    "raise_budget_cap", "approve_overage",
                ],
            }
        return view

    # ------------------------------------------------------------------

    def select_package(self, session_id: str, package_id: str) -> dict[str, Any]:
        s = self.sessions.get_session(session_id)
        if s is None:
            raise KeyError(f"unknown session {session_id}")
        pkg = self.pro.package(package_id)
        if pkg is None:
            raise ValueError(f"unknown package {package_id}")
        if pkg["city_id"] != s["city_id"]:
            raise ValueError(
                "package belongs to a different city than the session destination"
            )
        comps = self.pro.components(package_id)
        total = pricing.included_total(pkg["base_price"], comps)
        guard = BudgetGuard(self.sessions, session_id)
        result = guard.decide(total, action="select_package",
                              detail={"package_id": package_id})
        self.sessions.update_session(
            session_id,
            selected_package_id=package_id,
            status="customizing" if result["decision"] == "approved" else "over_budget",
            currency=pkg["currency"],
            total_amount=money_str(total),
        )
        self.sessions.add_trace(
            session_id,
            trace.package_selected(pkg, money_str(total), pkg["currency"]),
        )
        self.sessions.add_trace(
            session_id,
            trace.itinerary_loaded(pkg, len(comps), money_str(total)),
        )
        if result["decision"] == "approved":
            self.sessions.add_trace(
                session_id, trace.budget_approved(result["remaining"], result["currency"])
            )
        else:
            self.sessions.add_trace(
                session_id, trace.budget_blocked(result["overage"] or "0.00", result["cap"], result["currency"])
            )
        it = ItineraryService(self.pro, self.sessions, session_id)
        it._persist_cart()
        return self._session_view(session_id, recommendations=None)

    # ------------------------------------------------------------------

    def swap(self, session_id: str, component_id: str,
             replacement_component_id: str) -> dict[str, Any]:
        it = ItineraryService(self.pro, self.sessions, session_id)
        old, new, _ = it.validate_swap(component_id, replacement_component_id)
        package_total = pricing.apply_swap(it.package_total(), old, new)
        guide = it.guide_total()
        new_total = package_total + guide
        guard = BudgetGuard(self.sessions, session_id)
        result = guard.decide(
            new_total, currency=new["currency"], action="swap",
            detail={
                "component_id": component_id,
                "replacement_component_id": replacement_component_id,
                "delta": money_str(pricing.swap_delta(old, new)),
            },
        )
        if result["decision"] != "approved":
            self.sessions.add_trace(
                session_id,
                trace.swap_blocked(
                    f"Budget Guard blocked the swap: it would exceed your cap by "
                    f"{result['overage']} {result['currency']}."
                ),
            )
            return self._session_view(session_id) | {
                "budget": result,
                "budget_message": guard.message(result),
                "swap_blocked": True,
            }

        applied = it.apply_swap(component_id, replacement_component_id)
        self.sessions.add_trace(
            session_id,
            trace.swap_applied(
                old["title"], new["title"], applied["delta"], new["currency"],
                applied["total"], result["remaining"],
            ),
        )
        self.sessions.add_trace(
            session_id, trace.budget_approved(result["remaining"], result["currency"])
        )
        view = self._session_view(session_id)
        view["budget"] = result
        return view

    # ------------------------------------------------------------------

    def select_guide(self, session_id: str, guide_id: str,
                     service: str = "full_day") -> dict[str, Any]:
        from ..services.guides import guide_cost_for_trip, match_guides, to_guide_model

        s = self.sessions.get_session(session_id)
        if s is None:
            raise KeyError(f"unknown session {session_id}")
        guide = self.pro.guide(guide_id)
        if guide is None:
            raise ValueError(f"unknown guide {guide_id}")
        if guide["city_id"] != s["city_id"]:
            raise ValueError(
                "guide belongs to a different city than the session destination"
            )
        if service not in ("full_day", "half_day"):
            raise ValueError("service must be 'full_day' or 'half_day'")

        avail = self.pro.guide_availability(
            guide_id, s["start_date"], s["end_date"]
        )
        free = [a for a in avail if int(a["is_available"]) == 1 and int(a["slots_available"]) > 0]
        if not free:
            self.sessions.add_trace(session_id, trace.guide_unavailable(guide))
            self.sessions.add_audit(
                session_id, "select_guide", "budget_guard",
                {"guide_id": guide_id, "reason": "no availability on trip dates"},
                decision="blocked", amount="0.00", currency=guide["currency"],
            )
            raise ValueError(
                f"{guide['display_name']} is not available on any of your trip dates"
            )

        mult = free[0]["price_multiplier"]
        cost = pricing.guide_cost(guide, service, mult)
        it = ItineraryService(self.pro, self.sessions, session_id)
        new_total = it.package_total() + cost
        guard = BudgetGuard(self.sessions, session_id)
        result = guard.decide(
            new_total, currency=guide["currency"], action="select_guide",
            detail={"guide_id": guide_id, "service": service, "cost": money_str(cost)},
        )
        if result["decision"] != "approved":
            self.sessions.add_trace(
                session_id,
                trace.budget_blocked(result["overage"] or "0.00", result["cap"], result["currency"]),
            )
            return self._session_view(session_id) | {
                "budget": result,
                "budget_message": guard.message(result),
                "guide_blocked": True,
            }

        self.sessions.update_session(
            session_id,
            selected_guide_id=guide_id,
            guide_service=service,
            guide_cost=money_str(cost),
            guide_multiplier=f"{mult}",
            total_amount=money_str(new_total),
        )
        self.sessions.add_trace(
            session_id,
            trace.guide_selected(guide, money_str(cost), f"{mult}", guide["currency"],
                                 money_str(new_total)),
        )
        self.sessions.add_trace(
            session_id, trace.budget_approved(result["remaining"], result["currency"])
        )
        it = ItineraryService(self.pro, self.sessions, session_id)
        it._persist_cart()
        return self._session_view(session_id)

    # ------------------------------------------------------------------

    def negotiate(self, session_id: str, option: str,
                  new_budget: Optional[str] = None) -> dict[str, Any]:
        s = self.sessions.get_session(session_id)
        if s is None:
            raise KeyError(f"unknown session {session_id}")
        guard = BudgetGuard(self.sessions, session_id)
        budget_decimal = None
        if option == "raise_budget_cap":
            if not new_budget:
                raise ValueError("raise_budget_cap requires a new budget")
            budget_decimal = Decimal(new_budget)
        result = guard.negotiate(s, option, budget_decimal)
        self.sessions.add_trace(
            session_id,
            trace.negotiation_applied(
                option, result["total"], result["remaining"], result["currency"]
            ),
        )
        view = self._session_view(session_id)
        view["budget"] = result
        return view

    # ------------------------------------------------------------------

    def trust_receipt(self, session_id: str) -> dict[str, Any]:
        from ..models import TrustReceiptModel, TrustReceiptRow

        s = self.sessions.get_session(session_id)
        if s is None:
            raise KeyError(f"unknown session {session_id}")
        if not s.get("selected_package_id"):
            raise ValueError("no package selected")
        it = ItineraryService(self.pro, self.sessions, session_id)
        pkg = self.pro.package(s["selected_package_id"])
        rows: list[TrustReceiptRow] = []

        total = it.current_total()
        cap = __import__("decimal").Decimal(s["budget_amount"])
        over = pricing.overage(cap, total)
        guard_state = (
            "Passed" if over is None else "negotiation required "
            f"(over by {money_str(over)} {s['budget_currency']})"
        )

        rows.append(
            TrustReceiptRow(
                decision="Package",
                source="PackagePro.tour_packages",
                why_selected=(
                    f"Constraint match: {pkg['duration_days']} days, group "
                    f"{s['travelers']}, languages {pkg['languages_offered']}, "
                    f"{pkg['theme']} theme"
                ),
                price_effect=f"{it.package_total():.2f}",
                currency=pkg["currency"],
            )
        )

        comps = it.effective_components()
        swaps = s.get("component_overrides_map") or {}
        kept = [c for c in comps if int(c["is_optional"]) == 0]
        opts = [c for c in comps if int(c["is_optional"]) == 1]
        rows.append(
            TrustReceiptRow(
                decision="Components",
                source="PackagePro.package_components",
                why_selected=(
                    f"{len(kept)} included + {len(opts)} optional kept"
                    + (f"; {len(swaps)} user swap(s) applied" if swaps else "")
                    + (
                        f"; {len(s.get('removed_optional_list') or [])} optional removed"
                        if s.get("removed_optional_list")
                        else ""
                    )
                ),
                price_effect=f"{sum((__import__('decimal').Decimal(c['price_delta']) for c in comps), __import__('decimal').Decimal('0')):.2f}",
                currency=pkg["currency"],
            )
        )

        gid = s.get("selected_guide_id")
        if gid:
            guide = self.pro.guide(gid)
            rows.append(
                TrustReceiptRow(
                    decision="Guide",
                    source="PackagePro guides + availability",
                    why_selected=(
                        f"Language/date match: {guide['display_name']}, "
                        f"{guide['languages']}, {s.get('guide_service')} "
                        f"x {s.get('guide_multiplier')} date multiplier"
                    ),
                    price_effect=f"{it.guide_total():.2f}",
                    currency=guide["currency"],
                )
            )

        rows.append(
            TrustReceiptRow(
                decision="Budget",
                source="Waypoint Budget Guard",
                why_selected="Code-enforced cap on every change",
                price_effect=f"{pricing.remaining(cap, total):.2f}",
                currency=s["budget_currency"],
            )
        )

        receipt = TrustReceiptModel(
            session_id=session_id,
            rows=rows,
            totals={
                "package_base": f"{dec(pkg['base_price']):.2f}",
                "components": f"{_component_sum(comps):.2f}",
                "guide": f"{it.guide_total():.2f}",
                "grand_total": f"{total:.2f}",
                "budget_cap": s["budget_amount"],
                "remaining": f"{pricing.remaining(cap, total):.2f}",
            },
            budget_guard=guard_state,
            data_backed_plan=True,
            confirmed=bool(s.get("confirmed")),
            confirmation=s.get("confirmation"),
            trace=self.sessions.trace(session_id),
        )
        self.sessions.add_trace(
            session_id,
            trace.receipt_ready(f"{total:.2f}", pkg["currency"], guard_state),
        )
        return receipt.model_dump()

    # ------------------------------------------------------------------

    def confirm(self, session_id: str) -> dict[str, Any]:
        s = self.sessions.get_session(session_id)
        if s is None:
            raise KeyError(f"unknown session {session_id}")
        if not s.get("selected_package_id"):
            raise ValueError("cannot confirm without a selected package")
        if bool(s.get("confirmed")):
            raise ValueError("session is already confirmed")

        it = ItineraryService(self.pro, self.sessions, session_id)
        total = it.current_total()
        cap = Decimal(s["budget_amount"])
        if total > cap:
            raise ValueError(
                "Budget Guard blocks confirmation above the cap; resolve the "
                "overage first"
            )

        reference = f"WP-MOCK-{session_id[-8:].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        confirmation = {
            "booking_reference": reference,
            "status": "mock_confirmed",
            "total_amount": money_str(total),
            "currency": s["budget_currency"],
            "confirmed_at": now,
            "note": (
                "Mock confirmation only. No payment was taken and no real "
                "booking was made."
            ),
        }
        self.sessions.update_session(
            session_id, confirmed=True, confirmation=confirmation, status="confirmed"
        )
        self.sessions.add_audit(
            session_id, "confirm", "user",
            {"reference": reference, "total": money_str(total)},
            decision="approved", amount=money_str(total), currency=s["budget_currency"],
        )
        self.sessions.add_trace(
            session_id, trace.confirmed(reference, money_str(total), s["budget_currency"])
        )
        return {"session_id": session_id, "confirmation": confirmation}

    # ------------------------------------------------------------------

    def optional_model_summaries(self) -> Optional[Any]:
        return None


def _component_sum(components: list[dict[str, Any]]) -> Decimal:
    from ..db.packagepro import dec as _dec

    return sum((_dec(c["price_delta"]) for c in components), Decimal("0"))
