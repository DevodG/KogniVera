# KogniVera Hackathon 2026 — PS-04: PackagePro — Dynamic Tour Packages
## COMPLETE PROJECT ANALYSIS FOR DESIGN SUBMISSION PPT

> **Purpose of this document**: This is a deep, exhaustive analysis of our entire project — codebase, data model, architecture, AI features, and hackathon requirements. Feed this to an AI and ask it to create a **winning design submission** (PPT/PDF) for the KogniVera Hackathon 2026. **Submission deadline: 2 September 2026. ONE upload, locked after submission.**

---

## TABLE OF CONTENTS
1. [Team & Problem Statement](#1-team--problem-statement)
2. [Problem Understanding](#2-problem-understanding)
3. [Scope — IN vs. OUT](#3-scope--in-vs-out)
4. [Complete Data Model Analysis](#4-complete-data-model-analysis)
5. [System Architecture — Complete](#5-system-architecture--complete)
6. [User Journey — End to End](#6-user-journey--end-to-end)
7. [AI Features — Detailed Design](#7-ai-features--detailed-design)
8. [Business Benefits](#8-business-benefits)
9. [Tech Stack — With Rationale](#9-tech-stack--with-rationale)
10. [24-Hour Build Plan](#10-24-hour-build-plan)
11. [Risks & Fallbacks](#11-risks--fallbacks)
12. [Multilingual Approach](#12-multilingual-approach)
13. [Codebase Deep Dive](#13-codebase-deep-dive)
14. [Submission Checklist](#14-submission-checklist)

---

## 1. TEAM & PROBLEM STATEMENT

- **Problem Statement**: PS-04 — PackagePro — Dynamic Tour Packages
- **Hackathon**: Kognivera Hackathon 2026 · Travel & Tourism
- **Product Name**: **Waypoint** — Agentic Travel Concierge
- **Team Name**: *(FILL IN)*
- **Team Members & Roles**: *(FILL IN — 3 to 5 members, each with a clear role)*

### Key Dates
| Date | What |
|------|------|
| **2 September 2026** | Design submission closes (ONE upload, then locked) |
| By 17 September 2026 | Teams confirmed |
| **24 Sep 12:00 → 25 Sep 12:00** | 24-hour build sprint |
| 25 September 12:00 | Hard stop — submission closes |
| 25 September post-lunch | Presentations |
| 26 September | Finale and prizes |

---

## 2. PROBLEM UNDERSTANDING

### The Core Problem (in our own words — NOT copied from the statement)
The travel industry has a trust problem with AI. Only ~8% of travelers currently trust AI to book on their behalf. Existing AI travel tools compete on **prettier itineraries** — but travelers are afraid of hidden costs, auto-bookings without consent, and opaque decision-making. Nobody wants an AI to silently overspend their budget or book a hotel they never approved.

### What PS-04 Specifically Asks For
**PackagePro — Dynamic Tour Packages** asks us to build a system that takes **curated tour packages** (60 packages with 420 individually swappable components) and makes them **dynamic**: let travelers customize, swap components, reprice in real-time, match language preferences, and attach local guides — all without the package losing coherence or the traveler losing control of their budget.

### The Gap We're Filling
The core requirement is: **a tour package that reacts to the traveler, not the other way around.** Swap the hotel? The price updates live. Want a Tamil-speaking heritage guide on Day 3? The system filters, checks availability, reprices, and stays under budget — or tells you honestly why it can't.

Our thesis: **Trust, not prettiness, wins.** An agent that shows its plan before acting, calls real tools, and is *structurally incapable* of spending past a budget cap you set — because the guardrail is enforced in code, not by asking the model nicely.

---

## 3. SCOPE — IN vs. OUT

### ✅ What We WILL Build in 24 Hours (MVP)

| # | Feature | Category | Status |
|---|---------|----------|--------|
| 1 | **Dynamic package customization** — swap components (hotels, POIs, guides, transfers, meals) within packages, with live repricing using `price_delta` from `package_components` | Core | Pre-built |
| 2 | **Hard budget cap enforcement** — `BudgetGuard` in code (not LLM prompt) prevents any over-cap spend; offers 4 structured negotiation trade-offs instead of flat refusal | Core Trust | ✅ Done |
| 3 | **Plan-before-act timeline** — visible step-by-step plan shown BEFORE the agent executes anything | Core Trust | ✅ Done |
| 4 | **User-driven selection** — traveler picks their own flights, hotels, guides (not auto-booked by AI) | Core Trust | ✅ Done |
| 5 | **Live cost ledger** — real-time running total vs. budget cap, updated as user makes selections | Differentiator | ✅ Done |
| 6 | **Confidence-scored recommendations** — AI self-reports confidence on each recommendation | Differentiator | ✅ Done |
| 7 | **Negotiation instead of flat refusal** — over-budget triggers 4 structured trade-off options (approve overage, swap cheaper, remove item, raise cap) | Differentiator | ✅ Done |
| 8 | **Tour guide matching** — filter 120 guides by language (BCP-47), specialization, availability calendar, and day rate | PS-04 Specific | To wire to DB |
| 9 | **Language-preference filtering** — packages filtered by `languages_offered`, guides filtered by `languages` field, UI respects user's `preferred_languages` | PS-04 Specific | To wire to DB |
| 10 | **Confirmation gate before booking** — nothing is "booked" without explicit user confirm | Core Trust | ✅ Done |
| 11 | **Live agent trace** — full reasoning/tool-call/decision log visible to user in real-time | Demo Polish | ✅ Done |
| 12 | **Resumable session state** — SQLite-backed, swappable to Postgres; sessions survive restarts | Core | ✅ Done |
| 13 | **Multilingual UI** — at least Hindi and Tamil alongside English, using BCP-47 tags from the `languages` table | Required | To build |
| 14 | **Integration with provided database** — query `PS-04.db` (28,103 rows, 21 tables) for real package data, guides, availability, pricing | Required | To wire |

### ❌ What We Are Deliberately LEAVING OUT (and why)

| Feature | Why We're Cutting It |
|---------|---------------------|
| **Real Amadeus/Hotelbeds API integration** | Mock data is faster and more reliable for a 24-hour demo. The swap-in architecture (`USE_REAL_*` flags) proves we can go live without code changes. |
| **Real payment processing (Stripe/Razorpay)** | The confirm gate is the trust feature; the payment backend is commodity plumbing. Mocked behind one endpoint. |
| **Constraint-solver optimization (OR-Tools)** | Replaces heuristic picks with real optimization — valuable but scope-creep for 24 hours. The heuristic works. |
| **Preference memory across sessions** | Needs a `users` table + embedding store. Cold-start from provided user data is sufficient. |
| **Group budget splitting** | Per-traveler sub-caps are a nice-to-have, not core to the PS-04 requirement. |
| **Proactive monitoring / rebooking agent** | Background worker for price drops — a Week 4 feature, not a 24-hour feature. |
| **Voice narration (TTS)** | Demo polish, not core trust or PS-04 requirement. |
| **Mobile-responsive layout** | Current layout works on desktop/tablet. Sub-700px stacked layout is polish. |
| **Multi-agent transparency view** | Only valuable if we split to multi-agent (flight/hotel/budget agents). Single graph is simpler and sufficient. |
| **XR / AR / VR** | We are NOT an XR statement. No XR device declaration needed. |

> **Why this scope works**: Every "IN" item directly addresses either the PS-04 core requirement (dynamic packages, guides, language, repricing) or the trust thesis (budget guard, plan-before-act, user-driven selection). Every "OUT" item is either commodity infrastructure or a differentiator that doesn't fit 24 hours.

---

## 4. COMPLETE DATA MODEL ANALYSIS

### 4.1 The Provided Database
- **Database**: `PS-04.db` (SQLite, 7MB, indexed, ready to query)
- **Total**: 28,103 rows across 21 tables (20 statement tables + 1 reference table)
- **Also provided as**: CSV files, DDL for Postgres and SQLite

### 4.2 Tables We WILL Use (and how)

| Table | Rows | How We Use It |
|-------|------|---------------|
| **`tour_packages`** | 60 | The starting point — curated packages with themes (adventure/honeymoon/pilgrimage/family/heritage/wellness/wildlife/food_trail), tiers (standard/deluxe/premium), base pricing, language offerings |
| **`package_components`** | 420 | **THE CORE TABLE** — individually swappable lines with `price_delta` (signed!), `swap_group` for alternatives, `is_swappable`/`is_optional` flags. Day-indexed, time-slotted. |
| **`tour_guides`** | 120 | Guides with BCP-47 language tags, specializations (heritage/food/trekking/wildlife/photography/religious/shopping/accessibility), day/half-day rates, ratings |
| **`guide_availability`** | 3,600 | 30-day calendar per guide: `is_available`, `slots_available` (0/1/2 half-day), `price_multiplier` for peak dates |
| **`hotels`** | 300 | Rich properties with geo, ratings, reviews, room types, media, distance to center |
| **`hotel_room_types`** | 1,200 | Bookable units with occupancy, bed config, base rate, availability (scarce units for contention) |
| **`cities`** | 60 | Geographic anchor — every entity hangs off a city. Has timezone, season_profile, peak_months, primary_language |
| **`users`** | 1,200 | Traveler identity with `budget_band`, `travel_style`, `traveller_type`, `segment` (heavy/light/cold_start) |
| **`user_preferences`** | 1,200 | Explicit preferences: `preferred_languages`, `guide_language`, `interests`, `dietary_flags`, `accessibility_needs`, `pace` |
| **`trips`** | 600 | Trip container: dates, party size, destination, budget, status |
| **`itineraries`** | 803 | Versioned plans belonging to trips — `generated_by` tracks if user/AI/optimizer made it |
| **`itinerary_items`** | 8,583 | **The atom** — each item in an itinerary with cost, carbon_kg, duration, source, explanation, locked status |
| **`bookings`** | 1,996 | Order headers with idempotency keys, booking references, payment amounts |
| **`price_history`** | 5,950 | Price over time with driving factors (demand_index, occupancy, seasonality, competitor, event) — for explainability |
| **`transfers`** | 300 | Airport/intercity legs with cost, duration, carbon, accessibility, transport mode |
| **`categories`** | 70 | Two-level taxonomy for POI types, package themes, expense categories |
| **`amenities`** | 60 | Hotel amenities (connectivity, wellness, food, family, accessibility, etc.) |
| **`currencies`** | 25 | ISO-4217 with minor_unit_exponent for correct display of JPY/KWD |
| **`languages`** | 26 | BCP-47 tags with script, RTL flag, TTS support |
| **`countries`** | 30 | ISO country reference |
| **`hotel_media`** | 1,500 | Images with roles (hero/room/lobby/etc.) and alt text |

### 4.3 Critical Data Rules We Follow

| Rule | What It Means |
|------|---------------|
| **R1: Additive only** | We ADD columns/tables. We NEVER rename/drop provided fields. |
| **R2: IDs are opaque strings** | `htl_a91f3c`, `pkg_xxxx` — never parsed, never integers |
| **R3: Money is a pair** | Decimal(12,2) + ISO-4217 currency code. NEVER a float. |
| **R4: Time is ISO-8601 with offset** | `_at` fields carry offset; `_date` fields have no zone |
| **R5: Enums are lowercase snake_case** | Legal values in `enums.json` |
| **R6: Language is BCP-47** | `ta` not "Tamil", `hi` not "Hindi" |
| **R7: Geography is WGS-84** | 6 decimal places, lat+lng together or not at all |
| **R8: Nothing is hard-deleted** | Rows carry `status` and `updated_at` |

### 4.4 The `price_delta` Trap (Critical!)
> `price_delta` in `package_components` is **signed and can be negative**. Repricing formula: `base_price + Σ(price_deltas you keep)`. Must use `Decimal` arithmetic — a float produces totals that are ₹0.01 off and impossible to explain to a judge.

### 4.5 Tables We Add (extensions, not renames)

| New Table | Purpose |
|-----------|---------|
| `sessions` | Agent session state (JSON blob of AgentState) — already built in `database.py` |
| *(Optional)* `agent_audit_log` | Exportable decision audit trail from BudgetGuard |

### 4.6 Starter Query Insights (We ran them)

**Query 1 — Package decomposed into swappable lines**: A package like "Kandy Food Trail" has 7 components across 4 days — hotel, POIs, transfers, guides, meals, entry tickets — each individually swappable with signed price deltas in LKR.

**Query 2 — Swap alternatives**: Components sharing a `swap_group` are alternatives for each other. E.g., `poi_4071` group offers "Kandy Bazaar" vs alternatives. This is the core PS-04 requirement.

**Query 3 — Live repricing**: Base price + sum of non-optional deltas. E.g., "Bali Wildlife" goes from ₹8.5M IDR base to ₹9.7M IDR with included components.

**Query 4 — Guides by language**: 15 Tamil-speaking guides found, rated 3.5–5.0, across Chennai, Madurai, Ooty, Thanjavur, Pondicherry — with specializations in heritage, food, photography, wildlife, accessibility.

**Query 5 — Guide availability**: Real availability calendar with peak-date multipliers (1.0×–1.35×). Some guides have 0 availability on certain dates. This is a state our UI must handle.

**Query 6 — Language-filtered packages**: 10 Hindi-offered packages found (Jaisalmer Food Trail, Agra Heritage, New Delhi Family, etc.) — this is the filter PS-04 asks us to demonstrate.

---

## 5. SYSTEM ARCHITECTURE — COMPLETE

### 5.1 Architecture Diagram (Mermaid — convert to visual for PPT)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React / Vite)                        │
│                                                                        │
│   IntakeForm → FlightPicker → HotelPicker → CartConfirm              │
│   PlanTimeline · CostLedger · AgentTraceFeed · NegotiationGate       │
│   ConfidenceBadge · PlacesGrid                                        │
│                                                                        │
│   Design: "Flight Log / Control Tower" — navy bg, amber accent,      │
│   IBM Plex Mono for data, Fraunces for headers                        │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │  HTTP/JSON (Vite proxy /api/* → :8000)
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                                │
│                                                                        │
│   POST /session           ← Start session (Phase 1: intake+search)   │
│   POST /session/{id}/select-flight  ← Phase 2: flight → budget → hotels │
│   POST /session/{id}/select-hotel   ← Phase 3: hotel → budget → cart   │
│   POST /session/{id}/negotiate      ← Budget negotiation              │
│   POST /session/{id}/confirm        ← Confirmation gate               │
│   GET  /session/{id}                ← Resume/poll state               │
│   GET  /health                      ← Health check                    │
│                                                                        │
│   ┌──────────────────────────────────────────────────────────────┐    │
│   │                AGENT STATE MACHINE (LangGraph)               │    │
│   │                                                              │    │
│   │  Phase 1: intake → plan → search_flights + search_places     │    │
│   │           → PAUSE (select_flight)                            │    │
│   │  Phase 2: user picks flight → budget_check → search_hotels   │    │
│   │           → PAUSE (select_hotel)                             │    │
│   │  Phase 3: user picks hotel → budget_check → propose_cart     │    │
│   │           → PAUSE (awaiting_confirmation)                    │    │
│   │  Phase 4: user confirms → done                               │    │
│   │                                                              │    │
│   │  Every node appends to `trace` (live agent thinking feed)    │    │
│   │  Every budget decision logged in `budget_decisions`          │    │
│   └──────────────────────────────────────────────────────────────┘    │
│                                                                        │
│   ┌─────────────────────────────┐  ┌─────────────────────────────┐   │
│   │    BUDGET GUARD (Hard Cap)  │  │     LLM CLIENT (Router)     │   │
│   │                             │  │                             │   │
│   │  - Code-enforced, not LLM   │  │  NVIDIA NIM (default)      │   │
│   │  - Never commits over-cap   │  │  OpenAI (swap-in)          │   │
│   │  - 4 negotiation options    │  │  Anthropic (swap-in)       │   │
│   │  - Audit trail exportable   │  │  GLM-5.2 / Nemotron-3     │   │
│   └─────────────────────────────┘  └─────────────────────────────┘   │
│                                                                        │
│   ┌─────────────────────────────┐  ┌─────────────────────────────┐   │
│   │     TOOLS (Mock + Real)     │  │    DATABASE (Persistence)   │   │
│   │                             │  │                             │   │
│   │  search_flights()           │  │  SQLite (dev) / Postgres    │   │
│   │  search_hotels()            │  │  Session state as JSON blob │   │
│   │  search_nearby_places()     │  │  PS-04.db for package data  │   │
│   │  check_budget()             │  │                             │   │
│   │  USE_REAL_* flag pattern    │  │  Resumable across restarts  │   │
│   └─────────────────────────────┘  └─────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES (all optional)                    │
│                                                                        │
│   NVIDIA NIM (GLM-5.2)  │  Amadeus (flights)  │  Hotelbeds (hotels)  │
│   Google Places (nearby) │  ExchangeRate API    │  Twilio/Resend (SMS)│
│                                                                        │
│   All have mock fallbacks. System degrades safely, never crashes.     │
└────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Agent State Machine Flow

```
[START] → intake (validate fields)
  ├─ missing fields? → needs_input (ask user)
  └─ all present → make_plan → search_flights + search_places
       └─ PAUSE: "select_flight" (user picks)
            └─ budget_check_flight
                 ├─ OVER CAP → needs_input (4 negotiation options)
                 └─ WITHIN CAP → search_hotels
                      └─ PAUSE: "select_hotel" (user picks)
                           └─ budget_check_hotel
                                ├─ OVER CAP → needs_input (4 negotiation options)
                                └─ WITHIN CAP → propose_cart
                                     └─ PAUSE: "awaiting_confirmation"
                                          └─ user confirms → DONE
```

### 5.3 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/session` | Start new planning session (Phase 1) |
| `GET` | `/session/{id}` | Retrieve session state |
| `POST` | `/session/{id}/select-flight` | User picks a flight (Phase 2) |
| `POST` | `/session/{id}/select-hotel` | User picks a hotel (Phase 3) |
| `POST` | `/session/{id}/negotiate` | Resolve budget over-cap negotiation |
| `POST` | `/session/{id}/confirm` | Explicit booking confirmation |
| `GET` | `/health` | Health check with LLM provider info |

---

## 6. USER JOURNEY — END TO END

### From the Traveler's Point of View

**Screen 1 — Intake Form**
The traveler enters: origin city, destination, travel dates, number of travelers, and a budget cap in their preferred currency. Defaults are pre-filled with a deliberately tight budget to demo the negotiation feature. The "flight log / control tower" design aesthetic (deep navy, amber accents, IBM Plex Mono for data) signals this is a tool that shows its work.

**Screen 2 — Flight Selection + Places Discovery**
The agent searches flights and nearby attractions simultaneously. A split layout shows:
- **Left**: Flight options as cards with airline, time, duration, price, and a confidence badge (0.7–0.98). User clicks to select.
- **Right**: Live cost ledger (running total vs. budget cap as a progress bar) and a places grid showing what's at the destination.
- **Bottom**: Collapsible agent trace log showing every tool call and reasoning step.
- **Top**: Progress bar: Details → Flight ✓ → Hotel → Review

**Screen 3 — Hotel Selection**
After locking in a flight, the agent searches hotels. Same split layout:
- **Left**: Hotel cards with name, city, rating, price/night, total price, nights, confidence.
- **Right**: Updated cost ledger showing flight cost + prospective hotel cost. If the combined total exceeds budget → **Negotiation Gate** appears.

**Screen 3b — Negotiation Gate (if over budget)**
Instead of a flat "no," the agent offers 4 structured trade-offs:
1. "Approve a ₹X overage for this item"
2. "Swap this item for a cheaper alternative and re-search"
3. "Remove this item and continue with what's already planned"
4. "Raise the overall trip budget cap"

This is the signature trust feature. The AI never silently overspends.

**Screen 4 — Cart Review + Confirmation**
Final cart shows flight + hotel + total + remaining budget. The traveler must explicitly click "Confirm Booking" — the confirmation gate. Nothing happens without consent. A "Plan another trip" button resets the flow.

### Key UX Principles
- **Plan shown BEFORE execution** — traveler always knows what will happen next
- **User drives selection** — AI suggests, human decides
- **Budget is an instrument reading, not a suggestion** — always visible, always enforced
- **Trace is transparent** — every reasoning step, tool call, and decision is logged and viewable

---

## 7. AI FEATURES — DETAILED DESIGN

### AI Feature 1: Budget Guard — Hard Spend Cap Enforcement

| Attribute | Detail |
|-----------|--------|
| **What it does** | Prevents any cost from being committed if it would push the running total over the user's budget cap. Enforced in Python code (`budget_guard.py`), NOT by LLM prompt. |
| **Where in the flow** | Called after every cost-adding step (flight selection, hotel selection, guide selection, component swap). |
| **How it's grounded** | Against the user's stated budget cap (numeric) and the actual prices from the database (Decimal arithmetic). No LLM hallucination possible — this is `if prospective_total > cap: block`. |
| **What happens on trigger** | Returns 4 structured negotiation options (not a flat refusal): approve overage, swap cheaper, remove item, raise cap. |
| **How we know it's working** | Unit tests (`test_budget_guard.py`): (1) allows spending within cap, (2) blocks over-cap and offers 4 negotiation options, (3) audit trail records every decision. The running total is NEVER committed on a blocked decision. |
| **Measurable target** | 0% unauthorized overspend. 100% of over-budget scenarios produce negotiation options. Verifiable via `guard.audit_trail()`. |

```python
# The actual guard — this is NOT a prompt, it's code
def add_cost(self, amount, label):
    prospective_total = self.running_total + amount
    overage = max(0.0, prospective_total - self.cap)
    if overage <= 0:
        self.running_total = prospective_total  # COMMIT
        return BudgetDecision(allowed=True, ...)
    else:
        # HARD STOP — do NOT commit the cost
        return BudgetDecision(allowed=False, negotiation_options=[
            f"Approve a {overage} {self.currency} overage",
            "Swap for cheaper alternative",
            "Remove this item",
            "Raise the budget cap",
        ])
```

### AI Feature 2: Intelligent Package Customization with Live Repricing

| Attribute | Detail |
|-----------|--------|
| **What it does** | Uses the LLM (NVIDIA NIM / GLM-5.2) to recommend which package components to swap based on traveler preferences, then reprices using `Decimal(base_price) + Σ(Decimal(price_delta))` for each kept component. |
| **Which data** | `tour_packages` (60 packages), `package_components` (420 swappable lines with `swap_group` linking alternatives), `price_history` (5,950 rows with demand/seasonality factors). |
| **Retrieved how** | SQL query against `PS-04.db`: join `package_components` on `package_id`, filter by `is_swappable=1` and `swap_group`, retrieve alternatives. |
| **Prompted how** | System prompt with user's `travel_style`, `budget_band`, `interests`, `dietary_flags`, `accessibility_needs`. The LLM ranks alternatives within each `swap_group` and explains its reasoning (visible in the trace feed). |
| **Grounded in what** | Real prices from the DB (not hallucinated), real availability from `guide_availability`, real language matches from `languages_offered` and `tour_guides.languages`. |
| **How we know it's right** | (1) Repriced total matches Decimal arithmetic exactly (no float drift). (2) Swapped components share the same `swap_group`. (3) Budget guard prevents overspend post-swap. |

### AI Feature 3: Language-Aware Guide Matching

| Attribute | Detail |
|-----------|--------|
| **What it does** | Matches travelers to tour guides based on their preferred language (`user_preferences.guide_language`), filtering by availability calendar and specialization. |
| **Which data** | `tour_guides` (120 guides, BCP-47 `languages` field), `guide_availability` (3,600 rows with `is_available`, `slots_available`, `price_multiplier`), `user_preferences.preferred_languages`. |
| **Retrieved how** | SQL: `WHERE g.languages LIKE '%{bcp47}%' AND g.status='active'` joined with `guide_availability WHERE for_date=X AND is_available=1 AND slots_available > 0`. |
| **Prompted how** | LLM receives filtered candidates with ratings, experience, specializations, and current multiplier. Ranks by match quality and explains: "Karthik Tanaka specializes in photography and speaks Tamil — matching your preference. Rating: 5.0, 21 years experience." |
| **Grounded in what** | Actual availability calendar (not assumed), actual pricing with peak multipliers, actual language tags (BCP-47, not freetext). |
| **Edge case** | "No guide free that day" is a real state — the UI shows it clearly and offers adjacent dates. |

### AI Feature 4: Confidence-Scored Recommendations

| Attribute | Detail |
|-----------|--------|
| **What it does** | Every recommendation (flight, hotel, guide, component swap) carries a confidence score (0.0–1.0) displayed as a visual badge in the UI. |
| **How it works** | For mock data: random(0.7, 0.98). For real data: model self-reports confidence based on match quality to user preferences. For DB-grounded results: higher confidence when more data points (reviews, ratings) are available. |
| **Why it matters** | Transparency. A 0.72 confidence tells the traveler "this is a reasonable match but there might be better options" — building trust through honesty rather than fake certainty. |

### AI Feature 5: Plan-Before-Act Transparency

| Attribute | Detail |
|-----------|--------|
| **What it does** | Before executing ANY search or action, the agent creates a visible step-by-step plan (`plan_steps`) rendered as a timeline in the UI. Each step shows status: pending → in_progress → done/failed. |
| **How it works** | `graph.py` calls `_plan_step()` at every node transition. The frontend renders `PlanTimeline.jsx` showing the sequence. |
| **Why it matters** | The traveler knows what will happen BEFORE it happens. No black-box decision-making. |

### AI Feature 6: Explainable Price Factors

| Attribute | Detail |
|-----------|--------|
| **What it does** | Uses `price_history` table (5,950 rows) to explain WHY a price is what it is: demand index, occupancy percentage, seasonality factor, event factor, competitor factor. |
| **Grounded in what** | Each `price_history` row has `demand_index`, `occupancy_pct`, `lead_time_factor`, `seasonality_factor`, `event_factor`, `competitor_factor`, `bound_clamped`, and a human-readable `explanation`. |
| **Why it matters** | "This hotel costs ₹6,500/night because occupancy is at 85% and Diwali is 2 weeks away (event_factor: 1.25)" builds trust. |

---

## 8. BUSINESS BENEFITS

### For the Traveler
| Benefit | What Changes |
|---------|-------------|
| **Zero unauthorized overspend** | Budget guard is code-enforced. No travel agent or AI has ever guaranteed this before. |
| **Full transparency** | Every AI decision is explained, every cost is itemized, every step is visible before execution. |
| **Personalized packages** | Language-matched guides, preference-driven component swaps, accessibility-aware filtering — the package adapts to you, not the other way around. |
| **Faster planning** | User-driven selection with AI-curated options: 3 flights, 3 hotels, filtered guides — not 500 raw search results. |
| **Negotiation, not refusal** | Over-budget? Here are 4 trade-offs. The AI works WITH you to find a fit, not against you. |

### For the Business
| Benefit | What Changes |
|---------|-------------|
| **Higher conversion** | Trust → confidence → booking. The 8% AI-trust gap closes when travelers see their budget is protected by code, not promises. |
| **Reduced support costs** | Explainable AI decisions → fewer "why was I charged this?" complaints. Audit trail is exportable. |
| **Dynamic inventory utilization** | Swappable components mean a "Deluxe Heritage" package that's sold out at one hotel can seamlessly swap to another without losing the sale. |
| **B2B configurable policy** | The budget guard architecture extends to any business rule: "no red-eyes for corporate travelers," "min 4-star for premium segment." |
| **Data-driven pricing** | Price history with factor decomposition enables dynamic pricing strategies grounded in demand, seasonality, and competition. |

### Key Metrics We Can Demonstrate
- **0% over-budget bookings** (hard guarantee, not probabilistic)
- **4 negotiation paths per over-budget event** (vs. 0 in traditional systems)
- **100% decision auditability** (every step logged with reasoning)
- **Sub-second repricing** (Decimal arithmetic, no API call needed)

---

## 9. TECH STACK — WITH RATIONALE

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | React 18 + Vite 5 | Fast HMR, JSX components, lightweight (no Next.js overhead for a single-page flow). |
| **Styling** | Vanilla CSS (custom properties) | Full control over the "flight log / control tower" design system. No Tailwind needed. |
| **Backend** | FastAPI (Python 3.11+) | Async, OpenAPI docs auto-generated, Pydantic validation for request/response schemas. |
| **Agent Orchestration** | LangGraph 0.2 | State machine with composable phases, built-in state persistence, clean node-based flow. |
| **LLM** | NVIDIA NIM (GLM-5.2 / Nemotron-3) via OpenAI-compatible API | Free tier, 1M context, strong function-calling. Swappable to OpenAI/Anthropic with one env var. |
| **Budget Guardrail** | Custom `BudgetGuard` class (Python) | Code-enforced, not prompt-enforced. Unit-tested. The entire trust thesis. |
| **Database (session state)** | SQLite (dev) → Postgres (prod) via SQLAlchemy async | Zero-setup locally, one URL change for production. JSON blob per session = maximum flexibility. |
| **Database (package data)** | SQLite `PS-04.db` (provided) | 28,103 rows, indexed, ready to query. Conformance-validated with `validate_conformance.py`. |
| **API Integrations** | Amadeus (flights), Hotelbeds (hotels), Google Places | All optional with mock fallbacks. `USE_REAL_*` flag pattern: real API auto-activates when env key is set. |
| **Testing** | pytest + pytest-asyncio | Budget guard is the trust-critical path → must be tested. |
| **Version Control** | Git | Standard. |

### Why NOT other technologies
- **Not Next.js**: No SSR needed for a single-page agent flow. Vite is lighter.
- **Not Tailwind**: Our design system has exactly 4 colors and 2 fonts. Custom properties are simpler.
- **Not LangChain (full)**: LangGraph is the orchestration piece we need. Full LangChain is heavyweight for our use case.
- **Not GPT-4 / Claude directly**: NVIDIA NIM is free, OpenAI-compatible, and function-calling-capable. Cost = $0.

---

## 10. 24-HOUR BUILD PLAN

> **Critical rule**: At 09:00 on Day 2, STOP building features. Last 3 hours = stabilize + rehearse.

### Hour-by-Hour Plan

| Time Block | Hours | Who | What |
|-----------|-------|-----|------|
| **12:00–13:00** | 1h | ALL | Agree: the ONE demo flow, who owns what, what to cut first if behind. Run `validate_conformance.py`. Load PS-04.db. |
| **13:00–16:00** | 3h | **Backend Lead** | Wire `PS-04.db` into the agent: package search → component swap → guide matching → availability check → repricing with Decimal. |
| | | **Frontend Lead** | Package browser UI: show packages → component list → swap interface → live reprice display. |
| | | **AI/Integration** | Prompt engineering: system prompt for package customization, guide recommendation, swap reasoning. Test with NIM. |
| **16:00–20:00** | 4h | **Backend Lead** | Complete guide availability integration. Wire `user_preferences` into filtering. Budget guard integration with package repricing. |
| | | **Frontend Lead** | Guide picker component, language filter UI, multilingual strings (Hindi + Tamil). |
| | | **AI/Integration** | Price explainability: pull `price_history` factors, format for UI. Confidence scoring calibration. |
| **20:00–00:00** | 4h | **ALL** | Integration testing: full demo flow end-to-end. Fix broken handoffs. Polish the negotiation → re-plan loop until smooth. |
| **00:00–04:00** | 4h | **Backend Lead** | Harden: error handling, edge cases (no guides available, all hotels over budget, empty swap groups). |
| | | **Frontend Lead** | Design polish: animations, loading states, responsive tweaks, confidence badges. |
| | | **AI/Integration** | Audit trail UI panel, trace feed polish, multilingual content verification. |
| **04:00–08:00** | 4h | **ALL** | Buffer. Fix whatever broke. Sleep in rotation if possible. |
| **08:00–09:00** | 1h | **ALL** | Final integration run. The demo flow must work perfectly once. |
| **09:00–11:00** | 2h | **ALL** | **STOP building.** Stabilize. Fix the demo path. Nothing new. Record a backup demo video. |
| **11:00–12:00** | 1h | **ALL** | Rehearse the demo TWICE, on the actual demo machine. Close everything else. |
| **12:00** | — | **ALL** | **HARD STOP.** Submit. |

### The Demo Flow We Rehearse
1. Start → intake form (pre-filled with tight budget for a Jaipur Heritage package)
2. Show the plan timeline rendering BEFORE any search
3. Browse Hindi-language packages from the DB → select one
4. Swap a component (e.g., swap a heritage POI for a food trail) → watch the price update live
5. Find a Tamil-speaking heritage guide → show availability calendar
6. Budget check → **trigger over-budget negotiation** (the money shot)
7. Pick a trade-off → agent re-plans → under budget
8. Confirm booking → trace shows full audit trail
9. **Show the budget guard code** — "this isn't a prompt, it's an `if` statement"

---

## 11. RISKS & FALLBACKS

| # | Risk | Likelihood | Impact | Fallback |
|---|------|-----------|--------|----------|
| 1 | **NVIDIA NIM API goes down or rate-limited during demo** | Medium | High — no LLM reasoning | The agent falls back to deterministic "cheapest first" picks. The trace feed shows "LLM call failed... falling back to cheapest option." **We demo this as a feature**: "the system degrades safely, it doesn't crash." |
| 2 | **PS-04.db integration takes longer than expected** | Medium | Medium — core feature delayed | We have working mock data for flights/hotels already. Worst case: demo the full flow with mock data, show the DB queries separately to prove we understand the data model. The architecture (flag-based swap) is the same either way. |
| 3 | **Venue WiFi fails during live demo** | High (per hackathon docs) | Critical — can't reach NIM | Pre-warm all API calls. Record a backup demo video before the presentation. The agent's mock-data fallback means the entire flow works offline except LLM reasoning. SQLite is local. |
| 4 | **Budget guard Decimal arithmetic edge case** | Low | Medium — wrong total shown | Unit tests cover the critical paths. `validate_conformance.py` checks DB integrity. The guard never commits over-cap by design. |
| 5 | **Multilingual content not ready in time** | Medium | Low — required but scoped | Minimum viable: key UI strings (labels, headings, button text) in Hindi + Tamil + English. Content from DB is already multilingual (BCP-47 tagged). |

---

## 12. MULTILINGUAL APPROACH

### Languages Supported
| Language | BCP-47 | Script | Where It Appears |
|----------|--------|--------|-----------------|
| English | `en-IN` | Latn | Default UI, all content |
| Hindi | `hi` | Deva | UI strings, package names/descriptions, guide bios |
| Tamil | `ta` | Taml | UI strings, guide matching, package filtering |

### How We Handle It
1. **Data layer**: The `languages` table has 26 BCP-47 entries with `script`, `rtl` flag, `tts_supported`. All package data references languages via BCP-47 tags.
2. **Package filtering**: `tour_packages.languages_offered` is a comma-separated BCP-47 list. Filtering is a SQL `LIKE '%hi%'` (shown working in starter query 6).
3. **Guide matching**: `tour_guides.languages` is comma-separated BCP-47. `user_preferences.guide_language` stores the traveler's preferred guide language.
4. **UI strings**: A simple JSON translation file with `{en: {...}, hi: {...}, ta: {...}}` for key interface text. Language selector in the header.
5. **RTL support**: The `languages.rtl` field flags right-to-left languages (Arabic, Urdu in the dataset). CSS `dir="rtl"` applied conditionally.

### What the judges care about
> "Multilingual support matters. At least one Indian language, wherever it is natural to your statement." — Hackathon README

We demonstrate: Hindi package filtering, Tamil guide matching, language-preference-driven recommendations, and a language toggle in the UI. The data already supports 26 languages — we make 3 visible.

---

## 13. CODEBASE DEEP DIVE

### 13.1 Repository Structure

```
travel-concierge-agent/
├── PROJECT.md                  ← Architecture, thesis, feature inventory
├── SETUP.md                    ← How to run (2 commands)
├── .env.example                ← Every API key with where to get it
├── PackagePro/                 ← Hackathon data package
│   ├── 01_YOUR_DATA_MODEL.md   ← 21 tables, every field documented
│   ├── 02_DATA_MODEL_DIAGRAM.html ← Clickable ER diagram
│   ├── 03_DESIGN_SUBMISSION_GUIDE.md ← This submission's requirements
│   ├── 04_HACKATHON_DAY_PROCESS.md   ← Sprint process
│   ├── data/
│   │   ├── PS-04.db            ← SQLite: 28,103 rows, indexed
│   │   ├── csv/                ← Same data as CSV (numbered load order)
│   │   ├── queries/starter_queries.sql ← 6 ready-to-run queries
│   │   ├── schema.sql          ← Postgres DDL
│   │   ├── schema.sqlite.sql   ← SQLite DDL
│   │   ├── enums.json          ← Legal enum values
│   │   └── WORKING_WITH_THE_DATA.md  ← Money/ID/language conventions
│   └── tools/
│       └── validate_conformance.py   ← Data integrity checker
│
├── backend/
│   ├── requirements.txt        ← 11 dependencies
│   ├── tests/
│   │   └── test_budget_guard.py ← 3 unit tests (trust-critical path)
│   └── app/
│       ├── main.py             ← FastAPI entrypoint, CORS, lifespan
│       ├── config.py           ← Pydantic settings, all env vars
│       ├── models.py           ← Request/response Pydantic schemas
│       ├── agent/
│       │   ├── graph.py        ← THE STATE MACHINE — 3 phases, user-driven
│       │   ├── state.py        ← AgentState TypedDict (full shape)
│       │   ├── tools.py        ← 4 tools with mock+real flag pattern
│       │   ├── budget_guard.py ← TRUST CENTERPIECE — hard cap enforcement
│       │   └── llm_client.py   ← NIM/OpenAI/Anthropic router
│       ├── api/
│       │   └── routes_session.py ← 6 HTTP endpoints, phase orchestration
│       └── db/
│           └── database.py     ← SQLAlchemy async, JSON blob per session
│
└── frontend/
    ├── package.json            ← React 18 + Vite 5
    ├── vite.config.js          ← Proxy /api/* → backend:8000
    └── src/
        ├── App.jsx             ← Main app: 4-step wizard with progress bar
        ├── main.jsx            ← React DOM render
        ├── api/client.js       ← 6 API methods (fetch wrapper)
        ├── styles/
        │   └── global.css      ← Design system (navy/amber/green/red)
        └── components/
            ├── IntakeForm.jsx      ← Goal, origin, destination, dates, budget
            ├── FlightPicker.jsx    ← Flight cards with selection
            ├── HotelPicker.jsx     ← Hotel cards with selection
            ├── PlanTimeline.jsx    ← Step-by-step plan visualization
            ├── CostLedger.jsx      ← Live budget meter (running total vs cap)
            ├── AgentTraceFeed.jsx  ← Real-time reasoning/tool-call log
            ├── NegotiationGate.jsx ← 4 trade-off options on over-budget
            ├── CartConfirm.jsx     ← Final cart review + confirm button
            ├── ConfidenceBadge.jsx ← Visual confidence score (0–1)
            └── PlacesGrid.jsx      ← Nearby attractions grid
```

### 13.2 Key Code Patterns

**Mock-first, real-second (tools.py)**:
```python
USE_REAL_FLIGHTS = bool(settings.AMADEUS_CLIENT_ID and settings.AMADEUS_CLIENT_SECRET)

def search_flights(origin, destination, date, travelers=1):
    if USE_REAL_FLIGHTS:
        return _search_flights_amadeus(origin, destination, date, travelers)
    return _mock_flights(origin, destination, date, travelers)
```

**LLM provider swap (llm_client.py)**:
```python
def _client():
    if settings.LLM_PROVIDER == "nvidia_nim":
        return OpenAI(base_url=settings.NVIDIA_BASE_URL, api_key=settings.NVIDIA_API_KEY)
    if settings.LLM_PROVIDER == "openai":
        return OpenAI(api_key=settings.OPENAI_API_KEY)
```

**Session resumability (database.py)**:
```python
async def save_state(session_id, state):
    # JSON blob — entire AgentState serialized and stored
    # Load, resume the graph from any point
```

### 13.3 Design System

| Token | Value | Usage |
|-------|-------|-------|
| `--ink` | `#0E1420` | Background — deep instrument-panel navy |
| `--signal` | `#E8A33D` | Accent — amber, used ONLY for "something is live" |
| `--go` | `#5FBF8F` | Confirmed / allowed / within budget |
| `--stop` | `#E2665C` | Blocked / over-budget / error |
| Font: display | Fraunces | Headers only, used sparingly |
| Font: data | IBM Plex Mono | Ledger, trace feed, numbers — looks like a readout |

**Design rule**: "If you're about to add a second bright color or a second display font, stop — the whole point is restraint so the amber 'something is live' signal stays meaningful."

---

## 14. SUBMISSION CHECKLIST

### Pre-Upload Verification

- [ ] **Cover**: Team name, PS-04 title, every member's name and role
- [ ] **Problem understanding**: Written in our own words, not copied
- [ ] **Scope**: IN list AND OUT list (the OUT list shows judgement)
- [ ] **User journey**: 4 screens described with the exact flow
- [ ] **Architecture diagram**: Legible at 100% zoom, one diagram
- [ ] **Flow diagram**: User flow through the 4-phase agent state machine
- [ ] **Data model usage**: 20 tables listed with how we use each one, plus our extensions
- [ ] **AI features**: 6 features named, each with: what it does, where in the flow, how grounded, how we know it works, measurable target
- [ ] **Business benefits**: Value to traveler AND business, with metrics
- [ ] **Tech stack**: Every technology with one-line rationale
- [ ] **24-hour plan**: Hour-by-hour, names assigned, demo rehearsal time marked
- [ ] **Risks and fallbacks**: 5 risks with concrete fallbacks
- [ ] **Multilingual approach**: 3 languages, where they appear, how handled
- [ ] **XR device declaration**: NOT APPLICABLE (we are not an XR statement)
- [ ] Exported to PDF and reopened to check rendering
- [ ] 10 files or fewer, each under 25 MB
- [ ] Statement on screen is PS-04
- [ ] Someone outside the team has read and understood it

### File Naming Convention
```
TeamName_PS-04_Design_v1.pdf
TeamName_PS-04_Architecture.drawio  (optional editable source)
```

---

## APPENDIX A: SAMPLE DATABASE QUERY RESULTS

### Packages with Hindi support:
- Jaisalmer Food Trail — 5 Days (₹74,537 INR)
- Agra Heritage — 4 Days (₹19,347 INR)
- New Delhi Family — 3 Days (₹19,917 INR)
- Varanasi Heritage — 6 Days (₹28,239 INR)
- Jodhpur Heritage — 3 Days (₹10,922 INR)
- Jaipur Honeymoon — 4 Days (₹15,713 INR)

### Tamil-speaking guides:
- Karthik Tanaka (Pondicherry, photography, 5.0★, 21yr exp, ₹3,200/day)
- Arjun Nair (Thanjavur, heritage, 4.7★, 23yr exp, ₹2,400/day)
- Karthik Patel (Chennai, accessibility, 4.4★, 23yr exp, ₹6,000/day)
- Priya Kulkarni (Ooty, photography, 4.2★, 13yr exp, ₹2,400/day)

### Package component swap example (swap_group: poi_4071):
- "Kandy Bazaar" (₹1,375 LKR delta) — swappable with alternatives in the same group

---

## APPENDIX B: WHAT JUDGES LOOK FOR (FROM THE SUBMISSION GUIDE)

> "The two things that most often let a design down:
> 1. Scope that does not fit 24 hours
> 2. An AI feature described but not designed — 'we will use an LLM to summarise reviews' is not a design (which reviews, retrieved how, prompted how, grounded in what, and how do you know the output is right?)"

**We address both**: Our scope is tight (14 IN, 9 OUT with reasons). Every AI feature specifies: which data, retrieved how, prompted how, grounded in what, and how we verify the output.

> "A working build beats a polished deck."

**We have a working build.** The backend + frontend runs end-to-end with `uvicorn` + `npm run dev`. Unit tests pass. The demo flow works from intake to confirmation.

> "Show the AI feature actually working — live, on real data, not a screenshot."

**The budget guard is the showstopper**: it's code, not a prompt. We can show the unit test, the live negotiation gate, and the audit trail in real-time.

---

*END OF ANALYSIS — This document contains everything needed to generate a winning design submission PPT for the KogniVera Hackathon 2026 PS-04 PackagePro problem statement.*
