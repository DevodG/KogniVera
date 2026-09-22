# Waypoint — transparent AI-assisted travel package customizer

Kognivera Hackathon **PS-04 · PackagePro — Dynamic Tour Packages**.

> The user never has to trust the AI blindly: Waypoint shows what it is doing,
> which data it used, why it recommends something, what a change costs, and it
> cannot spend beyond the user's cap without consent.

Everything is built on the supplied `PackagePro/data/PS-04.db`, which is treated
as **read-only**. Waypoint keeps its own session, cart, trace and audit state in
a **separate** SQLite database. No API key is required — the product is fully
functional without one.

## Run it

```bash
# Backend (FastAPI, port 8000)
cd backend
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000

# Frontend (Vite + React, port 5173)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to the backend.

Verification commands:

```bash
cd backend && python3 -m pytest -q
cd frontend && npm run build
```

## The flow

```
Preferences → transparent agent plan → real package recommendations
→ package selected → itinerary customization → available guide selected
→ server-side budget validation → Trust Receipt → explicit mocked confirmation
```

1. **Preferences.** Destination from real `cities` rows, dates, travellers, INR
   cap, BCP-47 languages, theme, free-text goal. The plan is shown *before* any
   query runs.
2. **Recommendations.** Hard eligibility filters (city, language in
   `languages_offered`, duration vs date range, group size, INR only) then a
   published, deterministic score: language +40, duration +25, theme +20, within
   budget +15. No LLM is needed for ranking.
3. **Itinerary.** `package_components` grouped by day and slot, labelled
   included / optional / swappable, each with source and price delta.
4. **Swaps.** Only alternatives from the same package and `swap_group`. Every
   swap returns refreshed itinerary, running total, remaining budget, budget
   decision and a user-safe trace event.
5. **Guides.** `tour_guides` + `guide_availability` filtered by language,
   speciality and real date availability. The date multiplier is applied with
   `Decimal` server-side.
6. **Budget Guard.** Server-owned. Over-cap changes are refused with the four
   trade-offs (cheaper alternative / remove optional / raise cap / approve exact
   overage). Every decision lands in the audit log.
7. **Trust Receipt.** One row per decision: decision, source table, why
   selected, exact price effect.
8. **Confirmation.** A mocked state change only. No payment, no real booking.

## API

| Method | Path |
|---|---|
| `GET` | `/health` |
| `GET` | `/cities` |
| `GET` | `/languages` |
| `POST` | `/planner/recommend` |
| `POST` | `/sessions/{id}/select-package` |
| `GET` | `/sessions/{id}` |
| `GET` | `/sessions/{id}/itinerary` |
| `POST` | `/sessions/{id}/swap-component` |
| `POST` | `/sessions/{id}/select-guide` |
| `POST` | `/sessions/{id}/negotiate` |
| `GET` | `/sessions/{id}/trust-receipt` |
| `POST` | `/sessions/{id}/confirm` |

Plus `GET /sessions/{id}/guides`, used by the guide-matching step.

Example request:

```json
{
  "city_id": "cty_f288c6a0",
  "start_date": "2026-09-05",
  "end_date": "2026-09-10",
  "travelers": 2,
  "budget": { "amount": "34000.00", "currency": "INR" },
  "preferred_languages": ["ta", "en-IN"],
  "theme": "heritage",
  "goal": "A relaxed Tamil heritage trip with local food"
}
```

## Structure

```
waypoint/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app, store singletons
│   │   ├── config.py          env-driven config, no key required
│   │   ├── models.py          Pydantic models + money helpers
│   │   ├── api/routes.py      all endpoints
│   │   ├── agent/solver.py    the transparent planner
│   │   ├── db/
│   │   │   ├── packagepro.py  read-only PS-04.db access + Decimal casting
│   │   │   └── session.py     Waypoint session/trace/audit/cart store
│   │   └── services/
│   │       ├── pricing.py     Decimal pricing conventions
│   │       ├── recommender.py eligibility + deterministic ranking
│   │       ├── guides.py      guide matching + availability
│   │       ├── itinerary.py   components, swaps, ledger
│   │       ├── budget.py      the Budget Guard
│   │       └── trace.py       user-safe structured events
│   ├── tests/                 100 tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx            flow orchestration
│   │   ├── api.js             client (money is strings on the wire)
│   │   ├── money.js           decimal.js wrapper; never parseFloat
│   │   └── components/        Preferences, PackageCard, Itinerary,
│   │                          GuideCard, TrustReceipt, TraceTimeline, …
│   └── package.json
├── PackagePro/                supplied, read-only
├── README.md
└── .env.example
```

## How the PackagePro rules are honoured

- **PS-04.db is read-only.** It is opened with `mode=ro`; Waypoint's state lives
  in `backend/data/waypoint_sessions.db`.
- **Money is `Decimal`.** `dec()` casts stored money strings and actively
  rejects any Python `float`. All totals, deltas, budget comparisons and
  displayed amounts use `Decimal`; the frontend uses `decimal.js` and never
  `parseFloat`.
- **IDs are opaque.** Nothing is parsed for meaning; package membership is
  resolved by lookup.
- **BCP-47 everywhere.** Language filtering uses `languages.bcp47` tags such as
  `ta`, `hi`, `en-IN`.
- **No hidden chain-of-thought.** Transparency is the structured event set in
  `trace.py`: step, action, status, named source, input summary, result
  summary, user-safe reason.
- **No payment, no real booking.** `POST /confirm` writes a mock status only.
- **INR only.** Non-INR packages are filtered out; currency conversion is out
  of MVP scope.
- **Every data source is visible.** Cards, the ledger and the receipt all name
  the source table.

## Pricing conventions (exactly as supplied)

```
included_total = package.base_price
               + sum(price_delta for included, non-optional components)

new_total      = current_total - old_component.price_delta
               + replacement_component.price_delta
```

Guide cost is `day_rate` (or `half_day_rate`) × the `price_multiplier` of the
first available trip day, all in `Decimal`.

## Try the demo scenario

Tamil-friendly heritage trip under a cap:

- City: **Pondicherry** (`cty_f288c6a0`)
- Dates: 2026-09-05 → 2026-09-10 (6 days)
- Travellers: 2, cap ₹34,000, languages `ta` + `en-IN`, theme `heritage`
- Package: *Pondicherry Heritage — 6 Days* (`pkg_e2cdfb87`), included total
  ₹28,865.17
- Swap: *Tea Estate Trail* → *Night Food Bazaar* (same `swap_group`), +₹358.85
  → ₹29,224.02
- Guide: **Arjun Patel** (`gid_3561d64b`), Tamil + English, free on the trip
  dates, ₹2,400 × 1.25 = ₹3,000 → total ₹32,224.02
- Receipt: Budget Guard **Passed**, ₹1,775.98 remaining
- Confirm: `WP-MOCK-…`, mock only

For the blocked path, use a ₹20,000 cap and add guide `gid_460ad60c`: the guard
refuses the change and offers the four trade-offs.

## Known limitations (non-blocking)

- INR packages only; no currency conversion.
- `price_history` covers room types and fares, not packages, so price
  explanations are not wired into package cards.
- Guide availability exists for September 2026 only; dates outside that window
  have no availability rows and every guide is reported unavailable.
- Swaps are constrained to the supplied `swap_group` pairs (each group has
  exactly two rows in the data, one per itinerary day). The two rows are the
  curated alternatives for each other; the itinerary day and slot of the chosen
  activity stay fixed.
- The optional AI key is read from the environment but is never required. With
  no key, all reasoning is the deterministic, grounded planner described above.
