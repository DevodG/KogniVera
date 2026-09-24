"""Waypoint configuration.

All values resolve from environment variables with safe defaults so the MVP
runs with no API key and no external service. No real key is ever read,
printed, or committed.
"""
from __future__ import annotations

import os
from pathlib import Path

# Project roots. Walk up from config.py looking for the PackagePro directory.
# Supports both ``waypoint/backend/app/`` (nested) and ``backend/app/`` (flat).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _depth in (2, 3, 4):
    _candidate = Path(__file__).resolve().parents[_depth]
    if (_candidate / "PackagePro").exists():
        PROJECT_ROOT = _candidate
        break

BACKEND_ROOT = Path(__file__).resolve().parents[1]

#: Read-only PackagePro source database. Never opened for writing.
PACKAGEPRO_DB_PATH = Path(
    os.getenv("WAYPOINT_PACKAGEPRO_DB", str(PROJECT_ROOT / "PackagePro" / "data" / "PS-04.db"))
)

#: Waypoint's own session/store database. Completely separate from PS-04.db.
SESSION_DB_PATH = Path(
    os.getenv("WAYPOINT_SESSION_DB", str(BACKEND_ROOT / "data" / "waypoint_sessions.db"))
)

#: MVP supports INR only. Currency conversion is intentionally out of scope.
SUPPORTED_CURRENCY = os.getenv("WAYPOINT_CURRENCY", "INR")

#: Money is always quantised to the ISO-4217 minor unit of the ledger currency.
MONEY_QUANT = "0.01"

#: Optional AI/model key. The product is fully functional when this is unset.
AI_API_KEY: str | None = os.getenv("WAYPOINT_AI_API_KEY") or None
AI_BASE_URL: str | None = os.getenv("WAYPOINT_AI_BASE_URL") or None
AI_MODEL: str | None = os.getenv("WAYPOINT_AI_MODEL") or None

#: CORS origin for the Vite dev server.
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

CITIES_DEFAULT_LIMIT = int(os.getenv("WAYPOINT_CITIES_LIMIT", "200"))


def packagepro_db_exists() -> bool:
    return PACKAGEPRO_DB_PATH.is_file()
