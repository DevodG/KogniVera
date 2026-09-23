import { useEffect, useState } from "react";
import * as api from "./api.js";
import { formatMoney } from "./money.js";
import Preferences from "./components/Preferences.jsx";
import PackageCard from "./components/PackageCard.jsx";
import Itinerary from "./components/Itinerary.jsx";
import GuideCard from "./components/GuideCard.jsx";
import TrustReceipt from "./components/TrustReceipt.jsx";
import TraceTimeline, { BudgetBar, Ledger } from "./components/TraceTimeline.jsx";
import NegotiateModal from "./components/NegotiateModal.jsx";
import FlightHotelSelector from "./components/FlightHotelSelector.jsx";

const STAGE = {
  prefs: "prefs",
  recommend: "recommend",
  customizing: "customizing",
  guides: "guides",
  receipt: "receipt",
  done: "done",
};

const STEPPER = [
  { key: STAGE.prefs, label: "Preferences" },
  { key: STAGE.recommend, label: "Agent plan" },
  { key: STAGE.customizing, label: "Itinerary" },
  { key: STAGE.guides, label: "Guide" },
  { key: STAGE.receipt, label: "Trust Receipt" },
];

export default function App() {
  const [cities, setCities] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [health, setHealth] = useState(null);
  const [stage, setStage] = useState(STAGE.prefs);
  const [busy, setBusy] = useState(false);
  const [session, setSession] = useState(null);
  const [itinerary, setItinerary] = useState(null);
  const [guides, setGuides] = useState([]);
  const [receipt, setReceipt] = useState(null);
  const [negotiation, setNegotiation] = useState(null);
  const [banner, setBanner] = useState("");
  const [error, setError] = useState("");
  const [viewPackage, setViewPackage] = useState(null);

  useEffect(() => {
    api
      .getHealth()
      .then(setHealth)
      .catch(() => setError("Backend unreachable on /api/health"));
    api.getCities().then(setCities).catch(() => setCities([]));
    api.getLanguages().then(setLanguages).catch(() => setLanguages([]));

    const params = new URLSearchParams(window.location.search);
    const sid = params.get("session") || localStorage.getItem("waypoint_session_id");
    if (sid) {
      restoreSession(sid);
    }
  }, []);

  async function restoreSession(sid) {
    const s = await run(() => api.getSession(sid), "Could not restore previous session");
    if (!s) {
      localStorage.removeItem("waypoint_session_id");
      return;
    }
    setSession(s);
    localStorage.setItem("waypoint_session_id", s.session_id);
    const url = new URL(window.location);
    url.searchParams.set("session", s.session_id);
    window.history.replaceState({}, "", url);

    if (s.selected_package_id) {
      const it = await run(() => api.getItinerary(s.session_id), "Could not load itinerary");
      if (it) {
        setItinerary(it);
        const g = await run(() => api.getGuides(s.session_id), "");
        if (g) setGuides(g.guides);

        if (s.selected_guide_id) {
          const rc = await run(() => api.getTrustReceipt(s.session_id), "");
          if (rc) setReceipt(rc);
          setStage(s.state === "confirmed" ? STAGE.done : STAGE.receipt);
        } else {
          setStage(STAGE.customizing);
        }
      } else {
        setStage(STAGE.recommend);
      }
    } else if (s.recommendations && s.recommendations.length) {
      setStage(STAGE.recommend);
    } else {
      setStage(STAGE.prefs);
    }
  }

  function startNewTrip() {
    localStorage.removeItem("waypoint_session_id");
    const url = new URL(window.location);
    url.searchParams.delete("session");
    window.history.replaceState({}, "", url);
    setSession(null);
    setItinerary(null);
    setGuides([]);
    setReceipt(null);
    setNegotiation(null);
    setBanner("");
    setError("");
    setViewPackage(null);
    setStage(STAGE.prefs);
  }

  function guardError(e, fallback) {
    const msg = e?.message || fallback;
    setError(msg);
    if (e?.body?.budget) {
      setNegotiation(e.body.budget);
    }
    setBusy(false);
  }

  async function run(fn, fallback) {
    setBusy(true);
    setError("");
    try {
      const out = await fn();
      setBusy(false);
      return out;
    } catch (e) {
      guardError(e, fallback);
      return null;
    }
  }

  async function handleRecommend(payload) {
    const view = await run(() => api.recommend(payload), "Recommendation failed");
    if (!view) return;
    setSession(view);
    localStorage.setItem("waypoint_session_id", view.session_id);
    const url = new URL(window.location);
    url.searchParams.set("session", view.session_id);
    window.history.replaceState({}, "", url);
    setStage(STAGE.recommend);
    setBanner(
      view.recommendations.length
        ? `Found ${view.recommendations.length} eligible package(s) for ${payload.city_id}.`
        : "No package matched every constraint. Loosen a filter and try again.",
    );
  }

  async function handleChoose(packageId) {
    const view = await run(
      () => api.selectPackage(session.session_id, packageId),
      "Package selection failed",
    );
    if (!view) return;
    setSession(view);
    const it = await run(
      () => api.getItinerary(view.session_id),
      "Itinerary load failed",
    );
    if (!it) return;
    setItinerary(it);
    setStage(STAGE.customizing);
    const g = await run(() => api.getGuides(view.session_id), "Guide match failed");
    if (g) setGuides(g.guides);
    setReceipt(null);
    setBanner(`Package chosen at ${formatMoney(it.current_total, it.currency)}. No booking made.`);
  }

  async function loadItinerary(sid) {
    const it = await run(() => api.getItinerary(sid), "Itinerary load failed");
    if (it) setItinerary(it);
    return it;
  }

  async function handleSwap(componentId, replacementId) {
    const view = await run(
      () => api.swapComponent(session.session_id, componentId, replacementId),
      "Swap failed",
    );
    if (!view) return;
    setSession(view);
    if (view.swap_blocked) {
      setNegotiation(view.budget);
      setBanner("The Budget Guard blocked that swap.");
    } else {
      setBanner(`Swap applied. Total now ${formatMoney(view.budget.total, view.budget.currency)}.`);
    }
    await loadItinerary(session.session_id);
  }

  async function handleSelectFlight(flight) {
    if (!session) return;
    const view = await run(
      () => api.selectFlight(session.session_id, flight),
      "Flight selection failed",
    );
    if (!view) return;
    setSession(view);
    if (view.swap_blocked) {
      setNegotiation(view.budget);
      setBanner("The Budget Guard blocked that flight (exceeds budget cap).");
    } else {
      setBanner(
        flight
          ? `Flight selected: ${flight.airline} ${flight.flight_number}. Total now ${formatMoney(
              view.budget.total,
              view.budget.currency,
            )}.`
          : "Flight removed.",
      );
    }
    await loadItinerary(session.session_id);
  }

  async function handleSelectHotel(hotel) {
    if (!session) return;
    const view = await run(
      () => api.selectHotel(session.session_id, hotel),
      "Hotel selection failed",
    );
    if (!view) return;
    setSession(view);
    if (view.swap_blocked) {
      setNegotiation(view.budget);
      setBanner("The Budget Guard blocked that hotel (exceeds budget cap).");
    } else {
      setBanner(
        hotel
          ? `Hotel selected: ${hotel.hotel_name}. Total now ${formatMoney(
              view.budget.total,
              view.budget.currency,
            )}.`
          : "Hotel removed.",
      );
    }
    await loadItinerary(session.session_id);
  }

  async function handleSelectGuide(guideId, service) {
    const view = await run(
      () => api.selectGuide(session.session_id, guideId, service),
      "Guide selection failed",
    );
    if (!view) return;
    setSession(view);
    if (view.guide_blocked) {
      setNegotiation(view.budget);
      setBanner("The Budget Guard blocked that guide.");
      const g = await run(() => api.getGuides(session.session_id), "");
      if (g) setGuides(g.guides);
      return;
    }
    setStage(STAGE.receipt);
    const it = await loadItinerary(session.session_id);
    const rc = await run(() => api.getTrustReceipt(session.session_id), "Receipt failed");
    if (rc) setReceipt(rc);
    setBanner(
      `Guide added. Total ${formatMoney(view.budget.total, view.budget.currency)}; ${formatMoney(
        view.budget.remaining,
        view.budget.currency,
      )} remains.`,
    );
  }

  async function handleNegotiate(option, extra) {
    const view = await run(
      () => api.negotiate(session.session_id, option, extra),
      "Negotiation failed",
    );
    if (!view) return;
    setSession(view);
    setNegotiation(null);
    setBanner(`Negotiation applied: ${option.replace(/_/g, " ")}.`);
    const g = await run(() => api.getGuides(session.session_id), "");
    if (g) setGuides(g.guides);
  }

  async function handleConfirm() {
    const result = await run(() => api.confirm(session.session_id), "Confirmation failed");
    if (!result) return;
    const rc = await run(() => api.getTrustReceipt(session.session_id), "");
    if (rc) setReceipt(rc);
    setStage(STAGE.done);
    setBanner(`Mock confirmation ${result.confirmation.booking_reference} recorded. Nothing booked.`);
  }

  function viewPackageItinerary(pkg) {
    setViewPackage(pkg);
  }

  function canNavigateTo(key) {
    if (key === STAGE.prefs) return true;
    if (key === STAGE.recommend) return Boolean(session);
    if (key === STAGE.customizing) return Boolean(itinerary);
    if (key === STAGE.guides) return Boolean(itinerary);
    if (key === STAGE.receipt) return Boolean(receipt);
    return false;
  }

  function handleStepClick(targetStage) {
    if (!canNavigateTo(targetStage)) {
      if (targetStage === STAGE.recommend) {
        setBanner("Submit your preferences in Step 1 to generate recommendations.");
      } else if (targetStage === STAGE.customizing) {
        setBanner("Choose a package in Step 2 first to view and customize its itinerary.");
      } else if (targetStage === STAGE.guides) {
        setBanner("Choose a package in Step 2 first before selecting guides.");
      } else if (targetStage === STAGE.receipt) {
        setBanner("Select a guide to proceed to the Trust Receipt.");
      }
      return;
    }
    if (targetStage === STAGE.guides && !guides.length && session) {
      api.getGuides(session.session_id).then((g) => {
        if (g) setGuides(g.guides);
      });
    }
    setStage(targetStage);
    setBanner("");
    setError("");
  }

  return (
    <div className="app">
      <header className="app__header">
        <div className="brand">
          <div className="brand__mark" aria-hidden="true">
            W
          </div>
          <div>
            <h1>Waypoint</h1>
            <p className="brand__tag">
              Transparent AI-assisted travel package customizer · Kognivera PS-04
            </p>
          </div>
        </div>
        <div className="header__pulse" style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {session ? (
            <span
              className="badge badge--source"
              style={{ fontFamily: "var(--mono)", fontSize: 11 }}
              title="Resumable Session ID (persisted across refresh)"
            >
              {session.session_id}
            </span>
          ) : null}
          <span className={busy ? "pulse-dot pulse-dot--live" : "pulse-dot"} />
          {health ? (
            <span>
              {health.packagepro_db} · {health.rows.tour_packages} packages ·{" "}
              {health.rows.tour_guides} guides
            </span>
          ) : (
            <span>connecting…</span>
          )}
          {session ? (
            <button
              type="button"
              className="btn btn--ghost"
              style={{ fontSize: 11, padding: "3px 8px", marginLeft: 6 }}
              onClick={startNewTrip}
              title="Reset session and start a new trip"
            >
              + New Trip
            </button>
          ) : null}
        </div>
      </header>

      <nav className="stepper" aria-label="Flow progress">
        {STEPPER.map((s, i) => {
          const unlocked = canNavigateTo(s.key);
          const isCurrent = i === currentStep(stage);
          const isDone = i < currentStep(stage);
          return (
            <button
              key={s.key}
              type="button"
              className={`stepper__item ${
                isDone ? "stepper__item--done" : isCurrent ? "stepper__item--active" : ""
              } ${unlocked ? "stepper__item--clickable" : ""}`}
              onClick={() => handleStepClick(s.key)}
              title={
                unlocked
                  ? `Go to Step ${i + 1} (${s.label})`
                  : `Step ${i + 1}: ${s.label} (complete earlier steps first)`
              }
            >
              <span className="stepper__n">
                {isDone ? "DONE" : isCurrent ? "NOW" : `STEP ${i + 1}`}
              </span>
              <span>{s.label}</span>
            </button>
          );
        })}
      </nav>

      {banner ? <div className="alert alert--info">{banner}</div> : null}
      {error ? (
        <div className="alert alert--blocked">
          <h3>Something needs attention</h3>
          <p>{error}</p>
        </div>
      ) : null}

      {stage === STAGE.prefs ? (
        <Preferences
          cities={cities}
          languages={languages}
          onSubmit={handleRecommend}
          busy={busy}
          health={health}
        />
      ) : null}

      {stage === STAGE.recommend && session ? (
        <div className="grid grid--two">
          <div>
            <div className="card">
              <h2 className="card__title">
                Real package recommendations
                <span className="badge badge--source">PackagePro.tour_packages</span>
              </h2>
              <p className="card__sub">
                Eligible on city, language, duration, group size and INR budget. Ranked
                deterministically: language +40, duration +25, theme +20, within budget +15.
              </p>
            </div>
            {session.ai_explanation ? (
              <div
                className="card"
                style={{
                  borderLeft: "3px solid var(--accent)",
                  background: "rgba(99, 102, 241, 0.05)",
                  marginBottom: 14,
                }}
              >
                <h3
                  style={{
                    fontSize: 13.5,
                    color: "var(--accent)",
                    marginBottom: 6,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  <span>✦</span> Agent Plan Explanation
                  <span className="badge badge--source">
                    {session.ai_explanation.includes("NIM") ? "NVIDIA NIM" : "Waypoint AI"}
                  </span>
                </h3>
                <p
                  style={{
                    fontSize: 12.5,
                    lineHeight: 1.5,
                    whiteSpace: "pre-wrap",
                    color: "var(--text-light)",
                  }}
                >
                  {session.ai_explanation}
                </p>
              </div>
            ) : null}
            {session.recommendations.length ? (
              session.recommendations.map((pkg) => (
                <PackageCard
                  key={pkg.package_id}
                  pkg={pkg}
                  rank={pkg.rank}
                  chosen={session.selected_package_id === pkg.package_id}
                  onChoose={handleChoose}
                  onView={viewPackageItinerary}
                  busy={busy}
                />
              ))
            ) : (
              <div className="card">
                <h3 style={{ color: "var(--amber)", marginBottom: 8 }}>No packages matched</h3>
                <p className="card__sub">
                  No package in <strong>PackagePro.tour_packages</strong> satisfied every
                  constraint (city + exact duration + language + group size + INR currency).
                </p>
                <ul className="pkg__reasons" style={{ marginBottom: 12 }}>
                  <li>Try a different date range — the package duration must <strong>exactly</strong> match your trip days</li>
                  <li>Try a different language or set it to English (en-IN) which most packages offer</li>
                  <li>Increase the budget cap — some packages are above ₹20,000</li>
                </ul>
                <button
                  className="btn btn--primary"
                  onClick={() => { setStage(STAGE.prefs); setBanner(""); setError(""); }}
                >
                  ← Go back and adjust
                </button>
              </div>
            )}
          </div>
          <div className="stack">
            <BudgetBar budget={session.budget} />
            <TraceTimeline events={session.trace} />
            {session.audit && session.audit.length ? (
              <Ledger
                lines={session.audit.map((a) => ({
                  title: `${a.action} · ${a.actor}`,
                  source_table: "Waypoint audit_log",
                  amount: a.amount || "0.00",
                  currency: a.currency || "INR",
                }))}
                title="Audit log so far"
              />
            ) : null}
          </div>
        </div>
      ) : null}

      {(stage === STAGE.customizing || stage === STAGE.receipt || stage === STAGE.done) && itinerary ? (
        <div className="grid grid--two">
          <div className="stack">
            <Itinerary itinerary={itinerary} onSwap={handleSwap} busy={busy} />
            {stage === STAGE.customizing ? (
              <>
                <FlightHotelSelector
                  sessionId={session.session_id}
                  selectedFlight={itinerary.selected_flight || session.selected_flight}
                  selectedHotel={itinerary.selected_hotel || session.selected_hotel}
                  budget={itinerary.budget || session.budget}
                  onSelectFlight={handleSelectFlight}
                  onSelectHotel={handleSelectHotel}
                  busy={busy}
                />
                <div className="card">
                  <h2 className="card__title">Next: pick a local guide</h2>
                  <p className="card__sub">
                    Guides below are filtered by your language, theme and real date availability.
                  </p>
                  <button
                    className="btn btn--primary"
                    onClick={() => setStage(STAGE.guides)}
                    disabled={busy}
                  >
                    Match me with a guide →
                  </button>
                </div>
              </>
            ) : null}
          </div>
          <div className="stack">
            <BudgetBar budget={itinerary.budget} />
            {itinerary.swaps && itinerary.swaps.length ? (
              <Ledger
                lines={itinerary.swaps.map((s) => ({
                  title: `${s.from_title} → ${s.to_title}`,
                  source_table: "PackagePro.package_components",
                  amount: s.delta,
                  currency: s.currency,
                }))}
                title="Swap ledger"
              />
            ) : null}
            <TraceTimeline events={session ? session.trace : []} />
          </div>
        </div>
      ) : null}

      {stage === STAGE.guides && session ? (
        <div className="grid grid--two">
          <div className="stack">
            <div className="card">
              <h2 className="card__title">
                Language-matched local guides
                <span className="badge badge--source">
                  PackagePro.tour_guides + guide_availability
                </span>
              </h2>
              <p className="card__sub">
                Only guides actually free on your trip dates can be selected. The date
                multiplier is applied with Decimal on the server.
              </p>
            </div>
            {guides.length ? (
              guides.map((g) => (
                <GuideCard
                  key={g.guide_id}
                  guide={g}
                  selected={session.selected_guide_id === g.guide_id}
                  onSelect={handleSelectGuide}
                  busy={busy}
                />
              ))
            ) : (
              <div className="empty">No guides matched this city.</div>
            )}
          </div>
          <div className="stack">
            <BudgetBar budget={session.budget} />
            <TraceTimeline events={session.trace} />
          </div>
        </div>
      ) : null}

      {(stage === STAGE.receipt || stage === STAGE.done) && receipt ? (
        <div className="grid grid--two">
          <TrustReceipt
            receipt={receipt}
            onConfirm={handleConfirm}
            busy={busy}
            confirmed={stage === STAGE.done}
          />
          <div className="stack">
            <BudgetBar budget={session.budget} />
            <Ledger
              lines={buildLedger(itinerary, session)}
              title="Cart ledger"
            />
            <TraceTimeline events={session.trace} title="Full transparency log" />
          </div>
        </div>
      ) : null}

      <NegotiateModal
        budget={negotiation}
        onChoose={handleNegotiate}
        onClose={() => setNegotiation(null)}
        busy={busy}
      />

      {viewPackage ? (
        <div className="modal-backdrop" role="dialog" onClick={() => setViewPackage(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{viewPackage.name}</h2>
            <p className="muted tiny">
              {viewPackage.city_name} · {viewPackage.theme} · {viewPackage.tier} ·{" "}
              {viewPackage.duration_days} days
            </p>
            <p className="tiny">{viewPackage.description}</p>
            <div className="pkg__tags">
              {viewPackage.languages_offered.map((l) => (
                <span className="tag tag--lang" key={l}>
                  {l}
                </span>
              ))}
            </div>
            <p className="tiny muted">
              <strong>Included total:</strong>{" "}
              {formatMoney(viewPackage.included_total, viewPackage.currency)} · base{" "}
              {formatMoney(viewPackage.base_price, viewPackage.currency)}
            </p>
            <p className="tiny muted">
              <strong>Inclusions:</strong> {viewPackage.inclusions}
            </p>
            <p className="tiny muted">
              <strong>Exclusions:</strong> {viewPackage.exclusions}
            </p>
            <div className="modal__actions">
              <button
                className="btn btn--primary"
                onClick={() => {
                  const pkg = viewPackage;
                  setViewPackage(null);
                  handleChoose(pkg.package_id);
                }}
                disabled={busy}
              >
                Choose this package
              </button>
              <button className="btn btn--ghost" onClick={() => setViewPackage(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <footer className="tiny muted" style={{ marginTop: 30, textAlign: "center" }}>
        Waypoint · PS-04 · PackagePro data is read-only · no payments · no real bookings ·
        money handled in Decimal
      </footer>
    </div>
  );
}

function currentStep(stage) {
  return Math.max(0, STEPPER.findIndex((s) => s.key === stage));
}

function buildLedger(itinerary, session) {
  const lines = [];
  if (!itinerary) return lines;
  const base = itinerary.included_total;
  lines.push({
    title: `${itinerary.package_name} — base price`,
    source_table: "PackagePro.tour_packages",
    amount: base,
    currency: itinerary.currency,
  });
  for (const day of itinerary.days) {
    for (const comp of day.components) {
      lines.push({
        title: `Day ${day.day_index} · ${comp.slot} · ${comp.title}`,
        source_table: "PackagePro.package_components",
        amount: comp.price_delta,
        currency: comp.currency,
      });
    }
  }
  const flight = itinerary.selected_flight || session?.selected_flight;
  if (flight && (flight.total_fare || flight.price)) {
    lines.push({
      title: `Flight · ${flight.airline} (${flight.flight_number}) · ${flight.origin_airport || flight.origin} → ${flight.destination_airport || flight.destination}`,
      source_table: flight.source || "Amadeus.flight-offers",
      amount: flight.total_fare || flight.price,
      currency: flight.currency || "INR",
    });
  }
  const hotel = itinerary.selected_hotel || session?.selected_hotel;
  if (hotel && (hotel.total_cost || hotel.price_total)) {
    lines.push({
      title: `Hotel · ${hotel.hotel_name} · ${hotel.room_name || hotel.room_type_name || "Room"} (${hotel.nights}n)`,
      source_table: hotel.source || "Hotelbeds.hotel-api",
      amount: hotel.total_cost || hotel.price_total,
      currency: hotel.currency || "INR",
    });
  }
  const guide = itinerary.selected_guide;
  if (guide && guide.selected_cost) {
    lines.push({
      title: `Guide · ${guide.display_name} · ${guide.selected_service}`,
      source_table: "PackagePro.tour_guides + guide_availability",
      amount: guide.selected_cost,
      currency: guide.currency,
    });
  }
  return lines;
}
