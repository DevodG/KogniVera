import ConfidenceBadge from "./ConfidenceBadge.jsx";

export default function FlightPicker({ options, selectedIndex, onSelect, loading }) {
  if (!options || options.length === 0) return null;

  // Find the cheapest for "Recommended" badge
  const cheapestIdx = options.reduce(
    (minIdx, opt, i, arr) => (opt.price_inr < arr[minIdx].price_inr ? i : minIdx),
    0
  );

  return (
    <div className="slide-up">
      <div className="section-header">Pick your flight</div>
      <div className="section-sub">
        {options.length} flights found. Tap to select — the agent recommends the best value.
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {options.map((flight, i) => (
          <div
            key={i}
            className={`option-card ${selectedIndex === i ? "selected" : ""}`}
            onClick={() => !loading && onSelect(i)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && !loading && onSelect(i)}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
                  {flight.airline}
                </div>
                <div className="mono dim" style={{ fontSize: 12 }}>
                  {flight.origin} → {flight.destination}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="mono" style={{ fontSize: 18, fontWeight: 600, color: "var(--signal)" }}>
                  ₹{flight.price_inr?.toLocaleString()}
                </div>
                {flight.travelers > 1 && (
                  <div className="mono dim" style={{ fontSize: 11 }}>
                    for {flight.travelers} travelers
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <div className="mono dim" style={{ fontSize: 12 }}>
                🕐 {flight.departure_time}
              </div>
              <div className="mono dim" style={{ fontSize: 12 }}>
                ⏱ {flight.duration_minutes}min
              </div>
              <div className="mono dim" style={{ fontSize: 12 }}>
                📅 {flight.date}
              </div>
              {i === cheapestIdx && (
                <span className="badge badge-recommended">★ Best value</span>
              )}
              {flight.confidence && (
                <ConfidenceBadge confidence={flight.confidence} />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
