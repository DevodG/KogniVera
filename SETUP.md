# Setup — PackagePro (PS-04: Dynamic Tour Packages)

Two services: a **FastAPI backend** (deterministic scoring engine + budget guard)
and a **Vite/React frontend** (liquid itinerary UI). Runs with **zero API keys** —
all intelligence is scoring over the real `PackagePro/data/PS-04.db` rows.

## 0. Prerequisites

- Python 3.11+ (tested on 3.14)
- Node 18+

No external accounts, no LLM keys, no travel-API registrations.

## 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# run tests (should pass with zero config)
PYTHONPATH=. pytest tests/ -v

# start the API on http://127.0.0.1:8100
uvicorn app.main:app --reload --port 8100
```

Check it's alive: open http://127.0.0.1:8100/health — should report
`db_present: true`. Interactive docs: http://127.0.0.1:8100/docs.

The dataset is bundled at `PackagePro/data/PS-04.db` and found automatically.
Override with `PACKAGEPRO_DB_PATH` only if you relocate it (see `.env.example`).

## 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5174. The Vite dev server proxies `/api/*` to the backend
on port 8100 (see `frontend/vite.config.js`) — no CORS setup needed in dev.

Production build: `npm run build` (output in `frontend/dist/`).

## 3. Try the demo flow

1. Fill the intake form (defaults are pre-filled; the budget cap is the vessel).
2. Watch the **ranked package gallery** — each card shows its score and the
   per-signal reasons it ranked there (language, budget, theme, pace, party).
3. Pick a package → **customize**. Click any swappable component to open the
   swap drawer of ranked alternatives; the total reprices in exact decimal.
4. Open the **agent trace** to see every tool call and guard decision.
5. Match a **guide** — filtered by BCP-47 language and real availability.
6. Set a budget cap below a package's cost to watch the **budget guard refuse**:
   nothing is charged, the overage is reported, and the audit trail records it.

## 4. The budget guard (the trust thesis)

Every cost-adding path (package, swap, optional add-on, guide) goes through
`BudgetGuard.add_cost()` in `backend/app/core/budget_guard.py`. Money is a
`Decimal` value object (`core/money.py`) end to end — it is never a float, and
crosses the wire as `{amount: string, currency: string}`. An over-cap cost is
never committed; the audit trail is the evidence.

## 5. Common issues

| Symptom | Fix |
|---|---|
| `PackagePro DB not found at ...` | Run backend commands from `backend/`, or set `PACKAGEPRO_DB_PATH` to the absolute path of `PS-04.db` |
| `ModuleNotFoundError: app` | Run from inside `backend/` with `PYTHONPATH=.` set, or use `uvicorn app.main:app` from that directory |
| Frontend shows blank page | Confirm the backend is running on port 8100 — check the browser Network tab for failed `/api/*` calls |
| Swaps return no alternatives | The component has no same-`swap_group` siblings; `GET /session/{id}/swap-advice/{component_id}` explains why |
