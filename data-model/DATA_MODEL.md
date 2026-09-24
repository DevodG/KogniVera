# Data Model — Waypoint (PS-04: PackagePro)

## Source of truth

The canonical shared data model is `PackagePro/data/PS-04.db` (SQLite, **28,103 rows across 21 tables**).
Waypoint opens this file **read-only** (`mode=ro` in code — see [`backend/app/db/packagepro.py`](../backend/app/db/packagepro.py) line 47–48).

All Waypoint session, cart, audit, and trace state lives in a **separate** SQLite database (`waypoint_sessions.db`), never in the canonical DB.

---

## Canonical tables used by Waypoint

| # | Table | Rows | How Waypoint uses it |
|---|-------|------|----------------------|
| D1 | `cities` | 60 | Geographic anchor. Every package lookup starts with a `city_id`. Destination selector in the frontend. |
| D2 | `tour_packages` | 60 | Core catalogue. Filtered by city, status, currency (INR only), group size, duration, and language eligibility. Deterministic scoring ranks matches. |
| D3 | `package_components` | 420 | The swappable line items. Grouped by `day_index`/`slot`, with signed `price_delta` re-priced via `Decimal`. `swap_group` constrains which alternatives the user can pick. |
| D4 | `tour_guides` | 120 | Selectable by city, language match, specialisation. Day/half-day rate priced in `Decimal`. |
| D5 | `guide_availability` | 3,600 | Real per-date availability calendar (September 2026). `is_available`, `price_multiplier` applied server-side. |
| D6 | `languages` | 26 | BCP-47 tags used everywhere: package `languages_offered` matching, guide language filtering, UI presets. |
| D7 | `price_history` | 5,950 | Optional explainability. Exposes historical pricing factors (`demand_index`, `seasonality_factor`, etc.) for room types, fares, and guides. |
| D8 | `currencies` | 25 | Reference. Used for `minor_unit_exponent` and display. Waypoint enforces INR-only; non-INR packages are filtered out. |
| D9 | `categories` | 70 | Two-level taxonomy (package theme, POI type). Used to match user `theme` preference to package theme. |

### Also referenced (joined through, not primary)

| Table | Rows | Usage |
|-------|------|-------|
| `countries` | 30 | Joined via `cities.country_code` for display. |
| `amenities` | 60 | Available for filter expansion (not yet wired to UI). |
| `hotel_room_types` | 1,200 | Referenced by `price_history` entity lookups. |
| `hotels` | 300 | Entity resolution for hotel-type components. |
| `hotel_media` | 1,500 | Available for image display (future). |
| `bookings` | 1,996 | Order header structure (mock confirmation writes to session DB, not here). |
| `trips` | 600 | Container for dates/party/budget. Waypoint maintains its own session model. |
| `itineraries` | 803 | Versioned plans. Waypoint builds its own itinerary from `package_components`. |
| `itinerary_items` | 8,583 | Item atoms. Waypoint uses `package_components` directly instead. |
| `transfers` | 300 | Airport/intercity legs (available, not yet wired). |
| `user_preferences` | 1,200 | Explicit preference signal (language preference read capability). |
| `users` | 1,200 | Traveller identity (Waypoint uses anonymous sessions). |

---

## Additions (Waypoint-owned tables)

Waypoint creates its own `waypoint_sessions.db` with these tables. **None modify the canonical DB.**

| Table | Purpose |
|-------|---------|
| `sessions` | Stores session state (city, dates, travellers, budget cap, selected package, guide, preferences, language). Keyed by `session_id`. |
| `cart_items` | Persisted cart: tracks which components are selected and any swaps, with `price_delta` in `Decimal`. |
| `trace_events` | Structured transparency log: step name, action, status, source table, input/result summaries, user-safe reasoning. |
| `audit_log` | Every BudgetGuard decision: `approved`, `blocked`, or `negotiation_required`, with proposed total, cap, overage, and the four trade-off options offered. |

---

## Boundary rules enforced in code

| Rule | Enforcement | Code location | Test |
|------|-------------|---------------|------|
| **INR only** | Non-INR packages filtered out during recommendation | [`services/recommender.py`](../backend/app/services/recommender.py) | `test_recommendation.py` |
| **Money is `Decimal`, never `float`** | `dec()` rejects Python `float` with an explicit error | [`db/packagepro.py`](../backend/app/db/packagepro.py) L245–261 | `test_pricing.py` |
| **Budget cap is hard** | `BudgetGuard.decide()` blocks any proposed total > cap | [`services/budget.py`](../backend/app/services/budget.py) | `test_budget.py` |
| **`price_delta` is signed** | Totals computed as `base_price + Σ(deltas)` using `Decimal` | [`services/itinerary.py`](../backend/app/services/itinerary.py) | `test_itinerary.py` |
| **Group size bounds** | `min_group_size ≤ travellers ≤ max_group_size` checked | [`services/recommender.py`](../backend/app/services/recommender.py) | `test_recommendation.py` |
| **Duration fits date range** | `duration_days ≤ (end_date - start_date).days + 1` | [`services/recommender.py`](../backend/app/services/recommender.py) | `test_recommendation.py` |
| **Swap constrained to `swap_group`** | Only alternatives from same `package_id` and `swap_group` | [`services/itinerary.py`](../backend/app/services/itinerary.py) | `test_itinerary.py` |
| **Guide availability is real** | Checked against `guide_availability.for_date` rows | [`services/guides.py`](../backend/app/services/guides.py) | `test_guides.py` |
| **PS-04.db is read-only** | Opened with `mode=ro` URI parameter | [`db/packagepro.py`](../backend/app/db/packagepro.py) L47–48 | `test_reference.py` |
| **No payment, mock only** | `POST /confirm` writes mock status to session DB only | [`agent/solver.py`](../backend/app/agent/solver.py) | `test_receipt_confirm.py` |
