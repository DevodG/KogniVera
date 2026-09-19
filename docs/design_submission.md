# KogniVera_PS-04_Design_v1

## Cover
- **Team Name**: KogniVera
- **Problem Statement**: PS-04 (PackagePro — Dynamic Tour Packages)
- **Team Members**: Agentic Concierge System

## Problem understanding
The travel market requires personalized package tours that seamlessly blend static itinerary planning with dynamic component swapping. Current solutions are rigid, leaving travelers with pre-defined packages that don't fit their exact needs or budgets. We aim to solve this by providing an AI-driven concierge that allows flexible, budget-aware substitution of activities, hotels, and guides. The concierge must handle multi-lingual interactions, live budget tracking, and real-time package customization.

## Scope
**What we will build in 24 hours (MVP):**
- A conversational web UI that guides users through trip planning.
- Strict budget enforcement (Budget Guard) that triggers negotiation dialogs rather than failing silently.
- Multilingual interface supporting English, Hindi, Tamil, and Telugu based on user preference.
- Live package component swapping, where swapping an activity instantly recalculates total cost and checks against budget.
- Guide matching based on language (BCP-47), specialisation, and daily rate.

**What we are deliberately leaving out:**
- Live booking of flights/hotels (we will stub the external APIs or use read-only mock data).
- Complex multi-city routing within a single trip.
- Full offline sync capability for mobile users.

## User journey
1. **Intake**: Traveler enters their destination, dates, budget, and language preference.
2. **Flight & Hotel Selection**: The system queries mock/stubbed APIs for options. The user picks their preferred options.
3. **Component Swapping**: The user views the pre-built package itinerary and can swap out individual activities (e.g., swapping a generic city tour for a specialized food tour). Prices update dynamically.
4. **Guide Matching**: The user selects a tour guide matching their language and specific interest.
5. **Confirmation**: The user reviews the finalized cart, which shows the cost ledger and remaining budget, and confirms the trip.

## Architecture
```text
[ React Frontend (Vite) ] <---> [ FastAPI Backend ]
       |                                |
       v                                v
[ Local Storage (Auth) ]         [ SQLite DBs ]
                                  - concierge.db (Session/Auth State)
                                  - PS-04.db (PackagePro Read-Only Data)
```
- **Frontend**: React components manage state (LanguageSwitcher, ComponentSwapper, GuideMatcher) and communicate via REST APIs.
- **Backend**: FastAPI orchestrates the LangGraph state machine. It handles budget checking and routing to tools.
- **Data Layer**: Python `sqlite3` driver connects to the read-only PackagePro DB, coercing all money fields to Decimal and enforcing BCP-47 language matching.

## Data model usage
We are leveraging the provided `PS-04.db` tables exclusively for travel data, extending our architecture via a separate state database (`concierge.db`) for tracking user sessions and authentication.
- `tour_guides` & `guide_availability`: Used for finding guides with specific languages/specialisations and active dates.
- `tour_packages` & `package_components`: Used for displaying base packages and enabling swappable alternatives within the same `swap_group`.
- `languages`: Used to power the frontend i18n logic (en-IN, hi, ta, te).
- `cities`: Used for filtering packages and guides.
We enforce all rules (R1-R8), especially treating money as Decimals (R3) and keeping IDs opaque (R2).

## AI approach
The AI acts as an orchestrator behind the scenes using a state-machine (LangGraph) approach. 
- **Grounding**: The LLM doesn't hallucinate packages. It triggers explicit tool calls (`search_packages`, `check_budget`) that query our strict data layer.
- **Decision Engine**: Rather than letting the LLM book things autonomously, it builds the plan and pauses, allowing the *user* to make selections. The AI then validates the selection against constraints (Budget Guard).

## Tech stack
- **Backend**: FastAPI (Python) - Fast, async, built-in Pydantic validation.
- **Database**: SQLite - Zero-setup, perfect for read-only synthetic datasets and simple state tracking.
- **Frontend**: React / Vite - Fast HMR, component-based UI for complex state like component swapping.
- **Styling**: Vanilla CSS - Lightweight, custom design system without Tailwind overhead.

## 24-hour plan
- **Hour 0-4**: Connect to PS-04.db, write read-only data access layer, enforce Decimal money handling.
- **Hour 4-8**: Build FastAPI routes for guide matching and package component swapping.
- **Hour 8-12**: Implement frontend i18n (LanguageSwitcher) and ComponentSwapper UI.
- **Hour 12-16**: Connect external API stubs (Hotelbeds, Google Places) and add JWT auth.
- **Hour 16-20**: End-to-end testing, bug fixing, mobile CSS tweaks.
- **Hour 20-24**: Rehearse demo, record video, prepare final submission package.

## Risks and fallbacks
1. **External APIs Rate Limit / Fail**: We wrap all external API calls (Amadeus, Hotelbeds) in `try/except` blocks. If they fail, they instantly fall back to mock data generators.
2. **OR-Tools Solver Overcomplicates Routing**: If the constraint solver takes too long to execute or fails, we fall back to the existing heuristic-based selection logic.
3. **Frontend State Desync**: If component swapping gets out of sync with the backend budget, the final `/confirm` endpoint does a hard server-side re-validation of the cart total before allowing confirmation.

## Multilingual approach
The frontend uses a custom React context (`LanguageProvider`) supporting BCP-47 tags (en-IN, hi, ta, te). 
- UI strings are translated client-side. 
- When searching for guides or packages, the selected language tag is sent to the backend, which uses SQL `LIKE` logic on comma-separated language fields to filter results.
