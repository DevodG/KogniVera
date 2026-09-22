# PackagePro — Dynamic Tour Packages (KogniVera PS-04)

> An agentic travel concierge for **dynamic** tour packages: a package takes the
> shape of the traveler, and the budget is the vessel.

**Thesis:** most AI travel tools compete on prettier itineraries. This one
competes on **trust** — an agent that scores real data, reprices in exact
decimal, and is *structurally incapable* of spending past the cap you set,
because the guardrail is enforced in code (`budget_guard.py`), not by asking a
model nicely.

## What's built

- **Deterministic scoring engine** over the real `PackagePro/data/PS-04.db` —
  packages and guides ranked per traveler with per-signal reasons (language,
  budget, theme, pace, party), plus honest cold-start labelling.
- **Live component swapping** — the core PS-04 requirement. Swaps reprice in
  `Decimal`, server-side; the client never owns a total.
- **Hard budget cap** — every cost-adding path (package / swap / optional /
  guide) flows through `BudgetGuard`. Over-cap = nothing charged, overage
  reported, decision written to an audit trail.
- **Explainable pricing** — `GET /explain/{entity_id}` decomposes a price into
  its real factors (demand, occupancy, lead time, seasonality, event, competitor).
- **Language-aware guide matching** — BCP-47 filtering against real
  `guide_availability`, with peak day-rate multipliers.
- **Live agent trace** — every tool call, reasoning step and guard decision.
- **64 unit tests** covering money arithmetic, repricing and the budget guard.

## Run it

See **[SETUP.md](SETUP.md)** — zero API keys required:

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && PYTHONPATH=. pytest tests/ -v   # 64 passed
uvicorn app.main:app --port 8100                                    # API

cd frontend && npm install && npm run dev                           # UI :5174
```

## Repo map

```
├── DESIGN.md                 visual system + feature blueprint (the "liquid itinerary")
├── PROJECT.md                architecture, feature status, rules for contributors
├── SETUP.md                  how to run it
├── .env.example              optional overrides (nothing is required)
├── PackagePro/data/PS-04.db  the real dataset — read-only by construction
├── docs/                     hackathon design submission
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    FastAPI entrypoint
│       ├── api/routes.py              all HTTP endpoints
│       ├── core/
│       │   ├── money.py               Money value object (Decimal + ISO-4217)
│       │   ├── reprice.py             the repricer: base + Σ(kept deltas)
│       │   ├── budget_guard.py        the trust-critical hard cap
│       │   └── session.py             server-authoritative session state
│       ├── data/packagepro.py         read-only data layer over PS-04.db
│       └── intel/engine.py            scoring + recommendation reasoning
│   └── tests/                         money / reprice / budget_guard
└── frontend/
    └── src/
        ├── App.jsx                    intake → packages → customize
        ├── api/{client,money}.js      fetch wrapper + client-side Money
        ├── components/                BudgetVessel · ComponentTimeline · TraceFeed
        └── i18n/strings.js            en/hi/ta/te UI strings
```

## The design system

Aesthetic: **liquid**, not a control tower — a dynamic package *flows and
reshapes*, so the UI shows fluidity as the evidence of dynamism. Deep abyss
background with a drifting aurora, glassmorphic panels, spring physics, and a
single iridescent accent reserved for anything "live". Full tokens in
`frontend/src/styles/global.css`; full rationale in **[DESIGN.md](DESIGN.md)**.

## Rules for whoever works on this next

1. **Never bypass `BudgetGuard`.** A new cost-adding step must call
   `guard.add_cost(...)`, never mutate a running total directly. This is the
   entire trust thesis — breaking it breaks the product.
2. **Money is never a float.** Use the `Money` value object server-side and the
   `Money` class in `api/money.js` client-side. Cross the wire as
   `{amount: string, currency: string}`.
3. **The trace is not optional.** Any new operation should append to the session
   trace — if you can't state what it did in one sentence, it's doing too much.
4. **Update the feature table in PROJECT.md** — it is the single source of truth.
