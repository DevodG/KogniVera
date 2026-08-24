# Setup — Waypoint (Agentic Travel Concierge)

Two services: a **FastAPI backend** (the agent) and a **Vite/React frontend**
(the UI). Runs fully with mock data and zero API keys — layer in real keys
as you get them.

## 0. Prerequisites

- Python 3.11+
- Node 18+
- (Optional) a free NVIDIA NIM API key — see below, takes ~2 minutes

## 1. Get your NVIDIA NIM key (recommended, 2 min)

1. Go to https://build.nvidia.com and sign in with any email — no card needed.
2. Click your profile → **API Keys** → **Generate API Key**.
3. Copy the key (starts with `nvapi-`).

Without this key the agent still runs end-to-end — it just falls back to
picking the cheapest option deterministically instead of reasoning about
fit/preferences. You'll see this clearly in the trace feed
(`LLM call failed... falling back to cheapest option`), which is itself a
good thing to point out to judges: **the system degrades safely, it doesn't crash.**

## 2. Configure environment

```bash
cp .env.example .env
# open .env and paste your NVIDIA_API_KEY (and anything else you have)
```

See `.env.example` for where to get every other key (flights, hotels,
places, notifications) — all optional, all mock-backed until you add them.

## 3. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# run tests (should pass with zero keys set)
PYTHONPATH=. pytest tests/ -v

# start the API
uvicorn app.main:app --reload --port 8000
```

Check it's alive: open http://localhost:8000/health — should return
`{"status": "ok", "llm_provider": "nvidia_nim", "model": "..."}`.

Interactive API docs: http://localhost:8000/docs

## 4. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to the
backend on port 8000 (see `frontend/vite.config.js`) — no CORS setup needed
in dev.

## 5. Try the demo flow

1. Fill in the intake form (defaults are pre-filled — a tight budget on
   purpose, to demo the negotiation gate).
2. Watch the **plan** render before anything executes.
3. Watch the **agent trace** stream tool calls and reasoning in real time.
4. If the hotel pushes the trip over budget, you'll see the **negotiation
   gate** — pick a trade-off instead of the agent silently overspending.
5. Confirm the final cart — booking is intentionally mocked; wire a real
   payment provider only behind `POST /session/{id}/confirm` in
   `backend/app/api/routes_session.py`.

## 6. Common issues

| Symptom | Fix |
|---|---|
| `Host not in allowlist` / connection errors calling NVIDIA | Your network/sandbox blocks outbound calls to `integrate.api.nvidia.com` — check firewall/proxy settings, or run with a provider that is allowlisted. The agent will fall back to deterministic picks either way. |
| `sqlite3.OperationalError` on startup | Delete `backend/concierge.db` and restart — schema is auto-created on boot. |
| Frontend shows blank page | Confirm the backend is running on port 8000 first — check the Network tab for failed `/api/session` calls. |
| `ModuleNotFoundError: app` | Always run backend commands from inside `backend/` with `PYTHONPATH=.` set, or use `uvicorn app.main:app` from that directory. |

## 7. Swapping in real data (any time during the month)

Every external integration lives in `backend/app/agent/tools.py` behind a
`USE_REAL_*` flag that auto-flips on when the matching `.env` key is set.
No other file needs to change — the LangGraph nodes call the same function
signatures whether they're hitting mock data or a real API.

## 8. Production database

Swap `DATABASE_URL` in `.env` from SQLite to Postgres (e.g. a free instance
on [neon.tech](https://neon.tech) or [supabase.com](https://supabase.com)) —
`backend/app/db/database.py` needs zero code changes, only the URL.
