# Architecture — Waypoint

## System diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React + Vite)                    │
│  Port 5173 ─ Vite dev proxy ──→ /api/* ──→ backend:8000            │
│                                                                     │
│  App.jsx (flow orchestrator)                                        │
│   ├─ PreferencesPanel ─ city, dates, travellers, budget, language   │
│   ├─ PlanExplainer ─ shows agent's 5-step plan before acting       │
│   ├─ PackageCard[] ─ deterministic-scored recommendations          │
│   ├─ ItineraryTimeline ─ day-by-day components, swap buttons       │
│   ├─ GuideCard[] ─ language-matched, availability-checked guides   │
│   ├─ TrustReceipt ─ full audit trail of every decision             │
│   └─ TraceTimeline ─ real-time transparency events                 │
│                                                                     │
│  money.js ─ decimal.js wrapper, never parseFloat                   │
│  api.js ─ fetch wrapper, money as strings on the wire              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ JSON / REST
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + Python)                      │
│  Port 8000 ─ CORS enabled for frontend                             │
│                                                                     │
│  api/routes.py ──→ all REST endpoints                              │
│  agent/solver.py ──→ the transparent planner (state machine)       │
│                                                                     │
│  ┌─────────── SERVICES ───────────┐    ┌──── DB LAYER ────────┐    │
│  │ recommender.py  eligibility +  │    │ packagepro.py         │    │
│  │                 scoring        │    │  → PS-04.db (read-    │    │
│  │ itinerary.py    components,    │    │    only, mode=ro)     │    │
│  │                 swaps, ledger  │    │                       │    │
│  │ guides.py       matching +     │    │ session.py            │    │
│  │                 availability   │    │  → waypoint_sessions  │    │
│  │ budget.py       BudgetGuard    │    │    .db (Waypoint's    │    │
│  │                 (hard cap)     │    │    own state)         │    │
│  │ pricing.py      Decimal conv.  │    └───────────────────────┘    │
│  │ trace.py        transparency   │                                 │
│  │ llm.py          NVIDIA NIM +   │                                 │
│  │                 fallback       │                                 │
│  └────────────────────────────────┘                                 │
│                                                                     │
│  services/external/ ─ API adapters (mock-first, swap-ready)        │
│   ├─ amadeus.py ─ flight search                                    │
│   ├─ hotelbeds.py ─ hotel search                                   │
│   └─ places.py ─ Google Places enrichment                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ sqlite3 (read-only)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                       │
│                                                                     │
│  PackagePro/data/PS-04.db ─ canonical 21-table, 28K-row dataset    │
│   └─ cities, tour_packages, package_components, tour_guides,       │
│      guide_availability, languages, price_history, currencies, …   │
│                                                                     │
│  backend/data/waypoint_sessions.db ─ session/cart/trace/audit      │
│   └─ Separate write DB. Never modifies PS-04.db.                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Request flow

```
User action ──→ React component ──→ api.js fetch()
                                        │
                                        ▼
                                  FastAPI route
                                        │
                                        ▼
                                  Solver (state machine)
                                   ├─→ Recommender (filter + rank)
                                   ├─→ Itinerary (build + swap)
                                   ├─→ Guides (match + price)
                                   ├─→ BudgetGuard.decide()
                                   │    ├─ approved → proceed
                                   │    └─ blocked → 4 trade-offs
                                   ├─→ Trace (log event)
                                   └─→ LLM (explain, optional)
                                        │
                                        ▼
                                  JSON response ──→ UI update
```

## Key design decisions

1. **Transparency first**: The agent publishes its 5-step plan *before* querying any data. Every backend action emits a structured trace event visible in the UI.

2. **Server-owned budget**: `BudgetGuard` runs server-side. The browser never computes totals. Over-cap changes return 4 structured negotiation options (raise cap / approve overage / drop optional / pick cheaper alternative) — never a flat refusal.

3. **Decimal everywhere**: Money is `Decimal` in Python and `decimal.js` in the browser. The `dec()` function actively rejects `float` inputs. Wire format is strings.

4. **Read-only canonical data**: `PS-04.db` is opened with SQLite's `mode=ro` flag. All Waypoint state goes to a separate file.

5. **Deterministic ranking**: No LLM needed for package scoring. Published formula: language match (+40), duration fit (+25), theme match (+20), within budget (+15). LLM is optional for natural-language explanations only.

6. **Resumable sessions**: Session ID persists to `localStorage` + URL params. Page refresh restores state from the server without re-entering preferences.

## Technology stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + Vite | React 18, Vite 6 |
| Backend | FastAPI + Uvicorn | Python 3.11+ |
| Database | SQLite | (read-only canonical + separate session store) |
| AI/LLM | NVIDIA NIM (Llama 3.1 70B) | Optional, with deterministic fallback |
| External APIs | Amadeus, Hotelbeds, Google Places | Mock-first adapters |
| Testing | pytest | 100 tests |
