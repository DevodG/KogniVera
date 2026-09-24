import { useEffect, useState } from "react";
import { formatMoney, money } from "../money.js";
import * as api from "../api.js";

const STEPS = [
  "Find packages that match your city, dates, language, group size, and budget.",
  "Explain the best eligible options.",
  "Let you customize itinerary components and choose a guide.",
  "Check your budget after every change.",
  "Never book anything until you approve.",
];

/**
 * Preferences screen. Collects the traveller's constraints, then shows the
 * agent's plan *before* any query runs.
 *
 * When the user selects a city, we fetch available packages from
 * PackagePro.tour_packages and show duration/theme/price hints so the user
 * can pick a date range that actually matches an existing package.
 */
export default function Preferences({ cities, languages, onSubmit, busy, health }) {
  const [cityId, setCityId] = useState("");
  const [startDate, setStartDate] = useState("2026-09-05");
  const [endDate, setEndDate] = useState("2026-09-08");
  const [travelers, setTravelers] = useState(2);
  const [budget, setBudget] = useState("35000.00");
  const [lang, setLang] = useState("hi");
  const [secondLang, setSecondLang] = useState("en-IN");
  const [theme, setTheme] = useState("heritage");
  const [goal, setGoal] = useState("A relaxed heritage short break with local food.");
  const [showPlan, setShowPlan] = useState(false);
  const [error, setError] = useState("");

  // City-aware package hints
  const [cityPackages, setCityPackages] = useState([]);
  const [loadingHints, setLoadingHints] = useState(false);

  // When a city is selected, fetch available packages for that city
  useEffect(() => {
    if (!cityId) {
      setCityPackages([]);
      return;
    }
    setLoadingHints(true);
    api
      .getCityPackages(cityId)
      .then((pkgs) => {
        setCityPackages(pkgs);

        // Auto-adjust end date to match the first available package duration
        if (pkgs.length > 0) {
          const durations = [...new Set(pkgs.map((p) => p.duration_days))].sort((a, b) => a - b);
          const firstDuration = durations[0];
          const start = new Date(startDate);
          const newEnd = new Date(start);
          newEnd.setDate(newEnd.getDate() + firstDuration - 1);
          setEndDate(newEnd.toISOString().slice(0, 10));
        }
      })
      .catch(() => setCityPackages([]))
      .finally(() => setLoadingHints(false));
  }, [cityId]); // eslint-disable-line react-hooks/exhaustive-deps

  const citiesWithPackages = cities;

  // Compute trip days for display
  const tripDays = (() => {
    try {
      const s = new Date(startDate);
      const e = new Date(endDate);
      return Math.round((e - s) / 86400000) + 1;
    } catch {
      return 0;
    }
  })();

  // Check if current trip duration matches any available package
  const matchingPackages = cityPackages.filter((p) => p.duration_days === tripDays);
  const availableDurations = [...new Set(cityPackages.map((p) => p.duration_days))].sort((a, b) => a - b);

  function setDurationFromDays(days) {
    const start = new Date(startDate);
    const newEnd = new Date(start);
    newEnd.setDate(newEnd.getDate() + days - 1);
    setEndDate(newEnd.toISOString().slice(0, 10));
  }

  function applyPreset(name) {
    setError("");
    if (name === "tamil") {
      const city = cities.find((c) => c.name.toLowerCase().includes("pondicherry")) || cities[0];
      if (city) setCityId(city.city_id);
      setStartDate("2026-09-05");
      setEndDate("2026-09-10");
      setTravelers(2);
      setBudget("34000.00");
      setLang("ta");
      setSecondLang("en-IN");
      setTheme("heritage");
      setGoal("A relaxed Tamil heritage trip with local food.");
    } else if (name === "hindi") {
      const city = cities.find((c) => c.name.toLowerCase().includes("jaipur")) || cities[0];
      if (city) setCityId(city.city_id);
      setStartDate("2026-09-05");
      setEndDate("2026-09-08");
      setTravelers(2);
      setBudget("35000.00");
      setLang("hi");
      setSecondLang("en-IN");
      setTheme("heritage");
      setGoal("A relaxed heritage short break with local food.");
    } else if (name === "telugu") {
      const city = cities.find((c) => c.name.toLowerCase().includes("tirupati")) || cities[0];
      if (city) setCityId(city.city_id);
      setStartDate("2026-09-05");
      setEndDate("2026-09-08");
      setTravelers(2);
      setBudget("30000.00");
      setLang("te");
      setSecondLang("en-IN");
      setTheme("pilgrimage");
      setGoal("Spiritual temple tour with comfortable arrangements.");
    }
  }

  function submit(e) {
    e.preventDefault();
    setError("");
    if (!cityId) {
      setError("Choose a destination city.");
      return;
    }
    if (endDate < startDate) {
      setError("End date must not be before the start date.");
      return;
    }
    try {
      money(budget);
    } catch {
      setError("Budget must be a plain amount, e.g. 35000.00");
      return;
    }
    if (cityPackages.length > 0 && matchingPackages.length === 0) {
      setError(
        `No packages exist for a ${tripDays}-day trip to this city. ` +
          `Available durations: ${availableDurations.join(", ")} days. ` +
          `Click a duration chip below to adjust.`,
      );
      return;
    }
    const langs = [lang];
    if (secondLang && secondLang !== lang) langs.push(secondLang);
    onSubmit({
      city_id: cityId,
      start_date: startDate,
      end_date: endDate,
      travelers: Number(travelers),
      budget: { amount: money(budget).toDecimalPlaces(2).toString(), currency: "INR" },
      preferred_languages: langs,
      theme: theme || null,
      goal: goal || null,
    });
  }

  return (
    <div className="grid grid--two">
      <form className="card" onSubmit={submit}>
        <h2 className="card__title">1 · Preferences</h2>
        <p className="card__sub">
          Destination, dates, travellers, INR cap, preferred language, theme and goal.
          Only INR packages are offered in the MVP.
        </p>

        {/* Quick Demo Presets */}
        <div className="field" style={{ marginBottom: 16 }}>
          <label style={{ color: "var(--amber)", fontWeight: 600 }}>Quick Demo Presets</label>
          <div className="row" style={{ gap: 8, flexWrap: "wrap", marginTop: 4 }}>
            <button
              type="button"
              className="btn btn--ghost tiny"
              onClick={() => applyPreset("tamil")}
              title="6-day Pondicherry tour in Tamil + English, ₹34,000 cap"
            >
              🌊 Tamil Heritage (Pondicherry · 6d)
            </button>
            <button
              type="button"
              className="btn btn--ghost tiny"
              onClick={() => applyPreset("hindi")}
              title="4-day Jaipur tour in Hindi + English, ₹35,000 cap"
            >
              🏰 Hindi Cultural (Jaipur · 4d)
            </button>
            <button
              type="button"
              className="btn btn--ghost tiny"
              onClick={() => applyPreset("telugu")}
              title="4-day Tirupati tour in Telugu + English, ₹30,000 cap"
            >
              🕉️ Telugu Spiritual (Tirupati · 4d)
            </button>
          </div>
        </div>

        <div className="field">
          <label htmlFor="city">Destination city (real PackagePro city)</label>
          <select id="city" value={cityId} onChange={(e) => setCityId(e.target.value)} required>
            <option value="">Select a city…</option>
            {citiesWithPackages.map((c) => (
              <option key={c.city_id} value={c.city_id}>
                {c.name} · {c.state} ({c.country_code}) · {c.city_id}
              </option>
            ))}
          </select>
        </div>

        {/* Duration hints from PackagePro */}
        {cityId && cityPackages.length > 0 && (
          <div className="field hint-bar">
            <label>
              Available packages{" "}
              <span className="badge badge--source">PackagePro.tour_packages</span>
            </label>
            <div className="hint-chips">
              {cityPackages.map((p) => (
                <button
                  key={p.package_id}
                  type="button"
                  className={`hint-chip ${p.duration_days === tripDays ? "hint-chip--active" : ""}`}
                  onClick={() => setDurationFromDays(p.duration_days)}
                  title={`${p.name}\n${formatMoney(p.included_total, p.currency)} included total`}
                >
                  <span className="hint-chip__dur">{p.duration_days}d</span>
                  <span className="hint-chip__theme">{p.theme}</span>
                  <span className="hint-chip__price">{formatMoney(p.included_total, p.currency)}</span>
                </button>
              ))}
            </div>
            {matchingPackages.length === 0 && (
              <p className="tiny" style={{ color: "var(--amber)", marginTop: 6 }}>
                ⚠ No {tripDays}-day package for this city. Pick a duration above:{" "}
                {availableDurations.map((d) => `${d}d`).join(", ")}
              </p>
            )}
            {matchingPackages.length > 0 && (
              <p className="tiny" style={{ color: "var(--green)", marginTop: 6 }}>
                ✓ {matchingPackages.length} package(s) match your {tripDays}-day trip
              </p>
            )}
          </div>
        )}

        {cityId && loadingHints && (
          <p className="tiny muted">Loading packages from PackagePro…</p>
        )}

        <div className="form-row">
          <div className="field">
            <label htmlFor="start">Start date</label>
            <input
              id="start"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="end">
              End date{" "}
              <span className="tiny muted">({tripDays} day{tripDays !== 1 ? "s" : ""} trip)</span>
            </label>
            <input
              id="end"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="form-row">
          <div className="field">
            <label htmlFor="travelers">Travellers</label>
            <input
              id="travelers"
              type="number"
              min="1"
              max="50"
              value={travelers}
              onChange={(e) => setTravelers(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="budget">Budget cap (INR)</label>
            <input
              id="budget"
              inputMode="decimal"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="form-row">
          <div className="field">
            <label htmlFor="lang">Preferred language (BCP-47)</label>
            <select id="lang" value={lang} onChange={(e) => setLang(e.target.value)}>
              {languages.map((l) => (
                <option key={l.bcp47} value={l.bcp47}>
                  {l.english_name} {l.native_name && l.native_name !== l.english_name ? `(${l.native_name})` : ""} — {l.bcp47}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="lang2">Second language</label>
            <select id="lang2" value={secondLang} onChange={(e) => setSecondLang(e.target.value)}>
              <option value="">none</option>
              {languages.map((l) => (
                <option key={l.bcp47} value={l.bcp47}>
                  {l.english_name} {l.native_name && l.native_name !== l.english_name ? `(${l.native_name})` : ""} — {l.bcp47}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="field">
          <label htmlFor="theme">Theme</label>
          <select id="theme" value={theme} onChange={(e) => setTheme(e.target.value)}>
            <option value="">any</option>
            <option value="heritage">heritage</option>
            <option value="pilgrimage">pilgrimage</option>
            <option value="food_trail">food_trail</option>
            <option value="adventure">adventure</option>
            <option value="wildlife">wildlife</option>
            <option value="wellness">wellness</option>
            <option value="honeymoon">honeymoon</option>
            <option value="family">family</option>
          </select>
        </div>

        <div className="field">
          <label htmlFor="goal">Free-text goal</label>
          <textarea
            id="goal"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g. Relaxed Tamil heritage trip with local food"
          />
        </div>

        {error ? (
          <p className="tiny" style={{ color: "var(--red)" }}>
            {error}
          </p>
        ) : null}

        <div className="row">
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {busy ? "Querying PackagePro…" : "Show me the plan"}
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setShowPlan((s) => !s)}
          >
            {showPlan ? "Hide the plan" : "What will the agent do?"}
          </button>
        </div>
      </form>

      <div className="stack">
        {showPlan ? (
          <div className="card">
            <h2 className="card__title">2 · The plan, before any data is queried</h2>
            <p className="card__sub">
              Waypoint publishes its intent first. You see the whole approach before a single
              row is read.
            </p>
            <ol className="pkg__reasons" style={{ paddingLeft: 19 }}>
              {STEPS.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </div>
        ) : (
          <div className="card">
            <h2 className="card__title">Transparency contract</h2>
            <ul className="pkg__reasons">
              <li>Every recommendation names the PackagePro table it came from.</li>
              <li>Every price change shows the exact delta, in Decimal.</li>
              <li>The server owns the budget guard; the browser is not trusted.</li>
              <li>Nothing is booked without your explicit click.</li>
            </ul>
          </div>
        )}

        {health ? (
          <div className="card">
            <h2 className="card__title">Data sources</h2>
            <table className="ledger">
              <tbody>
                {Object.entries(health.rows).map(([table, n]) => (
                  <tr key={table}>
                    <td>PackagePro.{table}</td>
                    <td className="num">{n.toLocaleString()} rows</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="tiny muted" style={{ marginTop: 10 }}>
              Connected read-only to <code>{health.packagepro_path.split("/").slice(-3).join("/")}</code>.
              AI key: <strong>{health.ai_key_configured ? "configured" : "not required"}</strong>.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
