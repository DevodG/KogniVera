/**
 * Money handling for the Waypoint frontend.
 *
 * Rule: money is a pair — a 2-place decimal plus an ISO-4217 currency. A JSON
 * number is an IEEE-754 double and cannot hold the exact value, so every
 * amount travels as a *string* and all arithmetic goes through decimal.js.
 * parseFloat/Number are never used for totals, deltas, budget decisions or
 * displayed money.
 */
import Decimal from "decimal.js";

Decimal.set({ precision: 28, rounding: Decimal.ROUND_HALF_UP });

const SYMBOLS = {
  INR: "₹",
  USD: "$",
  EUR: "€",
  GBP: "£",
  AED: "د.إ",
};

/** Parse a money string from the API into a Decimal (never a float). */
export function money(amount) {
  if (amount === null || amount === undefined || amount === "") {
    return new Decimal("0");
  }
  if (Decimal.isDecimal(amount)) return amount;
  if (typeof amount === "number") {
    throw new Error("float money reached the frontend; amounts must be strings");
  }
  const cleaned = String(amount).replace(/[^0-9.\-]/g, "");
  return new Decimal(cleaned);
}

/** Add two money strings. */
export function add(a, b) {
  return money(a).plus(money(b));
}

/** Subtract two money strings. */
export function subtract(a, b) {
  return money(a).minus(money(b));
}

/** Signed delta as a normalised 2-place string. */
export function delta(a, b) {
  return money(a).minus(money(b)).toDecimalPlaces(2).toString();
}

/** Two-place decimal string, e.g. "20000.00". */
export function toMoneyString(value) {
  return money(value).toDecimalPlaces(2).toString();
}

/** Human readable display, e.g. "₹20,000.00". */
export function formatMoney(amount, currency = "INR") {
  const value = money(amount).toDecimalPlaces(2);
  const symbol = SYMBOLS[currency] || "";
  const numStr = value.toNumber().toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${symbol}${numStr}`;
}

/** Signed display, e.g. "+₹250.00" / "-₹120.00". */
export function formatSignedMoney(amount, currency = "INR") {
  const value = money(amount).toDecimalPlaces(2);
  const symbol = SYMBOLS[currency] || "";
  const sign = value.isNegative() ? "−" : "+";
  const numStr = value.abs().toNumber().toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${sign}${symbol}${numStr}`;
}

/** True when the total is within the cap (comparison only, never a display). */
export function withinBudget(total, cap) {
  return money(total).lte(money(cap));
}
