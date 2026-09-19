import { useState, useEffect } from "react";
import { api } from "../api/client.js";

export default function GuideMatcher({ cityId, onSelectGuide }) {
  const [guides, setGuides] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [languages, setLanguages] = useState("");
  const [specialisation, setSpecialisation] = useState("");
  const [maxRate, setMaxRate] = useState("");

  const loadGuides = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (cityId) params.city_id = cityId;
      if (languages) params.languages = languages;
      if (specialisation) params.specialisation = specialisation;
      if (maxRate) params.max_day_rate = maxRate;

      const res = await api.matchGuides(params);
      setGuides(res.guides || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGuides();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cityId]); // Reload if city changes

  return (
    <div className="panel slide-up" style={{ padding: 24, marginTop: 24 }}>
      <div className="section-header" style={{ fontSize: 20, marginBottom: 16 }}>
        Find a Local Guide
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 12, marginBottom: 24, alignItems: "end" }}>
        <div>
          <label style={{ display: "block", fontSize: 12, color: "var(--dim)", marginBottom: 4 }}>Language (e.g. hi, en-IN)</label>
          <input
            type="text"
            className="input-field"
            style={{ width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--paper)", color: "var(--ink)" }}
            placeholder="hi,en-IN"
            value={languages}
            onChange={(e) => setLanguages(e.target.value)}
          />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 12, color: "var(--dim)", marginBottom: 4 }}>Specialty</label>
          <input
            type="text"
            className="input-field"
            style={{ width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--paper)", color: "var(--ink)" }}
            placeholder="food, history..."
            value={specialisation}
            onChange={(e) => setSpecialisation(e.target.value)}
          />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 12, color: "var(--dim)", marginBottom: 4 }}>Max Day Rate</label>
          <input
            type="number"
            className="input-field"
            style={{ width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--paper)", color: "var(--ink)" }}
            placeholder="₹"
            value={maxRate}
            onChange={(e) => setMaxRate(e.target.value)}
          />
        </div>
        <button className="btn-secondary" onClick={loadGuides} disabled={loading} style={{ padding: "8px 16px", height: "37px" }}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {error && <div style={{ color: "var(--stop)", fontSize: 13, marginBottom: 16 }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {guides.map((g) => (
          <div key={g.guide_id} style={{ border: "1px solid var(--line)", borderRadius: 8, padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
              <div>
                <div style={{ fontWeight: 600 }}>{g.display_name}</div>
                <div style={{ fontSize: 12, color: "var(--dim)" }}>{g.city_name} • ★ {g.rating} ({g.review_count})</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontWeight: 600, color: "var(--signal)" }}>₹{g.day_rate}</div>
                <div style={{ fontSize: 11, color: "var(--dim)" }}>per day</div>
              </div>
            </div>
            
            <div style={{ fontSize: 13, marginBottom: 12, lineHeight: 1.4 }}>
              {g.bio?.length > 100 ? g.bio.substring(0, 100) + "..." : g.bio}
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16 }}>
              {g.languages?.split(",").map((l) => (
                <span key={l} style={{ fontSize: 11, background: "var(--panel-sunken)", padding: "2px 8px", borderRadius: 12 }}>
                  {l.trim()}
                </span>
              ))}
              <span style={{ fontSize: 11, background: "rgba(0, 200, 100, 0.1)", color: "#00c864", padding: "2px 8px", borderRadius: 12 }}>
                {g.specialisation}
              </span>
            </div>
            
            <button
              className="btn-primary"
              style={{ width: "100%", padding: "8px" }}
              onClick={() => onSelectGuide && onSelectGuide(g)}
            >
              Select Guide
            </button>
          </div>
        ))}
        {!loading && guides.length === 0 && (
          <div className="dim" style={{ gridColumn: "1 / -1", textAlign: "center", padding: 32 }}>
            No guides found matching your criteria.
          </div>
        )}
      </div>
    </div>
  );
}
