"""
Money — the R3 boundary. Rule R3: money is a pair, a 2-place decimal plus an
ISO-4217 currency code. Never a float.

This is the single most load-bearing type in the product. The old build used
float in BudgetGuard; a float total drifts 0.01 and the trust thesis dies on
stage. Here a float can never reach a price: the only constructors are
Decimal, str, or int, and every arithmetic path stays in Decimal end to end.

The class is serialised as a STRING ("8532674.03"), never a JSON number — a
JSON number is an IEEE-754 double and would silently reintroduce the bug.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import total_ordering

# 2-place storage is the contract (DECIMAL(12,2) in the provided schema).
_CENTS = Decimal("0.01")


class CurrencyMismatchError(TypeError):
    """Raised when money in two currencies is combined without conversion."""


@total_ordering
class Money:
    """An amount plus its ISO-4217 currency. Immutable, decimal-exact."""

    __slots__ = ("_amount", "_currency")

    def __init__(self, amount: Decimal | str | int, currency: str) -> None:
        if isinstance(amount, float):
            raise TypeError(
                "Money must never be constructed from a float (R3). "
                "Pass a Decimal, str or int; the DB stores money as TEXT."
            )
        if not currency or not isinstance(currency, str):
            raise ValueError("Money requires an ISO-4217 currency code")
        try:
            parsed = Decimal(str(amount))
        except InvalidOperation as exc:
            raise ValueError(f"not a valid money amount: {amount!r}") from exc
        if parsed.is_nan() or parsed.is_infinite():
            raise ValueError(f"money amount must be finite: {amount!r}")
        self._amount = parsed.quantize(_CENTS, rounding=ROUND_HALF_UP)
        self._currency = currency

    # ------------------------------------------------------------------ props
    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def currency(self) -> str:
        return self._currency

    # ------------------------------------------------------------ arithmetic
    def _check(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError(f"can only combine Money with Money, got {type(other).__name__}")
        if other._currency != self._currency:
            raise CurrencyMismatchError(
                f"cannot combine {self._currency} with {other._currency} — convert first"
            )

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self._amount + other._amount, self._currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self._amount - other._amount, self._currency)

    def __mul__(self, factor: Decimal | str | int) -> "Money":
        if isinstance(factor, float):
            raise TypeError("never multiply Money by a float (R3)")
        return Money(self._amount * Decimal(str(factor)), self._currency)

    __rmul__ = __mul__

    def __neg__(self) -> "Money":
        return Money(-self._amount, self._currency)

    def __abs__(self) -> "Money":
        return Money(abs(self._amount), self._currency)

    # ------------------------------------------------------------- comparison
    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Money)
            and self._currency == other._currency
            and self._amount == other._amount
        )

    def __lt__(self, other: "Money") -> bool:
        self._check(other)
        return self._amount < other._amount

    def __bool__(self) -> bool:
        return self._amount != 0

    def is_zero(self) -> bool:
        return self._amount == 0

    def is_negative(self) -> bool:
        return self._amount < 0

    # --------------------------------------------------------------- helpers
    @classmethod
    def zero(cls, currency: str) -> "Money":
        return cls(Decimal("0"), currency)

    def scale(self, multiplier: Decimal | str | int) -> "Money":
        """Multiply by a dimensionless factor (e.g. a peak-date multiplier)."""
        if isinstance(multiplier, float):
            raise TypeError("never scale Money by a float (R3)")
        return Money(self._amount * Decimal(str(multiplier)), self._currency)

    def split(self, parts: int) -> list["Money"]:
        """
        Largest-remainder allocation so the parts sum exactly to the whole.
        R1000.00 three ways is 333.34 + 333.33 + 333.33 — never 3 x 333.33,
        which leaks 0.01. This is the convention the data guide specifies.
        """
        if parts <= 0:
            raise ValueError("parts must be positive")
        if parts == 1:
            return [self]
        total_cents = int((self._amount * 100).to_integral_value())
        base, remainder = divmod(total_cents, parts)
        shares = [Decimal(base)] * parts
        for i in range(remainder):
            shares[i] += 1
        return [Money(Decimal(c) / 100, self._currency) for c in shares]

    def format(self, locale: str = "en-IN") -> str:
        """Human-readable display string. Amount stays Decimal throughout."""
        sign = "-" if self._amount < 0 else ""
        whole = abs(int(self._amount))
        cents = abs(int((self._amount * 100).to_integral_value()) % 100)
        # Indian grouping (2-3-3...) for INR, 3-grouping otherwise.
        if self._currency == "INR":
            s = str(whole)
            if len(s) > 3:
                last3, rest = s[-3:], s[:-3]
                groups = [last3]
                while rest:
                    groups.insert(0, rest[-2:])
                    rest = rest[:-2]
                whole_str = ",".join(groups)
            else:
                whole_str = s
        else:
            whole_str = f"{whole:,}"
        return f"{sign}{whole_str}.{cents:02d} {self._currency}"

    # ----------------------------------------------------------- serialisation
    def __str__(self) -> str:
        # Text on the wire — a JSON number would be a float (R3).
        return f"{self._amount} {self._currency}"

    def __repr__(self) -> str:
        return f"Money('{self._amount}', '{self._currency}')"

    def to_dict(self) -> dict[str, str]:
        """API boundary: amount as string, currency alongside (always a pair)."""
        return {"amount": str(self._amount), "currency": self._currency}

    @classmethod
    def from_db(cls, value: str | None, currency: str) -> "Money":
        """Lift a TEXT money column straight from SQLite into Money."""
        if value is None:
            return cls.zero(currency)
        return cls(value, currency)

    @classmethod
    def sum(cls, amounts: list["Money"], currency: str) -> "Money":
        """Sum a list, enforcing one currency. Empty list is zero in `currency`."""
        total = cls.zero(currency)
        for m in amounts:
            total = total + m  # currency check fires on the first mismatch
        return total


def money_sum(amounts: list[Money], currency: str) -> Money:
    return Money.sum(amounts, currency)


# ---------------------------------------------------------------------------
# FX — read-only rates from the provided currencies table are not present, so
# conversion is an explicit, logged operation the caller must supply rates for.
# We never silently invent a rate; that would be worse than raising.
# ---------------------------------------------------------------------------
def convert(m: Money, to_currency: str, rate: Decimal | str) -> Money:
    """Convert via an explicit rate supplied by the caller (rate = to/from)."""
    if m.currency == to_currency:
        return m
    if isinstance(rate, float):
        raise TypeError("never convert via a float rate (R3)")
    return Money(m.amount * Decimal(str(rate)), to_currency)
