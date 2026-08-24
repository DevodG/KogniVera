export default function CostLedger({ runningTotal, budgetCap, chosenFlight, chosenHotel, currency = "INR" }) {
  const cap = budgetCap || 0;
  const total = runningTotal || 0;
  const pct = cap > 0 ? Math.min(100, (total / cap) * 100) : 0;
  const over = total > cap;
  const remaining = cap - total;

  const flightCost = chosenFlight?.price_inr || 0;
  const hotelCost = chosenHotel?.total_price_inr || 0;

  return (
    <div className="panel" style={{ padding: 20 }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 18, marginBottom: 16 }}>
        Budget ledger
      </div>

      {/* Progress bar */}
      <div style={{ height: 10, background: "var(--panel-raised)", borderRadius: 6, overflow: "hidden", marginBottom: 12 }}>
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: over
              ? "var(--stop)"
              : pct > 80
                ? "linear-gradient(90deg, var(--signal), var(--stop))"
                : "linear-gradient(90deg, var(--go), var(--signal))",
            transition: "width 0.5s ease, background 0.3s ease",
            borderRadius: 6,
          }}
        />
      </div>

      {/* Percentage label */}
      <div className="mono" style={{ fontSize: 12, textAlign: "right", marginBottom: 16, color: over ? "var(--stop)" : "var(--dim)" }}>
        {pct.toFixed(0)}% of budget used
      </div>

      {/* Breakdown items */}
      {flightCost > 0 && (
        <div className="mono" style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 6 }}>
          <span className="dim">✈ Flight ({chosenFlight?.airline})</span>
          <span>₹{flightCost.toLocaleString()}</span>
        </div>
      )}
      {hotelCost > 0 && (
        <div className="mono" style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 6 }}>
          <span className="dim">🏨 Hotel ({chosenHotel?.name})</span>
          <span>₹{hotelCost.toLocaleString()}</span>
        </div>
      )}

      {/* Divider */}
      {(flightCost > 0 || hotelCost > 0) && (
        <div style={{ borderTop: "1px solid var(--line)", marginTop: 10, paddingTop: 10 }}>
          <div className="mono" style={{ display: "flex", justifyContent: "space-between", fontSize: 14, fontWeight: 600 }}>
            <span>Total</span>
            <span style={{ color: over ? "var(--stop)" : "var(--signal)" }}>
              ₹{total.toLocaleString()} {currency}
            </span>
          </div>
        </div>
      )}

      {/* Cap info */}
      <div className="mono dim" style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginTop: 8 }}>
        <span>Budget cap</span>
        <span>₹{cap.toLocaleString()} {currency}</span>
      </div>
      <div className="mono dim" style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginTop: 4 }}>
        <span>Remaining</span>
        <span style={{ color: remaining < 0 ? "var(--stop)" : "var(--go)" }}>
          ₹{remaining.toLocaleString()} {currency}
        </span>
      </div>
    </div>
  );
}
