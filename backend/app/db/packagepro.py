"""
PackagePro data-access layer (read-only).

Rules followed (from PackagePro/data/WORKING_WITH_THE_DATA.md):
  R1  Additive only — no rename/drop of provided fields.
  R2  IDs are opaque prefixed strings.
  R3  Money is Decimal + ISO-4217 code.  Never float.
  R4  Timestamps carry UTC offset; calendar dates have no zone.
  R5  Enums are lowercase snake_case.
  R6  Language is a BCP-47 tag.
  R7  Geography is WGS-84 decimal degrees.
  R8  Nothing is hard-deleted; rows carry status + updated_at.

Connection is opened lazily and shared as a module-level singleton.
The connection is always in READ-ONLY mode (uri=True, mode=ro).
"""
from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.config import settings


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    """Return the shared read-only connection, opening it on first call."""
    global _conn
    if _conn is None:
        db_path = Path(settings.PACKAGEPRO_DB_PATH)
        if not db_path.exists():
            raise FileNotFoundError(
                f"PackagePro DB not found at {db_path}. "
                "Run from the repo root or set PACKAGEPRO_DB_PATH in .env."
            )
        uri = f"file:{db_path}?mode=ro"
        _conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute a SELECT and return rows as plain dicts."""
    conn = _get_conn()
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    """Execute a SELECT and return the first row or None."""
    conn = _get_conn()
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Money helpers (R3)
# ---------------------------------------------------------------------------

MONEY_FIELDS = frozenset({
    "day_rate", "half_day_rate", "base_price", "price_delta",
    "base_rate", "max_daily_budget",
})


def _to_decimal(value: str | None) -> Decimal | None:
    """Convert a TEXT money value from the DB to Decimal.  Never float."""
    if value is None:
        return None
    return Decimal(str(value))


def _coerce_money(row: dict[str, Any]) -> dict[str, Any]:
    """Coerce all known money fields in a row dict to Decimal."""
    result = {}
    for k, v in row.items():
        if k in MONEY_FIELDS and v is not None:
            result[k] = _to_decimal(v)
        else:
            result[k] = v
    return result


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    """Convert Decimal values to str so they're JSON-serialisable."""
    return {k: str(v) if isinstance(v, Decimal) else v for k, v in row.items()}


# ---------------------------------------------------------------------------
# Tour Guides (Task B)
# ---------------------------------------------------------------------------

