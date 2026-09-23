import { useEffect, useState } from "react";
import { formatMoney } from "../money.js";
import * as api from "../api.js";

/**
 * Flight and Hotel add-on/customizer component.
 * Connects to external API adapters (Amadeus and Hotelbeds) with explicit
 * provenance badges, live price deltas, and strict BudgetGuard verification.
 */
export default function FlightHotelSelector({
  sessionId,
  selectedFlight,
  selectedHotel,
  onSelectFlight,
  onSelectHotel,
  busy,
}) {
  const [tab, setTab] = useState("flights");
  const [flights, setFlights] = useState([]);
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    Promise.all([
      api.getFlights(sessionId).catch(() => ({ flights: [] })),
      api.getHotels(sessionId).catch(() => ({ hotels: [] })),
    ])
      .then(([fltRes, htlRes]) => {
        setFlights(fltRes.flights || []);
        setHotels(htlRes.hotels || []);
      })
      .finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <h2 className="card__title" style={{ margin: 0 }}>
          External Travel Add-ons
          <span className="badge badge--swappable">Live-API Ready</span>
        </h2>
        <button
          type="button"
          className="btn btn--ghost tiny"
          onClick={() => setIsOpen((prev) => !prev)}
        >
          {isOpen ? "Collapse ▲" : "Expand add-ons ▼"}
        </button>
      </div>

      <p className="card__sub">
        Optionally add real-time flight offers and room selections. Every choice routes
        structurally through the <strong>Budget Guard</strong> before being committed.
      </p>

      {isOpen ? (
        <>
          <div className="row" style={{ gap: 8, marginBottom: 14 }}>
            <button
              type="button"
              className={`btn tiny ${tab === "flights" ? "btn--primary" : "btn--ghost"}`}
              onClick={() => setTab("flights")}
            >
              Flights ({flights.length}) · Amadeus
            </button>
            <button
              type="button"
              className={`btn tiny ${tab === "hotels" ? "btn--primary" : "btn--ghost"}`}
              onClick={() => setTab("hotels")}
            >
              Hotels ({hotels.length}) · Hotelbeds
            </button>
          </div>

          {loading ? (
            <p className="tiny muted">Loading live offers from external adapters…</p>
          ) : null}

          {/* ---------------- Flights Tab ---------------- */}
          {tab === "flights" && !loading ? (
            <div className="stack" style={{ gap: 10 }}>
              {flights.length === 0 ? (
                <p className="tiny muted">No flight offers found for this route.</p>
              ) : (
                flights.map((f) => {
                  const isChosen = selectedFlight?.flight_id === f.flight_id;
                  return (
                    <div
                      key={f.flight_id}
                      className="pkg"
                      style={{
                        padding: 12,
                        borderColor: isChosen ? "var(--green)" : "var(--line-soft)",
                        background: isChosen ? "rgba(52, 211, 153, 0.05)" : "var(--navy-900)",
                      }}
                    >
                      <div className="pkg__head">
                        <div>
                          <h4 style={{ margin: "0 0 4px", fontSize: 14 }}>
                            {f.airline} · {f.flight_number}
                            <span className="badge badge--source" style={{ marginLeft: 6 }}>
                              {f.source}
                            </span>
                            {isChosen ? (
                              <span className="tag tag--lang" style={{ marginLeft: 6 }}>
                                Selected in cart
                              </span>
                            ) : null}
                          </h4>
                          <p className="pkg__meta" style={{ margin: 0 }}>
                            {f.origin_airport} ({f.departure_time}) → {f.destination_airport} ({f.arrival_time})
                            {" · "}{f.cabin} · {f.stops === 0 ? "Non-stop" : `${f.stops} stop`}
                          </p>
                        </div>
                        <div className="pkg__price">
                          {formatMoney(f.total_fare, f.currency)}
                          <small>total ({f.travelers} pax)</small>
                          <small style={{ color: "var(--text-faint)" }}>
                            {formatMoney(f.fare_per_traveler, f.currency)} / pax
                          </small>
                        </div>
                      </div>

                      <div className="pkg__actions" style={{ marginTop: 8 }}>
                        <button
                          type="button"
                          className="btn btn--primary tiny"
                          onClick={() => onSelectFlight && onSelectFlight(f)}
                          disabled={busy || isChosen}
                        >
                          {isChosen ? "✓ Flight Added" : "Add Flight to Trip"}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          ) : null}

          {/* ---------------- Hotels Tab ---------------- */}
          {tab === "hotels" && !loading ? (
            <div className="stack" style={{ gap: 10 }}>
              {hotels.length === 0 ? (
                <p className="tiny muted">No hotel room options found for this city.</p>
              ) : (
                hotels.map((h) => {
                  const isChosen = selectedHotel?.hotel_id === h.hotel_id && selectedHotel?.room_type_id === h.room_type_id;
                  return (
                    <div
                      key={`${h.hotel_id}-${h.room_type_id}`}
                      className="pkg"
                      style={{
                        padding: 12,
                        borderColor: isChosen ? "var(--green)" : "var(--line-soft)",
                        background: isChosen ? "rgba(52, 211, 153, 0.05)" : "var(--navy-900)",
                      }}
                    >
                      <div className="pkg__head">
                        <div>
                          <h4 style={{ margin: "0 0 4px", fontSize: 14 }}>
                            {h.hotel_name} · {h.room_name}
                            <span className="badge badge--source" style={{ marginLeft: 6 }}>
                              {h.source}
                            </span>
                            {isChosen ? (
                              <span className="tag tag--lang" style={{ marginLeft: 6 }}>
                                Selected
                              </span>
                            ) : null}
                          </h4>
                          <p className="pkg__meta" style={{ margin: 0 }}>
                            {"★".repeat(h.star_rating)} · Rating {h.guest_score} · {h.property_type}
                            {" · "}{h.bed_config} · {h.size_sqm} m² · {h.nights} nights
                          </p>
                        </div>
                        <div className="pkg__price">
                          {formatMoney(h.total_cost, h.currency)}
                          <small>total ({h.nights} nights)</small>
                          <small style={{ color: "var(--text-faint)" }}>
                            {formatMoney(h.rate_per_night, h.currency)} / night
                          </small>
                        </div>
                      </div>

                      <p className="tiny muted" style={{ margin: "6px 0" }}>
                        {h.description}
                      </p>

                      <div className="pkg__actions" style={{ marginTop: 8 }}>
                        <button
                          type="button"
                          className="btn btn--primary tiny"
                          onClick={() => onSelectHotel && onSelectHotel(h)}
                          disabled={busy || isChosen}
                        >
                          {isChosen ? "✓ Room Selected" : "Select Room Upgrade"}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
