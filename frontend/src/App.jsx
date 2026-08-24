import { useState } from "react";
import { api } from "./api/client.js";
import IntakeForm from "./components/IntakeForm.jsx";
import PlanTimeline from "./components/PlanTimeline.jsx";
import CostLedger from "./components/CostLedger.jsx";
import AgentTraceFeed from "./components/AgentTraceFeed.jsx";
import NegotiationGate from "./components/NegotiationGate.jsx";
import CartConfirm from "./components/CartConfirm.jsx";
import FlightPicker from "./components/FlightPicker.jsx";
import HotelPicker from "./components/HotelPicker.jsx";
import PlacesGrid from "./components/PlacesGrid.jsx";

// Step definitions for the progress bar
const STEPS = [
  { id: "intake", label: "Details" },
  { id: "flight", label: "Flight" },
  { id: "hotel", label: "Hotel" },
  { id: "review", label: "Review" },
];

function getStepIndex(status) {
  if (!status || status === "needs_input") return 0;
  if (status === "select_flight") return 1;
  if (status === "select_hotel") return 2;
  if (status === "awaiting_confirmation" || status === "confirmed") return 3;
  return 0;
}

function ProgressBar({ currentStep }) {
  return (
    <div className="progress-bar">
      {STEPS.map((step, i) => (
        <div key={step.id} className="progress-step" style={{ flex: i < STEPS.length - 1 ? 1 : "0 0 auto" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div
              className={`progress-step-dot ${
                i < currentStep ? "completed" : i === currentStep ? "active" : ""
              }`}
            >
              {i < currentStep ? "✓" : i + 1}
            </div>
            <div className={`progress-step-label ${i === currentStep ? "active" : ""}`}>
              {step.label}
            </div>
          </div>
          {i < STEPS.length - 1 && (
            <div
              className={`progress-step-line ${i < currentStep ? "completed" : ""}`}
              style={{ margin: "0 8px", marginBottom: 20 }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedFlight, setSelectedFlight] = useState(null);
  const [selectedHotel, setSelectedHotel] = useState(null);

  async function handleStart(payload) {
    setLoading(true);
    setError(null);
    try {
      const result = await api.startSession(payload);
      setSession(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectFlight() {
    if (selectedFlight === null) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.selectFlight(session.session_id, selectedFlight);
      setSession(result);
      setSelectedHotel(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectHotel() {
    if (selectedHotel === null) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.selectHotel(session.session_id, selectedHotel);
      setSession(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleNegotiate(choice) {
    setLoading(true);
    try {
      const result = await api.negotiate(session.session_id, { choice });
      setSession(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    setLoading(true);
    try {
      const result = await api.confirm(session.session_id);
      setSession(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setSession(null);
    setError(null);
    setSelectedFlight(null);
    setSelectedHotel(null);
  }

  const currentStep = session ? getStepIndex(session.status) : 0;
  const status = session?.status;

  return (
    <div style={{ minHeight: "100vh", padding: "32px 24px" }}>
      {/* Header */}
      <header style={{ maxWidth: 900, margin: "0 auto 28px" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <span style={{ fontFamily: "var(--font-display)", fontSize: 24, color: "var(--signal)" }}>◈</span>
          <span style={{ fontFamily: "var(--font-display)", fontSize: 24 }}>Waypoint</span>
          <span className="dim mono" style={{ fontSize: 12 }}>agentic travel concierge</span>
        </div>
      </header>

      <main style={{ maxWidth: 900, margin: "0 auto" }}>
        {/* Progress bar — only shown when a session is active */}
        {session && <ProgressBar currentStep={currentStep} />}

        {/* Error display */}
        {error && (
          <div className="panel slide-up" style={{ padding: 16, border: "1px solid var(--stop)", marginBottom: 20 }}>
            <div style={{ color: "var(--stop)", fontWeight: 600, marginBottom: 6 }}>Something went wrong</div>
            <div className="mono dim" style={{ fontSize: 13, marginBottom: 12 }}>{error}</div>
            <button onClick={() => setError(null)} className="btn-secondary" style={{ width: "auto", padding: "8px 16px", fontSize: 12 }}>
              Dismiss
            </button>
          </div>
        )}

        {/* ========== Step 1: Intake Form ========== */}
        {!session && <IntakeForm onSubmit={handleStart} loading={loading} />}

        {/* ========== Step 2: Flight Selection ========== */}
        {status === "select_flight" && (
          <div className="slide-up" style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
              <div>
                <FlightPicker
                  options={session.flight_options}
                  selectedIndex={selectedFlight}
                  onSelect={setSelectedFlight}
                  loading={loading}
                />

                {/* Confirm flight button */}
                {selectedFlight !== null && (
                  <div className="fade-in" style={{ marginTop: 16 }}>
                    <button onClick={handleSelectFlight} disabled={loading} className="btn-primary">
                      {loading ? "Processing…" : `Lock in ${session.flight_options[selectedFlight]?.airline} →`}
                    </button>
                  </div>
                )}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <CostLedger
                  runningTotal={
                    selectedFlight !== null
                      ? session.flight_options[selectedFlight]?.price_inr || 0
                      : 0
                  }
                  budgetCap={session.budget_cap}
                  chosenFlight={selectedFlight !== null ? session.flight_options[selectedFlight] : null}
                />
                <PlacesGrid places={session.place_options} destination={session.flight_options?.[0]?.destination} />
              </div>
            </div>
          </div>
        )}

        {/* ========== Step 3: Hotel Selection ========== */}
        {status === "select_hotel" && (
          <div className="slide-up" style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
            <div>
              <HotelPicker
                options={session.hotel_options}
                selectedIndex={selectedHotel}
                onSelect={setSelectedHotel}
                loading={loading}
              />

              {/* Confirm hotel button */}
              {selectedHotel !== null && (
                <div className="fade-in" style={{ marginTop: 16 }}>
                  <button onClick={handleSelectHotel} disabled={loading} className="btn-primary">
                    {loading ? "Processing…" : `Lock in ${session.hotel_options[selectedHotel]?.name} →`}
                  </button>
                </div>
              )}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <CostLedger
                runningTotal={
                  session.running_total +
                  (selectedHotel !== null ? session.hotel_options[selectedHotel]?.total_price_inr || 0 : 0)
                }
                budgetCap={session.budget_cap}
                chosenFlight={session.chosen_flight}
                chosenHotel={selectedHotel !== null ? session.hotel_options[selectedHotel] : null}
              />
              <PlacesGrid places={session.place_options} destination={session.chosen_flight?.destination} />
            </div>
          </div>
        )}

        {/* ========== Budget Negotiation ========== */}
        {status === "needs_input" && session.negotiation_options?.length > 0 && (
          <div className="slide-up" style={{ maxWidth: 560 }}>
            <NegotiationGate
              options={session.negotiation_options}
              onChoose={handleNegotiate}
              loading={loading}
            />
          </div>
        )}

        {/* ========== Clarifying Question ========== */}
        {status === "needs_input" && session.clarifying_question && !session.negotiation_options?.length && (
          <div className="panel slide-up" style={{ padding: 24, maxWidth: 560 }}>
            <div className="section-header" style={{ fontSize: 20 }}>One more thing…</div>
            <div style={{ fontSize: 14, lineHeight: 1.6, marginTop: 8 }}>
              {session.clarifying_question}
            </div>
          </div>
        )}

        {/* ========== Step 4: Cart / Confirmation ========== */}
        {(status === "awaiting_confirmation" || status === "confirmed") && session.cart && (
          <div className="slide-up" style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 20 }}>
            <CartConfirm
              cart={session.cart}
              chosenFlight={session.chosen_flight}
              chosenHotel={session.chosen_hotel}
              status={session.status}
              onConfirm={handleConfirm}
              loading={loading}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <CostLedger
                runningTotal={session.running_total}
                budgetCap={session.budget_cap}
                chosenFlight={session.chosen_flight}
                chosenHotel={session.chosen_hotel}
              />
              <PlacesGrid places={session.place_options} destination={session.chosen_flight?.destination} />
            </div>
          </div>
        )}

        {/* ========== Plan another trip ========== */}
        {(status === "confirmed" || status === "failed") && (
          <div className="fade-in" style={{ marginTop: 20 }}>
            <button onClick={handleReset} className="btn-secondary" style={{ width: "100%", maxWidth: 300 }}>
              Plan another trip
            </button>
          </div>
        )}

        {/* ========== Agent Trace (collapsible at bottom) ========== */}
        {session && session.trace?.length > 0 && (
          <details style={{ marginTop: 32 }}>
            <summary
              className="mono dim"
              style={{ cursor: "pointer", fontSize: 12, marginBottom: 12, userSelect: "none" }}
            >
              Agent trace log ({session.trace.length} entries) ▾
            </summary>
            <AgentTraceFeed trace={session.trace} />
          </details>
        )}
      </main>
    </div>
  );
}
