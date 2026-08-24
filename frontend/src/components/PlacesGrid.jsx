const CATEGORY_EMOJI = {
  heritage: "🏛️",
  food: "🍜",
  outdoors: "🌿",
  culture: "🎨",
};

export default function PlacesGrid({ places, destination }) {
  if (!places || places.length === 0) return null;

  return (
    <div className="slide-up" style={{ marginTop: 8 }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 18, marginBottom: 6 }}>
        Things to do in {destination}
      </div>
      <div className="dim" style={{ fontSize: 13, marginBottom: 16 }}>
        Nearby attractions and activities at your destination.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {places.map((place, i) => (
          <div key={i} className="place-card">
            <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>
              {CATEGORY_EMOJI[place.category] || "📌"} {place.name}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="badge badge-category">{place.category}</span>
              {place.avg_cost_inr === 0 ? (
                <span className="badge badge-free">Free</span>
              ) : (
                <span className="mono dim" style={{ fontSize: 11 }}>
                  ~₹{place.avg_cost_inr}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
