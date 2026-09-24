# Waypoint — Transparent AI Travel Package Customizer

## 1. Team & Problem Statement

| | |
|---|---|
| **Team** | RNG Gods |
| **Problem Statement** | PS-04 — PackagePro: Dynamic Tour Packages |
| **College** | BMS College of Engineering |
| **Hackathon** | KogniVera 2026 |

---

## 2. What we built

Waypoint is an agentic travel concierge that **shows its reasoning before acting** and enforces budget limits in code, not prompts.

- ✅ **Dynamic package recommendations** — deterministic eligibility filters (city, language, duration, group size, INR only) + published scoring formula (language +40, duration +25, theme +20, budget fit +15). No LLM needed for ranking.
- ✅ **Swappable itinerary components** — per-day/slot breakdown from `package_components` with `swap_group`-constrained alternatives. Signed `price_delta` repriced via `Decimal`.
- ✅ **Tour guide matching** — filtered by language, specialisation, city; priced using `day_rate × price_multiplier` from real `guide_availability` rows.
- ✅ **Hard budget enforcement** — `BudgetGuard` runs server-side. Over-cap changes return 4 structured trade-offs (raise cap / approve overage / drop optional / pick cheaper). Never a flat refusal.
- ✅ **Transparent Trust Receipt** — every decision logged: what changed, source table, reason, exact price effect. Full audit trail before confirmation.
- ✅ **Multilingual AI explanations** — NVIDIA NIM (Llama 3.1 70B) for natural-language reasoning in English, Hindi, Tamil, Telugu. Deterministic fallback when no key is set.

---

## 3. Architecture

```
┌──────────────────────┐         ┌──────────────────────────────┐
│   Frontend (React)   │  JSON   │     Backend (FastAPI)        │
│   Vite · port 5173   │ ──────→ │     Python · port 8000       │
│                      │         │                              │
│  PreferencesPanel    │         │  api/routes.py               │
│  PackageCard[]       │         │  agent/solver.py (planner)   │
│  ItineraryTimeline   │         │  services/                   │
│  GuideCard[]         │         │   ├─ recommender.py          │
│  TrustReceipt       │         │   ├─ itinerary.py            │
│  TraceTimeline       │         │   ├─ guides.py               │
│                      │         │   ├─ budget.py (BudgetGuard) │
│  money.js            │         │   ├─ pricing.py (Decimal)    │
│  (decimal.js, no     │         │   ├─ trace.py                │
│   parseFloat)        │         │   ├─ llm.py (NIM + fallback) │
│                      │         │   └─ external/ (adapters)    │
└──────────────────────┘         │  db/                         │
                                 │   ├─ packagepro.py (ro)      │
                                 │   └─ session.py (rw)         │
                                 └──────────┬───────────────────┘
                                            │
                             ┌──────────────┴──────────────┐
                             │       SQLite Data Layer      │
                             │                              │
                             │  PS-04.db (read-only, 21     │
                             │  tables, 28K rows)           │
                             │                              │
                             │  waypoint_sessions.db        │
                             │  (Waypoint's own state)      │
                             └──────────────────────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full architecture with request flow, design decisions, and tech stack.

---

## 4. Data model

### Canonical tables used (from PS-04.db)

| Table | What Waypoint does with it |
|-------|---------------------------|
| `cities` | Destination selector, geographic anchor for all lookups |
| `tour_packages` | Core catalogue — filtered by city, language, duration, group size, INR |
| `package_components` | Swappable line items with signed `price_delta` |
| `tour_guides` | Guide matching by language, specialisation, city |
| `guide_availability` | Real per-date availability + `price_multiplier` |
| `languages` | BCP-47 tags for all language matching |
| `price_history` | Optional pricing explainability |
| `currencies` | Reference for display formatting |
| `categories` | Theme taxonomy for package matching |

### Additions (Waypoint-owned, separate DB)

| Table | Purpose |
|-------|---------|
| `sessions` | Session state (city, dates, budget cap, selections) |
| `cart_items` | Persisted cart with component swaps |
| `trace_events` | Structured transparency log |
| `audit_log` | Every BudgetGuard decision with trade-offs |

Full details: [`data-model/DATA_MODEL.md`](data-model/DATA_MODEL.md)

---

## 5. AI features

| Capability | Mechanism | Grounding |
|-----------|-----------|-----------|
| **Plan explanation** | NVIDIA NIM (Llama 3.1 70B) via OpenAI-compatible API | Deterministic 5-step plan published *before* data access. LLM explains; code acts. |
| **Recommendation reasoning** | Deterministic scoring formula + optional LLM explanation | Scores computed from DB fields (language, duration, theme, price). LLM narrates the result. |
| **Multilingual output** | Template-based fallback (en-IN, hi, ta, te) + NIM for richer text | Templates reference actual package/guide data. LLM responses grounded by system prompt constraints. |
| **Budget negotiation** | Code-only (`BudgetGuard`) | LLM is never involved in price computation. All `Decimal` arithmetic server-side. |
| **Swap explanation** | LLM narration of code-computed diff | Old/new component names and deltas from DB. LLM explains the human impact. |
| **External API adapters** | Mock-first wrappers for Amadeus, Hotelbeds, Google Places | Adapters return structured data; LLM does not call APIs. |

**Key constraint**: The LLM **never** computes prices, totals, or budget decisions. If no API key is configured, the app is fully functional with deterministic templates.

---

## 6. Run it locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- SQLite 3

### Steps

```bash
# Clone
git clone https://github.com/DevodG/KogniVera.git
cd KogniVera

# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Environment (optional)

```bash
cp .env.example backend/.env
# Edit backend/.env to add API keys (all optional)
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to the backend.

---

## 7. Demo path

> This exact click-path completes the MVP's terminal outcome.

1. **Open** http://localhost:5173
2. **Select destination** — pick **Pondicherry** from the city dropdown
3. **Set preferences** — dates: Sep 5–10 2026, 2 travellers, ₹34,000 budget, Tamil + English, theme: Heritage
4. **View plan** — the agent shows its 5-step intent *before* querying any data
5. **Review recommendations** — packages ranked by deterministic score; pick **Pondicherry Heritage — 6 Days** (₹28,865.17)
6. **Explore itinerary** — day-by-day timeline with included/optional/swappable components
7. **Swap a component** — click swap on *Tea Estate Trail* → *Night Food Bazaar* (+₹358.85 → ₹29,224.02)
8. **Select a guide** — pick **Arjun Patel** (Tamil + English, ₹3,000 with multiplier → total ₹32,224.02)
9. **Review Trust Receipt** — every decision with source table, reason, and price effect. Budget Guard: **Passed**, ₹1,775.98 remaining
10. **Confirm** — mock confirmation (`WP-MOCK-…`), no real payment

**Blocked path**: Use a ₹20,000 cap → BudgetGuard blocks and offers 4 trade-offs (raise cap / approve overage / drop optional / cheaper alternative).

---

## 8. Tests / proof

### Run the test suite

```bash
cd backend
source .venv/bin/activate
python3 -m pytest -q
```

**100 tests** covering:

| Test file | What it proves |
|-----------|---------------|
| `test_budget.py` | BudgetGuard blocks over-cap, offers 4 trade-offs, approves under-cap |
| `test_itinerary.py` | Swap logic respects `swap_group`, recalculates `Decimal` totals correctly |
| `test_recommendation.py` | Eligibility filters (city, language, duration, group size, INR), deterministic scoring |
| `test_guides.py` | Language matching, availability check, `day_rate × price_multiplier` in `Decimal` |
| `test_pricing.py` | `Decimal` enforcement — `float` inputs rejected, money always exact |
| `test_receipt_confirm.py` | Trust Receipt generation, mock confirmation flow |
| `test_reference.py` | PS-04.db read-only enforcement, canonical table existence |
| `test_external_apis.py` | External API adapters (Amadeus, Hotelbeds, Places) mock and real modes |

### Hard-proof test (boundary rules)

```bash
# Specifically test that budget enforcement is structural, not advisory:
python3 -m pytest tests/test_budget.py -v

# Test that float money is rejected at the boundary:
python3 -m pytest tests/test_pricing.py -v

# Test that INR-only filtering works:
python3 -m pytest tests/test_recommendation.py -v
```

### Frontend build verification

```bash
cd frontend
npm run build   # exits 0 = no build errors
```
