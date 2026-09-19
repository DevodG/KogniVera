import { useState } from "react";
import { useT } from "../i18n.js";

const field = {
  width: "100%",
  padding: "10px 12px",
  background: "var(--panel-raised)",
  border: "1px solid var(--line)",
  borderRadius: 8,
  color: "var(--paper)",
  fontFamily: "var(--font-mono)",
  fontSize: 14,
};

const label = {
  display: "block",
  fontSize: 12,
  color: "var(--dim)",
  marginBottom: 6,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
};

export default function IntakeForm({ onSubmit, loading }) {
  const { lang, t } = useT();
  const [form, setForm] = useState({
    goal: "3-day Goa trip, relaxed pace, love beaches and seafood",
    origin: "DEL",
    destination: "GOI",
    depart_date: "2026-12-05",
    return_date: "2026-12-08",
    travelers: 1,
    budget_cap: 12000,
    currency: "INR",
  });
  
  const [error, setError] = useState(null);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const handleSubmit = () => {
    setError(null);
    const travelers = Number(form.travelers);
    const cap = Number(form.budget_cap);
    
    // FIX B11: Client-side validation
    if (travelers < 1 || isNaN(travelers)) {
      setError("Travelers must be at least 1.");
      return;
    }
    if (cap <= 0 || isNaN(cap)) {
      setError("Budget cap must be greater than 0.");
      return;
    }
    if (!form.origin || !form.destination || !form.depart_date) {
      setError("Origin, destination, and depart date are required.");
      return;
    }
    if (form.return_date && form.depart_date > form.return_date) {
      setError("Return date cannot be before depart date.");
      return;
    }
    
    
    onSubmit({ ...form, travelers, budget_cap: cap, preferred_languages: lang });
  };

  return (
    <div className="panel" style={{ padding: 28, maxWidth: 560 }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 26, marginBottom: 4 }}>
        {t("form.goal")}
      </div>
      <div className="dim" style={{ fontSize: 14, marginBottom: 22, lineHeight: 1.5 }}>
        {t("form.goal_desc")}
      </div>

      <label style={label}>{t("form.trip_goal")}</label>
      <textarea
        style={{ ...field, minHeight: 60, marginBottom: 16, fontFamily: "var(--font-body)" }}
        value={form.goal}
        onChange={set("goal")}
      />

      <div className="intake-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <div>
          <label style={label}>{t("form.origin")}</label>
          <input style={field} value={form.origin} onChange={set("origin")} />
        </div>
        <div>
          <label style={label}>{t("form.destination")}</label>
          <input style={field} value={form.destination} onChange={set("destination")} />
        </div>
        <div>
          <label style={label}>{t("form.depart")}</label>
          <input type="date" style={field} value={form.depart_date} onChange={set("depart_date")} />
        </div>
        <div>
          <label style={label}>{t("form.return")}</label>
          <input type="date" style={field} value={form.return_date} onChange={set("return_date")} />
        </div>
        <div>
          <label style={label}>{t("form.travelers")}</label>
          <input type="number" min="1" style={field} value={form.travelers} onChange={set("travelers")} />
        </div>
        <div>
          <label style={label}>{t("form.budget")}</label>
          <input type="number" style={field} value={form.budget_cap} onChange={set("budget_cap")} />
        </div>
      </div>

      {error && (
        <div style={{ color: "var(--stop)", fontSize: 13, marginBottom: 16 }}>
          {error}
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading}
        style={{
          width: "100%",
          padding: "12px",
          background: "var(--signal)",
          color: "var(--ink)",
          border: "none",
          borderRadius: 8,
          fontWeight: 600,
          fontSize: 14,
        }}
      >
        {loading ? t("form.planning") : t("form.submit")}
      </button>
    </div>
  );
}
