import ConfidenceBadge from "./ConfidenceBadge.jsx";

export default function CartConfirm({ cart, chosenFlight, chosenHotel, status, onConfirm, loading }) {
  if (!cart) return null;
  const confirmed = status === "confirmed";

  return (
    <div className="panel" style={{ padding: 20, border: confirmed ? "1px solid var(--go)" : "1px solid var(--signal)" }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 18, marginBottom: 14 }}>
        {confirmed ? "Confirmed" : "Cart — awaiting your confirmation"}
      </div>

      {chosenFlight && (
        <Row
          title={`Flight · ${chosenFlight.airline}`}
          detail={`${chosenFlight.origin} → ${chosenFlight.destination}, ${chosenFlight.date}`}
          price={chosenFlight.price_inr}
          reasoning={chosenFlight.agent_reasoning}
          confidence={chosenFlight.agent_confidence}
        />
      )}
      {chosenHotel && (
        <Row
          title={`Hotel · ${chosenHotel.name}`}
          detail={`${chosenHotel.nights} night(s), ${chosenHotel.rating}★`}
          price={chosenHotel.total_price_inr}
          reasoning={chosenHotel.agent_reasoning}
          confidence={chosenHotel.agent_confidence}
        />
      )}

      <div className="mono" style={{ display: "flex", justifyContent: "space-between", marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--line)", fontSize: 14 }}>
        <span>Total</span>
        <span style={{ color: "var(--signal)" }}>{cart.total_inr?.toLocaleString()} INR</span>
      </div>
      <div className="mono dim" style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span>Remaining under cap</span>
        <span>{cart.remaining_inr?.toLocaleString()} INR</span>
      </div>

      {!confirmed ? (
        <button
          onClick={onConfirm}
          disabled={loading}
          style={{
            marginTop: 16,
            width: "100%",
            padding: "12px",
            background: "var(--go)",
            color: "var(--ink)",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            fontSize: 14,
          }}
        >
          {loading ? "Booking…" : "Confirm & book (payment is mocked)"}
        </button>
      ) : (
        <div className="mono" style={{ marginTop: 16, color: "var(--go)", fontSize: 13 }}>
          ✓ Booked. Nothing further will be charged.
        </div>
      )}
    </div>
  );
}

function Row({ title, detail, price, reasoning, confidence }) {
  return (
    <div style={{ marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid var(--line)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 14 }}>{title}</span>
        <ConfidenceBadge confidence={confidence} />
      </div>
      <div className="dim" style={{ fontSize: 12, marginTop: 2 }}>{detail}</div>
      {reasoning && <div className="dim" style={{ fontSize: 12, marginTop: 4, fontStyle: "italic" }}>"{reasoning}"</div>}
      <div className="mono" style={{ fontSize: 13, marginTop: 4 }}>{price?.toLocaleString()} INR</div>
    </div>
  );
}
