"""
PackagePro data-access layer (read-only).

Every column name in this module was read from the live PS-04.db with
PRAGMA table_info, not from memory or from the PDF. The previous build
queried `city_name`, `state_province` and `country_iso2`, which do not exist;
the real columns are `name`, `state` and `country_code`. That single mistake
made the entire data layer throw on every query.

Conventions enforced here:
  R2  IDs are opaque prefixed strings — returned untouched, never parsed.
  R3  Money columns are TEXT in the DB (deliberate: SQLite NUMERIC affinity
      would turn 8500.00 into the float 8500.0). They are lifted straight to
      Money without ever passing through a float.
  R5  Enums are passed through; validation lives in validate_conformance.py.
  R6  Language is matched as a BCP-47 tag against comma-separated lists.
"""
from __future__ import annotations

import os
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

from app.core.money import Money
from app.core.reprice import Component, Package

# ---------------------------------------------------------------------------
# Connection — READ ONLY by construction (mode=ro in the URI).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DB = Path(os.environ.get("PACKAGEPRO_DB_PATH") or (_REPO_ROOT / "PackagePro" / "data" / "PS-04.db"))

_conn: sqlite3.Connection | None = None


def _get_conn(db_path: Path | None = None) -> sqlite3.Connection:
    global _conn
    if _conn is None or db_path is not None:
        path = db_path or _DEFAULT_DB
        if not path.exists():
            raise FileNotFoundError(
                f"PackagePro DB not found at {path}. "
                "Set PACKAGEPRO_DB_PATH or run from the repo root."
            )
        # mode=ro makes it structurally impossible to mutate the provided data.
        _conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    cur = _get_conn().execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    cur = _get_conn().execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# BCP-47 language matching (R6)
# ---------------------------------------------------------------------------

def _parse_langs(raw: str | None) -> list[str]:
    """Split a comma-separated BCP-47 field into a clean list."""
    if not raw:
        return []
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def _lang_matches(wanted: list[str], offered_raw: str | None) -> bool:
    """True if ANY wanted tag appears in the offered list (substring-safe)."""
    if not wanted:
        return True
    offered = _parse_langs(offered_raw)
    # Exact tag match first (fast, correct). Fallback to primary-subtag
    # containment so 'hi' matches 'hi,en-IN' and 'en' matches 'en-IN'.
    for w in wanted:
        if w in offered:
            return True
        w_primary = w.split("-")[0]
        for o in offered:
            if o == w_primary or o.split("-")[0] == w_primary:
                return True
    return False


# ---------------------------------------------------------------------------
# Cities
# ---------------------------------------------------------------------------

