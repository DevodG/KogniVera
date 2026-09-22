import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "./api/client.js";
import { Money } from "./api/money.js";
import BudgetVessel from "./components/BudgetVessel.jsx";
import ComponentTimeline from "./components/ComponentTimeline.jsx";
import TraceFeed from "./components/TraceFeed.jsx";

// The flow: intake -> packages -> customize -> confirm.
// Server-authoritative: the client renders state, it never owns the total.

export default function App() {
  const [step, setStep] = useState("intake");
  const [session, setSession] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [guides, setGuides] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [traceOpen, setTraceOpen] = useState(true);

  const [profile, setProfile] = useState({
    languages: ["hi"],
    budget_band: "value",
    travel_style: "cultural",
    traveller_type: "family",
    pace: "balanced",
    budget_cap: "25000",
    currency: "INR",
  });

  // ---------------------------------------------------------------- intake
  const startSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.createSession(profile);
      setSession(res);
      setStep("packages");
      await loadRecommendations(res.session_id);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadRecommendations = async (id) => {
    const res = await api.recommend(id, 8);
    setRecommendations(res.results || []);
  };

  // ------------------------------------------------------------ customize
  const choosePackage = async (packageId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.choosePackage(session.session_id, packageId);
      setSession((prev) => ({ ...prev, state: res.state }));
      setStep("customize");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const onMutate = (res) => {
    if (res.state) setSession((prev) => ({ ...prev, state: res.state }));
  };

  const loadGuides = async () => {
    const res = await api.recommendGuides(session.session_id, "2026-09-24");
    setGuides(res.results || []);
  };

  const attachGuide = async (guideId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.attachGuide(session.session_id, guideId, "2026-09-24");
      if (!res.applied) setError(res.decision?.message || "guide blocked");
      onMutate(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const state = session?.state;

  return (
    <div style={{ position: "relative", zIndex: 1, minHeight: "100vh" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto", padding: "32px 24px 80px" }}>
        {/* Header */}
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
          <div>
            <div
              className="iridescent"
              style={{ fontFamily: "var(--font-display)", fontSize: 30, fontWeight: 600, letterSpacing: "-0.02em" }}
            >
              PackagePro
            </div>
            <div className="dim" style={{ fontSize: 12 }}>
              Dynamic tour packages · liquid itineraries · PS-04
            </div>
          </div>
          {state?.budget && (
            <div style={{ minWidth: 260 }}>
              <BudgetVessel
                cap={state.budget.cap}
                runningTotal={state.budget.running_total}
                pctUsed={state.budget.pct_used}
              />
            </div>
          )}
        </header>

        {error && (
          <div
            className="panel"
            style={{
              padding: 14,
              marginBottom: 20,
              borderColor: "rgba(226,102,92,0.45)",
              color: "var(--stop)",
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        {/* ---------------------------------------------------------- intake */}
        {step === "intake" && (
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 120, damping: 18, mass: 1.1 }}
            className="panel"
            style={{ padding: 28, maxWidth: 640 }}
          >
            <h1 style={{ fontFamily: "var(--font-display)", fontSize: 28, margin: "0 0 6px", fontWeight: 600 }}>
              Plan a trip that takes your shape
            </h1>
            <p className="dim" style={{ fontSize: 14, marginTop: 0 }}>
              Tell the concierge what you want. It ranks real packages, swaps components
              live, and never spends past the cap you set.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 20 }}>
              <Field label="Language (BCP-47)">
                <select
                  value={profile.languages[0]}
                  onChange={(e) => setProfile({ ...profile, languages: [e.target.value] })}
                >
                  <option value="hi">हिन्दी hi</option>
                  <option value="ta">தமிழ் ta</option>
                  <option value="te">తెలుగు te</option>
                  <option value="en-IN">English en-IN</option>
                </select>
              </Field>
              <Field label="Budget band">
                <select
                  value={profile.budget_band}
                  onChange={(e) => setProfile({ ...profile, budget_band: e.target.value })}
                >
                  {["shoestring", "value", "mid", "premium", "luxury"].map((b) => (
                    <option key={b}>{b}</option>
                  ))}
                </select>
              </Field>
              <Field label="Travel style">
                <select
                  value={profile.travel_style}
                  onChange={(e) => setProfile({ ...profile, travel_style: e.target.value })}
                >
                  {["budget", "comfort", "luxury", "adventure", "slow", "cultural", "wellness"].map((b) => (
                    <option key={b}>{b}</option>
                  ))}
                </select>
              </Field>
              <Field label="Pace">
                <select
                  value={profile.pace}
                  onChange={(e) => setProfile({ ...profile, pace: e.target.value })}
                >
                  {["relaxed", "balanced", "packed"].map((b) => (
                    <option key={b}>{b}</option>
                  ))}
                </select>
              </Field>
              <Field label="Budget cap (INR)">
                <input
                  type="text"
                  value={profile.budget_cap}
                  onChange={(e) => setProfile({ ...profile, budget_cap: e.target.value })}
                  className="money"
                />
              </Field>
            </div>
            <button
              className="btn btn-primary"
              style={{ marginTop: 22, width: "100%", padding: 14 }}
              disabled={loading}
              onClick={startSession}
            >
              {loading ? "Planning…" : "Find my packages"}
            </button>
          </motion.div>
        )}

        {/* -------------------------------------------------------- packages */}
        {step === "packages" && (
          <div>
            <SectionHeader
              eyebrow="Ranked for you"
              title="Recommended packages"
              sub={session?.cold_start?.cold_start ? session.cold_start.evidence : "Scored against your declared preferences."}
            />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
              {recommendations.map((r, i) => (
                <motion.div
                  key={r.package.package_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.07, type: "spring", stiffness: 170, damping: 22 }}
                  whileHover={{ y: -4, scale: 1.01 }}
                  className="panel"
                  style={{ padding: 18, cursor: "pointer" }}
                  onClick={() => choosePackage(r.package.package_id)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ fontWeight: 600, fontSize: 16 }}>{r.package.name}</div>
                    <ConfidenceBadge score={r.score.score} />
                  </div>
                  <div className="dim" style={{ fontSize: 12, marginTop: 4 }}>
                    {r.package.theme} · {r.package.duration_days} days · {r.package.tier}
                  </div>
                  <div className="money" style={{ fontSize: 19, fontWeight: 600, marginTop: 10 }}>
                    {fmtMoney(r.package.base_price)}
                  </div>
                  {r.score.reasons?.slice(0, 2).map((reason, idx) => (
                    <div key={idx} style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 4 }}>
                      · {reason.label}: {reason.detail}
                    </div>
                  ))}
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------ customize */}
        {step === "customize" && state && (
          <div>
            <SectionHeader
              eyebrow="Customize"
              title={state.package?.name}
              sub="Click any swappable stone to see ranked alternatives. Prices reprice live, in exact decimal."
            />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20, alignItems: "start" }}>
              <div className="panel" style={{ padding: 20 }}>
                <ComponentTimeline
                  sessionId={session.session_id}
                  components={state.components}
                  swaps={state.swaps}
                  state={state}
                  onMutate={onMutate}
                />
                <Breakdown breakdown={state.breakdown} />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <BudgetVessel
                  cap={state.budget.cap}
                  runningTotal={state.budget.running_total}
                  pctUsed={state.budget.pct_used}
                />
                <GuidePanel guides={guides} onLoad={loadGuides} onPick={attachGuide} chosen={state.chosen_guide} loading={loading} />
                <button
                  className="btn btn-ghost"
                  style={{ width: "100%" }}
                  onClick={() => setTraceOpen((v) => !v)}
                >
                  {traceOpen ? "Hide" : "Show"} agent trace
                </button>
                <TraceFeed trace={state.trace} open={traceOpen} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span
        className="mono"
        style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-3)" }}
      >
        {label}
      </span>
      {children}
    </label>
  );
}

function SectionHeader({ eyebrow, title, sub }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div
        className="mono"
        style={{ fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--aurora-1)" }}
      >
        {eyebrow}
      </div>
      <h2
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 26,
          margin: "4px 0 2px",
          fontWeight: 600,
          letterSpacing: "-0.01em",
        }}
      >
        {title}
      </h2>
      <div className="dim" style={{ fontSize: 13 }}>{sub}</div>
    </div>
  );
}

function ConfidenceBadge({ score }) {
  const n = Number(score);
  const band = n >= 0.75 ? "high" : n >= 0.5 ? "medium" : "low";
  const color = band === "high" ? "var(--go)" : band === "medium" ? "var(--aurora-3)" : "var(--stop)";
  return (
    <span
      className="mono"
      style={{
        fontSize: 10,
        padding: "3px 8px",
        borderRadius: 999,
        border: `1px solid ${color}`,
        color,
        whiteSpace: "nowrap",
      }}
    >
      {n.toFixed(2)} {band}
    </span>
  );
}

function fmtMoney(pair) {
  if (!pair) return "";
  return new Money(pair.amount, pair.currency).format();
}

function Breakdown({ breakdown }) {
  if (!breakdown) return null;
  return (
    <div
      className="panel"
      style={{
        marginTop: 20,
        padding: 16,
        background: "rgba(255,255,255,0.02)",
      }}
    >
      <div
        className="mono"
        style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-3)", marginBottom: 10 }}
      >
        Reprice breakdown
      </div>
      <Row label="Base price" value={fmtMoney(breakdown.base_price)} />
      <Row label="Included components" value={fmtMoney(breakdown.included_delta)} />
      {Number(breakdown.optional_added?.amount || 0) > 0 && (
        <Row label="Optional add-ons" value={fmtMoney(breakdown.optional_added)} />
      )}
      <div
        style={{
          borderTop: "1px solid var(--hairline)",
          marginTop: 8,
          paddingTop: 8,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontWeight: 600 }}>Total</span>
        <span className="money" style={{ fontWeight: 700, fontSize: 17, color: "var(--aurora-1)" }}>
          {fmtMoney(breakdown.total)}
        </span>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "3px 0" }}>
      <span className="dim">{label}</span>
      <span className="money">{value}</span>
    </div>
  );
}

