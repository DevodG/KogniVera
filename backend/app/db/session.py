"""Waypoint's own session store.

This is a *separate* SQLite database from ``PackagePro/data/PS-04.db``.
PS-04.db is read-only supply/catalogue data; everything Waypoint creates,
mutates or audits lives here.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from .. import config

_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id            TEXT PRIMARY KEY,
    status                TEXT NOT NULL,
    request_json          TEXT NOT NULL,
    plan_steps_json       TEXT NOT NULL,
    city_id               TEXT,
    city_name             TEXT,
    start_date            TEXT,
    end_date              TEXT,
    travelers             INTEGER,
    budget_amount         TEXT NOT NULL,
    budget_currency       TEXT NOT NULL,
    preferred_languages   TEXT NOT NULL,
    theme                 TEXT,
    goal                  TEXT,
    selected_package_id   TEXT,
    component_overrides   TEXT NOT NULL DEFAULT '{}',
    removed_optional      TEXT NOT NULL DEFAULT '[]',
    selected_guide_id     TEXT,
    guide_service         TEXT,
    guide_cost            TEXT,
    guide_multiplier      TEXT,
    total_amount          TEXT,
    currency              TEXT,
    confirmed             INTEGER NOT NULL DEFAULT 0,
    confirmation_json     TEXT,
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trace_events (
    event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    step         INTEGER NOT NULL,
    action       TEXT NOT NULL,
    status       TEXT NOT NULL,
    source       TEXT NOT NULL,
    input_summary  TEXT NOT NULL,
    result_summary TEXT NOT NULL,
    user_safe_reason TEXT NOT NULL,
    occurred_at  TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    action       TEXT NOT NULL,
    actor        TEXT NOT NULL,
    detail_json  TEXT NOT NULL,
    decision     TEXT,
    amount       TEXT,
    currency     TEXT,
    occurred_at  TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cart_lines (
    line_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    line_type    TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_id    TEXT,
    title        TEXT NOT NULL,
    amount       TEXT NOT NULL,
    currency     TEXT NOT NULL,
    signed_delta TEXT,
    meta_json    TEXT NOT NULL DEFAULT '{}',
    sort_order   INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_trace_session ON trace_events(session_id, event_id);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id, audit_id);
CREATE INDEX IF NOT EXISTS idx_cart_session ON cart_lines(session_id, sort_order);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionDB:
    """SQLite-backed session, cart, trace and audit store."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = str(path or config.SESSION_DB_PATH)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterable[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as conn, _LOCK:
            conn.executescript(_SCHEMA)
            for col in ("selected_flight_json", "selected_hotel_json"):
                try:
                    conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} TEXT")
                except sqlite3.OperationalError:
                    pass
            conn.commit()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, session_id: str, request: dict[str, Any],
                       plan_steps: list[str]) -> None:
        budget = request["budget"]
        with self.connect() as conn, _LOCK:
            conn.execute(
                """INSERT INTO sessions
                   (session_id, status, request_json, plan_steps_json, city_id,
                    city_name, start_date, end_date, travelers, budget_amount,
                    budget_currency, preferred_languages, theme, goal,
                    selected_package_id, component_overrides, removed_optional,
                    selected_guide_id, guide_service, guide_cost, guide_multiplier,
                    total_amount, currency, confirmed, confirmation_json,
                    created_at, updated_at)
                   VALUES (?, 'planning', ?, ?, ?, NULL, ?, ?, ?, ?, ?,
                           ?, ?, ?, NULL, '{}', '[]', NULL, NULL, NULL, NULL,
                           NULL, NULL, 0, NULL, ?, ?)""",
                (
                    session_id,
                    json.dumps(request, ensure_ascii=False),
                    json.dumps(plan_steps, ensure_ascii=False),
                    request["city_id"],
                    request["start_date"],
                    request["end_date"],
                    int(request["travelers"]),
                    str(budget["amount"]),
                    str(budget["currency"]),
                    json.dumps(request["preferred_languages"], ensure_ascii=False),
                    request.get("theme"),
                    request.get("goal"),
                    _now(),
                    _now(),
                ),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn, _LOCK:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["request"] = json.loads(d.pop("request_json"))
        d["plan_steps"] = json.loads(d.pop("plan_steps_json"))
        d["component_overrides_map"] = json.loads(d.pop("component_overrides") or "{}")
        d["removed_optional_list"] = json.loads(d.pop("removed_optional") or "[]")
        d["confirmation"] = json.loads(d["confirmation_json"]) if d.get("confirmation_json") else None
        d.pop("confirmation_json", None)
        d["selected_flight"] = json.loads(d["selected_flight_json"]) if d.get("selected_flight_json") else None
        d.pop("selected_flight_json", None)
        d["selected_hotel"] = json.loads(d["selected_hotel_json"]) if d.get("selected_hotel_json") else None
        d.pop("selected_hotel_json", None)
        d["confirmed"] = bool(d["confirmed"])
        return d

    def update_session(self, session_id: str, **fields: Any) -> None:
        if not fields:
            return
        if "component_overrides_map" in fields:
            fields["component_overrides"] = json.dumps(
                fields.pop("component_overrides_map"), ensure_ascii=False
            )
        if "removed_optional_list" in fields:
            fields["removed_optional"] = json.dumps(
                fields.pop("removed_optional_list"), ensure_ascii=False
            )
        if "confirmation" in fields:
            fields["confirmation_json"] = json.dumps(
                fields.pop("confirmation"), ensure_ascii=False
            )
        if "selected_flight" in fields:
            val = fields.pop("selected_flight")
            fields["selected_flight_json"] = json.dumps(val, ensure_ascii=False) if val else None
        if "selected_hotel" in fields:
            val = fields.pop("selected_hotel")
            fields["selected_hotel_json"] = json.dumps(val, ensure_ascii=False) if val else None
        fields["updated_at"] = _now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        params = list(fields.values()) + [session_id]
        with self.connect() as conn, _LOCK:
            conn.execute(f"UPDATE sessions SET {cols} WHERE session_id = ?", params)
            conn.commit()

    # ------------------------------------------------------------------
    # Trace events (structured, user-safe — never chain-of-thought)
    # ------------------------------------------------------------------

    def add_trace(self, session_id: str, event: dict[str, Any]) -> None:
        with self.connect() as conn, _LOCK:
            conn.execute(
                """INSERT INTO trace_events
                   (session_id, step, action, status, source, input_summary,
                    result_summary, user_safe_reason, occurred_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    int(event["step"]),
                    event["action"],
                    event["status"],
                    event["source"],
                    event["input_summary"],
                    event["result_summary"],
                    event["user_safe_reason"],
                    event.get("occurred_at", _now()),
                ),
            )
            conn.commit()

    def trace(self, session_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn, _LOCK:
            rows = conn.execute(
                """SELECT step, action, status, source, input_summary,
                          result_summary, user_safe_reason, occurred_at
                   FROM trace_events
                   WHERE session_id = ? ORDER BY event_id""",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Audit log — every budget decision is recorded
    # ------------------------------------------------------------------

    def add_audit(self, session_id: str, action: str, actor: str,
                  detail: dict[str, Any], decision: Optional[str] = None,
                  amount: Optional[str] = None, currency: Optional[str] = None) -> None:
        with self.connect() as conn, _LOCK:
            conn.execute(
                """INSERT INTO audit_log
                   (session_id, action, actor, detail_json, decision, amount,
                    currency, occurred_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id, action, actor,
                    json.dumps(detail, ensure_ascii=False),
                    decision, amount, currency, _now(),
                ),
            )
            conn.commit()

    def audit(self, session_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn, _LOCK:
            rows = conn.execute(
                """SELECT audit_id, action, actor, detail_json, decision, amount,
                          currency, occurred_at
                   FROM audit_log
                   WHERE session_id = ? ORDER BY audit_id""",
                (session_id,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["detail"] = json.loads(d.pop("detail_json"))
            out.append(d)
        return out

    # ------------------------------------------------------------------
    # Cart lines (ledger)
    # ------------------------------------------------------------------

    def replace_cart(self, session_id: str, lines: list[dict[str, Any]]) -> None:
        with self.connect() as conn, _LOCK:
            conn.execute("DELETE FROM cart_lines WHERE session_id = ?", (session_id,))
            for i, ln in enumerate(lines):
                conn.execute(
                    """INSERT INTO cart_lines
                       (session_id, line_type, source_table, source_id, title,
                        amount, currency, signed_delta, meta_json, sort_order)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        session_id,
                        ln["line_type"],
                        ln["source_table"],
                        ln.get("source_id"),
                        ln["title"],
                        str(ln["amount"]),
                        ln["currency"],
                        str(ln["signed_delta"]) if ln.get("signed_delta") is not None else None,
                        json.dumps(ln.get("meta", {}), ensure_ascii=False),
                        i,
                    ),
                )
            conn.commit()

    def cart(self, session_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn, _LOCK:
            rows = conn.execute(
                """SELECT line_type, source_table, source_id, title, amount,
                          currency, signed_delta, meta_json
                   FROM cart_lines
                   WHERE session_id = ? ORDER BY sort_order""",
                (session_id,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["meta"] = json.loads(d.pop("meta_json"))
            out.append(d)
        return out
