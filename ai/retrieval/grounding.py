"""Grounding layer — ensures LLM explanations reference actual DB data.

Every LLM response is grounded in facts retrieved from PS-04.db. This
module provides helpers to build grounded context for prompts so the LLM
cannot hallucinate package names, prices, or availability.
"""
from __future__ import annotations

from typing import Any, Optional


def build_package_context(package: dict[str, Any], city: dict[str, Any]) -> dict[str, str]:
    """Build a grounded context dict from actual DB rows for recommendation prompts."""
    return {
        "package_name": package.get("name", "Unknown"),
        "city_name": city.get("name", "Unknown"),
        "duration_days": str(package.get("duration_days", "?")),
        "theme": package.get("theme", "general"),
        "base_price": str(package.get("base_price", "0")),
        "languages": package.get("languages_offered", ""),
    }


def build_swap_context(
    old_comp: dict[str, Any],
    new_comp: dict[str, Any],
    new_total: str,
    remaining: str,
) -> dict[str, str]:
    """Build a grounded context dict from actual component rows for swap prompts."""
    return {
        "old_component": old_comp.get("title", "Unknown"),
        "old_delta": str(old_comp.get("price_delta", "0")),
        "new_component": new_comp.get("title", "Unknown"),
        "new_delta": str(new_comp.get("price_delta", "0")),
        "new_total": new_total,
        "remaining": remaining,
    }


def build_budget_context(
    decision: str,
    proposed_total: str,
    budget_cap: str,
    overage: Optional[str] = None,
    options: Optional[list[str]] = None,
) -> dict[str, str]:
    """Build a grounded context dict for budget decision prompts."""
    overage_line = f"Overage: ₹{overage}" if overage else "Within budget."
    options_text = ""
    if options:
        options_text = "Options offered:\n" + "\n".join(f"- {o}" for o in options)
    return {
        "decision": decision,
        "proposed_total": proposed_total,
        "budget_cap": budget_cap,
        "overage_line": overage_line,
        "options_text": options_text,
    }
