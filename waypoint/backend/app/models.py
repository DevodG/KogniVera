"""Pydantic models for the Waypoint API.

Money rule (R3): every amount is carried as a two-decimal *string* together
with an ISO-4217 currency code. Amounts are converted to ``Decimal`` on the
server for all arithmetic and are never exposed as JSON numbers.
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

_MONEY_RE = re.compile(r"^-?\d+(\.\d{1,2})?$")

BUDGET_NEGOTIATION_OPTIONS = [
    "select_cheaper_alternative",
    "remove_optional_component",
    "raise_budget_cap",
    "approve_overage",
]


class Money(BaseModel):
    """A money pair: fixed-point decimal string + ISO-4217 currency."""

    amount: str = Field(..., description="Two-decimal decimal string, e.g. '20000.00'")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO-4217 code")

    @field_validator("amount")
    @classmethod
    def _amount_must_be_two_place_decimal(cls, v: str) -> str:
        return validate_money_string(v)

    def as_decimal(self) -> Decimal:
        return Decimal(self.amount)

    def format(self) -> str:
        return format_money(self.as_decimal(), self.currency)


class PlannerRequest(BaseModel):
    city_id: str = Field(..., description="Opaque PackagePro city ID")
    start_date: str = Field(..., description="ISO-8601 calendar date")
    end_date: str = Field(..., description="ISO-8601 calendar date")
    travelers: int = Field(..., ge=1, le=50)
    budget: Money
    preferred_languages: list[str] = Field(..., min_length=1, description="BCP-47 tags")
    theme: Optional[str] = Field(None, description="e.g. 'heritage'; optional")
    goal: Optional[str] = Field(None, description="Free-text traveller goal")


class SwapRequest(BaseModel):
    component_id: str
    replacement_component_id: str


class SelectGuideRequest(BaseModel):
    guide_id: str
    service: str = Field("full_day", description="'full_day' or 'half_day'")


class NegotiateRequest(BaseModel):
    option: str = Field(..., description="One of the budget negotiation options")
    component_id: Optional[str] = None
    replacement_component_id: Optional[str] = None
    new_budget: Optional[Money] = None
    guide_id: Optional[str] = None
    service: Optional[str] = None

    @field_validator("option")
    @classmethod
    def _option_is_legal(cls, v: str) -> str:
        if v not in BUDGET_NEGOTIATION_OPTIONS:
            raise ValueError(
                f"option must be one of {', '.join(BUDGET_NEGOTIATION_OPTIONS)}"
            )
        return v


class ConfirmRequest(BaseModel):
    pass


# --------------------------------------------------------------------------
# Response models
# --------------------------------------------------------------------------


class CityModel(BaseModel):
    city_id: str
    name: str
    state: Optional[str] = None
    country_code: str
    timezone: str
    region: str
    primary_language: str


class LanguageModel(BaseModel):
    bcp47: str
    english_name: str
    native_name: str
    script: str


class PackageComponentModel(BaseModel):
    component_id: str
    component_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    day_index: int
    slot: str
    title: str
    quantity: int
    price_delta: str
    currency: str
    is_optional: bool
    is_swappable: bool
    swap_group: Optional[str] = None
    selected: bool = True
    source: str = "PackagePro.package_components"


class RecommendationModel(BaseModel):
    rank: int
    package_id: str
    city_id: str
    city_name: str
    name: str
    theme: str
    tier: str
    duration_days: int
    duration_nights: int
    base_price: str
    currency: str
    included_total: str
    min_group_size: int
    max_group_size: int
    languages_offered: list[str]
    inclusions: str
    exclusions: str
    description: str
    match_score: int
    match_reasons: list[str]
    within_budget: bool
    source: str = "PackagePro.tour_packages"


class TraceEventModel(BaseModel):
    step: int
    action: str
    status: str
    source: str
    input_summary: str
    result_summary: str
    user_safe_reason: str
    occurred_at: str


class BudgetStateModel(BaseModel):
    cap: str
    currency: str
    total: str
    remaining: str
    decision: str
    overage: Optional[str] = None
    negotiation_options: list[str] = Field(default_factory=list)


class DayPlanModel(BaseModel):
    day_index: int
    date: Optional[str] = None
    components: list[PackageComponentModel]


class GuideAvailabilityModel(BaseModel):
    for_date: str
    is_available: bool
    slots_available: int
    price_multiplier: str


class GuideModel(BaseModel):
    guide_id: str
    display_name: str
    languages: list[str]
    specialisation: str
    secondary_specialisation: Optional[str] = None
    years_experience: int
    rating: Optional[str] = None
    review_count: int
    day_rate: str
    half_day_rate: str
    currency: str
    certified: bool
    bio: str
    city_id: str
    available: bool
    available_days: list[GuideAvailabilityModel] = Field(default_factory=list)
    unavailable_days: list[GuideAvailabilityModel] = Field(default_factory=list)
    selected_cost: Optional[str] = None
    selected_multiplier: Optional[str] = None
    selected_service: Optional[str] = None
    fit_reason: str
    source: str = "PackagePro.tour_guides + guide_availability"


class ItineraryResponse(BaseModel):
    session_id: str
    package_id: str
    package_name: str
    days: list[DayPlanModel]
    components: list[PackageComponentModel]
    included_total: str
    current_total: str
    currency: str
    budget: BudgetStateModel
    selected_guide: Optional[GuideModel] = None
    selected_flight: Optional[dict[str, Any]] = None
    selected_hotel: Optional[dict[str, Any]] = None
    swaps: list[dict[str, Any]] = Field(default_factory=list)


class SessionResponse(BaseModel):
    session_id: str
    status: str
    request: Optional[PlannerRequest] = None
    plan_steps: list[str] = Field(default_factory=list)
    recommendations: list[RecommendationModel] = Field(default_factory=list)
    selected_package_id: Optional[str] = None
    selected_guide_id: Optional[str] = None
    selected_flight: Optional[dict[str, Any]] = None
    selected_hotel: Optional[dict[str, Any]] = None
    ai_explanation: Optional[str] = None
    budget: Optional[BudgetStateModel] = None
    trace: list[TraceEventModel] = Field(default_factory=list)
    audit: list[dict[str, Any]] = Field(default_factory=list)
    confirmed: bool = False
    confirmation: Optional[dict[str, Any]] = None


class TrustReceiptRow(BaseModel):
    decision: str
    source: str
    why_selected: str
    price_effect: str
    currency: str


class TrustReceiptModel(BaseModel):
    session_id: str
    rows: list[TrustReceiptRow]
    totals: dict[str, str]
    budget_guard: str
    data_backed_plan: bool
    automatic_booking_disabled: bool = True
    user_confirmation_required: bool = True
    confirmed: bool
    confirmation: Optional[dict[str, Any]] = None
    trace: list[TraceEventModel] = Field(default_factory=list)


class HealthModel(BaseModel):
    status: str
    packagepro_db: str
    packagepro_path: str
    session_db: str
    rows: dict[str, int]
    ai_key_configured: bool


def validate_money_string(v: Any) -> str:
    """Accept Decimal/int/str and normalise to an exact two-decimal string."""
    if isinstance(v, Decimal):
        s = format(Decimal(v).quantize(Decimal("0.01")), "f")
    elif isinstance(v, int):
        s = f"{v}.00"
    elif isinstance(v, float):
        raise ValueError("float money is forbidden; pass a decimal string")
    else:
        s = str(v).strip()
    if not _MONEY_RE.match(s):
        raise ValueError(f"not a valid two-place decimal money string: {v!r}")
    return s


def quantize_money(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"))


def format_money(amount: Decimal, currency: str) -> str:
    """Human-readable money string with the currency's symbol."""
    symbols = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "AED": "د.إ"}
    q = quantize_money(Decimal(amount))
    sym = symbols.get(currency.upper(), "")
    return f"{sym}{q:,.2f}"


def money_str(d: Decimal) -> str:
    return format(quantize_money(Decimal(d)), "f")
