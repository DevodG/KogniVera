"""
Session state — the planning session, server-side and authoritative.

The session holds the guard, the chosen package, the applied swaps and the
trace. The frontend is a view onto it; it never owns a running total. This is
the fix for the old build, where the client kept its own parseFloat total and
the guard was bypassable by construction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.budget_guard import BudgetDecision, BudgetGuard
from app.core.money import Money
from app.core.reprice import Component, Package, RepriceBreakdown, reprice, validate_swap
from app.data.packagepro import get_components, get_package


@dataclass
class TraceEntry:
    """One line of the live agent trace — the transparency feature."""

    node: str
    kind: str          # reasoning | tool_call | tool_result | decision
    content: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {"node": self.node, "kind": self.kind, "content": self.content, "ts": self.ts}


@dataclass
class Session:
    """
    A planning session. Mutated only on the server. Every cost-adding path
    goes through self.guard — there is no other way to move the total.
    """

    session_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # traveler profile
    languages: tuple[str, ...] = ()
    budget_band: str = ""
    travel_style: str = ""
    traveller_type: str = ""
    pace: str = ""
    interests: tuple[str, ...] = ()

    # the plan
    package: Package | None = None
    components: list[Component] = field(default_factory=list)
    swaps: dict[str, str] = field(default_factory=dict)     # original -> replacement
    selected_optional: set[str] = field(default_factory=set)
    chosen_guide: dict | None = None

    guard: BudgetGuard | None = None
    trace: list[TraceEntry] = field(default_factory=list)
    status: str = "intake"   # intake -> package -> customize -> confirm

    # ------------------------------------------------------------------ trace
    def say(self, node: str, kind: str, content: str) -> None:
        self.trace.append(TraceEntry(node=node, kind=kind, content=content))

    # ------------------------------------------------------------- construction
    def init_guard(self, cap: Money) -> None:
        self.guard = BudgetGuard(cap)
        self.say("budget", "decision",
                 f"Budget cap set to {cap.format()}. Enforcement is in code, not a prompt.")

    @property
    def traveler(self):
        from app.intel.engine import Traveler

        return Traveler(
            languages=self.languages,
            interests=self.interests,
            budget_band=self.budget_band,
            travel_style=self.travel_style,
            traveller_type=self.traveller_type,
            pace=self.pace,
            preferred_currency=self.guard.cap.currency if self.guard else "INR",
        )

    # --------------------------------------------------------------- package
    def choose_package(self, package_id: str) -> RepriceBreakdown:
        pkg = get_package(package_id)
        if pkg is None:
            raise KeyError(f"no such package: {package_id}")
        self.package = pkg
        self.components = get_components(package_id)
        self.say("package", "tool_call", f"get_package({package_id})")
        self.say("package", "tool_result",
                 f"{pkg.name} — {len(self.components)} components, base {pkg.base_price.format()}")

        # Commit the package cost through the guard: base + included component
        # deltas. The running total must reflect the actual trip cost, not just
        # later swaps — otherwise the cap would never measure the package itself.
        breakdown = self.reprice()
        if self.guard:
            self.guard.running_total = Money.zero(self.guard.cap.currency)
            package_cost = breakdown.base_price + breakdown.included_delta
            if package_cost.amount > 0:
                decision = self.guard.add_cost(package_cost, f"package: {pkg.name}")
                self.say("package", "decision", decision.message)
                if not decision.allowed:
                    # The package itself exceeds the cap: report the negotiation
                    # options rather than silently showing a broken ledger.
                    self.status = "package"
                    return breakdown
        self.status = "customize"
        return breakdown

    # ----------------------------------------------------------------- repricing
    def reprice(self) -> RepriceBreakdown:
        """The core PS-04 operation, Decimal end to end."""
        if self.package is None:
            raise RuntimeError("no package selected")
        return reprice(
            self.package, self.components, self.selected_optional, self.swaps
        )

    # ------------------------------------------------------------------- swap
    def swap(self, from_id: str, to_id: str) -> dict:
        """
        Swap a component for an alternative. Server-authoritative:

          1. validate the swap is legal (same package + swap_group)
          2. compute the net delta in Decimal
          3. check the budget guard — over cap means the swap is NOT applied
             and negotiation options come back instead
        """
        if self.package is None:
            raise RuntimeError("no package selected")
        by_id = {c.component_id: c for c in self.components}
        if from_id not in by_id or to_id not in by_id:
            raise KeyError("unknown component id in swap")

        from_comp = by_id[from_id]
        to_comp = by_id[to_id]
        validate_swap(from_comp, to_comp)  # raises if illegal

        delta = to_comp.price_delta - from_comp.price_delta
        self.say("swap", "tool_call", f"swap({from_id} -> {to_id})")
        self.say("swap", "reasoning",
                 f"{to_comp.title} vs {from_comp.title}: net {delta.format()}")

        # Guard the swap. Nothing moves if it would breach the cap.
        if self.guard and delta.amount > 0 and self.guard.would_exceed(delta):
            decision = self.guard.add_cost(delta, f"swap -> {to_comp.title}")
            self.say("swap", "decision", decision.message)
            return {
                "applied": False,
                "decision": decision.to_dict(),
                "breakdown": self.reprice().to_dict(),
            }

        # Apply the swap and commit the (signed) delta through the guard.
        self.swaps[from_id] = to_id
        if self.guard:
            label = f"swap: {from_comp.title} -> {to_comp.title}"
            if delta.amount >= 0:
                decision = self.guard.add_cost(delta, label)
            else:
                # A saving is a negative delta — record it as a removal.
                decision = self.guard.remove_cost(-delta, label)
            self.say("swap", "decision", decision.message)

        breakdown = self.reprice()
        return {
            "applied": True,
            "delta": delta.to_dict(),
            "decision": self.guard.decisions[-1].to_dict() if self.guard else None,
            "breakdown": breakdown.to_dict(),
        }

    def unswap(self, from_id: str) -> dict:
        """Revert a swap back to the original component."""
        if from_id not in self.swaps:
            raise KeyError(f"no swap recorded for {from_id}")
        to_id = self.swaps.pop(from_id)
        by_id = {c.component_id: c for c in self.components}
        delta = by_id[to_id].price_delta - by_id[from_id].price_delta
        if self.guard:
            # Reverse the effect of the original swap.
            if delta.amount >= 0:
                self.guard.remove_cost(delta, f"unswap {from_id}")
            else:
                self.guard.add_cost(-delta, f"unswap {from_id}")
        self.say("swap", "decision", f"Reverted swap {from_id}; total {self.guard.running_total.format() if self.guard else '?'}")
        return {"applied": True, "breakdown": self.reprice().to_dict()}

    # ------------------------------------------------------------ optional add
    def add_optional(self, component_id: str) -> dict:
        """Opt into an optional component (meal, insurance, ticket). Guarded."""
        by_id = {c.component_id: c for c in self.components}
        comp = by_id.get(component_id)
        if comp is None or not comp.is_optional:
            raise ValueError(f"{component_id} is not an optional component")
        if component_id in self.selected_optional:
            return {"applied": False, "reason": "already selected"}
        delta = comp.price_delta
        if self.guard and self.guard.would_exceed(delta):
            decision = self.guard.add_cost(delta, comp.title)
            return {"applied": False, "decision": decision.to_dict()}
        self.selected_optional.add(component_id)
        if self.guard:
            decision = self.guard.add_cost(delta, comp.title)
            self.say("optional", "decision", decision.message)
        return {
            "applied": True,
            "decision": self.guard.decisions[-1].to_dict() if self.guard else None,
            "breakdown": self.reprice().to_dict(),
        }

    def remove_optional(self, component_id: str) -> dict:
        by_id = {c.component_id: c for c in self.components}
        comp = by_id.get(component_id)
        if component_id not in self.selected_optional or comp is None:
            raise ValueError(f"{component_id} not selected")
        self.selected_optional.discard(component_id)
        if self.guard:
            self.guard.remove_cost(comp.price_delta, comp.title)
        return {"applied": True, "breakdown": self.reprice().to_dict()}

    # ------------------------------------------------------------------ guides
    def choose_guide(self, guide: dict) -> dict:
        """Attach a guide. Peak-day rate is applied in Decimal and guarded."""
        rate: Money = guide.get("peak_day_rate") or guide["day_rate"]
        label = f"guide: {guide['display_name']}"
        if self.guard:
            decision = self.guard.add_cost(rate, label)
            self.say("guide", "decision", decision.message)
            if not decision.allowed:
                return {"applied": False, "decision": decision.to_dict()}
        self.chosen_guide = guide
        return {
            "applied": True,
            "decision": self.guard.decisions[-1].to_dict() if self.guard else None,
            "guide": _guide_to_dict(guide),
        }

    # ------------------------------------------------------------------ export
    def to_state(self) -> dict:
        breakdown = self.reprice().to_dict() if self.package else None
        return {
            "session_id": self.session_id,
            "status": self.status,
            "languages": list(self.languages),
            "budget_band": self.budget_band,
            "travel_style": self.travel_style,
            "traveller_type": self.traveller_type,
            "pace": self.pace,
            "interests": list(self.interests),
            "package": _package_to_dict(self.package) if self.package else None,
            "components": [_component_to_dict(c, self.swaps) for c in self.components],
            "swaps": dict(self.swaps),
            "selected_optional": sorted(self.selected_optional),
            "chosen_guide": _guide_to_dict(self.chosen_guide) if self.chosen_guide else None,
            "budget": {
                "cap": self.guard.cap.to_dict() if self.guard else None,
                "running_total": self.guard.running_total.to_dict() if self.guard else None,
                "remaining": self.guard.remaining().to_dict() if self.guard else None,
                "pct_used": str(self.guard.pct_used()) if self.guard else "0",
                "audit_trail": self.guard.audit_trail() if self.guard else [],
            },
            "breakdown": breakdown,
            "trace": [t.to_dict() for t in self.trace],
        }


# ---------------------------------------------------------------------------
# Serialisers — Money always leaves as {amount: str, currency: str}, never float
# ---------------------------------------------------------------------------

def _package_to_dict(p: Package) -> dict:
    return {
        "package_id": p.package_id,
        "city_id": p.city_id,
        "name": p.name,
        "theme": p.theme,
        "tier": p.tier,
        "duration_days": p.duration_days,
        "duration_nights": p.duration_nights,
        "base_price": p.base_price.to_dict(),
        "difficulty": p.difficulty,
        "languages_offered": p.languages_offered,
        "inclusions": p.inclusions,
        "exclusions": p.exclusions,
        "description": p.description,
    }


def _component_to_dict(c: Component, swaps: dict[str, str] | None = None) -> dict:
    """Serialise a component. `swapped_to` shows its replacement if swapped out."""
    return {
        "component_id": c.component_id,
        "component_type": c.component_type,
        "entity_type": c.entity_type,
        "entity_id": c.entity_id,
        "day_index": c.day_index,
        "slot": c.slot,
        "title": c.title,
        "quantity": c.quantity,
        "price_delta": c.price_delta.to_dict(),
        "is_optional": c.is_optional,
        "is_swappable": c.is_swappable,
        "swap_group": c.swap_group,
        "swapped_to": swaps.get(c.component_id) if swaps else None,
    }


def _guide_to_dict(g: dict | None) -> dict | None:
    if g is None:
        return None
    rate = g.get("peak_day_rate") or g.get("day_rate")
    return {
        "guide_id": g["guide_id"],
        "display_name": g["display_name"],
        "languages": g.get("languages", []),
        "specialisation": g.get("specialisation"),
        "secondary_specialisation": g.get("secondary_specialisation"),
        "years_experience": g.get("years_experience"),
        "rating": str(g["rating"]) if g.get("rating") is not None else None,
        "review_count": g.get("review_count"),
        "day_rate": rate.to_dict() if isinstance(rate, Money) else None,
        "currency": g.get("currency"),
        "certified": g.get("certified"),
        "bio": g.get("bio"),
        "on_date": g.get("on_date"),
    }