function GuidePanel({ guides, onLoad, onPick, chosen, loading }) {
  return (
    <div className="panel" style={{ padding: 18 }}>
      <div
        className="mono"
        style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-3)" }}
      >
        Guides · free 2026-09-24
      </div>
      {guides.length === 0 ? (
        <button
          className="btn btn-ghost"
          style={{ width: "100%", marginTop: 12 }}
          onClick={onLoad}
        >
          Match guides
        </button>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>
          {guides.map((g, i) => (
            <motion.div
              key={g.guide.guide_id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
              style={{
                padding: 10,
                borderRadius: "var(--r-md)",
                background: chosen?.guide_id === g.guide.guide_id ? "rgba(94,234,212,0.08)" : "var(--surface)",
                border: `1px solid ${chosen?.guide_id === g.guide.guide_id ? "rgba(94,234,212,0.35)" : "var(--hairline)"}`,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{g.guide.display_name}</div>
                  <div className="dim" style={{ fontSize: 11 }}>
                    {g.guide.languages?.join(", ")} · {g.guide.specialisation}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="money" style={{ fontSize: 13 }}>
                    {fmtMoney(g.guide.day_rate)}
                  </div>
                  <button
                    className="btn btn-primary"
                    style={{ padding: "4px 10px", fontSize: 11, marginTop: 4 }}
                    disabled={loading}
                    onClick={() => onPick(g.guide.guide_id)}
                  >
                    {chosen?.guide_id === g.guide.guide_id ? "Added" : "Add"}
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