def get_matching_guides(
    *,
    languages: list[str] | None = None,
    specialisation: str | None = None,
    max_day_rate: Decimal | None = None,
    city_id: str | None = None,
    from_date: str | None = None,   # YYYY-MM-DD
    to_date: str | None = None,     # YYYY-MM-DD
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Match tour guides by language, specialisation, day rate, and availability.

    Language matching: a guide is included if *any* of the requested BCP-47
    tags appears in the guide's comma-separated `languages` column.
    """
    filters: list[str] = ["g.status = 'active'"]
    params: list[Any] = []

    if city_id:
        filters.append("g.city_id = ?")
        params.append(city_id)

    if specialisation:
        filters.append("(g.specialisation = ? OR g.secondary_specialisation = ?)")
        params.extend([specialisation, specialisation])

    where = " AND ".join(filters)
    sql = f"""
        SELECT
            g.guide_id,
            g.display_name,
            g.languages,
            g.specialisation,
            g.secondary_specialisation,
            g.years_experience,
            g.rating,
            g.review_count,
            g.day_rate,
            g.half_day_rate,
            g.currency,
            g.certified,
            g.bio,
            g.city_id,
            c.city_name
        FROM tour_guides g
        LEFT JOIN cities c ON c.city_id = g.city_id
        WHERE {where}
        ORDER BY g.rating DESC, g.review_count DESC
        LIMIT ?
    """
    params.append(limit * 5)  # over-fetch to allow client-side filtering
    rows = query(sql, tuple(params))

    results = []
    for row in rows:
        row = _coerce_money(row)

        # Language filter (R6 — BCP-47)
        if languages:
            guide_langs = [l.strip() for l in (row.get("languages") or "").split(",")]
            if not any(lang in guide_langs for lang in languages):
                continue

        # Day-rate filter (R3 — Decimal comparison)
        if max_day_rate is not None:
            rate = row.get("day_rate")
            if rate is not None and rate > max_day_rate:
                continue

        results.append(_serialize(row))
        if len(results) >= limit:
            break

    # Attach availability if date range given
    if from_date and to_date and results:
        guide_ids = [r["guide_id"] for r in results]
        placeholders = ",".join("?" * len(guide_ids))
        avail_rows = query(
            f"""
            SELECT guide_id, for_date, is_available, slots_available, price_multiplier
            FROM guide_availability
            WHERE guide_id IN ({placeholders})
              AND for_date >= ?
              AND for_date <= ?
              AND is_available = 1
            ORDER BY for_date
            """,
            tuple(guide_ids) + (from_date, to_date),
        )
        avail_map: dict[str, list[dict]] = {}
        for av in avail_rows:
            avail_map.setdefault(av["guide_id"], []).append(av)
        for r in results:
            r["availability"] = avail_map.get(r["guide_id"], [])

    return results


# ---------------------------------------------------------------------------
# Tour Packages (Task C)
# ---------------------------------------------------------------------------

def get_packages(
    *,
    city_id: str | None = None,
    languages: list[str] | None = None,
    theme: str | None = None,
    min_days: int | None = None,
    max_days: int | None = None,
    max_price: Decimal | None = None,
    currency: str = "INR",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return tour packages filtered by city, language, theme, duration, price."""
    filters: list[str] = ["tp.status = 'active'"]
    params: list[Any] = []

    if city_id:
        filters.append("tp.city_id = ?")
        params.append(city_id)

    if theme:
        filters.append("tp.theme = ?")
        params.append(theme)

    if min_days is not None:
        filters.append("tp.duration_days >= ?")
        params.append(min_days)

    if max_days is not None:
        filters.append("tp.duration_days <= ?")
        params.append(max_days)

    where = " AND ".join(filters)
    sql = f"""
        SELECT
            tp.package_id,
            tp.city_id,
            tp.name,
            tp.theme,
            tp.tier,
            tp.duration_days,
            tp.duration_nights,
            tp.base_price,
            tp.currency,
            tp.min_group_size,
            tp.max_group_size,
            tp.difficulty,
            tp.languages_offered,
            tp.inclusions,
            tp.exclusions,
            tp.description,
            c.city_name
        FROM tour_packages tp
        LEFT JOIN cities c ON c.city_id = tp.city_id
        WHERE {where}
        ORDER BY tp.base_price ASC
        LIMIT ?
    """
    params.append(limit * 5)
    rows = query(sql, tuple(params))

    results = []
    for row in rows:
        row = _coerce_money(row)

        # Language filter
        if languages:
            pkg_langs = [l.strip() for l in (row.get("languages_offered") or "").split(",")]
            if not any(lang in pkg_langs for lang in languages):
                continue

        # Price filter (same currency only for simplicity)
        if max_price is not None and row.get("currency") == currency:
            price = row.get("base_price")
            if price is not None and price > max_price:
                continue

        results.append(_serialize(row))
        if len(results) >= limit:
            break

    return results


# ---------------------------------------------------------------------------
# Package Components (Task D)
# ---------------------------------------------------------------------------

def get_components(package_id: str) -> list[dict[str, Any]]:
    """Return all components for a package, ordered by day_index + slot."""
    rows = query(
        """
        SELECT *
        FROM package_components
        WHERE package_id = ?
        ORDER BY day_index, slot
        """,
        (package_id,),
    )
    return [_serialize(_coerce_money(r)) for r in rows]


def get_alternatives(component_id: str) -> list[dict[str, Any]]:
    """
    Return swappable alternatives for a component (same swap_group,
    different component_id, same package).
    """
    comp = query_one(
        "SELECT package_id, swap_group FROM package_components WHERE component_id = ?",
        (component_id,),
    )
    if not comp or not comp.get("swap_group"):
        return []

    rows = query(
        """
        SELECT *
        FROM package_components
        WHERE package_id = ?
          AND swap_group = ?
          AND component_id != ?
          AND is_swappable = 1
        ORDER BY price_delta ASC
        """,
        (comp["package_id"], comp["swap_group"], component_id),
    )
    return [_serialize(_coerce_money(r)) for r in rows]


def compute_swap_delta(
    from_component_id: str, to_component_id: str
) -> Decimal:
    """
    Compute the net price change when swapping one component for another.
    Returns a signed Decimal (positive = costs more, negative = saves).
    """
    from_row = query_one(
        "SELECT price_delta FROM package_components WHERE component_id = ?",
        (from_component_id,),
    )
    to_row = query_one(
        "SELECT price_delta FROM package_components WHERE component_id = ?",
        (to_component_id,),
    )
    if not from_row or not to_row:
        raise ValueError("Component not found")

    delta = _to_decimal(to_row["price_delta"]) - _to_decimal(from_row["price_delta"])
    return delta


# ---------------------------------------------------------------------------
# Reference data helpers
# ---------------------------------------------------------------------------

def get_cities(country_iso2: str = "IN", limit: int = 100) -> list[dict[str, Any]]:
    """Return active cities for a country."""
    rows = query(
        """
        SELECT city_id, city_name, state_province, country_iso2, timezone
        FROM cities
        WHERE country_iso2 = ? AND status = 'active'
        ORDER BY city_name
        LIMIT ?
        """,
        (country_iso2, limit),
    )
    return rows


def get_languages() -> list[dict[str, Any]]:
    """Return all supported languages (BCP-47 tags)."""
    return query(
        "SELECT language_id, bcp47, english_name, native_name, script, rtl FROM languages ORDER BY english_name"
    )
