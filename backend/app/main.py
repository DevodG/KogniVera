"""Waypoint backend — FastAPI application.

PS-04.db is opened read-only. Waypoint's own state lives in a separate
SQLite database. No API key is required for the MVP.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .api.routes import router
from .db.packagepro import PackageProDB
from .db.session import SessionDB

_PRO: PackageProDB | None = None
_SESSIONS: SessionDB | None = None


def get_pro() -> PackageProDB:
    global _PRO
    if _PRO is None:
        _PRO = PackageProDB()
    return _PRO


def get_sessions() -> SessionDB:
    global _SESSIONS
    if _SESSIONS is None:
        _SESSIONS = SessionDB()
    return _SESSIONS


def reset_stores_for_tests() -> None:
    """Test hook: drop cached singletons so a fresh DB can be injected."""
    global _PRO, _SESSIONS
    _PRO = None
    _SESSIONS = None


def create_app() -> FastAPI:
    if not config.packagepro_db_exists():
        print(
            f"WARNING: PackagePro DB not found at {config.PACKAGEPRO_DB_PATH}. "
            "The API will return errors until the data is present.",
            file=sys.stderr,
        )
    app = FastAPI(
        title="Waypoint — transparent AI-assisted travel package customizer",
        description=(
            "Kognivera Hackathon PS-04 · PackagePro — Dynamic Tour Packages. "
            "Shows what the agent is doing, which data it used, why it "
            "recommends something, what a change costs, and it cannot spend "
            "beyond your cap without consent."
        ),
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.CORS_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("WAYPOINT_HOST", "127.0.0.1")
    port = int(os.getenv("WAYPOINT_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
