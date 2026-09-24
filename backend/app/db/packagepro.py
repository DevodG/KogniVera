"""Read-only access to the PackagePro source database.

The supplied ``PS-04.db`` is the single source of travel truth. It is opened
read-only (``mode=ro``) and Waypoint never writes to it. Money columns are
TEXT by design; they are converted to ``Decimal`` on the way in and never
touched by a float.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Iterable, Optional

from .. import config

_LOCK = threading.Lock()


class PackageProError(RuntimeError):
    """Raised when the PackagePro source is missing or unusable."""


class PackageProDB:
    """Thin read-only wrapper over ``PackagePro/data/PS-04.db``."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = str(path or config.PACKAGEPRO_DB_PATH)
        if not self._exists():
            raise PackageProError(f"PackagePro DB not found: {self.path}")

    def _exists(self) -> bool:
        try:
            with open(self.path, "rb"):
                return True
        except OSError:
            return False

    @contextmanager
    def connect(self) -> Iterable[sqlite3.Connection]:
        """Yield a read-only connection.

        ``uri=True`` + ``mode=ro`` means SQLite refuses to write even if a
        caller tries, which protects rule 1 (PS-04.db is read-only).
        """
        conn = sqlite3.connect(
            f"file:{self.path}?mode=ro", uri=True, check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Low-level query helper
    # ------------------------------------------------------------------

    def query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            with _LOCK:
                cur = conn.execute(sql, params)
                rows = cur.fetchall()
        return [dict(r) for r in rows]

    def query_one(self, sql: str, params: tuple = ()) -> Optional[dict[str, Any]]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    # ------------------------------------------------------------------
    # Reference data
    # ------------------------------------------------------------------

    def cities(self, limit: int = 200) -> list[dict[str, Any]]:
        return self.query(
            """SELECT city_id, name, state, country_code, timezone, region,
                      primary_language
               FROM cities
               WHERE status = 'active'
               ORDER BY name
               LIMIT ?""",
            (limit,),
        )

    def city(self, city_id: str) -> Optional[dict[str, Any]]:
        return self.query_one(
            """SELECT city_id, name, state, country_code, timezone, region,
                      primary_language, description
               FROM cities WHERE city_id = ?""",
            (city_id,),
        )

    def languages(self) -> list[dict[str, Any]]:
        return self.query(
            """SELECT bcp47, english_name, native_name, script, rtl
               FROM languages ORDER BY english_name"""
        )

    # ------------------------------------------------------------------
    # Packages
    # ------------------------------------------------------------------

    def packages_by_city(self, city_id: str) -> list[dict[str, Any]]:
        return self.query(
            """SELECT package_id, city_id, name, theme, tier, duration_days,
                      duration_nights, base_price, currency, min_group_size,
                      max_group_size, difficulty, languages_offered, inclusions,
                      exclusions, description, status
               FROM tour_packages
               WHERE city_id = ? AND status = 'active'
               ORDER BY package_id""",
            (city_id,),
        )

    def package(self, package_id: str) -> Optional[dict[str, Any]]:
        return self.query_one(
            """SELECT package_id, city_id, name, theme, tier, duration_days,
                      duration_nights, base_price, currency, min_group_size,
                      max_group_size, difficulty, languages_offered, inclusions,
                      exclusions, description, status
               FROM tour_packages WHERE package_id = ?""",
            (package_id,),
        )

    def components(self, package_id: str) -> list[dict[str, Any]]:
        return self.query(
            """SELECT component_id, package_id, component_type, entity_type,
                      entity_id, day_index, slot, title, quantity, price_delta,
                      currency, is_optional, is_swappable, swap_group
               FROM package_components
               WHERE package_id = ?
               ORDER BY day_index, slot, component_id""",
            (package_id,),
        )

    def component(self, component_id: str) -> Optional[dict[str, Any]]:
        return self.query_one(
            """SELECT component_id, package_id, component_type, entity_type,
                      entity_id, day_index, slot, title, quantity, price_delta,
                      currency, is_optional, is_swappable, swap_group
               FROM package_components WHERE component_id = ?""",
            (component_id,),
        )

    def swap_alternatives(self, package_id: str, swap_group: str) -> list[dict[str, Any]]:
        return self.query(
            """SELECT component_id, package_id, component_type, entity_type,
                      entity_id, day_index, slot, title, quantity, price_delta,
                      currency, is_optional, is_swappable, swap_group
               FROM package_components
               WHERE package_id = ? AND swap_group = ? AND is_swappable = 1
               ORDER BY day_index, slot, component_id""",
            (package_id, swap_group),
        )

    # ------------------------------------------------------------------
    # Guides
    # ------------------------------------------------------------------

    def guides_by_city(self, city_id: str) -> list[dict[str, Any]]:
        return self.query(
            """SELECT guide_id, city_id, display_name, languages, specialisation,
                      secondary_specialisation, years_experience, rating,
                      review_count, day_rate, half_day_rate, currency,
                      certified, bio, status
               FROM tour_guides
               WHERE city_id = ? AND status = 'active'
               ORDER BY display_name""",
            (city_id,),
        )

    def guide(self, guide_id: str) -> Optional[dict[str, Any]]:
        return self.query_one(
            """SELECT guide_id, city_id, display_name, languages, specialisation,
                      secondary_specialisation, years_experience, rating,
                      review_count, day_rate, half_day_rate, currency,
                      certified, bio, status
               FROM tour_guides WHERE guide_id = ?""",
            (guide_id,),
        )

    def guide_availability(
        self, guide_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        return self.query(
            """SELECT availability_id, guide_id, for_date, is_available,
                      slots_available, price_multiplier
               FROM guide_availability
               WHERE guide_id = ? AND for_date BETWEEN ? AND ?
               ORDER BY for_date""",
            (guide_id, start_date, end_date),
        )

    def availability_for_guides(
        self, guide_ids: list[str], start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        if not guide_ids:
            return []
        placeholders = ",".join("?" for _ in guide_ids)
        return self.query(
            f"""SELECT availability_id, guide_id, for_date, is_available,
                       slots_available, price_multiplier
                FROM guide_availability
                WHERE guide_id IN ({placeholders}) AND for_date BETWEEN ? AND ?
                ORDER BY guide_id, for_date""",
            (*guide_ids, start_date, end_date),
        )

    # ------------------------------------------------------------------
    # Optional price-history enhancement
    # ------------------------------------------------------------------

    def price_history(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
        return self.query(
            """SELECT history_id, entity_type, entity_id, effective_date, price,
                      currency, baseline_price, demand_index, occupancy_pct,
                      lead_time_factor, seasonality_factor, event_factor,
                      competitor_factor, bound_clamped, explanation
               FROM price_history
               WHERE entity_type = ? AND entity_id = ?
               ORDER BY effective_date""",
            (entity_type, entity_id),
        )

    def table_counts(self) -> dict[str, int]:
        wanted = [
            "cities", "tour_packages", "package_components", "tour_guides",
            "guide_availability", "languages", "price_history",
        ]
        out: dict[str, int] = {}
        for t in wanted:
            try:
                out[t] = int(self.query_one(f"SELECT COUNT(*) AS n FROM {t}")["n"])
            except sqlite3.OperationalError:
                out[t] = 0
        return out


# ---------------------------------------------------------------------------
# Decimal casting helpers — the money rule, enforced at the boundary
# ---------------------------------------------------------------------------


def dec(value: Any) -> Decimal:
    """Cast a stored money/number string to Decimal. Never a float.

    R3: money is a pair (2-place decimal + ISO currency). The DB stores TEXT so
    SQLite's NUMERIC affinity cannot destroy the exact value. A genuine Python
    ``float`` reaching this function is a bug and is rejected, because a float
    already lost the exact value. Values that arrive from SQLite via NUMERIC
    affinity (e.g. a ``rating`` read back as ``4.3``) are converted from their
    *text* representation so no precision is lost.
    """
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise PackageProError(f"float money value reached Decimal casting: {value!r}")
    return Decimal(str(value).strip())


def dec_num(value: Any) -> Decimal:
    """Cast a non-money numeric column (rating, multiplier, occupancy) safely.

    These columns are NUMERIC in SQLite and may come back as Python floats.
    They are never money, so they are converted from their shortest text form
    rather than being treated as prices.
    """
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value).strip())


def money_cols(row: dict[str, Any], *cols: str) -> dict[str, Decimal]:
    return {c: dec(row.get(c)) for c in cols}
