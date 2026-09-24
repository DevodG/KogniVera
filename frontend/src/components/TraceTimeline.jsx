import { formatMoney, money } from "../money.js";

const STATUS_CLASS = {
  complete: "event--complete",
  blocked: "event--blocked",
  running: "event--running",
};

/**
 * Structured transparency timeline.
 * Rule 8: this shows user-safe events, never chain-of-thought.
 */
export default function TraceTimeline({ events = [], title = "Agent activity log" }) {
  if (!events.length) {
    return (
      <div className="card">
        <h2 className="card__title">{title}</h2>
        <p className="card__sub">No activity yet. The log starts when you run the planner.</p>
      </div>
    );
  }
  return (
    <div className="card">
      <h2 className="card__title">
        <span className="pulse-dot pulse-dot--live" aria-hidden="true" />
        {title}
      </h2>
      <p className="card__sub">
        Structured, user-safe events. Sources are named; reasoning is never hidden.
      </p>
      <div className="timeline">
        {events.map((ev, i) => (
          <div className={`event ${STATUS_CLASS[ev.status] || ""}`} key={i}>
            <p className="event__summary">{ev.result_summary}</p>
            <p className="event__meta">
              step {ev.step} · {ev.action} · {ev.status} · {ev.source}
            </p>
            {ev.user_safe_reason ? (
              <p className="event__reason">{ev.user_safe_reason}</p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export function BudgetBar({ budget }) {
  if (!budget) return null;
  const cap = money(budget.cap);
  const total = money(budget.total);
  const pct = cap.gt(0) ? total.dividedBy(cap).times(100) : money("100");
  const clamped = Math.min(Math.max(pct.toNumber(), 0), 100);
  const over = total.gt(cap);
  const warn = !over && pct.gte(85);
  const cls = over ? "budget__fill--over" : warn ? "budget__fill--warn" : "";
  return (
    <div className="budget card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2 className="card__title" style={{ margin: 0 }}>
          Budget Guard
        </h2>
        <span className={`decision decision--${budget.decision === "approved" ? "approved" : "blocked"}`}>
          {budget.decision === "approved" ? "● approved" : "■ blocked"}
        </span>
      </div>
      <div className="budget__bar">
        <div className={`budget__fill ${cls}`} style={{ width: `${clamped}%` }} />
      </div>
      <div className="budget__line">
        <span>
          spent <strong>{formatMoney(budget.total, budget.currency)}</strong> of{" "}
          <strong>{formatMoney(budget.cap, budget.currency)}</strong>
        </span>
        <span>
          remaining <strong>{formatMoney(budget.remaining, budget.currency)}</strong>
        </span>
      </div>
      {over ? (
        <p className="tiny" style={{ color: "var(--red)", marginTop: 9 }}>
          Over cap by {formatMoney(budget.overage, budget.currency)}. Resolve below before
          confirming.
        </p>
      ) : null}
    </div>
  );
}

export function Ledger({ lines = [], title = "Ledger" }) {
  if (!lines.length) {
    return (
      <div className="card">
        <h2 className="card__title">{title}</h2>
        <p className="card__sub">Empty. Cart lines appear after a package is chosen.</p>
      </div>
    );
  }
  const currency = lines[0].currency;
  return (
    <div className="card">
      <h2 className="card__title">{title}</h2>
      <p className="card__sub">Every line names the table it came from.</p>
      <table className="ledger">
        <thead>
          <tr>
            <th>line</th>
            <th>source</th>
            <th className="num">amount</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((ln, i) => (
            <tr key={i}>
              <td>{ln.title}</td>
              <td className="muted">{ln.source_table}</td>
              <td className="num">{formatMoney(ln.amount, ln.currency)}</td>
            </tr>
          ))}
          <tr className="total">
            <td>total</td>
            <td />
            <td className="num">
              {formatMoney(
                lines.reduce((acc, ln) => acc.plus(money(ln.amount)), money("0")),
                currency,
              )}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
