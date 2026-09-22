# Waypoint frontend

Vite + React. Talks to the Waypoint FastAPI backend.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # production bundle in dist/
```

The dev server proxies `/api` to `http://127.0.0.1:8000`, so start the backend
first:

```bash
cd ../backend && python3 -m uvicorn app.main:app --reload --port 8000
```

## Rules honoured here

- Money is carried as a **string** everywhere and rendered with
  `decimal.js` (`src/money.js`). `parseFloat` is never used for a total, delta,
  budget decision or displayed amount.
- IDs are opaque strings; nothing is parsed for meaning.
- Languages are BCP-47 tags.
- The server owns every total and every budget decision. The browser only
  displays what the server returned.
