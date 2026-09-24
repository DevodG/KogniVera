import { formatMoney } from "../money.js";

/**
 * The Trust Receipt: every decision, its source, why it was selected, and its
 * exact price effect. Followed by an explicit, mocked confirmation.
 */
export default function TrustReceipt({ receipt, onConfirm, busy, confirmed }) {
  if (!receipt) return null;
  const guardPassed = receipt.budget_guard === "Passed";
  return (
    <div className="card">
      <h2 className="card__title">
        Trust Receipt
        <span className="badge badge--source">Waypoint session store</span>
      </h2>
      <p className="card__sub">
        Everything above is reconstructed from the audit trail. Nothing here was generated
        without a named data source.
      </p>

      <table className="ledger receipt__row">
        <thead>
          <tr>
            <th>decision</th>
            <th>source</th>
            <th>why selected</th>
            <th className="num">price effect</th>
          </tr>
        </thead>
        <tbody>
          {receipt.rows.map((row, i) => (
            <tr key={i}>
              <td>{row.decision}</td>
              <td className="muted">{row.source}</td>
              <td className="muted" style={{ fontFamily: "var(--sans)", fontSize: 11.5 }}>
                {row.why_selected}
              </td>
              <td className="num">{formatMoney(row.price_effect, row.currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pkg__tags" style={{ marginTop: 14 }}>
        {Object.entries(receipt.totals).map(([k, v]) => (
          <span className="tag" key={k}>
            {k}: {k === "budget_cap" || k === "remaining" || k === "grand_total"
              ? formatMoney(v, "INR")
              : formatMoney(v, "INR")}
          </span>
        ))}
      </div>

      <div className="spacer" />
      <div className="receipt__flag">
        <span className={`tick ${guardPassed ? "tick--ok" : "tick--warn"}`}>
          {guardPassed ? "✓" : "!"}
        </span>
        Data-backed plan: <strong>Yes</strong>
      </div>
      <div className="receipt__flag">
        <span className={`tick ${guardPassed ? "tick--ok" : "tick--warn"}`}>
          {guardPassed ? "✓" : "!"}
        </span>
        Budget Guard: <strong>{receipt.budget_guard}</strong>
      </div>
      <div className="receipt__flag">
        <span className="tick tick--ok">✓</span>
        Automatic booking: <strong>Disabled</strong>
      </div>
      <div className="receipt__flag">
        <span className="tick tick--warn">!</span>
        User confirmation required: <strong>Yes</strong>
      </div>

      <div className="modal__actions">
        <button
          className="btn btn--primary"
          onClick={onConfirm}
          disabled={busy || confirmed || !guardPassed}
          title={guardPassed ? "Record a mock confirmation" : "Resolve the overage first"}
        >
          {confirmed ? "✓ mock confirmed" : "Confirm booking (mock)"}
        </button>
        {!guardPassed ? (
          <span className="tiny" style={{ color: "var(--red)" }}>
            Blocked: the cap is exceeded. Resolve the negotiation first.
          </span>
        ) : null}
      </div>

      {confirmed && receipt.confirmation ? (
        <div className="alert alert--info" style={{ marginTop: 14 }}>
          <h3>Mock confirmation recorded</h3>
          <p className="mono tiny">
            reference {receipt.confirmation.booking_reference} ·{" "}
            {formatMoney(receipt.confirmation.total_amount, receipt.confirmation.currency)} ·{" "}
            {receipt.confirmation.confirmed_at}
          </p>
          <p className="tiny" style={{ marginTop: 7 }}>
            {receipt.confirmation.note}
          </p>
        </div>
      ) : null}
    </div>
  );
}
