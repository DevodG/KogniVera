export default function PlanTimeline({ steps }) {
  return (
    <div className="panel" style={{ padding: 20 }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 18, marginBottom: 14 }}>
        The plan
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {steps.map((s) => (
          <div key={s.id} style={{ display: "flex", alignItems: "center", fontSize: 13 }}>
            <span className={`status-dot ${s.status}`} />
            <span
              className="mono"
              style={{
                color: s.status === "done" ? "var(--paper)" : "var(--dim)",
                textDecoration: s.status === "failed" ? "line-through" : "none",
              }}
            >
              {s.title}
            </span>
            {s.status === "failed" && (
              <span style={{ marginLeft: 8, color: "var(--stop)", fontSize: 11 }}>needs your input →</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
