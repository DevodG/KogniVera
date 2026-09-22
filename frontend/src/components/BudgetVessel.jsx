import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Money, animateMoney } from "../api/money.js";

// The budget vessel — a liquid gauge that fills as the traveler spends.
// Over-cap and the liquid hits the rim, flushes red, and opens negotiation
// from the physics rather than a modal out of nowhere.

export default function BudgetVessel({ cap, runningTotal, pctUsed, onNegotiate }) {
  const pct = Math.max(0, Math.min(100, Number(pctUsed ?? 0)));
  const over = runningTotal && cap && new Decimal(runningTotal.amount).gt(new Decimal(cap.amount));
  const remaining = cap && runningTotal
    ? new Decimal(cap.amount).minus(new Decimal(runningTotal.amount))
    : new Decimal("0");

  // Animated money ticker: counts to the new total on every change.
  const [displayTotal, setDisplayTotal] = useState("0.00");
  const cancelRef = useRef(null);
  useEffect(() => {
    if (!runningTotal) return;
    cancelRef.current?.();
    cancelRef.current = animateMoney(displayTotal, runningTotal.amount, setDisplayTotal, {
      duration: 620,
    });
    return () => cancelRef.current?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runningTotal?.amount]);

  const fmt = (val) => {
    const d = new Decimal(val);
    const neg = d.isNeg() ? "-" : "";
    const abs = d.abs();
    const [whole, frac] = abs.toFixed(2).split(".");
    const chars = whole.split("");
    const out = [chars.splice(-3).join("")];
    while (chars.length) out.unshift(chars.splice(-2).join(""));
    return `${neg}${out.join(",")}.${frac}`;
  };

  return (
    <div className="panel" style={{ padding: 20 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 14,
        }}
      >
        <div>
          <div
            className="mono"
            style={{ fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink-3)" }}
          >
            Budget Vessel
          </div>
          <div style={{ fontSize: 13, color: "var(--ink-2)" }}>
            {cap ? `cap ${fmt(cap.amount)} ${cap.currency}` : "no cap set"}
          </div>
        </div>
        <div
          className="money"
          style={{ fontSize: 20, fontWeight: 600, color: over ? "var(--stop)" : "var(--ink)" }}
        >
          {fmt(displayTotal)}
        </div>
      </div>

      {/* The vessel */}
      <div
        style={{
          position: "relative",
          height: 14,
          borderRadius: 999,
          background: "rgba(255,255,255,0.06)",
          overflow: "hidden",
          border: "1px solid var(--hairline)",
        }}
      >
        <motion.div
          initial={false}
          animate={{
            width: `${pct}%`,
            backgroundColor: over ? "rgba(226,102,92,0.85)" : "rgba(94,234,212,0.7)",
          }}
          transition={{ type: "spring", stiffness: 90, damping: 15, mass: 1.1 }}
          style={{
            height: "100%",
            borderRadius: 999,
            boxShadow: over
              ? "0 0 18px rgba(226,102,92,0.6)"
              : "0 0 14px rgba(94,234,212,0.35)",
          }}
        />
        {/* rim line — where the liquid stops */}
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: `calc(${pct}% - 1px)`,
            width: 2,
            background: over ? "var(--stop)" : "var(--aurora-1)",
            opacity: 0.9,
          }}
        />
      </div>

      <div
        className="mono"
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 10,
          fontSize: 11,
          color: "var(--ink-3)",
        }}
      >
        <span>{pct.toFixed(1)}% used</span>
        <span style={{ color: over ? "var(--stop)" : "var(--go)" }}>
          {over ? "over cap" : `${fmt(remaining.toString())} left`}
        </span>
      </div>

      {over && onNegotiate && (
        <button
          className="btn btn-ghost"
          style={{ width: "100%", marginTop: 14, borderColor: "rgba(226,102,92,0.5)" }}
          onClick={onNegotiate}
        >
          Negotiate
        </button>
      )}
    </div>
  );
}
