import { useEffect, useRef } from "react";

const KIND_COLOR = {
  reasoning: "var(--dim)",
  tool_call: "var(--signal)",
  tool_result: "var(--go)",
  decision: "var(--paper)",
};

const KIND_LABEL = {
  reasoning: "think",
  tool_call: "call ",
  tool_result: "recv ",
  decision: "note ",
};

export default function AgentTraceFeed({ trace }) {
  // FIX B9: Auto-scroll trace feed to bottom
  const feedRef = useRef(null);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [trace]);

  return (
    <div className="panel" style={{ padding: 20, maxHeight: 360, overflowY: "auto", display: "flex", flexDirection: "column" }} ref={feedRef}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 18, marginBottom: 14 }}>
        Agent trace
      </div>
      <div className="mono" style={{ fontSize: 12, lineHeight: 1.7 }}>
        {trace.length === 0 && <div className="dim">Waiting for the agent to start…</div>}
        {trace.map((t, i) => (
          <div key={i} style={{ marginBottom: 4 }}>
            <span style={{ color: KIND_COLOR[t.kind] || "var(--dim)" }}>[{KIND_LABEL[t.kind] || t.kind}]</span>{" "}
            <span className="dim">{t.node}</span> — {t.content}
          </div>
        ))}
      </div>
    </div>
  );
}
