const CHOICE_MAP = [
  { match: "Approve", value: "approve_overage" },
  { match: "Swap", value: "swap_cheaper" },
  { match: "Remove", value: "remove_item" },
  { match: "Raise", value: "raise_cap" },
];

function toChoiceValue(label) {
  return CHOICE_MAP.find((c) => label.startsWith(c.match))?.value || "swap_cheaper";
}

export default function NegotiationGate({ options, onChoose, loading }) {
  return (
    <div className="panel" style={{ padding: 20, border: "1px solid var(--stop)" }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 18, color: "var(--stop)", marginBottom: 6 }}>
        Over budget — your call
      </div>
      <div className="dim" style={{ fontSize: 13, marginBottom: 16, lineHeight: 1.5 }}>
        The agent refused to add this cost silently. Pick how you want it to proceed.
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {options.map((opt) => (
          <button
            key={opt}
            disabled={loading}
            onClick={() => onChoose(toChoiceValue(opt))}
            style={{
              textAlign: "left",
              padding: "10px 14px",
              background: "var(--panel-raised)",
              border: "1px solid var(--line)",
              borderRadius: 8,
              color: "var(--paper)",
              fontSize: 13,
            }}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
