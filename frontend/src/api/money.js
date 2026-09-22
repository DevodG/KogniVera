// Money on the client — decimal.js, never a JS number.
// The server sends {amount: "17645.89", currency: "INR"} as STRINGS. A JSON
// number would be an IEEE-754 double and would reintroduce the float drift
// the whole R3 rule exists to prevent. We parse into Decimal and format out.

import Decimal from "decimal.js";

Decimal.set({ precision: 28, rounding: Decimal.ROUND_HALF_UP });

export class Money {
  constructor(amount, currency) {
    if (typeof amount === "number") {
      throw new TypeError("Money must never be constructed from a JS number (R3)");
    }
    this.amount = new Decimal(String(amount));
    this.currency = currency;
  }

  static fromPair(pair) {
    if (!pair || typeof pair.amount !== "string") {
      throw new TypeError("expected {amount: string, currency: string}");
    }
    return new Money(pair.amount, pair.currency);
  }

  static zero(currency) {
    return new Money("0", currency);
  }

  add(other) {
    this._check(other);
    return new Money(this.amount.plus(other.amount), this.currency);
  }

  sub(other) {
    this._check(other);
    return new Money(this.amount.minus(other.amount), this.currency);
  }

  _check(other) {
    if (!(other instanceof Money)) {
      throw new TypeError("can only combine Money with Money");
    }
    if (other.currency !== this.currency) {
      throw new TypeError(`currency mismatch: ${this.currency} vs ${other.currency}`);
    }
  }

  isNegative() {
    return this.amount.isNeg();
  }

  isZero() {
    return this.amount.isZero();
  }

  // Indian grouping for INR, 3-grouping otherwise. Decimal-safe.
  format() {
    const neg = this.amount.isNeg() ? "-" : "";
    const abs = this.amount.abs();
    const [whole, frac] = abs.toFixed(2).split(".");
    let grouped;
    if (this.currency === "INR") {
      grouped = whole.length > 3
        ? whole.slice(-3) + "," + whole.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",")
            .split("").reverse().join("").split("").reverse().join("")
        : whole;
      // simpler: build from the right in 2-digit groups after the first 3
      const chars = whole.split("");
      const out = [chars.splice(-3).join("")];
      while (chars.length) out.unshift(chars.splice(-2).join(""));
      grouped = out.join(",");
    } else {
      grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }
    return `${neg}${grouped}.${frac} ${this.currency}`;
  }

  toPair() {
    return { amount: this.amount.toFixed(2), currency: this.currency };
  }

  toString() {
    return this.format();
  }
}

// Count a Decimal value up to a target with eased progress — for the live
// reprice "ticker". `from` and `to` are Decimal strings; cb receives a
// formatted string. Cancels via the returned handle.
export function animateMoney(fromStr, toStr, cb, { duration = 620, formatter } = {}) {
  const from = new Decimal(fromStr);
  const to = new Decimal(toStr);
  if (from.equals(to)) {
    cb(formatter ? formatter(to) : to.toFixed(2));
    return () => {};
  }
  let raf;
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / duration);
    // easeOutQuint — decelerating, like liquid settling
    const eased = 1 - Math.pow(1 - t, 5);
    const current = from.plus(to.minus(from).times(eased));
    cb(formatter ? formatter(current) : current.toFixed(2));
    if (t < 1) raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
  return () => cancelAnimationFrame(raf);
}
