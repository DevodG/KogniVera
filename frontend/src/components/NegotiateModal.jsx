import { useState } from "react";
import { money, formatMoney } from "../money.js";

const OPTIONS = [
  {
    key: "select_cheaper_alternative",
    label: "Select a cheaper verified alternative",
    hint: "Swap or remove something to bring the total back under the cap.",
  },
  {
    key: "remove_optional_component",
    label: "Remove an optional component",
    hint: "Drop an optional add-on from the itinerary.",
  },
  {
    key: "raise_budget_cap",
    label: "Raise the budget cap",
    hint: "Enter a higher INR cap. The guard then re-checks against it.",
  },
  {
    key: "approve_overage",
    label: "Explicitly approve this exact overage",
    hint: "You accept the exact amount shown. This is written to the audit log.",
  },
];

/**
 * The budget negotiation modal. Rendered when the guard blocks a change; the
 * traveller must pick one of the four trade-offs.
 */
export default function NegotiateModal({ budget, onChoose, onClose, busy }) {
  const [newCap, setNewCap] = useState("");
  const [chosen, setChosen] = useState(null);

  if (!budget || budget.decision !== "blocked") return null;

  function choose(option) {
    setChosen(option);
    const extra = {};
    if (option === "raise_budget_cap") {
      try {
        extra.new_budget = {
          amount: money(newCap).toDecimalPlaces(2).toString(),
          currency: budget.currency,
        };
      } catch {
        return;
      }
    }
    onChoose(option, extra);
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Budget Guard blocked this choice</h2>
        <p className="muted tiny">
          This choice would exceed your {formatMoney(budget.cap, budget.currency)} cap by{" "}
          <strong style={{ color: "var(--red)" }}>
            {formatMoney(budget.overage, budget.currency)}
          </strong>
          . Nothing was applied. Choose one:
        </p>
        <ol className="pkg__reasons" style={{ paddingLeft: 19 }}>
          {OPTIONS.map((o) => (
            <li key={o.key} style={{ marginBottom: 7 }}>
              <strong>{o.label}</strong> — {o.hint}
            </li>
          ))}
        </ol>

        {chosen === "raise_budget_cap" ? (
          <div className="field" style={{ marginTop: 12 }}>
            <label htmlFor="newcap">New cap (must be higher than {formatMoney(budget.cap, budget.currency)})</label>
            <input
              id="newcap"
              inputMode="decimal"
              placeholder="e.g. 25000.00"
              value={newCap}
              onChange={(e) => setNewCap(e.target.value)}
            />
          </div>
        ) : null}

        <div className="modal__actions">
          <button
            className="btn btn--ghost"
            onClick={() => {
              setChosen("raise_budget_cap");
            }}
            disabled={busy}
          >
            Raise budget cap…
          </button>
          <button
            className="btn"
            onClick={() => choose("raise_budget_cap")}
            disabled={busy || (chosen === "raise_budget_cap" && !newCap)}
          >
            Apply raised cap
          </button>
          <button
            className="btn btn--danger"
            onClick={() => choose("approve_overage")}
            disabled={busy}
          >
            Approve exact overage
          </button>
          <button className="btn btn--ghost" onClick={onClose} disabled={busy}>
            Close
          </button>
        </div>

        <p className="tiny muted" style={{ marginTop: 12 }}>
          Every choice here is written to the audit log before anything is persisted.
        </p>
      </div>
    </div>
  );
}