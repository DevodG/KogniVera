"""Shared pytest fixtures.

Each test module gets an isolated session database (a temp file) and a
read-only PackagePro handle pointing at the supplied PS-04.db.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("WAYPOINT_CURRENCY", "INR")

from app import config  # noqa: E402
from app.agent.solver import Solver  # noqa: E402
from app.api.routes import router  # noqa: E402
from app.db.packagepro import PackageProDB  # noqa: E402
from app.db.session import SessionDB  # noqa: E402
from app.main import create_app, reset_stores_for_tests  # noqa: E402

PACKAGEPRO_PATH = None
for _depth in (2, 3, 4):
    _candidate = Path(__file__).resolve().parents[_depth] / "PackagePro" / "data" / "PS-04.db"
    if _candidate.exists():
        PACKAGEPRO_PATH = _candidate
        break
if PACKAGEPRO_PATH is None:
    PACKAGEPRO_PATH = Path(__file__).resolve().parents[2] / "PackagePro" / "data" / "PS-04.db"


@pytest.fixture(scope="session")
def pro() -> PackageProDB:
    return PackageProDB(str(PACKAGEPRO_PATH))


@pytest.fixture
def sessions(tmp_path) -> SessionDB:
    db = SessionDB(str(tmp_path / "waypoint-test.db"))
    yield db


@pytest.fixture
def solver(pro, sessions, monkeypatch) -> Solver:
    # Point the app-level singletons at the isolated test stores.
    monkeypatch.setattr(config, "PACKAGEPRO_DB_PATH", Path(pro.path))
    monkeypatch.setattr(config, "SESSION_DB_PATH", Path(sessions.path))
    reset_stores_for_tests()
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "_PRO", pro, raising=False)
    monkeypatch.setattr(main_mod, "_SESSIONS", sessions, raising=False)
    return Solver(pro, sessions)


@pytest.fixture
def client(pro, sessions, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(config, "PACKAGEPRO_DB_PATH", Path(pro.path))
    monkeypatch.setattr(config, "SESSION_DB_PATH", Path(sessions.path))
    reset_stores_for_tests()
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "_PRO", pro, raising=False)
    monkeypatch.setattr(main_mod, "_SESSIONS", sessions, raising=False)
    app = create_app()
    app.include_router(router)
    with TestClient(app) as c:
        c._sessions = sessions
        c._pro = pro
        yield c


#: Jodhpur Heritage — 3 Days, heritage, INR, hi/en-IN, 1-6 pax.
JODHPUR = {
    "city_id": "cty_076e8e86",
    "start_date": "2026-09-05",
    "end_date": "2026-09-07",
    "travelers": 2,
    "budget": {"amount": "20000.00", "currency": "INR"},
    "preferred_languages": ["hi", "en-IN"],
    "theme": "heritage",
    "goal": "A short heritage break",
}
JODHPUR_PACKAGE = "pkg_55c9e36a"
#: Pondicherry Heritage — 6 Days, heritage, INR, ta/en-IN, 2-4 pax.
PONDICHERRY = {
    "city_id": "cty_f288c6a0",
    "start_date": "2026-09-05",
    "end_date": "2026-09-10",
    "travelers": 2,
    "budget": {"amount": "30000.00", "currency": "INR"},
    "preferred_languages": ["ta", "en-IN"],
    "theme": "heritage",
    "goal": "Relaxed Tamil heritage trip with local food",
}
PONDICHERRY_PACKAGE = "pkg_e2cdfb87"