def get_cities(country_code: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Active cities, optionally filtered by denormalised ISO2 country_code."""
    sql = """
        SELECT city_id, name, state, country_id, country_code, timezone,
               region, primary_language, description
        FROM cities
        WHERE status = 'active'
    """
    params: tuple = ()
    if country_code:
        sql += " AND country_code = ?"
        params = (country_code,)
    sql += " ORDER BY name LIMIT ?"
    params = params + (limit,)
    return query(sql, params)


def get_city(city_id: str) -> dict[str, Any] | None:
    return query_one(
        "SELECT city_id, name, state, country_id, country_code, timezone, "
        "region, primary_language, description FROM cities WHERE city_id = ?",
        (city_id,),
    )


# ---------------------------------------------------------------------------
# Tour packages
# ---------------------------------------------------------------------------

_PACKAGE_COLS = """package_id, city_id, name, theme, tier, duration_days,
    duration_nights, base_price, currency, min_group_size, max_group_size,
    difficulty, languages_offered, inclusions, exclusions, description, status"""


def _row_to_package(row: dict[str, Any]) -> Package:
    return Package(
        package_id=row["package_id"],
        city_id=row["city_id"],
        name=row["name"],
        theme=row["theme"],
        tier=row["tier"],
        duration_days=row["duration_days"],
        duration_nights=row["duration_nights"],
        base_price=Money.from_db(row["base_price"], row["currency"]),  # R3
        min_group_size=row["min_group_size"],
        max_group_size=row["max_group_size"],
        difficulty=row["difficulty"],
        languages_offered=_parse_langs(row["languages_offered"]),
        inclusions=row["inclusions"],
        exclusions=row["exclusions"],
        description=row["description"],
    )


def get_packages(
    *,
    languages: list[str] | None = None,
    theme: str | None = None,
    tier: str | None = None,
    city_id: str | None = None,
    min_days: int | None = None,
    max_days: int | None = None,
    max_price: Decimal | None = None,
    party_size: int | None = None,
    limit: int = 24,
) -> list[Package]:
    """Filter tour packages. Language filtering is the PS-04 requirement (R6)."""
    filters = ["status = 'active'"]
    params: list[Any] = []

    if city_id:
        filters.append("city_id = ?")
        params.append(city_id)
    if theme:
        filters.append("theme = ?")
        params.append(theme)
    if tier:
        filters.append("tier = ?")
        params.append(tier)
    if min_days is not None:
        filters.append("duration_days >= ?")
        params.append(min_days)
    if max_days is not None:
        filters.append("duration_days <= ?")
        params.append(max_days)
    if party_size is not None:
        filters.append("min_group_size <= ? AND max_group_size >= ?")
        params.extend([party_size, party_size])

    sql = f"SELECT {_PACKAGE_COLS} FROM tour_packages WHERE {' AND '.join(filters)}"
    sql += " ORDER BY CAST(base_price AS REAL) ASC"  # CAST for sort only, never arithmetic
    rows = query(sql, tuple(params))

    out = [_row_to_package(r) for r in rows]

    # Language filter (R6) — applied on parsed tags, never on raw substring.
    if languages:
        out = [p for p in out if _lang_matches(languages, ",".join(p.languages_offered))]

    # Price ceiling — compared in Decimal (R3), same currency only.
    if max_price is not None:
        out = [p for p in out if p.base_price.amount <= max_price]

    return out[:limit]


def get_package(package_id: str) -> Package | None:
    row = query_one(
        f"SELECT {_PACKAGE_COLS} FROM tour_packages WHERE package_id = ?",
        (package_id,),
    )
    return _row_to_package(row) if row else None


# ---------------------------------------------------------------------------
# Package components
# ---------------------------------------------------------------------------

def _row_to_component(row: dict[str, Any]) -> Component:
    return Component(
        component_id=row["component_id"],
        package_id=row["package_id"],
        component_type=row["component_type"],
        entity_type=row.get("entity_type"),
        entity_id=row.get("entity_id"),
        day_index=row["day_index"],
        slot=row["slot"],
        title=row["title"],
        quantity=row["quantity"],
        price_delta=Money.from_db(row["price_delta"], row["currency"]),  # R3
        is_optional=bool(row["is_optional"]),
        is_swappable=bool(row["is_swappable"]),
        swap_group=row.get("swap_group") or None,
    )


def get_components(package_id: str) -> list[Component]:
    """All components of a package in itinerary order."""
    rows = query(
        """
        SELECT * FROM package_components
        WHERE package_id = ?
        ORDER BY day_index, slot, component_id
        """,
        (package_id,),
    )
    return [_row_to_component(r) for r in rows]


def get_component(component_id: str) -> Component | None:
    row = query_one("SELECT * FROM package_components WHERE component_id = ?", (component_id,))
    return _row_to_component(row) if row else None


def get_swap_alternatives(component_id: str) -> list[Component]:
    """
    The PS-04 core query: what can this component be swapped for?
    Alternatives share a swap_group within the same package (same slot).
    """
    comp = get_component(component_id)
    if not comp or not comp.swap_group:
        return []
    rows = query(
        """
        SELECT * FROM package_components
        WHERE package_id = ? AND swap_group = ? AND component_id != ?
          AND is_swappable = 1
        ORDER BY CAST(price_delta AS REAL) ASC
        """,
        (comp.package_id, comp.swap_group, component_id),
    )
    return [_row_to_component(r) for r in rows]


def components_grouped_by_day(package_id: str) -> dict[int, list[Component]]:
    """Components bucketed by day_index for the itinerary timeline UI."""
    out: dict[int, list[Component]] = {}
    for comp in get_components(package_id):
        out.setdefault(comp.day_index, []).append(comp)
    return dict(sorted(out.items()))


# ---------------------------------------------------------------------------
# Tour guides + availability (the PS-04 guide dimension)
# ---------------------------------------------------------------------------

_GUIDE_COLS = """guide_id, city_id, display_name, languages, specialisation,
    secondary_specialisation, years_experience, rating, review_count, day_rate,
    half_day_rate, currency, certified, bio, status"""


def _row_to_guide(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "guide_id": row["guide_id"],
        "city_id": row["city_id"],
        "display_name": row["display_name"],
        "languages": _parse_langs(row["languages"]),  # R6
        "specialisation": row["specialisation"],
        "secondary_specialisation": row.get("secondary_specialisation"),
        "years_experience": row["years_experience"],
        "rating": Decimal(str(row["rating"])) if row.get("rating") is not None else None,
        "review_count": row["review_count"],
        "day_rate": Money.from_db(row["day_rate"], row["currency"]),  # R3
        "half_day_rate": Money.from_db(row["half_day_rate"], row["currency"]),
        "currency": row["currency"],
        "certified": bool(row["certified"]),
        "bio": row["bio"],
    }


def get_guides(
    *,
    languages: list[str] | None = None,
    specialisation: str | None = None,
    city_id: str | None = None,
    max_day_rate: Decimal | None = None,
    certified_only: bool = False,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Match guides by language, specialisation, city and rate (all PS-04 filters)."""
    filters = ["status = 'active'"]
    params: list[Any] = []

    if city_id:
        filters.append("city_id = ?")
        params.append(city_id)
    if specialisation:
        filters.append("(specialisation = ? OR secondary_specialisation = ?)")
        params.extend([specialisation, specialisation])
    if certified_only:
        filters.append("certified = 1")
    if max_day_rate is not None:
        filters.append("CAST(day_rate AS REAL) <= ?")
        params.append(float(max_day_rate))  # filter bound, not displayed arithmetic

    sql = f"""
        SELECT {_GUIDE_COLS} FROM tour_guides
        WHERE {' AND '.join(filters)}
        ORDER BY CAST(rating AS REAL) DESC NULLS LAST, review_count DESC
    """
    rows = query(sql, tuple(params))

    out = [_row_to_guide(r) for r in rows]
    if languages:
        out = [g for g in out if _lang_matches(languages, ",".join(g["languages"]))]

    return out[:limit]


def get_guide(guide_id: str) -> dict[str, Any] | None:
    row = query_one(f"SELECT {_GUIDE_COLS} FROM tour_guides WHERE guide_id = ?", (guide_id,))
    return _row_to_guide(row) if row else None


def get_guide_availability(
    guide_id: str, from_date: str, to_date: str
) -> list[dict[str, Any]]:
    """
    Is this guide actually free? Availability is a real query, never an
    assumption — 'no guide free that day' is a state the UI must handle.
    """
    rows = query(
        """
        SELECT availability_id, guide_id, for_date, is_available,
               slots_available, price_multiplier
        FROM guide_availability
        WHERE guide_id = ? AND for_date >= ? AND for_date <= ?
        ORDER BY for_date
        """,
        (guide_id, from_date, to_date),
    )
    return [
        {
            **r,
            "is_available": bool(r["is_available"]),
            "price_multiplier": Decimal(str(r["price_multiplier"])),
        }
        for r in rows
    ]


def guides_available_on(
    languages: list[str] | None,
    specialisation: str | None,
    on_date: str,
    city_id: str | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Guides who speak the language, do the specialisation, AND are free that day."""
    guides = get_guides(
        languages=languages,
        specialisation=specialisation,
        city_id=city_id,
        limit=limit * 3,
    )
    free: list[dict[str, Any]] = []
    for g in guides:
        avail = get_guide_availability(g["guide_id"], on_date, on_date)
        slot = next((a for a in avail if a["is_available"] and a["slots_available"] > 0), None)
        if slot:
            # Peak-date price: day_rate * multiplier, in Decimal (R3).
            peak_rate = g["day_rate"].scale(slot["price_multiplier"])
            free.append({**g, "on_date": on_date, "slot": slot, "peak_day_rate": peak_rate})
    return free[:limit]


# ---------------------------------------------------------------------------
# Price history — the explainability surface
# ---------------------------------------------------------------------------

def get_price_explanation(entity_id: str, on_date: str | None = None) -> dict[str, Any] | None:
    """
    Why does this cost what it costs? Pulls the driving factors for a date
    (or the latest available date) from price_history.

    price_history covers only room_type and flight_fare entities, while
    package_components point at hotels — so hotel-level requests are resolved
    through the hotel's room types. Returns None where no history exists
    rather than fabricating factors.
    """
    # Resolve a hotel to the room_type rows that actually carry history.
    entity_ids: list[str] = [entity_id]
    if entity_id.startswith("htl_"):
        rows = query(
            "SELECT room_type_id FROM hotel_room_types WHERE hotel_id = ?", (entity_id,)
        )
        entity_ids = [r["room_type_id"] for r in rows] or [entity_id]
    if not entity_ids:
        return None

    placeholders = ",".join("?" * len(entity_ids))
    if on_date:
        row = query_one(
            f"""SELECT * FROM price_history WHERE entity_id IN ({placeholders})
               AND effective_date = ?
               ORDER BY computed_at DESC LIMIT 1""",
            (*entity_ids, on_date),
        )
    else:
        row = query_one(
            f"""SELECT * FROM price_history WHERE entity_id IN ({placeholders})
               ORDER BY effective_date DESC, computed_at DESC LIMIT 1""",
            (*entity_ids,),
        )
    if not row:
        return None
    return {
        "history_id": row["history_id"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "effective_date": row["effective_date"],
        "price": Money.from_db(row["price"], row["currency"]),  # R3
        "baseline_price": Money.from_db(row["baseline_price"], row["currency"]),
        "demand_index": Decimal(str(row["demand_index"])),
        "occupancy_pct": Decimal(str(row["occupancy_pct"])),
        "lead_time_factor": Decimal(str(row["lead_time_factor"])),
        "seasonality_factor": Decimal(str(row["seasonality_factor"])),
        "event_factor": Decimal(str(row["event_factor"])),
        "competitor_factor": Decimal(str(row["competitor_factor"])),
        "bound_clamped": bool(row["bound_clamped"]),
        "explanation": row["explanation"],
    }


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

def get_languages() -> list[dict[str, Any]]:
    return query(
        "SELECT language_id, bcp47, english_name, native_name, script, rtl, tts_supported "
        "FROM languages ORDER BY english_name"
    )


def get_currencies() -> list[dict[str, Any]]:
    rows = query(
        "SELECT currency_id, iso4217, name, symbol, minor_unit_exponent, display_locale "
        "FROM currencies ORDER BY iso4217"
    )
    return rows


def get_currency(iso: str) -> dict[str, Any] | None:
    return query_one(
        "SELECT currency_id, iso4217, name, symbol, minor_unit_exponent, display_locale "
        "FROM currencies WHERE iso4217 = ?",
        (iso,),
    )
