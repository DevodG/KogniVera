export default function ConfidenceBadge({ confidence }) {
  const pct = Math.round((confidence ?? 0) * 100);
  const color = pct >= 80 ? "var(--go)" : pct >= 55 ? "var(--signal)" : "var(--stop)";
  return (
    <span
      className="mono"
      style={{
        fontSize: 11,
        color,
        border: `1px solid ${color}`,
        borderRadius: 999,
        padding: "2px 8px",
        whiteSpace: "nowrap",
      }}
      title="How confident the agent is in this pick"
    >
      {pct}% confident
    </span>
  );
}
