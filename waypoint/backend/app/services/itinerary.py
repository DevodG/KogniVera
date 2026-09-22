"""Itinerary assembly, swap validation and cart (ledger) construction."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from ..db.packagepro import PackageProDB, dec
from ..db.session import SessionDB
from ..models import (
    DayPlanModel,
    ItineraryResponse,
    PackageComponentModel,
    money_str,
    quantize_money,
)
from . import pricing
from .guides import match_guides, to_guide_model

SLOT_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, "overnight": 3}


class SwapError(ValueError):
    """A swap that violates the PackagePro swap rules."""


def component_model(row: dict[str, Any], selected: bool = True) -> PackageComponentModel:
    return PackageComponentModel(
        component_id=row["component_id"],
        component_type=row["component_type"],
        entity_type=row.get("entity_type"),
        entity_id=row.get("entity_id"),
        day_index=int(row["day_index"]),
        slot=row["slot"],
        title=row["title"],
        quantity=int(row["quantity"]),
        price_delta=f"{dec(row['price_delta']):.2f}",
        currency=row["currency"],
        is_optional=bool(int(row["is_optional"])),
        is_swappable=bool(int(row["is_swappable"])),
        swap_group=row.get("swap_group"),
        selected=selected,
    )


class ItineraryService:
    def __init__(self, pro: PackageProDB, sessions: SessionDB, session_id: str) -> None:
        self.pro = pro
        self.sessions = sessions
        self.session_id = session_id
        self.session = sessions.get_session(session_id)
        if self.session is None:
            raise KeyError(f"unknown session {session_id}")
        if not self.session.get("selected_package_id"):
            raise ValueError("no package selected for this session")

    # ------------------------------------------------------------------
    # Pricing core
    # ------------------------------------------------------------------

    @property
    def package_id(self) -> str:
        return str(self.session["selected_package_id"])

    @property
    def base_components(self) -> list[dict[str, Any]]:
        return self.pro.components(self.package_id)

    def effective_components(self) -> list[dict[str, Any]]:
        """The live component set after the user's swaps and removals."""
        overrides = self.session.get("component_overrides_map") or {}
        removed = set(self.session.get("removed_optional_list") or [])
        out: list[dict[str, Any]] = []
        for c in self.base_components:
            cid = c["component_id"]
            if cid in removed:
                continue
            if cid in overrides:
                replacement_id = overrides[cid]
                rep = self.pro.component(replacement_id)
                if rep is None:
                    continue
                rep = dict(rep)
                rep["day_index"] = c["day_index"]
                rep["slot"] = c["slot"]
                rep["replaces"] = cid
                out.append(rep)
            else:
                out.append(dict(c))
        return out

    def package_total(self) -> Decimal:
        """included_total after swaps, using the PackagePro convention."""
        comps = self.effective_components()
        pkg = self.pro.package(self.package_id)
        base = dec(pkg["base_price"])
        total = base
        for c in comps:
            if int(c["is_optional"]) == 0:
                total += dec(c["price_delta"])
        return quantize_money(total)

    def guide_total(self) -> Decimal:
        gid = self.session.get("selected_guide_id")
        if not gid:
            return Decimal("0")
        cost = self.session.get("guide_cost")
        return dec(cost) if cost else Decimal("0")

    def current_total(self) -> Decimal:
        return quantize_money(self.package_total() + self.guide_total())

    # ------------------------------------------------------------------
    # Swap validation
    # ------------------------------------------------------------------

    def validate_swap(
        self, component_id: str, replacement_component_id: str
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        old = self.pro.component(component_id)
        new = self.pro.component(replacement_component_id)
        if old is None:
            raise SwapError(f"unknown component {component_id}")
        if new is None:
            raise SwapError(f"unknown replacement component {replacement_component_id}")
        if old["package_id"] != self.package_id:
            raise SwapError(
                "component does not belong to the selected package "
                "(IDs are opaque; package membership is enforced by lookup)"
            )
        if new["package_id"] != self.package_id:
            raise SwapError(
                "replacement must come from the same package — cross-package "
                "changes are not allowed"
            )
        if int(old["is_swappable"]) != 1:
            raise SwapError(f"'{old['title']}' is not swappable")
        if int(new["is_swappable"]) != 1:
            raise SwapError(f"'{new['title']}' is not swappable")
        if not old.get("swap_group") or old["swap_group"] != new.get("swap_group"):
            raise SwapError(
                f"'{new['title']}' is not in the same swap_group as "
                f"'{old['title']}' ({old.get('swap_group')})"
            )
        if old["component_type"] != new["component_type"]:
            raise SwapError(
                "replacement must be the same component_type "
                f"({old['component_type']})"
            )
        if component_id == replacement_component_id:
            raise SwapError("replacement must differ from the current component")
        return old, new, "ok"

    def swap_alternatives(self, component_id: str) -> list[dict[str, Any]]:
        """Alternatives for a component, per the PackagePro swap convention.

        An alternative is a row in the same package and the same
        ``swap_group``. In the supplied data each multi-member swap_group
        contains exactly two rows (a day-1 POI and a day-2 POI), so swapping
        keeps the traveller inside the same package and the same curated POI
        set — the itinerary day and slot of the chosen activity stay put, and
        only the activity itself changes.
        """
        c = self.pro.component(component_id)
        if c is None or not c.get("swap_group") or int(c["is_swappable"]) != 1:
            return []
        return [
            a
            for a in self.pro.swap_alternatives(c["package_id"], c["swap_group"])
            if a["component_id"] != component_id
        ]

    def apply_swap(self, component_id: str, replacement_component_id: str) -> dict[str, Any]:
        old, new, _ = self.validate_swap(component_id, replacement_component_id)
        delta = pricing.swap_delta(old, new)
        package_total = pricing.apply_swap(self.package_total(), old, new)
        guide = self.guide_total()
        new_total = quantize_money(package_total + guide)

        overrides = dict(self.session.get("component_overrides_map") or {})
        overrides[component_id] = replacement_component_id
        self.sessions.update_session(
            self.session_id, component_overrides_map=overrides
        )
        self.sessions.update_session(
            self.session_id,
            total_amount=money_str(new_total),
            currency=new["currency"],
        )
        self._persist_cart()
        self.session = self.sessions.get_session(self.session_id)

        return {
            "old": old,
            "new": new,
            "delta": money_str(delta),
            "package_total": money_str(package_total),
            "total": money_str(new_total),
            "currency": new["currency"],
        }

    # ------------------------------------------------------------------
    # Optional component removal / re-add
    # ------------------------------------------------------------------

    def remove_optional(self, component_id: str) -> dict[str, Any]:
        c = self.pro.component(component_id)
        if c is None:
            raise SwapError(f"unknown component {component_id}")
        if int(c["is_optional"]) != 1:
            raise SwapError(f"'{c['title']}' is not optional and cannot be removed")
        removed = list(self.session.get("removed_optional_list") or [])
        if component_id not in removed:
            removed.append(component_id)
        self.sessions.update_session(self.session_id, removed_optional_list=removed)
        self.session = self.sessions.get_session(self.session_id)
        new_total = self.current_total()
        self.sessions.update_session(
            self.session_id, total_amount=money_str(new_total), currency=c["currency"]
        )
        self._persist_cart()
        self.session = self.sessions.get_session(self.session_id)
        return {
            "component": c,
            "delta": money_str(-dec(c["price_delta"])),
            "total": money_str(new_total),
            "currency": c["currency"],
        }

    def restore_optional(self, component_id: str) -> dict[str, Any]:
        c = self.pro.component(component_id)
        if c is None:
            raise SwapError(f"unknown component {component_id}")
        removed = [x for x in (self.session.get("removed_optional_list") or []) if x != component_id]
        self.sessions.update_session(self.session_id, removed_optional_list=removed)
        self.session = self.sessions.get_session(self.session_id)
        new_total = self.current_total()
        self.sessions.update_session(
            self.session_id, total_amount=money_str(new_total), currency=c["currency"]
        )
        self._persist_cart()
        self.session = self.sessions.get_session(self.session_id)
        return {
            "component": c,
            "delta": money_str(dec(c["price_delta"])),
            "total": money_str(new_total),
            "currency": c["currency"],
        }

    # ------------------------------------------------------------------
    # Ledger
    # ------------------------------------------------------------------

    def _persist_cart(self) -> None:
        pkg = self.pro.package(self.package_id)
        currency = pkg["currency"]
        lines: list[dict[str, Any]] = []
        base = dec(pkg["base_price"])
        lines.append(
            {
                "line_type": "package_base",
                "source_table": "PackagePro.tour_packages",
                "source_id": pkg["package_id"],
                "title": f"{pkg['name']} — base price",
                "amount": money_str(base),
                "currency": currency,
                "signed_delta": money_str(base),
                "meta": {"package_id": pkg["package_id"], "tier": pkg["tier"]},
            }
        )
        overrides = self.session.get("component_overrides_map") or {}
        for c in self.effective_components():
            cid = c["component_id"]
            replaced = cid in overrides.values()
            replaces = next(
                (k for k, v in overrides.items() if v == cid), None
            )
            delta = dec(c["price_delta"])
            lines.append(
                {
                    "line_type": (
                        "component_included" if int(c["is_optional"]) == 0 else "component_optional"
                    ),
                    "source_table": "PackagePro.package_components",
                    "source_id": cid,
                    "title": (
                        f"Day {c['day_index']} · {c['slot']} · {c['title']}"
                    ),
                    "amount": money_str(delta),
                    "currency": c["currency"],
                    "signed_delta": money_str(delta),
                    "meta": {
                        "day_index": c["day_index"],
                        "slot": c["slot"],
                        "component_type": c["component_type"],
                        "replaces": replaces,
                        "replaced": replaced,
                    },
                }
            )
        gid = self.session.get("selected_guide_id")
        if gid:
            guide = self.pro.guide(gid)
            if guide:
                cost = self.guide_total()
                lines.append(
                    {
                        "line_type": "guide",
                        "source_table": "PackagePro.tour_guides + guide_availability",
                        "source_id": gid,
                        "title": (
                            f"Guide · {guide['display_name']} · "
                            f"{self.session.get('guide_service') or 'full_day'}"
                        ),
                        "amount": money_str(cost),
                        "currency": guide["currency"],
                        "signed_delta": money_str(cost),
                        "meta": {
                            "multiplier": self.session.get("guide_multiplier"),
                            "service": self.session.get("guide_service"),
                        },
                    }
                )
        self.sessions.replace_cart(self.session_id, lines)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def itinerary(self) -> ItineraryResponse:
        pkg = self.pro.package(self.package_id)
        comps = self.effective_components()
        removed = set(self.session.get("removed_optional_list") or [])
        all_components = self.base_components

        by_day: dict[int, list[dict[str, Any]]] = {}
        for c in comps:
            by_day.setdefault(int(c["day_index"]), []).append(c)

        days = []
        for day_index in sorted(by_day):
            day_comps = sorted(
                by_day[day_index], key=lambda c: (SLOT_ORDER.get(c["slot"], 9), c["component_id"])
            )
            days.append(
                DayPlanModel(
                    day_index=day_index,
                    components=[component_model(c) for c in day_comps],
                )
            )

        budget = self._budget_state()
        guide_model = None
        gid = self.session.get("selected_guide_id")
        if gid:
            guide = self.pro.guide(gid)
            if guide:
                entries = match_guides(
                    self.pro,
                    guide["city_id"],
                    [self.session["request"].get("preferred_languages", [])[0]
                     if self.session["request"].get("preferred_languages") else "en-IN"],
                    self.session.get("theme"),
                    self.session["start_date"],
                    self.session["end_date"],
                )
                hit = next((e for e in entries if e["guide"]["guide_id"] == gid), None)
                if hit:
                    guide_model = to_guide_model(
                        hit, selected=True,
                        service=self.session.get("guide_service") or "full_day",
                    )

        return ItineraryResponse(
            session_id=self.session_id,
            package_id=pkg["package_id"],
            package_name=pkg["name"],
            days=days,
            components=[component_model(c) for c in all_components],
            included_total=f"{pricing.included_total(pkg['base_price'], all_components):.2f}",
            current_total=f"{self.current_total():.2f}",
            currency=pkg["currency"],
            budget=budget,
            selected_guide=guide_model,
            swaps=self._swap_history(),
        )

    def _swap_history(self) -> list[dict[str, Any]]:
        overrides = self.session.get("component_overrides_map") or {}
        history = []
        for old_id, new_id in overrides.items():
            old = self.pro.component(old_id)
            new = self.pro.component(new_id)
            if old and new:
                history.append(
                    {
                        "component_id": old_id,
                        "replacement_component_id": new_id,
                        "from_title": old["title"],
                        "to_title": new["title"],
                        "delta": money_str(pricing.swap_delta(old, new)),
                        "currency": new["currency"],
                    }
                )
        return history

    def _budget_state(self) -> dict[str, Any]:
        cap = dec(self.session["budget_amount"])
        currency = str(self.session["budget_currency"])
        total = self.current_total()
        rem = pricing.remaining(cap, total)
        over = pricing.overage(cap, total)
        return {
            "cap": money_str(cap),
            "currency": currency,
            "total": money_str(total),
            "remaining": money_str(rem),
            "decision": "approved" if over is None else "blocked",
            "overage": money_str(over) if over is not None else None,
            "negotiation_options": [] if over is None else [
                "select_cheaper_alternative",
                "remove_optional_component",
                "raise_budget_cap",
                "approve_overage",
            ],
        }
