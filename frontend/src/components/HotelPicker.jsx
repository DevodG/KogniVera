export default function HotelPicker({ options, selectedIndex, onSelect, loading }) {
  if (!options || options.length === 0) return null;

  // Find the best value (cheapest total)
  const bestValueIdx = options.reduce(
    (minIdx, opt, i, arr) => (opt.total_price_inr < arr[minIdx].total_price_inr ? i : minIdx),
    0
  );

  return (
    <div className="slide-up">
      <div className="section-header">Pick your hotel</div>
      <div className="section-sub">
        {options.length} hotels found. Your flight is locked in — now choose where to stay.
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {options.map((hotel, i) => (
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
                  {hotel.name}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ color: "var(--signal)", fontSize: 14 }}>
                    {"★".repeat(Math.round(hotel.rating || 0))}
                    {"☆".repeat(5 - Math.round(hotel.rating || 0))}
                  </span>
                  <span className="dim" style={{ fontSize: 13 }}>{hotel.rating}</span>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="mono" style={{ fontSize: 18, fontWeight: 600, color: "var(--signal)" }}>
                  ₹{hotel.total_price_inr?.toLocaleString()}
                </div>
                <div className="mono dim" style={{ fontSize: 11 }}>
                  ₹{hotel.price_per_night_inr?.toLocaleString()}/night × {hotel.nights}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <div className="mono dim" style={{ fontSize: 12 }}>
                📍 {hotel.city}
              </div>
              <div className="mono dim" style={{ fontSize: 12 }}>
                📅 {hotel.check_in} → {hotel.check_out}
              </div>
              {i === bestValueIdx && (
                <span className="badge badge-recommended">★ Best value</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
